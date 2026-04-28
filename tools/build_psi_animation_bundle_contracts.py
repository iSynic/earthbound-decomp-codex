from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_JSON_OUT = ROOT / "build" / "psi-animation-bundle-contracts.json"
DEFAULT_MARKDOWN_OUT = ROOT / "notes" / "psi-animation-bundle-contracts.md"

MANIFEST_PATH = ROOT / "asset-manifests" / "bank-cc-assets.json"
TABLE_BIN_DIR = ROOT / "build" / "assets" / "cc" / "tables"
PSI_ANIM_CFG_BIN = TABLE_BIN_DIR / "043_data_psi_anim_cfg_asm.bin"
PSI_ANIM_POINTERS_BIN = TABLE_BIN_DIR / "080_data_psi_anim_pointers_asm.bin"
ANIMATION_SEQUENCE_POINTERS_BIN = TABLE_BIN_DIR / "006_data_animation_sequence_pointers_asm.bin"
ANIMATION_SEQUENCE_REF = (
    ROOT / "refs" / "ebsrc-main" / "ebsrc-main" / "src" / "data" / "animation_sequence_pointers.asm"
)
SHOW_PSI_ANIMATION_REF = ROOT / "refs" / "ebsrc-main" / "ebsrc-main" / "src" / "battle" / "show_psi_animation.asm"
C2_ADVANCE_DOC = ROOT / "notes" / "c2-psi-swirl-overlay-tail-c2e6b3-c2ea74.md"

CFG_ROW_SIZE = 12
ANIM_POINTER_ROW_SIZE = 4
SEQUENCE_ROW_SIZE = 8

TARGET_MODES = {
    0: "current_enemy_centered",
    1: "same_enemy_row",
    2: "all_enemies_fixed_y",
    3: "current_enemy_centered_alt",
}


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def require_bytes(path: Path) -> bytes:
    if not path.exists():
        raise FileNotFoundError(
            f"{rel(path)} is required. Run the asset extraction pipeline with a user-supplied ROM first."
        )
    return path.read_bytes()


def parse_cpu_range_start(cpu_range: str) -> str:
    return cpu_range.split("..", 1)[0]


def pointer_to_cpu(pointer: bytes) -> str | None:
    if len(pointer) != 4:
        raise ValueError("pointer rows must be four bytes")
    low = pointer[0] | (pointer[1] << 8)
    bank = pointer[2]
    if low == 0 and bank == 0:
        return None
    return f"{bank:02X}:{low:04X}"


def bgr555(word: int) -> dict[str, int]:
    return {
        "raw": word,
        "red": word & 0x1F,
        "green": (word >> 5) & 0x1F,
        "blue": (word >> 10) & 0x1F,
    }


def load_cc_assets() -> list[dict[str, Any]]:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    assets = []
    for asset in manifest["assets"]:
        source = asset.get("source", {})
        if not isinstance(source, dict):
            source = {}
        assets.append(
            {
                "id": asset["id"],
                "title": asset["title"],
                "category": asset["category"],
                "range": source.get("range"),
                "bytes": source.get("bytes"),
            }
        )
    return assets


def asset_ref(asset: dict[str, Any] | None) -> dict[str, Any] | None:
    if asset is None:
        return None
    return {
        "id": asset["id"],
        "title": asset["title"],
        "range": asset["range"],
        "bytes": asset["bytes"],
    }


def build_asset_maps(assets: list[dict[str, Any]]) -> dict[str, Any]:
    by_title = {asset["title"]: asset for asset in assets}
    by_start = {parse_cpu_range_start(asset["range"]): asset for asset in assets if asset.get("range")}
    palettes_by_index: dict[int, dict[str, Any]] = {}
    for asset in assets:
        title = str(asset["title"])
        asset_id = str(asset["id"])
        if title == "PSI_ANIM_PALETTES":
            palettes_by_index[0] = asset
            continue
        match = re.search(r"psianims/palettes/(\d+)\.pal", title)
        if match:
            palettes_by_index[int(match.group(1))] = asset
            continue
        match = re.search(r"psianims_palettes_(\d+)_pal", asset_id)
        if match:
            palettes_by_index[int(match.group(1))] = asset
    return {
        "by_title": by_title,
        "by_start": by_start,
        "palettes_by_index": palettes_by_index,
    }


def parse_sequence_labels(path: Path) -> list[str]:
    labels = []
    for line in path.read_text(encoding="utf-8").splitlines():
        match = re.search(r"\.DWORD\s+([A-Z0-9_]+)", line)
        if match:
            labels.append(match.group(1))
    return labels


def parse_sequence_table(asset_maps: dict[str, Any]) -> list[dict[str, Any]]:
    data = require_bytes(ANIMATION_SEQUENCE_POINTERS_BIN)
    if len(data) % SEQUENCE_ROW_SIZE:
        raise ValueError(f"{rel(ANIMATION_SEQUENCE_POINTERS_BIN)} is not divisible by {SEQUENCE_ROW_SIZE}")
    labels = parse_sequence_labels(ANIMATION_SEQUENCE_REF)
    rows = []
    for index in range(0, len(data), SEQUENCE_ROW_SIZE):
        row = data[index : index + SEQUENCE_ROW_SIZE]
        pointer = pointer_to_cpu(row[:4])
        label = labels[index // SEQUENCE_ROW_SIZE] if index // SEQUENCE_ROW_SIZE < len(labels) else None
        asset = None if pointer is None else asset_maps["by_start"].get(pointer)
        rows.append(
            {
                "sequence_index": index // SEQUENCE_ROW_SIZE,
                "label": label,
                "pointer": pointer,
                "asset": asset_ref(asset),
                "parameters": {
                    "byte_0": row[4],
                    "byte_1": row[5],
                    "byte_2": row[6],
                    "byte_3": row[7],
                },
            }
        )
    return rows


def parse_psi_animation_bundles(asset_maps: dict[str, Any]) -> list[dict[str, Any]]:
    cfg = require_bytes(PSI_ANIM_CFG_BIN)
    pointers = require_bytes(PSI_ANIM_POINTERS_BIN)
    if len(cfg) % CFG_ROW_SIZE:
        raise ValueError(f"{rel(PSI_ANIM_CFG_BIN)} is not divisible by {CFG_ROW_SIZE}")
    if len(pointers) % ANIM_POINTER_ROW_SIZE:
        raise ValueError(f"{rel(PSI_ANIM_POINTERS_BIN)} is not divisible by {ANIM_POINTER_ROW_SIZE}")
    row_count = len(cfg) // CFG_ROW_SIZE
    pointer_count = len(pointers) // ANIM_POINTER_ROW_SIZE
    if row_count != pointer_count:
        raise ValueError(f"PSI config rows ({row_count}) do not match pointer rows ({pointer_count})")

    bundles = []
    for index in range(row_count):
        row = cfg[index * CFG_ROW_SIZE : (index + 1) * CFG_ROW_SIZE]
        gfx_pointer = f"CC:{int.from_bytes(row[0:2], 'little'):04X}"
        arrangement_pointer = pointer_to_cpu(
            pointers[index * ANIM_POINTER_ROW_SIZE : (index + 1) * ANIM_POINTER_ROW_SIZE]
        )
        enemy_colour = int.from_bytes(row[10:12], "little")
        target_mode = row[7]
        bundles.append(
            {
                "animation_id": index,
                "gfx_pointer": gfx_pointer,
                "arrangement_pointer": arrangement_pointer,
                "palette_index": index,
                "frame_hold_frames": row[2],
                "palette_animation_frames": row[3],
                "palette_animation_lower_index": row[4],
                "palette_animation_upper_index": row[5],
                "total_frames": row[6],
                "target_mode": target_mode,
                "target_mode_name": TARGET_MODES.get(target_mode, f"unknown_{target_mode:02X}"),
                "enemy_colour_change_start_frames_left": row[8],
                "enemy_colour_change_frames_left": row[9],
                "enemy_colour_change_bgr555": bgr555(enemy_colour),
                "assets": {
                    "gfx_set": asset_ref(asset_maps["by_start"].get(gfx_pointer)),
                    "arrangement": asset_ref(asset_maps["by_start"].get(arrangement_pointer)),
                    "palette": asset_ref(asset_maps["palettes_by_index"].get(index)),
                },
            }
        )
    return bundles


def build_contract() -> dict[str, Any]:
    assets = load_cc_assets()
    asset_maps = build_asset_maps(assets)
    bundles = parse_psi_animation_bundles(asset_maps)
    sequences = parse_sequence_table(asset_maps)

    gfx_ids = {bundle["assets"]["gfx_set"]["id"] for bundle in bundles if bundle["assets"]["gfx_set"]}
    arrangement_ids = {
        bundle["assets"]["arrangement"]["id"] for bundle in bundles if bundle["assets"]["arrangement"]
    }
    palette_ids = {bundle["assets"]["palette"]["id"] for bundle in bundles if bundle["assets"]["palette"]}
    target_modes = Counter(bundle["target_mode_name"] for bundle in bundles)

    return {
        "schema": "earthbound-decomp.psi-animation-bundle-contracts.v1",
        "scope": "CC PSI animation config/pointer/palette joins plus the small named animation-sequence table",
        "inputs": [
            rel(MANIFEST_PATH),
            rel(PSI_ANIM_CFG_BIN),
            rel(PSI_ANIM_POINTERS_BIN),
            rel(ANIMATION_SEQUENCE_POINTERS_BIN),
            rel(ANIMATION_SEQUENCE_REF),
            rel(SHOW_PSI_ANIMATION_REF),
            rel(C2_ADVANCE_DOC),
        ],
        "generated_json": rel(DEFAULT_JSON_OUT),
        "tracked_markdown": rel(DEFAULT_MARKDOWN_OUT),
        "totals": {
            "psi_animation_bundles": len(bundles),
            "sequence_rows": len(sequences),
            "unique_gfx_sets": len(gfx_ids),
            "unique_arrangements": len(arrangement_ids),
            "unique_palettes": len(palette_ids),
            "matched_gfx_sets": sum(1 for bundle in bundles if bundle["assets"]["gfx_set"]),
            "matched_arrangements": sum(1 for bundle in bundles if bundle["assets"]["arrangement"]),
            "matched_palettes": sum(1 for bundle in bundles if bundle["assets"]["palette"]),
        },
        "validation": {
            "all_gfx_sets_matched": all(bundle["assets"]["gfx_set"] for bundle in bundles),
            "all_arrangements_matched": all(bundle["assets"]["arrangement"] for bundle in bundles),
            "all_palettes_matched": all(bundle["assets"]["palette"] for bundle in bundles),
            "all_sequence_assets_matched_or_null": all(
                row["pointer"] is None or row["asset"] is not None for row in sequences
            ),
        },
        "target_mode_counts": dict(sorted(target_modes.items())),
        "known_semantics": [
            "`SHOW_PSI_ANIMATION` takes an animation id and indexes `PSI_ANIM_CFG` as 12-byte rows.",
            "Config bytes 0-1 are a bank-CC offset to the compressed PSI graphics set.",
            "`PSI_ANIM_POINTERS[animation_id]` selects the compressed arrangement payload.",
            "`PSI_ANIM_PALETTES + animation_id * 8` selects the 4-color palette payload copied into `psi_animation_state::palette` and the displayed palette buffer.",
            "Config byte 2 seeds frame hold duration, byte 6 seeds total frames, and bytes 3-5 seed palette animation timing/range.",
            "Config byte 7 selects enemy targeting/offset behavior; values 0 and 3 center on the current enemy, 1 expands to the enemy row, and 2 marks all enemies with a fixed vertical offset.",
            "Config bytes 8-11 seed enemy-color change timers and a BGR555 target color consumed by the C2 animation tick helper.",
        ],
        "open_questions": [
            "The four parameter bytes in `ANIMATION_SEQUENCE_POINTERS` are preserved but not yet caller-named.",
            "Target mode labels are inferred from `SHOW_PSI_ANIMATION`; they can be promoted once caller-side effect names are exhaustively tied to battle actions.",
            "This contract joins metadata to assets, but rendered PSI animation previews remain a local output generated from a user-supplied ROM.",
        ],
        "psi_animation_bundles": bundles,
        "animation_sequence_rows": sequences,
    }


def render_asset(asset: dict[str, Any] | None) -> str:
    if asset is None:
        return "-"
    return f"`{asset['id']}`"


def render_bool(value: bool) -> str:
    return "yes" if value else "no"


def render_markdown(contract: dict[str, Any]) -> str:
    totals = contract["totals"]
    validation = contract["validation"]
    lines = [
        "# PSI Animation Bundle Contracts",
        "",
        "Generated by `tools/build_psi_animation_bundle_contracts.py` from the CC asset manifest, ignored locally extracted table bytes, and checked-in ebsrc loader evidence.",
        "",
        "No ROM-derived payload bytes or rendered animation previews are checked in by this report.",
        "",
        "## Snapshot",
        "",
        f"- PSI animation bundles: `{totals['psi_animation_bundles']}`",
        f"- named animation-sequence rows: `{totals['sequence_rows']}`",
        f"- unique graphics sets used: `{totals['unique_gfx_sets']}`",
        f"- unique arrangements used: `{totals['unique_arrangements']}`",
        f"- unique palettes used: `{totals['unique_palettes']}`",
        f"- matched graphics/arrangement/palette rows: `{totals['matched_gfx_sets']}` / `{totals['matched_arrangements']}` / `{totals['matched_palettes']}`",
        "",
        "## Validation",
        "",
        f"- all graphics set references matched: `{render_bool(validation['all_gfx_sets_matched'])}`",
        f"- all arrangement references matched: `{render_bool(validation['all_arrangements_matched'])}`",
        f"- all palette references matched: `{render_bool(validation['all_palettes_matched'])}`",
        f"- all named animation sequence pointers matched or null: `{render_bool(validation['all_sequence_assets_matched_or_null'])}`",
        "",
        "## Runtime Contract",
        "",
    ]
    for item in contract["known_semantics"]:
        lines.append(f"- {item}")

    lines.extend(["", "## Target Modes", ""])
    for mode, count in contract["target_mode_counts"].items():
        lines.append(f"- `{mode}`: `{count}` rows")

    lines.extend(
        [
            "",
            "## PSI Animation Bundles",
            "",
            "| ID | Graphics set | Arrangement | Palette | Hold | Frames | Palette anim | Target mode | Enemy color |",
            "| ---: | --- | --- | --- | ---: | ---: | --- | --- | --- |",
        ]
    )
    for bundle in contract["psi_animation_bundles"]:
        color = bundle["enemy_colour_change_bgr555"]
        lines.append(
            "| {id} | {gfx} | {arr} | {pal} | {hold} | {frames} | {pal_anim} | `{target}` | `{raw:04X}` ({r},{g},{b}) |".format(
                id=bundle["animation_id"],
                gfx=render_asset(bundle["assets"]["gfx_set"]),
                arr=render_asset(bundle["assets"]["arrangement"]),
                pal=render_asset(bundle["assets"]["palette"]),
                hold=bundle["frame_hold_frames"],
                frames=bundle["total_frames"],
                pal_anim=f"`{bundle['palette_animation_frames']}` frames, `{bundle['palette_animation_lower_index']}..{bundle['palette_animation_upper_index']}`",
                target=bundle["target_mode_name"],
                raw=color["raw"],
                r=color["red"],
                g=color["green"],
                b=color["blue"],
            )
        )

    lines.extend(
        [
            "",
            "## Named Animation Sequence Table",
            "",
            "| Row | Label | Asset | Parameters |",
            "| ---: | --- | --- | --- |",
        ]
    )
    for row in contract["animation_sequence_rows"]:
        params = row["parameters"]
        lines.append(
            "| {row} | `{label}` | {asset} | `{b0:02X} {b1:02X} {b2:02X} {b3:02X}` |".format(
                row=row["sequence_index"],
                label=row["label"],
                asset=render_asset(row["asset"]),
                b0=params["byte_0"],
                b1=params["byte_1"],
                b2=params["byte_2"],
                b3=params["byte_3"],
            )
        )

    lines.extend(["", "## Open Questions", ""])
    for question in contract["open_questions"]:
        lines.append(f"- {question}")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build CC PSI animation bundle contracts.")
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
        "psi animation bundle contracts: "
        f"{totals['psi_animation_bundles']} bundles, "
        f"{totals['unique_gfx_sets']} gfx sets, "
        f"{totals['unique_arrangements']} arrangements"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
