#!/usr/bin/env python3
"""Validate the consolidated audio exact-duration readiness rollup."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ROLLUP = ROOT / "manifests" / "audio-duration-readiness-rollup.json"
REQUIRED_REFERENCES = {
    "manifests/audio-duration-uncertainty-register.json",
    "manifests/audio-finite-ending-tail-metrics.json",
    "manifests/audio-loop-point-tail-metrics.json",
    "manifests/audio-oracle-verification-report-all-tracks.json",
    "manifests/audio-independent-oracle-campaign-plan.json",
    "manifests/audio-independent-oracle-coverage-report.json",
    "manifests/audio-probe-campaign-plan.json",
    "manifests/audio-nonzero-control-coverage-report.json",
    "manifests/audio-zero-runtime-coverage-report.json",
}
REQUIRED_GATES = {
    "public_exact_duration_gate",
    "finite_ending_tail_gate",
    "loop_point_tail_gate",
    "near_oracle_gate",
    "independent_oracle_gate",
    "sequence_promotion_gate",
    "nonzero_control_coverage_gate",
    "zero_runtime_coverage_gate",
}
REQUIRED_LANES = {
    "non_zero_control_semantics",
    "zero_runtime_probe",
    "finite_transition_review",
    "loop_point_metadata",
    "independent_oracle",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate audio duration readiness rollup.")
    parser.add_argument("rollup", nargs="?", default=str(DEFAULT_ROLLUP))
    return parser.parse_args()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def validate(data: dict[str, Any]) -> None:
    require(data.get("schema") == "earthbound-decomp.audio-duration-readiness-rollup.v1", "unexpected schema")
    require(data.get("status") == "audio_duration_readiness_blocked_policy_preserved", "unexpected status")
    require(REQUIRED_REFERENCES <= set(data.get("references", [])), "missing references")
    summary = data.get("summary", {})
    require(int(summary.get("track_count", 0)) == 192, "expected 192 tracks")
    public_exact = int(summary.get("public_exact_duration_track_count", -1))
    blocking_tracks = int(summary.get("blocking_track_count", -1))
    require(0 <= public_exact < 192, "public exact duration count should be incomplete")
    require(blocking_tracks == 192 - public_exact, "blocking track count mismatch")
    require(summary.get("near_oracle_passed") is True, "near-oracle gate should currently pass")
    require(summary.get("independent_oracle_passed") is False, "independent oracle gate should currently fail")
    require(
        int(summary.get("independent_oracle_representative_missing", -1)) == 16,
        "expected 16 missing representative independent captures",
    )
    require(int(summary.get("finite_tail_records", 0)) == 5, "expected 5 finite tail records")
    require(int(summary.get("loop_tail_records", 0)) == 5, "expected 5 loop tail records")
    require(int(summary.get("probe_campaign_jobs", 0)) == 26, "expected 26 probe campaign jobs")
    require(int(summary.get("nonzero_coverage_probe_jobs", 0)) == 7, "expected 7 nonzero coverage probe jobs")
    require(
        int(summary.get("nonzero_blocker_tracks_without_source_candidate", 0)) == 146,
        "expected 146 nonzero blockers without source candidate",
    )
    require(int(summary.get("zero_coverage_probe_jobs", 0)) == 19, "expected 19 zero coverage probe jobs")
    require(int(summary.get("zero_runtime_reader_pc_targets", 0)) == 10, "expected 10 zero runtime reader PC targets")
    require(summary.get("release_ready") is False, "release readiness should remain blocked")
    require(summary.get("current_playback_export_behavior_preserved") is True, "behavior preservation flag missing")
    primary_counts = summary.get("primary_uncertainty_track_counts", {})
    for key in (
        "non_zero_control_semantics_pending",
        "zero_runtime_probe_pending",
        "finite_transition_review_pending",
        "loop_point_metadata_pending",
    ):
        require(int(primary_counts.get(key, 0)) > 0, f"missing primary uncertainty count {key}")

    gates = data.get("gates", {})
    require(set(gates) == REQUIRED_GATES, "gate coverage mismatch")
    public_gate = gates["public_exact_duration_gate"]
    require(public_gate.get("passed") is False, "public exact duration gate should fail")
    require(int(public_gate.get("blocking_track_count", -1)) == blocking_tracks, "public gate blocking count mismatch")
    finite_gate = gates["finite_ending_tail_gate"]
    require(finite_gate.get("passed") is False, "finite tail gate should fail")
    require(int(finite_gate.get("records", 0)) == 5, "finite gate record count mismatch")
    require(int(finite_gate.get("nonzero_after_candidate_end_count", 0)) == 5, "finite gate should see five post-candidate tails")
    loop_gate = gates["loop_point_tail_gate"]
    require(loop_gate.get("passed") is False, "loop tail gate should fail")
    require(int(loop_gate.get("records", 0)) == 5, "loop gate record count mismatch")
    require(int(loop_gate.get("missing_exact_loop_field_count", 0)) == 20, "loop gate missing field count mismatch")
    require(gates["near_oracle_gate"].get("passed") is True, "near oracle gate should pass")
    independent_gate = gates["independent_oracle_gate"]
    require(independent_gate.get("passed") is False, "independent oracle gate should fail")
    require(int(independent_gate.get("missing_independent_capture_count", 0)) == 190, "expected 190 missing independent captures")
    require(
        int(independent_gate.get("representative_missing_independent_capture_count", -1)) == 16,
        "expected 16 missing representative independent captures",
    )
    sequence_gate = gates["sequence_promotion_gate"]
    require(sequence_gate.get("passed") is False, "sequence promotion gate should fail")
    require(sequence_gate.get("uncertainty_register_allows_sequence_promotion") is False, "uncertainty sequence promotion should be blocked")
    require(sequence_gate.get("probe_campaign_allows_sequence_promotion") is False, "probe campaign sequence promotion should be blocked")
    nonzero_gate = gates["nonzero_control_coverage_gate"]
    require(nonzero_gate.get("passed") is False, "nonzero coverage gate should fail")
    require(int(nonzero_gate.get("blocker_track_count", 0)) == 155, "nonzero coverage blocker count mismatch")
    require(int(nonzero_gate.get("probe_job_count", 0)) == 7, "nonzero coverage probe job count mismatch")
    require(int(nonzero_gate.get("source_candidate_record_count", 0)) == 56, "nonzero coverage source record count mismatch")
    require(int(nonzero_gate.get("unique_source_candidate_track_count", 0)) == 10, "nonzero coverage unique track count mismatch")
    require(
        int(nonzero_gate.get("blocker_tracks_without_source_candidate_count", 0)) == 146,
        "nonzero coverage missing-source count mismatch",
    )
    zero_gate = gates["zero_runtime_coverage_gate"]
    require(zero_gate.get("passed") is False, "zero runtime coverage gate should fail")
    require(int(zero_gate.get("blocker_track_count", 0)) == 19, "zero runtime blocker count mismatch")
    require(int(zero_gate.get("probe_job_count", 0)) == 19, "zero runtime probe job count mismatch")
    require(zero_gate.get("job_track_coverage_exact") is True, "zero runtime should exactly cover blockers")
    require(int(zero_gate.get("reader_pc_target_count", 0)) == 10, "zero runtime reader target count mismatch")
    require(int(zero_gate.get("runtime_zero_read_count", 0)) == 5931, "zero runtime read count mismatch")
    require(
        zero_gate.get("pre_promotion_blocker_counts") == {"ef_return_stack_model": 15, "zero_runtime_effect_proof": 19},
        "zero runtime blocker counts mismatch",
    )

    lanes = data.get("blocker_lanes", [])
    require({str(lane.get("lane")) for lane in lanes} == REQUIRED_LANES, "blocker lane coverage mismatch")
    for lane in lanes:
        require(int(lane.get("blocking_count", -1)) >= 0, f"{lane.get('lane')}: invalid blocker count")
        require(lane.get("current_contract"), f"{lane.get('lane')}: missing current contract")
        require(lane.get("next_action"), f"{lane.get('lane')}: missing next action")
    require(data.get("decision_policy"), "missing decision policy")


def main() -> int:
    args = parse_args()
    data = json.loads(Path(args.rollup).read_text(encoding="utf-8"))
    validate(data)
    print(
        "Audio duration readiness rollup validation OK: "
        f"{data['summary']['blocking_track_count']} blocking tracks, "
        f"release_ready={data['summary']['release_ready']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
