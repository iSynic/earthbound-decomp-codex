#!/usr/bin/env python3
"""Probe local Mesen save states for C2 battle trace-oracle readiness."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT_ROOT = ROOT / "build" / "c2" / "battle-trace-oracles" / "save-state-probes"
DEFAULT_STATE_DIR = Path(r"F:\Mesen\SaveStates")
DEFAULT_ORACLE = "c1_c2_target_action_staging"
DEFAULT_PATTERN = "neutral:30,a:4,neutral:20,a:4,neutral:240"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Probe local Mesen save states for C2 oracle hits.")
    parser.add_argument("--oracle-id", default=DEFAULT_ORACLE)
    parser.add_argument("--state", action="append", help="Specific .mss save state. May repeat.")
    parser.add_argument("--state-dir", default=str(DEFAULT_STATE_DIR), help="Directory to scan for .mss save states.")
    parser.add_argument("--pattern", default=DEFAULT_PATTERN, help="C2_ORACLE_INPUT_PATTERN for each probe.")
    parser.add_argument("--frame-limit", type=int, default=420)
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--limit", type=int, help="Maximum number of candidate save states to probe.")
    parser.add_argument("--output-root", default=str(DEFAULT_OUTPUT_ROOT))
    parser.add_argument("--mesen", help="Path to Mesen.exe.")
    return parser.parse_args()


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def manifest_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def slug(path: Path) -> str:
    text = path.stem.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text or "save-state"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def candidate_states(args: argparse.Namespace) -> list[Path]:
    if args.state:
        states = [Path(item) for item in args.state]
    else:
        state_dir = Path(args.state_dir)
        states = sorted(state_dir.glob("*.mss")) if state_dir.exists() else []
    if args.limit is not None:
        states = states[: args.limit]
    return states


def run_probe(args: argparse.Namespace, state: Path, output_root: Path, index: int) -> dict[str, Any]:
    probe_id = f"{index:02d}-{slug(state)}"
    output_dir = output_root / args.oracle_id / probe_id
    command = [
        sys.executable,
        "tools/run_c2_battle_trace_oracle_mesen.py",
        "--oracle-id",
        args.oracle_id,
    ]
    if args.mesen:
        command.extend(["--mesen", args.mesen])
    command.extend(
        [
            "--state",
            str(state),
            "--input-pattern",
            args.pattern,
            "--frame-limit",
            str(args.frame_limit),
            "--timeout",
            str(args.timeout),
            "--summarize-trace",
            "--output-dir",
            str(output_dir),
        ]
    )
    record: dict[str, Any] = {
        "probe_id": probe_id,
        "oracle_id": args.oracle_id,
        "save_state_path_local_only": str(state),
        "output_dir": manifest_path(output_dir),
        "command": command,
        "status": "pending",
        "minimum_hits_satisfied": False,
        "observed_addresses": [],
        "raw_trace_summary_path": manifest_path(output_dir / "raw-trace-summary.json"),
        "mesen_run_summary_path": manifest_path(output_dir / "mesen-run-summary.json"),
        "raw_trace_path": manifest_path(output_dir / "raw-trace.jsonl"),
        "input_pattern": args.pattern,
        "frame_limit": args.frame_limit,
        "timeout": args.timeout,
        "source_promotion_allowed": False,
        "behavior_change_allowed": False,
    }
    if not state.is_file():
        record["status"] = "missing_state"
        record["error"] = f"save state not found: {state}"
        return record
    record["save_state_size"] = state.stat().st_size
    record["save_state_sha256"] = sha256(state)
    result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, timeout=args.timeout + 30, check=False)
    record["returncode"] = result.returncode
    record["stdout_tail"] = result.stdout[-2000:]
    record["stderr_tail"] = result.stderr[-2000:]
    record["status"] = "completed" if result.returncode == 0 else "failed"
    raw_summary_path = output_dir / "raw-trace-summary.json"
    run_summary_path = output_dir / "mesen-run-summary.json"
    if raw_summary_path.exists():
        raw_summary = load_json(raw_summary_path)
        record["minimum_hits_satisfied"] = bool(raw_summary.get("minimum_hits_satisfied"))
        record["observed_addresses"] = raw_summary.get("observed_addresses", [])
        record["missing_minimum_hits"] = raw_summary.get("missing_minimum_hits", [])
        record["configured_minimum_hits"] = raw_summary.get("configured_minimum_hits", [])
        record["event_counts"] = raw_summary.get("event_counts", {})
        record["breakpoint_hit_counts"] = raw_summary.get("breakpoint_hit_counts", {})
        record["raw_trace_exists"] = raw_summary.get("trace_exists")
        record["raw_trace_nonempty"] = raw_summary.get("trace_nonempty")
        record["line_count"] = raw_summary.get("line_count")
        record["invalid_line_count"] = raw_summary.get("invalid_line_count")
        record["first_frame"] = raw_summary.get("first_frame")
        record["last_frame"] = raw_summary.get("last_frame")
        record["runner_start"] = raw_summary.get("runner_start")
        record["runner_summary"] = raw_summary.get("runner_summary")
    if run_summary_path.exists():
        run_summary = load_json(run_summary_path)
        record["raw_trace_nonempty"] = run_summary.get("raw_trace_nonempty")
    return record


def build_summary(args: argparse.Namespace, records: list[dict[str, Any]], output_root: Path) -> dict[str, Any]:
    ready = [record for record in records if record.get("minimum_hits_satisfied")]
    return {
        "schema": "earthbound-decomp.c2-battle-trace-save-state-probes.v1",
        "status": "save_state_probes_completed",
        "oracle_id": args.oracle_id,
        "input_pattern": args.pattern,
        "frame_limit": args.frame_limit,
        "timeout": args.timeout,
        "output_root": manifest_path(output_root),
        "summary": {
            "candidate_count": len(records),
            "completed_count": sum(1 for record in records if record.get("status") == "completed"),
            "failed_count": sum(1 for record in records if record.get("status") == "failed"),
            "missing_state_count": sum(1 for record in records if record.get("status") == "missing_state"),
            "minimum_hit_candidate_count": len(ready),
            "ready_fixture_candidates": [record["probe_id"] for record in ready],
            "source_promotion_allowed": False,
            "behavior_change_allowed": False,
        },
        "records": records,
    }


def main() -> int:
    args = parse_args()
    states = candidate_states(args)
    output_root = Path(args.output_root)
    records = [run_probe(args, state, output_root, index + 1) for index, state in enumerate(states)]
    summary = build_summary(args, records, output_root)
    summary_path = output_root / args.oracle_id / "probe-summary.json"
    write_json(summary_path, summary)
    print(
        "C2 save-state probes: "
        f"{summary['summary']['candidate_count']} candidates, "
        f"{summary['summary']['minimum_hit_candidate_count']} with minimum hits"
    )
    print(f"Wrote {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
