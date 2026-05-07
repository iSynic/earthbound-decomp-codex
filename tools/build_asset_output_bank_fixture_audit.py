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
from build_asset_output_recipe_contracts import compact_counts, family_for_bank, load_manifest_assets, rel
from build_asset_output_smoke_fixtures import (
    TARGET_BANK_OUTPUT_FIXTURE_BANKS,
    bank_output_priority,
    build_fixture_plan,
    build_output_candidates,
)


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MANIFEST_DIR = ROOT / "asset-manifests"
DEFAULT_JSON_OUT = ROOT / "build" / "asset-output-bank-fixture-audit.json"
DEFAULT_MARKDOWN_OUT = ROOT / "notes" / "asset-output-bank-fixture-audit.md"


def candidate_tier(output: dict[str, Any]) -> str:
    contract = OUTPUT_RECIPE_CONTRACTS[str(output["kind"])]
    if contract.renderer is not None:
        return "renderer"
    if contract.decoder is not None:
        return "decoder_only"
    return "metadata_only"


def output_key(asset: dict[str, Any], output: dict[str, Any]) -> tuple[str, str, str, str]:
    return (
        str(asset["manifest_path"]),
        str(asset["id"]),
        str(output["kind"]),
        str(output["path"]),
    )


def fixture_output_key(fixture: dict[str, Any]) -> tuple[str, str, str, str] | None:
    target = fixture.get("target_output")
    if not isinstance(target, dict):
        return None
    return (
        str(fixture.get("manifest_path")),
        str(fixture.get("asset_id")),
        str(target.get("kind")),
        str(target.get("path")),
    )


def bank_fixture_candidates(
    manifest_dir: Path,
) -> tuple[dict[str, list[tuple[dict[str, Any], dict[str, Any]]]], Counter[str]]:
    assets = load_manifest_assets(manifest_dir)
    candidates_by_bank: dict[str, list[tuple[dict[str, Any], dict[str, Any]]]] = defaultdict(list)
    output_counts_by_bank: Counter[str] = Counter()
    for asset, output in build_output_candidates(assets):
        bank = str(asset["bank"])
        kind = str(output["kind"])
        contract = OUTPUT_RECIPE_CONTRACTS[kind]
        if kind != "raw":
            output_counts_by_bank[bank] += 1
        if (
            bank in TARGET_BANK_OUTPUT_FIXTURE_BANKS
            and kind != "raw"
            and (contract.decoder is not None or contract.renderer is not None)
        ):
            candidates_by_bank[bank].append((asset, output))
    return candidates_by_bank, output_counts_by_bank


def build_report(manifest_dir: Path, *, smoke_plan: dict[str, Any] | None = None) -> dict[str, Any]:
    smoke_plan = smoke_plan if smoke_plan is not None else build_fixture_plan(manifest_dir)
    candidates_by_bank, output_counts_by_bank = bank_fixture_candidates(manifest_dir)
    fixtures_by_bank: dict[str, list[dict[str, Any]]] = defaultdict(list)
    errors: list[str] = []

    for fixture in smoke_plan.get("fixtures", []):
        if not isinstance(fixture, dict) or fixture.get("type") != "bank_output":
            continue
        bank = str(fixture.get("bank"))
        fixtures_by_bank[bank].append(fixture)
        if bank not in TARGET_BANK_OUTPUT_FIXTURE_BANKS:
            errors.append(f"{bank}: bank_output fixture is outside the target policy bank set")

    bank_records = []
    for bank in sorted(TARGET_BANK_OUTPUT_FIXTURE_BANKS):
        family = family_for_bank(bank)
        candidates = sorted(
            candidates_by_bank.get(bank, []),
            key=lambda item: bank_output_priority(item[0], item[1]),
        )
        fixtures = fixtures_by_bank.get(bank, [])
        selected = fixtures[0] if fixtures else None
        expected = candidates[0] if candidates else None
        tier_counts = Counter(candidate_tier(output) for _asset, output in candidates)
        kind_counts = Counter(str(output["kind"]) for _asset, output in candidates)
        status = "ok"
        selected_record = None

        if len(fixtures) > 1:
            status = "invalid"
            errors.append(f"{bank}: expected one bank_output fixture, found {len(fixtures)}")

        if candidates and selected is None:
            status = "invalid"
            errors.append(f"{bank}: typed non-raw outputs have no bank_output fixture")
        elif not candidates and selected is not None:
            status = "invalid"
            errors.append(f"{bank}: bank_output fixture exists but bank has no typed non-raw candidates")
        elif not candidates:
            status = "no_typed_non_raw_outputs"

        if selected is not None:
            selected_key = fixture_output_key(selected)
            expected_key = output_key(expected[0], expected[1]) if expected is not None else None
            target = selected.get("target_output", {})
            if selected_key != expected_key:
                status = "invalid"
                errors.append(f"{bank}: bank_output fixture is not the deterministic priority candidate")
            selected_record = {
                "fixture_id": selected.get("id"),
                "asset_id": selected.get("asset_id"),
                "manifest_path": selected.get("manifest_path"),
                "kind": target.get("kind") if isinstance(target, dict) else None,
                "path": target.get("path") if isinstance(target, dict) else None,
                "decoder": target.get("decoder") if isinstance(target, dict) else None,
                "renderer": target.get("renderer") if isinstance(target, dict) else None,
                "tier": candidate_tier({"kind": target.get("kind")}) if isinstance(target, dict) else None,
            }

        bank_records.append(
            {
                "bank": bank,
                "family": family["id"],
                "label": family["label"],
                "typed_non_raw_output_count": output_counts_by_bank[bank],
                "bank_fixture_candidate_count": len(candidates),
                "candidate_tier_counts": dict(sorted(tier_counts.items())),
                "candidate_kind_counts": dict(sorted(kind_counts.items())),
                "selected": selected_record,
                "status": status,
            }
        )

    status_counts = Counter(str(record["status"]) for record in bank_records)
    return {
        "schema": "earthbound-decomp.asset-output-bank-fixture-audit.v1",
        "inputs": {
            "manifest_dir": rel(manifest_dir),
            "smoke_fixture_plan": "notes/asset-output-smoke-fixtures.json",
            "recipe_contract_module": "tools/asset_output_recipe_contracts.py",
        },
        "source_policy": {
            "contains_rom_derived_outputs": False,
            "audits_generated_smoke_fixture_selectors_only": True,
        },
        "coverage_policy": {
            "target_banks": sorted(TARGET_BANK_OUTPUT_FIXTURE_BANKS),
            "selector_priority": [
                "renderer-backed typed non-raw outputs",
                "decoder-only typed non-raw outputs",
                "manifest path, asset id, output path",
            ],
        },
        "totals": {
            "target_policy_banks": len(TARGET_BANK_OUTPUT_FIXTURE_BANKS),
            "target_banks_with_typed_non_raw_outputs": sum(
                1 for record in bank_records if int(record["bank_fixture_candidate_count"]) > 0
            ),
            "target_banks_with_bank_output_fixtures": sum(1 for record in bank_records if record["selected"]),
            "target_banks_without_typed_non_raw_outputs": status_counts["no_typed_non_raw_outputs"],
            "invalid_banks": status_counts["invalid"],
        },
        "status_counts": dict(sorted(status_counts.items())),
        "banks": bank_records,
        "errors": errors,
        "status": "ok" if not errors else "invalid",
    }


def render_markdown(report: dict[str, Any]) -> str:
    totals = report["totals"]
    lines = [
        "# Asset Output Bank Fixture Audit",
        "",
        "Generated by `tools/build_asset_output_bank_fixture_audit.py` from checked-in asset manifests, the typed output recipe registry, and generated smoke fixture selectors.",
        "",
        "This ROM-free audit verifies the `bank_output` fixture policy: each target graphics/map/UI/battle/sprite bank with typed non-raw outputs gets one deterministic representative selector, while target banks that are still raw-only stay explicit.",
        "",
        "Generated asset-output reports are freshness-checked together with `tools/validate_asset_output_reports.py`.",
        "",
        "## Snapshot",
        "",
        f"- status: `{report['status']}`",
        f"- target policy banks: `{totals['target_policy_banks']}`",
        f"- target banks with typed non-raw outputs: `{totals['target_banks_with_typed_non_raw_outputs']}`",
        f"- target banks with bank-output fixtures: `{totals['target_banks_with_bank_output_fixtures']}`",
        f"- target banks without typed non-raw outputs: `{totals['target_banks_without_typed_non_raw_outputs']}`",
        f"- invalid banks: `{totals['invalid_banks']}`",
        f"- status mix: {compact_counts(report['status_counts'])}",
        "",
        "## Bank Fixtures",
        "",
        "| Bank | Status | Candidates | Tiers | Selected asset | Target recipe | Target output |",
        "| --- | --- | ---: | --- | --- | --- | --- |",
    ]
    for bank in report["banks"]:
        selected = bank.get("selected")
        if isinstance(selected, dict):
            asset = f"`{selected['asset_id']}`"
            kind = f"`{selected['kind']}`"
            path = f"`{selected['path']}`"
        else:
            asset = "-"
            kind = "-"
            path = "-"
        lines.append(
            "| {bank} | `{status}` | {candidates} | {tiers} | {asset} | {kind} | {path} |".format(
                bank=f"`{bank['bank']}`",
                status=bank["status"],
                candidates=bank["bank_fixture_candidate_count"],
                tiers=compact_counts(bank["candidate_tier_counts"]),
                asset=asset,
                kind=kind,
                path=path,
            )
        )

    if report["errors"]:
        lines.extend(["", "## Errors", ""])
        for error in report["errors"]:
            lines.append(f"- {error}")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a ROM-free audit of bank-level smoke fixture selectors.")
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
        "asset output bank fixture audit: "
        f"{report['status']}, "
        f"{totals['target_banks_with_bank_output_fixtures']} covered banks, "
        f"{totals['invalid_banks']} invalid banks"
    )
    if report["errors"]:
        for error in report["errors"]:
            print(f"ERROR {error}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
