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
COMMUNITY_RAM_MAP = ROOT / "refs" / "community-earthbound-docs" / "RAM_map.txt"
SECTOR_TILE_WIDTH = 8
SECTOR_TILE_HEIGHT = 8
CELLS_PER_METATILE = 16
PIXELS_PER_CELL = 64
SUBPALETTE_SIZE = 16
AVAILABLE_SUBPALETTES = MAP_PALETTE_VARIANT_COLORS // SUBPALETTE_SIZE
OFFSET_CANDIDATES = (-2, -1, 0)
MAP_CGRAM_DESCRIPTOR_OFFSET = -2
TEXT_DESCRIPTOR_PALETTES = (0, 1)
MAP_DESCRIPTOR_PALETTES = tuple(range(2, 8))


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


def cgram_role_rows(counter: Counter[int]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for descriptor_palette in range(8):
        count = counter.get(descriptor_palette, 0)
        if descriptor_palette in TEXT_DESCRIPTOR_PALETTES:
            role = "current_text_palette"
            cgram_shadow_range = (
                "$0200..$021F" if descriptor_palette == 0 else "$0220..$023F"
            )
            map_palette_subpalette = None
            map_palette_status = "outside_da_map_palette_payload"
        else:
            role = "current_map_palette"
            map_palette_subpalette = descriptor_palette + MAP_CGRAM_DESCRIPTOR_OFFSET
            start = 0x0240 + map_palette_subpalette * 0x20
            end = start + 0x1F
            cgram_shadow_range = f"${start:04X}..${end:04X}"
            map_palette_status = "covered_by_da_map_palette_variant"
        rows.append(
            {
                "descriptor_palette": descriptor_palette,
                "cell_count": count,
                "pixel_count": count * PIXELS_PER_CELL,
                "cgram_role": role,
                "cgram_shadow_range": cgram_shadow_range,
                "map_palette_subpalette": map_palette_subpalette,
                "map_palette_status": map_palette_status,
            }
        )
    return rows


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
            "community_ram_map": rel(COMMUNITY_RAM_MAP),
        },
        "summary": {
            "direct_scenes": len(direct_scenes),
            "cells_per_scene": SECTOR_TILE_WIDTH * SECTOR_TILE_HEIGHT * CELLS_PER_METATILE,
            "pixels_per_cell": PIXELS_PER_CELL,
            "map_palette_variant_colors": MAP_PALETTE_VARIANT_COLORS,
            "available_16_color_subpalettes_per_variant": AVAILABLE_SUBPALETTES,
            "resolved_cgram_model": {
                "confidence": "high",
                "descriptor_palettes_0_1": "current text palettes at $0200..$023F",
                "descriptor_palettes_2_7": "current map palettes at $0240..$02FF",
                "da_map_palette_descriptor_offset": MAP_CGRAM_DESCRIPTOR_OFFSET,
                "da_map_palette_descriptor_palette_range": [2, 7],
                "da_map_palette_subpalette_range": [0, AVAILABLE_SUBPALETTES - 1],
                "da_map_palette_fit_overflow_cells": overflow_for_offset(
                    Counter(
                        {
                            descriptor_palette: count
                            for descriptor_palette, count in global_counts.items()
                            if descriptor_palette in MAP_DESCRIPTOR_PALETTES
                        }
                    ),
                    MAP_CGRAM_DESCRIPTOR_OFFSET,
                ),
                "text_palette_cell_count": sum(global_counts.get(value, 0) for value in TEXT_DESCRIPTOR_PALETTES),
                "map_palette_cell_count": sum(global_counts.get(value, 0) for value in MAP_DESCRIPTOR_PALETTES),
            },
            "descriptor_palette_counts": hex_counts(global_counts),
            "descriptor_cgram_roles": cgram_role_rows(global_counts),
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
                "descriptor_cgram_roles": cgram_role_rows(counter),
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
                "descriptor_cgram_roles": cgram_role_rows(counter),
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
        "The arrangement descriptor exposes a three-bit SNES BG palette field.",
        "Community RAM notes and the local C0 palette loaders split the CGRAM",
        "shadow as text palettes at `$0200..$023F`, map palettes at",
        "`$0240..$02FF`, and sprite palettes after that. This makes the bank DA",
        "map palette payload the six BG palette block for descriptor palettes",
        "`2..7`, with descriptor palette `N` mapping to DA subpalette `N - 2`.",
        "",
        "## Summary",
        "",
        f"- direct scenes sampled: `{summary['direct_scenes']}`",
        f"- cells per scene: `{summary['cells_per_scene']}`",
        f"- pixels per cell: `{summary['pixels_per_cell']}`",
        f"- map palette variant colors: `{summary['map_palette_variant_colors']}`",
        f"- available 16-color subpalettes per variant: `{summary['available_16_color_subpalettes_per_variant']}`",
        f"- resolved DA descriptor offset: `{summary['resolved_cgram_model']['da_map_palette_descriptor_offset']}`",
        f"- DA map-palette fit overflow cells: `{summary['resolved_cgram_model']['da_map_palette_fit_overflow_cells']}`",
        f"- descriptor palette 0/1 text-palette cells: `{summary['resolved_cgram_model']['text_palette_cell_count']}`",
        f"- descriptor palette 2-7 map-palette cells: `{summary['resolved_cgram_model']['map_palette_cell_count']}`",
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
            "## Resolved CGRAM Roles",
            "",
            "| Descriptor Palette | CGRAM Shadow Range | Role | DA Subpalette | Cells |",
            "| ---: | --- | --- | ---: | ---: |",
        ]
    )
    for row in summary["descriptor_cgram_roles"]:
        subpalette = row["map_palette_subpalette"]
        subpalette_text = "" if subpalette is None else str(subpalette)
        lines.append(
            f"| {row['descriptor_palette']} | `{row['cgram_shadow_range']}` | "
            f"`{row['cgram_role']}` | {subpalette_text} | {row['cell_count']} |"
        )

    lines.extend(
        [
            "",
            "## Historical Candidate Offset Fit",
            "",
            "These rows are kept for continuity with earlier audits. Offset `-2` is now",
            "the resolved DA map-palette offset for descriptor palettes `2..7`; its",
            "remaining overflow is exactly descriptor palettes `0..1`, which belong",
            "to the text/common palette block rather than the DA map-palette payload.",
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
            "and per-tileset/palette descriptor counts, resolved CGRAM roles, and",
            "historical offset fit statistics.",
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
