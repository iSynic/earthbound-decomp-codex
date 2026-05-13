#!/usr/bin/env python3
"""Run or dry-run C2 battle trace-oracle jobs."""

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

import c2_battle_trace_oracle_stub_harness
import validate_c2_battle_trace_oracle_result


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PACKET = ROOT / "manifests" / "c2-battle-trace-oracle-packet.json"
DEFAULT_SUMMARY = ROOT / "build" / "c2" / "battle-trace-oracles" / "batch-summary.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run or dry-run C2 battle trace-oracle jobs.")
    parser.add_argument("--packet", default=str(DEFAULT_PACKET), help="C2 battle trace-oracle packet JSON.")
    parser.add_argument(
        "--mode",
        default="dry-run-stub",
        choices=["dry-run-stub", "external"],
        help="Run schema-only dry runs or invoke an external harness.",
    )
    parser.add_argument("--job-id", action="append", help="Specific job id to run. May be repeated.")
    parser.add_argument("--oracle-id", action="append", help="Specific oracle id to run. May be repeated.")
    parser.add_argument("--first-pass-only", action="store_true", help="Select only first trace pass jobs.")
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


def result_path(job: dict[str, Any]) -> Path:
    return repo_path(str(job["output_paths"]["result_path"]))


def select_jobs(packet: dict[str, Any], args: argparse.Namespace) -> list[dict[str, Any]]:
    requested_jobs = set(args.job_id or [])
    requested_oracles = set(args.oracle_id or [])
    jobs: list[dict[str, Any]] = []
    for job in packet.get("jobs", []):
        if requested_jobs and job["job_id"] not in requested_jobs:
            continue
        if requested_oracles and job["oracle_id"] not in requested_oracles:
            continue
        if args.first_pass_only and not job.get("first_trace_pass"):
            continue
        if not args.force and result_path(job).exists():
            continue
        jobs.append(job)
    missing_jobs = requested_jobs - {str(job.get("job_id")) for job in packet.get("jobs", [])}
    missing_oracles = requested_oracles - {str(job.get("oracle_id")) for job in packet.get("jobs", [])}
    if missing_jobs:
        raise ValueError(f"requested job ids not found: {', '.join(sorted(missing_jobs))}")
    if missing_oracles:
        raise ValueError(f"requested oracle ids not found: {', '.join(sorted(missing_oracles))}")
    if args.limit is not None:
        jobs = jobs[: args.limit]
    return jobs


def ensure_job_manifest(job: dict[str, Any]) -> Path:
    path = repo_path(str(job["output_paths"]["job_path"]))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(job, indent=2) + "\n", encoding="utf-8")
    return path


def validate_result(result: Path, packet: dict[str, Any]) -> None:
    data = validate_c2_battle_trace_oracle_result.load_json(result)
    job = validate_c2_battle_trace_oracle_result.find_job(packet, str(data.get("job_id", "")))
    errors = validate_c2_battle_trace_oracle_result.validate(data, job)
    if job is None:
        errors.insert(0, f"job {data.get('job_id')} was not found in packet")
    if errors:
        formatted = "\n".join(f"- {error}" for error in errors)
        raise ValueError(f"C2 battle trace oracle result validation failed:\n{formatted}")


def write_dry_run_result(job: dict[str, Any]) -> Path:
    path = result_path(job)
    path.parent.mkdir(parents=True, exist_ok=True)
    result = c2_battle_trace_oracle_stub_harness.build_result(
        job,
        harness_version="c2-battle-trace-oracle-batch-dry-run",
        status="unsupported",
    )
    path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return path


def expand_external_command(command: list[str], job: dict[str, Any], job_path: Path) -> list[str]:
    paths = job["output_paths"]
    replacements = {
        "{job}": str(job_path),
        "{result}": str(repo_path(str(paths["result_path"]))),
        "{output_dir}": str(repo_path(str(paths["output_dir"]))),
        "{raw_trace}": str(repo_path(str(paths["raw_trace_path"]))),
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
        raise RuntimeError(f"external C2 oracle harness exited with status {result.returncode}: {expanded}")
    return result_path(job)


def run_one(job: dict[str, Any], mode: str, external: list[str] | None, packet: dict[str, Any]) -> dict[str, Any]:
    job_path = ensure_job_manifest(job)
    try:
        if mode == "dry-run-stub":
            path = write_dry_run_result(job)
        else:
            path = run_external(job, job_path, external)
        validate_result(path, packet)
        return {
            "job_id": job["job_id"],
            "oracle_id": job["oracle_id"],
            "status": "completed",
            "result_path": str(path),
            "error": None,
        }
    except Exception as exc:
        return {
            "job_id": job["job_id"],
            "oracle_id": job["oracle_id"],
            "status": "failed",
            "result_path": str(result_path(job)),
            "error": str(exc),
        }


def write_summary(summary_path: Path, packet: dict[str, Any], batch: dict[str, Any]) -> None:
    summary = {
        "schema": "earthbound-decomp.c2-battle-trace-oracle-batch-run.v1",
        "packet": "manifests/c2-battle-trace-oracle-packet.json",
        "mode": batch["mode"],
        "selected_count": batch["selected_count"],
        "completed_count": batch["completed_count"],
        "failed_count": batch["failed_count"],
        "promotion_allowed_by_batch": False,
        "behavior_change_allowed": False,
        "runs": batch["runs"],
    }
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    packet = load_json(Path(args.packet))
    selected = select_jobs(packet, args)
    runs: list[dict[str, Any]] = []
    print(f"Selected {len(selected)} C2 battle trace-oracle jobs for {args.mode} mode")
    for job in selected:
        record = run_one(job, args.mode, args.external, packet)
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
    write_summary(Path(args.summary), packet, batch)
    return 1 if batch["failed_count"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
