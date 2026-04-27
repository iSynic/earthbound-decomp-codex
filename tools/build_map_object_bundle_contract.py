from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SPRITE_USAGE = ROOT / "notes" / "map-sprite-usage-contract.json"
DEFAULT_MOVEMENT_USAGE = ROOT / "notes" / "map-movement-usage-contract.json"
DEFAULT_JSON_OUT = ROOT / "notes" / "map-object-bundles.json"
DEFAULT_MARKDOWN_OUT = ROOT / "notes" / "map-object-bundles.md"
SCHEMA = "earthbound-decomp.map-object-bundles.v1"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Combine map placement visuals, behavior entrypoints, and interaction fields."
    )
    parser.add_argument("--sprite-usage", default=str(DEFAULT_SPRITE_USAGE))
    parser.add_argument("--movement-usage", default=str(DEFAULT_MOVEMENT_USAGE))
    parser.add_argument("--json-out", default=str(DEFAULT_JSON_OUT))
    parser.add_argument("--markdown-out", default=str(DEFAULT_MARKDOWN_OUT))
    return parser.parse_args()


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def top_counts(counter: Counter[Any], limit: int = 10) -> list[dict[str, Any]]:
    return [{"value": value, "count": count} for value, count in counter.most_common(limit)]


def nonzero_pointer(value: Any) -> bool:
    return value not in (None, "$0", "$000000", "0", 0)


def compact_behavior(row: dict[str, Any] | None) -> dict[str, Any]:
    if row is None:
        return {
            "movement_id": None,
            "target_label": None,
            "behavior_bucket": "missing_movement_join",
            "source_status": "missing_movement_join",
            "source_file": None,
        }
    return {
        "movement_id": row["movement_id"],
        "target_label": row["target_label"],
        "behavior_bucket": row["behavior_bucket"],
        "source_status": row["source_status"],
        "source_file": row["source_file"],
        "expected_source_file": row.get("expected_source_file"),
        "event_op_count": row.get("event_op_count"),
    }


def object_row(
    placement: dict[str, Any],
    npc: dict[str, Any],
    movement: dict[str, Any] | None,
) -> dict[str, Any]:
    object_id = f"map_object.{int(placement['placement_index']):04d}"
    return {
        "object_id": object_id,
        "placement_index": placement["placement_index"],
        "npc_id": placement["npc_id"],
        "sector": placement["sector"],
        "position": {
            "sector_x": placement["x"],
            "sector_y": placement["y"],
            "world_pixel_x": placement["world_pixel_x"],
            "world_pixel_y": placement["world_pixel_y"],
        },
        "classification": {
            "npc_type": npc["type"],
            "show_sprite": npc["show_sprite"],
            "initial_direction": npc["direction"],
        },
        "visual": {
            "sprite_id": npc["sprite_id"],
            "sprite_label": npc["sprite_label"],
            "sprite_group": npc["sprite_group"],
            "sprite_enum_name": npc.get("sprite_enum_name"),
            "sprite_palette_id": npc.get("sprite_palette_id"),
            "role_resolution": npc["role_resolution"],
            "sprite_role_model": npc["sprite_role_model"],
            "runtime_slot_count": npc["runtime_slot_count"],
            "resolved_runtime_slots": npc["resolved_runtime_slots"],
        },
        "behavior": compact_behavior(movement),
        "interaction": {
            "event_flag": npc["event_flag"],
            "text_pointer_1": npc["text_pointer_1"],
            "text_pointer_2": npc["text_pointer_2"],
            "has_text_pointer_1": nonzero_pointer(npc["text_pointer_1"]),
            "has_text_pointer_2": nonzero_pointer(npc["text_pointer_2"]),
        },
    }


def summarize_sectors(objects: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_sector: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in objects:
        by_sector[int(row["sector"]["linear_index"])].append(row)
    sectors: list[dict[str, Any]] = []
    for linear_index, rows in sorted(by_sector.items()):
        first = rows[0]["sector"]
        sprite_counter: Counter[str] = Counter(row["visual"]["sprite_label"] for row in rows)
        behavior_counter: Counter[str] = Counter(row["behavior"]["behavior_bucket"] for row in rows)
        type_counter: Counter[str] = Counter(row["classification"]["npc_type"] for row in rows)
        sectors.append(
            {
                "sector": first,
                "object_count": len(rows),
                "object_ids": [row["object_id"] for row in rows],
                "npc_ids": [row["npc_id"] for row in rows],
                "top_sprites": top_counts(sprite_counter, 8),
                "behavior_buckets": top_counts(behavior_counter, 8),
                "npc_types": top_counts(type_counter, 8),
            }
        )
    return sectors


def build_contract(args: argparse.Namespace) -> dict[str, Any]:
    sprite_usage_path = Path(args.sprite_usage)
    movement_usage_path = Path(args.movement_usage)
    sprite_usage = json.loads(sprite_usage_path.read_text(encoding="utf-8"))
    movement_usage = json.loads(movement_usage_path.read_text(encoding="utf-8"))

    npc_by_id = {int(row["npc_id"]): row for row in sprite_usage["npc_configs"]}
    movement_by_id = {int(row["movement_id"]): row for row in movement_usage["movement_usage"]}

    objects: list[dict[str, Any]] = []
    for placement in sprite_usage["placements"]:
        npc = npc_by_id[int(placement["npc_id"])]
        movement = movement_by_id.get(int(npc["movement"]))
        objects.append(object_row(placement, npc, movement))

    placed_npc_ids = {int(row["npc_id"]) for row in sprite_usage["placements"]}
    unplaced_npcs: list[dict[str, Any]] = []
    for npc_id, npc in sorted(npc_by_id.items()):
        if npc_id in placed_npc_ids:
            continue
        movement = movement_by_id.get(int(npc["movement"]))
        unplaced_npcs.append(
            {
                "npc_id": npc_id,
                "npc_type": npc["type"],
                "sprite_id": npc["sprite_id"],
                "sprite_label": npc["sprite_label"],
                "movement": npc["movement"],
                "show_sprite": npc["show_sprite"],
                "event_flag": npc["event_flag"],
                "text_pointer_1": npc["text_pointer_1"],
                "text_pointer_2": npc["text_pointer_2"],
                "behavior": compact_behavior(movement),
            }
        )

    behavior_counter: Counter[str] = Counter(row["behavior"]["behavior_bucket"] for row in objects)
    source_status_counter: Counter[str] = Counter(row["behavior"]["source_status"] for row in objects)
    visual_counter: Counter[str] = Counter(row["visual"]["role_resolution"] for row in objects)
    type_counter: Counter[str] = Counter(row["classification"]["npc_type"] for row in objects)
    show_counter: Counter[str] = Counter(row["classification"]["show_sprite"] for row in objects)
    text_1_count = sum(1 for row in objects if row["interaction"]["has_text_pointer_1"])
    text_2_count = sum(1 for row in objects if row["interaction"]["has_text_pointer_2"])
    event_flag_count = sum(1 for row in objects if int(row["interaction"]["event_flag"]) != 0)
    missing_behavior = [
        row
        for row in objects
        if row["behavior"]["source_status"] != "script_file_present"
    ]
    sectors = summarize_sectors(objects)

    return {
        "schema": SCHEMA,
        "title": "Map Object Bundle Contract",
        "generator": "tools/build_map_object_bundle_contract.py",
        "source_policy": (
            "Derived from checked-in sprite and movement usage contracts. It contains placement, "
            "visual, behavior-entry, and interaction metadata, not extracted ROM asset payloads."
        ),
        "sources": {
            "sprite_usage": rel(sprite_usage_path),
            "movement_usage": rel(movement_usage_path),
        },
        "summary": {
            "npc_config_count": len(sprite_usage["npc_configs"]),
            "placed_object_count": len(objects),
            "unplaced_npc_config_count": len(unplaced_npcs),
            "sectors_with_objects": len(sectors),
            "visual_role_resolution_counts": dict(sorted(visual_counter.items())),
            "behavior_bucket_counts": dict(sorted(behavior_counter.items())),
            "behavior_source_status_counts": dict(sorted(source_status_counter.items())),
            "npc_type_counts": dict(sorted(type_counter.items())),
            "show_sprite_counts": dict(sorted(show_counter.items())),
            "objects_with_event_flags": event_flag_count,
            "objects_with_text_pointer_1": text_1_count,
            "objects_with_text_pointer_2": text_2_count,
            "objects_without_present_behavior_script": len(missing_behavior),
            "top_sectors_by_object_count": [
                {
                    "sector": row["sector"],
                    "object_count": row["object_count"],
                    "top_sprites": row["top_sprites"][:3],
                    "behavior_buckets": row["behavior_buckets"][:3],
                }
                for row in sorted(sectors, key=lambda item: (-item["object_count"], item["sector"]["linear_index"]))[:20]
            ],
            "top_behavior_buckets": top_counts(behavior_counter, 12),
            "top_visual_labels": top_counts(Counter(row["visual"]["sprite_label"] for row in objects), 20),
        },
        "objects": objects,
        "sectors": sectors,
        "unplaced_npc_configs": unplaced_npcs,
    }


def write_markdown(contract: dict[str, Any], path: Path) -> None:
    summary = contract["summary"]
    lines = [
        "# Map Object Bundle Contract",
        "",
        "This contract is the portable placed-object view over the current map-object work.",
        "It combines the visual role contract, movement/actionscript pointer join, map sector",
        "position, event flag, and text pointer fields into one row per placed NPC object.",
        "",
        "## Summary",
        "",
        f"- placed objects: `{summary['placed_object_count']}`",
        f"- NPC config rows: `{summary['npc_config_count']}`",
        f"- unplaced NPC config rows: `{summary['unplaced_npc_config_count']}`",
        f"- sectors with objects: `{summary['sectors_with_objects']}`",
        f"- objects with event flags: `{summary['objects_with_event_flags']}`",
        f"- objects with primary text pointers: `{summary['objects_with_text_pointer_1']}`",
        f"- objects with secondary text pointers: `{summary['objects_with_text_pointer_2']}`",
        f"- objects without present behavior script files in refs: `{summary['objects_without_present_behavior_script']}`",
        "",
        "## Visual Role Resolution",
        "",
        "| Resolution | Objects |",
        "| --- | ---: |",
    ]
    for key, count in summary["visual_role_resolution_counts"].items():
        lines.append(f"| `{key}` | {count} |")

    lines.extend(
        [
            "",
            "## Behavior Source Status",
            "",
            "| Status | Objects |",
            "| --- | ---: |",
        ]
    )
    for key, count in summary["behavior_source_status_counts"].items():
        lines.append(f"| `{key}` | {count} |")

    lines.extend(
        [
            "",
            "## Behavior Buckets",
            "",
            "| Bucket | Objects |",
            "| --- | ---: |",
        ]
    )
    for row in summary["top_behavior_buckets"]:
        lines.append(f"| `{row['value']}` | {row['count']} |")

    lines.extend(
        [
            "",
            "## Top Sectors By Object Count",
            "",
            "| Sector | Objects | Top sprites | Behavior buckets |",
            "| --- | ---: | --- | --- |",
        ]
    )
    for row in summary["top_sectors_by_object_count"]:
        sector = row["sector"]
        sprites = ", ".join(f"{item['value']} ({item['count']})" for item in row["top_sprites"])
        buckets = ", ".join(f"{item['value']} ({item['count']})" for item in row["behavior_buckets"])
        lines.append(
            f"| `{sector['x']},{sector['y']}` | {row['object_count']} | {sprites} | {buckets} |"
        )

    if contract["unplaced_npc_configs"]:
        lines.extend(
            [
                "",
                "## Unplaced NPC Config Rows",
                "",
                "| NPC ID | Sprite | Movement | Behavior |",
                "| ---: | --- | ---: | --- |",
            ]
        )
        for row in contract["unplaced_npc_configs"]:
            lines.append(
                f"| {row['npc_id']} | `{row['sprite_label']}` | {row['movement']} | "
                f"`{row['behavior']['behavior_bucket']}` |"
            )

    lines.extend(
        [
            "",
            "## Machine-Readable Data",
            "",
            "The JSON file records `objects` with stable `map_object.NNNN` IDs and nested",
            "`visual`, `behavior`, `interaction`, `classification`, `sector`, and `position` fields.",
            "The behavior rows intentionally store compact movement IDs and source status; detailed",
            "event macro and C3-reference profiles remain in `notes/map-movement-usage-contract.json`.",
            "It also includes per-sector summaries and unplaced NPC config rows.",
            "",
            "- JSON: `notes/map-object-bundles.json`",
            f"- generator: `{contract['generator']}`",
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
