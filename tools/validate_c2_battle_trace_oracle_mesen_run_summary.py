#!/usr/bin/env python3
"""Validate a local ignored C2 battle trace-oracle Mesen run summary."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SUMMARY_ROOT = ROOT / "build" / "c2" / "battle-trace-oracles"
ALLOWED_STATUS = {"dry_run", "completed", "failed"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate C2 Mesen oracle run summary.")
    parser.add_argument("summary", help="Ignored mesen-run-summary.json path.")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def repo_path(path_text: str) -> Path:
    path = Path(path_text)
    return path if path.is_absolute() else ROOT / path


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def validate(data: dict[str, Any], summary_path: Path) -> None:
    require(data.get("schema") == "earthbound-decomp.c2-battle-trace-oracle-mesen-run.v1", "bad schema")
    require(data.get("status") in ALLOWED_STATUS, f"bad status {data.get('status')}")
    require(str(data.get("job_id", "")).startswith("c2-battle-oracle-"), "bad job id")
    require(data.get("oracle_id"), "missing oracle id")
    require(data.get("mesen_path"), "missing Mesen path")
    require(data.get("rom_path"), "missing ROM path")
    require(data.get("lua_skeleton"), "missing Lua skeleton")
    require(data.get("job_path"), "missing job path")
    require(data.get("raw_trace_path"), "missing raw trace path")
    if data.get("probe_output_dir") is not None:
        require(isinstance(data.get("probe_output_dir"), str) and data.get("probe_output_dir"), "probe_output_dir must be a string")
    require(isinstance(data.get("command"), list) and data.get("command"), "missing command vector")
    if data.get("input_pattern") is not None:
        require(isinstance(data.get("input_pattern"), str) and data.get("input_pattern"), "input_pattern must be a non-empty string")
    require(data.get("source_promotion_allowed") is False, "summary cannot allow source promotion")
    require(data.get("behavior_change_allowed") is False, "summary cannot allow behavior changes")
    require(str(summary_path.resolve()).startswith(str(DEFAULT_SUMMARY_ROOT.resolve())), "summary must stay under ignored C2 build output")
    require(str(repo_path(str(data["lua_skeleton"]))).endswith("mesen-runner-skeleton.lua"), "unexpected Lua skeleton path")
    if data.get("status") == "completed":
        require(data.get("returncode") == 0, "completed run must have returncode 0")
        require(data.get("raw_trace_exists") is True, "completed run must produce raw trace")
        require(data.get("raw_trace_nonempty") is True, "completed run must produce non-empty raw trace")
    if data.get("status") == "dry_run":
        require(data.get("raw_trace_exists") is False, "dry run should not claim raw trace")
        require(data.get("raw_trace_nonempty") is False, "dry run should not claim non-empty raw trace")
    if data.get("observed_addresses"):
        require(isinstance(data["observed_addresses"], list), "observed addresses must be a list")
        for address in data["observed_addresses"]:
            require(isinstance(address, str) and ":" in address, f"bad observed address {address!r}")


def main() -> int:
    args = parse_args()
    path = Path(args.summary)
    data = load_json(path)
    validate(data, path)
    print(f"C2 Mesen oracle run summary validation OK: {data['oracle_id']} {data['status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
