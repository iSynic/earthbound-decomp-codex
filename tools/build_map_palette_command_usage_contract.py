from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import disasm_ebtext_script as ebscript
import find_ebtext_command as findcmd
import rom_tools


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_YML = ROOT / "refs" / "ebsrc-main" / "ebsrc-main" / "earthbound.yml"
DEFAULT_PALETTE_CONTRACT = ROOT / "notes" / "map-fts-palette-variant-contract.json"
DEFAULT_JSON_OUT = ROOT / "notes" / "map-palette-command-usage-contract.json"
DEFAULT_MARKDOWN_OUT = ROOT / "notes" / "map-palette-command-usage-contract.md"
SCHEMA = "earthbound-decomp.map-palette-command-usage-contract.v1"
CHANGE_MAP_PALETTE_OPCODE = 0x1F
CHANGE_MAP_PALETTE_SUBOPCODE = 0xE1
CHANGE_MAP_PALETTE_COMMAND_SIZE = 5


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Join parsed EBText CHANGE_MAP_PALETTE commands to resolved map "
            "palette variant rows."
        )
    )
    parser.add_argument("--rom", help="EarthBound US ROM path.")
    parser.add_argument("--yml", default=str(DEFAULT_YML))
    parser.add_argument("--palette-contract", default=str(DEFAULT_PALETTE_CONTRACT))
    parser.add_argument("--json-out", default=str(DEFAULT_JSON_OUT))
    parser.add_argument("--markdown-out", default=str(DEFAULT_MARKDOWN_OUT))
    return parser.parse_args()


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_command_args(rom_data: bytes, address: int) -> dict[str, int | str]:
    bank = (address >> 16) & 0xFF
    cpu_offset = address & 0xFFFF
    file_offset = rom_tools.hirom_to_file_offset(bank, cpu_offset, len(rom_data))
    if file_offset is None:
        raise ValueError(f"{ebscript.fmt_addr(address)} does not map to ROM data")
    command = rom_data[file_offset : file_offset + CHANGE_MAP_PALETTE_COMMAND_SIZE]
    if len(command) != CHANGE_MAP_PALETTE_COMMAND_SIZE:
        raise ValueError(f"ROM ended in CHANGE_MAP_PALETTE at {ebscript.fmt_addr(address)}")
    if command[0] != CHANGE_MAP_PALETTE_OPCODE or command[1] != CHANGE_MAP_PALETTE_SUBOPCODE:
        raise ValueError(f"Parsed hit at {ebscript.fmt_addr(address)} is not command 1F E1")
    palette_word = command[2] | (command[3] << 8)
    return {
        "file_offset": file_offset,
        "palette_word": palette_word,
        "palette_id": palette_word & 0xFF,
        "variant": (palette_word >> 8) & 0xFF,
        "duration_frames": command[4],
    }


def palette_entries_by_key(contract: dict[str, Any]) -> dict[tuple[int, int], dict[str, Any]]:
    entries: dict[tuple[int, int], dict[str, Any]] = {}
    for entry in contract["entries"]:
        entries[(int(entry["tileset_id"]), int(entry["variant"]))] = entry
    return entries


def build_contract(args: argparse.Namespace) -> dict[str, Any]:
    rom_path = rom_tools.find_rom(args.rom)
    rom_data = rom_tools.load_rom(rom_path)
    yml_path = Path(args.yml)
    palette_contract_path = Path(args.palette_contract)
    palette_contract = load_json(palette_contract_path)
    palette_entries = palette_entries_by_key(palette_contract)
    segments = findcmd.load_segments(yml_path)
    hits = findcmd.find_hits(
        rom_data,
        segments,
        CHANGE_MAP_PALETTE_OPCODE,
        CHANGE_MAP_PALETTE_SUBOPCODE,
    )

    entries: list[dict[str, Any]] = []
    for segment_name, address, text in hits:
        args_for_hit = read_command_args(rom_data, address)
        key = (int(args_for_hit["palette_id"]), int(args_for_hit["variant"]))
        palette_entry = palette_entries.get(key)
        command_entry: dict[str, Any] = {
            "address": ebscript.fmt_addr(address),
            "file_offset": f"0x{int(args_for_hit['file_offset']):06X}",
            "segment": segment_name,
            "command_text": text,
            "palette_word": f"0x{int(args_for_hit['palette_word']):04X}",
            "palette_id": int(args_for_hit["palette_id"]),
            "variant": int(args_for_hit["variant"]),
            "duration_frames": int(args_for_hit["duration_frames"]),
            "argument_model": "palette_word = (variant << 8) | palette_id",
            "palette_variant_match": palette_entry is not None,
        }
        if palette_entry is not None:
            command_entry.update(
                {
                    "row_id": palette_entry["row_id"],
                    "palette_contract_status": palette_entry["status"],
                    "palette_asset": palette_entry["asset"],
                    "setting_summary": palette_entry["setting_summary"],
                    "tileset_dependency": palette_entry["tileset_dependency"],
                }
            )
        entries.append(command_entry)

    by_palette: dict[tuple[int, int], list[dict[str, Any]]] = defaultdict(list)
    for entry in entries:
        by_palette[(int(entry["palette_id"]), int(entry["variant"]))].append(entry)

    usage_by_palette_variant: list[dict[str, Any]] = []
    for (palette_id, variant), rows in sorted(by_palette.items()):
        durations = Counter(int(row["duration_frames"]) for row in rows)
        segments_counter = Counter(str(row["segment"]) for row in rows)
        first = rows[0]
        usage_by_palette_variant.append(
            {
                "palette_id": palette_id,
                "variant": variant,
                "palette_word": f"0x{((variant << 8) | palette_id):04X}",
                "row_id": first.get("row_id"),
                "hit_count": len(rows),
                "duration_frames": [
                    {"duration": duration, "count": count}
                    for duration, count in sorted(durations.items())
                ],
                "segments": [
                    {"segment": segment, "count": count}
                    for segment, count in sorted(segments_counter.items())
                ],
                "palette_variant_match": all(bool(row["palette_variant_match"]) for row in rows),
                "palette_contract_status": first.get("palette_contract_status"),
                "setting_summary": first.get("setting_summary"),
                "sample_addresses": [row["address"] for row in rows[:6]],
            }
        )

    segment_counts = Counter(str(entry["segment"]) for entry in entries)
    duration_counts = Counter(int(entry["duration_frames"]) for entry in entries)
    status_counts = Counter(str(entry.get("palette_contract_status", "missing")) for entry in entries)
    return {
        "schema": SCHEMA,
        "title": "Map Palette Command Usage Contract",
        "generator": "tools/build_map_palette_command_usage_contract.py",
        "source_policy": (
            "ROM-parsed text-command usage contract. This records command "
            "addresses, decoded arguments, segment names, and joined palette "
            "contract IDs; it does not commit text payload bytes or palette data."
        ),
        "sources": {
            "text_segment_yml": rel(yml_path),
            "palette_variant_contract": rel(palette_contract_path),
            "text_macro_ref": "refs/ebsrc-main/ebsrc-main/include/textmacros.asm",
        },
        "command": {
            "name": "CHANGE_MAP_PALETTE",
            "opcode": f"0x{CHANGE_MAP_PALETTE_OPCODE:02X}",
            "subopcode": f"0x{CHANGE_MAP_PALETTE_SUBOPCODE:02X}",
            "size_bytes": CHANGE_MAP_PALETTE_COMMAND_SIZE,
            "argument_model": {
                "word_argument": "palette_word = (variant << 8) | palette_id",
                "byte_argument": "duration_frames",
            },
        },
        "summary": {
            "hit_count": len(entries),
            "unique_palette_variant_count": len(usage_by_palette_variant),
            "palette_variant_matches": sum(1 for entry in entries if entry["palette_variant_match"]),
            "missing_palette_variant_matches": sum(
                1 for entry in entries if not entry["palette_variant_match"]
            ),
            "duration_frame_values": [
                {"duration": duration, "count": count}
                for duration, count in sorted(duration_counts.items())
            ],
            "segment_counts": [
                {"segment": segment, "count": count}
                for segment, count in sorted(segment_counts.items(), key=lambda item: (-item[1], item[0]))
            ],
            "palette_contract_status_counts": [
                {"status": status, "count": count}
                for status, count in sorted(status_counts.items())
            ],
        },
        "usage_by_palette_variant": usage_by_palette_variant,
        "entries": entries,
    }


def write_markdown(contract: dict[str, Any], path: Path) -> None:
    summary = contract["summary"]
    duration_text = ", ".join(
        f"`{item['duration']}`:{item['count']}" for item in summary["duration_frame_values"]
    )
    segment_text = ", ".join(
        f"`{item['segment']}`:{item['count']}" for item in summary["segment_counts"]
    )
    status_text = ", ".join(
        f"`{item['status']}`:{item['count']}" for item in summary["palette_contract_status_counts"]
    )
    lines = [
        "# Map Palette Command Usage Contract",
        "",
        "This contract joins parsed EBText `CHANGE_MAP_PALETTE` commands to the",
        "resolved `.fts`/DA map palette variant contract.",
        "",
        "## Summary",
        "",
        f"- parsed `CHANGE_MAP_PALETTE` hits: `{summary['hit_count']}`",
        f"- unique palette variants referenced: `{summary['unique_palette_variant_count']}`",
        f"- palette contract matches: `{summary['palette_variant_matches']}`",
        f"- missing palette contract matches: `{summary['missing_palette_variant_matches']}`",
        f"- duration frame values: {duration_text}",
        f"- text segments: {segment_text}",
        f"- palette row status counts: {status_text}",
        "",
        "## Argument Model",
        "",
        "The command macro is `1F E1 word byte`. Every parsed hit supports this",
        "model:",
        "",
        "- `word = (variant << 8) | palette_id`",
        "- `byte = duration_frames`",
        "",
        "The low byte of the word selects the DA `MAP_DATA_PALETTE_N` asset and",
        "the high byte selects that asset's 192-byte variant. This links script",
        "palette changes directly to the visual palette rows decoded in",
        "`notes/map-fts-palette-variant-contract.md`.",
        "",
        "## Usage By Palette Variant",
        "",
        "| Palette ID | Variant | Word | Row ID | Hits | Durations | Segments | Palette Row Status | Setting |",
        "| ---: | ---: | --- | --- | ---: | --- | --- | --- | --- |",
    ]
    for row in contract["usage_by_palette_variant"]:
        durations = ", ".join(
            f"`{item['duration']}`:{item['count']}" for item in row["duration_frames"]
        )
        segments = ", ".join(
            f"`{item['segment']}`:{item['count']}" for item in row["segments"]
        )
        setting = row.get("setting_summary") or {}
        setting_text = (
            f"event_flag `{setting.get('event_flag')}`, "
            f"sprite `{setting.get('sprite_palette')}`, "
            f"flash `{setting.get('flash_effect')}`, "
            f"event-palette `{setting.get('has_event_palette')}`"
        )
        lines.append(
            f"| {row['palette_id']} | {row['variant']} | `{row['palette_word']}` | "
            f"`{row.get('row_id')}` | {row['hit_count']} | {durations} | "
            f"{segments} | `{row.get('palette_contract_status')}` | {setting_text} |"
        )
    lines.extend(
        [
            "",
            "## Parsed Hits",
            "",
            "| Address | Segment | Word | Palette ID | Variant | Duration | Row ID |",
            "| --- | --- | --- | ---: | ---: | ---: | --- |",
        ]
    )
    for entry in contract["entries"]:
        lines.append(
            f"| `{entry['address']}` | `{entry['segment']}` | `{entry['palette_word']}` | "
            f"{entry['palette_id']} | {entry['variant']} | {entry['duration_frames']} | "
            f"`{entry.get('row_id')}` |"
        )
    lines.extend(
        [
            "",
            "## Machine-Readable Data",
            "",
            "`notes/map-palette-command-usage-contract.json` records one row per",
            "parsed command hit and one grouped row per referenced palette variant.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    contract = build_contract(args)
    json_path = Path(args.json_out)
    markdown_path = Path(args.markdown_out)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(contract, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_markdown(contract, markdown_path)
    print(f"Wrote {rel(json_path)} and {rel(markdown_path)}")


if __name__ == "__main__":
    main()
