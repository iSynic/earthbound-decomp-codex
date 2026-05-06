#!/usr/bin/env python3
"""Validate one targeted non-0x00 control probe result."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PLAN = ROOT / "manifests" / "audio-nonzero-control-probe-plan.json"

ALLOWED_STATUS = {"ok", "failed", "unsupported", "unresolved"}
ALLOWED_CLASSIFICATIONS = {
    "ef_call_return",
    "timing_toggle",
    "earthbound_variant_ff",
    "unreachable",
    "unresolved",
}
REQUIRED_READER_OBSERVATION_FIELDS = {
    "reader_pc",
    "sequence_address",
    "command",
    "instruction",
    "command_pointer_registers",
    "post_read_pc",
    "post_read_branch_or_effect",
}
REQUIRED_STATE_EFFECT_FIELDS = {
    "effect_summary",
    "state_before",
    "state_after",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate one audio non-0x00 control probe result.")
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


def expected_source_sha1s(job: dict[str, Any]) -> set[str]:
    sha1s: set[str] = set()
    for candidate in job.get("source_candidates", []):
        source = candidate.get("source") or {}
        sha1 = source.get("source_spc", {}).get("sha1")
        if sha1:
            sha1s.add(str(sha1))
    return sha1s


def expected_track_ids(job: dict[str, Any]) -> set[int]:
    return {int(candidate["track_id"]) for candidate in job.get("source_candidates", [])}


def expected_classification_for_command(command: str) -> set[str]:
    if command == "0xEF":
        return {"ef_call_return", "unreachable", "unresolved"}
    if command in {"0xFD", "0xFE"}:
        return {"timing_toggle", "unreachable", "unresolved"}
    if command == "0xFF":
        return {"earthbound_variant_ff", "unreachable", "unresolved"}
    return {"unresolved"}


def validate(result: dict[str, Any], job: dict[str, Any] | None) -> list[str]:
    errors: list[str] = []
    if result.get("schema") != "earthbound-decomp.audio-nonzero-control-probe-result.v1":
        errors.append(f"unexpected schema: {result.get('schema')}")
    for field in (
        "job_id",
        "command",
        "reader_pc",
        "status",
        "source_candidate_track_id",
        "source_spc_sha1",
        "control_effect_classification",
        "reader_pc_observations",
        "state_effect_observations",
        "promotion_allowed_by_result",
        "evidence",
    ):
        if field not in result:
            errors.append(f"missing required result field {field}")

    status = str(result.get("status"))
    if status not in ALLOWED_STATUS:
        errors.append(f"unexpected status {status}")
    classification = str(result.get("control_effect_classification"))
    if classification not in ALLOWED_CLASSIFICATIONS:
        errors.append(f"unexpected control_effect_classification {classification}")
    if status == "ok" and classification == "unresolved":
        errors.append("ok result must provide a resolved control-effect classification")
    if status != "ok" and classification != "unresolved":
        errors.append("non-ok result must not claim a resolved control-effect classification")
    if result.get("promotion_allowed_by_result") is True:
        errors.append("probe results must not directly allow public exact-duration promotion")

    if job is not None:
        command = str(job.get("command"))
        if result.get("command") != command:
            errors.append(f"command mismatch {result.get('command')} != {command}")
        if result.get("reader_pc") != job.get("reader_pc"):
            errors.append(f"reader_pc mismatch {result.get('reader_pc')} != {job.get('reader_pc')}")
        if classification not in expected_classification_for_command(command):
            errors.append(f"{command}: classification {classification} is not accepted for this command family")
        track_id = int(result.get("source_candidate_track_id", 0))
        if track_id not in expected_track_ids(job):
            errors.append(f"source_candidate_track_id {track_id} is not in the planned source candidates")
        source_sha1 = str(result.get("source_spc_sha1", ""))
        if source_sha1 not in expected_source_sha1s(job):
            errors.append("source_spc_sha1 does not match any planned source candidate")
        if result.get("promotion_allowed_by_result") != job.get("promotion_allowed_by_plan"):
            errors.append("promotion_allowed_by_result must match the blocked plan policy")

    reader_observations = result.get("reader_pc_observations", [])
    if status == "ok" and classification != "unreachable" and not reader_observations:
        errors.append("ok reachable result must include reader_pc_observations")
    for index, observation in enumerate(reader_observations):
        missing = REQUIRED_READER_OBSERVATION_FIELDS - set(observation)
        if missing:
            errors.append(f"reader observation {index}: missing fields {sorted(missing)}")
        if str(observation.get("command")) != str(result.get("command")):
            errors.append(f"reader observation {index}: command mismatch")
        if str(observation.get("reader_pc")) != str(result.get("reader_pc")):
            errors.append(f"reader observation {index}: reader PC mismatch")
        registers = observation.get("command_pointer_registers", {})
        for field in ("dp_10_11", "dp_12_13"):
            if field not in registers:
                errors.append(f"reader observation {index}: missing command pointer {field}")

    state_observations = result.get("state_effect_observations", [])
    if status == "ok" and classification not in {"unreachable", "unresolved"} and not state_observations:
        errors.append("ok effect result must include state_effect_observations")
    for index, observation in enumerate(state_observations):
        missing = REQUIRED_STATE_EFFECT_FIELDS - set(observation)
        if missing:
            errors.append(f"state effect observation {index}: missing fields {sorted(missing)}")

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
        print("Audio non-0x00 control probe result validation failed:")
        print(f"- job {result.get('job_id')} was not found in {args.plan}")
        return 1
    errors = validate(result, job)
    if errors:
        print("Audio non-0x00 control probe result validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print(
        "Audio non-0x00 control probe result validation OK: "
        f"{result['job_id']} {result['control_effect_classification']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
