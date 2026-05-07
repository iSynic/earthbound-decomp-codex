#!/usr/bin/env python3
"""Validate the oracle source-evidence preflight report."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PREFLIGHT = ROOT / "manifests" / "audio-oracle-source-evidence-preflight.json"
REQUIRED_REFERENCES = {
    "manifests/audio-oracle-comparison-plan-all-tracks.json",
    "manifests/audio-oracle-verification-report-all-tracks.json",
    "manifests/audio-independent-oracle-handoff-matrix.json",
}
REQUIRED_FOCUS_COUNTS = {
    "active_through_preview_or_loop_candidate": 149,
    "finite_tail_or_transition_end": 26,
    "general_playback_equivalence": 15,
}
REQUIRED_REP_PHASE_COUNTS = {
    "independent-duration-uncertainty-coverage": 4,
    "independent-probe-source-coverage": 5,
    "independent-representative-core": 7,
}
REQUIRED_REPRESENTATIVE_TRACK_IDS = {1, 5, 8, 10, 12, 17, 25, 32, 46, 115, 123, 135, 161, 171, 173, 175}
SHA1_RE = re.compile(r"^[0-9a-f]{40}$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate oracle source-evidence preflight report.")
    parser.add_argument("preflight", nargs="?", default=str(DEFAULT_PREFLIGHT))
    return parser.parse_args()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def count_records(records: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for record in records:
        counts[str(record.get(key))] += 1
    return dict(sorted(counts.items()))


def validate_paths(record: dict[str, Any]) -> None:
    job_id = str(record.get("job_id"))
    source_spc = record.get("source_spc", {})
    source_render = record.get("source_render", {})
    reference = record.get("reference_outputs", {})
    require(str(source_spc.get("path", "")).endswith(".spc"), f"{job_id}: source SPC path missing")
    require(bool(SHA1_RE.match(str(source_spc.get("expected_sha1", "")))), f"{job_id}: invalid source SPC sha1")
    require(int(source_spc.get("expected_bytes", 0)) == 66048, f"{job_id}: source SPC expected bytes mismatch")
    require(str(source_render.get("path", "")).endswith(".wav"), f"{job_id}: source render path missing")
    require(bool(SHA1_RE.match(str(source_render.get("expected_sha1", "")))), f"{job_id}: invalid source render sha1")
    require(int(source_render.get("expected_bytes", 0)) > 0, f"{job_id}: source render expected bytes missing")
    require(str(reference.get("spc_snapshot", "")).startswith("build/audio/oracle-comparison-all-tracks/"), f"{job_id}: bad reference SPC path")
    require(str(reference.get("pcm_wav", "")).startswith("build/audio/oracle-comparison-all-tracks/"), f"{job_id}: bad reference WAV path")
    require(str(reference.get("capture_metadata", "")).endswith("reference-capture.json"), f"{job_id}: bad capture metadata path")
    require(str(reference.get("comparison_result", "")).endswith("oracle-comparison-result.json"), f"{job_id}: bad comparison result path")


def validate_record(record: dict[str, Any]) -> None:
    job_id = str(record.get("job_id"))
    track_id = int(record.get("track_id", -1))
    require(job_id.startswith("oracle-track-"), f"{job_id}: unexpected job id")
    require(1 <= track_id <= 191, f"{job_id}: unexpected track id")
    require(record.get("diagnostic_focus") in REQUIRED_FOCUS_COUNTS, f"{job_id}: unexpected diagnostic focus")
    require(record.get("source_state") == "full_change_music_real_c0ab06_live_driver_zero_burst_keyon_snapshot", f"{job_id}: source state mismatch")
    validate_paths(record)
    source_spc_exists = bool(record.get("source_spc", {}).get("exists"))
    source_render_exists = bool(record.get("source_render", {}).get("exists"))
    reference = record.get("reference_outputs", {})
    reference_spc_exists = bool(reference.get("spc_snapshot_exists"))
    reference_wav_exists = bool(reference.get("pcm_wav_exists"))
    expected_reasons: set[str] = set()
    if not source_spc_exists:
        expected_reasons.add("missing_source_spc")
    if not source_render_exists:
        expected_reasons.add("missing_source_render_wav")
    if not reference_spc_exists:
        expected_reasons.add("missing_reference_spc")
    if not reference_wav_exists:
        expected_reasons.add("missing_reference_wav")
    if not bool(reference.get("capture_metadata_exists")):
        expected_reasons.add("missing_capture_metadata")
    if not bool(reference.get("comparison_result_exists")):
        expected_reasons.add("missing_comparison_result")
    if source_spc_exists and source_render_exists and reference_spc_exists and reference_wav_exists:
        expected_status = "collector_ready_for_job"
    elif not source_spc_exists or not source_render_exists:
        expected_status = "collector_blocked_missing_source_evidence"
    else:
        expected_status = "collector_pending_reference_capture"
    require(record.get("collector_preflight_status") == expected_status, f"{job_id}: collector status mismatch")
    require(set(record.get("blocking_reasons", [])) == expected_reasons, f"{job_id}: blocking reasons mismatch")
    require(record.get("collect_summary_validation_ready") is (expected_status == "collector_ready_for_job"), f"{job_id}: collect readiness mismatch")
    require(record.get("behavior_change_allowed") is False, f"{job_id}: behavior changes should be blocked")
    if record.get("independent_representative"):
        require(track_id in REQUIRED_REPRESENTATIVE_TRACK_IDS, f"{job_id}: unexpected representative track")
        require(record.get("representative_phase") in REQUIRED_REP_PHASE_COUNTS, f"{job_id}: bad representative phase")
        require(record.get("representative_primary_uncertainty"), f"{job_id}: missing representative uncertainty")
    else:
        require(track_id not in REQUIRED_REPRESENTATIVE_TRACK_IDS, f"{job_id}: missing representative marker")
        require(record.get("representative_phase") is None, f"{job_id}: non-representative phase should be null")
        require(record.get("representative_primary_uncertainty") is None, f"{job_id}: non-representative uncertainty should be null")


def validate_batches(data: dict[str, Any]) -> None:
    batches = data.get("operator_batches", {})
    status_batches = {
        batch.get("collector_preflight_status"): int(batch.get("job_count", 0))
        for batch in batches.get("by_collector_preflight_status", [])
    }
    focus_batches = {
        batch.get("diagnostic_focus"): int(batch.get("job_count", 0))
        for batch in batches.get("by_diagnostic_focus", [])
    }
    phase_batches = {
        batch.get("representative_phase"): int(batch.get("job_count", 0))
        for batch in batches.get("by_representative_phase", [])
    }
    require(status_batches, "collector status batches missing")
    require(focus_batches == REQUIRED_FOCUS_COUNTS, "diagnostic focus batches mismatch")
    require(phase_batches == REQUIRED_REP_PHASE_COUNTS, "representative phase batches mismatch")
    for group in batches.values():
        for batch in group:
            count = int(batch.get("job_count", 0))
            require(len(batch.get("track_ids", [])) == count, "batch track count mismatch")
            require(len(batch.get("job_ids", [])) == count, "batch job count mismatch")


def validate(data: dict[str, Any]) -> None:
    require(data.get("schema") == "earthbound-decomp.audio-oracle-source-evidence-preflight.v1", "unexpected schema")
    require(
        data.get("status")
        in {
            "oracle_source_evidence_preflight_blocked_missing_ignored_artifacts",
            "oracle_source_evidence_preflight_source_ready_reference_captures_pending",
            "oracle_source_evidence_preflight_ready_for_collection",
        },
        "unexpected status",
    )
    require(data.get("source_plan_status") == "oracle_plan_ready_no_reference_captures_yet", "unexpected plan status")
    require(data.get("source_verification_status") == "all_track_near_oracle_passed_independent_oracle_pending", "unexpected verification status")
    require(data.get("source_handoff_status") == "independent_oracle_handoff_matrix_ready_external_inputs_required", "unexpected handoff status")
    require(REQUIRED_REFERENCES <= set(data.get("references", [])), "missing references")
    summary = data.get("summary", {})
    records = data.get("records", [])
    require(int(summary.get("job_count", 0)) == 190, "expected 190 oracle jobs")
    require(len(records) == 190, "record count mismatch")
    ready_count = sum(1 for record in records if record.get("collector_preflight_status") == "collector_ready_for_job")
    source_blocked_count = sum(
        1 for record in records if record.get("collector_preflight_status") == "collector_blocked_missing_source_evidence"
    )
    pending_reference_count = sum(
        1 for record in records if record.get("collector_preflight_status") == "collector_pending_reference_capture"
    )
    require(int(summary.get("collector_ready_job_count", -1)) == ready_count, "collector-ready count mismatch")
    require(int(summary.get("collector_blocked_missing_source_evidence_count", -1)) == source_blocked_count, "source-blocked count mismatch")
    require(int(summary.get("collector_pending_reference_capture_count", -1)) == pending_reference_count, "pending-reference-only count mismatch")
    expected_presence_counts = {
        "source_spc_present_count": sum(1 for record in records if record.get("source_spc", {}).get("exists")),
        "source_render_wav_present_count": sum(1 for record in records if record.get("source_render", {}).get("exists")),
        "reference_spc_present_count": sum(1 for record in records if record.get("reference_outputs", {}).get("spc_snapshot_exists")),
        "reference_wav_present_count": sum(1 for record in records if record.get("reference_outputs", {}).get("pcm_wav_exists")),
        "capture_metadata_present_count": sum(1 for record in records if record.get("reference_outputs", {}).get("capture_metadata_exists")),
        "comparison_result_present_count": sum(1 for record in records if record.get("reference_outputs", {}).get("comparison_result_exists")),
    }
    for key, count in expected_presence_counts.items():
        require(int(summary.get(key, -1)) == count, f"{key} count mismatch")
    require(int(summary.get("representative_job_count", 0)) == 16, "representative job count mismatch")
    expected_blocking_counts: Counter[str] = Counter()
    for record in records:
        expected_blocking_counts.update(str(reason) for reason in record.get("blocking_reasons", []))
    require(summary.get("blocking_reason_counts") == dict(sorted(expected_blocking_counts.items())), "blocking reason counts mismatch")
    require(summary.get("collector_preflight_status_counts") == count_records(records, "collector_preflight_status"), "collector status counts mismatch")
    require(summary.get("diagnostic_focus_counts") == REQUIRED_FOCUS_COUNTS, "focus counts mismatch")
    require(summary.get("representative_oracle_gate_passed") is True, "representative near-oracle gate should pass")
    require(summary.get("all_track_oracle_gate_passed") is True, "all-track near-oracle gate should pass")
    require(summary.get("independent_emulator_gate_passed") is False, "independent gate should be blocked")
    require(summary.get("release_quality_playback_claim_ready") is False, "release-quality claim should be blocked")
    require(summary.get("behavior_change_allowed") is False, "behavior changes should be blocked")
    require(summary.get("collector_preflight_status_counts") == count_records(records, "collector_preflight_status"), "status counts do not match records")
    require(summary.get("diagnostic_focus_counts") == count_records(records, "diagnostic_focus"), "focus counts do not match records")
    representative_tracks: set[int] = set()
    seen_tracks: set[int] = set()
    for record in records:
        track_id = int(record.get("track_id", -1))
        require(track_id not in seen_tracks, f"{record.get('job_id')}: duplicate track")
        seen_tracks.add(track_id)
        if record.get("independent_representative"):
            representative_tracks.add(track_id)
        validate_record(record)
    require(len(seen_tracks) == 190, "track coverage mismatch")
    require(representative_tracks == REQUIRED_REPRESENTATIVE_TRACK_IDS, "representative coverage mismatch")
    validate_batches(data)
    require(data.get("preflight_policy"), "missing preflight policy")
    required_commands = {
        "python tools/build_audio_oracle_source_evidence_preflight.py",
        "python tools/validate_audio_oracle_source_evidence_preflight.py",
        "python tools/validate_audio_oracle_comparison_plan.py manifests/audio-oracle-comparison-plan-all-tracks.json --allow-missing-source-outputs",
        "python tools/validate_audio_oracle_verification_report.py manifests/audio-oracle-verification-report-all-tracks.json --require-representative-pass",
        "python tools/validate_audio_independent_oracle_handoff_matrix.py",
        "python tools/validate_audio_independent_oracle_capture_packet.py",
        "python tools/build_audio_oracle_source_regeneration_plan.py",
        "python tools/validate_audio_oracle_source_regeneration_plan.py",
    }
    require(required_commands <= set(data.get("post_preflight_validation_commands", [])), "missing post-preflight validation commands")


def main() -> int:
    args = parse_args()
    data = json.loads(Path(args.preflight).read_text(encoding="utf-8"))
    validate(data)
    print(
        "Audio oracle source evidence preflight validation OK: "
        f"{data['summary']['collector_ready_job_count']} ready, "
        f"{data['summary']['collector_blocked_missing_source_evidence_count']} source-blocked"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
