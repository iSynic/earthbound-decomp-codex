#!/usr/bin/env python3
"""Build a source-backed frontier for the SPC700 music-driver command table."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import audio_pack_contracts
import rom_tools
from build_audio_sequence_semantics_frontier import COMMAND_HYPOTHESES


DEFAULT_CONTRACT = ROOT / "manifests" / "audio-pack-contracts.json"
DEFAULT_OUTPUT = ROOT / "manifests" / "audio-spc700-driver-dispatch-frontier.json"
DEFAULT_NOTES = ROOT / "notes" / "audio-spc700-driver-dispatch-frontier.md"
DEFAULT_SOURCE_MAIN = ROOT / "refs" / "earthbound-sounddriver-byte-perfect" / "main.asm"
HIGH_COMMAND_FIRST = 0xE0
HIGH_COMMAND_LAST = 0xFE


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the audio SPC700 driver dispatch frontier.")
    parser.add_argument("--contract", default=str(DEFAULT_CONTRACT), help="Audio pack contract JSON.")
    parser.add_argument("--rom", help="Optional explicit EarthBound US ROM path.")
    parser.add_argument("--source-main", default=str(DEFAULT_SOURCE_MAIN), help="Checked-in byte-perfect sound-driver main.asm.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Manifest output JSON.")
    parser.add_argument("--notes", default=str(DEFAULT_NOTES), help="Markdown note output.")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def parse_hex_int(text: str) -> int:
    return int(text, 16)


def hex_word(value: int) -> str:
    return f"0x{value:04X}"


def hex_byte(value: int) -> str:
    return f"0x{value:02X}"


def extract_driver_payload(contract: dict[str, Any], rom: bytes) -> tuple[dict[str, Any], bytes, int]:
    for pack in contract["audio_packs"]:
        for block in pack.get("stream", {}).get("blocks", []):
            if block.get("role_guess") != "main_spc700_driver_or_driver_overlay":
                continue
            data = audio_pack_contracts.slice_range(rom, audio_pack_contracts.parse_cpu_range(pack["range"]))
            payload_offset = parse_hex_int(block["payload_offset"])
            count = int(block["count"])
            payload = data[payload_offset:payload_offset + count]
            destination = parse_hex_int(block["destination"])
            record = {
                "pack_id": int(pack["pack_id"]),
                "asset_id": pack["asset_id"],
                "range": pack["range"],
                "block_index": int(block["index"]),
                "destination": hex_word(destination),
                "count": count,
                "sha1": block["sha1"],
                "role_guess": block["role_guess"],
            }
            return record, payload, destination
    raise ValueError("audio pack contract does not contain a main SPC700 driver block")


def target_profile(payload: bytes, base: int, target: int) -> dict[str, Any]:
    if not (base <= target < base + len(payload)):
        return {"target": hex_word(target), "inside_driver": False}
    offset = target - base
    first = payload[offset]
    return {
        "target": hex_word(target),
        "inside_driver": True,
        "target_offset": hex_word(offset),
        "first_byte": hex_byte(first),
        "first_byte_is_sequence_high_command_candidate": first >= 0xE0,
        "first_byte_is_note_or_rest_candidate": 0x80 <= first <= 0xC9,
    }


def parse_source_main(path: Path) -> tuple[dict[str, int], dict[str, int], list[dict[str, Any]]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    label_to_addr: dict[str, int] = {}
    addr_re = re.compile(r"^;\s+\$(?P<addr>[0-9A-F]{4})$")
    label_re = re.compile(r"^(?P<label>[A-Za-z0-9_]+):")
    current_addr: int | None = None

    for line in lines:
        addr_match = addr_re.match(line.strip())
        if addr_match:
            current_addr = int(addr_match.group("addr"), 16)
            continue
        label_match = label_re.match(line.strip())
        if label_match and current_addr is not None:
            label_to_addr[label_match.group("label")] = current_addr

    table_index = next(index for index, line in enumerate(lines) if line.strip().startswith("VCMD_Jump_Table:"))
    arg_index = next(index for index, line in enumerate(lines) if line.strip().startswith("VCMD_Arg_Length:"))

    entries: list[dict[str, Any]] = []
    command = HIGH_COMMAND_FIRST
    for line in lines[table_index + 1:arg_index]:
        stripped = line.strip()
        if not stripped.startswith("dw "):
            continue
        label = stripped.split("dw ", 1)[1].split(";")[0].strip()
        if label not in label_to_addr:
            continue
        hypothesis = COMMAND_HYPOTHESES.get(command, {})
        entries.append(
            {
                "command": hex_byte(command),
                "hypothesis": hypothesis.get("name", label),
                "confidence": hypothesis.get("confidence", "source_backed"),
                "source_label": label,
                "target": hex_word(label_to_addr[label]),
            }
        )
        command += 1

    arg_lengths: dict[str, int] = {}
    command = HIGH_COMMAND_FIRST
    for line in lines[arg_index + 1:]:
        stripped = line.strip()
        if not stripped.startswith("db "):
            if arg_lengths:
                break
            continue
        bytes_part = stripped.split("db ", 1)[1].split(";")[0]
        for chunk in bytes_part.split(","):
            value = chunk.strip()
            if not value:
                continue
            arg_lengths[hex_byte(command)] = int(value, 0)
            command += 1

    return label_to_addr, arg_lengths, entries


def build_frontier(contract: dict[str, Any], rom: bytes, source_main: Path) -> dict[str, Any]:
    driver, payload, base = extract_driver_payload(contract, rom)
    label_to_addr, arg_lengths, entries = parse_source_main(source_main)
    for entry in entries:
        entry["arg_length"] = arg_lengths.get(entry["command"])
        entry["target_profile"] = target_profile(payload, base, parse_hex_int(entry["target"]))

    high_command = {
        "status": "source_backed_vcmd_jump_table_ingested",
        "table_base": hex_word(label_to_addr["VCMD_Jump_Table"]),
        "arg_length_table_base": hex_word(label_to_addr["VCMD_Arg_Length"]),
        "command_range": f"{hex_byte(HIGH_COMMAND_FIRST)}..{hex_byte(HIGH_COMMAND_LAST)}",
        "entry_count": len(entries),
        "entries": entries,
        "unresolved_control_bytes": ["0x00", "0xFF"],
    }

    return {
        "schema": "earthbound-decomp.audio-spc700-driver-dispatch-frontier.v1",
        "status": "source_backed_vcmd_table_ingested_ff_reader_effect_pending",
        "references": [
            "manifests/audio-pack-contracts.json",
            "manifests/audio-spc700-sounddriver-source-ingest.json",
            "manifests/audio-sequence-semantics-frontier.json",
            str(source_main.relative_to(ROOT)).replace("\\", "/"),
        ],
        "driver": driver,
        "summary": {
            "driver_base": hex_word(base),
            "driver_bytes": len(payload),
            "high_command_table_base": high_command["table_base"],
            "high_command_entry_count": high_command["entry_count"],
            "arg_length_table_base": high_command["arg_length_table_base"],
            "unresolved_control_bytes": high_command["unresolved_control_bytes"],
            "semantic_status": "source_backed_vcmd_labels_known_ff_reader_effect_unconfirmed",
        },
        "high_command_dispatch_candidate": high_command,
        "indirect_jump_candidates": [],
        "findings": [
            "The ingested byte-perfect source labels the VCMD jump table directly at 0x0BE3 and the argument-length table at 0x0C21.",
            "Commands 0xE0..0xFE now have source-backed labels and handler targets rather than heuristic candidate names.",
            "0x16C7 is refuted as a music high-command dispatch table; the checked-in source shows it is an SFX pointer table.",
            "0xFF remains unresolved because the source-backed VCMD table ends at 0xFE, so FF still needs reader-path proof.",
        ],
        "next_work": [
            "align project-local sequence command names with the source-backed VCMD labels",
            "trace 0xFF reader behavior relative to the source-backed 0xE0..0xFE VCMD table",
            "feed the updated labels into the sequence-control and exact-duration lanes",
        ],
    }


def render_markdown(data: dict[str, Any]) -> str:
    summary = data["summary"]
    high = data["high_command_dispatch_candidate"]
    entry_rows = [
        "| `{command}` | `{label}` | `{target}` | `{arglen}` | `{first_byte}` |".format(
            command=entry["command"],
            label=entry.get("source_label", entry["hypothesis"]),
            target=entry["target"],
            arglen=entry.get("arg_length"),
            first_byte=entry["target_profile"].get("first_byte"),
        )
        for entry in high["entries"]
    ]
    return "\n".join(
        [
            "# Audio SPC700 Driver Dispatch Frontier",
            "",
            "Status: byte-perfect source-backed VCMD labels are known; FF runtime effect still pending.",
            "",
            "## Summary",
            "",
            f"- driver block: pack `{data['driver']['pack_id']}` block `{data['driver']['block_index']}` at `{data['driver']['destination']}`, `{data['driver']['count']}` bytes",
            f"- source-backed VCMD table: `{summary['high_command_table_base']}`",
            f"- source-backed arg-length table: `{summary['arg_length_table_base']}`",
            f"- source-backed command range: `{high['command_range']}`",
            f"- unresolved control bytes: `{summary['unresolved_control_bytes']}`",
            f"- semantic status: `{summary['semantic_status']}`",
            "",
            "## Source-Backed Table",
            "",
            f"- `VCMD_Jump_Table`: `{high['table_base']}`",
            f"- `VCMD_Arg_Length`: `{high['arg_length_table_base']}`",
            "- commands `0xE0..0xFE` now come from checked-in source labels, not static table guesses",
            "- `0xFF` remains outside the source-backed VCMD table and still needs reader-path classification",
            "",
            "## Entries",
            "",
            "| Command | Source label | Driver target | Arg bytes | Target first byte |",
            "| --- | --- | ---: | ---: | --- |",
            *entry_rows,
            "",
            "## Findings",
            "",
            *[f"- {item}" for item in data["findings"]],
            "",
            "## Next Work",
            "",
            *[f"- {item}" for item in data["next_work"]],
            "",
        ]
    )


def main() -> int:
    args = parse_args()
    contract = load_json(Path(args.contract))
    rom_path = rom_tools.find_rom(args.rom)
    data = build_frontier(contract, rom_tools.load_rom(rom_path), Path(args.source_main))
    output = Path(args.output)
    notes = Path(args.notes)
    output.parent.mkdir(parents=True, exist_ok=True)
    notes.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    notes.write_text(render_markdown(data), encoding="utf-8")
    print(
        "Built audio SPC700 driver dispatch frontier: "
        f"{data['summary']['high_command_entry_count']} source-backed VCMD entries, "
        f"unresolved {data['summary']['unresolved_control_bytes']}"
    )
    print(f"Wrote {output}")
    print(f"Wrote {notes}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
