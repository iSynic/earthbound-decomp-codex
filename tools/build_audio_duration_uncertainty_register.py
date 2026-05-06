#!/usr/bin/env python3
"""Build a joined register of remaining audio duration uncertainty."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_EXPORT_PLAN = ROOT / "manifests" / "audio-export-plan.json"
DEFAULT_TRIAGE = ROOT / "manifests" / "audio-exact-duration-triage.json"
DEFAULT_ZERO_RESULTS = ROOT / "manifests" / "audio-zero-runtime-probe-results-summary.json"
DEFAULT_NONZERO_RESULTS = ROOT / "manifests" / "audio-nonzero-control-probe-results-summary.json"
DEFAULT_ORACLE_REPORT = ROOT / "manifests" / "audio-oracle-verification-report-all-tracks.json"
DEFAULT_OUTPUT = ROOT / "manifests" / "audio-duration-uncertainty-register.json"
DEFAULT_NOTES = ROOT / "notes" / "audio-duration-uncertainty-register.md"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build audio duration uncertainty register.")
    parser.add_argument("--export-plan", default=str(DEFAULT_EXPORT_PLAN), help="Audio export plan JSON.")
    parser.add_argument("--triage", default=str(DEFAULT_TRIAGE), help="Exact-duration triage JSON.")
    parser.add_argument("--zero-results", default=str(DEFAULT_ZERO_RESULTS), help="0x00 probe results summary JSON.")
    parser.add_argument(
        "--nonzero-results",
        default=str(DEFAULT_NONZERO_RESULTS),
        help="Non-0x00 control probe results summary JSON.",
    )
    parser.add_argument("--oracle-report", default=str(DEFAULT_ORACLE_REPORT), help="Oracle verification report JSON.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Register JSON output.")
    parser.add_argument("--notes", default=str(DEFAULT_NOTES), help="Register markdown output.")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def triage_category_by_track(triage: dict[str, Any]) -> dict[int, str]:
    by_track: dict[int, str] = {}
    for category, packs in triage.get("categories", {}).items():
        for pack in packs:
            for track in pack.get("tracks", []):
                by_track[int(track["track_id"])] = str(category)
    return by_track


def zero_result_by_track(zero_results: dict[str, Any]) -> dict[int, dict[str, Any]]:
    return {int(record["track_id"]): record for record in zero_results.get("results", [])}


def primary_uncertainty(track: dict[str, Any], triage_category: str | None, zero_record: dict[str, Any] | None) -> str:
    export_class = str(track.get("export_class"))
    export_status = str(track.get("export_status"))
    if export_status == "ready" or export_class == "skip_no_audio":
        return "no_duration_uncertainty_for_current_export"
    if export_class == "unmeasured_or_missing":
        return "measurement_missing"
    if zero_record is not None:
        return "zero_runtime_probe_pending"
    if triage_category == "blocked_by_unpromoted_control":
        return "non_zero_control_semantics_pending"
    if export_class == "loop_or_held_candidate":
        return "loop_point_metadata_pending"
    if export_class == "unknown_active_preview":
        return "active_preview_classification_pending"
    if export_class == "finite_or_transition_review_candidate":
        return "finite_transition_review_pending"
    if export_class == "finite_trim_candidate":
        return "pcm_trim_usable_sequence_intent_open"
    return "unclassified_duration_uncertainty"


def primary_next_action(primary: str) -> str:
    actions = {
        "no_duration_uncertainty_for_current_export": "no duration action required for the current export policy",
        "measurement_missing": "regenerate playback/export duration measurements before export",
        "zero_runtime_probe_pending": "run targeted 0x00 runtime probe jobs and collect validated results",
        "non_zero_control_semantics_pending": "decode FD/FE/FF and related control-flow semantics before exact promotion",
        "loop_point_metadata_pending": "decode loop entry/exit metadata before public exact loop export",
        "active_preview_classification_pending": "classify active preview as finite, held, looping, or unresolved",
        "finite_transition_review_pending": "review observed tail/silence as finite ending or transition",
        "pcm_trim_usable_sequence_intent_open": "keep PCM-trim export usable while sequence intent remains advisory",
        "unclassified_duration_uncertainty": "review duration policy classification",
    }
    return actions[primary]


def release_gate_summary(export_plan: dict[str, Any], oracle_report: dict[str, Any]) -> dict[str, Any]:
    playback = export_plan.get("playback_confidence", {})
    gates = oracle_report.get("gate_results", {})
    return {
        "all_track_near_oracle_passed": bool(playback.get("all_track_near_oracle_passed")),
        "independent_emulator_gate_passed": bool(playback.get("independent_emulator_gate_passed")),
        "release_quality_playback_claim_ready": bool(playback.get("release_quality_playback_claim_ready")),
        "oracle_report_gates": gates,
        "release_gate_blocker": (
            "independent_emulator_gate_pending"
            if not bool(playback.get("independent_emulator_gate_passed"))
            else "duration_semantics_pending"
        ),
    }


def build_register(
    export_plan: dict[str, Any],
    triage: dict[str, Any],
    zero_results: dict[str, Any],
    nonzero_results: dict[str, Any],
    oracle_report: dict[str, Any],
) -> dict[str, Any]:
    triage_by_track = triage_category_by_track(triage)
    zero_by_track = zero_result_by_track(zero_results)
    records: list[dict[str, Any]] = []
    primary_counts: Counter[str] = Counter()
    export_class_counts: Counter[str] = Counter()
    next_action_counts: Counter[str] = Counter()
    blocker_counts: Counter[str] = Counter()
    zero_status_counts: Counter[str] = Counter()

    for track in export_plan.get("tracks", []):
        track_id = int(track["track_id"])
        zero_record = zero_by_track.get(track_id)
        triage_category = triage_by_track.get(track_id)
        primary = primary_uncertainty(track, triage_category, zero_record)
        next_action = primary_next_action(primary)
        remaining_blockers = list(zero_record.get("remaining_blockers", [])) if zero_record else []
        record = {
            "track_id": track_id,
            "track_name": track.get("track_name"),
            "export_class": track.get("export_class"),
            "export_status": track.get("export_status"),
            "recommended_mode": track.get("recommended_mode"),
            "duration_seconds": track.get("duration_seconds"),
            "needs_sequence_semantics": bool(track.get("needs_sequence_semantics")),
            "triage_category": triage_category,
            "primary_uncertainty": primary,
            "remaining_blockers": remaining_blockers,
            "zero_probe": {
                "job_id": zero_record.get("job_id"),
                "status": zero_record.get("status"),
                "valid": zero_record.get("valid"),
                "zero_effect_classification": zero_record.get("zero_effect_classification"),
                "result_path": zero_record.get("result_path"),
            }
            if zero_record
            else None,
            "next_action": next_action,
            "public_exact_duration_allowed_now": bool(
                track.get("duration_semantics", {}).get("public_exact_export_allowed")
            ),
        }
        records.append(record)
        primary_counts[primary] += 1
        export_class_counts[str(track.get("export_class"))] += 1
        next_action_counts[next_action] += 1
        zero_status_counts[str(zero_record.get("status")) if zero_record else "not_in_zero_probe_lane"] += 1
        for blocker in remaining_blockers:
            blocker_counts[str(blocker)] += 1

    return {
        "schema": "earthbound-decomp.audio-duration-uncertainty-register.v1",
        "status": "duration_uncertainty_joined_probe_outputs_pending",
        "references": [
            "manifests/audio-export-plan.json",
            "manifests/audio-exact-duration-triage.json",
            "manifests/audio-zero-runtime-probe-results-summary.json",
            "manifests/audio-nonzero-control-probe-results-summary.json",
            "manifests/audio-oracle-verification-report-all-tracks.json",
        ],
        "source_policy": export_plan.get("inputs", {}),
        "summary": {
            "track_count": len(records),
            "primary_uncertainty_track_counts": dict(sorted(primary_counts.items())),
            "export_class_counts": dict(sorted(export_class_counts.items())),
            "zero_probe_status_track_counts": dict(sorted(zero_status_counts.items())),
            "remaining_zero_probe_blocker_track_counts": dict(sorted(blocker_counts.items())),
            "nonzero_control_probe_job_status_counts": nonzero_results.get("summary", {}).get("status_counts", {}),
            "remaining_nonzero_control_probe_blocker_job_counts": nonzero_results.get("summary", {}).get(
                "remaining_blocker_job_counts",
                {},
            ),
            "next_action_track_counts": dict(sorted(next_action_counts.items())),
            "sequence_promotion_allowed": bool(export_plan.get("summary", {}).get("sequence_command_promotion_allowed")),
            "public_exact_duration_track_count": sum(1 for record in records if record["public_exact_duration_allowed_now"]),
        },
        "release_gate_summary": release_gate_summary(export_plan, oracle_report),
        "decision_policy": [
            "Zero-probe evidence can reduce sequence uncertainty only after individual results validate.",
            "Sequence-derived public exact-duration promotion remains blocked when sequence command promotion is false.",
            "Loop-point metadata and active-preview classification remain separate work even after a 0x00 effect is understood.",
            "Independent emulator comparison remains a release confidence gate, not a prerequisite for local diagnostics.",
        ],
        "priority_lanes": [
            {
                "lane": "zero_runtime_probe_pending",
                "track_count": primary_counts.get("zero_runtime_probe_pending", 0),
                "recommended_work": "run the 19 generated zero-runtime probe jobs, then collect and validate results",
            },
            {
                "lane": "non_zero_control_semantics_pending",
                "track_count": primary_counts.get("non_zero_control_semantics_pending", 0),
                "recommended_work": "run the 7 nonzero control probe jobs, starting with the 0x0957 FF/FE/EF mix",
            },
            {
                "lane": "loop_point_metadata_pending",
                "track_count": primary_counts.get("loop_point_metadata_pending", 0),
                "recommended_work": "extract loop entry/exit evidence before exact loop export",
            },
        ],
        "tracks": records,
    }


def render_markdown(data: dict[str, Any]) -> str:
    summary = data["summary"]
    priority_rows = [
        "| `{lane}` | {track_count} | {recommended_work} |".format(**lane)
        for lane in data["priority_lanes"]
    ]
    track_rows = [
        "| `{track_id:03d}` | `{track_name}` | `{export_class}` | `{primary}` | `{blockers}` | {action} |".format(
            track_id=record["track_id"],
            track_name=record["track_name"],
            export_class=record["export_class"],
            primary=record["primary_uncertainty"],
            blockers=record["remaining_blockers"],
            action=record["next_action"],
        )
        for record in data["tracks"]
        if record["primary_uncertainty"] != "no_duration_uncertainty_for_current_export"
    ][:80]
    return "\n".join(
        [
            "# Audio Duration Uncertainty Register",
            "",
            "Status: duration/export uncertainty is joined across export policy, sequence triage, zero/nonzero probe results, and oracle gates.",
            "",
            "## Summary",
            "",
            f"- tracks: `{summary['track_count']}`",
            f"- primary uncertainty: `{summary['primary_uncertainty_track_counts']}`",
            f"- export classes: `{summary['export_class_counts']}`",
            f"- zero probe statuses: `{summary['zero_probe_status_track_counts']}`",
            f"- zero probe blockers: `{summary['remaining_zero_probe_blocker_track_counts']}`",
            f"- nonzero probe statuses: `{summary['nonzero_control_probe_job_status_counts']}`",
            f"- nonzero probe blockers: `{summary['remaining_nonzero_control_probe_blocker_job_counts']}`",
            f"- public exact-duration tracks now: `{summary['public_exact_duration_track_count']}`",
            f"- sequence promotion allowed: `{summary['sequence_promotion_allowed']}`",
            "",
            "## Release Gates",
            "",
            f"- all-track near-oracle passed: `{data['release_gate_summary']['all_track_near_oracle_passed']}`",
            f"- independent emulator gate passed: `{data['release_gate_summary']['independent_emulator_gate_passed']}`",
            f"- release-quality playback claim ready: `{data['release_gate_summary']['release_quality_playback_claim_ready']}`",
            f"- release gate blocker: `{data['release_gate_summary']['release_gate_blocker']}`",
            "",
            "## Priority Lanes",
            "",
            "| Lane | Tracks | Recommended work |",
            "| --- | ---: | --- |",
            *priority_rows,
            "",
            "## Decision Policy",
            "",
            *[f"- {item}" for item in data["decision_policy"]],
            "",
            "## Track Register Sample",
            "",
            "| Track | Name | Export class | Primary uncertainty | Remaining blockers | Next action |",
            "| ---: | --- | --- | --- | --- | --- |",
            *track_rows,
            "",
        ]
    )


def main() -> int:
    args = parse_args()
    data = build_register(
        load_json(Path(args.export_plan)),
        load_json(Path(args.triage)),
        load_json(Path(args.zero_results)),
        load_json(Path(args.nonzero_results)),
        load_json(Path(args.oracle_report)),
    )
    output = Path(args.output)
    notes = Path(args.notes)
    output.parent.mkdir(parents=True, exist_ok=True)
    notes.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    notes.write_text(render_markdown(data), encoding="utf-8")
    print(
        "Built audio duration uncertainty register: "
        f"{data['summary']['track_count']} tracks, "
        f"{data['summary']['primary_uncertainty_track_counts']}"
    )
    print(f"Wrote {output}")
    print(f"Wrote {notes}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
