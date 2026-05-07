#!/usr/bin/env python3
"""Validate the SPC700 driver dispatch frontier manifest."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MANIFEST = ROOT / "manifests" / "audio-spc700-driver-dispatch-frontier.json"
EXPECTED_COMMANDS = [f"0x{value:02X}" for value in range(0xE0, 0xFF)]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate the audio SPC700 driver dispatch frontier.")
    parser.add_argument("manifest", nargs="?", default=str(DEFAULT_MANIFEST))
    return parser.parse_args()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def validate(data: dict[str, Any]) -> None:
    require(data.get("schema") == "earthbound-decomp.audio-spc700-driver-dispatch-frontier.v1", "unexpected schema")
    driver = data.get("driver", {})
    summary = data.get("summary", {})
    high = data.get("high_command_dispatch_candidate", {})
    entries = high.get("entries", [])
    indirect = data.get("indirect_jump_candidates", [])

    require(driver.get("destination") == "0x0500", "driver block must load at $0500")
    require(int(driver.get("count", 0)) > 0, "driver block has no bytes")
    require(bool(driver.get("sha1")), "driver block missing sha1")
    require(summary.get("driver_base") == "0x0500", "unexpected driver base")
    require(summary.get("semantic_status") == "source_backed_vcmd_labels_known_ff_reader_effect_unconfirmed", "unexpected semantic status")

    require(high.get("status") == "source_backed_vcmd_jump_table_ingested", "unexpected high-command status")
    require(high.get("table_base") == "0x0BE3", "unexpected VCMD table base")
    require(high.get("arg_length_table_base") == "0x0C21", "unexpected VCMD arg-length table base")
    require(high.get("command_range") == "0xE0..0xFE", "unexpected VCMD command range")
    require(high.get("entry_count") == 31, "VCMD table must have 31 entries")
    require(summary.get("high_command_entry_count") == 31, "summary VCMD entry count mismatch")
    require(summary.get("high_command_table_base") == "0x0BE3", "summary VCMD table base mismatch")
    require(summary.get("arg_length_table_base") == "0x0C21", "summary arg-length table base mismatch")
    require(summary.get("get_next_byte") == "0x0955", "summary GetNextByte mismatch")
    require(summary.get("skip_byte") == "0x0957", "summary SkipByte mismatch")
    require(int(summary.get("ram_alias_count", 0)) > 0, "expected parsed RAM aliases")
    require(summary.get("unresolved_control_bytes") == ["0x00", "0xFF"], "unexpected unresolved control bytes")
    source_navigation = data.get("source_navigation", {})
    require(source_navigation.get("get_next_byte") == "0x0955", "source navigation GetNextByte mismatch")
    require(source_navigation.get("skip_byte") == "0x0957", "source navigation SkipByte mismatch")
    require(entries and len(entries) == 31, "VCMD entries missing")
    require([entry.get("command") for entry in entries] == EXPECTED_COMMANDS, "high-command entry range mismatch")
    require(entries[0].get("source_label") == "VCMD_Instrument", "unexpected E0 label")
    require(entries[0].get("source_role") == "source_backed_vcmd", "unexpected E0 source role")
    require(entries[0].get("source_target") == entries[0].get("target"), "unexpected E0 source target")
    require(entries[0].get("target") == "0x095F", "unexpected E0 target")
    require(entries[0].get("arg_length") == 1, "unexpected E0 arg length")
    require(entries[-1].get("command") == "0xFE", "last source-backed VCMD entry is not FE")
    require(entries[-1].get("source_label") == "VCMD_FastForwardOff", "unexpected FE label")
    require(entries[-1].get("target") == "0x0B7F", "unexpected FE target")
    require(all(entry.get("confidence") == "source_backed" for entry in entries), "entries must be source-backed")
    require(all(entry.get("target_profile", {}).get("inside_driver") for entry in entries), "entry target outside driver")

    require(indirect == [], "heuristic indirect candidates should be empty for source-backed frontier")


def main() -> int:
    args = parse_args()
    path = Path(args.manifest)
    data = json.loads(path.read_text(encoding="utf-8"))
    validate(data)
    print(
        "Audio SPC700 driver dispatch frontier validation OK: "
        f"{data['summary']['high_command_entry_count']} source-backed VCMD entries, "
        f"unresolved {data['summary']['unresolved_control_bytes']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
