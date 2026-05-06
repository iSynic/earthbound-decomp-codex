#!/usr/bin/env python3
"""Schema-only external harness stub for targeted 0x00 runtime probes."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a schema-only audio 0x00 runtime probe harness stub.")
    parser.add_argument("--job", required=True, help="Per-job zero-runtime probe job.json path.")
    parser.add_argument("--result", help="Result JSON path. Defaults to the job result_path.")
    parser.add_argument("--harness-version", default="zero-runtime-probe-stub")
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
    return {
        "schema": "earthbound-decomp.audio-zero-runtime-probe-result.v1",
        "job_id": job["job_id"],
        "track_id": job["track_id"],
        "track_name": job["track_name"],
        "status": status,
        "source_spc_sha1": job.get("source", {}).get("source_spc", {}).get("sha1"),
        "zero_effect_classification": "unresolved",
        "reader_pc_observations": [],
        "ef_stack_observations": [],
        "promotion_allowed_by_result": False,
        "evidence": {
            "harness_name": "audio_zero_runtime_probe_stub_harness",
            "harness_version": harness_version,
            "trace_path": job.get("raw_trace_path"),
            "classification_rationale": (
                "Schema-only harness check. No SPC700 execution or 0x00 effect proof was attempted."
            ),
            "job_path": job.get("job_path"),
        },
    }


def main() -> int:
    args = parse_args()
    job_path = Path(args.job)
    job = load_json(job_path)
    result_path = Path(args.result) if args.result else Path(job["result_path"])
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result = build_result(job, harness_version=args.harness_version, status=args.status)
    result_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote zero-runtime probe stub result -> {result_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
