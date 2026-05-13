#!/usr/bin/env python3
"""Validate C2 battle trace save-state probe summary."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SUMMARY = ROOT / "build" / "c2" / "battle-trace-oracles" / "save-state-probes" / "c1_c2_target_action_staging" / "probe-summary.json"
DEFAULT_ROOT = ROOT / "build" / "c2" / "battle-trace-oracles" / "save-state-probes"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate C2 save-state probe summary.")
    parser.add_argument("summary", nargs="?", default=str(DEFAULT_SUMMARY))
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def validate(data: dict[str, Any], path: Path) -> None:
    require(data.get("schema") == "earthbound-decomp.c2-battle-trace-save-state-probes.v1", "bad schema")
    require(data.get("status") == "save_state_probes_completed", "bad status")
    require(data.get("oracle_id"), "missing oracle id")
    require(data.get("input_pattern"), "missing input pattern")
    require(isinstance(data.get("frame_limit"), int) and data["frame_limit"] > 0, "bad frame limit")
    require(isinstance(data.get("timeout"), int) and data["timeout"] > 0, "bad timeout")
    require(str(path.resolve()).startswith(str(DEFAULT_ROOT.resolve())), "summary must stay under ignored save-state probe root")
    summary = data.get("summary", {})
    records = data.get("records", [])
    require(isinstance(records, list), "records must be list")
    require(summary.get("candidate_count") == len(records), "candidate count mismatch")
    require(summary.get("source_promotion_allowed") is False, "summary cannot allow source promotion")
    require(summary.get("behavior_change_allowed") is False, "summary cannot allow behavior changes")
    ready = []
    for record in records:
        require(record.get("probe_id"), "record missing probe id")
        require(record.get("oracle_id") == data["oracle_id"], f"{record.get('probe_id')}: oracle mismatch")
        require(record.get("status") in {"completed", "failed", "missing_state"}, f"{record.get('probe_id')}: bad status")
        require(record.get("output_dir"), f"{record.get('probe_id')}: missing output dir")
        require(record.get("raw_trace_summary_path"), f"{record.get('probe_id')}: missing raw summary path")
        require(record.get("mesen_run_summary_path"), f"{record.get('probe_id')}: missing run summary path")
        require(record.get("raw_trace_path"), f"{record.get('probe_id')}: missing raw trace path")
        require(record.get("input_pattern") == data["input_pattern"], f"{record.get('probe_id')}: input pattern mismatch")
        require(record.get("frame_limit") == data["frame_limit"], f"{record.get('probe_id')}: frame limit mismatch")
        require(record.get("timeout") == data["timeout"], f"{record.get('probe_id')}: timeout mismatch")
        require(record.get("source_promotion_allowed") is False, f"{record.get('probe_id')}: source promotion must be false")
        require(record.get("behavior_change_allowed") is False, f"{record.get('probe_id')}: behavior change must be false")
        require(isinstance(record.get("minimum_hits_satisfied"), bool), f"{record.get('probe_id')}: minimum flag not bool")
        require(isinstance(record.get("observed_addresses", []), list), f"{record.get('probe_id')}: observed addresses not list")
        if record.get("status") != "missing_state":
            require(isinstance(record.get("save_state_size"), int) and record["save_state_size"] > 0, f"{record.get('probe_id')}: bad save state size")
            require(isinstance(record.get("save_state_sha256"), str) and len(record["save_state_sha256"]) == 64, f"{record.get('probe_id')}: bad save state hash")
        if record.get("status") == "completed":
            require(isinstance(record.get("event_counts", {}), dict), f"{record.get('probe_id')}: event counts not object")
            require(isinstance(record.get("breakpoint_hit_counts", {}), dict), f"{record.get('probe_id')}: breakpoint counts not object")
            require(isinstance(record.get("configured_minimum_hits", []), list), f"{record.get('probe_id')}: configured minimum hits not list")
            require(isinstance(record.get("missing_minimum_hits", []), list), f"{record.get('probe_id')}: missing minimum hits not list")
        if record.get("minimum_hits_satisfied"):
            ready.append(record["probe_id"])
            require(record.get("status") == "completed", f"{record.get('probe_id')}: ready probe must complete")
            require(record.get("observed_addresses"), f"{record.get('probe_id')}: ready probe needs observed addresses")
    require(summary.get("minimum_hit_candidate_count") == len(ready), "ready count mismatch")
    require(summary.get("ready_fixture_candidates", []) == ready, "ready fixture list mismatch")


def main() -> int:
    args = parse_args()
    path = Path(args.summary)
    data = load_json(path)
    validate(data, path)
    print(
        "C2 save-state probe validation OK: "
        f"{data['summary']['candidate_count']} candidates, "
        f"{data['summary']['minimum_hit_candidate_count']} ready"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
