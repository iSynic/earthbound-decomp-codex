#!/usr/bin/env python3
"""Build a focused review of N-SPC-family 0x00 terminator candidates."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_TRIAGE = ROOT / "manifests" / "audio-exact-duration-triage.json"
DEFAULT_WALK_FRONTIER = ROOT / "manifests" / "audio-sequence-walk-frontier.json"
DEFAULT_COMMAND_SEMANTICS = ROOT / "manifests" / "audio-sequence-command-semantics.json"
DEFAULT_OUTPUT = ROOT / "manifests" / "audio-zero-terminator-review.json"
DEFAULT_NOTES = ROOT / "notes" / "audio-zero-terminator-review.md"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build 0x00 terminator candidate review.")
    parser.add_argument("--triage", default=str(DEFAULT_TRIAGE), help="Exact-duration triage JSON.")
    parser.add_argument("--walk-frontier", default=str(DEFAULT_WALK_FRONTIER), help="Sequence walk frontier JSON.")
    parser.add_argument("--command-semantics", default=str(DEFAULT_COMMAND_SEMANTICS), help="Promoted command semantics JSON.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Review manifest output JSON.")
    parser.add_argument("--notes", default=str(DEFAULT_NOTES), help="Review markdown output.")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def zero_walk_detail(pack_record: dict[str, Any]) -> dict[str, Any]:
    root_count = 0
    zero_terminating_roots = 0
    fallthrough_roots = 0
    blocked_roots = 0
    zero_terminators = []
    tail_counts: Counter[str] = Counter()

    for block in pack_record.get("blocks", []):
        for walk in block.get("root_walks_sample", []):
            root_count += 1
            status = str(walk.get("status"))
            if status == "falls_through_segment":
                fallthrough_roots += 1
            elif status == "blocked":
                blocked_roots += 1
            for terminator in walk.get("terminators", []):
                if terminator.get("command") != "0x00":
                    continue
                zero_terminating_roots += 1
                tail = int(terminator.get("bytes_before_segment_end", 0))
                tail_counts[str(tail)] += 1
                zero_terminators.append(
                    {
                        "block_index": block.get("block_index"),
                        "destination": block.get("destination"),
                        "root_offset": walk.get("root_offset"),
                        "terminator_offset": terminator.get("offset"),
                        "segment_end": terminator.get("segment_end"),
                        "bytes_before_segment_end": tail,
                        "semantic_status": terminator.get("semantic_status"),
                    }
                )

    tail_values = [int(item["bytes_before_segment_end"]) for item in zero_terminators]
    return {
        "sampled_root_count": root_count,
        "sampled_zero_terminating_roots": zero_terminating_roots,
        "sampled_fallthrough_roots": fallthrough_roots,
        "sampled_blocked_roots": blocked_roots,
        "sampled_zero_terminators": zero_terminators,
        "zero_terminator_tail_byte_counts": dict(sorted(tail_counts.items(), key=lambda item: int(item[0]))),
        "zero_at_segment_end_count": int(tail_counts.get("0", 0)),
        "zero_with_trailing_bytes_count": sum(count for tail, count in tail_counts.items() if int(tail) > 0),
        "minimum_tail_bytes": min(tail_values) if tail_values else None,
        "maximum_tail_bytes": max(tail_values) if tail_values else None,
    }


def post_proof_track_action(track: dict[str, Any]) -> str:
    export_class = str(track.get("export_class"))
    if export_class == "finite_trim_candidate":
        return "corroborate_existing_pcm_trim"
    if export_class == "finite_or_transition_review_candidate":
        return "review_observed_silence_as_finite_or_transition"
    if export_class == "loop_or_held_candidate":
        return "decode_loop_points_before_exact_export"
    if export_class == "unknown_active_preview":
        return "classify_active_preview_before_exact_export"
    return "keep_current_export_policy"


def track_review_records(tracks: list[dict[str, Any]], *, ef_call_edges: int, zero_promotion_allowed: bool) -> list[dict[str, Any]]:
    records = []
    blockers = ["zero_runtime_effect_proof"]
    if ef_call_edges > 0:
        blockers.append("ef_return_stack_model")
    for track in tracks:
        action = post_proof_track_action(track)
        records.append(
            {
                "track_id": int(track["track_id"]),
                "track_name": track.get("track_name"),
                "export_class": track.get("export_class"),
                "recommended_mode": track.get("recommended_mode"),
                "duration_seconds": track.get("duration_seconds"),
                "pre_promotion_blockers": [] if zero_promotion_allowed else blockers,
                "post_zero_proof_action": action,
                "public_exact_export_after_zero_proof": action == "corroborate_existing_pcm_trim",
            }
        )
    return records


def priority_rank(record: dict[str, Any]) -> int:
    classes = record.get("export_class_counts", {})
    if record["ef_call_edges"] > 0 and "finite_or_transition_review_candidate" in classes:
        return 5
    if record["ef_call_edges"] > 0:
        return 4
    if "finite_trim_candidate" in classes:
        return 4
    if "finite_or_transition_review_candidate" in classes:
        return 3
    if "loop_or_held_candidate" in classes:
        return 2
    return 1


def promotion_class(pack: dict[str, Any], zero_semantics: dict[str, Any]) -> str:
    if not zero_semantics.get("exact_duration_promotion_allowed"):
        return "zero_runtime_effect_pending"
    export_classes = pack.get("export_class_counts", {})
    if "loop_or_held_candidate" in export_classes:
        return "zero_present_but_loop_metadata_still_needed"
    if "finite_or_transition_review_candidate" in export_classes:
        return "zero_can_promote_after_track_review"
    if "finite_trim_candidate" in export_classes:
        return "zero_can_confirm_existing_pcm_trim_candidate"
    return "zero_can_promote_after_effect_proof"


def build_review(
    triage: dict[str, Any],
    walk_frontier: dict[str, Any],
    command_semantics: dict[str, Any],
) -> dict[str, Any]:
    triage_records = triage.get("categories", {}).get("candidate_for_zero_terminator_review", [])
    walk_by_pack = {int(pack["pack_id"]): pack for pack in walk_frontier.get("priority_packs", [])}
    summary_by_pack = {int(pack["pack_id"]): pack for pack in walk_frontier.get("pack_summaries", [])}
    zero_semantics = command_semantics.get("commands", {}).get("0x00", {})
    records = []
    promotion_counts: Counter[str] = Counter()
    track_counts: Counter[str] = Counter()
    action_track_counts: Counter[str] = Counter()
    blocker_track_counts: Counter[str] = Counter()

    for triage_pack in triage_records:
        pack_id = int(triage_pack["pack_id"])
        detail_source = walk_by_pack.get(pack_id, summary_by_pack.get(pack_id, {}))
        record = {
            "pack_id": pack_id,
            "range": triage_pack["range"],
            "track_count": int(triage_pack["track_count"]),
            "track_ids": triage_pack["track_ids"],
            "tracks": triage_pack.get("tracks", []),
            "export_class_counts": triage_pack["export_class_counts"],
            "walk_status_counts": triage_pack["walk_status_counts"],
            "ef_call_edges": int(triage_pack["ef_call_edges"]),
            "zero_terminator_candidates": int(triage_pack.get("terminator_counts_by_command", {}).get("0x00", 0)),
            "blocker_counts": triage_pack["blocker_counts"],
            "zero_semantic_status": zero_semantics.get("semantic_status", "missing_command_semantics"),
            "zero_exact_duration_promotion_allowed": bool(zero_semantics.get("exact_duration_promotion_allowed")),
            "eligible_next_export_action": zero_semantics.get(
                "eligible_next_export_action",
                "keep_public_exact_promotion_blocked",
            ),
            "review_detail": zero_walk_detail(detail_source),
        }
        record["track_review_actions"] = track_review_records(
            record["tracks"],
            ef_call_edges=record["ef_call_edges"],
            zero_promotion_allowed=record["zero_exact_duration_promotion_allowed"],
        )
        record["promotion_class"] = promotion_class(record, zero_semantics)
        record["priority_rank"] = priority_rank(record)
        records.append(record)
        promotion_counts[record["promotion_class"]] += 1
        track_counts[record["promotion_class"]] += record["track_count"]
        for track_action in record["track_review_actions"]:
            action_track_counts[str(track_action["post_zero_proof_action"])] += 1
            for blocker in track_action.get("pre_promotion_blockers", []):
                blocker_track_counts[str(blocker)] += 1

    records.sort(
        key=lambda item: (
            item["priority_rank"],
            item["track_count"],
            item["zero_terminator_candidates"],
            item["ef_call_edges"],
        ),
        reverse=True,
    )
    return {
        "schema": "earthbound-decomp.audio-zero-terminator-review.v1",
        "status": "zero_terminator_candidates_grouped_effect_proof_pending",
        "references": [
            "https://sneslab.net/wiki/N-SPC_Engine",
            "manifests/audio-exact-duration-triage.json",
            "manifests/audio-sequence-walk-frontier.json",
            "manifests/audio-sequence-command-semantics.json",
        ],
        "summary": {
            "candidate_pack_count": len(records),
            "candidate_track_count": sum(record["track_count"] for record in records),
            "promotion_class_pack_counts": dict(sorted(promotion_counts.items())),
            "promotion_class_track_counts": dict(sorted(track_counts.items())),
            "post_zero_proof_action_track_counts": dict(sorted(action_track_counts.items())),
            "pre_promotion_blocker_track_counts": dict(sorted(blocker_track_counts.items())),
            "semantic_status": "zero_terminators_need_end_vs_return_proof",
            "zero_semantic_status": zero_semantics.get("semantic_status", "missing_command_semantics"),
            "zero_exact_duration_promotion_allowed": bool(zero_semantics.get("exact_duration_promotion_allowed")),
        },
        "command_semantics": {
            "schema": command_semantics.get("schema"),
            "status": command_semantics.get("status"),
            "zero": zero_semantics,
        },
        "promotion_rules": [
            "0x00 is the N-SPC-family phrase termination/end-of-subroutine candidate, not automatic public exact-duration proof.",
            "EF context must distinguish subroutine return from true phrase/song end.",
            "Finite trim candidates may use 0x00 as corroboration only after EarthBound-local effect proof.",
            "Loop/held candidates remain preview exports until loop entry/exit semantics are decoded.",
        ],
        "candidates": records,
        "findings": [
            "The focused 0x00 lane replaces the former FF-centered terminator review for N-SPC-family evidence.",
            "Candidate records include offsets, counts, hashes inherited from the walk frontier, and derived statuses only.",
            "No candidate is promoted for public sequence exact-duration export until local EarthBound effect proof is added.",
        ],
        "next_work": [
            "trace or disassemble EarthBound 0x00 handling and record end-vs-EF-return behavior",
            "join 0x00 observations with EF call-stack context for finite candidate packs",
            "feed confirmed finite/return semantics back into audio-export-plan duration_semantics",
        ],
    }


def render_markdown(data: dict[str, Any]) -> str:
    summary = data["summary"]
    rows = [
        "| `{pack_id}` | `{range}` | `{track_ids}` | `{classes}` | {zero} | {ef} | `{promotion}` |".format(
            pack_id=record["pack_id"],
            range=record["range"],
            track_ids=record["track_ids"],
            classes=record["export_class_counts"],
            zero=record["zero_terminator_candidates"],
            ef=record["ef_call_edges"],
            promotion=record["promotion_class"],
        )
        for record in data["candidates"]
    ]
    action_rows = [
        "| `{action}` | {count} |".format(action=action, count=count)
        for action, count in summary.get("post_zero_proof_action_track_counts", {}).items()
    ]
    blocker_rows = [
        "| `{blocker}` | {count} |".format(blocker=blocker, count=count)
        for blocker, count in summary.get("pre_promotion_blocker_track_counts", {}).items()
    ]
    return "\n".join(
        [
            "# Audio 0x00 Terminator Review",
            "",
            "Status: N-SPC-family 0x00 terminator candidates grouped; EarthBound end-vs-return proof is still pending.",
            "",
            "## Summary",
            "",
            f"- candidate packs: `{summary['candidate_pack_count']}`",
            f"- candidate tracks: `{summary['candidate_track_count']}`",
            f"- promotion classes: `{summary['promotion_class_pack_counts']}`",
            f"- post-zero-proof track actions: `{summary['post_zero_proof_action_track_counts']}`",
            f"- pre-promotion blockers by track: `{summary['pre_promotion_blocker_track_counts']}`",
            f"- zero semantic status: `{summary['zero_semantic_status']}`",
            f"- zero exact-duration promotion allowed: `{summary['zero_exact_duration_promotion_allowed']}`",
            "",
            "## Track Action Triage",
            "",
            "| Action | Tracks |",
            "| --- | ---: |",
            *action_rows,
            "",
            "| Blocker | Tracks |",
            "| --- | ---: |",
            *blocker_rows,
            "",
            "## Candidates",
            "",
            "| Pack | ROM range | Tracks | Export classes | 0x00 candidates | EF edges | Promotion class |",
            "| ---: | --- | --- | --- | ---: | ---: | --- |",
            *rows,
            "",
            "## Promotion Rules",
            "",
            *[f"- {rule}" for rule in data["promotion_rules"]],
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
    data = build_review(
        load_json(Path(args.triage)),
        load_json(Path(args.walk_frontier)),
        load_json(Path(args.command_semantics)),
    )
    output = Path(args.output)
    notes = Path(args.notes)
    output.parent.mkdir(parents=True, exist_ok=True)
    notes.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    notes.write_text(render_markdown(data), encoding="utf-8")
    print(
        "Built audio 0x00 terminator review: "
        f"{data['summary']['candidate_pack_count']} packs, "
        f"{data['summary']['candidate_track_count']} tracks"
    )
    print(f"Wrote {output}")
    print(f"Wrote {notes}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
