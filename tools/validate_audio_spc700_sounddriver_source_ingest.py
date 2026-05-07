#!/usr/bin/env python3
"""Validate the checked-in SPC700 sound-driver source ingest manifest."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MANIFEST = ROOT / "manifests" / "audio-spc700-sounddriver-source-ingest.json"
REQUIRED_FILES = {
    "refs/earthbound-sounddriver-byte-perfect/main.asm",
    "refs/earthbound-sounddriver-byte-perfect/ram.asm",
    "refs/earthbound-sounddriver-byte-perfect/macros.asm",
    "refs/earthbound-sounddriver-byte-perfect/sfx_sequences.asm",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate SPC700 sound-driver source ingest manifest.")
    parser.add_argument("manifest", nargs="?", default=str(DEFAULT_MANIFEST))
    return parser.parse_args()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def validate(data: dict[str, Any]) -> None:
    require(data.get("schema") == "earthbound-decomp.audio-spc700-sounddriver-source-ingest.v1", "unexpected schema")
    files = data.get("files", [])
    by_path = {record.get("path"): record for record in files}
    require(set(by_path) == REQUIRED_FILES, "source file coverage mismatch")
    for path, record in by_path.items():
        full_path = ROOT / path
        require(full_path.exists(), f"{path}: missing checked-in source file")
        require(int(record.get("size", -1)) == full_path.stat().st_size, f"{path}: size mismatch")
        require(record.get("sha256"), f"{path}: missing sha256")
        require(record.get("role"), f"{path}: missing role")
    nav = data.get("source_navigation", {})
    require(nav.get("vcmd_table") == "0x0BE3", "unexpected VCMD table")
    require(nav.get("vcmd_arg_length_table") == "0x0C21", "unexpected arg-length table")
    require(nav.get("get_next_byte") == "0x0955", "unexpected GetNextByte address")
    require(nav.get("skip_byte") == "0x0957", "unexpected SkipByte address")
    require(nav.get("vcmd_command_range") == "0xE0..0xFE", "unexpected VCMD command range")
    require(nav.get("vcmd_entry_count") == 31, "unexpected VCMD entry count")
    require(int(nav.get("ram_alias_count", 0)) > 0, "expected RAM aliases")
    fact_topics = {fact.get("topic") for fact in data.get("source_backed_facts", [])}
    for topic in ("driver_base", "control_reader_labels", "vcmd_dispatch", "vcmd_arg_lengths", "refuted_static_guess"):
        require(topic in fact_topics, f"missing fact {topic}")
    require(data.get("related_notes"), "missing related notes")


def main() -> int:
    args = parse_args()
    data = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    validate(data)
    print(
        "Audio SPC700 sound-driver source ingest validation OK: "
        f"{len(data['files'])} files, {data['source_navigation']['vcmd_entry_count']} VCMD entries"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
