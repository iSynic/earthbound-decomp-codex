#!/usr/bin/env python3
"""Validate the 0x00 runtime audio coverage report."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_REPORT = ROOT / "manifests" / "audio-zero-runtime-coverage-report.json"
REQUIRED_REFERENCES = {
    "manifests/audio-duration-uncertainty-register.json",
    "manifests/audio-zero-runtime-probe-plan.json",
}
REQUIRED_EXPORT_COUNTS = {
    "finite_or_transition_review_candidate": 10,
    "loop_or_held_candidate": 2,
    "unknown_active_preview": 7,
}
REQUIRED_TRACE_COUNTS = {
    "prove_zero_effect_but_loop_points_remain_required": 2,
    "prove_zero_effect_then_classify_active_preview": 5,
    "prove_zero_end_effect_then_review_finite_candidate": 1,
    "trace_zero_reader_with_ef_stack_state": 11,
}
REQUIRED_CONTEXT_COUNTS = {"needs_ef_return_stack_model": 11, "zero_phrase_end_candidate_runtime_pending": 8}
REQUIRED_ACTION_COUNTS = {
    "classify_active_preview_before_exact_export": 7,
    "decode_loop_points_before_exact_export": 2,
    "review_observed_silence_as_finite_or_transition": 10,
}
REQUIRED_BLOCKER_COUNTS = {"ef_return_stack_model": 15, "zero_runtime_effect_proof": 19}
REQUIRED_READER_PCS = {"0x2DB0", "0x2DDA", "0x2DF8", "0x2E3D", "0x0957", "0x0B8A", "0x0847", "0x0782", "0x07A6", "0x0D12"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate zero runtime coverage report.")
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


def list_count_jobs(jobs: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for job in jobs:
        for item in job.get(key, []):
            counts[str(item)] += 1
    return dict(sorted(counts.items()))


def validate(data: dict[str, Any]) -> None:
    require(data.get("schema") == "earthbound-decomp.audio-zero-runtime-coverage-report.v1", "unexpected schema")
    require(data.get("status") == "zero_runtime_coverage_ready_probe_outputs_pending", "unexpected status")
    require(data.get("source_plan_status") == "zero_runtime_probe_jobs_ready_runner_extension_pending", "unexpected source plan status")
    require(REQUIRED_REFERENCES <= set(data.get("references", [])), "missing references")
    summary = data.get("summary", {})
    jobs = data.get("jobs", [])
    readers = data.get("reader_pc_targets", [])
    require(int(summary.get("blocker_track_count", 0)) == 19, "expected 19 zero-runtime blocker tracks")
    require(int(summary.get("probe_job_count", -1)) == 19, "expected 19 zero-runtime probe jobs")
    require(len(jobs) == 19, "job list count mismatch")
    require(summary.get("job_track_coverage_exact") is True, "jobs should exactly cover zero blockers")
    require(int(summary.get("candidate_pack_count", 0)) == 10, "expected 10 candidate packs")
    require(int(summary.get("runtime_zero_read_count", 0)) == 5931, "expected 5931 runtime zero reads")
    require(int(summary.get("reader_pc_target_count", 0)) == 10, "expected 10 reader PC targets")
    require(summary.get("export_class_counts") == REQUIRED_EXPORT_COUNTS, "export class counts mismatch")
    require(summary.get("trace_focus_job_counts") == REQUIRED_TRACE_COUNTS, "trace focus counts mismatch")
    require(summary.get("pack_context_job_counts") == REQUIRED_CONTEXT_COUNTS, "pack context counts mismatch")
    require(summary.get("post_zero_proof_action_job_counts") == REQUIRED_ACTION_COUNTS, "post-proof action counts mismatch")
    require(summary.get("pre_promotion_blocker_counts") == REQUIRED_BLOCKER_COUNTS, "pre-promotion blocker counts mismatch")
    require(summary.get("export_class_counts") == count_jobs(jobs, "export_class"), "export counts do not match jobs")
    require(summary.get("trace_focus_job_counts") == count_jobs(jobs, "trace_focus"), "trace counts do not match jobs")
    require(summary.get("pack_context_job_counts") == count_jobs(jobs, "pack_context_class"), "context counts do not match jobs")
    require(summary.get("post_zero_proof_action_job_counts") == count_jobs(jobs, "post_zero_proof_action"), "action counts do not match jobs")
    require(summary.get("pre_promotion_blocker_counts") == list_count_jobs(jobs, "pre_promotion_blockers"), "blocker counts do not match jobs")
    require(summary.get("sequence_promotion_allowed") is False, "sequence promotion should be blocked")
    require(summary.get("public_exact_promotion_allowed") is False, "public exact promotion should be blocked")

    require(len(readers) == 10, "reader target count mismatch")
    require({str(target.get("pc")) for target in readers} == REQUIRED_READER_PCS, "reader PC set mismatch")
    require(sum(int(target.get("read_count", 0)) for target in readers) == 4107, "reader target sampled read-count total mismatch")

    seen_tracks: set[int] = set()
    for job in jobs:
        job_id = str(job.get("job_id", ""))
        track_id = int(job.get("track_id", -1))
        require(job_id.startswith("zero-probe-track-"), f"{job_id}: unexpected job id")
        require(track_id > 0, f"{job_id}: invalid track id")
        require(track_id not in seen_tracks, f"{job_id}: duplicate track id")
        seen_tracks.add(track_id)
        require(int(job.get("pack_id", 0)) > 0, f"{job_id}: invalid pack id")
        require(job.get("trace_focus") in REQUIRED_TRACE_COUNTS, f"{job_id}: unexpected trace focus")
        require(job.get("export_class") in REQUIRED_EXPORT_COUNTS, f"{job_id}: unexpected export class")
        require(job.get("post_zero_proof_action") in REQUIRED_ACTION_COUNTS, f"{job_id}: unexpected post-proof action")
        require("zero_runtime_effect_proof" in job.get("pre_promotion_blockers", []), f"{job_id}: missing zero proof blocker")
        require(int(job.get("reader_pc_target_count", 0)) == 10, f"{job_id}: expected 10 reader targets")
        require(set(job.get("reader_pc_targets", [])) == REQUIRED_READER_PCS, f"{job_id}: reader targets mismatch")
        require(job.get("source_oracle_job_id", "").startswith("oracle-track-"), f"{job_id}: missing source oracle job")
        require(job.get("source_spc_sha1"), f"{job_id}: missing source SPC SHA-1")
        require(job.get("promotion_allowed_by_plan") is False, f"{job_id}: promotion should be blocked")
        require(job.get("probe_outputs", {}).get("result_json"), f"{job_id}: missing result_json output contract")
    require(data.get("coverage_policy"), "missing coverage policy")


def main() -> int:
    args = parse_args()
    data = json.loads(Path(args.report).read_text(encoding="utf-8"))
    validate(data)
    print(
        "Audio zero runtime coverage report validation OK: "
        f"{data['summary']['probe_job_count']} jobs, "
        f"{data['summary']['blocker_track_count']} blockers"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
