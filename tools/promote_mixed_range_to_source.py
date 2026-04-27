from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from add_source_bank_range import recalculate_summary
from emit_linear_source_module import (
    BASE_SYMBOLS,
    Instruction,
    collect_instructions,
    parse_address_list,
    parse_label_list,
    parse_symbol_list,
    render_module,
)
from decode_snippet import parse_cpu_address
from rom_tools import find_rom, hirom_to_file_offset, load_rom


ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Part:
    kind: str
    start: str
    end: str
    name: str


def default_manifest(bank: str) -> Path:
    return ROOT / "build" / f"{bank.lower()}-build-candidate-ranges.json"


def resolve(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def title_from_name(name: str) -> str:
    return name.replace("_", " ")


def module_name(module: dict[str, Any]) -> str:
    if module.get("source_segments"):
        return str(module["source_segments"][0].get("name") or Path(module["source_path"]).stem)
    if module.get("data_gaps"):
        return str(module["data_gaps"][0].get("name") or Path(module["source_path"]).stem)
    labels = module.get("labels", [])
    if labels:
        return labels[0].split(" ", 1)[-1].strip().replace(" ", "_")
    return Path(module["source_path"]).stem


def find_module(manifest: dict[str, Any], module_filter: str) -> dict[str, Any]:
    matches = [
        item
        for item in manifest.get("ranges", [])
        if module_filter.lower()
        in f"{item.get('source_path', '')} {item.get('start', '')} {item.get('end', '')} {' '.join(item.get('labels', []))}".lower()
    ]
    if not matches:
        raise SystemExit(f"No range matched {module_filter!r}")
    if len(matches) > 1:
        choices = ", ".join(f"{item['start']} {item['source_path']}" for item in matches[:12])
        raise SystemExit(f"Ambiguous range filter {module_filter!r}; matched {choices}")
    return matches[0]


def parse_part(raw: str, kind: str) -> Part:
    pieces = [piece.strip() for piece in raw.split(",", 2)]
    if len(pieces) not in {2, 3} or not pieces[0] or not pieces[1]:
        raise SystemExit(f"--{kind} must look like START,END[,Name], got {raw!r}")
    name = pieces[2] if len(pieces) == 3 and pieces[2] else f"{kind}_{pieces[0].replace(':', '_')}"
    return Part(kind=kind, start=pieces[0].upper(), end=pieces[1].upper(), name=name)


def parse_bank_address(raw: str) -> tuple[int, int]:
    return parse_cpu_address(raw)


def address_key(raw: str) -> int:
    bank, address = parse_bank_address(raw)
    return (bank << 16) | address


def validate_parts(module: dict[str, Any], parts: list[Part]) -> None:
    if not parts:
        raise SystemExit("At least one --code or --data part is required")
    parts.sort(key=lambda part: address_key(part.start))
    expected = module["start"].upper()
    for part in parts:
        if part.start != expected:
            raise SystemExit(f"Parts must exactly cover the module; expected {expected}, got {part.start}")
        start_bank, start_address = parse_bank_address(part.start)
        end_bank, end_address = parse_bank_address(part.end)
        if start_bank != end_bank:
            raise SystemExit(f"Part crosses banks: {part.start}..{part.end}")
        if end_address <= start_address:
            raise SystemExit(f"Part end must be after start: {part.start}..{part.end}")
        expected = part.end
    if expected != module["end"].upper():
        raise SystemExit(f"Parts must end at {module['end']}, got {expected}")


def bytes_for_range(rom: bytes, start: str, end: str) -> bytes:
    start_bank, start_address = parse_bank_address(start)
    end_bank, end_address = parse_bank_address(end)
    start_offset = hirom_to_file_offset(start_bank, start_address, len(rom))
    end_offset = hirom_to_file_offset(end_bank, end_address, len(rom))
    if start_offset is None or end_offset is None:
        raise SystemExit(f"Could not convert {start}..{end} to ROM offsets")
    return rom[start_offset:end_offset]


def render_db(data: bytes) -> list[str]:
    lines: list[str] = []
    for index in range(0, len(data), 16):
        chunk = data[index : index + 16]
        lines.append("    db " + ",".join(f"${byte:02X}" for byte in chunk))
    return lines


def render_data_part(bank: int, part: Part, rom: bytes) -> str:
    _start_bank, start = parse_bank_address(part.start)
    _end_bank, end = parse_bank_address(part.end)
    data = bytes_for_range(rom, part.start, part.end)
    lines = [
        f"; ---------------------------------------------------------------------------",
        f"; {part.start}",
        "",
        f"{bank:02X}{start:04X}_{part.name}:",
        f"    ; data bytes: {part.start}..{part.end}",
    ]
    lines.extend(render_db(data))
    lines.extend(["", f"; {part.end}", f"{bank:02X}{end:04X}_{part.name}_End:"])
    return "\n".join(lines)


def render_code_part(
    bank: int,
    part: Part,
    rom: bytes,
    *,
    force_m16_at: set[tuple[int, int]],
    force_m8_at: set[tuple[int, int]],
    force_x16_at: set[tuple[int, int]],
    force_x8_at: set[tuple[int, int]],
    symbols: dict[str, str],
    entry_labels: dict[int, str],
) -> tuple[str, int]:
    _start_bank, start = parse_bank_address(part.start)
    _end_bank, end = parse_bank_address(part.end)
    instructions = collect_instructions(
        rom,
        bank,
        start,
        end,
        force_m16_at=force_m16_at,
        force_m8_at=force_m8_at,
        force_x16_at=force_x16_at,
        force_x8_at=force_x8_at,
    )
    text = render_module(
        bank,
        start,
        end,
        part.name,
        instructions,
        title=title_from_name(part.name),
        symbols=symbols,
        entry_labels=entry_labels,
    )
    body = text.split("; ---------------------------------------------------------------------------\n", 2)[-1]
    return "; ---------------------------------------------------------------------------\n" + body.rstrip(), len(instructions)


def render_mixed_module(
    bank: int,
    module: dict[str, Any],
    name: str,
    title: str,
    parts: list[Part],
    rom: bytes,
    *,
    force_m16_at: set[tuple[int, int]],
    force_m8_at: set[tuple[int, int]],
    force_x16_at: set[tuple[int, int]],
    force_x8_at: set[tuple[int, int]],
    symbols: dict[str, str],
    entry_labels: dict[int, str],
) -> tuple[str, int]:
    lines = [
        f"; EarthBound {bank:02X} {title}.",
        ";",
        "; Source-emission status:",
        "; - Prototype level: build-candidate mixed source/data unit.",
        "; - Generated by tools/promote_mixed_range_to_source.py from explicit",
        ";   code and data spans, then intended for byte-equivalence validation.",
        ";",
        "; Source units covered:",
        f"; - {module['start']}..{module['end']} {name}",
        "",
        "; ---------------------------------------------------------------------------",
        "; External contracts used by this module",
        "",
    ]
    external_symbols = dict(BASE_SYMBOLS)
    external_symbols.update(symbols)
    width = max(len(symbol_name) for symbol_name in external_symbols.values())
    for raw, symbol_name in sorted(external_symbols.items(), key=lambda item: int(item[0][1:], 16)):
        lines.append(f"{symbol_name:<{width}} = {raw}")
    lines.append("")
    instruction_count = 0
    for part in parts:
        if part.kind == "code":
            rendered, count = render_code_part(
                bank,
                part,
                rom,
                force_m16_at=force_m16_at,
                force_m8_at=force_m8_at,
                force_x16_at=force_x16_at,
                force_x8_at=force_x8_at,
                symbols=symbols,
                entry_labels=entry_labels,
            )
            instruction_count += count
            lines.append(rendered)
        else:
            lines.append(render_data_part(bank, part, rom))
        lines.append("")
    return "\n".join(lines).rstrip() + "\n", instruction_count


def full_source_segment(module: dict[str, Any]) -> dict[str, Any]:
    segment = {
        key: module[key]
        for key in (
            "start",
            "end",
            "size",
            "file_offset_start",
            "file_offset_end",
            "sha1",
            "first_bytes",
            "last_bytes",
            "labels",
            "evidence",
        )
        if key in module
    }
    segment["kind"] = "source"
    segment["name"] = module_name(module)
    return segment


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Promote one manifest range to explicit mixed code/data source."
    )
    parser.add_argument("--bank", required=True)
    parser.add_argument("--module", required=True)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--rom")
    parser.add_argument("--subsystem", default="mixed-decoded-source")
    parser.add_argument("--title")
    parser.add_argument("--code", action="append", default=[], help="START,END[,Name]")
    parser.add_argument("--data", action="append", default=[], help="START,END[,Name]")
    parser.add_argument("--force-m16-at", action="append", default=[])
    parser.add_argument("--force-m8-at", action="append", default=[])
    parser.add_argument("--force-x16-at", action="append", default=[])
    parser.add_argument("--force-x8-at", action="append", default=[])
    parser.add_argument("--symbol", action="append", default=[], help="additional symbol mapping, NAME=$ADDR")
    parser.add_argument("--label", action="append", default=[], help="semantic label mapping, C0:1234=Name")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    bank = args.bank.upper()
    bank_int = int(bank, 16)
    manifest_path = resolve(args.manifest) if args.manifest else default_manifest(bank)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    module = find_module(manifest, args.module)
    start_bank, _start = parse_bank_address(module["start"])
    end_bank, _end = parse_bank_address(module["end"])
    if start_bank != end_bank or start_bank != bank_int:
        raise SystemExit(f"Module range {module['start']}..{module['end']} is not in bank {bank}")

    parts = [parse_part(raw, "code") for raw in args.code]
    parts.extend(parse_part(raw, "data") for raw in args.data)
    validate_parts(module, parts)

    rom = load_rom(find_rom(args.rom))
    name = module_name(module)
    output = resolve(Path(module["source_path"]))
    text, instruction_count = render_mixed_module(
        bank_int,
        module,
        name,
        args.title or title_from_name(name),
        parts,
        rom,
        force_m16_at=parse_address_list(args.force_m16_at),
        force_m8_at=parse_address_list(args.force_m8_at),
        force_x16_at=parse_address_list(args.force_x16_at),
        force_x8_at=parse_address_list(args.force_x8_at),
        symbols=parse_symbol_list(args.symbol),
        entry_labels=parse_label_list(args.label),
    )
    output.write_text(text, encoding="utf-8", newline="\n")

    module["subsystem"] = args.subsystem
    module["source_size"] = int(module["size"])
    module["data_gap_size"] = 0
    module["source_segments"] = [full_source_segment(module)]
    module["data_gaps"] = []
    recalculate_summary(manifest)
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(
        f"Promoted {module['start']}..{module['end']} -> {output.relative_to(ROOT).as_posix()} "
        f"with {instruction_count} instruction(s) and {len([part for part in parts if part.kind == 'data'])} data part(s)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
