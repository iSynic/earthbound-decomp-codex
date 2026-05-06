#!/usr/bin/env python3
"""Validate guarded audio probe-result intake into sequence semantics."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MANIFEST = ROOT / "manifests" / "audio-sequence-semantics-intake-plan.json"
REQUIRED_COMMANDS = {"0x00", "0xEF", "0xFD", "0xFE", "0xFF"}
ALLOWED_ZERO_CLASSIFICATIONS = {
    "pending",
    "true_end",
    "ef_return",
    "loop_or_hold_continues",
    "unreachable_from_source_state",
    "unresolved",
    "unknown",
}
ALLOWED_NONZERO_CLASSIFICATIONS = {
    "pending",
    "ef_call_return",
    "timing_toggle",
    "earthbound_variant_ff",
    "unreachable",
    "unresolved",
    "unknown",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate audio sequence semantics intake plan.")
    parser.add_argument("manifest", nargs="?", default=str(DEFAULT_MANIFEST))
    return parser.parse_args()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def count_records(records: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for record in records:
        counts[str(record.get(key))] += 1
    return dict(sorted(counts.items()))


def accepted_counts(records: list[dict[str, Any]]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for record in records:
        if record.get("accepted_for_semantics_candidate"):
            counts[str(record.get("command"))] += 1
    return dict(sorted(counts.items()))


def validate(data: dict[str, Any]) -> None:
    require(data.get("schema") == "earthbound-decomp.audio-sequence-semantics-intake-plan.v1", "unexpected schema")
    require(data.get("status") == "probe_result_intake_pending", f"unexpected status {data.get('status')}")
    references = set(data.get("references", []))
    for reference in (
        "manifests/audio-sequence-command-semantics.json",
        "manifests/audio-zero-runtime-probe-results-summary.json",
        "manifests/audio-nonzero-control-probe-results-summary.json",
        "manifests/audio-duration-uncertainty-register.json",
    ):
        require(reference in references, f"missing reference {reference}")

    records = data.get("intake_records", [])
    summary = data.get("summary", {})
    require(int(summary.get("intake_record_count", -1)) == len(records), "intake record count mismatch")
    require(int(summary.get("zero_intake_record_count", -1)) == sum(1 for record in records if record.get("command") == "0x00"), "zero intake count mismatch")
    require(
        int(summary.get("nonzero_intake_record_count", -1))
        == sum(1 for record in records if record.get("command") != "0x00"),
        "nonzero intake count mismatch",
    )
    require(
        int(summary.get("accepted_candidate_count", -1))
        == sum(1 for record in records if record.get("accepted_for_semantics_candidate")),
        "accepted candidate count mismatch",
    )
    require(summary.get("command_intake_record_counts") == count_records(records, "command"), "command counts mismatch")
    require(summary.get("accepted_candidate_counts_by_command") == accepted_counts(records), "accepted counts mismatch")
    require(summary.get("status_counts") == count_records(records, "status"), "status counts mismatch")
    require(summary.get("classification_counts") == count_records(records, "classification"), "classification counts mismatch")
    require(summary.get("sequence_promotion_allowed_by_intake") is False, "intake must not allow direct sequence promotion")
    require(int(summary.get("current_confirmed_command_count", -1)) == 0, "current semantics should still have 0 confirmed")

    command_set: set[str] = set()
    for record in records:
        command = str(record.get("command"))
        command_set.add(command)
        require(command in REQUIRED_COMMANDS, f"unexpected command {command}")
        require(record.get("job_id"), f"{command}: missing job id")
        require(record.get("source_result"), f"{command}: missing source result path")
        require(record.get("exact_duration_promotion_allowed_by_intake") is False, f"{command}: intake promotion must stay blocked")
        classification = str(record.get("classification"))
        if command == "0x00":
            require(classification in ALLOWED_ZERO_CLASSIFICATIONS, f"0x00: unexpected classification {classification}")
        else:
            require(
                classification in ALLOWED_NONZERO_CLASSIFICATIONS,
                f"{command}: unexpected classification {classification}",
            )
        if record.get("accepted_for_semantics_candidate"):
            require(record.get("valid") is True, f"{command}: accepted candidate must be valid")
            require(
                str(record.get("candidate_semantic_evidence", "")).startswith("earthbound_"),
                f"{command}: accepted candidate must name EarthBound evidence",
            )
        else:
            require(record.get("candidate_semantic_evidence"), f"{command}: missing candidate evidence status")

    require(command_set == REQUIRED_COMMANDS, "intake command coverage mismatch")
    states = data.get("command_intake_state", [])
    require({str(state.get("command")) for state in states} == REQUIRED_COMMANDS, "command state coverage mismatch")
    for state in states:
        command = str(state.get("command"))
        require(state.get("current_semantic_status"), f"{command}: missing current semantic status")
        require(state.get("current_exact_duration_promotion_allowed") is False, f"{command}: current promotion must remain false")
        require(state.get("exact_duration_promotion_allowed_by_intake") is False, f"{command}: state promotion must stay false")
    require(data.get("intake_policy"), "missing intake policy")
    require(data.get("next_work"), "missing next work")


def main() -> int:
    args = parse_args()
    data = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    validate(data)
    print(
        "Audio sequence semantics intake plan validation OK: "
        f"{data['summary']['intake_record_count']} records, "
        f"{data['summary']['accepted_candidate_count']} accepted"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
