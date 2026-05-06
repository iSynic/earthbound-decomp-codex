#!/usr/bin/env python3
"""Validate the 0x00/EF end-vs-return frontier."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MANIFEST = ROOT / "manifests" / "audio-zero-ef-return-frontier.json"
ALLOWED_PACK_CLASSES = {
    "needs_ef_return_stack_model",
    "zero_phrase_end_candidate_runtime_pending",
    "zero_candidates_outside_sample_detail",
}
ALLOWED_WALK_CLASSES = {
    "blocked_static_context",
    "end_vs_ef_return_ambiguous",
    "phrase_or_song_end_candidate_pending_runtime_proof",
}
ALLOWED_TRACE_FOCUS = {
    "prove_zero_effect_but_loop_points_remain_required",
    "prove_zero_effect_for_policy_corroboration",
    "prove_zero_effect_then_classify_active_preview",
    "prove_zero_end_effect_then_review_finite_candidate",
    "trace_zero_reader_with_ef_stack_state",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate audio 0x00/EF return frontier.")
    parser.add_argument("manifest", nargs="?", default=str(DEFAULT_MANIFEST))
    return parser.parse_args()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def validate(data: dict[str, Any]) -> None:
    require(data.get("schema") == "earthbound-decomp.audio-zero-ef-return-frontier.v1", "unexpected schema")
    summary = data.get("summary", {})
    packs = data.get("packs", [])
    require(summary.get("candidate_pack_count") == len(packs), "pack count mismatch")
    require(summary.get("candidate_pack_count", 0) > 0, "expected candidate packs")
    require(summary.get("sequence_promotion_allowed") is False, "frontier must not directly promote sequence exact duration")
    require("https://sneslab.net/wiki/N-SPC_Engine" in data.get("references", []), "missing N-SPC reference")
    require(data.get("runtime_zero_evidence"), "missing runtime zero evidence")
    require(data.get("promotion_policy"), "missing promotion policy")
    pack_classes: Counter[str] = Counter()
    trace_focus_counts: Counter[str] = Counter()
    action_counts: Counter[str] = Counter()
    sampled_walk_count = 0
    sampled_walk_classes: Counter[str] = Counter()
    for pack in packs:
        require("pack_id" in pack, "pack missing id")
        require(pack.get("zero_terminator_candidates", 0) > 0, f"pack {pack.get('pack_id')}: expected zero candidates")
        pack_class = str(pack.get("pack_context_class"))
        require(pack_class in ALLOWED_PACK_CLASSES, f"pack {pack.get('pack_id')}: unexpected pack class {pack_class}")
        pack_classes[pack_class] += 1
        trace_focus = str(pack.get("trace_focus"))
        require(trace_focus in ALLOWED_TRACE_FOCUS, f"pack {pack.get('pack_id')}: unexpected trace focus {trace_focus}")
        trace_focus_counts[trace_focus] += 1
        require("track_review_actions" in pack, f"pack {pack.get('pack_id')}: missing track review actions")
        for action in pack.get("track_review_actions", []):
            action_counts[str(action.get("post_zero_proof_action"))] += 1
        for walk in pack.get("sampled_zero_walks", []):
            sampled_walk_count += 1
            walk_class = str(walk.get("static_context_class"))
            require(walk_class in ALLOWED_WALK_CLASSES, f"pack {pack.get('pack_id')}: unexpected walk class {walk_class}")
            require(walk.get("terminator_offset"), f"pack {pack.get('pack_id')}: zero walk missing terminator offset")
            require(walk.get("payload_sha1"), f"pack {pack.get('pack_id')}: zero walk missing payload hash")
            sampled_walk_classes[walk_class] += 1
    require(dict(sorted(pack_classes.items())) == summary.get("pack_context_class_counts"), "pack class counts mismatch")
    require(dict(sorted(trace_focus_counts.items())) == summary.get("trace_focus_pack_counts"), "trace focus counts mismatch")
    require(
        dict(sorted(action_counts.items())) == summary.get("post_zero_proof_action_track_counts"),
        "track action counts mismatch",
    )
    require(sampled_walk_count == summary.get("sampled_zero_walk_count"), "sampled zero walk count mismatch")
    expected_walk_counts = dict(summary.get("sampled_zero_walk_class_counts", {}))
    for key, count in sampled_walk_classes.items():
        require(expected_walk_counts.get(key) == count, f"sampled walk class count mismatch for {key}")
    command_semantics = data.get("command_semantics", {})
    require(command_semantics.get("zero", {}).get("semantic_status"), "missing zero semantic status")
    require(command_semantics.get("ef", {}).get("semantic_status"), "missing EF semantic status")
    probe_plan = data.get("runtime_probe_plan", {})
    require(probe_plan.get("reader_pc_plan"), "missing runtime reader PC probe plan")
    for record in probe_plan.get("reader_pc_plan", []):
        require(record.get("pc"), "probe plan record missing PC")
        require(int(record.get("read_count", 0)) > 0, f"probe plan {record.get('pc')}: missing read count")
        require(record.get("required_observation"), f"probe plan {record.get('pc')}: missing required observation")
    require(data.get("findings"), "missing findings")
    require(data.get("next_work"), "missing next work")


def main() -> int:
    args = parse_args()
    data = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    validate(data)
    print(
        "Audio 0x00/EF return frontier validation OK: "
        f"{data['summary']['candidate_pack_count']} packs, "
        f"{data['summary']['sampled_zero_walk_count']} sampled zero walks"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
