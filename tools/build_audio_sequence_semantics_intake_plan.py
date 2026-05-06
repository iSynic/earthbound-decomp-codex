#!/usr/bin/env python3
"""Build a guarded intake plan for audio probe results into sequence semantics."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SEMANTICS = ROOT / "manifests" / "audio-sequence-command-semantics.json"
DEFAULT_ZERO_RESULTS = ROOT / "manifests" / "audio-zero-runtime-probe-results-summary.json"
DEFAULT_NONZERO_RESULTS = ROOT / "manifests" / "audio-nonzero-control-probe-results-summary.json"
DEFAULT_UNCERTAINTY = ROOT / "manifests" / "audio-duration-uncertainty-register.json"
DEFAULT_OUTPUT = ROOT / "manifests" / "audio-sequence-semantics-intake-plan.json"
DEFAULT_NOTES = ROOT / "notes" / "audio-sequence-semantics-intake-plan.md"

ZERO_ACCEPTED = {"true_end", "ef_return", "loop_or_hold_continues"}
NONZERO_ACCEPTED = {"ef_call_return", "timing_toggle", "earthbound_variant_ff", "unreachable"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build audio sequence semantics intake plan.")
    parser.add_argument("--semantics", default=str(DEFAULT_SEMANTICS), help="Current command semantics manifest.")
    parser.add_argument("--zero-results", default=str(DEFAULT_ZERO_RESULTS), help="0x00 probe results summary.")
    parser.add_argument("--nonzero-results", default=str(DEFAULT_NONZERO_RESULTS), help="Non-0x00 probe results summary.")
    parser.add_argument("--uncertainty", default=str(DEFAULT_UNCERTAINTY), help="Duration uncertainty register.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Intake plan output JSON.")
    parser.add_argument("--notes", default=str(DEFAULT_NOTES), help="Intake plan markdown output.")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def zero_intake_records(zero_results: dict[str, Any]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for result in zero_results.get("results", []):
        classification = str(result.get("zero_effect_classification"))
        valid = bool(result.get("valid"))
        accepted = valid and classification in ZERO_ACCEPTED and not bool(result.get("promotion_allowed"))
        records.append(
            {
                "source_result": result.get("result_path"),
                "job_id": result.get("job_id"),
                "command": "0x00",
                "track_id": int(result.get("track_id", 0)),
                "track_name": result.get("track_name"),
                "status": result.get("status"),
                "valid": valid,
                "classification": classification,
                "accepted_for_semantics_candidate": accepted,
                "candidate_semantic_evidence": (
                    f"earthbound_zero_{classification}" if accepted else "pending_valid_zero_runtime_effect"
                ),
                "remaining_blockers": result.get("remaining_blockers", []),
                "exact_duration_promotion_allowed_by_intake": False,
            }
        )
    return records


def nonzero_intake_records(nonzero_results: dict[str, Any]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for result in nonzero_results.get("results", []):
        command = str(result.get("command"))
        classification = str(result.get("control_effect_classification"))
        valid = bool(result.get("valid"))
        accepted = valid and classification in NONZERO_ACCEPTED and not bool(result.get("promotion_allowed"))
        records.append(
            {
                "source_result": result.get("result_path"),
                "job_id": result.get("job_id"),
                "command": command,
                "reader_pc": result.get("reader_pc"),
                "read_count": int(result.get("read_count", 0)),
                "affected_kind": result.get("affected_kind"),
                "status": result.get("status"),
                "valid": valid,
                "classification": classification,
                "accepted_for_semantics_candidate": accepted,
                "candidate_semantic_evidence": (
                    f"earthbound_nonzero_{command.lower()}_{classification}" if accepted else "pending_valid_control_effect"
                ),
                "remaining_blockers": result.get("remaining_blockers", []),
                "exact_duration_promotion_allowed_by_intake": False,
            }
        )
    return records


def command_intake_state(records: list[dict[str, Any]], semantics: dict[str, Any]) -> list[dict[str, Any]]:
    by_command: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        by_command.setdefault(str(record["command"]), []).append(record)

    states: list[dict[str, Any]] = []
    for command, current in semantics.get("commands", {}).items():
        command_records = by_command.get(str(command), [])
        accepted = [record for record in command_records if record["accepted_for_semantics_candidate"]]
        pending = [record for record in command_records if not record["accepted_for_semantics_candidate"]]
        states.append(
            {
                "command": command,
                "current_semantic_status": current.get("semantic_status"),
                "current_exact_duration_promotion_allowed": bool(current.get("exact_duration_promotion_allowed")),
                "intake_record_count": len(command_records),
                "accepted_candidate_count": len(accepted),
                "pending_or_rejected_count": len(pending),
                "accepted_candidate_evidence": [record["candidate_semantic_evidence"] for record in accepted],
                "intake_state": "candidate_evidence_ready" if accepted else "probe_results_pending",
                "next_action": (
                    "review candidate evidence before editing audio-sequence-command-semantics"
                    if accepted
                    else "run and collect the relevant runtime probe jobs"
                ),
                "exact_duration_promotion_allowed_by_intake": False,
            }
        )
    return states


def build_plan(
    semantics: dict[str, Any],
    zero_results: dict[str, Any],
    nonzero_results: dict[str, Any],
    uncertainty: dict[str, Any],
) -> dict[str, Any]:
    zero_records = zero_intake_records(zero_results)
    nonzero_records = nonzero_intake_records(nonzero_results)
    records = zero_records + nonzero_records
    command_counts: Counter[str] = Counter(str(record["command"]) for record in records)
    accepted_counts: Counter[str] = Counter(
        str(record["command"]) for record in records if record["accepted_for_semantics_candidate"]
    )
    status_counts: Counter[str] = Counter(str(record["status"]) for record in records)
    classification_counts: Counter[str] = Counter(str(record["classification"]) for record in records)
    return {
        "schema": "earthbound-decomp.audio-sequence-semantics-intake-plan.v1",
        "status": "probe_result_intake_pending",
        "references": [
            "manifests/audio-sequence-command-semantics.json",
            "manifests/audio-zero-runtime-probe-results-summary.json",
            "manifests/audio-nonzero-control-probe-results-summary.json",
            "manifests/audio-duration-uncertainty-register.json",
        ],
        "summary": {
            "current_confirmed_command_count": int(
                semantics.get("summary", {}).get("confirmed_for_exact_duration_count", 0)
            ),
            "intake_record_count": len(records),
            "zero_intake_record_count": len(zero_records),
            "nonzero_intake_record_count": len(nonzero_records),
            "accepted_candidate_count": sum(1 for record in records if record["accepted_for_semantics_candidate"]),
            "command_intake_record_counts": dict(sorted(command_counts.items())),
            "accepted_candidate_counts_by_command": dict(sorted(accepted_counts.items())),
            "status_counts": dict(sorted(status_counts.items())),
            "classification_counts": dict(sorted(classification_counts.items())),
            "sequence_promotion_allowed_by_intake": False,
            "duration_uncertainty_track_counts": uncertainty.get("summary", {}).get(
                "primary_uncertainty_track_counts",
                {},
            ),
        },
        "intake_policy": [
            "Probe results can create candidate sequence-command evidence only after their individual result validators pass.",
            "A zero result is candidate evidence only for true_end, ef_return, or loop_or_hold_continues classifications.",
            "A nonzero result is candidate evidence only for ef_call_return, timing_toggle, earthbound_variant_ff, or unreachable classifications that match the command family validator.",
            "This intake plan cannot directly promote public exact-duration exports or edit audio-sequence-command-semantics.",
            "Candidate evidence must still be reviewed in a later semantics-promotion pass and then re-run export triage.",
        ],
        "command_intake_state": command_intake_state(records, semantics),
        "intake_records": records,
        "next_work": [
            "run the 0x0957 FF/FE/EF nonzero jobs first, then re-collect nonzero control probe results",
            "run the highest-priority 0x00 finite/loop/active-preview jobs, then re-collect zero runtime probe results",
            "promote only validator-clean candidate evidence through a separate audio-sequence-command-semantics update",
        ],
    }


def render_markdown(data: dict[str, Any]) -> str:
    summary = data["summary"]
    state_rows = [
        "| `{command}` | `{current_semantic_status}` | {intake_record_count} | {accepted_candidate_count} | `{intake_state}` | {next_action} |".format(
            **state
        )
        for state in data["command_intake_state"]
    ]
    record_rows = [
        "| `{command}` | `{job_id}` | `{status}` | `{valid}` | `{classification}` | `{accepted}` | `{blockers}` |".format(
            command=record["command"],
            job_id=record["job_id"],
            status=record["status"],
            valid=record["valid"],
            classification=record["classification"],
            accepted=record["accepted_for_semantics_candidate"],
            blockers=record["remaining_blockers"],
        )
        for record in data["intake_records"]
    ][:40]
    return "\n".join(
        [
            "# Audio Sequence Semantics Intake Plan",
            "",
            "Status: probe results are mapped to candidate semantics evidence only; no export behavior changes.",
            "",
            "## Summary",
            "",
            f"- current confirmed commands: `{summary['current_confirmed_command_count']}`",
            f"- intake records: `{summary['intake_record_count']}`",
            f"- zero intake records: `{summary['zero_intake_record_count']}`",
            f"- nonzero intake records: `{summary['nonzero_intake_record_count']}`",
            f"- accepted candidates: `{summary['accepted_candidate_count']}`",
            f"- command record counts: `{summary['command_intake_record_counts']}`",
            f"- statuses: `{summary['status_counts']}`",
            f"- classifications: `{summary['classification_counts']}`",
            f"- sequence promotion allowed by intake: `{summary['sequence_promotion_allowed_by_intake']}`",
            "",
            "## Intake Policy",
            "",
            *[f"- {item}" for item in data["intake_policy"]],
            "",
            "## Command State",
            "",
            "| Command | Current semantic status | Records | Accepted | Intake state | Next action |",
            "| --- | --- | ---: | ---: | --- | --- |",
            *state_rows,
            "",
            "## Intake Records",
            "",
            "| Command | Job | Status | Valid | Classification | Accepted | Remaining blockers |",
            "| --- | --- | --- | --- | --- | --- | --- |",
            *record_rows,
            "",
            "## Next Work",
            "",
            *[f"- {item}" for item in data["next_work"]],
            "",
        ]
    )


def main() -> int:
    args = parse_args()
    data = build_plan(
        load_json(Path(args.semantics)),
        load_json(Path(args.zero_results)),
        load_json(Path(args.nonzero_results)),
        load_json(Path(args.uncertainty)),
    )
    output = Path(args.output)
    notes = Path(args.notes)
    output.parent.mkdir(parents=True, exist_ok=True)
    notes.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    notes.write_text(render_markdown(data), encoding="utf-8")
    print(
        "Built audio sequence semantics intake plan: "
        f"{data['summary']['intake_record_count']} records, "
        f"{data['summary']['accepted_candidate_count']} accepted candidates"
    )
    print(f"Wrote {output}")
    print(f"Wrote {notes}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
