from __future__ import annotations

import argparse
import difflib
import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
SCHEMA = "earthbound-decomp.overworld-sprite-groups.v1"

DEFAULT_SPRITE_GROUPS_YML = ROOT / "refs" / "eb-decompile-4ef92" / "sprite_groups.yml"
DEFAULT_OVERWORLD_SPRITES = (
    ROOT / "refs" / "ebsrc-main" / "ebsrc-main" / "include" / "constants" / "overworldsprites.asm"
)
DEFAULT_BANKCONFIG_DIR = ROOT / "refs" / "ebsrc-main" / "ebsrc-main" / "src" / "bankconfig" / "common"
DEFAULT_ASSET_MANIFEST_DIR = ROOT / "asset-manifests"
DEFAULT_JSON_OUT = ROOT / "notes" / "overworld-sprite-groups.json"
DEFAULT_MARKDOWN_OUT = ROOT / "notes" / "overworld-sprite-group-contracts.md"

GROUP_LABEL_RE = re.compile(r"^(SPRITE_GROUP_[A-Z0-9_]+):")
SPRITE_LABEL_RE = re.compile(r"^SPRITE_(\d{4}):")
BINARY_RE = re.compile(r'\b(LOCALEBINARY|BINARY)\s+"overworld_sprites/gfx/(\d{4})\.gfx"')
ENUM_RE = re.compile(r"^\s*([A-Z0-9_]+)\s*;(\d+)\s*$")
GROUP_ID_RE = re.compile(r"^(\d+):\s*$")
SCALAR_RE = re.compile(r"^\s{2}([^:]+):\s*(.*)$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a machine-readable contract for overworld sprite groups."
    )
    parser.add_argument("--sprite-groups-yml", default=str(DEFAULT_SPRITE_GROUPS_YML))
    parser.add_argument("--overworld-sprites", default=str(DEFAULT_OVERWORLD_SPRITES))
    parser.add_argument("--bankconfig-dir", default=str(DEFAULT_BANKCONFIG_DIR))
    parser.add_argument("--asset-manifest-dir", default=str(DEFAULT_ASSET_MANIFEST_DIR))
    parser.add_argument("--json-out", default=str(DEFAULT_JSON_OUT))
    parser.add_argument("--markdown-out", default=str(DEFAULT_MARKDOWN_OUT))
    return parser.parse_args()


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def parse_bool_list(text: str) -> list[bool]:
    return [item == "true" for item in re.findall(r"\btrue\b|\bfalse\b", text)]


def parse_sprite_group_metadata(path: Path) -> dict[int, dict[str, Any]]:
    entries: dict[int, dict[str, Any]] = {}
    current_id: int | None = None
    pending_key: str | None = None
    pending_value = ""

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        group_match = GROUP_ID_RE.match(raw_line)
        if group_match:
            current_id = int(group_match.group(1))
            entries[current_id] = {}
            pending_key = None
            pending_value = ""
            continue

        if current_id is None:
            continue

        if pending_key:
            pending_value += " " + raw_line.strip()
            if "]" in raw_line:
                entries[current_id][pending_key] = parse_bool_list(pending_value)
                pending_key = None
                pending_value = ""
            continue

        scalar_match = SCALAR_RE.match(raw_line)
        if not scalar_match:
            continue
        key, value = scalar_match.groups()
        key = key.strip()
        value = value.strip()
        if key == "Swim Flags":
            if "]" in value:
                entries[current_id][key] = parse_bool_list(value)
            else:
                pending_key = key
                pending_value = value
            continue
        if key == "Size":
            size_match = re.match(r"^(\d+)x(\d+)(?:\s+(.*))?$", value.lower())
            if not size_match:
                raise ValueError(f"Could not parse sprite group size {value!r} for group {current_id}")
            width, height, suffix = size_match.groups()
            entries[current_id][key] = {
                "width": int(width),
                "height": int(height),
                "raw": value,
            }
            if suffix:
                entries[current_id][key]["suffix"] = suffix
            continue
        entries[current_id][key] = int(value)

    return entries


def parse_overworld_sprite_enum(path: Path) -> dict[str, int]:
    entries: dict[str, int] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        match = ENUM_RE.match(line)
        if match:
            entries[match.group(1)] = int(match.group(2))
    return entries


def parse_group_payloads(bankconfig_dir: Path) -> list[dict[str, Any]]:
    groups: list[dict[str, Any]] = []
    current_group: dict[str, Any] | None = None
    pending_sprite_id: int | None = None

    for bank in range(11, 16):
        path = bankconfig_dir / f"bank{bank}.asm"
        for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            line = raw_line.strip()
            group_match = GROUP_LABEL_RE.match(line)
            if group_match:
                current_group = {
                    "label": group_match.group(1),
                    "bank_config": rel(path),
                    "line": line_number,
                    "sprite_payloads": [],
                }
                groups.append(current_group)
                pending_sprite_id = None
                continue

            sprite_match = SPRITE_LABEL_RE.match(line)
            if sprite_match:
                pending_sprite_id = int(sprite_match.group(1))
                continue

            binary_match = BINARY_RE.search(line)
            if binary_match and current_group is not None:
                path_sprite_id = int(binary_match.group(2))
                current_group["sprite_payloads"].append(
                    {
                        "sprite_id": path_sprite_id,
                        "label_sprite_id": pending_sprite_id,
                        "directive": binary_match.group(1),
                        "path": f"overworld_sprites/gfx/{path_sprite_id:04d}.gfx",
                    }
                )
                pending_sprite_id = None

    return groups


def output_path_by_kind(outputs: list[dict[str, Any]], kind: str) -> str | None:
    for output in outputs:
        if output.get("kind") == kind:
            return str(output.get("path"))
    return None


def load_sprite_asset_lookup(asset_manifest_dir: Path) -> dict[int, dict[str, Any]]:
    lookup: dict[int, dict[str, Any]] = {}
    for path in sorted(asset_manifest_dir.glob("bank-d*-assets.json")):
        manifest = json.loads(path.read_text(encoding="utf-8"))
        for asset in manifest.get("assets", []):
            for output in asset.get("outputs", []):
                raw_path = str(output.get("path", ""))
                match = re.fullmatch(r"d([1-5])/overworld_sprites/gfx/(\d{4})\.gfx", raw_path)
                if not match:
                    continue
                sprite_id = int(match.group(2))
                lookup[sprite_id] = {
                    "asset_id": asset.get("id"),
                    "manifest": rel(path),
                    "source": asset.get("source", {}),
                    "raw_output": raw_path,
                    "grayscale_preview": output_path_by_kind(
                        asset.get("outputs", []), "snes_4bpp_tiles_png"
                    ),
                    "palette_00_preview": output_path_by_kind(
                        asset.get("outputs", []), "snes_4bpp_tiles_palette_png"
                    ),
                }
    return lookup


def enum_name_for_group_label(label: str) -> str:
    return label.removeprefix("SPRITE_GROUP_")


def alias_key(name: str) -> str:
    key = name
    replacements = {
        "FIVE": "5",
        "PJ": "PJS",
        "PAJAMAS": "PJS",
        "PAJAMA": "PJS",
        "PHOTOGRAPHERS": "PHOTOGRAPHER",
        "STARMASTER": "STAR_MASTER",
        "STARMASTERS": "STAR_MASTER",
        "DARK_HAIRED": "DARK_HAIR",
        "BLONDE_GUY_IN_SUIT": "BLONDE_GUY_IN_A_SUIT",
    }
    for old, new in replacements.items():
        key = key.replace(old, new)
    return re.sub(r"[^A-Z0-9]+", "", key)


def alias_tokens(name: str) -> set[str]:
    normalized = name
    replacements = {
        "FIVE": "5",
        "PJ": "PJS",
        "PAJAMAS": "PJS",
        "PAJAMA": "PJS",
        "PHOTOGRAPHERS": "PHOTOGRAPHER",
        "STARMASTER": "STAR_MASTER",
        "STARMASTERS": "STAR_MASTER",
    }
    for old, new in replacements.items():
        normalized = normalized.replace(old, new)
    return {token for token in normalized.split("_") if token and token not in {"A", "THE", "IN", "OF"}}


def candidate_aliases(enum_name: str, enum_by_name: dict[str, int], limit: int = 5) -> list[dict[str, Any]]:
    target_key = alias_key(enum_name)
    target_tokens = alias_tokens(enum_name)
    candidates: list[dict[str, Any]] = []
    for candidate_name, sprite_id in enum_by_name.items():
        candidate_key = alias_key(candidate_name)
        candidate_tokens = alias_tokens(candidate_name)
        overlap = len(target_tokens & candidate_tokens) / max(len(target_tokens | candidate_tokens), 1)
        score = max(
            difflib.SequenceMatcher(None, enum_name, candidate_name).ratio(),
            difflib.SequenceMatcher(None, target_key, candidate_key).ratio(),
        )
        score = max(score, (score * 0.65) + (overlap * 0.45))
        if target_tokens and target_tokens <= candidate_tokens:
            score += 0.2
        elif candidate_tokens and candidate_tokens <= target_tokens:
            score += 0.08
        if enum_name in candidate_name or candidate_name in enum_name:
            score += 0.05
        candidates.append(
            {
                "enum_name": candidate_name,
                "overworld_sprite_id": sprite_id,
                "score": round(min(score, 1.0), 3),
            }
        )
    return sorted(candidates, key=lambda item: (-item["score"], item["overworld_sprite_id"]))[:limit]


def attach_metadata(
    groups: list[dict[str, Any]],
    enum_by_name: dict[str, int],
    metadata_by_id: dict[int, dict[str, Any]],
    asset_by_sprite_id: dict[int, dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    enriched: list[dict[str, Any]] = []
    missing_assets: list[dict[str, Any]] = []
    unmatched_labels: list[str] = []
    alias_candidates: list[dict[str, Any]] = []
    payload_count = 0

    for group in groups:
        enum_name = enum_name_for_group_label(group["label"])
        overworld_sprite_id = enum_by_name.get(enum_name)
        metadata = metadata_by_id.get(overworld_sprite_id) if overworld_sprite_id is not None else None
        if overworld_sprite_id is None:
            unmatched_labels.append(group["label"])
            alias_candidates.append(
                {
                    "label": group["label"],
                    "enum_name": enum_name,
                    "candidates": candidate_aliases(enum_name, enum_by_name),
                }
            )

        payloads: list[dict[str, Any]] = []
        for payload in group["sprite_payloads"]:
            sprite_id = payload["sprite_id"]
            payload_count += 1
            asset = asset_by_sprite_id.get(sprite_id)
            if asset is None:
                missing_assets.append({"group": group["label"], "sprite_id": sprite_id})
            payloads.append({**payload, "asset": asset})

        enriched.append(
            {
                "label": group["label"],
                "enum_name": enum_name,
                "overworld_sprite_id": overworld_sprite_id,
                "metadata": metadata,
                "bank_config": group["bank_config"],
                "line": group["line"],
                "payload_count": len(payloads),
                "sprite_payloads": payloads,
            }
        )

    summary = {
        "group_count": len(enriched),
        "groups_with_metadata": sum(1 for group in enriched if group["metadata"] is not None),
        "groups_without_metadata": sum(1 for group in enriched if group["metadata"] is None),
        "referenced_sprite_payloads": payload_count,
        "unique_referenced_sprite_payloads": len(
            {payload["sprite_id"] for group in enriched for payload in group["sprite_payloads"]}
        ),
        "available_sprite_assets": len(asset_by_sprite_id),
        "missing_sprite_assets": len(missing_assets),
        "unmatched_group_labels": len(unmatched_labels),
    }
    return enriched, {
        "summary": summary,
        "missing_sprite_assets": missing_assets,
        "unmatched_group_labels": unmatched_labels,
        "alias_candidates": alias_candidates,
    }


def write_json(path: Path, document: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_markdown(path: Path, document: dict[str, Any]) -> None:
    summary = document["summary"]
    references = document["references"]
    unmatched = document["unmatched_group_labels"]
    alias_candidates = document["alias_candidates"]
    missing = document["missing_sprite_assets"]
    groups = document["groups"]
    payloads_by_bank: dict[str, int] = {}
    for group in groups:
        for payload in group["sprite_payloads"]:
            asset = payload.get("asset")
            manifest = asset.get("manifest") if asset else "missing"
            payloads_by_bank[manifest] = payloads_by_bank.get(manifest, 0) + 1

    lines = [
        "# Overworld Sprite Group Contracts",
        "",
        "Generated by `tools/build_overworld_sprite_group_manifest.py`.",
        "",
        "This note summarizes the checked-in sprite group contract in "
        "`notes/overworld-sprite-groups.json`. It ties ebsrc `SPRITE_GROUP_*` labels to the "
        "D1-D5 sprite tile payloads and, when the labels match, EBDecomp group size/collision metadata.",
        "",
        "## Inputs",
        "",
    ]
    lines.extend(f"- `{ref}`" for ref in references)
    lines.extend(
        [
            "",
            "## Coverage",
            "",
            f"- Sprite groups from ebsrc bankconfig: {summary['group_count']}",
            f"- Groups with exact EBDecomp metadata matches: {summary['groups_with_metadata']}",
            f"- Groups still needing enum alias mapping: {summary['groups_without_metadata']}",
            f"- Referenced sprite payload records: {summary['referenced_sprite_payloads']}",
            f"- Unique referenced sprite payloads: {summary['unique_referenced_sprite_payloads']}",
            f"- Available D1-D5 sprite assets: {summary['available_sprite_assets']}",
            f"- Missing D1-D5 sprite assets: {summary['missing_sprite_assets']}",
            "",
            "## Payload Distribution",
            "",
            "| Manifest | Referenced payloads |",
            "| --- | ---: |",
        ]
    )
    for manifest, count in sorted(payloads_by_bank.items()):
        lines.append(f"| `{manifest}` | {count} |")

    lines.extend(
        [
            "",
            "## Remaining Interpretation",
            "",
            "- The JSON records the sprite tile payload sequence, source ranges, and default palette previews.",
            "- It does not yet infer the full animation frame order or direction table semantics.",
            "- Several ebsrc group labels use names that differ from the `OVERWORLD_SPRITE` enum names, so their "
            "size/collision metadata is intentionally left unresolved until an alias map is added.",
            "- Ranked enum alias candidates are included in the JSON as hints only; they are not applied to metadata.",
            "- No ROM-derived bytes or rendered assets are committed by this contract; generated outputs remain under `build/`.",
            "",
            "## Enum Alias Frontier",
            "",
        ]
    )
    if unmatched:
        preview = unmatched[:40]
        lines.extend(f"- `{label}`" for label in preview)
        if len(unmatched) > len(preview):
            lines.append(f"- ... {len(unmatched) - len(preview)} more in `notes/overworld-sprite-groups.json`")
    else:
        lines.append("- None.")

    lines.extend(["", "## Alias Candidate Samples", ""])
    if alias_candidates:
        for item in alias_candidates[:10]:
            candidates = ", ".join(
                f"`{candidate['enum_name']}` ({candidate['score']:.3f})"
                for candidate in item["candidates"][:3]
            )
            lines.append(f"- `{item['label']}`: {candidates}")
        if len(alias_candidates) > 10:
            lines.append(f"- ... {len(alias_candidates) - 10} more in `notes/overworld-sprite-groups.json`")
    else:
        lines.append("- None.")

    lines.extend(["", "## Missing Payload Assets", ""])
    if missing:
        lines.extend(f"- `{item['group']}` references sprite `{item['sprite_id']:04d}`" for item in missing)
    else:
        lines.append("- None.")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    sprite_groups_yml = Path(args.sprite_groups_yml)
    overworld_sprites = Path(args.overworld_sprites)
    bankconfig_dir = Path(args.bankconfig_dir)
    asset_manifest_dir = Path(args.asset_manifest_dir)

    metadata_by_id = parse_sprite_group_metadata(sprite_groups_yml)
    enum_by_name = parse_overworld_sprite_enum(overworld_sprites)
    group_payloads = parse_group_payloads(bankconfig_dir)
    asset_by_sprite_id = load_sprite_asset_lookup(asset_manifest_dir)
    groups, diagnostics = attach_metadata(group_payloads, enum_by_name, metadata_by_id, asset_by_sprite_id)

    document = {
        "schema": SCHEMA,
        "game": "earthbound-us",
        "title": "Overworld sprite group contract",
        "source_policy": {
            "requires_user_supplied_rom_for_outputs": True,
            "do_not_commit_generated_outputs": True,
        },
        "generator": {
            "tool": "tools/build_overworld_sprite_group_manifest.py",
        },
        "references": [
            rel(sprite_groups_yml),
            rel(overworld_sprites),
            rel(bankconfig_dir / "bank11.asm"),
            rel(bankconfig_dir / "bank12.asm"),
            rel(bankconfig_dir / "bank13.asm"),
            rel(bankconfig_dir / "bank14.asm"),
            rel(bankconfig_dir / "bank15.asm"),
            rel(asset_manifest_dir / "bank-d1-assets.json"),
            rel(asset_manifest_dir / "bank-d2-assets.json"),
            rel(asset_manifest_dir / "bank-d3-assets.json"),
            rel(asset_manifest_dir / "bank-d4-assets.json"),
            rel(asset_manifest_dir / "bank-d5-assets.json"),
        ],
        "summary": diagnostics["summary"],
        "unmatched_group_labels": diagnostics["unmatched_group_labels"],
        "alias_candidates": diagnostics["alias_candidates"],
        "missing_sprite_assets": diagnostics["missing_sprite_assets"],
        "groups": groups,
    }

    write_json(Path(args.json_out), document)
    write_markdown(Path(args.markdown_out), document)
    print(
        "Built overworld sprite group contract: "
        f"{document['summary']['group_count']} groups, "
        f"{document['summary']['referenced_sprite_payloads']} payload references, "
        f"{document['summary']['missing_sprite_assets']} missing assets."
    )
    print(f"Wrote {rel(Path(args.json_out))}")
    print(f"Wrote {rel(Path(args.markdown_out))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
