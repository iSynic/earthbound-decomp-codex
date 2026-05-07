#!/usr/bin/env python3
"""Validate the targeted 0x00 runtime probe plan."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MANIFEST = ROOT / "manifests" / "audio-zero-runtime-probe-plan.json"

ALLOWED_TRACE_FOCUS = {
    "prove_zero_effect_but_loop_points_remain_required",
    "prove_zero_effect_for_policy_corroboration",
    "prove_zero_effect_then_classify_active_preview",
    "prove_zero_end_effect_then_review_finite_candidate",
    "trace_zero_reader_with_ef_stack_state",
}
ALLOWED_PACK_CLASSES = {
    "needs_ef_return_stack_model",
    "zero_phrase_end_candidate_runtime_pending",
    "zero_candidates_outside_sample_detail",
}
ALLOWED_POST_ZERO_ACTIONS = {
    "classify_active_preview_before_exact_export",
    "corroborate_existing_pcm_trim",
    "decode_loop_points_before_exact_export",
    "keep_current_export_policy",
    "review_observed_silence_as_finite_or_transition",
}
REQUIRED_CAPTURE_FIELD_SUBSET = {
    "sequence_read_trace",
    "reader_pc",
    "sequence_address",
    "command_pointer_registers.dp_10_11",
    "command_pointer_registers.dp_12_13",
    "ef_call_depth_before_zero",
    "ef_return_target_before_zero",
    "post_zero_branch_or_effect",
    "zero_effect_classification",
    "classification_evidence",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate the audio 0x00 runtime probe plan.")
    parser.add_argument("manifest", nargs="?", default=str(DEFAULT_MANIFEST))
    return parser.parse_args()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def output_path_is_under(root: str, path_text: str) -> bool:
    normalized_root = root.rstrip("/\\") + "/"
    normalized_path = path_text.replace("\\", "/")
    return normalized_path.startswith(normalized_root) and ".." not in Path(normalized_path).parts


def count_jobs(jobs: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for job in jobs:
        counts[str(job.get(key))] += 1
    return dict(sorted(counts.items()))


def blocker_counts(jobs: list[dict[str, Any]]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for job in jobs:
        for blocker in job.get("pre_promotion_blockers", []):
            counts[str(blocker)] += 1
    return dict(sorted(counts.items()))


def validate_source(job: dict[str, Any]) -> None:
    source = job.get("source", {})
    require(source.get("oracle_job_id"), f"{job.get('job_id')}: missing source oracle job id")
    for label in ("source_spc", "source_render"):
        record = source.get(label, {})
        require(record.get("path"), f"{job.get('job_id')}: missing {label} path")
        require(record.get("sha1"), f"{job.get('job_id')}: missing {label} SHA-1")
        require(int(record.get("bytes", 0)) > 0, f"{job.get('job_id')}: missing {label} byte count")


def validate(data: dict[str, Any]) -> None:
    require(data.get("schema") == "earthbound-decomp.audio-zero-runtime-probe-plan.v1", "unexpected schema")
    require(
        data.get("status") == "zero_runtime_probe_jobs_ready_runner_extension_pending",
        f"unexpected status {data.get('status')}",
    )
    references = set(data.get("references", []))
    require("manifests/audio-zero-ef-return-frontier.json" in references, "missing frontier reference")
    require("manifests/audio-oracle-comparison-plan-all-tracks.json" in references, "missing oracle plan reference")

    source_policy = data.get("source_policy", {})
    require(source_policy.get("requires_user_supplied_rom") is True, "source policy must require user ROM")
    require(source_policy.get("generated_probe_outputs_are_ignored") is True, "probe outputs must be ignored")
    output_root = str(source_policy.get("generated_outputs_root", ""))
    require(output_root.startswith("build/audio/zero-runtime-probe"), f"unexpected output root {output_root}")
    require(
        source_policy.get("do_not_distribute_reference_spc_wav_or_rom_derived_audio") is True,
        "source policy must forbid distributing ROM-derived audio",
    )

    runner_contract = data.get("runner_contract", {})
    require(runner_contract.get("behavior_change_allowed") is False, "probe plan must not allow behavior changes")
    require(runner_contract.get("public_exact_promotion_allowed") is False, "plan must not allow direct exact promotion")
    required_fields = set(runner_contract.get("required_capture_fields", []))
    missing_fields = REQUIRED_CAPTURE_FIELD_SUBSET - required_fields
    require(not missing_fields, f"runner contract missing fields {sorted(missing_fields)}")
    source_requirements = set(runner_contract.get("source_effect_capture_requirements", []))
    require(
        runner_contract.get("source_effect_frontier") == "earthbound-decomp.audio-spc700-source-effect-frontier.v1",
        "missing source-effect frontier reference",
    )
    require(len(source_requirements) >= 8, "source-effect capture requirements too thin")
    require("independent emulator oracle" in str(runner_contract.get("independent_oracle_scope", "")), "missing oracle scope boundary")

    reader_pcs = data.get("reader_pc_targets", [])
    require(reader_pcs, "missing reader PC targets")
    seen_pcs: set[str] = set()
    for record in reader_pcs:
        pc = str(record.get("pc", ""))
        require(pc.startswith("0x"), f"invalid reader PC {pc}")
        require(pc not in seen_pcs, f"duplicate reader PC {pc}")
        seen_pcs.add(pc)
        require(int(record.get("read_count", 0)) > 0, f"reader PC {pc}: missing read count")
        require(record.get("required_observation"), f"reader PC {pc}: missing required observation")

    jobs = data.get("jobs", [])
    summary = data.get("summary", {})
    require(int(summary.get("job_count", -1)) == len(jobs), "job count mismatch")
    require(len(jobs) > 0, "expected probe jobs")
    require(int(summary.get("reader_pc_target_count", -1)) == len(reader_pcs), "reader PC count mismatch")
    require(summary.get("sequence_promotion_allowed") is False, "summary must keep sequence promotion blocked")
    require(int(summary.get("source_oracle_job_count", -1)) == len(jobs), "source oracle job count mismatch")

    seen_job_ids: set[str] = set()
    seen_track_ids: set[int] = set()
    for job in jobs:
        job_id = str(job.get("job_id", ""))
        require(job_id.startswith("zero-probe-track-"), f"unexpected job id {job_id}")
        require(job_id not in seen_job_ids, f"duplicate job id {job_id}")
        seen_job_ids.add(job_id)
        track_id = int(job.get("track_id", 0))
        require(track_id > 0, f"{job_id}: invalid track id")
        require(track_id not in seen_track_ids, f"duplicate track id {track_id}")
        seen_track_ids.add(track_id)
        require(str(job.get("pack_context_class")) in ALLOWED_PACK_CLASSES, f"{job_id}: unexpected pack class")
        require(str(job.get("trace_focus")) in ALLOWED_TRACE_FOCUS, f"{job_id}: unexpected trace focus")
        require(
            str(job.get("post_zero_proof_action")) in ALLOWED_POST_ZERO_ACTIONS,
            f"{job_id}: unexpected post-zero action",
        )
        require(job.get("pre_promotion_blockers"), f"{job_id}: expected pre-promotion blockers")
        require("zero_runtime_effect_proof" in job.get("pre_promotion_blockers", []), f"{job_id}: missing zero proof blocker")
        require(job.get("promotion_question"), f"{job_id}: missing promotion question")
        require(set(job.get("required_capture_fields", [])) == required_fields, f"{job_id}: capture fields differ")
        require(
            set(job.get("source_effect_capture_requirements", [])) == source_requirements,
            f"{job_id}: source-effect capture requirements differ",
        )
        require(set(job.get("reader_pc_targets", [])) == seen_pcs, f"{job_id}: reader PC targets differ")
        require(job.get("promotion_allowed_by_plan") is False, f"{job_id}: promotion must be blocked by plan")
        validate_source(job)
        static_context = job.get("zero_static_context", {})
        require(int(static_context.get("zero_terminator_candidates", 0)) > 0, f"{job_id}: missing zero candidates")
        require(static_context.get("sampled_zero_walk_context_class_counts"), f"{job_id}: missing walk context")
        outputs = job.get("probe_outputs", {})
        for key in ("root", "raw_trace", "result_json", "evidence_markdown"):
            require(output_path_is_under(output_root, str(outputs.get(key, ""))), f"{job_id}: bad {key} output path")
        require(len(job.get("success_criteria", [])) >= 4, f"{job_id}: success criteria too thin")

    require(int(summary.get("unique_track_count", -1)) == len(seen_track_ids), "unique track count mismatch")
    require(summary.get("trace_focus_job_counts") == count_jobs(jobs, "trace_focus"), "trace focus counts mismatch")
    require(summary.get("pack_context_job_counts") == count_jobs(jobs, "pack_context_class"), "pack class counts mismatch")
    require(
        summary.get("post_zero_proof_action_job_counts") == count_jobs(jobs, "post_zero_proof_action"),
        "post-zero action counts mismatch",
    )
    require(
        summary.get("pre_promotion_blocker_track_counts") == blocker_counts(jobs),
        "pre-promotion blocker counts mismatch",
    )
    require(data.get("promotion_policy"), "missing promotion policy")
    require(data.get("next_work"), "missing next work")


def main() -> int:
    args = parse_args()
    data = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    validate(data)
    print(
        "Audio 0x00 runtime probe plan validation OK: "
        f"{data['summary']['job_count']} jobs, "
        f"{data['summary']['reader_pc_target_count']} reader PCs"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
