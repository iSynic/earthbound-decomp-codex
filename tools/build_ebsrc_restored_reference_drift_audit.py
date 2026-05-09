#!/usr/bin/env python3
"""Audit restored herringway/ebsrc references against local semantic progress."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

from build_ebsrc_bank_map import build as build_ebsrc_bank_map


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_BANKS = ("C0", "C1", "C2", "C3", "C4", "EF")
DEFAULT_OUTPUT = ROOT / "manifests" / "ebsrc-restored-reference-drift-audit.json"
DEFAULT_NOTES = ROOT / "notes" / "ebsrc-restored-reference-drift-audit.md"
PLACEHOLDER_RE = re.compile(r"^(UNKNOWN|NULL|REDIRECT|DATA|CODE|UNUSED)_", re.IGNORECASE)
GENERIC_SOURCE_RE = re.compile(r"^[a-z0-9]{2}_[0-9a-f]{4}(?:_[0-9a-f]{4})?$", re.IGNORECASE)
PREFIXED_SOURCE_RE = re.compile(r"^[a-z0-9]{2}_[0-9a-f]{4}_(?P<name>.+)$", re.IGNORECASE)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bank", action="append", choices=DEFAULT_BANKS, help="Bank to audit. Defaults to priority banks.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Manifest JSON output.")
    parser.add_argument("--notes", default=str(DEFAULT_NOTES), help="Markdown note output.")
    return parser.parse_args()


def load_source_ranges(bank: str) -> list[dict[str, Any]]:
    path = ROOT / "build" / f"{bank.lower()}-build-candidate-ranges.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("ranges", [])


def parse_address(address: str | None) -> int | None:
    if not address:
        return None
    return int(address.split(":", 1)[1], 16)


def range_for_address(ranges: list[dict[str, Any]], address: str | None) -> dict[str, Any] | None:
    value = parse_address(address)
    if value is None:
        return None
    for record in ranges:
        start = parse_address(record.get("start"))
        end = parse_address(record.get("end"))
        if start is not None and end is not None and start <= value < end:
            return record
    return None


def name_from_label(label: str) -> str | None:
    parts = label.split(maxsplit=1)
    if len(parts) != 2:
        return None
    return parts[1].strip()


def name_from_source_path(path_text: str | None) -> str | None:
    if not path_text:
        return None
    stem = Path(path_text).stem
    if GENERIC_SOURCE_RE.fullmatch(stem):
        return None
    match = PREFIXED_SOURCE_RE.fullmatch(stem)
    if match:
        return match.group("name")
    return stem


def is_meaningful_name(name: str | None) -> bool:
    if not name:
        return False
    stripped = name.strip()
    if not stripped or PLACEHOLDER_RE.match(stripped):
        return False
    if GENERIC_SOURCE_RE.fullmatch(stripped):
        return False
    return True


def local_semantic_name(entry: dict[str, Any], source_range: dict[str, Any] | None) -> str | None:
    candidates = [entry.get("local_name")]
    if source_range:
        for label in source_range.get("labels", []):
            if label.startswith(str(entry.get("start", ""))):
                candidates.append(name_from_label(label))
        candidates.append(name_from_source_path(source_range.get("source_path")))
        candidates.append(source_range.get("subsystem"))
    for candidate in candidates:
        if is_meaningful_name(candidate):
            return str(candidate)
    return None


def is_unknown_reference(entry: dict[str, Any]) -> bool:
    include = str(entry.get("include_path", "")).lower()
    return include.startswith("unknown/") or "/unknown/" in include


def is_semantic_reference(entry: dict[str, Any]) -> bool:
    if is_unknown_reference(entry):
        return False
    symbol = str(entry.get("ebsrc_symbol") or "")
    return not PLACEHOLDER_RE.match(symbol) and str(entry.get("kind")) not in {"support", "unknown-code", "unknown-data"}


def classify_entry(entry: dict[str, Any], source_range: dict[str, Any] | None, name: str | None) -> str:
    if str(entry.get("kind")) == "support":
        return "reference_support_entry"
    if is_unknown_reference(entry):
        if source_range and name:
            return "local_source_classification_supersedes_ebsrc_unknown"
        if source_range:
            return "local_bytes_cover_ebsrc_unknown_name_polish_available"
        return "ebsrc_unknown_review_candidate"
    if is_semantic_reference(entry):
        if not entry.get("start"):
            return "ebsrc_semantic_unaddressed_reference"
        if source_range:
            return "ebsrc_semantic_name_corroborates_local_source"
        return "ebsrc_semantic_reference_review_candidate"
    if source_range:
        return "local_source_covers_reference_entry"
    return "reference_entry_review_candidate"


def audit_bank(bank: str) -> dict[str, Any]:
    source_ranges = load_source_ranges(bank)
    bank_map = build_ebsrc_bank_map(bank)
    records: list[dict[str, Any]] = []
    status_counts: Counter[str] = Counter()
    kind_counts: Counter[str] = Counter()
    unknown_total = 0
    semantic_total = 0
    for entry in bank_map.get("entries", []):
        source_range = range_for_address(source_ranges, entry.get("start"))
        name = local_semantic_name(entry, source_range)
        status = classify_entry(entry, source_range, name)
        status_counts[status] += 1
        kind_counts[str(entry.get("kind"))] += 1
        unknown_total += int(is_unknown_reference(entry))
        semantic_total += int(is_semantic_reference(entry))
        if status.endswith("review_candidate") or status in {
            "local_source_classification_supersedes_ebsrc_unknown",
            "local_bytes_cover_ebsrc_unknown_name_polish_available",
            "ebsrc_semantic_name_corroborates_local_source",
        }:
            records.append(
                {
                    "ordinal": entry.get("ordinal"),
                    "start": entry.get("start"),
                    "end": entry.get("end"),
                    "size": entry.get("size"),
                    "include_path": entry.get("include_path"),
                    "kind": entry.get("kind"),
                    "ebsrc_symbol": entry.get("ebsrc_symbol"),
                    "local_semantic_name": name,
                    "local_source_path": source_range.get("source_path") if source_range else entry.get("covered_by"),
                    "status": status,
                    "recommended_action": recommended_action(status),
                }
            )

    review_candidates = [record for record in records if str(record["status"]).endswith("review_candidate")]
    name_polish = [
        record
        for record in records
        if record["status"] == "local_bytes_cover_ebsrc_unknown_name_polish_available"
    ]
    surpassed = [
        record
        for record in records
        if record["status"] == "local_source_classification_supersedes_ebsrc_unknown"
    ]
    corroboration = [
        record
        for record in records
        if record["status"] == "ebsrc_semantic_name_corroborates_local_source"
    ]
    return {
        "bank": bank,
        "source_range_count": len(source_ranges),
        "ebsrc_summary": bank_map.get("summary", {}),
        "summary": {
            "reference_include_count": len(bank_map.get("entries", [])),
            "reference_unknown_entry_count": unknown_total,
            "reference_semantic_entry_count": semantic_total,
            "status_counts": dict(sorted(status_counts.items())),
            "kind_counts": dict(sorted(kind_counts.items())),
            "local_source_classification_supersedes_ebsrc_unknown_count": len(surpassed),
            "local_bytes_cover_unknown_name_polish_count": len(name_polish),
            "ebsrc_semantic_corroboration_count": len(corroboration),
            "review_candidate_count": len(review_candidates),
        },
        "surpassed_unknown_examples": surpassed[:20],
        "name_polish_candidates": name_polish[:20],
        "semantic_corroboration_examples": corroboration[:20],
        "review_candidates": review_candidates[:40],
    }


def recommended_action(status: str) -> str:
    if status == "local_source_classification_supersedes_ebsrc_unknown":
        return "keep local source classification/name; use ebsrc address/path only as corroboration"
    if status == "local_bytes_cover_ebsrc_unknown_name_polish_available":
        return "inspect local range and add a semantic label/comment only if evidence is already present"
    if status == "ebsrc_unknown_review_candidate":
        return "review restored ebsrc unknown against local source map before claiming semantic closure"
    if status == "ebsrc_semantic_name_corroborates_local_source":
        return "compare ebsrc name with local name; adopt only if exact-address and role-compatible"
    if status == "ebsrc_semantic_reference_review_candidate":
        return "check why ebsrc semantic include is not covered by local source range"
    return "review only if touched by current subsystem work"


def build_audit(banks: list[str]) -> dict[str, Any]:
    bank_records = [audit_bank(bank) for bank in banks]
    total_counts: Counter[str] = Counter()
    for record in bank_records:
        total_counts.update(record["summary"]["status_counts"])
    return {
        "schema": "earthbound-decomp.ebsrc-restored-reference-drift-audit.v1",
        "status": "restored_ebsrc_reference_audited_local_semantics_still_primary",
        "references": [
            "refs/ebsrc-main/ebsrc-main/README.md",
            "refs/ebsrc-main/ebsrc-main/src/bankconfig/US",
            "refs/ebsrc-main/ebsrc-main/include/symbols",
            "notes/project-status.md",
            "notes/readable-source-bank-closure.md",
            "notes/source-readiness-triage.md",
        ],
        "summary": {
            "bank_count": len(bank_records),
            "banks": banks,
            "status_counts": dict(sorted(total_counts.items())),
            "reference_unknown_entry_count": sum(record["summary"]["reference_unknown_entry_count"] for record in bank_records),
            "local_source_classification_supersedes_ebsrc_unknown_count": sum(
                record["summary"]["local_source_classification_supersedes_ebsrc_unknown_count"] for record in bank_records
            ),
            "local_bytes_cover_unknown_name_polish_count": sum(
                record["summary"]["local_bytes_cover_unknown_name_polish_count"] for record in bank_records
            ),
            "review_candidate_count": sum(record["summary"]["review_candidate_count"] for record in bank_records),
            "semantic_posture": "local source classifications, source names, and semantic manifests are ahead of restored ebsrc UNKNOWN coverage for audited priority banks",
        },
        "interpretation": [
            "Restored ebsrc is again a strong reference for include order, constants, labels, and historical naming.",
            "For audited priority banks, local readable-source closure and generated semantic contracts remain the source of truth.",
            "Do not bulk-import ebsrc UNKNOWN names; keep local semantic labels when they are more descriptive and byte-equivalent.",
            "Use ebsrc semantic names as corroboration only after exact-address and role-compatibility checks.",
        ],
        "banks": bank_records,
    }


def render_table_row(record: dict[str, Any]) -> str:
    summary = record["summary"]
    return "| `{bank}` | {includes} | {unknown} | {surpassed} | {polish} | {review} | {semantic} |".format(
        bank=record["bank"],
        includes=summary["reference_include_count"],
        unknown=summary["reference_unknown_entry_count"],
        surpassed=summary["local_source_classification_supersedes_ebsrc_unknown_count"],
        polish=summary["local_bytes_cover_unknown_name_polish_count"],
        review=summary["review_candidate_count"],
        semantic=summary["ebsrc_semantic_corroboration_count"],
    )


def render_records(records: list[dict[str, Any]], limit: int = 10) -> list[str]:
    rows = []
    for record in records[:limit]:
        rows.append(
            "| `{start}` | `{include}` | `{local}` | `{status}` | {action} |".format(
                start=record.get("start") or "",
                include=record.get("include_path") or "",
                local=record.get("local_semantic_name") or "",
                status=record.get("status"),
                action=record.get("recommended_action"),
            )
        )
    if len(records) > limit:
        rows.append(f"| ... | ... | ... | ... | {len(records) - limit} more |")
    return rows


def render_markdown(data: dict[str, Any]) -> str:
    summary = data["summary"]
    lines = [
        "# ebsrc Restored Reference Drift Audit",
        "",
        "Status: restored `refs/ebsrc-main` was rechecked against the current local semantic/source state.",
        "",
        "## Summary",
        "",
        f"- banks audited: `{summary['banks']}`",
        f"- restored ebsrc unknown entries: `{summary['reference_unknown_entry_count']}`",
        f"- ebsrc unknown entries superseded by local source classification/name: `{summary['local_source_classification_supersedes_ebsrc_unknown_count']}`",
        f"- locally covered ebsrc unknowns with possible name-polish follow-up: `{summary['local_bytes_cover_unknown_name_polish_count']}`",
        f"- reference review candidates: `{summary['review_candidate_count']}`",
        f"- semantic posture: `{summary['semantic_posture']}`",
        "",
        "## Interpretation",
        "",
        *[f"- {item}" for item in data["interpretation"]],
        "",
        "## Bank Summary",
        "",
        "| Bank | ebsrc includes | ebsrc unknowns | Local supersedes unknown | Name polish | Review candidates | ebsrc semantic corroboration |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        *[render_table_row(record) for record in data["banks"]],
    ]
    for bank in data["banks"]:
        lines.extend(
            [
                "",
                f"## Bank {bank['bank']}",
                "",
                f"- status counts: `{bank['summary']['status_counts']}`",
                f"- ebsrc map summary: `{bank['ebsrc_summary']}`",
                "",
                "### Best Local-Supersedes-ebsrc Examples",
                "",
                "| Start | ebsrc include | Local semantic name | Status | Action |",
                "| --- | --- | --- | --- | --- |",
                *render_records(bank["surpassed_unknown_examples"], 8),
                "",
                "### Name-Polish Candidates",
                "",
                "| Start | ebsrc include | Local semantic name | Status | Action |",
                "| --- | --- | --- | --- | --- |",
                *render_records(bank["name_polish_candidates"], 8),
                "",
                "### Review Candidates",
                "",
                "| Start | ebsrc include | Local semantic name | Status | Action |",
                "| --- | --- | --- | --- | --- |",
                *render_records(bank["review_candidates"], 8),
            ]
        )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    banks = args.bank or list(DEFAULT_BANKS)
    data = build_audit([bank.upper() for bank in banks])
    output = Path(args.output)
    notes = Path(args.notes)
    output.parent.mkdir(parents=True, exist_ok=True)
    notes.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    notes.write_text(render_markdown(data), encoding="utf-8")
    print(
        "Built ebsrc restored reference drift audit: "
        f"{data['summary']['reference_unknown_entry_count']} restored unknown entries, "
        f"{data['summary']['local_source_classification_supersedes_ebsrc_unknown_count']} locally superseded"
    )
    print(f"Wrote {output}")
    print(f"Wrote {notes}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
