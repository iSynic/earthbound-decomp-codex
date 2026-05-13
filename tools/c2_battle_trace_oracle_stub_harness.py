#!/usr/bin/env python3
"""Schema-only external harness stub for C2 battle trace-oracle jobs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a schema-only C2 battle trace-oracle harness stub.")
    parser.add_argument("--job", required=True, help="Per-job C2 oracle job.json path.")
    parser.add_argument("--result", help="Result JSON path. Defaults to the job result_path.")
    parser.add_argument("--harness-version", default="c2-battle-trace-oracle-stub")
    parser.add_argument(
        "--status",
        default="unsupported",
        choices=["failed", "unsupported", "unresolved"],
        help="Dry-run status to write. Successful proof requires a real runtime harness.",
    )
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_result(job: dict[str, Any], *, harness_version: str, status: str) -> dict[str, Any]:
    paths = job.get("output_paths", {})
    return {
        "schema": "earthbound-decomp.c2-battle-trace-oracle-result.v1",
        "job_id": job["job_id"],
        "oracle_id": job["oracle_id"],
        "status": status,
        "contract_classification": "unresolved",
        "observed_addresses": [],
        "captured_fields": {},
        "promotion_allowed_by_result": False,
        "behavior_change_allowed": False,
        "evidence": {
            "harness_name": "c2_battle_trace_oracle_stub_harness",
            "harness_version": harness_version,
            "trace_path": paths.get("raw_trace_path"),
            "job_path": paths.get("job_path"),
            "classification_rationale": (
                "Schema-only harness check. No SNES execution, WRAM capture, or C2 behavior proof was attempted."
            ),
        },
    }


def main() -> int:
    args = parse_args()
    job_path = Path(args.job)
    job = load_json(job_path)
    result_path = Path(args.result) if args.result else Path(job["output_paths"]["result_path"])
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result = build_result(job, harness_version=args.harness_version, status=args.status)
    result_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote C2 battle trace oracle stub result -> {result_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
