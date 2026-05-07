#!/usr/bin/env python3
"""Validate the finite-transition classification packet."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PACKET = ROOT / "manifests" / "audio-finite-transition-classification-packet.json"
REQUIRED_REFERENCES = {
    "manifests/audio-finite-ending-evidence-plan.json",
    "manifests/audio-finite-ending-tail-metrics.json",
    "build/audio/finite-ending-evidence-runs/finite-ending-evidence-run-summary.json",
    "manifests/audio-duration-next-actions-plan.json",
}
REQUIRED_TRACK_IDS = {8, 9, 11, 123, 176}
REQUIRED_TAIL_COUNTS = {"active_through_render_boundary": 3, "post_candidate_tail_nonzero": 2}
REQUIRED_FOCUS_COUNTS = {
    "active_through_preview_or_loop_candidate": 2,
    "finite_tail_or_transition_end": 2,
    "general_playback_equivalence": 1,
}
REQUIRED_BLOCKING_REASONS = {
    "finite_tail_review_pending": 5,
    "missing_explicit_tail_classification": 5,
    "nonzero_pcm_after_candidate_end": 5,
    "public_exact_export_blocked": 5,
    "sequence_semantics_required": 5,
}
REQUIRED_STATUSES = {"true_finite_end", "transition_or_stinger_policy", "unresolved_finite_boundary"}
REQUIRED_POST_COMMANDS = {
    "python tools/validate_audio_finite_transition_classification_packet.py",
    "python tools/run_audio_finite_ending_evidence_plan.py --mode audit-current-export",
    "python tools/validate_audio_finite_ending_evidence_run_summary.py",
    "python tools/build_audio_finite_ending_tail_metrics.py",
    "python tools/validate_audio_finite_ending_tail_metrics.py",
    "python tools/validate_audio_finite_ending_evidence_plan.py",
    "python tools/validate_audio_export_plan.py",
    "python tools/validate_audio_duration_uncertainty_register.py",
    "python tools/build_audio_duration_readiness_rollup.py",
    "python tools/validate_audio_duration_readiness_rollup.py",
}
SHA1_RE = re.compile(r"^[0-9a-f]{40}$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate finite-transition classification packet.")
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
    outputs = source.get("reference_capture_outputs", {})
    require(str(outputs.get("comparison_result", "")).endswith("oracle-comparison-result.json"), f"{job_id}: missing comparison output")


def validate_record(record: dict[str, Any]) -> None:
    job_id = str(record.get("job_id"))
    track_id = int(record.get("track_id", -1))
    require(job_id.startswith(f"finite-ending-track-{track_id:03d}-"), f"{job_id}: unexpected job id")
    require(track_id in REQUIRED_TRACK_IDS, f"{job_id}: unexpected track id")
    require(record.get("primary_uncertainty") == "finite_transition_review_pending", f"{job_id}: wrong uncertainty")
    require(record.get("export_class") == "finite_or_transition_review_candidate", f"{job_id}: wrong export class")
    require(record.get("export_status") == "review_needed_before_public_exact_export", f"{job_id}: wrong export status")
    require(record.get("recommended_mode") == "trim_candidate_after_manual_or_sequence_review", f"{job_id}: wrong mode")
    require(float(record.get("duration_seconds", 0.0)) > 0.0, f"{job_id}: missing duration")
    require(record.get("needs_sequence_semantics") is True, f"{job_id}: expected sequence semantics gate")
    validate_source(job_id, record.get("source_candidate", {}))
    candidate = record.get("candidate_end", {})
    require(int(candidate.get("frame", 0)) > 0, f"{job_id}: missing candidate frame")
    require(candidate.get("frame") == candidate.get("metadata_frame"), f"{job_id}: candidate metadata frame mismatch")
    require(float(candidate.get("seconds", 0.0)) > 0.0, f"{job_id}: missing candidate seconds")
    require(candidate.get("seconds") == candidate.get("metadata_seconds"), f"{job_id}: candidate metadata seconds mismatch")
    require(candidate.get("measured_by") == "audio_export_duration_measurement", f"{job_id}: unexpected measurement source")
    tail = record.get("tail_metrics", {})
    classification = str(tail.get("tail_classification"))
    require(classification in REQUIRED_TAIL_COUNTS, f"{job_id}: unexpected tail classification")
    units = tail.get("unit_policy", {})
    require(units.get("finite_end_sample") == "pcm_frame_32000hz", f"{job_id}: finite-end unit mismatch")
    require(units.get("source_render_nonzero_index") == "interleaved_pcm_sample_index", f"{job_id}: source render unit mismatch")
    require(int(units.get("assumed_channels", 0)) == 2, f"{job_id}: expected stereo")
    require(int(units.get("assumed_sample_rate", 0)) == 32000, f"{job_id}: expected 32 kHz")
    require(int(tail.get("last_nonzero_frame_index", -1)) >= int(candidate.get("frame", 0)), f"{job_id}: tail ordering mismatch")
    require(int(tail.get("frames_after_candidate_end", -1)) >= 0, f"{job_id}: missing tail frames")
    require(float(tail.get("seconds_after_candidate_end", -1.0)) >= 0.0, f"{job_id}: missing tail seconds")
    require(int(tail.get("rendered_frames", 0)) == 960000, f"{job_id}: expected 30-second diagnostic render")
    if classification == "active_through_render_boundary":
        require(tail.get("active_through_render_boundary") is True, f"{job_id}: active flag mismatch")
        require(int(tail.get("trailing_silent_frames_at_render_end", 99)) <= 4, f"{job_id}: active boundary silence mismatch")
    if classification == "post_candidate_tail_nonzero":
        require(tail.get("active_through_render_boundary") is False, f"{job_id}: active flag mismatch")
        require(int(tail.get("trailing_silent_frames_at_render_end", -1)) > 4, f"{job_id}: post-candidate silence mismatch")
    audit = record.get("current_audit_status", {})
    require(audit.get("status") == "pending_finite_ending_evidence", f"{job_id}: audit status mismatch")
    require(audit.get("evidence_status") == "finite_tail_review_pending", f"{job_id}: audit evidence mismatch")
    require(set(audit.get("blocking_reasons", [])) == set(REQUIRED_BLOCKING_REASONS), f"{job_id}: blocking reasons mismatch")
    require(audit.get("public_exact_export_allowed") is False, f"{job_id}: public exact should be blocked")
    require(audit.get("promotion_allowed_by_run") is False, f"{job_id}: run promotion should be blocked")
    require(set(record.get("accepted_evidence_statuses", [])) == REQUIRED_STATUSES, f"{job_id}: accepted statuses mismatch")
    require(len(record.get("evidence_questions", [])) >= 4, f"{job_id}: evidence questions too thin")
    require(len(record.get("required_runtime_evidence", [])) >= 4, f"{job_id}: runtime evidence too thin")
    commands = record.get("commands", {})
    require("run_audio_finite_ending_evidence_plan.py" in str(commands.get("dry_run", "")), f"{job_id}: missing dry run")
    require("run_audio_finite_ending_evidence_plan.py" in str(commands.get("audit", "")), f"{job_id}: missing audit")
    require("build_audio_finite_ending_tail_metrics.py" in str(commands.get("build_tail_metrics", "")), f"{job_id}: missing build metrics")
    require("validate_audio_finite_ending_tail_metrics.py" in str(commands.get("validate_tail_metrics", "")), f"{job_id}: missing validate metrics")
    require("python tools/validate_audio_duration_uncertainty_register.py" in commands.get("post_evidence", []), f"{job_id}: missing post evidence validation")
    require(record.get("completion_gate"), f"{job_id}: missing completion gate")
    require(record.get("public_exact_export_allowed_by_packet") is False, f"{job_id}: public exact should remain blocked")
    require(record.get("promotion_allowed_by_packet") is False, f"{job_id}: packet promotion should be blocked")
    require(record.get("behavior_change_allowed") is False, f"{job_id}: behavior changes should be blocked")


def validate_batches(data: dict[str, Any]) -> None:
    tail_batches = {batch.get("group"): int(batch.get("job_count", 0)) for batch in data.get("operator_batches", {}).get("by_tail_classification", [])}
    focus_batches = {batch.get("group"): int(batch.get("job_count", 0)) for batch in data.get("operator_batches", {}).get("by_diagnostic_focus", [])}
    audit_batches = {batch.get("group"): int(batch.get("job_count", 0)) for batch in data.get("operator_batches", {}).get("by_audit_status", [])}
    require(tail_batches == REQUIRED_TAIL_COUNTS, "tail classification batches mismatch")
    require(focus_batches == REQUIRED_FOCUS_COUNTS, "diagnostic focus batches mismatch")
    require(audit_batches == {"pending_finite_ending_evidence": 5}, "audit status batches mismatch")
    for group in data.get("operator_batches", {}).values():
        for batch in group:
            count = int(batch.get("job_count", 0))
            require(len(batch.get("track_ids", [])) == count, "batch track count mismatch")
            require(len(batch.get("job_ids", [])) == count, "batch job count mismatch")


def validate(data: dict[str, Any]) -> None:
    require(data.get("schema") == "earthbound-decomp.audio-finite-transition-classification-packet.v1", "unexpected schema")
    require(data.get("status") == "finite_transition_classification_packet_ready_policy_preserved", "unexpected status")
    require(data.get("source_plan_status") == "finite_ending_evidence_plan_ready_preview_policy_preserved", "unexpected plan status")
    require(data.get("source_tail_status") == "finite_ending_tail_metrics_ready_policy_preserved", "unexpected tail status")
    require(data.get("source_run_mode") == "audit-current-export", "unexpected run mode")
    require(data.get("source_next_action_lane") == "finite_transition_tail_classification", "unexpected next-action lane")
    require(REQUIRED_REFERENCES <= set(data.get("references", [])), "missing references")
    summary = data.get("summary", {})
    records = data.get("records", [])
    require(int(summary.get("packet_job_count", 0)) == 5, "expected five packet jobs")
    require(len(records) == 5, "record count mismatch")
    require(set(summary.get("track_ids", [])) == REQUIRED_TRACK_IDS, "track summary mismatch")
    require(summary.get("tail_classification_counts") == REQUIRED_TAIL_COUNTS, "tail counts mismatch")
    require(summary.get("diagnostic_focus_counts") == REQUIRED_FOCUS_COUNTS, "focus counts mismatch")
    require(int(summary.get("nonzero_after_candidate_end_count", 0)) == 5, "nonzero tail count mismatch")
    require(int(summary.get("active_through_render_boundary_count", 0)) == 3, "active boundary count mismatch")
    require(int(summary.get("post_candidate_tail_nonzero_count", 0)) == 2, "post-candidate tail count mismatch")
    require(int(summary.get("pending_evidence_count", 0)) == 5, "pending evidence count mismatch")
    require(int(summary.get("ready_evidence_count", -1)) == 0, "ready evidence count mismatch")
    require(summary.get("blocking_reason_counts") == REQUIRED_BLOCKING_REASONS, "blocking reason counts mismatch")
    require(set(summary.get("accepted_evidence_statuses", [])) == REQUIRED_STATUSES, "accepted status summary mismatch")
    require(summary.get("public_exact_finite_export_ready") is False, "public exact finite should be blocked")
    require(summary.get("promotion_allowed_by_packet") is False, "packet promotion should be blocked")
    require(summary.get("behavior_change_allowed") is False, "behavior changes should be blocked")
    require(summary.get("tail_classification_counts") == count_records(records, ("tail_metrics", "tail_classification")), "tail counts do not match records")
    require(summary.get("diagnostic_focus_counts") == count_records(records, ("source_candidate", "diagnostic_focus")), "focus counts do not match records")
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
        "Audio finite-transition classification packet validation OK: "
        f"{data['summary']['packet_job_count']} jobs, "
        f"{data['summary']['pending_evidence_count']} pending"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
