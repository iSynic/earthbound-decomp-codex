#!/usr/bin/env python3
"""Build the emulator handoff for first-pass C2 battle trace oracles."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PACKET = ROOT / "manifests" / "c2-battle-trace-oracle-packet.json"
DEFAULT_OUTPUT = ROOT / "manifests" / "c2-battle-trace-oracle-emulator-handoff.json"
DEFAULT_NOTES = ROOT / "notes" / "c2-battle-trace-oracle-emulator-handoff.md"

SCENARIOS: dict[str, dict[str, Any]] = {
    "c1_c2_target_action_staging": {
        "scenario_goal": "reach a battle command/menu selection that crosses C1 target staging and exports into C2 selection snapshots",
        "manual_setup": [
            "load or create a save state in an ordinary battle before selecting a command",
            "exercise one normal target prompt and one item/PSI target prompt if possible",
            "stop after C2:B930/BAC5 have captured/exported candidate rows",
        ],
        "preferred_trigger": "select a player action that opens target selection before the action resolves",
        "minimum_hits": ["C1:ADB4", "C1:CE85", "C1:CFC6", "C2:B930"],
    },
    "c2_40a4_current_action_payload": {
        "scenario_goal": "observe a selected action whose second-pointer/current-action payload is applied through C2:40A4",
        "manual_setup": [
            "load or create a save state in battle with a curative, item-status, or other second-pointer action available",
            "choose the action and allow it to enter the C2 payload application path",
            "capture the selected row pointer, action row id, payload pointer, and per-target loop state",
        ],
        "preferred_trigger": "use a curative or item-status action with a concrete selected target",
        "minimum_hits": ["C2:40A4"],
    },
    "c2_724a_affliction_writer_matrix": {
        "scenario_goal": "observe one parameterized C2:724A affliction write and distinguish it from nearby direct writers",
        "manual_setup": [
            "load or create a battle state with PSI Flash, asleep/paralysis/strange status, or a solidification item available",
            "prefer Flash paralysis or item solidification for the first capture because they have compact caller paths",
            "capture caller PC, X subgroup, Y value, selected row, gate result, and success/failure text pointers",
        ],
        "preferred_trigger": "execute a status action that reaches C2:724A",
        "minimum_hits": ["C2:724A", "C2:9917"],
    },
    "c2_8125_damage_abi_boundary": {
        "scenario_goal": "prove the selected-target damage ABI boundary without folding HP roller/collapse behavior into it",
        "manual_setup": [
            "load or create a battle state with a random-damage item, bomb, bottle rocket, or PSI common damage action",
            "execute the action and capture amount input, damage selector X, selected target row, and downstream text/collapse state",
            "prefer one low-noise item or PSI common path before broader damage family work",
        ],
        "preferred_trigger": "execute a damage action that calls C2:8125",
        "minimum_hits": ["C2:8125"],
    },
    "resource_amount_pair_magnet_vs_pp_loss": {
        "scenario_goal": "distinguish PSI Magnet PP transfer from PP reduction/loss-only paths",
        "manual_setup": [
            "load or create a battle state where PSI Magnet can target an enemy with PP",
            "capture source and target PP before/after the Magnet path",
            "run a separate PP reduction action and capture the same before/after fields for loss-only comparison",
        ],
        "preferred_trigger": "execute PSI Magnet, then a PP reduction action in a comparable battle state",
        "minimum_hits": ["C2:8E42", "C2:9F5E"],
    },
}

EXTRA_TRACE_FIELDS: dict[str, list[str]] = {
    "c1_c2_target_action_staging": [
        "D5:7B68 action row direction/target bytes",
        "$9FFA selection snapshot header",
        "$9FAC candidate row pointer",
    ],
    "c2_40a4_current_action_payload": [
        "$1E/$20 selected action pointer",
        "$06/$08 selected row pointer",
        "$00BC/$00BE payload pointer",
        "$A21C versus $9FAC target domain",
    ],
    "c2_724a_affliction_writer_matrix": [
        "row +0x0F host gate state",
        "row +0x1D+X affliction subgroup before/after",
        "$0E/$10 success or failure text pointer",
    ],
    "c2_8125_damage_abi_boundary": [
        "A amount input",
        "X damage/resistance selector",
        "$A972 selected target row pointer",
        "$02 normalized amount scratch",
        "HP/shield/collapse state before and after",
    ],
    "resource_amount_pair_magnet_vs_pp_loss": [
        "source and target PP +0x17/+0x19/+0x1B before/after",
        "random amount roll and cap amount",
        "$12/$14 text payload pointer",
        "transfer versus loss-only classification",
    ],
}

WATCH_RANGES: dict[str, list[dict[str, Any]]] = {
    "c1_c2_target_action_staging": [
        {"id": "selection_snapshot", "address_or_symbol": "$9FFA", "bytes": 64, "purpose": "C2 target/export snapshot"},
        {"id": "candidate_rows", "address_or_symbol": "$9FAC", "bytes": 96, "purpose": "candidate row and target byte state"},
    ],
    "c2_40a4_current_action_payload": [
        {"id": "payload_pointer_dp", "address_or_symbol": "$00BC", "bytes": 4, "purpose": "current action payload pointer"},
        {"id": "selected_target_row", "address_or_symbol": "$A972", "bytes": 64, "purpose": "selected battler row before/after"},
    ],
    "c2_724a_affliction_writer_matrix": [
        {"id": "selected_battler_afflictions", "address_or_symbol": "$A972 + row", "bytes": 64, "purpose": "affliction subgroup before/after"},
    ],
    "c2_8125_damage_abi_boundary": [
        {"id": "selected_target_row", "address_or_symbol": "$A972 + row", "bytes": 96, "purpose": "HP/shield/collapse before/after"},
    ],
    "resource_amount_pair_magnet_vs_pp_loss": [
        {"id": "source_target_pp_rows", "address_or_symbol": "source/target battler rows", "bytes": 96, "purpose": "PP transfer/loss before/after"},
    ],
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build C2 battle trace-oracle emulator handoff.")
    parser.add_argument("--packet", default=str(DEFAULT_PACKET), help="C2 battle trace-oracle packet JSON.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Handoff JSON output.")
    parser.add_argument("--notes", default=str(DEFAULT_NOTES), help="Handoff markdown output.")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def first_pass_jobs(packet: dict[str, Any]) -> list[dict[str, Any]]:
    return [job for job in packet.get("jobs", []) if job.get("first_trace_pass")]


def breakpoint_records(job: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "address": address,
            "address_space": "snes_cpu_bus",
            "hit_policy": "capture_registers_dp_wram_then_continue",
            "required_for_minimum_capture": address in set(SCENARIOS[job["oracle_id"]]["minimum_hits"]),
        }
        for address in job.get("addresses", [])
        if str(address).startswith(("C0:", "C1:", "C2:", "C3:", "C4:", "EF:"))
    ]


def handoff_job(job: dict[str, Any]) -> dict[str, Any]:
    oracle_id = str(job["oracle_id"])
    scenario = SCENARIOS[oracle_id]
    paths = job["output_paths"]
    return {
        "job_id": job["job_id"],
        "oracle_id": oracle_id,
        "priority": int(job["priority"]),
        "question": job["question"],
        "scenario_goal": scenario["scenario_goal"],
        "scenario": {
            "scenario_name": f"{oracle_id}_manual_first_pass",
            "save_state_id": "local_fixture_required",
            "save_state_path_local_only": "<local-only save state path>",
            "setup_steps": scenario["manual_setup"],
            "stop_condition": "minimum breakpoint hits plus required before/after snapshots written to raw-trace.jsonl",
        },
        "manual_setup": scenario["manual_setup"],
        "preferred_trigger": scenario["preferred_trigger"],
        "minimum_hits": scenario["minimum_hits"],
        "breakpoints": breakpoint_records(job),
        "watch_ranges": WATCH_RANGES.get(oracle_id, []),
        "extra_trace_fields": EXTRA_TRACE_FIELDS.get(oracle_id, []),
        "capture_fields": job.get("capture_fields", []),
        "acceptance_criteria": job.get("acceptance_criteria", []),
        "output_paths": {
            "job_path": paths["job_path"],
            "raw_trace_path": paths["raw_trace_path"],
            "result_path": paths["result_path"],
            "evidence_markdown_path": paths["evidence_markdown_path"],
        },
        "result_validator": f"python tools/validate_c2_battle_trace_oracle_result.py {paths['result_path']}",
        "result_collector": "python tools/collect_c2_battle_trace_oracle_results.py",
        "proof_gate": {
            "result_schema": "earthbound-decomp.c2-battle-trace-oracle-result.v1",
            "required_status": "ok",
            "required_capture_coverage": "every packet job capture field",
            "stub_results_are_proof": False,
            "source_promotion_allowed": False,
            "behavior_change_allowed": False,
        },
    }


def build_handoff(packet: dict[str, Any]) -> dict[str, Any]:
    jobs = [handoff_job(job) for job in first_pass_jobs(packet)]
    return {
        "schema": "earthbound-decomp.c2-battle-trace-oracle-emulator-handoff.v1",
        "status": "c2_battle_trace_oracle_emulator_handoff_ready_runner_pending",
        "packet": "manifests/c2-battle-trace-oracle-packet.json",
        "references": [
            "notes/c2-battle-trace-oracle-plan.md",
            "notes/c2-battle-trace-oracle-packet.md",
            "notes/c2-battle-trace-oracle-results-summary.md",
            "notes/overworld_stutter_mesen_test_results_2026-04-30.md",
        ],
        "emulator_policy": {
            "accepted_runner_classes": ["mesen2_test_runner", "ares_external_harness", "other_external_snes_trace_harness"],
            "mesen_address_policy": (
                "Set breakpoints/watchpoints on SNES CPU bus addresses. If a runner patches ROM, use Mesen's "
                "emu.convertAddress result in the snesPrgRom domain; do not write CPU ROM addresses directly in snesMemory."
            ),
            "required_rom_role": "user-supplied EarthBound US ROM; ROM bytes are not committed",
            "save_state_policy": "save states are local fixtures under ignored build/ or emulator folders",
            "output_root": packet.get("source_policy", {}).get("generated_outputs_root"),
        },
        "proof_policy": {
            "stub_results_are_not_proof": True,
            "ok_result_must_pass": "tools/validate_c2_battle_trace_oracle_result.py",
            "collector_must_report_proof_grade": "tools/collect_c2_battle_trace_oracle_results.py",
            "source_edits_allowed_from_handoff_alone": False,
            "behavior_change_allowed_from_handoff_alone": False,
        },
        "summary": {
            "handoff_job_count": len(jobs),
            "minimum_breakpoint_count": sum(len(job["minimum_hits"]) for job in jobs),
            "breakpoint_count": sum(len(job["breakpoints"]) for job in jobs),
            "source_promotion_allowed": False,
            "behavior_change_allowed": False,
        },
        "jobs": jobs,
        "runner_result_contract": {
            "write_result_schema": "earthbound-decomp.c2-battle-trace-oracle-result.v1",
            "required_status_for_proof": "ok",
            "required_capture_coverage": "every capture field listed on the job",
            "trace_format": "jsonl; one event per breakpoint/watchpoint hit or explicit before/after capture",
            "trace_minimum": "non-empty raw trace at output_paths.raw_trace_path",
        },
        "validation_commands": [
            "python tools/validate_c2_battle_trace_oracle_emulator_handoff.py",
            "python tools/build_c2_battle_trace_oracle_runner_assets.py",
            "python tools/validate_c2_battle_trace_oracle_runner_assets.py",
            "python tools/run_c2_battle_trace_oracle_batch.py --mode dry-run-stub --force",
            "python tools/collect_c2_battle_trace_oracle_results.py",
            "python tools/validate_c2_battle_trace_oracle_results_summary.py",
        ],
    }


def render_markdown(handoff: dict[str, Any]) -> str:
    rows = [
        "| {priority} | `{oracle}` | `{minimum}` | `{capture_count}` | `{result}` |".format(
            priority=job["priority"],
            oracle=job["oracle_id"],
            minimum=", ".join(job["minimum_hits"]),
            capture_count=len(job["capture_fields"]),
            result=job["output_paths"]["result_path"],
        )
        for job in handoff["jobs"]
    ]
    return "\n".join(
        [
            "# C2 Battle Trace Oracle Emulator Handoff",
            "",
            "Generated by `tools/build_c2_battle_trace_oracle_emulator_handoff.py`.",
            "",
            "This handoff turns the five first-pass C2 oracle jobs into a concrete",
            "external-emulator runner checklist. It does not run Mesen or any other",
            "emulator, and it does not prove behavior by itself.",
            "",
            "## Summary",
            "",
            f"- handoff jobs: `{handoff['summary']['handoff_job_count']}`",
            f"- breakpoints: `{handoff['summary']['breakpoint_count']}`",
            f"- source promotion allowed: `{handoff['summary']['source_promotion_allowed']}`",
            f"- behavior change allowed: `{handoff['summary']['behavior_change_allowed']}`",
            "",
            "## Runner Policy",
            "",
            f"- accepted runner classes: `{handoff['emulator_policy']['accepted_runner_classes']}`",
            f"- output root: `{handoff['emulator_policy']['output_root']}`",
            f"- Mesen address policy: {handoff['emulator_policy']['mesen_address_policy']}",
            "- Stub results are not proof; a real result must pass",
            "  `tools/validate_c2_battle_trace_oracle_result.py` and then the",
            "  results collector before any source-facing semantic promotion.",
            "- Ignored Mesen runner assets can be generated with",
            "  `tools/build_c2_battle_trace_oracle_runner_assets.py`; they provide",
            "  Lua skeletons and command snippets only, not proof-grade results.",
            "",
            "## First-Pass Jobs",
            "",
            "| Priority | Oracle | Minimum hits | Capture fields | Result path |",
            "| ---: | --- | --- | ---: | --- |",
            *rows,
            "",
            "## Job Details",
            "",
        ]
    ) + "\n" + "\n".join(render_job_detail(job) for job in handoff["jobs"])


def render_job_detail(job: dict[str, Any]) -> str:
    return "\n".join(
        [
            f"### `{job['oracle_id']}`",
            "",
            f"- goal: {job['scenario_goal']}",
            f"- preferred trigger: {job['preferred_trigger']}",
            f"- scenario name: `{job['scenario']['scenario_name']}`",
            f"- save state: `{job['scenario']['save_state_path_local_only']}`",
            f"- stop condition: {job['scenario']['stop_condition']}",
            f"- minimum hits: `{job['minimum_hits']}`",
            f"- watch ranges: `{[item['id'] for item in job['watch_ranges']]}`",
            f"- extra trace fields: `{job['extra_trace_fields']}`",
            f"- raw trace: `{job['output_paths']['raw_trace_path']}`",
            f"- result: `{job['output_paths']['result_path']}`",
            "- manual setup:",
            *[f"  - {item}" for item in job["manual_setup"]],
            "",
        ]
    )


def main() -> int:
    args = parse_args()
    handoff = build_handoff(load_json(Path(args.packet)))
    output = Path(args.output)
    notes = Path(args.notes)
    output.parent.mkdir(parents=True, exist_ok=True)
    notes.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(handoff, indent=2) + "\n", encoding="utf-8")
    notes.write_text(render_markdown(handoff), encoding="utf-8")
    print(f"Wrote {output}")
    print(f"Wrote {notes}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
