#!/usr/bin/env python3
"""Validate collected 0x00 runtime probe result status."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SUMMARY = ROOT / "manifests" / "audio-zero-runtime-probe-results-summary.json"

ALLOWED_STATUS = {"pending", "ok", "failed", "unsupported", "unresolved", "unknown"}
ALLOWED_CLASSIFICATIONS = {
    "pending",
    "true_end",
    "ef_return",
    "loop_or_hold_continues",
    "unreachable_from_source_state",
    "unresolved",
    "unknown",
}
ALLOWED_BLOCKERS = {
    "zero_runtime_effect_proof",
    "ef_return_stack_model",
    "loop_point_metadata",
    "finite_transition_review",
    "active_preview_classification",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate audio 0x00 runtime probe result summary.")
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
        data.get("schema") == "earthbound-decomp.audio-zero-runtime-probe-results-summary.v1",
        "unexpected schema",
    )
    require(data.get("status") == "zero_runtime_probe_results_collected", f"unexpected status {data.get('status')}")
    require(data.get("probe_plan") == "manifests/audio-zero-runtime-probe-plan.json", "unexpected probe plan")
    source_policy = data.get("source_policy", {})
    require(source_policy.get("requires_user_supplied_rom") is True, "source policy must require user ROM")
    require(source_policy.get("generated_probe_outputs_are_ignored") is True, "probe outputs must be ignored")
    require(
        str(source_policy.get("generated_outputs_root", "")).startswith("build/audio/zero-runtime-probe"),
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
        summary.get("zero_effect_classification_counts") == count_records(records, "zero_effect_classification"),
        "classification counts mismatch",
    )
    require(summary.get("remaining_blocker_track_counts") == blocker_counts(records), "remaining blockers mismatch")

    seen_job_ids: set[str] = set()
    seen_track_ids: set[int] = set()
    for record in records:
        job_id = str(record.get("job_id", ""))
        require(job_id.startswith("zero-probe-track-"), f"unexpected job id {job_id}")
        require(job_id not in seen_job_ids, f"duplicate job id {job_id}")
        seen_job_ids.add(job_id)
        track_id = int(record.get("track_id", 0))
        require(track_id > 0, f"{job_id}: invalid track id")
        require(track_id not in seen_track_ids, f"duplicate track id {track_id}")
        seen_track_ids.add(track_id)
        require(str(record.get("status")) in ALLOWED_STATUS, f"{job_id}: unexpected status")
        require(
            str(record.get("zero_effect_classification")) in ALLOWED_CLASSIFICATIONS,
            f"{job_id}: unexpected classification",
        )
        require(record.get("promotion_allowed") is False, f"{job_id}: promotion must remain blocked")
        path_text = str(record.get("result_path", "")).replace("\\", "/")
        require(
            path_text.startswith("build/audio/zero-runtime-probe/") and path_text.endswith("zero-runtime-proof-result.json"),
            f"{job_id}: unexpected result path {path_text}",
        )
        for blocker in record.get("remaining_blockers", []):
            require(str(blocker) in ALLOWED_BLOCKERS, f"{job_id}: unexpected blocker {blocker}")
        if record.get("result_exists"):
            require(record.get("status") != "pending", f"{job_id}: existing result cannot be pending")
        else:
            require(record.get("status") == "pending", f"{job_id}: missing result must be pending")
            require(record.get("zero_effect_classification") == "pending", f"{job_id}: missing result classification must be pending")

    require(data.get("result_acceptance_policy"), "missing acceptance policy")
    require(data.get("next_work"), "missing next work")


def main() -> int:
    args = parse_args()
    data = json.loads(Path(args.summary).read_text(encoding="utf-8"))
    validate(data)
    print(
        "Audio 0x00 runtime probe results summary validation OK: "
        f"{data['summary']['result_count']} / {data['summary']['job_count']} results, "
        f"remaining {data['summary']['remaining_blocker_track_counts']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
