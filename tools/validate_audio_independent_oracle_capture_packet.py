#!/usr/bin/env python3
"""Validate the representative independent oracle capture packet."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PACKET = ROOT / "manifests" / "audio-independent-oracle-capture-packet.json"
REQUIRED_REFERENCES = {
    "manifests/audio-independent-oracle-campaign-plan.json",
    "manifests/audio-independent-oracle-coverage-report.json",
    "manifests/audio-duration-next-actions-plan.json",
    "manifests/audio-oracle-comparison-plan-all-tracks.json",
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
    "python tools/validate_audio_independent_oracle_capture_packet.py",
    "python tools/run_audio_independent_oracle_campaign.py --mode audit-existing-captures",
    "python tools/validate_audio_independent_oracle_campaign_run_summary.py",
    "python tools/validate_audio_oracle_verification_report.py manifests/audio-oracle-verification-report-all-tracks.json --require-representative-pass",
    "python tools/build_audio_independent_oracle_coverage_report.py",
    "python tools/validate_audio_independent_oracle_coverage_report.py",
    "python tools/build_audio_duration_readiness_rollup.py",
    "python tools/validate_audio_duration_readiness_rollup.py",
}
SHA1_RE = re.compile(r"^[0-9a-f]{40}$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate independent oracle capture packet.")
    parser.add_argument("packet", nargs="?", default=str(DEFAULT_PACKET))
    return parser.parse_args()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def count_records(records: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for record in records:
        counts[str(record.get(key))] += 1
    return dict(sorted(counts.items()))


def validate_record(record: dict[str, Any]) -> None:
    job_id = str(record.get("job_id"))
    track_id = int(record.get("track_id", -1))
    require(job_id.startswith("oracle-track-"), f"{job_id}: unexpected job id")
    require(track_id > 0, f"{job_id}: invalid track id")
    require(record.get("phase") in REQUIRED_PHASE_COUNTS, f"{job_id}: unexpected phase")
    require(record.get("primary_uncertainty") in REQUIRED_UNCERTAINTY_COUNTS, f"{job_id}: unexpected uncertainty")
    require(record.get("current_near_oracle_status") == "audio_equivalent_state_delta", f"{job_id}: near oracle status mismatch")
    require(record.get("current_independent_emulator_capture") is False, f"{job_id}: current capture should be missing")
    require(record.get("independent_capture_required") is True, f"{job_id}: independent capture should be required")
    require(set(record.get("accepted_oracles", [])) == {"mesen2", "bsnes_higan", "mednafen"}, f"{job_id}: accepted oracle set mismatch")
    require(set(record.get("expected_capture_metadata_fields", [])) == REQUIRED_METADATA_FIELDS, f"{job_id}: metadata fields mismatch")
    require(len(record.get("acceptance_gates", [])) >= 6, f"{job_id}: missing acceptance gates")
    source_spc = record.get("source_spc", {})
    require(str(source_spc.get("path", "")).endswith(".spc"), f"{job_id}: source SPC path missing")
    require(bool(SHA1_RE.match(str(source_spc.get("sha1", "")))), f"{job_id}: invalid source SPC sha1")
    require(int(source_spc.get("bytes", 0)) == 66048, f"{job_id}: source SPC byte count mismatch")
    source_render = record.get("source_render", {})
    require(str(source_render.get("path", "")).endswith(".wav"), f"{job_id}: source render path missing")
    require(bool(SHA1_RE.match(str(source_render.get("sha1", "")))), f"{job_id}: invalid source render sha1")
    require(int(source_render.get("bytes", 0)) > 0, f"{job_id}: source render byte count missing")
    outputs = record.get("capture_outputs", {})
    require(str(outputs.get("spc_snapshot", "")).startswith("build/audio/oracle-comparison-all-tracks/"), f"{job_id}: bad SPC output")
    require(str(outputs.get("pcm_wav", "")).startswith("build/audio/oracle-comparison-all-tracks/"), f"{job_id}: bad WAV output")
    require(str(outputs.get("capture_metadata", "")).endswith("reference-capture.json"), f"{job_id}: bad metadata output")
    require(str(outputs.get("comparison_result", "")).endswith("oracle-comparison-result.json"), f"{job_id}: bad comparison output")
    commands = record.get("commands", {})
    required_command_fragments = {
        "dry_run": "run_audio_independent_oracle_campaign.py",
        "audit": "run_audio_independent_oracle_campaign.py",
        "import": "import_audio_oracle_reference_capture.py",
        "validate_capture": "validate_audio_oracle_reference_capture.py",
        "collect_comparison": "collect_audio_oracle_comparison_results.py",
        "refresh_report": "build_audio_oracle_verification_report.py",
        "validate_report": "validate_audio_oracle_verification_report.py",
    }
    for key, fragment in required_command_fragments.items():
        require(fragment in str(commands.get(key, "")), f"{job_id}: missing command {key}")
    require(record.get("promotion_allowed_by_packet") is False, f"{job_id}: packet promotion should be blocked")
    require(record.get("behavior_change_allowed") is False, f"{job_id}: behavior changes should be blocked")


def validate_batches(data: dict[str, Any]) -> None:
    by_phase = data.get("operator_batches", {}).get("by_phase", [])
    require({batch.get("phase"): int(batch.get("job_count", 0)) for batch in by_phase} == REQUIRED_PHASE_COUNTS, "phase batches mismatch")
    by_uncertainty = data.get("operator_batches", {}).get("by_primary_uncertainty", [])
    require(
        {batch.get("primary_uncertainty"): int(batch.get("job_count", 0)) for batch in by_uncertainty}
        == REQUIRED_UNCERTAINTY_COUNTS,
        "uncertainty batches mismatch",
    )
    for batch in by_phase + by_uncertainty:
        require(len(batch.get("track_ids", [])) == int(batch.get("job_count", 0)), "batch track count mismatch")
        require(len(batch.get("job_ids", [])) == int(batch.get("job_count", 0)), "batch job count mismatch")


def validate(data: dict[str, Any]) -> None:
    require(data.get("schema") == "earthbound-decomp.audio-independent-oracle-capture-packet.v1", "unexpected schema")
    require(data.get("status") == "independent_oracle_capture_packet_ready_external_inputs_required", "unexpected status")
    require(data.get("source_campaign_status") == "independent_external_oracle_campaign_ready", "unexpected campaign status")
    require(data.get("source_coverage_status") == "independent_oracle_coverage_ready_external_captures_pending", "unexpected coverage status")
    require(data.get("source_next_action_lane") == "independent_oracle_representative_capture", "unexpected next-action lane")
    require(REQUIRED_REFERENCES <= set(data.get("references", [])), "missing references")
    summary = data.get("summary", {})
    records = data.get("records", [])
    require(int(summary.get("packet_job_count", 0)) == 16, "expected 16 packet jobs")
    require(len(records) == 16, "record count mismatch")
    require(int(summary.get("missing_independent_capture_count", 0)) == 16, "expected 16 missing representative captures")
    require(int(summary.get("all_track_missing_independent_capture_count", 0)) == 190, "expected 190 missing all-track captures")
    require(int(summary.get("near_oracle_pass_count", 0)) == 190, "expected 190 near-oracle passes")
    require(summary.get("phase_job_counts") == REQUIRED_PHASE_COUNTS, "phase counts mismatch")
    require(summary.get("phase_job_counts") == count_records(records, "phase"), "phase counts do not match records")
    require(summary.get("primary_uncertainty_counts") == REQUIRED_UNCERTAINTY_COUNTS, "uncertainty counts mismatch")
    require(summary.get("primary_uncertainty_counts") == count_records(records, "primary_uncertainty"), "uncertainty counts do not match records")
    require(set(summary.get("accepted_oracles", [])) == {"mesen2", "bsnes_higan", "mednafen"}, "accepted oracle set mismatch")
    require(set(summary.get("minimum_metadata_fields", [])) == REQUIRED_METADATA_FIELDS, "metadata fields mismatch")
    require(int(summary.get("sample_rate_hz", 0)) == 32000, "sample rate mismatch")
    require(int(summary.get("channels", 0)) == 2, "channel count mismatch")
    require(int(summary.get("bits_per_sample", 0)) == 16, "bits per sample mismatch")
    require(float(summary.get("minimum_seconds", 0.0)) == 30.0, "minimum seconds mismatch")
    require(summary.get("release_quality_playback_claim_ready") is False, "release-quality claim should be blocked")
    require(summary.get("promotion_allowed_by_packet") is False, "packet promotion should be blocked")
    require(summary.get("behavior_change_allowed") is False, "behavior changes should be blocked")
    seen_orders: set[int] = set()
    seen_tracks: set[int] = set()
    for record in records:
        order = int(record.get("execution_order", 0))
        track_id = int(record.get("track_id", -1))
        require(order not in seen_orders, f"{record.get('job_id')}: duplicate order")
        seen_orders.add(order)
        require(track_id not in seen_tracks, f"{record.get('job_id')}: duplicate track")
        seen_tracks.add(track_id)
        validate_record(record)
    require(seen_orders == set(range(1, 17)), "execution orders should be contiguous")
    validate_batches(data)
    require(data.get("capture_packet_policy"), "missing packet policy")
    require(REQUIRED_POST_COMMANDS <= set(data.get("post_packet_validation_commands", [])), "missing post-packet validation commands")


def main() -> int:
    args = parse_args()
    data = json.loads(Path(args.packet).read_text(encoding="utf-8"))
    validate(data)
    print(
        "Audio independent oracle capture packet validation OK: "
        f"{data['summary']['packet_job_count']} jobs, "
        f"{data['summary']['missing_independent_capture_count']} captures missing"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
