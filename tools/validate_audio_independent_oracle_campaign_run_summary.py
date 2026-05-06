#!/usr/bin/env python3
"""Validate an ignored independent external-emulator oracle campaign run summary."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SUMMARY = ROOT / "build" / "audio" / "independent-oracle-campaign-runs" / "independent-oracle-campaign-run-summary.json"
VALID_STATUSES = {"independent_capture_ready", "pending_independent_capture"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate independent oracle campaign run summary.")
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
    require(data.get("schema") == "earthbound-decomp.audio-independent-oracle-campaign-run.v1", "unexpected schema")
    require(data.get("campaign_plan") == "manifests/audio-independent-oracle-campaign-plan.json", "unexpected campaign plan")
    require(data.get("campaign_status") == "independent_external_oracle_campaign_ready", "unexpected campaign status")
    require(data.get("mode") in {"dry-run-plan", "audit-existing-captures"}, f"unexpected mode {data.get('mode')}")
    require(data.get("promotion_allowed_by_run") is False, "run must not allow promotion")
    require(data.get("release_quality_claim_ready_by_run") is False, "run must not claim release quality")
    runs = data.get("runs", [])
    require(len(runs) > 0, "run summary should include at least one selected job")
    require(int(data.get("selected_count", -1)) == len(runs), "selected count mismatch")
    ready_count = sum(1 for run in runs if run.get("status") == "independent_capture_ready")
    pending_count = sum(1 for run in runs if run.get("status") == "pending_independent_capture")
    require(int(data.get("independent_capture_ready_count", -1)) == ready_count, "ready count mismatch")
    require(int(data.get("pending_independent_capture_count", -1)) == pending_count, "pending count mismatch")
    require(ready_count + pending_count == len(runs), "run status counts do not cover selected runs")

    seen_orders: set[int] = set()
    seen_job_ids: set[str] = set()
    previous_order = 0
    for run in runs:
        order = int(run.get("execution_order", 0))
        job_id = str(run.get("job_id", ""))
        status = str(run.get("status"))
        require(order > 0, f"{job_id}: invalid execution order")
        require(order not in seen_orders, f"{job_id}: duplicate order {order}")
        require(order >= previous_order, f"{job_id}: run order is not sorted")
        previous_order = order
        seen_orders.add(order)
        require(job_id not in seen_job_ids, f"duplicate job id {job_id}")
        seen_job_ids.add(job_id)
        require(job_id.startswith("oracle-track-"), f"{job_id}: unexpected oracle job id")
        require(status in VALID_STATUSES, f"{job_id}: unexpected status {status}")
        require(int(run.get("track_id", -1)) > 0, f"{job_id}: invalid track id")
        require(str(run.get("phase", "")).startswith("independent-"), f"{job_id}: unexpected phase")
        require("import_audio_oracle_reference_capture.py" in str(run.get("import_command", "")), f"{job_id}: missing import command")
        require("collect_audio_oracle_comparison_results.py" in str(run.get("collect_command", "")), f"{job_id}: missing collect command")
        require("validate_audio_oracle_verification_report.py" in str(run.get("result_validator", "")), f"{job_id}: missing validator")
        require(str(run.get("capture_metadata_path", "")).startswith("build/audio/oracle-comparison-all-tracks/"), f"{job_id}: bad metadata path")
        require(run.get("promotion_allowed_by_run") is False, f"{job_id}: run promoted unexpectedly")
        if data.get("mode") == "audit-existing-captures":
            audit = run.get("audit", {})
            require(isinstance(audit, dict), f"{job_id}: missing audit record")
            require(audit.get("capture_metadata_path") == run.get("capture_metadata_path"), f"{job_id}: audit path mismatch")
            if status == "independent_capture_ready":
                require(audit.get("capture_metadata_exists") is True, f"{job_id}: ready capture missing metadata")
                require(audit.get("independent_emulator_capture") is True, f"{job_id}: ready capture is not independent")
                require(not audit.get("missing_metadata_fields"), f"{job_id}: ready capture missing metadata fields")
                require(audit.get("source_spc_sha1_matches") is True, f"{job_id}: ready capture source SHA mismatch")
                require(audit.get("wav_format_matches_policy") is True, f"{job_id}: ready capture WAV format mismatch")
                require(audit.get("duration_covers_planned") is True, f"{job_id}: ready capture too short")
        else:
            require(run.get("audit") == {}, f"{job_id}: dry-run should not include audit evidence")

    require(data.get("selection") is not None, "missing selection")
    require(count_runs(runs, "status").get("pending_independent_capture", 0) == pending_count, "pending count mismatch")


def main() -> int:
    args = parse_args()
    data = json.loads(Path(args.summary).read_text(encoding="utf-8"))
    validate(data)
    print(
        "Audio independent oracle campaign run summary validation OK: "
        f"{data['independent_capture_ready_count']} ready, "
        f"{data['pending_independent_capture_count']} pending"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
