from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_JSON_OUT = ROOT / "build" / "intro-title-visual-bundle-contracts.json"
DEFAULT_MARKDOWN_OUT = ROOT / "notes" / "intro-title-visual-bundle-contracts.md"
MANIFEST_PATH = ROOT / "asset-manifests" / "bank-e1-assets.json"
BUILD_E1 = ROOT / "build" / "assets" / "e1"
REF_LOGOS = ROOT / "refs" / "eb-decompile-4ef92" / "Logos"
REF_TITLE = ROOT / "refs" / "eb-decompile-4ef92" / "TitleScreen"
LEGACY = ROOT / "refs" / "earthbound-disasm-legacy" / "Earthbound Decomp" / "EB"


SCENES: list[dict[str, Any]] = [
    {
        "id": "intro.logo.ape",
        "label": "APE software logo",
        "role": "Intro logo scene.",
        "assets": ["asset.e1.ape_arrangement", "asset.e1.ape_graphics", "asset.e1.ape_palette"],
        "refs": ["refs/eb-decompile-4ef92/Logos/APE.png"],
        "legacy_refs": [
            "refs/earthbound-disasm-legacy/Earthbound Decomp/EB/Tilemaps/ApeSoftwareLogoTilemap.bin",
            "refs/earthbound-disasm-legacy/Earthbound Decomp/EB/Palettes/Compressed/ApeSoftwareLogoPalette.bin",
        ],
        "status": "named-by-ebsrc-and-legacy",
    },
    {
        "id": "intro.logo.halken",
        "label": "HALKEN logo",
        "role": "Intro logo scene.",
        "assets": ["asset.e1.halken_arrangement", "asset.e1.halken_graphics", "asset.e1.halken_palette"],
        "refs": ["refs/eb-decompile-4ef92/Logos/HALKEN.png"],
        "legacy_refs": [
            "refs/earthbound-disasm-legacy/Earthbound Decomp/EB/Tilemaps/HalLogoTilemap.bin",
            "refs/earthbound-disasm-legacy/Earthbound Decomp/EB/Palettes/Compressed/HalLogoPalette.bin",
        ],
        "status": "named-by-ebsrc-and-legacy",
    },
    {
        "id": "intro.logo.nintendo",
        "label": "Nintendo logo",
        "role": "Intro logo scene.",
        "assets": [
            "asset.e1.nintendo_arrangement",
            "asset.e1.nintendo_graphics",
            "asset.e1.nintendo_palette",
        ],
        "refs": ["refs/eb-decompile-4ef92/Logos/Nintendo.png"],
        "legacy_refs": [
            "refs/earthbound-disasm-legacy/Earthbound Decomp/EB/Tilemaps/NintendoLogoTilemap.bin",
            "refs/earthbound-disasm-legacy/Earthbound Decomp/EB/Palettes/Compressed/NintendoLogoPalette.bin",
        ],
        "status": "named-by-ebsrc-and-legacy",
    },
    {
        "id": "intro.war_on_giygas_gas_station",
        "label": "War on Giygas / gas-station intro visual",
        "role": "Large intro visual loaded by the C4 gas-station intro helper; ebsrc names the files gas_station while the legacy disassembly names matching compressed tilemap/palette payloads WarOnGiygasScreen.",
        "assets": [
            "asset.e1.gas_station_arrangement",
            "asset.e1.gas_station_graphics",
            "asset.e1.gas_station_palette",
            "asset.e1.gas_station_palette_2",
        ],
        "refs": [
            "refs/eb-decompile-4ef92/Logos/GasStation1.png",
            "refs/eb-decompile-4ef92/Logos/GasStation2.png",
            "refs/eb-decompile-4ef92/Logos/GasStation3.png",
        ],
        "legacy_refs": [
            "refs/earthbound-disasm-legacy/Earthbound Decomp/EB/Tilemaps/WarOnGiygasScreenTilemap.bin",
            "refs/earthbound-disasm-legacy/Earthbound Decomp/EB/Palettes/Compressed/WarOnGiygasScreenPalette.bin",
            "refs/earthbound-disasm-legacy/Earthbound Decomp/EB/Palettes/Compressed/WarOnGiygasScreenFlashPalette.bin",
        ],
        "status": "runtime-loader-backed",
    },
    {
        "id": "intro.attract.presented_produced_by",
        "label": "Presented/produced-by attract cards",
        "role": "Small attract presentation cards around the Nintendo/Itoi credits before the title screen.",
        "assets": [
            "asset.e1.produced_itoi_arrangement",
            "asset.e1.produced_itoi_graphics",
            "asset.e1.nintendo_presentation_arrangement",
            "asset.e1.nintendo_presentation_graphics",
            "asset.e1.nintendo_itoi_palette",
        ],
        "refs": [
            "refs/eb-decompile-4ef92/Logos/ProducedBy.png",
            "refs/eb-decompile-4ef92/Logos/PresentedBy.png",
        ],
        "legacy_refs": [],
        "status": "named-by-ebsrc-and-logo-refs",
    },
    {
        "id": "intro.title_screen",
        "label": "Title-screen background, logo, and letter sprites",
        "role": "Main title-screen visual bundle: background/tilemap, 4bpp graphics, logo-letter graphics, palette animation payloads, and OAM records.",
        "assets": [
            "asset.e1.unknown_e1ae7c",
            "asset.e1.title_screen_arrangement",
            "asset.e1.title_screen_graphics",
            "asset.e1.unknown_e1c6e5",
            "asset.e1.title_screen_palette",
            "table.e1.041_data_unknown_e1ce08_asm",
        ],
        "refs": [
            "refs/eb-decompile-4ef92/TitleScreen/Background",
            "refs/eb-decompile-4ef92/TitleScreen/Chars",
            "notes/title-screen-palette-animation-contracts.md",
            "notes/title-screen-letter-oam-contracts.md",
        ],
        "legacy_refs": [
            "refs/earthbound-disasm-legacy/Earthbound Decomp/EB/Tilemaps/TitleLogoTilemap.bin",
            "refs/earthbound-disasm-legacy/Earthbound Decomp/EB/Palettes/Compressed/TitleScreenBGPalettes.bin",
            "refs/earthbound-disasm-legacy/Earthbound Decomp/EB/Palettes/Compressed/TitleScreenLetterPalettes.bin",
            "refs/earthbound-disasm-legacy/Earthbound Decomp/EB/Palettes/Compressed/TitleScreenGlowPalettes.bin",
        ],
        "status": "named-by-ebsrc-and-ref-family",
        "open": "E1:AE7C..AF7D is promoted by notes/title-screen-palette-animation-contracts.md into initial, letter, and glow palette animation subpayloads; E1:CE08 is promoted by notes/title-screen-letter-oam-contracts.md into TitleScreenLetterOAMData.",
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


def output_paths(asset: dict[str, Any]) -> list[str]:
    outputs = asset.get("outputs", [])
    if not isinstance(outputs, list):
        return []
    return [str(output["path"]) for output in outputs if isinstance(output, dict) and "path" in output]


def output_kinds(asset: dict[str, Any]) -> list[str]:
    outputs = asset.get("outputs", [])
    if not isinstance(outputs, list):
        return []
    return [str(output.get("kind", "unknown")) for output in outputs if isinstance(output, dict)]


def local_generated_sizes(asset: dict[str, Any]) -> list[dict[str, Any]]:
    sizes = []
    for path_text in output_paths(asset):
        path = BUILD_E1.parent / path_text
        if path.exists():
            sizes.append({"path": rel(path), "bytes": path.stat().st_size})
    return sizes


def path_size(path_text: str) -> int | None:
    path = ROOT / path_text
    return path.stat().st_size if path.exists() and path.is_file() else None


def path_exists(path_text: str) -> bool:
    path = ROOT / path_text
    return path.exists()


def title_ref_summary() -> dict[str, Any]:
    backgrounds = sorted((REF_TITLE / "Background").glob("*.png"))
    chars = sorted((REF_TITLE / "Chars").glob("*.png"))
    numbered_chars = [path for path in chars if path.stem.isdigit()]
    positions = REF_TITLE / "Chars" / "positions.yml"
    position_rows = 0
    if positions.exists():
        for line in positions.read_text(encoding="utf-8").splitlines():
            if line and not line.startswith(" ") and line.rstrip(":").isdigit():
                position_rows += 1
    return {
        "background_pngs": len([path for path in backgrounds if path.name != "Reference.png"]),
        "background_reference_png_exists": (REF_TITLE / "Background" / "Reference.png").exists(),
        "numbered_char_pngs": len(numbered_chars),
        "initial_char_png_exists": (REF_TITLE / "Chars" / "Initial.png").exists(),
        "position_rows": position_rows,
        "positions_ref": rel(positions),
    }


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
    }


def build_scene(scene: dict[str, Any], assets: dict[str, dict[str, Any]]) -> dict[str, Any]:
    components = [build_component(asset_id, assets) for asset_id in scene["assets"]]
    refs = [{"path": ref, "exists": path_exists(ref), "bytes": path_size(ref)} for ref in scene["refs"]]
    legacy_refs = [
        {"path": ref, "exists": path_exists(ref), "bytes": path_size(ref)} for ref in scene["legacy_refs"]
    ]
    return {
        "id": scene["id"],
        "label": scene["label"],
        "status": scene["status"],
        "runtime_role": scene["role"],
        "components": components,
        "refs": refs,
        "legacy_refs": legacy_refs,
        "source_bytes": sum(component["source_bytes"] for component in components),
        "generated_output_bytes": sum(
            int(output["bytes"]) for component in components for output in component["generated_outputs"]
        ),
        "open": scene.get("open"),
    }


def build_contract() -> dict[str, Any]:
    assets = load_assets()
    scenes = [build_scene(scene, assets) for scene in SCENES]
    all_refs = [ref for scene in scenes for ref in scene["refs"] + scene["legacy_refs"]]
    return {
        "schema": "earthbound-decomp.intro-title-visual-bundle-contracts.v1",
        "scope": "Bank E1 intro logos, War on Giygas/gas-station visuals, attract cards, and title-screen assets",
        "inputs": {
            "manifest": rel(MANIFEST_PATH),
            "local_generated_outputs": "build/assets/e1",
            "ebdecomp_logo_refs": rel(REF_LOGOS),
            "ebdecomp_title_refs": rel(REF_TITLE),
            "legacy_earthbound_disasm_refs": rel(LEGACY),
        },
        "generated_json": rel(DEFAULT_JSON_OUT),
        "tracked_markdown": rel(DEFAULT_MARKDOWN_OUT),
        "totals": {
            "scenes": len(scenes),
            "components": sum(len(scene["components"]) for scene in scenes),
            "source_bytes": sum(scene["source_bytes"] for scene in scenes),
            "generated_output_bytes_seen": sum(scene["generated_output_bytes"] for scene in scenes),
            "missing_refs": sum(1 for ref in all_refs if not ref["exists"]),
        },
        "validation": {
            "all_manifest_components_found": True,
            "all_declared_refs_exist": all(ref["exists"] for ref in all_refs),
            "title_refs_have_34_background_frames": title_ref_summary()["background_pngs"] == 34,
            "title_refs_have_14_numbered_char_frames": title_ref_summary()["numbered_char_pngs"] == 14,
            "title_refs_have_9_position_rows": title_ref_summary()["position_rows"] == 9,
        },
        "title_ref_summary": title_ref_summary(),
        "scenes": scenes,
        "runtime_context": [
            {
                "source": "notes/gas-station-intro-asset-loader-c4a377.md",
                "role": "C4:A377 loads the gas-station/War-on-Giygas visual bundle through compact-script-driven graphics, tilemap, and palette pointer choices.",
            },
            {
                "source": "notes/intro-logo-wait-and-gas-station-helpers-c0efe1-c0f21e.md",
                "role": "C0 intro/logo wait helpers are the bank-C0 side of the same intro visual path.",
            },
            {
                "source": "refs/earthbound-disasm-legacy/Earthbound Decomp/EB/Tilemaps",
                "role": "Legacy compressed tilemaps corroborate APE, HAL, Nintendo, War-on-Giygas, and title-logo compressed arrangement byte counts.",
            },
            {
                "source": "refs/eb-decompile-4ef92/TitleScreen",
                "role": "EBDecomp title-screen image refs establish the title background frame count, character sprite count, and position-row count without committing ROM payloads.",
            },
            {
                "source": "notes/title-screen-letter-oam-contracts.md",
                "role": "Promotes the raw E1:CE08 table to TitleScreenLetterOAMData with nine letter records and the E1:CF9D pointer table.",
            },
            {
                "source": "notes/title-screen-palette-animation-contracts.md",
                "role": "Promotes the E1:AE7C manifest blob to initial title palette, 14-frame letter palette animation, and 20-frame glow palette animation subpayloads.",
            },
            {
                "source": "notes/landing-cast-visual-contracts.md",
                "role": "Owns the former E1:CFAF..D835 tail as saved-coordinate landing display assets plus ending cast-name visual support.",
            },
        ],
        "open_questions": [],
    }


def render_ref_list(refs: list[dict[str, Any]]) -> str:
    if not refs:
        return "-"
    parts = []
    for ref in refs:
        label = ref["path"]
        if ref["bytes"] is not None:
            label = f"{label} ({ref['bytes']} bytes)"
        parts.append(f"`{label}`")
    return ", ".join(parts)


def render_markdown(contract: dict[str, Any]) -> str:
    totals = contract["totals"]
    title = contract["title_ref_summary"]
    lines = [
        "# Intro/Title Visual Bundle Contracts",
        "",
        "Generated by `tools/build_intro_title_visual_bundle_contracts.py`. This groups bank E1 intro, logo, attract, and title-screen visual payloads into portable scene bundles using checked-in manifests plus ignored reference directories.",
        "",
        "No ROM-derived graphics, palettes, tilemaps, or decoded image payloads are checked in by this report.",
        "",
        "## Snapshot",
        "",
        f"- scene bundles: `{totals['scenes']}`",
        f"- manifest components covered: `{totals['components']}`",
        f"- source bytes covered: `{totals['source_bytes']}`",
        f"- generated local output bytes observed: `{totals['generated_output_bytes_seen']}`",
        f"- missing declared refs: `{totals['missing_refs']}`",
        "",
        "## Validation",
        "",
    ]
    for key, value in contract["validation"].items():
        lines.append(f"- `{key}`: `{str(value).lower()}`")
    lines.extend(
        [
            "",
            "## Title Ref Shape",
            "",
            f"- EBDecomp title background frames: `{title['background_pngs']}` plus reference PNG `{str(title['background_reference_png_exists']).lower()}`",
            f"- EBDecomp numbered title character PNGs: `{title['numbered_char_pngs']}` plus initial PNG `{str(title['initial_char_png_exists']).lower()}`",
            f"- EBDecomp title position rows: `{title['position_rows']}` from `{title['positions_ref']}`",
            "",
            "## Scene Bundles",
            "",
            "| Scene | Status | Components | Source bytes | Generated bytes observed | Refs | Legacy refs |",
            "| --- | --- | ---: | ---: | ---: | --- | --- |",
        ]
    )
    for scene in contract["scenes"]:
        lines.append(
            "| {label} | `{status}` | {components} | {source_bytes} | {generated_bytes} | {refs} | {legacy_refs} |".format(
                label=scene["label"],
                status=scene["status"],
                components=len(scene["components"]),
                source_bytes=scene["source_bytes"],
                generated_bytes=scene["generated_output_bytes"],
                refs=render_ref_list(scene["refs"]),
                legacy_refs=render_ref_list(scene["legacy_refs"]),
            )
        )

    lines.extend(["", "## Component Details", ""])
    for scene in contract["scenes"]:
        lines.append(f"### {scene['label']}")
        lines.append("")
        lines.append(f"- bundle id: `{scene['id']}`")
        lines.append(f"- role: {scene['runtime_role']}")
        if scene.get("open"):
            lines.append(f"- followup: {scene['open']}")
        lines.append("")
        lines.append("| Component | Range | Source bytes | Output kinds | Generated outputs observed |")
        lines.append("| --- | --- | ---: | --- | --- |")
        for component in scene["components"]:
            outputs = ", ".join(
                f"`{output['path']}` ({output['bytes']})" for output in component["generated_outputs"]
            )
            lines.append(
                "| `{id}` | `{range}` | {source_bytes} | {kinds} | {outputs} |".format(
                    id=component["id"],
                    range=component["range"],
                    source_bytes=component["source_bytes"],
                    kinds=", ".join(f"`{kind}`" for kind in component["output_kinds"]) or "-",
                    outputs=outputs or "-",
                )
            )
        lines.append("")

    lines.extend(["## Runtime Context", ""])
    for item in contract["runtime_context"]:
        lines.append(f"- `{item['source']}`: {item['role']}")

    if contract["open_questions"]:
        lines.extend(["", "## Open Questions", ""])
        for question in contract["open_questions"]:
            lines.append(f"- {question}")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build E1 intro/title visual bundle contracts.")
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
        "intro/title visual bundles: "
        f"{totals['scenes']} scenes, "
        f"{totals['components']} components, "
        f"{totals['source_bytes']} source bytes"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
