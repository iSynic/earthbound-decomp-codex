#!/usr/bin/env python3
"""Validate one targeted 0x00 runtime probe result."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PLAN = ROOT / "manifests" / "audio-zero-runtime-probe-plan.json"

ALLOWED_STATUS = {"ok", "failed", "unsupported", "unresolved"}
ALLOWED_CLASSIFICATIONS = {
    "true_end",
    "ef_return",
    "loop_or_hold_continues",
    "unreachable_from_source_state",
    "unresolved",
}
REQUIRED_READER_OBSERVATION_FIELDS = {
    "reader_pc",
    "sequence_address",
    "command",
    "instruction",
    "command_pointer_registers",
    "post_zero_branch_or_effect",
}
REQUIRED_EF_OBSERVATION_FIELDS = {
    "ef_call_depth_before_zero",
    "ef_return_target_before_zero",
    "ef_call_depth_after_zero",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate one audio 0x00 runtime probe result.")
    parser.add_argument("result", help="Probe result JSON path.")
    parser.add_argument("--plan", default=str(DEFAULT_PLAN), help="Probe plan manifest for cross-checking.")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def find_job(plan: dict[str, Any], job_id: str) -> dict[str, Any] | None:
    for job in plan.get("jobs", []):
        if job.get("job_id") == job_id:
            return job
    return None


def validate(result: dict[str, Any], job: dict[str, Any] | None) -> list[str]:
    errors: list[str] = []
    if result.get("schema") != "earthbound-decomp.audio-zero-runtime-probe-result.v1":
        errors.append(f"unexpected schema: {result.get('schema')}")
    for field in (
        "job_id",
        "track_id",
        "track_name",
        "status",
        "source_spc_sha1",
        "zero_effect_classification",
        "reader_pc_observations",
        "ef_stack_observations",
        "promotion_allowed_by_result",
        "evidence",
    ):
        if field not in result:
            errors.append(f"missing required result field {field}")

    status = str(result.get("status"))
    if status not in ALLOWED_STATUS:
        errors.append(f"unexpected status {status}")
    classification = str(result.get("zero_effect_classification"))
    if classification not in ALLOWED_CLASSIFICATIONS:
        errors.append(f"unexpected zero_effect_classification {classification}")
    if status == "ok" and classification in {"unreachable_from_source_state", "unresolved"}:
        errors.append("ok result must provide a resolved zero-effect classification")
    if status != "ok" and classification not in {"unreachable_from_source_state", "unresolved"}:
        errors.append("non-ok result must not claim a resolved zero-effect classification")
    if result.get("promotion_allowed_by_result") is True:
        errors.append("probe results must not directly allow public exact-duration promotion")

    if job is not None:
        if result.get("track_id") != job.get("track_id"):
            errors.append(f"track_id mismatch {result.get('track_id')} != {job.get('track_id')}")
        if result.get("track_name") != job.get("track_name"):
            errors.append(f"track_name mismatch {result.get('track_name')} != {job.get('track_name')}")
        expected_sha1 = job.get("source", {}).get("source_spc", {}).get("sha1")
        if result.get("source_spc_sha1") != expected_sha1:
            errors.append(f"source_spc_sha1 mismatch {result.get('source_spc_sha1')} != {expected_sha1}")
        if result.get("promotion_allowed_by_result") != job.get("promotion_allowed_by_plan"):
            errors.append("promotion_allowed_by_result must match the blocked plan policy")

    reader_observations = result.get("reader_pc_observations", [])
    if status == "ok" and not reader_observations:
        errors.append("ok result must include reader_pc_observations")
    for index, observation in enumerate(reader_observations):
        missing = REQUIRED_READER_OBSERVATION_FIELDS - set(observation)
        if missing:
            errors.append(f"reader observation {index}: missing fields {sorted(missing)}")
        if str(observation.get("command")) != "0x00":
            errors.append(f"reader observation {index}: command must be 0x00")
        registers = observation.get("command_pointer_registers", {})
        for field in ("dp_10_11", "dp_12_13"):
            if field not in registers:
                errors.append(f"reader observation {index}: missing command pointer {field}")

    ef_observations = result.get("ef_stack_observations", [])
    if status == "ok" and not ef_observations:
        errors.append("ok result must include ef_stack_observations")
    for index, observation in enumerate(ef_observations):
        missing = REQUIRED_EF_OBSERVATION_FIELDS - set(observation)
        if missing:
            errors.append(f"EF observation {index}: missing fields {sorted(missing)}")

    evidence = result.get("evidence", {})
    if status == "ok":
        for field in ("trace_path", "classification_rationale", "harness_name", "harness_version"):
            if field not in evidence:
                errors.append(f"ok result evidence missing {field}")
    return errors


def main() -> int:
    args = parse_args()
    result = load_json(Path(args.result))
    plan = load_json(Path(args.plan))
    job = find_job(plan, str(result.get("job_id", "")))
    if job is None:
        print("Audio 0x00 runtime probe result validation failed:")
        print(f"- job {result.get('job_id')} was not found in {args.plan}")
        return 1
    errors = validate(result, job)
    if errors:
        print("Audio 0x00 runtime probe result validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print(
        "Audio 0x00 runtime probe result validation OK: "
        f"{result['job_id']} {result['zero_effect_classification']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
