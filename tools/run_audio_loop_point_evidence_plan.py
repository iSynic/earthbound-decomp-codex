#!/usr/bin/env python3
"""Run non-mutating checks for the audio loop-point evidence plan."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PLAN = ROOT / "manifests" / "audio-loop-point-evidence-plan.json"
DEFAULT_SUMMARY = ROOT / "build" / "audio" / "loop-point-evidence-runs" / "loop-point-evidence-run-summary.json"
READY_STATUSES = {"exact_loop_points_available", "held_policy_no_exact_loop_points"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run audio loop-point evidence plan checks.")
    parser.add_argument("--plan", default=str(DEFAULT_PLAN), help="Committed loop-point evidence plan JSON.")
    parser.add_argument(
        "--mode",
        default="audit-current-export",
        choices=["dry-run-plan", "audit-current-export"],
        help="Emit checklist records only, or audit current export-plan loop metadata in the committed plan.",
    )
    parser.add_argument("--track-id", type=int, action="append", help="Track id to include. May be repeated.")
    parser.add_argument("--job-id", action="append", help="Loop evidence job id to include. May be repeated.")
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
        return ["loop_point_evidence_not_audited"]
    gap = job.get("loop_gap", {})
    reasons: list[str] = []
    if gap.get("status") == "placeholder_only_exact_loop_points_pending":
        reasons.append("placeholder_loop_points_pending")
    for field in gap.get("missing_fields", []):
        reasons.append(f"missing_{field}")
    if job.get("pack_context", {}).get("no_dedicated_sequence_pack") is True:
        reasons.append("held_or_sample_loop_policy_unresolved")
    if job.get("promotion_allowed_by_plan") is not False:
        reasons.append("promotion_policy_not_blocked")
    return sorted(set(reasons))


def run_one(job: dict[str, Any], *, mode: str) -> dict[str, Any]:
    gap = job.get("loop_gap", {})
    evidence_status = "not_audited" if mode == "dry-run-plan" else str(gap.get("status"))
    ready = mode == "audit-current-export" and evidence_status in READY_STATUSES and not gap.get("missing_fields")
    status = "loop_evidence_ready" if ready else "pending_loop_evidence"
    reasons = [] if ready else blocking_reasons(job, mode=mode)
    return {
        "execution_order": int(job["execution_order"]),
        "job_id": job["job_id"],
        "track_id": int(job["track_id"]),
        "track_name": job["track_name"],
        "mode": mode,
        "status": status,
        "evidence_status": evidence_status,
        "blocking_reasons": reasons,
        "primary_sample_pack": int(job.get("pack_context", {}).get("primary_sample_pack", -1)),
        "no_dedicated_sequence_pack": bool(job.get("pack_context", {}).get("no_dedicated_sequence_pack")),
        "diagnostic_focus": job.get("source_candidate", {}).get("diagnostic_focus"),
        "missing_fields": gap.get("missing_fields", []),
        "preview_policy": job.get("loop_preview_policy", {}),
        "promotion_allowed_by_run": False,
    }


def write_summary(plan: dict[str, Any], summary_path: Path, args: argparse.Namespace, runs: list[dict[str, Any]]) -> None:
    status_counts: Counter[str] = Counter(str(run.get("status")) for run in runs)
    evidence_status_counts: Counter[str] = Counter(str(run.get("evidence_status")) for run in runs)
    blocking_reason_counts: Counter[str] = Counter()
    pack_counts: Counter[str] = Counter(str(run.get("primary_sample_pack")) for run in runs)
    focus_counts: Counter[str] = Counter(str(run.get("diagnostic_focus")) for run in runs)
    for run in runs:
        for reason in run.get("blocking_reasons", []):
            blocking_reason_counts[str(reason)] += 1
    summary = {
        "schema": "earthbound-decomp.audio-loop-point-evidence-run.v1",
        "plan": "manifests/audio-loop-point-evidence-plan.json",
        "plan_status": plan.get("status"),
        "mode": args.mode,
        "selected_count": len(runs),
        "loop_evidence_ready_count": int(status_counts.get("loop_evidence_ready", 0)),
        "pending_loop_evidence_count": int(status_counts.get("pending_loop_evidence", 0)),
        "status_counts": dict(sorted(status_counts.items())),
        "evidence_status_counts": dict(sorted(evidence_status_counts.items())),
        "blocking_reason_counts": dict(sorted(blocking_reason_counts.items())),
        "primary_sample_pack_counts": dict(sorted(pack_counts.items())),
        "diagnostic_focus_counts": dict(sorted(focus_counts.items())),
        "promotion_allowed_by_run": False,
        "public_exact_loop_export_ready_by_run": len(runs) > 0 and int(status_counts.get("pending_loop_evidence", 0)) == 0,
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
    print(f"Selected {len(selected)} loop-point evidence jobs for {args.mode} mode")
    runs = [run_one(job, mode=args.mode) for job in selected]
    for run in runs:
        print(f"- {run['execution_order']:03d} {run['job_id']}: {run['status']}")
    write_summary(plan, Path(args.summary), args, runs)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
