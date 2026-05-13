#!/usr/bin/env python3
"""Validate the generated C3 actionscript semantics audit."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_AUDIT = ROOT / "build" / "c3-actionscript-semantics-audit.json"
SCHEMA = "earthbound-decomp.c3-actionscript-semantics-audit.v1"

REQUIRED_VALUE_STATUSES = {
    "runtime_boundary_confirmed",
    "bounded_local_unknown",
    "decode_contract_named",
    "reader_path_named",
    "reference_label_correlated",
    "payload_join_named",
    "payload_identity_pending",
}

REQUIRED_VALUE_CLASSES = {
    "direction_class_words",
    "field2b32_movement_words",
    "animation_ids",
    "visual_countdown_seed_bytes",
    "sound_effect_ids",
    "entity_script_ids",
    "visual_state_bytes",
    "surface_flags_bytes",
    "sprite_pose_descriptor_words",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate C3 actionscript semantics audit output.")
    parser.add_argument("audit", nargs="?", default=str(DEFAULT_AUDIT))
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def validate_value_readiness(data: dict[str, Any]) -> None:
    readiness = data.get("value_semantics_readiness")
    require(isinstance(readiness, list), "value_semantics_readiness must be a list")

    by_class = {str(item.get("value_class")): item for item in readiness}
    missing_classes = REQUIRED_VALUE_CLASSES - set(by_class)
    require(not missing_classes, f"missing value readiness classes: {sorted(missing_classes)}")

    status_counts = Counter(str(item.get("status")) for item in readiness)
    missing_statuses = REQUIRED_VALUE_STATUSES - set(status_counts)
    require(not missing_statuses, f"missing value readiness statuses: {sorted(missing_statuses)}")

    summary = data.get("summary", {})
    require(
        summary.get("value_semantics_statuses") == dict(status_counts.most_common()),
        "summary value_semantics_statuses mismatch",
    )

    for value_class, item in by_class.items():
        prefix = f"value class {value_class}"
        require(item.get("status"), f"{prefix}: missing status")
        require(isinstance(item.get("coverage"), dict), f"{prefix}: coverage must be object")
        observed_values = len(item["coverage"])
        observations = sum(int(value) for value in item["coverage"].values())
        require(item.get("observed_values") == observed_values, f"{prefix}: observed_values mismatch")
        require(item.get("observations") == observations, f"{prefix}: observations mismatch")
        require(isinstance(item.get("evidence"), str) and item["evidence"], f"{prefix}: missing evidence")
        require(isinstance(item.get("next_action"), str) and item["next_action"], f"{prefix}: missing next_action")

    require(by_class["direction_class_words"].get("status") == "runtime_boundary_confirmed", "direction words must be runtime-boundary confirmed")
    require(by_class["direction_class_words"].get("observed_values") == 4, "direction words should cover four directions")
    require(by_class["field2b32_movement_words"].get("status") == "runtime_boundary_confirmed", "field2b32 words must be runtime-boundary confirmed")
    require(by_class["field2b32_movement_words"].get("observed_values", 0) > 0, "field2b32 words need observed coverage")
    require(by_class["visual_state_bytes"].get("status") == "bounded_local_unknown", "visual state bytes must remain bounded local unknowns")
    require(by_class["surface_flags_bytes"].get("status") == "bounded_local_unknown", "surface flag bytes must remain bounded local unknowns")


def validate(data: dict[str, Any]) -> None:
    require(data.get("schema") == SCHEMA, "bad schema")
    summary = data.get("summary", {})
    require(summary.get("rows") == 181, "unexpected script row count")
    require(summary.get("by_decode_status") == {"complete": 181}, "C3 actionscript decode must remain complete")
    require(summary.get("unknown_callback_targets") == {}, "unknown callback targets must remain empty")
    require(summary.get("callback_contracts", 0) > 0, "missing callback contracts")
    require(summary.get("installed_callback_contracts", 0) > 0, "missing installed callback contracts")
    require(data.get("field2b32_boundary_signals", {}).get("producer_count", 0) > 0, "missing field2b32 boundary signals")
    require(data.get("direction_boundary_signals", {}).get("producer_count", 0) > 0, "missing direction boundary signals")
    validate_value_readiness(data)


def main() -> int:
    args = parse_args()
    data = load_json(Path(args.audit))
    validate(data)
    print(
        "C3 actionscript semantics audit validation OK: "
        f"{data['summary']['rows']} rows, "
        f"{len(data['value_semantics_readiness'])} value classes"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
