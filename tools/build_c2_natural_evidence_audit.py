#!/usr/bin/env python3
"""Build a C2 natural evidence audit from sanitized Mesen probe metadata."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MATRIX = ROOT / "manifests" / "c2-battle-trace-manual-probe-matrix.json"
DEFAULT_RESULTS = ROOT / "manifests" / "c2-battle-trace-oracle-results-summary.json"
DEFAULT_OUTPUT = ROOT / "manifests" / "c2-natural-evidence-audit.json"
DEFAULT_NOTE = ROOT / "notes" / "c2-natural-evidence-audit.md"

STATUSES = {
    "natural_proof_candidate",
    "natural_capture_fields_missing",
    "runtime_steered_needed",
    "fixture_only_navigation",
    "not_yet_observed",
}

NATURAL_PROBE_GROUP_MARKERS = (
    "battle-fixtures-1-7",
    "battle-fixtures-8",
    "battle-fixtures-replaced-slots",
    "collapse-save-state-probes-neutral",
    "collapse-save-state-probes-neutral-long",
    "natural-resource-scout",
)
STEERED_MARKERS = (
    "fixture-rom-tests",
    "resource-wram-patched",
    "resource-natural-scripted-entry",
    "resource-startup-only-scripted-entry",
    "resource-unseeded-scripted-entry",
    "resource-dynamic-selected-pp-scripted-entry",
    "resource-targeted-selected-pp-scripted-entry",
    "resource-action-steered-no-wram",
)

MECHANISMS: list[dict[str, Any]] = [
    {
        "id": "physical_damage",
        "title": "Physical damage",
        "oracle": "c2_8125_damage_abi_boundary",
        "natural_keywords": ("before-damage", "jeff-hp-rolling", "command-menu", "target-select"),
        "required_hits": ("C2:8125", "C2:7EAF"),
        "success_status": "natural_proof_candidate",
        "next_action": "Review existing C2:8125 fields and keep source contract proof-grade.",
    },
    {
        "id": "psi_damage",
        "title": "PSI damage",
        "oracle": "c2_8125_damage_abi_boundary",
        "natural_keywords": ("paula-freeze", "psi-menu"),
        "required_hits": ("C2:8125",),
        "success_status": "natural_proof_candidate",
        "next_action": "Use Paula Freeze save-backed traces for PSI amount and text-join review.",
    },
    {
        "id": "hp_healing",
        "title": "HP healing",
        "oracle": "c2_8125_damage_abi_boundary",
        "natural_keywords": ("ness-healing", "large-pizza"),
        "required_hits": ("C2:8125",),
        "success_status": "natural_proof_candidate",
        "next_action": "Review healing amount fields before adding any new saves.",
    },
    {
        "id": "hp_roller_collapse",
        "title": "HP roller and collapse",
        "oracle": "hp_roller_collapse_boundary",
        "natural_keywords": ("hp-rolling", "paula-freeze", "earthbound-usa-7", "earthbound-usa-8"),
        "required_hits": ("C2:8125", "C2:BB18"),
        "success_status": "natural_proof_candidate",
        "next_action": "Keep collapse/death tails split from HP rolling unless C2:7550/C2:77CA are present.",
    },
    {
        "id": "status_apply_success",
        "title": "Status apply success",
        "oracle": "c2_724a_affliction_writer_matrix",
        "natural_keywords": ("dread-scorpion", "poison"),
        "required_hits": ("C2:724A",),
        "success_status": "natural_capture_fields_missing",
        "next_action": "Rerun Dread Scorpion poison with C2:724A post-return capture before promotion.",
    },
    {
        "id": "item_effect",
        "title": "Battle item effect",
        "oracle": "c2_8125_damage_abi_boundary",
        "natural_keywords": ("large-pizza", "goods-menu"),
        "required_hits": ("C2:8125",),
        "success_status": "natural_proof_candidate",
        "next_action": "Use Large Pizza natural save to join item action, HP amount, and text payload.",
    },
    {
        "id": "multi_target_heal",
        "title": "Multi-target heal",
        "oracle": "hp_roller_collapse_boundary",
        "natural_keywords": ("large-pizza",),
        "required_hits": ("C2:BB18",),
        "success_status": "natural_capture_fields_missing",
        "next_action": "Add per-party-row HP before/after capture for Large Pizza.",
    },
    {
        "id": "target_action_staging",
        "title": "Target/action staging",
        "oracle": "c1_c2_target_action_staging",
        "natural_keywords": ("target-select", "goods-menu", "psi-menu", "command-menu"),
        "required_hits": ("C2:BAC5",),
        "success_status": "natural_capture_fields_missing",
        "next_action": "Upgrade target/action staging with export-field capture; do not require new saves first.",
    },
    {
        "id": "pp_transfer",
        "title": "PP transfer",
        "oracle": "resource_amount_pair_magnet_vs_pp_loss",
        "natural_keywords": ("natural-magnet", "save"),
        "required_hits": ("C2:9F5E", "C2:721D"),
        "success_status": "runtime_steered_needed",
        "next_action": "Use SRM anchors or runtime steering to create a nonzero-PP PSI Magnet setup.",
    },
    {
        "id": "pp_loss_only",
        "title": "PP loss-only",
        "oracle": "resource_amount_pair_magnet_vs_pp_loss",
        "natural_keywords": ("natural-pp-reduction", "guardian-general"),
        "required_hits": ("C2:8E42", "C2:721D"),
        "success_status": "runtime_steered_needed",
        "next_action": "Use Guardian General/late-game SRM anchor with explicit evidence tier labeling.",
    },
    {
        "id": "flash_status_gate",
        "title": "Flash/status gate",
        "oracle": "psi_flash_and_status_gate_family",
        "fallback_oracle": "c2_724a_affliction_writer_matrix",
        "natural_keywords": ("flash", "numb"),
        "required_hits": ("C2:9917", "C2:724A"),
        "success_status": "fixture_only_navigation",
        "next_action": "Find or steer a natural C2:98A1 gate run; current C2:9917 route is forced-fixture only.",
    },
    {
        "id": "battle_text_amount_substitution",
        "title": "Battle text amount substitution",
        "oracle": "battle_text_payload_join",
        "fallback_oracle": "c2_8125_damage_abi_boundary",
        "natural_keywords": ("large-pizza", "paula-freeze", "ness-healing", "before-damage"),
        "required_hits": ("C1:DC1C",),
        "success_status": "natural_capture_fields_missing",
        "next_action": "Capture C1/EF text pointer and amount payload joins from existing natural saves.",
    },
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--matrix", default=str(DEFAULT_MATRIX))
    parser.add_argument("--results", default=str(DEFAULT_RESULTS))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--note", default=str(DEFAULT_NOTE))
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def is_natural_record(record: dict[str, Any]) -> bool:
    group = str(record.get("probe_group", ""))
    return any(marker in group for marker in NATURAL_PROBE_GROUP_MARKERS) and not any(
        marker in group for marker in STEERED_MARKERS
    )


def record_hits(record: dict[str, Any]) -> set[str]:
    return {str(item) for item in record.get("observed_addresses", [])}


def keyword_match(record: dict[str, Any], keywords: tuple[str, ...]) -> bool:
    haystack = f"{record.get('fixture_id', '')} {record.get('probe_group', '')}".lower()
    return any(keyword.lower() in haystack for keyword in keywords)


def has_required_hits(record: dict[str, Any], required_hits: tuple[str, ...]) -> bool:
    hits = record_hits(record)
    return set(required_hits).issubset(hits)


def sanitize_record(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "fixture_id": record.get("fixture_id"),
        "probe_group": record.get("probe_group"),
        "oracle_id": record.get("oracle_id"),
        "minimum_hits_satisfied": bool(record.get("minimum_hits_satisfied")),
        "observed_addresses": record.get("observed_addresses", []),
        "post_call_snapshot_counts": record.get("post_call_snapshot_counts", {}),
        "first_frame": record.get("first_frame"),
        "last_frame": record.get("last_frame"),
        "save_state": record.get("save_state", {}),
        "raw_trace_summary": record.get("raw_trace_summary"),
    }


def result_by_oracle(results: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(row.get("oracle")): row for row in results.get("results", [])}


def audit_mechanism(
    mechanism: dict[str, Any],
    records: list[dict[str, Any]],
    results_index: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    oracle = str(mechanism["oracle"])
    fallback_oracle = str(mechanism.get("fallback_oracle") or oracle)
    keywords = tuple(str(item) for item in mechanism.get("natural_keywords", ()))
    required_hits = tuple(str(item) for item in mechanism.get("required_hits", ()))
    candidates = [
        record
        for record in records
        if record.get("oracle_id") in {oracle, fallback_oracle}
        and is_natural_record(record)
        and keyword_match(record, keywords)
        and (not required_hits or has_required_hits(record, required_hits))
    ]
    partial_natural = [
        record
        for record in records
        if record.get("oracle_id") in {oracle, fallback_oracle}
        and is_natural_record(record)
        and keyword_match(record, keywords)
        and record.get("observed_addresses")
    ]
    steered = [
        record
        for record in records
        if record.get("oracle_id") in {oracle, fallback_oracle}
        and not is_natural_record(record)
        and (keyword_match(record, keywords) or has_required_hits(record, required_hits))
    ]
    if candidates:
        status = str(mechanism["success_status"])
    elif partial_natural:
        status = "natural_capture_fields_missing"
    elif steered:
        status = str(mechanism["success_status"])
        if status == "natural_proof_candidate":
            status = "fixture_only_navigation"
    else:
        status = "not_yet_observed"
    if status not in STATUSES:
        raise ValueError(f"bad mechanism status for {mechanism['id']}: {status}")
    result = results_index.get(oracle, {})
    return {
        "mechanism_id": mechanism["id"],
        "title": mechanism["title"],
        "status": status,
        "oracle_id": oracle,
        "fallback_oracle_id": fallback_oracle if fallback_oracle != oracle else None,
        "required_hits": list(required_hits),
        "natural_candidate_count": len(candidates),
        "natural_partial_count": len(partial_natural),
        "steered_candidate_count": len(steered),
        "reviewed_result_classification": result.get("classification"),
        "reviewed_result_status": result.get("status"),
        "next_action": mechanism["next_action"],
        "best_natural_records": [sanitize_record(record) for record in candidates[:5]],
        "partial_natural_records": [sanitize_record(record) for record in partial_natural[:5]],
        "steered_records": [sanitize_record(record) for record in steered[:5]],
    }


def summarize(audits: list[dict[str, Any]]) -> dict[str, Any]:
    counts = Counter(str(row["status"]) for row in audits)
    return {
        "mechanism_count": len(audits),
        "status_counts": dict(sorted(counts.items())),
        "natural_proof_candidate_count": counts.get("natural_proof_candidate", 0),
        "natural_capture_fields_missing_count": counts.get("natural_capture_fields_missing", 0),
        "runtime_steered_needed_count": counts.get("runtime_steered_needed", 0),
        "fixture_only_navigation_count": counts.get("fixture_only_navigation", 0),
        "not_yet_observed_count": counts.get("not_yet_observed", 0),
        "source_promotion_allowed": False,
        "behavior_change_allowed": False,
    }


def render_note(data: dict[str, Any]) -> str:
    lines = [
        "# C2 Natural Evidence Audit",
        "",
        "Generated by `tools/build_c2_natural_evidence_audit.py` from sanitized",
        "Mesen probe metadata. This note classifies existing evidence only; it does",
        "not promote source semantics by itself.",
        "",
        "## Summary",
        "",
    ]
    summary = data["summary"]
    lines.extend(
        [
            f"- mechanisms audited: `{summary['mechanism_count']}`",
            f"- natural proof candidates: `{summary['natural_proof_candidate_count']}`",
            f"- natural captures needing fields/review: `{summary['natural_capture_fields_missing_count']}`",
            f"- runtime-steered setups needed: `{summary['runtime_steered_needed_count']}`",
            f"- fixture-only navigation lanes: `{summary['fixture_only_navigation_count']}`",
            f"- not yet observed: `{summary['not_yet_observed_count']}`",
            "- source promotion allowed: `False`",
            "- behavior change allowed: `False`",
            "",
            "## Mechanisms",
            "",
            "| Mechanism | Status | Natural candidates | Partial natural | Steered | Next action |",
            "| --- | --- | ---: | ---: | ---: | --- |",
        ]
    )
    for row in data["mechanisms"]:
        lines.append(
            "| `{mechanism_id}` | `{status}` | `{natural}` | `{partial}` | `{steered}` | {next_action} |".format(
                mechanism_id=row["mechanism_id"],
                status=row["status"],
                natural=row["natural_candidate_count"],
                partial=row["natural_partial_count"],
                steered=row["steered_candidate_count"],
                next_action=str(row["next_action"]).replace("|", "\\|"),
            )
        )
    lines.extend(
        [
            "",
            "## Evidence Policy",
            "",
            "- Vanilla `.mss` traces are natural evidence when no WRAM/ROM steering is used.",
            "- SRM anchors plus automated input remain natural until RAM or ROM steering is applied.",
            "- Runtime RAM edits are setup evidence, not natural proof.",
            "- Fixture ROM/Game Genie/table patches are navigation or routine-mechanics evidence unless separately confirmed by vanilla traces.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    matrix = load_json(Path(args.matrix))
    results = load_json(Path(args.results))
    records = [row for row in matrix.get("records", []) if isinstance(row, dict)]
    audits = [audit_mechanism(mechanism, records, result_by_oracle(results)) for mechanism in MECHANISMS]
    data = {
        "schema": "earthbound-decomp.c2-natural-evidence-audit.v1",
        "status": "audit_generated_no_source_promotion",
        "generated_by": "tools/build_c2_natural_evidence_audit.py",
        "source_inputs": [
            "manifests/c2-battle-trace-manual-probe-matrix.json",
            "manifests/c2-battle-trace-oracle-results-summary.json",
        ],
        "evidence_policy": {
            "vanilla_save_state": "natural",
            "vanilla_srm_plus_input": "natural_until_ram_or_rom_steering",
            "runtime_ram_edit": "runtime_steered_needed",
            "fixture_rom_or_game_genie": "fixture_only_navigation",
        },
        "summary": summarize(audits),
        "mechanisms": audits,
    }
    write_json(Path(args.output), data)
    write_text(Path(args.note), render_note(data))
    print(f"Wrote {args.output}")
    print(f"Wrote {args.note}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
