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

from asset_output_recipe_contracts import OUTPUT_RECIPE_CONTRACTS, validate_output_spec


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MANIFEST_DIR = ROOT / "asset-manifests"
DEFAULT_JSON_OUT = ROOT / "build" / "asset-output-recipe-contracts.json"
DEFAULT_MARKDOWN_OUT = ROOT / "notes" / "asset-output-recipe-contracts.md"
SMOKE_FIXTURES_JSON = ROOT / "notes" / "asset-output-smoke-fixtures.json"
SMOKE_FIXTURES_MARKDOWN = ROOT / "notes" / "asset-output-smoke-fixtures.md"


FAMILIES: list[dict[str, Any]] = [
    {
        "id": "battle_visual_assets",
        "label": "Battle visual assets",
        "banks": ["CA", "CB", "CC", "CD", "CE"],
    },
    {
        "id": "mixed_asset_tables",
        "label": "Mixed asset/table banks",
        "banks": ["CF", "D0"],
    },
    {
        "id": "overworld_sprites",
        "label": "Overworld sprites",
        "banks": ["D1", "D2", "D3", "D4", "D5"],
    },
    {
        "id": "map_tilesets_and_runtime_tables",
        "label": "Map tilesets and runtime tables",
        "banks": ["D6", "D7", "D8", "D9", "DA", "DB", "DC", "DD", "DE", "DF"],
    },
    {
        "id": "ui_font_town_map_assets",
        "label": "UI, fonts, and town-map assets",
        "banks": ["E0", "E1"],
    },
    {
        "id": "audio_packs",
        "label": "Audio packs",
        "banks": ["E2", "E3", "E4", "E5", "E6", "E7", "E8", "E9", "EA", "EB", "EC", "ED", "EE"],
    },
    {
        "id": "ef_debug_and_late_tail",
        "label": "EF debug and late-tail data",
        "banks": ["EF"],
    },
]


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def infer_bank(path: Path, manifest: dict[str, Any]) -> str:
    if path.name.startswith("bank-"):
        return path.name.split("-", 2)[1].upper()
    title = str(manifest.get("title", ""))
    for token in title.replace("-", " ").split():
        if len(token) == 2:
            try:
                int(token, 16)
            except ValueError:
                continue
            return token.upper()
    if path.name.startswith("ef-"):
        return "EF"
    raise ValueError(f"Could not infer bank for {path}")


def family_for_bank(bank: str) -> dict[str, Any]:
    for family in FAMILIES:
        if bank in family["banks"]:
            return family
    raise ValueError(f"No asset-output family for bank {bank}")


def output_kinds(asset: dict[str, Any]) -> list[str]:
    outputs = asset.get("outputs", [])
    if not isinstance(outputs, list):
        return []
    return [str(output.get("kind", "unknown")) for output in outputs if isinstance(output, dict)]


def load_manifest_assets(manifest_dir: Path) -> list[dict[str, Any]]:
    assets: list[dict[str, Any]] = []
    for path in sorted(manifest_dir.glob("*.json")):
        manifest = json.loads(path.read_text(encoding="utf-8"))
        bank = infer_bank(path, manifest)
        family = family_for_bank(bank)
        for asset in manifest.get("assets", []):
            source = asset.get("source", {})
            if not isinstance(source, dict):
                source = {}
            assets.append(
                {
                    "id": asset.get("id"),
                    "title": asset.get("title"),
                    "bank": bank,
                    "family": family["id"],
                    "manifest_path": rel(path),
                    "category": asset.get("category"),
                    "bytes": int(source.get("bytes", 0) or 0),
                    "outputs": asset.get("outputs", []),
                }
            )
    return assets


def compact_counts(counts: dict[str, int], limit: int = 5) -> str:
    if not counts:
        return "-"
    parts = []
    for key, value in sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:limit]:
        parts.append(f"`{key}` {value}")
    remaining = len(counts) - limit
    if remaining > 0:
        parts.append(f"+{remaining} more")
    return ", ".join(parts)


def build_contract(manifest_dir: Path) -> dict[str, Any]:
    assets = load_manifest_assets(manifest_dir)
    manifest_files = sorted(manifest_dir.glob("*.json"))
    typed_manifest_summaries = 0
    smoke_linked_manifests = 0
    for path in manifest_files:
        manifest = json.loads(path.read_text(encoding="utf-8"))
        summary = manifest.get("typed_output_summary")
        if isinstance(summary, dict) and summary.get("schema") == "earthbound-decomp.asset-manifest-output-summary.v1":
            typed_manifest_summaries += 1
            if int(summary.get("smoke_fixture_count", 0) or 0) > 0:
                smoke_linked_manifests += 1
    errors: list[str] = []
    output_counts: Counter[str] = Counter()
    output_asset_counts: Counter[str] = Counter()
    output_bank_counts: dict[str, Counter[str]] = defaultdict(Counter)
    output_family_counts: dict[str, Counter[str]] = defaultdict(Counter)
    output_examples: dict[str, dict[str, Any]] = {}

    family_output_counts: dict[str, Counter[str]] = defaultdict(Counter)
    family_renderer_counts: dict[str, Counter[str]] = defaultdict(Counter)
    family_decoder_counts: dict[str, Counter[str]] = defaultdict(Counter)
    family_asset_counts: Counter[str] = Counter()
    family_bytes: Counter[str] = Counter()

    for asset in assets:
        asset_id = str(asset.get("id"))
        family = str(asset["family"])
        family_asset_counts[family] += 1
        family_bytes[family] += int(asset["bytes"])
        seen_kinds = set()
        outputs = asset.get("outputs", [])
        if not isinstance(outputs, list):
            errors.append(f"{asset_id}: outputs must be a list")
            continue
        for output in outputs:
            if not isinstance(output, dict):
                errors.append(f"{asset_id}: output entry must be an object")
                continue
            errors.extend(validate_output_spec(output, asset_id))
            kind = str(output.get("kind", "unknown"))
            contract = OUTPUT_RECIPE_CONTRACTS.get(kind)
            output_counts[kind] += 1
            family_output_counts[family][kind] += 1
            output_bank_counts[kind][str(asset["bank"])] += 1
            output_family_counts[kind][family] += 1
            seen_kinds.add(kind)
            output_examples.setdefault(
                kind,
                {
                    "asset_id": asset_id,
                    "manifest_path": asset["manifest_path"],
                    "path": output.get("path"),
                },
            )
            if contract is not None:
                if contract.renderer is not None:
                    family_renderer_counts[family][contract.renderer] += 1
                if contract.decoder is not None:
                    family_decoder_counts[family][contract.decoder] += 1
        for kind in seen_kinds:
            output_asset_counts[kind] += 1

    if errors:
        raise ValueError("Typed output recipe contract errors:\n- " + "\n- ".join(errors))

    recipe_kinds = []
    for kind, contract in sorted(OUTPUT_RECIPE_CONTRACTS.items()):
        recipe_kinds.append(
            {
                "kind": kind,
                "output_type": contract.output_type,
                "decoder": contract.decoder,
                "renderer": contract.renderer,
                "required_fields": list(contract.required_fields),
                "optional_fields": list(contract.optional_fields),
                "extension": contract.extension,
                "output_count": output_counts[kind],
                "asset_count": output_asset_counts[kind],
                "bank_counts": dict(sorted(output_bank_counts[kind].items())),
                "family_counts": dict(sorted(output_family_counts[kind].items())),
                "example": output_examples.get(kind),
            }
        )

    families = []
    for family in FAMILIES:
        family_id = family["id"]
        outputs = family_output_counts[family_id]
        decoder_outputs = sum(
            count
            for kind, count in outputs.items()
            if OUTPUT_RECIPE_CONTRACTS[kind].decoder is not None
        )
        renderer_outputs = sum(
            count
            for kind, count in outputs.items()
            if OUTPUT_RECIPE_CONTRACTS[kind].renderer is not None
        )
        preview_outputs = sum(count for kind, count in outputs.items() if kind.endswith("_png"))
        families.append(
            {
                "id": family_id,
                "label": family["label"],
                "banks": family["banks"],
                "asset_count": family_asset_counts[family_id],
                "bytes": family_bytes[family_id],
                "output_count": sum(outputs.values()),
                "decoder_output_count": decoder_outputs,
                "renderer_output_count": renderer_outputs,
                "preview_output_count": preview_outputs,
                "output_kind_counts": dict(sorted(outputs.items())),
                "renderer_counts": dict(sorted(family_renderer_counts[family_id].items())),
                "decoder_counts": dict(sorted(family_decoder_counts[family_id].items())),
            }
        )

    totals = {
        "manifests": len(manifest_files),
        "manifests_with_typed_output_summary": typed_manifest_summaries,
        "manifests_with_smoke_fixtures": smoke_linked_manifests,
        "assets": len(assets),
        "output_recipes": sum(output_counts.values()),
        "typed_output_kinds": len(OUTPUT_RECIPE_CONTRACTS),
        "decoder_output_recipes": sum(
            count
            for kind, count in output_counts.items()
            if OUTPUT_RECIPE_CONTRACTS[kind].decoder is not None
        ),
        "renderer_output_recipes": sum(
            count
            for kind, count in output_counts.items()
            if OUTPUT_RECIPE_CONTRACTS[kind].renderer is not None
        ),
        "preview_png_recipes": sum(count for kind, count in output_counts.items() if kind.endswith("_png")),
    }

    return {
        "schema": "earthbound-decomp.asset-output-recipe-contracts.v1",
        "inputs": {
            "manifest_dir": rel(manifest_dir),
            "recipe_contract_module": "tools/asset_output_recipe_contracts.py",
        },
        "generated_json": rel(DEFAULT_JSON_OUT),
        "tracked_markdown": rel(DEFAULT_MARKDOWN_OUT),
        "smoke_fixtures": {
            "tracked_json": rel(SMOKE_FIXTURES_JSON),
            "tracked_markdown": rel(SMOKE_FIXTURES_MARKDOWN),
            "runner": "tools/run_asset_output_smoke_fixtures.py",
        },
        "source_policy": {
            "contains_rom_derived_outputs": False,
            "validates_recipes_for_user_rom_extraction": True,
        },
        "totals": totals,
        "recipe_kinds": recipe_kinds,
        "families": families,
        "validation_rules": [
            "Every output recipe kind is known to the typed contract registry.",
            "Every output path is relative to the configured output root and uses POSIX separators.",
            "PNG and JSON recipe paths use the extension implied by their typed output kind.",
            "Renderer dimensions, palette counts, tile columns, and ids use integer fields with bounded values.",
            "Palette and graphics source references carry rom-range, byte count, SHA-1, and optional earthbound_lzhal compression metadata.",
        ],
    }


def render_markdown(contract: dict[str, Any]) -> str:
    totals = contract["totals"]
    lines = [
        "# Asset Output Recipe Contracts",
        "",
        "Generated by `tools/build_asset_output_recipe_contracts.py` from checked-in `asset-manifests/*.json` and `tools/asset_output_recipe_contracts.py`.",
        "",
        "This report is a typed emitter/render/decode coverage map. It contains no ROM-derived payloads; it validates the reproducible recipes that `tools/extract_assets.py` uses when a user supplies a ROM.",
        "",
        "Reproducible smoke selectors for these recipe kinds are tracked in `notes/asset-output-smoke-fixtures.md` and executable with `tools/run_asset_output_smoke_fixtures.py`.",
        "",
        "## Snapshot",
        "",
        f"- manifests: `{totals['manifests']}`",
        f"- manifests with typed output summaries: `{totals['manifests_with_typed_output_summary']}`",
        f"- manifests with smoke fixture links: `{totals['manifests_with_smoke_fixtures']}`",
        f"- assets/tables/gaps represented: `{totals['assets']}`",
        f"- output recipes: `{totals['output_recipes']}`",
        f"- typed output recipe kinds: `{totals['typed_output_kinds']}`",
        f"- decoder-backed output recipes: `{totals['decoder_output_recipes']}`",
        f"- renderer-backed output recipes: `{totals['renderer_output_recipes']}`",
        f"- PNG preview/render recipes: `{totals['preview_png_recipes']}`",
        "",
        "## Reproducibility Rules",
        "",
    ]
    for rule in contract["validation_rules"]:
        lines.append(f"- {rule}")

    lines.extend(
        [
            "",
            "## Recipe Kinds",
            "",
            "| Recipe kind | Recipes | Assets | Output type | Decoder | Renderer | Required fields | Example |",
            "| --- | ---: | ---: | --- | --- | --- | --- | --- |",
        ]
    )
    for recipe in contract["recipe_kinds"]:
        example = recipe.get("example") or {}
        example_text = "-"
        if example:
            example_text = f"`{example['asset_id']}` -> `{example['path']}`"
        required = ", ".join(f"`{field}`" for field in recipe["required_fields"]) or "-"
        lines.append(
            "| {kind} | {recipes} | {assets} | {output_type} | {decoder} | {renderer} | {required} | {example} |".format(
                kind=f"`{recipe['kind']}`",
                recipes=recipe["output_count"],
                assets=recipe["asset_count"],
                output_type=recipe["output_type"],
                decoder=f"`{recipe['decoder']}`" if recipe["decoder"] else "-",
                renderer=f"`{recipe['renderer']}`" if recipe["renderer"] else "-",
                required=required,
                example=example_text,
            )
        )

    lines.extend(
        [
            "",
            "## Family Coverage",
            "",
            "| Family | Banks | Assets | Outputs | Decoder-backed | Renderer-backed | PNG previews | Output mix | Renderer mix |",
            "| --- | --- | ---: | ---: | ---: | ---: | ---: | --- | --- |",
        ]
    )
    for family in contract["families"]:
        lines.append(
            "| {label} | `{banks}` | {assets} | {outputs} | {decoders} | {renderers} | {previews} | {output_mix} | {renderer_mix} |".format(
                label=family["label"],
                banks=", ".join(family["banks"]),
                assets=family["asset_count"],
                outputs=family["output_count"],
                decoders=family["decoder_output_count"],
                renderers=family["renderer_output_count"],
                previews=family["preview_output_count"],
                output_mix=compact_counts(family["output_kind_counts"]),
                renderer_mix=compact_counts(family["renderer_counts"]),
            )
        )

    lines.extend(
        [
            "",
            "## Typed Output Boundary",
            "",
            "- `raw` and `earthbound_lzhal` are reproducible extraction/decode recipes, not semantic flattening of hand-authored payloads.",
            "- Palette-applied and composed preview recipes are fixtures: they bind graphics bytes to explicit palette/graphics source refs with range SHA-1s.",
            "- Audio-pack outputs remain raw by design; this contract only proves byte-stable extraction until a later audio format boundary is chosen.",
            "- Table and raw-gap outputs remain typed as byte-for-byte extraction recipes so source scaffolds keep intentional data blocks intact.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build typed asset output recipe contracts.")
    parser.add_argument("--manifest-dir", default=str(DEFAULT_MANIFEST_DIR))
    parser.add_argument("--json-out", default=str(DEFAULT_JSON_OUT))
    parser.add_argument("--markdown-out", default=str(DEFAULT_MARKDOWN_OUT))
    args = parser.parse_args()

    contract = build_contract(Path(args.manifest_dir))

    json_out = Path(args.json_out)
    json_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(json.dumps(contract, indent=2) + "\n", encoding="utf-8")

    markdown_out = Path(args.markdown_out)
    markdown_out.parent.mkdir(parents=True, exist_ok=True)
    markdown_out.write_text(render_markdown(contract), encoding="utf-8")

    totals = contract["totals"]
    print(
        "asset output recipe contracts: "
        f"{totals['output_recipes']} recipes, "
        f"{totals['typed_output_kinds']} kinds, "
        f"{totals['renderer_output_recipes']} renderer-backed"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
