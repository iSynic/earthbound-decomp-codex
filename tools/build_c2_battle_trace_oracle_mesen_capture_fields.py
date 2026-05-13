#!/usr/bin/env python3
"""Build reviewed capture fields from a rich C2 Mesen oracle trace."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import rom_tools


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PACKET = ROOT / "manifests" / "c2-battle-trace-oracle-packet.json"
SUPPORTED_ORACLES = {"c2_8125_damage_abi_boundary"}
ROUTINE_LABELS = {
    "C2:8125": "C28125_ApplyDamageToSelectedTarget",
    "C2:7EAF": "C27EAF_RunHitResolutionAndStatusActionCluster",
    "C2:941D": "C2941D_CheckSelectedBattlerTimedSubstateBlocker",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build C2 Mesen trace capture fields.")
    parser.add_argument("--oracle-id", default="c2_8125_damage_abi_boundary")
    parser.add_argument("--packet", default=str(DEFAULT_PACKET))
    parser.add_argument("--trace", help="Raw trace JSONL path. Defaults to packet raw_trace_path.")
    parser.add_argument("--rom", help="EarthBound ROM path. Defaults to rom_tools discovery.")
    parser.add_argument("--output", help="Captured-fields JSON path. Defaults beside the trace.")
    parser.add_argument(
        "--classification",
        default="needs_followup",
        choices=["confirmed_contract", "refined_contract", "contradicted_plan", "needs_followup"],
    )
    parser.add_argument("--classification-evidence", help="Override generated classification evidence.")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def repo_path(path_text: str) -> Path:
    path = Path(path_text)
    return path if path.is_absolute() else ROOT / path


def sha1(path: Path) -> str:
    digest = hashlib.sha1()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def find_job(packet: dict[str, Any], oracle_id: str) -> dict[str, Any]:
    for job in packet.get("jobs", []):
        if job.get("oracle_id") == oracle_id:
            return job
    raise ValueError(f"could not find oracle {oracle_id!r}")


def read_trace(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        row = json.loads(line)
        if not isinstance(row, dict):
            raise ValueError(f"{path}:{line_no}: trace row must be object")
        rows.append(row)
    return rows


def first_row(rows: list[dict[str, Any]], *, event_type: str, pc: str | None = None) -> dict[str, Any] | None:
    for row in rows:
        if row.get("type") != event_type:
            continue
        if pc is not None and row.get("pc") != pc:
            continue
        return row
    return None


def first_after(rows: list[dict[str, Any]], start_index: int, *, event_type: str, pc: str | None = None) -> dict[str, Any] | None:
    for row in rows[start_index + 1 :]:
        if row.get("type") != event_type:
            continue
        if pc is not None and row.get("pc") != pc:
            continue
        return row
    return None


def row_index(rows: list[dict[str, Any]], target: dict[str, Any]) -> int:
    for index, row in enumerate(rows):
        if row is target:
            return index
    raise ValueError("target row not found")


def require_text(row: dict[str, Any], key: str) -> str:
    value = row.get(key)
    if value is None or value == "":
        raise ValueError(f"trace row missing {key}")
    return str(value)


def save_state_id(row: dict[str, Any] | None) -> str:
    if row is None:
        return "not_captured"
    path_text = str(row.get("statePath", ""))
    if not path_text:
        return "not_captured"
    path = Path(path_text)
    if path.is_file():
        return f"{path.name} sha256:{sha256(path)}"
    return path.name or path_text


def build_c2_8125_fields(job: dict[str, Any], rows: list[dict[str, Any]], *, rom: Path, trace: Path, classification: str, evidence: str | None) -> dict[str, Any]:
    runner_start = first_row(rows, event_type="runner_start")
    state_load = first_row(rows, event_type="before_state_load")
    hit = first_row(rows, event_type="breakpoint_hit", pc="C2:8125")
    if hit is None:
        raise ValueError("trace does not contain a C2:8125 breakpoint hit")
    hit_index = row_index(rows, hit)
    downstream = first_after(rows, hit_index, event_type="breakpoint_hit", pc="C2:7EAF")
    before_watch = first_after(rows, hit_index, event_type="watch_snapshot", pc="C2:8125")
    after_watch = first_after(rows, hit_index, event_type="watch_snapshot", pc="C2:7EAF")
    observed = sorted({str(row.get("pc")) for row in rows if row.get("type") == "breakpoint_hit" and row.get("pc")})
    target_row = str(hit.get("selectedTargetRowHex") or (before_watch or {}).get("valueHex") or "")
    downstream_row = str((downstream or {}).get("selectedTargetRowHex") or (after_watch or {}).get("valueHex") or target_row)
    if not target_row:
        raise ValueError("trace does not include selected target row data")
    generated_evidence = (
        "Mesen canonical trace hit C2:8125 with CPU register capture and the pointed-to $A972 target row; "
        "the first downstream C2:7EAF hit provides a follow-up row snapshot. Text pointer/collapse labels remain follow-up decode work."
    )
    fields = {
        "trace_id": f"{trace.as_posix()} sha256:{sha256(trace)}",
        "scenario_name": require_text(runner_start or {}, "scenarioName"),
        "rom_sha1": sha1(rom),
        "save_state_id": save_state_id(state_load),
        "frame_or_instruction_counter": f"frame:{hit.get('frame')} cycle:{hit.get('cpuCycleCount')}",
        "pc": "C2:8125",
        "routine_label": ROUTINE_LABELS["C2:8125"],
        "registers.a": require_text(hit, "cpuA"),
        "registers.x": require_text(hit, "cpuX"),
        "registers.y": require_text(hit, "cpuY"),
        "registers.db": require_text(hit, "cpuDB"),
        "registers.dp": require_text(hit, "cpuDP"),
        "direct_page_snapshot": require_text(hit, "directPageHex"),
        "wram_before": target_row,
        "wram_after": downstream_row,
        "ef_text_pointer": "not_captured_by_current_mesen_runner",
        "c1_text_call": "not_captured_by_current_mesen_runner",
        "classification": classification,
        "classification_evidence": evidence or generated_evidence,
        "amount_input": require_text(hit, "cpuA"),
        "damage_selector_x": require_text(hit, "cpuX"),
        "selected_target_row": f"{require_text(hit, 'selectedTargetPointer')} {target_row}",
        "caller_family": "damage ABI reached from numbered multi-enemy battle fixture; exact caller subfamily still needs call-stack/source join",
        "post_call_hp_roller_state": downstream_row,
        "collapse_candidate_state": "selected target row captured; collapse field decode pending",
        "result_text_pointer": "not_captured_by_current_mesen_runner",
        "observed_addresses": observed,
        "downstream_routine_label": ROUTINE_LABELS.get(str((downstream or {}).get("pc", "")), "not_observed"),
    }
    missing = set(job.get("capture_fields", [])) - set(fields)
    if missing:
        raise ValueError(f"missing capture fields: {sorted(missing)}")
    return fields


def main() -> int:
    args = parse_args()
    if args.oracle_id not in SUPPORTED_ORACLES:
        raise ValueError(f"{args.oracle_id} is not supported by this Mesen capture assembler yet")
    packet = load_json(Path(args.packet))
    job = find_job(packet, args.oracle_id)
    trace = repo_path(args.trace or str(job["output_paths"]["raw_trace_path"]))
    rom = rom_tools.find_rom(args.rom)
    rows = read_trace(trace)
    fields = build_c2_8125_fields(
        job,
        rows,
        rom=rom,
        trace=trace,
        classification=args.classification,
        evidence=args.classification_evidence,
    )
    output = repo_path(args.output) if args.output else trace.parent / "captured-fields.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(fields, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote C2 Mesen capture fields {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
