#!/usr/bin/env python3
"""Validate a C2 battle trace-oracle raw trace summary."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ROOT = ROOT / "build" / "c2" / "battle-trace-oracles"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate C2 raw trace summary JSON.")
    parser.add_argument("summary", help="raw-trace-summary.json path.")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def repo_path(path_text: str) -> Path:
    path = Path(path_text)
    return path if path.is_absolute() else ROOT / path


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def validate(data: dict[str, Any], summary_path: Path) -> None:
    require(data.get("schema") == "earthbound-decomp.c2-battle-trace-raw-summary.v1", "bad schema")
    require(data.get("status") == "raw_trace_summarized", f"bad status {data.get('status')}")
    require(str(data.get("job_id", "")).startswith("c2-battle-oracle-"), "bad job id")
    require(data.get("oracle_id"), "missing oracle id")
    require(str(summary_path.resolve()).startswith(str(DEFAULT_ROOT.resolve())), "summary must stay under ignored C2 build output")
    trace_path = repo_path(str(data.get("trace_path", "")))
    require(str(trace_path.resolve()).startswith(str(DEFAULT_ROOT.resolve())), "trace path must stay under ignored C2 build output")
    require(isinstance(data.get("trace_exists"), bool), "trace_exists must be bool")
    require(isinstance(data.get("trace_nonempty"), bool), "trace_nonempty must be bool")
    require(isinstance(data.get("line_count"), int) and data["line_count"] >= 0, "line_count must be non-negative int")
    require(isinstance(data.get("invalid_line_count"), int) and data["invalid_line_count"] >= 0, "invalid_line_count must be non-negative int")
    for key in ("event_counts", "breakpoint_hit_counts", "watch_snapshot_counts"):
        require(isinstance(data.get(key), dict), f"{key} must be object")
    for key in (
        "probe_breakpoint_hit_counts",
        "probe_route_group_hit_counts",
        "dispatch_target_counts",
        "probe_dispatch_target_counts",
        "stack_return_counts",
        "probe_stack_return_counts",
        "dispatch_lane_counts",
        "probe_dispatch_lane_counts",
        "post_call_snapshot_counts",
    ):
        require(isinstance(data.get(key, {}), dict), f"{key} must be object when present")
    for key in ("observed_addresses", "required_hit_addresses", "configured_minimum_hits", "missing_minimum_hits"):
        require(isinstance(data.get(key), list), f"{key} must be list")
        for item in data[key]:
            require(isinstance(item, str), f"{key} entries must be strings")
    probe_observed = data.get("probe_observed_addresses", [])
    require(isinstance(probe_observed, list), "probe_observed_addresses must be list when present")
    for item in probe_observed:
        require(isinstance(item, str), "probe_observed_addresses entries must be strings")
    require(isinstance(data.get("minimum_hits_satisfied"), bool), "minimum_hits_satisfied must be bool")
    require(data.get("source_promotion_allowed") is False, "summary cannot allow source promotion")
    require(data.get("behavior_change_allowed") is False, "summary cannot allow behavior changes")
    if data.get("minimum_hits_satisfied") is True:
        require(data.get("trace_nonempty") is True, "minimum hits require non-empty trace")
        require(not data.get("missing_minimum_hits"), "minimum hits cannot be satisfied with missing hits")
    else:
        if data.get("configured_minimum_hits"):
            require(
                bool(data.get("missing_minimum_hits")) or data.get("trace_nonempty") is False,
                "unsatisfied minimum hits must reflect missing configured hits or an empty trace",
            )


def main() -> int:
    args = parse_args()
    path = Path(args.summary)
    data = load_json(path)
    validate(data, path)
    print(f"C2 raw trace summary validation OK: {data['oracle_id']} minimum={data['minimum_hits_satisfied']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
