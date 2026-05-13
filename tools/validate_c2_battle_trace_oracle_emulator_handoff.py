#!/usr/bin/env python3
"""Validate the C2 battle trace-oracle emulator handoff."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_HANDOFF = ROOT / "manifests" / "c2-battle-trace-oracle-emulator-handoff.json"
OUTPUT_ROOT = "build/c2/battle-trace-oracles"
REQUIRED_FIRST_PASS_IDS = {
    "c1_c2_target_action_staging",
    "c2_40a4_current_action_payload",
    "c2_724a_affliction_writer_matrix",
    "c2_8125_damage_abi_boundary",
    "hp_roller_collapse_boundary",
    "resource_amount_pair_magnet_vs_pp_loss",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate C2 battle trace-oracle emulator handoff.")
    parser.add_argument("handoff", nargs="?", default=str(DEFAULT_HANDOFF))
    return parser.parse_args()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def require_paths(paths: list[str], *, label: str) -> None:
    for path_text in paths:
        require((ROOT / path_text).exists(), f"missing {label} path {path_text}")


def validate_job(job: dict[str, Any]) -> None:
    oracle_id = str(job.get("oracle_id", ""))
    require(oracle_id in REQUIRED_FIRST_PASS_IDS, f"unexpected oracle id {oracle_id}")
    require(str(job.get("job_id")) == f"c2-battle-oracle-{oracle_id}", f"{oracle_id}: job id mismatch")
    require(int(job.get("priority", 0)) in {1, 2}, f"{oracle_id}: invalid priority")
    require(job.get("scenario_goal"), f"{oracle_id}: missing scenario goal")
    scenario = job.get("scenario", {})
    require(str(scenario.get("scenario_name", "")).startswith(oracle_id), f"{oracle_id}: bad scenario name")
    require(scenario.get("save_state_id") == "local_fixture_required", f"{oracle_id}: bad save state id")
    require(scenario.get("save_state_path_local_only"), f"{oracle_id}: missing local save state path")
    require(len(scenario.get("setup_steps", [])) >= 2, f"{oracle_id}: setup steps too thin")
    require("minimum breakpoint hits" in str(scenario.get("stop_condition", "")), f"{oracle_id}: missing stop condition")
    require(len(job.get("manual_setup", [])) >= 2, f"{oracle_id}: manual setup too thin")
    require(job.get("preferred_trigger"), f"{oracle_id}: missing preferred trigger")
    minimum_hits = job.get("minimum_hits", [])
    breakpoints = job.get("breakpoints", [])
    capture_fields = job.get("capture_fields", [])
    require(minimum_hits, f"{oracle_id}: missing minimum hits")
    require(breakpoints, f"{oracle_id}: missing breakpoints")
    require(capture_fields, f"{oracle_id}: missing capture fields")
    breakpoint_addresses = {str(record.get("address")) for record in breakpoints}
    require(set(minimum_hits).issubset(breakpoint_addresses), f"{oracle_id}: minimum hits must be breakpoints")
    require("trace_id" in capture_fields and "classification_evidence" in capture_fields, f"{oracle_id}: missing proof capture core")
    route_groups = job.get("route_groups", {})
    require(isinstance(route_groups, dict), f"{oracle_id}: route_groups must be object")
    for group_id, group in route_groups.items():
        require(isinstance(group, dict), f"{oracle_id}/{group_id}: route group must be object")
        addresses = group.get("addresses", [])
        require(isinstance(addresses, list) and addresses, f"{oracle_id}/{group_id}: missing route group addresses")
        require(set(addresses).issubset(breakpoint_addresses), f"{oracle_id}/{group_id}: route group address must be breakpoint")
        require(group.get("role"), f"{oracle_id}/{group_id}: missing route group role")
        require(group.get("status"), f"{oracle_id}/{group_id}: missing route group status")
    require(job.get("extra_trace_fields"), f"{oracle_id}: missing extra trace fields")
    require(job.get("watch_ranges"), f"{oracle_id}: missing watch ranges")
    for watch in job.get("watch_ranges", []):
        require(watch.get("id"), f"{oracle_id}: watch range missing id")
        require(watch.get("address_or_symbol"), f"{oracle_id}: watch range missing address")
        require(int(watch.get("bytes", 0)) > 0, f"{oracle_id}: watch range bytes invalid")
        require(watch.get("purpose"), f"{oracle_id}: watch range missing purpose")
    paths = job.get("output_paths", {})
    for key, suffix in {
        "job_path": "job.json",
        "raw_trace_path": "raw-trace.jsonl",
        "result_path": "result.json",
        "evidence_markdown_path": "evidence.md",
    }.items():
        value = str(paths.get(key, "")).replace("\\", "/")
        require(value == f"{OUTPUT_ROOT}/{oracle_id}/{suffix}", f"{oracle_id}: unexpected {key} {value}")
    require(str(job.get("result_validator", "")).endswith(f"{oracle_id}/result.json"), f"{oracle_id}: bad result validator")
    require("collect_c2_battle_trace_oracle_results.py" in str(job.get("result_collector", "")), f"{oracle_id}: bad collector")
    proof_gate = job.get("proof_gate", {})
    require(proof_gate.get("required_status") == "ok", f"{oracle_id}: proof gate must require ok")
    require("every packet job capture field" in str(proof_gate.get("required_capture_coverage", "")), f"{oracle_id}: proof gate must require all captures")
    require(proof_gate.get("stub_results_are_proof") is False, f"{oracle_id}: stubs cannot prove")
    require(proof_gate.get("source_promotion_allowed") is False, f"{oracle_id}: proof gate cannot allow source promotion")
    for record in breakpoints:
        address = str(record.get("address", ""))
        require(address.startswith(("C0:", "C1:", "C2:", "C3:", "C4:", "EF:")), f"{oracle_id}: bad breakpoint {address}")
        require(record.get("address_space") == "snes_cpu_bus", f"{oracle_id}: bad address space")
        require(record.get("hit_policy") == "capture_registers_dp_wram_then_continue", f"{oracle_id}: bad hit policy")
        require(isinstance(record.get("required_for_minimum_capture"), bool), f"{oracle_id}: minimum flag must be bool")


def validate(data: dict[str, Any]) -> None:
    require(
        data.get("schema") == "earthbound-decomp.c2-battle-trace-oracle-emulator-handoff.v1",
        "unexpected schema",
    )
    require(
        data.get("status") == "c2_battle_trace_oracle_emulator_handoff_ready_runner_pending",
        f"unexpected status {data.get('status')}",
    )
    require(data.get("packet") == "manifests/c2-battle-trace-oracle-packet.json", "unexpected packet")
    require_paths(data.get("references", []), label="reference")
    emulator_policy = data.get("emulator_policy", {})
    require("mesen2_test_runner" in emulator_policy.get("accepted_runner_classes", []), "missing Mesen runner class")
    require(emulator_policy.get("output_root") == OUTPUT_ROOT, "unexpected output root")
    require("emu.convertAddress" in str(emulator_policy.get("mesen_address_policy", "")), "missing Mesen address caveat")
    proof_policy = data.get("proof_policy", {})
    require(proof_policy.get("stub_results_are_not_proof") is True, "stub proof policy missing")
    require(proof_policy.get("source_edits_allowed_from_handoff_alone") is False, "handoff cannot allow source edits")
    require(proof_policy.get("behavior_change_allowed_from_handoff_alone") is False, "handoff cannot allow behavior changes")

    jobs = data.get("jobs", [])
    summary = data.get("summary", {})
    require(len(jobs) == len(REQUIRED_FIRST_PASS_IDS), "handoff job count mismatch")
    ids = {str(job.get("oracle_id")) for job in jobs}
    require(ids == REQUIRED_FIRST_PASS_IDS, f"first-pass id mismatch: {sorted(ids ^ REQUIRED_FIRST_PASS_IDS)}")
    require(int(summary.get("handoff_job_count", -1)) == len(jobs), "summary job count mismatch")
    require(int(summary.get("breakpoint_count", -1)) == sum(len(job.get("breakpoints", [])) for job in jobs), "breakpoint count mismatch")
    require(int(summary.get("minimum_breakpoint_count", -1)) == sum(len(job.get("minimum_hits", [])) for job in jobs), "minimum count mismatch")
    require(summary.get("source_promotion_allowed") is False, "summary cannot allow source promotion")
    require(summary.get("behavior_change_allowed") is False, "summary cannot allow behavior changes")
    for job in jobs:
        validate_job(job)
    contract = data.get("runner_result_contract", {})
    require(contract.get("required_status_for_proof") == "ok", "runner contract must require ok")
    require("every capture field" in str(contract.get("required_capture_coverage", "")), "runner contract must require all capture fields")
    commands = data.get("validation_commands", [])
    require(commands, "missing validation commands")
    require(
        any("build_c2_battle_trace_oracle_runner_assets.py" in str(command) for command in commands),
        "missing runner asset builder validation command",
    )
    require(
        any("validate_c2_battle_trace_oracle_runner_assets.py" in str(command) for command in commands),
        "missing runner asset validator command",
    )


def main() -> int:
    args = parse_args()
    data = json.loads(Path(args.handoff).read_text(encoding="utf-8"))
    validate(data)
    print(f"C2 battle trace oracle emulator handoff validation OK: {data['summary']['handoff_job_count']} jobs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
