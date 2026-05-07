"""Helpers for reading the checked-in EarthBound SPC700 sound-driver source."""

from __future__ import annotations

from dataclasses import dataclass
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SOURCE_ROOT = ROOT / "refs" / "earthbound-sounddriver-byte-perfect"
DEFAULT_MAIN = DEFAULT_SOURCE_ROOT / "main.asm"
DEFAULT_RAM = DEFAULT_SOURCE_ROOT / "ram.asm"

HIGH_COMMAND_FIRST = 0xE0
HIGH_COMMAND_LAST = 0xFE


@dataclass(frozen=True)
class SourceLabel:
    name: str
    address: int


@dataclass(frozen=True)
class RamAlias:
    name: str
    address: int
    comment: str | None


@dataclass(frozen=True)
class VcmdEntry:
    command: int
    source_label: str
    source_target: int
    arg_length: int
    source_role: str


def hex_byte(value: int) -> str:
    return f"0x{value:02X}"


def hex_word(value: int) -> str:
    return f"0x{value:04X}"


def parse_source_labels(main_path: Path = DEFAULT_MAIN) -> dict[str, SourceLabel]:
    lines = main_path.read_text(encoding="utf-8").splitlines()
    labels: dict[str, SourceLabel] = {}
    current_addr: int | None = None
    addr_re = re.compile(r"^;\s+\$(?P<addr>[0-9A-F]{4})(?:\b.*)?$")
    label_re = re.compile(r"^(?P<label>[A-Za-z0-9_]+):")
    byte_comment_re = re.compile(r";\s*(?P<bytes>(?:[0-9A-F]{2}\s*)+)$", re.IGNORECASE)

    for line in lines:
        addr_match = addr_re.match(line.strip())
        if addr_match:
            current_addr = int(addr_match.group("addr"), 16)
            continue
        label_match = label_re.match(line.strip())
        if label_match and current_addr is not None:
            label = label_match.group("label")
            if label.startswith("L_") and re.fullmatch(r"L_[0-9A-Fa-f]{4}", label):
                label_addr = int(label.split("_", 1)[1], 16)
            else:
                label_addr = current_addr
            labels[label] = SourceLabel(label, label_addr)
        if current_addr is None:
            continue
        byte_match = byte_comment_re.search(line)
        if byte_match:
            current_addr += len(byte_match.group("bytes").split())
            continue
        stripped = line.strip()
        if stripped.startswith("dw "):
            current_addr += 2 * len([chunk for chunk in stripped.split("dw ", 1)[1].split(";", 1)[0].split(",") if chunk.strip()])
        elif stripped.startswith("db "):
            current_addr += len([chunk for chunk in stripped.split("db ", 1)[1].split(";", 1)[0].split(",") if chunk.strip()])
    return labels


def parse_ram_aliases(ram_path: Path = DEFAULT_RAM) -> dict[str, RamAlias]:
    aliases: dict[str, RamAlias] = {}
    alias_re = re.compile(r"^(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*=\s*\$(?P<addr>[0-9A-Fa-f]{2,4})(?:\s*;\s*(?P<comment>.*))?$")

    for line in ram_path.read_text(encoding="utf-8").splitlines():
        match = alias_re.match(line.strip())
        if not match:
            continue
        name = match.group("name")
        aliases[name] = RamAlias(
            name=name,
            address=int(match.group("addr"), 16),
            comment=match.group("comment"),
        )
    return aliases


def _source_lines(main_path: Path) -> list[str]:
    return main_path.read_text(encoding="utf-8").splitlines()


def _table_bounds(lines: list[str]) -> tuple[int, int]:
    table_index = next(index for index, line in enumerate(lines) if line.strip().startswith("VCMD_Jump_Table:"))
    arg_index = next(index for index, line in enumerate(lines) if line.strip().startswith("VCMD_Arg_Length:"))
    return table_index, arg_index


def parse_vcmd_arg_lengths(main_path: Path = DEFAULT_MAIN) -> dict[int, int]:
    lines = _source_lines(main_path)
    _, arg_index = _table_bounds(lines)
    lengths: dict[int, int] = {}
    command = HIGH_COMMAND_FIRST

    for line in lines[arg_index + 1:]:
        stripped = line.strip()
        if not stripped.startswith("db "):
            if lengths:
                break
            continue
        bytes_part = stripped.split("db ", 1)[1].split(";", 1)[0]
        for chunk in bytes_part.split(","):
            value = chunk.strip()
            if not value:
                continue
            lengths[command] = int(value, 0)
            command += 1
    return lengths


def parse_vcmd_entries(main_path: Path = DEFAULT_MAIN) -> list[VcmdEntry]:
    lines = _source_lines(main_path)
    labels = parse_source_labels(main_path)
    arg_lengths = parse_vcmd_arg_lengths(main_path)
    table_index, arg_index = _table_bounds(lines)
    entries: list[VcmdEntry] = []
    command = HIGH_COMMAND_FIRST

    for line in lines[table_index + 1:arg_index]:
        stripped = line.strip()
        if not stripped.startswith("dw "):
            continue
        label = stripped.split("dw ", 1)[1].split(";", 1)[0].strip()
        if label not in labels:
            continue
        if command > HIGH_COMMAND_LAST:
            raise ValueError("VCMD source table has more entries than expected for E0..FE")
        entries.append(
            VcmdEntry(
                command=command,
                source_label=label,
                source_target=labels[label].address,
                arg_length=arg_lengths[command],
                source_role="source_backed_vcmd",
            )
        )
        command += 1

    if command != HIGH_COMMAND_LAST + 1:
        raise ValueError(f"VCMD source table ended at {hex_byte(command - 1)}; expected {hex_byte(HIGH_COMMAND_LAST)}")
    return entries


def source_table_summary(main_path: Path = DEFAULT_MAIN, ram_path: Path = DEFAULT_RAM) -> dict[str, Any]:
    labels = parse_source_labels(main_path)
    aliases = parse_ram_aliases(ram_path)
    entries = parse_vcmd_entries(main_path)
    return {
        "main_path": str(main_path.relative_to(ROOT)).replace("\\", "/"),
        "ram_path": str(ram_path.relative_to(ROOT)).replace("\\", "/"),
        "vcmd_table": hex_word(labels["VCMD_Jump_Table"].address),
        "vcmd_arg_length_table": hex_word(labels["VCMD_Arg_Length"].address),
        "get_next_byte": hex_word(labels["GetNextByte"].address),
        "skip_byte": hex_word(labels["SkipByte"].address),
        "vcmd_command_range": f"{hex_byte(HIGH_COMMAND_FIRST)}..{hex_byte(HIGH_COMMAND_LAST)}",
        "vcmd_entry_count": len(entries),
        "ram_alias_count": len(aliases),
    }


def vcmd_entry_records(main_path: Path = DEFAULT_MAIN) -> list[dict[str, Any]]:
    return [
        {
            "command": hex_byte(entry.command),
            "source_label": entry.source_label,
            "source_target": hex_word(entry.source_target),
            "arg_length": entry.arg_length,
            "source_role": entry.source_role,
        }
        for entry in parse_vcmd_entries(main_path)
    ]


def ram_alias_records(ram_path: Path = DEFAULT_RAM) -> list[dict[str, Any]]:
    aliases = sorted(parse_ram_aliases(ram_path).values(), key=lambda alias: (alias.address, alias.name))
    return [
        {
            "name": alias.name,
            "address": hex_word(alias.address),
            "comment": alias.comment,
        }
        for alias in aliases
    ]
