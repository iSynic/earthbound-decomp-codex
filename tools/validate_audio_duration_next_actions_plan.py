#!/usr/bin/env python3
"""Validate the ranked next-actions plan for audio exact-duration evidence."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PLAN = ROOT / "manifests" / "audio-duration-next-actions-plan.json"
REQUIRED_REFERENCES = {
    "manifests/audio-duration-readiness-rollup.json",
    "manifests/audio-independent-oracle-coverage-report.json",
    "manifests/audio-nonzero-control-coverage-report.json",
    "manifests/audio-zero-runtime-coverage-report.json",
    "manifests/audio-finite-ending-tail-metrics.json",
    "manifests/audio-loop-point-tail-metrics.json",
    "manifests/audio-residual-uncertainty-coverage-report.json",
    "manifests/audio-probe-campaign-plan.json",
}
REQUIRED_LANE_ORDER = [
    "independent_oracle_representative_capture",
    "nonzero_control_probe_import",
    "zero_runtime_probe_import",
    "finite_transition_tail_classification",
    "loop_point_or_hold_classification",
    "residual_public_exact_blockers",
    "pcm_trim_sequence_intent_review",
]
REQUIRED_VALIDATION_COMMANDS = {
    "python tools/build_audio_duration_readiness_rollup.py",
    "python tools/validate_audio_duration_readiness_rollup.py",
    "python tools/build_audio_duration_next_actions_plan.py",
    "python tools/validate_audio_duration_next_actions_plan.py",
    "python tools/validate_audio_export_plan.py",
    "python tools/validate_audio_duration_uncertainty_register.py",
    "python tools/validate_audio_oracle_verification_report.py manifests/audio-oracle-verification-report-all-tracks.json --require-representative-pass",
    "git diff --check",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate audio duration next-actions plan.")
    parser.add_argument("plan", nargs="?", default=str(DEFAULT_PLAN))
    return parser.parse_args()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def lane_by_id(data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(lane.get("lane_id")): lane for lane in data.get("priority_lanes", [])}


def require_commands(lane: dict[str, Any], expected_fragments: list[str]) -> None:
    commands = [str(command) for command in lane.get("commands", [])]
    require(commands, f"{lane.get('lane_id')}: missing commands")
    for fragment in expected_fragments:
        require(any(fragment in command for command in commands), f"{lane.get('lane_id')}: missing command fragment {fragment}")


def validate_lane_basics(lanes: list[dict[str, Any]]) -> None:
    require(len(lanes) == len(REQUIRED_LANE_ORDER), "priority lane count mismatch")
    require([str(lane.get("lane_id")) for lane in lanes] == REQUIRED_LANE_ORDER, "priority lane order mismatch")
    for index, lane in enumerate(lanes, start=1):
        lane_id = str(lane.get("lane_id"))
        require(int(lane.get("priority_rank", 0)) == index, f"{lane_id}: priority rank mismatch")
        require(lane.get("status"), f"{lane_id}: missing status")
        require(lane.get("priority_reason"), f"{lane_id}: missing priority reason")
        require(lane.get("completion_gate"), f"{lane_id}: missing completion gate")
        require(lane.get("promotion_allowed_by_lane") is False, f"{lane_id}: promotion should be blocked")
        require(lane.get("behavior_change_allowed") is False, f"{lane_id}: behavior changes should be blocked")
        require(lane.get("primary_inputs"), f"{lane_id}: missing primary inputs")
        require_commands(lane, [])


def track_ids(lane: dict[str, Any], field: str = "track_refs") -> set[int]:
    return {int(track["track_id"]) for track in lane.get(field, [])}


def validate(data: dict[str, Any]) -> None:
    require(data.get("schema") == "earthbound-decomp.audio-duration-next-actions-plan.v1", "unexpected schema")
    require(data.get("status") == "audio_duration_next_actions_ready_policy_preserved", "unexpected status")
    require(REQUIRED_REFERENCES <= set(data.get("references", [])), "missing references")
    summary = data.get("summary", {})
    require(int(summary.get("priority_lane_count", 0)) == 7, "expected seven priority lanes")
    require(summary.get("release_ready") is False, "release readiness should remain blocked")
    require(summary.get("behavior_change_allowed") is False, "behavior changes should be blocked")
    require(summary.get("promotion_allowed_by_plan") is False, "promotion should be blocked")
    require(int(summary.get("blocking_track_count", 0)) == 171, "expected 171 blocking tracks")
    require(int(summary.get("independent_oracle_representative_jobs", 0)) == 16, "expected 16 independent oracle jobs")
    require(int(summary.get("independent_oracle_representative_missing", 0)) == 16, "expected 16 missing independent captures")
    require(int(summary.get("nonzero_control_probe_jobs", 0)) == 7, "expected 7 nonzero probe jobs")
    require(int(summary.get("nonzero_control_blocker_tracks", 0)) == 155, "expected 155 nonzero blockers")
    require(int(summary.get("zero_runtime_probe_jobs", 0)) == 19, "expected 19 zero probe jobs")
    require(int(summary.get("zero_runtime_blocker_tracks", 0)) == 19, "expected 19 zero blockers")
    require(int(summary.get("finite_transition_tracks", 0)) == 5, "expected 5 finite-transition tracks")
    require(int(summary.get("loop_point_tracks", 0)) == 5, "expected 5 loop-point tracks")
    require(int(summary.get("residual_public_exact_blockers", 0)) == 2, "expected 2 residual public-exact blockers")
    require(int(summary.get("pcm_trim_sequence_intent_tracks", 0)) == 5, "expected 5 PCM-trim sequence-intent tracks")

    lanes = data.get("priority_lanes", [])
    validate_lane_basics(lanes)
    by_id = lane_by_id(data)

    independent = by_id["independent_oracle_representative_capture"]
    require(independent.get("status") == "external_captures_missing", "independent lane status mismatch")
    require(int(independent["counts"].get("representative_job_count", 0)) == 16, "independent lane job count mismatch")
    require(int(independent["counts"].get("representative_missing_independent_capture_count", 0)) == 16, "independent missing count mismatch")
    require(int(independent["counts"].get("all_track_missing_independent_capture_count", 0)) == 190, "all-track independent missing mismatch")
    require(len(independent.get("job_ids", [])) == 16, "independent lane should list 16 jobs")
    require(len(track_ids(independent)) == 16, "independent lane should list 16 tracks")
    require_commands(
        independent,
        [
            "run_audio_independent_oracle_campaign.py --mode audit-existing-captures",
            "build_audio_independent_oracle_capture_packet.py",
            "validate_audio_independent_oracle_capture_packet.py",
            "build_audio_independent_oracle_handoff_matrix.py",
            "validate_audio_independent_oracle_handoff_matrix.py",
            "import_audio_oracle_reference_capture.py",
            "validate_audio_oracle_verification_report.py",
        ],
    )

    nonzero = by_id["nonzero_control_probe_import"]
    require(int(nonzero["counts"].get("blocker_track_count", 0)) == 155, "nonzero blocker count mismatch")
    require(int(nonzero["counts"].get("probe_job_count", 0)) == 7, "nonzero job count mismatch")
    require(int(nonzero["counts"].get("source_candidate_record_count", 0)) == 56, "nonzero source record count mismatch")
    require(int(nonzero["counts"].get("blocker_tracks_without_source_candidate_count", 0)) == 146, "nonzero missing-source count mismatch")
    require(len(nonzero.get("job_ids", [])) == 7, "nonzero lane should list seven coverage jobs")
    require(len(nonzero.get("campaign_job_ids", [])) == 7, "nonzero lane should list seven campaign jobs")
    require(track_ids(nonzero, "source_candidate_track_refs") == {1, 17, 83, 84, 109, 110, 133, 137, 138, 139}, "nonzero source candidate tracks mismatch")
    require_commands(
        nonzero,
        [
            "build_audio_nonzero_control_probe_packet.py",
            "validate_audio_nonzero_control_probe_packet.py",
            "run_audio_probe_campaign.py --lane nonzero",
            "run_audio_nonzero_control_probe_batch.py",
            "collect_audio_nonzero_control_probe_results.py",
        ],
    )

    zero = by_id["zero_runtime_probe_import"]
    require(int(zero["counts"].get("blocker_track_count", 0)) == 19, "zero blocker count mismatch")
    require(int(zero["counts"].get("probe_job_count", 0)) == 19, "zero job count mismatch")
    require(int(zero["counts"].get("reader_pc_target_count", 0)) == 10, "zero reader target count mismatch")
    require(int(zero["counts"].get("runtime_zero_read_count", 0)) == 5931, "zero read count mismatch")
    require(len(zero.get("job_ids", [])) == 19, "zero lane should list 19 coverage jobs")
    require(len(zero.get("campaign_job_ids", [])) == 19, "zero lane should list 19 campaign jobs")
    require(len(track_ids(zero)) == 19, "zero lane should list 19 tracks")
    require_commands(
        zero,
        [
            "build_audio_zero_runtime_probe_packet.py",
            "validate_audio_zero_runtime_probe_packet.py",
            "run_audio_probe_campaign.py --lane zero",
            "run_audio_zero_runtime_probe_batch.py",
            "collect_audio_zero_runtime_probe_results.py",
        ],
    )

    finite = by_id["finite_transition_tail_classification"]
    require(int(finite["counts"].get("track_count", 0)) == 5, "finite track count mismatch")
    require(int(finite["counts"].get("nonzero_after_candidate_end_count", 0)) == 5, "finite nonzero tail count mismatch")
    require(int(finite["counts"].get("active_through_render_boundary_count", 0)) == 3, "finite active-through-boundary count mismatch")
    require(track_ids(finite) == {8, 9, 11, 123, 176}, "finite track coverage mismatch")
    require_commands(
        finite,
        [
            "build_audio_finite_transition_classification_packet.py",
            "validate_audio_finite_transition_classification_packet.py",
            "run_audio_finite_ending_evidence_plan.py",
            "build_audio_finite_ending_tail_metrics.py",
        ],
    )

    loop = by_id["loop_point_or_hold_classification"]
    require(int(loop["counts"].get("track_count", 0)) == 5, "loop track count mismatch")
    require(int(loop["counts"].get("active_through_render_boundary_count", 0)) == 5, "loop active-through-boundary count mismatch")
    require(int(loop["counts"].get("missing_exact_loop_field_count", 0)) == 20, "loop missing field count mismatch")
    require(track_ids(loop) == {5, 6, 115, 183, 184}, "loop track coverage mismatch")
    require_commands(
        loop,
        [
            "build_audio_loop_hold_classification_packet.py",
            "validate_audio_loop_hold_classification_packet.py",
            "run_audio_loop_point_evidence_plan.py",
            "build_audio_loop_point_tail_metrics.py",
        ],
    )

    residual = by_id["residual_public_exact_blockers"]
    require(int(residual["counts"].get("record_count", 0)) == 8, "residual record count mismatch")
    require(int(residual["counts"].get("public_exact_blocked_count", 0)) == 2, "residual blocked count mismatch")
    require(track_ids(residual) == {0, 10}, "residual public-exact blocker tracks mismatch")
    require(residual.get("recommended_actions") == {
        "0": "measure_or_confirm_skip_policy_before_public_export",
        "10": "classify_active_preview_or_find_exact_end_before_public_exact_export",
    }, "residual recommended actions mismatch")
    require_commands(residual, ["build_audio_export_plan.py", "build_audio_duration_uncertainty_register.py"])

    pcm_trim = by_id["pcm_trim_sequence_intent_review"]
    require(int(pcm_trim["counts"].get("pcm_trim_sequence_intent_open_count", 0)) == 5, "PCM trim count mismatch")
    require(int(pcm_trim["counts"].get("public_exact_allowed_count", 0)) == 6, "residual public-exact allowed count mismatch")
    require(track_ids(pcm_trim) == {12, 13, 14, 15, 135}, "PCM trim track coverage mismatch")
    require_commands(pcm_trim, ["validate_audio_sequence_semantics_intake_plan.py", "validate_audio_export_plan.py"])

    require(REQUIRED_VALIDATION_COMMANDS <= set(data.get("post_completion_validation_commands", [])), "missing post-completion validation commands")
    require(data.get("decision_policy"), "missing decision policy")


def main() -> int:
    args = parse_args()
    data = json.loads(Path(args.plan).read_text(encoding="utf-8"))
    validate(data)
    print(
        "Audio duration next-actions plan validation OK: "
        f"{data['summary']['priority_lane_count']} lanes, "
        f"{data['summary']['blocking_track_count']} blocking tracks"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
