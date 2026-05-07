#!/usr/bin/env python3
"""Build frame-normalized loop/held preview tail metrics from the loop-point evidence plan."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PLAN = ROOT / "manifests" / "audio-loop-point-evidence-plan.json"
DEFAULT_OUTPUT = ROOT / "manifests" / "audio-loop-point-tail-metrics.json"
DEFAULT_NOTES = ROOT / "notes" / "audio-loop-point-tail-metrics.md"
ASSUMED_RENDER_CHANNELS = 2
ASSUMED_RENDER_SAMPLE_RATE = 32000
RENDER_BOUNDARY_ACTIVE_TOLERANCE_FRAMES = 4


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build loop/held preview tail metrics report.")
    parser.add_argument("--plan", default=str(DEFAULT_PLAN), help="Loop-point evidence plan JSON.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Tail metrics JSON output.")
    parser.add_argument("--notes", default=str(DEFAULT_NOTES), help="Tail metrics markdown output.")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def frame_metrics(source_render: dict[str, Any]) -> dict[str, Any]:
    metrics = source_render.get("metrics", {})
    rendered_samples = metrics.get("rendered_samples")
    first_nonzero_sample = metrics.get("first_nonzero_sample_index")
    last_nonzero_sample = metrics.get("last_nonzero_sample_index")
    rendered_frames = rendered_samples // ASSUMED_RENDER_CHANNELS if isinstance(rendered_samples, int) else None
    first_nonzero_frame = first_nonzero_sample // ASSUMED_RENDER_CHANNELS if isinstance(first_nonzero_sample, int) else None
    last_nonzero_frame = last_nonzero_sample // ASSUMED_RENDER_CHANNELS if isinstance(last_nonzero_sample, int) else None
    trailing_silent_frames = (
        rendered_frames - last_nonzero_frame - 1
        if isinstance(rendered_frames, int) and isinstance(last_nonzero_frame, int)
        else None
    )
    render_seconds = (
        round(rendered_frames / ASSUMED_RENDER_SAMPLE_RATE, 6) if isinstance(rendered_frames, int) else None
    )
    active_through_boundary = (
        isinstance(trailing_silent_frames, int)
        and 0 <= trailing_silent_frames <= RENDER_BOUNDARY_ACTIVE_TOLERANCE_FRAMES
    )
    return {
        "unit_policy": {
            "source_render_nonzero_index": "interleaved_pcm_sample_index",
            "normalized_nonzero_index": "pcm_frame_32000hz",
            "assumed_channels": ASSUMED_RENDER_CHANNELS,
            "assumed_sample_rate": ASSUMED_RENDER_SAMPLE_RATE,
            "render_boundary_active_tolerance_frames": RENDER_BOUNDARY_ACTIVE_TOLERANCE_FRAMES,
        },
        "peak_abs_sample": metrics.get("peak_abs_sample"),
        "rms_sample": metrics.get("rms_sample"),
        "nonzero_sample_count": metrics.get("nonzero_sample_count"),
        "first_nonzero_sample_index": first_nonzero_sample,
        "first_nonzero_frame_index": first_nonzero_frame,
        "last_nonzero_sample_index": last_nonzero_sample,
        "last_nonzero_frame_index": last_nonzero_frame,
        "rendered_samples": rendered_samples,
        "rendered_frames": rendered_frames,
        "render_seconds": render_seconds,
        "trailing_silent_frames_at_render_end": trailing_silent_frames,
        "active_through_render_boundary": active_through_boundary,
        "voice_count": metrics.get("voice_count"),
        "warning": metrics.get("warning", ""),
    }


def classify_tail(metrics: dict[str, Any]) -> str:
    if metrics.get("active_through_render_boundary") is True:
        return "active_through_diagnostic_render_boundary"
    if int(metrics.get("last_nonzero_frame_index", -1)) >= 0:
        return "post_attack_tail_then_silence"
    return "missing_or_silent_render_metrics"


def metric_record(job: dict[str, Any]) -> dict[str, Any]:
    metrics = frame_metrics(job.get("source_candidate", {}).get("source_render", {}))
    preview = job.get("loop_preview_policy", {})
    gap = job.get("loop_gap", {})
    return {
        "track_id": int(job["track_id"]),
        "track_name": job["track_name"],
        "job_id": job["job_id"],
        "diagnostic_focus": job.get("source_candidate", {}).get("diagnostic_focus"),
        "primary_sample_pack": int(job.get("pack_context", {}).get("primary_sample_pack", -1)),
        "no_dedicated_sequence_pack": bool(job.get("pack_context", {}).get("no_dedicated_sequence_pack")),
        "current_public_preview_duration_seconds": job.get("duration_seconds"),
        "current_public_preview_policy": {
            "loop_count": preview.get("loop_count"),
            "fade_seconds": preview.get("fade_seconds"),
            "recommended_mode": preview.get("current_public_mode"),
        },
        "diagnostic_render": metrics,
        "loop_gap_status": gap.get("status"),
        "missing_loop_fields": gap.get("missing_fields", []),
        "tail_classification": classify_tail(metrics),
        "exact_loop_export_implication": "blocked_pending_loop_or_hold_classification",
        "promotion_allowed_by_report": False,
    }


def build_report(plan: dict[str, Any]) -> dict[str, Any]:
    records = [metric_record(job) for job in plan.get("jobs", [])]
    records.sort(key=lambda item: int(item["track_id"]))
    class_counts: Counter[str] = Counter(str(record["tail_classification"]) for record in records)
    focus_counts: Counter[str] = Counter(str(record["diagnostic_focus"]) for record in records)
    pack_counts: Counter[str] = Counter(str(record["primary_sample_pack"]) for record in records)
    return {
        "schema": "earthbound-decomp.audio-loop-point-tail-metrics.v1",
        "status": "loop_point_tail_metrics_ready_preview_policy_preserved",
        "references": [
            "manifests/audio-loop-point-evidence-plan.json",
            "manifests/audio-duration-uncertainty-register.json",
            "manifests/audio-export-plan.json",
            "manifests/audio-pack-contracts.json",
            "manifests/audio-oracle-comparison-plan-all-tracks.json",
        ],
        "source_plan_status": plan.get("status"),
        "unit_policy": {
            "source_render_nonzero_index": "interleaved_pcm_sample_index",
            "normalized_nonzero_index": "pcm_frame_32000hz",
            "render_boundary_active_tolerance_frames": RENDER_BOUNDARY_ACTIVE_TOLERANCE_FRAMES,
            "diagnostic_render_seconds": 30.0,
            "public_preview_duration_seconds": 120.0,
        },
        "summary": {
            "record_count": len(records),
            "track_ids": [int(record["track_id"]) for record in records],
            "tail_classification_counts": dict(sorted(class_counts.items())),
            "diagnostic_focus_counts": dict(sorted(focus_counts.items())),
            "primary_sample_pack_counts": dict(sorted(pack_counts.items())),
            "active_through_render_boundary_count": int(class_counts.get("active_through_diagnostic_render_boundary", 0)),
            "missing_exact_loop_field_count": sum(len(record["missing_loop_fields"]) for record in records),
            "public_exact_loop_export_ready": False,
            "promotion_allowed_by_report": False,
        },
        "decision_policy": [
            "This report measures diagnostic render tails only; it does not derive sample-accurate intro/start/end loop points.",
            "All source-render nonzero indexes are normalized from interleaved stereo sample indexes to 32 kHz PCM frames.",
            "Activity through the diagnostic render boundary supports loop/held prioritization but does not prove exact loop points.",
            "Public loop export remains loop-count-plus-fade preview until exact loop points or a held-policy classification are validated.",
        ],
        "records": records,
    }


def render_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    rows = [
        "| {track_id:03d} | `{track_name}` | `{classification}` | {render_seconds} | {last_frame} | {trailing} | `{missing}` |".format(
            track_id=record["track_id"],
            track_name=record["track_name"],
            classification=record["tail_classification"],
            render_seconds=record["diagnostic_render"]["render_seconds"],
            last_frame=record["diagnostic_render"]["last_nonzero_frame_index"],
            trailing=record["diagnostic_render"]["trailing_silent_frames_at_render_end"],
            missing=record["missing_loop_fields"],
        )
        for record in report["records"]
    ]
    return "\n".join(
        [
            "# Audio Loop Point Tail Metrics",
            "",
            "Status: loop/held diagnostic tail metrics are frame-normalized; current loop-count/fade preview behavior remains unchanged.",
            "",
            "## Summary",
            "",
            f"- records: `{summary['record_count']}`",
            f"- tail classifications: `{summary['tail_classification_counts']}`",
            f"- diagnostic focus counts: `{summary['diagnostic_focus_counts']}`",
            f"- primary sample packs: `{summary['primary_sample_pack_counts']}`",
            f"- active through diagnostic render boundary: `{summary['active_through_render_boundary_count']}`",
            f"- missing exact loop fields: `{summary['missing_exact_loop_field_count']}`",
            f"- public exact loop export ready: `{summary['public_exact_loop_export_ready']}`",
            "",
            "## Unit Policy",
            "",
            f"- source nonzero index: `{report['unit_policy']['source_render_nonzero_index']}`",
            f"- normalized nonzero index: `{report['unit_policy']['normalized_nonzero_index']}`",
            f"- diagnostic render seconds: `{report['unit_policy']['diagnostic_render_seconds']}`",
            f"- public preview duration seconds: `{report['unit_policy']['public_preview_duration_seconds']}`",
            "",
            "## Records",
            "",
            "| Track | Name | Tail classification | Render seconds | Last nonzero frame | Silent frames at render end | Missing loop fields |",
            "| ---: | --- | --- | ---: | ---: | ---: | --- |",
            *rows,
            "",
            "## Decision Policy",
            "",
            *[f"- {item}" for item in report["decision_policy"]],
            "",
            "## Remaining Uncertainty",
            "",
            "- All five loop/held candidates are active through the diagnostic render boundary.",
            "- Exact loop metadata is still placeholder-only: intro, loop start, loop end, and measured_by remain missing for every track.",
            "- The next runtime evidence needs to decide exact loop points versus held-policy/no-exact-loop classification.",
            "",
        ]
    )


def main() -> int:
    args = parse_args()
    report = build_report(load_json(Path(args.plan)))
    output = Path(args.output)
    notes = Path(args.notes)
    output.parent.mkdir(parents=True, exist_ok=True)
    notes.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    notes.write_text(render_markdown(report), encoding="utf-8")
    print(
        "Built loop-point tail metrics: "
        f"{report['summary']['record_count']} records, "
        f"classifications {report['summary']['tail_classification_counts']}"
    )
    print(f"Wrote {output}")
    print(f"Wrote {notes}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
