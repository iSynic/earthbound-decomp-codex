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

from asset_output_recipe_contracts import OUTPUT_RECIPE_CONTRACTS
from build_asset_output_recipe_contracts import FAMILIES, compact_counts, load_manifest_assets, rel


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MANIFEST_DIR = ROOT / "asset-manifests"
DEFAULT_JSON_OUT = ROOT / "build" / "asset-output-raw-only-audit.json"
DEFAULT_MARKDOWN_OUT = ROOT / "notes" / "asset-output-raw-only-audit.md"


BOUNDARY_BY_CATEGORY = {
    "audio": {
        "id": "deferred_audio_pack",
        "label": "Deferred audio pack",
        "note": "Raw-pack extraction is intentional until the audio pack/sample/sequence contract boundary is chosen.",
    },
    "binary-asset": {
        "id": "binary_asset_semantics",
        "label": "Binary asset semantics",
        "note": "Byte-stable extraction exists; format-level decode depends on narrower table or runtime-owner evidence.",
    },
    "raw-gap": {
        "id": "preserved_coverage_gap",
        "label": "Preserved coverage gap",
        "note": "Raw gap output preserves source accounting and should not be flattened into a semantic asset blindly.",
    },
    "raw-preserved-corridor": {
        "id": "preserved_corridor",
        "label": "Preserved mixed corridor",
        "note": "Mixed data/code corridor is intentionally preserved until source/runtime semantics split it safely.",
    },
    "raw-table": {
        "id": "table_semantics",
        "label": "Table semantics pending",
        "note": "Table rows are byte-accounted; row-level decode should wait for caller/runtime context.",
    },
    "graphics": {
        "id": "graphics_decode_candidate",
        "label": "Graphics decode candidate",
        "note": "Graphic bytes are extractable but do not yet have a typed tile/font/preview recipe.",
    },
}


def output_contracts(outputs: list[Any]) -> list[tuple[dict[str, Any], Any | None]]:
    contracts = []
    for output in outputs:
        if not isinstance(output, dict):
            continue
        kind = output.get("kind")
        if not isinstance(kind, str):
            contracts.append((output, None))
            continue
        contracts.append((output, OUTPUT_RECIPE_CONTRACTS.get(kind)))
    return contracts


def has_decode_or_render(outputs: list[Any]) -> bool:
    for _output, contract in output_contracts(outputs):
        if contract is not None and (contract.decoder is not None or contract.renderer is not None):
            return True
    return False


def output_kinds(outputs: list[Any]) -> list[str]:
    return [
        str(output.get("kind"))
        for output in outputs
        if isinstance(output, dict) and isinstance(output.get("kind"), str)
    ]


def boundary_for_category(category: str) -> dict[str, str]:
    return BOUNDARY_BY_CATEGORY.get(
        category,
        {
            "id": "extract_only_candidate",
            "label": "Extract-only candidate",
            "note": "The category is byte-accounted but has no category-specific raw-only boundary note yet.",
        },
    )


def decode_candidate_sort_key(record: dict[str, Any]) -> tuple[int, int, str]:
    priority = {
        "graphics_decode_candidate": 0,
        "binary_asset_semantics": 1,
        "table_semantics": 2,
    }
    return (priority.get(str(record["boundary"]), 99), -int(record["bytes"]), str(record["asset_id"]))


def build_report(manifest_dir: Path) -> dict[str, Any]:
    assets = load_manifest_assets(manifest_dir)
    records: list[dict[str, Any]] = []
    errors: list[str] = []
    decoded_or_rendered_assets = 0
    assets_with_outputs = 0

    for asset in assets:
        outputs = asset.get("outputs", [])
        if not isinstance(outputs, list):
            outputs = []
        if outputs:
            assets_with_outputs += 1
        unsupported_kinds = [
            str(output.get("kind"))
            for output, contract in output_contracts(outputs)
            if contract is None
        ]
        if unsupported_kinds:
            errors.append(f"{asset['id']}: unsupported output kinds: {', '.join(unsupported_kinds)}")
        if has_decode_or_render(outputs):
            decoded_or_rendered_assets += 1
            continue
        if not outputs:
            continue

        category = str(asset.get("category", "unknown"))
        boundary = boundary_for_category(category)
        records.append(
            {
                "asset_id": asset.get("id"),
                "title": asset.get("title"),
                "manifest_path": asset.get("manifest_path"),
                "bank": asset.get("bank"),
                "family": asset.get("family"),
                "category": category,
                "bytes": int(asset.get("bytes", 0) or 0),
                "output_kinds": sorted(set(output_kinds(outputs))),
                "output_count": len(output_kinds(outputs)),
                "boundary": boundary["id"],
                "boundary_label": boundary["label"],
                "boundary_note": boundary["note"],
            }
        )

    category_counts: Counter[str] = Counter()
    category_bytes: Counter[str] = Counter()
    boundary_counts: Counter[str] = Counter()
    boundary_bytes: Counter[str] = Counter()
    bank_counts: Counter[str] = Counter()
    bank_bytes: Counter[str] = Counter()
    family_counts: dict[str, Counter[str]] = defaultdict(Counter)
    family_bytes: Counter[str] = Counter()
    family_boundary_counts: dict[str, Counter[str]] = defaultdict(Counter)
    family_category_bytes: dict[str, Counter[str]] = defaultdict(Counter)

    for record in records:
        category = str(record["category"])
        boundary = str(record["boundary"])
        bank = str(record["bank"])
        family = str(record["family"])
        byte_count = int(record["bytes"])
        category_counts[category] += 1
        category_bytes[category] += byte_count
        boundary_counts[boundary] += 1
        boundary_bytes[boundary] += byte_count
        bank_counts[bank] += 1
        bank_bytes[bank] += byte_count
        family_counts[family][category] += 1
        family_boundary_counts[family][boundary] += 1
        family_category_bytes[family][category] += byte_count
        family_bytes[family] += byte_count

    families = []
    for family in FAMILIES:
        family_id = family["id"]
        family_records = [record for record in records if record["family"] == family_id]
        if not family_records:
            continue
        examples = sorted(family_records, key=lambda item: (-int(item["bytes"]), str(item["asset_id"])))[:8]
        families.append(
            {
                "id": family_id,
                "label": family["label"],
                "banks": family["banks"],
                "raw_only_asset_count": len(family_records),
                "raw_only_bytes": family_bytes[family_id],
                "category_counts": dict(sorted(family_counts[family_id].items())),
                "category_bytes": dict(sorted(family_category_bytes[family_id].items())),
                "boundary_counts": dict(sorted(family_boundary_counts[family_id].items())),
                "largest_examples": [
                    {
                        "asset_id": example["asset_id"],
                        "manifest_path": example["manifest_path"],
                        "category": example["category"],
                        "bytes": example["bytes"],
                        "boundary": example["boundary"],
                    }
                    for example in examples
                ],
            }
        )

    banks = []
    for bank, count in sorted(bank_counts.items()):
        bank_records = [record for record in records if record["bank"] == bank]
        bank_categories = Counter(str(record["category"]) for record in bank_records)
        bank_boundaries = Counter(str(record["boundary"]) for record in bank_records)
        banks.append(
            {
                "bank": bank,
                "raw_only_asset_count": count,
                "raw_only_bytes": bank_bytes[bank],
                "category_counts": dict(sorted(bank_categories.items())),
                "boundary_counts": dict(sorted(bank_boundaries.items())),
            }
        )

    decode_candidates = [
        record
        for record in sorted(records, key=decode_candidate_sort_key)
        if record["boundary"] in {"graphics_decode_candidate", "binary_asset_semantics", "table_semantics"}
    ]

    return {
        "schema": "earthbound-decomp.asset-output-raw-only-audit.v1",
        "inputs": {
            "manifest_dir": rel(manifest_dir),
            "recipe_contract_module": "tools/asset_output_recipe_contracts.py",
        },
        "source_policy": {
            "contains_rom_derived_outputs": False,
            "records_extract_only_pressure_without_flattening_payloads": True,
        },
        "totals": {
            "assets": len(assets),
            "assets_with_outputs": assets_with_outputs,
            "decoder_or_renderer_backed_assets": decoded_or_rendered_assets,
            "raw_only_assets": len(records),
            "raw_only_bytes": sum(int(record["bytes"]) for record in records),
            "raw_only_categories": len(category_counts),
            "raw_only_banks": len(bank_counts),
            "unsupported_output_kinds": len(errors),
        },
        "category_counts": dict(sorted(category_counts.items())),
        "category_bytes": dict(sorted(category_bytes.items())),
        "boundary_counts": dict(sorted(boundary_counts.items())),
        "boundary_bytes": dict(sorted(boundary_bytes.items())),
        "boundary_notes": BOUNDARY_BY_CATEGORY,
        "families": families,
        "banks": banks,
        "decode_candidate_records": decode_candidates[:50],
        "records": records,
        "errors": errors,
        "status": "ok" if not errors else "invalid",
    }


def render_markdown(report: dict[str, Any]) -> str:
    totals = report["totals"]
    lines = [
        "# Asset Output Raw-Only Audit",
        "",
        "Generated by `tools/build_asset_output_raw_only_audit.py` from checked-in asset manifests and the typed output recipe registry.",
        "",
        "This ROM-free audit separates assets that already have decoder or renderer-backed outputs from assets that are intentionally extract-only for now. It is a pressure map for future emitter work, not permission to flatten audio packs, tables, raw gaps, or preserved mixed corridors blindly.",
        "",
        "Generated asset-output and source-range reports are freshness-checked together with `tools/validate_asset_output_reports.py`.",
        "",
        "## Snapshot",
        "",
        f"- status: `{report['status']}`",
        f"- assets with outputs: `{totals['assets_with_outputs']}`",
        f"- decoder/renderer-backed assets: `{totals['decoder_or_renderer_backed_assets']}`",
        f"- extract-only assets: `{totals['raw_only_assets']}`",
        f"- extract-only bytes: `{totals['raw_only_bytes']}`",
        f"- extract-only categories: `{totals['raw_only_categories']}`",
        f"- extract-only banks: `{totals['raw_only_banks']}`",
        f"- unsupported output kinds: `{totals['unsupported_output_kinds']}`",
        f"- extract-only category mix: {compact_counts(report['category_counts'])}",
        f"- extract-only boundary mix: {compact_counts(report['boundary_counts'])}",
        "",
        "## Boundary Notes",
        "",
        "| Boundary | Assets | Bytes | Meaning |",
        "| --- | ---: | ---: | --- |",
    ]
    for boundary_id, count in sorted(report["boundary_counts"].items()):
        note = next(
            (
                boundary["note"]
                for boundary in report["boundary_notes"].values()
                if boundary["id"] == boundary_id
            ),
            "Extract-only boundary.",
        )
        lines.append(
            f"| `{boundary_id}` | {count} | {report['boundary_bytes'][boundary_id]} | {note} |"
        )

    lines.extend(
        [
            "",
            "## Family Extract-Only Pressure",
            "",
            "| Family | Assets | Bytes | Categories | Boundaries |",
            "| --- | ---: | ---: | --- | --- |",
        ]
    )
    for family in report["families"]:
        lines.append(
            "| {label} | {assets} | {bytes} | {categories} | {boundaries} |".format(
                label=family["label"],
                assets=family["raw_only_asset_count"],
                bytes=family["raw_only_bytes"],
                categories=compact_counts(family["category_counts"]),
                boundaries=compact_counts(family["boundary_counts"]),
            )
        )

    lines.extend(
        [
            "",
            "## Bank Extract-Only Pressure",
            "",
            "| Bank | Assets | Bytes | Categories | Boundaries |",
            "| --- | ---: | ---: | --- | --- |",
        ]
    )
    for bank in report["banks"]:
        lines.append(
            "| `{bank_id}` | {assets} | {bytes} | {categories} | {boundaries} |".format(
                bank_id=bank["bank"],
                assets=bank["raw_only_asset_count"],
                bytes=bank["raw_only_bytes"],
                categories=compact_counts(bank["category_counts"], limit=4),
                boundaries=compact_counts(bank["boundary_counts"], limit=4),
            )
        )

    if report["decode_candidate_records"]:
        lines.extend(
            [
                "",
                "## Decode Candidate Records",
                "",
                "| Asset | Manifest | Category | Bytes | Boundary |",
                "| --- | --- | --- | ---: | --- |",
            ]
        )
        for record in report["decode_candidate_records"]:
            lines.append(
                "| `{asset}` | `{manifest}` | `{category}` | {bytes} | `{boundary}` |".format(
                    asset=record["asset_id"],
                    manifest=record["manifest_path"],
                    category=record["category"],
                    bytes=record["bytes"],
                    boundary=record["boundary"],
                )
            )

    if report["errors"]:
        lines.extend(["", "## Errors", ""])
        for error in report["errors"][:50]:
            lines.append(f"- {error}")

    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a ROM-free audit of extract-only asset outputs.")
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
        "asset output raw-only audit: "
        f"{report['status']}, "
        f"{totals['raw_only_assets']} extract-only assets, "
        f"{totals['decoder_or_renderer_backed_assets']} decoder/renderer-backed assets"
    )
    if report["errors"]:
        for error in report["errors"][:50]:
            print(f"ERROR {error}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
