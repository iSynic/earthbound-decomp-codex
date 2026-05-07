from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_FTS_CONTRACT = ROOT / "notes" / "map-fts-palette-variant-contract.json"
DEFAULT_POINTER_CONTRACT = ROOT / "notes" / "map-palette-pointer-table-contract.json"
DEFAULT_DESCRIPTOR_CONTRACT = ROOT / "notes" / "map-palette-descriptor-context.json"
DEFAULT_COMMAND_CONTRACT = ROOT / "notes" / "map-palette-command-usage-contract.json"
DEFAULT_JSON_OUT = ROOT / "notes" / "da-map-palette-subrecord-contracts.json"
DEFAULT_MARKDOWN_OUT = ROOT / "notes" / "da-map-palette-subrecord-contracts.md"

SCHEMA = "earthbound-decomp.da-map-palette-subrecord-contracts.v1"
PALETTE_TABLE_START = "DA:7CA7"
PALETTE_TABLE_END = "DA:FAA7"
PALETTE_VARIANT_BYTES = 0xC0
PALETTE_VARIANT_WORDS = PALETTE_VARIANT_BYTES // 2
SUBPALETTE_COUNT = 6
SUBPALETTE_BYTES = 0x20
SUBPALETTE_COLOURS = 16

RESERVED_METADATA_WORDS = {
    0: "event_flag",
    16: "event_palette_selector_word",
    32: "sprite_palette",
    48: "flash_effect",
}
METADATA_SUMMARY_ROLES = (
    "event_flag",
    "event_palette_selector_word",
    "sprite_palette",
    "flash_effect",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build DA map-palette subrecord contracts from existing palette evidence."
    )
    parser.add_argument("--fts-contract", type=Path, default=DEFAULT_FTS_CONTRACT)
    parser.add_argument("--pointer-contract", type=Path, default=DEFAULT_POINTER_CONTRACT)
    parser.add_argument("--descriptor-contract", type=Path, default=DEFAULT_DESCRIPTOR_CONTRACT)
    parser.add_argument("--command-contract", type=Path, default=DEFAULT_COMMAND_CONTRACT)
    parser.add_argument("--json-out", type=Path, default=DEFAULT_JSON_OUT)
    parser.add_argument("--markdown-out", type=Path, default=DEFAULT_MARKDOWN_OUT)
    return parser.parse_args()


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def top_counter_rows(counter: Counter[int], count: int = 8) -> list[dict[str, int]]:
    return [
        {"value": value, "count": seen}
        for value, seen in counter.most_common(count)
    ]


def build_record_shape(descriptor: dict[str, Any]) -> list[dict[str, Any]]:
    roles = {
        int(row["map_palette_subpalette"]): row
        for row in descriptor["summary"]["descriptor_cgram_roles"]
        if row["map_palette_subpalette"] is not None
    }
    fields: list[dict[str, Any]] = []
    for subpalette in range(SUBPALETTE_COUNT):
        offset = subpalette * SUBPALETTE_BYTES
        word_index = offset // 2
        if word_index in RESERVED_METADATA_WORDS:
            role = RESERVED_METADATA_WORDS[word_index]
            fields.append(
                {
                    "offset": offset,
                    "field": role,
                    "size": 2,
                    "word_index": word_index,
                    "note": (
                        "raw ROM metadata word in the first colour slot of this "
                        "subpalette; EBDecomp `.fts` visual rows zero this slot"
                    ),
                }
            )
        descriptor_role = roles[subpalette]
        fields.append(
            {
                "offset": offset,
                "field": f"map_subpalette_{subpalette}_colours",
                "size": 2,
                "count": SUBPALETTE_COLOURS,
                "descriptor_palette": int(descriptor_role["descriptor_palette"]),
                "cgram_shadow_range": descriptor_role["cgram_shadow_range"],
                "note": (
                    f"16 SNES BGR555 colours for arrangement descriptor palette "
                    f"{descriptor_role['descriptor_palette']}; raw colour 0 overlaps "
                    "the metadata word at this subpalette boundary"
                ),
            }
        )
    return fields


def build_physical_rows(pointer: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    row_index = 0
    for entry in pointer["entries"]:
        asset = entry["expected_asset"]
        variant_count = int(asset["variant_count"])
        for variant in range(variant_count):
            rows.append(
                {
                    "physical_row_index": row_index,
                    "palette_id": int(entry["index"]),
                    "variant": variant,
                    "row_id": f"{int(entry['index']):x}{variant:x}",
                    "address": f"DA:{int(asset['start']) + variant * PALETTE_VARIANT_BYTES:04X}",
                    "asset": asset["title"],
                    "asset_range": asset["range"],
                    "tileset_dependency_status": entry["tileset_dependency"]["dependency_status"],
                    "sector_count": int(entry["tileset_dependency"]["sector_count"]),
                }
            )
            row_index += 1
    return rows


def build_metadata_summaries(fts: dict[str, Any]) -> list[dict[str, Any]]:
    summaries = []
    for role in METADATA_SUMMARY_ROLES:
        values = []
        for entry in fts["entries"]:
            if role == "event_palette_selector_word":
                value = int(entry["setting_word_checks"]["event_palette_selector_word"])
            else:
                value = int(entry["setting_summary"][role])
            values.append(value)
        counter = Counter(values)
        nonzero_counter = Counter(value for value in values if value)
        summaries.append(
            {
                "field": role,
                "rows": len(values),
                "zero_rows": counter[0],
                "nonzero_rows": len(values) - counter[0],
                "unique_nonzero_values": len(nonzero_counter),
                "top_nonzero_values": top_counter_rows(nonzero_counter),
            }
        )
    return summaries


def build_event_palette_rows(fts: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for entry in fts["entries"]:
        checks = entry["setting_word_checks"]
        if not bool(checks["event_palette_selector_present"]):
            continue
        rows.append(
            {
                "row_id": entry["row_id"],
                "palette_id": int(entry["tileset_id"]),
                "variant": int(entry["variant"]),
                "event_flag": int(entry["setting_summary"]["event_flag"]),
                "event_palette_selector_word": int(checks["event_palette_selector_word"]),
                "sprite_palette": int(entry["setting_summary"]["sprite_palette"]),
                "status": entry["status"],
                "payload_shape_matches": entry["event_palette_payload"] is not None,
            }
        )
    return rows


def build_script_usage_top(command: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for row in sorted(command["usage_by_palette_variant"], key=lambda item: (-int(item["hit_count"]), item["row_id"])):
        rows.append(
            {
                "row_id": row["row_id"],
                "palette_id": int(row["palette_id"]),
                "variant": int(row["variant"]),
                "hit_count": int(row["hit_count"]),
                "durations": row["duration_frames"],
                "segments": row["segments"],
                "palette_contract_status": row["palette_contract_status"],
                "event_flag": int(row["setting_summary"]["event_flag"]),
                "has_event_palette": bool(row["setting_summary"]["has_event_palette"]),
                "sprite_palette": int(row["setting_summary"]["sprite_palette"]),
                "flash_effect": int(row["setting_summary"]["flash_effect"]),
            }
        )
    return rows


def build_contract(
    fts_path: Path,
    pointer_path: Path,
    descriptor_path: Path,
    command_path: Path,
) -> dict[str, Any]:
    fts = load_json(fts_path)
    pointer = load_json(pointer_path)
    descriptor = load_json(descriptor_path)
    command = load_json(command_path)
    physical_rows = build_physical_rows(pointer)

    if len(physical_rows) != int(fts["summary"]["row_count"]):
        raise ValueError(
            f"Physical DA rows {len(physical_rows)} != FTS rows {fts['summary']['row_count']}"
        )
    if len(physical_rows) * PALETTE_VARIANT_BYTES != 0x7E00:
        raise ValueError("DA map palette span is not the expected DA:7CA7..DA:FAA7 size")

    status_counts = Counter(row["status"] for row in fts["entries"])
    command_status_counts = Counter(row["palette_contract_status"] for row in command["entries"])
    command_variant_keys = {
        (int(row["palette_id"]), int(row["variant"]))
        for row in command["entries"]
    }
    event_palette_rows = build_event_palette_rows(fts)

    descriptor_model = descriptor["summary"]["resolved_cgram_model"]
    if int(descriptor_model["da_map_palette_fit_overflow_cells"]) != 0:
        raise ValueError("Descriptor palette fit still has DA overflow cells")

    return {
        "schema": SCHEMA,
        "title": "DA Map Palette Subrecord Contracts",
        "generator": "tools/build_da_palette_subrecord_contracts.py",
        "source_policy": (
            "Derived from checked-in palette pointer, FTS palette variant, "
            "descriptor-context, and script-command usage contracts. This records "
            "row shapes, offsets, counts, hashes/statuses, and interpretation "
            "boundaries only; it does not commit raw palette bytes."
        ),
        "sources": {
            "fts_palette_variant_contract": rel(fts_path),
            "palette_pointer_contract": rel(pointer_path),
            "palette_descriptor_context": rel(descriptor_path),
            "palette_command_usage": rel(command_path),
        },
        "summary": {
            "palette_variant_table_range": f"{PALETTE_TABLE_START}..{PALETTE_TABLE_END}",
            "palette_variant_rows": len(physical_rows),
            "palette_variant_bytes": PALETTE_VARIANT_BYTES,
            "palette_variant_words": PALETTE_VARIANT_WORDS,
            "subpalettes_per_variant": SUBPALETTE_COUNT,
            "colours_per_subpalette": SUBPALETTE_COLOURS,
            "pointer_entries": int(pointer["summary"]["entry_count"]),
            "exact_pointer_asset_matches": int(pointer["summary"]["exact_pointer_asset_matches"]),
            "palette_setting_variant_count": int(fts["summary"]["palette_setting_variant_count"]),
            "fts_row_key_matches": int(fts["summary"]["row_key_matches_palette_setting_keys"]),
            "exact_rom_palette_variant_matches": int(fts["summary"]["exact_rom_palette_variant_matches"]),
            "reserved_metadata_zeroed_matches": int(fts["summary"]["reserved_metadata_zeroed_matches"]),
            "unexplained_mismatches": int(fts["summary"]["unexplained_mismatches"]),
            "metadata_word_setting_mismatches": int(fts["summary"]["metadata_word_setting_mismatches"]),
            "script_palette_command_hits": int(command["summary"]["hit_count"]),
            "script_referenced_palette_variants": len(command_variant_keys),
            "event_palette_selector_rows": len(event_palette_rows),
            "event_palette_payload_shape_matches": int(fts["summary"]["event_palette_payload_shape_matches"]),
            "script_referenced_event_palette_rows": sum(
                1 for row in command["usage_by_palette_variant"] if row["setting_summary"]["has_event_palette"]
            ),
            "descriptor_palettes_2_7_map_palette_cells": int(descriptor_model["map_palette_cell_count"]),
            "descriptor_palettes_0_1_text_palette_cells": int(descriptor_model["text_palette_cell_count"]),
            "da_map_palette_fit_overflow_cells": int(descriptor_model["da_map_palette_fit_overflow_cells"]),
            "reserved_metadata_difference_counts": fts["summary"]["reserved_metadata_difference_counts"],
            "fts_status_counts": dict(sorted(status_counts.items())),
            "script_command_status_counts": dict(sorted(command_status_counts.items())),
        },
        "metadata_word_summaries": build_metadata_summaries(fts),
        "event_palette_rows": event_palette_rows,
        "script_usage_top_variants": build_script_usage_top(command),
        "record_shape": {
            "struct": "da_map_palette_variant",
            "size": PALETTE_VARIANT_BYTES,
            "fields": build_record_shape(descriptor),
        },
        "script_command_shape": {
            "macro": "CHANGE_MAP_PALETTE",
            "bytes": "1F E1 word byte",
            "fields": [
                {
                    "offset": 2,
                    "field": "palette_word",
                    "size": 2,
                    "model": "palette_word = (variant << 8) | palette_id",
                },
                {
                    "offset": 4,
                    "field": "duration_frames",
                    "size": 1,
                    "model": "palette fade/change duration in frames",
                },
            ],
        },
        "physical_row_samples": physical_rows[:12],
        "interpretation_boundary": [
            "The 168 DA rows are physical contiguous palette variants; use the pointer contract to map palette_id and variant to a physical row.",
            "The four reserved metadata words are field-named because they match map_palette_settings and explain all raw-ROM versus `.fts` visual-row differences.",
            "The event_palette_selector_word is only named as a selector/presence word here; its runtime dispatch semantics remain deferred.",
            "Descriptor palettes 0 and 1 belong to text/common palette memory, not the DA map palette variant rows.",
        ],
    }


def render_markdown(contract: dict[str, Any]) -> str:
    summary = contract["summary"]
    lines = [
        "# DA Map Palette Subrecord Contracts",
        "",
        "Generated by `tools/build_da_palette_subrecord_contracts.py` from the DA pointer, FTS palette-variant, descriptor-context, and script-command contracts.",
        "",
        "## Summary",
        "",
        f"- palette variant table range: `{summary['palette_variant_table_range']}`",
        f"- palette variant rows: `{summary['palette_variant_rows']}`",
        f"- row size: `{summary['palette_variant_bytes']}` bytes / `{summary['palette_variant_words']}` words",
        f"- subpalettes per row: `{summary['subpalettes_per_variant']}`",
        f"- colours per subpalette: `{summary['colours_per_subpalette']}`",
        f"- pointer entries: `{summary['pointer_entries']}`",
        f"- exact pointer/asset matches: `{summary['exact_pointer_asset_matches']}`",
        f"- FTS row-key matches: `{summary['fts_row_key_matches']}`",
        f"- exact ROM palette variant matches: `{summary['exact_rom_palette_variant_matches']}`",
        f"- reserved-metadata zeroed visual-row matches: `{summary['reserved_metadata_zeroed_matches']}`",
        f"- unexplained mismatches: `{summary['unexplained_mismatches']}`",
        f"- metadata-word/setting mismatches: `{summary['metadata_word_setting_mismatches']}`",
        f"- script `CHANGE_MAP_PALETTE` hits: `{summary['script_palette_command_hits']}`",
        f"- script-referenced palette variants: `{summary['script_referenced_palette_variants']}`",
        f"- event-palette selector rows: `{summary['event_palette_selector_rows']}`",
        f"- event-palette payload shape matches: `{summary['event_palette_payload_shape_matches']}`",
        f"- script-referenced event-palette rows: `{summary['script_referenced_event_palette_rows']}`",
        f"- DA descriptor-palette overflow cells: `{summary['da_map_palette_fit_overflow_cells']}`",
        "",
        "## Record Shape",
        "",
        "Each physical DA map-palette variant row is 192 bytes: six 16-colour SNES BGR555 subpalettes.",
        "The first word of subpalettes 0..3 is also a raw-ROM metadata slot; EBDecomp `.fts` visual rows zero those metadata words.",
        "",
        "| Offset | Field | Size | Count | Descriptor/CGRAM Role |",
        "| ---: | --- | ---: | ---: | --- |",
    ]
    for field in contract["record_shape"]["fields"]:
        count = field.get("count", 1)
        role = field.get("note", "")
        if "descriptor_palette" in field:
            role = (
                f"descriptor palette `{field['descriptor_palette']}`, "
                f"CGRAM `{field['cgram_shadow_range']}`"
            )
        lines.append(
            f"| `+0x{field['offset']:02X}` | `{field['field']}` | {field['size']} | {count} | {role} |"
        )

    lines.extend(
        [
            "",
            "## Metadata Word Summary",
            "",
            "| Field | Nonzero Rows | Unique Nonzero Values | Top Nonzero Values |",
            "| --- | ---: | ---: | --- |",
        ]
    )
    for row in contract["metadata_word_summaries"]:
        top_values = ", ".join(f"`{item['value']}` x {item['count']}" for item in row["top_nonzero_values"]) or "-"
        lines.append(
            f"| `{row['field']}` | {row['nonzero_rows']} | {row['unique_nonzero_values']} | {top_values} |"
        )

    lines.extend(
        [
            "",
            "## Event-Palette Rows",
            "",
            "Rows with an event-palette selector/payload are listed for source-emission targeting; selector dispatch semantics remain deferred.",
            "",
            "| Row ID | Palette ID | Variant | Event Flag | Selector Word | Sprite Palette | Status |",
            "| --- | ---: | ---: | ---: | ---: | ---: | --- |",
        ]
    )
    for row in contract["event_palette_rows"]:
        lines.append(
            f"| `{row['row_id']}` | {row['palette_id']} | {row['variant']} | {row['event_flag']} | "
            f"{row['event_palette_selector_word']} | {row['sprite_palette']} | `{row['status']}` |"
        )

    lines.extend(
        [
            "",
            "## Script Command Shape",
            "",
            "`CHANGE_MAP_PALETTE` uses `1F E1 word byte`; all parsed hits match the resolved DA/FTS palette rows.",
            "",
            "| Offset | Field | Size | Model |",
            "| ---: | --- | ---: | --- |",
        ]
    )
    for field in contract["script_command_shape"]["fields"]:
        model = str(field["model"]).replace("|", r"\|")
        lines.append(
            f"| `+0x{field['offset']:X}` | `{field['field']}` | {field['size']} | {model} |"
        )

    lines.extend(
        [
            "",
            "## Script Usage Snapshot",
            "",
            "| Row ID | Palette ID | Variant | Hits | Durations | Segments | Event Palette | Status |",
            "| --- | ---: | ---: | ---: | --- | --- | --- | --- |",
        ]
    )
    for row in contract["script_usage_top_variants"]:
        durations = ", ".join(f"`{item['duration']}`:{item['count']}" for item in row["durations"])
        segments = ", ".join(f"`{item['segment']}`:{item['count']}" for item in row["segments"])
        event_palette = "yes" if row["has_event_palette"] else "no"
        lines.append(
            f"| `{row['row_id']}` | {row['palette_id']} | {row['variant']} | {row['hit_count']} | "
            f"{durations} | {segments} | {event_palette} | `{row['palette_contract_status']}` |"
        )

    lines.extend(
        [
            "",
            "## Physical Row Samples",
            "",
            "| Row | Palette ID | Variant | Address | Asset | Sector Count |",
            "| ---: | ---: | ---: | --- | --- | ---: |",
        ]
    )
    for row in contract["physical_row_samples"]:
        lines.append(
            f"| {row['physical_row_index']} | {row['palette_id']} | {row['variant']} | "
            f"`{row['address']}` | `{row['asset']}` | {row['sector_count']} |"
        )

    lines.extend(["", "## Interpretation Boundary", ""])
    for row in contract["interpretation_boundary"]:
        lines.append(f"- {row}")

    lines.extend(
        [
            "",
            "## Evidence",
            "",
            "- `notes/map-palette-pointer-table-contract.md` proves `DA:FAA7..DA:FB06` points to all 32 DA palette assets.",
            "- `notes/map-fts-palette-variant-contract.md` proves each 192-byte variant shape, the six-subpalette visual payload, and the reserved metadata word roles.",
            "- `notes/map-palette-descriptor-context.md` maps arrangement descriptor palettes `2..7` onto DA subpalettes `0..5` with zero overflow cells.",
            "- `notes/map-palette-command-usage-contract.md` proves the script-side `(variant << 8) | palette_id` argument model for `CHANGE_MAP_PALETTE`.",
            "- `notes/da-map-palette-subrecord-contracts.json` carries the machine-readable record shape, summary counts, and physical row samples.",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    args = parse_args()
    contract = build_contract(
        args.fts_contract,
        args.pointer_contract,
        args.descriptor_contract,
        args.command_contract,
    )
    args.json_out.write_text(json.dumps(contract, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    args.markdown_out.write_text(render_markdown(contract), encoding="utf-8")
    print(f"Wrote {args.json_out} and {args.markdown_out}")


if __name__ == "__main__":
    main()
