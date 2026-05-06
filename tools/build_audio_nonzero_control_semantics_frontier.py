#!/usr/bin/env python3
"""Build the non-0x00 control-semantics frontier for duration work."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_TRIAGE = ROOT / "manifests" / "audio-exact-duration-triage.json"
DEFAULT_COMMAND_SEMANTICS = ROOT / "manifests" / "audio-sequence-command-semantics.json"
DEFAULT_CONTROL_READER = ROOT / "manifests" / "audio-spc700-control-reader-frontier.json"
DEFAULT_UNCERTAINTY = ROOT / "manifests" / "audio-duration-uncertainty-register.json"
DEFAULT_OUTPUT = ROOT / "manifests" / "audio-nonzero-control-semantics-frontier.json"
DEFAULT_NOTES = ROOT / "notes" / "audio-nonzero-control-semantics-frontier.md"
NONZERO_COMMANDS = ("0xEF", "0xFD", "0xFE", "0xFF")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build non-0x00 audio control-semantics frontier.")
    parser.add_argument("--triage", default=str(DEFAULT_TRIAGE), help="Exact-duration triage JSON.")
    parser.add_argument("--command-semantics", default=str(DEFAULT_COMMAND_SEMANTICS), help="Command semantics JSON.")
    parser.add_argument("--control-reader", default=str(DEFAULT_CONTROL_READER), help="Control reader frontier JSON.")
    parser.add_argument("--uncertainty", default=str(DEFAULT_UNCERTAINTY), help="Duration uncertainty register JSON.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Frontier JSON output.")
    parser.add_argument("--notes", default=str(DEFAULT_NOTES), help="Frontier markdown output.")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def uncertainty_tracks(uncertainty: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        record
        for record in uncertainty.get("tracks", [])
        if record.get("primary_uncertainty") == "non_zero_control_semantics_pending"
    ]


def blocked_packs(triage: dict[str, Any]) -> list[dict[str, Any]]:
    return list(triage.get("categories", {}).get("blocked_by_unpromoted_control", []))


def command_reader_pc_records(control_reader: dict[str, Any], command: str) -> list[dict[str, Any]]:
    records = []
    for record in control_reader.get("reader_pcs", []):
        count = int(record.get("command_counts", {}).get(command, 0))
        if count <= 0:
            continue
        records.append(
            {
                "pc": record.get("pc"),
                "driver_offset": record.get("driver_offset"),
                "role": record.get("role"),
                "read_count": count,
                "sample_reads": [
                    sample
                    for sample in record.get("sample_reads", [])
                    if sample.get("command") == command
                ][:8],
            }
        )
    records.sort(key=lambda item: int(item["read_count"]), reverse=True)
    return records


def command_frontier_records(
    command_semantics: dict[str, Any],
    control_reader: dict[str, Any],
    packs: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    commands = command_semantics.get("commands", {})
    ff_blocker_pack_count = sum(1 for pack in packs if int(pack.get("blocker_counts", {}).get("0xFF", 0)) > 0)
    ff_blocker_total = sum(int(pack.get("blocker_counts", {}).get("0xFF", 0)) for pack in packs)
    ef_edge_pack_count = sum(1 for pack in packs if int(pack.get("ef_call_edges", 0)) > 0)
    ef_edge_total = sum(int(pack.get("ef_call_edges", 0)) for pack in packs)
    frontier: list[dict[str, Any]] = []
    for command in NONZERO_COMMANDS:
        semantic = commands.get(command, {})
        trace = semantic.get("trace_evidence", {})
        if command == "0xFF":
            affected_kind = "static_walk_blocker"
            affected_pack_count = ff_blocker_pack_count
            affected_observation_count = ff_blocker_total
            priority_reason = "0xFF blocks the broad static walk lane and contradicts stock N-SPC semantics until EarthBound effect is decoded."
        elif command == "0xEF":
            affected_kind = "return_stack_context"
            affected_pack_count = ef_edge_pack_count
            affected_observation_count = ef_edge_total
            priority_reason = "0xEF call/return behavior controls whether later terminators are true ends or subroutine returns."
        else:
            affected_kind = "timing_toggle_context"
            affected_pack_count = 0
            affected_observation_count = int(trace.get("sequence_control_read_count", 0))
            priority_reason = "FD/FE are rare runtime-observed timing toggles; exact duration needs local timing-effect proof before use."
        frontier.append(
            {
                "command": command,
                "hypothesis": semantic.get("hypothesis"),
                "semantic_status": semantic.get("semantic_status"),
                "exact_duration_promotion_allowed": bool(semantic.get("exact_duration_promotion_allowed")),
                "static_dispatch_target": semantic.get("static_dispatch_target"),
                "static_walk_policy": semantic.get("static_walk_policy", {}),
                "trace_evidence": trace,
                "reader_pc_records": command_reader_pc_records(control_reader, command),
                "affected_kind": affected_kind,
                "affected_pack_count": affected_pack_count,
                "affected_observation_count": affected_observation_count,
                "priority_reason": priority_reason,
                "required_next_evidence": [
                    "reader PC and command pointer before/after consuming the command byte",
                    "post-read branch target and state mutation",
                    "voice/channel index and phrase/subroutine stack state when applicable",
                    "timing counter or tempo mutation when FD/FE are observed",
                    "classification as timing_toggle, ef_call_return, earthbound_variant_ff, unreachable, or unresolved",
                ],
                "eligible_next_export_action": "keep_public_exact_promotion_blocked",
            }
        )
    return frontier


def priority_pack_records(packs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    records = []
    for pack in packs:
        records.append(
            {
                "pack_id": int(pack["pack_id"]),
                "range": pack.get("range"),
                "track_ids": pack.get("track_ids", []),
                "track_count": int(pack.get("track_count", 0)),
                "export_class_counts": pack.get("export_class_counts", {}),
                "ef_call_edges": int(pack.get("ef_call_edges", 0)),
                "terminators": int(pack.get("terminators", 0)),
                "terminator_counts_by_command": pack.get("terminator_counts_by_command", {}),
                "blocker_counts": pack.get("blocker_counts", {}),
                "recommended_next_step": pack.get("recommended_next_step"),
            }
        )
    records.sort(
        key=lambda item: (
            int(item.get("blocker_counts", {}).get("0xFF", 0)),
            int(item.get("ef_call_edges", 0)),
            int(item.get("track_count", 0)),
        ),
        reverse=True,
    )
    return records


def build_frontier(
    triage: dict[str, Any],
    command_semantics: dict[str, Any],
    control_reader: dict[str, Any],
    uncertainty: dict[str, Any],
) -> dict[str, Any]:
    packs = blocked_packs(triage)
    tracks = uncertainty_tracks(uncertainty)
    export_class_counts = Counter(str(track.get("export_class")) for track in tracks)
    command_records = command_frontier_records(command_semantics, control_reader, packs)
    command_read_counts = {
        record["command"]: int(record.get("trace_evidence", {}).get("sequence_control_read_count", 0))
        for record in command_records
    }
    reader_pc_counts = {
        record["command"]: len(record.get("reader_pc_records", []))
        for record in command_records
    }
    return {
        "schema": "earthbound-decomp.audio-nonzero-control-semantics-frontier.v1",
        "status": "nonzero_control_semantics_frontier_ready_effect_decode_pending",
        "references": [
            "manifests/audio-duration-uncertainty-register.json",
            "manifests/audio-exact-duration-triage.json",
            "manifests/audio-sequence-command-semantics.json",
            "manifests/audio-spc700-control-reader-frontier.json",
            "manifests/audio-spc700-driver-dispatch-frontier.json",
        ],
        "summary": {
            "track_count": len(tracks),
            "pack_count": len(packs),
            "export_class_counts": dict(sorted(export_class_counts.items())),
            "ff_static_blocker_count": sum(int(pack.get("blocker_counts", {}).get("0xFF", 0)) for pack in packs),
            "ef_call_edge_count": sum(int(pack.get("ef_call_edges", 0)) for pack in packs),
            "command_runtime_read_counts": command_read_counts,
            "command_reader_pc_counts": reader_pc_counts,
            "sequence_promotion_allowed": False,
            "semantic_status": "ff_variant_ef_return_fd_fe_timing_effects_unproven",
        },
        "command_frontier": command_records,
        "priority_packs": priority_pack_records(packs)[:32],
        "tracks": [
            {
                "track_id": int(track["track_id"]),
                "track_name": track.get("track_name"),
                "export_class": track.get("export_class"),
                "export_status": track.get("export_status"),
                "recommended_mode": track.get("recommended_mode"),
                "duration_seconds": track.get("duration_seconds"),
                "triage_category": track.get("triage_category"),
                "next_action": track.get("next_action"),
            }
            for track in tracks
        ],
        "promotion_policy": [
            "This frontier is diagnostic only and cannot promote sequence-derived exact duration.",
            "0xFF remains an EarthBound variant/unreachable blocker until local reader-path effect is decoded.",
            "0xEF call/return behavior is required context for exact end-vs-return decisions.",
            "FD/FE timing toggles require local timing-effect proof before exact duration math can depend on them.",
        ],
        "next_work": [
            "decode reader PC 0x0957 first because it observes FF, FE, and EF in the current control-reader frontier",
            "join FF observations to post-read branch/effect state and classify EarthBound-specific behavior",
            "capture FD/FE timing counter or tempo mutations for the rare observed reads",
            "feed validated effects back into audio-sequence-command-semantics before changing export policy",
        ],
    }


def render_markdown(data: dict[str, Any]) -> str:
    summary = data["summary"]
    command_rows = [
        "| `{command}` | `{status}` | `{target}` | {reads} | {pcs} | `{kind}` | {affected} |".format(
            command=record["command"],
            status=record["semantic_status"],
            target=record["static_dispatch_target"],
            reads=record["trace_evidence"].get("sequence_control_read_count", 0),
            pcs=len(record["reader_pc_records"]),
            kind=record["affected_kind"],
            affected=record["affected_observation_count"],
        )
        for record in data["command_frontier"]
    ]
    pack_rows = [
        "| `{pack_id}` | `{track_ids}` | `{classes}` | {ff} | {ef} |".format(
            pack_id=pack["pack_id"],
            track_ids=pack["track_ids"],
            classes=pack["export_class_counts"],
            ff=pack["blocker_counts"].get("0xFF", 0),
            ef=pack["ef_call_edges"],
        )
        for pack in data["priority_packs"][:16]
    ]
    return "\n".join(
        [
            "# Audio Nonzero Control Semantics Frontier",
            "",
            "Status: the 155-track non-0x00 duration lane is grouped by command family and remains effect-proof pending.",
            "",
            "## Summary",
            "",
            f"- tracks: `{summary['track_count']}`",
            f"- packs: `{summary['pack_count']}`",
            f"- export classes: `{summary['export_class_counts']}`",
            f"- FF static blockers: `{summary['ff_static_blocker_count']}`",
            f"- EF call edges: `{summary['ef_call_edge_count']}`",
            f"- command runtime reads: `{summary['command_runtime_read_counts']}`",
            f"- command reader PCs: `{summary['command_reader_pc_counts']}`",
            f"- sequence promotion allowed: `{summary['sequence_promotion_allowed']}`",
            "",
            "## Command Frontier",
            "",
            "| Command | Status | Static target | Runtime reads | Reader PCs | Affected kind | Affected observations |",
            "| --- | --- | --- | ---: | ---: | --- | ---: |",
            *command_rows,
            "",
            "## Priority Packs",
            "",
            "| Pack | Tracks | Export classes | FF blockers | EF edges |",
            "| ---: | --- | --- | ---: | ---: |",
            *pack_rows,
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
    data = build_frontier(
        load_json(Path(args.triage)),
        load_json(Path(args.command_semantics)),
        load_json(Path(args.control_reader)),
        load_json(Path(args.uncertainty)),
    )
    output = Path(args.output)
    notes = Path(args.notes)
    output.parent.mkdir(parents=True, exist_ok=True)
    notes.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    notes.write_text(render_markdown(data), encoding="utf-8")
    print(
        "Built audio nonzero control semantics frontier: "
        f"{data['summary']['track_count']} tracks, "
        f"{data['summary']['pack_count']} packs"
    )
    print(f"Wrote {output}")
    print(f"Wrote {notes}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
