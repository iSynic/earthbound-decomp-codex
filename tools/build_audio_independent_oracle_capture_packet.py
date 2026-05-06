#!/usr/bin/env python3
"""Build an execution packet for representative independent oracle captures."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CAMPAIGN = ROOT / "manifests" / "audio-independent-oracle-campaign-plan.json"
DEFAULT_COVERAGE = ROOT / "manifests" / "audio-independent-oracle-coverage-report.json"
DEFAULT_NEXT_ACTIONS = ROOT / "manifests" / "audio-duration-next-actions-plan.json"
DEFAULT_OUTPUT = ROOT / "manifests" / "audio-independent-oracle-capture-packet.json"
DEFAULT_NOTES = ROOT / "notes" / "audio-independent-oracle-capture-packet.md"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build independent oracle capture packet.")
    parser.add_argument("--campaign", default=str(DEFAULT_CAMPAIGN), help="Independent oracle campaign plan JSON.")
    parser.add_argument("--coverage", default=str(DEFAULT_COVERAGE), help="Independent oracle coverage report JSON.")
    parser.add_argument("--next-actions", default=str(DEFAULT_NEXT_ACTIONS), help="Audio duration next-actions plan JSON.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Capture packet JSON output.")
    parser.add_argument("--notes", default=str(DEFAULT_NOTES), help="Capture packet markdown output.")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def capture_record(job: dict[str, Any]) -> dict[str, Any]:
    outputs = job.get("reference_capture_outputs", {})
    source_spc = job.get("source_spc", {})
    source_render = job.get("source_render", {})
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
        "planned_duration_seconds": job.get("duration_seconds"),
        "current_near_oracle_status": job.get("current_near_oracle_status"),
        "current_independent_emulator_capture": bool(job.get("current_independent_emulator_capture")),
        "independent_capture_required": bool(job.get("independent_capture_required")),
        "accepted_oracles": job.get("accepted_oracles", []),
        "source_spc": {
            "path": source_spc.get("path"),
            "sha1": source_spc.get("sha1"),
            "bytes": source_spc.get("bytes"),
        },
        "source_render": {
            "path": source_render.get("path"),
            "sha1": source_render.get("sha1"),
            "bytes": source_render.get("bytes"),
        },
        "capture_outputs": {
            "spc_snapshot": outputs.get("spc_snapshot"),
            "pcm_wav": outputs.get("pcm_wav"),
            "capture_metadata": outputs.get("capture_metadata"),
            "comparison_result": outputs.get("comparison_result"),
        },
        "expected_capture_metadata_fields": job.get("expected_capture_metadata_fields", []),
        "acceptance_gates": job.get("acceptance_gates", []),
        "commands": {
            "dry_run": job.get("dry_run_command"),
            "audit": job.get("audit_command"),
            "import": job.get("import_command"),
            "validate_capture": job.get("capture_validator_command"),
            "collect_comparison": job.get("collect_command"),
            "refresh_report": job.get("report_refresh_command"),
            "validate_report": job.get("result_validator"),
        },
        "promotion_allowed_by_packet": False,
        "behavior_change_allowed": False,
    }


def grouped_jobs(records: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        groups[str(record.get(key))].append(record)
    batches: list[dict[str, Any]] = []
    for value, items in groups.items():
        items.sort(key=lambda item: int(item["execution_order"]))
        batches.append(
            {
                key: value,
                "job_count": len(items),
                "execution_orders": [int(item["execution_order"]) for item in items],
                "track_ids": [int(item["track_id"]) for item in items],
                "job_ids": [str(item["job_id"]) for item in items],
            }
        )
    return sorted(batches, key=lambda item: min(item["execution_orders"]))


def find_next_action_lane(next_actions: dict[str, Any]) -> dict[str, Any]:
    for lane in next_actions.get("priority_lanes", []):
        if lane.get("lane_id") == "independent_oracle_representative_capture":
            return lane
    return {}


def build_packet(campaign: dict[str, Any], coverage: dict[str, Any], next_actions: dict[str, Any]) -> dict[str, Any]:
    records = [capture_record(job) for job in campaign.get("campaign_jobs", [])]
    records.sort(key=lambda record: int(record["execution_order"]))
    phase_counts = Counter(str(record["phase"]) for record in records)
    uncertainty_counts = Counter(str(record["primary_uncertainty"]) for record in records)
    focus_counts = Counter(str(record["diagnostic_focus"]) for record in records)
    lane = find_next_action_lane(next_actions)
    coverage_summary = coverage.get("summary", {})
    capture_contract = campaign.get("capture_contract", {})
    return {
        "schema": "earthbound-decomp.audio-independent-oracle-capture-packet.v1",
        "status": "independent_oracle_capture_packet_ready_external_inputs_required",
        "references": [
            "manifests/audio-independent-oracle-campaign-plan.json",
            "manifests/audio-independent-oracle-coverage-report.json",
            "manifests/audio-duration-next-actions-plan.json",
            "manifests/audio-oracle-comparison-plan-all-tracks.json",
        ],
        "source_campaign_status": campaign.get("status"),
        "source_coverage_status": coverage.get("status"),
        "source_next_action_lane": lane.get("lane_id"),
        "summary": {
            "packet_job_count": len(records),
            "missing_independent_capture_count": int(coverage_summary.get("representative_missing_independent_capture_count", 0)),
            "all_track_missing_independent_capture_count": int(coverage_summary.get("missing_independent_capture_count", 0)),
            "near_oracle_pass_count": int(coverage_summary.get("near_oracle_pass_count", 0)),
            "phase_job_counts": dict(sorted(phase_counts.items())),
            "primary_uncertainty_counts": dict(sorted(uncertainty_counts.items())),
            "diagnostic_focus_counts": dict(sorted(focus_counts.items())),
            "accepted_oracles": capture_contract.get("accepted_oracles", []),
            "minimum_metadata_fields": capture_contract.get("minimum_metadata_fields", []),
            "sample_rate_hz": capture_contract.get("comparison_thresholds", {}).get("sample_rate"),
            "channels": capture_contract.get("comparison_thresholds", {}).get("channels"),
            "bits_per_sample": capture_contract.get("comparison_thresholds", {}).get("bits_per_sample"),
            "minimum_seconds": capture_contract.get("comparison_thresholds", {}).get("minimum_seconds"),
            "release_quality_playback_claim_ready": bool(coverage_summary.get("release_quality_playback_claim_ready")),
            "promotion_allowed_by_packet": False,
            "behavior_change_allowed": False,
        },
        "operator_batches": {
            "by_phase": grouped_jobs(records, "phase"),
            "by_primary_uncertainty": grouped_jobs(records, "primary_uncertainty"),
        },
        "capture_packet_policy": [
            "This packet is an operator checklist for external independent-emulator captures; it does not run an emulator.",
            "External SPC/WAV capture artifacts are generated evidence and must stay under ignored build/audio paths.",
            "Each imported capture must identify mesen2, bsnes/higan, or mednafen and set independent_emulator_capture=true.",
            "The importer must preserve planned source_spc.sha1 in capture metadata before comparison results are collected.",
            "Any mismatch must be explained before release-quality playback can be claimed.",
            "This packet cannot promote exact durations, sequence semantics, or public loop metadata by itself.",
        ],
        "records": records,
        "post_packet_validation_commands": [
            "python tools/validate_audio_independent_oracle_capture_packet.py",
            "python tools/run_audio_independent_oracle_campaign.py --mode audit-existing-captures",
            "python tools/validate_audio_independent_oracle_campaign_run_summary.py",
            "python tools/collect_audio_oracle_comparison_results.py --plan manifests/audio-oracle-comparison-plan-all-tracks.json --summary build/audio/oracle-comparison-all-tracks/oracle-comparison-summary.json",
            "python tools/validate_audio_oracle_comparison_summary.py build/audio/oracle-comparison-all-tracks/oracle-comparison-summary.json --require-compared",
            "python tools/build_audio_oracle_verification_report.py --summary build/audio/oracle-comparison-all-tracks/oracle-comparison-summary.json --json manifests/audio-oracle-verification-report-all-tracks.json --markdown notes/audio-oracle-verification-report-all-tracks.md",
            "python tools/validate_audio_oracle_verification_report.py manifests/audio-oracle-verification-report-all-tracks.json --require-representative-pass",
            "python tools/build_audio_independent_oracle_coverage_report.py",
            "python tools/validate_audio_independent_oracle_coverage_report.py",
            "python tools/build_audio_duration_readiness_rollup.py",
            "python tools/validate_audio_duration_readiness_rollup.py",
        ],
    }


def render_markdown(data: dict[str, Any]) -> str:
    summary = data["summary"]
    rows = [
        "| {order} | {track_id:03d} | `{name}` | `{phase}` | `{uncertainty}` | `{duration}` | `{metadata}` |".format(
            order=record["execution_order"],
            track_id=record["track_id"],
            name=record["track_name"],
            phase=record["phase"],
            uncertainty=record["primary_uncertainty"],
            duration=record["planned_duration_seconds"],
            metadata=record["capture_outputs"]["capture_metadata"],
        )
        for record in data["records"]
    ]
    command_rows = [f"- `{command}`" for command in data["post_packet_validation_commands"]]
    batch_rows = [
        "| `{phase}` | {count} | `{tracks}` |".format(
            phase=batch["phase"],
            count=batch["job_count"],
            tracks=batch["track_ids"],
        )
        for batch in data["operator_batches"]["by_phase"]
    ]
    return "\n".join(
        [
            "# Audio Independent Oracle Capture Packet",
            "",
            "Status: representative independent-emulator capture jobs are packaged for external inputs; current playback/export behavior is preserved.",
            "",
            "## Summary",
            "",
            f"- packet jobs: `{summary['packet_job_count']}`",
            f"- missing representative captures: `{summary['missing_independent_capture_count']}`",
            f"- all-track missing independent captures: `{summary['all_track_missing_independent_capture_count']}`",
            f"- near-oracle pass count: `{summary['near_oracle_pass_count']}`",
            f"- phases: `{summary['phase_job_counts']}`",
            f"- uncertainty counts: `{summary['primary_uncertainty_counts']}`",
            f"- accepted oracles: `{summary['accepted_oracles']}`",
            f"- WAV policy: `{summary['sample_rate_hz']} Hz`, `{summary['channels']}` channels, `{summary['bits_per_sample']}` bits, at least `{summary['minimum_seconds']}` seconds",
            f"- release-quality playback claim ready: `{summary['release_quality_playback_claim_ready']}`",
            "",
            "## Phase Batches",
            "",
            "| Phase | Jobs | Tracks |",
            "| --- | ---: | --- |",
            *batch_rows,
            "",
            "## Capture Jobs",
            "",
            "| Order | Track | Name | Phase | Primary uncertainty | Planned seconds | Metadata output |",
            "| ---: | ---: | --- | --- | --- | ---: | --- |",
            *rows,
            "",
            "## Validation After Imports",
            "",
            *command_rows,
            "",
            "## Capture Packet Policy",
            "",
            *[f"- {item}" for item in data["capture_packet_policy"]],
            "",
            "## Remaining Uncertainty",
            "",
            "- All 16 representative captures still require external independent-emulator SPC/WAV inputs.",
            "- All imported captures must pass per-track reference capture validation before comparison summaries are refreshed.",
            "- Release-quality playback remains blocked until the independent emulator gate passes after report refresh.",
            "",
        ]
    )


def main() -> int:
    args = parse_args()
    data = build_packet(load_json(Path(args.campaign)), load_json(Path(args.coverage)), load_json(Path(args.next_actions)))
    output = Path(args.output)
    notes = Path(args.notes)
    output.parent.mkdir(parents=True, exist_ok=True)
    notes.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    notes.write_text(render_markdown(data), encoding="utf-8")
    print(
        "Built independent oracle capture packet: "
        f"{data['summary']['packet_job_count']} jobs, "
        f"{data['summary']['missing_independent_capture_count']} captures missing"
    )
    print(f"Wrote {output}")
    print(f"Wrote {notes}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
