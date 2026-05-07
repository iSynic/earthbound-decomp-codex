#!/usr/bin/env python3
"""Build a frontier for SPC700 sequence control-byte reader PCs."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import audio_pack_contracts
import audio_spc700_source
import rom_tools


DEFAULT_DISPATCH_TRACE = ROOT / "manifests" / "audio-spc700-dispatch-trace-frontier.json"
DEFAULT_CONTRACT = ROOT / "manifests" / "audio-pack-contracts.json"
DEFAULT_SOURCE_MAIN = ROOT / "refs" / "earthbound-sounddriver-byte-perfect" / "main.asm"
DEFAULT_OUTPUT = ROOT / "manifests" / "audio-spc700-control-reader-frontier.json"
DEFAULT_NOTES = ROOT / "notes" / "audio-spc700-control-reader-frontier.md"
CONTROL_COMMANDS = ("0x00", "0xEF", "0xFD", "0xFE", "0xFF")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the SPC700 control reader frontier.")
    parser.add_argument("--dispatch-trace", default=str(DEFAULT_DISPATCH_TRACE), help="Dispatch trace frontier JSON.")
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


def driver_payload(contract: dict[str, Any], rom: bytes) -> tuple[dict[str, Any], bytes]:
    pack = next(pack for pack in contract["audio_packs"] if int(pack["pack_id"]) == 1)
    block = next(
        block
        for block in pack["stream"]["blocks"]
        if block.get("role_guess") == "main_spc700_driver_or_driver_overlay"
    )
    data = audio_pack_contracts.slice_range(rom, audio_pack_contracts.parse_cpu_range(pack["range"]))
    offset = parse_hex_int(block["payload_offset"])
    return block, data[offset:offset + int(block["count"])]


def window_profile(payload: bytes, destination: int, pc: str) -> dict[str, Any]:
    address = parse_hex_int(pc)
    offset = address - destination
    start = max(0, offset - 8)
    end = min(len(payload), offset + 24)
    window = payload[start:end]
    first_byte = payload[offset] if 0 <= offset < len(payload) else None
    return {
        "pc": pc,
        "inside_driver_block": 0 <= offset < len(payload),
        "driver_offset": None if not (0 <= offset < len(payload)) else f"0x{offset:04X}",
        "window_start_offset": f"0x{start:04X}",
        "window_byte_count": len(window),
        "window_sha1": hashlib.sha1(window).hexdigest(),
        "first_byte": None if first_byte is None else f"0x{first_byte:02X}",
    }


def collect_reader_records(dispatch_trace: dict[str, Any], payload: bytes, destination: int) -> list[dict[str, Any]]:
    by_pc: dict[str, dict[str, Any]] = {}
    command_pc_counts = dispatch_trace.get("summary", {}).get("control_reader_pc_counts_by_command", {})
    sample_by_pc: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in dispatch_trace.get("records", []):
        for sample in record.get("control_candidate_read_samples", []):
            pc = str(sample.get("pc"))
            if len(sample_by_pc[pc]) >= 8:
                continue
            sample_by_pc[pc].append(
                {
                    "track_id": record.get("track_id"),
                    "track_name": record.get("track_name"),
                    "command": sample.get("data"),
                    "sequence_address": sample.get("address"),
                    "instruction": sample.get("instruction"),
                    "registers": sample.get("registers"),
                    "command_pointer_registers": sample.get("command_pointer_registers"),
                }
            )
    for command, pcs in command_pc_counts.items():
        for pc, count in pcs.items():
            record = by_pc.setdefault(
                pc,
                {
                    **window_profile(payload, destination, pc),
                    "role": "sequence_control_byte_reader_candidate",
                    "command_counts": {},
                    "total_control_reads": 0,
                    "sample_reads": sample_by_pc.get(pc, []),
                },
            )
            record["command_counts"][command] = int(count)
            record["total_control_reads"] += int(count)
    records = list(by_pc.values())
    records.sort(key=lambda item: (-int(item["total_control_reads"]), item["pc"]))
    return records


def add_source_reader_labels(records: list[dict[str, Any]], source_main: Path) -> dict[str, str]:
    labels = audio_spc700_source.parse_source_labels(source_main)
    source_reader_labels = {
        audio_spc700_source.hex_word(labels["GetNextByte"].address): "GetNextByte",
        audio_spc700_source.hex_word(labels["SkipByte"].address): "SkipByte",
    }
    for record in records:
        label = source_reader_labels.get(str(record.get("pc")))
        if label:
            record["source_label"] = label
            record["source_role"] = "source_backed_reader_helper"
    return source_reader_labels


def build_frontier(dispatch_trace: dict[str, Any], contract: dict[str, Any], rom: bytes, source_main: Path) -> dict[str, Any]:
    block, payload = driver_payload(contract, rom)
    destination = parse_hex_int(block["destination"])
    records = collect_reader_records(dispatch_trace, payload, destination)
    source_reader_labels = add_source_reader_labels(records, source_main)
    command_totals: Counter[str] = Counter()
    for record in records:
        command_totals.update(record["command_counts"])
    return {
        "schema": "earthbound-decomp.audio-spc700-control-reader-frontier.v1",
        "status": "control_reader_pcs_identified_effect_decode_pending",
        "references": [
            "manifests/audio-spc700-dispatch-trace-frontier.json",
            "manifests/audio-pack-contracts.json",
            "tools/ares_audio_harness/main.cpp",
        ],
        "driver": {
            "pack_id": 1,
            "block_index": int(block["index"]),
            "destination": block["destination"],
            "bytes": int(block["count"]),
            "payload_sha1": block["sha1"],
        },
        "summary": {
            "reader_pc_count": len(records),
            "control_read_count": sum(int(record["total_control_reads"]) for record in records),
            "command_counts": dict(sorted(command_totals.items())),
            "source_backed_reader_labels": source_reader_labels,
            "exact_duration_promotion_allowed": False,
            "semantic_status": "reader_paths_known_effects_unpromoted",
        },
        "reader_pcs": records,
        "findings": [
            "Runtime traces now identify concrete SPC700 PCs that read sequence control bytes.",
            "The checked-in byte-perfect source labels the strongest helper readers as GetNextByte and SkipByte.",
            "The control reader PCs are stronger next targets than the provisional high-command dispatch table for current exact-duration work.",
            "This frontier records offsets, counts, hashes, and sampled register context only; it does not embed ROM-derived driver byte windows.",
        ],
        "next_work": [
            "decode reader PCs that observe 0x00 because they are now the primary end-vs-return proof target",
            "decode reader PC 0x0957 because it observes FF, FE, and EF control bytes",
            "decode reader PC 0x0847 because it observes FD and FE control bytes",
            "decode reader PC 0x0B8A because it is the dominant EF reader in the sampled corpus",
        ],
    }


def render_markdown(data: dict[str, Any]) -> str:
    summary = data["summary"]
    rows = [
        "| `{pc}` | `{label}` | {count} | `{commands}` | `{offset}` | `{first}` | `{sha1}` |".format(
            pc=record["pc"],
            label=record.get("source_label"),
            count=record["total_control_reads"],
            commands=record["command_counts"],
            offset=record["driver_offset"],
            first=record["first_byte"],
            sha1=record["window_sha1"],
        )
        for record in data["reader_pcs"]
    ]
    return "\n".join(
        [
            "# Audio SPC700 Control Reader Frontier",
            "",
            "Status: runtime control-byte reader PCs identified; command effects remain unpromoted.",
            "",
            "## Summary",
            "",
            f"- reader PCs: `{summary['reader_pc_count']}`",
            f"- control reads: `{summary['control_read_count']}`",
            f"- command counts: `{summary['command_counts']}`",
            f"- source-backed reader labels: `{summary['source_backed_reader_labels']}`",
            f"- exact-duration promotion allowed: `{summary['exact_duration_promotion_allowed']}`",
            f"- semantic status: `{summary['semantic_status']}`",
            "",
            "## Reader PCs",
            "",
            "| PC | Source label | Control reads | Commands | Driver offset | First byte | Window SHA-1 |",
            "| ---: | --- | ---: | --- | ---: | ---: | --- |",
            *rows,
            "",
            "## Findings",
            "",
            *[f"- {finding}" for finding in data["findings"]],
            "",
            "## Next Work",
            "",
            *[f"- {item}" for item in data["next_work"]],
            "",
        ]
    )


def main() -> int:
    args = parse_args()
    dispatch_trace = load_json(Path(args.dispatch_trace))
    contract = load_json(Path(args.contract))
    rom = rom_tools.load_rom(rom_tools.find_rom(args.rom))
    data = build_frontier(dispatch_trace, contract, rom, Path(args.source_main))
    output = Path(args.output)
    notes = Path(args.notes)
    output.parent.mkdir(parents=True, exist_ok=True)
    notes.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    notes.write_text(render_markdown(data), encoding="utf-8")
    print(
        "Built audio SPC700 control reader frontier: "
        f"{data['summary']['reader_pc_count']} PCs, "
        f"{data['summary']['control_read_count']} reads"
    )
    print(f"Wrote {output}")
    print(f"Wrote {notes}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
