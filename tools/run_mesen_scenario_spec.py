#!/usr/bin/env python3
"""Run or dry-run one ignored Mesen scenario spec through the C2 oracle runner."""

from __future__ import annotations

import argparse
import hashlib
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

import rom_tools


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_RUN_ROOT = ROOT / "build" / "mesen-scenarios" / "runs"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("spec", help="Ignored runnable scenario spec JSON.")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--mesen")
    parser.add_argument("--rom")
    parser.add_argument("--timeout", type=int, default=180)
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str | None:
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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


def link_or_copy(source: Path, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        dest.unlink()
    try:
        os.link(source, dest)
    except OSError:
        shutil.copy2(source, dest)


def prepare_srm_rom(spec: dict[str, Any], rom_arg: str | None) -> tuple[Path, dict[str, Any]]:
    source_rom = rom_tools.find_rom(rom_arg)
    run_dir = repo_path(str(spec["output_dir"])) / "srm-rom"
    rom_dest = run_dir / "earthbound-us.sfc"
    srm_dest = run_dir / "earthbound-us.srm"
    link_or_copy(source_rom, rom_dest)
    srm_path = repo_path(str(spec["start"]["working_srm_path_local_only"]))
    if not srm_path.is_file():
        raise FileNotFoundError(f"working SRM missing; rebuild catalog first: {srm_path}")
    shutil.copy2(srm_path, srm_dest)
    return rom_dest, {
        "srm_anchor_id": spec["start"].get("anchor_id"),
        "srm_archive_name": spec["start"].get("archive_name"),
        "srm_expected_sha256": spec["start"].get("srm_sha256"),
        "srm_copied_sha256": sha256(srm_dest),
        "srm_rom_path": manifest_path(rom_dest),
        "srm_copy_path": manifest_path(srm_dest),
        "bootstrap_status": spec.get("bootstrap_status", "not_declared"),
        "bootstrap_input_pattern": spec.get("bootstrap_input_pattern", "not_declared"),
        "bootstrap_frame_count": spec.get("bootstrap_frame_count", 0),
        "post_resume_snapshot_required": bool(spec.get("post_resume_snapshot_required")),
        "resume_proof_status": spec.get("resume_proof_status", "not_declared"),
        "post_resume_snapshot_seen": False,
        "srm_launch_caveat": (
            "This runner currently proves only ROM/SRM pairing and launch. "
            "A future bootstrap phase must record a post-resume snapshot before this becomes vanilla SRM-plus-input evidence."
        ),
    }


def build_runner_command(spec: dict[str, Any], *, dry_run: bool, mesen: str | None, rom: str | None, timeout: int) -> tuple[list[str], dict[str, Any]]:
    cmd = [
        sys.executable,
        str(ROOT / "tools" / "run_c2_battle_trace_oracle_mesen.py"),
        "--oracle-id",
        str(spec["oracle_id"]),
        "--input-pattern",
        str(spec["input_pattern"]),
        "--frame-limit",
        str(spec.get("frame_limit", 1200)),
        "--timeout",
        str(timeout),
        "--output-dir",
        str(repo_path(str(spec["output_dir"]))),
    ]
    if dry_run:
        cmd.append("--dry-run")
    if mesen:
        cmd.extend(["--mesen", mesen])
    start = spec["start"]
    run_metadata: dict[str, Any] = {}
    if start["type"] == "load_state":
        state = Path(start["state_path_local_only"])
        if not state.is_file():
            raise FileNotFoundError(f"save state missing: {state}")
        cmd.extend(["--state", str(state)])
        if rom:
            cmd.extend(["--rom", rom])
    elif start["type"] == "load_srm_anchor":
        rom_path, run_metadata = prepare_srm_rom(spec, rom)
        cmd.extend(["--rom", str(rom_path)])
    else:
        raise ValueError(f"unsupported scenario start type: {start['type']}")
    if not dry_run:
        cmd.append("--summarize-trace")
    return cmd, run_metadata


def main() -> int:
    args = parse_args()
    spec_path = Path(args.spec)
    spec = load_json(spec_path)
    cmd, run_metadata = build_runner_command(spec, dry_run=args.dry_run, mesen=args.mesen, rom=args.rom, timeout=args.timeout)
    summary_path = repo_path(str(spec["output_dir"])) / "scenario-run-summary.json"
    record: dict[str, Any] = {
        "schema": "earthbound-decomp.mesen-scenario-run.v1",
        "status": "dry_run" if args.dry_run else "pending",
        "scenario_id": spec["scenario_id"],
        "evidence_tier": spec["evidence_tier"],
        "oracle_id": spec["oracle_id"],
        "spec_path": manifest_path(spec_path),
        "output_dir": manifest_path(repo_path(str(spec["output_dir"]))),
        "command": cmd,
        "source_promotion_allowed": False,
        "scenario_run_metadata": run_metadata,
    }
    if args.dry_run:
        write_json(summary_path, record)
        print("Dry-run Mesen scenario command:")
        print(" ".join(cmd))
        print(f"Wrote {summary_path}")
        return 0
    result = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, timeout=args.timeout + 30, check=False)
    record.update(
        {
            "status": "completed" if result.returncode == 0 else "failed",
            "returncode": result.returncode,
            "stdout_tail": result.stdout[-4000:],
            "stderr_tail": result.stderr[-4000:],
        }
    )
    write_json(summary_path, record)
    print(f"Mesen scenario run {record['status']}: {spec['scenario_id']}")
    print(f"Wrote {summary_path}")
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
