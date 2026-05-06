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
from build_asset_output_recipe_contracts import FAMILIES, compact_counts, load_manifest_assets, rel


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MANIFEST_DIR = ROOT / "asset-manifests"
DEFAULT_JSON_OUT = ROOT / "notes" / "asset-output-smoke-fixtures.json"
DEFAULT_MARKDOWN_OUT = ROOT / "notes" / "asset-output-smoke-fixtures.md"


def asset_sort_key(asset: dict[str, Any]) -> tuple[str, str]:
    return (str(asset["manifest_path"]), str(asset["id"]))


def output_sort_key(output: dict[str, Any]) -> tuple[str, str]:
    return (str(output.get("kind", "")), str(output.get("path", "")))


def fixture_id(prefix: str, *parts: str) -> str:
    cleaned = ["".join(char.lower() if char.isalnum() else "_" for char in part).strip("_") for part in parts]
    return ".".join([prefix, *cleaned])


def output_summary(output: dict[str, Any]) -> dict[str, Any]:
    kind = str(output["kind"])
    contract = OUTPUT_RECIPE_CONTRACTS[kind]
    return {
        "kind": kind,
        "path": output["path"],
        "decoder": contract.decoder,
        "renderer": contract.renderer,
    }


def make_fixture(
    fixture_type: str,
    fixture_key: str,
    asset: dict[str, Any],
    output: dict[str, Any],
    *,
    reason: str,
) -> dict[str, Any]:
    return {
        "id": fixture_id("fixture", fixture_type, fixture_key),
        "type": fixture_type,
        "key": fixture_key,
        "reason": reason,
        "family": asset["family"],
        "bank": asset["bank"],
        "manifest_path": asset["manifest_path"],
        "asset_id": asset["id"],
        "title": asset["title"],
        "category": asset["category"],
        "bytes": asset["bytes"],
        "target_output": output_summary(output),
        "all_output_kinds": sorted({str(item.get("kind")) for item in asset["outputs"] if isinstance(item, dict)}),
    }


def build_output_candidates(assets: list[dict[str, Any]]) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    candidates: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for asset in sorted(assets, key=asset_sort_key):
        outputs = [output for output in asset["outputs"] if isinstance(output, dict)]
        for output in sorted(outputs, key=output_sort_key):
            kind = output.get("kind")
            if isinstance(kind, str) and kind in OUTPUT_RECIPE_CONTRACTS:
                candidates.append((asset, output))
    return candidates


def first_candidate(
    candidates: list[tuple[dict[str, Any], dict[str, Any]]],
    predicate,
) -> tuple[dict[str, Any], dict[str, Any]] | None:
    for asset, output in candidates:
        if predicate(asset, output):
            return asset, output
    return None


def command_groups(fixtures: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, set[str]] = defaultdict(set)
    for fixture in fixtures:
        grouped[str(fixture["manifest_path"])].add(str(fixture["asset_id"]))
    groups = []
    for manifest_path in sorted(grouped):
        groups.append(
            {
                "manifest_path": manifest_path,
                "asset_ids": sorted(grouped[manifest_path]),
                "extract_command": (
                    "python tools/extract_assets.py "
                    f"--manifest {manifest_path} "
                    + " ".join(f"--asset-id {asset_id}" for asset_id in sorted(grouped[manifest_path]))
                    + " --out build/asset-output-smoke-fixtures"
                ),
            }
        )
    return groups


def build_fixture_plan(manifest_dir: Path) -> dict[str, Any]:
    assets = load_manifest_assets(manifest_dir)
    candidates = build_output_candidates(assets)
    fixtures: list[dict[str, Any]] = []

    output_counts: Counter[str] = Counter()
    family_renderer_counts: Counter[tuple[str, str]] = Counter()
    family_decoder_counts: Counter[tuple[str, str]] = Counter()
    family_output_counts: dict[str, Counter[str]] = defaultdict(Counter)
    for asset, output in candidates:
        kind = str(output["kind"])
        contract = OUTPUT_RECIPE_CONTRACTS[kind]
        output_counts[kind] += 1
        family_output_counts[str(asset["family"])][kind] += 1
        if contract.renderer is not None:
            family_renderer_counts[(str(asset["family"]), contract.renderer)] += 1
        if contract.decoder is not None:
            family_decoder_counts[(str(asset["family"]), contract.decoder)] += 1

    for kind in sorted(output_counts):
        selected = first_candidate(candidates, lambda _asset, output, wanted=kind: output["kind"] == wanted)
        if selected is None:
            raise ValueError(f"No fixture candidate found for output kind {kind}")
        asset, output = selected
        fixtures.append(
            make_fixture(
                "recipe_kind",
                kind,
                asset,
                output,
                reason="Covers one typed output recipe kind.",
            )
        )

    for family, renderer in sorted(family_renderer_counts):
        selected = first_candidate(
            candidates,
            lambda asset, output, wanted_family=family, wanted_renderer=renderer: (
                asset["family"] == wanted_family
                and OUTPUT_RECIPE_CONTRACTS[str(output["kind"])].renderer == wanted_renderer
            ),
        )
        if selected is None:
            raise ValueError(f"No fixture candidate found for {family}/{renderer}")
        asset, output = selected
        fixtures.append(
            make_fixture(
                "family_renderer",
                f"{family}.{renderer}",
                asset,
                output,
                reason="Covers one renderer in one asset family.",
            )
        )

    for family, decoder in sorted(family_decoder_counts):
        selected = first_candidate(
            candidates,
            lambda asset, output, wanted_family=family, wanted_decoder=decoder: (
                asset["family"] == wanted_family
                and OUTPUT_RECIPE_CONTRACTS[str(output["kind"])].decoder == wanted_decoder
            ),
        )
        if selected is None:
            raise ValueError(f"No fixture candidate found for {family}/{decoder}")
        asset, output = selected
        fixtures.append(
            make_fixture(
                "family_decoder",
                f"{family}.{decoder}",
                asset,
                output,
                reason="Covers one decoder chain in one asset family.",
            )
        )

    fixture_ids = [str(fixture["id"]) for fixture in fixtures]
    duplicates = [fixture_id for fixture_id, count in Counter(fixture_ids).items() if count > 1]
    if duplicates:
        raise ValueError(f"Duplicate fixture ids: {duplicates}")

    selected_asset_ids = sorted({str(fixture["asset_id"]) for fixture in fixtures})
    selected_manifest_asset_pairs = sorted(
        {(str(fixture["manifest_path"]), str(fixture["asset_id"])) for fixture in fixtures}
    )
    family_counts = Counter(str(fixture["family"]) for fixture in fixtures)
    type_counts = Counter(str(fixture["type"]) for fixture in fixtures)

    return {
        "schema": "earthbound-decomp.asset-output-smoke-fixtures.v1",
        "inputs": {
            "manifest_dir": rel(manifest_dir),
            "recipe_contract_module": "tools/asset_output_recipe_contracts.py",
            "recipe_contract_report": "notes/asset-output-recipe-contracts.md",
        },
        "tracked_json": rel(DEFAULT_JSON_OUT),
        "tracked_markdown": rel(DEFAULT_MARKDOWN_OUT),
        "source_policy": {
            "contains_rom_derived_outputs": False,
            "runner_requires_user_supplied_rom": True,
            "default_output_root": "build/asset-output-smoke-fixtures",
        },
        "coverage": {
            "fixture_count": len(fixtures),
            "unique_selected_assets": len(selected_asset_ids),
            "unique_selected_manifest_asset_pairs": len(selected_manifest_asset_pairs),
            "recipe_kinds_covered": len(output_counts),
            "family_renderer_pairs_covered": len(family_renderer_counts),
            "family_decoder_pairs_covered": len(family_decoder_counts),
            "fixture_type_counts": dict(sorted(type_counts.items())),
            "fixture_family_counts": dict(sorted(family_counts.items())),
        },
        "family_output_kind_counts": {
            family["id"]: dict(sorted(family_output_counts[family["id"]].items())) for family in FAMILIES
        },
        "fixtures": fixtures,
        "command_groups": command_groups(fixtures),
        "runner": {
            "tool": "tools/run_asset_output_smoke_fixtures.py",
            "default_command": "python tools/run_asset_output_smoke_fixtures.py",
            "rom_command": "python tools/run_asset_output_smoke_fixtures.py --rom path/to/EarthBound.sfc",
        },
    }


def render_markdown(plan: dict[str, Any]) -> str:
    coverage = plan["coverage"]
    lines = [
        "# Asset Output Smoke Fixtures",
        "",
        "Generated by `tools/build_asset_output_smoke_fixtures.py` from checked-in asset manifests and the typed output recipe registry.",
        "",
        "This is the reproducible smoke-test selector set for extraction, decode, and preview/render recipes. It contains no ROM-derived outputs; `tools/run_asset_output_smoke_fixtures.py` executes these selectors when a user-supplied ROM is available.",
        "",
        "## Snapshot",
        "",
        f"- fixture selectors: `{coverage['fixture_count']}`",
        f"- unique selected assets: `{coverage['unique_selected_assets']}`",
        f"- recipe kinds covered: `{coverage['recipe_kinds_covered']}`",
        f"- family/renderer pairs covered: `{coverage['family_renderer_pairs_covered']}`",
        f"- family/decoder pairs covered: `{coverage['family_decoder_pairs_covered']}`",
        f"- fixture type mix: {compact_counts(coverage['fixture_type_counts'])}",
        f"- fixture family mix: {compact_counts(coverage['fixture_family_counts'])}",
        "",
        "## Runner",
        "",
        "- validate selectors without a ROM: `python tools/run_asset_output_smoke_fixtures.py --dry-run`",
        "- execute smoke fixtures with a ROM: `python tools/run_asset_output_smoke_fixtures.py --rom path/to/EarthBound.sfc`",
        "- default output root: `build/asset-output-smoke-fixtures`",
        "",
        "## Recipe-Kind Fixtures",
        "",
        "| Recipe kind | Asset | Manifest | Target output | Decoder | Renderer |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for fixture in plan["fixtures"]:
        if fixture["type"] != "recipe_kind":
            continue
        output = fixture["target_output"]
        lines.append(
            "| `{kind}` | `{asset}` | `{manifest}` | `{path}` | {decoder} | {renderer} |".format(
                kind=fixture["key"],
                asset=fixture["asset_id"],
                manifest=fixture["manifest_path"],
                path=output["path"],
                decoder=f"`{output['decoder']}`" if output["decoder"] else "-",
                renderer=f"`{output['renderer']}`" if output["renderer"] else "-",
            )
        )

    lines.extend(
        [
            "",
            "## Family Renderer Fixtures",
            "",
            "| Family/renderer | Asset | Manifest | Target recipe | Target output |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for fixture in plan["fixtures"]:
        if fixture["type"] != "family_renderer":
            continue
        output = fixture["target_output"]
        lines.append(
            f"| `{fixture['key']}` | `{fixture['asset_id']}` | `{fixture['manifest_path']}` | `{output['kind']}` | `{output['path']}` |"
        )

    lines.extend(
        [
            "",
            "## Family Decoder Fixtures",
            "",
            "| Family/decoder | Asset | Manifest | Target recipe | Target output |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for fixture in plan["fixtures"]:
        if fixture["type"] != "family_decoder":
            continue
        output = fixture["target_output"]
        lines.append(
            f"| `{fixture['key']}` | `{fixture['asset_id']}` | `{fixture['manifest_path']}` | `{output['kind']}` | `{output['path']}` |"
        )

    lines.extend(
        [
            "",
            "## Extraction Command Groups",
            "",
            "| Manifest | Selected assets | Command |",
            "| --- | ---: | --- |",
        ]
    )
    for group in plan["command_groups"]:
        lines.append(
            f"| `{group['manifest_path']}` | {len(group['asset_ids'])} | `{group['extract_command']}` |"
        )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build reproducible asset output smoke fixtures.")
    parser.add_argument("--manifest-dir", default=str(DEFAULT_MANIFEST_DIR))
    parser.add_argument("--json-out", default=str(DEFAULT_JSON_OUT))
    parser.add_argument("--markdown-out", default=str(DEFAULT_MARKDOWN_OUT))
    args = parser.parse_args()

    plan = build_fixture_plan(Path(args.manifest_dir))

    json_out = Path(args.json_out)
    json_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")

    markdown_out = Path(args.markdown_out)
    markdown_out.parent.mkdir(parents=True, exist_ok=True)
    markdown_out.write_text(render_markdown(plan), encoding="utf-8")

    coverage = plan["coverage"]
    print(
        "asset output smoke fixtures: "
        f"{coverage['fixture_count']} fixtures, "
        f"{coverage['recipe_kinds_covered']} recipe kinds, "
        f"{coverage['family_renderer_pairs_covered']} family/renderers"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
