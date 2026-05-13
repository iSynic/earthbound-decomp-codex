#!/usr/bin/env python3
"""Build an execution packet for C2 battle trace-oracle jobs."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PLAN = ROOT / "manifests" / "c2-battle-trace-oracle-plan.json"
DEFAULT_OUTPUT = ROOT / "manifests" / "c2-battle-trace-oracle-packet.json"
DEFAULT_NOTES = ROOT / "notes" / "c2-battle-trace-oracle-packet.md"
OUTPUT_ROOT = "build/c2/battle-trace-oracles"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the C2 battle trace-oracle execution packet.")
    parser.add_argument("--plan", default=str(DEFAULT_PLAN), help="C2 battle trace-oracle plan JSON.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Packet JSON output.")
    parser.add_argument("--notes", default=str(DEFAULT_NOTES), help="Packet markdown output.")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def output_paths(oracle_id: str) -> dict[str, str]:
    root = f"{OUTPUT_ROOT}/{oracle_id}"
    return {
        "output_dir": root,
        "job_path": f"{root}/job.json",
        "raw_trace_path": f"{root}/raw-trace.jsonl",
        "result_path": f"{root}/result.json",
        "evidence_markdown_path": f"{root}/evidence.md",
    }


def packet_job(oracle: dict[str, Any], *, execution_order: int, first_trace: bool) -> dict[str, Any]:
    oracle_id = str(oracle["id"])
    paths = output_paths(oracle_id)
    return {
        "job_id": f"c2-battle-oracle-{oracle_id}",
        "oracle_id": oracle_id,
        "execution_order": execution_order,
        "priority": int(oracle["priority"]),
        "first_trace_pass": first_trace,
        "status": oracle["status"],
        "question": oracle["question"],
        "addresses": oracle.get("addresses", []),
        "capture_fields": oracle.get("capture_fields", []),
        "diary_entries": oracle.get("diary_entries", []),
        "evidence_notes": oracle.get("evidence_notes", []),
        "source_paths": oracle.get("source_paths", []),
        "acceptance_criteria": oracle.get("acceptance_criteria", []),
        "promotion_allowed_by_plan": False,
        "behavior_change_allowed": False,
        "output_paths": paths,
        "commands": {
            "dry_run_stub": (
                "python tools/run_c2_battle_trace_oracle_batch.py "
                f"--job-id c2-battle-oracle-{oracle_id} --mode dry-run-stub --force"
            ),
            "external_run": (
                "python tools/run_c2_battle_trace_oracle_batch.py "
                f"--job-id c2-battle-oracle-{oracle_id} --mode external "
                "--external <harness> --job {job} --result {result} --trace {raw_trace}"
            ),
            "validate_result": f"python tools/validate_c2_battle_trace_oracle_result.py {paths['result_path']}",
        },
    }


def build_packet(plan: dict[str, Any]) -> dict[str, Any]:
    first_trace_order = [str(oracle_id) for oracle_id in plan.get("first_trace_pass", [])]
    first_trace_ids = set(first_trace_order)
    oracle_by_id = {str(oracle.get("id")): oracle for oracle in plan.get("oracles", [])}
    ordered_first = [oracle_by_id[oracle_id] for oracle_id in first_trace_order if oracle_id in oracle_by_id]
    ordered_rest = sorted(
        [oracle for oracle in plan.get("oracles", []) if str(oracle.get("id")) not in first_trace_ids],
        key=lambda item: (int(item.get("priority", 99)), str(item.get("id", ""))),
    )
    oracles = ordered_first + ordered_rest
    jobs = [
        packet_job(oracle, execution_order=index + 1, first_trace=str(oracle["id"]) in first_trace_ids)
        for index, oracle in enumerate(oracles)
    ]
    priority_counts = Counter(str(job["priority"]) for job in jobs)
    return {
        "schema": "earthbound-decomp.c2-battle-trace-oracle-packet.v1",
        "status": "c2_battle_trace_oracle_packet_ready_external_harness_required",
        "source_plan": "manifests/c2-battle-trace-oracle-plan.json",
        "references": [
            "manifests/c2-battle-trace-oracle-plan.json",
            "notes/c2-battle-trace-oracle-plan.md",
            "notes/c2-battle-trace-oracle-index.md",
            "notes/c-port-feedback-intake.md",
            "notes/phase-2-semantic-closure-plan.md",
        ],
        "source_policy": {
            "requires_user_supplied_rom": True,
            "generated_probe_outputs_are_ignored": True,
            "generated_outputs_root": OUTPUT_ROOT,
            "source_edits_allowed_from_packet_alone": False,
            "ghidra_role": "hint-only; never source-facing proof",
        },
        "summary": {
            "job_count": len(jobs),
            "first_trace_job_count": sum(1 for job in jobs if job["first_trace_pass"]),
            "priority_counts": dict(sorted(priority_counts.items())),
            "promotion_allowed_by_packet": False,
            "behavior_change_allowed": False,
        },
        "runner_contract": {
            "stub_mode": "schema-only; no emulator execution or behavior proof",
            "external_mode": "future emulator/harness command that writes the same result schema",
            "allowed_result_statuses": ["ok", "failed", "unsupported", "unresolved"],
            "allowed_contract_classifications": [
                "confirmed_contract",
                "refined_contract",
                "contradicted_plan",
                "unreachable_from_source_state",
                "needs_followup",
                "unresolved",
            ],
            "required_result_fields": [
                "schema",
                "job_id",
                "oracle_id",
                "status",
                "contract_classification",
                "observed_addresses",
                "captured_fields",
                "promotion_allowed_by_result",
                "behavior_change_allowed",
                "evidence",
            ],
            "ok_result_proof_requirements": [
                "result status is ok and classification is resolved",
                "result is not emitted by the schema-only stub harness",
                "evidence job_path and trace_path match the packet output paths exactly",
                "trace_path exists under the ignored build/c2 output root and is non-empty",
                "captured_fields includes every packet job capture field, including trace_id, scenario_name, rom_sha1, pc, routine_label, classification, and classification_evidence",
                "observed_addresses is non-empty and every address belongs to the oracle address set",
                "promotion_allowed_by_result and behavior_change_allowed remain false",
            ],
        },
        "packet_policy": [
            "This packet is an operator checklist for local C2 battle runtime evidence; it does not run a real emulator by itself.",
            "Generated jobs, traces, results, and evidence markdown stay under ignored build/c2 paths.",
            "Dry-run stub output validates schema plumbing only and must not be treated as semantic proof.",
            "A result cannot promote source names or comments until local trace/source evidence is reviewed.",
            "A result cannot validate as ok unless the single-result validator can see non-stub provenance, a non-empty trace, typed observed addresses, and the full packet capture-field contract.",
        ],
        "jobs": jobs,
        "post_packet_validation_commands": [
            "python tools/build_c2_battle_trace_oracle_packet.py",
            "python tools/validate_c2_battle_trace_oracle_packet.py",
            "python tools/run_c2_battle_trace_oracle_batch.py --mode dry-run-stub --force",
            "python tools/validate_c2_battle_trace_oracle_batch_summary.py",
            "python tools/collect_c2_battle_trace_oracle_results.py",
            "python tools/validate_c2_battle_trace_oracle_results_summary.py",
        ],
    }


def render_markdown(packet: dict[str, Any]) -> str:
    summary = packet["summary"]
    rows = []
    for job in packet["jobs"]:
        rows.append(
            "| {order} | {priority} | `{oracle}` | `{first}` | `{addresses}` | `{result}` |".format(
                order=job["execution_order"],
                priority=job["priority"],
                oracle=job["oracle_id"],
                first=job["first_trace_pass"],
                addresses=", ".join(job["addresses"][:6]),
                result=job["output_paths"]["result_path"],
            )
        )
    return "\n".join(
        [
            "# C2 Battle Trace Oracle Packet",
            "",
            "Generated by `tools/build_c2_battle_trace_oracle_packet.py`.",
            "",
            "This packet turns the C2 battle oracle plan into concrete local job",
            "contracts. It is runner plumbing only: stub runs do not prove behavior,",
            "and external runs must write the same result schema before any source",
            "comment or name promotion.",
            "",
            "## Summary",
            "",
            f"- jobs: `{summary['job_count']}`",
            f"- first trace jobs: `{summary['first_trace_job_count']}`",
            f"- priority counts: `{summary['priority_counts']}`",
            f"- promotion allowed by packet: `{summary['promotion_allowed_by_packet']}`",
            f"- generated output root: `{packet['source_policy']['generated_outputs_root']}`",
            "",
            "## Jobs",
            "",
            "| Order | Priority | Oracle | First pass | Key addresses | Result path |",
            "| ---: | ---: | --- | --- | --- | --- |",
            *rows,
            "",
            "## Runner Commands",
            "",
            "```powershell",
            "python tools\\build_c2_battle_trace_oracle_packet.py",
            "python tools\\validate_c2_battle_trace_oracle_packet.py",
            "python tools\\run_c2_battle_trace_oracle_batch.py --mode dry-run-stub --force",
            "python tools\\validate_c2_battle_trace_oracle_batch_summary.py",
            "python tools\\collect_c2_battle_trace_oracle_results.py",
            "python tools\\validate_c2_battle_trace_oracle_results_summary.py",
            "```",
            "",
            "## Policy",
            "",
            *[f"- {item}" for item in packet["packet_policy"]],
            "",
        ]
    )


def main() -> int:
    args = parse_args()
    packet = build_packet(load_json(Path(args.plan)))
    output = Path(args.output)
    notes = Path(args.notes)
    output.parent.mkdir(parents=True, exist_ok=True)
    notes.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(packet, indent=2) + "\n", encoding="utf-8")
    notes.write_text(render_markdown(packet), encoding="utf-8")
    print(f"Wrote {output}")
    print(f"Wrote {notes}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
