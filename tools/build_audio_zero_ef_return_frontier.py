#!/usr/bin/env python3
"""Build a 0x00/EF end-vs-return frontier for N-SPC-family sequence evidence."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ZERO_REVIEW = ROOT / "manifests" / "audio-zero-terminator-review.json"
DEFAULT_WALK_FRONTIER = ROOT / "manifests" / "audio-sequence-walk-frontier.json"
DEFAULT_COMMAND_SEMANTICS = ROOT / "manifests" / "audio-sequence-command-semantics.json"
DEFAULT_DISPATCH_TRACE = ROOT / "manifests" / "audio-spc700-dispatch-trace-frontier.json"
DEFAULT_CONTROL_READER = ROOT / "manifests" / "audio-spc700-control-reader-frontier.json"
DEFAULT_OUTPUT = ROOT / "manifests" / "audio-zero-ef-return-frontier.json"
DEFAULT_NOTES = ROOT / "notes" / "audio-zero-ef-return-frontier.md"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build 0x00/EF return frontier.")
    parser.add_argument("--zero-review", default=str(DEFAULT_ZERO_REVIEW), help="0x00 terminator review JSON.")
    parser.add_argument("--walk-frontier", default=str(DEFAULT_WALK_FRONTIER), help="Sequence walk frontier JSON.")
    parser.add_argument("--command-semantics", default=str(DEFAULT_COMMAND_SEMANTICS), help="Command semantics JSON.")
    parser.add_argument("--dispatch-trace", default=str(DEFAULT_DISPATCH_TRACE), help="Runtime dispatch trace frontier JSON.")
    parser.add_argument("--control-reader", default=str(DEFAULT_CONTROL_READER), help="Control reader frontier JSON.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Manifest output JSON.")
    parser.add_argument("--notes", default=str(DEFAULT_NOTES), help="Markdown note output.")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def classify_zero_walk(walk: dict[str, Any]) -> str:
    if walk.get("blockers") or walk.get("truncations"):
        return "blocked_static_context"
    if walk.get("ef_call_edges"):
        return "end_vs_ef_return_ambiguous"
    return "phrase_or_song_end_candidate_pending_runtime_proof"


def zero_walk_records(pack_record: dict[str, Any]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for block in pack_record.get("blocks", []):
        for walk in block.get("root_walks_sample", []):
            zero_terms = [term for term in walk.get("terminators", []) if term.get("command") == "0x00"]
            if not zero_terms:
                continue
            ef_edges = walk.get("ef_call_edges", [])
            for terminator in zero_terms:
                records.append(
                    {
                        "block_index": block.get("block_index"),
                        "destination": block.get("destination"),
                        "payload_sha1": block.get("payload_sha1"),
                        "root_offset": walk.get("root_offset"),
                        "walked_until": walk.get("walked_until"),
                        "terminator_offset": terminator.get("offset"),
                        "segment_end": terminator.get("segment_end"),
                        "bytes_before_segment_end": int(terminator.get("bytes_before_segment_end", 0)),
                        "ef_call_edge_count_in_walk": len(ef_edges),
                        "ef_call_edges_sample": ef_edges[:4],
                        "static_context_class": classify_zero_walk(walk),
                        "semantic_status": terminator.get("semantic_status"),
                    }
                )
    return records


def trace_focus_for_pack(pack_class: str, export_class_counts: dict[str, Any]) -> str:
    if pack_class == "needs_ef_return_stack_model":
        return "trace_zero_reader_with_ef_stack_state"
    if "finite_or_transition_review_candidate" in export_class_counts:
        return "prove_zero_end_effect_then_review_finite_candidate"
    if "loop_or_held_candidate" in export_class_counts:
        return "prove_zero_effect_but_loop_points_remain_required"
    if "unknown_active_preview" in export_class_counts:
        return "prove_zero_effect_then_classify_active_preview"
    return "prove_zero_effect_for_policy_corroboration"


def runtime_probe_pc_plan(zero_trace: dict[str, Any], zero_reader_records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    records_by_pc = {str(record.get("pc")): record for record in zero_reader_records}
    counts = zero_trace.get("control_reader_pc_counts", {})
    plan = []
    for pc, count in sorted(counts.items(), key=lambda item: int(item[1]), reverse=True):
        reader = records_by_pc.get(str(pc), {})
        plan.append(
            {
                "pc": pc,
                "read_count": int(count),
                "driver_offset": reader.get("driver_offset"),
                "role": reader.get("role", "sequence_control_byte_reader_candidate"),
                "required_observation": "record command pointer, EF stack/return state, voice slot, and post-read branch/effect for 0x00",
            }
        )
    return plan


def build_frontier(
    zero_review: dict[str, Any],
    walk_frontier: dict[str, Any],
    command_semantics: dict[str, Any],
    dispatch_trace: dict[str, Any],
    control_reader: dict[str, Any],
) -> dict[str, Any]:
    priority_by_pack = {int(pack["pack_id"]): pack for pack in walk_frontier.get("priority_packs", [])}
    summary_by_pack = {int(pack["pack_id"]): pack for pack in walk_frontier.get("pack_summaries", [])}
    zero_semantics = command_semantics.get("commands", {}).get("0x00", {})
    ef_semantics = command_semantics.get("commands", {}).get("0xEF", {})
    zero_trace = dispatch_trace.get("control_command_semantics", {}).get("0x00", {})
    zero_reader_records = [
        record
        for record in control_reader.get("reader_pcs", [])
        if int(record.get("command_counts", {}).get("0x00", 0)) > 0
    ]

    pack_records = []
    class_counts: Counter[str] = Counter()
    trace_focus_counts: Counter[str] = Counter()
    track_action_counts: Counter[str] = Counter()
    candidate_total = 0
    ambiguous_total = 0
    static_end_total = 0
    for candidate in zero_review.get("candidates", []):
        pack_id = int(candidate["pack_id"])
        detail_source = priority_by_pack.get(pack_id, summary_by_pack.get(pack_id, {}))
        walks = zero_walk_records(detail_source)
        walk_class_counts = Counter(record["static_context_class"] for record in walks)
        candidate_total += len(walks)
        ambiguous_total += int(walk_class_counts.get("end_vs_ef_return_ambiguous", 0))
        static_end_total += int(walk_class_counts.get("phrase_or_song_end_candidate_pending_runtime_proof", 0))
        if walk_class_counts.get("end_vs_ef_return_ambiguous"):
            pack_class = "needs_ef_return_stack_model"
        elif walks:
            pack_class = "zero_phrase_end_candidate_runtime_pending"
        else:
            pack_class = "zero_candidates_outside_sample_detail"
        trace_focus = trace_focus_for_pack(pack_class, candidate["export_class_counts"])
        class_counts[pack_class] += 1
        trace_focus_counts[trace_focus] += 1
        for action in candidate.get("track_review_actions", []):
            track_action_counts[str(action.get("post_zero_proof_action"))] += 1
        pack_records.append(
            {
                "pack_id": pack_id,
                "range": candidate["range"],
                "track_count": candidate["track_count"],
                "track_ids": candidate["track_ids"],
                "export_class_counts": candidate["export_class_counts"],
                "ef_call_edges": candidate["ef_call_edges"],
                "zero_terminator_candidates": candidate["zero_terminator_candidates"],
                "pack_context_class": pack_class,
                "trace_focus": trace_focus,
                "zero_walk_context_class_counts": dict(sorted(walk_class_counts.items())),
                "track_review_actions": candidate.get("track_review_actions", []),
                "sampled_zero_walks": walks[:16],
                "eligible_next_export_action": "keep_public_exact_promotion_blocked",
            }
        )

    return {
        "schema": "earthbound-decomp.audio-zero-ef-return-frontier.v1",
        "status": "zero_end_vs_ef_return_frontier_ready_runtime_proof_pending",
        "references": [
            "https://sneslab.net/wiki/N-SPC_Engine",
            "manifests/audio-zero-terminator-review.json",
            "manifests/audio-sequence-walk-frontier.json",
            "manifests/audio-sequence-command-semantics.json",
            "manifests/audio-spc700-dispatch-trace-frontier.json",
            "manifests/audio-spc700-control-reader-frontier.json",
        ],
        "summary": {
            "candidate_pack_count": len(pack_records),
            "sampled_zero_walk_count": candidate_total,
            "sampled_zero_walk_class_counts": {
                "end_vs_ef_return_ambiguous": ambiguous_total,
                "phrase_or_song_end_candidate_pending_runtime_proof": static_end_total,
            },
            "pack_context_class_counts": dict(sorted(class_counts.items())),
            "trace_focus_pack_counts": dict(sorted(trace_focus_counts.items())),
            "post_zero_proof_action_track_counts": dict(sorted(track_action_counts.items())),
            "zero_runtime_read_count": int(zero_trace.get("sequence_control_read_count", 0)),
            "zero_runtime_reader_pc_count": len(zero_reader_records),
            "sequence_promotion_allowed": False,
            "semantic_status": "static_zero_context_classified_runtime_zero_reader_proof_pending",
        },
        "command_semantics": {
            "zero": {
                "semantic_status": zero_semantics.get("semantic_status", "missing_command_semantics"),
                "exact_duration_promotion_allowed": bool(zero_semantics.get("exact_duration_promotion_allowed")),
            },
            "ef": {
                "semantic_status": ef_semantics.get("semantic_status", "missing_command_semantics"),
                "exact_duration_promotion_allowed": bool(ef_semantics.get("exact_duration_promotion_allowed")),
            },
        },
        "runtime_zero_evidence": {
            "dispatch_trace_status": zero_trace.get("semantic_status", "missing_zero_trace_status"),
            "sequence_control_read_count": int(zero_trace.get("sequence_control_read_count", 0)),
            "execution_fetch_control_read_count": int(zero_trace.get("execution_fetch_control_read_count", 0)),
            "control_reader_pc_counts": zero_trace.get("control_reader_pc_counts", {}),
            "reader_pc_records": zero_reader_records,
        },
        "runtime_probe_plan": {
            "reader_pc_plan": runtime_probe_pc_plan(zero_trace, zero_reader_records),
            "first_pack_focus": [
                {
                    "pack_id": pack["pack_id"],
                    "track_ids": pack["track_ids"],
                    "trace_focus": pack["trace_focus"],
                    "pack_context_class": pack["pack_context_class"],
                }
                for pack in pack_records[:5]
            ],
        },
        "packs": pack_records,
        "promotion_policy": [
            "Static 0x00 context can prioritize work, but cannot decide exact end-vs-return semantics alone.",
            "A 0x00 on a path with an EF call edge remains ambiguous until the EF return stack model is proven.",
            "A 0x00 on a path without an EF call edge is an end candidate, but still needs EarthBound runtime/disassembly proof before public exact export.",
            "No record in this frontier directly promotes sequence exact-duration exports.",
        ],
        "findings": [
            "The new frontier identifies which 0x00 candidates need an EF return stack model first.",
            "Runtime 0x00 reader evidence is currently taken from the dispatch/control-reader manifests; older traces may report zero reads until regenerated with the widened harness contract.",
            "Pack-level export promotion remains blocked even for phrase-end-looking candidates.",
        ],
        "next_work": [
            "regenerate targeted ares traces for the 0x00 review packs using the widened zero-control trace contract",
            "decode reader PCs that observe 0x00 and record end-vs-return state transitions",
            "promote only packs whose 0x00 end proof agrees with EF context and track policy",
        ],
    }


def render_markdown(data: dict[str, Any]) -> str:
    summary = data["summary"]
    rows = [
        "| `{pack_id}` | `{tracks}` | `{classes}` | {zero} | {ef} | `{context}` | `{focus}` | `{walks}` |".format(
            pack_id=pack["pack_id"],
            tracks=pack["track_ids"],
            classes=pack["export_class_counts"],
            zero=pack["zero_terminator_candidates"],
            ef=pack["ef_call_edges"],
            context=pack["pack_context_class"],
            focus=pack["trace_focus"],
            walks=pack["zero_walk_context_class_counts"],
        )
        for pack in data["packs"]
    ]
    pc_rows = [
        "| `{pc}` | {count} | `{offset}` | {observation} |".format(
            pc=record["pc"],
            count=record["read_count"],
            offset=record.get("driver_offset"),
            observation=record["required_observation"],
        )
        for record in data.get("runtime_probe_plan", {}).get("reader_pc_plan", [])[:8]
    ]
    return "\n".join(
        [
            "# Audio 0x00/EF Return Frontier",
            "",
            "Status: 0x00 candidates are grouped by EF context; runtime proof is still required.",
            "",
            "## Summary",
            "",
            f"- candidate packs: `{summary['candidate_pack_count']}`",
            f"- sampled 0x00 walks: `{summary['sampled_zero_walk_count']}`",
            f"- sampled 0x00 walk classes: `{summary['sampled_zero_walk_class_counts']}`",
            f"- pack context classes: `{summary['pack_context_class_counts']}`",
            f"- trace focus packs: `{summary['trace_focus_pack_counts']}`",
            f"- post-zero-proof track actions: `{summary['post_zero_proof_action_track_counts']}`",
            f"- runtime 0x00 reads: `{summary['zero_runtime_read_count']}`",
            f"- runtime 0x00 reader PCs: `{summary['zero_runtime_reader_pc_count']}`",
            f"- sequence promotion allowed: `{summary['sequence_promotion_allowed']}`",
            "",
            "## Runtime Probe Plan",
            "",
            "| Reader PC | 0x00 reads | Driver offset | Required observation |",
            "| --- | ---: | --- | --- |",
            *pc_rows,
            "",
            "## Packs",
            "",
            "| Pack | Tracks | Export classes | 0x00 candidates | EF edges | Context | Trace focus | Sampled walk classes |",
            "| ---: | --- | --- | ---: | ---: | --- | --- | --- |",
            *rows,
            "",
            "## Promotion Policy",
            "",
            *[f"- {item}" for item in data["promotion_policy"]],
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
    data = build_frontier(
        load_json(Path(args.zero_review)),
        load_json(Path(args.walk_frontier)),
        load_json(Path(args.command_semantics)),
        load_json(Path(args.dispatch_trace)),
        load_json(Path(args.control_reader)),
    )
    output = Path(args.output)
    notes = Path(args.notes)
    output.parent.mkdir(parents=True, exist_ok=True)
    notes.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    notes.write_text(render_markdown(data), encoding="utf-8")
    print(
        "Built audio 0x00/EF return frontier: "
        f"{data['summary']['candidate_pack_count']} packs, "
        f"{data['summary']['sampled_zero_walk_count']} sampled zero walks"
    )
    print(f"Wrote {output}")
    print(f"Wrote {notes}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
