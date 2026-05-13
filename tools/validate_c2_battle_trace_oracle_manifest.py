#!/usr/bin/env python3
"""Validate the C2 battle trace-oracle manifest."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MANIFEST = ROOT / "manifests" / "c2-battle-trace-oracle-plan.json"

REQUIRED_COMMON_FIELDS = {
    "trace_id",
    "scenario_name",
    "rom_sha1",
    "pc",
    "routine_label",
    "classification",
    "classification_evidence",
}
REQUIRED_ORACLE_IDS = {
    "c1_c2_target_action_staging",
    "c2_40a4_current_action_payload",
    "c2_724a_affliction_writer_matrix",
    "c2_8125_damage_abi_boundary",
    "hp_roller_collapse_boundary",
    "resource_amount_pair_magnet_vs_pp_loss",
    "healing_ladder_gamma_omega",
    "numeric_stat_edge_behavior",
    "psi_flash_and_status_gate_family",
    "battle_text_payload_join",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate the C2 battle trace-oracle manifest.")
    parser.add_argument("manifest", nargs="?", default=str(DEFAULT_MANIFEST))
    return parser.parse_args()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def require_existing_paths(paths: list[str], *, label: str, oracle_id: str) -> None:
    for path_text in paths:
        path = ROOT / path_text
        require(path.exists(), f"{oracle_id}: missing {label} path {path_text}")


def validate_oracle(oracle: dict[str, Any]) -> None:
    oracle_id = str(oracle.get("id", ""))
    require(oracle_id in REQUIRED_ORACLE_IDS, f"unexpected oracle id {oracle_id}")
    require(int(oracle.get("priority", 0)) in {1, 2, 3}, f"{oracle_id}: invalid priority")
    require(oracle.get("status") == "trace_plan_ready", f"{oracle_id}: unexpected status")
    require(oracle.get("promotion_allowed_by_plan") is False, f"{oracle_id}: promotion must be blocked")
    require(
        oracle.get("evidence_class") == "trace_required_before_source_promotion",
        f"{oracle_id}: unexpected evidence class",
    )
    require(oracle.get("question"), f"{oracle_id}: missing question")
    require(len(oracle.get("addresses", [])) >= 2, f"{oracle_id}: expected address anchors")
    require(len(oracle.get("diary_entries", [])) >= 1, f"{oracle_id}: expected diary entries")
    fields = set(oracle.get("capture_fields", []))
    missing = REQUIRED_COMMON_FIELDS - fields
    require(not missing, f"{oracle_id}: missing common capture fields {sorted(missing)}")
    require(len(fields) >= 12, f"{oracle_id}: capture field set too small")
    notes = oracle.get("evidence_notes", [])
    sources = oracle.get("source_paths", [])
    require(len(notes) >= 2, f"{oracle_id}: expected evidence notes")
    require(len(sources) >= 1, f"{oracle_id}: expected source paths")
    require_existing_paths(notes, label="note", oracle_id=oracle_id)
    require_existing_paths(sources, label="source", oracle_id=oracle_id)
    criteria = oracle.get("acceptance_criteria", [])
    require(len(criteria) >= 2, f"{oracle_id}: acceptance criteria too thin")
    route_groups = oracle.get("route_groups", {})
    if route_groups:
        addresses = set(oracle.get("addresses", []))
        require(isinstance(route_groups, dict), f"{oracle_id}: route_groups must be an object")
        for group_id, group in route_groups.items():
            require(isinstance(group_id, str) and group_id, f"{oracle_id}: empty route group id")
            require(isinstance(group, dict), f"{oracle_id}/{group_id}: route group must be object")
            group_addresses = group.get("addresses", [])
            require(isinstance(group_addresses, list) and group_addresses, f"{oracle_id}/{group_id}: missing addresses")
            require(set(group_addresses).issubset(addresses), f"{oracle_id}/{group_id}: route group address outside oracle anchors")
            require(group.get("role"), f"{oracle_id}/{group_id}: missing role")
            require(group.get("status"), f"{oracle_id}/{group_id}: missing status")
            for hint_key in ("probe_breakpoint_hints", "watch_hints"):
                hints = group.get(hint_key, [])
                require(isinstance(hints, list), f"{oracle_id}/{group_id}: {hint_key} must be a list")
                require(all(isinstance(item, str) and item for item in hints), f"{oracle_id}/{group_id}: {hint_key} has blank entries")


def validate(data: dict[str, Any]) -> None:
    require(data.get("schema") == "earthbound-decomp.c2-battle-trace-oracle-plan.v1", "unexpected schema")
    require(data.get("status") == "trace_plan_ready_runner_pending", "unexpected status")
    policy = data.get("policy", {})
    require(policy.get("source_edits_allowed_from_manifest_alone") is False, "manifest cannot allow source edits")
    require("hint" in str(policy.get("ghidra_role", "")), "Ghidra role must remain hint-only")
    require("not source-facing proof" in str(policy.get("c_port_diary_role", "")), "C-port diary role too strong")
    require_existing_paths(data.get("references", []), label="reference", oracle_id="manifest")

    oracles = data.get("oracles", [])
    require(len(oracles) == len(REQUIRED_ORACLE_IDS), "oracle count mismatch")
    ids = [str(oracle.get("id", "")) for oracle in oracles]
    require(set(ids) == REQUIRED_ORACLE_IDS, f"oracle id set mismatch: {sorted(set(ids) ^ REQUIRED_ORACLE_IDS)}")
    require(len(ids) == len(set(ids)), "duplicate oracle ids")
    for oracle in oracles:
        validate_oracle(oracle)

    summary = data.get("summary", {})
    require(int(summary.get("oracle_count", -1)) == len(oracles), "summary oracle count mismatch")
    require(summary.get("promotion_allowed_by_plan") is False, "summary must block promotion")
    first_pass = data.get("first_trace_pass", [])
    require(first_pass, "missing first trace pass")
    require(set(first_pass).issubset(set(ids)), "first trace pass references unknown oracle")
    require("c2_8125_damage_abi_boundary" in first_pass, "first trace pass must include C2:8125")
    require("c2_724a_affliction_writer_matrix" in first_pass, "first trace pass must include C2:724A")


def main() -> int:
    args = parse_args()
    data = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    validate(data)
    print(f"C2 battle trace oracle manifest validation OK: {data['summary']['oracle_count']} oracles")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
