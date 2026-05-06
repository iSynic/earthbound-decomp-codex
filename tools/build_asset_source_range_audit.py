from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import extract_assets
from build_asset_output_recipe_contracts import FAMILIES, compact_counts, family_for_bank, infer_bank, rel


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MANIFEST_DIR = ROOT / "asset-manifests"
DEFAULT_JSON_OUT = ROOT / "build" / "asset-source-range-audit.json"
DEFAULT_MARKDOWN_OUT = ROOT / "notes" / "asset-source-range-audit.md"
BANK_SIZE = 0x10000


def manifest_paths(manifest_dir: Path) -> list[Path]:
    return sorted(manifest_dir.glob("*.json"))


def load_manifest(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def parse_source_range(source: dict[str, Any]) -> tuple[int, int, int]:
    range_text = source.get("range")
    if not isinstance(range_text, str):
        raise ValueError("source.range must be a string")
    return extract_assets.parse_bank_range(range_text)


def hex_range(bank: str, start: int, end: int) -> str:
    return f"{bank}:{start:04X}..{bank}:{end:04X}"


def build_report(manifest_dir: Path) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    bank_reports: list[dict[str, Any]] = []
    errors: list[str] = []

    for manifest_path in manifest_paths(manifest_dir):
        manifest = load_manifest(manifest_path)
        bank = infer_bank(manifest_path, manifest)
        bank_number = int(bank, 16)
        family = family_for_bank(bank)
        assets = manifest.get("assets", [])
        if not isinstance(assets, list):
            raise ValueError(f"{manifest_path}: assets must be a list")

        bank_records: list[dict[str, Any]] = []
        category_counts: Counter[str] = Counter()
        category_bytes: Counter[str] = Counter()
        compression_counts: Counter[str] = Counter()
        output_kind_counts: Counter[str] = Counter()
        bank_errors: list[str] = []

        for asset in assets:
            if not isinstance(asset, dict):
                continue
            asset_id = str(asset.get("id"))
            category = str(asset.get("category", "unknown"))
            source = asset.get("source")
            source_errors: list[str] = []
            if not isinstance(source, dict):
                source_errors.append("source must be an object")
                parsed_bank = bank_number
                start = 0
                end = 0
                range_text = ""
                source_bytes = 0
                compression = None
            else:
                range_text = str(source.get("range", ""))
                source_bytes = int(source.get("bytes", 0) or 0)
                compression = source.get("compression")
                if source.get("type") != "rom-range":
                    source_errors.append("source.type must be 'rom-range'")
                try:
                    parsed_bank, start, end = parse_source_range(source)
                except ValueError as exc:
                    source_errors.append(str(exc))
                    parsed_bank = bank_number
                    start = 0
                    end = 0
                if parsed_bank != bank_number:
                    source_errors.append(
                        f"source bank {parsed_bank:02X} must match manifest bank {bank}"
                    )
                span_bytes = end - start
                if span_bytes <= 0:
                    source_errors.append("source range must contain at least one byte")
                if source_bytes != span_bytes:
                    source_errors.append(
                        f"source.bytes {source_bytes} must match range span {span_bytes}"
                    )

            outputs = asset.get("outputs", [])
            if not isinstance(outputs, list):
                outputs = []
            output_kinds = [
                str(output.get("kind"))
                for output in outputs
                if isinstance(output, dict) and isinstance(output.get("kind"), str)
            ]
            output_kind_counts.update(output_kinds)
            category_counts[category] += 1
            category_bytes[category] += source_bytes
            compression_counts[str(compression or "(none)")] += 1

            record = {
                "asset_id": asset_id,
                "title": asset.get("title"),
                "manifest_path": rel(manifest_path),
                "bank": bank,
                "family": family["id"],
                "category": category,
                "range": range_text,
                "start": start,
                "end": end,
                "bytes": source_bytes,
                "compression": compression,
                "output_kinds": output_kinds,
                "errors": source_errors,
            }
            records.append(record)
            bank_records.append(record)
            for error in source_errors:
                bank_errors.append(f"{asset_id}: {error}")

        sorted_records = sorted(bank_records, key=lambda record: (int(record["start"]), int(record["end"])))
        holes: list[dict[str, Any]] = []
        overlaps: list[dict[str, Any]] = []
        cursor = 0
        previous: dict[str, Any] | None = None
        covered_bytes = 0
        for record in sorted_records:
            start = int(record["start"])
            end = int(record["end"])
            if start > cursor:
                holes.append({"range": hex_range(bank, cursor, start), "bytes": start - cursor})
            if start < cursor and previous is not None:
                overlaps.append(
                    {
                        "range": hex_range(bank, start, min(cursor, end)),
                        "bytes": max(0, min(cursor, end) - start),
                        "previous_asset_id": previous["asset_id"],
                        "asset_id": record["asset_id"],
                    }
                )
            if end > cursor:
                covered_bytes += end - max(start, cursor)
                cursor = end
                previous = record
        if cursor < BANK_SIZE:
            holes.append({"range": hex_range(bank, cursor, BANK_SIZE), "bytes": BANK_SIZE - cursor})

        bank_summary = manifest.get("bank_summary", {})
        if not isinstance(bank_summary, dict):
            bank_summary = {}
        expected_source_bytes = sum(int(record["bytes"]) for record in bank_records)
        if holes:
            bank_errors.append(f"{len(holes)} source coverage hole(s)")
        if overlaps:
            bank_errors.append(f"{len(overlaps)} source range overlap(s)")
        if covered_bytes != BANK_SIZE:
            bank_errors.append(f"covered bytes {covered_bytes} must equal bank size {BANK_SIZE}")
        if expected_source_bytes != BANK_SIZE:
            bank_errors.append(
                f"source byte sum {expected_source_bytes} must equal bank size {BANK_SIZE}"
            )

        bank_reports.append(
            {
                "bank": bank,
                "family": family["id"],
                "manifest_path": rel(manifest_path),
                "asset_count": len(bank_records),
                "source_bytes": expected_source_bytes,
                "covered_bytes": covered_bytes,
                "hole_count": len(holes),
                "hole_bytes": sum(int(hole["bytes"]) for hole in holes),
                "overlap_count": len(overlaps),
                "overlap_bytes": sum(int(overlap["bytes"]) for overlap in overlaps),
                "category_counts": dict(sorted(category_counts.items())),
                "category_bytes": dict(sorted(category_bytes.items())),
                "compression_counts": dict(sorted(compression_counts.items())),
                "output_kind_counts": dict(sorted(output_kind_counts.items())),
                "bank_summary": {
                    "binary_asset_bytes": int(bank_summary.get("binary_asset_bytes", 0) or 0),
                    "table_bytes": int(bank_summary.get("table_bytes", 0) or 0),
                    "coverage_gap_bytes": int(bank_summary.get("coverage_gap_bytes", 0) or 0),
                },
                "holes": holes[:20],
                "overlaps": overlaps[:20],
                "errors": bank_errors,
                "status": "ok" if not bank_errors else "invalid",
            }
        )
        for error in bank_errors:
            errors.append(f"{rel(manifest_path)}: {error}")

    family_counts: dict[str, Counter[str]] = defaultdict(Counter)
    family_bytes: Counter[str] = Counter()
    family_gap_bytes: Counter[str] = Counter()
    family_hole_bytes: Counter[str] = Counter()
    family_overlap_bytes: Counter[str] = Counter()
    category_counts: Counter[str] = Counter()
    category_bytes: Counter[str] = Counter()
    compression_counts: Counter[str] = Counter()

    for record in records:
        family = str(record["family"])
        category = str(record["category"])
        family_counts[family][category] += 1
        family_bytes[family] += int(record["bytes"])
        category_counts[category] += 1
        category_bytes[category] += int(record["bytes"])
        compression_counts[str(record["compression"] or "(none)")] += 1
    for bank_report in bank_reports:
        family = str(bank_report["family"])
        family_gap_bytes[family] += int(bank_report["bank_summary"]["coverage_gap_bytes"])
        family_hole_bytes[family] += int(bank_report["hole_bytes"])
        family_overlap_bytes[family] += int(bank_report["overlap_bytes"])

    families = []
    for family in FAMILIES:
        family_id = family["id"]
        if family_counts[family_id] or family_bytes[family_id]:
            families.append(
                {
                    "id": family_id,
                    "label": family["label"],
                    "banks": family["banks"],
                    "asset_count": sum(family_counts[family_id].values()),
                    "source_bytes": family_bytes[family_id],
                    "coverage_gap_bytes": family_gap_bytes[family_id],
                    "hole_bytes": family_hole_bytes[family_id],
                    "overlap_bytes": family_overlap_bytes[family_id],
                    "category_counts": dict(sorted(family_counts[family_id].items())),
                }
            )

    invalid_records = [record for record in records if record["errors"]]
    invalid_banks = [bank_report for bank_report in bank_reports if bank_report["status"] != "ok"]

    return {
        "schema": "earthbound-decomp.asset-source-range-audit.v1",
        "inputs": {
            "manifest_dir": rel(manifest_dir),
            "range_parser": "tools/extract_assets.py:parse_bank_range",
        },
        "source_policy": {
            "contains_rom_derived_outputs": False,
            "validates_manifest_source_ranges_only": True,
            "range_semantics": "half-open bank ranges: BB:START..BB:END",
        },
        "totals": {
            "manifests": len(bank_reports),
            "assets": len(records),
            "source_bytes": sum(int(record["bytes"]) for record in records),
            "covered_bytes": sum(int(bank_report["covered_bytes"]) for bank_report in bank_reports),
            "expected_bank_bytes": len(bank_reports) * BANK_SIZE,
            "coverage_holes": sum(int(bank_report["hole_count"]) for bank_report in bank_reports),
            "coverage_hole_bytes": sum(int(bank_report["hole_bytes"]) for bank_report in bank_reports),
            "overlaps": sum(int(bank_report["overlap_count"]) for bank_report in bank_reports),
            "overlap_bytes": sum(int(bank_report["overlap_bytes"]) for bank_report in bank_reports),
            "invalid_source_records": len(invalid_records),
            "invalid_banks": len(invalid_banks),
        },
        "category_counts": dict(sorted(category_counts.items())),
        "category_bytes": dict(sorted(category_bytes.items())),
        "compression_counts": dict(sorted(compression_counts.items())),
        "families": families,
        "banks": bank_reports,
        "invalid_records": invalid_records[:50],
        "errors": errors,
        "status": "ok" if not errors else "invalid",
    }


def render_markdown(report: dict[str, Any]) -> str:
    totals = report["totals"]
    lines = [
        "# Asset Source Range Audit",
        "",
        "Generated by `tools/build_asset_source_range_audit.py` from checked-in asset manifests.",
        "",
        "This ROM-free audit validates the manifest source ranges that extraction recipes depend on. It proves each asset range is half-open, byte-counted, bank-local, non-overlapping, and collectively covers its manifest bank before any user-supplied ROM bytes are read.",
        "",
        "Generated asset-output and source-range reports are freshness-checked together with `tools/validate_asset_output_reports.py`.",
        "",
        "## Snapshot",
        "",
        f"- status: `{report['status']}`",
        f"- manifests: `{totals['manifests']}`",
        f"- source records: `{totals['assets']}`",
        f"- source bytes: `{totals['source_bytes']}`",
        f"- expected bank bytes: `{totals['expected_bank_bytes']}`",
        f"- covered bytes: `{totals['covered_bytes']}`",
        f"- coverage holes: `{totals['coverage_holes']}`",
        f"- coverage hole bytes: `{totals['coverage_hole_bytes']}`",
        f"- overlaps: `{totals['overlaps']}`",
        f"- overlap bytes: `{totals['overlap_bytes']}`",
        f"- invalid source records: `{totals['invalid_source_records']}`",
        f"- invalid banks: `{totals['invalid_banks']}`",
        f"- category mix: {compact_counts(report['category_counts'])}",
        f"- compression mix: {compact_counts(report['compression_counts'])}",
        "",
        "## Family Source Coverage",
        "",
        "| Family | Assets | Source bytes | Gap bytes | Holes | Overlaps | Category mix |",
        "| --- | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for family in report["families"]:
        lines.append(
            "| {label} | {assets} | {source_bytes} | {gap_bytes} | {holes} | {overlaps} | {categories} |".format(
                label=family["label"],
                assets=family["asset_count"],
                source_bytes=family["source_bytes"],
                gap_bytes=family["coverage_gap_bytes"],
                holes=family["hole_bytes"],
                overlaps=family["overlap_bytes"],
                categories=compact_counts(family["category_counts"]),
            )
        )

    lines.extend(
        [
            "",
            "## Per-Bank Source Coverage",
            "",
            "| Bank | Manifest | Assets | Source bytes | Covered | Holes | Overlaps | Categories |",
            "| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |",
        ]
    )
    for bank in report["banks"]:
        lines.append(
            "| `{bank_id}` | `{manifest}` | {assets} | {source_bytes} | {covered} | {holes} | {overlaps} | {categories} |".format(
                bank_id=bank["bank"],
                manifest=bank["manifest_path"],
                assets=bank["asset_count"],
                source_bytes=bank["source_bytes"],
                covered=bank["covered_bytes"],
                holes=bank["hole_bytes"],
                overlaps=bank["overlap_bytes"],
                categories=compact_counts(bank["category_counts"], limit=4),
            )
        )

    if report["invalid_records"]:
        lines.extend(["", "## Invalid Source Records", ""])
        lines.extend(["| Asset | Range | Errors |", "| --- | --- | --- |"])
        for record in report["invalid_records"]:
            lines.append(
                f"| `{record['asset_id']}` | `{record['range']}` | {'; '.join(record['errors'])} |"
            )

    if report["errors"]:
        lines.extend(["", "## Errors", ""])
        for error in report["errors"][:50]:
            lines.append(f"- {error}")

    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a ROM-free audit of asset manifest source ranges.")
    parser.add_argument("--manifest-dir", default=str(DEFAULT_MANIFEST_DIR))
    parser.add_argument("--json-out", default=str(DEFAULT_JSON_OUT))
    parser.add_argument("--markdown-out", default=str(DEFAULT_MARKDOWN_OUT))
    args = parser.parse_args()

    report = build_report(Path(args.manifest_dir))

    json_out = Path(args.json_out)
    json_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    markdown_out = Path(args.markdown_out)
    markdown_out.parent.mkdir(parents=True, exist_ok=True)
    markdown_out.write_text(render_markdown(report), encoding="utf-8")

    totals = report["totals"]
    print(
        "asset source range audit: "
        f"{report['status']}, "
        f"{totals['assets']} ranges, "
        f"{totals['coverage_hole_bytes']} hole bytes, "
        f"{totals['overlap_bytes']} overlap bytes"
    )
    if report["errors"]:
        for error in report["errors"][:50]:
            print(f"ERROR {error}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
