#!/usr/bin/env python3
"""Validate the source-evidence regeneration plan for oracle comparison inputs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PLAN = ROOT / "manifests" / "audio-oracle-source-regeneration-plan.json"
REQUIRED_REFERENCES = {
    "manifests/audio-oracle-source-evidence-preflight.json",
    "manifests/audio-independent-oracle-handoff-matrix.json",
    "manifests/audio-duration-next-actions-plan.json",
    "notes/audio-backend-contract.md",
}
REQUIRED_STAGE_ORDER = [
    "preflight_current_gap",
    "all_track_fusion_source_spc",
    "spc_index_and_renderer_jobs",
    "libgme_render_and_metrics",
    "playback_oracle_plan_refresh",
    "reference_capture_and_collection",
]
REQUIRED_REPRESENTATIVE_TRACK_IDS = {1, 5, 8, 10, 12, 17, 25, 32, 46, 115, 123, 135, 161, 171, 173, 175}
ALLOWED_PREFLIGHT_STATUSES = {
    "oracle_source_evidence_preflight_blocked_missing_ignored_artifacts",
    "oracle_source_evidence_preflight_source_ready_reference_captures_pending",
    "oracle_source_evidence_preflight_ready_for_collection",
}
REQUIRED_COMMAND_FRAGMENTS = {
    "preflight_current_gap": [
        "build_audio_oracle_source_evidence_preflight.py",
        "validate_audio_oracle_source_evidence_preflight.py",
    ],
    "all_track_fusion_source_spc": [
        "collect_audio_c0ab06_change_music_fusion_frontier.py --all-tracks",
        "validate_audio_c0ab06_change_music_fusion_frontier.py",
    ],
    "spc_index_and_renderer_jobs": [
        "build_audio_c0ab06_change_music_fusion_spc_index.py",
        "build_audio_backend_jobs_from_spc_index.py",
        "validate_audio_backend_jobs.py",
    ],
    "libgme_render_and_metrics": [
        "cmake -S tools/libgme_audio_harness",
        "run_audio_backend_batch.py",
        "validate_audio_backend_result_summary.py",
        "collect_audio_render_metrics.py",
        "validate_audio_render_metrics.py",
    ],
    "playback_oracle_plan_refresh": [
        "build_audio_playback_export_manifest.py",
        "validate_audio_playback_export_manifest.py",
        "build_audio_oracle_comparison_plan.py --all-tracks",
        "validate_audio_oracle_comparison_plan.py",
        "build_audio_oracle_source_evidence_preflight.py",
        "validate_audio_oracle_source_evidence_preflight.py",
    ],
    "reference_capture_and_collection": [
        "import_audio_oracle_reference_capture.py",
        "validate_audio_oracle_reference_capture.py",
        "collect_audio_oracle_comparison_results.py",
        "validate_audio_oracle_comparison_summary.py",
        "build_audio_oracle_verification_report.py",
        "validate_audio_oracle_verification_report.py",
    ],
}
REQUIRED_POST_COMMANDS = {
    "python tools/build_audio_oracle_source_regeneration_plan.py",
    "python tools/validate_audio_oracle_source_regeneration_plan.py",
    "python tools/validate_audio_oracle_source_evidence_preflight.py",
    "python tools/validate_audio_oracle_comparison_plan.py manifests/audio-oracle-comparison-plan-all-tracks.json --allow-missing-source-outputs",
    "python tools/validate_audio_oracle_verification_report.py manifests/audio-oracle-verification-report-all-tracks.json --require-representative-pass",
    "python tools/validate_audio_independent_oracle_handoff_matrix.py",
    "python tools/validate_audio_independent_oracle_capture_packet.py",
    "python tools/validate_audio_duration_next_actions_plan.py",
    "git diff --check",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate oracle source-evidence regeneration plan.")
    parser.add_argument("plan", nargs="?", default=str(DEFAULT_PLAN))
    return parser.parse_args()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def require_commands(stage: dict[str, Any]) -> None:
    stage_id = str(stage.get("stage_id"))
    commands = [str(command) for command in stage.get("commands", [])]
    require(commands, f"{stage_id}: missing commands")
    for fragment in REQUIRED_COMMAND_FRAGMENTS[stage_id]:
        require(any(fragment in command for command in commands), f"{stage_id}: missing command fragment {fragment}")


def validate_stages(stages: list[dict[str, Any]]) -> None:
    require([str(stage.get("stage_id")) for stage in stages] == REQUIRED_STAGE_ORDER, "stage order mismatch")
    for index, stage in enumerate(stages, start=1):
        stage_id = str(stage.get("stage_id"))
        require(int(stage.get("rank", 0)) == index, f"{stage_id}: rank mismatch")
        require(stage.get("purpose"), f"{stage_id}: missing purpose")
        require(stage.get("completion_gate"), f"{stage_id}: missing completion gate")
        require(stage.get("behavior_change_allowed") is False, f"{stage_id}: behavior changes should be blocked")
        require_commands(stage)

    by_id = {str(stage["stage_id"]): stage for stage in stages}
    frontier_outputs = by_id["all_track_fusion_source_spc"].get("expected_outputs", {})
    require(int(frontier_outputs.get("expected_load_paths", 0)) == 191, "expected 191 fused load paths")
    require(int(frontier_outputs.get("expected_payload_matches", 0)) == 191, "expected 191 payload matches")
    require(int(frontier_outputs.get("expected_key_on_snapshots", 0)) == 190, "expected 190 key-on snapshots")
    require(frontier_outputs.get("known_no_key_on_track", {}).get("track_id") == 4, "expected track 4 as no-key-on skip")
    renderer_outputs = by_id["spc_index_and_renderer_jobs"].get("expected_outputs", {})
    require(int(renderer_outputs.get("expected_renderer_jobs", 0)) == 190, "expected 190 renderer jobs")
    require(int(renderer_outputs.get("expected_skipped_records", 0)) == 1, "expected one renderer skip")
    render_metrics = by_id["libgme_render_and_metrics"].get("expected_outputs", {})
    require(int(render_metrics.get("expected_ok_results", 0)) == 190, "expected 190 backend OK results")
    require(int(render_metrics.get("expected_audible_metrics", 0)) == 190, "expected 190 audible metrics")
    oracle_outputs = by_id["playback_oracle_plan_refresh"].get("expected_outputs", {})
    require(int(oracle_outputs.get("expected_oracle_jobs", 0)) == 190, "expected 190 oracle jobs")
    reference_outputs = by_id["reference_capture_and_collection"].get("expected_outputs", {})
    require(int(reference_outputs.get("representative_jobs", 0)) == 16, "expected 16 representative jobs")
    require(int(reference_outputs.get("all_track_jobs", 0)) == 190, "expected 190 all-track jobs")


def validate_representatives(records: list[dict[str, Any]]) -> None:
    require(len(records) == 16, "expected 16 representative handoff tracks")
    track_ids = {int(record.get("track_id", -1)) for record in records}
    require(track_ids == REQUIRED_REPRESENTATIVE_TRACK_IDS, "representative track coverage mismatch")
    orders = [int(record.get("execution_order", 0)) for record in records]
    require(orders == list(range(1, 17)), "representative execution order mismatch")
    for record in records:
        require(record.get("track_name"), f"{record.get('track_id')}: missing track name")
        require(record.get("phase"), f"{record.get('track_id')}: missing phase")
        require(record.get("primary_uncertainty"), f"{record.get('track_id')}: missing uncertainty")


def validate(data: dict[str, Any]) -> None:
    require(data.get("schema") == "earthbound-decomp.audio-oracle-source-regeneration-plan.v1", "unexpected schema")
    require(data.get("status") == "oracle_source_regeneration_plan_ready_policy_preserved", "unexpected status")
    require(REQUIRED_REFERENCES <= set(data.get("references", [])), "missing references")
    require(data.get("source_preflight_status") in ALLOWED_PREFLIGHT_STATUSES, "unexpected source preflight status")
    require(data.get("source_handoff_status") == "independent_oracle_handoff_matrix_ready_external_inputs_required", "unexpected handoff status")
    require(data.get("source_next_action_lane") == "independent_oracle_representative_capture", "unexpected next action lane")
    summary = data.get("summary", {})
    require(int(summary.get("stage_count", 0)) == len(REQUIRED_STAGE_ORDER), "stage count mismatch")
    require(int(summary.get("all_track_oracle_jobs", 0)) == 190, "expected 190 oracle jobs")
    require(int(summary.get("representative_capture_jobs", 0)) == 16, "expected 16 representative capture jobs")
    require(int(summary.get("expected_source_spc_after_regeneration", 0)) == 190, "expected 190 source SPCs")
    require(int(summary.get("expected_source_render_wav_after_regeneration", 0)) == 190, "expected 190 source render WAVs")
    require(int(summary.get("expected_known_no_keyon_skips", 0)) == 1, "expected one no-key-on skip")
    require(summary.get("behavior_change_allowed") is False, "behavior changes should be blocked")
    require(summary.get("promotion_allowed_by_plan") is False, "promotion should be blocked")
    require(int(summary.get("current_collector_ready_jobs", -1)) >= 0, "bad ready count")
    require(int(summary.get("current_source_blocked_jobs", -1)) >= 0, "bad source-blocked count")
    require(int(summary.get("current_source_spc_present_count", -1)) >= 0, "bad source SPC count")
    require(int(summary.get("current_source_render_wav_present_count", -1)) >= 0, "bad source WAV count")
    require(
        int(summary.get("current_collector_ready_jobs", 0))
        + int(summary.get("current_source_blocked_jobs", 0))
        <= int(summary.get("all_track_oracle_jobs", 0)),
        "current preflight counts exceed all-track jobs",
    )
    validate_representatives(data.get("representative_handoff_tracks", []))
    validate_stages(data.get("stages", []))
    policy = data.get("regeneration_policy", [])
    require(len(policy) >= 4, "missing regeneration policy")
    require(any("does not change playback/export behavior" in str(item) for item in policy), "missing behavior-preservation policy")
    require(REQUIRED_POST_COMMANDS <= set(data.get("post_plan_validation_commands", [])), "missing post-plan validation commands")


def main() -> int:
    args = parse_args()
    data = json.loads(Path(args.plan).read_text(encoding="utf-8"))
    validate(data)
    print(
        "Audio oracle source regeneration plan validation OK: "
        f"{data['summary']['stage_count']} stages, "
        f"{data['summary']['current_source_blocked_jobs']} source-blocked jobs"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
