from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from render_map_scene_metatile_previews import (
    DEFAULT_CONTRACT,
    DEFAULT_MAP_TILES,
    DEFAULT_TILESET_DIR,
    MAP_PALETTE_VARIANT_COLORS,
    ROOT,
    extract_arrangement_records,
    parse_map_tiles,
    rel,
    sector_tile_grid,
)


DEFAULT_JSON_OUT = ROOT / "notes" / "map-palette-descriptor-context.json"
DEFAULT_MARKDOWN_OUT = ROOT / "notes" / "map-palette-descriptor-context.md"
SCHEMA = "earthbound-decomp.map-palette-descriptor-context.v1"
SECTOR_TILE_WIDTH = 8
SECTOR_TILE_HEIGHT = 8
CELLS_PER_METATILE = 16
PIXELS_PER_CELL = 64
SUBPALETTE_SIZE = 16
AVAILABLE_SUBPALETTES = MAP_PALETTE_VARIANT_COLORS // SUBPALETTE_SIZE
OFFSET_CANDIDATES = (-2, -1, 0)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit live-scene descriptor palette bits against map palette variant shape."
    )
    parser.add_argument("--map-tiles", default=str(DEFAULT_MAP_TILES))
    parser.add_argument("--tileset-dir", default=str(DEFAULT_TILESET_DIR))
    parser.add_argument("--contract", default=str(DEFAULT_CONTRACT))
    parser.add_argument("--json-out", default=str(DEFAULT_JSON_OUT))
    parser.add_argument("--markdown-out", default=str(DEFAULT_MARKDOWN_OUT))
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def hex_counts(counter: Counter[int]) -> list[dict[str, int]]:
    return [
        {"descriptor_palette": value, "cell_count": count, "pixel_count": count * PIXELS_PER_CELL}
        for value, count in sorted(counter.items())
    ]


def scene_palette_counts(
    scene: dict[str, Any],
    map_tiles: list[list[int]],
    arrangement_cache: dict[int, list[list[dict[str, int]]]],
    tileset_dir: Path,
) -> Counter[int]:
    sector = scene["sector"]
    tileset_id = int(scene["tileset_dependency"]["tileset_id"])
    if tileset_id not in arrangement_cache:
        arrangement_cache[tileset_id] = extract_arrangement_records(tileset_dir / f"{tileset_id:02d}.fts")
    grid = sector_tile_grid(map_tiles, int(sector["x"]), int(sector["y"]))
    counts: Counter[int] = Counter()
    for local_x in range(SECTOR_TILE_WIDTH):
        for local_y in range(SECTOR_TILE_HEIGHT):
            for cell in arrangement_cache[tileset_id][grid[local_x][local_y]]:
                counts[int(cell["palette"])] += 1
    return counts


def overflow_for_offset(counter: Counter[int], offset: int) -> int:
    overflow = 0
    for descriptor_palette, count in counter.items():
        subpalette = descriptor_palette + offset
        if not 0 <= subpalette < AVAILABLE_SUBPALETTES:
            overflow += count
    return overflow


def build_context(args: argparse.Namespace) -> dict[str, Any]:
    map_tiles = parse_map_tiles(Path(args.map_tiles))
    contract = load_json(Path(args.contract))
    tileset_dir = Path(args.tileset_dir)
    arrangement_cache: dict[int, list[list[dict[str, int]]]] = {}

    direct_scenes = [
        scene
        for scene in contract["scenes"]
        if scene["tileset_dependency"]["direct_contract_status"] == "direct_fts_contracts_present"
    ]

    global_counts: Counter[int] = Counter()
    by_tileset: dict[int, Counter[int]] = defaultdict(Counter)
    by_palette_variant: dict[str, Counter[int]] = defaultdict(Counter)
    scene_rows: list[dict[str, Any]] = []

    for scene in direct_scenes:
        counts = scene_palette_counts(scene, map_tiles, arrangement_cache, tileset_dir)
        tileset_id = int(scene["tileset_dependency"]["tileset_id"])
        palette_id = int(scene["palette_dependency"]["palette_id"])
        global_counts.update(counts)
        by_tileset[tileset_id].update(counts)
        by_palette_variant[f"{tileset_id:02d}:{palette_id:02d}"].update(counts)
        scene_rows.append(
            {
                "scene_id": scene["scene_id"],
                "sector": scene["sector"],
                "tileset_id": tileset_id,
                "palette_id": palette_id,
                "descriptor_palette_counts": hex_counts(counts),
                "offset_overflow_cell_counts": {
                    str(offset): overflow_for_offset(counts, offset)
                    for offset in OFFSET_CANDIDATES
                },
            }
        )

    total_cells = sum(global_counts.values())
    return {
        "schema": SCHEMA,
        "title": "Map Palette Descriptor Context",
        "generator": "tools/build_map_palette_descriptor_context.py",
        "source_policy": (
            "Reference-derived descriptor-palette context. This records counts and "
            "fit statistics only; it does not commit raw map tile grids, decoded "
            "graphics, palette bytes, or rendered previews."
        ),
        "sources": {
            "map_tiles": rel(Path(args.map_tiles)),
            "tileset_dir": rel(Path(args.tileset_dir)),
            "scene_contract": rel(Path(args.contract)),
        },
        "summary": {
            "direct_scenes": len(direct_scenes),
            "cells_per_scene": SECTOR_TILE_WIDTH * SECTOR_TILE_HEIGHT * CELLS_PER_METATILE,
            "pixels_per_cell": PIXELS_PER_CELL,
            "map_palette_variant_colors": MAP_PALETTE_VARIANT_COLORS,
            "available_16_color_subpalettes_per_variant": AVAILABLE_SUBPALETTES,
            "descriptor_palette_counts": hex_counts(global_counts),
            "offset_candidates": [
                {
                    "palette_subpalette_offset": offset,
                    "overflow_cells": overflow_for_offset(global_counts, offset),
                    "overflow_pixels": overflow_for_offset(global_counts, offset) * PIXELS_PER_CELL,
                    "overflow_percent": (
                        overflow_for_offset(global_counts, offset) / total_cells
                        if total_cells
                        else 0.0
                    ),
                }
                for offset in OFFSET_CANDIDATES
            ],
        },
        "by_tileset": [
            {
                "tileset_id": tileset_id,
                "descriptor_palette_counts": hex_counts(counter),
                "offset_overflow_cell_counts": {
                    str(offset): overflow_for_offset(counter, offset)
                    for offset in OFFSET_CANDIDATES
                },
            }
            for tileset_id, counter in sorted(by_tileset.items())
        ],
        "by_tileset_palette_variant": [
            {
                "tileset_palette": key,
                "descriptor_palette_counts": hex_counts(counter),
                "offset_overflow_cell_counts": {
                    str(offset): overflow_for_offset(counter, offset)
                    for offset in OFFSET_CANDIDATES
                },
            }
            for key, counter in sorted(by_palette_variant.items())
        ],
        "top_overflow_scenes_raw_descriptor": sorted(
            scene_rows,
            key=lambda row: (-int(row["offset_overflow_cell_counts"]["0"]), int(row["sector"]["linear_index"])),
        )[:32],
    }


def write_markdown(context: dict[str, Any], path: Path) -> None:
    summary = context["summary"]
    lines = [
        "# Map Palette Descriptor Context",
        "",
        "This audit compares live-scene descriptor palette bits against the bank DA",
        "map palette payload shape. Each map palette variant is `192` bytes, or",
        "`96` SNES BGR555 colors: six 16-color subpalettes.",
        "",
        "The arrangement descriptor still exposes a three-bit palette field. This",
        "report keeps the field named literally and measures candidate offsets",
        "instead of picking an unproven interpretation.",
        "",
        "## Summary",
        "",
        f"- direct scenes sampled: `{summary['direct_scenes']}`",
        f"- cells per scene: `{summary['cells_per_scene']}`",
        f"- pixels per cell: `{summary['pixels_per_cell']}`",
        f"- map palette variant colors: `{summary['map_palette_variant_colors']}`",
        f"- available 16-color subpalettes per variant: `{summary['available_16_color_subpalettes_per_variant']}`",
        "",
        "## Descriptor Palette Counts",
        "",
        "| Descriptor Palette | Cell Count | Pixel Count |",
        "| ---: | ---: | ---: |",
    ]
    for row in summary["descriptor_palette_counts"]:
        lines.append(f"| {row['descriptor_palette']} | {row['cell_count']} | {row['pixel_count']} |")

    lines.extend(
        [
            "",
            "## Candidate Offset Fit",
            "",
            "| Offset | Overflow Cells | Overflow Pixels | Overflow % |",
            "| ---: | ---: | ---: | ---: |",
        ]
    )
    for row in summary["offset_candidates"]:
        lines.append(
            f"| {row['palette_subpalette_offset']} | {row['overflow_cells']} | "
            f"{row['overflow_pixels']} | {row['overflow_percent']:.3%} |"
        )

    lines.extend(
        [
            "",
            "## Top Raw-Descriptor Overflow Scenes",
            "",
            "| Scene | Sector | Tileset | Palette | Overflow Cells |",
            "| --- | --- | ---: | ---: | ---: |",
        ]
    )
    for row in context["top_overflow_scenes_raw_descriptor"][:16]:
        sector = row["sector"]
        lines.append(
            f"| `{row['scene_id']}` | `{sector['x']},{sector['y']}` | "
            f"{row['tileset_id']} | {row['palette_id']} | {row['offset_overflow_cell_counts']['0']} |"
        )

    lines.extend(
        [
            "",
            "## Machine-Readable Data",
            "",
            "`notes/map-palette-descriptor-context.json` records global, per-tileset,",
            "and per-tileset/palette descriptor counts plus offset fit statistics.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    context = build_context(args)
    json_out = Path(args.json_out)
    markdown_out = Path(args.markdown_out)
    json_out.write_text(json.dumps(context, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_markdown(context, markdown_out)
    print(f"Wrote {rel(json_out)} and {rel(markdown_out)}")


if __name__ == "__main__":
    main()
