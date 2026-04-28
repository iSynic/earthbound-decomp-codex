from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_JSON_OUT = ROOT / "build" / "landing-cast-visual-contracts.json"
DEFAULT_MARKDOWN_OUT = ROOT / "notes" / "landing-cast-visual-contracts.md"
MANIFEST_PATH = ROOT / "asset-manifests" / "bank-e1-assets.json"
BUILD_E1 = ROOT / "build" / "assets" / "e1"


BUNDLES: list[dict[str, Any]] = [
    {
        "id": "landing.saved_coordinate_display",
        "label": "Saved-coordinate landing display visual",
        "status": "runtime-loader-backed",
        "runtime_owner": "C4:C2DE InitializeSavedLandingDisplayState",
        "assets": [
            "asset.e1.unknown_e1cfaf",
            "asset.e1.unknown_e1d5e8",
            "asset.e1.unknown_e1d4f4",
        ],
        "portable_contract": "Expose as a landing display scene with compressed 4bpp graphics, BG tile arrangement, and palette blocks.",
        "evidence": [
            {
                "source": "notes/saved-landing-display-stage-c4c2de-c4c64d.md",
                "role": "Caller-side proof: C4:C2DE decompresses E1:CFAF, E1:D5E8, and E1:D4F4, then queues the graphics, tilemap, and palette work into the display pipeline.",
            },
            {
                "source": "src/c4/saved_landing_display_stage_helpers.asm",
                "role": "Source-backed callsite showing the three E1 immediate addresses and the C4:1A9E decompression contract.",
            },
            {
                "source": "refs/eb-decompile-4ef92/Logos/SoundStone.png",
                "role": "Reference visual for the player-facing presentation family; kept under ignored refs and not distributed.",
            },
        ],
        "subranges": [
            {
                "range": "E1:CFAF..E1:D4F4",
                "role": "compressed 4bpp landing-display graphics",
                "asset": "asset.e1.unknown_e1cfaf",
            },
            {
                "range": "E1:D5E8..E1:D6E1",
                "role": "compressed landing-display BG arrangement",
                "asset": "asset.e1.unknown_e1d5e8",
            },
            {
                "range": "E1:D4F4..E1:D5E8",
                "role": "compressed landing-display palette data",
                "asset": "asset.e1.unknown_e1d4f4",
            },
        ],
    },
    {
        "id": "ending.cast_name_visuals",
        "label": "Ending cast-name visual support",
        "status": "runtime-loader-backed",
        "runtime_owner": "C4:E369 LoadCastScene",
        "assets": [
            "asset.e1.unknown_e1d6e1",
            "table.e1.046_data_unknown_e1d815_asm",
            "asset.e1.cast_names_gfx",
            "asset.e1.unknown_e1e4e6",
        ],
        "portable_contract": "Expose as an ending cast-name bundle with prelude graphics, support-table bytes, cast-name glyph graphics, and cast-name palette data.",
        "evidence": [
            {
                "source": "notes/cast-scene-scroll-helpers-c4e4da-c4e583.md",
                "role": "C4:E369 initializes the cast scene, expands E1:D6E1 and E1:D835, prepares the cast-name tilemap, and later uses E1:D815 plus the E1:E4E6 cast-name palette payload.",
            },
            {
                "source": "src/c4/cast_scene_loader.asm",
                "role": "Source-backed callsite showing E1:D6E1, E1:D835, E1:D815, and the cast-name palette upload path.",
            },
            {
                "source": "refs/ebsrc-main/ebsrc-main/src/bankconfig/common/bank21.asm",
                "role": "ebsrc include order places UNKNOWN_E1D6E1, then data/unknown/E1D815.asm, then CAST_NAMES_GFX, then ending/cast_names.pal.lzhal.",
            },
            {
                "source": "refs/eb-decompile-4ef92/Cast/NameGraphic.png",
                "role": "Reference visual for the cast-name graphics family; kept under ignored refs and not distributed.",
            },
        ],
        "subranges": [
            {
                "range": "E1:D6E1..E1:D815",
                "role": "compressed cast-scene prelude graphics",
                "asset": "asset.e1.unknown_e1d6e1",
            },
            {
                "range": "E1:D815..E1:D835",
                "role": "small cast-scene support table included by ebsrc as data/unknown/E1D815.asm",
                "asset": "table.e1.046_data_unknown_e1d815_asm",
            },
            {
                "range": "E1:D835..E1:E4E6",
                "role": "compressed cast-name graphics",
                "asset": "asset.e1.cast_names_gfx",
            },
            {
                "range": "E1:E4E6..E1:E528",
                "role": "compressed cast-name palette data",
                "asset": "asset.e1.unknown_e1e4e6",
            },
        ],
    },
]


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def load_assets() -> dict[str, dict[str, Any]]:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    return {str(asset["id"]): asset for asset in manifest["assets"]}


def source(asset: dict[str, Any]) -> dict[str, Any]:
    value = asset.get("source", {})
    return value if isinstance(value, dict) else {}


def output_kinds(asset: dict[str, Any]) -> list[str]:
    outputs = asset.get("outputs", [])
    if not isinstance(outputs, list):
        return []
    return [str(output.get("kind", "unknown")) for output in outputs if isinstance(output, dict)]


def output_paths(asset: dict[str, Any]) -> list[str]:
    outputs = asset.get("outputs", [])
    if not isinstance(outputs, list):
        return []
    return [str(output["path"]) for output in outputs if isinstance(output, dict) and "path" in output]


def local_generated_sizes(asset: dict[str, Any]) -> list[dict[str, Any]]:
    sizes = []
    for path_text in output_paths(asset):
        path = BUILD_E1.parent / path_text
        if path.exists():
            sizes.append({"path": rel(path), "bytes": path.stat().st_size})
    return sizes


def path_exists(path_text: str) -> bool:
    return (ROOT / path_text).exists()


def path_size(path_text: str) -> int | None:
    path = ROOT / path_text
    return path.stat().st_size if path.is_file() else None


def build_component(asset_id: str, assets: dict[str, dict[str, Any]]) -> dict[str, Any]:
    asset = assets.get(asset_id)
    if asset is None:
        raise KeyError(f"Missing E1 asset in manifest: {asset_id}")
    src = source(asset)
    return {
        "id": asset_id,
        "title": asset.get("title"),
        "category": asset.get("category"),
        "range": src.get("range"),
        "source_bytes": int(src.get("bytes", 0) or 0),
        "output_kinds": output_kinds(asset),
        "generated_outputs": local_generated_sizes(asset),
        "notes": asset.get("notes", []),
    }


def build_bundle(bundle: dict[str, Any], assets: dict[str, dict[str, Any]]) -> dict[str, Any]:
    components = [build_component(asset_id, assets) for asset_id in bundle["assets"]]
    evidence = [
        {**item, "exists": path_exists(item["source"]), "bytes": path_size(item["source"])}
        for item in bundle["evidence"]
    ]
    return {
        "id": bundle["id"],
        "label": bundle["label"],
        "status": bundle["status"],
        "runtime_owner": bundle["runtime_owner"],
        "portable_contract": bundle["portable_contract"],
        "components": components,
        "subranges": bundle["subranges"],
        "evidence": evidence,
        "source_bytes": sum(component["source_bytes"] for component in components),
        "generated_output_bytes": sum(
            int(output["bytes"]) for component in components for output in component["generated_outputs"]
        ),
    }


def build_contract() -> dict[str, Any]:
    assets = load_assets()
    bundles = [build_bundle(bundle, assets) for bundle in BUNDLES]
    evidence = [item for bundle in bundles for item in bundle["evidence"]]
    return {
        "schema": "earthbound-decomp.landing-cast-visual-contracts.v1",
        "scope": "Bank E1 landing-display and ending cast-name visual assets with C4 runtime-owner proof",
        "inputs": {
            "manifest": rel(MANIFEST_PATH),
            "local_generated_outputs": "build/assets/e1",
        },
        "generated_json": rel(DEFAULT_JSON_OUT),
        "tracked_markdown": rel(DEFAULT_MARKDOWN_OUT),
        "totals": {
            "bundles": len(bundles),
            "components": sum(len(bundle["components"]) for bundle in bundles),
            "subranges": sum(len(bundle["subranges"]) for bundle in bundles),
            "source_bytes": sum(bundle["source_bytes"] for bundle in bundles),
            "generated_output_bytes_seen": sum(bundle["generated_output_bytes"] for bundle in bundles),
            "missing_evidence_refs": sum(1 for item in evidence if not item["exists"]),
        },
        "validation": {
            "all_manifest_components_found": True,
            "all_declared_evidence_refs_exist": all(item["exists"] for item in evidence),
            "d6e1_manifest_split_completed": True,
        },
        "bundles": bundles,
        "open_questions": [
            "Decide final public-facing names for the saved-coordinate landing display visual after comparing the in-game presentation against the Sound Stone reference image.",
        ],
    }


def render_ref(ref: dict[str, Any]) -> str:
    suffix = ""
    if ref["bytes"] is not None:
        suffix = f" ({ref['bytes']} bytes)"
    return f"`{ref['source']}{suffix}`"


def render_markdown(contract: dict[str, Any]) -> str:
    totals = contract["totals"]
    lines = [
        "# Landing/Cast Visual Contracts",
        "",
        "Generated by `tools/build_landing_cast_visual_contracts.py`. This report promotes the former E1 visual tail into two runtime-owned bundles: the saved-coordinate landing display and the ending cast-name visual path.",
        "",
        "No ROM-derived graphics, palettes, tilemaps, or decoded image payloads are checked in by this report.",
        "",
        "## Snapshot",
        "",
        f"- bundles: `{totals['bundles']}`",
        f"- manifest components covered: `{totals['components']}`",
        f"- subranges described: `{totals['subranges']}`",
        f"- source bytes covered: `{totals['source_bytes']}`",
        f"- generated local output bytes observed: `{totals['generated_output_bytes_seen']}`",
        f"- missing evidence refs: `{totals['missing_evidence_refs']}`",
        "",
        "## Validation",
        "",
    ]
    for key, value in contract["validation"].items():
        lines.append(f"- `{key}`: `{str(value).lower()}`")

    lines.extend(
        [
            "",
            "## Bundles",
            "",
            "| Bundle | Status | Runtime owner | Components | Source bytes | Portable contract |",
            "| --- | --- | --- | ---: | ---: | --- |",
        ]
    )
    for bundle in contract["bundles"]:
        lines.append(
            "| {label} | `{status}` | `{owner}` | {components} | {source_bytes} | {contract_text} |".format(
                label=bundle["label"],
                status=bundle["status"],
                owner=bundle["runtime_owner"],
                components=len(bundle["components"]),
                source_bytes=bundle["source_bytes"],
                contract_text=bundle["portable_contract"],
            )
        )

    lines.extend(["", "## Subrange Roles", ""])
    lines.append("| Bundle | Range | Asset | Role | Status |")
    lines.append("| --- | --- | --- | --- | --- |")
    for bundle in contract["bundles"]:
        for subrange in bundle["subranges"]:
            lines.append(
                "| {bundle} | `{range_text}` | `{asset}` | {role} | `{status}` |".format(
                    bundle=bundle["label"],
                    range_text=subrange["range"],
                    asset=subrange["asset"],
                    role=subrange["role"],
                    status=subrange.get("status", bundle["status"]),
                )
            )

    lines.extend(["", "## Component Details", ""])
    for bundle in contract["bundles"]:
        lines.append(f"### {bundle['label']}")
        lines.append("")
        lines.append("| Component | Range | Source bytes | Output kinds | Generated outputs observed |")
        lines.append("| --- | --- | ---: | --- | --- |")
        for component in bundle["components"]:
            outputs = ", ".join(
                f"`{output['path']}` ({output['bytes']})" for output in component["generated_outputs"]
            )
            lines.append(
                "| `{id}` | `{range_text}` | {source_bytes} | {kinds} | {outputs} |".format(
                    id=component["id"],
                    range_text=component["range"],
                    source_bytes=component["source_bytes"],
                    kinds=", ".join(f"`{kind}`" for kind in component["output_kinds"]) or "-",
                    outputs=outputs or "-",
                )
            )
        lines.append("")
        lines.append("Evidence:")
        for item in bundle["evidence"]:
            lines.append(f"- {render_ref(item)}: {item['role']}")
        lines.append("")

    lines.extend(["## Open Questions", ""])
    for question in contract["open_questions"]:
        lines.append(f"- {question}")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build E1 landing/cast visual bundle contracts.")
    parser.add_argument("--json-out", default=str(DEFAULT_JSON_OUT))
    parser.add_argument("--markdown-out", default=str(DEFAULT_MARKDOWN_OUT))
    args = parser.parse_args()

    contract = build_contract()
    json_out = Path(args.json_out)
    json_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(json.dumps(contract, indent=2) + "\n", encoding="utf-8")

    markdown_out = Path(args.markdown_out)
    markdown_out.parent.mkdir(parents=True, exist_ok=True)
    markdown_out.write_text(render_markdown(contract), encoding="utf-8")

    totals = contract["totals"]
    print(
        "landing/cast visual bundles: "
        f"{totals['bundles']} bundles, "
        f"{totals['components']} components, "
        f"{totals['subranges']} subranges"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
