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

import extract_assets
import rom_tools
from build_asset_manifest_output_metadata import (
    SUMMARY_KEY,
    SUMMARY_SCHEMA,
    build_manifest_output_summary,
    load_smoke_plan,
)
from asset_output_recipe_contracts import validate_output_spec


ROOT = Path(__file__).resolve().parent.parent


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate checked-in asset manifests and optionally extract them."
    )
    parser.add_argument(
        "manifest",
        nargs="*",
        help="Manifest path(s). Defaults to asset-manifests/*.json.",
    )
    parser.add_argument("--rom", help="Optional explicit ROM path.")
    parser.add_argument(
        "--out",
        default="build/assets",
        help="Output root when --extract is enabled.",
    )
    parser.add_argument(
        "--extract",
        action="store_true",
        help="Extract every manifest and validate range hashes/output recipes.",
    )
    return parser.parse_args()


def manifest_paths(args: argparse.Namespace) -> list[Path]:
    if args.manifest:
        return [Path(path) for path in args.manifest]
    return sorted((ROOT / "asset-manifests").glob("*.json"))


def load(path: Path) -> dict[str, Any]:
    return extract_assets.load_manifest(path)


def validate_duplicate_ids(manifests: list[tuple[Path, dict[str, Any]]]) -> list[str]:
    ids: list[str] = []
    for _, manifest in manifests:
        ids.extend(str(asset["id"]) for asset in manifest["assets"])
    return [asset_id for asset_id, count in Counter(ids).items() if count > 1]


def validate_manifest(
    path: Path,
    manifest: dict[str, Any],
    smoke_fixtures_by_manifest: dict[str, list[dict[str, Any]]],
) -> tuple[int, int]:
    asset_ids = [asset.get("id") for asset in manifest["assets"]]
    missing_ids = [index for index, asset_id in enumerate(asset_ids) if not isinstance(asset_id, str)]
    if missing_ids:
        raise ValueError(f"{path}: assets missing string id at indices {missing_ids}")
    local_duplicates = [
        asset_id for asset_id, count in Counter(asset_ids).items() if count > 1
    ]
    if local_duplicates:
        raise ValueError(f"{path}: duplicate asset ids: {local_duplicates}")

    output_count = 0
    for asset in manifest["assets"]:
        extract_assets.asset_source(asset)
        outputs = asset.get("outputs")
        if not isinstance(outputs, list) or not outputs:
            raise ValueError(f"{path}: {asset['id']} has no outputs")
        for output in outputs:
            if not isinstance(output.get("kind"), str) or not isinstance(output.get("path"), str):
                raise ValueError(f"{path}: {asset['id']} has an invalid output spec")
            output_errors = validate_output_spec(output, str(asset["id"]))
            if output_errors:
                formatted = "\n  - ".join(output_errors)
                raise ValueError(f"{path}: typed output recipe validation failed:\n  - {formatted}")
            output_count += 1

    summary = manifest.get(SUMMARY_KEY)
    if not isinstance(summary, dict):
        raise ValueError(f"{path}: missing {SUMMARY_KEY}")
    if summary.get("schema") != SUMMARY_SCHEMA:
        raise ValueError(f"{path}: unsupported {SUMMARY_KEY}.schema")
    expected_summary = build_manifest_output_summary(path, manifest, smoke_fixtures_by_manifest)
    if summary != expected_summary:
        raise ValueError(
            f"{path}: {SUMMARY_KEY} is stale; run tools/build_asset_manifest_output_metadata.py"
        )
    return len(asset_ids), output_count


def main() -> int:
    args = parse_args()
    paths = manifest_paths(args)
    if not paths:
        raise SystemExit("No asset manifests found.")

    manifests = [(path, load(path)) for path in paths]
    duplicate_ids = validate_duplicate_ids(manifests)
    if duplicate_ids:
        raise SystemExit(f"Duplicate asset IDs across manifests: {duplicate_ids[:20]}")

    smoke_fixtures_by_manifest = load_smoke_plan(ROOT / "notes" / "asset-output-smoke-fixtures.json")
    total_assets = 0
    total_outputs = 0
    for path, manifest in manifests:
        asset_count, output_count = validate_manifest(path, manifest, smoke_fixtures_by_manifest)
        total_assets += asset_count
        total_outputs += output_count
        print(f"OK {path}: {asset_count} assets, {output_count} outputs")

    if args.extract:
        rom_path = rom_tools.find_rom(args.rom)
        rom = rom_tools.load_rom(rom_path)
        info = rom_tools.read_rom_info(rom_path)
        problems = rom_tools.verify_earthbound_us(info)
        if problems:
            formatted = "\n".join(f"- {problem}" for problem in problems)
            raise SystemExit(f"ROM verification failed:\n{formatted}")

        out_root = Path(args.out).resolve()
        for path, manifest in manifests:
            report = extract_assets.extract_assets(
                manifest=manifest,
                manifest_path=path.resolve(),
                rom_path=rom_path,
                rom=rom,
                out_root=out_root,
                selected_ids=set(),
                allow_range_mismatch=False,
            )
            report["rom_verified"] = True
            report["rom_info"] = info.to_dict()
            report_path = out_root / f"asset-extraction-report-{path.stem}.json"
            report_path.parent.mkdir(parents=True, exist_ok=True)
            report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
            print(f"EXTRACTED {path.name}: {report['asset_count']} assets -> {report_path}")

    print(f"Validated {len(manifests)} manifests, {total_assets} assets, {total_outputs} outputs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
