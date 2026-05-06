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
from build_asset_output_recipe_contracts import FAMILIES, compact_counts, family_for_bank, infer_bank, rel


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MANIFEST_DIR = ROOT / "asset-manifests"
DEFAULT_JSON_OUT = ROOT / "build" / "asset-output-source-refs.json"
DEFAULT_MARKDOWN_OUT = ROOT / "notes" / "asset-output-source-refs.md"

SOURCE_REF_FIELDS = ("palette_source", "graphics_source")
KNOWN_EXTERNAL_SOURCE_REFS = {
    (
        "C3:0000..C3:0020",
        32,
        "ec19ba264a2c8430ecba455c016d17da86e55916",
    ): {
        "id": "overworld_sprite_palette_00_runtime_source",
        "role": "Default overworld sprite palette used by D1-D5 palette-00 preview recipes.",
        "boundary": "runtime-source-bank-consumer-ref",
        "note": "The palette lives in C3 runtime data, outside the owned asset-manifest bank scope for this pass.",
    }
}


def manifest_paths(manifest_dir: Path) -> list[Path]:
    return sorted(manifest_dir.glob("*.json"))


def asset_source_key(source: dict[str, Any]) -> tuple[str, int, str] | None:
    range_text = source.get("range")
    bytes_value = source.get("bytes")
    sha1 = source.get("sha1")
    if not isinstance(range_text, str) or not isinstance(bytes_value, int) or not isinstance(sha1, str):
        return None
    return (range_text, bytes_value, sha1)


def source_ref_key(source: dict[str, Any]) -> tuple[str, int, str] | None:
    if source.get("type") != "rom-range":
        return None
    range_text = source.get("range")
    bytes_value = source.get("bytes")
    sha1 = source.get("sha1")
    if not isinstance(range_text, str) or not isinstance(bytes_value, int) or not isinstance(sha1, str):
        return None
    return (range_text, bytes_value, sha1)


def build_asset_source_index(manifest_dir: Path) -> dict[tuple[str, int, str], list[dict[str, Any]]]:
    by_source: dict[tuple[str, int, str], list[dict[str, Any]]] = defaultdict(list)
    for manifest_path in manifest_paths(manifest_dir):
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        bank = infer_bank(manifest_path, manifest)
        family = family_for_bank(bank)
        assets = manifest.get("assets", [])
        if not isinstance(assets, list):
            raise ValueError(f"{manifest_path}: assets must be a list")
        for asset in assets:
            if not isinstance(asset, dict):
                continue
            source = asset.get("source", {})
            if not isinstance(source, dict):
                continue
            key = asset_source_key(source)
            if key is None:
                continue
            by_source[key].append(
                {
                    "asset_id": asset.get("id"),
                    "title": asset.get("title"),
                    "manifest_path": rel(manifest_path),
                    "bank": bank,
                    "family": family["id"],
                    "category": asset.get("category"),
                    "range": key[0],
                    "bytes": key[1],
                    "sha1": key[2],
                }
            )
    return by_source


def build_report(manifest_dir: Path) -> dict[str, Any]:
    asset_sources = build_asset_source_index(manifest_dir)
    records: list[dict[str, Any]] = []
    errors: list[str] = []

    for manifest_path in manifest_paths(manifest_dir):
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        bank = infer_bank(manifest_path, manifest)
        family = family_for_bank(bank)
        assets = manifest.get("assets", [])
        if not isinstance(assets, list):
            raise ValueError(f"{manifest_path}: assets must be a list")
        for asset in assets:
            if not isinstance(asset, dict):
                continue
            asset_id = str(asset.get("id"))
            outputs = asset.get("outputs", [])
            if not isinstance(outputs, list):
                outputs = []
            for output in outputs:
                if not isinstance(output, dict):
                    continue
                kind = str(output.get("kind"))
                contract = OUTPUT_RECIPE_CONTRACTS.get(kind)
                if contract is None:
                    continue
                for field in SOURCE_REF_FIELDS:
                    source = output.get(field)
                    if source is None:
                        continue
                    if not isinstance(source, dict):
                        errors.append(f"{asset_id}: {kind}.{field} must be an object")
                        continue
                    key = source_ref_key(source)
                    if key is None:
                        errors.append(f"{asset_id}: {kind}.{field} is not a complete rom-range source ref")
                        continue
                    matches = asset_sources.get(key, [])
                    external = KNOWN_EXTERNAL_SOURCE_REFS.get(key)
                    if matches:
                        match_status = "manifest_asset"
                    elif external is not None:
                        match_status = "known_external"
                    else:
                        match_status = "unmatched"
                    records.append(
                        {
                            "asset_id": asset_id,
                            "title": asset.get("title"),
                            "manifest_path": rel(manifest_path),
                            "bank": bank,
                            "family": family["id"],
                            "category": asset.get("category"),
                            "output_kind": kind,
                            "output_path": output.get("path"),
                            "decoder": contract.decoder,
                            "renderer": contract.renderer,
                            "field": field,
                            "range": key[0],
                            "bytes": key[1],
                            "sha1": key[2],
                            "compression": source.get("compression"),
                            "match_status": match_status,
                            "known_external_source": external,
                            "matched_assets": matches,
                        }
                    )

    field_counts = Counter(str(record["field"]) for record in records)
    status_counts = Counter(str(record["match_status"]) for record in records)
    kind_counts = Counter(str(record["output_kind"]) for record in records)
    family_counts: dict[str, Counter[str]] = defaultdict(Counter)
    family_field_counts: dict[str, Counter[str]] = defaultdict(Counter)
    referenced_asset_ids = set()
    distinct_ref_keys = set()
    self_refs = 0
    cross_manifest_refs = 0
    for record in records:
        family = str(record["family"])
        status = str(record["match_status"])
        family_counts[family][status] += 1
        family_field_counts[family][str(record["field"])] += 1
        distinct_ref_keys.add((record["range"], record["bytes"], record["sha1"]))
        for matched in record["matched_assets"]:
            matched_id = str(matched["asset_id"])
            referenced_asset_ids.add((matched["manifest_path"], matched_id))
            if matched_id == record["asset_id"] and matched["manifest_path"] == record["manifest_path"]:
                self_refs += 1
            elif matched["manifest_path"] != record["manifest_path"]:
                cross_manifest_refs += 1

    family_summaries = []
    for family in FAMILIES:
        family_id = family["id"]
        if family_counts[family_id] or family_field_counts[family_id]:
            family_summaries.append(
                {
                    "id": family_id,
                    "label": family["label"],
                    "banks": family["banks"],
                    "source_ref_count": sum(family_counts[family_id].values()),
                    "match_status_counts": dict(sorted(family_counts[family_id].items())),
                    "field_counts": dict(sorted(family_field_counts[family_id].items())),
                }
            )

    unmatched = [record for record in records if record["match_status"] == "unmatched"]
    known_external = [record for record in records if record["match_status"] == "known_external"]

    return {
        "schema": "earthbound-decomp.asset-output-source-refs.v1",
        "inputs": {
            "manifest_dir": rel(manifest_dir),
            "recipe_contract_module": "tools/asset_output_recipe_contracts.py",
        },
        "source_policy": {
            "contains_rom_derived_outputs": False,
            "matches_manifest_ranges_only": True,
        },
        "totals": {
            "source_ref_count": len(records),
            "distinct_source_refs": len(distinct_ref_keys),
            "referenced_manifest_assets": len(referenced_asset_ids),
            "self_refs": self_refs,
            "cross_manifest_refs": cross_manifest_refs,
            "known_external_source_refs": len(known_external),
            "unmatched_source_refs": len(unmatched),
        },
        "field_counts": dict(sorted(field_counts.items())),
        "match_status_counts": dict(sorted(status_counts.items())),
        "output_kind_counts": dict(sorted(kind_counts.items())),
        "families": family_summaries,
        "known_external_sources": list(KNOWN_EXTERNAL_SOURCE_REFS.values()),
        "unmatched_records": unmatched[:50],
        "records": records,
        "errors": errors,
        "status": "ok" if not errors else "invalid",
    }


def render_markdown(report: dict[str, Any]) -> str:
    totals = report["totals"]
    lines = [
        "# Asset Output Source References",
        "",
        "Generated by `tools/build_asset_output_source_refs.py` from checked-in asset manifests and the typed output recipe registry.",
        "",
        "This ROM-free audit matches every typed output `palette_source` and `graphics_source` reference back to manifest source ranges using range, byte count, and SHA-1. It proves composed and palette-applied previews are tied to byte-accounted manifest assets rather than implicit extraction order.",
        "",
        "Generated asset-output reports are freshness-checked together with `tools/validate_asset_output_reports.py`.",
        "",
        "## Snapshot",
        "",
        f"- status: `{report['status']}`",
        f"- output source refs: `{totals['source_ref_count']}`",
        f"- distinct source refs: `{totals['distinct_source_refs']}`",
        f"- referenced manifest assets: `{totals['referenced_manifest_assets']}`",
        f"- self refs: `{totals['self_refs']}`",
        f"- cross-manifest refs: `{totals['cross_manifest_refs']}`",
        f"- known external source refs: `{totals['known_external_source_refs']}`",
        f"- unmatched source refs: `{totals['unmatched_source_refs']}`",
        f"- source field mix: {compact_counts(report['field_counts'])}",
        f"- match status mix: {compact_counts(report['match_status_counts'])}",
        "",
        "## Recipe Source-Ref Mix",
        "",
        compact_counts(report["output_kind_counts"], limit=12),
        "",
        "## Family Source-Ref Coverage",
        "",
        "| Family | Source refs | Match status | Source fields |",
        "| --- | ---: | --- | --- |",
    ]
    for family in report["families"]:
        lines.append(
            "| {label} | {count} | {status} | {fields} |".format(
                label=family["label"],
                count=family["source_ref_count"],
                status=compact_counts(family["match_status_counts"]),
                fields=compact_counts(family["field_counts"]),
            )
        )

    if report["known_external_sources"]:
        lines.extend(["", "## Known External Sources", ""])
        for source in report["known_external_sources"]:
            lines.append(
                f"- `{source['id']}`: {source['role']} Boundary: `{source['boundary']}`. {source['note']}"
            )

    if report["unmatched_records"]:
        lines.extend(["", "## Unmatched Source Refs", ""])
        lines.extend(["| Asset | Output | Field | Range | Bytes |", "| --- | --- | --- | --- | ---: |"])
        for record in report["unmatched_records"]:
            lines.append(
                f"| `{record['asset_id']}` | `{record['output_path']}` | `{record['field']}` | `{record['range']}` | {record['bytes']} |"
            )

    if report["errors"]:
        lines.extend(["", "## Errors", ""])
        for error in report["errors"]:
            lines.append(f"- {error}")

    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a ROM-free audit of typed asset output source refs.")
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
        "asset output source refs: "
        f"{report['status']}, "
        f"{totals['source_ref_count']} refs, "
        f"{totals['unmatched_source_refs']} unmatched"
    )
    if report["errors"]:
        for error in report["errors"]:
            print(f"ERROR {error}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
