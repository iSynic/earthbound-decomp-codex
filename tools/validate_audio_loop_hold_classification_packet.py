#!/usr/bin/env python3
"""Validate the loop/hold classification packet."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PACKET = ROOT / "manifests" / "audio-loop-hold-classification-packet.json"
REQUIRED_REFERENCES = {
    "manifests/audio-loop-point-evidence-plan.json",
    "manifests/audio-loop-point-tail-metrics.json",
    "build/audio/loop-point-evidence-runs/loop-point-evidence-run-summary.json",
    "manifests/audio-duration-next-actions-plan.json",
}
REQUIRED_TRACK_IDS = {5, 6, 115, 183, 184}
REQUIRED_TAIL_COUNTS = {"active_through_diagnostic_render_boundary": 5}
REQUIRED_FOCUS_COUNTS = {
    "active_through_preview_or_loop_candidate": 4,
    "general_playback_equivalence": 1,
}
REQUIRED_PACK_COUNTS = {"5": 5}
REQUIRED_MISSING_FIELDS = {"intro_samples", "loop_start_sample", "loop_end_sample", "measured_by"}
REQUIRED_BLOCKING_REASONS = {
    "held_or_sample_loop_policy_unresolved": 5,
    "missing_intro_samples": 5,
    "missing_loop_end_sample": 5,
    "missing_loop_start_sample": 5,
    "missing_measured_by": 5,
    "placeholder_loop_points_pending": 5,
}
REQUIRED_STATUSES = {
    "exact_loop_points_available",
    "held_policy_no_exact_loop_points",
    "unresolved_loop_or_hold_policy",
}
REQUIRED_POST_COMMANDS = {
    "python tools/validate_audio_loop_hold_classification_packet.py",
    "python tools/run_audio_loop_point_evidence_plan.py --mode audit-current-export",
    "python tools/validate_audio_loop_point_evidence_run_summary.py",
    "python tools/build_audio_loop_point_tail_metrics.py",
    "python tools/validate_audio_loop_point_tail_metrics.py",
    "python tools/validate_audio_loop_point_evidence_plan.py",
    "python tools/validate_audio_export_plan.py",
    "python tools/validate_audio_duration_uncertainty_register.py",
    "python tools/build_audio_duration_readiness_rollup.py",
    "python tools/validate_audio_duration_readiness_rollup.py",
}
SHA1_RE = re.compile(r"^[0-9a-f]{40}$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate loop/hold classification packet.")
    parser.add_argument("packet", nargs="?", default=str(DEFAULT_PACKET))
    return parser.parse_args()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def count_records(records: list[dict[str, Any]], key_path: tuple[str, ...]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for record in records:
        current: Any = record
        for key in key_path:
            current = current.get(key, {}) if isinstance(current, dict) else None
        counts[str(current)] += 1
    return dict(sorted(counts.items()))


def validate_pack_context(job_id: str, pack: dict[str, Any]) -> None:
    require(int(pack.get("primary_sample_pack", 0)) == 5, f"{job_id}: expected primary sample pack 5")
    require(pack.get("secondary_sample_pack") is None, f"{job_id}: unexpected secondary sample pack")
    require(pack.get("sequence_pack") is None, f"{job_id}: unexpected sequence pack")
    require(pack.get("no_dedicated_sequence_pack") is True, f"{job_id}: expected no dedicated sequence pack")
    source = pack.get("primary_pack_source", {})
    require(source.get("asset_id") == "asset.eb.audio_pack_5", f"{job_id}: unexpected primary pack asset")
    require(source.get("range") == "EB:520C..EB:78D6", f"{job_id}: unexpected primary pack range")
    require(bool(SHA1_RE.match(str(source.get("sha1", "")))), f"{job_id}: invalid primary pack sha1")
    stream = source.get("stream_summary", {})
    require(int(stream.get("block_count", 0)) == 4, f"{job_id}: primary pack block count mismatch")
    require(int(stream.get("payload_bytes", 0)) == 9916, f"{job_id}: primary pack payload mismatch")


def validate_source(job_id: str, source: dict[str, Any]) -> None:
    require(str(source.get("oracle_job_id", "")).startswith("oracle-track-"), f"{job_id}: missing oracle job id")
    require(source.get("diagnostic_focus") in REQUIRED_FOCUS_COUNTS, f"{job_id}: unexpected diagnostic focus")
    source_spc = source.get("source_spc", {})
    source_render = source.get("source_render", {})
    require(str(source_spc.get("path", "")).endswith(".spc"), f"{job_id}: source SPC path missing")
    require(bool(SHA1_RE.match(str(source_spc.get("sha1", "")))), f"{job_id}: invalid source SPC sha1")
    require(int(source_spc.get("bytes", 0)) == 66048, f"{job_id}: source SPC byte count mismatch")
    require(str(source_render.get("path", "")).endswith(".wav"), f"{job_id}: source render path missing")
    require(bool(SHA1_RE.match(str(source_render.get("sha1", "")))), f"{job_id}: invalid source render sha1")
    require(int(source_render.get("bytes", 0)) > 0, f"{job_id}: source render byte count missing")
    metrics = source_render.get("metrics", {})
    require(int(metrics.get("rendered_samples", 0)) == 1920000, f"{job_id}: source render sample count mismatch")
    require(int(metrics.get("voice_count", 0)) > 0, f"{job_id}: source render voice count missing")
    outputs = source.get("reference_capture_outputs", {})
    require(str(outputs.get("comparison_result", "")).endswith("oracle-comparison-result.json"), f"{job_id}: missing comparison output")


def validate_loop_gap(job_id: str, loop_gap: dict[str, Any]) -> None:
    require(loop_gap.get("status") == "placeholder_only_exact_loop_points_pending", f"{job_id}: loop gap status mismatch")
    require(set(loop_gap.get("missing_fields", [])) == REQUIRED_MISSING_FIELDS, f"{job_id}: missing loop fields mismatch")
    require(len(loop_gap.get("required_evidence", [])) >= 3, f"{job_id}: required evidence too thin")
    preview = loop_gap.get("preview_policy", {})
    require(preview.get("mode") == "loop_count_plus_fade_preview", f"{job_id}: loop gap preview mode mismatch")
    require(int(preview.get("loop_count", 0)) == 2, f"{job_id}: loop gap loop count mismatch")
    require(float(preview.get("fade_seconds", 0.0)) == 5.0, f"{job_id}: loop gap fade mismatch")


def validate_tail(job_id: str, tail: dict[str, Any]) -> None:
    require(tail.get("tail_classification") == "active_through_diagnostic_render_boundary", f"{job_id}: unexpected tail classification")
    units = tail.get("unit_policy", {})
    require(units.get("source_render_nonzero_index") == "interleaved_pcm_sample_index", f"{job_id}: source render unit mismatch")
    require(units.get("normalized_nonzero_index") == "pcm_frame_32000hz", f"{job_id}: normalized unit mismatch")
    require(int(units.get("assumed_channels", 0)) == 2, f"{job_id}: expected stereo")
    require(int(units.get("assumed_sample_rate", 0)) == 32000, f"{job_id}: expected 32 kHz")
    require(int(tail.get("rendered_samples", 0)) == 1920000, f"{job_id}: expected 30-second interleaved render samples")
    require(int(tail.get("rendered_frames", 0)) == 960000, f"{job_id}: expected 30-second diagnostic render")
    require(float(tail.get("render_seconds", 0.0)) == 30.0, f"{job_id}: render seconds mismatch")
    require(tail.get("active_through_render_boundary") is True, f"{job_id}: active boundary flag mismatch")
    require(int(tail.get("trailing_silent_frames_at_render_end", 99)) <= 4, f"{job_id}: too much render-end silence")
    require(int(tail.get("last_nonzero_frame_index", -1)) >= 959995, f"{job_id}: last nonzero frame too early")
    require(int(tail.get("voice_count", 0)) > 0, f"{job_id}: missing voice count")


def validate_audit(job_id: str, audit: dict[str, Any]) -> None:
    require(audit.get("status") == "pending_loop_evidence", f"{job_id}: audit status mismatch")
    require(audit.get("evidence_status") == "placeholder_only_exact_loop_points_pending", f"{job_id}: audit evidence mismatch")
    require(set(audit.get("blocking_reasons", [])) == set(REQUIRED_BLOCKING_REASONS), f"{job_id}: blocking reasons mismatch")
    require(set(audit.get("missing_fields", [])) == REQUIRED_MISSING_FIELDS, f"{job_id}: audit missing fields mismatch")
    preview = audit.get("preview_policy", {})
    require(int(preview.get("loop_count", 0)) == 2, f"{job_id}: audit loop count mismatch")
    require(float(preview.get("fade_seconds", 0.0)) == 5.0, f"{job_id}: audit fade mismatch")
    require(preview.get("current_public_mode") == "loop_count_plus_fade_preview", f"{job_id}: audit preview mode mismatch")
    require(audit.get("promotion_allowed_by_run") is False, f"{job_id}: run promotion should be blocked")


def validate_record(record: dict[str, Any]) -> None:
    job_id = str(record.get("job_id"))
    track_id = int(record.get("track_id", -1))
    require(job_id.startswith(f"loop-point-track-{track_id:03d}-"), f"{job_id}: unexpected job id")
    require(track_id in REQUIRED_TRACK_IDS, f"{job_id}: unexpected track id")
    require(record.get("primary_uncertainty") == "loop_point_metadata_pending", f"{job_id}: wrong uncertainty")
    require(record.get("export_class") == "loop_or_held_candidate", f"{job_id}: wrong export class")
    require(record.get("export_status") == "preview_policy_ready_exact_loop_pending", f"{job_id}: wrong export status")
    require(record.get("recommended_mode") == "loop_count_plus_fade_preview", f"{job_id}: wrong mode")
    require(float(record.get("duration_seconds", 0.0)) == 120.0, f"{job_id}: preview duration mismatch")
    preview = record.get("loop_preview_policy", {})
    require(int(preview.get("loop_count", 0)) == 2, f"{job_id}: preview loop count mismatch")
    require(float(preview.get("fade_seconds", 0.0)) == 5.0, f"{job_id}: preview fade mismatch")
    require(preview.get("current_public_mode") == "loop_count_plus_fade_preview", f"{job_id}: preview mode mismatch")
    validate_pack_context(job_id, record.get("pack_context", {}))
    validate_source(job_id, record.get("source_candidate", {}))
    validate_loop_gap(job_id, record.get("loop_gap", {}))
    validate_tail(job_id, record.get("tail_metrics", {}))
    validate_audit(job_id, record.get("current_audit_status", {}))
    require(set(record.get("accepted_evidence_statuses", [])) == REQUIRED_STATUSES, f"{job_id}: accepted statuses mismatch")
    require(len(record.get("evidence_questions", [])) >= 3, f"{job_id}: evidence questions too thin")
    require(len(record.get("required_runtime_evidence", [])) >= 4, f"{job_id}: runtime evidence too thin")
    commands = record.get("commands", {})
    require("run_audio_loop_point_evidence_plan.py" in str(commands.get("dry_run", "")), f"{job_id}: missing dry run")
    require("run_audio_loop_point_evidence_plan.py" in str(commands.get("audit", "")), f"{job_id}: missing audit")
    require("build_audio_loop_point_tail_metrics.py" in str(commands.get("build_tail_metrics", "")), f"{job_id}: missing build metrics")
    require("validate_audio_loop_point_tail_metrics.py" in str(commands.get("validate_tail_metrics", "")), f"{job_id}: missing validate metrics")
    require("python tools/validate_audio_duration_uncertainty_register.py" in commands.get("post_evidence", []), f"{job_id}: missing post evidence validation")
    require(record.get("completion_gate"), f"{job_id}: missing completion gate")
    require(record.get("public_exact_loop_export_allowed_by_packet") is False, f"{job_id}: public exact loop should remain blocked")
    require(record.get("promotion_allowed_by_packet") is False, f"{job_id}: packet promotion should be blocked")
    require(record.get("behavior_change_allowed") is False, f"{job_id}: behavior changes should be blocked")


def validate_batches(data: dict[str, Any]) -> None:
    batches = data.get("operator_batches", {})
    tail_batches = {batch.get("group"): int(batch.get("job_count", 0)) for batch in batches.get("by_tail_classification", [])}
    focus_batches = {batch.get("group"): int(batch.get("job_count", 0)) for batch in batches.get("by_diagnostic_focus", [])}
    audit_batches = {batch.get("group"): int(batch.get("job_count", 0)) for batch in batches.get("by_audit_status", [])}
    pack_batches = {batch.get("group"): int(batch.get("job_count", 0)) for batch in batches.get("by_primary_sample_pack", [])}
    require(tail_batches == REQUIRED_TAIL_COUNTS, "tail classification batches mismatch")
    require(focus_batches == REQUIRED_FOCUS_COUNTS, "diagnostic focus batches mismatch")
    require(audit_batches == {"pending_loop_evidence": 5}, "audit status batches mismatch")
    require(pack_batches == REQUIRED_PACK_COUNTS, "primary sample pack batches mismatch")
    for group in batches.values():
        for batch in group:
            count = int(batch.get("job_count", 0))
            require(len(batch.get("track_ids", [])) == count, "batch track count mismatch")
            require(len(batch.get("job_ids", [])) == count, "batch job count mismatch")


def validate(data: dict[str, Any]) -> None:
    require(data.get("schema") == "earthbound-decomp.audio-loop-hold-classification-packet.v1", "unexpected schema")
    require(data.get("status") == "loop_hold_classification_packet_ready_preview_policy_preserved", "unexpected status")
    require(data.get("source_plan_status") == "loop_point_evidence_plan_ready_preview_policy_preserved", "unexpected plan status")
    require(data.get("source_tail_status") == "loop_point_tail_metrics_ready_preview_policy_preserved", "unexpected tail status")
    require(data.get("source_run_mode") == "audit-current-export", "unexpected run mode")
    require(data.get("source_next_action_lane") == "loop_point_or_hold_classification", "unexpected next-action lane")
    require(REQUIRED_REFERENCES <= set(data.get("references", [])), "missing references")
    summary = data.get("summary", {})
    records = data.get("records", [])
    require(int(summary.get("packet_job_count", 0)) == 5, "expected five packet jobs")
    require(len(records) == 5, "record count mismatch")
    require(set(summary.get("track_ids", [])) == REQUIRED_TRACK_IDS, "track summary mismatch")
    require(summary.get("tail_classification_counts") == REQUIRED_TAIL_COUNTS, "tail counts mismatch")
    require(summary.get("diagnostic_focus_counts") == REQUIRED_FOCUS_COUNTS, "focus counts mismatch")
    require(summary.get("primary_sample_pack_counts") == REQUIRED_PACK_COUNTS, "primary sample pack counts mismatch")
    require(int(summary.get("missing_exact_loop_field_count", 0)) == 20, "missing loop field count mismatch")
    require(int(summary.get("active_through_render_boundary_count", 0)) == 5, "active boundary count mismatch")
    require(int(summary.get("pending_evidence_count", 0)) == 5, "pending evidence count mismatch")
    require(int(summary.get("ready_evidence_count", -1)) == 0, "ready evidence count mismatch")
    require(summary.get("blocking_reason_counts") == REQUIRED_BLOCKING_REASONS, "blocking reason counts mismatch")
    require(set(summary.get("accepted_evidence_statuses", [])) == REQUIRED_STATUSES, "accepted status summary mismatch")
    require(int(summary.get("preview_policy_loop_count", 0)) == 2, "summary loop count mismatch")
    require(float(summary.get("preview_policy_fade_seconds", 0.0)) == 5.0, "summary fade mismatch")
    require(summary.get("public_exact_loop_export_ready") is False, "public exact loop should be blocked")
    require(summary.get("promotion_allowed_by_packet") is False, "packet promotion should be blocked")
    require(summary.get("behavior_change_allowed") is False, "behavior changes should be blocked")
    require(summary.get("tail_classification_counts") == count_records(records, ("tail_metrics", "tail_classification")), "tail counts do not match records")
    require(summary.get("diagnostic_focus_counts") == count_records(records, ("source_candidate", "diagnostic_focus")), "focus counts do not match records")
    require(summary.get("primary_sample_pack_counts") == count_records(records, ("pack_context", "primary_sample_pack")), "pack counts do not match records")
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
    require(seen_orders == set(range(1, 6)), "execution orders should be 1..5")
    require(seen_tracks == REQUIRED_TRACK_IDS, "record track coverage mismatch")
    validate_batches(data)
    require(data.get("classification_policy"), "missing classification policy")
    require(REQUIRED_POST_COMMANDS <= set(data.get("post_packet_validation_commands", [])), "missing post-packet validation commands")


def main() -> int:
    args = parse_args()
    data = json.loads(Path(args.packet).read_text(encoding="utf-8"))
    validate(data)
    print(
        "Audio loop/hold classification packet validation OK: "
        f"{data['summary']['packet_job_count']} jobs, "
        f"{data['summary']['pending_evidence_count']} pending"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
