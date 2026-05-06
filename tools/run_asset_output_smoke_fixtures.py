from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import extract_assets
import rom_tools


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_FIXTURES = ROOT / "notes" / "asset-output-smoke-fixtures.json"
DEFAULT_OUT = ROOT / "build" / "asset-output-smoke-fixtures"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run selected asset output smoke fixtures.")
    parser.add_argument("--fixtures", default=str(DEFAULT_FIXTURES))
    parser.add_argument("--rom", default=None, help="Path to the EarthBound ROM.")
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate fixture selectors and print the planned extraction groups without requiring a ROM.",
    )
    parser.add_argument(
        "--require-rom",
        action="store_true",
        help="Return an error instead of skip when no ROM is available.",
    )
    parser.add_argument(
        "--allow-rom-mismatch",
        action="store_true",
        help="Continue when the ROM header/SHA-1 does not match EarthBound US.",
    )
    parser.add_argument(
        "--allow-range-mismatch",
        action="store_true",
        help="Write outputs even when a manifest range SHA-1 does not match.",
    )
    return parser.parse_args()


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def load_plan(path: Path) -> dict[str, Any]:
    plan = json.loads(path.read_text(encoding="utf-8"))
    if plan.get("schema") != "earthbound-decomp.asset-output-smoke-fixtures.v1":
        raise ValueError(f"Unsupported smoke-fixture schema in {path}")
    if not isinstance(plan.get("fixtures"), list):
        raise ValueError(f"Fixture plan has no fixtures list: {path}")
    if not isinstance(plan.get("command_groups"), list):
        raise ValueError(f"Fixture plan has no command_groups list: {path}")
    return plan


def manifest_path(text: str) -> Path:
    path = Path(text)
    if not path.is_absolute():
        path = ROOT / path
    return path


def validate_selectors(plan: dict[str, Any]) -> dict[str, Any]:
    fixture_ids = set()
    fixture_count_by_type: dict[str, int] = {}
    selected_by_manifest: dict[str, set[str]] = {}

    for fixture in plan["fixtures"]:
        fixture_id = fixture.get("id")
        if not isinstance(fixture_id, str):
            raise ValueError(f"Fixture is missing a string id: {fixture!r}")
        if fixture_id in fixture_ids:
            raise ValueError(f"Duplicate fixture id: {fixture_id}")
        fixture_ids.add(fixture_id)

        fixture_type = str(fixture.get("type"))
        fixture_count_by_type[fixture_type] = fixture_count_by_type.get(fixture_type, 0) + 1
        manifest = fixture.get("manifest_path")
        asset_id = fixture.get("asset_id")
        if not isinstance(manifest, str) or not isinstance(asset_id, str):
            raise ValueError(f"{fixture_id}: manifest_path and asset_id must be strings")
        selected_by_manifest.setdefault(manifest, set()).add(asset_id)

    manifest_asset_counts = {}
    for manifest, asset_ids in sorted(selected_by_manifest.items()):
        path = manifest_path(manifest)
        data = extract_assets.load_manifest(path)
        known_ids = {str(asset["id"]) for asset in data["assets"]}
        missing = sorted(asset_ids - known_ids)
        if missing:
            raise ValueError(f"{manifest}: fixture asset ids not found: {missing}")
        manifest_asset_counts[manifest] = len(asset_ids)

    command_group_assets = {
        str(group["manifest_path"]): set(str(asset_id) for asset_id in group["asset_ids"])
        for group in plan["command_groups"]
    }
    if command_group_assets != selected_by_manifest:
        raise ValueError("command_groups do not match fixture-selected asset ids")

    return {
        "fixture_count": len(fixture_ids),
        "fixture_type_counts": dict(sorted(fixture_count_by_type.items())),
        "manifest_asset_counts": manifest_asset_counts,
        "unique_selected_assets": len({asset_id for asset_ids in selected_by_manifest.values() for asset_id in asset_ids}),
    }


def find_rom_or_skip(explicit_path: str | None, require_rom: bool) -> Path | None:
    try:
        return rom_tools.find_rom(explicit_path)
    except FileNotFoundError as exc:
        if require_rom:
            raise
        print(f"SKIP asset output smoke fixtures: {exc}")
        return None


def run_plan(
    plan: dict[str, Any],
    *,
    rom_path: Path,
    out_root: Path,
    allow_rom_mismatch: bool,
    allow_range_mismatch: bool,
) -> dict[str, Any]:
    rom = rom_tools.load_rom(rom_path)
    info = rom_tools.read_rom_info(rom_path)
    problems = rom_tools.verify_earthbound_us(info)
    if problems and not allow_rom_mismatch:
        formatted = "\n".join(f"- {problem}" for problem in problems)
        raise SystemExit(
            "ROM verification failed for smoke fixtures:\n"
            f"{formatted}\n"
            f"Expected SHA-1: {rom_tools.EXPECTED_SHA1}"
        )

    reports = []
    for group in plan["command_groups"]:
        manifest = manifest_path(str(group["manifest_path"]))
        data = extract_assets.load_manifest(manifest)
        report = extract_assets.extract_assets(
            manifest=data,
            manifest_path=manifest.resolve(),
            rom_path=rom_path,
            rom=rom,
            out_root=out_root,
            selected_ids={str(asset_id) for asset_id in group["asset_ids"]},
            allow_range_mismatch=allow_range_mismatch,
        )
        reports.append(report)

    merged_assets = [asset for report in reports for asset in report["assets"]]
    output_count = sum(len(asset["outputs"]) for asset in merged_assets)
    result = {
        "schema": "earthbound-decomp.asset-output-smoke-fixtures-report.v1",
        "source_plan": plan.get("tracked_json", rel(DEFAULT_FIXTURES)),
        "rom": str(rom_path),
        "rom_sha1": hashlib.sha1(rom).hexdigest(),
        "rom_verified": not problems,
        "rom_info": info.to_dict(),
        "output_root": rel(out_root),
        "manifest_groups": len(reports),
        "asset_count": len(merged_assets),
        "output_count": output_count,
        "assets": merged_assets,
    }
    report_path = out_root / "asset-output-smoke-fixtures-report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def main() -> int:
    args = parse_args()
    plan_path = Path(args.fixtures)
    if not plan_path.is_absolute():
        plan_path = ROOT / plan_path
    plan = load_plan(plan_path)
    selector_summary = validate_selectors(plan)

    if args.dry_run:
        print(
            "asset output smoke fixtures dry-run: "
            f"{selector_summary['fixture_count']} fixtures, "
            f"{selector_summary['unique_selected_assets']} selected assets"
        )
        for manifest, count in selector_summary["manifest_asset_counts"].items():
            print(f"PLAN {manifest}: {count} asset(s)")
        return 0

    rom_path = find_rom_or_skip(args.rom, args.require_rom)
    if rom_path is None:
        return 0

    report = run_plan(
        plan,
        rom_path=rom_path,
        out_root=Path(args.out).resolve(),
        allow_rom_mismatch=args.allow_rom_mismatch,
        allow_range_mismatch=args.allow_range_mismatch,
    )
    print(
        "asset output smoke fixtures: "
        f"{report['asset_count']} assets, "
        f"{report['output_count']} outputs, "
        f"{report['manifest_groups']} manifest groups"
    )
    print(f"Wrote {Path(args.out).resolve() / 'asset-output-smoke-fixtures-report.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
