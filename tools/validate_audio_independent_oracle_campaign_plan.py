#!/usr/bin/env python3
"""Validate the independent external-emulator audio oracle campaign plan."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MANIFEST = ROOT / "manifests" / "audio-independent-oracle-campaign-plan.json"
DEFAULT_ORACLE_PLAN = ROOT / "manifests" / "audio-oracle-comparison-plan-all-tracks.json"
DEFAULT_ORACLE_REPORT = ROOT / "manifests" / "audio-oracle-verification-report-all-tracks.json"
DEFAULT_UNCERTAINTY = ROOT / "manifests" / "audio-duration-uncertainty-register.json"
REQUIRED_REFERENCES = {
    "manifests/audio-oracle-comparison-plan-all-tracks.json",
    "manifests/audio-oracle-verification-report-all-tracks.json",
    "manifests/audio-duration-uncertainty-register.json",
    "notes/audio-oracle-verification-report-all-tracks.md",
}
REQUIRED_TRACKS = {1, 5, 8, 10, 12, 17, 25, 32, 46, 115, 123, 135, 161, 171, 173, 175}
REQUIRED_PRIMARY_UNCERTAINTIES = {
    "active_preview_classification_pending",
    "finite_transition_review_pending",
    "loop_point_metadata_pending",
    "non_zero_control_semantics_pending",
    "pcm_trim_usable_sequence_intent_open",
    "zero_runtime_probe_pending",
}
REQUIRED_FOCUSES = {
    "active_through_preview_or_loop_candidate",
    "finite_tail_or_transition_end",
    "general_playback_equivalence",
}
EXTERNAL_ORACLE_TOKENS = {"mesen2", "bsnes_higan", "mednafen"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate independent oracle campaign plan.")
    parser.add_argument("manifest", nargs="?", default=str(DEFAULT_MANIFEST))
    parser.add_argument("--oracle-plan", default=str(DEFAULT_ORACLE_PLAN), help="All-track oracle plan JSON.")
    parser.add_argument("--oracle-report", default=str(DEFAULT_ORACLE_REPORT), help="All-track oracle report JSON.")
    parser.add_argument("--uncertainty", default=str(DEFAULT_UNCERTAINTY), help="Duration uncertainty register JSON.")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def by_track(records: list[dict[str, Any]]) -> dict[int, dict[str, Any]]:
    return {int(record["track_id"]): record for record in records}


def count_records(records: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for record in records:
        counts[str(record.get(key))] += 1
    return dict(sorted(counts.items()))


def validate(
    data: dict[str, Any],
    oracle_plan: dict[str, Any],
    oracle_report: dict[str, Any],
    uncertainty: dict[str, Any],
) -> None:
    require(data.get("schema") == "earthbound-decomp.audio-independent-oracle-campaign-plan.v1", "unexpected schema")
    require(data.get("status") == "independent_external_oracle_campaign_ready", "unexpected status")
    require(REQUIRED_REFERENCES <= set(data.get("references", [])), "missing references")

    jobs = data.get("campaign_jobs", [])
    summary = data.get("summary", {})
    require(int(summary.get("oracle_job_count", -1)) == 190, "expected 190 oracle jobs")
    require(int(summary.get("near_oracle_pass_count", -1)) == 190, "expected 190 near-oracle passes")
    require(int(summary.get("independent_capture_count", -1)) == 0, "expected no independent captures yet")
    require(int(summary.get("missing_independent_capture_count", -1)) == 190, "expected 190 missing independent captures")
    require(int(summary.get("representative_campaign_job_count", -1)) == len(jobs), "campaign job count mismatch")
    require(len(jobs) == 16, f"expected 16 representative jobs, got {len(jobs)}")
    require(summary.get("phase_job_counts") == count_records(jobs, "phase"), "phase counts mismatch")
    require(summary.get("diagnostic_focus_counts") == count_records(jobs, "diagnostic_focus"), "focus counts mismatch")
    require(
        summary.get("representative_primary_uncertainty_counts") == count_records(jobs, "primary_uncertainty"),
        "primary uncertainty counts mismatch",
    )
    require(summary.get("release_quality_playback_claim_ready") is False, "campaign must not claim release quality")
    require(summary.get("independent_emulator_gate_passed") is False, "campaign must start from open independent gate")
    require(summary.get("all_track_near_oracle_passed") is True, "campaign must be based on passing near-oracle")
    require(summary.get("sequence_promotion_allowed_by_campaign") is False, "campaign must not allow sequence promotion")

    report_gates = oracle_report.get("gate_results", {})
    require(report_gates.get("all_track_oracle_gate_passed") is True, "source report all-track oracle gate should pass")
    require(report_gates.get("independent_emulator_gate_passed") is False, "source report independent gate should be open")
    require(report_gates.get("release_quality_playback_claim_ready") is False, "source report should not claim release")

    oracle_by_track = by_track(oracle_plan.get("jobs", []))
    report_by_track = by_track(oracle_report.get("records", []))
    uncertainty_by_track = by_track(uncertainty.get("tracks", []))
    seen_track_ids: set[int] = set()
    seen_job_ids: set[str] = set()
    seen_orders: set[int] = set()
    primary_uncertainties: set[str] = set()
    diagnostic_focuses: set[str] = set()
    for job in jobs:
        job_id = str(job.get("job_id", ""))
        track_id = int(job.get("track_id", -1))
        order = int(job.get("execution_order", 0))
        require(order > 0, f"{job_id}: invalid execution order")
        require(order not in seen_orders, f"{job_id}: duplicate execution order {order}")
        seen_orders.add(order)
        require(track_id not in seen_track_ids, f"duplicate track id {track_id}")
        require(job_id not in seen_job_ids, f"duplicate job id {job_id}")
        seen_track_ids.add(track_id)
        seen_job_ids.add(job_id)

        oracle_job = oracle_by_track.get(track_id)
        report_record = report_by_track.get(track_id)
        uncertainty_record = uncertainty_by_track.get(track_id)
        require(oracle_job is not None, f"{job_id}: missing source oracle job")
        require(report_record is not None, f"{job_id}: missing oracle report record")
        require(uncertainty_record is not None, f"{job_id}: missing uncertainty record")
        require(job_id == oracle_job.get("job_id"), f"{job_id}: job id does not match source oracle plan")
        require(job.get("track_name") == oracle_job.get("track_name"), f"{job_id}: track name mismatch")
        require(job.get("current_near_oracle_status") == report_record.get("status"), f"{job_id}: report status mismatch")
        require(job.get("current_independent_emulator_capture") is False, f"{job_id}: should still lack independent capture")
        require(report_record.get("independent_emulator_capture") is False, f"{job_id}: source report unexpectedly independent")
        require(job.get("independent_capture_required") is True, f"{job_id}: independent capture not required")
        require(job.get("promotion_allowed_by_campaign") is False, f"{job_id}: campaign promotion must be blocked")
        require(set(job.get("accepted_oracles", [])) >= EXTERNAL_ORACLE_TOKENS, f"{job_id}: missing external oracle options")
        require("import_audio_oracle_reference_capture.py" in str(job.get("import_command", "")), f"{job_id}: missing import command")
        require("--emulator-version" in str(job.get("import_command", "")), f"{job_id}: importer command lacks metadata args")
        require("run_audio_independent_oracle_campaign.py" in str(job.get("dry_run_command", "")), f"{job_id}: missing dry-run command")
        require("--mode dry-run-plan" in str(job.get("dry_run_command", "")), f"{job_id}: bad dry-run command")
        require("run_audio_independent_oracle_campaign.py" in str(job.get("audit_command", "")), f"{job_id}: missing audit command")
        require("--mode audit-existing-captures" in str(job.get("audit_command", "")), f"{job_id}: bad audit command")
        require("collect_audio_oracle_comparison_results.py" in str(job.get("collect_command", "")), f"{job_id}: missing collect command")
        require("validate_audio_oracle_verification_report.py" in str(job.get("result_validator", "")), f"{job_id}: missing result validator")

        source_spc = job.get("source_spc", {})
        source_render = job.get("source_render", {})
        outputs = job.get("reference_capture_outputs", {})
        require(source_spc.get("path") == oracle_job.get("source_spc", {}).get("path"), f"{job_id}: source SPC mismatch")
        require(source_spc.get("sha1"), f"{job_id}: missing source SPC SHA-1")
        require(source_render.get("path") == oracle_job.get("source_render", {}).get("path"), f"{job_id}: source render mismatch")
        require(outputs == oracle_job.get("reference_capture_outputs", {}), f"{job_id}: reference outputs mismatch")
        for key in ("spc_snapshot", "pcm_wav", "capture_metadata", "comparison_result"):
            require(str(outputs.get(key, "")).startswith("build/audio/oracle-comparison-all-tracks/"), f"{job_id}: bad output path {key}")
        metadata_fields = set(job.get("expected_capture_metadata_fields", []))
        for field in ("oracle_id", "oracle_kind", "independent_emulator_capture", "source_spc_sha1", "reference_wav_sha1"):
            require(field in metadata_fields, f"{job_id}: missing metadata field {field}")
        primary_uncertainties.add(str(job.get("primary_uncertainty")))
        diagnostic_focuses.add(str(job.get("diagnostic_focus")))

    require(seen_orders == set(range(1, len(jobs) + 1)), "execution orders must be contiguous")
    require(REQUIRED_TRACKS <= seen_track_ids, f"missing required tracks {sorted(REQUIRED_TRACKS - seen_track_ids)}")
    require(REQUIRED_PRIMARY_UNCERTAINTIES <= primary_uncertainties, "missing representative uncertainty coverage")
    require(REQUIRED_FOCUSES <= diagnostic_focuses, "missing diagnostic focus coverage")
    require(data.get("campaign_policy"), "missing campaign policy")
    capture_contract = data.get("capture_contract", {})
    require(set(capture_contract.get("accepted_oracles", [])) >= EXTERNAL_ORACLE_TOKENS, "capture contract lacks external oracle options")
    require(capture_contract.get("required_independent_flag") is True, "capture contract must require independent flag")
    for field in ("oracle_id", "oracle_kind", "independent_emulator_capture", "source_spc_sha1", "reference_wav_sha1"):
        require(field in set(capture_contract.get("minimum_metadata_fields", [])), f"capture contract missing {field}")
    commands = data.get("post_capture_validation_commands", [])
    for command in (
        "python tools/run_audio_independent_oracle_campaign.py --limit 1 --mode dry-run-plan",
        "python tools/run_audio_independent_oracle_campaign.py --limit 1 --mode audit-existing-captures",
        "python tools/validate_audio_independent_oracle_campaign_run_summary.py",
        "python tools/validate_audio_oracle_verification_report.py manifests/audio-oracle-verification-report-all-tracks.json --require-representative-pass",
        "python tools/validate_audio_duration_uncertainty_register.py",
    ):
        require(command in commands, f"missing post-capture command {command}")


def main() -> int:
    args = parse_args()
    data = load_json(Path(args.manifest))
    validate(
        data,
        load_json(Path(args.oracle_plan)),
        load_json(Path(args.oracle_report)),
        load_json(Path(args.uncertainty)),
    )
    print(
        "Audio independent oracle campaign plan validation OK: "
        f"{data['summary']['representative_campaign_job_count']} jobs, "
        f"{data['summary']['missing_independent_capture_count']} captures missing"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
