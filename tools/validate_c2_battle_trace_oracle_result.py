#!/usr/bin/env python3
"""Validate one C2 battle trace-oracle result."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PACKET = ROOT / "manifests" / "c2-battle-trace-oracle-packet.json"

ALLOWED_STATUS = {"ok", "failed", "unsupported", "unresolved"}
ALLOWED_CLASSIFICATIONS = {
    "confirmed_contract",
    "refined_contract",
    "contradicted_plan",
    "unreachable_from_source_state",
    "needs_followup",
    "unresolved",
}
RESOLVED_CLASSIFICATIONS = {
    "confirmed_contract",
    "refined_contract",
    "contradicted_plan",
    "needs_followup",
}
REQUIRED_PROOF_CAPTURE_FIELDS = {
    "trace_id",
    "scenario_name",
    "rom_sha1",
    "pc",
    "routine_label",
    "classification",
    "classification_evidence",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate one C2 battle trace-oracle result.")
    parser.add_argument("result", help="Result JSON path.")
    parser.add_argument("--packet", default=str(DEFAULT_PACKET), help="C2 battle trace-oracle packet JSON.")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def find_job(packet: dict[str, Any], job_id: str) -> dict[str, Any] | None:
    for job in packet.get("jobs", []):
        if job.get("job_id") == job_id:
            return job
    return None


def resolve_repo_path(path_text: str) -> Path:
    path = Path(path_text)
    return path if path.is_absolute() else ROOT / path


def is_stub_result(result: dict[str, Any]) -> bool:
    evidence = result.get("evidence", {})
    harness_name = str(evidence.get("harness_name", ""))
    harness_version = str(evidence.get("harness_version", "")).lower()
    return harness_name == "c2_battle_trace_oracle_stub_harness" or "stub" in harness_version or "dry-run" in harness_version


def proof_trace_path(result: dict[str, Any]) -> Path:
    return resolve_repo_path(str(result.get("evidence", {}).get("trace_path", "")))


def validate_ok_result(result: dict[str, Any], job: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    evidence = result.get("evidence", {})
    expected_paths = job.get("output_paths", {})
    if is_stub_result(result):
        errors.append("ok result cannot come from the schema-only stub harness")
    if str(evidence.get("job_path")) != str(expected_paths.get("job_path")):
        errors.append("ok result evidence job_path must match the packet job path")
    if str(evidence.get("trace_path")) != str(expected_paths.get("raw_trace_path")):
        errors.append("ok result evidence trace_path must match the packet raw trace path")
    for field in ("trace_path", "classification_rationale", "harness_name", "harness_version", "job_path"):
        value = evidence.get(field)
        if not isinstance(value, str) or not value:
            errors.append(f"ok result evidence {field} must be a non-empty string")
    trace_path = proof_trace_path(result)
    if not trace_path.exists():
        errors.append(f"ok result trace_path does not exist: {evidence.get('trace_path')}")
    elif trace_path.stat().st_size <= 0:
        errors.append(f"ok result trace_path is empty: {evidence.get('trace_path')}")
    captured = result.get("captured_fields", {})
    if not isinstance(captured, dict):
        errors.append("ok result captured_fields must be an object")
    else:
        missing_core = REQUIRED_PROOF_CAPTURE_FIELDS - set(captured)
        if missing_core:
            errors.append(f"ok result missing proof capture fields {sorted(missing_core)}")
        missing_job_fields = set(job.get("capture_fields", [])) - set(captured)
        if missing_job_fields:
            errors.append(f"ok result missing job capture fields {sorted(missing_job_fields)}")
        for field in REQUIRED_PROOF_CAPTURE_FIELDS:
            value = captured.get(field)
            if field in captured and (value is None or value == ""):
                errors.append(f"ok result proof capture field {field} must be populated")
    observed = result.get("observed_addresses", [])
    if not observed:
        errors.append("ok result must include observed_addresses")
    if observed and not isinstance(observed, list):
        errors.append("observed_addresses must be a list")
    expected_addresses = set(job.get("addresses", []))
    if isinstance(observed, list):
        for address in observed:
            if not isinstance(address, str) or not address:
                errors.append("observed_addresses must contain non-empty strings")
                continue
            if address not in expected_addresses:
                errors.append(f"observed address {address} is not part of the oracle address set")
    return errors


def validate(result: dict[str, Any], job: dict[str, Any] | None) -> list[str]:
    errors: list[str] = []
    if result.get("schema") != "earthbound-decomp.c2-battle-trace-oracle-result.v1":
        errors.append(f"unexpected schema: {result.get('schema')}")
    for field in (
        "job_id",
        "oracle_id",
        "status",
        "contract_classification",
        "observed_addresses",
        "captured_fields",
        "promotion_allowed_by_result",
        "behavior_change_allowed",
        "evidence",
    ):
        if field not in result:
            errors.append(f"missing required result field {field}")

    status = str(result.get("status"))
    classification = str(result.get("contract_classification"))
    if status not in ALLOWED_STATUS:
        errors.append(f"unexpected status {status}")
    if classification not in ALLOWED_CLASSIFICATIONS:
        errors.append(f"unexpected contract_classification {classification}")
    if status == "ok" and classification not in RESOLVED_CLASSIFICATIONS:
        errors.append("ok result must provide a resolved contract classification")
    if status != "ok" and classification in RESOLVED_CLASSIFICATIONS:
        errors.append("non-ok result must not claim a resolved contract classification")
    if result.get("promotion_allowed_by_result") is True:
        errors.append("result must not directly allow source-facing promotion")
    if result.get("behavior_change_allowed") is True:
        errors.append("result must not directly allow behavior changes")

    if job is not None:
        if result.get("oracle_id") != job.get("oracle_id"):
            errors.append(f"oracle_id mismatch {result.get('oracle_id')} != {job.get('oracle_id')}")
        if result.get("promotion_allowed_by_result") != job.get("promotion_allowed_by_plan"):
            errors.append("promotion_allowed_by_result must match the blocked packet policy")
        if result.get("behavior_change_allowed") != job.get("behavior_change_allowed"):
            errors.append("behavior_change_allowed must match the blocked packet policy")
        expected_addresses = set(job.get("addresses", []))
    else:
        expected_addresses = set()

    observed = result.get("observed_addresses", [])
    if status == "ok" and not observed:
        errors.append("ok result must include observed_addresses")
    if observed and not isinstance(observed, list):
        errors.append("observed_addresses must be a list")
    if isinstance(observed, list):
        for address in observed:
            if not isinstance(address, str) or not address:
                errors.append("observed_addresses must contain non-empty strings")
                continue
            if expected_addresses and address not in expected_addresses:
                errors.append(f"observed address {address} is not part of the oracle address set")

    captured = result.get("captured_fields", {})
    if status == "ok" and not captured:
        errors.append("ok result must include captured_fields")
    if captured and not isinstance(captured, dict):
        errors.append("captured_fields must be an object")

    evidence = result.get("evidence", {})
    for field in ("trace_path", "classification_rationale", "harness_name", "harness_version", "job_path"):
        if field not in evidence:
            errors.append(f"result evidence missing {field}")
    if status == "ok" and job is not None:
        errors.extend(validate_ok_result(result, job))
    return errors


def main() -> int:
    args = parse_args()
    result = load_json(Path(args.result))
    packet = load_json(Path(args.packet))
    job = find_job(packet, str(result.get("job_id", "")))
    if job is None:
        print("C2 battle trace oracle result validation failed:")
        print(f"- job {result.get('job_id')} was not found in {args.packet}")
        return 1
    errors = validate(result, job)
    if errors:
        print("C2 battle trace oracle result validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print(
        "C2 battle trace oracle result validation OK: "
        f"{result['job_id']} {result['contract_classification']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
