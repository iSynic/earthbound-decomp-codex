#!/usr/bin/env python3
"""Validate the residual audio duration uncertainty coverage report."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_REPORT = ROOT / "manifests" / "audio-residual-uncertainty-coverage-report.json"
REQUIRED_REFERENCES = {
    "manifests/audio-duration-uncertainty-register.json",
    "manifests/audio-export-plan.json",
}
REQUIRED_TRACK_IDS = {0, 4, 10, 12, 13, 14, 15, 135}
REQUIRED_UNCERTAINTY_COUNTS = {
    "active_preview_classification_pending": 1,
    "measurement_missing": 1,
    "no_duration_uncertainty_for_current_export": 1,
    "pcm_trim_usable_sequence_intent_open": 5,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate residual uncertainty coverage report.")
    parser.add_argument("report", nargs="?", default=str(DEFAULT_REPORT))
    return parser.parse_args()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def count_records(records: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for record in records:
        counts[str(record.get(key))] += 1
    return dict(sorted(counts.items()))


def validate(data: dict[str, Any]) -> None:
    require(data.get("schema") == "earthbound-decomp.audio-residual-uncertainty-coverage-report.v1", "unexpected schema")
    require(data.get("status") == "residual_uncertainty_coverage_ready_policy_preserved", "unexpected status")
    require(REQUIRED_REFERENCES <= set(data.get("references", [])), "missing references")
    records = data.get("records", [])
    summary = data.get("summary", {})
    require(len(records) == 8, f"expected 8 records, got {len(records)}")
    require(int(summary.get("record_count", -1)) == len(records), "record count mismatch")
    require(set(summary.get("track_ids", [])) == REQUIRED_TRACK_IDS, "track coverage mismatch")
    require(summary.get("primary_uncertainty_counts") == REQUIRED_UNCERTAINTY_COUNTS, "uncertainty counts mismatch")
    require(summary.get("primary_uncertainty_counts") == count_records(records, "primary_uncertainty"), "uncertainty counts do not match records")
    require(summary.get("export_class_counts") == count_records(records, "export_class"), "export class counts do not match records")
    require(summary.get("current_policy_state_counts") == count_records(records, "current_policy_state"), "policy counts do not match records")
    require(int(summary.get("public_exact_allowed_count", -1)) == 6, "expected 6 public-exact allowed residual records")
    require(int(summary.get("public_exact_blocked_count", -1)) == 2, "expected 2 public-exact blocked residual records")
    require(int(summary.get("pcm_trim_sequence_intent_open_count", -1)) == 5, "expected 5 PCM trim sequence-intent records")
    require(summary.get("behavior_change_allowed") is False, "behavior change should be blocked")
    require(summary.get("promotion_allowed_by_report") is False, "promotion should be blocked")

    for record in records:
        track_id = int(record.get("track_id", -1))
        uncertainty = str(record.get("primary_uncertainty"))
        require(track_id in REQUIRED_TRACK_IDS, f"{track_id}: unexpected track id")
        require(record.get("recommended_action"), f"{track_id}: missing recommended action")
        require(record.get("sequence_command_promotion_allowed") is False, f"{track_id}: sequence promotion should be blocked")
        if uncertainty == "pcm_trim_usable_sequence_intent_open":
            require(record.get("public_exact_export_allowed") is True, f"{track_id}: PCM trim should be public-exact allowed")
            require(record.get("current_policy_state") == "public_exact_ready_with_sequence_intent_open", f"{track_id}: bad PCM trim policy state")
        if uncertainty in {"measurement_missing", "active_preview_classification_pending"}:
            require(record.get("public_exact_export_allowed") is False, f"{track_id}: blocker should not be public-exact allowed")
            require(record.get("current_policy_state") == "public_exact_blocked", f"{track_id}: blocker policy state mismatch")
        if uncertainty == "no_duration_uncertainty_for_current_export":
            require(record.get("public_exact_export_allowed") is True, f"{track_id}: no-uncertainty record should be public-exact allowed")
            require(record.get("current_policy_state") == "public_exact_ready", f"{track_id}: no-uncertainty policy state mismatch")
    require(data.get("coverage_policy"), "missing coverage policy")


def main() -> int:
    args = parse_args()
    data = json.loads(Path(args.report).read_text(encoding="utf-8"))
    validate(data)
    print(
        "Audio residual uncertainty coverage report validation OK: "
        f"{data['summary']['record_count']} records, "
        f"{data['summary']['public_exact_blocked_count']} blocked"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
