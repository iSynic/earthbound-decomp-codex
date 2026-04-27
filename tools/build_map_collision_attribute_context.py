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
    ROOT,
    extract_arrangement_records,
    parse_map_tiles,
    rel,
    sector_tile_grid,
)


DEFAULT_JSON_OUT = ROOT / "notes" / "map-collision-attribute-context.json"
DEFAULT_MARKDOWN_OUT = ROOT / "notes" / "map-collision-attribute-context.md"
SCHEMA = "earthbound-decomp.map-collision-attribute-context.v1"
SECTOR_TILE_WIDTH = 8
SECTOR_TILE_HEIGHT = 8
CELLS_PER_METATILE = 16


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Summarize .fts arrangement attribute-byte usage in actual map scenes."
    )
    parser.add_argument("--map-tiles", default=str(DEFAULT_MAP_TILES))
    parser.add_argument("--tileset-dir", default=str(DEFAULT_TILESET_DIR))
    parser.add_argument("--contract", default=str(DEFAULT_CONTRACT))
    parser.add_argument("--json-out", default=str(DEFAULT_JSON_OUT))
    parser.add_argument("--markdown-out", default=str(DEFAULT_MARKDOWN_OUT))
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def hex_counter(counter: Counter[int]) -> list[dict[str, int | str]]:
    return [
        {"value": f"0x{value:02X}", "count": count}
        for value, count in sorted(counter.items())
    ]


def top_hex_counter(counter: Counter[int], limit: int = 12) -> list[dict[str, int | str]]:
    return [
        {"value": f"0x{value:02X}", "count": count}
        for value, count in counter.most_common(limit)
    ]


def top_named_counter(counter: Counter[str], limit: int = 12) -> list[dict[str, int | str]]:
    return [
        {"name": name, "count": count}
        for name, count in counter.most_common(limit)
    ]


def scene_sort_key(row: dict[str, Any]) -> tuple[int, int]:
    return (-int(row["nonzero_attribute_cells"]), int(row["sector"]["linear_index"]))


def summarize_scene(
    scene: dict[str, Any],
    map_tiles: list[list[int]],
    arrangement_cache: dict[int, list[list[dict[str, int]]]],
    tileset_dir: Path,
) -> dict[str, Any]:
    sector = scene["sector"]
    tileset_id = int(scene["tileset_dependency"]["tileset_id"])
    if tileset_id not in arrangement_cache:
        arrangement_cache[tileset_id] = extract_arrangement_records(tileset_dir / f"{tileset_id:02d}.fts")

    grid = sector_tile_grid(map_tiles, int(sector["x"]), int(sector["y"]))
    counts: Counter[int] = Counter()
    unique_metatiles: set[int] = set()
    for local_x in range(SECTOR_TILE_WIDTH):
        for local_y in range(SECTOR_TILE_HEIGHT):
            metatile_id = grid[local_x][local_y]
            unique_metatiles.add(metatile_id)
            for cell in arrangement_cache[tileset_id][metatile_id]:
                counts[int(cell["attribute_byte"])] += 1

    total_cells = SECTOR_TILE_WIDTH * SECTOR_TILE_HEIGHT * CELLS_PER_METATILE
    zero_cells = counts.get(0, 0)
    high_bit_cells = sum(count for value, count in counts.items() if value & 0x80)
    return {
        "scene_id": scene["scene_id"],
        "sector": sector,
        "tileset_id": tileset_id,
        "palette_id": int(scene["palette_dependency"]["palette_id"]),
        "scene_features": scene["scene_features"],
        "unique_metatile_count": len(unique_metatiles),
        "total_cells": total_cells,
        "zero_attribute_cells": zero_cells,
        "nonzero_attribute_cells": total_cells - zero_cells,
        "high_bit_attribute_cells": high_bit_cells,
        "attribute_counts": hex_counter(counts),
    }


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

    scenes = [
        summarize_scene(scene, map_tiles, arrangement_cache, tileset_dir)
        for scene in direct_scenes
    ]
    global_counts: Counter[int] = Counter()
    scene_presence: Counter[int] = Counter()
    tileset_counts: dict[int, Counter[int]] = defaultdict(Counter)
    setting_counts: dict[str, Counter[int]] = defaultdict(Counter)
    town_map_counts: dict[str, Counter[int]] = defaultdict(Counter)
    feature_presence: dict[str, Counter[int]] = defaultdict(Counter)

    for scene in scenes:
        counts = Counter(
            {
                int(row["value"], 16): int(row["count"])
                for row in scene["attribute_counts"]
            }
        )
        global_counts.update(counts)
        tileset_counts[int(scene["tileset_id"])].update(counts)
        setting_counts[str(scene["scene_features"]["setting"])].update(counts)
        town_map_counts[str(scene["scene_features"]["town_map"])].update(counts)
        for value in counts:
            scene_presence[value] += 1
            features = scene["scene_features"]
            if int(features["door_count"]) > 0:
                feature_presence["has_doors"][value] += 1
            if int(features["trigger_count"]) > 0:
                feature_presence["has_triggers"][value] += 1
            if int(features["object_count"]) > 0:
                feature_presence["has_objects"][value] += 1
            if int(features["hotspot_count"]) > 0:
                feature_presence["has_hotspots"][value] += 1
            if int(features["map_change_group_count"]) > 0:
                feature_presence["has_map_changes"][value] += 1

    total_cells = sum(int(scene["total_cells"]) for scene in scenes)
    nonzero_cells = sum(int(scene["nonzero_attribute_cells"]) for scene in scenes)
    high_bit_cells = sum(int(scene["high_bit_attribute_cells"]) for scene in scenes)
    top_nonzero_scenes = sorted(scenes, key=scene_sort_key)[:24]

    return {
        "schema": SCHEMA,
        "title": "Map Collision Attribute Context",
        "generator": "tools/build_map_collision_attribute_context.py",
        "source_policy": (
            "Reference-derived context contract. This records counts and scene-level "
            "correlations only; it does not commit raw map tile grids, arrangement rows, "
            "decoded graphics, or rendered ROM-derived payloads."
        ),
        "sources": {
            "map_tiles": rel(Path(args.map_tiles)),
            "tileset_dir": rel(Path(args.tileset_dir)),
            "scene_contract": rel(Path(args.contract)),
        },
        "summary": {
            "direct_scenes": len(scenes),
            "cells_per_scene": SECTOR_TILE_WIDTH * SECTOR_TILE_HEIGHT * CELLS_PER_METATILE,
            "scene_cells_sampled": total_cells,
            "nonzero_attribute_cells": nonzero_cells,
            "high_bit_attribute_cells": high_bit_cells,
            "unique_attribute_values": [f"0x{value:02X}" for value in sorted(global_counts)],
            "attribute_counts": hex_counter(global_counts),
            "attribute_scene_presence": hex_counter(scene_presence),
        },
        "by_tileset": [
            {
                "tileset_id": tileset_id,
                "scene_count": sum(1 for scene in scenes if int(scene["tileset_id"]) == tileset_id),
                "attribute_counts": hex_counter(counter),
                "top_attribute_counts": top_hex_counter(counter, 8),
            }
            for tileset_id, counter in sorted(tileset_counts.items())
        ],
        "by_setting": [
            {
                "setting": setting,
                "scene_count": sum(1 for scene in scenes if str(scene["scene_features"]["setting"]) == setting),
                "top_attribute_counts": top_hex_counter(counter, 8),
            }
            for setting, counter in sorted(setting_counts.items())
        ],
        "by_town_map": [
            {
                "town_map": town_map,
                "scene_count": sum(1 for scene in scenes if str(scene["scene_features"]["town_map"]) == town_map),
                "top_attribute_counts": top_hex_counter(counter, 8),
            }
            for town_map, counter in sorted(town_map_counts.items())
        ],
        "feature_presence": [
            {
                "feature": feature,
                "attribute_scene_presence": hex_counter(counter),
            }
            for feature, counter in sorted(feature_presence.items())
        ],
        "top_nonzero_attribute_scenes": [
            {
                "scene_id": scene["scene_id"],
                "sector": scene["sector"],
                "tileset_id": scene["tileset_id"],
                "palette_id": scene["palette_id"],
                "nonzero_attribute_cells": scene["nonzero_attribute_cells"],
                "high_bit_attribute_cells": scene["high_bit_attribute_cells"],
                "setting": scene["scene_features"]["setting"],
                "town_map": scene["scene_features"]["town_map"],
                "top_attribute_counts": top_hex_counter(
                    Counter(
                        {
                            int(row["value"], 16): int(row["count"])
                            for row in scene["attribute_counts"]
                        }
                    ),
                    8,
                ),
            }
            for scene in top_nonzero_scenes
        ],
    }


def write_markdown(context: dict[str, Any], path: Path) -> None:
    summary = context["summary"]
    lines: list[str] = [
        "# Map Collision Attribute Context",
        "",
        "This context audit counts the third byte of each `.fts` arrangement cell in",
        "actual sector scenes. The byte is still named cautiously: counts can expose",
        "where it appears, but they do not by themselves prove collision semantics.",
        "",
        "## Summary",
        "",
        f"- direct scenes sampled: `{summary['direct_scenes']}`",
        f"- cells per scene: `{summary['cells_per_scene']}`",
        f"- scene cells sampled: `{summary['scene_cells_sampled']}`",
        f"- nonzero attribute cells: `{summary['nonzero_attribute_cells']}`",
        f"- high-bit attribute cells: `{summary['high_bit_attribute_cells']}`",
        "- unique attribute values: "
        + ", ".join(f"`{value}`" for value in summary["unique_attribute_values"]),
        "",
        "## Attribute Counts In Scene Use",
        "",
        "| Value | Cell Count | Scene Presence |",
        "| ---: | ---: | ---: |",
    ]
    scene_presence = {
        row["value"]: row["count"]
        for row in summary["attribute_scene_presence"]
    }
    for row in summary["attribute_counts"]:
        lines.append(f"| `{row['value']}` | {row['count']} | {scene_presence[row['value']]} |")

    lines.extend(
        [
            "",
            "## Top Nonzero Scenes",
            "",
            "| Scene | Sector | Tileset | Palette | Nonzero Cells | High-Bit Cells | Setting | Town Map |",
            "| --- | --- | ---: | ---: | ---: | ---: | --- | --- |",
        ]
    )
    for scene in context["top_nonzero_attribute_scenes"][:16]:
        sector = scene["sector"]
        lines.append(
            f"| `{scene['scene_id']}` | `{sector['x']},{sector['y']}` | "
            f"{scene['tileset_id']} | {scene['palette_id']} | "
            f"{scene['nonzero_attribute_cells']} | {scene['high_bit_attribute_cells']} | "
            f"{scene['setting']} | {scene['town_map']} |"
        )

    lines.extend(
        [
            "",
            "## Strongest Setting Buckets",
            "",
            "| Setting | Scenes | Top Attribute Counts |",
            "| --- | ---: | --- |",
        ]
    )
    setting_rows = sorted(
        context["by_setting"],
        key=lambda row: sum(int(item["count"]) for item in row["top_attribute_counts"]),
        reverse=True,
    )
    for row in setting_rows[:12]:
        counts = ", ".join(
            f"`{item['value']}`:{item['count']}"
            for item in row["top_attribute_counts"][:6]
        )
        lines.append(f"| {row['setting']} | {row['scene_count']} | {counts} |")

    lines.extend(
        [
            "",
            "## Machine-Readable Data",
            "",
            "`notes/map-collision-attribute-context.json` records global counts,",
            "per-tileset counts, scene-presence correlations with coarse scene",
            "features, and the top scenes by nonzero attribute-byte cells.",
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
