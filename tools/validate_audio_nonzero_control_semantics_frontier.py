#!/usr/bin/env python3
"""Validate the non-0x00 control-semantics frontier."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MANIFEST = ROOT / "manifests" / "audio-nonzero-control-semantics-frontier.json"
REQUIRED_COMMANDS = {"0xEF", "0xFD", "0xFE", "0xFF"}
ALLOWED_AFFECTED_KIND = {
    "return_stack_context",
    "static_walk_blocker",
    "timing_toggle_context",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate audio non-0x00 control-semantics frontier.")
    parser.add_argument("manifest", nargs="?", default=str(DEFAULT_MANIFEST))
    return parser.parse_args()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def count_tracks(tracks: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for track in tracks:
        counts[str(track.get(key))] += 1
    return dict(sorted(counts.items()))


def validate(data: dict[str, Any]) -> None:
    require(data.get("schema") == "earthbound-decomp.audio-nonzero-control-semantics-frontier.v1", "unexpected schema")
    require(
        data.get("status") == "nonzero_control_semantics_frontier_ready_effect_decode_pending",
        f"unexpected status {data.get('status')}",
    )
    references = set(data.get("references", []))
    for reference in (
        "manifests/audio-duration-uncertainty-register.json",
        "manifests/audio-exact-duration-triage.json",
        "manifests/audio-sequence-command-semantics.json",
        "manifests/audio-spc700-control-reader-frontier.json",
    ):
        require(reference in references, f"missing reference {reference}")

    tracks = data.get("tracks", [])
    packs = data.get("priority_packs", [])
    commands = data.get("command_frontier", [])
    summary = data.get("summary", {})
    require(int(summary.get("track_count", -1)) == len(tracks), "track count mismatch")
    require(int(summary.get("track_count", 0)) == 155, "expected 155 non-zero control tracks")
    require(int(summary.get("pack_count", 0)) >= len(packs), "priority pack count larger than pack count")
    require(summary.get("export_class_counts") == count_tracks(tracks, "export_class"), "export class counts mismatch")
    require(summary.get("sequence_promotion_allowed") is False, "sequence promotion must remain blocked")
    require(int(summary.get("ff_static_blocker_count", 0)) > 0, "expected FF blockers")
    require(int(summary.get("ef_call_edge_count", 0)) > 0, "expected EF call edges")

    command_by_id = {str(record.get("command")): record for record in commands}
    require(set(command_by_id) == REQUIRED_COMMANDS, "nonzero command set mismatch")
    read_counts = {}
    reader_pc_counts = {}
    for command, record in command_by_id.items():
        require(record.get("semantic_status"), f"{command}: missing semantic status")
        require(record.get("exact_duration_promotion_allowed") is False, f"{command}: promotion must remain blocked")
        require(record.get("eligible_next_export_action") == "keep_public_exact_promotion_blocked", f"{command}: unexpected export action")
        require(record.get("affected_kind") in ALLOWED_AFFECTED_KIND, f"{command}: unexpected affected kind")
        require(record.get("priority_reason"), f"{command}: missing priority reason")
        require(len(record.get("required_next_evidence", [])) >= 4, f"{command}: required evidence too thin")
        trace = record.get("trace_evidence", {})
        require("sequence_control_read_count" in trace, f"{command}: missing read count")
        read_counts[command] = int(trace.get("sequence_control_read_count", 0))
        reader_pc_counts[command] = len(record.get("reader_pc_records", []))
        for pc_record in record.get("reader_pc_records", []):
            require(str(pc_record.get("pc", "")).startswith("0x"), f"{command}: invalid reader PC")
            require(int(pc_record.get("read_count", 0)) > 0, f"{command}: reader PC missing read count")
        if command == "0xFF":
            require(record.get("affected_kind") == "static_walk_blocker", "0xFF must be static walk blocker")
            require(int(record.get("affected_observation_count", 0)) == int(summary.get("ff_static_blocker_count", -1)), "FF blocker count mismatch")
        if command == "0xEF":
            require(record.get("affected_kind") == "return_stack_context", "0xEF must be return stack context")
            require(int(record.get("affected_observation_count", 0)) == int(summary.get("ef_call_edge_count", -1)), "EF edge count mismatch")
    require(summary.get("command_runtime_read_counts") == dict(sorted(read_counts.items())), "command read counts mismatch")
    require(summary.get("command_reader_pc_counts") == dict(sorted(reader_pc_counts.items())), "reader PC counts mismatch")

    seen_tracks: set[int] = set()
    for track in tracks:
        track_id = int(track.get("track_id", -1))
        require(track_id > 0, f"invalid track id {track_id}")
        require(track_id not in seen_tracks, f"duplicate track id {track_id}")
        seen_tracks.add(track_id)
        require(track.get("triage_category") == "blocked_by_unpromoted_control", f"track {track_id}: unexpected triage category")
        require(track.get("next_action"), f"track {track_id}: missing next action")
    for pack in packs:
        require("pack_id" in pack, "pack missing id")
        require(pack.get("track_ids"), f"pack {pack.get('pack_id')}: missing tracks")
        require("blocker_counts" in pack, f"pack {pack.get('pack_id')}: missing blocker counts")
        require("terminator_counts_by_command" in pack, f"pack {pack.get('pack_id')}: missing terminator counts")

    require(data.get("promotion_policy"), "missing promotion policy")
    require(data.get("next_work"), "missing next work")


def main() -> int:
    args = parse_args()
    data = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    validate(data)
    print(
        "Audio nonzero control semantics frontier validation OK: "
        f"{data['summary']['track_count']} tracks, "
        f"{data['summary']['pack_count']} packs"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
