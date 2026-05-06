from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_D7_HELPER = ROOT / "src" / "d7" / "bank_d7_helpers_asar.asm"
DEFAULT_SECTOR_BUNDLES = ROOT / "notes" / "map-sector-bundles.json"
DEFAULT_JSON_OUT = ROOT / "notes" / "d7-sector-metadata-contracts.json"
DEFAULT_MARKDOWN_OUT = ROOT / "notes" / "d7-sector-metadata-contracts.md"

SCHEMA = "earthbound-decomp.d7-sector-metadata-contracts.v1"
SOURCE_NAME = "src/d7/table_data_map_global_tileset_palette_data_asm.asm"
SECTOR_COLUMNS = 40
SECTOR_ROWS = 32
SECTOR_COUNT = SECTOR_COLUMNS * SECTOR_ROWS
METADATA_START = 0xA800
METADATA_END = 0xC600
TILESET_PALETTE_OFFSET = 0x0000
UNKNOWN_BYTE_PLANE_OFFSET = 0x0500
SECTOR_CONTEXT_WORD_OFFSET = 0x0A00
UNKNOWN_WORD_PLANE_OFFSET = 0x1400

SETTING_CODES = {
    "none": 0,
    "indoors": 1,
    "exit mouse usable": 2,
    "lost underworld sprites": 3,
    "magicant sprites": 4,
    "robot sprites": 5,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build D7 per-sector metadata contracts from source-scaffold bytes and map sector bundles."
    )
    parser.add_argument("--d7-helper", type=Path, default=DEFAULT_D7_HELPER)
    parser.add_argument("--sector-bundles", type=Path, default=DEFAULT_SECTOR_BUNDLES)
    parser.add_argument("--json-out", type=Path, default=DEFAULT_JSON_OUT)
    parser.add_argument("--markdown-out", type=Path, default=DEFAULT_MARKDOWN_OUT)
    return parser.parse_args()


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def parse_db_line(line: str) -> list[int]:
    match = re.match(r"\s*db\s+(.+)", line)
    if match is None:
        return []
    values: list[int] = []
    for item in match.group(1).split(","):
        item = item.strip()
        if not item:
            continue
        if not re.fullmatch(r"\$[0-9A-Fa-f]{2}", item):
            raise ValueError(f"Unsupported db token {item!r} in line {line!r}")
        values.append(int(item[1:], 16))
    return values


def source_bytes(path: Path, source_name: str) -> bytes:
    active = False
    values: list[int] = []
    source_marker = f"; Source: {source_name}"
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("; Source: "):
            if active:
                break
            active = line.strip() == source_marker
            continue
        if active:
            values.extend(parse_db_line(line))
    if not values:
        raise ValueError(f"No db bytes found for {source_name} in {rel(path)}")
    return bytes(values)


def word(data: bytes, offset: int) -> int:
    return data[offset] | (data[offset + 1] << 8)


def cpu(low_word: int) -> str:
    return f"D7:{low_word:04X}"


def sector_coords(linear_index: int) -> dict[str, int]:
    return {
        "linear_index": linear_index,
        "x": linear_index // SECTOR_ROWS,
        "y": linear_index % SECTOR_ROWS,
    }


def load_sector_rows(path: Path) -> list[dict[str, Any]]:
    contract = json.loads(path.read_text(encoding="utf-8"))
    sectors = contract["sectors"]
    if len(sectors) != SECTOR_COUNT:
        raise ValueError(f"Expected {SECTOR_COUNT} sectors in {rel(path)}, found {len(sectors)}")
    for index, row in enumerate(sectors):
        if int(row["sector"]["linear_index"]) != index:
            raise ValueError(f"Unexpected sector order at row {index}: {row['sector']!r}")
    return sectors


def counter_dict(counter: Counter[int]) -> dict[str, int]:
    return {f"0x{key:04X}": counter[key] for key in sorted(counter)}


def setting_counter_dict(counter: Counter[str]) -> dict[str, int]:
    return {key: counter[key] for key in sorted(counter, key=lambda value: SETTING_CODES[value])}


def top_counter_rows(counter: Counter[int], count: int = 12, width: int = 4) -> list[dict[str, Any]]:
    return [
        {"value": f"0x{value:0{width}X}", "count": seen}
        for value, seen in counter.most_common(count)
    ]


def build_contract(d7_helper: Path, sector_bundles: Path) -> dict[str, Any]:
    data = source_bytes(d7_helper, SOURCE_NAME)
    expected_len = METADATA_END - METADATA_START
    if len(data) != expected_len:
        raise ValueError(f"Expected {expected_len} D7 metadata bytes, found {len(data)}")

    sectors = load_sector_rows(sector_bundles)
    rows: list[dict[str, Any]] = []
    packed_mismatches: list[dict[str, Any]] = []
    setting_mismatches: list[dict[str, Any]] = []
    tileset_counts: Counter[int] = Counter()
    palette_counts: Counter[int] = Counter()
    packed_counts: Counter[int] = Counter()
    setting_counts: Counter[str] = Counter()
    context_word_counts: Counter[int] = Counter()
    context_low3_counts: Counter[int] = Counter()
    unresolved_byte_plane_counts: Counter[int] = Counter()
    unresolved_word_plane_counts: Counter[int] = Counter()

    for sector_index, sector in enumerate(sectors):
        metadata = sector["metadata"]
        packed = data[TILESET_PALETTE_OFFSET + sector_index]
        unresolved_byte = data[UNKNOWN_BYTE_PLANE_OFFSET + sector_index]
        unresolved_word = word(data, UNKNOWN_WORD_PLANE_OFFSET + sector_index * 2)
        tileset_id = packed >> 3
        palette_variant = packed & 0x07
        expected_tileset_id = int(metadata["Tileset"])
        expected_palette_variant = int(metadata["Palette"])
        if tileset_id != expected_tileset_id or palette_variant != expected_palette_variant:
            packed_mismatches.append(
                {
                    "sector_index": sector_index,
                    "sector": sector_coords(sector_index),
                    "packed": f"0x{packed:02X}",
                    "tileset_id": tileset_id,
                    "palette_variant": palette_variant,
                    "expected_tileset_id": expected_tileset_id,
                    "expected_palette_variant": expected_palette_variant,
                }
            )

        setting = str(metadata["Setting"])
        expected_setting_code = SETTING_CODES[setting]
        sector_context_word = word(data, SECTOR_CONTEXT_WORD_OFFSET + sector_index * 2)
        sector_setting_code = sector_context_word & 0x0007
        if sector_setting_code != expected_setting_code:
            setting_mismatches.append(
                {
                    "sector_index": sector_index,
                    "sector": sector_coords(sector_index),
                    "sector_context_word": f"0x{sector_context_word:04X}",
                    "sector_setting_code_low3": sector_setting_code,
                    "expected_setting": setting,
                    "expected_setting_code": expected_setting_code,
                }
            )

        tileset_counts[tileset_id] += 1
        palette_counts[palette_variant] += 1
        packed_counts[packed] += 1
        setting_counts[setting] += 1
        context_word_counts[sector_context_word] += 1
        context_low3_counts[sector_setting_code] += 1
        unresolved_byte_plane_counts[unresolved_byte] += 1
        unresolved_word_plane_counts[unresolved_word] += 1
        rows.append(
            {
                "sector_index": sector_index,
                "sector": sector_coords(sector_index),
                "packed_tileset_palette": f"0x{packed:02X}",
                "tileset_id": tileset_id,
                "palette_variant": palette_variant,
                "sector_context_word": f"0x{sector_context_word:04X}",
                "sector_setting_code_low3": sector_setting_code,
                "sector_setting": setting,
            }
        )

    if packed_mismatches or setting_mismatches:
        raise ValueError(
            "D7 sector metadata mismatches: "
            f"packed={len(packed_mismatches)}, setting={len(setting_mismatches)}"
        )

    spans = [
        {
            "name": "D7_SECTOR_TILESET_PALETTE_TABLE",
            "address": cpu(METADATA_START + TILESET_PALETTE_OFFSET),
            "end_exclusive": cpu(METADATA_START + UNKNOWN_BYTE_PLANE_OFFSET),
            "bytes": SECTOR_COUNT,
            "row_size": 1,
            "rows": SECTOR_COUNT,
            "status": "consumer-backed",
        },
        {
            "name": "D7_UNRESOLVED_METADATA_BYTE_PLANE",
            "address": cpu(METADATA_START + UNKNOWN_BYTE_PLANE_OFFSET),
            "end_exclusive": cpu(METADATA_START + SECTOR_CONTEXT_WORD_OFFSET),
            "bytes": SECTOR_COUNT,
            "row_size": 1,
            "rows": SECTOR_COUNT,
            "status": "bounded-but-unnamed",
        },
        {
            "name": "D7_SECTOR_CONTEXT_WORD_TABLE",
            "address": cpu(METADATA_START + SECTOR_CONTEXT_WORD_OFFSET),
            "end_exclusive": cpu(METADATA_START + UNKNOWN_WORD_PLANE_OFFSET),
            "bytes": SECTOR_COUNT * 2,
            "row_size": 2,
            "rows": SECTOR_COUNT,
            "status": "consumer-backed-low3",
        },
        {
            "name": "D7_UNRESOLVED_METADATA_WORD_PLANE",
            "address": cpu(METADATA_START + UNKNOWN_WORD_PLANE_OFFSET),
            "end_exclusive": cpu(METADATA_END),
            "bytes": SECTOR_COUNT * 2,
            "row_size": 2,
            "rows": SECTOR_COUNT,
            "status": "bounded-but-unnamed",
        },
    ]

    return {
        "schema": SCHEMA,
        "title": "D7 Sector Metadata Contracts",
        "generator": "tools/build_d7_sector_metadata_contracts.py",
        "source_policy": (
            "Derived from byte-equivalent D7 source-scaffold bytes and the checked-in "
            "map sector bundle contract. The JSON records row-level decoded values, "
            "counts, field names, and validation summaries only; it does not commit "
            "the unresolved raw metadata planes."
        ),
        "sources": {
            "d7_helper": rel(d7_helper),
            "source": SOURCE_NAME,
            "sector_bundles": rel(sector_bundles),
        },
        "summary": {
            "metadata_range": f"{cpu(METADATA_START)}..{cpu(METADATA_END)}",
            "metadata_bytes": expected_len,
            "sector_rows": SECTOR_COUNT,
            "packed_tileset_palette_matches": SECTOR_COUNT - len(packed_mismatches),
            "sector_setting_low3_matches": SECTOR_COUNT - len(setting_mismatches),
            "unique_packed_tileset_palette_bytes": len(packed_counts),
            "unique_tileset_ids": len(tileset_counts),
            "unique_palette_variants": len(palette_counts),
            "unique_sector_context_words": len(context_word_counts),
            "unique_sector_setting_codes": len(context_low3_counts),
            "unique_unresolved_byte_plane_values": len(unresolved_byte_plane_counts),
            "unique_unresolved_word_plane_values": len(unresolved_word_plane_counts),
            "setting_counts": setting_counter_dict(setting_counts),
            "context_word_top_values": top_counter_rows(context_word_counts),
        },
        "spans": spans,
        "record_shapes": {
            "map_sector_tileset_palette": [
                {
                    "offset": 0,
                    "field": "packed_tileset_palette",
                    "size": 1,
                    "bits": {
                        "0..2": "palette_variant",
                        "3..7": "tileset_id",
                    },
                    "evidence": "matches map-sector `Palette` and `Tileset` for all 1280 sectors",
                }
            ],
            "map_sector_context_word": [
                {
                    "offset": 0,
                    "field": "sector_context_word",
                    "size": 2,
                    "bits": {
                        "0..2": "sector_setting_code",
                        "3..15": "context_flags_or_payload_undecoded",
                    },
                    "evidence": (
                        "low three bits match map-sector `Setting` for all 1280 sectors; "
                        "C0:0AA1 loads the full word to $438E"
                    ),
                }
            ],
        },
        "setting_codes": {name: f"0x{code:01X}" for name, code in SETTING_CODES.items()},
        "counts": {
            "tileset_id": counter_dict(tileset_counts),
            "palette_variant": counter_dict(palette_counts),
            "packed_tileset_palette": counter_dict(packed_counts),
            "sector_context_word": counter_dict(context_word_counts),
            "sector_setting_code_low3": counter_dict(context_low3_counts),
        },
        "consumer_usage": {
            "D7_SECTOR_TILESET_PALETTE_TABLE": [
                {
                    "consumer": "src/c0/c0_08cf_derive_landing_region_profile_from_destination.asm",
                    "field_use": "masks bits 0..2 and shifts bits 3..7 while deriving the landing/profile selector",
                },
                {
                    "consumer": "src/c0/c0_0ac5_load_vertical_movement_map_strip_payload.asm",
                    "field_use": "compares shifted tileset/profile id against cached $436E during vertical strip loading",
                },
                {
                    "consumer": "src/c0/c0_0bdc_load_horizontal_movement_map_strip_payload.asm",
                    "field_use": "compares shifted tileset/profile id against cached $436E during horizontal strip loading",
                },
                {
                    "consumer": "src/c0/c0_2291_test_secondary_descriptor_leading_piece_context.asm",
                    "field_use": "rejects secondary descriptors whose shifted tileset/profile id does not match $436E",
                },
                {
                    "consumer": "src/c0/c0_2668_resolve_spawn_probe_candidate_list.asm",
                    "field_use": "uses the shifted tileset/profile id to validate table-backed spawn candidate lists",
                },
                {
                    "consumer": "src/c4/your_sanctuary_tile_arrangement_helpers.asm",
                    "field_use": "consumes the shifted tileset/profile id while choosing sanctuary tile-arrangement data",
                },
            ],
            "D7_SECTOR_CONTEXT_WORD_TABLE": [
                {
                    "consumer": "src/c0/c0_0aa1_lookup_position_cell_context_word.asm",
                    "field_use": "loads the full 16-bit context word into $438E and returns it to callers",
                },
                {
                    "consumer": "src/c0/c0_2668_resolve_spawn_probe_candidate_list.asm",
                    "field_use": "masks low three bits to select spawn-probe threshold behavior",
                },
                {
                    "consumer": "src/c0/c0_3a94_refresh_position_derived_visual_context_class.asm",
                    "field_use": "calls C0:0AA1, masks low three bits, and stores the position-derived visual context class in $9887",
                },
                {
                    "consumer": "src/c0/c0_c0b4_copy_path_to_lane_from_party_path.asm",
                    "field_use": "calls C0:0AA1, masks low three bits, and gates path-lane copying through C3:DFE8",
                },
                {
                    "consumer": "src/c0/c0_c19b_copy_path_to_lane_from_party_member_request.asm",
                    "field_use": "calls C0:0AA1, masks low three bits, and gates party-member path-lane copying through C3:DFE8",
                },
            ],
        },
        "unresolved_plane_summaries": [
            {
                "span": "D7:AD00..D7:B1FF",
                "row_shape": "1280 x 1",
                "status": "bounded-but-unnamed",
                "unique_values": len(unresolved_byte_plane_counts),
                "zero_rows": unresolved_byte_plane_counts[0],
                "top_values": top_counter_rows(unresolved_byte_plane_counts, width=2),
            },
            {
                "span": "D7:BC00..D7:C5FF",
                "row_shape": "1280 x 2",
                "status": "bounded-but-unnamed",
                "unique_values": len(unresolved_word_plane_counts),
                "zero_rows": unresolved_word_plane_counts[0],
                "top_values": top_counter_rows(unresolved_word_plane_counts),
            },
        ],
        "mismatches": {
            "packed_tileset_palette": packed_mismatches,
            "sector_setting_code_low3": setting_mismatches,
        },
        "sample_rows": rows[:8],
        "interpretation_boundary": [
            "D7:AD00..D7:B1FF is a bounded 1280-byte plane, but no direct consumer-backed field names are promoted here.",
            "D7:BC00..D7:C5FF is a bounded 1280-word plane, but no direct consumer-backed field names are promoted here.",
            "Only the low three bits of D7:B200 sector_context_word are named; the high bits remain context_flags_or_payload_undecoded.",
        ],
    }


def render_markdown(contract: dict[str, Any]) -> str:
    summary = contract["summary"]
    lines = [
        "# D7 Sector Metadata Contracts",
        "",
        "Generated by `tools/build_d7_sector_metadata_contracts.py` from the byte-equivalent D7 source scaffold and `notes/map-sector-bundles.json`.",
        "",
        "## Summary",
        "",
        f"- metadata range: `{summary['metadata_range']}`",
        f"- metadata bytes: `{summary['metadata_bytes']}`",
        f"- sector rows: `{summary['sector_rows']}`",
        f"- packed tileset/palette matches: `{summary['packed_tileset_palette_matches']}`",
        f"- sector setting low-three-bit matches: `{summary['sector_setting_low3_matches']}`",
        f"- unique packed tileset/palette bytes: `{summary['unique_packed_tileset_palette_bytes']}`",
        f"- unique tileset ids: `{summary['unique_tileset_ids']}`",
        f"- unique palette variants: `{summary['unique_palette_variants']}`",
        f"- unique sector context words: `{summary['unique_sector_context_words']}`",
        f"- unresolved byte-plane unique values: `{summary['unique_unresolved_byte_plane_values']}`",
        f"- unresolved word-plane unique values: `{summary['unique_unresolved_word_plane_values']}`",
        "",
        "## Span Split",
        "",
        "| Span | Bytes | Row Shape | Status |",
        "| --- | ---: | --- | --- |",
    ]
    for span in contract["spans"]:
        lines.append(
            f"| `{span['address']}..{span['end_exclusive']}` | {span['bytes']} | "
            f"`{span['rows']} x {span['row_size']}` | `{span['status']}` |"
        )

    lines.extend(
        [
            "",
            "## Record Shapes",
            "",
            "`D7:A800..D7:ACFF` is a 1280-row sector table. Each byte packs the map-sector tileset and palette variant.",
            "",
            "| Offset | Field | Size | Bit Meaning | Evidence |",
            "| ---: | --- | ---: | --- | --- |",
        ]
    )
    for field in contract["record_shapes"]["map_sector_tileset_palette"]:
        bits = ", ".join(f"`{key}` = `{value}`" for key, value in field["bits"].items())
        lines.append(
            f"| `+0x{field['offset']:X}` | `{field['field']}` | {field['size']} | {bits} | {field['evidence']} |"
        )

    lines.extend(
        [
            "",
            "`D7:B200..D7:BBFF` is a 1280-row sector context word table. Runtime consumers load the whole word, but only the low three bits are field-named here.",
            "",
            "| Offset | Field | Size | Bit Meaning | Evidence |",
            "| ---: | --- | ---: | --- | --- |",
        ]
    )
    for field in contract["record_shapes"]["map_sector_context_word"]:
        bits = ", ".join(f"`{key}` = `{value}`" for key, value in field["bits"].items())
        lines.append(
            f"| `+0x{field['offset']:X}` | `{field['field']}` | {field['size']} | {bits} | {field['evidence']} |"
        )

    lines.extend(
        [
            "",
            "## Consumer Usage",
            "",
        ]
    )
    for table_name, rows in contract["consumer_usage"].items():
        lines.extend(
            [
                f"### {table_name}",
                "",
                "| Consumer | Supported field use |",
                "| --- | --- |",
            ]
        )
        for row in rows:
            lines.append(f"| `{row['consumer']}` | {row['field_use']} |")

    lines.extend(
        [
            "",
            "## Sector Setting Codes",
            "",
            "| Setting | Code | Count |",
            "| --- | ---: | ---: |",
        ]
    )
    for setting, code in contract["setting_codes"].items():
        lines.append(f"| `{setting}` | `{code}` | {summary['setting_counts'][setting]} |")

    lines.extend(
        [
            "",
            "## Distribution Snapshot",
            "",
            "### Top context words",
            "",
            "| Word | Count |",
            "| ---: | ---: |",
        ]
    )
    for row in summary["context_word_top_values"]:
        lines.append(f"| `{row['value']}` | {row['count']} |")

    lines.extend(
        [
            "",
            "### Sample proven rows",
            "",
            "| Sector | Coords | Packed tileset/palette | Tileset | Palette | Context word | Setting code | Setting |",
            "| ---: | --- | ---: | ---: | ---: | ---: | ---: | --- |",
        ]
    )
    for row in contract["sample_rows"]:
        coords = row["sector"]
        lines.append(
            f"| {row['sector_index']} | `({coords['x']},{coords['y']})` | `{row['packed_tileset_palette']}` | "
            f"{row['tileset_id']} | {row['palette_variant']} | `{row['sector_context_word']}` | "
            f"{row['sector_setting_code_low3']} | `{row['sector_setting']}` |"
        )

    lines.extend(
        [
            "",
            "## Unresolved Plane Summaries",
            "",
            "These summaries keep the two remaining planes byte-bounded without promoting field names.",
            "",
            "| Span | Row Shape | Status | Unique values | Zero rows | Top values |",
            "| --- | --- | --- | ---: | ---: | --- |",
        ]
    )
    for plane in contract["unresolved_plane_summaries"]:
        top_values = ", ".join(f"`{row['value']}` x {row['count']}" for row in plane["top_values"][:6])
        lines.append(
            f"| `{plane['span']}` | `{plane['row_shape']}` | `{plane['status']}` | "
            f"{plane['unique_values']} | {plane['zero_rows']} | {top_values} |"
        )

    lines.extend(
        [
            "",
            "## Interpretation Boundary",
            "",
        ]
    )
    for row in contract["interpretation_boundary"]:
        lines.append(f"- {row}")

    lines.extend(
        [
            "",
            "## Evidence",
            "",
            "- `notes/map-sector-bundles.md` and `notes/map-sector-bundles.json` provide the reference sector-order tileset, palette, and setting values.",
            "- `src/c0/c0_08cf_derive_landing_region_profile_from_destination.asm` reads `D7A800,X`, masks bits `0..2`, and shifts bits `3..7` for the landing/profile selector.",
            "- `src/c0/c0_0ac5_load_vertical_movement_map_strip_payload.asm` and `src/c0/c0_0bdc_load_horizontal_movement_map_strip_payload.asm` read `D7A800,X` and compare the shifted tileset/profile id against `$436E` during movement strip loading.",
            "- `src/c0/c0_2291_test_secondary_descriptor_leading_piece_context.asm` and `src/c0/c0_2668_resolve_spawn_probe_candidate_list.asm` use the shifted `D7A800,X` value to gate secondary descriptors and spawn candidate lists.",
            "- `src/c0/c0_0aa1_lookup_position_cell_context_word.asm` loads `D7B200,X` into `$438E` as the position sector context word.",
            "- `src/c0/c0_2668_resolve_spawn_probe_candidate_list.asm`, `src/c0/c0_3a94_refresh_position_derived_visual_context_class.asm`, `src/c0/c0_c0b4_copy_path_to_lane_from_party_path.asm`, and `src/c0/c0_c19b_copy_path_to_lane_from_party_member_request.asm` mask the low three bits of the D7:B200 context word for spawn, visual-context, and path-lane gates.",
            "- `src/c4/your_sanctuary_tile_arrangement_helpers.asm` also consumes the shifted `D7A800,X` tileset/profile id.",
            "- `notes/d7-sector-metadata-contracts.json` carries machine-readable counts, span splits, and mismatch-free validation summaries.",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    args = parse_args()
    contract = build_contract(args.d7_helper, args.sector_bundles)
    args.json_out.write_text(json.dumps(contract, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    args.markdown_out.write_text(render_markdown(contract), encoding="utf-8")
    print(f"Wrote {args.json_out} and {args.markdown_out}")


if __name__ == "__main__":
    main()
