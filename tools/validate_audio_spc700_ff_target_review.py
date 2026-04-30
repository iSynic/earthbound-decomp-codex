#!/usr/bin/env python3
"""Validate the SPC700 FF target review manifest."""

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
    summary = data.get("summary", {})
    context = data.get("dispatch_context", {})
    review = data.get("target_review", {})
    span = review.get("span_profile", {})
    follow = review.get("first_512_byte_profile", {})

    require(summary.get("ff_target") == "0x1A81", "unexpected FF target")
    require(summary.get("next_pointer_run_target") == "0x1ACB", "unexpected next pointer-run target")
    require(summary.get("span_byte_count") == 74, "unexpected FF target span size")
    require(summary.get("word_reference_count") == 1, "unexpected FF word reference count")
    require(summary.get("direct_call_or_jump_reference_count") == 0, "FF target should not have direct CALL/JMP refs")
    require(summary.get("span_control_transfer_opcode_count") == 0, "span should not have byte-level control transfer markers")
    require(summary.get("first_512_control_transfer_opcode_count") == 0, "first 512 bytes should not have byte-level control transfer markers")
    require(summary.get("span_note_or_rest_like_count", 0) > summary.get("span_high_command_like_count", 0), "span should be data-like")
    require(context.get("table_base") == "0x16C7", "unexpected dispatch table base")
    require("0x12FD" in set(context.get("source_indirect_jump_addresses", [])), "missing dispatch source address")
    require(review.get("word_references") == ["0x1705"], "unexpected target word references")
    require(span.get("byte_count") == 74, "span profile byte count mismatch")
    require(follow.get("byte_count") == 512, "first-512 profile byte count mismatch")
    require(data.get("findings"), "missing findings")
    require(data.get("next_work"), "missing next work")


def main() -> int:
    args = parse_args()
    path = Path(args.manifest)
    data = json.loads(path.read_text(encoding="utf-8"))
    validate(data)
    print(
        "Audio SPC700 FF target review validation OK: "
        f"{data['summary']['ff_target']} span {data['summary']['span_byte_count']} bytes"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
