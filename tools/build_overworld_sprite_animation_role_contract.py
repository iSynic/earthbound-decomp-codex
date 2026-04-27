from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_FRAME_CONTRACT = ROOT / "notes" / "overworld-sprite-frame-contracts.json"
DEFAULT_JSON_OUT = ROOT / "notes" / "overworld-sprite-animation-roles.json"
DEFAULT_MARKDOWN_OUT = ROOT / "notes" / "overworld-sprite-animation-roles.md"
SCHEMA = "earthbound-decomp.overworld-sprite-animation-roles.v1"

DIRECTION_ORDER = [
    "up",
    "up_right",
    "right",
    "down_right",
    "down",
    "down_left",
    "left",
    "up_left",
]

DIRECTION_ENUM_NAMES = {
    direction: direction.upper()
    for direction in DIRECTION_ORDER
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Promote overworld sprite runtime slots into art-facing animation roles."
    )
    parser.add_argument("--frame-contract", default=str(DEFAULT_FRAME_CONTRACT))
    parser.add_argument("--json-out", default=str(DEFAULT_JSON_OUT))
    parser.add_argument("--markdown-out", default=str(DEFAULT_MARKDOWN_OUT))
    return parser.parse_args()


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def role_model(slot_count: int, layout_family: str) -> dict[str, str]:
    if slot_count == 0:
        return {
            "kind": "empty",
            "confidence": "high",
            "description": "No runtime sprite slots are present.",
        }
    if slot_count == 16:
        return {
            "kind": "two_phase_eight_direction_set",
            "confidence": "high",
            "description": (
                "Sixteen slots split into two eight-direction passes. The order follows "
                "the ebsrc DIRECTION enum, with phase 0 as the base pose row and phase 1 "
                "as an alternate/step pose row."
            ),
        }
    if slot_count == 8:
        return {
            "kind": "single_phase_eight_direction_set",
            "confidence": "high",
            "description": "Eight slots map directly to the ebsrc DIRECTION enum order.",
        }
    if slot_count == 9:
        return {
            "kind": "single_phase_eight_direction_set_plus_extra",
            "confidence": "medium",
            "description": (
                "The first eight slots map to the ebsrc DIRECTION enum order; slot 8 is "
                "a group-specific extra pose."
            ),
        }
    return {
        "kind": "custom_slot_sequence",
        "confidence": "low",
        "description": (
            "The slot count does not match the common 8/9/16 direction layouts. "
            f"Frame-contract layout family is {layout_family!r}."
        ),
    }


def phase_role(slot_count: int, phase_hint: Any) -> dict[str, Any]:
    if slot_count == 16:
        phase_index = int(phase_hint)
        if phase_index == 0:
            return {
                "index": 0,
                "name": "base_pose",
                "description": "First direction pass; usually the actor's base/contact pose.",
            }
        return {
            "index": phase_index,
            "name": "alternate_step_pose",
            "description": "Second direction pass; usually the actor's walking/alternate pose.",
        }
    if slot_count in {8, 9}:
        return {
            "index": None,
            "name": "single_pose",
            "description": "Only one pose is declared for this direction in the grouping record.",
        }
    return {
        "index": phase_hint,
        "name": "custom_phase",
        "description": "No common phase model is assigned for this slot count.",
    }


def descriptor_pass_role(pointer_flags: int) -> dict[str, Any]:
    pass_index = 1 if pointer_flags & 0x01 else 0
    if pass_index == 1:
        return {
            "index": 1,
            "name": "mirrored_piece_layout",
            "source": "pointer_flag_bit_0",
            "description": (
                "Uses secondary visual descriptor pass 1, selected by pointer bit 0. "
                "C0 initializes this as one body-pass span after pass 0."
            ),
        }
    return {
        "index": 0,
        "name": "primary_piece_layout",
        "source": "pointer_flag_bit_0_clear",
        "description": "Uses secondary visual descriptor pass 0.",
    }


def direction_role(slot: dict[str, Any], slot_count: int) -> dict[str, Any]:
    slot_index = int(slot["slot_index"])
    direction = slot.get("direction_hint")
    if isinstance(direction, str) and direction in DIRECTION_ENUM_NAMES:
        return {
            "index": slot_index % 8,
            "name": direction,
            "enum": f"DIRECTION::{DIRECTION_ENUM_NAMES[direction]}",
            "confidence": "high" if slot_count in {8, 9, 16} else "low",
        }
    if slot_count == 9 and slot_index == 8:
        return {
            "index": None,
            "name": "extra",
            "enum": None,
            "confidence": "medium",
        }
    return {
        "index": None,
        "name": "custom",
        "enum": None,
        "confidence": "low",
    }


def art_role_name(direction: dict[str, Any], phase: dict[str, Any]) -> str:
    direction_name = str(direction["name"])
    phase_name = str(phase["name"])
    if direction_name in {"extra", "custom"}:
        return direction_name
    if phase_name == "single_pose":
        return direction_name
    return f"{direction_name}_{phase_name}"


def normalized_asset_id(slot: dict[str, Any]) -> str | None:
    asset = slot.get("resolved_asset")
    if not isinstance(asset, dict):
        return None
    value = asset.get("asset_id")
    return str(value) if value is not None else None


def slot_role(slot: dict[str, Any], slot_count: int) -> dict[str, Any]:
    direction = direction_role(slot, slot_count)
    phase = phase_role(slot_count, slot.get("phase_hint"))
    pass_role = descriptor_pass_role(int(slot["pointer_flags"]))
    return {
        "slot_index": slot["slot_index"],
        "art_role": art_role_name(direction, phase),
        "direction": direction,
        "phase": phase,
        "descriptor_pass": pass_role,
        "pointer_flags": slot["pointer_flags"],
        "raw_pointer_word": slot["raw_pointer_word"],
        "normalized_pointer_offset": slot["normalized_pointer_offset"],
        "sprite_bank": slot["sprite_bank"],
        "resolved_asset": normalized_asset_id(slot),
        "source_range": slot.get("resolved_asset", {}).get("source_range"),
        "confidence": "high" if slot_count in {8, 16} else "medium" if slot_count == 9 else "low",
    }


def build_document(frame_contract: dict[str, Any]) -> dict[str, Any]:
    groups = []
    role_model_counts: Counter[str] = Counter()
    phase_counts: Counter[str] = Counter()
    descriptor_pass_counts: Counter[str] = Counter()
    direction_counts: Counter[str] = Counter()

    for group in frame_contract["groups"]:
        slot_count = int(group["runtime_slot_count"])
        layout_family = str(group["layout_family"]["kind"])
        model = role_model(slot_count, layout_family)
        role_model_counts[model["kind"]] += 1

        slots = [slot_role(slot, slot_count) for slot in group["runtime_slots"]]
        for slot in slots:
            phase_counts[slot["phase"]["name"]] += 1
            descriptor_pass_counts[slot["descriptor_pass"]["name"]] += 1
            direction_counts[slot["direction"]["name"]] += 1

        groups.append(
            {
                "label": group["label"],
                "enum_name": group["enum_name"],
                "overworld_sprite_id": group["overworld_sprite_id"],
                "runtime_slot_count": slot_count,
                "runtime_slot_model": group["runtime_slot_model"]["kind"],
                "layout_family": layout_family,
                "payload_model": group["payload_model"]["kind"],
                "role_model": model,
                "base_oam_attribute_byte": group["sprite_grouping_record"]["header"][
                    "base_oam_attribute_byte"
                ],
                "oam_palette_id": group["sprite_grouping_record"]["header"]["oam_palette_id"],
                "slots": slots,
            }
        )

    return {
        "schema": SCHEMA,
        "game": "earthbound-us",
        "title": "Overworld sprite animation role contract",
        "source_contract": rel(DEFAULT_FRAME_CONTRACT),
        "source_policy": {
            "contains_rom_derived_outputs": False,
            "safe_to_commit": True,
        },
        "generator": {
            "tool": "tools/build_overworld_sprite_animation_role_contract.py",
        },
        "references": [
            "notes/overworld-sprite-frame-contracts.json",
            "notes/secondary-visual-descriptor-contracts.json",
            "refs/ebsrc-main/ebsrc-main/include/enums.asm DIRECTION enum",
            "refs/ebsrc-main/ebsrc-main/include/structs.asm sprite_grouping",
            "refs/ebsrc-main/ebsrc-main/include/macros.asm SPRITES macro",
            "src/c0/c0_a3a4_build_display_record_from_current_task_data.asm",
            "src/c0/c0_1e49_initialize_entity_with_sprite_pose.asm",
        ],
        "direction_order": [
            {"index": index, "name": direction, "enum": f"DIRECTION::{DIRECTION_ENUM_NAMES[direction]}"}
            for index, direction in enumerate(DIRECTION_ORDER)
        ],
        "phase_names": {
            "base_pose": "Phase 0 in 16-slot groups; usually the base/contact pose row.",
            "alternate_step_pose": "Phase 1 in 16-slot groups; usually the alternate walking/animation pose row.",
            "single_pose": "Only one pose is declared for this direction.",
        },
        "summary": {
            "group_count": len(groups),
            "role_models": dict(sorted(role_model_counts.items())),
            "phase_roles": dict(sorted(phase_counts.items())),
            "descriptor_pass_roles": dict(sorted(descriptor_pass_counts.items())),
            "direction_roles": dict(sorted(direction_counts.items())),
        },
        "groups": groups,
    }


def write_json(path: Path, document: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_markdown(path: Path, document: dict[str, Any]) -> None:
    summary = document["summary"]
    lines = [
        "# Overworld Sprite Animation Roles",
        "",
        "Generated by `tools/build_overworld_sprite_animation_role_contract.py`.",
        "",
        "This note summarizes `notes/overworld-sprite-animation-roles.json`, an art-facing role layer over the lower-level runtime frame contract.",
        "",
        "## Coverage",
        "",
        f"- Sprite groups classified: {summary['group_count']}",
        "- Direction order source: `refs/ebsrc-main/ebsrc-main/include/enums.asm` `DIRECTION` enum.",
        "- Descriptor pass source: pointer bit 0 plus the C0 body-pass span documented in the frame contract.",
        "- Palette role source: sprite grouping header byte +3 decoded as OAM palette bits.",
        "",
        "## Role Models",
        "",
        "| Model | Groups |",
        "| --- | ---: |",
    ]
    for key, count in summary["role_models"].items():
        lines.append(f"| `{key}` | {count} |")

    lines.extend(["", "## Phase Roles", "", "| Role | Slots |", "| --- | ---: |"])
    for key, count in summary["phase_roles"].items():
        lines.append(f"| `{key}` | {count} |")

    lines.extend(["", "## Descriptor Pass Roles", "", "| Role | Slots |", "| --- | ---: |"])
    for key, count in summary["descriptor_pass_roles"].items():
        lines.append(f"| `{key}` | {count} |")

    lines.extend(["", "## Direction Roles", "", "| Direction | Slots |", "| --- | ---: |"])
    for key, count in summary["direction_roles"].items():
        lines.append(f"| `{key}` | {count} |")

    examples = [
        group
        for group in document["groups"]
        if group["role_model"]["kind"] in {
            "two_phase_eight_direction_set",
            "single_phase_eight_direction_set",
            "single_phase_eight_direction_set_plus_extra",
        }
    ][:6]
    lines.extend(["", "## Examples", ""])
    for group in examples:
        preview = ", ".join(
            f"{slot['slot_index']}=`{slot['art_role']}`"
            for slot in group["slots"][: min(8, len(group["slots"]))]
        )
        lines.append(f"- `{group['label']}`: {preview}")

    lines.extend(
        [
            "",
            "## Interpretation Rules",
            "",
            "- `art_role` names are stable tool-facing labels derived from slot position, not final animation-script semantics.",
            "- Sixteen-slot groups are promoted to two eight-direction passes: `base_pose` followed by `alternate_step_pose`.",
            "- Eight-slot groups are promoted to one `single_pose` per direction.",
            "- Nine-slot groups use the first eight slots as directions and reserve slot 8 as `extra` until a group-specific use is verified.",
            "- `descriptor_pass.name` records whether pointer bit 0 selects the primary or mirrored secondary-visual-descriptor body pass.",
            "- Custom slot counts stay conservative and should be inspected group-by-group before port code treats them as directional animation sets.",
            "",
            "## Next Step",
            "",
            "Use this role contract as the join point for map/object placement tools, editors, and any future native engine animation schema.",
        ]
    )

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    frame_contract_path = Path(args.frame_contract)
    frame_contract = json.loads(frame_contract_path.read_text(encoding="utf-8"))
    document = build_document(frame_contract)
    document["source_contract"] = rel(frame_contract_path)
    write_json(Path(args.json_out), document)
    write_markdown(Path(args.markdown_out), document)
    print(
        "Built overworld sprite animation role contract: "
        f"{document['summary']['group_count']} groups, "
        f"{len(document['summary']['role_models'])} role models."
    )
    print(f"Wrote {rel(Path(args.json_out))}")
    print(f"Wrote {rel(Path(args.markdown_out))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
