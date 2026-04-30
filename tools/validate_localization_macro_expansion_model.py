#!/usr/bin/env python3
"""Validate the generated localization macro expansion model."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import build_localization_macro_expansion_model as model_builder


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MODEL = ROOT / "build" / "localization-macro-expansion-model.json"
DEFAULT_FRONTIER = ROOT / "build" / "localization-macro-expansion-frontier.json"

REQUIRED_ROW_FIELDS = {
    "command",
    "expansion_class",
    "lowering_status",
    "source_role",
    "confidence",
    "runtime_alias",
    "vm_primitives",
    "preserve_source_form",
    "evidence_notes",
    "open_questions",
}

ALLOWED_LOWERING_STATUSES = {
    "direct_vm_alias",
    "source_macro_shape_proven",
    "source_macro_unproven",
    "defer_to_other_subsystem",
}

RAW_SOURCE_MARKERS = (
    ";@Habitat:",
    "message_label",
    "EDEBUG.MSG",
    "raw argument",
    "full source record",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate the localization macro expansion model.")
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL)
    parser.add_argument("--frontier", type=Path, default=DEFAULT_FRONTIER)
    return parser.parse_args()


def runtime_key(row: dict[str, Any]) -> tuple[str | None, str | None]:
    alias = row.get("runtime_alias") or {}
    return alias.get("opcode"), alias.get("subopcode")


def validate(model: dict[str, Any], frontier: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    rows = model.get("rows", [])
    frontier_rows = frontier.get("rows", [])
    rows_by_command = {row.get("command"): row for row in rows}
    frontier_by_command = {row.get("command"): row for row in frontier_rows}

    if model.get("generated_by") != "tools/build_localization_macro_expansion_model.py":
        errors.append("unexpected generated_by")
    source_frontier = str(model.get("source_frontier", "")).replace("\\", "/")
    if source_frontier != "build/localization-macro-expansion-frontier.json":
        errors.append("unexpected source_frontier")
    if len(rows) != len(frontier_rows):
        errors.append(f"model rows {len(rows)} do not match frontier rows {len(frontier_rows)}")
    if len(rows_by_command) != len(rows):
        errors.append("model contains duplicate command rows")

    for row in rows:
        command = row.get("command", "<missing>")
        missing = REQUIRED_ROW_FIELDS - set(row)
        if missing:
            errors.append(f"{command}: missing fields {sorted(missing)}")
        status = row.get("lowering_status")
        if status not in ALLOWED_LOWERING_STATUSES:
            errors.append(f"{command}: invalid lowering_status {status!r}")
        if not isinstance(row.get("vm_primitives"), list):
            errors.append(f"{command}: vm_primitives must be a list")
        if not isinstance(row.get("evidence_notes"), list) or not row.get("evidence_notes"):
            errors.append(f"{command}: missing evidence_notes")
        if not isinstance(row.get("open_questions"), list):
            errors.append(f"{command}: open_questions must be a list")
        if command not in frontier_by_command:
            errors.append(f"{command}: missing from frontier")

    frontier_control = {
        row["command"]
        for row in frontier_rows
        if row.get("expansion_lane") == "text_vm_control_macro"
    }
    expected_control = set(model_builder.CONTROL_MODELS)
    modeled_control = {
        row["command"]
        for row in rows
        if row.get("lowering_status") == "source_macro_shape_proven"
    }
    if frontier_control != expected_control:
        errors.append(
            "frontier control macro set drifted: "
            f"missing={sorted(expected_control - frontier_control)} "
            f"extra={sorted(frontier_control - expected_control)}"
        )
    if modeled_control != expected_control:
        errors.append(
            "proven control model set mismatch: "
            f"missing={sorted(expected_control - modeled_control)} "
            f"extra={sorted(modeled_control - expected_control)}"
        )

    for command, spec in model_builder.DIRECT_DISPLAY_ALIASES.items():
        row = rows_by_command.get(command)
        if row is None:
            errors.append(f"{command}: missing direct display alias row")
            continue
        if row.get("lowering_status") != "direct_vm_alias":
            errors.append(f"{command}: expected direct_vm_alias status")
        if runtime_key(row) != (spec["expected_opcode"], spec["expected_subopcode"]):
            errors.append(f"{command}: runtime alias mismatch")

    for command, spec in model_builder.DIRECT_INVENTORY_ALIASES.items():
        row = rows_by_command.get(command)
        if row is None:
            errors.append(f"{command}: missing direct inventory alias row")
            continue
        if row.get("lowering_status") != "direct_vm_alias":
            errors.append(f"{command}: expected direct_vm_alias status")
        if runtime_key(row) != (spec["expected_opcode"], spec["expected_subopcode"]):
            errors.append(f"{command}: runtime alias mismatch")

    for row in rows:
        lane = row.get("frontier", {}).get("expansion_lane")
        status = row.get("lowering_status")
        if lane in {"text_vm_display_macro", "text_vm_inventory_macro"} and status == "defer_to_other_subsystem":
            errors.append(f"{row.get('command')}: display/inventory lane should be modeled, not deferred")
        if lane not in {"text_vm_control_macro", "text_vm_display_macro", "text_vm_inventory_macro", "direct_runtime_hint"}:
            if status != "defer_to_other_subsystem":
                errors.append(f"{row.get('command')}: non-target lane {lane} should remain deferred")

    serialized = json.dumps(model, sort_keys=True)
    for marker in RAW_SOURCE_MARKERS:
        if marker in serialized:
            errors.append(f"model contains raw-source marker {marker!r}")

    summary = model.get("summary", {})
    status_counts = {
        status: sum(1 for row in rows if row.get("lowering_status") == status)
        for status in ALLOWED_LOWERING_STATUSES
    }
    for status, count in status_counts.items():
        if summary.get(status) != count:
            errors.append(f"summary count mismatch for {status}: expected {count}, saw {summary.get(status)}")

    return errors


def main() -> int:
    args = parse_args()
    model = json.loads(args.model.read_text(encoding="utf-8"))
    frontier = json.loads(args.frontier.read_text(encoding="utf-8"))
    errors = validate(model, frontier)
    if errors:
        print("Localization macro expansion model validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print(
        "Localization macro expansion model validation OK: "
        f"{len(model['rows'])} commands, "
        f"{model['summary']['source_macro_shape_proven']} proven control macros, "
        f"{model['summary']['direct_vm_alias']} direct aliases"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
