#!/usr/bin/env python3
"""Validate collected non-0x00 control probe result status."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SUMMARY = ROOT / "manifests" / "audio-nonzero-control-probe-results-summary.json"

ALLOWED_STATUS = {"pending", "ok", "failed", "unsupported", "unresolved", "unknown"}
ALLOWED_CLASSIFICATIONS = {
    "pending",
    "ef_call_return",
    "timing_toggle",
    "earthbound_variant_ff",
    "unreachable",
    "unresolved",
    "unknown",
}
ALLOWED_BLOCKERS = {
    "non_zero_control_semantics_pending",
    "ef_call_return_effect",
    "timing_toggle_effect",
    "earthbound_variant_ff_effect",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate audio non-0x00 control probe result summary.")
    parser.add_argument("summary", nargs="?", default=str(DEFAULT_SUMMARY))
    return parser.parse_args()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def count_records(records: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for record in records:
        counts[str(record.get(key))] += 1
    return dict(sorted(counts.items()))


def blocker_counts(records: list[dict[str, Any]]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for record in records:
        for blocker in record.get("remaining_blockers", []):
            counts[str(blocker)] += 1
    return dict(sorted(counts.items()))


def validate(data: dict[str, Any]) -> None:
    require(
        data.get("schema") == "earthbound-decomp.audio-nonzero-control-probe-results-summary.v1",
        "unexpected schema",
    )
    require(data.get("status") == "nonzero_control_probe_results_collected", f"unexpected status {data.get('status')}")
    require(data.get("probe_plan") == "manifests/audio-nonzero-control-probe-plan.json", "unexpected probe plan")
    source_policy = data.get("source_policy", {})
    require(source_policy.get("requires_user_supplied_rom") is True, "source policy must require user ROM")
    require(source_policy.get("generated_probe_outputs_are_ignored") is True, "probe outputs must be ignored")
    require(
        str(source_policy.get("generated_outputs_root", "")).startswith("build/audio/nonzero-control-probe"),
        "unexpected generated outputs root",
    )

    records = data.get("results", [])
    summary = data.get("summary", {})
    require(int(summary.get("job_count", -1)) == len(records), "job count mismatch")
    require(int(summary.get("result_count", -1)) == sum(1 for record in records if record.get("result_exists")), "result count mismatch")
    require(int(summary.get("valid_result_count", -1)) == sum(1 for record in records if record.get("valid")), "valid result count mismatch")
    require(summary.get("sequence_promotion_allowed") is False, "summary must not directly allow sequence promotion")
    require(summary.get("status_counts") == count_records(records, "status"), "status counts mismatch")
    validation_counts: Counter[str] = Counter("valid" if record.get("valid") else "invalid_or_pending" for record in records)
    require(summary.get("validation_counts") == dict(sorted(validation_counts.items())), "validation counts mismatch")
    require(
        summary.get("control_effect_classification_counts") == count_records(records, "control_effect_classification"),
        "classification counts mismatch",
    )
    require(summary.get("command_job_counts") == count_records(records, "command"), "command counts mismatch")
    require(summary.get("remaining_blocker_job_counts") == blocker_counts(records), "remaining blockers mismatch")

    seen_job_ids: set[str] = set()
    command_set: set[str] = set()
    for record in records:
        job_id = str(record.get("job_id", ""))
        require(job_id.startswith("nonzero-probe-"), f"unexpected job id {job_id}")
        require(job_id not in seen_job_ids, f"duplicate job id {job_id}")
        seen_job_ids.add(job_id)
        command = str(record.get("command"))
        command_set.add(command)
        require(command in {"0xEF", "0xFD", "0xFE", "0xFF"}, f"{job_id}: unexpected command {command}")
        require(str(record.get("reader_pc", "")).startswith("0x"), f"{job_id}: invalid reader PC")
        require(str(record.get("status")) in ALLOWED_STATUS, f"{job_id}: unexpected status")
        require(
            str(record.get("control_effect_classification")) in ALLOWED_CLASSIFICATIONS,
            f"{job_id}: unexpected classification",
        )
        require(record.get("promotion_allowed") is False, f"{job_id}: promotion must remain blocked")
        path_text = str(record.get("result_path", "")).replace("\\", "/")
        require(
            path_text.startswith("build/audio/nonzero-control-probe/")
            and path_text.endswith("nonzero-control-proof-result.json"),
            f"{job_id}: unexpected result path {path_text}",
        )
        for blocker in record.get("remaining_blockers", []):
            require(str(blocker) in ALLOWED_BLOCKERS, f"{job_id}: unexpected blocker {blocker}")
        if record.get("result_exists"):
            require(record.get("status") != "pending", f"{job_id}: existing result cannot be pending")
        else:
            require(record.get("status") == "pending", f"{job_id}: missing result must be pending")
            require(
                record.get("control_effect_classification") == "pending",
                f"{job_id}: missing result classification must be pending",
            )
    require(command_set == {"0xEF", "0xFD", "0xFE", "0xFF"}, "command coverage mismatch")
    require(data.get("result_acceptance_policy"), "missing acceptance policy")
    require(data.get("next_work"), "missing next work")


def main() -> int:
    args = parse_args()
    data = json.loads(Path(args.summary).read_text(encoding="utf-8"))
    validate(data)
    print(
        "Audio non-0x00 control probe results summary validation OK: "
        f"{data['summary']['result_count']} / {data['summary']['job_count']} results, "
        f"remaining {data['summary']['remaining_blocker_job_counts']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
