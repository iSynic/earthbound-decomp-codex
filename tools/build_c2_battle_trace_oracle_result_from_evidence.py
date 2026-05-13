#!/usr/bin/env python3
"""Build a C2 battle trace-oracle result from reviewed trace evidence."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import validate_c2_battle_trace_oracle_result


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PACKET = ROOT / "manifests" / "c2-battle-trace-oracle-packet.json"
ALLOWED_STATUS = ["ok", "failed", "unsupported", "unresolved"]
ALLOWED_CLASSIFICATIONS = [
    "confirmed_contract",
    "refined_contract",
    "contradicted_plan",
    "unreachable_from_source_state",
    "needs_followup",
    "unresolved",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a reviewed C2 battle trace-oracle result JSON.")
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--job-id", help="Packet job id.")
    target.add_argument("--oracle-id", help="Packet oracle id.")
    parser.add_argument("--packet", default=str(DEFAULT_PACKET), help="C2 battle trace-oracle packet JSON.")
    parser.add_argument("--output", help="Result JSON output path. Defaults to packet result path.")
    parser.add_argument("--trace-path", help="Raw trace path. Defaults to packet raw trace path.")
    parser.add_argument("--job-path", help="Job JSON path. Defaults to packet job path.")
    parser.add_argument("--status", default="unresolved", choices=ALLOWED_STATUS)
    parser.add_argument("--classification", default="unresolved", choices=ALLOWED_CLASSIFICATIONS)
    parser.add_argument("--classification-rationale", required=True, help="Short review rationale.")
    parser.add_argument("--harness-name", default="manual_c2_battle_trace_review")
    parser.add_argument("--harness-version", default="manual-review-v1")
    parser.add_argument("--observed-address", action="append", default=[], help="Observed SNES CPU address from the packet job. May repeat.")
    parser.add_argument("--captured-fields-json", help="JSON object containing captured_fields values.")
    parser.add_argument(
        "--allow-invalid",
        action="store_true",
        help="Write the result even if it fails validation. Intended only for debugging fixtures.",
    )
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def repo_path(path_text: str) -> Path:
    path = Path(path_text)
    return path if path.is_absolute() else ROOT / path


def find_job(packet: dict[str, Any], *, job_id: str | None, oracle_id: str | None) -> dict[str, Any]:
    for job in packet.get("jobs", []):
        if job_id and job.get("job_id") == job_id:
            return job
        if oracle_id and job.get("oracle_id") == oracle_id:
            return job
    raise ValueError(f"could not find C2 oracle job for job_id={job_id!r} oracle_id={oracle_id!r}")


def load_captured_fields(path_text: str | None) -> dict[str, Any]:
    if not path_text:
        return {}
    data = load_json(Path(path_text))
    if not isinstance(data, dict):
        raise ValueError("--captured-fields-json must contain a JSON object")
    return data


def build_result(job: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    paths = job["output_paths"]
    trace_path = args.trace_path or paths["raw_trace_path"]
    job_path = args.job_path or paths["job_path"]
    return {
        "schema": "earthbound-decomp.c2-battle-trace-oracle-result.v1",
        "job_id": job["job_id"],
        "oracle_id": job["oracle_id"],
        "status": args.status,
        "contract_classification": args.classification,
        "observed_addresses": args.observed_address,
        "captured_fields": load_captured_fields(args.captured_fields_json),
        "promotion_allowed_by_result": False,
        "behavior_change_allowed": False,
        "evidence": {
            "trace_path": trace_path,
            "classification_rationale": args.classification_rationale,
            "harness_name": args.harness_name,
            "harness_version": args.harness_version,
            "job_path": job_path,
        },
    }


def validate_result(result: dict[str, Any], job: dict[str, Any]) -> list[str]:
    return validate_c2_battle_trace_oracle_result.validate(result, job)


def main() -> int:
    args = parse_args()
    packet = load_json(Path(args.packet))
    job = find_job(packet, job_id=args.job_id, oracle_id=args.oracle_id)
    result = build_result(job, args)
    errors = validate_result(result, job)
    output = repo_path(args.output or str(job["output_paths"]["result_path"]))
    if errors and not args.allow_invalid:
        print("C2 battle trace oracle reviewed result was not written because validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    if errors:
        print(f"Wrote invalid debug result {output}")
        for error in errors:
            print(f"- {error}")
        return 1
    print(f"Wrote reviewed C2 battle trace-oracle result {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
