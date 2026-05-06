#!/usr/bin/env python3
"""Validate an ignored non-0x00 control probe batch-run summary."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SUMMARY = (
    ROOT / "build" / "audio" / "nonzero-control-probe-jobs" / "nonzero-control-probe-batch-summary.json"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate audio non-0x00 control probe batch summary.")
    parser.add_argument("summary", nargs="?", default=str(DEFAULT_SUMMARY))
    return parser.parse_args()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def validate(data: dict[str, Any]) -> None:
    require(data.get("schema") == "earthbound-decomp.audio-nonzero-control-probe-batch-run.v1", "unexpected schema")
    require(data.get("mode") in {"dry-run-stub", "external"}, f"unexpected mode {data.get('mode')}")
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
    for run in runs:
        job_id = str(run.get("job_id", ""))
        require(job_id.startswith("nonzero-probe-"), f"unexpected job id {job_id}")
        require(run.get("status") in {"completed", "failed"}, f"{job_id}: unexpected status")
        require(run.get("result_path"), f"{job_id}: missing result path")
        if run.get("status") == "completed":
            require(run.get("error") is None, f"{job_id}: completed run has error")


def main() -> int:
    args = parse_args()
    data = json.loads(Path(args.summary).read_text(encoding="utf-8"))
    validate(data)
    print(
        "Audio non-0x00 control probe batch summary validation OK: "
        f"{data['completed_count']} completed, {data['failed_count']} failed"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
