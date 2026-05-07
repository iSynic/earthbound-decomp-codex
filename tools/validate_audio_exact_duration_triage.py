#!/usr/bin/env python3
"""Validate the audio exact-duration triage report."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MANIFEST = ROOT / "manifests" / "audio-exact-duration-triage.json"
EXPECTED_CATEGORIES = {
    "candidate_for_zero_terminator_review",
    "candidate_for_ff_variant_review",
    "blocked_by_unpromoted_control",
    "needs_loop_or_fallthrough_semantics",
    "no_sequence_semantics_needed",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate audio exact-duration triage.")
    parser.add_argument("manifest", nargs="?", default=str(DEFAULT_MANIFEST))
    return parser.parse_args()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def validate(data: dict[str, Any]) -> None:
    require(data.get("schema") == "earthbound-decomp.audio-exact-duration-triage.v1", "unexpected schema")
    summary = data.get("summary", {})
    categories = data.get("categories", {})
    lane_diagnostics = data.get("lane_diagnostics", {})
    command_semantics = data.get("command_semantics", {})
    require(summary.get("sequence_packs_triaged", 0) > 0, "expected triaged sequence packs")
    require(
        command_semantics.get("schema") == "earthbound-decomp.audio-sequence-command-semantics.v1",
        "missing command semantics reference",
    )
    require("sequence_promotion_allowed" in summary, "summary missing sequence promotion flag")
    require(set(categories).issubset(EXPECTED_CATEGORIES), "unexpected triage category")
    require(set(lane_diagnostics).issubset(EXPECTED_CATEGORIES), "unexpected triage diagnostic category")
    counted = sum(len(records) for records in categories.values())
    require(counted == summary.get("sequence_packs_triaged"), "triage category count mismatch")
    require("candidate_for_zero_terminator_review" in categories, "expected 0x00 terminator review lane")
    require("candidate_for_zero_terminator_review" in lane_diagnostics, "expected 0x00 lane diagnostics")
    diagnostic_pack_count = sum(int(diagnostic.get("pack_count", 0)) for diagnostic in lane_diagnostics.values())
    require(diagnostic_pack_count == counted, "triage diagnostic pack count mismatch")
    for records in categories.values():
        for pack in records:
            require("pack_id" in pack, "pack missing id")
            require("tracks" in pack, f"pack {pack.get('pack_id')} missing tracks")
            require("command_semantic_status" in pack, f"pack {pack.get('pack_id')} missing command semantic status")
            status = pack.get("command_semantic_status", {})
            require("evidence_status" in status, f"pack {pack.get('pack_id')} missing evidence status")
            require("exact_duration_promotion_allowed" in status, f"pack {pack.get('pack_id')} missing promotion flag")
            if "blocked_command_statuses" in status:
                require("blocked_command_source_roles" in status, f"pack {pack.get('pack_id')} missing blocked command source roles")
                require("blocked_command_effect_proof_statuses" in status, f"pack {pack.get('pack_id')} missing blocked command effect statuses")
                require("blocked_command_source_effect_statuses" in status, f"pack {pack.get('pack_id')} missing blocked command source effect statuses")
                require(
                    "blocked_command_source_effect_capture_requirement_counts" in status,
                    f"pack {pack.get('pack_id')} missing blocked command source capture counts",
                )
            else:
                require("source_role" in status, f"pack {pack.get('pack_id')} missing source role")
                require("effect_proof_status" in status, f"pack {pack.get('pack_id')} missing effect proof status")
                require("source_effect_status" in status, f"pack {pack.get('pack_id')} missing source effect status")
                require(
                    "source_effect_capture_requirement_count" in status,
                    f"pack {pack.get('pack_id')} missing source effect capture count",
                )
            require("recommended_next_step" in pack, f"pack {pack.get('pack_id')} missing next step")
            require("terminator_counts_by_command" in pack, f"pack {pack.get('pack_id')} missing terminator command counts")


def main() -> int:
    args = parse_args()
    data = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    validate(data)
    print(
        "Audio exact-duration triage validation OK: "
        f"{data['summary']['sequence_packs_triaged']} packs"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
