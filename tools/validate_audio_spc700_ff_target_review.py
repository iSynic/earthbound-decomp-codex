#!/usr/bin/env python3
"""Validate the SPC700 FF outside-VCMD proof lane."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MANIFEST = ROOT / "manifests" / "audio-spc700-ff-target-review.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate the audio SPC700 FF target review.")
    parser.add_argument("manifest", nargs="?", default=str(DEFAULT_MANIFEST))
    return parser.parse_args()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def validate(data: dict[str, Any]) -> None:
    require(data.get("schema") == "earthbound-decomp.audio-spc700-ff-target-review.v1", "unexpected schema")
    require(data.get("status") == "ff_outside_source_backed_vcmd_table_reader_effect_pending", "unexpected status")
    summary = data.get("summary", {})
    context = data.get("dispatch_context", {})
    review = data.get("ff_review", {})

    require(summary.get("ff_in_source_backed_vcmd_table") is False, "FF must not be source-backed")
    require(summary.get("source_backed_command_range") == "0xE0..0xFE", "unexpected VCMD range")
    require(summary.get("source_backed_entry_count") == 31, "expected 31 source-backed VCMD entries")
    require(int(summary.get("ff_reader_pc_count", 0)) > 0, "expected FF reader PC evidence")
    require(int(summary.get("ff_runtime_read_count", 0)) > 0, "expected FF runtime read evidence")
    require(summary.get("exact_duration_promotion_allowed") is False, "FF must not promote exact duration")
    require(summary.get("semantic_status") == "outside_vcmd_table_reader_effect_pending", "unexpected semantic status")

    require(context.get("source_backed_table_base") == "0x0BE3", "unexpected source-backed table base")
    require(context.get("source_backed_arg_length_table_base") == "0x0C21", "unexpected arg-length table base")
    require(context.get("source_role") == "outside_vcmd_table", "unexpected source role")
    require(review.get("command") == "0xFF", "review command mismatch")
    require(review.get("source_label") is None, "FF must not have source label")
    require(review.get("source_target") is None, "FF must not have source target")
    require(review.get("arg_length") is None, "FF must not have arg length")
    require(review.get("source_role") == "outside_vcmd_table", "FF source role mismatch")
    require(review.get("effect_proof_status") == "outside_vcmd_table_reader_effect_pending", "FF effect status mismatch")
    require(review.get("duration_promotion_status") == "blocked_pending_local_effect_proof", "FF promotion status mismatch")
    require(len(review.get("required_next_evidence", [])) >= 4, "FF required evidence too thin")
    for record in review.get("reader_pc_records", []):
        require(record.get("pc"), "reader record missing PC")
        require(int(record.get("read_count", 0)) > 0, f"reader {record.get('pc')}: missing read count")
    require(data.get("findings"), "missing findings")
    require(data.get("next_work"), "missing next work")


def main() -> int:
    args = parse_args()
    data = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    validate(data)
    print(
        "Audio SPC700 FF target review validation OK: "
        f"{data['summary']['ff_runtime_read_count']} FF reader reads, outside VCMD table"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
