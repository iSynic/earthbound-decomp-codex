from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

import rom_tools
from render_map_scene_metatile_previews import (
    DEFAULT_TILESET_DIR,
    ROOT,
    extract_arrangement_records,
    rel,
)


DEFAULT_RANGES = ROOT / "build" / "d8-build-candidate-ranges.json"
DEFAULT_ATTRIBUTE_CONTEXT = ROOT / "notes" / "map-collision-attribute-context.json"
DEFAULT_JSON_OUT = ROOT / "notes" / "map-collision-pointer-contract.json"
DEFAULT_MARKDOWN_OUT = ROOT / "notes" / "map-collision-pointer-contract.md"
SCHEMA = "earthbound-decomp.map-collision-pointer-contract.v1"
RECORD_SIZE = 16
POINTER_LABEL_RE = re.compile(r"MapDataTileCollisionPointers(\d+)")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Validate bank D8 tile-collision pointer tables against the third "
            "byte of EBDecomp .fts arrangement/collision cells."
        )
    )
    parser.add_argument("--rom", help="Optional explicit ROM path.")
    parser.add_argument("--ranges", default=str(DEFAULT_RANGES))
    parser.add_argument("--tileset-dir", default=str(DEFAULT_TILESET_DIR))
    parser.add_argument("--attribute-context", default=str(DEFAULT_ATTRIBUTE_CONTEXT))
    parser.add_argument("--json-out", default=str(DEFAULT_JSON_OUT))
    parser.add_argument("--markdown-out", default=str(DEFAULT_MARKDOWN_OUT))
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def range_bytes(rom: bytes, row: dict[str, Any]) -> bytes:
    start = int(str(row["file_offset_start"]), 16)
    end = int(str(row["file_offset_end"]), 16)
    payload = rom[start:end]
    if len(payload) != int(row["size"]):
        raise ValueError(f"{row['labels'][0]} size mismatch: {len(payload)} != {row['size']}")
    return payload


def hex_count(counter: Counter[int]) -> list[dict[str, Any]]:
    return [
        {"value": f"0x{value:02X}", "count": count}
        for value, count in sorted(counter.items())
    ]


def top_hex_count(counter: Counter[int], limit: int = 12) -> list[dict[str, Any]]:
    return [
        {"value": f"0x{value:02X}", "count": count}
        for value, count in counter.most_common(limit)
    ]


def sha1(data: bytes) -> str:
    return hashlib.sha1(data).hexdigest()


def pointer_table_id(row: dict[str, Any]) -> int | None:
    for label in row.get("labels", []):
        match = POINTER_LABEL_RE.search(str(label))
        if match:
            return int(match.group(1))
    return None


def u16_words(payload: bytes) -> list[int]:
    if len(payload) % 2:
        raise ValueError(f"pointer payload has odd byte size: {len(payload)}")
    return [payload[index] | (payload[index + 1] << 8) for index in range(0, len(payload), 2)]


def fts_collision_chunks(path: Path) -> list[bytes]:
    return [
        bytes(int(cell["attribute_byte"]) for cell in metatile)
        for metatile in extract_arrangement_records(path)
    ]


def find_d8_ranges(ranges: list[dict[str, Any]]) -> tuple[dict[str, Any], list[tuple[int, dict[str, Any]]]]:
    data_rows = [
        row
        for row in ranges
        if any(str(label).endswith("MapTileCollisionData") for label in row.get("labels", []))
    ]
    if len(data_rows) != 1:
        raise ValueError(f"expected one MapTileCollisionData row, found {len(data_rows)}")

    pointer_rows: list[tuple[int, dict[str, Any]]] = []
    for row in ranges:
        table_id = pointer_table_id(row)
        if table_id is not None:
            pointer_rows.append((table_id, row))
    pointer_rows.sort(key=lambda item: item[0])
    if [table_id for table_id, _row in pointer_rows] != list(range(len(pointer_rows))):
        raise ValueError("D8 collision pointer tables are not a contiguous zero-based sequence")
    return data_rows[0], pointer_rows


def compare_table(
    table_id: int,
    row: dict[str, Any],
    pointer_payload: bytes,
    data_pool: bytes,
    chunks: list[bytes],
) -> dict[str, Any]:
    words = u16_words(pointer_payload)
    matched_entries = 0
    mismatch_examples: list[dict[str, Any]] = []
    out_of_range: list[dict[str, Any]] = []
    misaligned: list[dict[str, Any]] = []
    table_value_counts: Counter[int] = Counter()
    covered_fts_counts: Counter[int] = Counter()

    for metatile_index, pointer in enumerate(words):
        if pointer % RECORD_SIZE:
            misaligned.append({"metatile_index": metatile_index, "pointer": f"0x{pointer:04X}"})
            continue
        if pointer < 0 or pointer + RECORD_SIZE > len(data_pool):
            out_of_range.append({"metatile_index": metatile_index, "pointer": f"0x{pointer:04X}"})
            continue
        record = data_pool[pointer : pointer + RECORD_SIZE]
        table_value_counts.update(record)
        if metatile_index < len(chunks):
            expected = chunks[metatile_index]
            covered_fts_counts.update(expected)
            if record == expected:
                matched_entries += 1
            elif len(mismatch_examples) < 8:
                mismatch_examples.append(
                    {
                        "metatile_index": metatile_index,
                        "pointer": f"0x{pointer:04X}",
                        "rom_record_sha1": sha1(record),
                        "fts_record_sha1": sha1(expected),
                    }
                )

    trailing_chunks = chunks[len(words) :]
    trailing_nonzero_cells = sum(sum(1 for value in chunk if value != 0) for chunk in trailing_chunks)
    trailing_zero_metatiles = sum(1 for chunk in trailing_chunks if all(value == 0 for value in chunk))

    return {
        "tileset_id": table_id,
        "label": row["labels"][0],
        "range": f"{row['start']}..{row['end']}",
        "file_offsets": f"{row['file_offset_start']}..{row['file_offset_end']}",
        "sha1": row["sha1"],
        "pointer_entries": len(words),
        "fts_metatile_records": len(chunks),
        "covered_fts_metatile_records": min(len(words), len(chunks)),
        "implicit_zero_metatile_records": max(len(chunks) - len(words), 0),
        "trailing_zero_metatile_records": trailing_zero_metatiles,
        "trailing_nonzero_cells": trailing_nonzero_cells,
        "matched_entries": matched_entries,
        "mismatched_entries": len(words) - matched_entries - len(out_of_range) - len(misaligned),
        "out_of_range_pointers": len(out_of_range),
        "misaligned_pointers": len(misaligned),
        "zero_offset_entries": sum(1 for pointer in words if pointer == 0),
        "unique_pointer_offsets": len(set(words)),
        "max_pointer_offset": f"0x{max(words):04X}" if words else None,
        "pointer_value_counts": top_hex_count(table_value_counts, 8),
        "covered_fts_value_counts": top_hex_count(covered_fts_counts, 8),
        "mismatch_examples": mismatch_examples,
        "out_of_range_examples": out_of_range[:8],
        "misaligned_examples": misaligned[:8],
    }


def build_contract(args: argparse.Namespace) -> dict[str, Any]:
    rom_path = rom_tools.find_rom(args.rom)
    rom = rom_tools.load_rom(rom_path)
    ranges_path = Path(args.ranges)
    range_contract = load_json(ranges_path)
    data_row, pointer_rows = find_d8_ranges(range_contract["ranges"])

    data_pool = range_bytes(rom, data_row)
    if len(data_pool) % RECORD_SIZE:
        raise ValueError(f"D8 collision data pool size is not {RECORD_SIZE}-byte aligned")

    tileset_dir = Path(args.tileset_dir)
    all_fts_counts: Counter[int] = Counter()
    pointer_expanded_counts: Counter[int] = Counter()
    covered_fts_counts: Counter[int] = Counter()
    all_pointer_offsets: list[int] = []
    table_rows: list[dict[str, Any]] = []

    for table_id, row in pointer_rows:
        fts_path = tileset_dir / f"{table_id:02d}.fts"
        if not fts_path.is_file():
            raise FileNotFoundError(f"missing .fts tileset for D8 collision table {table_id}: {fts_path}")
        chunks = fts_collision_chunks(fts_path)
        for chunk in chunks:
            all_fts_counts.update(chunk)

        pointer_payload = range_bytes(rom, row)
        words = u16_words(pointer_payload)
        all_pointer_offsets.extend(words)
        for pointer in words:
            if pointer % RECORD_SIZE == 0 and 0 <= pointer <= len(data_pool) - RECORD_SIZE:
                pointer_expanded_counts.update(data_pool[pointer : pointer + RECORD_SIZE])
        for chunk in chunks[: len(words)]:
            covered_fts_counts.update(chunk)

        table_rows.append(compare_table(table_id, row, pointer_payload, data_pool, chunks))

    data_value_counts = Counter(data_pool)
    expected_offsets = set(range(0, len(data_pool), RECORD_SIZE))
    actual_offsets = set(all_pointer_offsets)
    attribute_context_values: list[str] = []
    attribute_context_path = Path(args.attribute_context)
    if attribute_context_path.is_file():
        attribute_context = load_json(attribute_context_path)
        attribute_context_values = list(attribute_context["summary"]["unique_attribute_values"])

    total_pointer_entries = sum(int(row["pointer_entries"]) for row in table_rows)
    matched_entries = sum(int(row["matched_entries"]) for row in table_rows)
    mismatched_entries = sum(int(row["mismatched_entries"]) for row in table_rows)
    out_of_range_pointers = sum(int(row["out_of_range_pointers"]) for row in table_rows)
    misaligned_pointers = sum(int(row["misaligned_pointers"]) for row in table_rows)
    implicit_zero_metatiles = sum(int(row["implicit_zero_metatile_records"]) for row in table_rows)
    trailing_nonzero_cells = sum(int(row["trailing_nonzero_cells"]) for row in table_rows)

    d8_values = set(data_value_counts)
    fts_values = set(all_fts_counts)
    scene_values = {int(value, 16) for value in attribute_context_values}

    return {
        "schema": SCHEMA,
        "title": "Map Collision Pointer Contract",
        "generator": "tools/build_map_collision_pointer_contract.py",
        "source_policy": (
            "Reference-derived structural contract. This records ranges, counts, hashes, "
            "pointer validation, and byte-value distributions only; it does not commit "
            "raw collision records or decoded ROM-derived map payloads."
        ),
        "sources": {
            "rom": rel(rom_path),
            "d8_build_candidate_ranges": rel(ranges_path),
            "tileset_dir": rel(tileset_dir),
            "attribute_context": rel(attribute_context_path),
            "c0_source_scaffold": rel(ROOT / "src" / "c0" / "bank_c0_helpers_asar.asm"),
            "collision_probe_note": rel(ROOT / "notes" / "collision-surface-probes-c052d4-c05e3a.md"),
        },
        "collision_data_pool": {
            "label": data_row["labels"][0],
            "range": f"{data_row['start']}..{data_row['end']}",
            "file_offsets": f"{data_row['file_offset_start']}..{data_row['file_offset_end']}",
            "size": len(data_pool),
            "sha1": data_row["sha1"],
            "record_size": RECORD_SIZE,
            "record_count": len(data_pool) // RECORD_SIZE,
            "unique_values": [f"0x{value:02X}" for value in sorted(d8_values)],
            "value_counts": hex_count(data_value_counts),
        },
        "summary": {
            "tileset_pointer_tables": len(table_rows),
            "collision_record_size_bytes": RECORD_SIZE,
            "collision_data_records": len(data_pool) // RECORD_SIZE,
            "unique_pointer_offsets": len(actual_offsets),
            "all_data_records_referenced": actual_offsets == expected_offsets,
            "missing_data_record_offsets": [f"0x{value:04X}" for value in sorted(expected_offsets - actual_offsets)],
            "extra_pointer_offsets": [f"0x{value:04X}" for value in sorted(actual_offsets - expected_offsets)],
            "pointer_entries": total_pointer_entries,
            "matched_pointer_entries": matched_entries,
            "mismatched_pointer_entries": mismatched_entries,
            "out_of_range_pointers": out_of_range_pointers,
            "misaligned_pointers": misaligned_pointers,
            "fts_metatile_records": sum(int(row["fts_metatile_records"]) for row in table_rows),
            "covered_fts_metatile_records": sum(
                int(row["covered_fts_metatile_records"]) for row in table_rows
            ),
            "implicit_zero_metatile_records": implicit_zero_metatiles,
            "trailing_nonzero_cells": trailing_nonzero_cells,
            "pointer_expanded_value_counts_match_covered_fts": pointer_expanded_counts == covered_fts_counts,
            "fts_values_absent_from_d8_pool": [f"0x{value:02X}" for value in sorted(fts_values - d8_values)],
            "d8_pool_values_absent_from_fts": [f"0x{value:02X}" for value in sorted(d8_values - fts_values)],
            "scene_sample_values_absent_from_full_fts": [
                f"0x{value:02X}" for value in sorted(scene_values - fts_values)
            ],
            "full_fts_values_absent_from_scene_sample": [
                f"0x{value:02X}" for value in sorted(fts_values - scene_values)
            ],
            "working_model": {
                "confidence": "high-structural",
                "collision_record": "16 bytes, one byte per 4x4 metatile cell",
                "pointer_word": "16-byte-aligned offset into D8:0000 collision data pool",
                "fts_link": (
                    "For each direct tileset, D8 pointer entry N resolves to the exact "
                    "16 third-byte values in .fts metatile N; omitted trailing .fts "
                    "metatiles are all-zero collision records."
                ),
                "runtime_load_path": (
                    "C0:0CF3 and the adjacent collision-strip loader path use cached "
                    "$7FF800 offsets and bank D8 source records to populate the active "
                    "$E000 collision page."
                ),
                "runtime_probe_path": (
                    "C0:54C9 reads $E000 as a 64x64 active collision page; C0:5503, "
                    "C0:559C, C0:5639, and C0:56D0 OR footprint edge bytes into $5DA4; "
                    "C0:5E3B/C0:5ECE cache $5DA4 & #$00D0 for entity collision checks."
                ),
            },
        },
        "value_alphabets": {
            "d8_pool_unique_values": [f"0x{value:02X}" for value in sorted(d8_values)],
            "fts_unique_values": [f"0x{value:02X}" for value in sorted(fts_values)],
            "scene_context_unique_values": [f"0x{value:02X}" for value in sorted(scene_values)],
            "d8_pool_value_counts": hex_count(data_value_counts),
            "pointer_expanded_value_counts": hex_count(pointer_expanded_counts),
            "covered_fts_value_counts": hex_count(covered_fts_counts),
            "full_fts_value_counts": hex_count(all_fts_counts),
        },
        "runtime_anchors": [
            {
                "address": "C0:0CF3",
                "name": "Load_VerticalMovementCollisionStripPayload",
                "evidence": "Reads $7FF800 offset cache, sources bank D8 records, writes collision bytes into $E000 active page.",
            },
            {
                "address": "C0:54C9",
                "name": "Read_CollisionByteAndLatchBit10Coord",
                "evidence": "Reads one byte from $E000 active 64x64 page and latches coordinates when bit 0x10 is set.",
            },
            {
                "address": "C0:5503/C0:559C/C0:5639/C0:56D0",
                "name": "Footprint edge collision probes",
                "evidence": "OR horizontal/vertical edge samples from $E000 into $5DA4.",
            },
            {
                "address": "C0:5E3B/C0:5ECE",
                "name": "Entity collision cache updates",
                "evidence": "Cache probed collision flags with mask #$00D0 before terrain compatibility checks.",
            },
        ],
        "tables": table_rows,
    }


def write_markdown(contract: dict[str, Any], path: Path) -> None:
    summary = contract["summary"]
    pool = contract["collision_data_pool"]
    lines: list[str] = [
        "# Map Collision Pointer Contract",
        "",
        "This ROM-verified contract ties the third byte in each `.fts`",
        "arrangement/collision cell to the bank D8 tile-collision pointer tables.",
        "It promotes that byte from a scene-counted candidate into the actual",
        "collision record byte used by the runtime loader.",
        "",
        "## Summary",
        "",
        f"- D8 collision data pool: `{pool['range']}` (`{pool['record_count']}` records of `{pool['record_size']}` bytes)",
        f"- pointer tables: `{summary['tileset_pointer_tables']}`",
        f"- pointer entries: `{summary['pointer_entries']}`",
        f"- matched pointer entries against `.fts`: `{summary['matched_pointer_entries']}`",
        f"- mismatched pointer entries: `{summary['mismatched_pointer_entries']}`",
        f"- out-of-range pointers: `{summary['out_of_range_pointers']}`",
        f"- misaligned pointers: `{summary['misaligned_pointers']}`",
        f"- unique pointer offsets: `{summary['unique_pointer_offsets']}`",
        f"- all D8 data records referenced: `{summary['all_data_records_referenced']}`",
        f"- covered `.fts` metatiles: `{summary['covered_fts_metatile_records']}`",
        f"- implicit all-zero trailing `.fts` metatiles: `{summary['implicit_zero_metatile_records']}`",
        f"- trailing nonzero collision cells: `{summary['trailing_nonzero_cells']}`",
        f"- pointer-expanded values match covered `.fts`: `{summary['pointer_expanded_value_counts_match_covered_fts']}`",
        "- full `.fts` values absent from scene sample: "
        + ", ".join(f"`{value}`" for value in summary["full_fts_values_absent_from_scene_sample"]),
        "",
        "## Data Flow",
        "",
        "- The D8 data pool is a contiguous set of 16-byte collision records.",
        "- Every pointer word is a 16-byte-aligned offset into that pool.",
        "- For tileset `N`, pointer entry `M` resolves to the exact 16 third-byte",
        "  values in `.fts` metatile `M`.",
        "- Pointer tables stop before the fixed `.fts` length of 1024 metatiles;",
        "  every omitted trailing metatile has all-zero collision bytes.",
        "- Pointer offset `0x0000` is a real data-record offset, not a null pointer.",
        "",
        "## Per-Tileset Validation",
        "",
        "| Tileset | Entries | Matches | Unique Offsets | Zero-Offset Entries | Implicit Zero Metatiles | Trailing Nonzero Cells | Max Offset |",
        "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in contract["tables"]:
        lines.append(
            f"| {row['tileset_id']} | {row['pointer_entries']} | {row['matched_entries']} | "
            f"{row['unique_pointer_offsets']} | {row['zero_offset_entries']} | "
            f"{row['implicit_zero_metatile_records']} | {row['trailing_nonzero_cells']} | "
            f"`{row['max_pointer_offset']}` |"
        )

    lines.extend(
        [
            "",
            "## Value Alphabet",
            "",
            "| Source | Unique Values |",
            "| --- | --- |",
        ]
    )
    alphabets = contract["value_alphabets"]
    for key in ("d8_pool_unique_values", "fts_unique_values", "scene_context_unique_values"):
        values = ", ".join(f"`{value}`" for value in alphabets[key])
        lines.append(f"| `{key}` | {values} |")

    lines.extend(
        [
            "",
            "## Runtime Anchors",
            "",
        ]
    )
    for anchor in contract["runtime_anchors"]:
        lines.append(f"- `{anchor['address']}` `{anchor['name']}`: {anchor['evidence']}")

    lines.extend(
        [
            "",
            "## Interpretation Boundary",
            "",
            "This contract proves the storage and load relationship for the collision",
            "byte grid. Runtime mask names are now owned by",
            "`notes/map-collision-runtime-bit-contract.md`: `0x80` is the observed",
            "solid/high-collision bit, `0x10` is the special surface coordinate-latch",
            "bit, and `0x04/0x08` feed the entity terrain-compatibility class. The",
            "remaining `0x01/0x02` low modifier labels still need more caller-side",
            "evidence before they should become final gameplay names.",
            "",
            "## Machine-Readable Data",
            "",
            "`notes/map-collision-pointer-contract.json` records source ranges,",
            "per-table validation, pointer-offset coverage, value distributions,",
            "and runtime anchors without committing raw ROM-derived collision records.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    contract = build_contract(args)
    json_out = Path(args.json_out)
    markdown_out = Path(args.markdown_out)
    json_out.write_text(json.dumps(contract, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_markdown(contract, markdown_out)
    print(f"Wrote {rel(json_out)} and {rel(markdown_out)}")


if __name__ == "__main__":
    main()
