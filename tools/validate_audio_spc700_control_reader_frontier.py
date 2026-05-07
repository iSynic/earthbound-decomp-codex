#!/usr/bin/env python3
"""Validate the SPC700 control reader frontier."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MANIFEST = ROOT / "manifests" / "audio-spc700-control-reader-frontier.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate the SPC700 control reader frontier.")
    parser.add_argument("manifest", nargs="?", default=str(DEFAULT_MANIFEST))
    return parser.parse_args()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def validate(data: dict[str, Any]) -> None:
    require(data.get("schema") == "earthbound-decomp.audio-spc700-control-reader-frontier.v1", "unexpected schema")
    summary = data.get("summary", {})
    records = data.get("reader_pcs", [])
    require(summary.get("reader_pc_count") == len(records), "reader PC count mismatch")
    require(summary.get("reader_pc_count", 0) > 0, "expected reader PCs")
    labels = summary.get("source_backed_reader_labels", {})
    require(labels.get("0x0955") == "GetNextByte", "missing GetNextByte source label")
    require(labels.get("0x0957") == "SkipByte", "missing SkipByte source label")
    require(summary.get("exact_duration_promotion_allowed") is False, "reader frontier must not directly promote exact duration")
    counts: Counter[str] = Counter()
    total = 0
    for record in records:
        require(record.get("pc"), "reader record missing PC")
        require(record.get("inside_driver_block") is True, f"{record.get('pc')}: expected PC inside driver block")
        require(record.get("driver_offset"), f"{record.get('pc')}: missing driver offset")
        require(record.get("window_sha1"), f"{record.get('pc')}: missing hashed window")
        require("window_bytes" not in record, f"{record.get('pc')}: must not embed ROM payload bytes")
        require(record.get("command_counts"), f"{record.get('pc')}: missing command counts")
        if record.get("pc") == "0x0957":
            require(record.get("source_label") == "SkipByte", "0x0957 should be source-labeled SkipByte")
            require(record.get("source_role") == "source_backed_reader_helper", "0x0957 source role mismatch")
        total += int(record.get("total_control_reads", 0))
        counts.update({str(command): int(count) for command, count in record.get("command_counts", {}).items()})
    require(total == summary.get("control_read_count"), "control read count mismatch")
    require(dict(sorted(counts.items())) == summary.get("command_counts"), "command counts mismatch")
    require(data.get("findings"), "missing findings")
    require(data.get("next_work"), "missing next work")


def main() -> int:
    args = parse_args()
    data = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    validate(data)
    print(
        "Audio SPC700 control reader frontier validation OK: "
        f"{data['summary']['reader_pc_count']} PCs, "
        f"{data['summary']['control_read_count']} reads"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
