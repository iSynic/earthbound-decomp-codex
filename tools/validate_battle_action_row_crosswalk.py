#!/usr/bin/env python3
"""Validate the generated D5 battle action row crosswalk."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MANIFEST = ROOT / "manifests" / "battle-action-row-crosswalk.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate battle action row crosswalk manifest.")
    parser.add_argument("manifest", nargs="?", default=str(DEFAULT_MANIFEST))
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def validate(data: dict[str, Any]) -> None:
    require(data.get("schema") == "earthbound-decomp.battle-action-row-crosswalk.v1", "bad schema")
    require(data.get("status") == "generated_from_local_rom_and_source_labels", "bad status")
    table = data.get("table", {})
    require(table.get("contract_id") == "BATTLE_ACTION_TABLE", "bad table contract")
    require(table.get("address") == "D5:7B68", "bad table address")
    require(table.get("stride") == 12, "bad stride")
    rows = data.get("rows", [])
    require(isinstance(rows, list), "rows must be list")
    require(table.get("row_count") == len(rows), "table row count mismatch")
    require(len(rows) == 318, "unexpected row count")
    expected_rows = list(range(len(rows)))
    require([row.get("row") for row in rows] == expected_rows, "rows must be contiguous")
    summary = data.get("summary", {})
    require(summary.get("row_count") == len(rows), "summary row count mismatch")
    require(summary.get("source_promotion_allowed") is False, "summary cannot allow source promotion")
    require(summary.get("behavior_change_allowed") is False, "summary cannot allow behavior changes")
    message_lanes = Counter()
    action_lanes = Counter()
    message_banks = Counter()
    action_banks = Counter()
    ef_labeled = 0
    c2_labeled = 0
    for row in rows:
        prefix = f"row {row.get('row')}"
        require(row.get("table_address"), f"{prefix}: missing table address")
        for key in ("direction", "target", "action_type"):
            require(isinstance(row.get(key), dict), f"{prefix}: {key} must be object")
            require(isinstance(row[key].get("value"), int), f"{prefix}: {key} value must be int")
            require(row[key].get("name"), f"{prefix}: {key} missing name")
        require(isinstance(row.get("cost"), int), f"{prefix}: cost must be int")
        require(isinstance(row.get("message_pointer"), str) and ":" in row["message_pointer"], f"{prefix}: bad message pointer")
        require(isinstance(row.get("action_pointer"), str) and ":" in row["action_pointer"], f"{prefix}: bad action pointer")
        require(row.get("message_bank") == row["message_pointer"].split(":", 1)[0], f"{prefix}: message bank mismatch")
        require(row.get("action_bank") == row["action_pointer"].split(":", 1)[0], f"{prefix}: action bank mismatch")
        require(row.get("message_lane") in {"ef_row_message", "non_ef_row_message", "other_message_bank", "no_message_pointer"}, f"{prefix}: bad message lane")
        require(row.get("action_lane") in {"c2_behavior_body", "other_action_bank", "no_action_pointer"}, f"{prefix}: bad action lane")
        require(isinstance(row.get("message_source_labels"), list), f"{prefix}: message labels must be list")
        require(isinstance(row.get("action_source_labels"), list), f"{prefix}: action labels must be list")
        require(row.get("source_promotion_allowed") is False, f"{prefix}: source promotion must be false")
        require(row.get("behavior_change_allowed") is False, f"{prefix}: behavior change must be false")
        message_lanes[row["message_lane"]] += 1
        action_lanes[row["action_lane"]] += 1
        message_banks[row["message_bank"]] += 1
        action_banks[row["action_bank"]] += 1
        if row["message_lane"] == "ef_row_message" and row["message_source_labels"]:
            ef_labeled += 1
        if row["action_lane"] == "c2_behavior_body" and row["action_source_labels"]:
            c2_labeled += 1
    require(summary.get("message_lanes") == dict(sorted(message_lanes.items())), "message lane counts mismatch")
    require(summary.get("action_lanes") == dict(sorted(action_lanes.items())), "action lane counts mismatch")
    require(summary.get("message_banks") == dict(sorted(message_banks.items())), "message bank counts mismatch")
    require(summary.get("action_banks") == dict(sorted(action_banks.items())), "action bank counts mismatch")
    require(summary.get("ef_message_rows_with_source_labels") == ef_labeled, "EF label count mismatch")
    require(summary.get("c2_action_rows_with_source_labels") == c2_labeled, "C2 label count mismatch")


def main() -> int:
    args = parse_args()
    data = load_json(Path(args.manifest))
    validate(data)
    print(
        "Battle action row crosswalk validation OK: "
        f"{data['summary']['row_count']} rows, "
        f"{data['summary']['message_lanes'].get('ef_row_message', 0)} EF messages"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
