#!/usr/bin/env python3
"""Build natural C2 PP resource-action probe candidates from enemy/action data."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError as exc:  # pragma: no cover - developer setup guard
    raise SystemExit("PyYAML is required to read eb-decompile YAML refs") from exc


ROOT = Path(__file__).resolve().parent.parent
REFS = ROOT / "refs" / "eb-decompile-4ef92"
DEFAULT_OUTPUT = ROOT / "manifests" / "c2-resource-amount-natural-candidates.json"
DEFAULT_NOTES = ROOT / "notes" / "c2-resource-amount-natural-candidates.md"
ACTION_ROWS = {
    54: {
        "lane": "psi_magnet_transfer",
        "routine": "C2:9F5E",
        "expected_contract": "target PP decreases and active row recovers the same capped amount",
    },
    95: {
        "lane": "pp_reduction_loss_only",
        "routine": "C2:8E42",
        "expected_contract": "target PP decreases without active-row PP recovery",
    },
}
ACTION_FIELDS = (
    ("Action 1", "Action 1 Argument"),
    ("Action 2", "Action 2 Argument"),
    ("Action 3", "Action 3 Argument"),
    ("Action 4", "Action 4 Argument"),
    ("Final Action", "Final Action Argument"),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--notes", default=str(DEFAULT_NOTES))
    return parser.parse_args()


def load_yaml(path: Path) -> dict[int, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"unexpected YAML shape: {path}")
    return {int(key): value for key, value in payload.items()}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def manifest_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def index_enemy_groups(enemy_groups: dict[int, Any]) -> dict[int, list[dict[str, Any]]]:
    by_enemy: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for group_id, group in enemy_groups.items():
        for entry in group.get("Enemies", []) or []:
            enemy_id = int(entry.get("Enemy"))
            by_enemy[enemy_id].append(
                {
                    "enemy_group": group_id,
                    "amount": int(entry.get("Amount", 0)),
                    "background_1": group.get("Background 1"),
                    "background_2": group.get("Background 2"),
                }
            )
    return dict(by_enemy)


def index_map_groups(map_enemy_groups: dict[int, Any]) -> dict[int, list[dict[str, Any]]]:
    by_enemy_group: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for map_group_id, map_group in map_enemy_groups.items():
        for subgroup_name in ("Sub-Group 1", "Sub-Group 2"):
            subgroup = map_group.get(subgroup_name) or {}
            for entry_index, entry in subgroup.items():
                enemy_group = int(entry.get("Enemy Group"))
                by_enemy_group[enemy_group].append(
                    {
                        "map_enemy_group": map_group_id,
                        "subgroup": subgroup_name,
                        "entry": int(entry_index),
                        "probability": int(entry.get("Probability", 0)),
                        "subgroup_rate": int(map_group.get(f"{subgroup_name} Rate", 0)),
                        "event_flag": str(map_group.get("Event Flag", "0x0")),
                    }
                )
    return dict(by_enemy_group)


def index_placements(map_enemy_placement: dict[int, Any]) -> dict[int, list[int]]:
    by_map_group: dict[int, list[int]] = defaultdict(list)
    for sector, row in map_enemy_placement.items():
        by_map_group[int(row.get("Enemy Map Group", 0))].append(sector)
    return dict(by_map_group)


def row_by_id(crosswalk: dict[str, Any]) -> dict[int, dict[str, Any]]:
    return {int(row["row"]): row for row in crosswalk.get("rows", [])}


def slot_records(enemy: dict[str, Any]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for slot_index, (action_field, argument_field) in enumerate(ACTION_FIELDS, start=1):
        action = int(enemy.get(action_field, 0) or 0)
        if action not in ACTION_ROWS:
            continue
        records.append(
            {
                "slot": action_field,
                "slot_index": slot_index,
                "action_row": action,
                "argument": int(enemy.get(argument_field, 0) or 0),
                "is_final_action": action_field == "Final Action",
            }
        )
    return records


def probe_rank(slot: dict[str, Any], enemy: dict[str, Any], lane: str) -> int:
    rank = 0
    if lane == "psi_magnet_transfer" and int(enemy.get("PP", 0) or 0) > 0:
        rank += 3
    if not slot["is_final_action"]:
        rank += 3
    rank += max(0, 5 - int(slot["slot_index"]))
    if int(enemy.get("Speed", 0) or 0) >= 20:
        rank += 1
    if int(enemy.get("HP", 0) or 0) >= 100:
        rank += 1
    return rank


def build_candidates(
    enemies: dict[int, Any],
    enemy_groups: dict[int, list[dict[str, Any]]],
    map_group_refs: dict[int, list[dict[str, Any]]],
    placements: dict[int, list[int]],
    action_rows: dict[int, dict[str, Any]],
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for enemy_id, enemy in enemies.items():
        for slot in slot_records(enemy):
            action = ACTION_ROWS[slot["action_row"]]
            lane = action["lane"]
            groups = enemy_groups.get(enemy_id, [])
            map_refs: list[dict[str, Any]] = []
            placement_sectors: set[int] = set()
            for group in groups:
                refs = map_group_refs.get(int(group["enemy_group"]), [])
                map_refs.extend(refs[:4])
                for ref in refs:
                    placement_sectors.update(placements.get(int(ref["map_enemy_group"]), [])[:8])
            action_row = action_rows.get(slot["action_row"], {})
            target = (action_row.get("target") or {}).get("name", "unknown")
            direction = (action_row.get("direction") or {}).get("name", "unknown")
            candidates.append(
                {
                    "lane": lane,
                    "routine": action["routine"],
                    "action_row": slot["action_row"],
                    "action_slot": slot["slot"],
                    "action_slot_index": slot["slot_index"],
                    "action_argument": slot["argument"],
                    "enemy_id": enemy_id,
                    "enemy_name": str(enemy.get("Name", "")),
                    "enemy_hp": int(enemy.get("HP", 0) or 0),
                    "enemy_pp": int(enemy.get("PP", 0) or 0),
                    "enemy_speed": int(enemy.get("Speed", 0) or 0),
                    "enemy_action_order": int(enemy.get("Action Order", 0) or 0),
                    "battle_action_direction": direction,
                    "battle_action_target": target,
                    "expected_contract": action["expected_contract"],
                    "enemy_groups": groups[:8],
                    "enemy_group_count": len(groups),
                    "map_group_refs": map_refs[:8],
                    "map_group_ref_count": len(map_refs),
                    "placement_sector_samples": sorted(placement_sectors)[:16],
                    "placement_sector_count": len(placement_sectors),
                    "probe_rank": probe_rank(slot, enemy, lane),
                    "promotion_gate": "natural unpatched trace with nonzero target PP and post-call PP deltas",
                }
            )
    return sorted(candidates, key=lambda row: (-int(row["probe_rank"]), row["lane"], row["enemy_id"], row["action_slot_index"]))


def summarize(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    by_lane: dict[str, int] = defaultdict(int)
    for candidate in candidates:
        by_lane[str(candidate["lane"])] += 1
    return {
        "candidate_count": len(candidates),
        "lanes": dict(sorted(by_lane.items())),
        "top_candidates": [
            {
                "lane": row["lane"],
                "enemy_id": row["enemy_id"],
                "enemy_name": row["enemy_name"],
                "action_row": row["action_row"],
                "action_slot": row["action_slot"],
                "enemy_pp": row["enemy_pp"],
                "probe_rank": row["probe_rank"],
            }
            for row in candidates[:8]
        ],
    }


def render_table(rows: list[dict[str, Any]]) -> list[str]:
    lines = [
        "| Rank | Lane | Enemy | Action | Slot | Enemy PP | Groups | Map sectors | Probe gate |",
        "| ---: | --- | --- | ---: | --- | ---: | ---: | ---: | --- |",
    ]
    for row in rows:
        lines.append(
            "| `{rank}` | `{lane}` | `{enemy_id}` {enemy_name} | `{action_row}` | `{slot}` | `{enemy_pp}` | `{groups}` | `{sectors}` | {gate} |".format(
                rank=row["probe_rank"],
                lane=row["lane"],
                enemy_id=row["enemy_id"],
                enemy_name=row["enemy_name"].replace("|", "\\|"),
                action_row=row["action_row"],
                slot=row["action_slot"],
                enemy_pp=row["enemy_pp"],
                groups=row["enemy_group_count"],
                sectors=row["placement_sector_count"],
                gate=row["promotion_gate"],
            )
        )
    return lines


def first_lane_candidate(candidates: list[dict[str, Any]], lane: str, *, require_placements: bool = False) -> dict[str, Any] | None:
    for row in candidates:
        if row["lane"] != lane:
            continue
        if require_placements and int(row["placement_sector_count"]) <= 0:
            continue
        return row
    return None


def describe_candidate(row: dict[str, Any] | None) -> str:
    if row is None:
        return "no generated candidate"
    return (
        f"`{row['enemy_name']}` (enemy `{row['enemy_id']}`, {row['action_slot']} "
        f"row `{row['action_row']}`, PP `{row['enemy_pp']}`)"
    )


def render_note(data: dict[str, Any]) -> str:
    candidates = data["candidates"]
    by_lane: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in candidates:
        by_lane[row["lane"]].append(row)
    top_magnet = first_lane_candidate(candidates, "psi_magnet_transfer")
    accessible_magnet = first_lane_candidate(candidates, "psi_magnet_transfer", require_placements=True)
    top_loss = first_lane_candidate(candidates, "pp_reduction_loss_only")
    accessible_loss = first_lane_candidate(candidates, "pp_reduction_loss_only", require_placements=True)

    lines = [
        "# C2 Resource Amount Natural Candidates",
        "",
        "Generated by `tools/build_c2_resource_amount_natural_candidates.py` from",
        "`refs/eb-decompile-4ef92` enemy/action data plus the local battle-action",
        "crosswalk. This is a Phase 2 probe-planning note: it identifies vanilla",
        "enemy/action users of the PP amount routines, but it does not promote",
        "runtime semantics without an unpatched Mesen trace.",
        "",
        "## Summary",
        "",
        f"- candidates: `{data['summary']['candidate_count']}`",
    ]
    for lane, count in data["summary"]["lanes"].items():
        lines.append(f"- `{lane}`: `{count}`")
    lines.extend(
        [
            "",
            "## Probe Rule",
            "",
            "A proof-grade resource trace must be an unpatched runtime run where the",
            "selected target has nonzero PP, the oracle observes the action entry",
            "and `C2:721D`, and the post-call snapshots show the target PP delta.",
            "For PSI Magnet, the same trace should also distinguish active-row PP",
            "recovery through `C2:7191`; for PP reduction, active-row PP should stay",
            "unchanged.",
            "",
            "## Recommended First Probes",
            "",
            f"- PSI Magnet transfer top rank: {describe_candidate(top_magnet)}.",
            f"- PSI Magnet transfer with map placements: {describe_candidate(accessible_magnet)}.",
            f"- PP reduction loss-only top rank: {describe_candidate(top_loss)}.",
            f"- PP reduction loss-only with map placements: {describe_candidate(accessible_loss)}.",
            "- The replaced Dread Skelpion save remains a poison/status fixture, not a",
            "  resource fixture; the current candidate list does not show Dread Skelpion",
            "  as a vanilla row `54` or row `95` user.",
            "",
            "## Top Candidates",
            "",
            *render_table(candidates[:16]),
        ]
    )
    for lane in sorted(by_lane):
        lines.extend(["", f"## `{lane}`", "", *render_table(by_lane[lane][:24])])
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    enemies = load_yaml(REFS / "enemy_configuration_table.yml")
    enemy_groups = load_yaml(REFS / "enemy_groups.yml")
    map_enemy_groups = load_yaml(REFS / "map_enemy_groups.yml")
    map_enemy_placement = load_yaml(REFS / "map_enemy_placement.yml")
    crosswalk = load_json(ROOT / "manifests" / "battle-action-row-crosswalk.json")
    group_index = index_enemy_groups(enemy_groups)
    map_group_index = index_map_groups(map_enemy_groups)
    placement_index = index_placements(map_enemy_placement)
    candidates = build_candidates(enemies, group_index, map_group_index, placement_index, row_by_id(crosswalk))
    data = {
        "schema": "earthbound-decomp.c2-resource-amount-natural-candidates.v1",
        "status": "probe_planning_only",
        "generated_by": "tools/build_c2_resource_amount_natural_candidates.py",
        "source_inputs": [
            manifest_path(REFS / "enemy_configuration_table.yml"),
            manifest_path(REFS / "enemy_groups.yml"),
            manifest_path(REFS / "map_enemy_groups.yml"),
            manifest_path(REFS / "map_enemy_placement.yml"),
            "manifests/battle-action-row-crosswalk.json",
            "notes/psi-magnet-drain-amount.md",
            "notes/c2-late-stat-resource-runtime-polish.md",
        ],
        "action_rows": ACTION_ROWS,
        "summary": summarize(candidates),
        "candidates": candidates,
    }
    write_json(Path(args.output), data)
    write_text(Path(args.notes), render_note(data))
    print(f"Wrote {args.output}")
    print(f"Wrote {args.notes}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
