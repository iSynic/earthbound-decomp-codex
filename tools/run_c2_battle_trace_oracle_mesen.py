#!/usr/bin/env python3
"""Run one C2 battle trace-oracle job with a local Mesen testRunner skeleton."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import build_c2_battle_trace_oracle_runner_assets
import rom_tools


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_HANDOFF = ROOT / "manifests" / "c2-battle-trace-oracle-emulator-handoff.json"
DEFAULT_PACKET = ROOT / "manifests" / "c2-battle-trace-oracle-packet.json"
DEFAULT_INDEX = ROOT / "build" / "c2" / "battle-trace-oracles" / "mesen-runner-assets" / "index.json"
DEFAULT_ASSET_ROOT = ROOT / "build" / "c2" / "battle-trace-oracles" / "mesen-runner-assets"
COMMON_MESEN_PATHS = [
    Path(os.environ.get("MESEN_EXE", "")) if os.environ.get("MESEN_EXE") else None,
    Path(os.environ.get("MESEN_PATH", "")) if os.environ.get("MESEN_PATH") else None,
    Path(r"F:\Mesen\Mesen.exe"),
    Path(r"C:\Mesen\Mesen.exe"),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a C2 battle trace-oracle Mesen skeleton.")
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--job-id", help="Packet job id.")
    target.add_argument("--oracle-id", help="Oracle id.")
    parser.add_argument("--runner-index", default=str(DEFAULT_INDEX), help="Ignored runner asset index JSON.")
    parser.add_argument("--packet", default=str(DEFAULT_PACKET), help="C2 battle trace-oracle packet JSON.")
    parser.add_argument("--mesen", help="Path to Mesen.exe. Defaults to MESEN_EXE/MESEN_PATH or common local paths.")
    parser.add_argument("--rom", help="Path to EarthBound (USA).sfc. Defaults to tools.rom_tools discovery.")
    parser.add_argument("--state", help="Optional local Mesen save-state path.")
    parser.add_argument("--frame-limit", type=int, default=3600, help="Frames before the generated Lua skeleton exits.")
    parser.add_argument("--timeout", type=int, default=180, help="Subprocess timeout in seconds.")
    parser.add_argument("--dry-run", action="store_true", help="Print and summarize the command without launching Mesen.")
    parser.add_argument(
        "--write-unresolved-result",
        action="store_true",
        help="After a successful run, replace the packet result with a non-proof unresolved Mesen result.",
    )
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def repo_path(path_text: str) -> Path:
    path = Path(path_text)
    return path if path.is_absolute() else ROOT / path


def manifest_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def ensure_runner_assets(index_path: Path) -> dict[str, Any]:
    if not index_path.exists():
        build_c2_battle_trace_oracle_runner_assets.build_assets(
            load_json(DEFAULT_HANDOFF),
            DEFAULT_ASSET_ROOT,
        )
    return load_json(index_path)


def find_runner_job(index: dict[str, Any], *, job_id: str | None, oracle_id: str | None) -> dict[str, Any]:
    for job in index.get("jobs", []):
        if job_id and job.get("job_id") == job_id:
            return job
        if oracle_id and job.get("oracle_id") == oracle_id:
            return job
    raise ValueError(f"could not find runner job for job_id={job_id!r} oracle_id={oracle_id!r}")


def resolve_mesen(explicit_path: str | None) -> Path:
    if explicit_path:
        path = Path(explicit_path)
        if not path.is_file():
            raise FileNotFoundError(f"Mesen executable not found: {path}")
        return path
    for candidate in COMMON_MESEN_PATHS:
        if candidate and candidate.is_file():
            return candidate
    found = shutil.which("Mesen.exe") or shutil.which("Mesen")
    if found:
        return Path(found)
    searched = "\n".join(f"- {path}" for path in COMMON_MESEN_PATHS if path)
    raise FileNotFoundError(f"Unable to find Mesen.exe. Searched:\n{searched}\nPass --mesen.")


def resolve_rom(explicit_path: str | None) -> Path:
    return rom_tools.find_rom(explicit_path)


def packet_job(packet: dict[str, Any], job_id: str) -> dict[str, Any]:
    for job in packet.get("jobs", []):
        if job.get("job_id") == job_id:
            return job
    raise ValueError(f"packet job not found: {job_id}")


def ensure_job_manifest(packet: dict[str, Any], runner_data: dict[str, Any]) -> Path:
    job = packet_job(packet, str(runner_data["job_id"]))
    packet_job_path = repo_path(str(job["output_paths"]["job_path"]))
    packet_job_path.parent.mkdir(parents=True, exist_ok=True)
    packet_job_path.write_text(json.dumps(job, indent=2) + "\n", encoding="utf-8")
    return packet_job_path


def parse_trace_addresses(trace_path: Path) -> list[str]:
    if not trace_path.exists():
        return []
    addresses: list[str] = []
    for line in trace_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if row.get("type") == "breakpoint_hit":
            pc = row.get("pc")
            if isinstance(pc, str) and pc not in addresses:
                addresses.append(pc)
    return addresses


def write_unresolved_result(runner_job: dict[str, Any], trace_path: Path, observed_addresses: list[str]) -> Path:
    runner_data = load_json(repo_path(str(runner_job["runner_job"])))
    paths = runner_data["output_paths"]
    result = {
        "schema": "earthbound-decomp.c2-battle-trace-oracle-result.v1",
        "job_id": runner_data["job_id"],
        "oracle_id": runner_data["oracle_id"],
        "status": "unresolved",
        "contract_classification": "unresolved",
        "observed_addresses": observed_addresses,
        "captured_fields": {},
        "promotion_allowed_by_result": False,
        "behavior_change_allowed": False,
        "evidence": {
            "trace_path": paths["raw_trace_path"],
            "classification_rationale": "Mesen raw trace captured but not reviewed into a proof-grade result.",
            "harness_name": "mesen2_test_runner_raw_trace",
            "harness_version": "c2-battle-trace-oracle-mesen-v1",
            "job_path": paths["job_path"],
        },
    }
    result_path = repo_path(str(paths["result_path"]))
    write_json(result_path, result)
    return result_path


def build_command(mesen: Path, lua: Path, rom: Path) -> list[str]:
    return [
        str(mesen),
        "--testRunner",
        "--enableStdout",
        "--doNotSaveSettings",
        "--debug.scriptWindow.allowIoOsAccess=true",
        str(lua),
        str(rom),
    ]


def main() -> int:
    args = parse_args()
    index = ensure_runner_assets(Path(args.runner_index))
    packet = load_json(Path(args.packet))
    runner_job = find_runner_job(index, job_id=args.job_id, oracle_id=args.oracle_id)
    runner_data = load_json(repo_path(str(runner_job["runner_job"])))
    mesen = resolve_mesen(args.mesen)
    rom = resolve_rom(args.rom)
    state = Path(args.state) if args.state else None
    if state is not None and not state.is_file():
        raise FileNotFoundError(f"save state not found: {state}")

    job_path = ensure_job_manifest(packet, runner_data)
    trace_path = repo_path(str(runner_job["target_raw_trace_path"]))
    trace_path.parent.mkdir(parents=True, exist_ok=True)
    lua_path = repo_path(str(runner_job["mesen_lua_skeleton"]))
    command = build_command(mesen, lua_path, rom)
    env = os.environ.copy()
    env["C2_ORACLE_TRACE_OUT"] = str(trace_path)
    env["C2_ORACLE_JOB_PATH"] = str(job_path)
    env["C2_ORACLE_FRAME_LIMIT"] = str(args.frame_limit)
    env["C2_ORACLE_RUNNER_VERSION"] = "c2-battle-trace-oracle-mesen-v1"
    if state is not None:
        env["C2_ORACLE_STATE_PATH"] = str(state)

    output_dir = repo_path(str(runner_data["output_paths"]["result_path"])).parent
    summary_path = output_dir / "mesen-run-summary.json"
    run_record: dict[str, Any] = {
        "schema": "earthbound-decomp.c2-battle-trace-oracle-mesen-run.v1",
        "status": "dry_run" if args.dry_run else "pending",
        "job_id": runner_data["job_id"],
        "oracle_id": runner_data["oracle_id"],
        "mesen_path": str(mesen),
        "rom_path": manifest_path(rom),
        "save_state_path_local_only": str(state) if state else None,
        "lua_skeleton": manifest_path(lua_path),
        "job_path": manifest_path(job_path),
        "raw_trace_path": manifest_path(trace_path),
        "frame_limit": args.frame_limit,
        "command": command,
        "observed_addresses": [],
        "raw_trace_exists": False,
        "raw_trace_nonempty": False,
        "write_unresolved_result": bool(args.write_unresolved_result),
        "result_path": runner_data["output_paths"]["result_path"],
        "source_promotion_allowed": False,
        "behavior_change_allowed": False,
    }
    if args.dry_run:
        write_json(summary_path, run_record)
        print("Dry-run C2 Mesen oracle command:")
        print(" ".join(command))
        print(f"Wrote {summary_path}")
        return 0

    result = subprocess.run(command, cwd=ROOT, env=env, text=True, capture_output=True, timeout=args.timeout, check=False)
    observed = parse_trace_addresses(trace_path)
    run_record.update(
        {
            "status": "completed" if result.returncode == 0 else "failed",
            "returncode": result.returncode,
            "stdout_tail": result.stdout[-4000:],
            "stderr_tail": result.stderr[-4000:],
            "observed_addresses": observed,
            "raw_trace_exists": trace_path.exists(),
            "raw_trace_nonempty": trace_path.exists() and trace_path.stat().st_size > 0,
        }
    )
    if args.write_unresolved_result and result.returncode == 0 and trace_path.exists() and trace_path.stat().st_size > 0:
        run_record["written_result_path"] = manifest_path(write_unresolved_result(runner_job, trace_path, observed))
    write_json(summary_path, run_record)
    print(f"C2 Mesen oracle run {run_record['status']}: {runner_data['oracle_id']}")
    print(f"Observed addresses: {observed}")
    print(f"Wrote {summary_path}")
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
