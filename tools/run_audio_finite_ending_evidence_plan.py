#!/usr/bin/env python3
"""Run non-mutating checks for the audio finite-ending evidence plan."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PLAN = ROOT / "manifests" / "audio-finite-ending-evidence-plan.json"
DEFAULT_SUMMARY = ROOT / "build" / "audio" / "finite-ending-evidence-runs" / "finite-ending-evidence-run-summary.json"
READY_STATUSES = {"true_finite_end", "transition_or_stinger_policy"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run audio finite-ending evidence plan checks.")
    parser.add_argument("--plan", default=str(DEFAULT_PLAN), help="Committed finite-ending evidence plan JSON.")
    parser.add_argument(
        "--mode",
        default="audit-current-export",
        choices=["dry-run-plan", "audit-current-export"],
        help="Emit checklist records only, or audit current export-plan finite evidence in the committed plan.",
    )
    parser.add_argument("--track-id", type=int, action="append", help="Track id to include. May be repeated.")
    parser.add_argument("--job-id", action="append", help="Finite-ending evidence job id to include. May be repeated.")
    parser.add_argument("--limit", type=int, help="Maximum selected jobs to include.")
    parser.add_argument("--summary", default=str(DEFAULT_SUMMARY), help="Ignored run summary output.")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def select_jobs(plan: dict[str, Any], args: argparse.Namespace) -> list[dict[str, Any]]:
    track_ids = set(args.track_id or [])
    job_ids = set(args.job_id or [])
    jobs: list[dict[str, Any]] = []
    for job in plan.get("jobs", []):
        if track_ids and int(job.get("track_id", -1)) not in track_ids:
            continue
        if job_ids and str(job.get("job_id")) not in job_ids:
            continue
        jobs.append(job)
    available_job_ids = {str(job.get("job_id")) for job in plan.get("jobs", [])}
    available_track_ids = {int(job.get("track_id", -1)) for job in plan.get("jobs", [])}
    missing_jobs = job_ids - available_job_ids
    missing_tracks = track_ids - available_track_ids
    if missing_jobs:
        raise ValueError(f"requested job ids not found: {', '.join(sorted(missing_jobs))}")
    if missing_tracks:
        raise ValueError(f"requested track ids not found: {sorted(missing_tracks)}")
    jobs.sort(key=lambda item: int(item.get("execution_order", 0)))
    if args.limit is not None:
        jobs = jobs[: args.limit]
    return jobs


def blocking_reasons(job: dict[str, Any], *, mode: str) -> list[str]:
    if mode == "dry-run-plan":
        return ["finite_ending_evidence_not_audited"]
    gap = job.get("finite_gap", {})
    finite = gap.get("current_finite_metadata", {})
    tail = gap.get("current_render_tail_metrics", {})
    reasons: list[str] = []
    if gap.get("status") == "finite_tail_review_pending":
        reasons.append("finite_tail_review_pending")
    if "explicit_tail_classification" in gap.get("missing_fields", []):
        reasons.append("missing_explicit_tail_classification")
    if tail.get("nonzero_after_candidate_end") is True:
        reasons.append("nonzero_pcm_after_candidate_end")
    if finite.get("public_exact_export_allowed") is False:
        reasons.append("public_exact_export_blocked")
    if job.get("needs_sequence_semantics") is True:
        reasons.append("sequence_semantics_required")
    if job.get("promotion_allowed_by_plan") is not False:
        reasons.append("promotion_policy_not_blocked")
    return sorted(set(reasons))


def run_one(job: dict[str, Any], *, mode: str) -> dict[str, Any]:
    gap = job.get("finite_gap", {})
    evidence_status = "not_audited" if mode == "dry-run-plan" else str(gap.get("status"))
    ready = (
        mode == "audit-current-export"
        and evidence_status in READY_STATUSES
        and not gap.get("missing_fields")
        and job.get("promotion_allowed_by_plan") is False
    )
    status = "finite_ending_evidence_ready" if ready else "pending_finite_ending_evidence"
    reasons = [] if ready else blocking_reasons(job, mode=mode)
    tail = gap.get("current_render_tail_metrics", {})
    finite = gap.get("current_finite_metadata", {})
    return {
        "execution_order": int(job["execution_order"]),
        "job_id": job["job_id"],
        "track_id": int(job["track_id"]),
        "track_name": job["track_name"],
        "mode": mode,
        "status": status,
        "evidence_status": evidence_status,
        "blocking_reasons": reasons,
        "diagnostic_focus": job.get("source_candidate", {}).get("diagnostic_focus"),
        "finite_end_sample": finite.get("finite_end_sample"),
        "finite_end_seconds": finite.get("finite_end_seconds"),
        "last_nonzero_sample_index": tail.get("last_nonzero_sample_index"),
        "nonzero_after_candidate_end": tail.get("nonzero_after_candidate_end"),
        "samples_after_candidate_end": tail.get("samples_after_candidate_end"),
        "needs_sequence_semantics": bool(job.get("needs_sequence_semantics")),
        "public_exact_export_allowed": bool(finite.get("public_exact_export_allowed")),
        "promotion_allowed_by_run": False,
    }


def write_summary(plan: dict[str, Any], summary_path: Path, args: argparse.Namespace, runs: list[dict[str, Any]]) -> None:
    status_counts: Counter[str] = Counter(str(run.get("status")) for run in runs)
    evidence_status_counts: Counter[str] = Counter(str(run.get("evidence_status")) for run in runs)
    blocking_reason_counts: Counter[str] = Counter()
    focus_counts: Counter[str] = Counter(str(run.get("diagnostic_focus")) for run in runs)
    for run in runs:
        for reason in run.get("blocking_reasons", []):
            blocking_reason_counts[str(reason)] += 1
    ready_count = int(status_counts.get("finite_ending_evidence_ready", 0))
    pending_count = int(status_counts.get("pending_finite_ending_evidence", 0))
    summary = {
        "schema": "earthbound-decomp.audio-finite-ending-evidence-run.v1",
        "plan": "manifests/audio-finite-ending-evidence-plan.json",
        "plan_status": plan.get("status"),
        "mode": args.mode,
        "selected_count": len(runs),
        "finite_ending_evidence_ready_count": ready_count,
        "pending_finite_ending_evidence_count": pending_count,
        "status_counts": dict(sorted(status_counts.items())),
        "evidence_status_counts": dict(sorted(evidence_status_counts.items())),
        "blocking_reason_counts": dict(sorted(blocking_reason_counts.items())),
        "diagnostic_focus_counts": dict(sorted(focus_counts.items())),
        "nonzero_after_candidate_end_count": sum(1 for run in runs if run.get("nonzero_after_candidate_end") is True),
        "promotion_allowed_by_run": False,
        "public_exact_finite_export_ready_by_run": len(runs) > 0 and pending_count == 0,
        "selection": {
            "track_id": args.track_id or [],
            "job_id": args.job_id or [],
            "limit": args.limit,
        },
        "runs": runs,
    }
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    plan = load_json(Path(args.plan))
    selected = select_jobs(plan, args)
    print(f"Selected {len(selected)} finite-ending evidence jobs for {args.mode} mode")
    runs = [run_one(job, mode=args.mode) for job in selected]
    for run in runs:
        print(f"- {run['execution_order']:03d} {run['job_id']}: {run['status']}")
    write_summary(plan, Path(args.summary), args, runs)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
