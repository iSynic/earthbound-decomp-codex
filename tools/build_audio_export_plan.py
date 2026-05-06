#!/usr/bin/env python3
"""Build the public-facing audio export plan.

This combines the policy manifest, the 30-second diagnostic measurements, and
any longer targeted measurements into a practical per-track export contract.
It does not create WAV files; it describes how the app/CLI should export them.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_POLICY = ROOT / "manifests" / "audio-export-duration-policy.json"
DEFAULT_MEASUREMENTS = ROOT / "build" / "audio" / "export-duration-measurements" / "export-duration-measurements.json"
DEFAULT_EXTENDED_MEASUREMENTS = (
    ROOT / "build" / "audio" / "finite-candidate-extended-duration-measurements" / "export-duration-measurements.json"
)
DEFAULT_ORACLE_REPORT = ROOT / "manifests" / "audio-oracle-verification-report-all-tracks.json"
DEFAULT_COMMAND_SEMANTICS = ROOT / "manifests" / "audio-sequence-command-semantics.json"
DEFAULT_JSON = ROOT / "manifests" / "audio-export-plan.json"
DEFAULT_MARKDOWN = ROOT / "notes" / "audio-export-plan.md"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the audio export plan.")
    parser.add_argument("--policy", default=str(DEFAULT_POLICY), help="Duration policy manifest.")
    parser.add_argument("--measurements", default=str(DEFAULT_MEASUREMENTS), help="30-second duration measurements.")
    parser.add_argument(
        "--extended-measurements",
        default=str(DEFAULT_EXTENDED_MEASUREMENTS),
        help="Optional longer targeted measurements.",
    )
    parser.add_argument("--oracle-report", default=str(DEFAULT_ORACLE_REPORT), help="All-track oracle report.")
    parser.add_argument("--command-semantics", default=str(DEFAULT_COMMAND_SEMANTICS), help="Promoted command semantics JSON.")
    parser.add_argument("--json", default=str(DEFAULT_JSON), help="JSON output path.")
    parser.add_argument("--markdown", default=str(DEFAULT_MARKDOWN), help="Markdown output path.")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def repo_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def records_by_track(measurements: dict[str, Any]) -> dict[int, dict[str, Any]]:
    return {int(record["track_id"]): record for record in measurements.get("records", [])}


def best_measurement(track_id: int, base: dict[int, dict[str, Any]], extended: dict[int, dict[str, Any]]) -> dict[str, Any] | None:
    extended_record = extended.get(track_id)
    if extended_record and extended_record.get("measurement") is not None:
        return extended_record
    base_record = base.get(track_id)
    if base_record and base_record.get("measurement") is not None:
        return base_record
    return base_record or extended_record


def loop_point_evidence(target: dict[str, Any]) -> dict[str, Any]:
    exact_fields = {
        "intro_samples": target.get("intro_samples"),
        "loop_start_sample": target.get("loop_start_sample"),
        "loop_end_sample": target.get("loop_end_sample"),
        "measured_by": target.get("measured_by"),
    }
    missing = [key for key, value in exact_fields.items() if value is None]
    return {
        "status": "exact_loop_points_available" if not missing else "placeholder_only_exact_loop_points_pending",
        "missing_fields": missing,
        "required_evidence": [
            "decoded sequence loop/fallthrough control flow",
            "runtime confirmation of loop restart or held-note policy",
            "sample-accurate loop start/end once the sequence semantics are promoted",
        ],
    }


def duration_semantics_for_decision(
    export_class: str,
    recommended_mode: str,
    finite_metadata: dict[str, Any] | None,
    loop_metadata: dict[str, Any] | None,
    command_semantics: dict[str, Any],
) -> dict[str, Any]:
    zero = command_semantics.get("commands", {}).get("0x00", {})
    ff = command_semantics.get("commands", {}).get("0xFF", {})
    fd = command_semantics.get("commands", {}).get("0xFD", {})
    fe = command_semantics.get("commands", {}).get("0xFE", {})
    sequence_allowed = bool(command_semantics.get("summary", {}).get("release_sequence_promotion_allowed"))
    if export_class == "finite_trim_candidate":
        return {
            "classification": "finite",
            "exactness_basis": "pcm_silence" if finite_metadata else "unavailable",
            "sequence_command_promotion_allowed": bool(zero.get("exact_duration_promotion_allowed")),
            "sequence_command_status": {
                "0x00": zero.get("semantic_status", "missing_command_semantics"),
                "0xFF": ff.get("semantic_status", "missing_command_semantics"),
            },
            "public_exact_export_allowed": finite_metadata is not None,
            "evidence": {
                "finite_metadata": finite_metadata,
                "pcm_corroboration": finite_metadata is not None,
                "sequence_command_semantics": "not_required_for_current_pcm_silence_trim_policy_zero_control_pending",
            },
        }
    if export_class == "loop_or_held_candidate":
        return {
            "classification": "loop_or_held",
            "exactness_basis": "preview_policy",
            "sequence_command_promotion_allowed": sequence_allowed,
            "sequence_command_status": {
                "0x00": zero.get("semantic_status", "missing_command_semantics"),
                "0xFD": fd.get("semantic_status", "missing_command_semantics"),
                "0xFE": fe.get("semantic_status", "missing_command_semantics"),
                "0xFF": ff.get("semantic_status", "missing_command_semantics"),
            },
            "public_exact_export_allowed": False,
            "evidence": {
                "loop_metadata": loop_metadata,
                "loop_point_evidence": loop_metadata.get("loop_point_evidence") if isinstance(loop_metadata, dict) else None,
                "preview_policy": loop_metadata.get("preview_policy") if isinstance(loop_metadata, dict) else None,
            },
        }
    if export_class == "finite_or_transition_review_candidate":
        return {
            "classification": "finite_or_transition_review",
            "exactness_basis": "review_required",
            "sequence_command_promotion_allowed": sequence_allowed,
            "sequence_command_status": {
                "0x00": zero.get("semantic_status", "missing_command_semantics"),
                "0xFF": ff.get("semantic_status", "missing_command_semantics"),
            },
            "public_exact_export_allowed": False,
            "evidence": {"finite_metadata": finite_metadata},
        }
    return {
        "classification": "skip" if recommended_mode == "skip" else "unknown_or_preview",
        "exactness_basis": "not_applicable" if recommended_mode == "skip" else "not_promoted",
        "sequence_command_promotion_allowed": sequence_allowed,
        "sequence_command_status": {
            command: command_semantics.get("commands", {}).get(command, {}).get("semantic_status", "missing_command_semantics")
            for command in ("0x00", "0xEF", "0xFD", "0xFE", "0xFF")
        },
        "public_exact_export_allowed": recommended_mode == "skip",
        "evidence": {},
    }


def with_duration_semantics(decision: dict[str, Any], command_semantics: dict[str, Any]) -> dict[str, Any]:
    decision["duration_semantics"] = duration_semantics_for_decision(
        str(decision["export_class"]),
        str(decision["recommended_mode"]),
        decision.get("finite_metadata"),
        decision.get("loop_metadata"),
        command_semantics,
    )
    return decision


def export_decision(
    policy_track: dict[str, Any],
    measurement_record: dict[str, Any] | None,
    command_semantics: dict[str, Any],
) -> dict[str, Any]:
    track_id = int(policy_track["track_id"])
    duration_class = str(policy_track["duration_class"])
    status = str(measurement_record.get("measurement_status")) if measurement_record else "missing_preview"
    measurement = measurement_record.get("measurement") if measurement_record else None
    candidate = measurement_record.get("candidate_duration") if measurement_record else None
    target = policy_track.get("target_metadata", {})

    if duration_class == "no_audio_no_key_on":
        return with_duration_semantics({
            "export_class": "skip_no_audio",
            "export_status": "ready",
            "recommended_mode": "skip",
            "reason": "Load path is valid but no key-on render is expected.",
            "duration_seconds": 0.0,
            "fade_seconds": 0.0,
            "loop_count": 0,
            "loop_metadata": None,
            "finite_metadata": None,
            "needs_sequence_semantics": False,
        }, command_semantics)

    if status == "finite_end_observed_in_preview" and candidate:
        return with_duration_semantics({
            "export_class": "finite_trim_candidate",
            "export_status": "usable_with_pcm_silence_evidence",
            "recommended_mode": "trim_to_observed_end",
            "reason": "Sustained trailing silence was observed in a rendered preview.",
            "duration_seconds": candidate["end_seconds"],
            "fade_seconds": 0.0,
            "loop_count": 0,
            "loop_metadata": None,
            "finite_metadata": {
                "finite_end_sample": candidate["end_frame"],
                "finite_end_seconds": candidate["end_seconds"],
                "tail_silence_seconds": candidate["tail_silence_seconds"],
                "silence_threshold_abs_sample": candidate["silence_threshold_abs_sample"],
                "evidence": "sustained_tail_pcm_silence",
                "measured_by": "audio_export_duration_measurement",
            },
            "needs_sequence_semantics": False,
            "evidence": {
                "end_frame": candidate["end_frame"],
                "tail_silence_seconds": candidate["tail_silence_seconds"],
                "silence_threshold_abs_sample": candidate["silence_threshold_abs_sample"],
            },
        }, command_semantics)

    if status in ("looping_candidate_preview_still_active", "finite_candidate_no_end_seen_in_preview"):
        loop_evidence = loop_point_evidence(target)
        return with_duration_semantics({
            "export_class": "loop_or_held_candidate",
            "export_status": "preview_policy_ready_exact_loop_pending",
            "recommended_mode": "loop_count_plus_fade_preview",
            "reason": "The render stays active through the longest available measurement; exact loop/end semantics are not pinned.",
            "duration_seconds": 120.0 if measurement and float(measurement.get("total_seconds", 0.0)) >= 120 else 30.0,
            "fade_seconds": 5.0,
            "loop_count": 2,
            "loop_metadata": {
                "intro_samples": target.get("intro_samples"),
                "loop_start_sample": target.get("loop_start_sample"),
                "loop_end_sample": target.get("loop_end_sample"),
                "measured_by": target.get("measured_by"),
                "status": "loop_points_pending",
                "loop_point_evidence": loop_evidence,
                "preview_policy": {
                    "mode": "loop_count_plus_fade_preview",
                    "loop_count": 2,
                    "fade_seconds": 5.0,
                },
            },
            "finite_metadata": None,
            "needs_sequence_semantics": True,
        }, command_semantics)

    if status in ("looping_candidate_silence_seen_review_needed", "unknown_silence_seen_needs_classification"):
        end_seconds = candidate.get("end_seconds") if candidate else measurement.get("candidate_end_seconds") if measurement else None
        return with_duration_semantics({
            "export_class": "finite_or_transition_review_candidate",
            "export_status": "review_needed_before_public_exact_export",
            "recommended_mode": "trim_candidate_after_manual_or_sequence_review",
            "reason": "Trailing silence was observed, but the policy class is not confidently finite.",
            "duration_seconds": end_seconds,
            "fade_seconds": 0.0,
            "loop_count": 0,
            "loop_metadata": None,
            "finite_metadata": {
                "finite_end_sample": candidate.get("end_frame") if candidate else None,
                "finite_end_seconds": end_seconds,
                "tail_silence_seconds": candidate.get("tail_silence_seconds") if candidate else None,
                "silence_threshold_abs_sample": candidate.get("silence_threshold_abs_sample") if candidate else None,
                "evidence": "trailing_pcm_silence_review_needed",
                "measured_by": "audio_export_duration_measurement",
            },
            "needs_sequence_semantics": True,
        }, command_semantics)

    if status == "unknown_preview_still_active":
        return with_duration_semantics({
            "export_class": "unknown_active_preview",
            "export_status": "preview_only",
            "recommended_mode": "diagnostic_preview",
            "reason": "Track remains active and has not been classified as finite or looping.",
            "duration_seconds": 30.0,
            "fade_seconds": 5.0,
            "loop_count": 0,
            "loop_metadata": None,
            "finite_metadata": None,
            "needs_sequence_semantics": True,
        }, command_semantics)

    return with_duration_semantics({
        "export_class": "unmeasured_or_missing",
        "export_status": "blocked_or_skip_until_measured",
        "recommended_mode": "do_not_public_export",
        "reason": "No rendered measurement is available for this table entry.",
        "duration_seconds": None,
        "fade_seconds": None,
        "loop_count": None,
        "loop_metadata": None,
        "finite_metadata": None,
        "needs_sequence_semantics": track_id != 0,
    }, command_semantics)


def diagnostic_summary(records: list[dict[str, Any]], oracle_report: dict[str, Any]) -> dict[str, Any]:
    finite = [record for record in records if record["export_class"] == "finite_trim_candidate"]
    review = [record for record in records if record["export_class"] == "finite_or_transition_review_candidate"]
    loop_or_held = [record for record in records if record["export_class"] == "loop_or_held_candidate"]
    unknown = [record for record in records if record["export_class"] == "unknown_active_preview"]
    finite_durations = [float(record["duration_seconds"]) for record in finite if record.get("duration_seconds") is not None]
    finite_tail_silence = [
        float(record.get("finite_metadata", {}).get("tail_silence_seconds", 0.0))
        for record in finite
        if record.get("finite_metadata", {}).get("tail_silence_seconds") is not None
    ]
    missing_exact_loop_points = 0
    for record in loop_or_held:
        evidence = record.get("loop_metadata", {}).get("loop_point_evidence", {})
        if evidence.get("status") != "exact_loop_points_available":
            missing_exact_loop_points += 1
    gate_results = oracle_report.get("gate_results", {})
    return {
        "finite_end_policy": {
            "public_exact_trim_count": len(finite),
            "basis": "sustained_tail_pcm_silence_only",
            "minimum_duration_seconds": min(finite_durations) if finite_durations else None,
            "maximum_duration_seconds": max(finite_durations) if finite_durations else None,
            "minimum_tail_silence_seconds": min(finite_tail_silence) if finite_tail_silence else None,
            "extra_generated_tail_seconds": 0.0,
            "sequence_semantics_required_for_current_trim": False,
        },
        "review_policy": {
            "finite_or_transition_review_count": len(review),
            "public_exact_export_allowed": False,
            "required_evidence": "manual or decoded sequence proof that observed silence is a musical end rather than a transition/loop setup",
        },
        "loop_point_evidence": {
            "loop_or_held_count": len(loop_or_held),
            "exact_loop_points_available": len(loop_or_held) - missing_exact_loop_points,
            "exact_loop_points_missing": missing_exact_loop_points,
            "public_exact_export_allowed": missing_exact_loop_points == 0 and bool(loop_or_held),
        },
        "preview_uncertainty": {
            "unknown_active_preview_count": len(unknown),
            "unmeasured_or_missing_count": sum(1 for record in records if record["export_class"] == "unmeasured_or_missing"),
            "tracks_requiring_sequence_semantics": sum(1 for record in records if record.get("needs_sequence_semantics")),
        },
        "oracle_release_gate": {
            "all_track_near_oracle_passed": bool(gate_results.get("all_track_oracle_gate_passed")),
            "independent_emulator_gate_passed": bool(gate_results.get("independent_emulator_gate_passed")),
            "release_quality_playback_claim_ready": bool(gate_results.get("release_quality_playback_claim_ready")),
        },
    }


def build_plan(
    policy_path: Path,
    measurements_path: Path,
    extended_measurements_path: Path,
    oracle_report_path: Path,
    command_semantics_path: Path,
) -> dict[str, Any]:
    policy = load_json(policy_path)
    measurements = load_json(measurements_path)
    extended_measurements = load_json(extended_measurements_path) if extended_measurements_path.exists() else {"records": []}
    oracle_report = load_json(oracle_report_path) if oracle_report_path.exists() else {}
    command_semantics = load_json(command_semantics_path) if command_semantics_path.exists() else {
        "schema": "earthbound-decomp.audio-sequence-command-semantics.v1",
        "status": "missing",
        "summary": {"release_sequence_promotion_allowed": False},
        "commands": {},
    }
    base_by_track = records_by_track(measurements)
    extended_by_track = records_by_track(extended_measurements)

    records: list[dict[str, Any]] = []
    class_counts: Counter[str] = Counter()
    status_counts: Counter[str] = Counter()
    mode_counts: Counter[str] = Counter()
    semantics_count = 0

    for track in policy.get("tracks", []):
        measurement_record = best_measurement(int(track["track_id"]), base_by_track, extended_by_track)
        decision = export_decision(track, measurement_record, command_semantics)
        record = {
            "track_id": int(track["track_id"]),
            "track_name": track["track_name"],
            "policy_duration_class": track["duration_class"],
            "measurement_status": measurement_record.get("measurement_status") if measurement_record else "missing_preview",
            **decision,
        }
        records.append(record)
        class_counts[record["export_class"]] += 1
        status_counts[record["export_status"]] += 1
        mode_counts[record["recommended_mode"]] += 1
        if record["needs_sequence_semantics"]:
            semantics_count += 1

    return {
        "schema": "earthbound-decomp.audio-export-plan.v1",
        "status": "export_policy_ready_exact_loop_points_pending",
        "inputs": {
            "duration_policy": repo_path(policy_path),
            "duration_measurements": repo_path(measurements_path),
            "extended_duration_measurements": repo_path(extended_measurements_path) if extended_measurements_path.exists() else None,
            "oracle_report": repo_path(oracle_report_path) if oracle_report_path.exists() else None,
            "command_semantics": repo_path(command_semantics_path) if command_semantics_path.exists() else None,
        },
        "playback_confidence": {
            "all_track_near_oracle_passed": bool(
                oracle_report.get("gate_results", {}).get("all_track_oracle_gate_passed")
            ),
            "independent_emulator_gate_passed": bool(
                oracle_report.get("gate_results", {}).get("independent_emulator_gate_passed")
            ),
            "release_quality_playback_claim_ready": bool(
                oracle_report.get("gate_results", {}).get("release_quality_playback_claim_ready")
            ),
        },
        "defaults": {
            "sample_rate": 32000,
            "channels": 2,
            "bits_per_sample": 16,
            "loop_preview_count": 2,
            "loop_preview_fade_seconds": 5.0,
            "finite_trim_tail_policy": "trim after the last sample above the silence threshold; keep no extra generated silence",
        },
        "summary": {
            "track_count": len(records),
            "export_class_counts": dict(class_counts),
            "export_status_counts": dict(status_counts),
            "recommended_mode_counts": dict(mode_counts),
            "needs_sequence_semantics_count": semantics_count,
            "sequence_command_promotion_allowed": bool(
                command_semantics.get("summary", {}).get("release_sequence_promotion_allowed")
            ),
        },
        "diagnostic_summary": diagnostic_summary(records, oracle_report),
        "command_semantics": {
            "schema": command_semantics.get("schema"),
            "status": command_semantics.get("status"),
            "summary": command_semantics.get("summary", {}),
        },
        "release_gates": [
            "Finite trim candidates are usable where sustained trailing silence is observed, but sequence semantics can still refine exact musical intent.",
            "Loop or held candidates must use an explicit loop-count/fade preview until loop points are decoded.",
            "Unknown active previews are not exact exports.",
            "Independent external-emulator playback validation remains optional for development but open for public release confidence.",
            "Generated WAV/SPC/audio outputs remain local ignored artifacts derived from a user-provided ROM.",
        ],
        "tracks": records,
    }


def render_markdown(plan: dict[str, Any]) -> str:
    rows = [
        "| `{track_id:03d}` | `{track_name}` | `{policy}` | `{export_class}` | `{status}` | `{mode}` | {duration} | {semantics} |".format(
            track_id=record["track_id"],
            track_name=record["track_name"],
            policy=record["policy_duration_class"],
            export_class=record["export_class"],
            status=record["export_status"],
            mode=record["recommended_mode"],
            duration="" if record["duration_seconds"] is None else record["duration_seconds"],
            semantics="yes" if record["needs_sequence_semantics"] else "no",
        )
        for record in plan["tracks"]
    ]
    loop_metadata_count = sum(1 for record in plan["tracks"] if record.get("loop_metadata"))
    gates = [f"- {gate}" for gate in plan["release_gates"]]
    diagnostics = plan.get("diagnostic_summary", {})
    finite_diag = diagnostics.get("finite_end_policy", {})
    loop_diag = diagnostics.get("loop_point_evidence", {})
    preview_diag = diagnostics.get("preview_uncertainty", {})
    return "\n".join(
        [
            "# Audio Export Plan",
            "",
            "Status: export policy ready; exact loop points and some sequence-level duration semantics remain open.",
            "",
            f"- tracks: `{plan['summary']['track_count']}`",
            f"- export classes: `{plan['summary']['export_class_counts']}`",
            f"- export statuses: `{plan['summary']['export_status_counts']}`",
            f"- recommended modes: `{plan['summary']['recommended_mode_counts']}`",
            f"- tracks needing sequence semantics: `{plan['summary']['needs_sequence_semantics_count']}`",
            f"- sequence command promotion allowed: `{plan['summary']['sequence_command_promotion_allowed']}`",
            f"- tracks with loop metadata placeholders: `{loop_metadata_count}`",
            "",
            "## Playback Confidence",
            "",
            f"- all-track near-oracle passed: `{plan['playback_confidence']['all_track_near_oracle_passed']}`",
            f"- independent emulator gate passed: `{plan['playback_confidence']['independent_emulator_gate_passed']}`",
            f"- release-quality playback claim ready: `{plan['playback_confidence']['release_quality_playback_claim_ready']}`",
            "",
            "## Defaults",
            "",
            f"- sample format: `{plan['defaults']['sample_rate']}` Hz, `{plan['defaults']['channels']}` channels, `{plan['defaults']['bits_per_sample']}` bits",
            f"- loop preview: `{plan['defaults']['loop_preview_count']}` loops plus `{plan['defaults']['loop_preview_fade_seconds']}` second fade",
            f"- finite trim policy: {plan['defaults']['finite_trim_tail_policy']}",
            "",
            "## Diagnostic Triage",
            "",
            f"- finite exact trims allowed by PCM silence evidence: `{finite_diag.get('public_exact_trim_count', 0)}`",
            f"- finite trim duration range: `{finite_diag.get('minimum_duration_seconds')}`..`{finite_diag.get('maximum_duration_seconds')}` seconds",
            f"- minimum finite tail silence evidence: `{finite_diag.get('minimum_tail_silence_seconds')}` seconds",
            f"- loop/held tracks with exact loop points missing: `{loop_diag.get('exact_loop_points_missing', 0)} / {loop_diag.get('loop_or_held_count', 0)}`",
            f"- unknown active previews still requiring triage: `{preview_diag.get('unknown_active_preview_count', 0)}`",
            f"- tracks still requiring sequence semantics: `{preview_diag.get('tracks_requiring_sequence_semantics', 0)}`",
            "",
            "## Release Gates",
            "",
            *gates,
            "",
            "## Tracks",
            "",
            "| Track | Name | Policy Class | Export Class | Status | Mode | Duration Seconds | Needs Semantics |",
            "| ---: | --- | --- | --- | --- | --- | ---: | --- |",
            *rows,
            "",
        ]
    )


def main() -> int:
    args = parse_args()
    plan = build_plan(
        Path(args.policy),
        Path(args.measurements),
        Path(args.extended_measurements),
        Path(args.oracle_report),
        Path(args.command_semantics),
    )
    json_path = Path(args.json)
    markdown_path = Path(args.markdown)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
    markdown_path.write_text(render_markdown(plan), encoding="utf-8")
    print(
        "Built audio export plan: "
        f"{plan['summary']['track_count']} tracks, classes {plan['summary']['export_class_counts']}"
    )
    print(f"Wrote {json_path}")
    print(f"Wrote {markdown_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
