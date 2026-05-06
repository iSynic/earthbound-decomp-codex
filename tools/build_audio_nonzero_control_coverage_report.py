#!/usr/bin/env python3
"""Build a coverage report for nonzero audio control-semantics probe blockers."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_UNCERTAINTY = ROOT / "manifests" / "audio-duration-uncertainty-register.json"
DEFAULT_PROBE_PLAN = ROOT / "manifests" / "audio-nonzero-control-probe-plan.json"
DEFAULT_OUTPUT = ROOT / "manifests" / "audio-nonzero-control-coverage-report.json"
DEFAULT_NOTES = ROOT / "notes" / "audio-nonzero-control-coverage-report.md"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build nonzero control coverage report.")
    parser.add_argument("--uncertainty", default=str(DEFAULT_UNCERTAINTY), help="Duration uncertainty register JSON.")
    parser.add_argument("--probe-plan", default=str(DEFAULT_PROBE_PLAN), help="Nonzero control probe plan JSON.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Coverage report JSON output.")
    parser.add_argument("--notes", default=str(DEFAULT_NOTES), help="Coverage report markdown output.")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def nonzero_blockers(uncertainty: dict[str, Any]) -> list[dict[str, Any]]:
    records = [
        record
        for record in uncertainty.get("tracks", [])
        if record.get("primary_uncertainty") == "non_zero_control_semantics_pending"
    ]
    records.sort(key=lambda record: int(record["track_id"]))
    return records


def job_record(job: dict[str, Any], blocker_track_ids: set[int]) -> dict[str, Any]:
    candidates = job.get("source_candidates", [])
    candidate_track_ids = [int(candidate["track_id"]) for candidate in candidates]
    unique_candidate_track_ids = sorted(set(candidate_track_ids))
    blocker_candidate_track_ids = sorted(set(candidate_track_ids) & blocker_track_ids)
    return {
        "job_id": job["job_id"],
        "command": job["command"],
        "reader_pc": job["reader_pc"],
        "driver_offset": job.get("driver_offset"),
        "read_count": int(job.get("read_count", 0)),
        "affected_kind": job.get("affected_kind"),
        "semantic_status": job.get("semantic_status"),
        "priority_rank": int(job.get("priority_rank", 0)),
        "source_candidate_count": len(candidates),
        "unique_source_candidate_track_count": len(unique_candidate_track_ids),
        "blocker_source_candidate_track_count": len(blocker_candidate_track_ids),
        "unique_source_candidate_track_ids": unique_candidate_track_ids,
        "blocker_source_candidate_track_ids": blocker_candidate_track_ids,
        "accepted_control_effect_classifications": job.get("accepted_control_effect_classifications", []),
        "promotion_allowed_by_plan": bool(job.get("promotion_allowed_by_plan")),
        "probe_outputs": job.get("probe_outputs", {}),
    }


def build_report(uncertainty: dict[str, Any], probe_plan: dict[str, Any]) -> dict[str, Any]:
    blockers = nonzero_blockers(uncertainty)
    blocker_track_ids = {int(record["track_id"]) for record in blockers}
    jobs = [job_record(job, blocker_track_ids) for job in probe_plan.get("jobs", [])]
    jobs.sort(key=lambda item: (int(item["priority_rank"]), item["job_id"]))
    source_track_counter: Counter[int] = Counter()
    for job in probe_plan.get("jobs", []):
        for candidate in job.get("source_candidates", []):
            source_track_counter[int(candidate["track_id"])] += 1
    source_track_ids = set(source_track_counter)
    blocker_source_track_ids = source_track_ids & blocker_track_ids
    command_counts: Counter[str] = Counter(str(job["command"]) for job in probe_plan.get("jobs", []))
    reader_counts: Counter[str] = Counter(str(job["reader_pc"]) for job in probe_plan.get("jobs", []))
    affected_counts: Counter[str] = Counter(str(job.get("affected_kind")) for job in probe_plan.get("jobs", []))
    blocker_export_counts: Counter[str] = Counter(str(record.get("export_class")) for record in blockers)
    return {
        "schema": "earthbound-decomp.audio-nonzero-control-coverage-report.v1",
        "status": "nonzero_control_coverage_ready_probe_outputs_pending",
        "references": [
            "manifests/audio-duration-uncertainty-register.json",
            "manifests/audio-nonzero-control-probe-plan.json",
        ],
        "source_plan_status": probe_plan.get("status"),
        "summary": {
            "blocker_track_count": len(blockers),
            "blocker_export_class_counts": dict(sorted(blocker_export_counts.items())),
            "probe_job_count": len(jobs),
            "command_job_counts": dict(sorted(command_counts.items())),
            "reader_pc_job_counts": dict(sorted(reader_counts.items())),
            "affected_kind_job_counts": dict(sorted(affected_counts.items())),
            "source_candidate_record_count": sum(int(job["source_candidate_count"]) for job in jobs),
            "unique_source_candidate_track_count": len(source_track_ids),
            "blocker_source_candidate_track_count": len(blocker_source_track_ids),
            "source_candidate_tracks_outside_primary_blocker_count": len(source_track_ids - blocker_track_ids),
            "blocker_tracks_without_source_candidate_count": len(blocker_track_ids - source_track_ids),
            "frontier_pack_count": int(probe_plan.get("summary", {}).get("frontier_pack_count", 0)),
            "sequence_promotion_allowed": False,
            "public_exact_promotion_allowed": False,
        },
        "coverage_policy": [
            "This report maps current nonzero-control blockers to the existing probe jobs; it does not run the harness.",
            "Source candidates are representative evidence anchors, not complete coverage of all blocked tracks.",
            "Promotion stays blocked until imported probe outputs classify command effects and refresh the duration uncertainty register.",
            "Independent external-emulator oracle evidence remains a separate release-quality gate.",
        ],
        "source_candidate_reuse": [
            {
                "track_id": track_id,
                "track_name": next(
                    (
                        candidate.get("track_name")
                        for job in probe_plan.get("jobs", [])
                        for candidate in job.get("source_candidates", [])
                        if int(candidate["track_id"]) == track_id
                    ),
                    None,
                ),
                "job_count": count,
                "is_primary_nonzero_blocker": track_id in blocker_track_ids,
            }
            for track_id, count in sorted(source_track_counter.items())
        ],
        "jobs": jobs,
    }


def render_markdown(data: dict[str, Any]) -> str:
    summary = data["summary"]
    job_rows = [
        "| `{job_id}` | `{command}` | `{reader}` | `{kind}` | {candidates} | {blockers} | `{promote}` |".format(
            job_id=job["job_id"],
            command=job["command"],
            reader=job["reader_pc"],
            kind=job["affected_kind"],
            candidates=job["source_candidate_count"],
            blockers=job["blocker_source_candidate_track_count"],
            promote=job["promotion_allowed_by_plan"],
        )
        for job in data["jobs"]
    ]
    reuse_rows = [
        "| {track_id:03d} | `{track_name}` | {job_count} | `{blocker}` |".format(
            track_id=record["track_id"],
            track_name=record["track_name"],
            job_count=record["job_count"],
            blocker=record["is_primary_nonzero_blocker"],
        )
        for record in data["source_candidate_reuse"]
    ]
    return "\n".join(
        [
            "# Audio Nonzero Control Coverage Report",
            "",
            "Status: nonzero control coverage is mapped; probe outputs are still pending and current export behavior is preserved.",
            "",
            "## Summary",
            "",
            f"- blocker tracks: `{summary['blocker_track_count']}`",
            f"- blocker export classes: `{summary['blocker_export_class_counts']}`",
            f"- probe jobs: `{summary['probe_job_count']}`",
            f"- command jobs: `{summary['command_job_counts']}`",
            f"- reader PC jobs: `{summary['reader_pc_job_counts']}`",
            f"- affected kinds: `{summary['affected_kind_job_counts']}`",
            f"- source candidate records: `{summary['source_candidate_record_count']}`",
            f"- unique source candidate tracks: `{summary['unique_source_candidate_track_count']}`",
            f"- blocker source candidate tracks: `{summary['blocker_source_candidate_track_count']}`",
            f"- blocker tracks without source candidate: `{summary['blocker_tracks_without_source_candidate_count']}`",
            f"- sequence promotion allowed: `{summary['sequence_promotion_allowed']}`",
            "",
            "## Probe Jobs",
            "",
            "| Job | Command | Reader PC | Affected kind | Source candidates | Blocker candidates | Promotion allowed |",
            "| --- | --- | --- | --- | ---: | ---: | --- |",
            *job_rows,
            "",
            "## Source Candidate Reuse",
            "",
            "| Track | Name | Probe job count | Primary nonzero blocker |",
            "| ---: | --- | ---: | --- |",
            *reuse_rows,
            "",
            "## Coverage Policy",
            "",
            *[f"- {item}" for item in data["coverage_policy"]],
            "",
            "## Remaining Uncertainty",
            "",
            "- The 7 probe jobs are representative anchors for 155 blocked tracks, not full track coverage.",
            "- 146 primary nonzero-control blocker tracks do not appear as source candidates in the current probe plan.",
            "- Probe output import and duration-register refresh remain required before any exact-duration promotion.",
            "",
        ]
    )


def main() -> int:
    args = parse_args()
    data = build_report(load_json(Path(args.uncertainty)), load_json(Path(args.probe_plan)))
    output = Path(args.output)
    notes = Path(args.notes)
    output.parent.mkdir(parents=True, exist_ok=True)
    notes.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    notes.write_text(render_markdown(data), encoding="utf-8")
    print(
        "Built nonzero control coverage report: "
        f"{data['summary']['probe_job_count']} jobs, "
        f"{data['summary']['blocker_track_count']} blockers"
    )
    print(f"Wrote {output}")
    print(f"Wrote {notes}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
