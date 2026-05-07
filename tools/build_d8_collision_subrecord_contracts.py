from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_POINTER_CONTRACT = ROOT / "notes" / "map-collision-pointer-contract.json"
DEFAULT_RUNTIME_CONTRACT = ROOT / "notes" / "map-collision-runtime-bit-contract.json"
DEFAULT_JSON_OUT = ROOT / "notes" / "d8-collision-subrecord-contracts.json"
DEFAULT_MARKDOWN_OUT = ROOT / "notes" / "d8-collision-subrecord-contracts.md"
SCHEMA = "earthbound-decomp.d8-collision-subrecord-contracts.v1"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def format_list(values: list[str]) -> str:
    return ", ".join(f"`{value}`" for value in values) if values else "`none`"


def parse_hex(value: str) -> int:
    return int(value, 16)


def format_hex(value: int, width: int = 2) -> str:
    return f"0x{value:0{width}X}"


def matching_count(row: dict[str, Any], source: str) -> int:
    return int(row["counts"][source]["matching_cell_count"])


def count_values(rows: list[dict[str, Any]]) -> dict[int, int]:
    return {parse_hex(row["value"]): int(row["count"]) for row in rows}


def sum_mask_matches(counts: dict[int, int], mask: int) -> int:
    return sum(count for value, count in counts.items() if value & mask)


def observed_mask_values(counts: dict[int, int], mask: int) -> list[str]:
    return [format_hex(value & mask, 4) for value in sorted({value & mask for value in counts})]


def build_bit_family_summary(
    d8_counts: dict[int, int], pointer_counts: dict[int, int], runtime: dict[str, Any]
) -> list[dict[str, Any]]:
    return [
        {
            "mask": "0x00C0",
            "working_name": "high_collision_block_mask",
            "observed_raw_values": runtime["summary"]["observed_high_collision_values"],
            "observed_mask_values": observed_mask_values(d8_counts, 0xC0),
            "d8_cells": sum_mask_matches(d8_counts, 0xC0),
            "pointer_expanded_cells": sum_mask_matches(pointer_counts, 0xC0),
            "source_emission_note": (
                "Preserve as numeric flag bits; 0x80 is observed and 0x40 is "
                "runtime-supported by C0 but absent from verified D8 data."
            ),
        },
        {
            "mask": "0x0010",
            "working_name": "special_surface_coord_latch",
            "observed_raw_values": runtime["summary"]["observed_special_latch_values"],
            "observed_mask_values": observed_mask_values(d8_counts, 0x10),
            "d8_cells": sum_mask_matches(d8_counts, 0x10),
            "pointer_expanded_cells": sum_mask_matches(pointer_counts, 0x10),
            "source_emission_note": (
                "Consumer-backed latch bit; name the mask, not individual gameplay surfaces."
            ),
        },
        {
            "mask": "0x000C",
            "working_name": "entity_terrain_compatibility_class",
            "observed_raw_values": [
                format_hex(value)
                for value in sorted(d8_counts)
                if value & 0x0C
            ],
            "observed_mask_values": observed_mask_values(d8_counts, 0x0C),
            "d8_cells": sum_mask_matches(d8_counts, 0x0C),
            "pointer_expanded_cells": sum_mask_matches(pointer_counts, 0x0C),
            "source_emission_note": (
                "Consumer-backed class bits from C0; keep class values numeric until caller evidence proves labels."
            ),
        },
        {
            "mask": "0x0003",
            "working_name": "low_surface_modifier_bits",
            "observed_raw_values": [
                format_hex(value)
                for value in sorted(d8_counts)
                if value & 0x03
            ],
            "observed_mask_values": observed_mask_values(d8_counts, 0x03),
            "d8_cells": sum_mask_matches(d8_counts, 0x03),
            "pointer_expanded_cells": sum_mask_matches(pointer_counts, 0x03),
            "source_emission_note": (
                "Preserved through C0:5B7B's low-six-bit return path; final gameplay labels remain open."
            ),
        },
    ]


def build_contract(pointer_path: Path, runtime_path: Path) -> dict[str, Any]:
    pointer = load_json(pointer_path)
    runtime = load_json(runtime_path)
    pool = pointer["collision_data_pool"]
    summary = pointer["summary"]
    alphabets = pointer["value_alphabets"]
    d8_counts = count_values(alphabets["d8_pool_value_counts"])
    pointer_counts = count_values(alphabets["pointer_expanded_value_counts"])

    cell_fields = [
        {
            "offset": row * 4 + column,
            "field": f"cell_r{row}_c{column}_surface_collision_flags",
            "row": row,
            "column": column,
            "size": 1,
            "meaning": (
                "one 4x4 metatile-cell surface/collision flag byte expanded "
                "from D8 through the tileset collision pointer table"
            ),
        }
        for row in range(4)
        for column in range(4)
    ]

    pointer_fields = [
        {
            "field": "collision_record_offset",
            "offset": 0,
            "size": 2,
            "meaning": (
                "16-byte-aligned offset into D8:0000 MAP_TILE_COLLISION_DATA; "
                "0x0000 is a real collision record"
            ),
        }
    ]

    mask_rows = [
        {
            "mask": row["mask"],
            "working_name": row["working_name"],
            "d8_cells": matching_count(row, "d8_pool"),
            "full_fts_cells": matching_count(row, "full_fts"),
            "scene_cells": matching_count(row, "scene_sample"),
            "runtime_role": row["runtime_role"],
        }
        for row in runtime["runtime_masks"]
    ]

    source_emission_rows = [
        {
            "family": "MAP_TILE_COLLISION_DATA",
            "span": pool["range"],
            "count": pool["record_count"],
            "stride": pool["record_size"],
            "source_emission_note": (
                "Emit as 2293 16-byte `map_tile_collision_record` rows; every cell byte is "
                "`surface_collision_flags` and all observed values must round-trip."
            ),
        },
        {
            "family": "MAP_DATA_TILE_COLLISION_POINTERS_0..19",
            "span": "D8:8F50..D8:F05D",
            "count": summary["pointer_entries"],
            "stride": 2,
            "source_emission_note": (
                "Emit as 20 exact word-offset tables into `MAP_TILE_COLLISION_DATA`; offsets are "
                "16-byte aligned and `0x0000` is a real record, not null."
            ),
        },
        {
            "family": "implicit .fts zero tails",
            "span": "outside D8 collision pointer tables",
            "count": summary["implicit_zero_metatile_records"],
            "stride": 16,
            "source_emission_note": (
                "These all-zero trailing metatiles are synthesized by `.fts` coverage behavior; "
                "they are not extra D8 records."
            ),
        },
    ]

    return {
        "schema": SCHEMA,
        "title": "D8 Collision Subrecord Contracts",
        "generator": "tools/build_d8_collision_subrecord_contracts.py",
        "source_policy": (
            "Derived from checked-in D8 pointer and C0 runtime-bit contracts. "
            "This records field names, masks, counts, and interpretation "
            "boundaries only; it does not commit raw collision records."
        ),
        "sources": {
            "collision_pointer_contract": str(pointer_path.relative_to(ROOT)),
            "collision_runtime_bit_contract": str(runtime_path.relative_to(ROOT)),
            "d8_table_splits": "notes/d8-table-splits.md",
        },
        "summary": {
            "collision_data_range": pool["range"],
            "collision_record_count": pool["record_count"],
            "collision_record_size": pool["record_size"],
            "surface_flag_cells": int(pool["record_count"]) * int(pool["record_size"]),
            "pointer_tables": summary["tileset_pointer_tables"],
            "pointer_entries": summary["pointer_entries"],
            "unique_pointer_offsets": summary["unique_pointer_offsets"],
            "all_data_records_referenced": summary["all_data_records_referenced"],
            "pointer_entries_matched_fts": summary["matched_pointer_entries"],
            "pointer_expanded_values_match_covered_fts": summary[
                "pointer_expanded_value_counts_match_covered_fts"
            ],
            "implicit_zero_metatile_records": summary["implicit_zero_metatile_records"],
            "trailing_nonzero_fts_cells": summary["trailing_nonzero_cells"],
            "observed_values": pool["unique_values"],
            "d8_pool_value_counts": alphabets["d8_pool_value_counts"],
            "pointer_expanded_value_counts": alphabets["pointer_expanded_value_counts"],
            "runtime_supported_but_unobserved_high_bit": runtime["summary"][
                "runtime_supported_but_unobserved_high_bit"
            ],
            "low_modifier_boundary": (
                "0x01 and 0x02 are preserved through C0:5B7B's low-six-bit "
                "return path, but final human gameplay labels remain open."
            ),
        },
        "record_shape": {
            "struct": "map_tile_collision_record",
            "size": pool["record_size"],
            "fields": cell_fields,
        },
        "pointer_table_shape": {
            "struct": "map_tile_collision_record_offset",
            "size": 2,
            "fields": pointer_fields,
        },
        "runtime_masks": mask_rows,
        "bit_family_summary": build_bit_family_summary(d8_counts, pointer_counts, runtime),
        "source_emission_rows": source_emission_rows,
        "runtime_anchors": runtime["runtime_anchors"],
    }


def render_markdown(contract: dict[str, Any]) -> str:
    summary = contract["summary"]
    lines = [
        "# D8 Collision Subrecord Contracts",
        "",
        "Generated by `tools/build_d8_collision_subrecord_contracts.py` from the D8 pointer and C0 runtime-bit contracts.",
        "",
        "## Summary",
        "",
        f"- collision data range: `{summary['collision_data_range']}`",
        f"- collision records: `{summary['collision_record_count']}` records of `{summary['collision_record_size']}` bytes",
        f"- surface flag cells: `{summary['surface_flag_cells']}`",
        f"- pointer tables: `{summary['pointer_tables']}`",
        f"- pointer entries: `{summary['pointer_entries']}`",
        f"- unique pointer offsets: `{summary['unique_pointer_offsets']}`",
        f"- all D8 data records referenced: `{summary['all_data_records_referenced']}`",
        f"- pointer entries matched against `.fts`: `{summary['pointer_entries_matched_fts']}`",
        f"- pointer-expanded values match covered `.fts`: `{summary['pointer_expanded_values_match_covered_fts']}`",
        f"- implicit all-zero trailing `.fts` metatiles: `{summary['implicit_zero_metatile_records']}`",
        f"- trailing nonzero `.fts` cells outside D8 pointer coverage: `{summary['trailing_nonzero_fts_cells']}`",
        "- observed collision values: " + format_list(summary["observed_values"]),
        f"- runtime-supported but unobserved high bit: `{summary['runtime_supported_but_unobserved_high_bit']}`",
        "",
        "## Source-Emission Summary",
        "",
        "| Family | Span | Count | Stride | Source Emission Note |",
        "| --- | --- | ---: | ---: | --- |",
    ]
    for row in contract["source_emission_rows"]:
        lines.append(
            f"| `{row['family']}` | `{row['span']}` | {row['count']} | "
            f"`0x{int(row['stride']):X}` | {row['source_emission_note']} |"
        )

    lines.extend(
        [
            "",
            "## Value Counts",
            "",
            "The D8 pool counts describe the 2293 unique source records; pointer-expanded counts describe the 12423 referenced metatiles after applying tileset pointer tables.",
            "",
            "| Value | D8 Pool Cells | Pointer-Expanded Cells |",
            "| ---: | ---: | ---: |",
        ]
    )
    pointer_counts_by_value = {
        row["value"]: int(row["count"])
        for row in summary["pointer_expanded_value_counts"]
    }
    for row in summary["d8_pool_value_counts"]:
        value = row["value"]
        lines.append(
            f"| `{value}` | {int(row['count'])} | {pointer_counts_by_value[value]} |"
        )

    lines.extend(
        [
            "",
            "## Bit Families",
            "",
            "| Mask | Working Name | Observed Raw Values | Observed Mask Values | D8 Cells | Pointer-Expanded Cells | Source Emission Note |",
            "| ---: | --- | --- | --- | ---: | ---: | --- |",
        ]
    )
    for row in contract["bit_family_summary"]:
        lines.append(
            f"| `{row['mask']}` | `{row['working_name']}` | "
            f"{format_list(row['observed_raw_values'])} | "
            f"{format_list(row['observed_mask_values'])} | {row['d8_cells']} | "
            f"{row['pointer_expanded_cells']} | {row['source_emission_note']} |"
        )

    lines.extend(
        [
            "",
            "## Record Shape",
            "",
            "Each `MAP_TILE_COLLISION_DATA` record is a 4x4 metatile-cell grid.",
            "Each byte is now named as a `surface_collision_flags` field because the D8 pointer contract proves the storage grid and the C0 runtime contract proves the mask roles.",
            "",
            "| Offset | Field | Cell | Size |",
            "| ---: | --- | --- | ---: |",
        ]
    )
    for field in contract["record_shape"]["fields"]:
        lines.append(
            f"| `0x{field['offset']:X}` | `{field['field']}` | "
            f"`r{field['row']}c{field['column']}` | {field['size']} |"
        )

    lines.extend(
        [
            "",
            "## Pointer Shape",
            "",
            "Each `MAP_DATA_TILE_COLLISION_POINTERS_n` entry is a 16-byte-aligned offset into `D8:0000`.",
            "Offset `0x0000` is a real collision record, not a null pointer.",
            "",
            "| Offset | Field | Size | Meaning |",
            "| ---: | --- | ---: | --- |",
        ]
    )
    for field in contract["pointer_table_shape"]["fields"]:
        lines.append(f"| `0x{field['offset']:X}` | `{field['field']}` | {field['size']} | {field['meaning']} |")

    lines.extend(
        [
            "",
            "## Runtime Masks",
            "",
            "| Mask | Working Name | D8 Cells | Full `.fts` Cells | Scene Cells | Role |",
            "| ---: | --- | ---: | ---: | ---: | --- |",
        ]
    )
    for row in contract["runtime_masks"]:
        lines.append(
            f"| `{row['mask']}` | `{row['working_name']}` | {row['d8_cells']} | "
            f"{row['full_fts_cells']} | {row['scene_cells']} | {row['runtime_role']} |"
        )

    lines.extend(
        [
            "",
            "## Interpretation Boundary",
            "",
            "- `0x80` is the observed high-collision bit; `0x40` is supported by the C0 mask but not observed in verified D8 data.",
            "- `0x10` latches special-surface coordinates through `C0:54C9` and participates in the per-slot movement cache stop mask.",
            "- `0x04/0x08` are the entity terrain-compatibility class consumed by `C0:5DE7`.",
            f"- {summary['low_modifier_boundary']}",
            "",
            "## Evidence",
            "",
            "- `notes/d8-table-splits.md` pins the D8 collision data and pointer-table spans.",
            "- `notes/map-collision-pointer-contract.md` proves the 16-byte D8 record grid and pointer-table equivalence to `.fts` collision bytes.",
            "- `notes/map-collision-runtime-bit-contract.md` proves the runtime mask roles from C0/C2 consumers.",
            "- `notes/d8-collision-subrecord-contracts.json` carries the machine-readable field names and mask summary.",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build D8 collision subrecord contracts.")
    parser.add_argument("--pointer-contract", type=Path, default=DEFAULT_POINTER_CONTRACT)
    parser.add_argument("--runtime-contract", type=Path, default=DEFAULT_RUNTIME_CONTRACT)
    parser.add_argument("--json-out", type=Path, default=DEFAULT_JSON_OUT)
    parser.add_argument("--markdown-out", type=Path, default=DEFAULT_MARKDOWN_OUT)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    contract = build_contract(args.pointer_contract, args.runtime_contract)
    args.json_out.write_text(json.dumps(contract, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    args.markdown_out.write_text(render_markdown(contract), encoding="utf-8")
    print(f"Wrote {args.json_out} and {args.markdown_out}")


if __name__ == "__main__":
    main()
