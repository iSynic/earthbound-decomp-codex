#!/usr/bin/env python3
"""Validate the FD/FE fast-forward timing frontier."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MANIFEST = ROOT / "manifests" / "audio-fd-fe-timing-frontier.json"
REQUIRED_COMMANDS = {"0xFD", "0xFE"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate FD/FE fast-forward timing frontier.")
    parser.add_argument("manifest", nargs="?", default=str(DEFAULT_MANIFEST))
    return parser.parse_args()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def validate(data: dict[str, Any]) -> None:
    require(data.get("schema") == "earthbound-decomp.audio-fd-fe-timing-frontier.v1", "unexpected schema")
    require(data.get("status") == "fd_fe_source_backed_timing_effect_pending", "unexpected status")
    summary = data.get("summary", {})
    commands = data.get("commands", [])
    by_command = {record.get("command"): record for record in commands}
    require(set(by_command) == REQUIRED_COMMANDS, "command coverage mismatch")
    require(summary.get("command_count") == 2, "expected two commands")
    require(summary.get("source_backed_vcmd_count") == 2, "expected source-backed FD/FE commands")
    require(int(summary.get("runtime_read_count", 0)) > 0, "expected FD/FE runtime reads")
    require(int(summary.get("reader_pc_count", 0)) > 0, "expected reader PC links")
    require(summary.get("exact_duration_promotion_allowed") is False, "FD/FE must not promote exact duration")
    for command, record in by_command.items():
        require(record.get("source_role") == "source_backed_vcmd", f"{command}: expected source-backed role")
        require(str(record.get("source_label", "")).startswith("VCMD_FastForward"), f"{command}: unexpected source label")
        require(record.get("arg_length") == 0, f"{command}: FD/FE arg length must be zero")
        require(record.get("effect_proof_status") == "runtime_effect_pending", f"{command}: effect proof must remain pending")
        require(record.get("duration_promotion_status") == "blocked_pending_local_effect_proof", f"{command}: duration promotion should remain blocked")
        require(record.get("exact_duration_promotion_allowed") is False, f"{command}: promotion must be blocked")
        require(len(record.get("required_next_evidence", [])) >= 4, f"{command}: required evidence too thin")
    require(data.get("promotion_policy"), "missing promotion policy")
    require(data.get("next_work"), "missing next work")


def main() -> int:
    args = parse_args()
    data = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    validate(data)
    print(
        "Audio FD/FE timing frontier validation OK: "
        f"{data['summary']['runtime_read_count']} runtime reads"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
