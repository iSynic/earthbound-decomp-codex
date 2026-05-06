#!/usr/bin/env python3
"""Build a coverage report for 0x00 runtime audio probe blockers."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_UNCERTAINTY = ROOT / "manifests" / "audio-duration-uncertainty-register.json"
DEFAULT_PROBE_PLAN = ROOT / "manifests" / "audio-zero-runtime-probe-plan.json"
DEFAULT_OUTPUT = ROOT / "manifests" / "audio-zero-runtime-coverage-report.json"
DEFAULT_NOTES = ROOT / "notes" / "audio-zero-runtime-coverage-report.md"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build 0x00 runtime coverage report.")
    parser.add_argument("--uncertainty", default=str(DEFAULT_UNCERTAINTY), help="Duration uncertainty register JSON.")
    parser.add_argument("--probe-plan", default=str(DEFAULT_PROBE_PLAN), help="0x00 runtime probe plan JSON.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Coverage report JSON output.")
    parser.add_argument("--notes", default=str(DEFAULT_NOTES), help="Coverage report markdown output.")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def zero_blockers(uncertainty: dict[str, Any]) -> list[dict[str, Any]]:
    records = [
        record
        for record in uncertainty.get("tracks", [])
        if record.get("primary_uncertainty") == "zero_runtime_probe_pending"
    ]
    records.sort(key=lambda record: int(record["track_id"]))
    return records


def job_record(job: dict[str, Any]) -> dict[str, Any]:
    return {
        "job_id": job["job_id"],
        "track_id": int(job["track_id"]),
        "track_name": job["track_name"],
        "pack_id": int(job["pack_id"]),
        "pack_track_ids": job.get("pack_track_ids", []),
        "pack_context_class": job.get("pack_context_class"),
        "trace_focus": job.get("trace_focus"),
        "export_class": job.get("export_class"),
        "recommended_mode": job.get("recommended_mode"),
        "duration_seconds": job.get("duration_seconds"),
        "pre_promotion_blockers": job.get("pre_promotion_blockers", []),
        "post_zero_proof_action": job.get("post_zero_proof_action"),
        "reader_pc_target_count": len(job.get("reader_pc_targets", [])),
        "reader_pc_targets": job.get("reader_pc_targets", []),
        "zero_static_context": job.get("zero_static_context", {}),
        "source_oracle_job_id": job.get("source", {}).get("oracle_job_id"),
        "source_spc_sha1": job.get("source", {}).get("source_spc", {}).get("sha1"),
        "promotion_allowed_by_plan": bool(job.get("promotion_allowed_by_plan")),
        "probe_outputs": job.get("probe_outputs", {}),
    }


def build_report(uncertainty: dict[str, Any], probe_plan: dict[str, Any]) -> dict[str, Any]:
    blockers = zero_blockers(uncertainty)
    blocker_track_ids = {int(record["track_id"]) for record in blockers}
    jobs = [job_record(job) for job in probe_plan.get("jobs", [])]
    jobs.sort(key=lambda item: int(item["track_id"]))
    job_track_ids = {int(job["track_id"]) for job in jobs}
    export_counts: Counter[str] = Counter(str(job["export_class"]) for job in jobs)
    pack_counts: Counter[str] = Counter(str(job["pack_id"]) for job in jobs)
    focus_counts: Counter[str] = Counter(str(job["trace_focus"]) for job in jobs)
    context_counts: Counter[str] = Counter(str(job["pack_context_class"]) for job in jobs)
    action_counts: Counter[str] = Counter(str(job["post_zero_proof_action"]) for job in jobs)
    blocker_counts: Counter[str] = Counter()
    for job in jobs:
        for blocker in job["pre_promotion_blockers"]:
            blocker_counts[str(blocker)] += 1
    reader_targets = probe_plan.get("reader_pc_targets", [])
    reader_target_counts = {str(target["pc"]): int(target["read_count"]) for target in reader_targets}
    return {
        "schema": "earthbound-decomp.audio-zero-runtime-coverage-report.v1",
        "status": "zero_runtime_coverage_ready_probe_outputs_pending",
        "references": [
            "manifests/audio-duration-uncertainty-register.json",
            "manifests/audio-zero-runtime-probe-plan.json",
        ],
        "source_plan_status": probe_plan.get("status"),
        "summary": {
            "blocker_track_count": len(blockers),
            "probe_job_count": len(jobs),
            "job_track_coverage_exact": job_track_ids == blocker_track_ids,
            "candidate_pack_count": int(probe_plan.get("summary", {}).get("candidate_pack_count", 0)),
            "runtime_zero_read_count": int(probe_plan.get("summary", {}).get("runtime_zero_read_count", 0)),
            "reader_pc_target_count": len(reader_targets),
            "reader_pc_target_read_counts": dict(sorted(reader_target_counts.items())),
            "export_class_counts": dict(sorted(export_counts.items())),
            "trace_focus_job_counts": dict(sorted(focus_counts.items())),
            "pack_context_job_counts": dict(sorted(context_counts.items())),
            "post_zero_proof_action_job_counts": dict(sorted(action_counts.items())),
            "pre_promotion_blocker_counts": dict(sorted(blocker_counts.items())),
            "pack_job_counts": dict(sorted(pack_counts.items())),
            "sequence_promotion_allowed": False,
            "public_exact_promotion_allowed": False,
        },
        "coverage_policy": [
            "This report maps every current 0x00 runtime blocker to a probe job; it does not run the harness.",
            "Every job targets the same 10 reader PCs so EF-return and true-end semantics can be observed consistently.",
            "Promotion stays blocked until imported probe outputs classify 0x00 effects and refresh the duration uncertainty register.",
            "Post-proof actions remain lane-specific: active preview classification, finite/transition review, or exact loop metadata work.",
        ],
        "reader_pc_targets": reader_targets,
        "jobs": jobs,
    }


def render_markdown(data: dict[str, Any]) -> str:
    summary = data["summary"]
    job_rows = [
        "| {track_id:03d} | `{track_name}` | `{export_class}` | `{focus}` | `{action}` | {reader_count} | `{promote}` |".format(
            track_id=job["track_id"],
            track_name=job["track_name"],
            export_class=job["export_class"],
            focus=job["trace_focus"],
            action=job["post_zero_proof_action"],
            reader_count=job["reader_pc_target_count"],
            promote=job["promotion_allowed_by_plan"],
        )
        for job in data["jobs"]
    ]
    reader_rows = [
        "| `{pc}` | {read_count} | `{offset}` | {role} |".format(
            pc=target["pc"],
            read_count=target["read_count"],
            offset=target["driver_offset"],
            role=target["role"],
        )
        for target in data["reader_pc_targets"]
    ]
    return "\n".join(
        [
            "# Audio Zero Runtime Coverage Report",
            "",
            "Status: 0x00 runtime coverage is mapped; probe outputs are still pending and current export behavior is preserved.",
            "",
            "## Summary",
            "",
            f"- blocker tracks: `{summary['blocker_track_count']}`",
            f"- probe jobs: `{summary['probe_job_count']}`",
            f"- job track coverage exact: `{summary['job_track_coverage_exact']}`",
            f"- candidate packs: `{summary['candidate_pack_count']}`",
            f"- runtime zero reads: `{summary['runtime_zero_read_count']}`",
            f"- reader PC targets: `{summary['reader_pc_target_count']}`",
            f"- export classes: `{summary['export_class_counts']}`",
            f"- trace focus jobs: `{summary['trace_focus_job_counts']}`",
            f"- pack contexts: `{summary['pack_context_job_counts']}`",
            f"- post-proof actions: `{summary['post_zero_proof_action_job_counts']}`",
            f"- pre-promotion blockers: `{summary['pre_promotion_blocker_counts']}`",
            f"- sequence promotion allowed: `{summary['sequence_promotion_allowed']}`",
            "",
            "## Reader PC Targets",
            "",
            "| Reader PC | Read count | Driver offset | Role |",
            "| --- | ---: | --- | --- |",
            *reader_rows,
            "",
            "## Probe Jobs",
            "",
            "| Track | Name | Export class | Trace focus | Post-proof action | Reader PCs | Promotion allowed |",
            "| ---: | --- | --- | --- | --- | ---: | --- |",
            *job_rows,
            "",
            "## Coverage Policy",
            "",
            *[f"- {item}" for item in data["coverage_policy"]],
            "",
            "## Remaining Uncertainty",
            "",
            "- All 19 zero-runtime blockers have probe jobs, but no imported runtime classifications yet.",
            "- 15 jobs still need EF-return stack modeling evidence before exact duration can be considered.",
            "- The 10 finite/transition post-proof jobs still need finite-ending review after 0x00 effect proof.",
            "",
        ]
    )


def main() -> int:
    args = parse_args()
    data = build_report(load_json(Path(args.uncertainty)), load_json(Path(args.probe_plan)))
    output = Path(args.output)
    notes = Path(args.notes)
    output.parent.mkdir(parents=True, exist_ok=True)
    notes.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    notes.write_text(render_markdown(data), encoding="utf-8")
    print(
        "Built zero runtime coverage report: "
        f"{data['summary']['probe_job_count']} jobs, "
        f"{data['summary']['blocker_track_count']} blockers"
    )
    print(f"Wrote {output}")
    print(f"Wrote {notes}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
