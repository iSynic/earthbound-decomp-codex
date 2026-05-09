#!/usr/bin/env python3
"""Validate the restored ebsrc reference drift audit."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MANIFEST = ROOT / "manifests" / "ebsrc-restored-reference-drift-audit.json"
REQUIRED_BANKS = {"C0", "C1", "C2", "C3", "C4", "EF"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", nargs="?", default=str(DEFAULT_MANIFEST))
    return parser.parse_args()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def validate(data: dict[str, Any]) -> None:
    require(data.get("schema") == "earthbound-decomp.ebsrc-restored-reference-drift-audit.v1", "unexpected schema")
    require(data.get("status") == "restored_ebsrc_reference_audited_local_semantics_still_primary", "unexpected status")
    references = set(data.get("references", []))
    require("refs/ebsrc-main/ebsrc-main/README.md" in references, "missing ebsrc README reference")
    require("notes/readable-source-bank-closure.md" in references, "missing readable closure reference")
    banks = data.get("banks", [])
    summary = data.get("summary", {})
    require(set(summary.get("banks", [])) == REQUIRED_BANKS, "bank coverage mismatch")
    require(int(summary.get("bank_count", 0)) == len(banks), "bank count mismatch")
    require(len(banks) == len(REQUIRED_BANKS), "expected six priority banks")
    require(int(summary.get("reference_unknown_entry_count", 0)) > 0, "expected restored ebsrc unknown entries")
    require(
        int(summary.get("local_source_classification_supersedes_ebsrc_unknown_count", 0)) > int(summary.get("review_candidate_count", 0)),
        "local source classification count should dominate review candidates",
    )
    counted_unknown = 0
    counted_surpassed = 0
    counted_polish = 0
    counted_review = 0
    for bank in banks:
        require(bank.get("bank") in REQUIRED_BANKS, f"unexpected bank {bank.get('bank')}")
        bank_summary = bank.get("summary", {})
        require(int(bank_summary.get("reference_include_count", 0)) > 0, f"{bank.get('bank')}: missing include count")
        require("status_counts" in bank_summary, f"{bank.get('bank')}: missing status counts")
        counted_unknown += int(bank_summary.get("reference_unknown_entry_count", 0))
        counted_surpassed += int(bank_summary.get("local_source_classification_supersedes_ebsrc_unknown_count", 0))
        counted_polish += int(bank_summary.get("local_bytes_cover_unknown_name_polish_count", 0))
        counted_review += int(bank_summary.get("review_candidate_count", 0))
        require("ebsrc_summary" in bank, f"{bank.get('bank')}: missing ebsrc map summary")
        for key in ("surpassed_unknown_examples", "name_polish_candidates", "review_candidates"):
            require(key in bank, f"{bank.get('bank')}: missing {key}")
            for record in bank.get(key, []):
                require(record.get("include_path"), f"{bank.get('bank')}: record missing include path")
                require(record.get("status"), f"{bank.get('bank')}: record missing status")
                require(record.get("recommended_action"), f"{bank.get('bank')}: record missing recommended action")
    require(counted_unknown == summary.get("reference_unknown_entry_count"), "unknown count mismatch")
    require(counted_surpassed == summary.get("local_source_classification_supersedes_ebsrc_unknown_count"), "surpass count mismatch")
    require(counted_polish == summary.get("local_bytes_cover_unknown_name_polish_count"), "polish count mismatch")
    require(counted_review == summary.get("review_candidate_count"), "review count mismatch")
    require(data.get("interpretation"), "missing interpretation")


def main() -> int:
    args = parse_args()
    data = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    validate(data)
    print(
        "ebsrc restored reference drift audit validation OK: "
        f"{data['summary']['reference_unknown_entry_count']} unknown entries, "
        f"{data['summary']['local_source_classification_supersedes_ebsrc_unknown_count']} locally superseded"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
