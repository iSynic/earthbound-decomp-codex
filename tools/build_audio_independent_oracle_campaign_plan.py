#!/usr/bin/env python3
"""Build the independent external-emulator audio oracle campaign plan."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ORACLE_PLAN = ROOT / "manifests" / "audio-oracle-comparison-plan-all-tracks.json"
DEFAULT_ORACLE_REPORT = ROOT / "manifests" / "audio-oracle-verification-report-all-tracks.json"
DEFAULT_UNCERTAINTY = ROOT / "manifests" / "audio-duration-uncertainty-register.json"
DEFAULT_OUTPUT = ROOT / "manifests" / "audio-independent-oracle-campaign-plan.json"
DEFAULT_NOTES = ROOT / "notes" / "audio-independent-oracle-campaign-plan.md"

REPRESENTATIVE_CORE_TRACKS = [1, 17, 32, 46, 171, 173, 175]
LANE_COVERAGE_TRACKS = [10, 8, 5, 12]
PROBE_SOURCE_TRACKS = [25, 115, 123, 135, 161]
ACCEPTED_EXTERNAL_ORACLES = ["mesen2", "bsnes_higan", "mednafen"]
METADATA_FIELDS = [
    "oracle_id",
    "oracle_kind",
    "independent_emulator_capture",
    "emulator_version",
    "capture_command",
    "audio_settings",
    "source_spc_sha1",
    "reference_wav_sha1",
    "render_sample_rate",
    "channels",
    "bits_per_sample",
    "duration_seconds",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build independent external-emulator oracle campaign plan.")
    parser.add_argument("--oracle-plan", default=str(DEFAULT_ORACLE_PLAN), help="All-track oracle plan JSON.")
    parser.add_argument("--oracle-report", default=str(DEFAULT_ORACLE_REPORT), help="All-track oracle report JSON.")
    parser.add_argument("--uncertainty", default=str(DEFAULT_UNCERTAINTY), help="Duration uncertainty register JSON.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Independent oracle campaign JSON output.")
    parser.add_argument("--notes", default=str(DEFAULT_NOTES), help="Independent oracle campaign markdown output.")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def repo_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def by_track(records: list[dict[str, Any]]) -> dict[int, dict[str, Any]]:
    return {int(record["track_id"]): record for record in records}


def campaign_phase(track_id: int) -> str:
    if track_id in REPRESENTATIVE_CORE_TRACKS:
        return "independent-representative-core"
    if track_id in LANE_COVERAGE_TRACKS:
        return "independent-duration-uncertainty-coverage"
    return "independent-probe-source-coverage"


def priority_reason(track_id: int, uncertainty: dict[str, Any], oracle_job: dict[str, Any]) -> str:
    if track_id == 1:
        return "zero-runtime baseline and active-preview uncertainty anchor"
    if track_id == 17:
        return "first non-zero control-semantics source candidate"
    if track_id == 32:
        return "finite/transition candidate with zero-runtime uncertainty"
    if track_id == 46:
        return "long-standing ONETT renderer/oracle smoke anchor"
    if track_id in {171, 173}:
        return "loop/held preview track with zero-runtime evidence still pending"
    if track_id == 175:
        return "finite title-screen transition candidate from zero-runtime lane"
    primary = str(uncertainty.get("primary_uncertainty", "unknown"))
    focus = str(oracle_job.get("diagnostic_focus", "unknown"))
    return f"coverage for {primary} with {focus} oracle focus"


def import_command(track_id: int) -> str:
    return (
        "python tools/import_audio_oracle_reference_capture.py "
        "--plan manifests/audio-oracle-comparison-plan-all-tracks.json "
        f"--track-id {track_id} --spc <external-capture.spc> --wav <external-render.wav> "
        "--oracle-id <mesen2|bsnes_higan|mednafen> "
        "--emulator-version <version> --capture-command <command> --audio-settings <settings> --overwrite"
    )


def capture_validator_command(track_id: int) -> str:
    return (
        "python tools/validate_audio_oracle_reference_capture.py "
        "--plan manifests/audio-oracle-comparison-plan-all-tracks.json "
        f"--track-id {track_id}"
    )


def build_campaign_jobs(
    oracle_plan: dict[str, Any],
    oracle_report: dict[str, Any],
    uncertainty: dict[str, Any],
) -> list[dict[str, Any]]:
    oracle_by_track = by_track(oracle_plan.get("jobs", []))
    report_by_track = by_track(oracle_report.get("records", []))
    uncertainty_by_track = by_track(uncertainty.get("tracks", []))
    selected_track_ids = REPRESENTATIVE_CORE_TRACKS + LANE_COVERAGE_TRACKS + PROBE_SOURCE_TRACKS
    jobs: list[dict[str, Any]] = []
    for order, track_id in enumerate(selected_track_ids, start=1):
        oracle_job = oracle_by_track[track_id]
        report_record = report_by_track[track_id]
        uncertainty_record = uncertainty_by_track[track_id]
        phase = campaign_phase(track_id)
        outputs = oracle_job["reference_capture_outputs"]
        jobs.append(
            {
                "campaign_job_id": f"independent-oracle-{oracle_job['job_id']}",
                "execution_order": order,
                "phase": phase,
                "priority_reason": priority_reason(track_id, uncertainty_record, oracle_job),
                "job_id": oracle_job["job_id"],
                "track_id": track_id,
                "track_name": oracle_job["track_name"],
                "diagnostic_focus": oracle_job.get("diagnostic_focus"),
                "primary_uncertainty": uncertainty_record.get("primary_uncertainty"),
                "export_class": uncertainty_record.get("export_class"),
                "duration_seconds": uncertainty_record.get("duration_seconds"),
                "source_spc": oracle_job.get("source_spc", {}),
                "source_render": oracle_job.get("source_render", {}),
                "reference_capture_outputs": outputs,
                "current_near_oracle_status": report_record.get("status"),
                "current_near_oracle_id": report_record.get("oracle_id"),
                "current_independent_emulator_capture": bool(report_record.get("independent_emulator_capture")),
                "independent_capture_required": True,
                "accepted_oracles": ACCEPTED_EXTERNAL_ORACLES,
                "expected_capture_metadata_fields": METADATA_FIELDS,
                "acceptance_gates": [
                    "capture_metadata.independent_emulator_capture must be true",
                    "capture_metadata.oracle_id must identify mesen2, bsnes/higan, or mednafen",
                    "source_spc_sha1 must match the planned source_spc.sha1",
                    "reference WAV must be 32 kHz stereo 16-bit PCM and at least the planned duration",
                    "collect_audio_oracle_comparison_results must classify the track as pass, audio_equivalent_state_delta, explained_timing_offset, or investigated_mismatch",
                    "any mismatch must be classified before release-quality playback is claimed",
                ],
                "import_command": import_command(track_id),
                "dry_run_command": f"python tools/run_audio_independent_oracle_campaign.py --job-id {oracle_job['job_id']} --mode dry-run-plan",
                "audit_command": f"python tools/run_audio_independent_oracle_campaign.py --job-id {oracle_job['job_id']} --mode audit-existing-captures",
                "capture_validator_command": capture_validator_command(track_id),
                "collect_command": (
                    "python tools/collect_audio_oracle_comparison_results.py "
                    "--plan manifests/audio-oracle-comparison-plan-all-tracks.json "
                    "--summary build/audio/oracle-comparison-all-tracks/oracle-comparison-summary.json"
                ),
                "report_refresh_command": (
                    "python tools/build_audio_oracle_verification_report.py "
                    "--summary build/audio/oracle-comparison-all-tracks/oracle-comparison-summary.json "
                    "--json manifests/audio-oracle-verification-report-all-tracks.json "
                    "--markdown notes/audio-oracle-verification-report-all-tracks.md"
                ),
                "result_validator": "python tools/validate_audio_oracle_verification_report.py manifests/audio-oracle-verification-report-all-tracks.json --require-representative-pass",
                "promotion_allowed_by_campaign": False,
            }
        )
    return jobs


def build_plan(
    oracle_plan: dict[str, Any],
    oracle_report: dict[str, Any],
    uncertainty: dict[str, Any],
) -> dict[str, Any]:
    jobs = build_campaign_jobs(oracle_plan, oracle_report, uncertainty)
    phase_counts: Counter[str] = Counter(str(job["phase"]) for job in jobs)
    focus_counts: Counter[str] = Counter(str(job["diagnostic_focus"]) for job in jobs)
    primary_uncertainty_counts: Counter[str] = Counter(str(job["primary_uncertainty"]) for job in jobs)
    report_gates = oracle_report.get("gate_results", {})
    independent_count = sum(1 for record in oracle_report.get("records", []) if record.get("independent_emulator_capture"))
    return {
        "schema": "earthbound-decomp.audio-independent-oracle-campaign-plan.v1",
        "status": "independent_external_oracle_campaign_ready",
        "references": [
            "manifests/audio-oracle-comparison-plan-all-tracks.json",
            "manifests/audio-oracle-verification-report-all-tracks.json",
            "manifests/audio-duration-uncertainty-register.json",
            "notes/audio-oracle-verification-report-all-tracks.md",
        ],
        "summary": {
            "oracle_job_count": int(oracle_plan.get("job_count", 0)),
            "near_oracle_pass_count": sum(int(count) for count in oracle_report.get("status_counts", {}).values()),
            "independent_capture_count": independent_count,
            "missing_independent_capture_count": max(0, int(oracle_report.get("job_count", 0)) - independent_count),
            "representative_campaign_job_count": len(jobs),
            "phase_job_counts": dict(sorted(phase_counts.items())),
            "diagnostic_focus_counts": dict(sorted(focus_counts.items())),
            "representative_primary_uncertainty_counts": dict(sorted(primary_uncertainty_counts.items())),
            "release_quality_playback_claim_ready": bool(report_gates.get("release_quality_playback_claim_ready")),
            "independent_emulator_gate_passed": bool(report_gates.get("independent_emulator_gate_passed")),
            "all_track_near_oracle_passed": bool(report_gates.get("all_track_oracle_gate_passed")),
            "sequence_promotion_allowed_by_campaign": False,
        },
        "campaign_policy": [
            "This plan selects a bounded representative subset for independent external-emulator capture.",
            "The campaign does not change playback/export behavior and cannot promote sequence-derived exact durations.",
            "External emulator captures are ROM-derived generated evidence and must stay under ignored build/audio paths.",
            "Passing this representative campaign is evidence for the independent gate; all-track independent capture remains a separate expansion decision.",
        ],
        "capture_contract": {
            "accepted_oracles": ACCEPTED_EXTERNAL_ORACLES,
            "minimum_metadata_fields": METADATA_FIELDS,
            "required_importer": "tools/import_audio_oracle_reference_capture.py",
            "required_independent_flag": True,
            "comparison_thresholds": oracle_plan.get("comparison_policy", {}).get("recommended_pcm_thresholds", {}),
        },
        "post_capture_validation_commands": [
            "python tools/run_audio_independent_oracle_campaign.py --limit 1 --mode dry-run-plan",
            "python tools/validate_audio_independent_oracle_campaign_run_summary.py",
            "python tools/run_audio_independent_oracle_campaign.py --limit 1 --mode audit-existing-captures",
            "python tools/validate_audio_independent_oracle_campaign_run_summary.py",
            "python tools/validate_audio_oracle_reference_capture.py --plan manifests/audio-oracle-comparison-plan-all-tracks.json --track-id 1 --allow-missing",
            "python tools/validate_audio_oracle_comparison_plan.py manifests/audio-oracle-comparison-plan-all-tracks.json --allow-missing-source-outputs",
            "python tools/collect_audio_oracle_comparison_results.py --plan manifests/audio-oracle-comparison-plan-all-tracks.json --summary build/audio/oracle-comparison-all-tracks/oracle-comparison-summary.json",
            "python tools/validate_audio_oracle_comparison_summary.py build/audio/oracle-comparison-all-tracks/oracle-comparison-summary.json --require-compared",
            "python tools/build_audio_oracle_verification_report.py --summary build/audio/oracle-comparison-all-tracks/oracle-comparison-summary.json --json manifests/audio-oracle-verification-report-all-tracks.json --markdown notes/audio-oracle-verification-report-all-tracks.md",
            "python tools/validate_audio_oracle_verification_report.py manifests/audio-oracle-verification-report-all-tracks.json --require-representative-pass",
            "python tools/build_audio_duration_uncertainty_register.py",
            "python tools/validate_audio_duration_uncertainty_register.py",
        ],
        "campaign_jobs": jobs,
    }


def render_markdown(data: dict[str, Any]) -> str:
    summary = data["summary"]
    rows = [
        "| {order} | `{phase}` | {track_id:03d} | `{track_name}` | `{focus}` | `{uncertainty}` | {reason} |".format(
            order=job["execution_order"],
            phase=job["phase"],
            track_id=job["track_id"],
            track_name=job["track_name"],
            focus=job["diagnostic_focus"],
            uncertainty=job["primary_uncertainty"],
            reason=job["priority_reason"],
        )
        for job in data["campaign_jobs"]
    ]
    return "\n".join(
        [
            "# Audio Independent Oracle Campaign Plan",
            "",
            "Status: independent external-emulator representative capture campaign is ready; current playback/export behavior remains unchanged.",
            "",
            "## Gate State",
            "",
            f"- all-track near-oracle passed: `{summary['all_track_near_oracle_passed']}`",
            f"- independent emulator gate passed: `{summary['independent_emulator_gate_passed']}`",
            f"- release-quality playback claim ready: `{summary['release_quality_playback_claim_ready']}`",
            f"- near-oracle pass count: `{summary['near_oracle_pass_count']} / {summary['oracle_job_count']}`",
            f"- independent captures: `{summary['independent_capture_count']} / {summary['oracle_job_count']}`",
            f"- missing independent captures: `{summary['missing_independent_capture_count']}`",
            f"- representative campaign jobs: `{summary['representative_campaign_job_count']}`",
            f"- representative primary uncertainty counts: `{summary['representative_primary_uncertainty_counts']}`",
            f"- diagnostic focus counts: `{summary['diagnostic_focus_counts']}`",
            "",
            "## Campaign Policy",
            "",
            *[f"- {item}" for item in data["campaign_policy"]],
            "",
            "## Capture Contract",
            "",
            f"- accepted oracles: `{data['capture_contract']['accepted_oracles']}`",
            f"- required importer: `{data['capture_contract']['required_importer']}`",
            f"- required independent flag: `{data['capture_contract']['required_independent_flag']}`",
            f"- minimum metadata fields: `{data['capture_contract']['minimum_metadata_fields']}`",
            "",
            "## Representative Jobs",
            "",
            "| Order | Phase | Track | Name | Focus | Primary uncertainty | Reason |",
            "| ---: | --- | ---: | --- | --- | --- | --- |",
            *rows,
            "",
            "## Post Capture Validation",
            "",
            *[f"- `{command}`" for command in data["post_capture_validation_commands"]],
            "",
            "## Remaining Uncertainty",
            "",
            "- The campaign closes only the representative independent-emulator evidence gap after real captures are imported.",
            "- Non-zero control semantics, zero-runtime proof, loop-point metadata, finite-transition review, and measurement gaps remain governed by the duration uncertainty register.",
            "- All-track independent capture can be staged after the representative campaign proves the external capture/import path.",
            "",
        ]
    )


def main() -> int:
    args = parse_args()
    data = build_plan(
        load_json(Path(args.oracle_plan)),
        load_json(Path(args.oracle_report)),
        load_json(Path(args.uncertainty)),
    )
    output = Path(args.output)
    notes = Path(args.notes)
    output.parent.mkdir(parents=True, exist_ok=True)
    notes.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    notes.write_text(render_markdown(data), encoding="utf-8")
    print(
        "Built independent oracle campaign plan: "
        f"{data['summary']['representative_campaign_job_count']} jobs, "
        f"{data['summary']['missing_independent_capture_count']} independent captures missing"
    )
    print(f"Wrote {output}")
    print(f"Wrote {notes}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
