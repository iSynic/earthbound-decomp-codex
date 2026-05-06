#!/usr/bin/env python3
"""Run or dry-run targeted non-0x00 control probe jobs."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import audio_nonzero_control_probe_stub_harness
import validate_audio_nonzero_control_probe_result


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_JOBS = ROOT / "build" / "audio" / "nonzero-control-probe-jobs" / "nonzero-control-probe-jobs.json"
DEFAULT_PLAN = ROOT / "manifests" / "audio-nonzero-control-probe-plan.json"
DEFAULT_SUMMARY = (
    ROOT / "build" / "audio" / "nonzero-control-probe-jobs" / "nonzero-control-probe-batch-summary.json"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run or dry-run audio non-0x00 control probe jobs.")
    parser.add_argument("--jobs", default=str(DEFAULT_JOBS), help="Generated nonzero-control probe job index path.")
    parser.add_argument("--plan", default=str(DEFAULT_PLAN), help="Committed nonzero-control probe plan for validation.")
    parser.add_argument(
        "--mode",
        default="dry-run-stub",
        choices=["dry-run-stub", "external"],
        help="Run schema-only dry runs or invoke an external nonzero-control probe harness.",
    )
    parser.add_argument("--job-id", action="append", help="Specific job id to run. May be repeated.")
    parser.add_argument("--limit", type=int, help="Maximum number of selected jobs to run.")
    parser.add_argument("--force", action="store_true", help="Re-run jobs that already have result JSON.")
    parser.add_argument("--stop-on-error", action="store_true", help="Stop at the first failed job.")
    parser.add_argument("--summary", default=str(DEFAULT_SUMMARY), help="Ignored batch summary JSON output path.")
    parser.add_argument(
        "--external",
        nargs=argparse.REMAINDER,
        help="External command vector. Use placeholders like {job}, {result}, {output_dir}, and {raw_trace}.",
    )
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def repo_path(path_text: str) -> Path:
    path = Path(path_text)
    return path if path.is_absolute() else ROOT / path


def select_jobs(index: dict[str, Any], requested_ids: list[str] | None, *, force: bool) -> list[dict[str, Any]]:
    requested = set(requested_ids or [])
    jobs: list[dict[str, Any]] = []
    for job in index.get("jobs", []):
        if requested and job["job_id"] not in requested:
            continue
        if not force and repo_path(str(job["result_path"])).exists():
            continue
        jobs.append(job)
    missing = requested - {str(job["job_id"]) for job in index.get("jobs", [])}
    if missing:
        raise ValueError(f"requested job ids not found: {', '.join(sorted(missing))}")
    return jobs


def ensure_job_manifest(job: dict[str, Any]) -> Path:
    path = repo_path(str(job["job_path"]))
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(job, indent=2) + "\n", encoding="utf-8")
    return path


def plan_job_by_id(plan: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(job.get("job_id")): job for job in plan.get("jobs", [])}


def validate_result(result_path: Path, plan_jobs: dict[str, dict[str, Any]]) -> None:
    result = validate_audio_nonzero_control_probe_result.load_json(result_path)
    job = plan_jobs.get(str(result.get("job_id", "")))
    errors = validate_audio_nonzero_control_probe_result.validate(result, job)
    if job is None:
        errors.insert(0, f"job {result.get('job_id')} was not found in probe plan")
    if errors:
        formatted = "\n".join(f"- {error}" for error in errors)
        raise ValueError(f"nonzero-control probe result validation failed:\n{formatted}")


def write_dry_run_result(job: dict[str, Any]) -> Path:
    result_path = repo_path(str(job["result_path"]))
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result = audio_nonzero_control_probe_stub_harness.build_result(
        job,
        harness_version="nonzero-control-probe-batch-dry-run",
        status="unsupported",
    )
    result_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result_path


def expand_external_command(command: list[str], job: dict[str, Any], job_path: Path) -> list[str]:
    replacements = {
        "{job}": str(job_path),
        "{result}": str(repo_path(str(job["result_path"]))),
        "{output_dir}": str(repo_path(str(job["output_dir"]))),
        "{raw_trace}": str(repo_path(str(job["raw_trace_path"]))),
    }
    expanded: list[str] = []
    for token in command:
        for key, value in replacements.items():
            token = token.replace(key, value)
        expanded.append(token)
    return expanded


def run_external(job: dict[str, Any], job_path: Path, command: list[str] | None) -> Path:
    if not command:
        raise ValueError("external mode requires --external command arguments")
    expanded = expand_external_command(command, job, job_path)
    result = subprocess.run(expanded, cwd=ROOT, text=True, capture_output=True, check=False)
    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)
    if result.returncode:
        raise RuntimeError(f"external nonzero-control probe harness exited with status {result.returncode}: {expanded}")
    return repo_path(str(job["result_path"]))


def run_one(job: dict[str, Any], mode: str, external: list[str] | None, plan_jobs: dict[str, dict[str, Any]]) -> dict[str, Any]:
    job_path = ensure_job_manifest(job)
    try:
        if mode == "dry-run-stub":
            result_path = write_dry_run_result(job)
        else:
            result_path = run_external(job, job_path, external)
        validate_result(result_path, plan_jobs)
        return {"job_id": job["job_id"], "status": "completed", "result_path": str(result_path), "error": None}
    except Exception as exc:
        return {"job_id": job["job_id"], "status": "failed", "result_path": job.get("result_path"), "error": str(exc)}


def write_summary(index: dict[str, Any], summary_path: Path, batch: dict[str, Any]) -> None:
    summary = {
        "schema": "earthbound-decomp.audio-nonzero-control-probe-batch-run.v1",
        "job_index": str(
            summary_path.parent / Path(str(index.get("runner", {}).get("job_index_path", "nonzero-control-probe-jobs.json"))).name
        ),
        "mode": batch["mode"],
        "selected_count": batch["selected_count"],
        "completed_count": batch["completed_count"],
        "failed_count": batch["failed_count"],
        "runs": batch["runs"],
    }
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    jobs_path = Path(args.jobs)
    index = load_json(jobs_path)
    plan = load_json(Path(args.plan))
    selected = select_jobs(index, args.job_id, force=args.force)
    if args.limit is not None:
        selected = selected[: args.limit]

    plan_jobs = plan_job_by_id(plan)
    runs: list[dict[str, Any]] = []
    print(f"Selected {len(selected)} nonzero-control probe jobs for {args.mode} mode")
    for job in selected:
        record = run_one(job, args.mode, args.external, plan_jobs)
        runs.append(record)
        print(f"- {record['job_id']}: {record['status']}")
        if record["error"]:
            print(f"  {record['error']}")
        if record["status"] == "failed" and args.stop_on_error:
            break

    batch = {
        "mode": args.mode,
        "selected_count": len(selected),
        "completed_count": sum(1 for run in runs if run["status"] == "completed"),
        "failed_count": sum(1 for run in runs if run["status"] == "failed"),
        "runs": runs,
    }
    write_summary(index, Path(args.summary), batch)
    return 1 if batch["failed_count"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
