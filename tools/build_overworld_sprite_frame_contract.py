from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
SCHEMA = "earthbound-decomp.overworld-sprite-frame-contracts.v1"
DEFAULT_GROUP_CONTRACT = ROOT / "notes" / "overworld-sprite-groups.json"
DEFAULT_JSON_OUT = ROOT / "notes" / "overworld-sprite-frame-contracts.json"
DEFAULT_MARKDOWN_OUT = ROOT / "notes" / "overworld-sprite-frame-semantics.md"

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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a conservative frame-semantics contract for overworld sprite groups."
    )
    parser.add_argument("--group-contract", default=str(DEFAULT_GROUP_CONTRACT))
    parser.add_argument("--json-out", default=str(DEFAULT_JSON_OUT))
    parser.add_argument("--markdown-out", default=str(DEFAULT_MARKDOWN_OUT))
    return parser.parse_args()


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def collision_is_zero(metadata: dict[str, Any]) -> bool:
    keys = [
        "North/South Collision Width",
        "North/South Collision Height",
        "East/West Collision Width",
        "East/West Collision Height",
    ]
    return all(int(metadata.get(key, 0)) == 0 for key in keys)


def payload_model(payload_count: int, slot_count: int) -> dict[str, Any]:
    if payload_count == 0:
        return {"kind": "metadata_only", "confidence": "high"}
    if slot_count == 0:
        return {"kind": "payloads_without_runtime_slots", "confidence": "medium"}
    if payload_count == slot_count:
        return {"kind": "one_payload_per_runtime_slot", "reuse_factor": 1, "confidence": "high"}
    if payload_count == 1:
        return {
            "kind": "single_payload_reused_by_runtime_slots",
            "reuse_factor": slot_count,
            "confidence": "high",
        }
    if slot_count % payload_count == 0:
        return {
            "kind": "payloads_reused_evenly_by_runtime_slots",
            "reuse_factor": slot_count // payload_count,
            "confidence": "medium",
        }
    if payload_count < slot_count:
        return {
            "kind": "payloads_reused_or_mirrored_by_runtime_slots",
            "reuse_factor": None,
            "confidence": "medium",
        }
    return {
        "kind": "payloads_exceed_runtime_slots",
        "reuse_factor": None,
        "confidence": "low",
    }


def slot_model(slot_count: int) -> dict[str, Any]:
    if slot_count == 0:
        return {
            "kind": "empty",
            "description": "No runtime sprite pointers are declared.",
            "confidence": "high",
        }
    if slot_count == 8:
        return {
            "kind": "eight_direction_slots",
            "description": "Likely one slot per DIRECTION enum entry.",
            "confidence": "medium",
        }
    if slot_count == 16:
        return {
            "kind": "sixteen_direction_phase_slots",
            "description": "Likely two animation phases for each DIRECTION enum entry.",
            "confidence": "medium",
        }
    if slot_count == 9:
        return {
            "kind": "eight_direction_slots_plus_extra",
            "description": "Likely one slot per DIRECTION enum entry plus one special/extra slot.",
            "confidence": "low",
        }
    return {
        "kind": "custom_slot_count",
        "description": "Runtime pointer count does not match the common 8/9/16 shapes.",
        "confidence": "low",
    }


def runtime_slots(slot_count: int) -> list[dict[str, Any]]:
    slots: list[dict[str, Any]] = []
    if slot_count == 8:
        for index, direction in enumerate(DIRECTION_ORDER):
            slots.append({"slot_index": index, "direction_hint": direction, "phase_hint": None})
        return slots
    if slot_count == 16:
        for phase in range(2):
            for direction_index, direction in enumerate(DIRECTION_ORDER):
                slots.append(
                    {
                        "slot_index": (phase * 8) + direction_index,
                        "direction_hint": direction,
                        "phase_hint": phase,
                    }
                )
        return slots
    if slot_count == 9:
        for index, direction in enumerate(DIRECTION_ORDER):
            slots.append({"slot_index": index, "direction_hint": direction, "phase_hint": None})
        slots.append({"slot_index": 8, "direction_hint": None, "phase_hint": "extra"})
        return slots
    return [
        {"slot_index": index, "direction_hint": None, "phase_hint": None}
        for index in range(slot_count)
    ]


def layout_family(group: dict[str, Any]) -> dict[str, str]:
    payload_count = int(group["payload_count"])
    metadata = group["metadata"]
    slot_count = int(metadata.get("Length", 0))
    size = metadata["Size"]
    size_key = f"{size['width']}x{size['height']}"
    no_collision = collision_is_zero(metadata)

    if slot_count == 0:
        return {"kind": "empty_group", "confidence": "high"}
    if payload_count == 1 and no_collision:
        return {"kind": "single_static_effect_or_prop", "confidence": "medium"}
    if payload_count == 1:
        return {"kind": "single_payload_actor_or_prop", "confidence": "medium"}
    if slot_count == 16 and payload_count in {8, 9}:
        return {"kind": "full_actor_walkset", "confidence": "medium"}
    if slot_count == 16 and payload_count in {3, 4}:
        return {"kind": "compact_actor_walkset_with_reuse", "confidence": "medium"}
    if slot_count == 8 and payload_count == 8:
        return {"kind": "one_payload_per_direction", "confidence": "medium"}
    if slot_count == 8 and payload_count == 4:
        if size_key in {"16x24", "24x24", "32x32"}:
            return {"kind": "four_payload_direction_set", "confidence": "medium"}
        return {"kind": "four_payload_object_or_vehicle_set", "confidence": "medium"}
    if slot_count == 8 and payload_count in {2, 3, 5}:
        return {"kind": "compact_object_or_special_animation", "confidence": "medium"}
    if slot_count == 9:
        return {"kind": "special_nine_slot_group", "confidence": "low"}
    return {"kind": "custom_layout", "confidence": "low"}


def payload_entries(group: dict[str, Any]) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for ordinal, payload in enumerate(group["sprite_payloads"]):
        asset = payload["asset"]
        entries.append(
            {
                "ordinal": ordinal,
                "sprite_id": payload["sprite_id"],
                "asset_id": asset["asset_id"],
                "source_range": asset["source"]["range"],
                "raw_output": asset["raw_output"],
                "palette_00_preview": asset["palette_00_preview"],
                "semantic_status": "payload_order_known_frame_role_unknown",
            }
        )
    return entries


def build_frame_contract(group_contract: dict[str, Any]) -> dict[str, Any]:
    groups: list[dict[str, Any]] = []
    family_counts: Counter[str] = Counter()
    slot_model_counts: Counter[str] = Counter()
    payload_model_counts: Counter[str] = Counter()

    for group in group_contract["groups"]:
        metadata = group["metadata"]
        slot_count = int(metadata.get("Length", 0))
        p_model = payload_model(int(group["payload_count"]), slot_count)
        s_model = slot_model(slot_count)
        family = layout_family(group)
        family_counts[family["kind"]] += 1
        slot_model_counts[s_model["kind"]] += 1
        payload_model_counts[p_model["kind"]] += 1
        groups.append(
            {
                "label": group["label"],
                "enum_name": group["enum_name"],
                "overworld_sprite_id": group["overworld_sprite_id"],
                "size": metadata["Size"],
                "collision": {
                    "north_south": {
                        "width": metadata["North/South Collision Width"],
                        "height": metadata["North/South Collision Height"],
                    },
                    "east_west": {
                        "width": metadata["East/West Collision Width"],
                        "height": metadata["East/West Collision Height"],
                    },
                    "all_zero": collision_is_zero(metadata),
                },
                "swim_flags": metadata["Swim Flags"],
                "runtime_slot_count": slot_count,
                "runtime_slot_model": s_model,
                "runtime_slots": runtime_slots(slot_count),
                "payload_count": group["payload_count"],
                "payload_model": p_model,
                "layout_family": family,
                "payloads": payload_entries(group),
                "frame_role_status": "direction_slot_hypothesis_only_pointer_table_not_extracted",
            }
        )

    return {
        "schema": SCHEMA,
        "game": "earthbound-us",
        "title": "Overworld sprite frame semantics contract",
        "source_policy": {
            "requires_user_supplied_rom_for_outputs": True,
            "do_not_commit_generated_outputs": True,
        },
        "generator": {"tool": "tools/build_overworld_sprite_frame_contract.py"},
        "references": [
            "notes/overworld-sprite-groups.json",
            "refs/ebsrc-main/ebsrc-main/include/structs.asm",
            "refs/ebsrc-main/ebsrc-main/include/enums.asm",
        ],
        "summary": {
            "group_count": len(groups),
            "runtime_slot_models": dict(sorted(slot_model_counts.items())),
            "payload_models": dict(sorted(payload_model_counts.items())),
            "layout_families": dict(sorted(family_counts.items())),
            "group_contract_referenced_payloads": group_contract["summary"][
                "referenced_sprite_payloads"
            ],
            "group_contract_unreferenced_payloads": group_contract["summary"][
                "unreferenced_sprite_assets"
            ],
            "group_contract_overflow_payloads": group_contract["summary"][
                "overflow_sprite_payloads"
            ],
        },
        "direction_order_reference": {
            "source": "refs/ebsrc-main/ebsrc-main/include/enums.asm DIRECTION enum",
            "order": DIRECTION_ORDER,
            "status": "hypothesis_for_runtime_slots_until_pointer_arrays_are_extracted",
        },
        "groups": groups,
    }


def write_json(path: Path, document: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_markdown(path: Path, document: dict[str, Any]) -> None:
    summary = document["summary"]
    lines = [
        "# Overworld Sprite Frame Semantics",
        "",
        "Generated by `tools/build_overworld_sprite_frame_contract.py`.",
        "",
        "This note summarizes `notes/overworld-sprite-frame-contracts.json`, a conservative "
        "frame-semantics layer over `notes/overworld-sprite-groups.json`.",
        "",
        "## Coverage",
        "",
        f"- Sprite groups classified: {summary['group_count']}",
        f"- Group-linked sprite payloads: {summary['group_contract_referenced_payloads']}",
        f"- Ungrouped D1-D5 sprite payloads carried from the group contract: {summary['group_contract_unreferenced_payloads']}",
        f"- Overflow payload labels past group pointer length: {summary['group_contract_overflow_payloads']}",
        "",
        "## Runtime Slot Models",
        "",
        "| Model | Groups |",
        "| --- | ---: |",
    ]
    for key, count in summary["runtime_slot_models"].items():
        lines.append(f"| `{key}` | {count} |")

    lines.extend(["", "## Payload Models", "", "| Model | Groups |", "| --- | ---: |"])
    for key, count in summary["payload_models"].items():
        lines.append(f"| `{key}` | {count} |")

    lines.extend(["", "## Layout Families", "", "| Family | Groups |", "| --- | ---: |"])
    for key, count in summary["layout_families"].items():
        lines.append(f"| `{key}` | {count} |")

    lines.extend(
        [
            "",
            "## Interpretation Rules",
            "",
            "- `runtime_slot_count` comes from EBDecomp `sprite_groups.yml` `Length`, matching the variable `spritepointerarray` size described by ebsrc `sprite_grouping`.",
            "- `runtime_slots` use the ebsrc `DIRECTION` enum order as a hypothesis only. The exact slot-to-payload mapping still needs pointer-array extraction from the ROM/source table.",
            "- `payload_model` describes how many unique D1-D5 payloads are available relative to the runtime slot count.",
            "- `layout_family` is a deterministic classification from payload count, slot count, size, and collision metadata; it is not yet a final animation name.",
            "- ROM-derived graphics remain generated under `build/` and are not committed.",
            "",
            "## Next Step",
            "",
            "Extract the actual sprite pointer arrays from the `sprite_grouping` table so each runtime slot can point to a concrete payload ordinal. That will turn these hypotheses into exact direction/frame records.",
        ]
    )

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    group_contract_path = Path(args.group_contract)
    group_contract = json.loads(group_contract_path.read_text(encoding="utf-8"))
    document = build_frame_contract(group_contract)
    write_json(Path(args.json_out), document)
    write_markdown(Path(args.markdown_out), document)
    print(
        "Built overworld sprite frame contract: "
        f"{document['summary']['group_count']} groups, "
        f"{len(document['summary']['layout_families'])} layout families."
    )
    print(f"Wrote {rel(Path(args.json_out))}")
    print(f"Wrote {rel(Path(args.markdown_out))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
