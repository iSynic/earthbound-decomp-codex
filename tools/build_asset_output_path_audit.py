from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path, PurePosixPath
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from asset_output_recipe_contracts import OUTPUT_RECIPE_CONTRACTS, validate_output_path
from build_asset_output_recipe_contracts import FAMILIES, compact_counts, family_for_bank, infer_bank, rel


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MANIFEST_DIR = ROOT / "asset-manifests"
DEFAULT_JSON_OUT = ROOT / "build" / "asset-output-path-audit.json"
DEFAULT_MARKDOWN_OUT = ROOT / "notes" / "asset-output-path-audit.md"


def manifest_paths(manifest_dir: Path) -> list[Path]:
    return sorted(manifest_dir.glob("*.json"))


def path_root(path: str) -> str:
    parts = PurePosixPath(path).parts
    return parts[0] if parts else ""


def path_depth(path: str) -> int:
    return len(PurePosixPath(path).parts)


def path_extension(path: str) -> str:
    suffix = PurePosixPath(path).suffix.lower()
    return suffix or "(none)"


def build_report(manifest_dir: Path) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    errors: list[str] = []
    paths_to_records: dict[str, list[dict[str, Any]]] = defaultdict(list)

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
                contract = OUTPUT_RECIPE_CONTRACTS.get(kind)
                path_value = output.get("path")
                output_path = str(path_value) if isinstance(path_value, str) else ""
                root = path_root(output_path)
                extension = path_extension(output_path)
                record_errors = validate_output_path(path_value)
                if contract is None:
                    record_errors.append(f"unsupported output kind {kind!r}")
                    expected_extension = None
                    output_type = None
                    decoder = None
                    renderer = None
                else:
                    expected_extension = contract.extension
                    output_type = contract.output_type
                    decoder = contract.decoder
                    renderer = contract.renderer
                    if expected_extension is not None and extension != expected_extension:
                        record_errors.append(f"{kind} output path must end with {expected_extension}")
                if root != bank.lower():
                    record_errors.append(
                        f"output path root {root!r} must match manifest bank folder {bank.lower()!r}"
                    )

                record = {
                    "asset_id": asset_id,
                    "title": asset.get("title"),
                    "manifest_path": rel(manifest_path),
                    "bank": bank,
                    "family": family["id"],
                    "category": asset.get("category"),
                    "output_index": output_index,
                    "kind": kind,
                    "path": output_path,
                    "root": root,
                    "depth": path_depth(output_path),
                    "extension": extension,
                    "expected_extension": expected_extension,
                    "output_type": output_type,
                    "decoder": decoder,
                    "renderer": renderer,
                    "errors": record_errors,
                }
                records.append(record)
                paths_to_records[output_path].append(record)
                for error in record_errors:
                    errors.append(f"{asset_id}: {output_path}: {error}")

    duplicate_paths = {
        path: records_for_path
        for path, records_for_path in sorted(paths_to_records.items())
        if path and len(records_for_path) > 1
    }
    for path, records_for_path in duplicate_paths.items():
        asset_refs = ", ".join(
            f"{record['asset_id']}[{record['output_index']}]" for record in records_for_path[:8]
        )
        errors.append(f"{path}: output path is reused by {len(records_for_path)} records: {asset_refs}")

    root_counts = Counter(str(record["root"]) for record in records)
    bank_counts = Counter(str(record["bank"]) for record in records)
    extension_counts = Counter(str(record["extension"]) for record in records)
    expected_extension_counts = Counter(
        str(record["expected_extension"] or "(none)") for record in records
    )
    depth_counts = Counter(str(record["depth"]) for record in records)
    kind_counts = Counter(str(record["kind"]) for record in records)
    family_counts: dict[str, Counter[str]] = defaultdict(Counter)
    family_root_counts: dict[str, Counter[str]] = defaultdict(Counter)
    family_extension_counts: dict[str, Counter[str]] = defaultdict(Counter)
    bank_root_alignment_counts: Counter[str] = Counter()

    for record in records:
        family = str(record["family"])
        family_counts[family][str(record["kind"])] += 1
        family_root_counts[family][str(record["root"])] += 1
        family_extension_counts[family][str(record["extension"])] += 1
        alignment = "matches_bank" if str(record["root"]) == str(record["bank"]).lower() else "mismatch"
        bank_root_alignment_counts[alignment] += 1

    families = []
    for family in FAMILIES:
        family_id = family["id"]
        if family_counts[family_id] or family_root_counts[family_id]:
            families.append(
                {
                    "id": family_id,
                    "label": family["label"],
                    "banks": family["banks"],
                    "output_count": sum(family_counts[family_id].values()),
                    "output_kind_counts": dict(sorted(family_counts[family_id].items())),
                    "root_counts": dict(sorted(family_root_counts[family_id].items())),
                    "extension_counts": dict(sorted(family_extension_counts[family_id].items())),
                }
            )

    collision_records = [
        {
            "path": path,
            "records": [
                {
                    "asset_id": record["asset_id"],
                    "manifest_path": record["manifest_path"],
                    "bank": record["bank"],
                    "kind": record["kind"],
                    "output_index": record["output_index"],
                }
                for record in records_for_path
            ],
        }
        for path, records_for_path in duplicate_paths.items()
    ]
    invalid_records = [record for record in records if record["errors"]]

    return {
        "schema": "earthbound-decomp.asset-output-path-audit.v1",
        "inputs": {
            "manifest_dir": rel(manifest_dir),
            "recipe_contract_module": "tools/asset_output_recipe_contracts.py",
        },
        "source_policy": {
            "contains_rom_derived_outputs": False,
            "validates_relative_output_recipes_only": True,
        },
        "totals": {
            "output_records": len(records),
            "unique_output_paths": len(paths_to_records),
            "duplicate_output_paths": len(duplicate_paths),
            "invalid_output_records": len(invalid_records),
            "root_prefixes": len(root_counts),
            "bank_root_aligned_outputs": bank_root_alignment_counts["matches_bank"],
            "bank_root_mismatched_outputs": bank_root_alignment_counts["mismatch"],
        },
        "path_root_counts": dict(sorted(root_counts.items())),
        "bank_counts": dict(sorted(bank_counts.items())),
        "extension_counts": dict(sorted(extension_counts.items())),
        "expected_extension_counts": dict(sorted(expected_extension_counts.items())),
        "path_depth_counts": dict(sorted(depth_counts.items())),
        "output_kind_counts": dict(sorted(kind_counts.items())),
        "bank_root_alignment_counts": dict(sorted(bank_root_alignment_counts.items())),
        "families": families,
        "collision_records": collision_records[:50],
        "invalid_records": invalid_records[:50],
        "records": records,
        "errors": errors,
        "status": "ok" if not errors else "invalid",
    }


def render_markdown(report: dict[str, Any]) -> str:
    totals = report["totals"]
    lines = [
        "# Asset Output Path Audit",
        "",
        "Generated by `tools/build_asset_output_path_audit.py` from checked-in asset manifests and the typed output recipe registry.",
        "",
        "This ROM-free audit proves typed asset outputs have one unambiguous relative destination each. It checks output-path uniqueness, bank-root alignment, POSIX relative paths, and typed extension expectations before any user-supplied ROM extraction writes files under ignored `build/assets`.",
        "",
        "Generated asset-output reports are freshness-checked together with `tools/validate_asset_output_reports.py`.",
        "",
        "## Snapshot",
        "",
        f"- status: `{report['status']}`",
        f"- typed output records: `{totals['output_records']}`",
        f"- unique output paths: `{totals['unique_output_paths']}`",
        f"- duplicate output paths: `{totals['duplicate_output_paths']}`",
        f"- invalid output records: `{totals['invalid_output_records']}`",
        f"- root prefixes: `{totals['root_prefixes']}`",
        f"- bank-root aligned outputs: `{totals['bank_root_aligned_outputs']}`",
        f"- bank-root mismatched outputs: `{totals['bank_root_mismatched_outputs']}`",
        f"- output extension mix: {compact_counts(report['extension_counts'])}",
        f"- path depth mix: {compact_counts(report['path_depth_counts'])}",
        "",
        "## Output Root Prefixes",
        "",
        compact_counts(report["path_root_counts"], limit=40),
        "",
        "## Recipe Path Mix",
        "",
        compact_counts(report["output_kind_counts"], limit=12),
        "",
        "## Family Path Coverage",
        "",
        "| Family | Outputs | Roots | Extensions | Output mix |",
        "| --- | ---: | --- | --- | --- |",
    ]
    for family in report["families"]:
        lines.append(
            "| {label} | {outputs} | {roots} | {extensions} | {output_mix} |".format(
                label=family["label"],
                outputs=family["output_count"],
                roots=compact_counts(family["root_counts"], limit=12),
                extensions=compact_counts(family["extension_counts"]),
                output_mix=compact_counts(family["output_kind_counts"]),
            )
        )

    if report["collision_records"]:
        lines.extend(["", "## Duplicate Output Paths", ""])
        lines.extend(["| Path | Records |", "| --- | --- |"])
        for collision in report["collision_records"]:
            refs = ", ".join(
                f"`{record['asset_id']}[{record['output_index']}]`"
                for record in collision["records"]
            )
            lines.append(f"| `{collision['path']}` | {refs} |")

    if report["invalid_records"]:
        lines.extend(["", "## Invalid Output Records", ""])
        lines.extend(["| Asset | Output path | Errors |", "| --- | --- | --- |"])
        for record in report["invalid_records"]:
            errors = "; ".join(record["errors"])
            lines.append(f"| `{record['asset_id']}` | `{record['path']}` | {errors} |")

    if report["errors"]:
        lines.extend(["", "## Errors", ""])
        for error in report["errors"][:50]:
            lines.append(f"- {error}")

    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a ROM-free audit of typed asset output paths.")
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
        "asset output path audit: "
        f"{report['status']}, "
        f"{totals['output_records']} outputs, "
        f"{totals['duplicate_output_paths']} duplicate paths, "
        f"{totals['invalid_output_records']} invalid records"
    )
    if report["errors"]:
        for error in report["errors"][:50]:
            print(f"ERROR {error}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
