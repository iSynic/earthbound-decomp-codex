#!/usr/bin/env python3
"""Validate the nonzero audio control-semantics coverage report."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_REPORT = ROOT / "manifests" / "audio-nonzero-control-coverage-report.json"
REQUIRED_REFERENCES = {
    "manifests/audio-duration-uncertainty-register.json",
    "manifests/audio-nonzero-control-probe-plan.json",
}
REQUIRED_COMMAND_COUNTS = {"0xEF": 3, "0xFD": 1, "0xFE": 2, "0xFF": 1}
REQUIRED_READER_COUNTS = {"0x0847": 2, "0x0957": 3, "0x0B8A": 1, "0x0D12": 1}
REQUIRED_AFFECTED_COUNTS = {"return_stack_context": 3, "static_walk_blocker": 1, "timing_toggle_context": 3}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate nonzero control coverage report.")
    parser.add_argument("report", nargs="?", default=str(DEFAULT_REPORT))
    return parser.parse_args()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def count_jobs(jobs: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for job in jobs:
        counts[str(job.get(key))] += 1
    return dict(sorted(counts.items()))


def validate(data: dict[str, Any]) -> None:
    require(data.get("schema") == "earthbound-decomp.audio-nonzero-control-coverage-report.v1", "unexpected schema")
    require(data.get("status") == "nonzero_control_coverage_ready_probe_outputs_pending", "unexpected status")
    require(data.get("source_plan_status") == "nonzero_control_probe_jobs_ready_runner_extension_pending", "unexpected source plan status")
    require(REQUIRED_REFERENCES <= set(data.get("references", [])), "missing references")
    summary = data.get("summary", {})
    jobs = data.get("jobs", [])
    reuse = data.get("source_candidate_reuse", [])
    require(int(summary.get("blocker_track_count", 0)) == 155, "expected 155 nonzero-control blocker tracks")
    require(int(summary.get("probe_job_count", -1)) == 7, "expected 7 probe jobs")
    require(len(jobs) == 7, "job list count mismatch")
    require(summary.get("command_job_counts") == REQUIRED_COMMAND_COUNTS, "command counts mismatch")
    require(summary.get("reader_pc_job_counts") == REQUIRED_READER_COUNTS, "reader PC counts mismatch")
    require(summary.get("affected_kind_job_counts") == REQUIRED_AFFECTED_COUNTS, "affected kind counts mismatch")
    require(summary.get("command_job_counts") == count_jobs(jobs, "command"), "command counts do not match jobs")
    require(summary.get("reader_pc_job_counts") == count_jobs(jobs, "reader_pc"), "reader counts do not match jobs")
    require(summary.get("affected_kind_job_counts") == count_jobs(jobs, "affected_kind"), "affected counts do not match jobs")
    require(int(summary.get("source_candidate_record_count", 0)) == 56, "expected 56 source candidate records")
    require(int(summary.get("unique_source_candidate_track_count", 0)) == 10, "expected 10 unique source candidate tracks")
    require(int(summary.get("blocker_source_candidate_track_count", 0)) == 9, "expected 9 blocker source candidate tracks")
    require(int(summary.get("source_candidate_tracks_outside_primary_blocker_count", 0)) == 1, "expected 1 source candidate outside primary blocker set")
    require(int(summary.get("blocker_tracks_without_source_candidate_count", 0)) == 146, "expected 146 blocker tracks without source candidate")
    require(int(summary.get("frontier_pack_count", 0)) == 108, "expected 108 frontier packs")
    require(summary.get("sequence_promotion_allowed") is False, "sequence promotion should be blocked")
    require(summary.get("public_exact_promotion_allowed") is False, "public exact promotion should be blocked")

    seen_jobs: set[str] = set()
    for job in jobs:
        job_id = str(job.get("job_id", ""))
        require(job_id.startswith("nonzero-probe-"), f"{job_id}: unexpected job id")
        require(job_id not in seen_jobs, f"{job_id}: duplicate job")
        seen_jobs.add(job_id)
        require(job.get("command") in REQUIRED_COMMAND_COUNTS, f"{job_id}: unexpected command")
        require(job.get("reader_pc") in REQUIRED_READER_COUNTS, f"{job_id}: unexpected reader PC")
        require(job.get("affected_kind") in REQUIRED_AFFECTED_COUNTS, f"{job_id}: unexpected affected kind")
        require(int(job.get("source_candidate_count", 0)) == 8, f"{job_id}: expected 8 source candidates")
        require(int(job.get("unique_source_candidate_track_count", 0)) == 8, f"{job_id}: expected 8 unique source candidate tracks")
        require(int(job.get("blocker_source_candidate_track_count", 0)) >= 7, f"{job_id}: expected mostly blocker candidates")
        require(job.get("promotion_allowed_by_plan") is False, f"{job_id}: promotion should be blocked")
        require(job.get("probe_outputs", {}).get("result_json"), f"{job_id}: missing result_json output contract")
        require("unresolved" in job.get("accepted_control_effect_classifications", []), f"{job_id}: missing unresolved classification")

    require(len(reuse) == 10, "source candidate reuse count mismatch")
    blocker_reuse_count = sum(1 for record in reuse if record.get("is_primary_nonzero_blocker") is True)
    require(blocker_reuse_count == 9, "expected 9 blocker reuse records")
    track_ids = {int(record.get("track_id", -1)) for record in reuse}
    require(track_ids == {1, 17, 83, 84, 109, 110, 133, 137, 138, 139}, "unexpected source candidate track set")
    require(data.get("coverage_policy"), "missing coverage policy")


def main() -> int:
    args = parse_args()
    data = json.loads(Path(args.report).read_text(encoding="utf-8"))
    validate(data)
    print(
        "Audio nonzero control coverage report validation OK: "
        f"{data['summary']['probe_job_count']} jobs, "
        f"{data['summary']['blocker_track_count']} blockers"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
