#!/usr/bin/env python3
"""Validate the non-0x00 control probe runner contract and optional generated jobs."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONTRACT = ROOT / "manifests" / "audio-nonzero-control-probe-runner-contract.json"

REQUIRED_COMMANDS = {"0xEF", "0xFD", "0xFE", "0xFF"}
REQUIRED_JOB_FIELDS = {
    "schema",
    "job_id",
    "command",
    "reader_pc",
    "read_count",
    "affected_kind",
    "source_candidates",
    "source_candidate_track_ids",
    "required_capture_fields",
    "accepted_control_effect_classifications",
    "promotion_allowed_by_job",
    "result_schema",
    "result_path",
    "job_path",
    "status",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate audio non-0x00 control probe runner contract.")
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


def output_path_is_under(root: str, path_text: str) -> bool:
    normalized_root = root.rstrip("/\\") + "/"
    normalized_path = path_text.replace("\\", "/")
    return normalized_path.startswith(normalized_root) and ".." not in Path(normalized_path).parts


def validate_source_candidate(job_id: str, candidate: dict[str, Any]) -> None:
    require(int(candidate.get("track_id", 0)) > 0, f"{job_id}: invalid source candidate track id")
    source = candidate.get("source")
    require(source, f"{job_id}: generated runner jobs must use oracle-joined source candidates")
    require(source.get("oracle_job_id"), f"{job_id}: source candidate missing oracle job id")
    for label in ("source_spc", "source_render"):
        record = source.get(label, {})
        require(record.get("path"), f"{job_id}: source candidate missing {label} path")
        require(record.get("sha1"), f"{job_id}: source candidate missing {label} SHA-1")
        require(int(record.get("bytes", 0)) > 0, f"{job_id}: source candidate missing {label} byte count")


def validate_job(job: dict[str, Any], *, job_root: str, output_root: str) -> None:
    job_id = str(job.get("job_id", ""))
    missing = REQUIRED_JOB_FIELDS - set(job)
    require(not missing, f"{job_id}: missing job fields {sorted(missing)}")
    require(
        job.get("schema") == "earthbound-decomp.audio-nonzero-control-probe-job.v1",
        f"{job_id}: unexpected job schema",
    )
    require(job_id.startswith("nonzero-probe-"), f"unexpected job id {job_id}")
    command = str(job.get("command"))
    require(command in REQUIRED_COMMANDS, f"{job_id}: unexpected command {command}")
    require(str(job.get("reader_pc", "")).startswith("0x"), f"{job_id}: invalid reader PC")
    require(int(job.get("read_count", 0)) > 0, f"{job_id}: missing read count")
    require(job.get("promotion_allowed_by_job") is False, f"{job_id}: promotion must be blocked")
    require(
        job.get("result_schema") == "earthbound-decomp.audio-nonzero-control-probe-result.v1",
        f"{job_id}: unexpected result schema",
    )
    require(job.get("required_capture_fields"), f"{job_id}: missing required capture fields")
    require(job.get("success_criteria"), f"{job_id}: missing success criteria")
    require("unresolved" in set(job.get("accepted_control_effect_classifications", [])), f"{job_id}: missing unresolved class")
    candidates = job.get("source_candidates", [])
    require(candidates, f"{job_id}: missing source candidates")
    track_ids = [int(candidate.get("track_id", 0)) for candidate in candidates]
    require(track_ids == [int(track_id) for track_id in job.get("source_candidate_track_ids", [])], f"{job_id}: track ID mirror mismatch")
    for candidate in candidates:
        validate_source_candidate(job_id, candidate)
    result_path = str(job.get("result_path", "")).replace("\\", "/")
    require(
        output_path_is_under(output_root, result_path)
        and result_path.endswith("nonzero-control-proof-result.json"),
        f"{job_id}: unexpected result path {result_path}",
    )
    output_dir = str(job.get("output_dir", "")).replace("\\", "/")
    require(output_path_is_under(output_root, output_dir + "/marker"), f"{job_id}: unexpected output dir {output_dir}")
    job_path = str(job.get("job_path", "")).replace("\\", "/")
    require(
        job_path.startswith(job_root.rstrip("/") + "/") and job_path.endswith("/job.json"),
        f"{job_id}: unexpected job path {job_path}",
    )
    if command == "0xFF":
        require(job.get("affected_kind") == "static_walk_blocker", f"{job_id}: FF must remain static-walk blocker")
    if command == "0xEF":
        require(job.get("affected_kind") == "return_stack_context", f"{job_id}: EF must be return-stack context")
    if command in {"0xFD", "0xFE"}:
        require(job.get("affected_kind") == "timing_toggle_context", f"{job_id}: FD/FE must be timing context")


def validate_generated_job_files(contract: dict[str, Any]) -> None:
    runner = contract.get("runner", {})
    index_path = repo_path(str(runner.get("job_index_path", "")))
    require(index_path.exists(), f"missing generated job index {index_path}")
    index = load_json(index_path)
    require(
        index.get("schema") == "earthbound-decomp.audio-nonzero-control-probe-job-index.v1",
        "unexpected generated job index schema",
    )
    require(int(index.get("job_count", -1)) == len(contract.get("jobs", [])), "generated job index count mismatch")
    by_id = {str(job.get("job_id")): job for job in index.get("jobs", [])}
    require(set(by_id) == {str(job.get("job_id")) for job in contract.get("jobs", [])}, "generated job IDs mismatch")
    for job in contract.get("jobs", []):
        path = repo_path(str(job.get("job_path", "")))
        require(path.exists(), f"{job.get('job_id')}: missing generated per-job file {path}")
        generated = load_json(path)
        require(generated == job, f"{job.get('job_id')}: generated per-job file differs from contract")


def validate(data: dict[str, Any], *, require_generated_jobs: bool) -> None:
    require(data.get("schema") == "earthbound-decomp.audio-nonzero-control-probe-runner-contract.v1", "unexpected schema")
    require(data.get("status") == "nonzero_control_probe_runner_jobs_ready", f"unexpected status {data.get('status')}")
    require(data.get("probe_plan") == "manifests/audio-nonzero-control-probe-plan.json", "unexpected probe plan")
    source_policy = data.get("source_policy", {})
    require(source_policy.get("requires_user_supplied_rom") is True, "source policy must require user ROM")
    require(source_policy.get("generated_probe_outputs_are_ignored") is True, "probe outputs must be ignored")
    output_root = str(source_policy.get("generated_outputs_root", ""))
    require(output_root.startswith("build/audio/nonzero-control-probe"), f"unexpected output root {output_root}")

    runner = data.get("runner", {})
    require(str(runner.get("job_root", "")).startswith("build/audio/nonzero-control-probe-jobs"), "unexpected job root")
    require(str(runner.get("job_index_path", "")).endswith("nonzero-control-probe-jobs.json"), "unexpected job index path")
    require(
        runner.get("per_job_schema") == "earthbound-decomp.audio-nonzero-control-probe-job.v1",
        "unexpected per-job schema",
    )
    require(
        runner.get("result_schema") == "earthbound-decomp.audio-nonzero-control-probe-result.v1",
        "unexpected result schema",
    )
    require(runner.get("behavior_change_allowed") is False, "runner must not allow behavior changes")
    require(runner.get("public_exact_promotion_allowed") is False, "runner must not allow direct exact promotion")
    command = runner.get("external_command_template", [])
    require("{job}" in command and "{result}" in command, "external command template must contain job/result placeholders")
    require(
        repo_path("tools/validate_audio_nonzero_control_probe_result.py").exists(),
        "missing referenced result validator",
    )
    require(
        repo_path("tools/collect_audio_nonzero_control_probe_results.py").exists(),
        "missing referenced result collector",
    )

    jobs = data.get("jobs", [])
    summary = data.get("summary", {})
    require(int(summary.get("job_count", -1)) == len(jobs), "job count mismatch")
    require(len(jobs) == 7, f"expected 7 jobs, got {len(jobs)}")
    require(summary.get("sequence_promotion_allowed") is False, "summary must keep sequence promotion blocked")
    require(summary.get("command_job_counts") == count_jobs(jobs, "command"), "command counts mismatch")
    require(summary.get("reader_pc_job_counts") == count_jobs(jobs, "reader_pc"), "reader PC counts mismatch")
    require(summary.get("affected_kind_job_counts") == count_jobs(jobs, "affected_kind"), "affected kind counts mismatch")
    require(int(summary.get("required_capture_field_count", 0)) >= 15, "required capture field count too small")
    require(int(summary.get("source_candidate_count", 0)) == sum(len(job.get("source_candidates", [])) for job in jobs), "source candidate count mismatch")
    require(
        int(summary.get("unique_source_track_count", 0))
        == len({int(track_id) for job in jobs for track_id in job.get("source_candidate_track_ids", [])}),
        "unique source track count mismatch",
    )

    seen_job_ids: set[str] = set()
    command_set: set[str] = set()
    has_priority_reader_mix = False
    for job in jobs:
        validate_job(job, job_root=str(runner["job_root"]), output_root=output_root)
        job_id = str(job["job_id"])
        require(job_id not in seen_job_ids, f"duplicate job id {job_id}")
        seen_job_ids.add(job_id)
        command_set.add(str(job["command"]))
        if job.get("reader_pc") == "0x0957" and job.get("command") in {"0xEF", "0xFE", "0xFF"}:
            has_priority_reader_mix = True
    require(command_set == REQUIRED_COMMANDS, "command coverage mismatch")
    require(has_priority_reader_mix, "missing 0x0957 priority reader mix")
    require(data.get("runner_policy"), "missing runner policy")
    if require_generated_jobs:
        validate_generated_job_files(data)


def main() -> int:
    args = parse_args()
    data = load_json(Path(args.contract))
    validate(data, require_generated_jobs=args.require_generated_jobs)
    suffix = " with generated job files" if args.require_generated_jobs else ""
    print(
        "Audio non-0x00 control probe runner contract validation OK: "
        f"{data['summary']['job_count']} jobs{suffix}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
