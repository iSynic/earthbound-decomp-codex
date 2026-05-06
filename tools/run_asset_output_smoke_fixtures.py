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
from asset_output_recipe_contracts import OUTPUT_RECIPE_CONTRACTS


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_FIXTURES = ROOT / "notes" / "asset-output-smoke-fixtures.json"
DEFAULT_OUT = ROOT / "build" / "asset-output-smoke-fixtures"
REPORT_ZERO_OK_FIELDS = {"arrangement_id", "graphics_id", "max_tile", "palette_id", "sprite_id"}


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
    fixtures_by_manifest: dict[str, list[dict[str, Any]]] = {}

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
        target_output = fixture.get("target_output")
        if not isinstance(target_output, dict):
            raise ValueError(f"{fixture_id}: target_output must be an object")
        kind = target_output.get("kind")
        path = target_output.get("path")
        if not isinstance(kind, str) or kind not in OUTPUT_RECIPE_CONTRACTS:
            raise ValueError(f"{fixture_id}: target_output.kind is unsupported: {kind!r}")
        if not isinstance(path, str) or not path:
            raise ValueError(f"{fixture_id}: target_output.path must be a non-empty string")
        contract = OUTPUT_RECIPE_CONTRACTS[kind]
        if target_output.get("decoder") != contract.decoder:
            raise ValueError(f"{fixture_id}: target_output.decoder is stale for {kind}")
        if target_output.get("renderer") != contract.renderer:
            raise ValueError(f"{fixture_id}: target_output.renderer is stale for {kind}")
        selected_by_manifest.setdefault(manifest, set()).add(asset_id)
        fixtures_by_manifest.setdefault(manifest, []).append(fixture)

    manifest_asset_counts = {}
    for manifest, asset_ids in sorted(selected_by_manifest.items()):
        path = manifest_path(manifest)
        data = extract_assets.load_manifest(path)
        assets_by_id = {str(asset["id"]): asset for asset in data["assets"]}
        known_ids = set(assets_by_id)
        missing = sorted(asset_ids - known_ids)
        if missing:
            raise ValueError(f"{manifest}: fixture asset ids not found: {missing}")
        for fixture in fixtures_by_manifest[manifest]:
            fixture_id = str(fixture["id"])
            asset_id = str(fixture["asset_id"])
            target_output = fixture["target_output"]
            target_kind = str(target_output["kind"])
            target_path = str(target_output["path"])
            asset = assets_by_id[asset_id]
            outputs = asset.get("outputs", [])
            if not isinstance(outputs, list):
                raise ValueError(f"{fixture_id}: asset outputs must be a list")
            if not any(
                isinstance(output, dict)
                and output.get("kind") == target_kind
                and output.get("path") == target_path
                for output in outputs
            ):
                raise ValueError(
                    f"{fixture_id}: target output not found on {asset_id}: "
                    f"{target_kind} {target_path}"
                )
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
        "target_outputs_checked": len(fixture_ids),
        "unique_selected_assets": len({asset_id for asset_ids in selected_by_manifest.values() for asset_id in asset_ids}),
    }


def report_output_relative_path(out_root: Path, output: dict[str, Any]) -> str:
    output_path = Path(str(output["path"]))
    if not output_path.is_absolute():
        return output_path.as_posix()
    resolved_root = out_root.resolve()
    resolved_output = output_path.resolve()
    try:
        return resolved_output.relative_to(resolved_root).as_posix()
    except ValueError:
        return resolved_output.as_posix()


def validate_report_output_file(output: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    path = Path(str(output["path"]))
    if not path.is_file():
        return [f"output file is missing: {path}"]
    data = path.read_bytes()
    if len(data) != int(output.get("bytes", -1)):
        errors.append(f"{path}: reported byte count does not match file size")
    sha1 = hashlib.sha1(data).hexdigest()
    if sha1 != output.get("sha1"):
        errors.append(f"{path}: reported SHA-1 does not match file content")
    return errors


def validate_report_metadata(output: dict[str, Any], fixture_id: str) -> list[str]:
    errors: list[str] = []
    kind = str(output.get("kind"))
    contract = OUTPUT_RECIPE_CONTRACTS[kind]
    for field in contract.report_required_fields:
        if field not in output:
            errors.append(f"{fixture_id}: {kind} report is missing {field!r}")
            continue
        value = output[field]
        if field.endswith("_range"):
            if not isinstance(value, str) or ":" not in value or ".." not in value:
                errors.append(f"{fixture_id}: {kind}.{field} must be a source range string")
        elif not isinstance(value, int):
            errors.append(f"{fixture_id}: {kind}.{field} must be an integer")
        elif field in REPORT_ZERO_OK_FIELDS and value < 0:
            errors.append(f"{fixture_id}: {kind}.{field} must be non-negative")
        elif field not in REPORT_ZERO_OK_FIELDS and value <= 0:
            errors.append(f"{fixture_id}: {kind}.{field} must be positive")
    return errors


def validate_report_preview_geometry(output: dict[str, Any], fixture: dict[str, Any]) -> tuple[list[str], int]:
    geometry = fixture.get("target_preview_geometry")
    if not isinstance(geometry, dict):
        return [], 0
    if geometry.get("status") != "known":
        return [], 0
    fixture_id = str(fixture["id"])
    errors: list[str] = []
    checked = 0
    for field in ("width", "height", "tiles", "colors"):
        expected = geometry.get(field)
        if expected is None:
            continue
        checked += 1
        actual = output.get(field)
        if actual != expected:
            errors.append(f"{fixture_id}: report {field}={actual!r}, expected {expected!r}")
    return errors, checked


def validate_smoke_report(plan: dict[str, Any], report: dict[str, Any], out_root: Path) -> dict[str, Any]:
    assets_by_id = {str(asset["id"]): asset for asset in report["assets"]}
    errors: list[str] = []
    verified_output_keys: set[tuple[str, str, str]] = set()
    metadata_field_checks = 0
    preview_geometry_field_checks = 0

    for fixture in plan["fixtures"]:
        fixture_id = str(fixture["id"])
        asset_id = str(fixture["asset_id"])
        target_output = fixture["target_output"]
        target_kind = str(target_output["kind"])
        target_path = str(target_output["path"])
        asset = assets_by_id.get(asset_id)
        if asset is None:
            errors.append(f"{fixture_id}: extracted report is missing asset {asset_id}")
            continue

        matched_output = None
        for output in asset.get("outputs", []):
            if not isinstance(output, dict):
                continue
            relative_path = report_output_relative_path(out_root, output)
            if output.get("kind") == target_kind and relative_path == target_path:
                matched_output = output
                break
        if matched_output is None:
            errors.append(f"{fixture_id}: missing target output {target_kind} {target_path}")
            continue

        if int(matched_output.get("bytes", 0) or 0) <= 0:
            errors.append(f"{fixture_id}: target output has no bytes: {target_path}")
        errors.extend(validate_report_output_file(matched_output))
        metadata_errors = validate_report_metadata(matched_output, fixture_id)
        errors.extend(metadata_errors)
        if not metadata_errors:
            metadata_field_checks += len(OUTPUT_RECIPE_CONTRACTS[target_kind].report_required_fields)
        geometry_errors, geometry_checks = validate_report_preview_geometry(matched_output, fixture)
        errors.extend(geometry_errors)
        preview_geometry_field_checks += geometry_checks
        verified_output_keys.add((asset_id, target_kind, target_path))

    if errors:
        raise ValueError("Smoke fixture report validation failed:\n- " + "\n- ".join(errors))

    return {
        "fixture_targets_checked": len(plan["fixtures"]),
        "unique_outputs_checked": len(verified_output_keys),
        "metadata_field_checks": metadata_field_checks,
        "preview_geometry_field_checks": preview_geometry_field_checks,
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
    result["fixture_validation"] = validate_smoke_report(plan, result, out_root)
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
            f"{selector_summary['target_outputs_checked']} target outputs, "
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
        f"{report['manifest_groups']} manifest groups, "
        f"{report['fixture_validation']['fixture_targets_checked']} fixture targets checked"
    )
    print(f"Wrote {Path(args.out).resolve() / 'asset-output-smoke-fixtures-report.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
