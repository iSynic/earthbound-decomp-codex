#!/usr/bin/env python3
"""Validate restored-ebsrc knowns integration candidate output."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MANIFEST = ROOT / "manifests" / "ebsrc-knowns-integration-candidates.json"
REQUIRED_BANKS = {"C0", "C1", "C2", "C3", "C4", "EF"}
REQUIRED_CLASSES = {
    "adopt_exact_symbol",
    "adopt_constant_or_field_name",
    "adopt_table_name",
    "macro_vocab_reference",
    "keep_local_supersedes",
    "blocked_unaddressed_or_payload_only",
    "manual_review",
}
REQUIRED_COMMUNITY_STATUSES = {
    "source_alias_ready",
    "source_alias_integrated",
    "docs_crosswalk_only",
    "local_primary_stronger",
    "blocked_conflict_or_unproven",
}
REQUIRED_REFERENCES = {
    "refs/ebsrc-main/ebsrc-main/src/bankconfig/US",
    "refs/ebsrc-main/ebsrc-main/include/constants",
    "refs/ebsrc-main/ebsrc-main/include/structs.asm",
    "manifests/ebsrc-restored-reference-drift-audit.json",
    "manifests/audio-spc700-sounddriver-source-ingest.json",
    "notes/source-readiness-triage.md",
    "notes/project-status.md",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", nargs="?", default=str(DEFAULT_MANIFEST))
    return parser.parse_args()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def validate(data: dict[str, Any]) -> None:
    require(data.get("schema") == "earthbound-decomp.ebsrc-knowns-integration-candidates.v1", "unexpected schema")
    require(data.get("status") == "restored_ebsrc_knowns_classified_for_curated_integration", "unexpected status")
    references = set(data.get("references", []))
    missing_refs = REQUIRED_REFERENCES - references
    require(not missing_refs, f"missing references: {sorted(missing_refs)}")

    summary = data.get("summary", {})
    require(set(summary.get("banks", [])) == REQUIRED_BANKS, "bank coverage mismatch")
    candidates = data.get("candidates", [])
    require(int(summary.get("candidate_count", 0)) == len(candidates), "candidate count mismatch")
    require(len(candidates) > 0, "expected candidates")

    class_counts = summary.get("class_counts", {})
    require(set(class_counts) == REQUIRED_CLASSES, "candidate class coverage mismatch")
    community_counts = summary.get("community_alignment_counts", {})
    require(set(community_counts) == REQUIRED_COMMUNITY_STATUSES, "community alignment status coverage mismatch")
    require(sum(int(count) for count in community_counts.values()) == len(candidates), "community status count mismatch")
    require(int(class_counts.get("keep_local_supersedes", 0)) > 0, "expected local-supersedes candidates")
    require(int(class_counts.get("adopt_constant_or_field_name", 0)) > 0, "expected constant/field candidates")
    require(int(class_counts.get("macro_vocab_reference", 0)) > 0, "expected macro vocabulary candidates")
    require(int(class_counts.get("blocked_unaddressed_or_payload_only", 0)) > 0, "expected blocked reference-only candidates")
    require("do_not_rename_when_local_name_is_more_specific" == summary.get("source_rename_default"), "unsafe rename default")
    require(
        int(summary.get("source_integrated_ebsrc_symbol_count", 0)) > 0,
        "expected at least one integrated ebsrc symbol",
    )
    require(int(community_counts.get("source_alias_integrated", 0)) > 0, "expected integrated ebsrc aliases")
    require(int(community_counts.get("source_alias_ready", 0)) == 0, "source alias backlog must be applied or explained")
    require(int(community_counts.get("docs_crosswalk_only", 0)) > 0, "expected docs-only community crosswalk entries")
    require(int(community_counts.get("blocked_conflict_or_unproven", 0)) > 0, "expected blocked/unproven community entries")

    counted: dict[str, int] = {name: 0 for name in REQUIRED_CLASSES}
    community_counted: dict[str, int] = {name: 0 for name in REQUIRED_COMMUNITY_STATUSES}
    banks_seen: set[str] = set()
    source_kinds: set[str] = set()
    lanes: set[str] = set()
    for index, record in enumerate(candidates):
        candidate_class = record.get("candidate_class")
        require(candidate_class in REQUIRED_CLASSES, f"candidate {index}: unknown class {candidate_class!r}")
        counted[str(candidate_class)] += 1
        community_status = record.get("community_alignment_status")
        require(community_status in REQUIRED_COMMUNITY_STATUSES, f"candidate {index}: unknown community status {community_status!r}")
        community_counted[str(community_status)] += 1
        require(record.get("community_alignment_confidence"), f"candidate {index}: missing community alignment confidence")
        require(record.get("lane"), f"candidate {index}: missing lane")
        require(record.get("source_kind"), f"candidate {index}: missing source_kind")
        require(record.get("reason"), f"candidate {index}: missing reason")
        require(record.get("recommended_action"), f"candidate {index}: missing recommended_action")
        if record.get("bank"):
            banks_seen.add(str(record["bank"]))
        source_kinds.add(str(record["source_kind"]))
        lanes.add(str(record["lane"]))
        if candidate_class in {"adopt_exact_symbol", "adopt_table_name"}:
            require(record.get("start") and record.get("local_source_path"), f"candidate {index}: adoption target lacks local source coverage")
            require(record.get("ebsrc_symbol"), f"candidate {index}: adoption target lacks ebsrc symbol/name")
        if candidate_class == "keep_local_supersedes" and record.get("source_kind") == "bank-include":
            require(record.get("local_name") or record.get("local_source_path"), f"candidate {index}: local-supersedes bank record lacks local evidence")

    require(banks_seen == REQUIRED_BANKS, f"missing bank records: {sorted(REQUIRED_BANKS - banks_seen)}")
    require("constant-enum" in source_kinds, "missing constant/enum records")
    require("struct-field" in source_kinds, "missing struct field records")
    require("macro" in source_kinds, "missing macro records")
    require("source-backed-vcmd" in source_kinds, "missing source-backed audio VCMD records")
    require("audio-spc700" in lanes, "missing audio lane")
    require("macro-vocabulary" in lanes, "missing macro lane")

    for name, count in counted.items():
        require(int(class_counts.get(name, -1)) == count, f"class count mismatch for {name}")
    for name, count in community_counted.items():
        require(int(community_counts.get(name, -1)) == count, f"community status count mismatch for {name}")
    require(data.get("sample_candidates_by_class"), "missing class samples")
    require(data.get("source_integrated_ebsrc_symbol_examples"), "missing integrated ebsrc symbol examples")
    require(data.get("community_alignment_statuses"), "missing community alignment status descriptions")


def main() -> int:
    args = parse_args()
    data = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    validate(data)
    print(
        "ebsrc knowns integration candidates validation OK: "
        f"{data['summary']['candidate_count']} candidates"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
