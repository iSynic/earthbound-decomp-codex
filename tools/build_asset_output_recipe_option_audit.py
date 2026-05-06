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
from build_asset_output_smoke_fixtures import build_fixture_plan
from validate_asset_output_codecs import output_cases


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MANIFEST_DIR = ROOT / "asset-manifests"
DEFAULT_JSON_OUT = ROOT / "build" / "asset-output-recipe-option-audit.json"
DEFAULT_MARKDOWN_OUT = ROOT / "notes" / "asset-output-recipe-option-audit.md"

DECODE_AFFECTING_OPTIONS = {"trim_trailing_bytes"}


def manifest_paths(manifest_dir: Path) -> list[Path]:
    return sorted(manifest_dir.glob("*.json"))


def output_key(manifest_path: str, asset_id: str, kind: str, path: str) -> tuple[str, str, str, str]:
    return (manifest_path, asset_id, kind, path)


def load_manifest_outputs(manifest_dir: Path) -> tuple[list[dict[str, Any]], dict[tuple[str, str, str, str], dict[str, Any]]]:
    records: list[dict[str, Any]] = []
    by_key: dict[tuple[str, str, str, str], dict[str, Any]] = {}
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
            for output_index, output in enumerate(outputs):
                if not isinstance(output, dict):
                    continue
                kind = str(output.get("kind"))
                path = str(output.get("path"))
                contract = OUTPUT_RECIPE_CONTRACTS.get(kind)
                if contract is None:
                    continue
                option_fields = [field for field in contract.optional_fields if field in output]
                record = {
                    "asset_id": asset_id,
                    "title": asset.get("title"),
                    "manifest_path": rel(manifest_path),
                    "bank": bank,
                    "family": family["id"],
                    "category": asset.get("category"),
                    "output_index": output_index,
                    "kind": kind,
                    "path": path,
                    "option_fields": option_fields,
                    "options": {field: output[field] for field in option_fields},
                }
                records.append(record)
                by_key[output_key(record["manifest_path"], asset_id, kind, path)] = record
    return records, by_key


def smoke_option_counts(plan: dict[str, Any], outputs_by_key: dict[tuple[str, str, str, str], dict[str, Any]]) -> Counter[tuple[str, str]]:
    counts: Counter[tuple[str, str]] = Counter()
    for fixture in plan.get("fixtures", []):
        if not isinstance(fixture, dict):
            continue
        target = fixture.get("target_output")
        if not isinstance(target, dict):
            continue
        key = output_key(
            str(fixture.get("manifest_path")),
            str(fixture.get("asset_id")),
            str(target.get("kind")),
            str(target.get("path")),
        )
        output = outputs_by_key.get(key)
        if output is None:
            continue
        for field in output["option_fields"]:
            counts[(str(output["kind"]), str(field))] += 1
    return counts


def codec_option_counts() -> Counter[tuple[str, str]]:
    counts: Counter[tuple[str, str]] = Counter()
    for case in output_cases():
        spec = case.get("spec")
        if not isinstance(spec, dict):
            continue
        kind = spec.get("kind")
        if not isinstance(kind, str):
            continue
        contract = OUTPUT_RECIPE_CONTRACTS.get(kind)
        if contract is None:
            continue
        for field in contract.optional_fields:
            if field in spec:
                counts[(kind, field)] += 1
    return counts


def build_report(manifest_dir: Path) -> dict[str, Any]:
    output_records, outputs_by_key = load_manifest_outputs(manifest_dir)
    smoke_plan = build_fixture_plan(manifest_dir)
    smoke_counts = smoke_option_counts(smoke_plan, outputs_by_key)
    codec_counts = codec_option_counts()
    errors: list[str] = []

    usage_counts: Counter[tuple[str, str]] = Counter()
    family_usage_counts: dict[str, Counter[str]] = defaultdict(Counter)
    field_usage_counts: Counter[str] = Counter()
    examples: dict[tuple[str, str], dict[str, Any]] = {}

    for record in output_records:
        for field in record["option_fields"]:
            key = (str(record["kind"]), field)
            usage_counts[key] += 1
            family_usage_counts[str(record["family"])][field] += 1
            field_usage_counts[field] += 1
            examples.setdefault(
                key,
                {
                    "asset_id": record["asset_id"],
                    "manifest_path": record["manifest_path"],
                    "path": record["path"],
                    "value": record["options"][field],
                },
            )

    option_records = []
    for kind, contract in sorted(OUTPUT_RECIPE_CONTRACTS.items()):
        for field in contract.optional_fields:
            key = (kind, field)
            manifest_usage_count = usage_counts[key]
            smoke_fixture_count = smoke_counts[key]
            codec_case_count = codec_counts[key]
            decode_affecting = field in DECODE_AFFECTING_OPTIONS
            status = "unused"
            if manifest_usage_count > 0:
                status = "ok"
                if smoke_fixture_count == 0:
                    status = "invalid"
                    errors.append(f"{kind}.{field}: manifest usage lacks smoke fixture coverage")
                if decode_affecting and codec_case_count == 0:
                    status = "invalid"
                    errors.append(f"{kind}.{field}: decode-affecting option lacks synthetic codec coverage")
            option_records.append(
                {
                    "kind": kind,
                    "field": field,
                    "decode_affecting": decode_affecting,
                    "manifest_usage_count": manifest_usage_count,
                    "smoke_fixture_count": smoke_fixture_count,
                    "codec_case_count": codec_case_count,
                    "example": examples.get(key),
                    "status": status,
                }
            )

    family_records = []
    for family in FAMILIES:
        family_id = family["id"]
        if family_usage_counts[family_id]:
            family_records.append(
                {
                    "id": family_id,
                    "label": family["label"],
                    "banks": family["banks"],
                    "option_usage_count": sum(family_usage_counts[family_id].values()),
                    "field_counts": dict(sorted(family_usage_counts[family_id].items())),
                }
            )

    status_counts = Counter(str(record["status"]) for record in option_records)
    used_records = [record for record in option_records if int(record["manifest_usage_count"]) > 0]

    return {
        "schema": "earthbound-decomp.asset-output-recipe-option-audit.v1",
        "inputs": {
            "manifest_dir": rel(manifest_dir),
            "recipe_contract_module": "tools/asset_output_recipe_contracts.py",
            "smoke_fixture_plan": "notes/asset-output-smoke-fixtures.json",
            "codec_validation_cases": "tools/validate_asset_output_codecs.py",
        },
        "source_policy": {
            "contains_rom_derived_outputs": False,
            "audits_manifest_recipe_options_only": True,
        },
        "coverage_policy": {
            "manifest_used_options_require_smoke_fixture": True,
            "decode_affecting_options_require_synthetic_codec_case": sorted(DECODE_AFFECTING_OPTIONS),
        },
        "totals": {
            "registered_optional_fields": len(option_records),
            "used_optional_pairs": len(used_records),
            "manifest_option_usages": sum(usage_counts.values()),
            "smoke_fixture_option_hits": sum(smoke_counts.values()),
            "codec_option_hits": sum(codec_counts.values()),
            "decode_affecting_used_pairs": sum(
                1 for record in used_records if record["decode_affecting"]
            ),
            "invalid_option_pairs": status_counts["invalid"],
        },
        "field_usage_counts": dict(sorted(field_usage_counts.items())),
        "status_counts": dict(sorted(status_counts.items())),
        "families": family_records,
        "options": option_records,
        "errors": errors,
        "status": "ok" if not errors else "invalid",
    }


def render_markdown(report: dict[str, Any]) -> str:
    totals = report["totals"]
    lines = [
        "# Asset Output Recipe Option Audit",
        "",
        "Generated by `tools/build_asset_output_recipe_option_audit.py` from checked-in asset manifests, the typed output recipe registry, smoke fixtures, and synthetic codec cases.",
        "",
        "This ROM-free audit makes optional recipe fields visible. Manifest-used options must appear in at least one smoke fixture target; options that change decode input bytes also need synthetic codec coverage.",
        "",
        "Generated asset-output and source-range reports are freshness-checked together with `tools/validate_asset_output_reports.py`.",
        "",
        "## Snapshot",
        "",
        f"- status: `{report['status']}`",
        f"- registered optional fields: `{totals['registered_optional_fields']}`",
        f"- used optional recipe/field pairs: `{totals['used_optional_pairs']}`",
        f"- manifest option usages: `{totals['manifest_option_usages']}`",
        f"- smoke fixture option hits: `{totals['smoke_fixture_option_hits']}`",
        f"- synthetic codec option hits: `{totals['codec_option_hits']}`",
        f"- decode-affecting used pairs: `{totals['decode_affecting_used_pairs']}`",
        f"- invalid option pairs: `{totals['invalid_option_pairs']}`",
        f"- field usage mix: {compact_counts(report['field_usage_counts'])}",
        "",
        "## Option Coverage",
        "",
        "| Recipe kind | Field | Decode-affecting | Manifest uses | Smoke hits | Codec hits | Status | Example |",
        "| --- | --- | --- | ---: | ---: | ---: | --- | --- |",
    ]
    for option in report["options"]:
        example = option.get("example")
        if isinstance(example, dict):
            example_text = f"`{example['asset_id']}` -> `{example['path']}`"
        else:
            example_text = "-"
        lines.append(
            "| {kind} | `{field}` | {decode} | {uses} | {smoke} | {codec} | `{status}` | {example} |".format(
                kind=f"`{option['kind']}`",
                field=option["field"],
                decode="yes" if option["decode_affecting"] else "no",
                uses=option["manifest_usage_count"],
                smoke=option["smoke_fixture_count"],
                codec=option["codec_case_count"],
                status=option["status"],
                example=example_text,
            )
        )

    if report["families"]:
        lines.extend(
            [
                "",
                "## Family Option Usage",
                "",
                "| Family | Option usages | Fields |",
                "| --- | ---: | --- |",
            ]
        )
        for family in report["families"]:
            lines.append(
                "| {label} | {count} | {fields} |".format(
                    label=family["label"],
                    count=family["option_usage_count"],
                    fields=compact_counts(family["field_counts"]),
                )
            )

    if report["errors"]:
        lines.extend(["", "## Errors", ""])
        for error in report["errors"]:
            lines.append(f"- {error}")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a ROM-free audit of optional typed output recipe fields.")
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
        "asset output recipe option audit: "
        f"{report['status']}, "
        f"{totals['manifest_option_usages']} manifest option usages, "
        f"{totals['invalid_option_pairs']} invalid pairs"
    )
    if report["errors"]:
        for error in report["errors"]:
            print(f"ERROR {error}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
