from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from asset_output_recipe_contracts import OUTPUT_RECIPE_CONTRACTS


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MANIFEST_DIR = ROOT / "asset-manifests"
DEFAULT_SMOKE_FIXTURES = ROOT / "notes" / "asset-output-smoke-fixtures.json"
SUMMARY_SCHEMA = "earthbound-decomp.asset-manifest-output-summary.v1"
SUMMARY_KEY = "typed_output_summary"


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def manifest_paths(manifest_dir: Path) -> list[Path]:
    return sorted(manifest_dir.glob("*.json"))


def load_smoke_plan(path: Path) -> dict[str, list[dict[str, Any]]]:
    if not path.exists():
        return {}
    plan = json.loads(path.read_text(encoding="utf-8"))
    if plan.get("schema") != "earthbound-decomp.asset-output-smoke-fixtures.v1":
        raise ValueError(f"Unsupported smoke fixture schema: {path}")
    by_manifest: dict[str, list[dict[str, Any]]] = {}
    for fixture in plan.get("fixtures", []):
        if not isinstance(fixture, dict):
            continue
        manifest_path = fixture.get("manifest_path")
        if isinstance(manifest_path, str):
            by_manifest.setdefault(manifest_path, []).append(fixture)
    return by_manifest


def build_manifest_output_summary(
    manifest_path: Path,
    manifest: dict[str, Any],
    smoke_fixtures_by_manifest: dict[str, list[dict[str, Any]]] | None = None,
) -> dict[str, Any]:
    smoke_fixtures_by_manifest = smoke_fixtures_by_manifest or {}
    outputs: list[dict[str, Any]] = []
    assets = manifest.get("assets", [])
    if not isinstance(assets, list):
        raise ValueError(f"{manifest_path}: assets must be a list")
    for asset in assets:
        if not isinstance(asset, dict):
            continue
        for output in asset.get("outputs", []):
            if isinstance(output, dict):
                outputs.append(output)

    output_kind_counts = Counter(str(output.get("kind")) for output in outputs)
    unknown_kinds = sorted(kind for kind in output_kind_counts if kind not in OUTPUT_RECIPE_CONTRACTS)
    if unknown_kinds:
        raise ValueError(f"{manifest_path}: unsupported output kind(s): {unknown_kinds}")
    decoder_counts: Counter[str] = Counter()
    renderer_counts: Counter[str] = Counter()
    for kind, count in output_kind_counts.items():
        contract = OUTPUT_RECIPE_CONTRACTS.get(kind)
        if contract is None:
            continue
        if contract.decoder is not None:
            decoder_counts[contract.decoder] += count
        if contract.renderer is not None:
            renderer_counts[contract.renderer] += count

    fixture_manifest_key = rel(manifest_path)
    fixtures = smoke_fixtures_by_manifest.get(fixture_manifest_key, [])
    fixture_asset_ids = sorted(
        {str(fixture["asset_id"]) for fixture in fixtures if isinstance(fixture.get("asset_id"), str)}
    )
    fixture_type_counts = Counter(str(fixture.get("type")) for fixture in fixtures)
    fixture_target_kinds = Counter(
        str(fixture.get("target_output", {}).get("kind"))
        for fixture in fixtures
        if isinstance(fixture.get("target_output"), dict)
    )

    return {
        "schema": SUMMARY_SCHEMA,
        "generator": {
            "tool": "tools/build_asset_manifest_output_metadata.py",
            "recipe_contract_module": "tools/asset_output_recipe_contracts.py",
            "smoke_fixture_plan": rel(DEFAULT_SMOKE_FIXTURES),
        },
        "asset_count": len(assets),
        "output_recipe_count": len(outputs),
        "typed_output_kind_count": len(output_kind_counts),
        "decoder_output_recipe_count": sum(
            count
            for kind, count in output_kind_counts.items()
            if OUTPUT_RECIPE_CONTRACTS[kind].decoder is not None
        ),
        "renderer_output_recipe_count": sum(
            count
            for kind, count in output_kind_counts.items()
            if OUTPUT_RECIPE_CONTRACTS[kind].renderer is not None
        ),
        "preview_png_recipe_count": sum(
            count for kind, count in output_kind_counts.items() if kind.endswith("_png")
        ),
        "output_kind_counts": dict(sorted(output_kind_counts.items())),
        "decoder_counts": dict(sorted(decoder_counts.items())),
        "renderer_counts": dict(sorted(renderer_counts.items())),
        "smoke_fixture_count": len(fixtures),
        "smoke_fixture_asset_ids": fixture_asset_ids,
        "smoke_fixture_type_counts": dict(sorted(fixture_type_counts.items())),
        "smoke_fixture_target_kind_counts": dict(sorted(fixture_target_kinds.items())),
    }


def ordered_manifest(manifest: dict[str, Any], summary: dict[str, Any]) -> dict[str, Any]:
    clean = {key: value for key, value in manifest.items() if key != SUMMARY_KEY}
    ordered: dict[str, Any] = {}
    preferred_order = [
        "schema",
        "game",
        "title",
        "source_policy",
        "generator",
        "references",
        "bank_summary",
        SUMMARY_KEY,
        "assets",
    ]
    for key in preferred_order:
        if key == SUMMARY_KEY:
            ordered[SUMMARY_KEY] = summary
        elif key in clean:
            ordered[key] = clean.pop(key)
    ordered.update(clean)
    return ordered


def update_manifest(path: Path, smoke_fixtures_by_manifest: dict[str, list[dict[str, Any]]]) -> bool:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    summary = build_manifest_output_summary(path, manifest, smoke_fixtures_by_manifest)
    updated = ordered_manifest(manifest, summary)
    new_text = json.dumps(updated, indent=2) + "\n"
    old_text = path.read_text(encoding="utf-8")
    if old_text == new_text:
        return False
    path.write_text(new_text, encoding="utf-8")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Stamp asset manifests with typed output metadata.")
    parser.add_argument("--manifest-dir", default=str(DEFAULT_MANIFEST_DIR))
    parser.add_argument("--smoke-fixtures", default=str(DEFAULT_SMOKE_FIXTURES))
    args = parser.parse_args()

    manifest_dir = Path(args.manifest_dir)
    smoke_path = Path(args.smoke_fixtures)
    smoke_fixtures_by_manifest = load_smoke_plan(smoke_path)

    changed = 0
    total = 0
    for path in manifest_paths(manifest_dir):
        total += 1
        if update_manifest(path, smoke_fixtures_by_manifest):
            changed += 1
    print(f"asset manifest output metadata: {changed}/{total} manifest(s) updated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
