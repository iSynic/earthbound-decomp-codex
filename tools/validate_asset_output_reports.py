from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import build_asset_data_contract_frontier
import build_asset_output_index
import build_asset_output_path_audit
import build_asset_output_preview_geometry
import build_asset_output_raw_only_audit
import build_asset_output_recipe_contracts
import build_asset_output_source_refs
import build_asset_output_smoke_fixtures
import build_asset_source_range_audit
import validate_asset_output_codecs


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MANIFEST_DIR = ROOT / "asset-manifests"


@dataclass(frozen=True)
class CheckedReport:
    path: Path
    expected: str
    command: str
    data: dict[str, Any] | None = None


def normalize_text(text: str) -> str:
    return text.replace("\r\n", "\n")


def json_text(data: object) -> str:
    return json.dumps(data, indent=2) + "\n"


def load_existing(path: Path) -> str:
    if not path.exists():
        return ""
    return normalize_text(path.read_text(encoding="utf-8"))


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def build_checked_reports(manifest_dir: Path, *, include_codec: bool) -> list[CheckedReport]:
    reports: list[CheckedReport] = []

    smoke_plan = build_asset_output_smoke_fixtures.build_fixture_plan(manifest_dir)
    reports.append(
        CheckedReport(
            build_asset_output_smoke_fixtures.DEFAULT_JSON_OUT,
            json_text(smoke_plan),
            "python tools/build_asset_output_smoke_fixtures.py",
            smoke_plan,
        )
    )
    reports.append(
        CheckedReport(
            build_asset_output_smoke_fixtures.DEFAULT_MARKDOWN_OUT,
            build_asset_output_smoke_fixtures.render_markdown(smoke_plan),
            "python tools/build_asset_output_smoke_fixtures.py",
        )
    )

    recipe_contract = build_asset_output_recipe_contracts.build_contract(manifest_dir)
    reports.append(
        CheckedReport(
            build_asset_output_recipe_contracts.DEFAULT_MARKDOWN_OUT,
            build_asset_output_recipe_contracts.render_markdown(recipe_contract),
            "python tools/build_asset_output_recipe_contracts.py",
            recipe_contract,
        )
    )

    preview_geometry = build_asset_output_preview_geometry.build_report(manifest_dir)
    reports.append(
        CheckedReport(
            build_asset_output_preview_geometry.DEFAULT_MARKDOWN_OUT,
            build_asset_output_preview_geometry.render_markdown(preview_geometry),
            "python tools/build_asset_output_preview_geometry.py",
            preview_geometry,
        )
    )

    output_index = build_asset_output_index.build_index(
        manifest_dir,
        smoke_plan=smoke_plan,
        preview_geometry_report=preview_geometry,
    )
    reports.append(
        CheckedReport(
            build_asset_output_index.DEFAULT_MARKDOWN_OUT,
            build_asset_output_index.render_markdown(output_index),
            "python tools/build_asset_output_index.py",
            output_index,
        )
    )

    source_refs = build_asset_output_source_refs.build_report(manifest_dir)
    reports.append(
        CheckedReport(
            build_asset_output_source_refs.DEFAULT_MARKDOWN_OUT,
            build_asset_output_source_refs.render_markdown(source_refs),
            "python tools/build_asset_output_source_refs.py",
            source_refs,
        )
    )

    path_audit = build_asset_output_path_audit.build_report(manifest_dir)
    reports.append(
        CheckedReport(
            build_asset_output_path_audit.DEFAULT_MARKDOWN_OUT,
            build_asset_output_path_audit.render_markdown(path_audit),
            "python tools/build_asset_output_path_audit.py",
            path_audit,
        )
    )

    raw_only_audit = build_asset_output_raw_only_audit.build_report(manifest_dir)
    reports.append(
        CheckedReport(
            build_asset_output_raw_only_audit.DEFAULT_MARKDOWN_OUT,
            build_asset_output_raw_only_audit.render_markdown(raw_only_audit),
            "python tools/build_asset_output_raw_only_audit.py",
            raw_only_audit,
        )
    )

    source_range_audit = build_asset_source_range_audit.build_report(manifest_dir)
    reports.append(
        CheckedReport(
            build_asset_source_range_audit.DEFAULT_MARKDOWN_OUT,
            build_asset_source_range_audit.render_markdown(source_range_audit),
            "python tools/build_asset_source_range_audit.py",
            source_range_audit,
        )
    )

    frontier = build_asset_data_contract_frontier.build_frontier(manifest_dir)
    reports.append(
        CheckedReport(
            build_asset_data_contract_frontier.DEFAULT_MARKDOWN_OUT,
            build_asset_data_contract_frontier.render_markdown(frontier),
            "python tools/build_asset_data_contract_frontier.py",
            frontier,
        )
    )

    if include_codec:
        codec_report = validate_asset_output_codecs.run_validation(validate_asset_output_codecs.DEFAULT_OUT)
        reports.append(
            CheckedReport(
                validate_asset_output_codecs.DEFAULT_MARKDOWN_OUT,
                validate_asset_output_codecs.render_markdown(codec_report),
                "python tools/validate_asset_output_codecs.py",
                codec_report,
            )
        )

    return reports


def report_health_errors(report: CheckedReport) -> list[str]:
    data = report.data
    if data is None:
        return []
    errors: list[str] = []
    status = data.get("status")
    if status is not None and status != "ok":
        errors.append(f"{rel(report.path)} generated status is {status!r}; run `{report.command}` and inspect errors")
    report_errors = data.get("errors")
    if isinstance(report_errors, list) and report_errors:
        errors.append(f"{rel(report.path)} generated {len(report_errors)} error(s); run `{report.command}`")
    return errors


def validate_reports(manifest_dir: Path, *, include_codec: bool) -> list[str]:
    errors: list[str] = []
    for report in build_checked_reports(manifest_dir, include_codec=include_codec):
        expected = normalize_text(report.expected)
        existing = load_existing(report.path)
        if existing != expected:
            if not report.path.exists():
                errors.append(f"{rel(report.path)} is missing; run `{report.command}`")
            else:
                errors.append(f"{rel(report.path)} is stale; run `{report.command}`")
        errors.extend(report_health_errors(report))
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate generated asset output reports are fresh.")
    parser.add_argument("--manifest-dir", default=str(DEFAULT_MANIFEST_DIR))
    parser.add_argument(
        "--skip-codec",
        action="store_true",
        help="Skip synthetic codec validation freshness; by default it also rebuilds ignored build/ codec outputs.",
    )
    args = parser.parse_args()

    errors = validate_reports(Path(args.manifest_dir), include_codec=not args.skip_codec)
    if errors:
        print("asset output report freshness: invalid")
        for error in errors:
            print(f"ERROR {error}")
        return 1
    print("asset output report freshness: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
