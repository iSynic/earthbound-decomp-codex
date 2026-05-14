#!/usr/bin/env python3
"""Validate the controlled C2 PP resource amount comparison manifest."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MANIFEST = ROOT / "manifests" / "c2-resource-amount-controlled-comparison.json"
EXPECTED_LANES = {
    "psi_magnet_transfer_controlled": {
        "required_addresses": {"C2:9F5E", "C2:721D"},
        "target_delta_sign": -1,
        "active_delta_sign": 1,
    },
    "pp_reduction_loss_only_controlled": {
        "required_addresses": {"C2:8E42", "C2:721D"},
        "target_delta_sign": -1,
        "active_delta_sign": 0,
    },
    "psi_magnet_action_steered_no_wram": {
        "required_addresses": {"C2:9F5E", "C2:721D"},
        "target_delta_sign": -1,
        "active_delta_sign": 0,
    },
    "pp_reduction_action_steered_no_wram": {
        "required_addresses": {"C2:8E42", "C2:721D"},
        "target_delta_sign": -1,
        "active_delta_sign": 0,
    },
    "gigantic_ant_natural_table_magnet_seeded": {
        "required_addresses": {"C2:9F5E", "C2:721D", "C2:7191"},
        "target_delta_sign": -1,
        "active_delta_sign": 1,
    },
    "guardian_general_natural_table_pp_reduction_seeded": {
        "required_addresses": {"C2:8E42", "C2:721D", "C2:7191"},
        "target_delta_sign": -1,
        "active_delta_sign": 0,
    },
    "gigantic_ant_forced_magnet_startup_only": {
        "required_addresses": {"C2:9F5E"},
        "target_delta_sign": 0,
        "active_delta_sign": 0,
    },
    "guardian_general_forced_pp_reduction_startup_only": {
        "required_addresses": {"C2:8E42"},
        "target_delta_sign": 0,
        "active_delta_sign": 0,
    },
}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sign(value: Any) -> int | None:
    if not isinstance(value, int):
        return None
    if value < 0:
        return -1
    if value > 0:
        return 1
    return 0


def validate(manifest: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if manifest.get("schema") != "earthbound-decomp.c2-resource-amount-controlled-comparison.v1":
        errors.append(f"unexpected schema: {manifest.get('schema')}")
    policy = manifest.get("policy", {})
    if policy.get("fixture_or_wram_seeded_evidence_only") is not True:
        errors.append("policy must mark evidence as fixture_or_wram_seeded_evidence_only")
    for field in ("natural_vanilla_amount_proven", "source_promotion_allowed", "behavior_change_allowed"):
        if policy.get(field) is not False:
            errors.append(f"policy {field} must be false")
    lanes = {lane.get("lane_id"): lane for lane in manifest.get("lanes", [])}
    missing = sorted(set(EXPECTED_LANES) - set(lanes))
    if missing:
        errors.append(f"missing lanes: {missing}")
    for lane_id, expectation in EXPECTED_LANES.items():
        lane = lanes.get(lane_id)
        if not lane:
            continue
        if lane.get("status") != "capture_loaded":
            errors.append(f"{lane_id} status must be capture_loaded")
        observed = set(lane.get("observed_addresses", []))
        required = expectation["required_addresses"]
        if not required <= observed:
            errors.append(f"{lane_id} missing observed addresses {sorted(required - observed)}")
        if lane.get("source_promotion_allowed") is not False:
            errors.append(f"{lane_id} source_promotion_allowed must be false")
        if lane.get("behavior_change_allowed") is not False:
            errors.append(f"{lane_id} behavior_change_allowed must be false")
        if lane.get("natural_vanilla_amount_proven") is not False:
            errors.append(f"{lane_id} natural_vanilla_amount_proven must be false")
        if sign(lane.get("target_pp_delta")) != expectation["target_delta_sign"]:
            errors.append(f"{lane_id} target_pp_delta sign mismatch: {lane.get('target_pp_delta')}")
        if sign(lane.get("active_pp_delta")) != expectation["active_delta_sign"]:
            errors.append(f"{lane_id} active_pp_delta sign mismatch: {lane.get('active_pp_delta')}")
    return errors


def main() -> int:
    manifest = load_json(DEFAULT_MANIFEST)
    errors = validate(manifest)
    if errors:
        print("C2 resource amount controlled comparison validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    summary = manifest["summary"]
    print(
        "C2 resource amount controlled comparison validation OK: "
        f"{summary['loaded_capture_count']} / {summary['lane_count']} captures"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
