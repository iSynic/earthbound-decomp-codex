#!/usr/bin/env python3
"""Validate the generated C2 natural evidence audit."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MANIFEST = ROOT / "manifests" / "c2-natural-evidence-audit.json"
SCHEMA = "earthbound-decomp.c2-natural-evidence-audit.v1"
STATUS = "audit_generated_no_source_promotion"
MECHANISMS = {
    "physical_damage",
    "psi_damage",
    "hp_healing",
    "hp_roller_collapse",
    "status_apply_success",
    "item_effect",
    "multi_target_heal",
    "target_action_staging",
    "pp_transfer",
    "pp_loss_only",
    "flash_status_gate",
    "battle_text_amount_substitution",
}
STATUSES = {
    "natural_proof_candidate",
    "natural_capture_fields_missing",
    "runtime_steered_needed",
    "fixture_only_navigation",
    "not_yet_observed",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", nargs="?", default=str(DEFAULT_MANIFEST))
    return parser.parse_args()


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    require(data.get("schema") == SCHEMA, f"bad schema {data.get('schema')}", errors)
    require(data.get("status") == STATUS, f"bad status {data.get('status')}", errors)
    policy = data.get("evidence_policy", {})
    require(policy.get("vanilla_save_state") == "natural", "vanilla save-state policy missing", errors)
    mechanisms = data.get("mechanisms")
    require(isinstance(mechanisms, list), "mechanisms must be a list", errors)
    if isinstance(mechanisms, list):
        ids = {str(row.get("mechanism_id")) for row in mechanisms}
        require(ids == MECHANISMS, f"mechanism set mismatch: {sorted(MECHANISMS - ids)} missing", errors)
        for index, row in enumerate(mechanisms):
            prefix = f"mechanism {index}"
            require(str(row.get("status")) in STATUSES, f"{prefix}: bad status {row.get('status')}", errors)
            require(isinstance(row.get("oracle_id"), str) and row.get("oracle_id"), f"{prefix}: oracle missing", errors)
            require(isinstance(row.get("required_hits"), list), f"{prefix}: required_hits not list", errors)
            require(isinstance(row.get("best_natural_records"), list), f"{prefix}: best records not list", errors)
            require(isinstance(row.get("partial_natural_records"), list), f"{prefix}: partial records not list", errors)
            require(isinstance(row.get("steered_records"), list), f"{prefix}: steered records not list", errors)
            require(row.get("next_action"), f"{prefix}: next_action missing", errors)
            for field in ("natural_candidate_count", "natural_partial_count", "steered_candidate_count"):
                require(isinstance(row.get(field), int), f"{prefix}: {field} not int", errors)
            if row.get("status") == "natural_proof_candidate":
                require(row.get("natural_candidate_count", 0) > 0, f"{prefix}: proof candidate without natural record", errors)
    summary = data.get("summary", {})
    require(summary.get("source_promotion_allowed") is False, "source promotion must remain blocked", errors)
    require(summary.get("behavior_change_allowed") is False, "behavior changes must remain blocked", errors)
    if isinstance(mechanisms, list):
        require(summary.get("mechanism_count") == len(mechanisms), "summary mechanism_count mismatch", errors)
    return errors


def main() -> int:
    args = parse_args()
    data = load_json(Path(args.manifest))
    errors = validate(data)
    if errors:
        print("C2 natural evidence audit validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print(f"C2 natural evidence audit validation OK: {data['summary']['mechanism_count']} mechanisms")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
