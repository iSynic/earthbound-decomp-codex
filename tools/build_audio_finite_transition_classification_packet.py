#!/usr/bin/env python3
"""Build a classification packet for finite-transition audio tail evidence."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PLAN = ROOT / "manifests" / "audio-finite-ending-evidence-plan.json"
DEFAULT_TAIL = ROOT / "manifests" / "audio-finite-ending-tail-metrics.json"
DEFAULT_RUN_SUMMARY = ROOT / "build" / "audio" / "finite-ending-evidence-runs" / "finite-ending-evidence-run-summary.json"
DEFAULT_NEXT_ACTIONS = ROOT / "manifests" / "audio-duration-next-actions-plan.json"
DEFAULT_OUTPUT = ROOT / "manifests" / "audio-finite-transition-classification-packet.json"
DEFAULT_NOTES = ROOT / "notes" / "audio-finite-transition-classification-packet.md"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build finite-transition classification packet.")
    parser.add_argument("--plan", default=str(DEFAULT_PLAN), help="Finite-ending evidence plan JSON.")
    parser.add_argument("--tail", default=str(DEFAULT_TAIL), help="Finite-ending tail metrics JSON.")
    parser.add_argument("--run-summary", default=str(DEFAULT_RUN_SUMMARY), help="Finite-ending evidence run summary JSON.")
    parser.add_argument("--next-actions", default=str(DEFAULT_NEXT_ACTIONS), help="Audio duration next-actions plan JSON.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Classification packet JSON output.")
    parser.add_argument("--notes", default=str(DEFAULT_NOTES), help="Classification packet markdown output.")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def by_job_id(records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(record.get("job_id")): record for record in records}


def find_next_action_lane(next_actions: dict[str, Any]) -> dict[str, Any]:
    for lane in next_actions.get("priority_lanes", []):
        if lane.get("lane_id") == "finite_transition_tail_classification":
            return lane
    return {}


def compact_source(source: dict[str, Any]) -> dict[str, Any]:
    source_spc = source.get("source_spc", {})
    source_render = source.get("source_render", {})
    return {
        "oracle_job_id": source.get("oracle_job_id"),
        "diagnostic_focus": source.get("diagnostic_focus"),
        "source_spc": {
            "path": source_spc.get("path"),
            "sha1": source_spc.get("sha1"),
            "bytes": source_spc.get("bytes"),
        },
        "source_render": {
            "path": source_render.get("path"),
            "sha1": source_render.get("sha1"),
            "bytes": source_render.get("bytes"),
            "metrics": source_render.get("metrics", {}),
        },
        "reference_capture_outputs": source.get("reference_capture_outputs", {}),
    }


def classification_record(plan_job: dict[str, Any], tail_record: dict[str, Any], run_record: dict[str, Any]) -> dict[str, Any]:
    gap = plan_job.get("finite_gap", {})
    finite = gap.get("current_finite_metadata", {})
    return {
        "execution_order": int(plan_job["execution_order"]),
        "job_id": plan_job["job_id"],
        "track_id": int(plan_job["track_id"]),
        "track_name": plan_job["track_name"],
        "primary_uncertainty": plan_job["primary_uncertainty"],
        "export_class": plan_job["export_class"],
        "export_status": plan_job["export_status"],
        "recommended_mode": plan_job["recommended_mode"],
        "duration_seconds": plan_job.get("duration_seconds"),
        "needs_sequence_semantics": bool(plan_job.get("needs_sequence_semantics")),
        "source_candidate": compact_source(plan_job.get("source_candidate", {})),
        "candidate_end": {
            "frame": int(tail_record["candidate_end_frame"]),
            "seconds": tail_record["candidate_end_seconds"],
            "metadata_frame": finite.get("finite_end_sample"),
            "metadata_seconds": finite.get("finite_end_seconds"),
            "measured_by": finite.get("measured_by"),
        },
        "tail_metrics": {
            "unit_policy": tail_record.get("source_metric_units", {}),
            "tail_classification": tail_record["tail_classification"],
            "last_nonzero_interleaved_sample_index": tail_record["last_nonzero_interleaved_sample_index"],
            "last_nonzero_frame_index": tail_record["last_nonzero_frame_index"],
            "frames_after_candidate_end": tail_record["frames_after_candidate_end"],
            "seconds_after_candidate_end": tail_record["seconds_after_candidate_end"],
            "rendered_frames": tail_record["rendered_frames"],
            "trailing_silent_frames_at_render_end": tail_record["trailing_silent_frames_at_render_end"],
            "active_through_render_boundary": tail_record["tail_classification"] == "active_through_render_boundary",
            "peak_abs_sample": tail_record["peak_abs_sample"],
            "rms_sample": tail_record["rms_sample"],
            "voice_count": tail_record["voice_count"],
        },
        "current_audit_status": {
            "status": run_record.get("status"),
            "evidence_status": run_record.get("evidence_status"),
            "blocking_reasons": run_record.get("blocking_reasons", []),
            "public_exact_export_allowed": bool(run_record.get("public_exact_export_allowed")),
            "promotion_allowed_by_run": bool(run_record.get("promotion_allowed_by_run")),
        },
        "accepted_evidence_statuses": ["true_finite_end", "transition_or_stinger_policy", "unresolved_finite_boundary"],
        "evidence_questions": plan_job.get("evidence_questions", []),
        "required_runtime_evidence": plan_job.get("required_runtime_evidence", []),
        "commands": {
            "dry_run": plan_job.get("dry_run_command"),
            "audit": plan_job.get("audit_command"),
            "build_tail_metrics": "python tools/build_audio_finite_ending_tail_metrics.py",
            "validate_tail_metrics": "python tools/validate_audio_finite_ending_tail_metrics.py",
            "post_evidence": plan_job.get("post_evidence_commands", []),
        },
        "completion_gate": (
            "Classify the candidate boundary as true_finite_end, transition_or_stinger_policy, "
            "or unresolved_finite_boundary using DSP state, PCM tail, extended render, or independent oracle evidence."
        ),
        "public_exact_export_allowed_by_packet": False,
        "promotion_allowed_by_packet": False,
        "behavior_change_allowed": False,
    }


def grouped(records: list[dict[str, Any]], key_path: tuple[str, ...]) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        value: Any = record
        for key in key_path:
            value = value.get(key, {}) if isinstance(value, dict) else None
        groups[str(value)].append(record)
    batches: list[dict[str, Any]] = []
    for value, items in groups.items():
        items.sort(key=lambda item: int(item["execution_order"]))
        batches.append(
            {
                "group": value,
                "job_count": len(items),
                "execution_orders": [int(item["execution_order"]) for item in items],
                "track_ids": [int(item["track_id"]) for item in items],
                "job_ids": [str(item["job_id"]) for item in items],
            }
        )
    return sorted(batches, key=lambda item: min(item["execution_orders"]))


def build_packet(plan: dict[str, Any], tail: dict[str, Any], run_summary: dict[str, Any], next_actions: dict[str, Any]) -> dict[str, Any]:
    tail_by_job = by_job_id(tail.get("records", []))
    run_by_job = by_job_id(run_summary.get("runs", []))
    records = [
        classification_record(job, tail_by_job[str(job["job_id"])], run_by_job[str(job["job_id"])])
        for job in plan.get("jobs", [])
    ]
    records.sort(key=lambda record: int(record["execution_order"]))
    tail_summary = tail.get("summary", {})
    run_counts = run_summary.get("blocking_reason_counts", {})
    lane = find_next_action_lane(next_actions)
    return {
        "schema": "earthbound-decomp.audio-finite-transition-classification-packet.v1",
        "status": "finite_transition_classification_packet_ready_policy_preserved",
        "references": [
            "manifests/audio-finite-ending-evidence-plan.json",
            "manifests/audio-finite-ending-tail-metrics.json",
            "build/audio/finite-ending-evidence-runs/finite-ending-evidence-run-summary.json",
            "manifests/audio-duration-next-actions-plan.json",
        ],
        "source_plan_status": plan.get("status"),
        "source_tail_status": tail.get("status"),
        "source_run_mode": run_summary.get("mode"),
        "source_next_action_lane": lane.get("lane_id"),
        "summary": {
            "packet_job_count": len(records),
            "track_ids": [int(record["track_id"]) for record in records],
            "tail_classification_counts": tail_summary.get("tail_classification_counts", {}),
            "diagnostic_focus_counts": tail_summary.get("diagnostic_focus_counts", {}),
            "nonzero_after_candidate_end_count": int(tail_summary.get("nonzero_after_candidate_end_count", 0)),
            "active_through_render_boundary_count": int(tail_summary.get("active_through_render_boundary_count", 0)),
            "post_candidate_tail_nonzero_count": int(tail_summary.get("tail_classification_counts", {}).get("post_candidate_tail_nonzero", 0)),
            "pending_evidence_count": int(run_summary.get("pending_finite_ending_evidence_count", 0)),
            "ready_evidence_count": int(run_summary.get("finite_ending_evidence_ready_count", 0)),
            "blocking_reason_counts": run_counts,
            "accepted_evidence_statuses": plan.get("accepted_evidence_statuses", []),
            "public_exact_finite_export_ready": False,
            "promotion_allowed_by_packet": False,
            "behavior_change_allowed": False,
        },
        "operator_batches": {
            "by_tail_classification": grouped(records, ("tail_metrics", "tail_classification")),
            "by_diagnostic_focus": grouped(records, ("source_candidate", "diagnostic_focus")),
            "by_audit_status": grouped(records, ("current_audit_status", "status")),
        },
        "classification_policy": [
            "This packet is diagnostic only and preserves current playback/export behavior.",
            "Post-candidate PCM activity blocks public exact finite export until explicit runtime/oracle classification is imported.",
            "Tracks active through the diagnostic render boundary need stronger evidence than candidate-end timing alone.",
            "Shorter post-candidate tails still need transition/stinger versus true-release classification.",
            "A transition_or_stinger_policy classification can be valid while still keeping public exact finite export blocked.",
            "Sequence command promotion remains blocked until separate zero/nonzero control evidence is consumed.",
        ],
        "records": records,
        "post_packet_validation_commands": [
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
        ],
    }


def render_markdown(data: dict[str, Any]) -> str:
    summary = data["summary"]
    rows = [
        "| {order} | {track:03d} | `{name}` | `{tail}` | {tail_seconds} | {silence} | `{status}` |".format(
            order=record["execution_order"],
            track=record["track_id"],
            name=record["track_name"],
            tail=record["tail_metrics"]["tail_classification"],
            tail_seconds=record["tail_metrics"]["seconds_after_candidate_end"],
            silence=record["tail_metrics"]["trailing_silent_frames_at_render_end"],
            status=record["current_audit_status"]["status"],
        )
        for record in data["records"]
    ]
    batch_rows = [
        "| `{group}` | {count} | `{tracks}` |".format(
            group=batch["group"],
            count=batch["job_count"],
            tracks=batch["track_ids"],
        )
        for batch in data["operator_batches"]["by_tail_classification"]
    ]
    command_rows = [f"- `{command}`" for command in data["post_packet_validation_commands"]]
    return "\n".join(
        [
            "# Audio Finite-Transition Classification Packet",
            "",
            "Status: finite-transition candidates are packaged for runtime/oracle tail classification; current playback/export behavior is preserved.",
            "",
            "## Summary",
            "",
            f"- packet jobs: `{summary['packet_job_count']}`",
            f"- tracks: `{summary['track_ids']}`",
            f"- tail classifications: `{summary['tail_classification_counts']}`",
            f"- nonzero after candidate end: `{summary['nonzero_after_candidate_end_count']}`",
            f"- active through render boundary: `{summary['active_through_render_boundary_count']}`",
            f"- pending evidence: `{summary['pending_evidence_count']}`",
            f"- ready evidence: `{summary['ready_evidence_count']}`",
            f"- blocking reasons: `{summary['blocking_reason_counts']}`",
            f"- accepted evidence statuses: `{summary['accepted_evidence_statuses']}`",
            "",
            "## Tail Batches",
            "",
            "| Tail classification | Jobs | Tracks |",
            "| --- | ---: | --- |",
            *batch_rows,
            "",
            "## Classification Jobs",
            "",
            "| Order | Track | Name | Tail classification | Tail seconds | Silent frames at render end | Audit status |",
            "| ---: | ---: | --- | --- | ---: | ---: | --- |",
            *rows,
            "",
            "## Validation After Evidence",
            "",
            *command_rows,
            "",
            "## Classification Policy",
            "",
            *[f"- {item}" for item in data["classification_policy"]],
            "",
            "## Remaining Uncertainty",
            "",
            "- All five candidate finite endings still need explicit runtime/oracle classification.",
            "- Three tracks are active through the 30-second diagnostic render boundary.",
            "- Two tracks have shorter post-candidate nonzero tails but still need transition/stinger versus true-release evidence.",
            "",
        ]
    )


def main() -> int:
    args = parse_args()
    data = build_packet(
        load_json(Path(args.plan)),
        load_json(Path(args.tail)),
        load_json(Path(args.run_summary)),
        load_json(Path(args.next_actions)),
    )
    output = Path(args.output)
    notes = Path(args.notes)
    output.parent.mkdir(parents=True, exist_ok=True)
    notes.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    notes.write_text(render_markdown(data), encoding="utf-8")
    print(
        "Built finite-transition classification packet: "
        f"{data['summary']['packet_job_count']} jobs, "
        f"{data['summary']['pending_evidence_count']} pending"
    )
    print(f"Wrote {output}")
    print(f"Wrote {notes}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
