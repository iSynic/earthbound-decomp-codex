#!/usr/bin/env python3
"""Validate the focused audio finite-ending evidence plan."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PLAN = ROOT / "manifests" / "audio-finite-ending-evidence-plan.json"
REQUIRED_REFERENCES = {
    "manifests/audio-duration-uncertainty-register.json",
    "manifests/audio-export-plan.json",
    "manifests/audio-oracle-comparison-plan-all-tracks.json",
}
REQUIRED_TRACK_IDS = {8, 9, 11, 123, 176}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate audio finite-ending evidence plan.")
    parser.add_argument("plan", nargs="?", default=str(DEFAULT_PLAN))
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


def validate(data: dict[str, Any]) -> None:
    require(data.get("schema") == "earthbound-decomp.audio-finite-ending-evidence-plan.v1", "unexpected schema")
    require(data.get("status") == "finite_ending_evidence_plan_ready_preview_policy_preserved", "unexpected status")
    require(REQUIRED_REFERENCES <= set(data.get("references", [])), "missing references")
    jobs = data.get("jobs", [])
    summary = data.get("summary", {})
    require(len(jobs) == 5, f"expected 5 finite-ending evidence jobs, got {len(jobs)}")
    require(int(summary.get("job_count", -1)) == len(jobs), "job count mismatch")
    require(set(summary.get("track_ids", [])) == REQUIRED_TRACK_IDS, "summary track coverage mismatch")
    require(summary.get("export_class_counts") == {"finite_or_transition_review_candidate": 5}, "export class counts mismatch")
    require(
        summary.get("recommended_mode_counts") == {"trim_candidate_after_manual_or_sequence_review": 5},
        "recommended mode counts mismatch",
    )
    require(summary.get("diagnostic_focus_counts") == count_records(jobs, ("source_candidate", "diagnostic_focus")), "focus counts mismatch")
    require(summary.get("finite_gap_status_counts") == {"finite_tail_review_pending": 5}, "finite gap counts mismatch")
    require(int(summary.get("nonzero_after_candidate_end_count", -1)) == 5, "expected all jobs to need post-candidate tail review")
    require(summary.get("promotion_allowed_by_plan") is False, "plan must not allow promotion")
    require(summary.get("public_exact_finite_export_ready") is False, "public exact finite export should remain blocked")

    seen_orders: set[int] = set()
    seen_track_ids: set[int] = set()
    for job in jobs:
        job_id = str(job.get("job_id", ""))
        track_id = int(job.get("track_id", -1))
        order = int(job.get("execution_order", 0))
        require(order > 0, f"{job_id}: invalid execution order")
        require(order not in seen_orders, f"{job_id}: duplicate execution order")
        seen_orders.add(order)
        require(track_id in REQUIRED_TRACK_IDS, f"{job_id}: unexpected track id {track_id}")
        require(track_id not in seen_track_ids, f"{job_id}: duplicate track id")
        seen_track_ids.add(track_id)
        require(job_id.startswith(f"finite-ending-track-{track_id:03d}-"), f"{job_id}: bad job id")
        require(job.get("primary_uncertainty") == "finite_transition_review_pending", f"{job_id}: wrong uncertainty")
        require(job.get("export_class") == "finite_or_transition_review_candidate", f"{job_id}: wrong export class")
        require(job.get("export_status") == "review_needed_before_public_exact_export", f"{job_id}: wrong export status")
        require(job.get("recommended_mode") == "trim_candidate_after_manual_or_sequence_review", f"{job_id}: wrong recommended mode")
        require(float(job.get("duration_seconds", 0.0)) > 0.0, f"{job_id}: missing duration")
        require(job.get("needs_sequence_semantics") is True, f"{job_id}: expected sequence semantics gate")
        source = job.get("source_candidate", {})
        require(source.get("oracle_job_id", "").startswith("oracle-track-"), f"{job_id}: missing oracle job")
        require(source.get("source_spc", {}).get("path"), f"{job_id}: missing source SPC")
        require(source.get("source_spc", {}).get("sha1"), f"{job_id}: missing source SPC SHA-1")
        require(source.get("source_render", {}).get("path"), f"{job_id}: missing source render")
        require(source.get("source_render", {}).get("sha1"), f"{job_id}: missing source render SHA-1")
        require(source.get("reference_capture_outputs", {}).get("comparison_result"), f"{job_id}: missing comparison output path")
        gap = job.get("finite_gap", {})
        require(gap.get("status") == "finite_tail_review_pending", f"{job_id}: unexpected finite gap status")
        missing = set(gap.get("missing_fields", []))
        require("explicit_tail_classification" in missing, f"{job_id}: missing tail classification gap")
        require("post_candidate_tail_state" in missing, f"{job_id}: missing post-candidate tail gap")
        finite = gap.get("current_finite_metadata", {})
        require(finite.get("classification") == "finite_or_transition_review", f"{job_id}: wrong finite classification")
        require(finite.get("exactness_basis") == "review_required", f"{job_id}: wrong exactness basis")
        require(finite.get("sequence_command_promotion_allowed") is False, f"{job_id}: sequence promotion should be blocked")
        require(finite.get("public_exact_export_allowed") is False, f"{job_id}: public exact export should be blocked")
        require(int(finite.get("finite_end_sample", 0)) > 0, f"{job_id}: missing finite end sample")
        require(float(finite.get("finite_end_seconds", 0.0)) > 0.0, f"{job_id}: missing finite end seconds")
        require(finite.get("evidence") == "trailing_pcm_silence_review_needed", f"{job_id}: unexpected finite evidence status")
        require(finite.get("measured_by") == "audio_export_duration_measurement", f"{job_id}: unexpected measurement source")
        tail = gap.get("current_render_tail_metrics", {})
        require(tail.get("nonzero_after_candidate_end") is True, f"{job_id}: expected nonzero PCM after candidate end")
        policy = tail.get("unit_policy", {})
        require(policy.get("finite_end_sample") == "pcm_frame_32000hz", f"{job_id}: bad finite-end unit policy")
        require(policy.get("source_render_nonzero_index") == "interleaved_pcm_sample_index", f"{job_id}: bad source metric unit policy")
        require(int(policy.get("assumed_channels", 0)) == 2, f"{job_id}: expected stereo render policy")
        require(int(policy.get("assumed_sample_rate", 0)) == 32000, f"{job_id}: expected 32 kHz render policy")
        require(int(tail.get("last_nonzero_frame_index", -1)) >= int(tail.get("finite_end_sample", 0)), f"{job_id}: bad tail ordering")
        require(int(tail.get("rendered_frames", 0)) > int(tail.get("finite_end_sample", 0)), f"{job_id}: render should extend past candidate")
        require(int(tail.get("frames_after_candidate_end", -1)) >= 0, f"{job_id}: missing frame-normalized tail delta")
        require(float(tail.get("seconds_after_candidate_end", -1.0)) >= 0.0, f"{job_id}: missing tail seconds")
        require(len(job.get("evidence_questions", [])) >= 4, f"{job_id}: evidence questions too thin")
        require(len(job.get("required_runtime_evidence", [])) >= 4, f"{job_id}: runtime evidence too thin")
        require("run_audio_finite_ending_evidence_plan.py" in str(job.get("dry_run_command", "")), f"{job_id}: missing dry-run command")
        require("--mode dry-run-plan" in str(job.get("dry_run_command", "")), f"{job_id}: bad dry-run command")
        require("run_audio_finite_ending_evidence_plan.py" in str(job.get("audit_command", "")), f"{job_id}: missing audit command")
        require("--mode audit-current-export" in str(job.get("audit_command", "")), f"{job_id}: bad audit command")
        require(job.get("promotion_allowed_by_plan") is False, f"{job_id}: job must not allow promotion")
        for command in (
            "python tools/build_audio_export_plan.py",
            "python tools/validate_audio_export_plan.py",
            "python tools/build_audio_duration_uncertainty_register.py",
            "python tools/validate_audio_duration_uncertainty_register.py",
        ):
            require(command in job.get("post_evidence_commands", []), f"{job_id}: missing post evidence command {command}")

    require(seen_orders == set(range(1, len(jobs) + 1)), "execution orders must be contiguous")
    require(seen_track_ids == REQUIRED_TRACK_IDS, "track coverage mismatch")
    require("true_finite_end" in data.get("accepted_evidence_statuses", []), "missing true finite status")
    require("transition_or_stinger_policy" in data.get("accepted_evidence_statuses", []), "missing transition policy status")
    require(data.get("decision_policy"), "missing decision policy")
    for command in (
        "python tools/run_audio_finite_ending_evidence_plan.py --mode audit-current-export",
        "python tools/validate_audio_finite_ending_evidence_run_summary.py",
        "python tools/validate_audio_finite_ending_evidence_plan.py",
        "python tools/validate_audio_export_plan.py",
        "python tools/validate_audio_duration_uncertainty_register.py",
    ):
        require(command in data.get("post_evidence_validation_commands", []), f"missing validation command {command}")


def main() -> int:
    args = parse_args()
    data = json.loads(Path(args.plan).read_text(encoding="utf-8"))
    validate(data)
    print(
        "Audio finite-ending evidence plan validation OK: "
        f"{data['summary']['job_count']} jobs, "
        f"{data['summary']['nonzero_after_candidate_end_count']} post-candidate tails"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
