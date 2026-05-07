#!/usr/bin/env python3
"""Build source-backed SPC700 control-effect facts for duration proof lanes."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from audio_spc700_source import DEFAULT_MAIN, DEFAULT_RAM, hex_byte, hex_word, parse_ram_aliases, parse_source_labels, parse_vcmd_entries


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT = ROOT / "manifests" / "audio-spc700-source-effect-frontier.json"
DEFAULT_NOTES = ROOT / "notes" / "audio-spc700-source-effect-frontier.md"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build SPC700 source-effect frontier.")
    parser.add_argument("--main", default=str(DEFAULT_MAIN), help="SPC700 main.asm source.")
    parser.add_argument("--ram", default=str(DEFAULT_RAM), help="SPC700 ram.asm source.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Manifest output JSON.")
    parser.add_argument("--notes", default=str(DEFAULT_NOTES), help="Markdown note output.")
    return parser.parse_args()


def label(labels: dict[str, Any], name: str) -> str:
    if name not in labels:
        raise ValueError(f"required source label {name} was not found")
    return hex_word(labels[name].address)


def ram(aliases: dict[str, Any], name: str) -> dict[str, Any]:
    if name not in aliases:
        raise ValueError(f"required RAM alias {name} was not found")
    alias = aliases[name]
    return {
        "name": alias.name,
        "address": hex_word(alias.address),
        "comment": alias.comment,
    }


def source_span(labels: dict[str, Any], start: str, end: str) -> dict[str, str]:
    return {
        "start_label": start,
        "start_address": label(labels, start),
        "end_label": end,
        "end_address": label(labels, end),
    }


def vcmd_record(entries: dict[str, Any], command: str) -> dict[str, Any]:
    if command not in entries:
        raise ValueError(f"missing source-backed VCMD entry for {command}")
    entry = entries[command]
    return {
        "command": command,
        "source_label": entry.source_label,
        "source_target": hex_word(entry.source_target),
        "arg_length": entry.arg_length,
        "source_role": entry.source_role,
    }


def build_frontier(main_path: Path, ram_path: Path) -> dict[str, Any]:
    labels = parse_source_labels(main_path)
    aliases = parse_ram_aliases(ram_path)
    entries = {hex_byte(entry.command): entry for entry in parse_vcmd_entries(main_path)}
    voice_pointer = {
        "low": {"address": "0x0030", "expression": "$30+x"},
        "high": {"address": "0x0031", "expression": "$31+x"},
    }
    ef_target = {
        "low": {"address": "0x0240", "expression": "$0240+x"},
        "high": {"address": "0x0241", "expression": "$0241+x"},
    }
    ef_return = {
        "low": {"address": "0x0230", "expression": "$0230+x"},
        "high": {"address": "0x0231", "expression": "$0231+x"},
    }
    loop_counter = {"address": "0x0080", "expression": "$80+x"}

    effects = {
        "0x00": {
            "command": "0x00",
            "source_role": "zero_control_pending",
            "source_effect_status": "source_backed_zero_reader_paths_effect_pending_runtime_context",
            "voice_reader": {
                "source_span": source_span(labels, "L_0882", "L_089C"),
                "reader_label": "L_0882",
                "reader_address": label(labels, "L_0882"),
                "entry_action": "GetNextByte reads the next voice-stream byte; zero falls into loop/return/end routing.",
                "zero_branches": [
                    {
                        "condition": "$80+x == 0",
                        "target_label": "L_081A",
                        "target_address": label(labels, "L_081A"),
                        "effect": "no active EF repeat count remains; advance to the pattern pointer reader instead of treating voice-byte 0x00 as a standalone finite end",
                    },
                    {
                        "condition": "$80+x != 0",
                        "target_label": "L_0AC4",
                        "target_address": label(labels, "L_0AC4"),
                        "effect": "reload the EF subroutine target into the voice pointer, decrement $80+x, and either loop or restore the saved return pointer",
                    },
                    {
                        "condition": "decremented $80+x == 0",
                        "target_label": "L_0892",
                        "target_address": label(labels, "L_0892"),
                        "effect": "copy $0230+x/$0231+x back into $30+x/$31+x before continuing the reader loop",
                    },
                ],
                "state_slots": {
                    "ef_loop_counter": loop_counter,
                    "voice_pointer": voice_pointer,
                    "ef_return_pointer": ef_return,
                    "ef_subroutine_target": ef_target,
                },
                "runtime_capture_requirements": [
                    "$80+x before and after the zero read",
                    "$30+x/$31+x before the zero read and after the post-zero branch",
                    "$0230+x/$0231+x and $0240+x/$0241+x for active EF context",
                    "whether post-zero execution branches to L_081A, L_0AC4, L_0882, or restored-return flow",
                ],
            },
            "pattern_reader": {
                "source_span": source_span(labels, "L_081A", "L_083F"),
                "reader_label": "L_081A",
                "reader_address": label(labels, "L_081A"),
                "zero_pair_branches": [
                    {
                        "pattern_byte": "0x00",
                        "target_label": "StopMusic",
                        "target_address": label(labels, "StopMusic"),
                        "effect": "pattern-level 0x00 0x00 reaches StopMusic",
                    },
                    {
                        "pattern_byte": "0x80",
                        "target_label": "L_082C",
                        "target_address": label(labels, "L_082C"),
                        "effect": "write 0x80 to fast_forward_flag and continue reading pattern pointers",
                    },
                    {
                        "pattern_byte": "0x81",
                        "target_label": "L_082C",
                        "target_address": label(labels, "L_082C"),
                        "effect": "normalize to 0x00, write fast_forward_flag off, and continue reading pattern pointers",
                    },
                    {
                        "pattern_byte": "0x01..0x7F or 0x82..0xFF",
                        "target_label": "L_0830",
                        "target_address": label(labels, "L_0830"),
                        "effect": "pattern jump/repeat handling updates $40/$41 when its counter allows the jump target",
                    },
                ],
                "state_slots": {
                    "pattern_pointer": {
                        "low": {"address": "0x0040", "expression": "$40"},
                        "high": {"address": "0x0041", "expression": "$41"},
                    },
                    "pattern_repeat_counter": {"address": "0x0042", "expression": "$42"},
                    "fast_forward_flag": ram(aliases, "fast_forward_flag"),
                },
                "runtime_capture_requirements": [
                    "distinguish voice-stream zero reads from pattern-pointer 0x00 control pairs",
                    "capture the byte following pattern-level 0x00 before classifying StopMusic or fast-forward behavior",
                    "capture $1B when the 0x80/0x81 pattern-control path is taken",
                ],
            },
        },
        "0xEF": {
            **vcmd_record(entries, "0xEF"),
            "source_effect_status": "source_backed_call_return_slots_runtime_effect_pending",
            "source_span": source_span(labels, "VCMD_Subroutine", "L_0ACE"),
            "handler_flow": [
                "stores the first EF operand/current A into $0240+x",
                "reads the second EF operand into $0241+x",
                "reads the loop/repeat count into $80+x",
                "saves $30+x/$31+x into $0230+x/$0231+x as the return pointer",
                "copies $0240+x/$0241+x into $30+x/$31+x via L_0AC4",
            ],
            "state_slots": {
                "ef_loop_counter": loop_counter,
                "voice_pointer": voice_pointer,
                "ef_return_pointer": ef_return,
                "ef_subroutine_target": ef_target,
            },
            "runtime_capture_requirements": [
                "EF operands and resulting $0240+x/$0241+x subroutine target",
                "$80+x call count after EF",
                "$0230+x/$0231+x saved return pointer",
                "later 0x00 branch result that consumes or restores this EF state",
            ],
        },
        "0xFD": {
            **vcmd_record(entries, "0xFD"),
            "source_effect_status": "source_backed_fast_forward_flag_write_runtime_timing_pending",
            "source_span": source_span(labels, "VCMD_FastForward", "L_0B81"),
            "handler_flow": [
                "increments A before falling through to VCMD_FastForwardOff",
                "writes A into fast_forward_flag ($1B)",
                "jumps to L_0787, which clears $0491/$04B1/$04B5 and ORs the non-SFX voice mask into $0046",
            ],
            "state_slots": {
                "fast_forward_flag": ram(aliases, "fast_forward_flag"),
                "sfx_voices": ram(aliases, "sfx_voices"),
                "helper_reset_slots": ["0x0491", "0x04B1", "0x04B5", "0x0046"],
                "music_effect_fastforward_timer": ram(aliases, "mfx_fastforward_timer"),
            },
            "runtime_capture_requirements": [
                "$1B before and after FD",
                "$0491/$04B1/$04B5/$0046 before and after the L_0787 helper",
                "tempo/tick counters around the affected phrase",
                "separate VCMD fast_forward_flag behavior from MFX_05 mfx_fastforward_timer behavior",
            ],
        },
        "0xFE": {
            **vcmd_record(entries, "0xFE"),
            "source_effect_status": "source_backed_fast_forward_flag_write_runtime_timing_pending",
            "source_span": source_span(labels, "VCMD_FastForwardOff", "L_0B81"),
            "handler_flow": [
                "writes A into fast_forward_flag ($1B)",
                "jumps to L_0787, which clears $0491/$04B1/$04B5 and ORs the non-SFX voice mask into $0046",
            ],
            "state_slots": {
                "fast_forward_flag": ram(aliases, "fast_forward_flag"),
                "sfx_voices": ram(aliases, "sfx_voices"),
                "helper_reset_slots": ["0x0491", "0x04B1", "0x04B5", "0x0046"],
                "music_effect_fastforward_timer": ram(aliases, "mfx_fastforward_timer"),
            },
            "runtime_capture_requirements": [
                "$1B before and after FE",
                "$0491/$04B1/$04B5/$0046 before and after the L_0787 helper",
                "tempo/tick counters around the affected phrase",
                "separate VCMD fast_forward_flag behavior from MFX_05 mfx_fastforward_timer behavior",
            ],
        },
        "0xFF": {
            "command": "0xFF",
            "source_role": "outside_vcmd_table",
            "source_label": None,
            "source_target": None,
            "arg_length": None,
            "source_effect_status": "outside_vcmd_table_no_source_handler",
            "handler_flow": [
                "the source-backed VCMD table covers 0xE0..0xFE only",
                "0xFF must stay classified as outside the VCMD table unless local reader-path evidence proves an EarthBound-specific effect",
            ],
            "runtime_capture_requirements": [
                "reader PC and post-read branch for any observed 0xFF byte",
                "prove whether 0xFF is unreachable data, static-walk overrun, or an EarthBound-specific reader-path effect",
            ],
        },
    }

    return {
        "schema": "earthbound-decomp.audio-spc700-source-effect-frontier.v1",
        "status": "source_effect_facts_ready_runtime_proof_pending",
        "references": [
            "refs/earthbound-sounddriver-byte-perfect/main.asm",
            "refs/earthbound-sounddriver-byte-perfect/ram.asm",
            "manifests/audio-spc700-sounddriver-source-ingest.json",
            "manifests/audio-sequence-command-semantics.json",
        ],
        "summary": {
            "command_count": len(effects),
            "source_backed_vcmd_count": sum(1 for effect in effects.values() if effect.get("source_role") == "source_backed_vcmd"),
            "zero_control_pending_count": sum(1 for effect in effects.values() if effect.get("source_role") == "zero_control_pending"),
            "outside_vcmd_table_count": sum(1 for effect in effects.values() if effect.get("source_role") == "outside_vcmd_table"),
            "runtime_effect_pending_count": len(effects),
            "exact_duration_promotion_allowed": False,
            "semantic_status": "source_navigation_proven_runtime_effects_not_promoted",
        },
        "source_landmarks": {
            "get_next_byte": label(labels, "GetNextByte"),
            "skip_byte": label(labels, "SkipByte"),
            "voice_zero_reader": label(labels, "L_0882"),
            "pattern_zero_reader": label(labels, "L_081A"),
            "ef_subroutine_handler": label(labels, "VCMD_Subroutine"),
            "ef_target_loader": label(labels, "L_0AC4"),
            "fd_handler": label(labels, "VCMD_FastForward"),
            "fe_handler": label(labels, "VCMD_FastForwardOff"),
            "fd_fe_post_write_helper": label(labels, "L_0787"),
            "music_effect_fastforward_tick": label(labels, "TickFastForward"),
            "music_effect_fastforward_start": label(labels, "MFX_05"),
        },
        "effects": effects,
        "promotion_policy": [
            "Source labels and state slots identify proof targets, but do not promote exact-duration exports.",
            "0x00 proof must distinguish voice-stream loop/return behavior from pattern-level StopMusic and fast-forward control pairs.",
            "EF proof must join the call target, loop count, saved return pointer, and later 0x00 behavior.",
            "FD/FE proof must capture fast_forward_flag and timing counters before duration math can model affected regions.",
            "0xFF remains outside the VCMD table unless an EarthBound reader path proves otherwise.",
        ],
        "next_work": [
            "feed these source-effect requirements into zero and nonzero probe plans",
            "capture EF/0x00 state transitions at runtime before unblocking finite end candidates",
            "capture FD/FE fast-forward flag and helper reset effects before timing promotion",
        ],
    }


def render_markdown(data: dict[str, Any]) -> str:
    summary = data["summary"]
    rows = [
        "| `{command}` | `{role}` | `{label}` | `{target}` | `{status}` | {requirements} |".format(
            command=command,
            role=effect.get("source_role"),
            label=effect.get("source_label"),
            target=effect.get("source_target"),
            status=effect.get("source_effect_status"),
            requirements=len(effect.get("runtime_capture_requirements", []))
            + len(effect.get("voice_reader", {}).get("runtime_capture_requirements", []))
            + len(effect.get("pattern_reader", {}).get("runtime_capture_requirements", [])),
        )
        for command, effect in data["effects"].items()
    ]
    return "\n".join(
        [
            "# Audio SPC700 Source Effect Frontier",
            "",
            "Status: source-backed effect landmarks are recorded for runtime proof, with exact-duration promotion still blocked.",
            "",
            "## Summary",
            "",
            f"- commands: `{summary['command_count']}`",
            f"- source-backed VCMDs: `{summary['source_backed_vcmd_count']}`",
            f"- zero-control pending: `{summary['zero_control_pending_count']}`",
            f"- outside-VCMD-table: `{summary['outside_vcmd_table_count']}`",
            f"- exact-duration promotion allowed: `{summary['exact_duration_promotion_allowed']}`",
            f"- semantic status: `{summary['semantic_status']}`",
            "",
            "## Landmarks",
            "",
            *[f"- {name}: `{address}`" for name, address in data["source_landmarks"].items()],
            "",
            "## Effects",
            "",
            "| Command | Source role | Source label | Source target | Source effect status | Runtime capture requirements |",
            "| --- | --- | --- | ---: | --- | ---: |",
            *rows,
            "",
            "## Promotion Policy",
            "",
            *[f"- {item}" for item in data["promotion_policy"]],
            "",
            "## Next Work",
            "",
            *[f"- {item}" for item in data["next_work"]],
            "",
        ]
    )


def main() -> int:
    args = parse_args()
    data = build_frontier(Path(args.main), Path(args.ram))
    output = Path(args.output)
    notes = Path(args.notes)
    output.parent.mkdir(parents=True, exist_ok=True)
    notes.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    notes.write_text(render_markdown(data), encoding="utf-8")
    print(
        "Built audio SPC700 source-effect frontier: "
        f"{data['summary']['command_count']} commands, promotion blocked"
    )
    print(f"Wrote {output}")
    print(f"Wrote {notes}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
