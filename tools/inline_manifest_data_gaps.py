from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from add_source_bank_range import ROOT, recalculate_summary
from rom_tools import find_rom, hirom_to_file_offset, load_rom


def parse_bank_address(raw: str) -> tuple[int, int]:
    bank, address = raw.split(":", 1)
    return int(bank, 16), int(address, 16)


def default_manifest(bank: str) -> Path:
    return ROOT / "build" / f"{bank.lower()}-build-candidate-ranges.json"


def resolve(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def address_label_prefix(address: str) -> str:
    bank, offset = parse_bank_address(address)
    if offset > 0xFFFF:
        return ""
    return f"{bank:02X}{offset:04X}_"


def find_label_index(lines: list[str], address: str) -> int | None:
    prefix = address_label_prefix(address)
    if not prefix:
        return None
    pattern = re.compile(rf"^{re.escape(prefix)}[A-Za-z0-9_]+:")
    for index, line in enumerate(lines):
        if pattern.match(line.strip()):
            return index
    return None


def next_label_index(lines: list[str], start_index: int) -> int | None:
    pattern = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*:")
    for index in range(start_index + 1, len(lines)):
        if pattern.match(lines[index].strip()):
            return index
    return None


def has_data_directive_between(lines: list[str], start_index: int, end_index: int | None) -> bool:
    limit = end_index if end_index is not None else len(lines)
    pattern = re.compile(r"^\s*(db|dw|dl|dd|incbin)\b", re.IGNORECASE)
    return any(pattern.match(line) for line in lines[start_index + 1 : limit])


def bytes_for_range(rom: bytes, start: str, end: str) -> bytes:
    start_bank, start_address = parse_bank_address(start)
    end_bank, end_address = parse_bank_address(end)
    if start_bank != end_bank:
        raise SystemExit(f"range crosses banks: {start}..{end}")
    start_offset = hirom_to_file_offset(start_bank, start_address, len(rom))
    end_offset = hirom_to_file_offset(end_bank, end_address, len(rom))
    if start_offset is None or end_offset is None:
        raise SystemExit(f"could not convert {start}..{end} to ROM offsets")
    return rom[start_offset:end_offset]


def render_db(data: bytes) -> list[str]:
    lines: list[str] = []
    for index in range(0, len(data), 16):
        chunk = data[index : index + 16]
        lines.append("    db " + ",".join(f"${byte:02X}" for byte in chunk))
    return lines


def render_gap_block(gap: dict[str, Any], rom: bytes) -> list[str]:
    start = str(gap["start"])
    end = str(gap["end"])
    name = str(gap.get("name") or "DataGap")
    bank, start_address = parse_bank_address(start)
    data = bytes_for_range(rom, start, end)
    lines = [
        "",
        "; ---------------------------------------------------------------------------",
        f"; {start}",
        "",
        f"{bank:02X}{start_address:04X}_{name}:",
        f"    ; data bytes: {start}..{end}",
    ]
    lines.extend(render_db(data))
    return lines


def inline_gap(source_path: Path, gap: dict[str, Any], rom: bytes) -> bool:
    lines = source_path.read_text(encoding="utf-8").splitlines()
    start_label_index = find_label_index(lines, str(gap["start"]))
    if start_label_index is not None:
        next_index = next_label_index(lines, start_label_index)
        if has_data_directive_between(lines, start_label_index, next_index):
            return False
        data = bytes_for_range(rom, str(gap["start"]), str(gap["end"]))
        insert_lines = [f"    ; data bytes: {gap['start']}..{gap['end']}"]
        insert_lines.extend(render_db(data))
        insert_lines.append("")
        lines[start_label_index + 1 : start_label_index + 1] = insert_lines
        source_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8", newline="\n")
        return True

    insert_at = find_label_index(lines, str(gap["end"]))
    block = render_gap_block(gap, rom)
    if insert_at is None:
        lines.extend(block)
    else:
        lines[insert_at:insert_at] = block + [""]
    source_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8", newline="\n")
    return True


def source_segment_from_gap(gap: dict[str, Any]) -> dict[str, Any]:
    segment = dict(gap)
    segment["kind"] = "source"
    return segment


def part_sort_key(part: dict[str, Any]) -> tuple[int, int]:
    return parse_bank_address(str(part["start"]))


def module_matches(module: dict[str, Any], module_filter: str) -> bool:
    if module_filter.lower() == "all":
        return True
    haystack = f"{module.get('source_path', '')} {module.get('subsystem', '')} {module.get('start', '')} {module.get('end', '')}"
    return module_filter.lower() in haystack.lower()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Inline manifest data gaps into source files and mark them as source segments."
    )
    parser.add_argument("--bank", required=True)
    parser.add_argument("--module", default="all")
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--rom")
    parser.add_argument("--dry-run", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    bank = args.bank.upper()
    manifest_path = resolve(args.manifest) if args.manifest else default_manifest(bank)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    rom = load_rom(find_rom(args.rom))

    changed_sources = 0
    converted_gaps = 0
    for module in manifest.get("ranges", []):
        if not module_matches(module, args.module):
            continue
        gaps = list(module.get("data_gaps", []))
        if not gaps:
            continue
        source_path = resolve(Path(str(module["source_path"])))
        for gap in sorted(gaps, key=part_sort_key):
            if not args.dry_run and inline_gap(source_path, gap, rom):
                changed_sources += 1
            converted_gaps += 1
        if not args.dry_run:
            module["source_segments"] = sorted(
                list(module.get("source_segments", []))
                + [source_segment_from_gap(gap) for gap in gaps],
                key=part_sort_key,
            )
            module["data_gaps"] = []
            module["source_size"] = int(module["size"])
            module["data_gap_size"] = 0

    if not args.dry_run:
        recalculate_summary(manifest)
        manifest_path.write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
            newline="\n",
        )

    print(
        f"{'Would convert' if args.dry_run else 'Converted'} {converted_gaps} gap(s); "
        f"{changed_sources} source insertion(s)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
