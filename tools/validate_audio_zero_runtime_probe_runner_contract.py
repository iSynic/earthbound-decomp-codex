#!/usr/bin/env python3
"""Validate the 0x00 runtime probe runner contract and optional generated jobs."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONTRACT = ROOT / "manifests" / "audio-zero-runtime-probe-runner-contract.json"

REQUIRED_JOB_FIELDS = {
    "schema",
    "job_id",
    "track_id",
    "track_name",
    "pack_id",
    "trace_focus",
    "source",
    "zero_static_context",
    "reader_pc_targets",
    "required_capture_fields",
    "accepted_zero_effect_classifications",
    "promotion_allowed_by_job",
    "result_schema",
    "result_path",
    "job_path",
    "status",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate audio 0x00 runtime probe runner contract.")
    parser.add_argument("contract", nargs="?", default=str(DEFAULT_CONTRACT))
    parser.add_argument(
        "--require-generated-jobs",
        action="store_true",
        help="Also require ignored build/audio job index and per-job files to exist.",
    )
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def repo_path(path_text: str) -> Path:
    path = Path(path_text)
    return path if path.is_absolute() else ROOT / path


def count_jobs(jobs: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for job in jobs:
        counts[str(job.get(key))] += 1
    return dict(sorted(counts.items()))


def validate_job(job: dict[str, Any], *, job_root: str) -> None:
    job_id = str(job.get("job_id", ""))
    missing = REQUIRED_JOB_FIELDS - set(job)
    require(not missing, f"{job_id}: missing job fields {sorted(missing)}")
    require(job.get("schema") == "earthbound-decomp.audio-zero-runtime-probe-job.v1", f"{job_id}: unexpected job schema")
    require(job_id.startswith("zero-probe-track-"), f"unexpected job id {job_id}")
    require(int(job.get("track_id", 0)) > 0, f"{job_id}: invalid track id")
    require(int(job.get("pack_id", 0)) > 0, f"{job_id}: invalid pack id")
    require(job.get("promotion_allowed_by_job") is False, f"{job_id}: promotion must be blocked")
    require(
        job.get("result_schema") == "earthbound-decomp.audio-zero-runtime-probe-result.v1",
        f"{job_id}: unexpected result schema",
    )
    require(job.get("reader_pc_targets"), f"{job_id}: missing reader PC targets")
    require(job.get("required_capture_fields"), f"{job_id}: missing required capture fields")
    require(job.get("success_criteria"), f"{job_id}: missing success criteria")
    source = job.get("source", {})
    require(source.get("source_spc", {}).get("sha1"), f"{job_id}: missing source SPC SHA-1")
    require(source.get("source_render", {}).get("sha1"), f"{job_id}: missing source render SHA-1")
    result_path = str(job.get("result_path", "")).replace("\\", "/")
    require(
        result_path.startswith("build/audio/zero-runtime-probe/") and result_path.endswith("zero-runtime-proof-result.json"),
        f"{job_id}: unexpected result path {result_path}",
    )
    job_path = str(job.get("job_path", "")).replace("\\", "/")
    require(
        job_path.startswith(job_root.rstrip("/") + "/") and job_path.endswith("/job.json"),
        f"{job_id}: unexpected job path {job_path}",
    )


def validate_generated_job_files(contract: dict[str, Any]) -> None:
    runner = contract.get("runner", {})
    index_path = repo_path(str(runner.get("job_index_path", "")))
    require(index_path.exists(), f"missing generated job index {index_path}")
    index = load_json(index_path)
    require(index.get("schema") == "earthbound-decomp.audio-zero-runtime-probe-job-index.v1", "unexpected generated job index schema")
    require(int(index.get("job_count", -1)) == len(contract.get("jobs", [])), "generated job index count mismatch")
    by_id = {str(job.get("job_id")): job for job in index.get("jobs", [])}
    require(set(by_id) == {str(job.get("job_id")) for job in contract.get("jobs", [])}, "generated job IDs mismatch")
    for job in contract.get("jobs", []):
        path = repo_path(str(job.get("job_path", "")))
        require(path.exists(), f"{job.get('job_id')}: missing generated per-job file {path}")
        generated = load_json(path)
        require(generated == job, f"{job.get('job_id')}: generated per-job file differs from contract")


def validate(data: dict[str, Any], *, require_generated_jobs: bool) -> None:
    require(data.get("schema") == "earthbound-decomp.audio-zero-runtime-probe-runner-contract.v1", "unexpected schema")
    require(data.get("status") == "zero_runtime_probe_runner_jobs_ready", f"unexpected status {data.get('status')}")
    require(data.get("probe_plan") == "manifests/audio-zero-runtime-probe-plan.json", "unexpected probe plan")
    source_policy = data.get("source_policy", {})
    require(source_policy.get("requires_user_supplied_rom") is True, "source policy must require user ROM")
    require(source_policy.get("generated_probe_outputs_are_ignored") is True, "probe outputs must be ignored")

    runner = data.get("runner", {})
    require(str(runner.get("job_root", "")).startswith("build/audio/zero-runtime-probe-jobs"), "unexpected job root")
    require(str(runner.get("job_index_path", "")).endswith("zero-runtime-probe-jobs.json"), "unexpected job index path")
    require(runner.get("per_job_schema") == "earthbound-decomp.audio-zero-runtime-probe-job.v1", "unexpected per-job schema")
    require(runner.get("result_schema") == "earthbound-decomp.audio-zero-runtime-probe-result.v1", "unexpected result schema")
    require(runner.get("behavior_change_allowed") is False, "runner must not allow behavior changes")
    require(runner.get("public_exact_promotion_allowed") is False, "runner must not allow direct exact promotion")
    command = runner.get("external_command_template", [])
    require("{job}" in command and "{result}" in command, "external command template must contain job/result placeholders")

    jobs = data.get("jobs", [])
    summary = data.get("summary", {})
    require(int(summary.get("job_count", -1)) == len(jobs), "job count mismatch")
    require(int(summary.get("unique_track_count", -1)) == len({int(job.get("track_id", 0)) for job in jobs}), "unique track count mismatch")
    require(summary.get("sequence_promotion_allowed") is False, "summary must keep sequence promotion blocked")
    require(summary.get("trace_focus_job_counts") == count_jobs(jobs, "trace_focus"), "trace focus counts mismatch")
    require(summary.get("pack_context_job_counts") == count_jobs(jobs, "pack_context_class"), "pack context counts mismatch")
    require(int(summary.get("required_capture_field_count", 0)) >= 10, "required capture field count too small")

    seen_job_ids: set[str] = set()
    seen_track_ids: set[int] = set()
    for job in jobs:
        validate_job(job, job_root=str(runner["job_root"]))
        job_id = str(job["job_id"])
        track_id = int(job["track_id"])
        require(job_id not in seen_job_ids, f"duplicate job id {job_id}")
        require(track_id not in seen_track_ids, f"duplicate track id {track_id}")
        seen_job_ids.add(job_id)
        seen_track_ids.add(track_id)

    require(data.get("runner_policy"), "missing runner policy")
    if require_generated_jobs:
        validate_generated_job_files(data)


def main() -> int:
    args = parse_args()
    data = load_json(Path(args.contract))
    validate(data, require_generated_jobs=args.require_generated_jobs)
    suffix = " with generated job files" if args.require_generated_jobs else ""
    print(
        "Audio 0x00 runtime probe runner contract validation OK: "
        f"{data['summary']['job_count']} jobs{suffix}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
