#!/usr/bin/env python3
"""Validate a local C2 battle fixture scout summary."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ROOT = ROOT / "build" / "c2" / "battle-trace-oracles" / "fixture-scout"
DEFAULT_SUMMARY = DEFAULT_ROOT / "fixture-scout-summary.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate C2 battle fixture scout summary.")
    parser.add_argument("summary", nargs="?", default=str(DEFAULT_SUMMARY))
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def validate(data: dict[str, Any], path: Path) -> None:
    require(data.get("schema") == "earthbound-decomp.c2-battle-fixture-scout.v1", "bad schema")
    require(data.get("status") == "fixture_scout_completed", "bad status")
    require(str(path.resolve()).startswith(str(DEFAULT_ROOT.resolve())), "summary must stay under ignored fixture-scout root")
    require(isinstance(data.get("frame_limit"), int) and data["frame_limit"] > 0, "bad frame limit")
    require(isinstance(data.get("timeout"), int) and data["timeout"] > 0, "bad timeout")
    require(isinstance(data.get("scout_addresses"), list) and data["scout_addresses"], "missing scout addresses")
    require(isinstance(data.get("watch_ranges"), list) and data["watch_ranges"], "missing watch ranges")
    require(isinstance(data.get("patterns"), list) and data["patterns"], "missing patterns")
    summary = data.get("summary", {})
    records = data.get("records", [])
    require(isinstance(records, list), "records must be list")
    require(summary.get("run_count") == len(records), "run count mismatch")
    require(summary.get("source_promotion_allowed") is False, "summary cannot allow source promotion")
    require(summary.get("behavior_change_allowed") is False, "summary cannot allow behavior changes")
    battle_candidates = []
    command_candidates = []
    for record in records:
        prefix = f"{record.get('state_id')}:{record.get('pattern_id')}"
        require(record.get("state_id"), "record missing state id")
        require(record.get("pattern_id"), f"{prefix}: missing pattern id")
        require(record.get("input_pattern"), f"{prefix}: missing input pattern")
        require(record.get("status") in {"completed", "failed", "missing_state"}, f"{prefix}: bad status")
        require(record.get("output_dir"), f"{prefix}: missing output dir")
        require(record.get("raw_trace_path"), f"{prefix}: missing raw trace path")
        require(record.get("source_promotion_allowed") is False, f"{prefix}: source promotion must be false")
        require(record.get("behavior_change_allowed") is False, f"{prefix}: behavior change must be false")
        require(isinstance(record.get("observed_addresses", []), list), f"{prefix}: observed addresses not list")
        require(isinstance(record.get("battle_entry_candidate"), bool), f"{prefix}: battle candidate flag not bool")
        require(isinstance(record.get("command_fixture_candidate"), bool), f"{prefix}: command candidate flag not bool")
        if record.get("status") != "missing_state":
            require(isinstance(record.get("state_size"), int) and record["state_size"] > 0, f"{prefix}: bad state size")
            require(isinstance(record.get("state_sha256"), str) and len(record["state_sha256"]) == 64, f"{prefix}: bad state hash")
        if record.get("status") == "completed":
            require(isinstance(record.get("line_count"), int) and record["line_count"] >= 0, f"{prefix}: bad line count")
            require(isinstance(record.get("invalid_line_count"), int) and record["invalid_line_count"] >= 0, f"{prefix}: bad invalid line count")
            require(isinstance(record.get("event_counts", {}), dict), f"{prefix}: bad event counts")
            require(isinstance(record.get("breakpoint_hit_counts", {}), dict), f"{prefix}: bad hit counts")
        if record.get("battle_entry_candidate"):
            battle_candidates.append(prefix)
        if record.get("command_fixture_candidate"):
            command_candidates.append(prefix)
    require(summary.get("battle_entry_candidate_count") == len(battle_candidates), "battle candidate count mismatch")
    require(summary.get("command_fixture_candidate_count") == len(command_candidates), "command candidate count mismatch")
    require(summary.get("battle_entry_candidates", []) == battle_candidates, "battle candidate list mismatch")
    require(summary.get("command_fixture_candidates", []) == command_candidates, "command candidate list mismatch")


def main() -> int:
    args = parse_args()
    path = Path(args.summary)
    data = load_json(path)
    validate(data, path)
    print(
        "C2 battle fixture scout validation OK: "
        f"{data['summary']['run_count']} runs, "
        f"{data['summary']['battle_entry_candidate_count']} battle-entry candidates"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
