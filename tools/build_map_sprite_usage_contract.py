from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ROLE_CONTRACT = ROOT / "notes" / "overworld-sprite-animation-roles.json"
DEFAULT_NPC_CONFIG = ROOT / "refs" / "eb-decompile-4ef92" / "npc_config_table.yml"
DEFAULT_MAP_SPRITES = ROOT / "refs" / "eb-decompile-4ef92" / "map_sprites.yml"
DEFAULT_SPRITE_GROUPS = ROOT / "refs" / "eb-decompile-4ef92" / "sprite_groups.yml"
DEFAULT_OVERWORLD_SPRITE_ENUM = (
    ROOT / "refs" / "ebsrc-main" / "ebsrc-main" / "include" / "constants" / "overworldsprites.asm"
)
DEFAULT_JSON_OUT = ROOT / "notes" / "map-sprite-usage-contract.json"
DEFAULT_MARKDOWN_OUT = ROOT / "notes" / "map-sprite-usage-contract.md"
SCHEMA = "earthbound-decomp.map-sprite-usage.v1"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Join map sprite placements and NPC configs to overworld sprite animation roles."
    )
    parser.add_argument("--role-contract", default=str(DEFAULT_ROLE_CONTRACT))
    parser.add_argument("--npc-config", default=str(DEFAULT_NPC_CONFIG))
    parser.add_argument("--map-sprites", default=str(DEFAULT_MAP_SPRITES))
    parser.add_argument("--sprite-groups", default=str(DEFAULT_SPRITE_GROUPS))
    parser.add_argument("--overworld-sprite-enum", default=str(DEFAULT_OVERWORLD_SPRITE_ENUM))
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
    return value


def parse_inline_mapping(text: str) -> dict[str, Any]:
    text = text.strip()
    if not text.startswith("{") or not text.endswith("}"):
        raise ValueError(f"Expected inline mapping, got: {text!r}")
    result: dict[str, Any] = {}
    for item in text[1:-1].split(","):
        key, value = item.split(":", 1)
        result[key.strip()] = scalar(value)
    return result


def parse_npc_config_table(path: Path) -> dict[int, dict[str, Any]]:
    configs: dict[int, dict[str, Any]] = {}
    current_id: int | None = None
    current: dict[str, Any] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        id_match = re.fullmatch(r"(\d+):", line)
        if id_match is not None:
            if current_id is not None:
                configs[current_id] = current
            current_id = int(id_match.group(1))
            current = {"npc_id": current_id}
            continue
        field_match = re.fullmatch(r"  ([^:]+):\s*(.+)", line)
        if field_match is not None and current_id is not None:
            current[field_match.group(1)] = scalar(field_match.group(2))
    if current_id is not None:
        configs[current_id] = current
    return configs


def parse_sprite_group_metadata(path: Path) -> dict[int, dict[str, Any]]:
    groups: dict[int, dict[str, Any]] = {}
    current_id: int | None = None
    current: dict[str, Any] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        id_match = re.fullmatch(r"(\d+):", line)
        if id_match is not None:
            if current_id is not None:
                groups[current_id] = current
            current_id = int(id_match.group(1))
            current = {"sprite_id": current_id}
            continue
        field_match = re.fullmatch(r"  ([^:]+):\s*(.+)", line)
        if field_match is not None and current_id is not None:
            current[field_match.group(1)] = scalar(field_match.group(2))
    if current_id is not None:
        groups[current_id] = current
    return groups


def parse_overworld_sprite_enum(path: Path) -> dict[int, str]:
    values: dict[int, str] = {}
    in_enum = False
    next_value = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip() == ".ENUM OVERWORLD_SPRITE":
            in_enum = True
            next_value = 0
            continue
        if in_enum and line.strip() == ".ENDENUM":
            break
        if not in_enum:
            continue
        match = re.match(r"\s*([A-Z0-9_]+)(?:\s*=\s*(\d+))?\s*(?:;(\d+))?", line)
        if match is None:
            continue
        name = match.group(1)
        explicit = match.group(2) or match.group(3)
        value = int(explicit) if explicit is not None else next_value
        values[value] = name
        next_value = value + 1
    return values


def parse_map_sprites(path: Path) -> list[dict[str, Any]]:
    placements: list[dict[str, Any]] = []
    current_sector_x: int | None = None
    current_sector_y: int | None = None
    for line in path.read_text(encoding="utf-8").splitlines():
        sector_x_match = re.fullmatch(r"(\d+):", line)
        if sector_x_match is not None:
            current_sector_x = int(sector_x_match.group(1))
            current_sector_y = None
            continue
        sector_y_match = re.fullmatch(r"  (\d+):(?:\s+null)?", line)
        if sector_y_match is not None:
            current_sector_y = int(sector_y_match.group(1))
            continue
        placement_match = re.fullmatch(r"  - (\{.+\})", line)
        if placement_match is None:
            continue
        if current_sector_x is None or current_sector_y is None:
            raise ValueError(f"Placement without current sector: {line!r}")
        entry = parse_inline_mapping(placement_match.group(1))
        npc_id = int(entry["NPC ID"])
        x = int(entry["X"])
        y = int(entry["Y"])
        placements.append(
            {
                "placement_index": len(placements),
                "sector": {
                    "x": current_sector_x,
                    "y": current_sector_y,
                    "linear_index": (current_sector_x * 32) + current_sector_y,
                },
                "npc_id": npc_id,
                "x": x,
                "y": y,
                "world_pixel_x": (current_sector_x * 256) + x,
                "world_pixel_y": (current_sector_y * 256) + y,
            }
        )
    return placements


def role_lookup(role_contract: dict[str, Any]) -> dict[int, dict[str, Any]]:
    return {int(group["overworld_sprite_id"]): group for group in role_contract["groups"]}


def metadata_role_model(slot_count: int) -> str:
    if slot_count == 0:
        return "empty"
    if slot_count == 16:
        return "two_phase_eight_direction_set"
    if slot_count == 8:
        return "single_phase_eight_direction_set"
    if slot_count == 9:
        return "single_phase_eight_direction_set_plus_extra"
    return "custom_slot_sequence"


def sprite_role_summary(
    sprite_id: int,
    roles: dict[int, dict[str, Any]],
    sprite_group_metadata: dict[int, dict[str, Any]],
    enum_names: dict[int, str],
) -> dict[str, Any]:
    role = roles.get(sprite_id)
    enum_name = enum_names.get(sprite_id)
    if role is not None:
        return {
            "sprite_id": sprite_id,
            "sprite_group": role["label"],
            "sprite_label": role["label"],
            "sprite_enum_name": role["enum_name"],
            "sprite_role_model": role["role_model"]["kind"],
            "sprite_palette_id": role["oam_palette_id"],
            "sprite_group_length": role["runtime_slot_count"],
            "sprite_group_size": None,
            "role_resolution": "full_animation_role_contract",
        }
    metadata = sprite_group_metadata.get(sprite_id)
    if metadata is not None:
        return {
            "sprite_id": sprite_id,
            "sprite_group": None,
            "sprite_label": f"OVERWORLD_SPRITE::{enum_name}" if enum_name else f"OVERWORLD_SPRITE::{sprite_id}",
            "sprite_enum_name": enum_name,
            "sprite_role_model": metadata_role_model(int(metadata.get("Length", 0))),
            "sprite_palette_id": None,
            "sprite_group_length": metadata.get("Length"),
            "sprite_group_size": metadata.get("Size"),
            "role_resolution": "sprite_group_metadata_only",
        }
    return {
        "sprite_id": sprite_id,
        "sprite_group": None,
        "sprite_label": f"OVERWORLD_SPRITE::{enum_name}" if enum_name else None,
        "sprite_enum_name": enum_name,
        "sprite_role_model": None,
        "sprite_palette_id": None,
        "sprite_group_length": None,
        "sprite_group_size": None,
        "role_resolution": "sprite_metadata_missing",
    }


def normalize_config(
    npc_id: int,
    config: dict[str, Any],
    roles: dict[int, dict[str, Any]],
    sprite_group_metadata: dict[int, dict[str, Any]],
    enum_names: dict[int, str],
    placement_count: int,
) -> dict[str, Any]:
    sprite_id = int(config["Sprite"])
    role = sprite_role_summary(sprite_id, roles, sprite_group_metadata, enum_names)
    return {
        "npc_id": npc_id,
        "type": config["Type"],
        "sprite_id": sprite_id,
        "sprite_group": role["sprite_group"],
        "sprite_label": role["sprite_label"],
        "sprite_enum_name": role["sprite_enum_name"],
        "sprite_role_model": role["sprite_role_model"],
        "sprite_palette_id": role["sprite_palette_id"],
        "sprite_group_length": role["sprite_group_length"],
        "sprite_group_size": role["sprite_group_size"],
        "role_resolution": role["role_resolution"],
        "direction": config["Direction"],
        "movement": config["Movement"],
        "show_sprite": config["Show Sprite"],
        "event_flag": config["Event Flag"],
        "text_pointer_1": config["Text Pointer 1"],
        "text_pointer_2": config["Text Pointer 2"],
        "map_placement_count": placement_count,
        "join_status": role["role_resolution"],
    }


def build_document(
    role_contract: dict[str, Any],
    npc_configs: dict[int, dict[str, Any]],
    placements: list[dict[str, Any]],
    sprite_group_metadata: dict[int, dict[str, Any]],
    enum_names: dict[int, str],
    role_contract_path: Path,
    npc_config_path: Path,
    map_sprites_path: Path,
    sprite_groups_path: Path,
    enum_path: Path,
) -> dict[str, Any]:
    roles = role_lookup(role_contract)
    placement_counts_by_npc: Counter[int] = Counter(int(item["npc_id"]) for item in placements)
    placements_by_npc: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for placement in placements:
        placements_by_npc[int(placement["npc_id"])].append(placement)

    npc_rows = [
        normalize_config(
            npc_id,
            npc_configs[npc_id],
            roles,
            sprite_group_metadata,
            enum_names,
            placement_counts_by_npc[npc_id],
        )
        for npc_id in sorted(npc_configs)
    ]

    npc_by_id = {row["npc_id"]: row for row in npc_rows}
    enriched_placements = []
    for placement in placements:
        npc = npc_by_id.get(int(placement["npc_id"]))
        enriched_placements.append(
            {
                **placement,
                "npc_type": npc["type"] if npc is not None else None,
                "sprite_id": npc["sprite_id"] if npc is not None else None,
                "sprite_group": npc["sprite_group"] if npc is not None else None,
                "sprite_label": npc["sprite_label"] if npc is not None else None,
                "sprite_role_model": npc["sprite_role_model"] if npc is not None else None,
                "role_resolution": npc["role_resolution"] if npc is not None else None,
                "initial_direction": npc["direction"] if npc is not None else None,
                "movement": npc["movement"] if npc is not None else None,
                "show_sprite": npc["show_sprite"] if npc is not None else None,
                "join_status": (
                    npc["role_resolution"]
                    if npc is not None
                    else "placement_npc_config_missing"
                ),
            }
        )

    sprite_usage: dict[int, dict[str, Any]] = {}
    for row in npc_rows:
        sprite_id = int(row["sprite_id"])
        usage = sprite_usage.setdefault(
            sprite_id,
            {
                "sprite_id": sprite_id,
                "sprite_group": row["sprite_group"],
                "sprite_label": row["sprite_label"],
                "sprite_enum_name": row["sprite_enum_name"],
                "sprite_role_model": row["sprite_role_model"],
                "sprite_palette_id": row["sprite_palette_id"],
                "sprite_group_length": row["sprite_group_length"],
                "sprite_group_size": row["sprite_group_size"],
                "role_resolution": row["role_resolution"],
                "npc_config_count": 0,
                "map_placement_count": 0,
                "npc_types": Counter(),
                "initial_directions": Counter(),
                "movement_ids": Counter(),
                "example_npc_ids": [],
            },
        )
        usage["npc_config_count"] += 1
        usage["map_placement_count"] += int(row["map_placement_count"])
        usage["npc_types"][str(row["type"])] += 1
        usage["initial_directions"][str(row["direction"])] += 1
        usage["movement_ids"][str(row["movement"])] += 1
        if len(usage["example_npc_ids"]) < 8:
            usage["example_npc_ids"].append(row["npc_id"])

    sprite_usage_rows = []
    for usage in sprite_usage.values():
        sprite_usage_rows.append(
            {
                **{
                    key: value
                    for key, value in usage.items()
                    if key not in {"npc_types", "initial_directions", "movement_ids"}
                },
                "npc_types": dict(sorted(usage["npc_types"].items())),
                "initial_directions": dict(sorted(usage["initial_directions"].items())),
                "movement_ids": dict(sorted(usage["movement_ids"].items())),
                "join_status": (
                    usage["role_resolution"]
                ),
            }
        )
    sprite_usage_rows.sort(key=lambda row: int(row["sprite_id"]))

    type_counts = Counter(str(row["type"]) for row in npc_rows)
    config_join_counts = Counter(str(row["join_status"]) for row in npc_rows)
    placement_join_counts = Counter(str(row["join_status"]) for row in enriched_placements)
    sectors_with_placements = {
        (int(item["sector"]["x"]), int(item["sector"]["y"])) for item in enriched_placements
    }
    placed_npcs = {int(item["npc_id"]) for item in enriched_placements}
    unplaced_npc_count = len(set(npc_configs) - placed_npcs)

    top_sprites = sorted(
        sprite_usage_rows,
        key=lambda row: (-int(row["map_placement_count"]), int(row["sprite_id"])),
    )[:20]

    return {
        "schema": SCHEMA,
        "game": "earthbound-us",
        "title": "Map sprite usage contract",
        "source_policy": {
            "contains_rom_derived_outputs": False,
            "safe_to_commit": True,
        },
        "generator": {
            "tool": "tools/build_map_sprite_usage_contract.py",
        },
        "sources": {
            "role_contract": rel(role_contract_path),
            "npc_config_table": rel(npc_config_path),
            "map_sprites": rel(map_sprites_path),
            "sprite_groups": rel(sprite_groups_path),
            "overworld_sprite_enum": rel(enum_path),
        },
        "references": [
            "refs/eb-decompile-4ef92/npc_config_table.yml",
            "refs/eb-decompile-4ef92/map_sprites.yml",
            "refs/eb-decompile-4ef92/sprite_groups.yml",
            "refs/ebsrc-main/ebsrc-main/include/constants/overworldsprites.asm",
            "refs/ebsrc-main/ebsrc-main/include/structs.asm npc_config",
            "refs/ebsrc-main/ebsrc-main/include/structs.asm sprite_placement",
            "notes/overworld-sprite-animation-roles.json",
            "notes/bank-cf-asset-data-map.md",
        ],
        "summary": {
            "npc_config_count": len(npc_rows),
            "map_placement_count": len(enriched_placements),
            "placed_npc_config_count": len(placed_npcs),
            "unplaced_npc_config_count": unplaced_npc_count,
            "sector_grid": {"columns": 40, "rows": 32, "sector_count": 1280},
            "sectors_with_placements": len(sectors_with_placements),
            "unique_sprite_ids_in_npc_configs": len(sprite_usage_rows),
            "unique_sprite_ids_with_full_animation_roles": sum(
                1 for row in sprite_usage_rows if row["role_resolution"] == "full_animation_role_contract"
            ),
            "unique_sprite_ids_with_metadata_roles": sum(
                1 for row in sprite_usage_rows if row["role_resolution"] == "sprite_group_metadata_only"
            ),
            "npc_config_join_status": dict(sorted(config_join_counts.items())),
            "placement_join_status": dict(sorted(placement_join_counts.items())),
            "npc_type_counts": dict(sorted(type_counts.items())),
            "top_sprites_by_map_placement_count": [
                {
                    "sprite_id": row["sprite_id"],
                    "sprite_label": row["sprite_label"],
                    "role_resolution": row["role_resolution"],
                    "map_placement_count": row["map_placement_count"],
                    "npc_config_count": row["npc_config_count"],
                }
                for row in top_sprites
            ],
        },
        "sprite_usage": sprite_usage_rows,
        "npc_configs": npc_rows,
        "placements": enriched_placements,
    }


def write_json(path: Path, document: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_markdown(path: Path, document: dict[str, Any]) -> None:
    summary = document["summary"]
    lines = [
        "# Map Sprite Usage Contract",
        "",
        "Generated by `tools/build_map_sprite_usage_contract.py`.",
        "",
        "This note summarizes `notes/map-sprite-usage-contract.json`, which joins map sprite placements, NPC configuration rows, and overworld sprite animation roles.",
        "",
        "## Coverage",
        "",
        f"- NPC config rows: {summary['npc_config_count']}",
        f"- Map sprite placements: {summary['map_placement_count']}",
        f"- NPC configs used by map placements: {summary['placed_npc_config_count']}",
        f"- NPC configs not directly placed in `map_sprites.yml`: {summary['unplaced_npc_config_count']}",
        f"- Sectors with placements: {summary['sectors_with_placements']} / {summary['sector_grid']['sector_count']}",
        f"- Unique sprite IDs in NPC configs: {summary['unique_sprite_ids_in_npc_configs']}",
        f"- Unique sprite IDs with full animation roles: {summary['unique_sprite_ids_with_full_animation_roles']}",
        f"- Unique sprite IDs with metadata-only roles: {summary['unique_sprite_ids_with_metadata_roles']}",
        "",
        "## Join Status",
        "",
        "| Scope | Status | Count |",
        "| --- | --- | ---: |",
    ]
    for key, count in summary["npc_config_join_status"].items():
        lines.append(f"| NPC config | `{key}` | {count} |")
    for key, count in summary["placement_join_status"].items():
        lines.append(f"| Placement | `{key}` | {count} |")

    lines.extend(["", "## NPC Types", "", "| Type | Config Rows |", "| --- | ---: |"])
    for key, count in summary["npc_type_counts"].items():
        lines.append(f"| `{key}` | {count} |")

    lines.extend(
        [
            "",
            "## Top Sprites By Map Placement Count",
            "",
            "| Sprite ID | Sprite Label | Resolution | Placements | NPC Configs |",
            "| ---: | --- | --- | ---: | ---: |",
        ]
    )
    for row in summary["top_sprites_by_map_placement_count"]:
        label = row["sprite_label"] or "unresolved"
        lines.append(
            f"| {row['sprite_id']} | `{label}` | `{row['role_resolution']}` | {row['map_placement_count']} | {row['npc_config_count']} |"
        )

    lines.extend(
        [
            "",
            "## Interpretation Rules",
            "",
            "- `npc_configs` are keyed by the `npc_config` table index referenced by map placements.",
            "- `placements` preserve the 40x32 sector grid from `map_sprites.yml`; `world_pixel_x/y` are sector-local coordinates expanded by 256 pixels per sector.",
            "- `sprite_usage` is the compact join table ports and editors should consult first when asking which map objects use a sprite group.",
            "- `full_animation_role_contract` rows have resolved payload/slot/palette roles from `notes/overworld-sprite-animation-roles.json`.",
            "- `sprite_group_metadata_only` rows fall back to `sprite_groups.yml` length/size metadata and the `OVERWORLD_SPRITE` enum name; these still need payload-level joins.",
            "- The source refs are not committed runtime assets. This contract preserves their semantic join so future ROM-backed tools can reproduce or replace the reference import.",
            "",
            "## Next Step",
            "",
            "Use this join to connect movement IDs and event script pointers to placed objects, so map editing can reason about visuals, movement, and behavior together.",
        ]
    )

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    role_contract_path = Path(args.role_contract)
    npc_config_path = Path(args.npc_config)
    map_sprites_path = Path(args.map_sprites)
    sprite_groups_path = Path(args.sprite_groups)
    enum_path = Path(args.overworld_sprite_enum)
    role_contract = json.loads(role_contract_path.read_text(encoding="utf-8"))
    npc_configs = parse_npc_config_table(npc_config_path)
    placements = parse_map_sprites(map_sprites_path)
    sprite_group_metadata = parse_sprite_group_metadata(sprite_groups_path)
    enum_names = parse_overworld_sprite_enum(enum_path)
    document = build_document(
        role_contract,
        npc_configs,
        placements,
        sprite_group_metadata,
        enum_names,
        role_contract_path,
        npc_config_path,
        map_sprites_path,
        sprite_groups_path,
        enum_path,
    )
    write_json(Path(args.json_out), document)
    write_markdown(Path(args.markdown_out), document)
    print(
        "Built map sprite usage contract: "
        f"{document['summary']['npc_config_count']} NPC configs, "
        f"{document['summary']['map_placement_count']} placements, "
        f"{document['summary']['unique_sprite_ids_with_full_animation_roles']} full sprite-role IDs."
    )
    print(f"Wrote {rel(Path(args.json_out))}")
    print(f"Wrote {rel(Path(args.markdown_out))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
