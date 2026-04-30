#!/usr/bin/env python3
"""Build an exact-duration triage report from export policy and sequence walking."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_EXPORT_PLAN = ROOT / "manifests" / "audio-export-plan.json"
DEFAULT_WALK_FRONTIER = ROOT / "manifests" / "audio-sequence-walk-frontier.json"
DEFAULT_COMMAND_SEMANTICS = ROOT / "manifests" / "audio-sequence-command-semantics.json"
DEFAULT_MANIFEST = ROOT / "manifests" / "audio-exact-duration-triage.json"
DEFAULT_NOTES = ROOT / "notes" / "audio-exact-duration-triage.md"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build audio exact-duration triage.")
    parser.add_argument("--export-plan", default=str(DEFAULT_EXPORT_PLAN), help="Audio export plan JSON.")
    parser.add_argument("--walk-frontier", default=str(DEFAULT_WALK_FRONTIER), help="Sequence walk frontier JSON.")
    parser.add_argument("--command-semantics", default=str(DEFAULT_COMMAND_SEMANTICS), help="Promoted command semantics JSON.")
    parser.add_argument("--output", default=str(DEFAULT_MANIFEST), help="Manifest output JSON.")
    parser.add_argument("--notes", default=str(DEFAULT_NOTES), help="Markdown note output.")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def classify_pack(pack: dict[str, Any]) -> str:
    blockers = pack.get("blocker_counts", {})
    needs = int(pack.get("needs_sequence_semantics_count", 0))
    terminator_counts = pack.get("terminator_counts_by_command", {})
    zero_terminators = int(terminator_counts.get("0x00", 0))
    ff_terminators = int(terminator_counts.get("0xFF", 0))
    if needs == 0:
        return "no_sequence_semantics_needed"
    if blockers:
        return "blocked_by_unpromoted_control"
    if zero_terminators > 0:
        return "candidate_for_zero_terminator_review"
    if ff_terminators > 0:
        return "candidate_for_ff_variant_review"
    return "needs_loop_or_fallthrough_semantics"


def lane_semantic_status(category: str, command_semantics: dict[str, Any]) -> dict[str, Any]:
    commands = command_semantics.get("commands", {})
    if category == "candidate_for_zero_terminator_review":
        zero = commands.get("0x00", {})
        return {
            "evidence_status": zero.get("semantic_status", "missing_command_semantics"),
            "exact_duration_promotion_allowed": bool(zero.get("exact_duration_promotion_allowed")),
            "eligible_next_export_action": zero.get("eligible_next_export_action", "keep_public_exact_promotion_blocked"),
        }
    if category == "candidate_for_ff_variant_review":
        ff = commands.get("0xFF", {})
        return {
            "evidence_status": ff.get("semantic_status", "missing_command_semantics"),
            "exact_duration_promotion_allowed": bool(ff.get("exact_duration_promotion_allowed")),
            "eligible_next_export_action": ff.get("eligible_next_export_action", "keep_public_exact_promotion_blocked"),
        }
    if category == "blocked_by_unpromoted_control":
        blocked = {
            command: commands.get(command, {}).get("semantic_status", "missing_command_semantics")
            for command in ("0xFD", "0xFE", "0xFF")
        }
        return {
            "evidence_status": "blocked_by_control_semantics",
            "exact_duration_promotion_allowed": False,
            "eligible_next_export_action": "decode_unpromoted_control_before_public_exact_promotion",
            "blocked_command_statuses": blocked,
        }
    return {
        "evidence_status": "not_promoted_by_command_semantics",
        "exact_duration_promotion_allowed": False,
        "eligible_next_export_action": "keep_current_export_policy",
    }


def build_triage(
    export_plan: dict[str, Any],
    walk_frontier: dict[str, Any],
    command_semantics: dict[str, Any],
) -> dict[str, Any]:
    tracks_by_id = {int(track["track_id"]): track for track in export_plan["tracks"]}
    categories: dict[str, list[dict[str, Any]]] = {}
    status_counts: Counter[str] = Counter()
    track_counts: Counter[str] = Counter()

    for pack in walk_frontier.get("pack_summaries", []):
        category = classify_pack(pack)
        status_counts[category] += 1
        track_counts[category] += len(pack.get("track_ids", []))
        track_records = []
        for track_id in pack.get("track_ids", []):
            track = tracks_by_id.get(int(track_id), {})
            track_records.append(
                {
                    "track_id": int(track_id),
                    "track_name": track.get("track_name"),
                    "export_class": track.get("export_class"),
                    "recommended_mode": track.get("recommended_mode"),
                    "duration_seconds": track.get("duration_seconds"),
                    "needs_sequence_semantics": track.get("needs_sequence_semantics"),
                }
            )
        categories.setdefault(category, []).append(
            {
                "pack_id": pack["pack_id"],
                "range": pack["range"],
                "track_count": pack["track_count"],
                "track_ids": pack["track_ids"],
                "tracks": track_records,
                "export_class_counts": pack["export_class_counts"],
                "walk_status_counts": pack["walk_status_counts"],
                "ef_call_edges": pack["ef_call_edges"],
                "terminators": pack["terminators"],
                "terminator_counts_by_command": pack.get("terminator_counts_by_command", {}),
                "blocker_counts": pack["blocker_counts"],
                "command_semantic_status": lane_semantic_status(category, command_semantics),
                "recommended_next_step": recommended_next_step(category),
            }
        )

    for records in categories.values():
        records.sort(
            key=lambda item: (
                item["track_count"],
                item["terminators"],
                item["ef_call_edges"],
            ),
            reverse=True,
        )

    return {
        "schema": "earthbound-decomp.audio-exact-duration-triage.v1",
        "source_policy": export_plan["source_policy"] if "source_policy" in export_plan else {
            "requires_user_supplied_rom": True,
            "do_not_commit_generated_outputs": True,
            "generated_audio_output_root": "build/audio",
        },
        "references": [
            "manifests/audio-export-plan.json",
            "manifests/audio-sequence-walk-frontier.json",
            "manifests/audio-sequence-command-semantics.json",
            "manifests/audio-sequence-control-flow-frontier.json",
        ],
        "summary": {
            "sequence_packs_triaged": sum(status_counts.values()),
            "category_pack_counts": dict(sorted(status_counts.items())),
            "category_track_counts": dict(sorted(track_counts.items())),
            "command_semantics_status": command_semantics.get("status"),
            "sequence_promotion_allowed": bool(
                command_semantics.get("summary", {}).get("release_sequence_promotion_allowed")
            ),
            "release_status": "exact_duration_not_promoted_sequence_triage_ready",
        },
        "command_semantics": {
            "schema": command_semantics.get("schema"),
            "status": command_semantics.get("status"),
            "summary": command_semantics.get("summary", {}),
        },
        "categories": categories,
        "findings": [
            "Exact-duration work now splits into packs with N-SPC 0x00 terminator candidates, packs blocked by unpromoted control, and packs needing loop/fallthrough semantics.",
            "The PK Hack/N-SPC confirmation moves finite-end review away from static FF terminator assumptions.",
            "Packs with 0x00 terminator candidates are the fastest next candidates for exact finite review, but EF return context still matters.",
            "Loop/held preview tracks still need explicit loop-point or fade policy even when playback/export is already near-oracle accurate.",
        ],
        "next_work": [
            "promote candidate_for_zero_terminator_review packs into focused reports that distinguish song end from EF subroutine return",
            "decode FD/FE fast-forward timing behavior because it can skip or resume audible playback",
            "keep FF in a variant/unreachable review lane unless EarthBound driver proof contradicts stock N-SPC",
            "feed resolved exact finite or loop outcomes back into audio-export-plan",
        ],
    }


def recommended_next_step(category: str) -> str:
    if category == "candidate_for_zero_terminator_review":
        return "build focused pack report and confirm whether 0x00 marks sequence end or EF subroutine return"
    if category == "candidate_for_ff_variant_review":
        return "treat FF as variant/unreachable evidence until EarthBound reader behavior is proven"
    if category == "blocked_by_unpromoted_control":
        return "decode FD/FE/FF command behavior through SPC700 driver dispatch before exact duration promotion"
    if category == "needs_loop_or_fallthrough_semantics":
        return "inspect loop/fallthrough behavior and runtime timing before choosing public export mode"
    return "no sequence-duration action required"


def render_markdown(data: dict[str, Any]) -> str:
    summary = data["summary"]
    sections = [
        "# Audio Exact-Duration Triage",
        "",
        "Status: exact-duration release promotion is still pending, but sequence work is now sorted into actionable lanes.",
        "",
        "## Summary",
        "",
        f"- sequence packs triaged: `{summary['sequence_packs_triaged']}`",
        f"- category pack counts: `{summary['category_pack_counts']}`",
        f"- category track counts: `{summary['category_track_counts']}`",
        f"- command semantics status: `{summary['command_semantics_status']}`",
        f"- sequence promotion allowed: `{summary['sequence_promotion_allowed']}`",
        f"- release status: `{summary['release_status']}`",
        "",
    ]
    for category in [
        "candidate_for_zero_terminator_review",
        "candidate_for_ff_variant_review",
        "blocked_by_unpromoted_control",
        "needs_loop_or_fallthrough_semantics",
        "no_sequence_semantics_needed",
    ]:
        rows = []
        for pack in data["categories"].get(category, [])[:20]:
            rows.append(
                f"| `{pack['pack_id']}` | `{pack['range']}` | `{pack['track_ids']}` | "
                f"`{pack['export_class_counts']}` | {pack['ef_call_edges']} | {pack['terminators']} | "
                f"`{pack.get('terminator_counts_by_command', {})}` | `{pack['blocker_counts']}` | `{pack['command_semantic_status'].get('evidence_status')}` |"
            )
        sections.extend(
            [
                f"## {category}",
                "",
                "| Pack | ROM range | Tracks | Export classes | EF edges | Terminators | Terminator commands | Blockers | Semantic evidence |",
                "| ---: | --- | --- | --- | ---: | ---: | --- | --- | --- |",
                *rows,
                "",
            ]
        )
    sections.extend(
        [
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
    return "\n".join(sections)


def main() -> int:
    args = parse_args()
    export_plan = load_json(Path(args.export_plan))
    walk_frontier = load_json(Path(args.walk_frontier))
    command_semantics = load_json(Path(args.command_semantics))
    data = build_triage(export_plan, walk_frontier, command_semantics)
    output = Path(args.output)
    notes = Path(args.notes)
    output.parent.mkdir(parents=True, exist_ok=True)
    notes.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    notes.write_text(render_markdown(data), encoding="utf-8")
    print(
        "Built audio exact-duration triage: "
        f"{data['summary']['sequence_packs_triaged']} packs"
    )
    print(f"Wrote {output}")
    print(f"Wrote {notes}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
