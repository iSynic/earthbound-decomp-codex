#!/usr/bin/env python3
"""Validate the joined audio duration uncertainty register."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MANIFEST = ROOT / "manifests" / "audio-duration-uncertainty-register.json"

ALLOWED_UNCERTAINTY = {
    "active_preview_classification_pending",
    "finite_transition_review_pending",
    "loop_point_metadata_pending",
    "measurement_missing",
    "no_duration_uncertainty_for_current_export",
    "non_zero_control_semantics_pending",
    "pcm_trim_usable_sequence_intent_open",
    "unclassified_duration_uncertainty",
    "zero_runtime_probe_pending",
}
ALLOWED_ZERO_BLOCKERS = {
    "active_preview_classification",
    "ef_return_stack_model",
    "finite_transition_review",
    "loop_point_metadata",
    "zero_runtime_effect_proof",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate audio duration uncertainty register.")
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


def blocker_counts(records: list[dict[str, Any]]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for record in records:
        for blocker in record.get("remaining_blockers", []):
            counts[str(blocker)] += 1
    return dict(sorted(counts.items()))


def zero_status_counts(records: list[dict[str, Any]]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for record in records:
        zero_probe = record.get("zero_probe")
        counts[str(zero_probe.get("status")) if zero_probe else "not_in_zero_probe_lane"] += 1
    return dict(sorted(counts.items()))


def validate(data: dict[str, Any]) -> None:
    require(data.get("schema") == "earthbound-decomp.audio-duration-uncertainty-register.v1", "unexpected schema")
    require(
        data.get("status") == "duration_uncertainty_joined_probe_outputs_pending",
        f"unexpected status {data.get('status')}",
    )
    references = set(data.get("references", []))
    for reference in (
        "manifests/audio-export-plan.json",
        "manifests/audio-exact-duration-triage.json",
        "manifests/audio-zero-runtime-probe-results-summary.json",
        "manifests/audio-nonzero-control-probe-results-summary.json",
        "manifests/audio-oracle-verification-report-all-tracks.json",
    ):
        require(reference in references, f"missing reference {reference}")

    records = data.get("tracks", [])
    summary = data.get("summary", {})
    require(int(summary.get("track_count", -1)) == len(records), "track count mismatch")
    require(len(records) >= 190, "unexpectedly small track register")
    require(
        summary.get("primary_uncertainty_track_counts") == count_records(records, "primary_uncertainty"),
        "primary uncertainty counts mismatch",
    )
    require(summary.get("export_class_counts") == count_records(records, "export_class"), "export class counts mismatch")
    require(summary.get("zero_probe_status_track_counts") == zero_status_counts(records), "zero status counts mismatch")
    require(
        summary.get("remaining_zero_probe_blocker_track_counts") == blocker_counts(records),
        "remaining blocker counts mismatch",
    )
    require(summary.get("nonzero_control_probe_job_status_counts"), "missing nonzero probe status counts")
    require(
        summary.get("remaining_nonzero_control_probe_blocker_job_counts"),
        "missing nonzero probe blocker counts",
    )
    require(
        summary["nonzero_control_probe_job_status_counts"].get("pending") == 7,
        "expected 7 pending nonzero control probe jobs",
    )
    require(
        summary["remaining_nonzero_control_probe_blocker_job_counts"].get("non_zero_control_semantics_pending") == 7,
        "expected 7 pending nonzero control semantics probe blockers",
    )
    require(summary.get("sequence_promotion_allowed") is False, "sequence promotion must remain blocked")
    require(
        int(summary.get("public_exact_duration_track_count", -1))
        == sum(1 for record in records if record.get("public_exact_duration_allowed_now")),
        "public exact-duration count mismatch",
    )

    seen_track_ids: set[int] = set()
    zero_lane_count = 0
    for record in records:
        track_id = int(record.get("track_id", -1))
        require(track_id not in seen_track_ids, f"duplicate track id {track_id}")
        seen_track_ids.add(track_id)
        primary = str(record.get("primary_uncertainty"))
        require(primary in ALLOWED_UNCERTAINTY, f"track {track_id}: unexpected uncertainty {primary}")
        require(record.get("next_action"), f"track {track_id}: missing next action")
        if record.get("public_exact_duration_allowed_now"):
            require(
                record.get("export_class") in {"finite_trim_candidate", "skip_no_audio"},
                f"track {track_id}: exact export allowed for unexpected export class {record.get('export_class')}",
            )
        for blocker in record.get("remaining_blockers", []):
            require(str(blocker) in ALLOWED_ZERO_BLOCKERS, f"track {track_id}: unexpected blocker {blocker}")
        zero_probe = record.get("zero_probe")
        if primary == "zero_runtime_probe_pending":
            zero_lane_count += 1
            require(zero_probe, f"track {track_id}: zero lane missing zero probe record")
            require("zero_runtime_effect_proof" in record.get("remaining_blockers", []), f"track {track_id}: zero lane missing zero proof blocker")
        else:
            require(not record.get("remaining_blockers"), f"track {track_id}: non-zero lane should not carry zero blockers")

    require(zero_lane_count == 19, f"expected 19 zero probe lane tracks, got {zero_lane_count}")
    release = data.get("release_gate_summary", {})
    require(release.get("all_track_near_oracle_passed") is True, "expected all-track near-oracle pass")
    require(release.get("independent_emulator_gate_passed") is False, "independent emulator gate should still be false")
    require(release.get("release_quality_playback_claim_ready") is False, "release-quality playback claim should remain false")
    require(data.get("decision_policy"), "missing decision policy")
    require(data.get("priority_lanes"), "missing priority lanes")


def main() -> int:
    args = parse_args()
    data = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    validate(data)
    print(
        "Audio duration uncertainty register validation OK: "
        f"{data['summary']['track_count']} tracks, "
        f"{data['summary']['primary_uncertainty_track_counts']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
