#!/usr/bin/env python3
"""Build an operator handoff matrix for independent oracle captures."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PACKET = ROOT / "manifests" / "audio-independent-oracle-capture-packet.json"
DEFAULT_RUN_SUMMARY = ROOT / "build" / "audio" / "independent-oracle-campaign-runs" / "independent-oracle-campaign-run-summary.json"
DEFAULT_COVERAGE = ROOT / "manifests" / "audio-independent-oracle-coverage-report.json"
DEFAULT_VERIFICATION = ROOT / "manifests" / "audio-oracle-verification-report-all-tracks.json"
DEFAULT_NEXT_ACTIONS = ROOT / "manifests" / "audio-duration-next-actions-plan.json"
DEFAULT_OUTPUT = ROOT / "manifests" / "audio-independent-oracle-handoff-matrix.json"
DEFAULT_NOTES = ROOT / "notes" / "audio-independent-oracle-handoff-matrix.md"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build independent oracle handoff matrix.")
    parser.add_argument("--packet", default=str(DEFAULT_PACKET), help="Independent oracle capture packet JSON.")
    parser.add_argument("--run-summary", default=str(DEFAULT_RUN_SUMMARY), help="Independent oracle campaign run summary JSON.")
    parser.add_argument("--coverage", default=str(DEFAULT_COVERAGE), help="Independent oracle coverage report JSON.")
    parser.add_argument("--verification", default=str(DEFAULT_VERIFICATION), help="All-track oracle verification report JSON.")
    parser.add_argument("--next-actions", default=str(DEFAULT_NEXT_ACTIONS), help="Audio duration next-actions plan JSON.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Handoff matrix JSON output.")
    parser.add_argument("--notes", default=str(DEFAULT_NOTES), help="Handoff matrix markdown output.")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def by_job_id(records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(record.get("job_id")): record for record in records}


def find_next_action_lane(next_actions: dict[str, Any]) -> dict[str, Any]:
    for lane in next_actions.get("priority_lanes", []):
        if lane.get("lane_id") == "independent_oracle_representative_capture":
            return lane
    return {}


def verification_gates(verification: dict[str, Any]) -> dict[str, Any]:
    gates = verification.get("gate_results", {})
    if isinstance(gates, dict):
        return gates
    summary = verification.get("summary", {})
    gates = summary.get("gates", {})
    if isinstance(gates, dict):
        return gates
    return {
        "representative_oracle_gate_passed": summary.get("representative_oracle_gate_passed"),
        "independent_emulator_gate_passed": summary.get("independent_emulator_gate_passed"),
        "all_track_oracle_gate_passed": summary.get("all_track_oracle_gate_passed"),
        "release_quality_playback_claim_ready": summary.get("release_quality_playback_claim_ready"),
    }


def duration_bucket(seconds: float) -> str:
    if seconds >= 120.0:
        return "long_preview_120s"
    if seconds >= 30.0:
        return "diagnostic_30s"
    return "short_finite_candidate"


def handoff_record(packet_record: dict[str, Any], run_record: dict[str, Any]) -> dict[str, Any]:
    audit = run_record.get("audit", {})
    outputs = packet_record.get("capture_outputs", {})
    commands = packet_record.get("commands", {})
    planned_seconds = float(packet_record.get("planned_duration_seconds", 0.0))
    return {
        "execution_order": int(packet_record["execution_order"]),
        "job_id": packet_record["job_id"],
        "campaign_job_id": packet_record["campaign_job_id"],
        "track_id": int(packet_record["track_id"]),
        "track_name": packet_record["track_name"],
        "phase": packet_record["phase"],
        "priority_reason": packet_record.get("priority_reason"),
        "primary_uncertainty": packet_record.get("primary_uncertainty"),
        "diagnostic_focus": packet_record.get("diagnostic_focus"),
        "export_class": packet_record.get("export_class"),
        "planned_duration_seconds": planned_seconds,
        "duration_bucket": duration_bucket(planned_seconds),
        "near_oracle_status": packet_record.get("current_near_oracle_status"),
        "accepted_oracles": packet_record.get("accepted_oracles", []),
        "source_spc": packet_record.get("source_spc", {}),
        "source_render": packet_record.get("source_render", {}),
        "capture_targets": {
            "spc_snapshot": outputs.get("spc_snapshot"),
            "pcm_wav": outputs.get("pcm_wav"),
            "capture_metadata": outputs.get("capture_metadata"),
            "comparison_result": outputs.get("comparison_result"),
        },
        "metadata_contract": {
            "minimum_fields": packet_record.get("expected_capture_metadata_fields", []),
            "sample_rate_hz": 32000,
            "channels": 2,
            "bits_per_sample": 16,
            "minimum_duration_seconds": planned_seconds,
        },
        "current_audit": {
            "status": run_record.get("status"),
            "blocking_reasons": run_record.get("blocking_reasons", []),
            "capture_metadata_exists": bool(audit.get("capture_metadata_exists")),
            "missing_metadata_fields": audit.get("missing_metadata_fields", []),
            "independent_emulator_capture": bool(audit.get("independent_emulator_capture")),
            "source_spc_sha1_matches": bool(audit.get("source_spc_sha1_matches")),
            "spc_exists": bool(audit.get("spc_exists")),
            "wav_exists": bool(audit.get("wav_exists")),
            "wav_format_matches_policy": bool(audit.get("wav_format_matches_policy")),
            "duration_covers_planned": bool(audit.get("duration_covers_planned")),
        },
        "handoff_commands": {
            "import": commands.get("import"),
            "validate_capture": commands.get("validate_capture"),
            "audit": commands.get("audit"),
            "collect_comparison": commands.get("collect_comparison"),
            "refresh_report": commands.get("refresh_report"),
            "validate_report": commands.get("validate_report"),
        },
        "acceptance_gates": packet_record.get("acceptance_gates", []),
        "handoff_gate": (
            "Import independent SPC/WAV capture, validate metadata and hashes, collect comparison results, "
            "refresh the all-track oracle report, then rerun the representative independent gate."
        ),
        "promotion_allowed_by_matrix": False,
        "behavior_change_allowed": False,
    }


def grouped(records: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
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


def build_matrix(
    packet: dict[str, Any],
    run_summary: dict[str, Any],
    coverage: dict[str, Any],
    verification: dict[str, Any],
    next_actions: dict[str, Any],
) -> dict[str, Any]:
    run_by_job = by_job_id(run_summary.get("runs", []))
    records = [handoff_record(record, run_by_job[str(record["job_id"])]) for record in packet.get("records", [])]
    records.sort(key=lambda record: int(record["execution_order"]))
    phase_counts = Counter(str(record["phase"]) for record in records)
    uncertainty_counts = Counter(str(record["primary_uncertainty"]) for record in records)
    focus_counts = Counter(str(record["diagnostic_focus"]) for record in records)
    duration_counts = Counter(str(record["duration_bucket"]) for record in records)
    lane = find_next_action_lane(next_actions)
    coverage_summary = coverage.get("summary", {})
    gates = verification_gates(verification)
    return {
        "schema": "earthbound-decomp.audio-independent-oracle-handoff-matrix.v1",
        "status": "independent_oracle_handoff_matrix_ready_external_inputs_required",
        "references": [
            "manifests/audio-independent-oracle-capture-packet.json",
            "build/audio/independent-oracle-campaign-runs/independent-oracle-campaign-run-summary.json",
            "manifests/audio-independent-oracle-coverage-report.json",
            "manifests/audio-oracle-verification-report-all-tracks.json",
            "manifests/audio-duration-next-actions-plan.json",
        ],
        "source_packet_status": packet.get("status"),
        "source_run_mode": run_summary.get("mode"),
        "source_coverage_status": coverage.get("status"),
        "source_next_action_lane": lane.get("lane_id"),
        "summary": {
            "handoff_job_count": len(records),
            "ready_capture_count": int(run_summary.get("independent_capture_ready_count", 0)),
            "pending_capture_count": int(run_summary.get("pending_independent_capture_count", 0)),
            "missing_capture_metadata_count": int(run_summary.get("blocking_reason_counts", {}).get("missing_capture_metadata", 0)),
            "all_track_missing_independent_capture_count": int(coverage_summary.get("missing_independent_capture_count", 0)),
            "near_oracle_pass_count": int(coverage_summary.get("near_oracle_pass_count", 0)),
            "phase_job_counts": dict(sorted(phase_counts.items())),
            "primary_uncertainty_counts": dict(sorted(uncertainty_counts.items())),
            "diagnostic_focus_counts": dict(sorted(focus_counts.items())),
            "duration_bucket_counts": dict(sorted(duration_counts.items())),
            "accepted_oracles": packet.get("summary", {}).get("accepted_oracles", []),
            "minimum_metadata_fields": packet.get("summary", {}).get("minimum_metadata_fields", []),
            "sample_rate_hz": int(packet.get("summary", {}).get("sample_rate_hz", 0)),
            "channels": int(packet.get("summary", {}).get("channels", 0)),
            "bits_per_sample": int(packet.get("summary", {}).get("bits_per_sample", 0)),
            "representative_oracle_gate_passed": bool(gates.get("representative_oracle_gate_passed")),
            "all_track_oracle_gate_passed": bool(gates.get("all_track_oracle_gate_passed")),
            "independent_emulator_gate_passed": bool(gates.get("independent_emulator_gate_passed")),
            "release_quality_playback_claim_ready": bool(gates.get("release_quality_playback_claim_ready")),
            "promotion_allowed_by_matrix": False,
            "behavior_change_allowed": False,
        },
        "operator_batches": {
            "by_phase": grouped(records, "phase"),
            "by_primary_uncertainty": grouped(records, "primary_uncertainty"),
            "by_diagnostic_focus": grouped(records, "diagnostic_focus"),
            "by_duration_bucket": grouped(records, "duration_bucket"),
        },
        "handoff_policy": [
            "This matrix is an external-capture handoff and audit artifact; it does not run an emulator.",
            "Every listed capture is still pending because committed evidence has no independent capture metadata.",
            "Imported captures must remain under ignored build/audio paths and pass per-track reference validation.",
            "The ares near-oracle gate remains green, but release-quality playback remains blocked until the independent emulator gate passes.",
            "This matrix cannot promote exact durations, loop metadata, sequence semantics, or playback/export behavior.",
        ],
        "records": records,
        "post_handoff_validation_commands": [
            "python tools/build_audio_independent_oracle_handoff_matrix.py",
            "python tools/validate_audio_independent_oracle_handoff_matrix.py",
            "python tools/run_audio_independent_oracle_campaign.py --mode audit-existing-captures",
            "python tools/validate_audio_independent_oracle_campaign_run_summary.py",
            "python tools/validate_audio_independent_oracle_capture_packet.py",
            "python tools/validate_audio_independent_oracle_coverage_report.py",
            "python tools/collect_audio_oracle_comparison_results.py --plan manifests/audio-oracle-comparison-plan-all-tracks.json --summary build/audio/oracle-comparison-all-tracks/oracle-comparison-summary.json",
            "python tools/validate_audio_oracle_comparison_summary.py build/audio/oracle-comparison-all-tracks/oracle-comparison-summary.json --require-compared",
            "python tools/build_audio_oracle_verification_report.py --summary build/audio/oracle-comparison-all-tracks/oracle-comparison-summary.json --json manifests/audio-oracle-verification-report-all-tracks.json --markdown notes/audio-oracle-verification-report-all-tracks.md",
            "python tools/validate_audio_oracle_verification_report.py manifests/audio-oracle-verification-report-all-tracks.json --require-representative-pass",
            "python tools/build_audio_duration_readiness_rollup.py",
            "python tools/validate_audio_duration_readiness_rollup.py",
        ],
    }


def render_markdown(data: dict[str, Any]) -> str:
    summary = data["summary"]
    rows = [
        "| {order} | {track:03d} | `{name}` | `{phase}` | `{uncertainty}` | `{duration}` | `{status}` | `{reason}` |".format(
            order=record["execution_order"],
            track=record["track_id"],
            name=record["track_name"],
            phase=record["phase"],
            uncertainty=record["primary_uncertainty"],
            duration=record["planned_duration_seconds"],
            status=record["current_audit"]["status"],
            reason=record["current_audit"]["blocking_reasons"],
        )
        for record in data["records"]
    ]
    phase_rows = [
        "| `{phase}` | {count} | `{tracks}` |".format(
            phase=batch["phase"],
            count=batch["job_count"],
            tracks=batch["track_ids"],
        )
        for batch in data["operator_batches"]["by_phase"]
    ]
    duration_rows = [
        "| `{bucket}` | {count} | `{tracks}` |".format(
            bucket=batch["duration_bucket"],
            count=batch["job_count"],
            tracks=batch["track_ids"],
        )
        for batch in data["operator_batches"]["by_duration_bucket"]
    ]
    commands = [f"- `{command}`" for command in data["post_handoff_validation_commands"]]
    return "\n".join(
        [
            "# Audio Independent Oracle Handoff Matrix",
            "",
            "Status: representative external-emulator captures are ready for operator handoff; current playback/export behavior is preserved.",
            "",
            "## Summary",
            "",
            f"- handoff jobs: `{summary['handoff_job_count']}`",
            f"- ready captures: `{summary['ready_capture_count']}`",
            f"- pending captures: `{summary['pending_capture_count']}`",
            f"- missing capture metadata: `{summary['missing_capture_metadata_count']}`",
            f"- all-track missing independent captures: `{summary['all_track_missing_independent_capture_count']}`",
            f"- near-oracle pass count: `{summary['near_oracle_pass_count']}`",
            f"- phase counts: `{summary['phase_job_counts']}`",
            f"- uncertainty counts: `{summary['primary_uncertainty_counts']}`",
            f"- duration buckets: `{summary['duration_bucket_counts']}`",
            f"- accepted oracles: `{summary['accepted_oracles']}`",
            f"- independent emulator gate passed: `{summary['independent_emulator_gate_passed']}`",
            f"- release-quality playback claim ready: `{summary['release_quality_playback_claim_ready']}`",
            "",
            "## Phase Batches",
            "",
            "| Phase | Jobs | Tracks |",
            "| --- | ---: | --- |",
            *phase_rows,
            "",
            "## Duration Batches",
            "",
            "| Duration bucket | Jobs | Tracks |",
            "| --- | ---: | --- |",
            *duration_rows,
            "",
            "## Handoff Jobs",
            "",
            "| Order | Track | Name | Phase | Primary uncertainty | Planned seconds | Audit status | Blocking reason |",
            "| ---: | ---: | --- | --- | --- | ---: | --- | --- |",
            *rows,
            "",
            "## Validation After Imports",
            "",
            *commands,
            "",
            "## Handoff Policy",
            "",
            *[f"- {item}" for item in data["handoff_policy"]],
            "",
            "## Remaining Uncertainty",
            "",
            "- All 16 representative independent captures are still pending external SPC/WAV inputs.",
            "- The all-track near-oracle gate remains green, but it is not independent external-emulator evidence.",
            "- Release-quality playback remains blocked until imported captures refresh the independent emulator gate.",
            "",
        ]
    )


def main() -> int:
    args = parse_args()
    data = build_matrix(
        load_json(Path(args.packet)),
        load_json(Path(args.run_summary)),
        load_json(Path(args.coverage)),
        load_json(Path(args.verification)),
        load_json(Path(args.next_actions)),
    )
    output = Path(args.output)
    notes = Path(args.notes)
    output.parent.mkdir(parents=True, exist_ok=True)
    notes.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    notes.write_text(render_markdown(data), encoding="utf-8")
    print(
        "Built independent oracle handoff matrix: "
        f"{data['summary']['handoff_job_count']} jobs, "
        f"{data['summary']['pending_capture_count']} pending"
    )
    print(f"Wrote {output}")
    print(f"Wrote {notes}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
