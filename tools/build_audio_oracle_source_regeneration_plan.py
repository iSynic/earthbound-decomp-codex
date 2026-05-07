#!/usr/bin/env python3
"""Build a source-evidence regeneration plan for oracle comparison inputs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PREFLIGHT = ROOT / "manifests" / "audio-oracle-source-evidence-preflight.json"
DEFAULT_HANDOFF = ROOT / "manifests" / "audio-independent-oracle-handoff-matrix.json"
DEFAULT_NEXT_ACTIONS = ROOT / "manifests" / "audio-duration-next-actions-plan.json"
DEFAULT_OUTPUT = ROOT / "manifests" / "audio-oracle-source-regeneration-plan.json"
DEFAULT_NOTES = ROOT / "notes" / "audio-oracle-source-regeneration-plan.md"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build oracle source-evidence regeneration plan.")
    parser.add_argument("--preflight", default=str(DEFAULT_PREFLIGHT), help="Oracle source preflight JSON.")
    parser.add_argument("--handoff", default=str(DEFAULT_HANDOFF), help="Independent oracle handoff matrix JSON.")
    parser.add_argument("--next-actions", default=str(DEFAULT_NEXT_ACTIONS), help="Audio duration next-actions plan JSON.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Regeneration plan JSON output.")
    parser.add_argument("--notes", default=str(DEFAULT_NOTES), help="Regeneration plan markdown output.")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def find_next_action_lane(next_actions: dict[str, Any]) -> dict[str, Any]:
    for lane in next_actions.get("priority_lanes", []):
        if lane.get("lane_id") == "independent_oracle_representative_capture":
            return lane
    return {}


def representative_tracks(handoff: dict[str, Any]) -> list[dict[str, Any]]:
    records = [
        {
            "execution_order": int(record["execution_order"]),
            "track_id": int(record["track_id"]),
            "track_name": record["track_name"],
            "phase": record.get("phase"),
            "primary_uncertainty": record.get("primary_uncertainty"),
            "planned_duration_seconds": record.get("planned_duration_seconds"),
        }
        for record in handoff.get("records", [])
    ]
    return sorted(records, key=lambda record: int(record["execution_order"]))


def build_plan(preflight: dict[str, Any], handoff: dict[str, Any], next_actions: dict[str, Any]) -> dict[str, Any]:
    preflight_summary = preflight.get("summary", {})
    lane = find_next_action_lane(next_actions)
    stages = [
        {
            "stage_id": "preflight_current_gap",
            "rank": 1,
            "purpose": "Confirm whether the oracle collector is blocked by missing local source/reference artifacts before regeneration.",
            "expected_state_now": {
                "collector_ready_job_count": int(preflight_summary.get("collector_ready_job_count", 0)),
                "collector_blocked_missing_source_evidence_count": int(
                    preflight_summary.get("collector_blocked_missing_source_evidence_count", 0)
                ),
                "source_spc_present_count": int(preflight_summary.get("source_spc_present_count", 0)),
                "source_render_wav_present_count": int(preflight_summary.get("source_render_wav_present_count", 0)),
            },
            "commands": [
                "python tools/build_audio_oracle_source_evidence_preflight.py",
                "python tools/validate_audio_oracle_source_evidence_preflight.py",
            ],
            "completion_gate": "The preflight records the current collector readiness state without creating comparison results.",
            "behavior_change_allowed": False,
        },
        {
            "stage_id": "all_track_fusion_source_spc",
            "rank": 2,
            "purpose": "Regenerate all-track fused CHANGE_MUSIC/C0:AB06 last-key-on source SPC snapshots under ignored build/audio.",
            "expected_outputs": {
                "frontier_json": "build/audio/c0ab06-change-music-fusion-frontier-all/c0ab06-change-music-fusion-frontier-all.json",
                "expected_load_paths": 191,
                "expected_payload_matches": 191,
                "expected_key_on_snapshots": 190,
                "known_no_key_on_track": {"track_id": 4, "track_name": "NONE2"},
            },
            "commands": [
                "python tools/collect_audio_c0ab06_change_music_fusion_frontier.py --all-tracks --output build/audio/c0ab06-change-music-fusion-frontier-all/c0ab06-change-music-fusion-frontier-all.json",
                "python tools/validate_audio_c0ab06_change_music_fusion_frontier.py build/audio/c0ab06-change-music-fusion-frontier-all/c0ab06-change-music-fusion-frontier-all.json",
            ],
            "completion_gate": "All CHANGE_MUSIC load paths validate, payload regions match, and all snapshot-backed tracks have valid last-key-on SPC files.",
            "behavior_change_allowed": False,
        },
        {
            "stage_id": "spc_index_and_renderer_jobs",
            "rank": 3,
            "purpose": "Index the regenerated SPC snapshots and build the all-track libgme/snes_spc renderer job queue.",
            "expected_outputs": {
                "snapshot_index": "build/audio/c0ab06-change-music-fusion-spc-all/c0ab06-change-music-fusion-spc-all-snapshots.json",
                "renderer_jobs": "build/audio/c0ab06-change-music-fusion-render-jobs-all/snes_spc-jobs.json",
                "expected_renderer_jobs": 190,
                "expected_skipped_records": 1,
            },
            "commands": [
                "python tools/build_audio_c0ab06_change_music_fusion_spc_index.py --frontier build/audio/c0ab06-change-music-fusion-frontier-all/c0ab06-change-music-fusion-frontier-all.json --output build/audio/c0ab06-change-music-fusion-spc-all/c0ab06-change-music-fusion-spc-all-snapshots.json",
                "python tools/build_audio_backend_jobs_from_spc_index.py --snapshot-index build/audio/c0ab06-change-music-fusion-spc-all/c0ab06-change-music-fusion-spc-all-snapshots.json --out build/audio/c0ab06-change-music-fusion-render-jobs-all",
                "python tools/validate_audio_backend_jobs.py build/audio/c0ab06-change-music-fusion-render-jobs-all/snes_spc-jobs.json",
            ],
            "completion_gate": "The job index contains 190 renderable snes_spc jobs and preserves the single no-key-on skip.",
            "behavior_change_allowed": False,
        },
        {
            "stage_id": "libgme_render_and_metrics",
            "rank": 4,
            "purpose": "Render source WAVs from regenerated SPC snapshots, collect backend statuses, and refresh render metrics.",
            "expected_outputs": {
                "backend_summary": "build/audio/c0ab06-change-music-fusion-render-jobs-all/snes_spc-result-summary.json",
                "render_metrics": "build/audio/c0ab06-change-music-fusion-render-jobs-all/libgme-render-metrics.json",
                "expected_ok_results": 190,
                "expected_audible_metrics": 190,
            },
            "commands": [
                "cmake -S tools/libgme_audio_harness -B build/audio/libgme-audio-harness-msvc -G \"Visual Studio 17 2022\" -DLIBGME_ROOT=<local-libgme-checkout>",
                "cmake --build build/audio/libgme-audio-harness-msvc --config RelWithDebInfo",
                "python tools/run_audio_backend_batch.py --jobs build/audio/c0ab06-change-music-fusion-render-jobs-all/snes_spc-jobs.json --summary build/audio/c0ab06-change-music-fusion-render-jobs-all/snes_spc-result-summary.json --mode external --force --external build/audio/libgme-audio-harness-msvc/RelWithDebInfo/earthbound_libgme_audio_harness.exe --job \"{job}\" --result \"{result}\"",
                "python tools/validate_audio_backend_result_summary.py build/audio/c0ab06-change-music-fusion-render-jobs-all/snes_spc-result-summary.json",
                "python tools/collect_audio_render_metrics.py --jobs build/audio/c0ab06-change-music-fusion-render-jobs-all/snes_spc-jobs.json --output build/audio/c0ab06-change-music-fusion-render-jobs-all/libgme-render-metrics.json",
                "python tools/validate_audio_render_metrics.py build/audio/c0ab06-change-music-fusion-render-jobs-all/libgme-render-metrics.json",
            ],
            "completion_gate": "Every snapshot-backed track has a valid backend result and audible libgme render metrics.",
            "behavior_change_allowed": False,
        },
        {
            "stage_id": "playback_oracle_plan_refresh",
            "rank": 5,
            "purpose": "Rebuild committed metadata that points to the regenerated source SPC/WAV evidence.",
            "expected_outputs": {
                "playback_manifest": "build/audio/c0ab06-change-music-fusion-render-jobs-all/playback-export-manifest.json",
                "oracle_comparison_plan": "manifests/audio-oracle-comparison-plan-all-tracks.json",
                "expected_oracle_jobs": 190,
            },
            "commands": [
                "python tools/build_audio_playback_export_manifest.py",
                "python tools/validate_audio_playback_export_manifest.py",
                "python tools/build_audio_oracle_comparison_plan.py --all-tracks --json manifests/audio-oracle-comparison-plan-all-tracks.json --markdown notes/audio-oracle-comparison-plan-all-tracks.md --output-root build/audio/oracle-comparison-all-tracks",
                "python tools/validate_audio_oracle_comparison_plan.py manifests/audio-oracle-comparison-plan-all-tracks.json --allow-missing-source-outputs",
                "python tools/build_audio_oracle_source_evidence_preflight.py",
                "python tools/validate_audio_oracle_source_evidence_preflight.py",
            ],
            "completion_gate": "The preflight no longer reports missing source SPC/WAV artifacts for the 190 oracle jobs.",
            "behavior_change_allowed": False,
        },
        {
            "stage_id": "reference_capture_and_collection",
            "rank": 6,
            "purpose": "After source evidence exists, import independent external-emulator captures and collect comparison results.",
            "expected_outputs": {
                "representative_jobs": 16,
                "all_track_jobs": 190,
                "comparison_summary": "build/audio/oracle-comparison-all-tracks/oracle-comparison-summary.json",
            },
            "commands": [
                "python tools/import_audio_oracle_reference_capture.py --plan manifests/audio-oracle-comparison-plan-all-tracks.json --track-id <track-id> --spc <external-capture.spc> --wav <external-render.wav> --oracle-id <mesen2|bsnes_higan|mednafen> --emulator-version <version> --capture-command <command> --audio-settings <settings> --overwrite",
                "python tools/validate_audio_oracle_reference_capture.py --plan manifests/audio-oracle-comparison-plan-all-tracks.json --track-id <track-id>",
                "python tools/collect_audio_oracle_comparison_results.py --plan manifests/audio-oracle-comparison-plan-all-tracks.json --summary build/audio/oracle-comparison-all-tracks/oracle-comparison-summary.json",
                "python tools/validate_audio_oracle_comparison_summary.py build/audio/oracle-comparison-all-tracks/oracle-comparison-summary.json",
                "python tools/build_audio_oracle_verification_report.py --summary build/audio/oracle-comparison-all-tracks/oracle-comparison-summary.json --json manifests/audio-oracle-verification-report-all-tracks.json --markdown notes/audio-oracle-verification-report-all-tracks.md",
                "python tools/validate_audio_oracle_verification_report.py manifests/audio-oracle-verification-report-all-tracks.json --require-representative-pass",
            ],
            "completion_gate": "Representative independent captures pass before release-quality playback is claimed.",
            "behavior_change_allowed": False,
        },
    ]
    return {
        "schema": "earthbound-decomp.audio-oracle-source-regeneration-plan.v1",
        "status": "oracle_source_regeneration_plan_ready_policy_preserved",
        "references": [
            "manifests/audio-oracle-source-evidence-preflight.json",
            "manifests/audio-independent-oracle-handoff-matrix.json",
            "manifests/audio-duration-next-actions-plan.json",
            "notes/audio-backend-contract.md",
        ],
        "source_preflight_status": preflight.get("status"),
        "source_handoff_status": handoff.get("status"),
        "source_next_action_lane": lane.get("lane_id"),
        "summary": {
            "stage_count": len(stages),
            "current_collector_ready_jobs": int(preflight_summary.get("collector_ready_job_count", 0)),
            "current_source_blocked_jobs": int(preflight_summary.get("collector_blocked_missing_source_evidence_count", 0)),
            "current_source_spc_present_count": int(preflight_summary.get("source_spc_present_count", 0)),
            "current_source_render_wav_present_count": int(preflight_summary.get("source_render_wav_present_count", 0)),
            "all_track_oracle_jobs": int(preflight_summary.get("job_count", 0)),
            "representative_capture_jobs": len(representative_tracks(handoff)),
            "expected_source_spc_after_regeneration": 190,
            "expected_source_render_wav_after_regeneration": 190,
            "expected_known_no_keyon_skips": 1,
            "behavior_change_allowed": False,
            "promotion_allowed_by_plan": False,
        },
        "representative_handoff_tracks": representative_tracks(handoff),
        "regeneration_policy": [
            "This plan regenerates ignored local source evidence and committed diagnostics only; it does not change playback/export behavior.",
            "All generated SPC/WAV/backend outputs remain under ignored build/audio paths and must not be distributed.",
            "The source regeneration lane must complete before collecting oracle comparison summaries in a clean workspace.",
            "Independent external-emulator captures remain a separate operator-provided evidence step after source SPC/WAV evidence exists.",
            "Exact durations, loop metadata, and release-quality playback claims remain blocked until their existing gates pass.",
        ],
        "stages": stages,
        "post_plan_validation_commands": [
            "python tools/build_audio_oracle_source_regeneration_plan.py",
            "python tools/validate_audio_oracle_source_regeneration_plan.py",
            "python tools/validate_audio_oracle_source_evidence_preflight.py",
            "python tools/validate_audio_oracle_comparison_plan.py manifests/audio-oracle-comparison-plan-all-tracks.json --allow-missing-source-outputs",
            "python tools/validate_audio_oracle_verification_report.py manifests/audio-oracle-verification-report-all-tracks.json --require-representative-pass",
            "python tools/validate_audio_independent_oracle_handoff_matrix.py",
            "python tools/validate_audio_independent_oracle_capture_packet.py",
            "python tools/validate_audio_duration_next_actions_plan.py",
            "git diff --check",
        ],
    }


def render_markdown(data: dict[str, Any]) -> str:
    summary = data["summary"]
    stage_rows = [
        "| {rank} | `{stage}` | {purpose} | {commands} |".format(
            rank=stage["rank"],
            stage=stage["stage_id"],
            purpose=stage["purpose"],
            commands=len(stage["commands"]),
        )
        for stage in data["stages"]
    ]
    rep_rows = [
        "| {order} | {track:03d} | `{name}` | `{phase}` | `{uncertainty}` |".format(
            order=record["execution_order"],
            track=record["track_id"],
            name=record["track_name"],
            phase=record["phase"],
            uncertainty=record["primary_uncertainty"],
        )
        for record in data["representative_handoff_tracks"]
    ]
    command_rows = [f"- `{command}`" for command in data["post_plan_validation_commands"]]
    return "\n".join(
        [
            "# Audio Oracle Source Regeneration Plan",
            "",
            "Status: source evidence regeneration is planned; current playback/export behavior is preserved.",
            "",
            "## Summary",
            "",
            f"- stages: `{summary['stage_count']}`",
            f"- current collector-ready jobs: `{summary['current_collector_ready_jobs']}`",
            f"- current source-blocked jobs: `{summary['current_source_blocked_jobs']}`",
            f"- current source SPCs present: `{summary['current_source_spc_present_count']}`",
            f"- current source render WAVs present: `{summary['current_source_render_wav_present_count']}`",
            f"- all-track oracle jobs: `{summary['all_track_oracle_jobs']}`",
            f"- representative capture jobs: `{summary['representative_capture_jobs']}`",
            f"- expected source SPCs after regeneration: `{summary['expected_source_spc_after_regeneration']}`",
            f"- expected source render WAVs after regeneration: `{summary['expected_source_render_wav_after_regeneration']}`",
            "",
            "## Stages",
            "",
            "| Rank | Stage | Purpose | Commands |",
            "| ---: | --- | --- | ---: |",
            *stage_rows,
            "",
            "## Representative Handoff Tracks",
            "",
            "| Order | Track | Name | Phase | Primary uncertainty |",
            "| ---: | ---: | --- | --- | --- |",
            *rep_rows,
            "",
            "## Validation",
            "",
            *command_rows,
            "",
            "## Policy",
            "",
            *[f"- {item}" for item in data["regeneration_policy"]],
            "",
            "## Remaining Uncertainty",
            "",
            "- The source SPC/WAV regeneration chain needs a user-provided ROM and local libgme harness build.",
            "- Independent emulator captures are still external inputs after the source evidence layer exists.",
            "- Exact duration, loop, finite-ending, and control-semantics gates remain unchanged.",
            "",
        ]
    )


def main() -> int:
    args = parse_args()
    data = build_plan(
        load_json(Path(args.preflight)),
        load_json(Path(args.handoff)),
        load_json(Path(args.next_actions)),
    )
    output = Path(args.output)
    notes = Path(args.notes)
    output.parent.mkdir(parents=True, exist_ok=True)
    notes.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    notes.write_text(render_markdown(data), encoding="utf-8")
    print(
        "Built oracle source regeneration plan: "
        f"{data['summary']['stage_count']} stages, "
        f"{data['summary']['current_source_blocked_jobs']} source-blocked jobs"
    )
    print(f"Wrote {output}")
    print(f"Wrote {notes}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
