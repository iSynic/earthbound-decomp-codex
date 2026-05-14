#!/usr/bin/env python3
"""Validate the generated Mesen SRM anchor catalog."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MANIFEST = ROOT / "manifests" / "mesen-srm-anchor-catalog.json"
SCHEMA = "earthbound-decomp.mesen-srm-anchor-catalog.v1"
STATUS = "catalog_generated_local_srm_bytes_ignored"
SRM_SIZE = 8192


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", nargs="?", default=str(DEFAULT_MANIFEST))
    return parser.parse_args()


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    require(data.get("schema") == SCHEMA, f"bad schema {data.get('schema')}", errors)
    require(data.get("status") == STATUS, f"bad status {data.get('status')}", errors)
    anchors = data.get("anchors")
    require(isinstance(anchors, list), "anchors must be a list", errors)
    if isinstance(anchors, list):
        require(len(anchors) == 36, f"expected 36 anchors, found {len(anchors)}", errors)
        ids: set[str] = set()
        hashes: set[str] = set()
        for index, row in enumerate(anchors):
            prefix = f"anchor {index}"
            anchor_id = str(row.get("anchor_id", ""))
            require(anchor_id and anchor_id not in ids, f"{prefix}: duplicate/missing anchor_id", errors)
            ids.add(anchor_id)
            require(str(row.get("archive_name", "")).endswith(".zip"), f"{prefix}: archive_name not zip", errors)
            require(int(row.get("srm_size", -1)) == SRM_SIZE, f"{prefix}: bad SRM size", errors)
            srm_hash = str(row.get("srm_sha256", ""))
            require(len(srm_hash) == 64 and srm_hash not in hashes, f"{prefix}: bad/duplicate SRM hash", errors)
            hashes.add(srm_hash)
            require(str(row.get("srm_entry", "")).lower().endswith(".srm"), f"{prefix}: missing srm entry", errors)
            require(row.get("evidence_role") == "vanilla_srm_anchor", f"{prefix}: bad evidence role", errors)
            require(row.get("source_promotion_allowed") is False, f"{prefix}: source promotion must be blocked", errors)
    summary = data.get("summary", {})
    if isinstance(anchors, list):
        require(summary.get("archive_count") == len(anchors), "summary archive_count mismatch", errors)
        require(summary.get("valid_srm_count") == len(anchors), "summary valid_srm_count mismatch", errors)
    require(summary.get("source_promotion_allowed") is False, "summary source promotion must be blocked", errors)
    return errors


def main() -> int:
    args = parse_args()
    data = load_json(Path(args.manifest))
    errors = validate(data)
    if errors:
        print("Mesen SRM anchor catalog validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print(f"Mesen SRM anchor catalog validation OK: {data['summary']['archive_count']} anchors")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
