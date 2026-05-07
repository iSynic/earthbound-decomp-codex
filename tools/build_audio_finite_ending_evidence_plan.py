#!/usr/bin/env python3
"""Build the focused finite-ending evidence plan for transition-review tracks."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_UNCERTAINTY = ROOT / "manifests" / "audio-duration-uncertainty-register.json"
DEFAULT_EXPORT_PLAN = ROOT / "manifests" / "audio-export-plan.json"
DEFAULT_ORACLE_PLAN = ROOT / "manifests" / "audio-oracle-comparison-plan-all-tracks.json"
DEFAULT_OUTPUT = ROOT / "manifests" / "audio-finite-ending-evidence-plan.json"
DEFAULT_NOTES = ROOT / "notes" / "audio-finite-ending-evidence-plan.md"
ASSUMED_RENDER_CHANNELS = 2
ASSUMED_RENDER_SAMPLE_RATE = 32000


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build audio finite-ending evidence plan.")
    parser.add_argument("--uncertainty", default=str(DEFAULT_UNCERTAINTY), help="Duration uncertainty register JSON.")
    parser.add_argument("--export-plan", default=str(DEFAULT_EXPORT_PLAN), help="Audio export plan JSON.")
    parser.add_argument("--oracle-plan", default=str(DEFAULT_ORACLE_PLAN), help="All-track oracle plan JSON.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Finite-ending evidence plan JSON output.")
    parser.add_argument("--notes", default=str(DEFAULT_NOTES), help="Finite-ending evidence plan markdown output.")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def by_track(records: list[dict[str, Any]]) -> dict[int, dict[str, Any]]:
    return {int(record["track_id"]): record for record in records}


def source_candidate(oracle_job: dict[str, Any]) -> dict[str, Any]:
    return {
        "oracle_job_id": oracle_job.get("job_id"),
        "diagnostic_focus": oracle_job.get("diagnostic_focus"),
        "source_spc": oracle_job.get("source_spc", {}),
        "source_render": oracle_job.get("source_render", {}),
        "reference_capture_outputs": oracle_job.get("reference_capture_outputs", {}),
    }


def finite_metadata(export_record: dict[str, Any]) -> dict[str, Any]:
    semantics = export_record.get("duration_semantics", {})
    evidence = semantics.get("evidence", {})
    metadata = evidence.get("finite_metadata", {})
    return {
        "classification": semantics.get("classification"),
        "exactness_basis": semantics.get("exactness_basis"),
        "sequence_command_promotion_allowed": semantics.get("sequence_command_promotion_allowed"),
        "sequence_command_status": semantics.get("sequence_command_status", {}),
        "public_exact_export_allowed": semantics.get("public_exact_export_allowed"),
        "finite_end_sample": metadata.get("finite_end_sample"),
        "finite_end_seconds": metadata.get("finite_end_seconds"),
        "evidence": metadata.get("evidence"),
        "measured_by": metadata.get("measured_by"),
    }


def render_tail_metrics(export_record: dict[str, Any], oracle_job: dict[str, Any]) -> dict[str, Any]:
    finite = finite_metadata(export_record)
    metrics = oracle_job.get("source_render", {}).get("metrics", {})
    finite_end_sample = finite.get("finite_end_sample")
    finite_end_seconds = finite.get("finite_end_seconds")
    last_nonzero = metrics.get("last_nonzero_sample_index")
    rendered_samples = metrics.get("rendered_samples")
    last_nonzero_frame = last_nonzero // ASSUMED_RENDER_CHANNELS if isinstance(last_nonzero, int) else None
    rendered_frames = rendered_samples // ASSUMED_RENDER_CHANNELS if isinstance(rendered_samples, int) else None
    nonzero_after_end = (
        isinstance(finite_end_sample, int)
        and isinstance(last_nonzero_frame, int)
        and last_nonzero_frame >= finite_end_sample
    )
    frames_after_candidate_end = (
        last_nonzero_frame - finite_end_sample
        if isinstance(finite_end_sample, int) and isinstance(last_nonzero_frame, int)
        else None
    )
    seconds_after_candidate_end = (
        round(frames_after_candidate_end / ASSUMED_RENDER_SAMPLE_RATE, 6)
        if isinstance(frames_after_candidate_end, int)
        else None
    )
    render_tail_frames_after_candidate = (
        rendered_frames - finite_end_sample
        if isinstance(finite_end_sample, int) and isinstance(rendered_frames, int)
        else None
    )
    inferred_sample_rate = (
        round(float(finite_end_sample) / float(finite_end_seconds))
        if isinstance(finite_end_sample, int) and isinstance(finite_end_seconds, (float, int)) and finite_end_seconds
        else None
    )
    return {
        "unit_policy": {
            "finite_end_sample": "pcm_frame_32000hz",
            "source_render_nonzero_index": "interleaved_pcm_sample_index",
            "normalized_tail_index": "pcm_frame_32000hz",
            "assumed_channels": ASSUMED_RENDER_CHANNELS,
            "assumed_sample_rate": ASSUMED_RENDER_SAMPLE_RATE,
            "inferred_sample_rate_from_finite_end": inferred_sample_rate,
        },
        "peak_abs_sample": metrics.get("peak_abs_sample"),
        "rms_sample": metrics.get("rms_sample"),
        "nonzero_sample_count": metrics.get("nonzero_sample_count"),
        "first_nonzero_sample_index": metrics.get("first_nonzero_sample_index"),
        "last_nonzero_sample_index": last_nonzero,
        "last_nonzero_frame_index": last_nonzero_frame,
        "rendered_samples": rendered_samples,
        "rendered_frames": rendered_frames,
        "voice_count": metrics.get("voice_count"),
        "finite_end_sample": finite_end_sample,
        "nonzero_after_candidate_end": nonzero_after_end,
        "frames_after_candidate_end": frames_after_candidate_end,
        "seconds_after_candidate_end": seconds_after_candidate_end,
        "render_tail_frames_after_candidate": render_tail_frames_after_candidate,
        "warning": metrics.get("warning", ""),
    }


def evidence_gap(export_record: dict[str, Any], oracle_job: dict[str, Any]) -> dict[str, Any]:
    finite = finite_metadata(export_record)
    tail = render_tail_metrics(export_record, oracle_job)
    missing_fields: list[str] = []
    for field in ("finite_end_sample", "finite_end_seconds", "evidence", "measured_by"):
        if finite.get(field) is None:
            missing_fields.append(field)
    if finite.get("evidence") == "trailing_pcm_silence_review_needed":
        missing_fields.append("explicit_tail_classification")
    if tail.get("nonzero_after_candidate_end") is True:
        missing_fields.append("post_candidate_tail_state")
    return {
        "status": "finite_tail_review_pending",
        "missing_fields": sorted(set(missing_fields)),
        "current_finite_metadata": finite,
        "current_render_tail_metrics": tail,
    }


def build_jobs(
    uncertainty: dict[str, Any],
    export_plan: dict[str, Any],
    oracle_plan: dict[str, Any],
) -> list[dict[str, Any]]:
    export_by_track = by_track(export_plan.get("tracks", []))
    oracle_by_track = by_track(oracle_plan.get("jobs", []))
    tracks = [
        record
        for record in uncertainty.get("tracks", [])
        if record.get("primary_uncertainty") == "finite_transition_review_pending"
    ]
    tracks.sort(key=lambda record: int(record["track_id"]))
    jobs: list[dict[str, Any]] = []
    for order, record in enumerate(tracks, start=1):
        track_id = int(record["track_id"])
        export_record = export_by_track[track_id]
        oracle_job = oracle_by_track[track_id]
        job_id = f"finite-ending-track-{track_id:03d}-{str(record['track_name']).lower()}"
        jobs.append(
            {
                "job_id": job_id,
                "execution_order": order,
                "track_id": track_id,
                "track_name": record["track_name"],
                "primary_uncertainty": record["primary_uncertainty"],
                "export_class": export_record.get("export_class"),
                "export_status": export_record.get("export_status"),
                "recommended_mode": export_record.get("recommended_mode"),
                "duration_seconds": export_record.get("duration_seconds"),
                "needs_sequence_semantics": export_record.get("needs_sequence_semantics"),
                "source_candidate": source_candidate(oracle_job),
                "finite_gap": evidence_gap(export_record, oracle_job),
                "evidence_questions": [
                    "Does the candidate end sample represent a true musical/SFX ending, or a transition/stinger boundary?",
                    "Do DSP voice key-off/envelope states and PCM tail metrics agree after the candidate boundary?",
                    "Does an extended render settle to silence/idle, or stay active past the candidate end?",
                    "Should this track remain blocked from public exact export as transition_or_stinger_policy?",
                ],
                "required_runtime_evidence": [
                    "DSP voice envelope/key-on/key-off state at the candidate finite end sample",
                    "PCM tail metrics around and after the candidate finite end sample",
                    "extended render or independent oracle capture proving silence/idle or continued activity after the candidate end",
                    "classification as true_finite_end, transition_or_stinger_policy, or unresolved_finite_boundary",
                ],
                "dry_run_command": f"python tools/run_audio_finite_ending_evidence_plan.py --job-id {job_id} --mode dry-run-plan",
                "audit_command": f"python tools/run_audio_finite_ending_evidence_plan.py --job-id {job_id} --mode audit-current-export",
                "promotion_allowed_by_plan": False,
                "post_evidence_commands": [
                    "python tools/build_audio_export_plan.py",
                    "python tools/validate_audio_export_plan.py",
                    "python tools/build_audio_duration_uncertainty_register.py",
                    "python tools/validate_audio_duration_uncertainty_register.py",
                ],
            }
        )
    return jobs


def build_plan(
    uncertainty: dict[str, Any],
    export_plan: dict[str, Any],
    oracle_plan: dict[str, Any],
) -> dict[str, Any]:
    jobs = build_jobs(uncertainty, export_plan, oracle_plan)
    focus_counts: Counter[str] = Counter(str(job["source_candidate"]["diagnostic_focus"]) for job in jobs)
    export_class_counts: Counter[str] = Counter(str(job["export_class"]) for job in jobs)
    mode_counts: Counter[str] = Counter(str(job["recommended_mode"]) for job in jobs)
    tail_counts: Counter[str] = Counter(str(job["finite_gap"]["status"]) for job in jobs)
    nonzero_after_candidate_count = sum(
        1
        for job in jobs
        if job["finite_gap"]["current_render_tail_metrics"].get("nonzero_after_candidate_end") is True
    )
    return {
        "schema": "earthbound-decomp.audio-finite-ending-evidence-plan.v1",
        "status": "finite_ending_evidence_plan_ready_preview_policy_preserved",
        "references": [
            "manifests/audio-duration-uncertainty-register.json",
            "manifests/audio-export-plan.json",
            "manifests/audio-oracle-comparison-plan-all-tracks.json",
        ],
        "summary": {
            "job_count": len(jobs),
            "track_ids": [int(job["track_id"]) for job in jobs],
            "track_names": [str(job["track_name"]) for job in jobs],
            "export_class_counts": dict(sorted(export_class_counts.items())),
            "recommended_mode_counts": dict(sorted(mode_counts.items())),
            "diagnostic_focus_counts": dict(sorted(focus_counts.items())),
            "finite_gap_status_counts": dict(sorted(tail_counts.items())),
            "nonzero_after_candidate_end_count": nonzero_after_candidate_count,
            "promotion_allowed_by_plan": False,
            "public_exact_finite_export_ready": False,
        },
        "decision_policy": [
            "Current playback/export behavior stays review-needed trim candidate until tail evidence is explicit.",
            "Trailing PCM silence measurement alone does not promote these tracks to public exact finite exports.",
            "A true finite ending requires candidate-end sample evidence plus post-boundary silence/idle state.",
            "A transition/stinger classification is valid evidence only if public exact finite export remains blocked or gets a separate policy.",
        ],
        "accepted_evidence_statuses": [
            "true_finite_end",
            "transition_or_stinger_policy",
            "unresolved_finite_boundary",
        ],
        "post_evidence_validation_commands": [
            "python tools/run_audio_finite_ending_evidence_plan.py --mode audit-current-export",
            "python tools/validate_audio_finite_ending_evidence_run_summary.py",
            "python tools/validate_audio_finite_ending_evidence_plan.py",
            "python tools/validate_audio_export_plan.py",
            "python tools/validate_audio_duration_uncertainty_register.py",
        ],
        "jobs": jobs,
    }


def render_markdown(data: dict[str, Any]) -> str:
    summary = data["summary"]
    rows = [
        "| {order} | `{track_id:03d}` | `{track_name}` | `{focus}` | `{status}` | `{end}` | `{last_frame}` | `{tail_seconds}` | `{after}` |".format(
            order=job["execution_order"],
            track_id=job["track_id"],
            track_name=job["track_name"],
            focus=job["source_candidate"]["diagnostic_focus"],
            status=job["finite_gap"]["status"],
            end=job["finite_gap"]["current_finite_metadata"]["finite_end_sample"],
            last_frame=job["finite_gap"]["current_render_tail_metrics"]["last_nonzero_frame_index"],
            tail_seconds=job["finite_gap"]["current_render_tail_metrics"]["seconds_after_candidate_end"],
            after=job["finite_gap"]["current_render_tail_metrics"]["nonzero_after_candidate_end"],
        )
        for job in data["jobs"]
    ]
    return "\n".join(
        [
            "# Audio Finite Ending Evidence Plan",
            "",
            "Status: finite-ending evidence plan is ready; current review-needed export behavior remains unchanged.",
            "",
            "## Summary",
            "",
            f"- jobs: `{summary['job_count']}`",
            f"- tracks: `{summary['track_names']}`",
            f"- export classes: `{summary['export_class_counts']}`",
            f"- recommended modes: `{summary['recommended_mode_counts']}`",
            f"- diagnostic focus counts: `{summary['diagnostic_focus_counts']}`",
            f"- finite gap statuses: `{summary['finite_gap_status_counts']}`",
            f"- nonzero after candidate end: `{summary['nonzero_after_candidate_end_count']}`",
            f"- promotion allowed by plan: `{summary['promotion_allowed_by_plan']}`",
            f"- public exact finite export ready: `{summary['public_exact_finite_export_ready']}`",
            "",
            "## Decision Policy",
            "",
            *[f"- {item}" for item in data["decision_policy"]],
            "",
            "## Jobs",
            "",
            "| Order | Track | Name | Oracle focus | Evidence status | Candidate end frame | Last nonzero frame | Tail seconds | Nonzero after end |",
            "| ---: | ---: | --- | --- | --- | ---: | ---: | ---: | --- |",
            *rows,
            "",
            "## Accepted Evidence Statuses",
            "",
            *[f"- `{status}`" for status in data["accepted_evidence_statuses"]],
            "",
            "## Post Evidence Validation",
            "",
            *[f"- `{command}`" for command in data["post_evidence_validation_commands"]],
            "",
            "## Remaining Uncertainty",
            "",
            "- The five tracks still need explicit true-ending versus transition/stinger classification.",
            "- Current diagnostic render metrics show nonzero PCM after the candidate finite end for every selected track.",
            "- Public exact finite export remains blocked until runtime/oracle tail evidence is imported and validated.",
            "",
        ]
    )


def main() -> int:
    args = parse_args()
    data = build_plan(
        load_json(Path(args.uncertainty)),
        load_json(Path(args.export_plan)),
        load_json(Path(args.oracle_plan)),
    )
    output = Path(args.output)
    notes = Path(args.notes)
    output.parent.mkdir(parents=True, exist_ok=True)
    notes.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    notes.write_text(render_markdown(data), encoding="utf-8")
    print(
        "Built audio finite-ending evidence plan: "
        f"{data['summary']['job_count']} jobs, "
        f"{data['summary']['nonzero_after_candidate_end_count']} with post-candidate nonzero PCM"
    )
    print(f"Wrote {output}")
    print(f"Wrote {notes}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
