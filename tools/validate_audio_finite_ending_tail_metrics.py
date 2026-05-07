#!/usr/bin/env python3
"""Validate frame-normalized finite-ending tail metrics."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_METRICS = ROOT / "manifests" / "audio-finite-ending-tail-metrics.json"
REQUIRED_REFERENCES = {
    "manifests/audio-finite-ending-evidence-plan.json",
    "manifests/audio-duration-uncertainty-register.json",
    "manifests/audio-export-plan.json",
    "manifests/audio-oracle-comparison-plan-all-tracks.json",
}
REQUIRED_TRACK_IDS = {8, 9, 11, 123, 176}
VALID_CLASSIFICATIONS = {
    "active_through_render_boundary",
    "candidate_end_silence_unconfirmed",
    "post_candidate_tail_nonzero",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate finite-ending tail metrics.")
    parser.add_argument("metrics", nargs="?", default=str(DEFAULT_METRICS))
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
    require(data.get("schema") == "earthbound-decomp.audio-finite-ending-tail-metrics.v1", "unexpected schema")
    require(data.get("status") == "finite_ending_tail_metrics_ready_policy_preserved", "unexpected status")
    require(data.get("source_plan_status") == "finite_ending_evidence_plan_ready_preview_policy_preserved", "unexpected source plan status")
    require(REQUIRED_REFERENCES <= set(data.get("references", [])), "missing references")
    policy = data.get("unit_policy", {})
    require(policy.get("candidate_end_frame") == "pcm_frame_32000hz", "bad candidate-end unit")
    require(int(policy.get("render_boundary_active_tolerance_frames", -1)) == 4, "bad render-boundary tolerance")

    records = data.get("records", [])
    summary = data.get("summary", {})
    require(len(records) == 5, f"expected 5 records, got {len(records)}")
    require(int(summary.get("record_count", -1)) == len(records), "record count mismatch")
    require(set(summary.get("track_ids", [])) == REQUIRED_TRACK_IDS, "track coverage mismatch")
    require(summary.get("tail_classification_counts") == count_records(records, "tail_classification"), "classification count mismatch")
    require(summary.get("diagnostic_focus_counts") == count_records(records, "diagnostic_focus"), "focus count mismatch")
    require(int(summary.get("nonzero_after_candidate_end_count", -1)) == 5, "expected all finite candidates to have post-candidate PCM")
    require(int(summary.get("active_through_render_boundary_count", -1)) == 3, "expected 3 active-through-boundary records")
    require(summary.get("public_exact_finite_export_ready") is False, "public exact finite export should remain blocked")
    require(summary.get("promotion_allowed_by_report") is False, "report must not allow promotion")

    seen: set[int] = set()
    for record in records:
        track_id = int(record.get("track_id", -1))
        name = str(record.get("track_name", ""))
        classification = str(record.get("tail_classification"))
        require(track_id in REQUIRED_TRACK_IDS, f"{track_id}: unexpected track id")
        require(track_id not in seen, f"{track_id}: duplicate record")
        seen.add(track_id)
        require(name, f"{track_id}: missing track name")
        require(classification in VALID_CLASSIFICATIONS, f"{track_id}: bad classification {classification}")
        require(int(record.get("candidate_end_frame", 0)) > 0, f"{track_id}: missing candidate end")
        require(float(record.get("candidate_end_seconds", 0.0)) > 0.0, f"{track_id}: missing candidate seconds")
        require(int(record.get("last_nonzero_interleaved_sample_index", -1)) >= 0, f"{track_id}: missing source last-nonzero index")
        require(int(record.get("last_nonzero_frame_index", -1)) >= int(record.get("candidate_end_frame", 0)), f"{track_id}: tail ordering mismatch")
        require(int(record.get("frames_after_candidate_end", -1)) >= 0, f"{track_id}: missing tail frame delta")
        require(float(record.get("seconds_after_candidate_end", -1.0)) >= 0.0, f"{track_id}: missing tail seconds")
        require(int(record.get("rendered_frames", 0)) > int(record.get("candidate_end_frame", 0)), f"{track_id}: render should extend past candidate")
        require(int(record.get("voice_count", 0)) > 0, f"{track_id}: missing voice count")
        require(record.get("public_exact_export_allowed") is False, f"{track_id}: public exact export should remain blocked")
        require(record.get("exact_export_implication") == "blocked_pending_runtime_tail_classification", f"{track_id}: bad export implication")
        units = record.get("source_metric_units", {})
        require(units.get("finite_end_sample") == "pcm_frame_32000hz", f"{track_id}: bad source finite unit")
        require(units.get("source_render_nonzero_index") == "interleaved_pcm_sample_index", f"{track_id}: bad source render unit")
        if classification == "active_through_render_boundary":
            require(int(record.get("trailing_silent_frames_at_render_end", 99)) <= 4, f"{track_id}: active boundary classification mismatch")
        if classification == "post_candidate_tail_nonzero":
            require(int(record.get("trailing_silent_frames_at_render_end", -1)) > 4, f"{track_id}: post-candidate classification mismatch")

    require(seen == REQUIRED_TRACK_IDS, "record coverage mismatch")


def main() -> int:
    args = parse_args()
    data = json.loads(Path(args.metrics).read_text(encoding="utf-8"))
    validate(data)
    print(
        "Audio finite-ending tail metrics validation OK: "
        f"{data['summary']['record_count']} records, "
        f"classifications {data['summary']['tail_classification_counts']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
