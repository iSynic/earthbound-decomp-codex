#!/usr/bin/env python3
"""Validate the generated C2 save-state battler scout manifest."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MANIFEST = ROOT / "manifests" / "c2-save-state-battler-scout.json"


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
    require(data.get("schema") == "earthbound-decomp.c2-save-state-battler-scout.v1", "bad schema")
    require(data.get("status") == "local_probe_inventory_only", "bad status")
    summary = data.get("summary", {})
    states = data.get("states")
    require(isinstance(states, list) and states, "states must be a non-empty list")
    require(int(summary.get("state_count", -1)) == len(states), "state_count mismatch")
    pp_total = 0
    seen: set[str] = set()
    for state in states:
        basename = str(state.get("state_basename", ""))
        require(basename.endswith(".mss"), f"bad state basename {basename}")
        require(basename not in seen, f"duplicate state {basename}")
        seen.add(basename)
        require(str(state.get("state_sha256", "")), f"{basename}: missing sha256")
        require(int(state.get("returncode", -1)) == 0, f"{basename}: Mesen run failed")
        require(state.get("source_promotion_allowed") is False, f"{basename}: source promotion must be false")
        require(state.get("behavior_change_allowed") is False, f"{basename}: behavior change must be false")
        pp_rows = state.get("pp_rows", [])
        require(isinstance(pp_rows, list), f"{basename}: pp_rows must be a list")
        require(int(state.get("pp_rows_seen", -1)) == len(pp_rows), f"{basename}: pp row count mismatch")
        target_row = state.get("selected_target_row")
        if target_row is not None:
            require(str(target_row.get("root_id")) == "battle_candidates_9fac", f"{basename}: selected target must be a battle candidate")
        pp_total += len(pp_rows)
        for row in pp_rows:
            require(str(row.get("root_id", "")) == "battle_candidates_9fac", f"{basename}: pp row must come from battler candidates")
            require(str(row.get("base", "")).startswith("$"), f"{basename}: pp row missing base")
            require(int(row.get("pp", 0)) >= 0, f"{basename}: pp row bad pp")
            require(int(row.get("max_pp", 0)) >= 0, f"{basename}: pp row bad max_pp")
            require(str(row.get("row_sha256", "")), f"{basename}: pp row missing hash")
    require(pp_total == int(summary.get("pp_row_count", -1)), "pp_row_count mismatch")


def main() -> int:
    args = parse_args()
    data = load_json(Path(args.manifest))
    validate(data)
    print(f"C2 save-state battler scout validation OK: {len(data['states'])} states")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
