#!/usr/bin/env python3
"""Validate the C2 battle trace-oracle execution packet."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PACKET = ROOT / "manifests" / "c2-battle-trace-oracle-packet.json"
OUTPUT_ROOT = "build/c2/battle-trace-oracles"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate the C2 battle trace-oracle packet.")
    parser.add_argument("packet", nargs="?", default=str(DEFAULT_PACKET))
    return parser.parse_args()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def require_paths(paths: list[str], *, label: str, owner: str) -> None:
    for path_text in paths:
        require((ROOT / path_text).exists(), f"{owner}: missing {label} path {path_text}")


def validate_output_paths(job: dict[str, Any]) -> None:
    oracle_id = str(job.get("oracle_id", ""))
    paths = job.get("output_paths", {})
    expected_root = f"{OUTPUT_ROOT}/{oracle_id}"
    require(paths.get("output_dir") == expected_root, f"{oracle_id}: unexpected output dir")
    expected_suffixes = {
        "job_path": "job.json",
        "raw_trace_path": "raw-trace.jsonl",
        "result_path": "result.json",
        "evidence_markdown_path": "evidence.md",
    }
    for key, suffix in expected_suffixes.items():
        value = str(paths.get(key, "")).replace("\\", "/")
        require(value == f"{expected_root}/{suffix}", f"{oracle_id}: unexpected {key} {value}")


def validate_job(job: dict[str, Any]) -> None:
    oracle_id = str(job.get("oracle_id", ""))
    require(str(job.get("job_id")) == f"c2-battle-oracle-{oracle_id}", f"{oracle_id}: job id mismatch")
    require(int(job.get("execution_order", 0)) > 0, f"{oracle_id}: missing execution order")
    require(int(job.get("priority", 0)) in {1, 2, 3}, f"{oracle_id}: invalid priority")
    require(job.get("status") == "trace_plan_ready", f"{oracle_id}: unexpected status")
    require(isinstance(job.get("first_trace_pass"), bool), f"{oracle_id}: first_trace_pass must be bool")
    require(job.get("promotion_allowed_by_plan") is False, f"{oracle_id}: promotion must be blocked")
    require(job.get("behavior_change_allowed") is False, f"{oracle_id}: behavior changes must be blocked")
    require(len(job.get("addresses", [])) >= 2, f"{oracle_id}: missing address anchors")
    address_set = {str(address) for address in job.get("addresses", [])}
    route_groups = job.get("route_groups", {})
    require(isinstance(route_groups, dict), f"{oracle_id}: route_groups must be an object")
    for group_id, group in route_groups.items():
        require(isinstance(group, dict), f"{oracle_id}: route group {group_id} must be an object")
        group_addresses = [str(address) for address in group.get("addresses", [])]
        require(group_addresses, f"{oracle_id}: route group {group_id} missing addresses")
        require(set(group_addresses).issubset(address_set), f"{oracle_id}: route group {group_id} has non-oracle addresses")
        require(str(group.get("role", "")), f"{oracle_id}: route group {group_id} missing role")
        require(str(group.get("status", "")), f"{oracle_id}: route group {group_id} missing status")
    require(len(job.get("capture_fields", [])) >= 12, f"{oracle_id}: capture fields too thin")
    require_paths(job.get("evidence_notes", []), label="evidence note", owner=oracle_id)
    require_paths(job.get("source_paths", []), label="source", owner=oracle_id)
    require(len(job.get("acceptance_criteria", [])) >= 2, f"{oracle_id}: acceptance criteria too thin")
    validate_output_paths(job)
    commands = job.get("commands", {})
    require("dry-run-stub" in str(commands.get("dry_run_stub", "")), f"{oracle_id}: missing dry run command")
    require("{job}" in str(commands.get("external_run", "")), f"{oracle_id}: external command must expose job placeholder")
    require(str(commands.get("validate_result", "")).endswith("result.json"), f"{oracle_id}: missing result validation command")


def validate(data: dict[str, Any]) -> None:
    require(data.get("schema") == "earthbound-decomp.c2-battle-trace-oracle-packet.v1", "unexpected schema")
    require(
        data.get("status") == "c2_battle_trace_oracle_packet_ready_external_harness_required",
        f"unexpected status {data.get('status')}",
    )
    require(data.get("source_plan") == "manifests/c2-battle-trace-oracle-plan.json", "unexpected source plan")
    require_paths(data.get("references", []), label="reference", owner="packet")
    policy = data.get("source_policy", {})
    require(policy.get("requires_user_supplied_rom") is True, "packet must require user ROM")
    require(policy.get("generated_probe_outputs_are_ignored") is True, "probe outputs must be ignored")
    require(policy.get("generated_outputs_root") == OUTPUT_ROOT, "unexpected output root")
    require(policy.get("source_edits_allowed_from_packet_alone") is False, "packet cannot allow source edits")
    require("hint" in str(policy.get("ghidra_role", "")), "Ghidra role must remain hint-only")

    jobs = data.get("jobs", [])
    summary = data.get("summary", {})
    require(int(summary.get("job_count", -1)) == len(jobs), "job count mismatch")
    require(int(summary.get("first_trace_job_count", -1)) == sum(1 for job in jobs if job.get("first_trace_pass")), "first trace count mismatch")
    require(summary.get("promotion_allowed_by_packet") is False, "packet must block promotion")
    require(summary.get("behavior_change_allowed") is False, "packet must block behavior changes")
    priority_counts = dict(sorted(Counter(str(job.get("priority")) for job in jobs).items()))
    require(summary.get("priority_counts") == priority_counts, "priority counts mismatch")

    seen_job_ids: set[str] = set()
    seen_oracle_ids: set[str] = set()
    orders: list[int] = []
    for job in jobs:
        validate_job(job)
        job_id = str(job.get("job_id"))
        oracle_id = str(job.get("oracle_id"))
        require(job_id not in seen_job_ids, f"duplicate job id {job_id}")
        require(oracle_id not in seen_oracle_ids, f"duplicate oracle id {oracle_id}")
        seen_job_ids.add(job_id)
        seen_oracle_ids.add(oracle_id)
        orders.append(int(job["execution_order"]))
    require(orders == list(range(1, len(jobs) + 1)), "execution orders must be contiguous")
    require(data.get("runner_contract"), "missing runner contract")
    require(data.get("packet_policy"), "missing packet policy")
    require(data.get("post_packet_validation_commands"), "missing validation commands")


def main() -> int:
    args = parse_args()
    data = json.loads(Path(args.packet).read_text(encoding="utf-8"))
    validate(data)
    print(f"C2 battle trace oracle packet validation OK: {data['summary']['job_count']} jobs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
