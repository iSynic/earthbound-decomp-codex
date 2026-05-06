#!/usr/bin/env python3
"""Collect targeted non-0x00 control probe result status."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import validate_audio_nonzero_control_probe_result


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PLAN = ROOT / "manifests" / "audio-nonzero-control-probe-plan.json"
DEFAULT_OUTPUT = ROOT / "manifests" / "audio-nonzero-control-probe-results-summary.json"
DEFAULT_NOTES = ROOT / "notes" / "audio-nonzero-control-probe-results-summary.md"

RESOLVED_CLASSIFICATIONS = {"ef_call_return", "timing_toggle", "earthbound_variant_ff", "unreachable"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect audio non-0x00 control probe result status.")
    parser.add_argument("--plan", default=str(DEFAULT_PLAN), help="Probe plan manifest.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Summary JSON output.")
    parser.add_argument("--notes", default=str(DEFAULT_NOTES), help="Summary markdown output.")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_repo_path(path_text: str) -> Path:
    path = Path(path_text)
    return path if path.is_absolute() else ROOT / path


def result_path(job: dict[str, Any]) -> Path:
    return resolve_repo_path(str(job.get("probe_outputs", {}).get("result_json", "")))


def manifest_path(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def result_resolves_control_effect(result: dict[str, Any] | None, valid: bool) -> bool:
    if not valid or result is None:
        return False
    return str(result.get("control_effect_classification")) in RESOLVED_CLASSIFICATIONS


def command_blocker(command: str) -> str:
    if command == "0xEF":
        return "ef_call_return_effect"
    if command in {"0xFD", "0xFE"}:
        return "timing_toggle_effect"
    if command == "0xFF":
        return "earthbound_variant_ff_effect"
    return "non_zero_control_semantics_pending"


def remaining_blockers(job: dict[str, Any], result: dict[str, Any] | None, valid: bool) -> list[str]:
    blockers: list[str] = []
    if not result_resolves_control_effect(result, valid):
        blockers.append("non_zero_control_semantics_pending")
        blockers.append(command_blocker(str(job.get("command"))))
    return blockers


def collect(plan: dict[str, Any]) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    status_counts: Counter[str] = Counter()
    validation_counts: Counter[str] = Counter()
    classification_counts: Counter[str] = Counter()
    command_counts: Counter[str] = Counter()
    blocker_counts: Counter[str] = Counter()
    resolved_job_ids: list[str] = []

    for job in plan.get("jobs", []):
        path = result_path(job)
        command = str(job["command"])
        record: dict[str, Any] = {
            "job_id": job["job_id"],
            "command": command,
            "reader_pc": job["reader_pc"],
            "read_count": int(job["read_count"]),
            "affected_kind": job["affected_kind"],
            "result_path": manifest_path(path),
            "result_exists": path.exists(),
            "status": "pending",
            "valid": False,
            "control_effect_classification": "pending",
            "errors": [],
            "remaining_blockers": [],
            "promotion_allowed": False,
        }
        result: dict[str, Any] | None = None
        if path.exists():
            result = load_json(path)
            errors = validate_audio_nonzero_control_probe_result.validate(result, job)
            record["status"] = str(result.get("status", "unknown"))
            record["valid"] = not errors
            record["control_effect_classification"] = str(result.get("control_effect_classification", "unknown"))
            record["errors"] = errors
            record["promotion_allowed"] = bool(result.get("promotion_allowed_by_result"))
            if result_resolves_control_effect(result, bool(record["valid"])):
                resolved_job_ids.append(str(job["job_id"]))
        record["remaining_blockers"] = remaining_blockers(job, result, bool(record["valid"]))
        for blocker in record["remaining_blockers"]:
            blocker_counts[str(blocker)] += 1
        status_counts[str(record["status"])] += 1
        validation_counts["valid" if record["valid"] else "invalid_or_pending"] += 1
        classification_counts[str(record["control_effect_classification"])] += 1
        command_counts[command] += 1
        records.append(record)

    return {
        "schema": "earthbound-decomp.audio-nonzero-control-probe-results-summary.v1",
        "status": "nonzero_control_probe_results_collected",
        "probe_plan": "manifests/audio-nonzero-control-probe-plan.json",
        "source_policy": plan.get("source_policy", {}),
        "summary": {
            "job_count": len(records),
            "result_count": sum(1 for record in records if record["result_exists"]),
            "valid_result_count": sum(1 for record in records if record["valid"]),
            "status_counts": dict(sorted(status_counts.items())),
            "validation_counts": dict(sorted(validation_counts.items())),
            "control_effect_classification_counts": dict(sorted(classification_counts.items())),
            "command_job_counts": dict(sorted(command_counts.items())),
            "remaining_blocker_job_counts": dict(sorted(blocker_counts.items())),
            "resolved_control_effect_job_ids": resolved_job_ids,
            "sequence_promotion_allowed": False,
            "semantic_status": (
                "nonzero_control_probe_outputs_pending"
                if not resolved_job_ids
                else "nonzero_control_probe_outputs_partially_collected"
            ),
        },
        "result_acceptance_policy": [
            "A result can resolve one command/reader-PC job only when it validates and classifies the effect as ef_call_return, timing_toggle, earthbound_variant_ff, or unreachable.",
            "EF, FD/FE, and FF classifications are command-family specific; a valid result cannot use a classification from the wrong family.",
            "This summary cannot directly promote public exact-duration exports.",
            "Validated command effects must be consumed by audio-sequence-command-semantics before exact-duration policy can change.",
        ],
        "results": records,
        "next_work": [
            "run the 0x0957 FF/FE/EF jobs first because that reader PC covers the highest-value command mix",
            "review invalid or unresolved probe outputs before changing sequence command semantics",
            "feed only validated control-effect classifications back into audio-sequence-command-semantics",
        ],
    }


def render_markdown(summary: dict[str, Any]) -> str:
    stats = summary["summary"]
    rows = [
        "| `{job_id}` | `{command}` | `{reader_pc}` | `{status}` | `{valid}` | `{classification}` | `{blockers}` | `{result_path}` |".format(
            job_id=record["job_id"],
            command=record["command"],
            reader_pc=record["reader_pc"],
            status=record["status"],
            valid=record["valid"],
            classification=record["control_effect_classification"],
            blockers=record["remaining_blockers"],
            result_path=record["result_path"],
        )
        for record in summary["results"]
    ]
    return "\n".join(
        [
            "# Audio Nonzero Control Probe Results Summary",
            "",
            "Status: no public export behavior changes; probe outputs are collected only when local ignored result files exist.",
            "",
            "## Summary",
            "",
            f"- probe jobs: `{stats['job_count']}`",
            f"- result files found: `{stats['result_count']}`",
            f"- valid results: `{stats['valid_result_count']}`",
            f"- statuses: `{stats['status_counts']}`",
            f"- validation: `{stats['validation_counts']}`",
            f"- classifications: `{stats['control_effect_classification_counts']}`",
            f"- command jobs: `{stats['command_job_counts']}`",
            f"- remaining blockers: `{stats['remaining_blocker_job_counts']}`",
            f"- resolved control-effect jobs: `{stats['resolved_control_effect_job_ids']}`",
            f"- sequence promotion allowed: `{stats['sequence_promotion_allowed']}`",
            "",
            "## Acceptance Policy",
            "",
            *[f"- {item}" for item in summary["result_acceptance_policy"]],
            "",
            "## Results",
            "",
            "| Job | Command | Reader PC | Status | Valid | Classification | Remaining blockers | Result path |",
            "| --- | --- | --- | --- | --- | --- | --- | --- |",
            *rows,
            "",
            "## Next Work",
            "",
            *[f"- {item}" for item in summary["next_work"]],
            "",
        ]
    )


def main() -> int:
    args = parse_args()
    summary = collect(load_json(Path(args.plan)))
    output = Path(args.output)
    notes = Path(args.notes)
    output.parent.mkdir(parents=True, exist_ok=True)
    notes.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    notes.write_text(render_markdown(summary), encoding="utf-8")
    print(
        "Collected audio non-0x00 control probe results: "
        f"{summary['summary']['result_count']} / {summary['summary']['job_count']} result files, "
        f"remaining blockers {summary['summary']['remaining_blocker_job_counts']}"
    )
    print(f"Wrote {output}")
    print(f"Wrote {notes}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
