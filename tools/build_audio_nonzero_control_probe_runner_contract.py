#!/usr/bin/env python3
"""Build a runnable job contract for targeted non-0x00 control probes."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PLAN = ROOT / "manifests" / "audio-nonzero-control-probe-plan.json"
DEFAULT_OUTPUT = ROOT / "manifests" / "audio-nonzero-control-probe-runner-contract.json"
DEFAULT_NOTES = ROOT / "notes" / "audio-nonzero-control-probe-runner-contract.md"
DEFAULT_JOB_ROOT = ROOT / "build" / "audio" / "nonzero-control-probe-jobs"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build non-0x00 control probe runner contract and ignored jobs.")
    parser.add_argument("--plan", default=str(DEFAULT_PLAN), help="Non-0x00 control probe plan JSON.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Committed runner contract output JSON.")
    parser.add_argument("--notes", default=str(DEFAULT_NOTES), help="Committed runner contract markdown output.")
    parser.add_argument("--job-root", default=str(DEFAULT_JOB_ROOT), help="Ignored generated job root.")
    parser.add_argument(
        "--skip-job-files",
        action="store_true",
        help="Only write the committed contract/note, not ignored build/audio job files.",
    )
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def rel(path: Path | str) -> str:
    path = Path(path)
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except (OSError, ValueError):
        return path.as_posix()


def output_dir(job: dict[str, Any]) -> str:
    return str(job.get("probe_outputs", {}).get("root", ""))


def job_path(job_root: Path, job: dict[str, Any]) -> str:
    return rel(job_root / str(job["job_id"]) / "job.json")


def result_path(job: dict[str, Any]) -> str:
    return str(job.get("probe_outputs", {}).get("result_json", ""))


def source_candidate_tracks(job: dict[str, Any]) -> list[int]:
    return [int(candidate["track_id"]) for candidate in job.get("source_candidates", [])]


def build_job_record(plan: dict[str, Any], job: dict[str, Any], job_root: Path) -> dict[str, Any]:
    return {
        "schema": "earthbound-decomp.audio-nonzero-control-probe-job.v1",
        "job_id": job["job_id"],
        "command": job["command"],
        "reader_pc": job["reader_pc"],
        "driver_offset": job.get("driver_offset"),
        "read_count": int(job["read_count"]),
        "affected_kind": job["affected_kind"],
        "semantic_status": job["semantic_status"],
        "static_dispatch_target": job.get("static_dispatch_target"),
        "priority_rank": int(job["priority_rank"]),
        "priority_reason": job["priority_reason"],
        "promotion_question": job["promotion_question"],
        "source_candidates": job["source_candidates"],
        "source_candidate_track_ids": source_candidate_tracks(job),
        "required_capture_fields": job["required_capture_fields"],
        "accepted_control_effect_classifications": plan["runner_contract"][
            "accepted_control_effect_classifications"
        ],
        "promotion_allowed_by_job": False,
        "success_criteria": job["success_criteria"],
        "result_schema": "earthbound-decomp.audio-nonzero-control-probe-result.v1",
        "result_path": result_path(job),
        "raw_trace_path": str(job.get("probe_outputs", {}).get("raw_trace", "")),
        "evidence_markdown_path": str(job.get("probe_outputs", {}).get("evidence_markdown", "")),
        "output_dir": output_dir(job),
        "job_path": job_path(job_root, job),
        "status": "planned_waiting_for_nonzero_control_probe_harness",
    }


def build_contract(plan: dict[str, Any], job_root: Path) -> dict[str, Any]:
    jobs = [build_job_record(plan, job, job_root) for job in plan.get("jobs", [])]
    command_counts: Counter[str] = Counter(str(job["command"]) for job in jobs)
    reader_counts: Counter[str] = Counter(str(job["reader_pc"]) for job in jobs)
    affected_counts: Counter[str] = Counter(str(job["affected_kind"]) for job in jobs)
    return {
        "schema": "earthbound-decomp.audio-nonzero-control-probe-runner-contract.v1",
        "status": "nonzero_control_probe_runner_jobs_ready",
        "probe_plan": "manifests/audio-nonzero-control-probe-plan.json",
        "source_policy": plan.get("source_policy", {}),
        "runner": {
            "job_root": rel(job_root),
            "job_index_path": rel(job_root / "nonzero-control-probe-jobs.json"),
            "job_note_path": rel(job_root / "nonzero-control-probe-jobs.md"),
            "external_command_template": [
                "<nonzero-control-probe-harness>",
                "--job",
                "{job}",
                "--result",
                "{result}",
            ],
            "per_job_schema": "earthbound-decomp.audio-nonzero-control-probe-job.v1",
            "result_schema": "earthbound-decomp.audio-nonzero-control-probe-result.v1",
            "result_validator": "python tools/validate_audio_nonzero_control_probe_result.py {result}",
            "result_collector": "python tools/collect_audio_nonzero_control_probe_results.py",
            "behavior_change_allowed": False,
            "public_exact_promotion_allowed": False,
        },
        "summary": {
            "job_count": len(jobs),
            "source_candidate_count": sum(len(job.get("source_candidates", [])) for job in jobs),
            "unique_source_track_count": len(
                {track_id for job in jobs for track_id in job.get("source_candidate_track_ids", [])}
            ),
            "command_job_counts": dict(sorted(command_counts.items())),
            "reader_pc_job_counts": dict(sorted(reader_counts.items())),
            "affected_kind_job_counts": dict(sorted(affected_counts.items())),
            "required_capture_field_count": len(plan.get("runner_contract", {}).get("required_capture_fields", [])),
            "sequence_promotion_allowed": False,
            "semantic_status": "ignored_job_queue_ready_nonzero_control_probe_outputs_pending",
        },
        "jobs": jobs,
        "runner_policy": [
            "Generated job files stay under ignored build/audio paths and may reference local ROM-derived SPC/WAV evidence.",
            "Each job targets one command and reader PC, then offers multiple source candidates for harness reachability.",
            "The harness must write one result JSON per job using earthbound-decomp.audio-nonzero-control-probe-result.v1.",
            "The runner contract cannot directly promote public exact-duration exports.",
            "Validated command effects must still be fed through audio-sequence-command-semantics before changing exact-duration policy.",
        ],
    }


def render_job_index(contract: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": "earthbound-decomp.audio-nonzero-control-probe-job-index.v1",
        "contract": "manifests/audio-nonzero-control-probe-runner-contract.json",
        "job_count": contract["summary"]["job_count"],
        "source_policy": contract["source_policy"],
        "runner": contract["runner"],
        "jobs": contract["jobs"],
    }


def render_markdown(contract: dict[str, Any]) -> str:
    summary = contract["summary"]
    job_rows = [
        "| `{job_id}` | `{command}` | `{reader_pc}` | {read_count} | `{affected_kind}` | {source_count} | `{job_path}` |".format(
            job_id=job["job_id"],
            command=job["command"],
            reader_pc=job["reader_pc"],
            read_count=job["read_count"],
            affected_kind=job["affected_kind"],
            source_count=len(job.get("source_candidates", [])),
            job_path=job["job_path"],
        )
        for job in contract["jobs"]
    ]
    return "\n".join(
        [
            "# Audio Nonzero Control Probe Runner Contract",
            "",
            "Status: ignored command/reader-PC job files can be generated for the future non-0x00 control probe harness.",
            "",
            "## Summary",
            "",
            f"- jobs: `{summary['job_count']}`",
            f"- source candidates: `{summary['source_candidate_count']}`",
            f"- unique source tracks: `{summary['unique_source_track_count']}`",
            f"- command jobs: `{summary['command_job_counts']}`",
            f"- reader PC jobs: `{summary['reader_pc_job_counts']}`",
            f"- affected kind jobs: `{summary['affected_kind_job_counts']}`",
            f"- required capture fields: `{summary['required_capture_field_count']}`",
            f"- sequence promotion allowed: `{summary['sequence_promotion_allowed']}`",
            "",
            "## Runner",
            "",
            f"- job root: `{contract['runner']['job_root']}`",
            f"- job index: `{contract['runner']['job_index_path']}`",
            f"- command template: `{contract['runner']['external_command_template']}`",
            f"- result validator: `{contract['runner']['result_validator']}`",
            f"- result collector: `{contract['runner']['result_collector']}`",
            "",
            "## Jobs",
            "",
            "| Job | Command | Reader PC | Reads | Affected kind | Source candidates | Job path |",
            "| --- | --- | --- | ---: | --- | ---: | --- |",
            *job_rows,
            "",
            "## Runner Policy",
            "",
            *[f"- {item}" for item in contract["runner_policy"]],
            "",
        ]
    )


def render_job_markdown(index: dict[str, Any]) -> str:
    rows = [
        "| `{job_id}` | `{command}` | `{reader_pc}` | `{status}` | `{result_path}` |".format(**job)
        for job in index["jobs"]
    ]
    return "\n".join(
        [
            "# Audio Nonzero Control Probe Jobs",
            "",
            "Status: ignored/generated job queue for local non-0x00 command probe harness work.",
            "",
            "| Job | Command | Reader PC | Status | Result path |",
            "| --- | --- | --- | --- | --- |",
            *rows,
            "",
        ]
    )


def write_job_files(contract: dict[str, Any], job_root: Path) -> None:
    index = render_job_index(contract)
    for job in contract["jobs"]:
        path = ROOT / job["job_path"]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(job, indent=2) + "\n", encoding="utf-8")
    job_root.mkdir(parents=True, exist_ok=True)
    (job_root / "nonzero-control-probe-jobs.json").write_text(json.dumps(index, indent=2) + "\n", encoding="utf-8")
    (job_root / "nonzero-control-probe-jobs.md").write_text(render_job_markdown(index), encoding="utf-8")


def main() -> int:
    args = parse_args()
    job_root = Path(args.job_root)
    contract = build_contract(load_json(Path(args.plan)), job_root)
    output = Path(args.output)
    notes = Path(args.notes)
    output.parent.mkdir(parents=True, exist_ok=True)
    notes.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(contract, indent=2) + "\n", encoding="utf-8")
    notes.write_text(render_markdown(contract), encoding="utf-8")
    if not args.skip_job_files:
        write_job_files(contract, job_root)
    print(
        "Built audio non-0x00 control probe runner contract: "
        f"{contract['summary']['job_count']} jobs -> {output}"
    )
    if not args.skip_job_files:
        print(f"Wrote ignored job queue -> {job_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
