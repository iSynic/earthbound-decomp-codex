#!/usr/bin/env python3
"""Validate the sanitized C2 manual Mesen probe matrix."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MATRIX = ROOT / "manifests" / "c2-battle-trace-manual-probe-matrix.json"
SCHEMA = "earthbound-decomp.c2-battle-trace-manual-probe-matrix.v1"
ALLOWED_STATUSES = {"minimum-hit-candidate", "partial-route-observed", "probed-no-route", "not-probed", "not-in-handoff"}
WINDOWS_ABSOLUTE_RE = re.compile(r"[A-Za-z]:\\")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate the C2 manual probe matrix.")
    parser.add_argument("matrix", nargs="?", default=str(DEFAULT_MATRIX))
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def contains_absolute_windows_path(value: Any) -> bool:
    if isinstance(value, str):
        return bool(WINDOWS_ABSOLUTE_RE.search(value))
    if isinstance(value, list):
        return any(contains_absolute_windows_path(item) for item in value)
    if isinstance(value, dict):
        return any(contains_absolute_windows_path(item) for item in value.values())
    return False


def validate(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    require(data.get("schema") == SCHEMA, f"unexpected schema {data.get('schema')}", errors)
    policy = data.get("policy", {})
    require(policy.get("source_promotion_allowed") is False, "source promotion must remain blocked", errors)
    require(policy.get("behavior_change_allowed") is False, "behavior changes must remain blocked", errors)
    require(policy.get("local_save_state_paths_redacted") is True, "local save-state paths must be redacted", errors)
    require(not contains_absolute_windows_path(data), "matrix must not contain absolute Windows paths", errors)

    records = data.get("records")
    oracles = data.get("oracles")
    require(isinstance(records, list), "records must be a list", errors)
    require(isinstance(oracles, list), "oracles must be a list", errors)
    if isinstance(records, list):
        for index, record in enumerate(records):
            prefix = f"record {index}"
            require(isinstance(record.get("fixture_id"), str) and record.get("fixture_id"), f"{prefix}: fixture_id missing", errors)
            require(isinstance(record.get("oracle_id"), str) and record.get("oracle_id"), f"{prefix}: oracle_id missing", errors)
            require(isinstance(record.get("observed_addresses"), list), f"{prefix}: observed_addresses not list", errors)
            require(isinstance(record.get("configured_minimum_hits"), list), f"{prefix}: configured_minimum_hits not list", errors)
            require(isinstance(record.get("missing_minimum_hits"), list), f"{prefix}: missing_minimum_hits not list", errors)
            if record.get("minimum_hits_satisfied"):
                require(not record.get("missing_minimum_hits"), f"{prefix}: ready record still has missing minimum hits", errors)
            save_state = record.get("save_state", {})
            require(isinstance(save_state, dict), f"{prefix}: save_state not object", errors)
            if isinstance(save_state, dict):
                require("basename" in save_state and "sha256" in save_state, f"{prefix}: save_state missing sanitized fields", errors)
    if isinstance(oracles, list):
        ready_total = 0
        for index, oracle in enumerate(oracles):
            prefix = f"oracle {index}"
            status = oracle.get("status")
            require(status in ALLOWED_STATUSES, f"{prefix}: unexpected status {status}", errors)
            require(isinstance(oracle.get("oracle_id"), str) and oracle.get("oracle_id"), f"{prefix}: oracle_id missing", errors)
            ready_count = oracle.get("minimum_hit_candidate_count")
            require(isinstance(ready_count, int), f"{prefix}: ready count not int", errors)
            if isinstance(ready_count, int):
                ready_total += ready_count
        summary = data.get("summary", {})
        require(summary.get("minimum_hit_candidate_count") == ready_total, "summary ready count mismatch", errors)
    route_gap_queue = data.get("route_gap_queue", [])
    require(isinstance(route_gap_queue, list), "route_gap_queue must be a list", errors)
    if isinstance(route_gap_queue, list):
        remaining_gaps = 0
        for index, item in enumerate(route_gap_queue):
            prefix = f"route gap {index}"
            require(isinstance(item.get("oracle_id"), str) and item.get("oracle_id"), f"{prefix}: oracle_id missing", errors)
            require(isinstance(item.get("route_group"), str) and item.get("route_group"), f"{prefix}: route_group missing", errors)
            require(isinstance(item.get("missing_from_all_probes"), list), f"{prefix}: missing list not list", errors)
            require(isinstance(item.get("covered_by_any_probe"), bool), f"{prefix}: covered flag not bool", errors)
            require(isinstance(item.get("probe_breakpoint_hints", []), list), f"{prefix}: breakpoint hints not list", errors)
            require(isinstance(item.get("watch_hints", []), list), f"{prefix}: watch hints not list", errors)
            if item.get("status") == "remaining_fixture_gap" and not item.get("covered_by_any_probe"):
                remaining_gaps += 1
        summary = data.get("summary", {})
        require(summary.get("remaining_route_gap_count") == remaining_gaps, "summary route gap count mismatch", errors)
    return errors


def main() -> int:
    args = parse_args()
    matrix = Path(args.matrix)
    data = load_json(matrix)
    errors = validate(data)
    if errors:
        print("C2 manual probe matrix validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print(
        "C2 manual probe matrix validation OK: "
        f"{data.get('summary', {}).get('record_count')} records"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
