#!/usr/bin/env python3
"""Validate source-backed SPC700 control-effect frontier."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MANIFEST = ROOT / "manifests" / "audio-spc700-source-effect-frontier.json"
REQUIRED_COMMANDS = {"0x00", "0xEF", "0xFD", "0xFE", "0xFF"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate SPC700 source-effect frontier.")
    parser.add_argument("manifest", nargs="?", default=str(DEFAULT_MANIFEST))
    return parser.parse_args()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def require_hex(text: Any, label: str) -> None:
    value = str(text)
    require(value.startswith("0x"), f"{label}: expected hex value")
    int(value[2:], 16)


def validate(data: dict[str, Any]) -> None:
    require(data.get("schema") == "earthbound-decomp.audio-spc700-source-effect-frontier.v1", "unexpected schema")
    require(data.get("status") == "source_effect_facts_ready_runtime_proof_pending", "unexpected status")
    require("refs/earthbound-sounddriver-byte-perfect/main.asm" in data.get("references", []), "missing main.asm reference")
    require("refs/earthbound-sounddriver-byte-perfect/ram.asm" in data.get("references", []), "missing ram.asm reference")
    effects = data.get("effects", {})
    summary = data.get("summary", {})
    require(set(effects) == REQUIRED_COMMANDS, "command coverage mismatch")
    require(summary.get("command_count") == len(effects), "command count mismatch")
    require(summary.get("source_backed_vcmd_count") == 3, "expected EF/FD/FE source-backed VCMDs")
    require(summary.get("zero_control_pending_count") == 1, "expected one zero-control command")
    require(summary.get("outside_vcmd_table_count") == 1, "expected one outside-VCMD command")
    require(summary.get("exact_duration_promotion_allowed") is False, "source effects must not promote exact duration")
    landmarks = data.get("source_landmarks", {})
    for key in (
        "get_next_byte",
        "voice_zero_reader",
        "pattern_zero_reader",
        "ef_subroutine_handler",
        "ef_target_loader",
        "fd_handler",
        "fe_handler",
        "fd_fe_post_write_helper",
        "music_effect_fastforward_tick",
        "music_effect_fastforward_start",
    ):
        require_hex(landmarks.get(key), f"landmark {key}")

    zero = effects["0x00"]
    require(zero.get("source_role") == "zero_control_pending", "0x00 role mismatch")
    require(zero.get("voice_reader", {}).get("zero_branches"), "0x00 missing voice branches")
    require(zero.get("pattern_reader", {}).get("zero_pair_branches"), "0x00 missing pattern branches")
    require(len(zero.get("voice_reader", {}).get("runtime_capture_requirements", [])) >= 4, "0x00 voice capture requirements too thin")
    require(len(zero.get("pattern_reader", {}).get("runtime_capture_requirements", [])) >= 3, "0x00 pattern capture requirements too thin")

    ef = effects["0xEF"]
    require(ef.get("source_label") == "VCMD_Subroutine", "EF source label mismatch")
    require(ef.get("arg_length") == 3, "EF arg length mismatch")
    require("ef_loop_counter" in ef.get("state_slots", {}), "EF missing loop counter state")
    require("ef_return_pointer" in ef.get("state_slots", {}), "EF missing return pointer state")

    for command, label in (("0xFD", "VCMD_FastForward"), ("0xFE", "VCMD_FastForwardOff")):
        effect = effects[command]
        require(effect.get("source_role") == "source_backed_vcmd", f"{command}: role mismatch")
        require(effect.get("source_label") == label, f"{command}: source label mismatch")
        require(effect.get("arg_length") == 0, f"{command}: arg length mismatch")
        state_slots = effect.get("state_slots", {})
        require(state_slots.get("fast_forward_flag", {}).get("name") == "fast_forward_flag", f"{command}: missing fast-forward flag")
        require(state_slots.get("music_effect_fastforward_timer", {}).get("name") == "mfx_fastforward_timer", f"{command}: missing MFX timer boundary")
        require(len(effect.get("runtime_capture_requirements", [])) >= 4, f"{command}: capture requirements too thin")

    ff = effects["0xFF"]
    require(ff.get("source_role") == "outside_vcmd_table", "FF must be outside VCMD table")
    require(ff.get("source_label") is None, "FF must not have a source label")
    require(ff.get("arg_length") is None, "FF must not have an arg length")
    require("outside" in str(ff.get("source_effect_status")), "FF source status must mention outside table")
    require(data.get("promotion_policy"), "missing promotion policy")
    require(data.get("next_work"), "missing next work")


def main() -> int:
    args = parse_args()
    data = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    validate(data)
    print(
        "Audio SPC700 source-effect frontier validation OK: "
        f"{data['summary']['command_count']} commands"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
