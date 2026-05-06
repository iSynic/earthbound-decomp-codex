#!/usr/bin/env python3
"""Validate the targeted non-0x00 control probe plan."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MANIFEST = ROOT / "manifests" / "audio-nonzero-control-probe-plan.json"
REQUIRED_COMMANDS = {"0xEF", "0xFD", "0xFE", "0xFF"}
REQUIRED_FIELDS = {
    "sequence_read_trace",
    "command",
    "reader_pc",
    "sequence_address",
    "command_pointer_registers.dp_10_11",
    "command_pointer_registers.dp_12_13",
    "post_read_branch_or_effect",
    "phrase_or_subroutine_stack_state",
    "timing_counter_state",
    "control_effect_classification",
    "classification_evidence",
}
ALLOWED_KINDS = {
    "return_stack_context",
    "static_walk_blocker",
    "timing_toggle_context",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate audio non-0x00 control probe plan.")
    parser.add_argument("manifest", nargs="?", default=str(DEFAULT_MANIFEST))
    return parser.parse_args()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


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
    if source is None:
        return
    require(source.get("oracle_job_id"), f"{job_id}: source candidate missing oracle job id")
    for label in ("source_spc", "source_render"):
        record = source.get(label, {})
        require(record.get("path"), f"{job_id}: source candidate missing {label} path")
        require(record.get("sha1"), f"{job_id}: source candidate missing {label} SHA-1")
        require(int(record.get("bytes", 0)) > 0, f"{job_id}: source candidate missing {label} byte count")


def validate(data: dict[str, Any]) -> None:
    require(data.get("schema") == "earthbound-decomp.audio-nonzero-control-probe-plan.v1", "unexpected schema")
    require(
        data.get("status") == "nonzero_control_probe_jobs_ready_runner_extension_pending",
        f"unexpected status {data.get('status')}",
    )
    references = set(data.get("references", []))
    for reference in (
        "manifests/audio-nonzero-control-semantics-frontier.json",
        "manifests/audio-duration-uncertainty-register.json",
        "manifests/audio-sequence-command-semantics.json",
        "manifests/audio-oracle-comparison-plan-all-tracks.json",
    ):
        require(reference in references, f"missing reference {reference}")

    source_policy = data.get("source_policy", {})
    require(source_policy.get("requires_user_supplied_rom") is True, "source policy must require user ROM")
    require(source_policy.get("generated_probe_outputs_are_ignored") is True, "probe outputs must be ignored")
    output_root = str(source_policy.get("generated_outputs_root", ""))
    require(output_root.startswith("build/audio/nonzero-control-probe"), f"unexpected output root {output_root}")

    runner_contract = data.get("runner_contract", {})
    require(runner_contract.get("behavior_change_allowed") is False, "probe plan must not allow behavior changes")
    require(runner_contract.get("public_exact_promotion_allowed") is False, "plan must not allow direct exact promotion")
    fields = set(runner_contract.get("required_capture_fields", []))
    missing = REQUIRED_FIELDS - fields
    require(not missing, f"runner contract missing fields {sorted(missing)}")
    classifications = set(runner_contract.get("accepted_control_effect_classifications", []))
    for classification in ("ef_call_return", "timing_toggle", "earthbound_variant_ff", "unresolved"):
        require(classification in classifications, f"missing classification {classification}")

    jobs = data.get("jobs", [])
    summary = data.get("summary", {})
    require(int(summary.get("job_count", -1)) == len(jobs), "job count mismatch")
    require(len(jobs) == 7, f"expected 7 command/reader-PC jobs, got {len(jobs)}")
    require(summary.get("sequence_promotion_allowed") is False, "summary must keep sequence promotion blocked")
    require(summary.get("command_job_counts") == count_jobs(jobs, "command"), "command counts mismatch")
    require(summary.get("reader_pc_job_counts") == count_jobs(jobs, "reader_pc"), "reader PC counts mismatch")
    require(summary.get("affected_kind_job_counts") == count_jobs(jobs, "affected_kind"), "affected kind counts mismatch")
    require(int(summary.get("frontier_track_count", 0)) == 155, "expected 155 frontier tracks")

    seen_job_ids: set[str] = set()
    command_set: set[str] = set()
    source_candidate_count = 0
    source_join_count = 0
    has_0957_ff = False
    for job in jobs:
        job_id = str(job.get("job_id", ""))
        require(job_id.startswith("nonzero-probe-"), f"unexpected job id {job_id}")
        require(job_id not in seen_job_ids, f"duplicate job id {job_id}")
        seen_job_ids.add(job_id)
        command = str(job.get("command"))
        command_set.add(command)
        require(command in REQUIRED_COMMANDS, f"{job_id}: unexpected command {command}")
        require(str(job.get("reader_pc", "")).startswith("0x"), f"{job_id}: invalid reader PC")
        require(int(job.get("read_count", 0)) > 0, f"{job_id}: missing read count")
        require(job.get("affected_kind") in ALLOWED_KINDS, f"{job_id}: unexpected affected kind")
        require(job.get("promotion_question"), f"{job_id}: missing promotion question")
        require(job.get("priority_reason"), f"{job_id}: missing priority reason")
        require(set(job.get("required_capture_fields", [])) == fields, f"{job_id}: capture fields differ")
        require(job.get("promotion_allowed_by_plan") is False, f"{job_id}: promotion must stay blocked")
        require(len(job.get("success_criteria", [])) >= 4, f"{job_id}: success criteria too thin")
        for output in job.get("probe_outputs", {}).values():
            require(output_path_is_under(output_root, str(output)), f"{job_id}: bad output path {output}")
        candidates = job.get("source_candidates", [])
        require(candidates, f"{job_id}: missing source candidates")
        source_candidate_count += len(candidates)
        for candidate in candidates:
            validate_source_candidate(job_id, candidate)
            if candidate.get("source"):
                source_join_count += 1
        if command == "0xFF" and job.get("reader_pc") == "0x0957":
            has_0957_ff = True
            require(int(job.get("priority_rank", 0)) >= 100, "0x0957 FF job should be highest priority")
        if command == "0xFF":
            require(job.get("affected_kind") == "static_walk_blocker", "FF job must be static-walk blocker")
        if command in {"0xFD", "0xFE"}:
            require(job.get("affected_kind") == "timing_toggle_context", f"{command}: expected timing context")
        if command == "0xEF":
            require(job.get("affected_kind") == "return_stack_context", "EF job must be return-stack context")
    require(command_set == REQUIRED_COMMANDS, "command coverage mismatch")
    require(has_0957_ff, "missing priority 0x0957 FF job")
    require(int(summary.get("source_candidate_count", -1)) == source_candidate_count, "source candidate count mismatch")
    require(
        int(summary.get("source_candidate_with_oracle_job_count", -1)) == source_join_count,
        "source candidate oracle join count mismatch",
    )
    require(data.get("promotion_policy"), "missing promotion policy")
    require(data.get("next_work"), "missing next work")


def main() -> int:
    args = parse_args()
    data = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    validate(data)
    print(
        "Audio nonzero control probe plan validation OK: "
        f"{data['summary']['job_count']} jobs, "
        f"{data['summary']['reader_pc_job_counts']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
