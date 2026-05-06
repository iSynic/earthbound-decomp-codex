#!/usr/bin/env python3
"""Run selected jobs from the unified audio probe campaign."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CAMPAIGN = ROOT / "manifests" / "audio-probe-campaign-plan.json"
DEFAULT_SUMMARY = ROOT / "build" / "audio" / "probe-campaign-runs" / "probe-campaign-run-summary.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run selected audio probe campaign jobs.")
    parser.add_argument("--campaign", default=str(DEFAULT_CAMPAIGN), help="Committed campaign plan JSON.")
    parser.add_argument(
        "--mode",
        default="dry-run-stub",
        choices=["dry-run-stub", "stub-shape"],
        help="Use lane runner dry-run mode or lane runner external mode with schema-only stub harnesses.",
    )
    parser.add_argument("--phase", action="append", help="Campaign phase to include. May be repeated.")
    parser.add_argument("--lane", action="append", choices=["zero", "nonzero"], help="Lane to include. May be repeated.")
    parser.add_argument("--job-id", action="append", help="Specific lane job id to include. May be repeated.")
    parser.add_argument("--limit", type=int, help="Maximum number of selected campaign jobs to run.")
    parser.add_argument("--force", action="store_true", help="Re-run lane jobs that already have result JSON.")
    parser.add_argument("--stop-on-error", action="store_true", help="Stop at the first failed campaign job.")
    parser.add_argument("--summary", default=str(DEFAULT_SUMMARY), help="Ignored campaign run summary output.")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def repo_path(path_text: str) -> Path:
    path = Path(path_text)
    return path if path.is_absolute() else ROOT / path


def select_jobs(campaign: dict[str, Any], args: argparse.Namespace) -> list[dict[str, Any]]:
    phases = set(args.phase or [])
    lanes = set(args.lane or [])
    job_ids = set(args.job_id or [])
    jobs: list[dict[str, Any]] = []
    for job in campaign.get("campaign_jobs", []):
        if phases and job.get("phase") not in phases:
            continue
        if lanes and job.get("lane") not in lanes:
            continue
        if job_ids and job.get("job_id") not in job_ids:
            continue
        jobs.append(job)
    missing = job_ids - {str(job.get("job_id")) for job in campaign.get("campaign_jobs", [])}
    if missing:
        raise ValueError(f"requested job ids not found: {', '.join(sorted(missing))}")
    jobs.sort(key=lambda item: int(item.get("execution_order", 0)))
    if args.limit is not None:
        jobs = jobs[: args.limit]
    return jobs


def lane_runner(job: dict[str, Any]) -> str:
    if job["lane"] == "zero":
        return "tools/run_audio_zero_runtime_probe_batch.py"
    return "tools/run_audio_nonzero_control_probe_batch.py"


def lane_stub(job: dict[str, Any]) -> str:
    if job["lane"] == "zero":
        return "tools/audio_zero_runtime_probe_stub_harness.py"
    return "tools/audio_nonzero_control_probe_stub_harness.py"


def lane_batch_summary(summary_root: Path, job: dict[str, Any]) -> Path:
    return summary_root / "lane-batches" / f"{job['execution_order']:03d}-{job['job_id']}.json"


def lane_command(job: dict[str, Any], *, mode: str, force: bool, summary_path: Path) -> list[str]:
    command = [
        sys.executable,
        lane_runner(job),
        "--job-id",
        str(job["job_id"]),
        "--summary",
        str(summary_path),
    ]
    if force:
        command.append("--force")
    if mode == "dry-run-stub":
        command.extend(["--mode", "dry-run-stub"])
    else:
        command.extend(
            [
                "--mode",
                "external",
                "--external",
                sys.executable,
                lane_stub(job),
                "--job",
                "{job}",
                "--result",
                "{result}",
            ]
        )
    return command


def run_one(job: dict[str, Any], *, mode: str, force: bool, summary_root: Path) -> dict[str, Any]:
    batch_summary = lane_batch_summary(summary_root, job)
    batch_summary.parent.mkdir(parents=True, exist_ok=True)
    command = lane_command(job, mode=mode, force=force, summary_path=batch_summary)
    result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False)
    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)
    status = "completed" if result.returncode == 0 else "failed"
    result_path = repo_path(str(job["result_path"]))
    return {
        "execution_order": int(job["execution_order"]),
        "campaign_job_id": job["campaign_job_id"],
        "job_id": job["job_id"],
        "lane": job["lane"],
        "phase": job["phase"],
        "command": job["command"],
        "reader_pc": job["reader_pc"],
        "mode": mode,
        "status": status,
        "returncode": int(result.returncode),
        "result_path": str(result_path),
        "result_exists": result_path.exists(),
        "lane_batch_summary": str(batch_summary),
        "error": None if status == "completed" else (result.stderr.strip() or result.stdout.strip()),
    }


def write_summary(campaign: dict[str, Any], summary_path: Path, batch: dict[str, Any]) -> None:
    summary = {
        "schema": "earthbound-decomp.audio-probe-campaign-run.v1",
        "campaign_plan": "manifests/audio-probe-campaign-plan.json",
        "campaign_status": campaign.get("status"),
        "mode": batch["mode"],
        "selected_count": batch["selected_count"],
        "completed_count": batch["completed_count"],
        "failed_count": batch["failed_count"],
        "force": batch["force"],
        "selection": batch["selection"],
        "promotion_allowed_by_run": False,
        "runs": batch["runs"],
    }
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    campaign = load_json(Path(args.campaign))
    selected = select_jobs(campaign, args)
    summary_path = Path(args.summary)
    summary_root = summary_path.parent
    print(f"Selected {len(selected)} campaign jobs for {args.mode} mode")
    runs: list[dict[str, Any]] = []
    for job in selected:
        record = run_one(job, mode=args.mode, force=args.force, summary_root=summary_root)
        runs.append(record)
        print(f"- {record['execution_order']:03d} {record['job_id']}: {record['status']}")
        if record["error"]:
            print(f"  {record['error']}")
        if record["status"] == "failed" and args.stop_on_error:
            break
    batch = {
        "mode": args.mode,
        "selected_count": len(runs),
        "completed_count": sum(1 for run in runs if run["status"] == "completed"),
        "failed_count": sum(1 for run in runs if run["status"] == "failed"),
        "force": bool(args.force),
        "selection": {
            "phase": args.phase or [],
            "lane": args.lane or [],
            "job_id": args.job_id or [],
            "limit": args.limit,
        },
        "runs": runs,
    }
    write_summary(campaign, summary_path, batch)
    return 1 if batch["failed_count"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
