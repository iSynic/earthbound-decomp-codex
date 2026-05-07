#!/usr/bin/env python3
"""Build a classification packet for loop-point versus held-policy evidence."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PLAN = ROOT / "manifests" / "audio-loop-point-evidence-plan.json"
DEFAULT_TAIL = ROOT / "manifests" / "audio-loop-point-tail-metrics.json"
DEFAULT_RUN_SUMMARY = ROOT / "build" / "audio" / "loop-point-evidence-runs" / "loop-point-evidence-run-summary.json"
DEFAULT_NEXT_ACTIONS = ROOT / "manifests" / "audio-duration-next-actions-plan.json"
DEFAULT_OUTPUT = ROOT / "manifests" / "audio-loop-hold-classification-packet.json"
DEFAULT_NOTES = ROOT / "notes" / "audio-loop-hold-classification-packet.md"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build loop/hold classification packet.")
    parser.add_argument("--plan", default=str(DEFAULT_PLAN), help="Loop-point evidence plan JSON.")
    parser.add_argument("--tail", default=str(DEFAULT_TAIL), help="Loop-point tail metrics JSON.")
    parser.add_argument("--run-summary", default=str(DEFAULT_RUN_SUMMARY), help="Loop-point evidence run summary JSON.")
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
        if lane.get("lane_id") == "loop_point_or_hold_classification":
            return lane
    return {}


def compact_pack_context(pack_context: dict[str, Any]) -> dict[str, Any]:
    source = pack_context.get("primary_pack_source", {})
    return {
        "primary_sample_pack": pack_context.get("primary_sample_pack"),
        "secondary_sample_pack": pack_context.get("secondary_sample_pack"),
        "sequence_pack": pack_context.get("sequence_pack"),
        "no_dedicated_sequence_pack": bool(pack_context.get("no_dedicated_sequence_pack")),
        "primary_pack_source": {
            "asset_id": source.get("asset_id"),
            "range": source.get("range"),
            "sha1": source.get("sha1"),
            "stream_summary": source.get("stream_summary", {}),
        },
    }


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
    diagnostic = tail_record.get("diagnostic_render", {})
    loop_gap = plan_job.get("loop_gap", {})
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
        "loop_preview_policy": plan_job.get("loop_preview_policy", {}),
        "pack_context": compact_pack_context(plan_job.get("pack_context", {})),
        "source_candidate": compact_source(plan_job.get("source_candidate", {})),
        "loop_gap": {
            "status": loop_gap.get("status"),
            "missing_fields": loop_gap.get("missing_fields", []),
            "required_evidence": loop_gap.get("required_evidence", []),
            "preview_policy": loop_gap.get("preview_policy", {}),
        },
        "tail_metrics": {
            "unit_policy": diagnostic.get("unit_policy", {}),
            "tail_classification": tail_record["tail_classification"],
            "first_nonzero_interleaved_sample_index": diagnostic.get("first_nonzero_sample_index"),
            "first_nonzero_frame_index": diagnostic.get("first_nonzero_frame_index"),
            "last_nonzero_interleaved_sample_index": diagnostic.get("last_nonzero_sample_index"),
            "last_nonzero_frame_index": diagnostic.get("last_nonzero_frame_index"),
            "rendered_samples": diagnostic.get("rendered_samples"),
            "rendered_frames": diagnostic.get("rendered_frames"),
            "render_seconds": diagnostic.get("render_seconds"),
            "trailing_silent_frames_at_render_end": diagnostic.get("trailing_silent_frames_at_render_end"),
            "active_through_render_boundary": bool(diagnostic.get("active_through_render_boundary")),
            "peak_abs_sample": diagnostic.get("peak_abs_sample"),
            "rms_sample": diagnostic.get("rms_sample"),
            "voice_count": diagnostic.get("voice_count"),
        },
        "current_audit_status": {
            "status": run_record.get("status"),
            "evidence_status": run_record.get("evidence_status"),
            "blocking_reasons": run_record.get("blocking_reasons", []),
            "missing_fields": run_record.get("missing_fields", []),
            "preview_policy": run_record.get("preview_policy", {}),
            "promotion_allowed_by_run": bool(run_record.get("promotion_allowed_by_run")),
        },
        "accepted_evidence_statuses": [
            "exact_loop_points_available",
            "held_policy_no_exact_loop_points",
            "unresolved_loop_or_hold_policy",
        ],
        "evidence_questions": plan_job.get("evidence_questions", []),
        "required_runtime_evidence": plan_job.get("required_runtime_evidence", []),
        "commands": {
            "dry_run": plan_job.get("dry_run_command"),
            "audit": plan_job.get("audit_command"),
            "build_tail_metrics": "python tools/build_audio_loop_point_tail_metrics.py",
            "validate_tail_metrics": "python tools/validate_audio_loop_point_tail_metrics.py",
            "post_evidence": plan_job.get("post_evidence_commands", []),
        },
        "completion_gate": (
            "Classify the candidate as exact_loop_points_available, held_policy_no_exact_loop_points, "
            "or unresolved_loop_or_hold_policy using DSP state, BRR sample-loop evidence, PCM repeat/hold "
            "analysis, or independent oracle evidence."
        ),
        "public_exact_loop_export_allowed_by_packet": False,
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
    lane = find_next_action_lane(next_actions)
    return {
        "schema": "earthbound-decomp.audio-loop-hold-classification-packet.v1",
        "status": "loop_hold_classification_packet_ready_preview_policy_preserved",
        "references": [
            "manifests/audio-loop-point-evidence-plan.json",
            "manifests/audio-loop-point-tail-metrics.json",
            "build/audio/loop-point-evidence-runs/loop-point-evidence-run-summary.json",
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
            "primary_sample_pack_counts": tail_summary.get("primary_sample_pack_counts", {}),
            "missing_exact_loop_field_count": int(tail_summary.get("missing_exact_loop_field_count", 0)),
            "active_through_render_boundary_count": int(tail_summary.get("active_through_render_boundary_count", 0)),
            "pending_evidence_count": int(run_summary.get("pending_loop_evidence_count", 0)),
            "ready_evidence_count": int(run_summary.get("loop_evidence_ready_count", 0)),
            "blocking_reason_counts": run_summary.get("blocking_reason_counts", {}),
            "accepted_evidence_statuses": plan.get("accepted_evidence_statuses", []),
            "preview_policy_loop_count": int(plan.get("summary", {}).get("preview_policy_loop_count", 0)),
            "preview_policy_fade_seconds": plan.get("summary", {}).get("preview_policy_fade_seconds"),
            "public_exact_loop_export_ready": False,
            "promotion_allowed_by_packet": False,
            "behavior_change_allowed": False,
        },
        "operator_batches": {
            "by_tail_classification": grouped(records, ("tail_metrics", "tail_classification")),
            "by_diagnostic_focus": grouped(records, ("source_candidate", "diagnostic_focus")),
            "by_audit_status": grouped(records, ("current_audit_status", "status")),
            "by_primary_sample_pack": grouped(records, ("pack_context", "primary_sample_pack")),
        },
        "classification_policy": [
            "This packet is diagnostic only and preserves current playback/export behavior.",
            "Activity through the diagnostic render boundary supports loop/held prioritization but does not prove exact loop points.",
            "Public loop export remains loop-count-plus-fade preview until exact loop points or a held-policy classification are validated.",
            "Exact loop metadata requires sample-accurate intro_samples, loop_start_sample, loop_end_sample, and measured_by evidence.",
            "A held_policy_no_exact_loop_points classification can be valid while still keeping public exact loop export blocked.",
            "Sequence command promotion remains separate from this loop/hold packet.",
        ],
        "records": records,
        "post_packet_validation_commands": [
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
        ],
    }


def render_markdown(data: dict[str, Any]) -> str:
    summary = data["summary"]
    rows = [
        "| {order} | {track:03d} | `{name}` | `{focus}` | {last_frame} | {silence} | `{status}` |".format(
            order=record["execution_order"],
            track=record["track_id"],
            name=record["track_name"],
            focus=record["source_candidate"]["diagnostic_focus"],
            last_frame=record["tail_metrics"]["last_nonzero_frame_index"],
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
        for batch in data["operator_batches"]["by_diagnostic_focus"]
    ]
    command_rows = [f"- `{command}`" for command in data["post_packet_validation_commands"]]
    return "\n".join(
        [
            "# Audio Loop/Hold Classification Packet",
            "",
            "Status: loop/held candidates are packaged for exact loop-point or held-policy classification; current playback/export behavior is preserved.",
            "",
            "## Summary",
            "",
            f"- packet jobs: `{summary['packet_job_count']}`",
            f"- tracks: `{summary['track_ids']}`",
            f"- tail classifications: `{summary['tail_classification_counts']}`",
            f"- diagnostic focus counts: `{summary['diagnostic_focus_counts']}`",
            f"- primary sample pack counts: `{summary['primary_sample_pack_counts']}`",
            f"- missing exact loop fields: `{summary['missing_exact_loop_field_count']}`",
            f"- active through render boundary: `{summary['active_through_render_boundary_count']}`",
            f"- pending evidence: `{summary['pending_evidence_count']}`",
            f"- ready evidence: `{summary['ready_evidence_count']}`",
            f"- blocking reasons: `{summary['blocking_reason_counts']}`",
            f"- accepted evidence statuses: `{summary['accepted_evidence_statuses']}`",
            "",
            "## Diagnostic Batches",
            "",
            "| Diagnostic focus | Jobs | Tracks |",
            "| --- | ---: | --- |",
            *batch_rows,
            "",
            "## Classification Jobs",
            "",
            "| Order | Track | Name | Diagnostic focus | Last nonzero frame | Silent frames at render end | Audit status |",
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
            "- All five loop/held candidates still need explicit runtime/oracle classification.",
            "- All five are active through the 30-second diagnostic render boundary.",
            "- Exact public loop metadata remains blocked by 20 missing intro/start/end/measured_by fields.",
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
        "Built loop/hold classification packet: "
        f"{data['summary']['packet_job_count']} jobs, "
        f"{data['summary']['pending_evidence_count']} pending"
    )
    print(f"Wrote {output}")
    print(f"Wrote {notes}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
