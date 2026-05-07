#!/usr/bin/env python3
"""Build the focused loop-point evidence plan for preview-only loop/held tracks."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_UNCERTAINTY = ROOT / "manifests" / "audio-duration-uncertainty-register.json"
DEFAULT_EXPORT_PLAN = ROOT / "manifests" / "audio-export-plan.json"
DEFAULT_PACK_CONTRACTS = ROOT / "manifests" / "audio-pack-contracts.json"
DEFAULT_ORACLE_PLAN = ROOT / "manifests" / "audio-oracle-comparison-plan-all-tracks.json"
DEFAULT_OUTPUT = ROOT / "manifests" / "audio-loop-point-evidence-plan.json"
DEFAULT_NOTES = ROOT / "notes" / "audio-loop-point-evidence-plan.md"
REQUIRED_LOOP_FIELDS = ["intro_samples", "loop_start_sample", "loop_end_sample", "measured_by"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build audio loop-point evidence plan.")
    parser.add_argument("--uncertainty", default=str(DEFAULT_UNCERTAINTY), help="Duration uncertainty register JSON.")
    parser.add_argument("--export-plan", default=str(DEFAULT_EXPORT_PLAN), help="Audio export plan JSON.")
    parser.add_argument("--pack-contracts", default=str(DEFAULT_PACK_CONTRACTS), help="Audio pack contracts JSON.")
    parser.add_argument("--oracle-plan", default=str(DEFAULT_ORACLE_PLAN), help="All-track oracle plan JSON.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Loop-point evidence plan JSON output.")
    parser.add_argument("--notes", default=str(DEFAULT_NOTES), help="Loop-point evidence plan markdown output.")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def by_track(records: list[dict[str, Any]], key: str = "track_id") -> dict[int, dict[str, Any]]:
    return {int(record[key]): record for record in records}


def by_pack(records: list[dict[str, Any]]) -> dict[int, dict[str, Any]]:
    return {int(record["pack_id"]): record for record in records}


def source_candidate(oracle_job: dict[str, Any]) -> dict[str, Any]:
    return {
        "oracle_job_id": oracle_job.get("job_id"),
        "diagnostic_focus": oracle_job.get("diagnostic_focus"),
        "source_spc": oracle_job.get("source_spc", {}),
        "source_render": oracle_job.get("source_render", {}),
        "reference_capture_outputs": oracle_job.get("reference_capture_outputs", {}),
    }


def loop_gap(export_record: dict[str, Any]) -> dict[str, Any]:
    loop = export_record.get("loop_metadata", {})
    evidence = loop.get("loop_point_evidence", {})
    missing = [field for field in REQUIRED_LOOP_FIELDS if loop.get(field) is None]
    return {
        "status": evidence.get("status"),
        "missing_fields": missing,
        "required_evidence": evidence.get("required_evidence", []),
        "preview_policy": loop.get("preview_policy", {}),
    }


def build_jobs(
    uncertainty: dict[str, Any],
    export_plan: dict[str, Any],
    pack_contracts: dict[str, Any],
    oracle_plan: dict[str, Any],
) -> list[dict[str, Any]]:
    export_by_track = by_track(export_plan.get("tracks", []))
    contracts_by_track = by_track(pack_contracts.get("tracks", []))
    packs_by_id = by_pack(pack_contracts.get("audio_packs", []))
    oracle_by_track = by_track(oracle_plan.get("jobs", []))
    jobs: list[dict[str, Any]] = []
    loop_tracks = [
        record
        for record in uncertainty.get("tracks", [])
        if record.get("primary_uncertainty") == "loop_point_metadata_pending"
    ]
    loop_tracks.sort(key=lambda record: int(record["track_id"]))
    for order, record in enumerate(loop_tracks, start=1):
        track_id = int(record["track_id"])
        export_record = export_by_track[track_id]
        contract = contracts_by_track[track_id]
        packs = contract.get("packs", {})
        primary_pack_id = int(packs["primary_sample_pack"])
        primary_pack = packs_by_id[primary_pack_id]
        sequence_pack = packs.get("sequence_pack")
        no_sequence_pack = sequence_pack is None
        oracle_job = oracle_by_track[track_id]
        jobs.append(
            {
                "job_id": f"loop-point-track-{track_id:03d}-{str(record['track_name']).lower()}",
                "execution_order": order,
                "track_id": track_id,
                "track_name": record["track_name"],
                "primary_uncertainty": record["primary_uncertainty"],
                "export_class": export_record.get("export_class"),
                "export_status": export_record.get("export_status"),
                "recommended_mode": export_record.get("recommended_mode"),
                "duration_seconds": export_record.get("duration_seconds"),
                "loop_preview_policy": {
                    "loop_count": export_record.get("loop_count"),
                    "fade_seconds": export_record.get("fade_seconds"),
                    "current_public_mode": export_record.get("recommended_mode"),
                },
                "pack_context": {
                    "primary_sample_pack": primary_pack_id,
                    "secondary_sample_pack": packs.get("secondary_sample_pack"),
                    "sequence_pack": sequence_pack,
                    "no_dedicated_sequence_pack": no_sequence_pack,
                    "load_order": contract.get("load_order", []),
                    "cold_start_load_order": contract.get("cold_start_load_order", []),
                    "primary_pack_source": {
                        "asset_id": primary_pack.get("asset_id"),
                        "range": primary_pack.get("range"),
                        "sha1": primary_pack.get("sha1"),
                        "stream_summary": primary_pack.get("stream", {}).get("summary", {}),
                    },
                },
                "source_candidate": source_candidate(oracle_job),
                "loop_gap": loop_gap(export_record),
                "evidence_questions": [
                    "Does the track sustain by held DSP voice state, BRR sample loop flags, or an actual driver loop?",
                    "If it loops, what are the sample-accurate intro, loop start, and loop end positions?",
                    "If it is held or policy-only, should public export remain loop-count/fade preview rather than exact loop metadata?",
                ],
                "required_runtime_evidence": [
                    "DSP voice envelope/key-on/key-off state across the preview tail",
                    "BRR/sample-loop evidence for voices active at the proposed loop boundary",
                    "rendered PCM repeat/hold evidence over at least the existing 120-second preview window",
                    "classification as exact_loop_points_available, held_policy_no_exact_loop_points, or unresolved",
                ],
                "dry_run_command": f"python tools/run_audio_loop_point_evidence_plan.py --job-id loop-point-track-{track_id:03d}-{str(record['track_name']).lower()} --mode dry-run-plan",
                "audit_command": f"python tools/run_audio_loop_point_evidence_plan.py --job-id loop-point-track-{track_id:03d}-{str(record['track_name']).lower()} --mode audit-current-export",
                "promotion_allowed_by_plan": False,
                "post_evidence_commands": [
                    "python tools/build_audio_export_plan.py",
                    "python tools/validate_audio_export_plan.py",
                    "python tools/build_audio_duration_uncertainty_register.py",
                    "python tools/validate_audio_duration_uncertainty_register.py",
                ],
            }
        )
    return jobs


def build_plan(
    uncertainty: dict[str, Any],
    export_plan: dict[str, Any],
    pack_contracts: dict[str, Any],
    oracle_plan: dict[str, Any],
) -> dict[str, Any]:
    jobs = build_jobs(uncertainty, export_plan, pack_contracts, oracle_plan)
    track_counts: Counter[str] = Counter(str(job["track_name"]) for job in jobs)
    pack_counts: Counter[str] = Counter(str(job["pack_context"]["primary_sample_pack"]) for job in jobs)
    focus_counts: Counter[str] = Counter(str(job["source_candidate"]["diagnostic_focus"]) for job in jobs)
    no_sequence_pack_count = sum(1 for job in jobs if job["pack_context"]["no_dedicated_sequence_pack"])
    return {
        "schema": "earthbound-decomp.audio-loop-point-evidence-plan.v1",
        "status": "loop_point_evidence_plan_ready_preview_policy_preserved",
        "references": [
            "manifests/audio-duration-uncertainty-register.json",
            "manifests/audio-export-plan.json",
            "manifests/audio-pack-contracts.json",
            "manifests/audio-oracle-comparison-plan-all-tracks.json",
        ],
        "summary": {
            "job_count": len(jobs),
            "track_names": sorted(track_counts),
            "primary_sample_pack_counts": dict(sorted(pack_counts.items())),
            "no_dedicated_sequence_pack_count": no_sequence_pack_count,
            "diagnostic_focus_counts": dict(sorted(focus_counts.items())),
            "preview_policy_loop_count": 2,
            "preview_policy_fade_seconds": 5.0,
            "promotion_allowed_by_plan": False,
            "public_exact_loop_export_ready": False,
        },
        "decision_policy": [
            "Current playback/export behavior stays loop-count-plus-fade preview until loop or hold evidence is explicit.",
            "These five tracks are not blocked by broad sequence-pack command promotion; they share primary sample pack 5 with no dedicated sequence pack.",
            "Exact loop export requires sample-accurate intro, loop start, loop end, and measured_by evidence.",
            "A held/SFX classification is valid evidence only if it keeps public exact loop export blocked or defines a separate held-policy export.",
        ],
        "accepted_evidence_statuses": [
            "exact_loop_points_available",
            "held_policy_no_exact_loop_points",
            "unresolved_loop_or_hold_policy",
        ],
        "post_evidence_validation_commands": [
            "python tools/run_audio_loop_point_evidence_plan.py --mode audit-current-export",
            "python tools/validate_audio_loop_point_evidence_run_summary.py",
            "python tools/validate_audio_loop_point_evidence_plan.py",
            "python tools/validate_audio_export_plan.py",
            "python tools/validate_audio_duration_uncertainty_register.py",
        ],
        "jobs": jobs,
    }


def render_markdown(data: dict[str, Any]) -> str:
    summary = data["summary"]
    rows = [
        "| {order} | `{track_id:03d}` | `{track_name}` | `{pack}` | `{focus}` | `{status}` | `{missing}` |".format(
            order=job["execution_order"],
            track_id=job["track_id"],
            track_name=job["track_name"],
            pack=job["pack_context"]["primary_sample_pack"],
            focus=job["source_candidate"]["diagnostic_focus"],
            status=job["loop_gap"]["status"],
            missing=job["loop_gap"]["missing_fields"],
        )
        for job in data["jobs"]
    ]
    return "\n".join(
        [
            "# Audio Loop Point Evidence Plan",
            "",
            "Status: loop-point evidence plan is ready; current loop-count/fade preview behavior remains unchanged.",
            "",
            "## Summary",
            "",
            f"- jobs: `{summary['job_count']}`",
            f"- tracks: `{summary['track_names']}`",
            f"- primary sample packs: `{summary['primary_sample_pack_counts']}`",
            f"- no dedicated sequence pack: `{summary['no_dedicated_sequence_pack_count']}`",
            f"- diagnostic focus counts: `{summary['diagnostic_focus_counts']}`",
            f"- preview policy: `{summary['preview_policy_loop_count']}` loops plus `{summary['preview_policy_fade_seconds']}` second fade",
            f"- promotion allowed by plan: `{summary['promotion_allowed_by_plan']}`",
            f"- public exact loop export ready: `{summary['public_exact_loop_export_ready']}`",
            "",
            "## Decision Policy",
            "",
            *[f"- {item}" for item in data["decision_policy"]],
            "",
            "## Jobs",
            "",
            "| Order | Track | Name | Primary pack | Oracle focus | Loop evidence status | Missing fields |",
            "| ---: | ---: | --- | ---: | --- | --- | --- |",
            *rows,
            "",
            "## Accepted Evidence Statuses",
            "",
            *[f"- `{status}`" for status in data["accepted_evidence_statuses"]],
            "",
            "## Post Evidence Validation",
            "",
            *[f"- `{command}`" for command in data["post_evidence_validation_commands"]],
            "",
        ]
    )


def main() -> int:
    args = parse_args()
    data = build_plan(
        load_json(Path(args.uncertainty)),
        load_json(Path(args.export_plan)),
        load_json(Path(args.pack_contracts)),
        load_json(Path(args.oracle_plan)),
    )
    output = Path(args.output)
    notes = Path(args.notes)
    output.parent.mkdir(parents=True, exist_ok=True)
    notes.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    notes.write_text(render_markdown(data), encoding="utf-8")
    print(
        "Built audio loop-point evidence plan: "
        f"{data['summary']['job_count']} jobs, "
        f"primary packs {data['summary']['primary_sample_pack_counts']}"
    )
    print(f"Wrote {output}")
    print(f"Wrote {notes}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
