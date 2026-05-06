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
from build_asset_output_preview_geometry import build_report as build_preview_geometry_report
from build_asset_output_recipe_contracts import FAMILIES, compact_counts, family_for_bank, infer_bank, rel
from build_asset_output_smoke_fixtures import DEFAULT_JSON_OUT as DEFAULT_SMOKE_FIXTURES
from build_asset_output_smoke_fixtures import build_fixture_plan


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MANIFEST_DIR = ROOT / "asset-manifests"
DEFAULT_JSON_OUT = ROOT / "build" / "asset-output-index.json"
DEFAULT_MARKDOWN_OUT = ROOT / "notes" / "asset-output-index.md"
SOURCE_REFS_MARKDOWN = ROOT / "notes" / "asset-output-source-refs.md"


def load_smoke_plan(manifest_dir: Path) -> dict[str, Any]:
    if DEFAULT_SMOKE_FIXTURES.exists():
        return json.loads(DEFAULT_SMOKE_FIXTURES.read_text(encoding="utf-8"))
    return build_fixture_plan(manifest_dir)


def smoke_fixture_map(plan: dict[str, Any]) -> dict[tuple[str, str, str, str], list[dict[str, str]]]:
    by_output: dict[tuple[str, str, str, str], list[dict[str, str]]] = defaultdict(list)
    for fixture in plan.get("fixtures", []):
        if not isinstance(fixture, dict):
            continue
        target = fixture.get("target_output")
        if not isinstance(target, dict):
            continue
        key = (
            str(fixture.get("manifest_path")),
            str(fixture.get("asset_id")),
            str(target.get("kind")),
            str(target.get("path")),
        )
        by_output[key].append(
            {
                "id": str(fixture.get("id")),
                "type": str(fixture.get("type")),
                "key": str(fixture.get("key")),
            }
        )
    return by_output


def preview_geometry_map(report: dict[str, Any]) -> dict[tuple[str, str, str, str], dict[str, Any]]:
    by_output = {}
    for record in report.get("records", []):
        if not isinstance(record, dict):
            continue
        key = (
            str(record.get("manifest_path")),
            str(record.get("asset_id")),
            str(record.get("kind")),
            str(record.get("path")),
        )
        geometry = {key: value for key, value in record.items() if key not in {"manifest_path", "asset_id", "kind", "path"}}
        by_output[key] = geometry
    return by_output


def manifest_paths(manifest_dir: Path) -> list[Path]:
    return sorted(manifest_dir.glob("*.json"))


def source_summary(asset: dict[str, Any]) -> dict[str, Any]:
    source = asset.get("source", {})
    if not isinstance(source, dict):
        source = {}
    return {
        "range": source.get("range"),
        "bytes": int(source.get("bytes", 0) or 0),
        "sha1": source.get("sha1"),
    }


def output_source_refs(output: dict[str, Any]) -> dict[str, str]:
    refs = {}
    for key in ("palette_source", "graphics_source"):
        source = output.get(key)
        if isinstance(source, dict) and isinstance(source.get("range"), str):
            refs[key] = str(source["range"])
    return refs


def build_index(
    manifest_dir: Path,
    *,
    smoke_plan: dict[str, Any] | None = None,
    preview_geometry_report: dict[str, Any] | None = None,
) -> dict[str, Any]:
    smoke_plan = smoke_plan if smoke_plan is not None else load_smoke_plan(manifest_dir)
    smoke_by_output = smoke_fixture_map(smoke_plan)
    preview_geometry_report = (
        preview_geometry_report
        if preview_geometry_report is not None
        else build_preview_geometry_report(manifest_dir)
    )
    preview_by_output = preview_geometry_map(preview_geometry_report)

    records: list[dict[str, Any]] = []
    asset_profiles: dict[tuple[str, str], dict[str, Any]] = {}
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
            manifest_key = rel(manifest_path)
            asset_key = (manifest_key, asset_id)
            source = source_summary(asset)
            profile = asset_profiles.setdefault(
                asset_key,
                {
                    "asset_id": asset_id,
                    "manifest_path": manifest_key,
                    "bank": bank,
                    "family": family["id"],
                    "category": asset.get("category"),
                    "output_count": 0,
                    "has_decoder": False,
                    "has_renderer": False,
                    "has_png_preview": False,
                    "has_smoke_fixture": False,
                },
            )
            outputs = asset.get("outputs", [])
            if not isinstance(outputs, list):
                outputs = []
            for output_index, output in enumerate(outputs):
                if not isinstance(output, dict):
                    continue
                kind = str(output.get("kind"))
                contract = OUTPUT_RECIPE_CONTRACTS.get(kind)
                if contract is None:
                    errors.append(f"{asset_id}: unsupported output kind {kind!r}")
                    continue
                path = str(output.get("path"))
                output_key = (manifest_key, asset_id, kind, path)
                smoke_fixtures = sorted(smoke_by_output.get(output_key, []), key=lambda item: item["id"])
                geometry = preview_by_output.get(output_key)
                profile["output_count"] += 1
                profile["has_decoder"] = bool(profile["has_decoder"] or contract.decoder is not None)
                profile["has_renderer"] = bool(profile["has_renderer"] or contract.renderer is not None)
                profile["has_png_preview"] = bool(profile["has_png_preview"] or contract.extension == ".png")
                profile["has_smoke_fixture"] = bool(profile["has_smoke_fixture"] or smoke_fixtures)
                records.append(
                    {
                        "asset_id": asset_id,
                        "title": asset.get("title"),
                        "manifest_path": manifest_key,
                        "bank": bank,
                        "family": family["id"],
                        "category": asset.get("category"),
                        "source": source,
                        "output_index": output_index,
                        "kind": kind,
                        "path": path,
                        "output_type": contract.output_type,
                        "decoder": contract.decoder,
                        "renderer": contract.renderer,
                        "extension": contract.extension,
                        "source_refs": output_source_refs(output),
                        "preview_geometry": geometry,
                        "smoke_fixtures": smoke_fixtures,
                    }
                )

    output_counts = Counter(str(record["kind"]) for record in records)
    renderer_counts = Counter(str(record["renderer"]) for record in records if record["renderer"] is not None)
    decoder_counts = Counter(str(record["decoder"]) for record in records if record["decoder"] is not None)
    family_output_counts: dict[str, Counter[str]] = defaultdict(Counter)
    family_renderer_counts: dict[str, Counter[str]] = defaultdict(Counter)
    family_asset_counts: Counter[str] = Counter()
    family_raw_only_assets: Counter[str] = Counter()
    family_smoke_assets: Counter[str] = Counter()
    family_smoke_outputs: Counter[str] = Counter()
    geometry_status_counts: Counter[str] = Counter()
    kind_smoke_counts: Counter[str] = Counter()

    for record in records:
        family = str(record["family"])
        kind = str(record["kind"])
        family_output_counts[family][kind] += 1
        if record["renderer"] is not None:
            family_renderer_counts[family][str(record["renderer"])] += 1
        if record["smoke_fixtures"]:
            kind_smoke_counts[kind] += 1
            family_smoke_outputs[family] += 1
        geometry = record.get("preview_geometry")
        if isinstance(geometry, dict):
            geometry_status_counts[str(geometry.get("status"))] += 1

    for profile in asset_profiles.values():
        family = str(profile["family"])
        family_asset_counts[family] += 1
        if profile["has_smoke_fixture"]:
            family_smoke_assets[family] += 1
        if profile["output_count"] > 0 and not profile["has_decoder"] and not profile["has_renderer"]:
            family_raw_only_assets[family] += 1

    family_summaries = []
    for family in FAMILIES:
        family_id = family["id"]
        family_records = [record for record in records if record["family"] == family_id]
        family_summaries.append(
            {
                "id": family_id,
                "label": family["label"],
                "banks": family["banks"],
                "asset_count": family_asset_counts[family_id],
                "output_count": len(family_records),
                "decoder_output_count": sum(1 for record in family_records if record["decoder"] is not None),
                "renderer_output_count": sum(1 for record in family_records if record["renderer"] is not None),
                "png_output_count": sum(1 for record in family_records if record["extension"] == ".png"),
                "smoke_fixture_output_count": family_smoke_outputs[family_id],
                "smoke_fixture_asset_count": family_smoke_assets[family_id],
                "raw_only_asset_count": family_raw_only_assets[family_id],
                "output_kind_counts": dict(sorted(family_output_counts[family_id].items())),
                "renderer_counts": dict(sorted(family_renderer_counts[family_id].items())),
            }
        )

    recipe_summaries = []
    for kind, contract in sorted(OUTPUT_RECIPE_CONTRACTS.items()):
        recipe_records = [record for record in records if record["kind"] == kind]
        geometry_counts = Counter()
        for record in recipe_records:
            geometry = record.get("preview_geometry")
            if isinstance(geometry, dict):
                geometry_counts[str(geometry.get("status"))] += 1
        recipe_summaries.append(
            {
                "kind": kind,
                "output_type": contract.output_type,
                "decoder": contract.decoder,
                "renderer": contract.renderer,
                "output_count": output_counts[kind],
                "asset_count": len({(record["manifest_path"], record["asset_id"]) for record in recipe_records}),
                "smoke_fixture_output_count": kind_smoke_counts[kind],
                "geometry_status_counts": dict(sorted(geometry_counts.items())),
            }
        )

    return {
        "schema": "earthbound-decomp.asset-output-index.v1",
        "inputs": {
            "manifest_dir": rel(manifest_dir),
            "recipe_contract_module": "tools/asset_output_recipe_contracts.py",
            "smoke_fixture_plan": rel(DEFAULT_SMOKE_FIXTURES),
            "preview_geometry_report": "notes/asset-output-preview-geometry.md",
        },
        "source_policy": {
            "contains_rom_derived_outputs": False,
            "records_typed_output_recipes_only": True,
        },
        "source_refs_report": rel(SOURCE_REFS_MARKDOWN),
        "totals": {
            "assets": len(asset_profiles),
            "outputs": len(records),
            "output_kinds": len(output_counts),
            "decoder_outputs": sum(decoder_counts.values()),
            "renderer_outputs": sum(renderer_counts.values()),
            "png_outputs": sum(1 for record in records if record["extension"] == ".png"),
            "smoke_fixture_selectors": len(smoke_plan.get("fixtures", [])),
            "smoke_fixture_outputs": sum(1 for record in records if record["smoke_fixtures"]),
            "smoke_fixture_assets": sum(1 for profile in asset_profiles.values() if profile["has_smoke_fixture"]),
            "raw_only_assets": sum(1 for profile in asset_profiles.values() if profile["output_count"] > 0 and not profile["has_decoder"] and not profile["has_renderer"]),
        },
        "output_kind_counts": dict(sorted(output_counts.items())),
        "decoder_counts": dict(sorted(decoder_counts.items())),
        "renderer_counts": dict(sorted(renderer_counts.items())),
        "preview_geometry_status_counts": dict(sorted(geometry_status_counts.items())),
        "families": family_summaries,
        "recipes": recipe_summaries,
        "records": records,
        "errors": errors,
        "status": "ok" if not errors else "invalid",
    }


def render_markdown(index: dict[str, Any]) -> str:
    totals = index["totals"]
    lines = [
        "# Asset Output Index",
        "",
        "Generated by `tools/build_asset_output_index.py` from checked-in asset manifests, the typed output recipe registry, smoke fixture selectors, and static preview geometry metadata.",
        "",
        "This is a ROM-free inventory of typed asset outputs. The machine-readable record list is written to ignored `build/asset-output-index.json`; this checked-in note summarizes coverage pressure and fixture links.",
        "",
        "Palette and graphics source-reference coverage for these outputs is tracked in `notes/asset-output-source-refs.md`.",
        "",
        "Generated asset-output reports are freshness-checked together with `tools/validate_asset_output_reports.py`.",
        "",
        "## Snapshot",
        "",
        f"- status: `{index['status']}`",
        f"- assets with typed outputs: `{totals['assets']}`",
        f"- typed output records: `{totals['outputs']}`",
        f"- output recipe kinds: `{totals['output_kinds']}`",
        f"- decoder-backed outputs: `{totals['decoder_outputs']}`",
        f"- renderer-backed outputs: `{totals['renderer_outputs']}`",
        f"- PNG preview/render outputs: `{totals['png_outputs']}`",
        f"- smoke fixture selectors: `{totals['smoke_fixture_selectors']}`",
        f"- distinct smoke target outputs: `{totals['smoke_fixture_outputs']}`",
        f"- smoke fixture assets: `{totals['smoke_fixture_assets']}`",
        f"- raw-only assets: `{totals['raw_only_assets']}`",
        f"- preview geometry status mix: {compact_counts(index['preview_geometry_status_counts'])}",
        "",
        "## Family Output Coverage",
        "",
        "| Family | Assets | Outputs | Decoder | Renderer | PNG | Smoke outputs | Smoke assets | Raw-only assets | Output mix | Renderer mix |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |",
    ]
    for family in index["families"]:
        lines.append(
            "| {label} | {assets} | {outputs} | {decoder} | {renderer} | {png} | {smoke_outputs} | {smoke_assets} | {raw_only} | {output_mix} | {renderer_mix} |".format(
                label=family["label"],
                assets=family["asset_count"],
                outputs=family["output_count"],
                decoder=family["decoder_output_count"],
                renderer=family["renderer_output_count"],
                png=family["png_output_count"],
                smoke_outputs=family["smoke_fixture_output_count"],
                smoke_assets=family["smoke_fixture_asset_count"],
                raw_only=family["raw_only_asset_count"],
                output_mix=compact_counts(family["output_kind_counts"]),
                renderer_mix=compact_counts(family["renderer_counts"]),
            )
        )

    lines.extend(
        [
            "",
            "## Recipe Output Coverage",
            "",
            "| Recipe kind | Outputs | Assets | Decoder | Renderer | Smoke targets | Geometry status |",
            "| --- | ---: | ---: | --- | --- | ---: | --- |",
        ]
    )
    for recipe in index["recipes"]:
        lines.append(
            "| {kind} | {outputs} | {assets} | {decoder} | {renderer} | {smoke} | {geometry} |".format(
                kind=f"`{recipe['kind']}`",
                outputs=recipe["output_count"],
                assets=recipe["asset_count"],
                decoder=f"`{recipe['decoder']}`" if recipe["decoder"] else "-",
                renderer=f"`{recipe['renderer']}`" if recipe["renderer"] else "-",
                smoke=recipe["smoke_fixture_output_count"],
                geometry=compact_counts(recipe["geometry_status_counts"]),
            )
        )

    if index["errors"]:
        lines.extend(["", "## Errors", ""])
        for error in index["errors"]:
            lines.append(f"- {error}")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a ROM-free typed asset output index.")
    parser.add_argument("--manifest-dir", default=str(DEFAULT_MANIFEST_DIR))
    parser.add_argument("--json-out", default=str(DEFAULT_JSON_OUT))
    parser.add_argument("--markdown-out", default=str(DEFAULT_MARKDOWN_OUT))
    args = parser.parse_args()

    index = build_index(Path(args.manifest_dir))

    json_out = Path(args.json_out)
    json_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(json.dumps(index, indent=2) + "\n", encoding="utf-8")

    markdown_out = Path(args.markdown_out)
    markdown_out.parent.mkdir(parents=True, exist_ok=True)
    markdown_out.write_text(render_markdown(index), encoding="utf-8")

    totals = index["totals"]
    print(
        "asset output index: "
        f"{index['status']}, "
        f"{totals['outputs']} outputs, "
        f"{totals['renderer_outputs']} renderer-backed, "
        f"{totals['smoke_fixture_outputs']} smoke targets"
    )
    if index["errors"]:
        for error in index["errors"]:
            print(f"ERROR {error}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
