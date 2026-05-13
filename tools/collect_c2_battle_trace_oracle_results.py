#!/usr/bin/env python3
"""Collect C2 battle trace-oracle result status."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import validate_c2_battle_trace_oracle_result


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PACKET = ROOT / "manifests" / "c2-battle-trace-oracle-packet.json"
DEFAULT_OUTPUT = ROOT / "manifests" / "c2-battle-trace-oracle-results-summary.json"
DEFAULT_NOTES = ROOT / "notes" / "c2-battle-trace-oracle-results-summary.md"

PROOF_GRADE_CLASSIFICATIONS = {"confirmed_contract", "refined_contract", "contradicted_plan"}
TRACE_OBSERVED_CLASSIFICATIONS = PROOF_GRADE_CLASSIFICATIONS | {"needs_followup"}
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
    parser = argparse.ArgumentParser(description="Collect C2 battle trace-oracle result status.")
    parser.add_argument("--packet", default=str(DEFAULT_PACKET), help="C2 battle trace-oracle packet JSON.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Summary JSON output.")
    parser.add_argument("--notes", default=str(DEFAULT_NOTES), help="Summary markdown output.")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_repo_path(path_text: str) -> Path:
    path = Path(path_text)
    return path if path.is_absolute() else ROOT / path


def manifest_path(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def result_path(job: dict[str, Any]) -> Path:
    return resolve_repo_path(str(job.get("output_paths", {}).get("result_path", "")))


def proof_trace_path(result: dict[str, Any]) -> Path:
    return resolve_repo_path(str(result.get("evidence", {}).get("trace_path", "")))


def is_stub_result(result: dict[str, Any] | None) -> bool:
    if result is None:
        return False
    evidence = result.get("evidence", {})
    harness_name = str(evidence.get("harness_name", ""))
    harness_version = str(evidence.get("harness_version", "")).lower()
    return harness_name == "c2_battle_trace_oracle_stub_harness" or "stub" in harness_version or "dry-run" in harness_version


def result_is_proof_capable(job: dict[str, Any], result: dict[str, Any] | None, valid: bool) -> bool:
    if not valid or result is None:
        return False
    if result.get("status") != "ok":
        return False
    if str(result.get("contract_classification")) not in TRACE_OBSERVED_CLASSIFICATIONS:
        return False
    if is_stub_result(result):
        return False
    expected_paths = job.get("output_paths", {})
    evidence = result.get("evidence", {})
    if str(evidence.get("job_path")) != str(expected_paths.get("job_path")):
        return False
    if str(evidence.get("trace_path")) != str(expected_paths.get("raw_trace_path")):
        return False
    for field in ("trace_path", "classification_rationale", "harness_name", "harness_version", "job_path"):
        value = evidence.get(field)
        if not isinstance(value, str) or not value:
            return False
    trace_path = proof_trace_path(result)
    if not trace_path.exists() or trace_path.stat().st_size <= 0:
        return False
    captured = result.get("captured_fields", {})
    if not isinstance(captured, dict):
        return False
    if REQUIRED_PROOF_CAPTURE_FIELDS - set(captured):
        return False
    if set(job.get("capture_fields", [])) - set(captured):
        return False
    for field in REQUIRED_PROOF_CAPTURE_FIELDS:
        value = captured.get(field)
        if value is None or value == "":
            return False
    observed = result.get("observed_addresses", [])
    if not observed or not isinstance(observed, list):
        return False
    allowed_addresses = set(job.get("addresses", []))
    return all(isinstance(address, str) and address and address in allowed_addresses for address in observed)


def result_is_trace_observed(job: dict[str, Any], result: dict[str, Any] | None, valid: bool) -> bool:
    return result_is_proof_capable(job, result, valid)


def result_is_proof_grade(job: dict[str, Any], result: dict[str, Any] | None, valid: bool) -> bool:
    if not result_is_proof_capable(job, result, valid) or result is None:
        return False
    return str(result.get("contract_classification")) in PROOF_GRADE_CLASSIFICATIONS


def remaining_blockers(job: dict[str, Any], result: dict[str, Any] | None, valid: bool) -> list[str]:
    blockers: list[str] = []
    classification = str(result.get("contract_classification")) if result else "pending"
    if not result_is_trace_observed(job, result, valid):
        blockers.append("runtime_trace_proof")
    if classification in {"pending", "unresolved"}:
        blockers.append("oracle_contract_unresolved")
    if classification == "needs_followup":
        blockers.append("followup_review")
    if classification == "contradicted_plan":
        blockers.append("manual_review_before_source_promotion")
    if not job.get("first_trace_pass"):
        blockers.append("not_first_trace_pass")
    return blockers


def collect(packet: dict[str, Any]) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    status_counts: Counter[str] = Counter()
    validation_counts: Counter[str] = Counter()
    classification_counts: Counter[str] = Counter()
    priority_counts: Counter[str] = Counter()
    blocker_counts: Counter[str] = Counter()
    trace_observed_oracles: list[str] = []
    proof_grade_oracles: list[str] = []

    for job in packet.get("jobs", []):
        path = result_path(job)
        record: dict[str, Any] = {
            "job_id": job["job_id"],
            "oracle_id": job["oracle_id"],
            "priority": int(job["priority"]),
            "first_trace_pass": bool(job["first_trace_pass"]),
            "result_path": manifest_path(path),
            "result_exists": path.exists(),
            "status": "pending",
            "valid": False,
            "contract_classification": "pending",
            "errors": [],
            "remaining_blockers": [],
            "stub_result": False,
            "proof_capable": False,
            "proof_result": False,
            "trace_path_exists": False,
            "trace_path_nonempty": False,
            "promotion_allowed": False,
            "behavior_change_allowed": False,
        }
        result: dict[str, Any] | None = None
        if path.exists():
            result = load_json(path)
            errors = validate_c2_battle_trace_oracle_result.validate(result, job)
            record["status"] = str(result.get("status", "unknown"))
            record["valid"] = not errors
            record["contract_classification"] = str(result.get("contract_classification", "unknown"))
            record["errors"] = errors
            record["promotion_allowed"] = bool(result.get("promotion_allowed_by_result"))
            record["behavior_change_allowed"] = bool(result.get("behavior_change_allowed"))
            record["stub_result"] = is_stub_result(result)
            trace_path = proof_trace_path(result)
            record["trace_path_exists"] = trace_path.exists()
            record["trace_path_nonempty"] = trace_path.exists() and trace_path.stat().st_size > 0
            record["proof_capable"] = result_is_proof_capable(job, result, bool(record["valid"]))
            record["proof_result"] = result_is_proof_grade(job, result, bool(record["valid"]))
            if result_is_trace_observed(job, result, bool(record["valid"])):
                trace_observed_oracles.append(str(job["oracle_id"]))
            if result_is_proof_grade(job, result, bool(record["valid"])):
                proof_grade_oracles.append(str(job["oracle_id"]))
        record["remaining_blockers"] = remaining_blockers(job, result, bool(record["valid"]))
        for blocker in record["remaining_blockers"]:
            blocker_counts[str(blocker)] += 1
        status_counts[str(record["status"])] += 1
        validation_counts["valid" if record["valid"] else "invalid_or_pending"] += 1
        classification_counts[str(record["contract_classification"])] += 1
        priority_counts[str(record["priority"])] += 1
        records.append(record)

    proof_grade_result_count = len(proof_grade_oracles)
    return {
        "schema": "earthbound-decomp.c2-battle-trace-oracle-results-summary.v1",
        "status": "c2_battle_trace_oracle_results_collected",
        "packet": "manifests/c2-battle-trace-oracle-packet.json",
        "source_policy": packet.get("source_policy", {}),
        "summary": {
            "job_count": len(records),
            "result_count": sum(1 for record in records if record["result_exists"]),
            "valid_result_count": sum(1 for record in records if record["valid"]),
            "trace_observed_result_count": len(trace_observed_oracles),
            "proof_grade_result_count": proof_grade_result_count,
            "stub_result_count": sum(1 for record in records if record["stub_result"]),
            "proof_capable_result_count": sum(1 for record in records if record["proof_capable"]),
            "status_counts": dict(sorted(status_counts.items())),
            "validation_counts": dict(sorted(validation_counts.items())),
            "contract_classification_counts": dict(sorted(classification_counts.items())),
            "priority_counts": dict(sorted(priority_counts.items())),
            "remaining_blocker_counts": dict(sorted(blocker_counts.items())),
            "trace_observed_oracles": trace_observed_oracles,
            "proof_grade_oracles": proof_grade_oracles,
            "source_promotion_allowed": False,
            "behavior_change_allowed": False,
            "semantic_status": (
                "c2_battle_trace_outputs_pending"
                if proof_grade_result_count == 0
                else "c2_battle_trace_outputs_partially_collected"
            ),
        },
        "result_acceptance_policy": [
            "Stub unsupported/unresolved results validate runner plumbing only and never count as trace-observed evidence.",
            "A result counts as trace-observed only when it validates, is non-stub, is status ok, has a non-empty trace, matches packet job/trace paths, includes every packet capture field, and classifies the contract as confirmed_contract, refined_contract, contradicted_plan, or needs_followup.",
            "A result counts as proof-grade only when it satisfies the trace-observed gate and classifies the contract as confirmed_contract, refined_contract, or contradicted_plan.",
            "Contradicted results require manual review before any source-facing promotion.",
            "This summary cannot directly promote source names, source comments, C-port helper contracts, or behavior changes.",
        ],
        "results": records,
        "next_work": [
            "replace stub results with a real emulator or trace harness for the five first-pass jobs",
            "review proof-grade results in the owning C2 subsystem notes before touching source comments",
            "keep non-first-pass oracle jobs queued until the first-pass contracts stop moving",
        ],
    }


def render_markdown(summary: dict[str, Any]) -> str:
    stats = summary["summary"]
    rows = [
        "| `{oracle_id}` | `{priority}` | `{first}` | `{status}` | `{valid}` | `{stub}` | `{proof}` | `{classification}` | `{blockers}` | `{result_path}` |".format(
            oracle_id=record["oracle_id"],
            priority=record["priority"],
            first=record["first_trace_pass"],
            status=record["status"],
            valid=record["valid"],
            stub=record["stub_result"],
            proof=record["proof_capable"],
            classification=record["contract_classification"],
            blockers=record["remaining_blockers"],
            result_path=record["result_path"],
        )
        for record in summary["results"]
    ]
    return "\n".join(
        [
            "# C2 Battle Trace Oracle Results Summary",
            "",
            "Status: no source or behavior promotion. Local results are collected",
            "only when ignored `build/c2/battle-trace-oracles/` result files exist.",
            "",
            "## Summary",
            "",
            f"- jobs: `{stats['job_count']}`",
            f"- result files found: `{stats['result_count']}`",
            f"- valid results: `{stats['valid_result_count']}`",
            f"- trace-observed results: `{stats['trace_observed_result_count']}`",
            f"- proof-grade results: `{stats['proof_grade_result_count']}`",
            f"- stub results: `{stats['stub_result_count']}`",
            f"- proof-capable results: `{stats['proof_capable_result_count']}`",
            f"- statuses: `{stats['status_counts']}`",
            f"- validation: `{stats['validation_counts']}`",
            f"- classifications: `{stats['contract_classification_counts']}`",
            f"- remaining blockers: `{stats['remaining_blocker_counts']}`",
            f"- source promotion allowed: `{stats['source_promotion_allowed']}`",
            f"- behavior change allowed: `{stats['behavior_change_allowed']}`",
            "",
            "## Acceptance Policy",
            "",
            *[f"- {item}" for item in summary["result_acceptance_policy"]],
            "",
            "## Results",
            "",
            "| Oracle | Priority | First pass | Status | Valid | Stub | Proof capable | Classification | Remaining blockers | Result path |",
            "| --- | ---: | --- | --- | --- | --- | --- | --- | --- | --- |",
            *rows,
            "",
            "## Next Work",
            "",
            *[f"- {item}" for item in summary["next_work"]],
            "",
        ]
    )


def main() -> int:
    args = parse_args()
    summary = collect(load_json(Path(args.packet)))
    output = Path(args.output)
    notes = Path(args.notes)
    output.parent.mkdir(parents=True, exist_ok=True)
    notes.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    notes.write_text(render_markdown(summary), encoding="utf-8")
    print(
        "Collected C2 battle trace-oracle results: "
        f"{summary['summary']['result_count']} / {summary['summary']['job_count']} result files, "
        f"proof-grade {summary['summary']['proof_grade_result_count']}"
    )
    print(f"Wrote {output}")
    print(f"Wrote {notes}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
