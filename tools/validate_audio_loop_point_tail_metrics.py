#!/usr/bin/env python3
"""Validate frame-normalized loop/held preview tail metrics."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_METRICS = ROOT / "manifests" / "audio-loop-point-tail-metrics.json"
REQUIRED_REFERENCES = {
    "manifests/audio-loop-point-evidence-plan.json",
    "manifests/audio-duration-uncertainty-register.json",
    "manifests/audio-export-plan.json",
    "manifests/audio-pack-contracts.json",
    "manifests/audio-oracle-comparison-plan-all-tracks.json",
}
REQUIRED_TRACK_IDS = {5, 6, 115, 183, 184}
REQUIRED_MISSING_FIELDS = {"intro_samples", "loop_start_sample", "loop_end_sample", "measured_by"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate loop-point tail metrics.")
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
    require(data.get("schema") == "earthbound-decomp.audio-loop-point-tail-metrics.v1", "unexpected schema")
    require(data.get("status") == "loop_point_tail_metrics_ready_preview_policy_preserved", "unexpected status")
    require(
        data.get("source_plan_status") == "loop_point_evidence_plan_ready_preview_policy_preserved",
        "unexpected source plan status",
    )
    require(REQUIRED_REFERENCES <= set(data.get("references", [])), "missing references")
    policy = data.get("unit_policy", {})
    require(policy.get("source_render_nonzero_index") == "interleaved_pcm_sample_index", "bad source metric unit")
    require(policy.get("normalized_nonzero_index") == "pcm_frame_32000hz", "bad normalized metric unit")
    require(int(policy.get("render_boundary_active_tolerance_frames", -1)) == 4, "bad render-boundary tolerance")
    require(float(policy.get("diagnostic_render_seconds", 0.0)) == 30.0, "unexpected diagnostic render duration")
    require(float(policy.get("public_preview_duration_seconds", 0.0)) == 120.0, "unexpected public preview duration")

    records = data.get("records", [])
    summary = data.get("summary", {})
    require(len(records) == 5, f"expected 5 records, got {len(records)}")
    require(int(summary.get("record_count", -1)) == len(records), "record count mismatch")
    require(set(summary.get("track_ids", [])) == REQUIRED_TRACK_IDS, "track coverage mismatch")
    require(summary.get("tail_classification_counts") == count_records(records, "tail_classification"), "classification count mismatch")
    require(summary.get("diagnostic_focus_counts") == count_records(records, "diagnostic_focus"), "focus count mismatch")
    require(summary.get("primary_sample_pack_counts") == count_records(records, "primary_sample_pack"), "pack count mismatch")
    require(
        summary.get("tail_classification_counts") == {"active_through_diagnostic_render_boundary": 5},
        "expected all records active through render boundary",
    )
    require(int(summary.get("active_through_render_boundary_count", -1)) == 5, "active boundary count mismatch")
    require(int(summary.get("missing_exact_loop_field_count", -1)) == 20, "expected four missing loop fields per record")
    require(summary.get("public_exact_loop_export_ready") is False, "public exact loop export should remain blocked")
    require(summary.get("promotion_allowed_by_report") is False, "report must not allow promotion")

    seen: set[int] = set()
    for record in records:
        track_id = int(record.get("track_id", -1))
        require(track_id in REQUIRED_TRACK_IDS, f"{track_id}: unexpected track id")
        require(track_id not in seen, f"{track_id}: duplicate record")
        seen.add(track_id)
        require(
            record.get("tail_classification") == "active_through_diagnostic_render_boundary",
            f"{track_id}: unexpected tail classification",
        )
        require(int(record.get("primary_sample_pack", -1)) == 5, f"{track_id}: expected primary sample pack 5")
        require(record.get("no_dedicated_sequence_pack") is True, f"{track_id}: expected no dedicated sequence pack")
        require(
            float(record.get("current_public_preview_duration_seconds", 0.0)) == 120.0,
            f"{track_id}: expected 120-second public preview",
        )
        preview = record.get("current_public_preview_policy", {})
        require(int(preview.get("loop_count", 0)) == 2, f"{track_id}: expected loop count 2")
        require(float(preview.get("fade_seconds", 0.0)) == 5.0, f"{track_id}: expected 5-second fade")
        require(preview.get("recommended_mode") == "loop_count_plus_fade_preview", f"{track_id}: bad recommended mode")
        require(record.get("loop_gap_status") == "placeholder_only_exact_loop_points_pending", f"{track_id}: bad loop gap status")
        require(set(record.get("missing_loop_fields", [])) == REQUIRED_MISSING_FIELDS, f"{track_id}: missing loop fields mismatch")
        require(
            record.get("exact_loop_export_implication") == "blocked_pending_loop_or_hold_classification",
            f"{track_id}: bad export implication",
        )
        require(record.get("promotion_allowed_by_report") is False, f"{track_id}: report promoted unexpectedly")
        diagnostic = record.get("diagnostic_render", {})
        units = diagnostic.get("unit_policy", {})
        require(units.get("source_render_nonzero_index") == "interleaved_pcm_sample_index", f"{track_id}: bad source render unit")
        require(units.get("normalized_nonzero_index") == "pcm_frame_32000hz", f"{track_id}: bad normalized render unit")
        require(int(units.get("assumed_channels", 0)) == 2, f"{track_id}: expected stereo render")
        require(int(units.get("assumed_sample_rate", 0)) == 32000, f"{track_id}: expected 32 kHz render")
        require(float(diagnostic.get("render_seconds", 0.0)) == 30.0, f"{track_id}: expected 30-second diagnostic render")
        require(int(diagnostic.get("rendered_frames", 0)) == 960000, f"{track_id}: expected 960000 rendered frames")
        require(int(diagnostic.get("last_nonzero_frame_index", -1)) >= 959995, f"{track_id}: expected activity near render boundary")
        require(int(diagnostic.get("trailing_silent_frames_at_render_end", 99)) <= 4, f"{track_id}: expected active boundary tail")
        require(diagnostic.get("active_through_render_boundary") is True, f"{track_id}: active boundary flag mismatch")
        require(int(diagnostic.get("voice_count", 0)) > 0, f"{track_id}: missing voice count")

    require(seen == REQUIRED_TRACK_IDS, "record coverage mismatch")
    require(data.get("decision_policy"), "missing decision policy")


def main() -> int:
    args = parse_args()
    data = json.loads(Path(args.metrics).read_text(encoding="utf-8"))
    validate(data)
    print(
        "Audio loop-point tail metrics validation OK: "
        f"{data['summary']['record_count']} records, "
        f"classifications {data['summary']['tail_classification_counts']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
