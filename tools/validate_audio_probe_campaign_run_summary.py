#!/usr/bin/env python3
"""Validate an ignored audio probe campaign run summary."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SUMMARY = ROOT / "build" / "audio" / "probe-campaign-runs" / "probe-campaign-run-summary.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate audio probe campaign run summary.")
    parser.add_argument("summary", nargs="?", default=str(DEFAULT_SUMMARY))
    return parser.parse_args()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def count_runs(runs: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for run in runs:
        counts[str(run.get(key))] += 1
    return dict(sorted(counts.items()))


def validate(data: dict[str, Any]) -> None:
    require(data.get("schema") == "earthbound-decomp.audio-probe-campaign-run.v1", "unexpected schema")
    require(data.get("campaign_plan") == "manifests/audio-probe-campaign-plan.json", "unexpected campaign plan")
    require(data.get("mode") in {"dry-run-stub", "stub-shape"}, f"unexpected mode {data.get('mode')}")
    require(data.get("promotion_allowed_by_run") is False, "campaign run must not allow promotion")
    runs = data.get("runs", [])
    require(int(data.get("selected_count", -1)) == len(runs), "selected count mismatch")
    require(
        int(data.get("completed_count", -1)) == sum(1 for run in runs if run.get("status") == "completed"),
        "completed count mismatch",
    )
    require(
        int(data.get("failed_count", -1)) == sum(1 for run in runs if run.get("status") == "failed"),
        "failed count mismatch",
    )
    seen_orders: set[int] = set()
    previous_order = 0
    for run in runs:
        order = int(run.get("execution_order", 0))
        job_id = str(run.get("job_id", ""))
        lane = str(run.get("lane"))
        require(order > 0, f"{job_id}: invalid execution order")
        require(order not in seen_orders, f"{job_id}: duplicate order {order}")
        require(order >= previous_order, f"{job_id}: run order is not sorted")
        previous_order = order
        seen_orders.add(order)
        require(lane in {"zero", "nonzero"}, f"{job_id}: unexpected lane {lane}")
        if lane == "zero":
            require(job_id.startswith("zero-probe-track-"), f"{job_id}: bad zero job id")
            require(str(run.get("command")) == "0x00", f"{job_id}: zero lane command mismatch")
            require("zero-runtime-probe" in str(run.get("result_path")), f"{job_id}: bad zero result path")
        else:
            require(job_id.startswith("nonzero-probe-"), f"{job_id}: bad nonzero job id")
            require("nonzero-control-probe" in str(run.get("result_path")), f"{job_id}: bad nonzero result path")
        require(run.get("status") in {"completed", "failed"}, f"{job_id}: unexpected status")
        require(isinstance(run.get("returncode"), int), f"{job_id}: missing returncode")
        require(run.get("lane_batch_summary"), f"{job_id}: missing lane batch summary")
        if run.get("status") == "completed":
            require(int(run.get("returncode")) == 0, f"{job_id}: completed run has nonzero return code")
            require(run.get("error") is None, f"{job_id}: completed run has error")
            require(run.get("result_exists") is True, f"{job_id}: completed run should create/retain result")
    require(data.get("selection") is not None, "missing selection record")
    require(count_runs(runs, "status").get("failed", 0) == int(data.get("failed_count", -1)), "failed run count mismatch")


def main() -> int:
    args = parse_args()
    data = json.loads(Path(args.summary).read_text(encoding="utf-8"))
    validate(data)
    print(
        "Audio probe campaign run summary validation OK: "
        f"{data['completed_count']} completed, {data['failed_count']} failed"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
