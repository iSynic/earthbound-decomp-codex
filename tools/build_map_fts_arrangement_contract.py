from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_TILESET_DIR = ROOT / "refs" / "eb-decompile-4ef92" / "Tilesets"
DEFAULT_JSON_OUT = ROOT / "notes" / "map-fts-arrangement-contract.json"
DEFAULT_MARKDOWN_OUT = ROOT / "notes" / "map-fts-arrangement-contract.md"
SCHEMA = "earthbound-decomp.map-fts-arrangement-contract.v1"
ROW_RE = re.compile(r"^[0-9A-Fa-f]{96}$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Decode the 96-character EBDecomp .fts arrangement/collision rows into structural stats."
    )
    parser.add_argument("--tileset-dir", default=str(DEFAULT_TILESET_DIR))
    parser.add_argument("--json-out", default=str(DEFAULT_JSON_OUT))
    parser.add_argument("--markdown-out", default=str(DEFAULT_MARKDOWN_OUT))
    return parser.parse_args()


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def hex_count(counter: Counter[int]) -> list[dict[str, Any]]:
    return [
        {"value": f"0x{value:02X}", "count": count}
        for value, count in sorted(counter.items())
    ]


def int_count(counter: Counter[int]) -> list[dict[str, int]]:
    return [{"value": value, "count": count} for value, count in sorted(counter.items())]


def extract_rows(path: Path) -> list[str]:
    rows = [line.lower() for line in path.read_text(encoding="utf-8", errors="ignore").splitlines() if len(line) == 96]
    bad = [row for row in rows if ROW_RE.fullmatch(row) is None]
    if bad:
        raise ValueError(f"{path} has non-hex 96-character rows")
    if len(rows) != 1024:
        raise ValueError(f"{path} has {len(rows)} 96-character rows, expected 1024")
    return rows


def iter_cells(rows: list[str]) -> list[dict[str, int]]:
    cells: list[dict[str, int]] = []
    for metatile_index, row in enumerate(rows):
        raw = bytes.fromhex(row)
        for cell_index in range(16):
            offset = cell_index * 3
            descriptor_word = raw[offset] | (raw[offset + 1] << 8)
            attribute_byte = raw[offset + 2]
            cells.append(
                {
                    "metatile_index": metatile_index,
                    "cell_index": cell_index,
                    "x": cell_index % 4,
                    "y": cell_index // 4,
                    "descriptor_word": descriptor_word,
                    "tile_index": descriptor_word & 0x03FF,
                    "bg_palette": (descriptor_word >> 10) & 0x07,
                    "priority": 1 if descriptor_word & 0x2000 else 0,
                    "hflip": 1 if descriptor_word & 0x4000 else 0,
                    "vflip": 1 if descriptor_word & 0x8000 else 0,
                    "attribute_byte": attribute_byte,
                }
            )
    return cells


def audit_tileset(path: Path) -> dict[str, Any]:
    match = re.fullmatch(r"(\d{2})\.fts", path.name)
    tileset_id = int(match.group(1)) if match else None
    rows = extract_rows(path)
    cells = iter_cells(rows)
    descriptor_words = [cell["descriptor_word"] for cell in cells]
    tile_indices = [cell["tile_index"] for cell in cells]
    attribute_counts = Counter(cell["attribute_byte"] for cell in cells)
    bg_palette_counts = Counter(cell["bg_palette"] for cell in cells)
    priority_count = sum(cell["priority"] for cell in cells)
    hflip_count = sum(cell["hflip"] for cell in cells)
    vflip_count = sum(cell["vflip"] for cell in cells)
    zero_record_count = sum(1 for row in rows if set(row) == {"0"})
    nonzero_cell_count = sum(
        1 for cell in cells if cell["descriptor_word"] != 0 or cell["attribute_byte"] != 0
    )
    attribute_high_bit_count = sum(count for value, count in attribute_counts.items() if value & 0x80)
    return {
        "tileset_id": tileset_id,
        "path": rel(path),
        "file_sha1": hashlib.sha1(path.read_bytes()).hexdigest(),
        "arrangement_collision_rows_sha1": hashlib.sha1("\n".join(rows).encode("utf-8")).hexdigest(),
        "record_count": len(rows),
        "record_byte_count_if_packed": len(rows) * 48,
        "cell_shape": {
            "cells_per_record": 16,
            "cell_grid_width": 4,
            "cell_grid_height": 4,
            "bytes_per_cell": 3,
            "descriptor_word_endian": "little",
            "descriptor_word_layout": "SNES BG tilemap word candidate: tile index bits 0-9, palette bits 10-12, priority bit 13, hflip bit 14, vflip bit 15",
            "attribute_byte_layout": "unresolved collision/behavior byte candidate",
        },
        "zero_record_count": zero_record_count,
        "unique_record_count": len(set(rows)),
        "cell_count": len(cells),
        "nonzero_cell_count": nonzero_cell_count,
        "descriptor_word_unique_count": len(set(descriptor_words)),
        "tile_index_min": min(tile_indices),
        "tile_index_max": max(tile_indices),
        "tile_index_unique_count": len(set(tile_indices)),
        "bg_palette_counts": int_count(bg_palette_counts),
        "priority_cell_count": priority_count,
        "hflip_cell_count": hflip_count,
        "vflip_cell_count": vflip_count,
        "attribute_byte_counts": hex_count(attribute_counts),
        "attribute_byte_unique_count": len(attribute_counts),
        "attribute_byte_nonzero_cell_count": len(cells) - attribute_counts.get(0, 0),
        "attribute_byte_high_bit_cell_count": attribute_high_bit_count,
    }


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    attribute_counts: Counter[int] = Counter()
    palette_counts: Counter[int] = Counter()
    total_cells = 0
    total_records = 0
    zero_records = 0
    nonzero_cells = 0
    priority_cells = 0
    hflip_cells = 0
    vflip_cells = 0
    tile_index_min = 0
    tile_index_max = 0
    if rows:
        tile_index_min = min(int(row["tile_index_min"]) for row in rows)
        tile_index_max = max(int(row["tile_index_max"]) for row in rows)

    for row in rows:
        total_cells += int(row["cell_count"])
        total_records += int(row["record_count"])
        zero_records += int(row["zero_record_count"])
        nonzero_cells += int(row["nonzero_cell_count"])
        priority_cells += int(row["priority_cell_count"])
        hflip_cells += int(row["hflip_cell_count"])
        vflip_cells += int(row["vflip_cell_count"])
        for item in row["attribute_byte_counts"]:
            attribute_counts[int(item["value"], 16)] += int(item["count"])
        for item in row["bg_palette_counts"]:
            palette_counts[int(item["value"])] += int(item["count"])

    return {
        "tileset_count": len(rows),
        "record_count_total": total_records,
        "cell_count_total": total_cells,
        "record_shape": "1024 records per tileset; each record is 16 cells in a 4x4 grid; each cell is 3 bytes",
        "packed_byte_count_total": total_records * 48,
        "zero_record_count_total": zero_records,
        "nonzero_cell_count_total": nonzero_cells,
        "tile_index_range": [tile_index_min, tile_index_max],
        "bg_palette_counts": int_count(palette_counts),
        "priority_cell_count": priority_cells,
        "hflip_cell_count": hflip_cells,
        "vflip_cell_count": vflip_cells,
        "attribute_byte_counts": hex_count(attribute_counts),
        "attribute_byte_unique_count": len(attribute_counts),
        "attribute_byte_high_bit_cell_count": sum(count for value, count in attribute_counts.items() if value & 0x80),
    }


def build_contract(args: argparse.Namespace) -> dict[str, Any]:
    tileset_dir = Path(args.tileset_dir)
    rows = [audit_tileset(path) for path in sorted(tileset_dir.glob("*.fts"))]
    return {
        "schema": SCHEMA,
        "title": "Map FTS Arrangement/Collision Contract",
        "generator": "tools/build_map_fts_arrangement_contract.py",
        "source_policy": (
            "Reference-derived structural contract. This records row hashes, counts, "
            "and decoded field statistics from the 96-character .fts rows; it does "
            "not commit raw rows or decoded ROM-derived payload arrays."
        ),
        "sources": {
            "tileset_dir": rel(tileset_dir),
            "ref_labels": [
                "refs/ebsrc-main/ebsrc-main/include/symbols/map.inc.asm",
                "refs/community-earthbound-docs/ROM_map.txt",
            ],
        },
        "evidence": [
            "EBDecomp Project.snake maps eb.TilesetModule resources to Tilesets/*.fts.",
            "ebsrc labels expose MAP_DATA_TILE_ARRANGEMENT_* and MAP_DATA_TILE_COLLISION_POINTERS_*.",
            "community ROM map names the adjacent map construction range as Tile Arrangement Collision Data.",
            "All present .fts exports have exactly 1024 96-character hex rows after the variable settings block.",
            "Each 96-character row splits evenly into 16 three-byte cells, matching a 4x4 grid of 8x8 subtiles per map tile/metatile.",
        ],
        "summary": summarize(rows),
        "tilesets": rows,
    }


def write_markdown(contract: dict[str, Any], path: Path) -> None:
    summary = contract["summary"]
    attr_counts = ", ".join(
        f"`{item['value']}`:{item['count']}" for item in summary["attribute_byte_counts"]
    )
    lines = [
        "# Map FTS Arrangement/Collision Contract",
        "",
        "This contract decodes the 96-character section of each local EBDecomp `.fts`",
        "tileset export as `1024` arrangement/collision records.",
        "",
        "The naming is intentionally cautious: reference labels and the row shape both",
        "point at tile arrangement plus collision/behavior data, but the final meaning",
        "of the third byte in each cell still needs runtime corroboration.",
        "",
        "## Summary",
        "",
        f"- tilesets audited: `{summary['tileset_count']}`",
        f"- records: `{summary['record_count_total']}`",
        f"- cells: `{summary['cell_count_total']}`",
        f"- packed bytes represented: `{summary['packed_byte_count_total']}`",
        f"- record shape: `{summary['record_shape']}`",
        f"- zero records: `{summary['zero_record_count_total']}`",
        f"- nonzero cells: `{summary['nonzero_cell_count_total']}`",
        f"- tile index range from descriptor words: `{summary['tile_index_range'][0]}-{summary['tile_index_range'][1]}`",
        f"- priority cells: `{summary['priority_cell_count']}`",
        f"- horizontal-flip cells: `{summary['hflip_cell_count']}`",
        f"- vertical-flip cells: `{summary['vflip_cell_count']}`",
        f"- attribute-byte high-bit cells: `{summary['attribute_byte_high_bit_cell_count']}`",
        "",
        "## Field Model",
        "",
        "| Offset In Cell | Size | Working Name | Status |",
        "| ---: | ---: | --- | --- |",
        "| 0 | 2 | `descriptor_word_le` | high-confidence SNES BG tilemap-word candidate |",
        "| 2 | 1 | `attribute_byte` | unresolved collision/behavior candidate |",
        "",
        "`descriptor_word_le` cleanly yields normal SNES tilemap fields: tile index",
        "bits `0-9`, palette bits `10-12`, priority bit `13`, horizontal flip bit",
        "`14`, and vertical flip bit `15`.",
        "",
        "## Attribute Byte Values",
        "",
        attr_counts,
        "",
        "## Per-Tileset Shape",
        "",
        "| Tileset | Zero Records | Unique Records | Nonzero Cells | Attr Values |",
        "| ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in contract["tilesets"]:
        lines.append(
            f"| {row['tileset_id']} | {row['zero_record_count']} | {row['unique_record_count']} | "
            f"{row['nonzero_cell_count']} | {row['attribute_byte_unique_count']} |"
        )

    lines.extend(
        [
            "",
            "## Machine-Readable Data",
            "",
            "`notes/map-fts-arrangement-contract.json` records one row per direct `.fts`",
            "export with per-tileset row hashes, record/cell counts, descriptor-word",
            "statistics, and attribute-byte distributions.",
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
