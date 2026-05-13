#!/usr/bin/env python3
"""Validate collected C2 battle trace-oracle result status."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SUMMARY = ROOT / "manifests" / "c2-battle-trace-oracle-results-summary.json"
OUTPUT_ROOT = "build/c2/battle-trace-oracles"

ALLOWED_STATUS = {"pending", "ok", "failed", "unsupported", "unresolved", "unknown"}
ALLOWED_CLASSIFICATIONS = {
    "pending",
    "confirmed_contract",
    "refined_contract",
    "contradicted_plan",
    "unreachable_from_source_state",
    "needs_followup",
    "unresolved",
    "unknown",
}
ALLOWED_BLOCKERS = {
    "runtime_trace_proof",
    "oracle_contract_unresolved",
    "followup_review",
    "manual_review_before_source_promotion",
    "not_first_trace_pass",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate C2 battle trace-oracle results summary.")
    parser.add_argument("summary", nargs="?", default=str(DEFAULT_SUMMARY))
    return parser.parse_args()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def count_records(records: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for record in records:
        counts[str(record.get(key))] += 1
    return dict(sorted(counts.items()))


def blocker_counts(records: list[dict[str, Any]]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for record in records:
        for blocker in record.get("remaining_blockers", []):
            counts[str(blocker)] += 1
    return dict(sorted(counts.items()))


def trace_observed_oracles(records: list[dict[str, Any]]) -> list[str]:
    return [str(record.get("oracle_id")) for record in records if record.get("proof_capable")]


def proof_grade_oracles(records: list[dict[str, Any]]) -> list[str]:
    return [str(record.get("oracle_id")) for record in records if record.get("proof_result")]


def validate(data: dict[str, Any]) -> None:
    require(
        data.get("schema") == "earthbound-decomp.c2-battle-trace-oracle-results-summary.v1",
        "unexpected schema",
    )
    require(data.get("status") == "c2_battle_trace_oracle_results_collected", f"unexpected status {data.get('status')}")
    require(data.get("packet") == "manifests/c2-battle-trace-oracle-packet.json", "unexpected packet")
    policy = data.get("source_policy", {})
    require(policy.get("requires_user_supplied_rom") is True, "source policy must require user ROM")
    require(policy.get("generated_probe_outputs_are_ignored") is True, "probe outputs must be ignored")
    require(policy.get("generated_outputs_root") == OUTPUT_ROOT, "unexpected generated outputs root")
    require(policy.get("source_edits_allowed_from_packet_alone") is False, "packet cannot allow source edits")

    records = data.get("results", [])
    summary = data.get("summary", {})
    require(int(summary.get("job_count", -1)) == len(records), "job count mismatch")
    require(int(summary.get("result_count", -1)) == sum(1 for record in records if record.get("result_exists")), "result count mismatch")
    require(int(summary.get("valid_result_count", -1)) == sum(1 for record in records if record.get("valid")), "valid result count mismatch")
    require(
        int(summary.get("trace_observed_result_count", -1)) == len(trace_observed_oracles(records)),
        "trace-observed count mismatch",
    )
    require(
        int(summary.get("proof_grade_result_count", -1)) == len(proof_grade_oracles(records)),
        "proof-grade count mismatch",
    )
    require(int(summary.get("stub_result_count", -1)) == sum(1 for record in records if record.get("stub_result")), "stub count mismatch")
    require(
        int(summary.get("proof_capable_result_count", -1)) == sum(1 for record in records if record.get("proof_capable")),
        "proof-capable count mismatch",
    )
    require(summary.get("status_counts") == count_records(records, "status"), "status counts mismatch")
    validation_counts: Counter[str] = Counter("valid" if record.get("valid") else "invalid_or_pending" for record in records)
    require(summary.get("validation_counts") == dict(sorted(validation_counts.items())), "validation counts mismatch")
    require(
        summary.get("contract_classification_counts") == count_records(records, "contract_classification"),
        "classification counts mismatch",
    )
    require(summary.get("priority_counts") == count_records(records, "priority"), "priority counts mismatch")
    require(summary.get("remaining_blocker_counts") == blocker_counts(records), "remaining blocker counts mismatch")
    require(summary.get("trace_observed_oracles") == trace_observed_oracles(records), "trace observed oracle list mismatch")
    require(summary.get("proof_grade_oracles") == proof_grade_oracles(records), "proof-grade oracle list mismatch")
    require(summary.get("source_promotion_allowed") is False, "summary must block source promotion")
    require(summary.get("behavior_change_allowed") is False, "summary must block behavior changes")

    seen_job_ids: set[str] = set()
    seen_oracle_ids: set[str] = set()
    for record in records:
        job_id = str(record.get("job_id", ""))
        oracle_id = str(record.get("oracle_id", ""))
        require(job_id == f"c2-battle-oracle-{oracle_id}", f"{oracle_id}: job id mismatch")
        require(job_id not in seen_job_ids, f"duplicate job id {job_id}")
        require(oracle_id not in seen_oracle_ids, f"duplicate oracle id {oracle_id}")
        seen_job_ids.add(job_id)
        seen_oracle_ids.add(oracle_id)
        require(int(record.get("priority", 0)) in {1, 2, 3}, f"{oracle_id}: invalid priority")
        require(str(record.get("status")) in ALLOWED_STATUS, f"{oracle_id}: unexpected status")
        require(str(record.get("contract_classification")) in ALLOWED_CLASSIFICATIONS, f"{oracle_id}: unexpected classification")
        require(record.get("promotion_allowed") is False, f"{oracle_id}: promotion must remain blocked")
        require(record.get("behavior_change_allowed") is False, f"{oracle_id}: behavior change must remain blocked")
        require(isinstance(record.get("stub_result"), bool), f"{oracle_id}: stub_result must be bool")
        require(isinstance(record.get("proof_capable"), bool), f"{oracle_id}: proof_capable must be bool")
        require(isinstance(record.get("proof_result"), bool), f"{oracle_id}: proof_result must be bool")
        require(isinstance(record.get("trace_path_exists"), bool), f"{oracle_id}: trace_path_exists must be bool")
        require(isinstance(record.get("trace_path_nonempty"), bool), f"{oracle_id}: trace_path_nonempty must be bool")
        if record.get("stub_result"):
            require(record.get("status") != "ok", f"{oracle_id}: stub result cannot be ok")
            require(record.get("contract_classification") == "unresolved", f"{oracle_id}: stub result must be unresolved")
            require(record.get("proof_capable") is False, f"{oracle_id}: stub result cannot be proof-capable")
            require(record.get("proof_result") is False, f"{oracle_id}: stub result cannot be proof-grade")
            require("runtime_trace_proof" in record.get("remaining_blockers", []), f"{oracle_id}: stub result must retain runtime trace blocker")
        if record.get("proof_result"):
            require(record.get("proof_capable") is True, f"{oracle_id}: proof result must be proof-capable")
        path_text = str(record.get("result_path", "")).replace("\\", "/")
        require(
            path_text == f"{OUTPUT_ROOT}/{oracle_id}/result.json",
            f"{oracle_id}: unexpected result path {path_text}",
        )
        for blocker in record.get("remaining_blockers", []):
            require(str(blocker) in ALLOWED_BLOCKERS, f"{oracle_id}: unexpected blocker {blocker}")
        if record.get("result_exists"):
            require(record.get("status") != "pending", f"{oracle_id}: existing result cannot be pending")
        else:
            require(record.get("status") == "pending", f"{oracle_id}: missing result must be pending")
            require(record.get("contract_classification") == "pending", f"{oracle_id}: missing result classification must be pending")

    require(data.get("result_acceptance_policy"), "missing acceptance policy")
    require(data.get("next_work"), "missing next work")


def main() -> int:
    args = parse_args()
    data = json.loads(Path(args.summary).read_text(encoding="utf-8"))
    validate(data)
    print(
        "C2 battle trace oracle results summary validation OK: "
        f"{data['summary']['result_count']} / {data['summary']['job_count']} results, "
        f"proof-grade {data['summary']['proof_grade_result_count']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
