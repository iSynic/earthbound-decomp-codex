#!/usr/bin/env python3
"""Validate ignored Mesen runner assets for C2 battle trace oracles."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INDEX = ROOT / "build" / "c2" / "battle-trace-oracles" / "mesen-runner-assets" / "index.json"
DEFAULT_HANDOFF = ROOT / "manifests" / "c2-battle-trace-oracle-emulator-handoff.json"
REQUIRED_FIRST_PASS_IDS = {
    "c1_c2_target_action_staging",
    "c2_40a4_current_action_payload",
    "c2_724a_affliction_writer_matrix",
    "c2_8125_damage_abi_boundary",
    "hp_roller_collapse_boundary",
    "resource_amount_pair_magnet_vs_pp_loss",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate C2 oracle Mesen runner assets.")
    parser.add_argument("index", nargs="?", default=str(DEFAULT_INDEX), help="Runner asset index JSON.")
    parser.add_argument("--handoff", default=str(DEFAULT_HANDOFF), help="C2 battle trace-oracle handoff JSON.")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def repo_path(path_text: str) -> Path:
    path = Path(path_text)
    return path if path.is_absolute() else ROOT / path


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def require_existing_file(path_text: str, *, label: str) -> Path:
    path = repo_path(path_text)
    require(path.exists(), f"missing {label}: {path_text}")
    require(path.is_file(), f"{label} is not a file: {path_text}")
    return path


def require_under_build(path_text: str) -> None:
    path = repo_path(path_text).resolve()
    build_root = (ROOT / "build" / "c2" / "battle-trace-oracles").resolve()
    require(str(path).startswith(str(build_root)), f"path is not under ignored C2 build output: {path_text}")


def expected_route_gap_probe_breakpoints(handoff_job: dict[str, Any]) -> list[dict[str, Any]]:
    base_addresses = {str(record.get("address")) for record in handoff_job.get("breakpoints", [])}
    records: list[dict[str, Any]] = []
    seen: set[str] = set()
    for group_id, group in handoff_job.get("route_groups", {}).items():
        for address in group.get("probe_breakpoint_hints", []):
            address_text = str(address)
            if address_text in base_addresses or address_text in seen:
                continue
            seen.add(address_text)
            records.append(
                {
                    "address": address_text,
                    "address_space": "snes_cpu_bus",
                    "hit_policy": "capture_registers_dp_wram_then_continue",
                    "required_for_minimum_capture": False,
                    "probe_source": "route_group_hint",
                    "route_group": str(group_id),
                    "route_group_status": str(group.get("status", "")),
                }
            )
    return records


def validate_result_template(path_text: str, job: dict[str, Any]) -> None:
    data = load_json(require_existing_file(path_text, label="result template"))
    require(data.get("schema") == "earthbound-decomp.c2-battle-trace-oracle-result.v1", "bad result template schema")
    require(data.get("job_id") == job["job_id"], f"{job['oracle_id']}: result template job mismatch")
    require(data.get("oracle_id") == job["oracle_id"], f"{job['oracle_id']}: result template oracle mismatch")
    require(data.get("status") == "unresolved", f"{job['oracle_id']}: template must stay unresolved")
    require(data.get("contract_classification") == "unresolved", f"{job['oracle_id']}: template classification must stay unresolved")
    require(data.get("observed_addresses") == [], f"{job['oracle_id']}: template cannot claim observed addresses")
    require(data.get("captured_fields") == {}, f"{job['oracle_id']}: template cannot claim captured fields")
    require(data.get("promotion_allowed_by_result") is False, f"{job['oracle_id']}: template cannot allow promotion")
    require(data.get("behavior_change_allowed") is False, f"{job['oracle_id']}: template cannot allow behavior changes")
    evidence = data.get("evidence", {})
    require(evidence.get("trace_path") == job["target_raw_trace_path"], f"{job['oracle_id']}: template trace path mismatch")
    require(evidence.get("job_path"), f"{job['oracle_id']}: template missing job path")


def validate_runner_job(path_text: str, index_job: dict[str, Any], handoff_job: dict[str, Any]) -> None:
    data = load_json(require_existing_file(path_text, label="runner job"))
    oracle_id = handoff_job["oracle_id"]
    require(data.get("schema") == "earthbound-decomp.c2-battle-trace-oracle-runner-job.v1", f"{oracle_id}: bad runner job schema")
    require(data.get("status") == "runner_asset_generated_no_execution", f"{oracle_id}: bad runner job status")
    require(data.get("job_id") == handoff_job["job_id"], f"{oracle_id}: runner job id mismatch")
    require(data.get("oracle_id") == oracle_id, f"{oracle_id}: runner oracle mismatch")
    require(data.get("minimum_hits") == handoff_job["minimum_hits"], f"{oracle_id}: minimum hits mismatch")
    require(data.get("route_groups", {}) == handoff_job.get("route_groups", {}), f"{oracle_id}: route groups mismatch")
    require(data.get("route_gap_probe_breakpoints", []) == expected_route_gap_probe_breakpoints(handoff_job), f"{oracle_id}: route gap probe breakpoints mismatch")
    require(data.get("breakpoints") == handoff_job["breakpoints"], f"{oracle_id}: breakpoints mismatch")
    require(data.get("capture_fields") == handoff_job["capture_fields"], f"{oracle_id}: capture fields mismatch")
    require(data.get("output_paths") == handoff_job["output_paths"], f"{oracle_id}: output paths mismatch")
    proof_gate = data.get("proof_gate", {})
    require(proof_gate.get("source_promotion_allowed") is False, f"{oracle_id}: runner job cannot allow source promotion")
    require(proof_gate.get("behavior_change_allowed") is False, f"{oracle_id}: runner job cannot allow behavior changes")
    assets = data.get("assets", {})
    for key in ("mesen_lua_skeleton", "operator_checklist", "result_template"):
        require(assets.get(key) == index_job[key], f"{oracle_id}: {key} does not match index")
        require_under_build(str(assets.get(key)))
    commands = data.get("commands", {})
    require("Mesen.exe" in str(commands.get("mesen_test_runner_template", "")), f"{oracle_id}: missing Mesen command")
    require("--testRunner" in str(commands.get("mesen_test_runner_template", "")), f"{oracle_id}: missing testRunner flag")
    require("run_c2_battle_trace_oracle_mesen.py" in str(commands.get("mesen_wrapper_dry_run", "")), f"{oracle_id}: missing Mesen wrapper dry-run command")
    require("run_c2_battle_trace_oracle_mesen.py" in str(commands.get("mesen_wrapper_trace_run", "")), f"{oracle_id}: missing Mesen wrapper trace-run command")
    require("run_c2_battle_trace_oracle_batch.py" in str(commands.get("external_batch_template", "")), f"{oracle_id}: missing external batch command")
    require("build_c2_battle_trace_oracle_result_from_evidence.py" in str(commands.get("reviewed_result_template", "")), f"{oracle_id}: missing reviewed result command")
    require("validate_c2_battle_trace_oracle_result.py" in str(commands.get("validate_result", "")), f"{oracle_id}: missing validator command")


def validate_lua(path_text: str, oracle_id: str, minimum_hits: list[str], route_gap_breakpoints: list[dict[str, Any]]) -> None:
    path = require_existing_file(path_text, label="Lua skeleton")
    text = path.read_text(encoding="utf-8")
    require("emu.addMemoryCallback" in text, f"{oracle_id}: Lua skeleton missing memory callback")
    require("emu.addEventCallback" in text, f"{oracle_id}: Lua skeleton missing event callback")
    require("C2_ORACLE_TRACE_OUT" in text, f"{oracle_id}: Lua skeleton missing trace env")
    require("C2_ORACLE_INPUT_PATTERN" in text, f"{oracle_id}: Lua skeleton missing input pattern env")
    require("runner_start" in text and "breakpoint_hit" in text and "summary" in text, f"{oracle_id}: Lua skeleton missing trace events")
    for address in minimum_hits:
        require(address in text, f"{oracle_id}: Lua skeleton missing minimum hit {address}")
    for record in route_gap_breakpoints:
        address = str(record["address"])
        require(address in text, f"{oracle_id}: Lua skeleton missing route-gap probe address {address}")
    if route_gap_breakpoints:
        require("route_group_hint" in text, f"{oracle_id}: Lua skeleton missing route-group hint marker")


def validate_index(index: dict[str, Any], handoff: dict[str, Any]) -> None:
    require(index.get("schema") == "earthbound-decomp.c2-battle-trace-oracle-runner-assets.v1", "bad index schema")
    require(index.get("status") == "runner_assets_generated_no_execution", "bad index status")
    require(index.get("handoff") == "manifests/c2-battle-trace-oracle-emulator-handoff.json", "unexpected handoff")
    output_root = str(index.get("output_root", ""))
    require(output_root == "build/c2/battle-trace-oracles/mesen-runner-assets", f"bad output root {output_root}")
    require_under_build(output_root)
    policy = index.get("source_policy", {})
    require(policy.get("generated_assets_are_ignored") is True, "assets must be ignored")
    require(policy.get("requires_user_supplied_rom") is True, "ROM policy missing")
    require(policy.get("requires_local_save_states") is True, "save-state policy missing")
    require(policy.get("source_promotion_allowed") is False, "index cannot allow source promotion")
    require(policy.get("behavior_change_allowed") is False, "index cannot allow behavior changes")
    require(policy.get("lua_skeletons_are_proof") is False, "Lua skeletons cannot be proof")
    jobs = index.get("jobs", [])
    summary = index.get("summary", {})
    require(len(jobs) == len(REQUIRED_FIRST_PASS_IDS), "runner asset job count mismatch")
    ids = {str(job.get("oracle_id")) for job in jobs}
    require(ids == REQUIRED_FIRST_PASS_IDS, f"first-pass id mismatch: {sorted(ids ^ REQUIRED_FIRST_PASS_IDS)}")
    require(summary.get("job_count") == len(jobs), "summary job count mismatch")
    require(summary.get("proof_grade_result_count") == 0, "runner assets cannot claim proof-grade results")
    require(summary.get("source_promotion_allowed") is False, "summary cannot allow promotion")
    require(summary.get("behavior_change_allowed") is False, "summary cannot allow behavior changes")

    handoff_by_id = {str(job["oracle_id"]): job for job in handoff.get("jobs", [])}
    for job in jobs:
        oracle_id = str(job["oracle_id"])
        handoff_job = handoff_by_id.get(oracle_id)
        require(handoff_job is not None, f"{oracle_id}: missing matching handoff job")
        require(job.get("job_id") == handoff_job["job_id"], f"{oracle_id}: job id mismatch")
        require(job.get("target_raw_trace_path") == handoff_job["output_paths"]["raw_trace_path"], f"{oracle_id}: raw trace path mismatch")
        require(job.get("target_result_path") == handoff_job["output_paths"]["result_path"], f"{oracle_id}: result path mismatch")
        require(job.get("minimum_hits") == handoff_job["minimum_hits"], f"{oracle_id}: minimum hits mismatch")
        require(job.get("route_groups", {}) == handoff_job.get("route_groups", {}), f"{oracle_id}: route groups mismatch")
        expected_gap_bps = expected_route_gap_probe_breakpoints(handoff_job)
        require(job.get("route_gap_probe_breakpoints", []) == expected_gap_bps, f"{oracle_id}: route gap probe breakpoints mismatch")
        require(job.get("capture_field_count") == len(handoff_job["capture_fields"]), f"{oracle_id}: capture count mismatch")
        for key in ("runner_job", "mesen_lua_skeleton", "operator_checklist", "result_template"):
            require_existing_file(str(job.get(key)), label=f"{oracle_id} {key}")
            require_under_build(str(job.get(key)))
        validate_lua(str(job["mesen_lua_skeleton"]), oracle_id, handoff_job["minimum_hits"], expected_gap_bps)
        validate_result_template(str(job["result_template"]), job)
        validate_runner_job(str(job["runner_job"]), job, handoff_job)

    assets = index.get("assets", {})
    for key in ("readme", "commands"):
        require_existing_file(str(assets.get(key)), label=key)
        require_under_build(str(assets.get(key)))
    require(index.get("validation_commands"), "missing validation commands")


def main() -> int:
    args = parse_args()
    index = load_json(Path(args.index))
    handoff = load_json(Path(args.handoff))
    validate_index(index, handoff)
    print(f"C2 battle trace oracle runner assets validation OK: {index['summary']['job_count']} jobs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
