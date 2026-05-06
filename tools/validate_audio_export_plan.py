#!/usr/bin/env python3
"""Validate the public-facing audio export plan."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PLAN = ROOT / "manifests" / "audio-export-plan.json"

ALLOWED_CLASSES = {
    "skip_no_audio",
    "finite_trim_candidate",
    "loop_or_held_candidate",
    "finite_or_transition_review_candidate",
    "unknown_active_preview",
    "unmeasured_or_missing",
}

ALLOWED_MODES = {
    "skip",
    "trim_to_observed_end",
    "loop_count_plus_fade_preview",
    "trim_candidate_after_manual_or_sequence_review",
    "diagnostic_preview",
    "do_not_public_export",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate the audio export plan.")
    parser.add_argument("plan", nargs="?", default=str(DEFAULT_PLAN))
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate(plan: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if plan.get("schema") != "earthbound-decomp.audio-export-plan.v1":
        errors.append(f"unexpected schema: {plan.get('schema')}")
    records = plan.get("tracks", [])
    if int(plan.get("summary", {}).get("track_count", -1)) != len(records):
        errors.append("summary track_count does not match tracks")

    class_counts: Counter[str] = Counter()
    status_counts: Counter[str] = Counter()
    mode_counts: Counter[str] = Counter()
    semantics_count = 0
    seen: set[int] = set()
    summary = plan.get("summary", {})
    sequence_promotion_allowed = bool(summary.get("sequence_command_promotion_allowed"))

    for record in records:
        track_id = int(record.get("track_id", -1))
        if track_id in seen:
            errors.append(f"duplicate track id {track_id}")
        seen.add(track_id)
        export_class = str(record.get("export_class", ""))
        mode = str(record.get("recommended_mode", ""))
        if export_class not in ALLOWED_CLASSES:
            errors.append(f"track {track_id}: unexpected export class {export_class}")
        if mode not in ALLOWED_MODES:
            errors.append(f"track {track_id}: unexpected recommended mode {mode}")
        class_counts[export_class] += 1
        status_counts[str(record.get("export_status", ""))] += 1
        mode_counts[mode] += 1
        if record.get("needs_sequence_semantics"):
            semantics_count += 1

        duration = record.get("duration_seconds")
        if mode == "trim_to_observed_end":
            if duration is None or float(duration) <= 0:
                errors.append(f"track {track_id}: finite trim requires a positive duration")
            if record.get("needs_sequence_semantics"):
                errors.append(f"track {track_id}: observed finite trim should not require sequence semantics")
            finite = record.get("finite_metadata")
            if not isinstance(finite, dict) or finite.get("finite_end_sample") is None:
                errors.append(f"track {track_id}: finite trim requires finite_metadata.finite_end_sample")
            else:
                if finite.get("tail_silence_seconds") is None:
                    errors.append(f"track {track_id}: finite trim requires finite_metadata.tail_silence_seconds")
                if finite.get("silence_threshold_abs_sample") is None:
                    errors.append(f"track {track_id}: finite trim requires finite_metadata.silence_threshold_abs_sample")
        if mode == "loop_count_plus_fade_preview":
            if float(record.get("fade_seconds", 0.0)) <= 0:
                errors.append(f"track {track_id}: loop preview requires fade seconds")
            if int(record.get("loop_count", 0)) <= 0:
                errors.append(f"track {track_id}: loop preview requires loop count")
            loop = record.get("loop_metadata")
            if not isinstance(loop, dict):
                errors.append(f"track {track_id}: loop preview requires loop_metadata")
            else:
                for key in ("intro_samples", "loop_start_sample", "loop_end_sample", "measured_by"):
                    if key not in loop:
                        errors.append(f"track {track_id}: loop_metadata missing {key}")
                preview = loop.get("preview_policy", {})
                if preview.get("mode") != "loop_count_plus_fade_preview":
                    errors.append(f"track {track_id}: loop_metadata preview policy mode mismatch")
                if int(preview.get("loop_count", 0)) != int(record.get("loop_count", -1)):
                    errors.append(f"track {track_id}: loop_metadata loop_count mismatch")
                if float(preview.get("fade_seconds", 0.0)) != float(record.get("fade_seconds", -1.0)):
                    errors.append(f"track {track_id}: loop_metadata fade_seconds mismatch")
                loop_evidence = loop.get("loop_point_evidence", {})
                if loop_evidence.get("status") not in {
                    "exact_loop_points_available",
                    "placeholder_only_exact_loop_points_pending",
                }:
                    errors.append(f"track {track_id}: loop_metadata missing loop point evidence status")
        if export_class == "skip_no_audio" and mode != "skip":
            errors.append(f"track {track_id}: no-audio class must use skip mode")
        duration_semantics = record.get("duration_semantics")
        if not isinstance(duration_semantics, dict):
            errors.append(f"track {track_id}: missing duration_semantics")
        else:
            if "public_exact_export_allowed" not in duration_semantics:
                errors.append(f"track {track_id}: duration_semantics missing public exact flag")
            if duration_semantics.get("sequence_command_promotion_allowed") and not sequence_promotion_allowed:
                errors.append(f"track {track_id}: sequence promotion allowed despite global command semantics block")
            if export_class == "loop_or_held_candidate" and duration_semantics.get("public_exact_export_allowed"):
                errors.append(f"track {track_id}: loop/held candidates must not be public exact exports without loop metadata promotion")
            if export_class == "finite_or_transition_review_candidate" and duration_semantics.get("public_exact_export_allowed"):
                errors.append(f"track {track_id}: review candidates must not be public exact exports")

    if dict(class_counts) != summary.get("export_class_counts"):
        errors.append("export_class_counts does not match tracks")
    if dict(status_counts) != summary.get("export_status_counts"):
        errors.append("export_status_counts does not match tracks")
    if dict(mode_counts) != summary.get("recommended_mode_counts"):
        errors.append("recommended_mode_counts does not match tracks")
    if int(summary.get("needs_sequence_semantics_count", -1)) != semantics_count:
        errors.append("needs_sequence_semantics_count does not match tracks")
    if "sequence_command_promotion_allowed" not in summary:
        errors.append("summary missing sequence_command_promotion_allowed")
    diagnostics = plan.get("diagnostic_summary", {})
    finite_diag = diagnostics.get("finite_end_policy", {})
    if int(finite_diag.get("public_exact_trim_count", -1)) != class_counts["finite_trim_candidate"]:
        errors.append("finite diagnostic count does not match finite trim candidates")
    loop_diag = diagnostics.get("loop_point_evidence", {})
    if int(loop_diag.get("loop_or_held_count", -1)) != class_counts["loop_or_held_candidate"]:
        errors.append("loop diagnostic count does not match loop/held candidates")
    preview_diag = diagnostics.get("preview_uncertainty", {})
    if int(preview_diag.get("tracks_requiring_sequence_semantics", -1)) != semantics_count:
        errors.append("preview diagnostic sequence semantics count mismatch")
    command_semantics = plan.get("command_semantics", {})
    if command_semantics.get("schema") != "earthbound-decomp.audio-sequence-command-semantics.v1":
        errors.append("missing command semantics reference")
    if sequence_promotion_allowed != bool(command_semantics.get("summary", {}).get("release_sequence_promotion_allowed")):
        errors.append("sequence command promotion flag mismatch")

    defaults = plan.get("defaults", {})
    if int(defaults.get("sample_rate", 0)) != 32000:
        errors.append("default sample rate must be 32000")
    if int(defaults.get("channels", 0)) != 2:
        errors.append("default channels must be stereo")
    if int(defaults.get("loop_preview_count", 0)) <= 0:
        errors.append("loop preview count must be positive")
    if len(plan.get("release_gates", [])) < 5:
        errors.append("release gates are too short")
    return errors


def main() -> int:
    args = parse_args()
    plan = load_json(Path(args.plan))
    errors = validate(plan)
    if errors:
        print("Audio export plan validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print(
        "Audio export plan validation OK: "
        f"{plan['summary']['track_count']} tracks, classes {plan['summary']['export_class_counts']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
