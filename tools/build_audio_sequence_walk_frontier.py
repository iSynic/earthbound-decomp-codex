#!/usr/bin/env python3
"""Build a provisional sequence-walk frontier for EarthBound music data.

This is not a full music decoder. It walks from pointer-table roots, records
strong EF call edges, N-SPC-family 0x00 terminator candidates, and
variant/control blockers so exact duration work can advance one conservative
semantic rung at a time.
"""

from __future__ import annotations

import argparse
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
import rom_tools
from build_audio_sequence_semantics_frontier import COMMAND_HYPOTHESES, pointer_prefix


DEFAULT_CONTRACT = ROOT / "manifests" / "audio-pack-contracts.json"
DEFAULT_EXPORT_PLAN = ROOT / "manifests" / "audio-export-plan.json"
DEFAULT_COMMAND_SEMANTICS = ROOT / "manifests" / "audio-sequence-command-semantics.json"
DEFAULT_MANIFEST = ROOT / "manifests" / "audio-sequence-walk-frontier.json"
DEFAULT_NOTES = ROOT / "notes" / "audio-sequence-walk-frontier.md"

# Provisional N-SPC-like VCMD operand widths. These are only used to avoid
# treating operands as opcodes while walking static structure; final names still
# require EarthBound driver/runtime evidence.
PROVISIONAL_OPERAND_WIDTHS = {
    0x00: 0,
    0xE0: 1,
    0xE1: 1,
    0xE2: 2,
    0xE3: 3,
    0xE4: 0,
    0xE5: 1,
    0xE6: 2,
    0xE7: 1,
    0xE8: 2,
    0xE9: 1,
    0xEA: 1,
    0xEB: 3,
    0xEC: 0,
    0xED: 1,
    0xEE: 2,
    0xEF: 3,
    0xF0: 1,
    0xF1: 3,
    0xF2: 3,
    0xF3: 0,
    0xF4: 1,
    0xF5: 3,
    0xF6: 0,
    0xF7: 3,
    0xF8: 3,
    0xF9: 3,
    0xFA: 1,
    0xFB: 2,
    0xFC: 0,
    0xFD: 0,
    0xFE: 0,
    0xFF: 0,
}

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the audio sequence walk frontier.")
    parser.add_argument("--contract", default=str(DEFAULT_CONTRACT), help="Audio pack contract JSON.")
    parser.add_argument("--export-plan", default=str(DEFAULT_EXPORT_PLAN), help="Audio export plan JSON.")
    parser.add_argument("--command-semantics", default=str(DEFAULT_COMMAND_SEMANTICS), help="Promoted command semantics JSON.")
    parser.add_argument("--rom", help="Optional explicit EarthBound US ROM path.")
    parser.add_argument("--output", default=str(DEFAULT_MANIFEST), help="Manifest output JSON.")
    parser.add_argument("--notes", default=str(DEFAULT_NOTES), help="Markdown note output.")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def command_semantic(command_semantics: dict[str, Any], value: int) -> dict[str, Any]:
    return command_semantics.get("commands", {}).get(f"0x{value:02X}", {})


def parse_hex_int(text: str) -> int:
    return int(text, 16)


def block_payload(rom: bytes, pack: dict[str, Any], block: dict[str, Any]) -> bytes:
    payload_offset = block.get("payload_offset")
    if payload_offset is None:
        return b""
    data = audio_pack_contracts.slice_range(rom, audio_pack_contracts.parse_cpu_range(pack["range"]))
    offset = parse_hex_int(payload_offset)
    return data[offset:offset + int(block["count"])]


def word_at(payload: bytes, offset: int) -> int | None:
    if offset + 1 >= len(payload):
        return None
    return payload[offset] | (payload[offset + 1] << 8)


def pointer_target_offset(value: int | None, destination: int, payload_len: int) -> int | None:
    if value is None:
        return None
    if destination <= value < destination + payload_len:
        return value - destination
    return None


def pointer_roots(prefix: dict[str, Any]) -> list[int]:
    roots = {
        parse_hex_int(entry["target_offset"])
        for entry in prefix["entries_sample"]
        if entry.get("target_offset") is not None
    }
    return sorted(roots)


def segment_end_for(root: int, roots: list[int], payload_len: int) -> int:
    higher = [candidate for candidate in roots if candidate > root]
    return min(higher) if higher else payload_len


def walk_root(
    payload: bytes,
    destination: int,
    root: int,
    roots: list[int],
    command_semantics: dict[str, Any],
) -> dict[str, Any]:
    end = segment_end_for(root, roots, len(payload))
    offset = root
    command_counts: Counter[str] = Counter()
    notes_or_literals = 0
    edges: list[dict[str, Any]] = []
    blockers: list[dict[str, Any]] = []
    terminators: list[dict[str, Any]] = []
    truncations: list[dict[str, Any]] = []

    while offset < end:
        value = payload[offset]
        if value == 0x00:
            semantic = command_semantic(command_semantics, value)
            command_counts["0x00"] += 1
            terminators.append(
                {
                    "offset": f"0x{offset:04X}",
                    "command": "0x00",
                    "segment_end": f"0x{end:04X}",
                    "bytes_before_segment_end": end - offset - 1,
                    "semantic_status": semantic.get("semantic_status", "missing_command_semantics"),
                    "terminator_promoted": bool(
                        semantic.get("static_walk_policy", {}).get("terminator_promoted")
                    ),
                    "n_spc_candidate": "phrase_termination_or_end_of_subroutine",
                }
            )
            break
        if value < 0xE0:
            notes_or_literals += 1
            offset += 1
            continue

        command_counts[f"0x{value:02X}"] += 1
        width = PROVISIONAL_OPERAND_WIDTHS.get(value)
        if width is None:
            blockers.append(
                {
                    "offset": f"0x{offset:04X}",
                    "command": f"0x{value:02X}",
                    "reason": "no_provisional_operand_width",
                }
            )
            break
        if offset + width >= len(payload) or offset + width >= end:
            truncations.append(
                {
                    "offset": f"0x{offset:04X}",
                    "command": f"0x{value:02X}",
                    "operand_width": width,
                    "segment_end": f"0x{end:04X}",
                }
            )
            break

        if value == 0xEF:
            semantic = command_semantic(command_semantics, value)
            target_word = word_at(payload, offset + 1)
            target_offset = pointer_target_offset(target_word, destination, len(payload))
            edges.append(
                {
                    "offset": f"0x{offset:04X}",
                    "target_word": None if target_word is None else f"0x{target_word:04X}",
                    "target_offset": None if target_offset is None else f"0x{target_offset:04X}",
                    "repeat_or_arg": f"0x{payload[offset + 3]:02X}",
                    "target_is_pointer_root": target_offset in roots if target_offset is not None else False,
                    "target_inside_block": target_offset is not None,
                    "semantic_status": semantic.get("semantic_status", "missing_command_semantics"),
                    "exact_duration_promotion_allowed": bool(semantic.get("exact_duration_promotion_allowed")),
                }
            )
        elif command_semantic(command_semantics, value).get("static_walk_policy", {}).get("blocks_static_walk"):
            semantic = command_semantic(command_semantics, value)
            blockers.append(
                {
                    "offset": f"0x{offset:04X}",
                    "command": f"0x{value:02X}",
                    "reason": semantic.get("static_walk_policy", {}).get("reason", "control_semantics_not_promoted"),
                    "semantic_status": semantic.get("semantic_status", "missing_command_semantics"),
                    "next_byte": f"0x{payload[offset + 1]:02X}" if width else None,
                }
            )
        elif command_semantic(command_semantics, value).get("static_walk_policy", {}).get("candidate_terminator"):
            semantic = command_semantic(command_semantics, value)
            terminators.append(
                {
                    "offset": f"0x{offset:04X}",
                    "command": f"0x{value:02X}",
                    "segment_end": f"0x{end:04X}",
                    "bytes_before_segment_end": end - offset - 1,
                    "semantic_status": semantic.get("semantic_status", "missing_command_semantics"),
                    "terminator_promoted": bool(
                        semantic.get("static_walk_policy", {}).get("terminator_promoted")
                    ),
                }
            )
            break

        offset += 1 + width

    return {
        "root_offset": f"0x{root:04X}",
        "segment_end": f"0x{end:04X}",
        "walked_until": f"0x{offset:04X}",
        "notes_or_literals": notes_or_literals,
        "command_counts": dict(sorted(command_counts.items())),
        "ef_call_edges": edges,
        "terminators": terminators,
        "blockers": blockers,
        "truncations": truncations,
        "status": (
            "blocked"
            if blockers or truncations
            else "terminates"
            if terminators
            else "falls_through_segment"
        ),
    }


def build_frontier(
    contract: dict[str, Any],
    export_plan: dict[str, Any],
    command_semantics: dict[str, Any],
    rom: bytes,
) -> dict[str, Any]:
    packs = {int(pack["pack_id"]): pack for pack in contract["audio_packs"]}
    export_by_track = {int(track["track_id"]): track for track in export_plan.get("tracks", [])}
    tracks_by_sequence_pack: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for track in contract["tracks"]:
        sequence_pack = track.get("packs", {}).get("sequence_pack")
        if sequence_pack is None:
            continue
        export = export_by_track.get(int(track["track_id"]), {})
        tracks_by_sequence_pack[int(sequence_pack)].append(
            {
                "track_id": int(track["track_id"]),
                "track_name": track["name"],
                "export_class": export.get("export_class", "unknown"),
                "needs_sequence_semantics": bool(export.get("needs_sequence_semantics", True)),
            }
        )

    pack_records = []
    global_counts: Counter[str] = Counter()
    status_counts: Counter[str] = Counter()
    edge_count = 0
    bad_ef_edges = 0
    blocker_counts: Counter[str] = Counter()
    terminator_count = 0
    terminator_counts_by_command: Counter[str] = Counter()

    for pack_id in sorted(tracks_by_sequence_pack):
        pack = packs[pack_id]
        block_records = []
        pack_status_counts: Counter[str] = Counter()
        pack_command_counts: Counter[str] = Counter()
        pack_blocker_counts: Counter[str] = Counter()
        pack_terminator_counts_by_command: Counter[str] = Counter()
        pack_edge_count = 0
        pack_terminator_count = 0
        for block in pack["stream"]["blocks"]:
            if block.get("terminal"):
                continue
            if block["role_guess"] not in {"sequence_or_runtime_tables", "music_sequence_or_sample_directory"}:
                continue
            payload = block_payload(rom, pack, block)
            destination = parse_hex_int(block["destination"])
            prefix = pointer_prefix(payload, destination)
            roots = pointer_roots(prefix)
            root_walks = [walk_root(payload, destination, root, roots, command_semantics) for root in roots]
            block_command_counts: Counter[str] = Counter()
            block_blocker_counts: Counter[str] = Counter()
            block_edges = 0
            block_bad_edges = 0
            block_terminators = 0
            block_terminator_counts_by_command: Counter[str] = Counter()
            for walk in root_walks:
                status_counts[walk["status"]] += 1
                pack_status_counts[walk["status"]] += 1
                for command, count in walk["command_counts"].items():
                    global_counts[command] += int(count)
                    pack_command_counts[command] += int(count)
                    block_command_counts[command] += int(count)
                for edge in walk["ef_call_edges"]:
                    edge_count += 1
                    pack_edge_count += 1
                    block_edges += 1
                    if not edge["target_inside_block"]:
                        bad_ef_edges += 1
                        block_bad_edges += 1
                for blocker in walk["blockers"]:
                    blocker_counts[blocker["command"]] += 1
                    pack_blocker_counts[blocker["command"]] += 1
                    block_blocker_counts[blocker["command"]] += 1
                terminator_count += len(walk["terminators"])
                pack_terminator_count += len(walk["terminators"])
                block_terminators += len(walk["terminators"])
                for terminator in walk["terminators"]:
                    command = str(terminator.get("command", "unknown"))
                    terminator_counts_by_command[command] += 1
                    pack_terminator_counts_by_command[command] += 1
                    block_terminator_counts_by_command[command] += 1

            block_records.append(
                {
                    "block_index": int(block["index"]),
                    "destination": block["destination"],
                    "bytes": int(block["count"]),
                    "payload_sha1": block["sha1"],
                    "pointer_roots": len(roots),
                    "walk_status_counts": dict(sorted(Counter(walk["status"] for walk in root_walks).items())),
                    "command_counts": dict(sorted(block_command_counts.items())),
                    "ef_call_edges": block_edges,
                    "ef_edges_not_inside_block": block_bad_edges,
                    "terminators": block_terminators,
                    "terminator_counts_by_command": dict(sorted(block_terminator_counts_by_command.items())),
                    "blocker_counts": dict(sorted(block_blocker_counts.items())),
                    "root_walks_sample": root_walks[:8],
                }
            )

        if block_records:
            pack_records.append(
                {
                    "pack_id": pack_id,
                    "range": pack["range"],
                    "tracks": tracks_by_sequence_pack[pack_id],
                    "block_count": len(block_records),
                    "walk_status_counts": dict(sorted(pack_status_counts.items())),
                    "command_counts": dict(sorted(pack_command_counts.items())),
                    "ef_call_edges": pack_edge_count,
                    "terminators": pack_terminator_count,
                    "terminator_counts_by_command": dict(sorted(pack_terminator_counts_by_command.items())),
                    "blocker_counts": dict(sorted(pack_blocker_counts.items())),
                    "blocks": block_records,
                }
            )

    priority_candidates = sorted(
        pack_records,
        key=lambda item: (
            sum(1 for track in item["tracks"] if track["needs_sequence_semantics"]),
            sum(item["blocker_counts"].values()),
            item["ef_call_edges"],
            len(item["tracks"]),
        ),
        reverse=True,
    )[:20]
    zero_review_candidates = [
        pack
        for pack in pack_records
        if not pack["blocker_counts"]
        and int(pack.get("terminator_counts_by_command", {}).get("0x00", 0)) > 0
        and any(track["needs_sequence_semantics"] for track in pack["tracks"])
    ]
    priority_by_id = {int(pack["pack_id"]): pack for pack in priority_candidates}
    for pack in zero_review_candidates:
        priority_by_id.setdefault(int(pack["pack_id"]), pack)
    priority_packs = sorted(
        priority_by_id.values(),
        key=lambda item: (
            int(item["pack_id"]) not in {int(pack["pack_id"]) for pack in priority_candidates},
            -sum(1 for track in item["tracks"] if track["needs_sequence_semantics"]),
            -int(item.get("terminator_counts_by_command", {}).get("0x00", 0)),
            int(item["pack_id"]),
        ),
    )

    return {
        "schema": "earthbound-decomp.audio-sequence-walk-frontier.v1",
        "source_policy": contract["source_policy"],
        "references": [
            "manifests/audio-pack-contracts.json",
            "manifests/audio-export-plan.json",
            "manifests/audio-sequence-command-semantics.json",
            "manifests/audio-sequence-control-flow-frontier.json",
            "manifests/audio-sequence-semantics-frontier.json",
        ],
        "summary": {
            "sequence_packs_walked": len(pack_records),
            "walk_status_counts": dict(sorted(status_counts.items())),
            "command_counts": dict(sorted(global_counts.items())),
            "ef_call_edges": edge_count,
            "ef_edges_not_inside_block": bad_ef_edges,
            "ef_edges_not_inside_block_ratio": round(bad_ef_edges / edge_count, 4) if edge_count else 0,
            "terminators": terminator_count,
            "terminator_counts_by_command": dict(sorted(terminator_counts_by_command.items())),
            "blocker_counts": dict(sorted(blocker_counts.items())),
            "priority_pack_count": len(priority_packs),
            "zero_review_priority_pack_count": len(zero_review_candidates),
            "command_semantics_status": command_semantics.get("status"),
            "command_semantics_release_promotion_allowed": bool(
                command_semantics.get("summary", {}).get("release_sequence_promotion_allowed")
            ),
            "semantic_status": "provisional_n_spc_static_walk_zero_terminators_unpromoted",
        },
        "command_semantics": {
            "schema": command_semantics.get("schema"),
            "status": command_semantics.get("status"),
            "summary": command_semantics.get("summary", {}),
            "control_commands": {
                command: {
                    "semantic_status": record.get("semantic_status"),
                    "exact_duration_promotion_allowed": record.get("exact_duration_promotion_allowed"),
                    "static_walk_policy": record.get("static_walk_policy"),
                }
                for command, record in command_semantics.get("commands", {}).items()
                if command in {"0x00", "0xEF", "0xFD", "0xFE", "0xFF"}
            },
        },
        "provisional_operand_widths": {
            f"0x{command:02X}": {
                "operand_width": width,
                "hypothesis": COMMAND_HYPOTHESES.get(command, {}).get("name", "unknown_high_command_candidate"),
            }
            for command, width in sorted(PROVISIONAL_OPERAND_WIDTHS.items())
        },
        "pack_summaries": [
            {
                "pack_id": pack["pack_id"],
                "range": pack["range"],
                "track_count": len(pack["tracks"]),
                "track_ids": [track["track_id"] for track in pack["tracks"]],
                "export_class_counts": dict(Counter(track["export_class"] for track in pack["tracks"])),
                "needs_sequence_semantics_count": sum(1 for track in pack["tracks"] if track["needs_sequence_semantics"]),
                "block_count": pack["block_count"],
                "walk_status_counts": pack["walk_status_counts"],
                "ef_call_edges": pack["ef_call_edges"],
                "terminators": pack["terminators"],
                "terminator_counts_by_command": pack["terminator_counts_by_command"],
                "blocker_counts": pack["blocker_counts"],
            }
            for pack in pack_records
        ],
        "priority_packs": priority_packs,
        "findings": [
            "EF call edges are now represented as explicit same-block target edges in a static walk frontier.",
            "A small number of EF-like bytes are tracked as out-of-block under the provisional width table, which marks operand-width or data/noise uncertainty rather than promoted call semantics.",
            "N-SPC-family 0x00 candidates are now recorded as phrase termination/end-of-subroutine evidence, but exact end-vs-return meaning still needs EarthBound-local proof.",
            "FD and FE are N-SPC fast-forward toggle candidates; timing effect is not promoted from driver/runtime evidence yet.",
            "FF is not treated as a terminator under the N-SPC hypothesis; stock N-SPC marks it invalid unless EarthBound proves a variant-specific effect.",
            "The walker records offsets, hashes, counts, and edge metadata only; it does not embed ROM-derived sequence payload byte strings.",
        ],
        "next_work": [
            "trace or disassemble 0x00 phrase/VCMD termination and EF return handling",
            "tie FD/FE/FF behavior to the SPC700 driver dispatch path",
            "turn EF call edges into a checked sequence subroutine stack model",
            "use walker status to narrow exact-duration work to packs without unpromoted blockers first",
        ],
    }


def render_markdown(data: dict[str, Any]) -> str:
    summary = data["summary"]
    priority_rows = []
    for pack in data["priority_packs"]:
        priority_rows.append(
            f"| `{pack['pack_id']}` | `{pack['range']}` | {len(pack['tracks'])} | "
            f"`{pack['walk_status_counts']}` | {pack['ef_call_edges']} | {pack['terminators']} | "
            f"`{pack['blocker_counts']}` |"
        )
    command_rows = [
        f"| `{command}` | {count} | {data['provisional_operand_widths'].get(command, {}).get('hypothesis', '')} |"
        for command, count in summary["command_counts"].items()
    ]
    return "\n".join(
        [
            "# Audio Sequence Walk Frontier",
            "",
            "Status: provisional N-SPC-family static walk built; 0x00 terminator candidates and EF edges are explicit, but exact duration promotion still needs EarthBound-local proof.",
            "",
            "## Summary",
            "",
            f"- sequence packs walked: `{summary['sequence_packs_walked']}`",
            f"- walk statuses: `{summary['walk_status_counts']}`",
            f"- EF call edges: `{summary['ef_call_edges']}`",
            f"- EF edges outside block: `{summary['ef_edges_not_inside_block']}` (`{summary['ef_edges_not_inside_block_ratio']}`)",
            f"- terminator candidates reached: `{summary['terminators']}`",
            f"- terminator counts by command: `{summary['terminator_counts_by_command']}`",
            f"- blocker counts: `{summary['blocker_counts']}`",
            f"- priority packs with full walk samples: `{summary['priority_pack_count']}`",
            f"- zero-review priority packs: `{summary['zero_review_priority_pack_count']}`",
            f"- semantic status: `{summary['semantic_status']}`",
            "",
            "## Commands Seen By Walker",
            "",
            "| Command | Count | Current label |",
            "| --- | ---: | --- |",
            *command_rows,
            "",
            "## Priority Packs",
            "",
            "| Pack | ROM range | Tracks | Walk statuses | EF edges | Terminators | Blockers |",
            "| ---: | --- | ---: | --- | ---: | ---: | --- |",
            *priority_rows,
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
    contract = load_json(Path(args.contract))
    export_plan = load_json(Path(args.export_plan))
    command_semantics = load_json(Path(args.command_semantics))
    rom = rom_tools.load_rom(rom_tools.find_rom(args.rom))
    data = build_frontier(contract, export_plan, command_semantics, rom)
    output = Path(args.output)
    notes = Path(args.notes)
    output.parent.mkdir(parents=True, exist_ok=True)
    notes.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    notes.write_text(render_markdown(data), encoding="utf-8")
    print(
        "Built audio sequence walk frontier: "
        f"{data['summary']['sequence_packs_walked']} packs, "
        f"{data['summary']['ef_call_edges']} EF edges"
    )
    print(f"Wrote {output}")
    print(f"Wrote {notes}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
