#!/usr/bin/env python3
"""Validate the controlled C2:B930 snapshot-export manifest."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MANIFEST = ROOT / "manifests" / "c2-b930-controlled-snapshot-export.json"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate(manifest: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if manifest.get("schema") != "earthbound-decomp.c2-b930-controlled-snapshot-export.v1":
        errors.append(f"unexpected schema: {manifest.get('schema')}")
    if manifest.get("status") != "result_loaded":
        errors.append(f"result status must be result_loaded: {manifest.get('status')}")
    policy = manifest.get("policy", {})
    if policy.get("forced_entry_fixture_only") is not True:
        errors.append("policy must mark forced_entry_fixture_only true")
    for field in ("natural_c1_route_proven_in_this_result", "source_promotion_allowed", "behavior_change_allowed"):
        if policy.get(field) is not False:
            errors.append(f"policy {field} must be false")
    summary = manifest.get("summary", {})
    if summary.get("controlled_snapshot_export_observed") is not True:
        errors.append("controlled snapshot export must be observed")
    if summary.get("source_fields_exported_to_destination") is not True:
        errors.append("source fields exported-to-destination check failed")
    for field in ("natural_c1_route_proven_in_this_result", "source_promotion_allowed", "behavior_change_allowed"):
        if summary.get(field) is not False:
            errors.append(f"summary {field} must be false")
    evidence = manifest.get("evidence", {})
    observed = set(evidence.get("observed_addresses", []))
    if "C2:B930" not in observed:
        errors.append("observed addresses must include C2:B930")
    if evidence.get("contract_classification") != "needs_followup":
        errors.append("contract classification must remain needs_followup")
    if evidence.get("promotion_allowed_by_result") is not False:
        errors.append("promotion_allowed_by_result must be false")
    if evidence.get("behavior_change_allowed") is not False:
        errors.append("evidence behavior_change_allowed must be false")
    snapshot = manifest.get("snapshot_export", {})
    source = snapshot.get("source_slot", {})
    destination = snapshot.get("destination_slot", {})
    if source.get("base") != "0x0099CE":
        errors.append(f"unexpected source slot base: {source.get('base')}")
    if destination.get("base") != "0x009FFA":
        errors.append(f"unexpected destination base: {destination.get('base')}")
    if source.get("byte_count") != 95:
        errors.append(f"expected 95 source bytes, got {source.get('byte_count')}")
    if destination.get("after_byte_count") != 78:
        errors.append(f"expected 78 destination after bytes, got {destination.get('after_byte_count')}")
    if not manifest.get("controlled_result_limits"):
        errors.append("controlled result limits must be listed")
    return errors


def main() -> int:
    manifest = load_json(DEFAULT_MANIFEST)
    errors = validate(manifest)
    if errors:
        print("C2 B930 controlled snapshot export validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print(
        "C2 B930 controlled snapshot export validation OK: "
        f"{manifest['summary']['source_slot_base']} -> {manifest['summary']['destination_base']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
