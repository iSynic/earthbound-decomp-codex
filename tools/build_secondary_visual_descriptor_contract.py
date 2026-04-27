from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import rom_tools


SCHEMA = "earthbound-decomp.secondary-visual-descriptor-contract.v1"
DEFAULT_JSON_OUT = ROOT / "notes" / "secondary-visual-descriptor-contracts.json"
DEFAULT_MARKDOWN_OUT = ROOT / "notes" / "secondary-visual-descriptor-contracts.md"
POINTER_TABLE_BANK = 0xC4
POINTER_TABLE_START = 0x2B0D
POINTER_TABLE_END = 0x2B51
DESCRIPTOR_RECORD_END = 0x2F45
SET_PARTY_TICK_CALLBACKS_START = 0x2F45
SET_PARTY_TICK_CALLBACKS_END = 0x2F65
MAP_TILE_TABLE_CHUNKS_TABLE_START = 0x2F65
MAP_TILE_TABLE_CHUNKS_TABLE_END = 0x2F8C
TILE_BASE_TABLE_START = 0x2F8C
TILE_BASE_TABLE_END = 0x303C
TILE_WORD_TABLE_START = 0x303C
TILE_WORD_TABLE_END = 0x30CC
DESCRIPTOR_NAMES = {
    0x2B51: "SecondaryVisualDescriptor1Piece",
    0x2B5D: "SecondaryVisualDescriptor2PieceNarrow",
    0x2B73: "SecondaryVisualDescriptor2PieceWide",
    0x2B89: "SecondaryVisualDescriptor3PieceColumn",
    0x2BA9: "SecondaryVisualDescriptor2PieceBandSplit",
    0x2BBF: "SecondaryVisualDescriptor4Piece2x2",
    0x2BE9: "SecondaryVisualDescriptor2PieceBandSplitAlt",
    0x2BFF: "SecondaryVisualDescriptor4Piece2x2Wide",
    0x2C29: "SecondaryVisualDescriptor6Piece3x2",
    0x2C67: "SecondaryVisualDescriptor6Piece3x2Tall",
    0x2CA5: "SecondaryVisualDescriptor3Piece1x3",
    0x2CC5: "SecondaryVisualDescriptor6Piece2x3Wide",
    0x2D03: "SecondaryVisualDescriptor9Piece3x3",
    0x2D5F: "SecondaryVisualDescriptor12Piece4x3",
    0x2DD9: "SecondaryVisualDescriptor16Piece4x4",
    0x2E7B: "SecondaryVisualDescriptor20Piece4x5",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Decode the C4 secondary visual descriptor pointer table and records."
    )
    parser.add_argument("--rom", default=None, help="EarthBound US ROM path.")
    parser.add_argument("--json-out", default=str(DEFAULT_JSON_OUT))
    parser.add_argument("--markdown-out", default=str(DEFAULT_MARKDOWN_OUT))
    return parser.parse_args()


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def bank_addr(bank: int, address: int) -> str:
    return f"{bank:02X}:{address:04X}"


def bank_range(bank: int, start: int, end: int) -> str:
    return f"{bank:02X}:{start:04X}..{bank:02X}:{end:04X}"


def slice_rom(rom: bytes, bank: int, start: int, end: int) -> bytes:
    offset = rom_tools.hirom_to_file_offset(bank, start, len(rom))
    if offset is None:
        raise ValueError(f"Address is not ROM mapped: {bank_addr(bank, start)}")
    return rom[offset : offset + (end - start)]


def read_long_pointer_entry(rom: bytes, bank: int, address: int) -> dict[str, Any]:
    offset = rom_tools.hirom_to_file_offset(bank, address, len(rom))
    if offset is None:
        raise ValueError(f"Address is not ROM mapped: {bank_addr(bank, address)}")
    pointer = rom_tools.read_u16_le(rom, offset)
    pointer_bank = rom[offset + 2]
    padding = rom[offset + 3]
    return {
        "table_address": bank_range(bank, address, address + 4),
        "target": bank_addr(pointer_bank, pointer),
        "target_bank": f"{pointer_bank:02X}",
        "target_offset": pointer,
        "padding": f"${padding:02X}",
    }


def decode_piece(raw: bytes, pass_index: int, ordinal: int) -> dict[str, Any]:
    attr = raw[2]
    trailing = raw[4]
    return {
        "pass_index": pass_index,
        "ordinal": ordinal,
        "raw": " ".join(f"{byte:02X}" for byte in raw),
        "relative_y": raw[0],
        "source_tile_low_or_spatial_byte": raw[1],
        "attribute_byte": f"${attr:02X}",
        "relative_x": raw[3],
        "trailing_attribute": f"${trailing:02X}",
        "trailing_attribute_bits": {
            "pass_terminal_piece_marker": bool(trailing & 0x80),
            "unknown_low_bits_raw": trailing & 0x7F,
        },
        "attribute_bits": {
            "vertical_flip": bool(attr & 0x80),
            "horizontal_flip": bool(attr & 0x40),
            "priority_bits_raw": (attr >> 4) & 0x03,
            "tile_high_bit": bool(attr & 0x01),
            "low_attribute_bits_raw": attr & 0x0E,
        },
    }


def decode_descriptor(rom: bytes, address: int) -> dict[str, Any]:
    offset = rom_tools.hirom_to_file_offset(POINTER_TABLE_BANK, address, len(rom))
    if offset is None:
        raise ValueError(f"Address is not ROM mapped: {bank_addr(POINTER_TABLE_BANK, address)}")
    piece_count = rom[offset]
    first_band_count = rom[offset + 1]
    second_band_count = piece_count - first_band_count
    if second_band_count < 0:
        raise ValueError(
            f"Descriptor {bank_addr(POINTER_TABLE_BANK, address)} has invalid band split"
        )

    length = 2 + (piece_count * 2 * 5)
    raw = rom[offset : offset + length]
    pieces = []
    body = raw[2:]
    for pass_index in range(2):
        pass_pieces = []
        for ordinal in range(piece_count):
            start = ((pass_index * piece_count) + ordinal) * 5
            pass_pieces.append(decode_piece(body[start : start + 5], pass_index, ordinal))
        pieces.append(pass_pieces)

    return {
        "address": bank_addr(POINTER_TABLE_BANK, address),
        "label": DESCRIPTOR_NAMES.get(address, f"SecondaryVisualDescriptor{address:04X}"),
        "range": bank_range(POINTER_TABLE_BANK, address, address + length),
        "bytes": length,
        "sha1": hashlib.sha1(raw).hexdigest(),
        "header": {
            "piece_count_per_pass": piece_count,
            "first_priority_band_count": first_band_count,
            "second_priority_band_count": second_band_count,
            "runtime_2be6_packed_counts": f"${first_band_count:02X}{second_band_count:02X}",
            "total_copied_piece_records": piece_count * 2,
        },
        "body_passes": pieces,
    }


def build_contract(rom_path_arg: str | None) -> dict[str, Any]:
    rom_path = rom_tools.find_rom(rom_path_arg)
    rom = rom_tools.load_rom(rom_path)
    rom_info = rom_tools.read_rom_info(rom_path)
    verification_problems = rom_tools.verify_earthbound_us(rom_info)
    if verification_problems:
        raise ValueError(
            "ROM identity verification failed:\n"
            + "\n".join(f"- {problem}" for problem in verification_problems)
        )

    pointer_entries = []
    for address in range(POINTER_TABLE_START, POINTER_TABLE_END, 4):
        entry = read_long_pointer_entry(rom, POINTER_TABLE_BANK, address)
        entry["index"] = len(pointer_entries)
        pointer_entries.append(entry)

    unique_offsets = sorted({entry["target_offset"] for entry in pointer_entries})
    descriptors = [decode_descriptor(rom, offset) for offset in unique_offsets]
    pointer_target_counts = Counter(entry["target"] for entry in pointer_entries)
    piece_count_counts = Counter(
        str(descriptor["header"]["piece_count_per_pass"]) for descriptor in descriptors
    )
    trailing_attribute_counts: Counter[str] = Counter()
    terminal_marker_mismatches = 0
    for descriptor in descriptors:
        piece_count = descriptor["header"]["piece_count_per_pass"]
        for body_pass in descriptor["body_passes"]:
            for piece in body_pass:
                trailing_attribute_counts[piece["trailing_attribute"]] += 1
                expected_terminal = piece["ordinal"] == piece_count - 1
                actual_terminal = piece["trailing_attribute_bits"]["pass_terminal_piece_marker"]
                if expected_terminal != actual_terminal:
                    terminal_marker_mismatches += 1
    max_record_end = max(int(descriptor["range"].split("..")[1].split(":")[1], 16) for descriptor in descriptors)

    return {
        "schema": SCHEMA,
        "game": "earthbound-us",
        "title": "Secondary visual descriptor contract",
        "source_policy": {
            "requires_user_supplied_rom_for_outputs": True,
            "do_not_commit_generated_outputs": True,
        },
        "generator": {"tool": "tools/build_secondary_visual_descriptor_contract.py"},
        "rom": {"sha1": rom_info.sha1, "verified": True},
        "references": [
            "notes/secondary-visual-descriptor-c42b0d.md",
            "notes/c4-visual-frame-copy-and-footprint-tables-283f-2b0d.md",
            "src/c0/c0_1d38_build_entity_visual_records467_e.asm",
            "src/c0/c0_a3a4_build_display_record_from_current_task_data.asm",
        ],
        "summary": {
            "pointer_table": {
                "entries": len(pointer_entries),
                "range": bank_range(POINTER_TABLE_BANK, POINTER_TABLE_START, POINTER_TABLE_END),
                "record_width_bytes": 4,
                "unique_targets": len(unique_offsets),
                "aliased_entries": len(pointer_entries) - len(unique_offsets),
            },
            "descriptor_region": {
                "range": bank_range(POINTER_TABLE_BANK, min(unique_offsets), DESCRIPTOR_RECORD_END),
                "decoded_record_end": bank_addr(POINTER_TABLE_BANK, max_record_end),
            },
            "adjacent_ranges": [
                {
                    "range": bank_range(
                        POINTER_TABLE_BANK,
                        SET_PARTY_TICK_CALLBACKS_START,
                        SET_PARTY_TICK_CALLBACKS_END,
                    ),
                    "name": "SetPartyTickCallbacks",
                    "source": "refs/ebsrc-main/ebsrc-main/src/bankconfig/US/bank04.asm overworld/set_party_tick_callbacks.asm",
                },
                {
                    "range": bank_range(
                        POINTER_TABLE_BANK,
                        MAP_TILE_TABLE_CHUNKS_TABLE_START,
                        MAP_TILE_TABLE_CHUNKS_TABLE_END,
                    ),
                    "name": "MapTileTableChunksTable",
                    "source": "refs/ebsrc-main/ebsrc-main/src/bankconfig/US/bank04.asm data/map/tile_table_chunks_table.asm",
                },
            ],
            "descriptor_count": len(descriptors),
            "piece_count_models": dict(sorted(piece_count_counts.items())),
            "trailing_attribute_counts": dict(sorted(trailing_attribute_counts.items())),
            "trailing_attribute_invariant": {
                "name": "pass_terminal_piece_marker",
                "confidence": "high",
                "observed_pattern": "Only bit 7 is used; it is set exactly on the final piece of each descriptor body pass.",
                "mismatches": terminal_marker_mismatches,
            },
            "tile_base_vram_offset_table": {
                "range": bank_range(
                    POINTER_TABLE_BANK, TILE_BASE_TABLE_START, TILE_BASE_TABLE_END
                ),
                "entries": (TILE_BASE_TABLE_END - TILE_BASE_TABLE_START) // 2,
            },
            "visual_piece_tile_word_ladder": {
                "range": bank_range(
                    POINTER_TABLE_BANK, TILE_WORD_TABLE_START, TILE_WORD_TABLE_END
                ),
                "entries": (TILE_WORD_TABLE_END - TILE_WORD_TABLE_START) // 2,
            },
        },
        "pointer_entries": [
            {
                "index": entry["index"],
                "address": entry["table_address"],
                "target": entry["target"],
                "target_label": DESCRIPTOR_NAMES.get(entry["target_offset"]),
                "alias_count_for_target": pointer_target_counts[entry["target"]],
                "padding": entry["padding"],
            }
            for entry in pointer_entries
        ],
        "descriptors": descriptors,
    }


def write_json(path: Path, document: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_markdown(path: Path, document: dict[str, Any]) -> None:
    summary = document["summary"]
    lines = [
        "# Secondary Visual Descriptor Contracts",
        "",
        "Generated by `tools/build_secondary_visual_descriptor_contract.py`.",
        "",
        "This note summarizes `notes/secondary-visual-descriptor-contracts.json`, a ROM-verified contract for the C4 secondary visual descriptor table used by the C0 entity visual setup path.",
        "",
        "## Coverage",
        "",
        f"- Pointer table: `{summary['pointer_table']['range']}`",
        f"- Pointer entries: {summary['pointer_table']['entries']}",
        f"- Unique descriptor targets: {summary['pointer_table']['unique_targets']}",
        f"- Aliased pointer entries: {summary['pointer_table']['aliased_entries']}",
        f"- Descriptor region: `{summary['descriptor_region']['range']}`",
        f"- Decoded descriptor records: {summary['descriptor_count']}",
        "- Adjacent non-descriptor ranges:",
    ]
    for adjacent in summary["adjacent_ranges"]:
        lines.append(f"  - `{adjacent['range']}` = `{adjacent['name']}`")
    lines.extend(
        [
            f"- Tile base VRAM offset table: `{summary['tile_base_vram_offset_table']['range']}` ({summary['tile_base_vram_offset_table']['entries']} words)",
            f"- Visual piece tile-word ladder: `{summary['visual_piece_tile_word_ladder']['range']}` ({summary['visual_piece_tile_word_ladder']['entries']} words)",
        "",
        "## Piece Count Models",
        "",
        "| Pieces per pass | Descriptor records |",
        "| ---: | ---: |",
        ]
    )
    for key, count in summary["piece_count_models"].items():
        lines.append(f"| {key} | {count} |")

    trailing = summary["trailing_attribute_invariant"]
    lines.extend(
        [
            "",
            "## Trailing Attribute Byte",
            "",
            f"- Current name: `{trailing['name']}`",
            f"- Confidence: `{trailing['confidence']}`",
            f"- Observed pattern: {trailing['observed_pattern']}",
            f"- Invariant mismatches: {trailing['mismatches']}",
            "",
            "| Trailing byte | Pieces |",
            "| --- | ---: |",
        ]
    )
    for key, count in summary["trailing_attribute_counts"].items():
        lines.append(f"| `{key}` | {count} |")

    lines.extend(
        [
            "",
            "## Pointer Entries",
            "",
            "| Index | Target | Label | Alias Count |",
            "| ---: | --- | --- | ---: |",
        ]
    )
    for entry in document["pointer_entries"]:
        lines.append(
            f"| {entry['index']} | `{entry['target']}` | `{entry['target_label']}` | {entry['alias_count_for_target']} |"
        )

    lines.extend(
        [
            "",
            "## Descriptor Records",
            "",
            "| Address | Label | Pieces/Pass | First Band | Second Band | Bytes |",
            "| --- | --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for descriptor in document["descriptors"]:
        header = descriptor["header"]
        lines.append(
            f"| `{descriptor['address']}` | `{descriptor['label']}` | "
            f"{header['piece_count_per_pass']} | {header['first_priority_band_count']} | "
            f"{header['second_priority_band_count']} | {descriptor['bytes']} |"
        )

    lines.extend(
        [
            "",
            "## Interpretation Rules",
            "",
            "- Descriptor byte `0` is the piece count copied in each of the two body passes.",
            "- Descriptor byte `1` is the first priority-band count; `byte0 - byte1` is the second band count packed into `$2BE6` low byte.",
            "- Each body pass has `piece_count` repeated 5-byte piece records.",
            "- Pass 1 carries the horizontally flipped partner records in the known descriptors.",
            "- Body record byte `4` uses bit `7` as a pass-terminal piece marker in all decoded descriptors; it is set exactly on the final piece of each body pass, and low bits are currently unused.",
            "- Runtime byte `2` is an OAM-like attribute byte: bit 6 is horizontal flip, bit 7 is likely vertical flip, and bits 4-5 are patched as priority by `C0:A3A4`.",
        ]
    )

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    document = build_contract(args.rom)
    write_json(Path(args.json_out), document)
    write_markdown(Path(args.markdown_out), document)
    print(
        "Built secondary visual descriptor contract: "
        f"{document['summary']['descriptor_count']} descriptors, "
        f"{document['summary']['pointer_table']['entries']} pointer entries."
    )
    print(f"Wrote {rel(Path(args.json_out))}")
    print(f"Wrote {rel(Path(args.markdown_out))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
