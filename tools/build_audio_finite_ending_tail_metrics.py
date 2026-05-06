#!/usr/bin/env python3
"""Build frame-normalized finite-ending tail metrics from the committed evidence plan."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PLAN = ROOT / "manifests" / "audio-finite-ending-evidence-plan.json"
DEFAULT_OUTPUT = ROOT / "manifests" / "audio-finite-ending-tail-metrics.json"
DEFAULT_NOTES = ROOT / "notes" / "audio-finite-ending-tail-metrics.md"
RENDER_BOUNDARY_ACTIVE_TOLERANCE_FRAMES = 4


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build finite-ending tail metrics report.")
    parser.add_argument("--plan", default=str(DEFAULT_PLAN), help="Finite-ending evidence plan JSON.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Tail metrics JSON output.")
    parser.add_argument("--notes", default=str(DEFAULT_NOTES), help="Tail metrics markdown output.")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def classify_tail(tail: dict[str, Any]) -> str:
    if tail.get("nonzero_after_candidate_end") is not True:
        return "candidate_end_silence_unconfirmed"
    rendered_frames = tail.get("rendered_frames")
    last_nonzero_frame = tail.get("last_nonzero_frame_index")
    if isinstance(rendered_frames, int) and isinstance(last_nonzero_frame, int):
        trailing_silent_frames = rendered_frames - last_nonzero_frame - 1
        if 0 <= trailing_silent_frames <= RENDER_BOUNDARY_ACTIVE_TOLERANCE_FRAMES:
            return "active_through_render_boundary"
    return "post_candidate_tail_nonzero"


def metric_record(job: dict[str, Any]) -> dict[str, Any]:
    gap = job.get("finite_gap", {})
    finite = gap.get("current_finite_metadata", {})
    tail = gap.get("current_render_tail_metrics", {})
    rendered_frames = tail.get("rendered_frames")
    last_nonzero_frame = tail.get("last_nonzero_frame_index")
    trailing_silent_frames = (
        rendered_frames - last_nonzero_frame - 1
        if isinstance(rendered_frames, int) and isinstance(last_nonzero_frame, int)
        else None
    )
    classification = classify_tail(tail)
    return {
        "track_id": int(job["track_id"]),
        "track_name": job["track_name"],
        "job_id": job["job_id"],
        "diagnostic_focus": job.get("source_candidate", {}).get("diagnostic_focus"),
        "duration_seconds": job.get("duration_seconds"),
        "candidate_end_frame": finite.get("finite_end_sample"),
        "candidate_end_seconds": finite.get("finite_end_seconds"),
        "source_metric_units": tail.get("unit_policy", {}),
        "last_nonzero_interleaved_sample_index": tail.get("last_nonzero_sample_index"),
        "last_nonzero_frame_index": last_nonzero_frame,
        "frames_after_candidate_end": tail.get("frames_after_candidate_end"),
        "seconds_after_candidate_end": tail.get("seconds_after_candidate_end"),
        "rendered_frames": rendered_frames,
        "rendered_interleaved_samples": tail.get("rendered_samples"),
        "trailing_silent_frames_at_render_end": trailing_silent_frames,
        "peak_abs_sample": tail.get("peak_abs_sample"),
        "rms_sample": tail.get("rms_sample"),
        "voice_count": tail.get("voice_count"),
        "tail_classification": classification,
        "public_exact_export_allowed": finite.get("public_exact_export_allowed"),
        "exact_export_implication": "blocked_pending_runtime_tail_classification",
    }


def build_report(plan: dict[str, Any]) -> dict[str, Any]:
    records = [metric_record(job) for job in plan.get("jobs", [])]
    records.sort(key=lambda item: int(item["track_id"]))
    class_counts: Counter[str] = Counter(str(record["tail_classification"]) for record in records)
    focus_counts: Counter[str] = Counter(str(record["diagnostic_focus"]) for record in records)
    return {
        "schema": "earthbound-decomp.audio-finite-ending-tail-metrics.v1",
        "status": "finite_ending_tail_metrics_ready_policy_preserved",
        "references": [
            "manifests/audio-finite-ending-evidence-plan.json",
            "manifests/audio-duration-uncertainty-register.json",
            "manifests/audio-export-plan.json",
            "manifests/audio-oracle-comparison-plan-all-tracks.json",
        ],
        "source_plan_status": plan.get("status"),
        "unit_policy": {
            "candidate_end_frame": "pcm_frame_32000hz",
            "last_nonzero_frame_index": "interleaved source sample index divided by stereo channel count",
            "render_boundary_active_tolerance_frames": RENDER_BOUNDARY_ACTIVE_TOLERANCE_FRAMES,
        },
        "summary": {
            "record_count": len(records),
            "track_ids": [int(record["track_id"]) for record in records],
            "tail_classification_counts": dict(sorted(class_counts.items())),
            "diagnostic_focus_counts": dict(sorted(focus_counts.items())),
            "nonzero_after_candidate_end_count": sum(
                1 for record in records if int(record.get("frames_after_candidate_end", -1)) >= 0
            ),
            "active_through_render_boundary_count": int(class_counts.get("active_through_render_boundary", 0)),
            "public_exact_finite_export_ready": False,
            "promotion_allowed_by_report": False,
        },
        "decision_policy": [
            "This report normalizes source-render sample indexes to 32 kHz PCM frames before comparing them to finite-end samples.",
            "Post-candidate PCM activity is diagnostic evidence only; it does not change export trimming or playback behavior.",
            "Tracks active through the render boundary need runtime/oracle state evidence before a true finite ending can be claimed.",
            "Tracks with shorter post-candidate tails still need transition/stinger versus true-release classification.",
        ],
        "records": records,
    }


def render_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    rows = [
        "| {track_id:03d} | `{track_name}` | `{classification}` | {end} | {last} | {frames_after} | {seconds_after} | {trailing} |".format(
            track_id=record["track_id"],
            track_name=record["track_name"],
            classification=record["tail_classification"],
            end=record["candidate_end_frame"],
            last=record["last_nonzero_frame_index"],
            frames_after=record["frames_after_candidate_end"],
            seconds_after=record["seconds_after_candidate_end"],
            trailing=record["trailing_silent_frames_at_render_end"],
        )
        for record in report["records"]
    ]
    return "\n".join(
        [
            "# Audio Finite Ending Tail Metrics",
            "",
            "Status: finite-ending tail metrics are frame-normalized; current export behavior remains unchanged.",
            "",
            "## Summary",
            "",
            f"- records: `{summary['record_count']}`",
            f"- tail classifications: `{summary['tail_classification_counts']}`",
            f"- diagnostic focus counts: `{summary['diagnostic_focus_counts']}`",
            f"- nonzero after candidate end: `{summary['nonzero_after_candidate_end_count']}`",
            f"- active through render boundary: `{summary['active_through_render_boundary_count']}`",
            f"- public exact finite export ready: `{summary['public_exact_finite_export_ready']}`",
            "",
            "## Unit Policy",
            "",
            f"- candidate end frame: `{report['unit_policy']['candidate_end_frame']}`",
            f"- last nonzero frame: `{report['unit_policy']['last_nonzero_frame_index']}`",
            f"- render-boundary active tolerance: `{report['unit_policy']['render_boundary_active_tolerance_frames']}` frames",
            "",
            "## Records",
            "",
            "| Track | Name | Tail classification | Candidate end frame | Last nonzero frame | Tail frames | Tail seconds | Silent frames at render end |",
            "| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: |",
            *rows,
            "",
            "## Decision Policy",
            "",
            *[f"- {item}" for item in report["decision_policy"]],
            "",
            "## Remaining Uncertainty",
            "",
            "- `BATTLE_SWIRL2`, `NEW_FRIEND`, and `BATTLE_SWIRL4` are active through the diagnostic render boundary.",
            "- `BATTLE_SWIRL1` and `SOMEONE_JOINS` have shorter nonzero post-candidate tails and still need true-release versus transition classification.",
            "- No public exact finite duration can be promoted from this report alone.",
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
        "Built finite-ending tail metrics: "
        f"{report['summary']['record_count']} records, "
        f"classifications {report['summary']['tail_classification_counts']}"
    )
    print(f"Wrote {output}")
    print(f"Wrote {notes}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
