#!/usr/bin/env python3
"""Build a coverage report for residual audio duration uncertainty lanes."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_UNCERTAINTY = ROOT / "manifests" / "audio-duration-uncertainty-register.json"
DEFAULT_EXPORT_PLAN = ROOT / "manifests" / "audio-export-plan.json"
DEFAULT_OUTPUT = ROOT / "manifests" / "audio-residual-uncertainty-coverage-report.json"
DEFAULT_NOTES = ROOT / "notes" / "audio-residual-uncertainty-coverage-report.md"
RESIDUAL_LANES = {
    "active_preview_classification_pending",
    "measurement_missing",
    "no_duration_uncertainty_for_current_export",
    "pcm_trim_usable_sequence_intent_open",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build residual duration uncertainty coverage report.")
    parser.add_argument("--uncertainty", default=str(DEFAULT_UNCERTAINTY), help="Duration uncertainty register JSON.")
    parser.add_argument("--export-plan", default=str(DEFAULT_EXPORT_PLAN), help="Audio export plan JSON.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Coverage report JSON output.")
    parser.add_argument("--notes", default=str(DEFAULT_NOTES), help="Coverage report markdown output.")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def by_track(records: list[dict[str, Any]]) -> dict[int, dict[str, Any]]:
    return {int(record["track_id"]): record for record in records}


def recommended_action(primary_uncertainty: str, public_exact_allowed: bool) -> str:
    if primary_uncertainty == "measurement_missing":
        return "measure_or_confirm_skip_policy_before_public_export"
    if primary_uncertainty == "active_preview_classification_pending":
        return "classify_active_preview_or_find_exact_end_before_public_exact_export"
    if primary_uncertainty == "pcm_trim_usable_sequence_intent_open":
        return "keep_public_pcm_trim_but_collect_sequence_intent_evidence_before_semantic_promotion"
    if primary_uncertainty == "no_duration_uncertainty_for_current_export" and public_exact_allowed:
        return "retain_ready_skip_no_audio_policy"
    return "review_residual_duration_policy"


def record_for_track(uncertainty_record: dict[str, Any], export_record: dict[str, Any]) -> dict[str, Any]:
    semantics = export_record.get("duration_semantics", {})
    public_exact_allowed = bool(semantics.get("public_exact_export_allowed"))
    primary_uncertainty = str(uncertainty_record.get("primary_uncertainty"))
    return {
        "track_id": int(uncertainty_record["track_id"]),
        "track_name": uncertainty_record["track_name"],
        "primary_uncertainty": primary_uncertainty,
        "export_class": uncertainty_record.get("export_class"),
        "export_status": export_record.get("export_status"),
        "recommended_mode": uncertainty_record.get("recommended_mode"),
        "duration_seconds": uncertainty_record.get("duration_seconds"),
        "public_exact_export_allowed": public_exact_allowed,
        "duration_semantics_classification": semantics.get("classification"),
        "sequence_command_promotion_allowed": bool(semantics.get("sequence_command_promotion_allowed")),
        "current_policy_state": (
            "public_exact_ready_with_sequence_intent_open"
            if public_exact_allowed and primary_uncertainty == "pcm_trim_usable_sequence_intent_open"
            else "public_exact_ready"
            if public_exact_allowed
            else "public_exact_blocked"
        ),
        "recommended_action": recommended_action(primary_uncertainty, public_exact_allowed),
    }


def build_report(uncertainty: dict[str, Any], export_plan: dict[str, Any]) -> dict[str, Any]:
    export_by_id = by_track(export_plan.get("tracks", []))
    records = [
        record_for_track(record, export_by_id[int(record["track_id"])])
        for record in uncertainty.get("tracks", [])
        if record.get("primary_uncertainty") in RESIDUAL_LANES
    ]
    records.sort(key=lambda record: int(record["track_id"]))
    uncertainty_counts: Counter[str] = Counter(str(record["primary_uncertainty"]) for record in records)
    policy_counts: Counter[str] = Counter(str(record["current_policy_state"]) for record in records)
    export_counts: Counter[str] = Counter(str(record["export_class"]) for record in records)
    public_exact_count = sum(1 for record in records if record["public_exact_export_allowed"])
    return {
        "schema": "earthbound-decomp.audio-residual-uncertainty-coverage-report.v1",
        "status": "residual_uncertainty_coverage_ready_policy_preserved",
        "references": [
            "manifests/audio-duration-uncertainty-register.json",
            "manifests/audio-export-plan.json",
        ],
        "summary": {
            "record_count": len(records),
            "track_ids": [int(record["track_id"]) for record in records],
            "primary_uncertainty_counts": dict(sorted(uncertainty_counts.items())),
            "export_class_counts": dict(sorted(export_counts.items())),
            "current_policy_state_counts": dict(sorted(policy_counts.items())),
            "public_exact_allowed_count": public_exact_count,
            "public_exact_blocked_count": len(records) - public_exact_count,
            "pcm_trim_sequence_intent_open_count": int(uncertainty_counts.get("pcm_trim_usable_sequence_intent_open", 0)),
            "behavior_change_allowed": False,
            "promotion_allowed_by_report": False,
        },
        "coverage_policy": [
            "This report covers residual duration lanes not already owned by control, loop, finite-tail, or independent-oracle coverage reports.",
            "Public PCM-trim readiness is distinct from semantic sequence-intent promotion.",
            "Measurement-missing and active-preview residual tracks remain public-exact blockers.",
            "The no-audio skip track is recorded as ready and should not be treated as an audio duration blocker.",
        ],
        "records": records,
    }


def render_markdown(data: dict[str, Any]) -> str:
    summary = data["summary"]
    rows = [
        "| {track_id:03d} | `{track_name}` | `{uncertainty}` | `{export_class}` | `{state}` | `{public}` | {action} |".format(
            track_id=record["track_id"],
            track_name=record["track_name"],
            uncertainty=record["primary_uncertainty"],
            export_class=record["export_class"],
            state=record["current_policy_state"],
            public=record["public_exact_export_allowed"],
            action=record["recommended_action"],
        )
        for record in data["records"]
    ]
    return "\n".join(
        [
            "# Audio Residual Uncertainty Coverage Report",
            "",
            "Status: residual duration uncertainty lanes are mapped; current playback/export behavior is preserved.",
            "",
            "## Summary",
            "",
            f"- records: `{summary['record_count']}`",
            f"- primary uncertainty counts: `{summary['primary_uncertainty_counts']}`",
            f"- export class counts: `{summary['export_class_counts']}`",
            f"- policy states: `{summary['current_policy_state_counts']}`",
            f"- public exact allowed: `{summary['public_exact_allowed_count']}`",
            f"- public exact blocked: `{summary['public_exact_blocked_count']}`",
            f"- PCM trim sequence-intent open: `{summary['pcm_trim_sequence_intent_open_count']}`",
            "",
            "## Records",
            "",
            "| Track | Name | Primary uncertainty | Export class | Policy state | Public exact | Recommended action |",
            "| ---: | --- | --- | --- | --- | --- | --- |",
            *rows,
            "",
            "## Coverage Policy",
            "",
            *[f"- {item}" for item in data["coverage_policy"]],
            "",
            "## Remaining Uncertainty",
            "",
            "- `NONE` still needs measurement or explicit skip policy before public export.",
            "- `WHAT_THE_HECK` still needs active-preview classification before public exact export.",
            "- Five PCM-trim tracks are public-exact ready from PCM evidence but still need sequence-intent evidence before semantic promotion.",
            "",
        ]
    )


def main() -> int:
    args = parse_args()
    data = build_report(load_json(Path(args.uncertainty)), load_json(Path(args.export_plan)))
    output = Path(args.output)
    notes = Path(args.notes)
    output.parent.mkdir(parents=True, exist_ok=True)
    notes.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    notes.write_text(render_markdown(data), encoding="utf-8")
    print(
        "Built residual uncertainty coverage report: "
        f"{data['summary']['record_count']} records, "
        f"{data['summary']['public_exact_blocked_count']} blocked"
    )
    print(f"Wrote {output}")
    print(f"Wrote {notes}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
