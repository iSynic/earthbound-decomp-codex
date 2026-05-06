#!/usr/bin/env python3
"""Validate the focused audio loop-point evidence plan."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PLAN = ROOT / "manifests" / "audio-loop-point-evidence-plan.json"
REQUIRED_REFERENCES = {
    "manifests/audio-duration-uncertainty-register.json",
    "manifests/audio-export-plan.json",
    "manifests/audio-pack-contracts.json",
    "manifests/audio-oracle-comparison-plan-all-tracks.json",
}
REQUIRED_TRACK_IDS = {5, 6, 115, 183, 184}
REQUIRED_MISSING_FIELDS = {"intro_samples", "loop_start_sample", "loop_end_sample", "measured_by"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate audio loop-point evidence plan.")
    parser.add_argument("plan", nargs="?", default=str(DEFAULT_PLAN))
    return parser.parse_args()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def count_records(records: list[dict[str, Any]], key_path: tuple[str, ...]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for record in records:
        current: Any = record
        for key in key_path:
            current = current.get(key, {}) if isinstance(current, dict) else None
        counts[str(current)] += 1
    return dict(sorted(counts.items()))


def validate(data: dict[str, Any]) -> None:
    require(data.get("schema") == "earthbound-decomp.audio-loop-point-evidence-plan.v1", "unexpected schema")
    require(data.get("status") == "loop_point_evidence_plan_ready_preview_policy_preserved", "unexpected status")
    require(REQUIRED_REFERENCES <= set(data.get("references", [])), "missing references")
    jobs = data.get("jobs", [])
    summary = data.get("summary", {})
    require(len(jobs) == 5, f"expected 5 loop-point evidence jobs, got {len(jobs)}")
    require(int(summary.get("job_count", -1)) == len(jobs), "job count mismatch")
    require(summary.get("primary_sample_pack_counts") == {"5": 5}, "all jobs should share primary sample pack 5")
    require(int(summary.get("no_dedicated_sequence_pack_count", -1)) == 5, "expected no dedicated sequence pack for all jobs")
    require(summary.get("diagnostic_focus_counts") == count_records(jobs, ("source_candidate", "diagnostic_focus")), "focus counts mismatch")
    require(int(summary.get("preview_policy_loop_count", 0)) == 2, "unexpected loop preview count")
    require(float(summary.get("preview_policy_fade_seconds", 0.0)) == 5.0, "unexpected loop preview fade")
    require(summary.get("promotion_allowed_by_plan") is False, "plan must not allow promotion")
    require(summary.get("public_exact_loop_export_ready") is False, "public exact loop export should remain blocked")

    seen_orders: set[int] = set()
    seen_track_ids: set[int] = set()
    for job in jobs:
        job_id = str(job.get("job_id", ""))
        track_id = int(job.get("track_id", -1))
        order = int(job.get("execution_order", 0))
        require(order > 0, f"{job_id}: invalid execution order")
        require(order not in seen_orders, f"{job_id}: duplicate execution order")
        seen_orders.add(order)
        require(track_id in REQUIRED_TRACK_IDS, f"{job_id}: unexpected track id {track_id}")
        require(track_id not in seen_track_ids, f"{job_id}: duplicate track id")
        seen_track_ids.add(track_id)
        require(job.get("primary_uncertainty") == "loop_point_metadata_pending", f"{job_id}: wrong uncertainty")
        require(job.get("export_class") == "loop_or_held_candidate", f"{job_id}: wrong export class")
        require(job.get("export_status") == "preview_policy_ready_exact_loop_pending", f"{job_id}: wrong export status")
        require(job.get("recommended_mode") == "loop_count_plus_fade_preview", f"{job_id}: wrong recommended mode")
        require(float(job.get("duration_seconds", 0.0)) == 120.0, f"{job_id}: expected 120 second preview")
        preview = job.get("loop_preview_policy", {})
        require(int(preview.get("loop_count", 0)) == 2, f"{job_id}: bad loop count")
        require(float(preview.get("fade_seconds", 0.0)) == 5.0, f"{job_id}: bad fade seconds")
        pack = job.get("pack_context", {})
        require(int(pack.get("primary_sample_pack", -1)) == 5, f"{job_id}: primary pack should be 5")
        require(pack.get("secondary_sample_pack") is None, f"{job_id}: secondary sample pack should be absent")
        require(pack.get("sequence_pack") is None, f"{job_id}: sequence pack should be absent")
        require(pack.get("no_dedicated_sequence_pack") is True, f"{job_id}: no sequence pack flag mismatch")
        primary_source = pack.get("primary_pack_source", {})
        require(primary_source.get("asset_id") == "asset.eb.audio_pack_5", f"{job_id}: bad primary source asset")
        require(primary_source.get("range") == "EB:520C..EB:78D6", f"{job_id}: bad primary source range")
        require(primary_source.get("sha1"), f"{job_id}: missing primary pack SHA-1")
        source = job.get("source_candidate", {})
        require(source.get("oracle_job_id", "").startswith("oracle-track-"), f"{job_id}: missing oracle job")
        require(source.get("source_spc", {}).get("path"), f"{job_id}: missing source SPC")
        require(source.get("source_render", {}).get("path"), f"{job_id}: missing source render")
        gap = job.get("loop_gap", {})
        require(gap.get("status") == "placeholder_only_exact_loop_points_pending", f"{job_id}: unexpected loop gap status")
        require(set(gap.get("missing_fields", [])) == REQUIRED_MISSING_FIELDS, f"{job_id}: missing loop fields mismatch")
        require(len(gap.get("required_evidence", [])) >= 3, f"{job_id}: required evidence too thin")
        require(len(job.get("evidence_questions", [])) >= 3, f"{job_id}: evidence questions too thin")
        require(len(job.get("required_runtime_evidence", [])) >= 4, f"{job_id}: runtime evidence too thin")
        require(job.get("promotion_allowed_by_plan") is False, f"{job_id}: job must not allow promotion")
        for command in (
            "python tools/build_audio_export_plan.py",
            "python tools/validate_audio_export_plan.py",
            "python tools/build_audio_duration_uncertainty_register.py",
            "python tools/validate_audio_duration_uncertainty_register.py",
        ):
            require(command in job.get("post_evidence_commands", []), f"{job_id}: missing post evidence command {command}")

    require(seen_orders == set(range(1, len(jobs) + 1)), "execution orders must be contiguous")
    require(seen_track_ids == REQUIRED_TRACK_IDS, "track coverage mismatch")
    require("held_policy_no_exact_loop_points" in data.get("accepted_evidence_statuses", []), "missing held-policy status")
    require(data.get("decision_policy"), "missing decision policy")
    for command in (
        "python tools/validate_audio_loop_point_evidence_plan.py",
        "python tools/validate_audio_export_plan.py",
        "python tools/validate_audio_duration_uncertainty_register.py",
    ):
        require(command in data.get("post_evidence_validation_commands", []), f"missing validation command {command}")


def main() -> int:
    args = parse_args()
    data = json.loads(Path(args.plan).read_text(encoding="utf-8"))
    validate(data)
    print(
        "Audio loop-point evidence plan validation OK: "
        f"{data['summary']['job_count']} jobs, packs {data['summary']['primary_sample_pack_counts']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
