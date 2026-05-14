#!/usr/bin/env python3
"""Validate the generated C2 resource amount natural-candidate manifest."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MANIFEST = ROOT / "manifests" / "c2-resource-amount-natural-candidates.json"
REQUIRED_LANES = {"psi_magnet_transfer", "pp_reduction_loss_only"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", nargs="?", default=str(DEFAULT_MANIFEST))
    return parser.parse_args()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate(data: dict[str, Any]) -> None:
    require(data.get("schema") == "earthbound-decomp.c2-resource-amount-natural-candidates.v1", "bad schema")
    require(data.get("status") == "probe_planning_only", "status must remain probe_planning_only")
    candidates = data.get("candidates")
    require(isinstance(candidates, list) and candidates, "candidates must be a non-empty list")
    lanes = {str(row.get("lane")) for row in candidates}
    require(REQUIRED_LANES <= lanes, f"missing required lanes: {sorted(REQUIRED_LANES - lanes)}")
    seen: set[tuple[str, int, str]] = set()
    for row in candidates:
        lane = str(row.get("lane"))
        action_row = int(row.get("action_row", -1))
        enemy_id = int(row.get("enemy_id", -1))
        slot = str(row.get("action_slot", ""))
        key = (lane, enemy_id, slot)
        require(key not in seen, f"duplicate candidate {key}")
        seen.add(key)
        require(lane in REQUIRED_LANES, f"unexpected lane {lane}")
        if lane == "psi_magnet_transfer":
            require(action_row == 54, f"{key}: PSI Magnet lane must use action row 54")
            require(str(row.get("routine")) == "C2:9F5E", f"{key}: bad PSI Magnet routine")
        if lane == "pp_reduction_loss_only":
            require(action_row == 95, f"{key}: PP reduction lane must use action row 95")
            require(str(row.get("routine")) == "C2:8E42", f"{key}: bad PP reduction routine")
        require(enemy_id >= 0, f"{key}: enemy_id must be non-negative")
        require(str(row.get("enemy_name", "")), f"{key}: missing enemy_name")
        require(int(row.get("probe_rank", -1)) >= 0, f"{key}: bad probe_rank")
        require("natural unpatched trace" in str(row.get("promotion_gate", "")), f"{key}: bad promotion gate")
    summary = data.get("summary", {})
    require(int(summary.get("candidate_count", -1)) == len(candidates), "summary candidate_count mismatch")
    lane_counts = summary.get("lanes", {})
    for lane in REQUIRED_LANES:
        require(int(lane_counts.get(lane, 0)) > 0, f"summary missing lane {lane}")


def main() -> int:
    args = parse_args()
    path = Path(args.manifest)
    data = load_json(path)
    validate(data)
    print(f"C2 resource amount natural-candidate validation OK: {len(data['candidates'])} candidates")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
