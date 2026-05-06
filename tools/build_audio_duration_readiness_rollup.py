#!/usr/bin/env python3
"""Build a consolidated audio exact-duration readiness rollup."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_UNCERTAINTY = ROOT / "manifests" / "audio-duration-uncertainty-register.json"
DEFAULT_FINITE_TAIL = ROOT / "manifests" / "audio-finite-ending-tail-metrics.json"
DEFAULT_LOOP_TAIL = ROOT / "manifests" / "audio-loop-point-tail-metrics.json"
DEFAULT_ORACLE_REPORT = ROOT / "manifests" / "audio-oracle-verification-report-all-tracks.json"
DEFAULT_INDEPENDENT_ORACLE = ROOT / "manifests" / "audio-independent-oracle-campaign-plan.json"
DEFAULT_PROBE_CAMPAIGN = ROOT / "manifests" / "audio-probe-campaign-plan.json"
DEFAULT_OUTPUT = ROOT / "manifests" / "audio-duration-readiness-rollup.json"
DEFAULT_NOTES = ROOT / "notes" / "audio-duration-readiness-rollup.md"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build audio duration readiness rollup.")
    parser.add_argument("--uncertainty", default=str(DEFAULT_UNCERTAINTY), help="Duration uncertainty register JSON.")
    parser.add_argument("--finite-tail", default=str(DEFAULT_FINITE_TAIL), help="Finite-ending tail metrics JSON.")
    parser.add_argument("--loop-tail", default=str(DEFAULT_LOOP_TAIL), help="Loop-point tail metrics JSON.")
    parser.add_argument("--oracle-report", default=str(DEFAULT_ORACLE_REPORT), help="All-track oracle report JSON.")
    parser.add_argument("--independent-oracle", default=str(DEFAULT_INDEPENDENT_ORACLE), help="Independent oracle campaign JSON.")
    parser.add_argument("--probe-campaign", default=str(DEFAULT_PROBE_CAMPAIGN), help="Probe campaign plan JSON.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Rollup JSON output.")
    parser.add_argument("--notes", default=str(DEFAULT_NOTES), help="Rollup markdown output.")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_rollup(
    uncertainty: dict[str, Any],
    finite_tail: dict[str, Any],
    loop_tail: dict[str, Any],
    oracle_report: dict[str, Any],
    independent_oracle: dict[str, Any],
    probe_campaign: dict[str, Any],
) -> dict[str, Any]:
    uncertainty_summary = uncertainty.get("summary", {})
    oracle_gates = oracle_report.get("gate_results", {})
    independent_summary = independent_oracle.get("summary", {})
    finite_summary = finite_tail.get("summary", {})
    loop_summary = loop_tail.get("summary", {})
    probe_summary = probe_campaign.get("summary", {})
    public_exact_count = int(uncertainty_summary.get("public_exact_duration_track_count", 0))
    track_count = int(uncertainty_summary.get("track_count", 0))
    primary_counts = uncertainty_summary.get("primary_uncertainty_track_counts", {})
    release_ready = (
        public_exact_count == track_count
        and bool(oracle_gates.get("release_quality_playback_claim_ready"))
        and bool(independent_summary.get("independent_emulator_gate_passed"))
    )
    gates = {
        "public_exact_duration_gate": {
            "passed": public_exact_count == track_count and track_count > 0,
            "public_exact_duration_track_count": public_exact_count,
            "track_count": track_count,
            "blocking_track_count": max(0, track_count - public_exact_count),
        },
        "finite_ending_tail_gate": {
            "passed": bool(finite_summary.get("public_exact_finite_export_ready")),
            "records": int(finite_summary.get("record_count", 0)),
            "tail_classification_counts": finite_summary.get("tail_classification_counts", {}),
            "active_through_render_boundary_count": int(finite_summary.get("active_through_render_boundary_count", 0)),
            "nonzero_after_candidate_end_count": int(finite_summary.get("nonzero_after_candidate_end_count", 0)),
        },
        "loop_point_tail_gate": {
            "passed": bool(loop_summary.get("public_exact_loop_export_ready")),
            "records": int(loop_summary.get("record_count", 0)),
            "tail_classification_counts": loop_summary.get("tail_classification_counts", {}),
            "missing_exact_loop_field_count": int(loop_summary.get("missing_exact_loop_field_count", 0)),
            "active_through_render_boundary_count": int(loop_summary.get("active_through_render_boundary_count", 0)),
        },
        "near_oracle_gate": {
            "passed": bool(oracle_gates.get("all_track_oracle_gate_passed")),
            "status_counts": oracle_report.get("status_counts", {}),
        },
        "independent_oracle_gate": {
            "passed": bool(independent_summary.get("independent_emulator_gate_passed")),
            "independent_capture_count": int(independent_summary.get("independent_capture_count", 0)),
            "missing_independent_capture_count": int(independent_summary.get("missing_independent_capture_count", 0)),
            "representative_campaign_job_count": int(independent_summary.get("representative_campaign_job_count", 0)),
        },
        "sequence_promotion_gate": {
            "passed": bool(uncertainty_summary.get("sequence_promotion_allowed")),
            "uncertainty_register_allows_sequence_promotion": bool(uncertainty_summary.get("sequence_promotion_allowed")),
            "probe_campaign_allows_sequence_promotion": bool(probe_summary.get("sequence_promotion_allowed_by_campaign")),
        },
    }
    blocker_lanes = [
        {
            "lane": "non_zero_control_semantics",
            "blocking_count": int(primary_counts.get("non_zero_control_semantics_pending", 0)),
            "current_contract": "audio-probe-campaign-plan",
            "next_action": "run/import nonzero control probe evidence and refresh duration uncertainty",
        },
        {
            "lane": "zero_runtime_probe",
            "blocking_count": int(primary_counts.get("zero_runtime_probe_pending", 0)),
            "current_contract": "audio-zero-runtime-probe-plan",
            "next_action": "run/import 0x00 runtime probe evidence and refresh duration uncertainty",
        },
        {
            "lane": "finite_transition_review",
            "blocking_count": int(primary_counts.get("finite_transition_review_pending", 0)),
            "current_contract": "audio-finite-ending-tail-metrics",
            "next_action": "classify true finite endings versus transition/stinger policy",
        },
        {
            "lane": "loop_point_metadata",
            "blocking_count": int(primary_counts.get("loop_point_metadata_pending", 0)),
            "current_contract": "audio-loop-point-tail-metrics",
            "next_action": "collect exact loop points or held-policy/no-exact-loop classification",
        },
        {
            "lane": "independent_oracle",
            "blocking_count": int(independent_summary.get("missing_independent_capture_count", 0)),
            "current_contract": "audio-independent-oracle-campaign-plan",
            "next_action": "import external emulator reference captures for representative campaign first",
        },
    ]
    return {
        "schema": "earthbound-decomp.audio-duration-readiness-rollup.v1",
        "status": "audio_duration_readiness_blocked_policy_preserved",
        "references": [
            "manifests/audio-duration-uncertainty-register.json",
            "manifests/audio-finite-ending-tail-metrics.json",
            "manifests/audio-loop-point-tail-metrics.json",
            "manifests/audio-oracle-verification-report-all-tracks.json",
            "manifests/audio-independent-oracle-campaign-plan.json",
            "manifests/audio-probe-campaign-plan.json",
        ],
        "summary": {
            "track_count": track_count,
            "public_exact_duration_track_count": public_exact_count,
            "blocking_track_count": max(0, track_count - public_exact_count),
            "primary_uncertainty_track_counts": primary_counts,
            "near_oracle_passed": bool(oracle_gates.get("all_track_oracle_gate_passed")),
            "independent_oracle_passed": bool(independent_summary.get("independent_emulator_gate_passed")),
            "finite_tail_records": int(finite_summary.get("record_count", 0)),
            "loop_tail_records": int(loop_summary.get("record_count", 0)),
            "probe_campaign_jobs": int(probe_summary.get("campaign_job_count", 0)),
            "release_ready": release_ready,
            "current_playback_export_behavior_preserved": True,
        },
        "gates": gates,
        "blocker_lanes": blocker_lanes,
        "decision_policy": [
            "This rollup is diagnostic only and does not promote sequence-derived durations or exact loop exports.",
            "Near-oracle equivalence is treated separately from independent external-emulator capture.",
            "Finite and loop tail metrics prove current diagnostic activity patterns, not final exact-duration policy.",
            "Release-quality exact-duration readiness requires public exact duration coverage plus independent oracle and lane-specific runtime evidence.",
        ],
    }


def render_markdown(data: dict[str, Any]) -> str:
    summary = data["summary"]
    gate_rows = [
        "| `{name}` | `{passed}` | `{details}` |".format(
            name=name,
            passed=gate.get("passed"),
            details={key: value for key, value in gate.items() if key != "passed"},
        )
        for name, gate in data["gates"].items()
    ]
    lane_rows = [
        "| `{lane}` | {count} | `{contract}` | {next_action} |".format(
            lane=lane["lane"],
            count=lane["blocking_count"],
            contract=lane["current_contract"],
            next_action=lane["next_action"],
        )
        for lane in data["blocker_lanes"]
    ]
    return "\n".join(
        [
            "# Audio Duration Readiness Rollup",
            "",
            "Status: exact-duration readiness remains blocked; current playback/export behavior is preserved.",
            "",
            "## Summary",
            "",
            f"- tracks: `{summary['track_count']}`",
            f"- public exact duration tracks: `{summary['public_exact_duration_track_count']}`",
            f"- blocking tracks: `{summary['blocking_track_count']}`",
            f"- primary uncertainty counts: `{summary['primary_uncertainty_track_counts']}`",
            f"- near oracle passed: `{summary['near_oracle_passed']}`",
            f"- independent oracle passed: `{summary['independent_oracle_passed']}`",
            f"- finite tail records: `{summary['finite_tail_records']}`",
            f"- loop tail records: `{summary['loop_tail_records']}`",
            f"- probe campaign jobs: `{summary['probe_campaign_jobs']}`",
            f"- release ready: `{summary['release_ready']}`",
            "",
            "## Gates",
            "",
            "| Gate | Passed | Details |",
            "| --- | --- | --- |",
            *gate_rows,
            "",
            "## Blocker Lanes",
            "",
            "| Lane | Blocking count | Current contract | Next action |",
            "| --- | ---: | --- | --- |",
            *lane_rows,
            "",
            "## Decision Policy",
            "",
            *[f"- {item}" for item in data["decision_policy"]],
            "",
            "## Remaining Uncertainty",
            "",
            "- Non-zero control semantics remains the largest track-level exact-duration blocker.",
            "- Independent external-emulator capture remains the release-quality oracle blocker.",
            "- Finite and loop tail metrics are now normalized evidence, but neither lane is promotion-ready without runtime classification.",
            "",
        ]
    )


def main() -> int:
    args = parse_args()
    data = build_rollup(
        load_json(Path(args.uncertainty)),
        load_json(Path(args.finite_tail)),
        load_json(Path(args.loop_tail)),
        load_json(Path(args.oracle_report)),
        load_json(Path(args.independent_oracle)),
        load_json(Path(args.probe_campaign)),
    )
    output = Path(args.output)
    notes = Path(args.notes)
    output.parent.mkdir(parents=True, exist_ok=True)
    notes.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    notes.write_text(render_markdown(data), encoding="utf-8")
    print(
        "Built audio duration readiness rollup: "
        f"{data['summary']['blocking_track_count']} blocking tracks, "
        f"release_ready={data['summary']['release_ready']}"
    )
    print(f"Wrote {output}")
    print(f"Wrote {notes}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
