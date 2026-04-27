from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
REFS = ROOT / "refs" / "eb-decompile-4ef92"
DEFAULT_OBJECT_BUNDLES = ROOT / "notes" / "map-object-bundles.json"
DEFAULT_MAP_SECTORS = REFS / "map_sectors.yml"
DEFAULT_MAP_DOORS = REFS / "map_doors.yml"
DEFAULT_MAP_ENEMY_PLACEMENT = REFS / "map_enemy_placement.yml"
DEFAULT_MAP_MUSIC = REFS / "map_music.yml"
DEFAULT_MAP_HOTSPOTS = REFS / "map_hotspots.yml"
DEFAULT_MAP_CHANGES = REFS / "map_changes.yml"
DEFAULT_MAP_TILES = REFS / "map_tiles.map"
DEFAULT_JSON_OUT = ROOT / "notes" / "map-sector-bundles.json"
DEFAULT_MARKDOWN_OUT = ROOT / "notes" / "map-sector-bundles.md"
SCHEMA = "earthbound-decomp.map-sector-bundles.v1"
SECTOR_COLUMNS = 40
SECTOR_ROWS = 32
SECTOR_COUNT = SECTOR_COLUMNS * SECTOR_ROWS
SECTOR_TILE_WIDTH = 32
SECTOR_TILE_HEIGHT = 32
MAP_TILE_BLOCK_BYTES = 256


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a first-pass scene/sector bundle contract from map refs and object bundles."
    )
    parser.add_argument("--object-bundles", default=str(DEFAULT_OBJECT_BUNDLES))
    parser.add_argument("--map-sectors", default=str(DEFAULT_MAP_SECTORS))
    parser.add_argument("--map-doors", default=str(DEFAULT_MAP_DOORS))
    parser.add_argument("--map-enemy-placement", default=str(DEFAULT_MAP_ENEMY_PLACEMENT))
    parser.add_argument("--map-music", default=str(DEFAULT_MAP_MUSIC))
    parser.add_argument("--map-hotspots", default=str(DEFAULT_MAP_HOTSPOTS))
    parser.add_argument("--map-changes", default=str(DEFAULT_MAP_CHANGES))
    parser.add_argument("--map-tiles", default=str(DEFAULT_MAP_TILES))
    parser.add_argument("--json-out", default=str(DEFAULT_JSON_OUT))
    parser.add_argument("--markdown-out", default=str(DEFAULT_MARKDOWN_OUT))
    return parser.parse_args()


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def scalar(value: str) -> Any:
    value = value.strip()
    if value == "null":
        return None
    if re.fullmatch(r"0x[0-9A-Fa-f]+", value):
        return int(value, 16)
    if re.fullmatch(r"-?\d+", value):
        return int(value)
    if value.startswith("$") and re.fullmatch(r"\$[0-9A-Fa-f]+", value):
        return value.lower()
    return value


def parse_inline_mapping(text: str) -> dict[str, Any]:
    text = text.strip()
    if not text.startswith("{") or not text.endswith("}"):
        raise ValueError(f"Expected inline mapping, got {text!r}")
    result: dict[str, Any] = {}
    for item in text[1:-1].split(","):
        key, value = item.split(":", 1)
        result[key.strip()] = scalar(value)
    return result


def sector_id(x: int, y: int) -> int:
    return (x * SECTOR_ROWS) + y


def sector_coords(linear_index: int) -> dict[str, int]:
    return {
        "linear_index": linear_index,
        "x": linear_index // SECTOR_ROWS,
        "y": linear_index % SECTOR_ROWS,
    }


def parse_simple_top_level_records(path: Path) -> dict[int, dict[str, Any]]:
    records: dict[int, dict[str, Any]] = {}
    current_id: int | None = None
    current: dict[str, Any] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        id_match = re.fullmatch(r"(\d+):", line)
        if id_match is not None:
            if current_id is not None:
                records[current_id] = current
            current_id = int(id_match.group(1))
            current = {}
            continue
        field_match = re.fullmatch(r"  ([^:]+):\s*(.+)", line)
        if field_match is not None and current_id is not None:
            current[field_match.group(1)] = scalar(field_match.group(2))
    if current_id is not None:
        records[current_id] = current
    return records


def parse_doors(path: Path) -> dict[int, list[dict[str, Any]]]:
    by_sector: dict[int, list[dict[str, Any]]] = defaultdict(list)
    current_x: int | None = None
    current_y: int | None = None
    current_entry: dict[str, Any] | None = None

    def finish_entry() -> None:
        nonlocal current_entry
        if current_entry is None:
            return
        if current_x is None or current_y is None:
            raise ValueError("Door entry without sector coordinates")
        current_entry["door_index"] = sum(len(rows) for rows in by_sector.values())
        current_entry["sector"] = sector_coords(sector_id(current_x, current_y))
        by_sector[sector_id(current_x, current_y)].append(current_entry)
        current_entry = None

    for line in path.read_text(encoding="utf-8").splitlines():
        x_match = re.fullmatch(r"(\d+):", line)
        if x_match is not None:
            finish_entry()
            current_x = int(x_match.group(1))
            current_y = None
            continue
        y_match = re.fullmatch(r"  (\d+):(?:\s+null)?", line)
        if y_match is not None:
            finish_entry()
            current_y = int(y_match.group(1))
            continue
        item_match = re.fullmatch(r"  - ([^:]+):\s*(.+)", line)
        if item_match is not None:
            finish_entry()
            current_entry = {item_match.group(1): scalar(item_match.group(2))}
            continue
        field_match = re.fullmatch(r"    ([^:]+):\s*(.+)", line)
        if field_match is not None and current_entry is not None:
            current_entry[field_match.group(1)] = scalar(field_match.group(2))
    finish_entry()
    return dict(by_sector)


def parse_top_level_list_records(path: Path) -> dict[int, list[dict[str, Any]]]:
    records: dict[int, list[dict[str, Any]]] = defaultdict(list)
    current_id: int | None = None
    current_entry: dict[str, Any] | None = None

    def finish_entry() -> None:
        nonlocal current_entry
        if current_id is not None and current_entry is not None:
            records[current_id].append(current_entry)
        current_entry = None

    for line in path.read_text(encoding="utf-8").splitlines():
        id_match = re.fullmatch(r"(\d+):(?:\s+\[\])?", line)
        if id_match is not None:
            finish_entry()
            current_id = int(id_match.group(1))
            if line.strip().endswith("[]"):
                records[current_id] = []
            continue
        item_match = re.fullmatch(r"- ([^:]+):\s*(.+)", line)
        if item_match is not None:
            finish_entry()
            current_entry = {item_match.group(1): scalar(item_match.group(2))}
            continue
        field_match = re.fullmatch(r"  ([^:]+):\s*(.+)", line)
        if field_match is not None and current_entry is not None:
            current_entry[field_match.group(1)] = scalar(field_match.group(2))
    finish_entry()
    return dict(records)


def parse_hotspots(path: Path) -> list[dict[str, Any]]:
    raw = parse_simple_top_level_records(path)
    hotspots: list[dict[str, Any]] = []
    for hotspot_id, row in sorted(raw.items()):
        x1 = int(row["X1"])
        x2 = int(row["X2"])
        y1 = int(row["Y1"])
        y2 = int(row["Y2"])
        min_sector_x = max(0, min(x1, x2) // SECTOR_TILE_WIDTH)
        max_sector_x = min(SECTOR_COLUMNS - 1, max(x1, x2) // SECTOR_TILE_WIDTH)
        min_sector_y = max(0, min(y1, y2) // SECTOR_TILE_HEIGHT)
        max_sector_y = min(SECTOR_ROWS - 1, max(y1, y2) // SECTOR_TILE_HEIGHT)
        sector_ids = [
            sector_id(x, y)
            for x in range(min_sector_x, max_sector_x + 1)
            for y in range(min_sector_y, max_sector_y + 1)
        ]
        hotspots.append(
            {
                "hotspot_id": hotspot_id,
                "bounds": {"x1": x1, "x2": x2, "y1": y1, "y2": y2},
                "sector_ids": sector_ids,
            }
        )
    return hotspots


def parse_map_change_counts(path: Path) -> dict[int, int]:
    counts: dict[int, int] = {}
    current_id: int | None = None
    current_count = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        id_match = re.fullmatch(r"(\d+):(?:\s+\[\])?", line)
        if id_match is not None:
            if current_id is not None:
                counts[current_id] = current_count
            current_id = int(id_match.group(1))
            current_count = 0
            continue
        if re.fullmatch(r"- Event Flag:\s*.+", line):
            current_count += 1
    if current_id is not None:
        counts[current_id] = current_count
    return counts


def map_tile_blocks(path: Path) -> dict[int, dict[str, Any]]:
    data = path.read_bytes()
    blocks: dict[int, dict[str, Any]] = {}
    for linear_index in range(SECTOR_COUNT):
        start = linear_index * MAP_TILE_BLOCK_BYTES
        end = start + MAP_TILE_BLOCK_BYTES
        block = data[start:end]
        blocks[linear_index] = {
            "source_range": f"{rel(path)}:{start:#x}..{end:#x}",
            "byte_count": len(block),
            "sha1": hashlib.sha1(block).hexdigest(),
            "unique_byte_count": len(set(block)),
        }
    return blocks


def build_contract(args: argparse.Namespace) -> dict[str, Any]:
    object_bundles_path = Path(args.object_bundles)
    map_sectors_path = Path(args.map_sectors)
    map_doors_path = Path(args.map_doors)
    map_enemy_placement_path = Path(args.map_enemy_placement)
    map_music_path = Path(args.map_music)
    map_hotspots_path = Path(args.map_hotspots)
    map_changes_path = Path(args.map_changes)
    map_tiles_path = Path(args.map_tiles)

    object_bundles = json.loads(object_bundles_path.read_text(encoding="utf-8"))
    object_sector_map: dict[int, list[str]] = defaultdict(list)
    for row in object_bundles["objects"]:
        object_sector_map[int(row["sector"]["linear_index"])].append(str(row["object_id"]))

    sectors = parse_simple_top_level_records(map_sectors_path)
    doors_by_sector = parse_doors(map_doors_path)
    enemy_placement = parse_simple_top_level_records(map_enemy_placement_path)
    music_by_sector = parse_top_level_list_records(map_music_path)
    hotspots = parse_hotspots(map_hotspots_path)
    hotspots_by_sector: dict[int, list[int]] = defaultdict(list)
    for hotspot in hotspots:
        for index in hotspot["sector_ids"]:
            hotspots_by_sector[index].append(int(hotspot["hotspot_id"]))
    map_change_counts = parse_map_change_counts(map_changes_path)
    tile_blocks = map_tile_blocks(map_tiles_path)

    rows: list[dict[str, Any]] = []
    for linear_index in range(SECTOR_COUNT):
        sector = sector_coords(linear_index)
        metadata = sectors.get(linear_index, {})
        tileset = metadata.get("Tileset")
        doors = doors_by_sector.get(linear_index, [])
        door_count = sum(1 for row in doors if row.get("Type") == "door")
        object_trigger_count = sum(1 for row in doors if row.get("Type") == "object")
        trigger_type_counter = Counter(str(row.get("Type")) for row in doors)
        rows.append(
            {
                "sector": sector,
                "metadata": metadata,
                "map_tile_block": tile_blocks[linear_index],
                "objects": object_sector_map.get(linear_index, []),
                "doors": doors,
                "trigger_count": len(doors),
                "trigger_type_counts": dict(sorted(trigger_type_counter.items())),
                "door_count": door_count,
                "object_trigger_count": object_trigger_count,
                "hotspot_ids": hotspots_by_sector.get(linear_index, []),
                "enemy_map_group": enemy_placement.get(linear_index, {}).get("Enemy Map Group"),
                "music_options": music_by_sector.get(linear_index, []),
                "map_change_group_count": map_change_counts.get(int(tileset), 0) if tileset is not None else 0,
            }
        )

    tileset_counter = Counter(row["metadata"].get("Tileset") for row in rows)
    palette_counter = Counter(row["metadata"].get("Palette") for row in rows)
    music_counter = Counter(row["metadata"].get("Music") for row in rows)
    town_map_counter = Counter(row["metadata"].get("Town Map") for row in rows)
    enemy_group_counter = Counter(row["enemy_map_group"] for row in rows)
    sectors_with_doors = sum(1 for row in rows if row["door_count"])
    sectors_with_trigger_records = sum(1 for row in rows if row["trigger_count"])
    sectors_with_object_triggers = sum(1 for row in rows if row["object_trigger_count"])
    sectors_with_hotspots = sum(1 for row in rows if row["hotspot_ids"])
    sectors_with_enemy_groups = sum(1 for row in rows if row["enemy_map_group"])
    sectors_with_music_overrides = sum(1 for row in rows if row["music_options"])
    sectors_with_map_changes = sum(1 for row in rows if row["map_change_group_count"])

    return {
        "schema": SCHEMA,
        "title": "Map Sector Bundle Contract",
        "generator": "tools/build_map_sector_bundle_contract.py",
        "source_policy": (
            "Reference-derived sector/world join. Raw map tile bytes stay in ignored refs; "
            "this contract records per-sector hashes and metadata, not copied tile payloads."
        ),
        "sources": {
            "object_bundles": rel(object_bundles_path),
            "map_sectors": rel(map_sectors_path),
            "map_doors": rel(map_doors_path),
            "map_enemy_placement": rel(map_enemy_placement_path),
            "map_music": rel(map_music_path),
            "map_hotspots": rel(map_hotspots_path),
            "map_changes": rel(map_changes_path),
            "map_tiles": rel(map_tiles_path),
        },
        "summary": {
            "sector_grid": {"columns": SECTOR_COLUMNS, "rows": SECTOR_ROWS, "sector_count": SECTOR_COUNT},
            "sectors_with_placed_objects": len(object_sector_map),
            "placed_object_count": len(object_bundles["objects"]),
            "door_record_count": sum(len(rows) for rows in doors_by_sector.values()),
            "trigger_type_counts": dict(
                sorted(Counter(str(door.get("Type")) for sector_doors in doors_by_sector.values() for door in sector_doors).items())
            ),
            "door_count": sum(row["door_count"] for row in rows),
            "object_trigger_count": sum(row["object_trigger_count"] for row in rows),
            "sectors_with_trigger_records": sectors_with_trigger_records,
            "sectors_with_doors": sectors_with_doors,
            "sectors_with_object_triggers": sectors_with_object_triggers,
            "hotspot_count": len(hotspots),
            "sectors_overlapped_by_hotspots": sectors_with_hotspots,
            "sectors_with_enemy_groups": sectors_with_enemy_groups,
            "sectors_with_music_overrides": sectors_with_music_overrides,
            "sectors_with_map_change_groups": sectors_with_map_changes,
            "unique_tilesets": len(tileset_counter),
            "unique_palettes": len(palette_counter),
            "unique_music_ids": len(music_counter),
            "unique_town_maps": len(town_map_counter),
            "unique_enemy_map_groups": len(enemy_group_counter),
            "top_tilesets": [{"tileset": key, "sector_count": count} for key, count in tileset_counter.most_common(20)],
            "top_palettes": [{"palette": key, "sector_count": count} for key, count in palette_counter.most_common(12)],
            "top_music_ids": [{"music": key, "sector_count": count} for key, count in music_counter.most_common(12)],
            "top_enemy_map_groups": [
                {"enemy_map_group": key, "sector_count": count} for key, count in enemy_group_counter.most_common(12)
            ],
            "top_sectors_by_scene_features": [
                {
                    "sector": row["sector"],
                    "object_count": len(row["objects"]),
                    "trigger_count": row["trigger_count"],
                    "door_count": row["door_count"],
                    "object_trigger_count": row["object_trigger_count"],
                    "hotspot_count": len(row["hotspot_ids"]),
                    "music_option_count": len(row["music_options"]),
                    "tileset": row["metadata"].get("Tileset"),
                    "palette": row["metadata"].get("Palette"),
                }
                for row in sorted(
                    rows,
                    key=lambda item: (
                        -(
                            len(item["objects"])
                            + item["trigger_count"]
                            + item["door_count"]
                            + item["object_trigger_count"]
                            + len(item["hotspot_ids"])
                            + len(item["music_options"])
                        ),
                        item["sector"]["linear_index"],
                    ),
                )[:20]
            ],
        },
        "sectors": rows,
        "hotspots": hotspots,
    }


def write_markdown(contract: dict[str, Any], path: Path) -> None:
    summary = contract["summary"]
    grid = summary["sector_grid"]
    lines = [
        "# Map Sector Bundle Contract",
        "",
        "This first-pass sector contract joins the 40x32 world-sector grid to placed",
        "objects, sector metadata, door/rope/ladder/object trigger refs, enemy-map groups, music",
        "options, hotspots, map-change group counts, and per-sector `map_tiles.map` hashes.",
        "",
        "It does not yet decode map graphics, arrangements, palettes, or collision into",
        "engine-ready scene assets. It establishes the scene inventory layer that those",
        "decoders can attach to next.",
        "",
        "## Summary",
        "",
        f"- sector grid: `{grid['columns']}x{grid['rows']}` = `{grid['sector_count']}` sectors",
        f"- sectors with placed objects: `{summary['sectors_with_placed_objects']}`",
        f"- placed objects: `{summary['placed_object_count']}`",
        f"- trigger records: `{summary['door_record_count']}` across `{summary['sectors_with_trigger_records']}` sectors",
        f"- doors: `{summary['door_count']}` across `{summary['sectors_with_doors']}` sectors",
        f"- object triggers: `{summary['object_trigger_count']}` across `{summary['sectors_with_object_triggers']}` sectors",
        f"- hotspots: `{summary['hotspot_count']}` overlapping `{summary['sectors_overlapped_by_hotspots']}` sectors",
        f"- sectors with nonzero enemy-map groups: `{summary['sectors_with_enemy_groups']}`",
        f"- sectors with music override lists: `{summary['sectors_with_music_overrides']}`",
        f"- sectors whose tileset has map-change groups: `{summary['sectors_with_map_change_groups']}`",
        f"- unique tilesets: `{summary['unique_tilesets']}`",
        f"- unique palettes: `{summary['unique_palettes']}`",
        f"- unique music IDs: `{summary['unique_music_ids']}`",
        f"- unique town map labels: `{summary['unique_town_maps']}`",
        f"- unique enemy-map groups: `{summary['unique_enemy_map_groups']}`",
        "",
        "## Trigger Types",
        "",
        "| Type | Records |",
        "| --- | ---: |",
    ]
    for trigger_type, count in summary["trigger_type_counts"].items():
        lines.append(f"| `{trigger_type}` | {count} |")

    lines.extend(
        [
            "",
            "## Top Tilesets",
            "",
            "| Tileset | Sectors |",
            "| ---: | ---: |",
        ]
    )
    for row in summary["top_tilesets"]:
        lines.append(f"| {row['tileset']} | {row['sector_count']} |")

    lines.extend(
        [
            "",
            "## Top Scene-Feature Sectors",
            "",
            "| Sector | Objects | Triggers | Doors | Object triggers | Hotspots | Music options | Tileset | Palette |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in summary["top_sectors_by_scene_features"]:
        sector = row["sector"]
        lines.append(
            f"| `{sector['x']},{sector['y']}` | {row['object_count']} | {row['trigger_count']} | "
            f"{row['door_count']} | {row['object_trigger_count']} | {row['hotspot_count']} | {row['music_option_count']} | "
            f"{row['tileset']} | {row['palette']} |"
        )

    lines.extend(
        [
            "",
            "## Machine-Readable Data",
            "",
            "`notes/map-sector-bundles.json` records one row per sector with:",
            "",
            "- `metadata` from `map_sectors.yml`",
            "- `objects` as stable IDs from `notes/map-object-bundles.json`",
            "- `doors` from `map_doors.yml`",
            "- `enemy_map_group` from `map_enemy_placement.yml`",
            "- `music_options` from `map_music.yml`",
            "- `hotspot_ids` by world tile-coordinate overlap",
            "- `map_change_group_count` keyed by sector tileset",
            "- `map_tile_block` hash/byte-count metadata for the sector slice in `map_tiles.map`",
            "",
            "## Next Refinement",
            "",
            "Attach real decoder outputs to each sector: tileset graphics, arrangements, palettes,",
            "collision, and door/warp destination bundles. The current contract gives those",
            "decoders a stable sector key and scene inventory to attach to.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    contract = build_contract(args)
    json_out = Path(args.json_out)
    markdown_out = Path(args.markdown_out)
    contract["sources"]["json_out"] = rel(json_out)
    json_out.write_text(json.dumps(contract, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_markdown(contract, markdown_out)


if __name__ == "__main__":
    main()
