#!/usr/bin/env python3
"""Validate the independent oracle handoff matrix."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MATRIX = ROOT / "manifests" / "audio-independent-oracle-handoff-matrix.json"
REQUIRED_REFERENCES = {
    "manifests/audio-independent-oracle-capture-packet.json",
    "build/audio/independent-oracle-campaign-runs/independent-oracle-campaign-run-summary.json",
    "manifests/audio-independent-oracle-coverage-report.json",
    "manifests/audio-oracle-verification-report-all-tracks.json",
    "manifests/audio-duration-next-actions-plan.json",
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
REQUIRED_FOCUS_COUNTS = {
    "active_through_preview_or_loop_candidate": 9,
    "finite_tail_or_transition_end": 4,
    "general_playback_equivalence": 3,
}
REQUIRED_DURATION_BUCKET_COUNTS = {
    "diagnostic_30s": 7,
    "long_preview_120s": 2,
    "short_finite_candidate": 7,
}
REQUIRED_METADATA_FIELDS = {
    "oracle_id",
    "oracle_kind",
    "independent_emulator_capture",
    "emulator_version",
    "capture_command",
    "audio_settings",
    "source_spc_sha1",
    "reference_wav_sha1",
    "render_sample_rate",
    "channels",
    "bits_per_sample",
    "duration_seconds",
}
REQUIRED_POST_COMMANDS = {
    "python tools/build_audio_independent_oracle_handoff_matrix.py",
    "python tools/validate_audio_independent_oracle_handoff_matrix.py",
    "python tools/run_audio_independent_oracle_campaign.py --mode audit-existing-captures",
    "python tools/validate_audio_independent_oracle_campaign_run_summary.py",
    "python tools/validate_audio_independent_oracle_capture_packet.py",
    "python tools/validate_audio_independent_oracle_coverage_report.py",
    "python tools/validate_audio_oracle_verification_report.py manifests/audio-oracle-verification-report-all-tracks.json --require-representative-pass",
    "python tools/build_audio_duration_readiness_rollup.py",
    "python tools/validate_audio_duration_readiness_rollup.py",
}
SHA1_RE = re.compile(r"^[0-9a-f]{40}$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate independent oracle handoff matrix.")
    parser.add_argument("matrix", nargs="?", default=str(DEFAULT_MATRIX))
    return parser.parse_args()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def count_records(records: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for record in records:
        counts[str(record.get(key))] += 1
    return dict(sorted(counts.items()))


def validate_source(job_id: str, record: dict[str, Any]) -> None:
    source_spc = record.get("source_spc", {})
    source_render = record.get("source_render", {})
    require(str(source_spc.get("path", "")).endswith(".spc"), f"{job_id}: source SPC path missing")
    require(bool(SHA1_RE.match(str(source_spc.get("sha1", "")))), f"{job_id}: invalid source SPC sha1")
    require(int(source_spc.get("bytes", 0)) == 66048, f"{job_id}: source SPC byte count mismatch")
    require(str(source_render.get("path", "")).endswith(".wav"), f"{job_id}: source render path missing")
    require(bool(SHA1_RE.match(str(source_render.get("sha1", "")))), f"{job_id}: invalid source render sha1")
    require(int(source_render.get("bytes", 0)) > 0, f"{job_id}: source render byte count missing")


def validate_targets(job_id: str, targets: dict[str, Any]) -> None:
    require(str(targets.get("spc_snapshot", "")).startswith("build/audio/oracle-comparison-all-tracks/"), f"{job_id}: bad SPC target")
    require(str(targets.get("pcm_wav", "")).startswith("build/audio/oracle-comparison-all-tracks/"), f"{job_id}: bad WAV target")
    require(str(targets.get("capture_metadata", "")).endswith("reference-capture.json"), f"{job_id}: bad metadata target")
    require(str(targets.get("comparison_result", "")).endswith("oracle-comparison-result.json"), f"{job_id}: bad comparison target")


def validate_audit(job_id: str, audit: dict[str, Any]) -> None:
    require(audit.get("status") == "pending_independent_capture", f"{job_id}: audit status mismatch")
    require(audit.get("blocking_reasons") == ["missing_capture_metadata"], f"{job_id}: blocking reason mismatch")
    require(audit.get("capture_metadata_exists") is False, f"{job_id}: metadata should be absent")
    require(set(audit.get("missing_metadata_fields", [])) == REQUIRED_METADATA_FIELDS, f"{job_id}: missing metadata fields mismatch")
    for field in (
        "independent_emulator_capture",
        "source_spc_sha1_matches",
        "spc_exists",
        "wav_exists",
        "wav_format_matches_policy",
        "duration_covers_planned",
    ):
        require(audit.get(field) is False, f"{job_id}: {field} should be false before import")


def validate_commands(job_id: str, commands: dict[str, Any]) -> None:
    required = {
        "import": "import_audio_oracle_reference_capture.py",
        "validate_capture": "validate_audio_oracle_reference_capture.py",
        "audit": "run_audio_independent_oracle_campaign.py",
        "collect_comparison": "collect_audio_oracle_comparison_results.py",
        "refresh_report": "build_audio_oracle_verification_report.py",
        "validate_report": "validate_audio_oracle_verification_report.py",
    }
    for key, fragment in required.items():
        require(fragment in str(commands.get(key, "")), f"{job_id}: missing handoff command {key}")


def validate_record(record: dict[str, Any]) -> None:
    job_id = str(record.get("job_id"))
    track_id = int(record.get("track_id", -1))
    planned_seconds = float(record.get("planned_duration_seconds", 0.0))
    require(job_id.startswith("oracle-track-"), f"{job_id}: unexpected job id")
    require(track_id > 0, f"{job_id}: invalid track id")
    require(record.get("phase") in REQUIRED_PHASE_COUNTS, f"{job_id}: unexpected phase")
    require(record.get("primary_uncertainty") in REQUIRED_UNCERTAINTY_COUNTS, f"{job_id}: unexpected uncertainty")
    require(record.get("diagnostic_focus") in REQUIRED_FOCUS_COUNTS, f"{job_id}: unexpected diagnostic focus")
    require(planned_seconds > 0.0, f"{job_id}: missing planned duration")
    if planned_seconds >= 120.0:
        require(record.get("duration_bucket") == "long_preview_120s", f"{job_id}: wrong duration bucket")
    elif planned_seconds >= 30.0:
        require(record.get("duration_bucket") == "diagnostic_30s", f"{job_id}: wrong duration bucket")
    else:
        require(record.get("duration_bucket") == "short_finite_candidate", f"{job_id}: wrong duration bucket")
    require(record.get("near_oracle_status") == "audio_equivalent_state_delta", f"{job_id}: near-oracle status mismatch")
    require(set(record.get("accepted_oracles", [])) == {"mesen2", "bsnes_higan", "mednafen"}, f"{job_id}: accepted oracle mismatch")
    validate_source(job_id, record)
    validate_targets(job_id, record.get("capture_targets", {}))
    contract = record.get("metadata_contract", {})
    require(set(contract.get("minimum_fields", [])) == REQUIRED_METADATA_FIELDS, f"{job_id}: metadata contract mismatch")
    require(int(contract.get("sample_rate_hz", 0)) == 32000, f"{job_id}: sample rate mismatch")
    require(int(contract.get("channels", 0)) == 2, f"{job_id}: channel count mismatch")
    require(int(contract.get("bits_per_sample", 0)) == 16, f"{job_id}: bit depth mismatch")
    require(float(contract.get("minimum_duration_seconds", 0.0)) == planned_seconds, f"{job_id}: minimum duration mismatch")
    validate_audit(job_id, record.get("current_audit", {}))
    validate_commands(job_id, record.get("handoff_commands", {}))
    require(len(record.get("acceptance_gates", [])) >= 6, f"{job_id}: acceptance gates too thin")
    require(record.get("handoff_gate"), f"{job_id}: missing handoff gate")
    require(record.get("promotion_allowed_by_matrix") is False, f"{job_id}: matrix promotion should be blocked")
    require(record.get("behavior_change_allowed") is False, f"{job_id}: behavior changes should be blocked")


def validate_batches(data: dict[str, Any]) -> None:
    batches = data.get("operator_batches", {})
    expected = {
        "by_phase": ("phase", REQUIRED_PHASE_COUNTS),
        "by_primary_uncertainty": ("primary_uncertainty", REQUIRED_UNCERTAINTY_COUNTS),
        "by_diagnostic_focus": ("diagnostic_focus", REQUIRED_FOCUS_COUNTS),
        "by_duration_bucket": ("duration_bucket", REQUIRED_DURATION_BUCKET_COUNTS),
    }
    for batch_key, (field, required_counts) in expected.items():
        actual = {batch.get(field): int(batch.get("job_count", 0)) for batch in batches.get(batch_key, [])}
        require(actual == required_counts, f"{batch_key} batches mismatch")
        for batch in batches.get(batch_key, []):
            count = int(batch.get("job_count", 0))
            require(len(batch.get("track_ids", [])) == count, f"{batch_key}: track count mismatch")
            require(len(batch.get("job_ids", [])) == count, f"{batch_key}: job count mismatch")


def validate(data: dict[str, Any]) -> None:
    require(data.get("schema") == "earthbound-decomp.audio-independent-oracle-handoff-matrix.v1", "unexpected schema")
    require(data.get("status") == "independent_oracle_handoff_matrix_ready_external_inputs_required", "unexpected status")
    require(data.get("source_packet_status") == "independent_oracle_capture_packet_ready_external_inputs_required", "unexpected packet status")
    require(data.get("source_run_mode") == "audit-existing-captures", "unexpected run mode")
    require(data.get("source_coverage_status") == "independent_oracle_coverage_ready_external_captures_pending", "unexpected coverage status")
    require(data.get("source_next_action_lane") == "independent_oracle_representative_capture", "unexpected next-action lane")
    require(REQUIRED_REFERENCES <= set(data.get("references", [])), "missing references")
    summary = data.get("summary", {})
    records = data.get("records", [])
    require(int(summary.get("handoff_job_count", 0)) == 16, "expected 16 handoff jobs")
    require(len(records) == 16, "record count mismatch")
    require(int(summary.get("ready_capture_count", -1)) == 0, "ready count mismatch")
    require(int(summary.get("pending_capture_count", 0)) == 16, "pending count mismatch")
    require(int(summary.get("missing_capture_metadata_count", 0)) == 16, "missing metadata count mismatch")
    require(int(summary.get("all_track_missing_independent_capture_count", 0)) == 190, "all-track missing count mismatch")
    require(int(summary.get("near_oracle_pass_count", 0)) == 190, "near-oracle pass count mismatch")
    require(summary.get("phase_job_counts") == REQUIRED_PHASE_COUNTS, "phase counts mismatch")
    require(summary.get("primary_uncertainty_counts") == REQUIRED_UNCERTAINTY_COUNTS, "uncertainty counts mismatch")
    require(summary.get("diagnostic_focus_counts") == REQUIRED_FOCUS_COUNTS, "focus counts mismatch")
    require(summary.get("duration_bucket_counts") == REQUIRED_DURATION_BUCKET_COUNTS, "duration bucket counts mismatch")
    require(summary.get("phase_job_counts") == count_records(records, "phase"), "phase counts do not match records")
    require(summary.get("primary_uncertainty_counts") == count_records(records, "primary_uncertainty"), "uncertainty counts do not match records")
    require(summary.get("diagnostic_focus_counts") == count_records(records, "diagnostic_focus"), "focus counts do not match records")
    require(summary.get("duration_bucket_counts") == count_records(records, "duration_bucket"), "duration counts do not match records")
    require(set(summary.get("accepted_oracles", [])) == {"mesen2", "bsnes_higan", "mednafen"}, "accepted oracle summary mismatch")
    require(set(summary.get("minimum_metadata_fields", [])) == REQUIRED_METADATA_FIELDS, "metadata fields summary mismatch")
    require(int(summary.get("sample_rate_hz", 0)) == 32000, "sample rate summary mismatch")
    require(int(summary.get("channels", 0)) == 2, "channel summary mismatch")
    require(int(summary.get("bits_per_sample", 0)) == 16, "bit-depth summary mismatch")
    require(summary.get("representative_oracle_gate_passed") is True, "representative near-oracle gate should pass")
    require(summary.get("all_track_oracle_gate_passed") is True, "all-track near-oracle gate should pass")
    require(summary.get("independent_emulator_gate_passed") is False, "independent gate should be blocked")
    require(summary.get("release_quality_playback_claim_ready") is False, "release-quality claim should be blocked")
    require(summary.get("promotion_allowed_by_matrix") is False, "matrix promotion should be blocked")
    require(summary.get("behavior_change_allowed") is False, "behavior changes should be blocked")
    seen_orders: set[int] = set()
    seen_tracks: set[int] = set()
    for record in records:
        order = int(record.get("execution_order", 0))
        track_id = int(record.get("track_id", -1))
        require(order not in seen_orders, f"{record.get('job_id')}: duplicate order")
        require(track_id not in seen_tracks, f"{record.get('job_id')}: duplicate track")
        seen_orders.add(order)
        seen_tracks.add(track_id)
        validate_record(record)
    require(seen_orders == set(range(1, 17)), "execution orders should be contiguous")
    validate_batches(data)
    require(data.get("handoff_policy"), "missing handoff policy")
    require(REQUIRED_POST_COMMANDS <= set(data.get("post_handoff_validation_commands", [])), "missing post-handoff validation commands")


def main() -> int:
    args = parse_args()
    data = json.loads(Path(args.matrix).read_text(encoding="utf-8"))
    validate(data)
    print(
        "Audio independent oracle handoff matrix validation OK: "
        f"{data['summary']['handoff_job_count']} jobs, "
        f"{data['summary']['pending_capture_count']} pending"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
