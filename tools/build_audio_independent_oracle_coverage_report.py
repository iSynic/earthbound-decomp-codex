#!/usr/bin/env python3
"""Build a coverage report for independent external-emulator audio oracle capture."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ORACLE_REPORT = ROOT / "manifests" / "audio-oracle-verification-report-all-tracks.json"
DEFAULT_CAMPAIGN = ROOT / "manifests" / "audio-independent-oracle-campaign-plan.json"
DEFAULT_OUTPUT = ROOT / "manifests" / "audio-independent-oracle-coverage-report.json"
DEFAULT_NOTES = ROOT / "notes" / "audio-independent-oracle-coverage-report.md"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build independent oracle coverage report.")
    parser.add_argument("--oracle-report", default=str(DEFAULT_ORACLE_REPORT), help="All-track oracle report JSON.")
    parser.add_argument("--campaign", default=str(DEFAULT_CAMPAIGN), help="Independent oracle campaign plan JSON.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Coverage report JSON output.")
    parser.add_argument("--notes", default=str(DEFAULT_NOTES), help="Coverage report markdown output.")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def campaign_record(job: dict[str, Any]) -> dict[str, Any]:
    return {
        "execution_order": int(job["execution_order"]),
        "campaign_job_id": job["campaign_job_id"],
        "job_id": job["job_id"],
        "track_id": int(job["track_id"]),
        "track_name": job["track_name"],
        "phase": job["phase"],
        "priority_reason": job.get("priority_reason"),
        "diagnostic_focus": job.get("diagnostic_focus"),
        "primary_uncertainty": job.get("primary_uncertainty"),
        "export_class": job.get("export_class"),
        "duration_seconds": job.get("duration_seconds"),
        "current_near_oracle_status": job.get("current_near_oracle_status"),
        "current_near_oracle_id": job.get("current_near_oracle_id"),
        "current_independent_emulator_capture": bool(job.get("current_independent_emulator_capture")),
        "independent_capture_required": bool(job.get("independent_capture_required")),
        "accepted_oracles": job.get("accepted_oracles", []),
        "capture_metadata_path": job.get("reference_capture_outputs", {}).get("capture_metadata"),
        "comparison_result_path": job.get("reference_capture_outputs", {}).get("comparison_result"),
        "import_command": job.get("import_command"),
        "audit_command": job.get("audit_command"),
        "capture_validator_command": job.get("capture_validator_command"),
        "promotion_allowed_by_campaign": bool(job.get("promotion_allowed_by_campaign")),
    }


def build_report(oracle_report: dict[str, Any], campaign: dict[str, Any]) -> dict[str, Any]:
    campaign_records = [campaign_record(job) for job in campaign.get("campaign_jobs", [])]
    campaign_records.sort(key=lambda record: int(record["execution_order"]))
    phase_counts: Counter[str] = Counter(str(record["phase"]) for record in campaign_records)
    focus_counts: Counter[str] = Counter(str(record["diagnostic_focus"]) for record in campaign_records)
    uncertainty_counts: Counter[str] = Counter(str(record["primary_uncertainty"]) for record in campaign_records)
    missing_representative = sum(1 for record in campaign_records if not record["current_independent_emulator_capture"])
    gate_results = oracle_report.get("gate_results", {})
    independent_capture_count = sum(
        1 for record in oracle_report.get("records", []) if record.get("independent_emulator_capture")
    )
    job_count = int(oracle_report.get("job_count", 0))
    return {
        "schema": "earthbound-decomp.audio-independent-oracle-coverage-report.v1",
        "status": "independent_oracle_coverage_ready_external_captures_pending",
        "references": [
            "manifests/audio-oracle-verification-report-all-tracks.json",
            "manifests/audio-independent-oracle-campaign-plan.json",
        ],
        "source_report_status": oracle_report.get("status"),
        "source_campaign_status": campaign.get("status"),
        "summary": {
            "oracle_job_count": job_count,
            "near_oracle_pass_count": sum(int(count) for count in oracle_report.get("status_counts", {}).values()),
            "status_counts": oracle_report.get("status_counts", {}),
            "independent_capture_count": independent_capture_count,
            "missing_independent_capture_count": max(0, job_count - independent_capture_count),
            "representative_campaign_job_count": len(campaign_records),
            "representative_missing_independent_capture_count": missing_representative,
            "phase_job_counts": dict(sorted(phase_counts.items())),
            "diagnostic_focus_counts": dict(sorted(focus_counts.items())),
            "representative_primary_uncertainty_counts": dict(sorted(uncertainty_counts.items())),
            "all_track_near_oracle_passed": bool(gate_results.get("all_track_oracle_gate_passed")),
            "representative_oracle_gate_passed": bool(gate_results.get("representative_oracle_gate_passed")),
            "independent_emulator_gate_passed": bool(gate_results.get("independent_emulator_gate_passed")),
            "release_quality_playback_claim_ready": bool(gate_results.get("release_quality_playback_claim_ready")),
            "promotion_allowed_by_report": False,
        },
        "capture_policy": [
            "Near-oracle equivalence is already all-track green but is not independent external-emulator evidence.",
            "Representative campaign capture should be completed before expanding to all-track independent capture.",
            "Accepted independent captures must use mesen2, bsnes/higan, or mednafen metadata and pass import validation.",
            "This report does not change playback/export behavior and cannot promote release-quality playback claims.",
        ],
        "campaign_records": campaign_records,
    }


def render_markdown(data: dict[str, Any]) -> str:
    summary = data["summary"]
    rows = [
        "| {order} | {track_id:03d} | `{track_name}` | `{phase}` | `{uncertainty}` | `{focus}` | `{independent}` |".format(
            order=record["execution_order"],
            track_id=record["track_id"],
            track_name=record["track_name"],
            phase=record["phase"],
            uncertainty=record["primary_uncertainty"],
            focus=record["diagnostic_focus"],
            independent=record["current_independent_emulator_capture"],
        )
        for record in data["campaign_records"]
    ]
    return "\n".join(
        [
            "# Audio Independent Oracle Coverage Report",
            "",
            "Status: near-oracle coverage is all-track green; independent external-emulator captures remain pending.",
            "",
            "## Summary",
            "",
            f"- oracle jobs: `{summary['oracle_job_count']}`",
            f"- near-oracle pass count: `{summary['near_oracle_pass_count']}`",
            f"- status counts: `{summary['status_counts']}`",
            f"- independent captures: `{summary['independent_capture_count']}`",
            f"- missing independent captures: `{summary['missing_independent_capture_count']}`",
            f"- representative campaign jobs: `{summary['representative_campaign_job_count']}`",
            f"- representative missing independent captures: `{summary['representative_missing_independent_capture_count']}`",
            f"- phase jobs: `{summary['phase_job_counts']}`",
            f"- representative uncertainty counts: `{summary['representative_primary_uncertainty_counts']}`",
            f"- all-track near oracle passed: `{summary['all_track_near_oracle_passed']}`",
            f"- independent emulator gate passed: `{summary['independent_emulator_gate_passed']}`",
            f"- release-quality playback claim ready: `{summary['release_quality_playback_claim_ready']}`",
            "",
            "## Representative Campaign",
            "",
            "| Order | Track | Name | Phase | Primary uncertainty | Focus | Independent capture |",
            "| ---: | ---: | --- | --- | --- | --- | --- |",
            *rows,
            "",
            "## Capture Policy",
            "",
            *[f"- {item}" for item in data["capture_policy"]],
            "",
            "## Remaining Uncertainty",
            "",
            "- All 16 representative campaign captures are still missing independent external-emulator evidence.",
            "- All 190 all-track oracle jobs are missing independent capture metadata.",
            "- Release-quality playback claims remain blocked until independent captures are imported and validated.",
            "",
        ]
    )


def main() -> int:
    args = parse_args()
    data = build_report(load_json(Path(args.oracle_report)), load_json(Path(args.campaign)))
    output = Path(args.output)
    notes = Path(args.notes)
    output.parent.mkdir(parents=True, exist_ok=True)
    notes.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    notes.write_text(render_markdown(data), encoding="utf-8")
    print(
        "Built independent oracle coverage report: "
        f"{data['summary']['near_oracle_pass_count']} near-oracle passes, "
        f"{data['summary']['missing_independent_capture_count']} independent captures missing"
    )
    print(f"Wrote {output}")
    print(f"Wrote {notes}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
