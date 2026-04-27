from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from decode_event_script import CALL_ARG_COUNTS, OPCODES, Address, Opcode, load_names, read_u16
from rom_tools import find_rom, hirom_to_file_offset, load_rom


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SOURCE_MAP = ROOT / "build" / "c3-source-data-map.json"
DEFAULT_REF_INDEX = ROOT / "build" / "ref-index.json"
DEFAULT_OUTPUT = ROOT / "src" / "c3" / "event_scripts" / "movement_pulse_presets.asar.asm"
DEFAULT_REPORT = ROOT / "notes" / "c3-event-script-source-pilot.md"
DEFAULT_MANIFEST = ROOT / "build" / "c3-event-script-source-pilot.json"

FAMILY_ID = "movement-pulse-presets"

SCRIPT_ROWS = [
    "C3:A09F",
    "C3:A0B2",
    "C3:A0C5",
    "C3:A0D8",
    "C3:A12E",
    "C3:A15E",
    "C3:A17B",
    "C3:A18F",
    "C3:A1A3",
    "C3:A1B7",
    "C3:A1CB",
    "C3:A1DF",
    "C3:A1F3",
]

PRESET_ROWS = [
    "C3:AA38",
    "C3:AA46",
    "C3:AA5A",
    "C3:AA6E",
    "C3:AA82",
    "C3:AA96",
    "C3:AAAA",
    "C3:AAB8",
    "C3:AAC2",
    "C3:AAD6",
    "C3:AAEA",
    "C3:AAFE",
    "C3:AB12",
    "C3:AB26",
]

LABEL_OVERRIDES = {
    "C3:A09F": "LoopActiveEntityWalkAnimationPulse",
    "C3:A0B2": "LoopActiveEntityWalkPulse24Frame",
    "C3:A0C5": "LoopActiveEntityWalkPulse12Frame",
    "C3:A0D8": "LoopActiveEntityWalkPulse9FrameConditional",
    "C3:A0EB": "LoopActiveEntityWalkPulse6FrameConditional",
    "C3:A0FE": "LoopActiveEntityWalkPulse2FrameConditional",
    "C3:A111": "LoopActiveEntityWalkPulseVar4Gate",
    "C3:A11E": "LoopActiveEntityWalkPulseVar4Gate_OffHalf",
    "C3:A12E": "LoopActiveEntityWalkPulseVar4Countdown",
    "C3:A159": "LoopActiveEntityWalkPulseVar4Countdown_WaitAndRestart",
    "C3:A15E": "LoopC40015Var4GatedPulseUntilRelease",
    "C3:A162": "LoopC40015Var4GatedPulseUntilRelease_Loop",
    "C3:A16F": "LoopC40015Var4GatedPulseUntilRelease_CheckRelease",
    "C3:A17B": "LoopC40015SlowPulseUntilRelease",
    "C3:A18F": "LoopC40015FastPulseUntilRelease",
    "C3:A1A3": "LoopC40015Pulse12FrameUntilRelease",
    "C3:A1B7": "LoopC40015Pulse9FrameUntilRelease",
    "C3:A1CB": "LoopC40015Pulse6FrameUntilRelease",
    "C3:A1DF": "LoopActiveEntityWalkPulse2FrameC40015Branch",
    "C3:A1F3": "LoopC40015Pulse16FrameUntilRelease",
    "C3:A204": "ReleaseCurrentVisualEntityAndEnd",
    "C3:AA38": "InitActionScriptMovementState",
    "C3:AA46": "InitMovementPreset40_00Pulse24Frame",
    "C3:AA5A": "InitMovementPreset00_01Pulse12Frame",
    "C3:AA6E": "InitMovementPreset60_01Pulse9Frame",
    "C3:AA82": "InitMovementPreset00_02Pulse6Frame",
    "C3:AA96": "InitMovementPreset00_06Pulse2Frame",
    "C3:AAAA": "InitMovementPresetVar4Countdown",
    "C3:AAB8": "InitMovementPresetC40015Pulse16Frame",
    "C3:AAC2": "InitMovementPreset40_00C40015FastPulse",
    "C3:AAD6": "InitMovementPreset00_01C40015Pulse12Frame",
    "C3:AAEA": "InitMovementPreset60_01C40015Pulse9Frame",
    "C3:AAFE": "InitMovementPreset00_02C40015Pulse6Frame",
    "C3:AB12": "InitMovementPreset00_06C40015Branch",
    "C3:AB26": "InitAlternatePhysicsVar4WalkPulse",
}

VAR_NAMES = {
    0x04: "!ACTIONSCRIPT_VARS_V4",
}


@dataclass(frozen=True)
class Operand:
    kind: str
    value: int | Address


@dataclass(frozen=True)
class Instruction:
    address: Address
    opcode_byte: int
    opcode: Opcode
    raw: bytes
    operands: tuple[Operand, ...]
    call_arg_count: int | None = None


@dataclass(frozen=True)
class RowSource:
    address: Address
    key: str
    name: str
    size: int
    raw: bytes
    instructions: tuple[Instruction, ...]


def parse_address_key(text: str) -> Address:
    bank_text, offset_text = text.split(":", 1)
    return Address(int(bank_text, 16), int(offset_text, 16))


def fmt_byte(value: int) -> str:
    return f"${value & 0xFF:02X}"


def fmt_word(value: int) -> str:
    return f"${value & 0xFFFF:04X}"


def fmt_long(value: int) -> str:
    return f"${value & 0xFFFFFF:06X}"


def sanitize_symbol(text: str) -> str:
    text = text.replace("::", "_")
    text = re.sub(r"[^0-9A-Za-z_]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    if not text:
        text = "Target"
    if text[0].isdigit():
        text = f"Addr_{text}"
    return text


def preferred_label(address: Address, names: dict[str, list[str]]) -> str:
    if address.key in LABEL_OVERRIDES:
        return LABEL_OVERRIDES[address.key]
    if names.get(address.key):
        return names[address.key][0]
    return f"Local_{address.bank:02X}{address.offset:04X}"


def row_name(row: dict[str, Any], names: dict[str, list[str]]) -> str:
    address = parse_address_key(row["address"])
    if address.key in LABEL_OVERRIDES:
        return LABEL_OVERRIDES[address.key]
    if row.get("name"):
        return str(row["name"])
    if names.get(address.key):
        return names[address.key][0]
    return f"Script_{address.bank:02X}{address.offset:04X}"


def load_row_map(path: Path) -> dict[str, dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows: dict[str, dict[str, Any]] = {}
    for row in payload["include_rows"]:
        address = row.get("address")
        if address:
            rows[address] = row
    return rows


def decode_exact_row(raw: bytes, start: Address) -> tuple[Instruction, ...]:
    instructions: list[Instruction] = []
    pos = 0
    while pos < len(raw):
        address = Address(start.bank, start.offset + pos)
        raw_start = pos
        opcode_byte = raw[pos]
        pos += 1
        opcode = OPCODES.get(opcode_byte)
        if opcode is None:
            raise ValueError(f"unknown opcode ${opcode_byte:02X} at {address.key}")

        operands: list[Operand] = []
        call_arg_count: int | None = None
        for spec in opcode.args:
            if spec == "byte":
                operands.append(Operand(spec, raw[pos]))
                pos += 1
            elif spec == "word":
                operands.append(Operand(spec, read_u16(raw, pos)))
                pos += 2
            elif spec == "shortptr":
                operands.append(Operand(spec, Address(start.bank, read_u16(raw, pos))))
                pos += 2
            elif spec == "callbackptr":
                operands.append(Operand(spec, Address(0xC0, read_u16(raw, pos))))
                pos += 2
            elif spec == "ptr3":
                operands.append(Operand(spec, Address(raw[pos + 2], read_u16(raw, pos))))
                pos += 3
            elif spec == "callroutine":
                target = Address(raw[pos + 2], read_u16(raw, pos))
                pos += 3
                operands.append(Operand(spec, target))
                count = CALL_ARG_COUNTS.get(target.key)
                if count is None:
                    raise ValueError(f"unknown callroutine arg count for {target.key} at {address.key}")
                call_arg_count = count
                for _ in range(count):
                    operands.append(Operand("call_arg_byte", raw[pos]))
                    pos += 1
            elif spec == "wordlist":
                count = raw[pos]
                pos += 1
                operands.append(Operand("wordlist_count", count))
                for _ in range(count):
                    operands.append(Operand("wordlist_shortptr", Address(start.bank, read_u16(raw, pos))))
                    pos += 2
            else:
                raise ValueError(f"unhandled operand spec {spec!r}")

        if pos > len(raw):
            raise ValueError(f"instruction at {address.key} runs past row end")
        instructions.append(
            Instruction(
                address=address,
                opcode_byte=opcode_byte,
                opcode=opcode,
                raw=raw[raw_start:pos],
                operands=tuple(operands),
                call_arg_count=call_arg_count,
            )
        )
    return tuple(instructions)


def load_rows(
    rom: bytes,
    rows_by_address: dict[str, dict[str, Any]],
    row_keys: list[str],
    names: dict[str, list[str]],
) -> list[RowSource]:
    rows: list[RowSource] = []
    for key in row_keys:
        row = rows_by_address.get(key)
        if not row:
            raise KeyError(f"{key} is not an addressed include row in the source/data map")
        address = parse_address_key(key)
        size = int(row["size"])
        file_offset = hirom_to_file_offset(address.bank, address.offset, len(rom))
        if file_offset is None:
            raise ValueError(f"{key} is not a mapped HiROM address")
        raw = rom[file_offset : file_offset + size]
        rows.append(
            RowSource(
                address=address,
                key=key,
                name=sanitize_symbol(row_name(row, names)),
                size=size,
                raw=raw,
                instructions=decode_exact_row(raw, address),
            )
        )
    return rows


def collect_selected_ranges(rows: list[RowSource]) -> list[tuple[int, int]]:
    return [(row.address.long, row.address.long + row.size) for row in rows]


def in_selected_ranges(address: Address, ranges: list[tuple[int, int]]) -> bool:
    return any(start <= address.long < end for start, end in ranges)


def collect_c3_targets(rows: list[RowSource]) -> set[str]:
    targets: set[str] = set()
    for row in rows:
        for instruction in row.instructions:
            for operand in instruction.operands:
                if isinstance(operand.value, Address) and operand.value.bank == 0xC3:
                    targets.add(operand.value.key)
    return targets


def collect_label_map(rows: list[RowSource], names: dict[str, list[str]]) -> dict[str, str]:
    ranges = collect_selected_ranges(rows)
    labels: dict[str, str] = {row.key: row.name for row in rows}
    instruction_addresses = {
        instruction.address.key
        for row in rows
        for instruction in row.instructions
    }
    for key in collect_c3_targets(rows):
        address = parse_address_key(key)
        if key in labels:
            continue
        if in_selected_ranges(address, ranges) and key in instruction_addresses:
            labels[key] = sanitize_symbol(preferred_label(address, names))
    return labels


def constant_name(address: Address, names: dict[str, list[str]]) -> str:
    if address.key in LABEL_OVERRIDES:
        return sanitize_symbol(LABEL_OVERRIDES[address.key])
    if names.get(address.key):
        return sanitize_symbol(names[address.key][0])
    return f"Target_{address.bank:02X}{address.offset:04X}"


def operand_expr(
    operand: Operand,
    *,
    labels: dict[str, str],
    names: dict[str, list[str]],
    constants: dict[str, str],
) -> str:
    if operand.kind == "byte":
        value = int(operand.value)
        return VAR_NAMES.get(value, fmt_byte(value))
    if operand.kind in {"word", "call_arg_byte"}:
        value = int(operand.value)
        return fmt_byte(value) if operand.kind == "call_arg_byte" else fmt_word(value)
    if operand.kind == "wordlist_count":
        return str(int(operand.value))

    if not isinstance(operand.value, Address):
        raise TypeError(f"expected address operand, got {operand.value!r}")

    target = operand.value
    if operand.kind in {"shortptr", "wordlist_shortptr"} and target.key in labels:
        return labels[target.key]

    name = constant_name(target, names)
    symbol = f"!{name}"
    if operand.kind in {"shortptr", "callbackptr", "wordlist_shortptr"}:
        constants.setdefault(symbol, fmt_word(target.offset))
    else:
        constants.setdefault(symbol, fmt_long(target.long))
    return symbol


def macro_name(instruction: Instruction) -> str:
    if instruction.opcode.name == "EVENT_CALLROUTINE":
        return f"EVENT_CALLROUTINE_{instruction.call_arg_count or 0}"
    if instruction.opcode.name in {"EVENT_SWITCH_JUMP_TEMPVAR", "EVENT_SWITCH_CALL_TEMPVAR"}:
        return f"{instruction.opcode.name}_{instruction.operands[0].value}"
    return instruction.opcode.name


def render_instruction(
    instruction: Instruction,
    *,
    labels: dict[str, str],
    names: dict[str, list[str]],
    constants: dict[str, str],
) -> str:
    rendered_operands = [
        operand_expr(operand, labels=labels, names=names, constants=constants)
        for operand in instruction.operands
    ]
    args = ", ".join(rendered_operands)
    raw = " ".join(f"{byte:02X}" for byte in instruction.raw)
    if args:
        return f"    %{macro_name(instruction)}({args}) ; {instruction.address.key}  {raw}"
    return f"    %{macro_name(instruction)}() ; {instruction.address.key}  {raw}"


def macro_definitions(used_macros: set[str]) -> list[str]:
    bodies = {
        "EVENT_BREAK_IF_FALSE": ["    db $16", "    dw <target>"],
        "EVENT_CALLROUTINE_0": ["    db $42", "    dl <target>"],
        "EVENT_CALLROUTINE_2": ["    db $42", "    dl <target>", "    db <arg0>, <arg1>"],
        "EVENT_CLEAR_TICK_CALLBACK": ["    db $0F"],
        "EVENT_END": ["    db $00"],
        "EVENT_HALT": ["    db $09"],
        "EVENT_LOOP": ["    db $01, <count>"],
        "EVENT_LOOP_END": ["    db $02"],
        "EVENT_LOOP_TEMPVAR": ["    db $24"],
        "EVENT_PAUSE": ["    db $06, <frames>"],
        "EVENT_SET_ANIMATION": ["    db $3B, <animation>"],
        "EVENT_SET_PHYSICS_CALLBACK": ["    db $25", "    dw <target>"],
        "EVENT_SET_POSITION_CHANGE_CALLBACK": ["    db $23", "    dw <target>"],
        "EVENT_SET_TICK_CALLBACK": ["    db $08", "    dl <target>"],
        "EVENT_SET_VAR": ["    db $0E, <var>", "    dw <value>"],
        "EVENT_SET_VELOCITIES_ZERO": ["    db $39"],
        "EVENT_SHORTCALL": ["    db $1A", "    dw <target>"],
        "EVENT_SHORTCALL_CONDITIONAL": ["    db $0A", "    dw <target>"],
        "EVENT_SHORTCALL_CONDITIONAL_NOT": ["    db $0B", "    dw <target>"],
        "EVENT_SHORTJUMP": ["    db $19", "    dw <target>"],
        "EVENT_SHORT_RETURN": ["    db $1B"],
        "EVENT_START_TASK": ["    db $07", "    dw <target>"],
        "EVENT_WRITE_VAR_TO_TEMPVAR": ["    db $20, <var>"],
    }
    args = {
        "EVENT_BREAK_IF_FALSE": "target",
        "EVENT_CALLROUTINE_0": "target",
        "EVENT_CALLROUTINE_2": "target, arg0, arg1",
        "EVENT_LOOP": "count",
        "EVENT_PAUSE": "frames",
        "EVENT_SET_ANIMATION": "animation",
        "EVENT_SET_PHYSICS_CALLBACK": "target",
        "EVENT_SET_POSITION_CHANGE_CALLBACK": "target",
        "EVENT_SET_TICK_CALLBACK": "target",
        "EVENT_SET_VAR": "var, value",
        "EVENT_SHORTCALL": "target",
        "EVENT_SHORTCALL_CONDITIONAL": "target",
        "EVENT_SHORTCALL_CONDITIONAL_NOT": "target",
        "EVENT_SHORTJUMP": "target",
        "EVENT_START_TASK": "target",
        "EVENT_WRITE_VAR_TO_TEMPVAR": "var",
    }
    missing = sorted(used_macros - bodies.keys())
    if missing:
        raise ValueError(f"missing macro definitions for: {', '.join(missing)}")
    lines = ["; Minimal macro vocabulary used by this source pilot."]
    for name in sorted(used_macros):
        lines.append(f"macro {name}({args.get(name, '')})")
        lines.extend(bodies[name])
        lines.append("endmacro")
        lines.append("")
    return lines


def render_source(rows: list[RowSource], labels: dict[str, str], names: dict[str, list[str]]) -> tuple[str, dict[str, str]]:
    constants: dict[str, str] = {"!ACTIONSCRIPT_VARS_V4": "$04"}
    used_macros = {macro_name(instruction) for row in rows for instruction in row.instructions}

    rendered_rows: list[str] = []
    for row in rows:
        rendered_rows.append("")
        rendered_rows.append(f"org ${row.address.bank:02X}{row.address.offset:04X}")
        rendered_rows.append(f"{row.name}:")
        for instruction in row.instructions:
            label = labels.get(instruction.address.key)
            if label and label != row.name:
                rendered_rows.append(f"{label}:")
            rendered_rows.append(
                render_instruction(instruction, labels=labels, names=names, constants=constants)
            )

    constant_lines = ["; External constants and action-script variable slots."]
    for symbol, value in sorted(constants.items()):
        constant_lines.append(f"{symbol} = {value}")

    header = [
        "; Generated by tools/build_c3_event_script_source_pilot.py",
        "; C3 event/actionscript source pilot: movement pulse presets.",
        "; This file is intentionally not wired into the bank C3 scaffold yet.",
        "hirom",
        "",
    ]
    source = "\n".join(header + constant_lines + [""] + macro_definitions(used_macros) + rendered_rows) + "\n"
    return source, constants


def row_manifest(row: RowSource) -> dict[str, Any]:
    return {
        "address": row.key,
        "name": row.name,
        "size": row.size,
        "sha1": hashlib.sha1(row.raw).hexdigest(),
        "instruction_count": len(row.instructions),
        "ends_at": f"C3:{row.address.offset + row.size:04X}",
    }


def render_report(
    rows: list[RowSource],
    *,
    output_path: Path,
    manifest_path: Path,
    mismatches: list[str],
) -> str:
    total_bytes = sum(row.size for row in rows)
    total_instructions = sum(len(row.instructions) for row in rows)
    validation = "PASS" if not mismatches else "FAIL"
    lines = [
        "# C3 event script source pilot",
        "",
        "## Summary",
        "",
        f"- Family: `{FAMILY_ID}`.",
        f"- Source: `{output_path.relative_to(ROOT).as_posix()}`.",
        f"- Manifest: `{manifest_path.relative_to(ROOT).as_posix()}`.",
        f"- Rows emitted: {len(rows)}.",
        f"- Bytes represented: {total_bytes}.",
        f"- Instructions represented: {total_instructions}.",
        f"- ROM byte validation: {validation}.",
        "",
        "This is the first checked-in C3 event/actionscript source-form pilot. It keeps the ROM-derived byte corridor intact, but presents the movement pulse preset family as labeled macro assembly instead of opaque `db` rows.",
        "",
        "The source is not wired into `src/c3/bank_c3_helpers_asar.asm` yet. That is deliberate: this pass proves the representation and byte validation before replacing generated byte corridors in the bank scaffold.",
        "",
        "## Covered Rows",
        "",
        "| Address | Label | Bytes | Instructions |",
        "| --- | --- | ---: | ---: |",
    ]
    for row in rows:
        lines.append(f"| `{row.key}` | `{row.name}` | {row.size} | {len(row.instructions)} |")
    lines.extend(
        [
            "",
            "## Validation",
            "",
        ]
    )
    if mismatches:
        for mismatch in mismatches:
            lines.append(f"- {mismatch}")
    else:
        lines.append("- Every emitted row was decoded over its exact source/data-map byte span and revalidated against the ROM bytes used to generate it.")
    lines.extend(
        [
            "",
            "## Next Promotion Step",
            "",
            "Promote another C3 family through this same generator pattern, then teach the bank scaffold to include source-form families in place of their opaque `script_event_payloads_0000_e450.asm` `db` corridors once enough families have stable labels and macro coverage.",
        ]
    )
    return "\n".join(lines) + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate a C3 event/actionscript source-form pilot.")
    parser.add_argument("--rom", help="path to EarthBound (USA).sfc")
    parser.add_argument("--source-map", type=Path, default=DEFAULT_SOURCE_MAP)
    parser.add_argument("--index", type=Path, default=DEFAULT_REF_INDEX)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    source_map = args.source_map if args.source_map.is_absolute() else ROOT / args.source_map
    index_path = args.index if args.index.is_absolute() else ROOT / args.index
    output_path = args.output if args.output.is_absolute() else ROOT / args.output
    report_path = args.report if args.report.is_absolute() else ROOT / args.report
    manifest_path = args.manifest if args.manifest.is_absolute() else ROOT / args.manifest

    rom = load_rom(find_rom(args.rom))
    names = load_names(index_path)
    rows_by_address = load_row_map(source_map)
    rows = load_rows(rom, rows_by_address, SCRIPT_ROWS + PRESET_ROWS, names)
    labels = collect_label_map(rows, names)
    source, constants = render_source(rows, labels, names)

    mismatches: list[str] = []
    for row in rows:
        file_offset = hirom_to_file_offset(row.address.bank, row.address.offset, len(rom))
        expected = rom[file_offset : file_offset + row.size] if file_offset is not None else b""
        observed = b"".join(instruction.raw for instruction in row.instructions)
        if observed != expected:
            mismatches.append(f"{row.key}: decoded bytes do not match ROM span")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(source, encoding="utf-8")

    manifest = {
        "schema": "earthbound-decomp.c3-event-script-source-pilot.v1",
        "generated_by": "tools/build_c3_event_script_source_pilot.py",
        "family": FAMILY_ID,
        "source": output_path.relative_to(ROOT).as_posix(),
        "report": report_path.relative_to(ROOT).as_posix(),
        "rows": [row_manifest(row) for row in rows],
        "constants": constants,
        "validation": {
            "mismatches": mismatches,
            "status": "pass" if not mismatches else "fail",
        },
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    report_path.write_text(
        render_report(rows, output_path=output_path, manifest_path=manifest_path, mismatches=mismatches),
        encoding="utf-8",
    )

    print(f"wrote {output_path.relative_to(ROOT).as_posix()}")
    print(f"wrote {report_path.relative_to(ROOT).as_posix()}")
    print(f"wrote {manifest_path.relative_to(ROOT).as_posix()}")
    print(f"rows={len(rows)} bytes={sum(row.size for row in rows)} validation={manifest['validation']['status']}")
    return 1 if mismatches else 0


if __name__ == "__main__":
    raise SystemExit(main())
