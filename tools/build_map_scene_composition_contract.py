from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
REFS = ROOT / "refs" / "eb-decompile-4ef92"
DEFAULT_SECTOR_BUNDLES = ROOT / "notes" / "map-sector-bundles.json"
DEFAULT_TILESET_BUNDLES = ROOT / "notes" / "map-tileset-bundles.json"
DEFAULT_FTS_FORMAT_AUDIT = ROOT / "notes" / "map-fts-format-audit.json"
DEFAULT_FTS_ARRANGEMENT_CONTRACT = ROOT / "notes" / "map-fts-arrangement-contract.json"
DEFAULT_FTS_ANIMATION_CONTRACT = ROOT / "notes" / "map-fts-animation-settings-contract.json"
DEFAULT_MAP_TILES = REFS / "map_tiles.map"
DEFAULT_JSON_OUT = ROOT / "notes" / "map-scene-composition-contract.json"
DEFAULT_MARKDOWN_OUT = ROOT / "notes" / "map-scene-composition-contract.md"
SCHEMA = "earthbound-decomp.map-scene-composition-contract.v1"

SECTOR_COLUMNS = 40
SECTOR_ROWS = 32
SECTOR_COUNT = SECTOR_COLUMNS * SECTOR_ROWS
MAP_TILE_GRID_WIDTH = 320
MAP_TILE_GRID_HEIGHT = 256
SECTOR_TILE_WIDTH = 8
SECTOR_TILE_HEIGHT = 8
ARRANGEMENT_RECORD_COUNT = 1024


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Join sector bundles, tileset contracts, and map_tiles.map into scene-composition metadata."
    )
    parser.add_argument("--sector-bundles", default=str(DEFAULT_SECTOR_BUNDLES))
    parser.add_argument("--tileset-bundles", default=str(DEFAULT_TILESET_BUNDLES))
    parser.add_argument("--fts-format-audit", default=str(DEFAULT_FTS_FORMAT_AUDIT))
    parser.add_argument("--fts-arrangement-contract", default=str(DEFAULT_FTS_ARRANGEMENT_CONTRACT))
    parser.add_argument("--fts-animation-contract", default=str(DEFAULT_FTS_ANIMATION_CONTRACT))
    parser.add_argument("--map-tiles", default=str(DEFAULT_MAP_TILES))
    parser.add_argument("--json-out", default=str(DEFAULT_JSON_OUT))
    parser.add_argument("--markdown-out", default=str(DEFAULT_MARKDOWN_OUT))
    return parser.parse_args()


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def sha1_text(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


def sector_id(x: int, y: int) -> int:
    return (x * SECTOR_ROWS) + y


def parse_map_tiles(path: Path) -> list[list[int]]:
    rows: list[list[int]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = [int(item, 16) for item in line.split()]
        rows.append(row)
    if len(rows) != MAP_TILE_GRID_WIDTH:
        raise ValueError(f"{path} has {len(rows)} rows, expected {MAP_TILE_GRID_WIDTH}")
    bad_widths = sorted({len(row) for row in rows})
    if bad_widths != [MAP_TILE_GRID_HEIGHT]:
        raise ValueError(f"{path} row widths are {bad_widths}, expected {[MAP_TILE_GRID_HEIGHT]}")
    return rows


def sector_tile_grid(map_tiles: list[list[int]], sector_x: int, sector_y: int) -> list[list[int]]:
    start_x = sector_x * SECTOR_TILE_WIDTH
    start_y = sector_y * SECTOR_TILE_HEIGHT
    return [
        map_tiles[x][start_y : start_y + SECTOR_TILE_HEIGHT]
        for x in range(start_x, start_x + SECTOR_TILE_WIDTH)
    ]


def canonical_grid_text(grid: list[list[int]]) -> str:
    return "\n".join(" ".join(f"{value:03x}" for value in row) for row in grid)


def top_counts(values: list[int], limit: int = 8) -> list[dict[str, int]]:
    return [
        {"tile_id": value, "count": count}
        for value, count in Counter(values).most_common(limit)
    ]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_contract(args: argparse.Namespace) -> dict[str, Any]:
    sector_bundles_path = Path(args.sector_bundles)
    tileset_bundles_path = Path(args.tileset_bundles)
    fts_format_path = Path(args.fts_format_audit)
    fts_arrangement_path = Path(args.fts_arrangement_contract)
    fts_animation_path = Path(args.fts_animation_contract)
    map_tiles_path = Path(args.map_tiles)

    sector_bundles = load_json(sector_bundles_path)
    tileset_bundles = load_json(tileset_bundles_path)
    fts_format = load_json(fts_format_path)
    fts_arrangement = load_json(fts_arrangement_path)
    fts_animation = load_json(fts_animation_path)
    map_tiles = parse_map_tiles(map_tiles_path)

    tilesets_by_id = {int(row["tileset_id"]): row for row in tileset_bundles["tilesets"]}
    arrangement_by_id = {int(row["tileset_id"]): row for row in fts_arrangement["tilesets"]}
    animation_by_id = {int(row["tileset_id"]): row for row in fts_animation["tilesets"]}

    scenes: list[dict[str, Any]] = []
    used_tile_ids_global: Counter[int] = Counter()
    unresolved_direct_tile_ids: Counter[int] = Counter()
    sector_status_counts: Counter[str] = Counter()
    palette_status_counts: Counter[str] = Counter()

    for sector_row in sorted(sector_bundles["sectors"], key=lambda row: int(row["sector"]["linear_index"])):
        sector = sector_row["sector"]
        linear_index = int(sector["linear_index"])
        sector_x = int(sector["x"])
        sector_y = int(sector["y"])
        metadata = sector_row["metadata"]
        tileset_id = int(metadata["Tileset"])
        palette_id = int(metadata["Palette"])
        tileset = tilesets_by_id[tileset_id]
        arrangement = arrangement_by_id.get(tileset_id)
        animation = animation_by_id.get(tileset_id)
        grid = sector_tile_grid(map_tiles, sector_x, sector_y)
        flat = [value for row in grid for value in row]
        used_tile_ids_global.update(flat)
        unique_ids = sorted(set(flat))
        max_id = max(unique_ids)
        out_of_range_ids = [value for value in unique_ids if value >= ARRANGEMENT_RECORD_COUNT]
        has_direct_fts = bool(tileset["has_direct_fts_export"])
        direct_contract_status = (
            "direct_fts_contracts_present"
            if has_direct_fts and arrangement is not None and animation is not None
            else "palette_settings_only"
            if not has_direct_fts
            else "direct_fts_missing_contract"
        )
        sector_status_counts[direct_contract_status] += 1
        if has_direct_fts:
            unresolved_direct_tile_ids.update(out_of_range_ids)

        palette_variants = {
            int(row["variant"])
            for row in tileset.get("palette_settings", [])
            if row.get("variant") is not None
        }
        palette_status = "palette_variant_present" if palette_id in palette_variants else "palette_variant_missing"
        palette_status_counts[palette_status] += 1
        grid_text = canonical_grid_text(grid)
        scenes.append(
            {
                "scene_id": f"map_scene.{linear_index:04d}",
                "sector": sector,
                "tileset_dependency": {
                    "tileset_bundle_id": tileset["tileset_bundle_id"],
                    "tileset_id": tileset_id,
                    "dependency_status": tileset["dependency_status"],
                    "direct_contract_status": direct_contract_status,
                },
                "palette_dependency": {
                    "palette_id": palette_id,
                    "status": palette_status,
                    "available_variant_count": len(palette_variants),
                },
                "map_tile_grid": {
                    "shape": {"width": SECTOR_TILE_WIDTH, "height": SECTOR_TILE_HEIGHT},
                    "orientation": "map_tiles.map rows are world x columns; each row has world y entries",
                    "source_window": {
                        "x": sector_x * SECTOR_TILE_WIDTH,
                        "y": sector_y * SECTOR_TILE_HEIGHT,
                        "width": SECTOR_TILE_WIDTH,
                        "height": SECTOR_TILE_HEIGHT,
                    },
                    "sha1": sha1_text(grid_text),
                    "unique_tile_id_count": len(unique_ids),
                    "tile_id_min": min(unique_ids),
                    "tile_id_max": max_id,
                    "out_of_arrangement_range_tile_ids": out_of_range_ids,
                    "out_of_arrangement_range_tile_id_count": len(out_of_range_ids),
                },
                "scene_features": {
                    "object_count": len(sector_row["objects"]),
                    "trigger_count": int(sector_row["trigger_count"]),
                    "door_count": int(sector_row["door_count"]),
                    "object_trigger_count": int(sector_row["object_trigger_count"]),
                    "hotspot_count": len(sector_row["hotspot_ids"]),
                    "music_option_count": len(sector_row["music_options"]),
                    "map_change_group_count": int(sector_row["map_change_group_count"]),
                    "enemy_map_group": sector_row["enemy_map_group"],
                    "music": metadata["Music"],
                    "setting": metadata["Setting"],
                    "town_map": metadata["Town Map"],
                },
            }
        )

    used_tileset_ids = {int(scene["tileset_dependency"]["tileset_id"]) for scene in scenes}
    direct_scene_count = sector_status_counts["direct_fts_contracts_present"]
    return {
        "schema": SCHEMA,
        "title": "Map Scene Composition Contract",
        "generator": "tools/build_map_scene_composition_contract.py",
        "source_policy": (
            "Reference-derived scene join. This records dependency IDs, sector-local "
            "map-tile statistics, hashes, and feature counts; it does not commit raw "
            "map tile grids, decoded graphics, or rendered scene payloads."
        ),
        "sources": {
            "sector_bundles": rel(sector_bundles_path),
            "tileset_bundles": rel(tileset_bundles_path),
            "fts_format_audit": rel(fts_format_path),
            "fts_arrangement_contract": rel(fts_arrangement_path),
            "fts_animation_contract": rel(fts_animation_path),
            "map_tiles": rel(map_tiles_path),
        },
        "map_tiles_shape": {
            "world_token_grid_width": MAP_TILE_GRID_WIDTH,
            "world_token_grid_height": MAP_TILE_GRID_HEIGHT,
            "sector_columns": SECTOR_COLUMNS,
            "sector_rows": SECTOR_ROWS,
            "sector_tile_width": SECTOR_TILE_WIDTH,
            "sector_tile_height": SECTOR_TILE_HEIGHT,
            "tokens_per_sector": SECTOR_TILE_WIDTH * SECTOR_TILE_HEIGHT,
            "token_meaning": "sector-local entries reference tileset arrangement/collision records",
        },
        "summary": {
            "sector_count": len(scenes),
            "used_tileset_count": len(used_tileset_ids),
            "scene_dependency_status_counts": dict(sorted(sector_status_counts.items())),
            "palette_status_counts": dict(sorted(palette_status_counts.items())),
            "direct_fts_scene_count": direct_scene_count,
            "palette_settings_only_scene_count": sector_status_counts["palette_settings_only"],
            "global_unique_map_tile_id_count": len(used_tile_ids_global),
            "global_map_tile_id_min": min(used_tile_ids_global),
            "global_map_tile_id_max": max(used_tile_ids_global),
            "direct_fts_out_of_arrangement_range_tile_ids": [
                {"tile_id": value, "scene_count": count}
                for value, count in sorted(unresolved_direct_tile_ids.items())
            ],
            "top_global_map_tile_ids": [
                {"tile_id": value, "count": count}
                for value, count in used_tile_ids_global.most_common(16)
            ],
            "fts_format_components": sorted(fts_format["summary"]["section_totals"].keys()),
            "top_feature_scenes": [
                {
                    "scene_id": scene["scene_id"],
                    "sector": scene["sector"],
                    "tileset": scene["tileset_dependency"]["tileset_id"],
                    "palette": scene["palette_dependency"]["palette_id"],
                    **scene["scene_features"],
                }
                for scene in sorted(
                    scenes,
                    key=lambda row: (
                        -int(row["scene_features"]["object_count"]),
                        -int(row["scene_features"]["trigger_count"]),
                        -int(row["scene_features"]["hotspot_count"]),
                        int(row["sector"]["linear_index"]),
                    ),
                )[:20]
            ],
        },
        "scenes": scenes,
    }


def write_markdown(contract: dict[str, Any], path: Path) -> None:
    summary = contract["summary"]
    shape = contract["map_tiles_shape"]
    status_counts = ", ".join(
        f"`{key}`:{value}" for key, value in summary["scene_dependency_status_counts"].items()
    )
    palette_counts = ", ".join(
        f"`{key}`:{value}" for key, value in summary["palette_status_counts"].items()
    )
    out_of_range = summary["direct_fts_out_of_arrangement_range_tile_ids"]
    lines = [
        "# Map Scene Composition Contract",
        "",
        "This contract joins sector metadata, placed scene features, tileset bundle",
        "dependencies, `.fts` component contracts, palette variants, and sector-local",
        "`map_tiles.map` tile-reference statistics.",
        "",
        "It intentionally does not store the 8x8 tile grids themselves. The JSON keeps",
        "hashes, counts, and dependency status so preview/build tools can regenerate",
        "ROM-derived scene payloads locally.",
        "",
        "## Summary",
        "",
        f"- scenes/sectors: `{summary['sector_count']}`",
        f"- used tilesets: `{summary['used_tileset_count']}`",
        f"- direct `.fts` scenes: `{summary['direct_fts_scene_count']}`",
        f"- palette-settings-only scenes: `{summary['palette_settings_only_scene_count']}`",
        f"- scene dependency status: {status_counts}",
        f"- palette status: {palette_counts}",
        f"- global unique map-tile IDs: `{summary['global_unique_map_tile_id_count']}`",
        f"- global map-tile ID range: `{summary['global_map_tile_id_min']}-{summary['global_map_tile_id_max']}`",
        f"- direct `.fts` out-of-range tile IDs: `{len(out_of_range)}`",
        "",
        "## `map_tiles.map` Shape",
        "",
        f"- world token grid: `{shape['world_token_grid_width']}x{shape['world_token_grid_height']}`",
        f"- sector grid: `{shape['sector_columns']}x{shape['sector_rows']}`",
        f"- sector-local tile-reference grid: `{shape['sector_tile_width']}x{shape['sector_tile_height']}`",
        f"- tokens per sector: `{shape['tokens_per_sector']}`",
        "",
        "Rows in `map_tiles.map` are world `x` columns; each row contains world `y`",
        "entries. A sector at `(x, y)` consumes an 8x8 window starting at `(x*8, y*8)`.",
        "",
        "## Top Feature Scenes",
        "",
        "| Scene | Sector | Tileset | Palette | Objects | Triggers | Hotspots | Music |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in summary["top_feature_scenes"]:
        sector = row["sector"]
        lines.append(
            f"| `{row['scene_id']}` | `{sector['x']},{sector['y']}` | {row['tileset']} | "
            f"{row['palette']} | {row['object_count']} | {row['trigger_count']} | "
            f"{row['hotspot_count']} | {row['music']} |"
        )

    lines.extend(
        [
            "",
            "## Machine-Readable Data",
            "",
            "`notes/map-scene-composition-contract.json` records one row per sector with:",
            "",
            "- stable `map_scene.NNNN` IDs",
            "- tileset and `.fts` component dependency statuses",
            "- palette variant availability",
            "- sector-local `map_tiles.map` window hash and tile-ID statistics",
            "- object/trigger/hotspot/music/enemy-map feature counts",
            "",
            "## Next Refinement",
            "",
            "Use this contract to drive ignored scene previews. The first preview pass can",
            "render each sector's 8x8 arrangement IDs as grayscale blocks, then expand to",
            "real metatile composition using the `.fts` arrangement/collision and tile-pixel",
            "contracts.",
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
