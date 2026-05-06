#!/usr/bin/env python3
"""Schema-only external harness stub for targeted non-0x00 control probes."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a schema-only audio non-0x00 control probe harness stub.")
    parser.add_argument("--job", required=True, help="Per-job nonzero-control probe job.json path.")
    parser.add_argument("--result", help="Result JSON path. Defaults to the job result_path.")
    parser.add_argument("--harness-version", default="nonzero-control-probe-stub")
    parser.add_argument(
        "--status",
        default="unsupported",
        choices=["failed", "unsupported", "unresolved"],
        help="Dry-run status to write. Successful proof requires a real runtime harness.",
    )
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def first_source_candidate(job: dict[str, Any]) -> dict[str, Any]:
    candidates = job.get("source_candidates", [])
    if not candidates:
        return {}
    return candidates[0]


def build_result(job: dict[str, Any], *, harness_version: str, status: str) -> dict[str, Any]:
    candidate = first_source_candidate(job)
    source = candidate.get("source") or {}
    return {
        "schema": "earthbound-decomp.audio-nonzero-control-probe-result.v1",
        "job_id": job["job_id"],
        "command": job["command"],
        "reader_pc": job["reader_pc"],
        "status": status,
        "source_candidate_track_id": candidate.get("track_id"),
        "source_spc_sha1": source.get("source_spc", {}).get("sha1"),
        "control_effect_classification": "unresolved",
        "reader_pc_observations": [],
        "state_effect_observations": [],
        "promotion_allowed_by_result": False,
        "evidence": {
            "harness_name": "audio_nonzero_control_probe_stub_harness",
            "harness_version": harness_version,
            "trace_path": job.get("raw_trace_path"),
            "classification_rationale": (
                "Schema-only harness check. No SPC700 execution or non-0x00 control effect proof was attempted."
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
    print(f"Wrote nonzero-control probe stub result -> {result_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
