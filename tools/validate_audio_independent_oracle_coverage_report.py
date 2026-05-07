#!/usr/bin/env python3
"""Validate the independent external-emulator audio oracle coverage report."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_REPORT = ROOT / "manifests" / "audio-independent-oracle-coverage-report.json"
REQUIRED_REFERENCES = {
    "manifests/audio-oracle-verification-report-all-tracks.json",
    "manifests/audio-independent-oracle-campaign-plan.json",
}
REQUIRED_PHASE_COUNTS = {
    "independent-duration-uncertainty-coverage": 4,
    "independent-probe-source-coverage": 5,
    "independent-representative-core": 7,
}
REQUIRED_UNCERTAINTY_COUNTS = {
    "active_preview_classification_pending": 1,
    "finite_transition_review_pending": 2,
    "loop_point_metadata_pending": 2,
    "non_zero_control_semantics_pending": 3,
    "pcm_trim_usable_sequence_intent_open": 2,
    "zero_runtime_probe_pending": 6,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate independent oracle coverage report.")
    parser.add_argument("report", nargs="?", default=str(DEFAULT_REPORT))
    return parser.parse_args()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def count_records(records: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for record in records:
        counts[str(record.get(key))] += 1
    return dict(sorted(counts.items()))


def validate(data: dict[str, Any]) -> None:
    require(data.get("schema") == "earthbound-decomp.audio-independent-oracle-coverage-report.v1", "unexpected schema")
    require(data.get("status") == "independent_oracle_coverage_ready_external_captures_pending", "unexpected status")
    require(data.get("source_report_status") == "all_track_near_oracle_passed_independent_oracle_pending", "unexpected source report status")
    require(data.get("source_campaign_status") == "independent_external_oracle_campaign_ready", "unexpected campaign status")
    require(REQUIRED_REFERENCES <= set(data.get("references", [])), "missing references")
    summary = data.get("summary", {})
    records = data.get("campaign_records", [])
    require(int(summary.get("oracle_job_count", 0)) == 190, "expected 190 oracle jobs")
    require(int(summary.get("near_oracle_pass_count", 0)) == 190, "expected all near-oracle jobs to pass")
    require(summary.get("status_counts") == {"audio_equivalent_state_delta": 190}, "unexpected near-oracle status counts")
    require(int(summary.get("independent_capture_count", -1)) == 0, "expected 0 independent captures")
    require(int(summary.get("missing_independent_capture_count", -1)) == 190, "expected 190 missing independent captures")
    require(int(summary.get("representative_campaign_job_count", -1)) == 16, "expected 16 representative jobs")
    require(len(records) == 16, "campaign record count mismatch")
    require(int(summary.get("representative_missing_independent_capture_count", -1)) == 16, "expected 16 missing representative captures")
    require(summary.get("phase_job_counts") == REQUIRED_PHASE_COUNTS, "phase counts mismatch")
    require(summary.get("phase_job_counts") == count_records(records, "phase"), "phase counts do not match records")
    require(summary.get("representative_primary_uncertainty_counts") == REQUIRED_UNCERTAINTY_COUNTS, "uncertainty counts mismatch")
    require(
        summary.get("representative_primary_uncertainty_counts") == count_records(records, "primary_uncertainty"),
        "uncertainty counts do not match records",
    )
    require(summary.get("all_track_near_oracle_passed") is True, "all-track near oracle should pass")
    require(summary.get("representative_oracle_gate_passed") is True, "representative oracle should pass")
    require(summary.get("independent_emulator_gate_passed") is False, "independent gate should fail")
    require(summary.get("release_quality_playback_claim_ready") is False, "release-quality claim should be blocked")
    require(summary.get("promotion_allowed_by_report") is False, "report must not allow promotion")

    seen_orders: set[int] = set()
    seen_tracks: set[int] = set()
    for record in records:
        order = int(record.get("execution_order", 0))
        track_id = int(record.get("track_id", -1))
        job_id = str(record.get("job_id", ""))
        require(order > 0, f"{job_id}: invalid order")
        require(order not in seen_orders, f"{job_id}: duplicate order")
        seen_orders.add(order)
        require(track_id > 0, f"{job_id}: invalid track id")
        require(track_id not in seen_tracks, f"{job_id}: duplicate track")
        seen_tracks.add(track_id)
        require(job_id.startswith("oracle-track-"), f"{job_id}: unexpected oracle job id")
        require(record.get("phase") in REQUIRED_PHASE_COUNTS, f"{job_id}: unexpected phase")
        require(record.get("primary_uncertainty") in REQUIRED_UNCERTAINTY_COUNTS, f"{job_id}: unexpected uncertainty")
        require(record.get("current_near_oracle_status") == "audio_equivalent_state_delta", f"{job_id}: near oracle status mismatch")
        require(record.get("current_independent_emulator_capture") is False, f"{job_id}: independent capture should be missing")
        require(record.get("independent_capture_required") is True, f"{job_id}: independent capture should be required")
        require(set(record.get("accepted_oracles", [])) == {"mesen2", "bsnes_higan", "mednafen"}, f"{job_id}: accepted oracle set mismatch")
        require(record.get("capture_metadata_path"), f"{job_id}: missing capture metadata path")
        require(record.get("comparison_result_path"), f"{job_id}: missing comparison result path")
        require("import_audio_oracle_reference_capture.py" in str(record.get("import_command")), f"{job_id}: missing import command")
        require("run_audio_independent_oracle_campaign.py" in str(record.get("audit_command")), f"{job_id}: missing audit command")
        require(record.get("promotion_allowed_by_campaign") is False, f"{job_id}: campaign promotion should be blocked")
    require(seen_orders == set(range(1, 17)), "execution orders should be contiguous")
    require(data.get("capture_policy"), "missing capture policy")


def main() -> int:
    args = parse_args()
    data = json.loads(Path(args.report).read_text(encoding="utf-8"))
    validate(data)
    print(
        "Audio independent oracle coverage report validation OK: "
        f"{data['summary']['near_oracle_pass_count']} near-oracle passes, "
        f"{data['summary']['missing_independent_capture_count']} missing independent captures"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
