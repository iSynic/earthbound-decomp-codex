#!/usr/bin/env python3
"""Validate the C2 snapshot-export natural scout manifest."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MANIFEST = ROOT / "manifests" / "c2-snapshot-export-natural-scout.json"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate(manifest: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if manifest.get("schema") != "earthbound-decomp.c2-snapshot-export-natural-scout.v1":
        errors.append(f"unexpected schema: {manifest.get('schema')}")
    summary = manifest.get("summary", {})
    runs = manifest.get("runs", [])
    if summary.get("run_count") != len(runs):
        errors.append("run_count must match runs length")
    if summary.get("run_count", 0) < 8:
        errors.append("expected at least the numbered-save scout runs")
    for field in ("natural_route_proven", "source_promotion_allowed", "behavior_change_allowed"):
        if field == "behavior_change_allowed":
            expected = False
        else:
            expected = summary.get("snapshot_export_callsite_run_count", 0) > 0 or summary.get("natural_b930_run_count", 0) > 0
        if summary.get(field) is not expected:
            errors.append(f"{field} expected {expected}")
    if summary.get("natural_route_proven") and summary.get("natural_b930_run_count", 0) <= 0:
        errors.append("natural route proof requires at least one C2:B930 hit")
    if summary.get("c2_bac5_neighbor_run_count", 0) <= 0:
        errors.append("expected C2:BAC5 neighbor evidence")
    if not any(run.get("c1_adb4_hit") for run in runs):
        errors.append("expected at least one C1:ADB4 neighbor hit")
    if not manifest.get("interpretation", {}).get("next_required_fixture"):
        errors.append("next required fixture must be documented")
    return errors


def main() -> int:
    manifest = load_json(DEFAULT_MANIFEST)
    errors = validate(manifest)
    if errors:
        print("C2 snapshot-export natural scout validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print(
        "C2 snapshot-export natural scout validation OK: "
        f"{manifest['summary']['run_count']} runs, "
        f"{manifest['summary']['c2_bac5_neighbor_run_count']} BAC5 neighbors"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
