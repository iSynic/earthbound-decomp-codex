from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import rom_tools


SCHEMA = "earthbound-decomp.overworld-sprite-frame-contracts.v1"
DEFAULT_GROUP_CONTRACT = ROOT / "notes" / "overworld-sprite-groups.json"
DEFAULT_JSON_OUT = ROOT / "notes" / "overworld-sprite-frame-contracts.json"
DEFAULT_MARKDOWN_OUT = ROOT / "notes" / "overworld-sprite-frame-semantics.md"
POINTER_TABLE_BANK = 0xEF
POINTER_TABLE_OFFSET = 0x133F
POINTER_TABLE_ENTRIES = 464
SPRITE_GROUPING_DATA_END = 0x4A40
GROUPING_HEADER_SIZE = 9
SPRITE_ASSET_BANKS = ["d1", "d2", "d3", "d4", "d5"]

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
        description="Build a ROM-resolved frame-semantics contract for overworld sprite groups."
    )
    parser.add_argument("--rom", default=None, help="EarthBound US ROM path.")
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


def bank_addr(bank: int, offset: int) -> str:
    return f"{bank:02X}:{offset:04X}"


def bank_range(bank: int, start: int, end: int) -> str:
    return f"{bank:02X}:{start:04X}..{bank:02X}:{end:04X}"


def hex_byte(value: int) -> str:
    return f"${value:02X}"


def hex_word(value: int) -> str:
    return f"${value:04X}"


def parse_range_start(source_range: str) -> tuple[int, int]:
    start = source_range.split("..", 1)[0]
    bank_text, offset_text = start.split(":", 1)
    return int(bank_text, 16), int(offset_text, 16)


def output_path(asset: dict[str, Any], kind: str) -> str | None:
    for output in asset.get("outputs", []):
        if output.get("kind") == kind:
            return output.get("path")
    return None


def palette_preview_path(asset: dict[str, Any]) -> str | None:
    for output in asset.get("outputs", []):
        if (
            output.get("kind") == "snes_4bpp_tiles_palette_png"
            and output.get("palette_id") == 0
        ):
            return output.get("path")
    return None


def sprite_id_from_asset(asset_id: str) -> int | None:
    marker = ".sprite_"
    if marker not in asset_id:
        return None
    try:
        return int(asset_id.rsplit(marker, 1)[1])
    except ValueError:
        return None


def load_sprite_asset_lookup() -> dict[tuple[int, int], dict[str, Any]]:
    lookup: dict[tuple[int, int], dict[str, Any]] = {}
    for bank_text in SPRITE_ASSET_BANKS:
        manifest_path = ROOT / "asset-manifests" / f"bank-{bank_text}-assets.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        for asset in manifest["assets"]:
            source_range = asset["source"]["range"]
            bank, start = parse_range_start(source_range)
            asset_id = asset["id"]
            lookup[(bank, start)] = {
                "sprite_id": sprite_id_from_asset(asset_id),
                "asset_id": asset_id,
                "source_range": source_range,
                "raw_output": output_path(asset, "raw"),
                "palette_00_preview": palette_preview_path(asset),
                "manifest": rel(manifest_path),
            }
    return lookup


def decode_pointer_table(rom: bytes) -> list[dict[str, Any]]:
    table_file_offset = rom_tools.hirom_to_file_offset(
        POINTER_TABLE_BANK, POINTER_TABLE_OFFSET, len(rom)
    )
    if table_file_offset is None:
        raise ValueError("sprite grouping pointer table is not in ROM address space")

    entries: list[dict[str, Any]] = []
    for index in range(POINTER_TABLE_ENTRIES):
        file_offset = table_file_offset + (index * 4)
        pointer_offset = rom_tools.read_u16_le(rom, file_offset)
        pointer_bank = rom[file_offset + 2]
        padding = rom[file_offset + 3]
        table_offset = POINTER_TABLE_OFFSET + (index * 4)
        entries.append(
            {
                "index": index,
                "table_address": bank_range(
                    POINTER_TABLE_BANK, table_offset, table_offset + 4
                ),
                "target": bank_addr(pointer_bank, pointer_offset),
                "target_bank": pointer_bank,
                "target_offset": pointer_offset,
                "padding": padding,
            }
        )
    return entries


def decode_grouping_header(raw: bytes) -> dict[str, Any]:
    return {
        "raw": " ".join(f"{byte:02X}" for byte in raw),
        "height_units": raw[0],
        "width_or_oam_byte": raw[1],
        "size_code": raw[2],
        "palette": raw[3],
        "hitbox_north_south_width": raw[4],
        "hitbox_north_south_height": raw[5],
        "hitbox_east_west_width": raw[6],
        "hitbox_east_west_height": raw[7],
        "sprite_bank": f"{raw[8]:02X}",
    }


def resolve_asset(
    asset_lookup: dict[tuple[int, int], dict[str, Any]], sprite_bank: int, raw_word: int
) -> tuple[str, dict[str, Any] | None, int, int]:
    normalized_word = raw_word & 0xFFFC
    flags = raw_word & 0x0003
    exact_asset = asset_lookup.get((sprite_bank, raw_word))
    if exact_asset is not None:
        return "exact", exact_asset, normalized_word, flags

    masked_asset = asset_lookup.get((sprite_bank, normalized_word))
    if masked_asset is not None:
        return "masked_low_two_bits", masked_asset, normalized_word, flags

    return "unresolved", None, normalized_word, flags


def read_grouping_slots(
    rom: bytes,
    pointer_entry: dict[str, Any],
    slot_count: int,
    base_slots: list[dict[str, Any]],
    group_owned_asset_ids: set[str],
    asset_lookup: dict[tuple[int, int], dict[str, Any]],
) -> tuple[dict[str, Any], list[dict[str, Any]], Counter[str], Counter[str]]:
    record_bank = int(pointer_entry["target_bank"])
    record_offset = int(pointer_entry["target_offset"])
    record_file_offset = rom_tools.hirom_to_file_offset(record_bank, record_offset, len(rom))
    if record_file_offset is None:
        raise ValueError(f"grouping record is not in ROM address space: {pointer_entry['target']}")

    header_raw = rom[record_file_offset : record_file_offset + GROUPING_HEADER_SIZE]
    if len(header_raw) != GROUPING_HEADER_SIZE:
        raise ValueError(f"grouping record header is truncated: {pointer_entry['target']}")

    header = decode_grouping_header(header_raw)
    sprite_bank = int(header["sprite_bank"], 16)
    slot_bytes_start = record_file_offset + GROUPING_HEADER_SIZE
    slots: list[dict[str, Any]] = []
    resolution_counts: Counter[str] = Counter()
    ownership_counts: Counter[str] = Counter()

    for index in range(slot_count):
        raw_word = rom_tools.read_u16_le(rom, slot_bytes_start + (index * 2))
        resolution, asset, normalized_word, flags = resolve_asset(
            asset_lookup, sprite_bank, raw_word
        )
        resolution_counts[resolution] += 1

        if asset is None:
            ownership = "unresolved"
        elif asset["asset_id"] in group_owned_asset_ids:
            ownership = "group_owned"
        else:
            ownership = "ungrouped_or_overflow"
        ownership_counts[ownership] += 1

        slot = dict(base_slots[index])
        slot.update(
            {
                "raw_pointer_word": hex_word(raw_word),
                "normalized_pointer_offset": hex_word(normalized_word),
                "pointer_flags": flags,
                "sprite_bank": f"{sprite_bank:02X}",
                "resolution": resolution,
                "ownership": ownership,
                "resolved_asset": asset,
            }
        )
        slots.append(slot)

    record_length = GROUPING_HEADER_SIZE + (slot_count * 2)
    record = {
        "address": bank_addr(record_bank, record_offset),
        "range": bank_range(record_bank, record_offset, record_offset + record_length),
        "record_bytes": record_length,
        "header": header,
    }
    return record, slots, resolution_counts, ownership_counts


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


def build_frame_contract(group_contract: dict[str, Any], rom_arg: str | None) -> dict[str, Any]:
    rom_path = rom_tools.find_rom(rom_arg)
    rom = rom_tools.load_rom(rom_path)
    rom_info = rom_tools.read_rom_info(rom_path)
    verification_problems = rom_tools.verify_earthbound_us(rom_info)
    if verification_problems:
        raise ValueError(
            "ROM identity verification failed:\n"
            + "\n".join(f"- {problem}" for problem in verification_problems)
        )

    asset_lookup = load_sprite_asset_lookup()
    pointer_entries = decode_pointer_table(rom)
    groups: list[dict[str, Any]] = []
    family_counts: Counter[str] = Counter()
    slot_model_counts: Counter[str] = Counter()
    payload_model_counts: Counter[str] = Counter()
    pointer_flag_counts: Counter[str] = Counter()
    slot_resolution_counts: Counter[str] = Counter()
    slot_ownership_counts: Counter[str] = Counter()
    total_runtime_slots = 0
    max_grouping_record_end = 0

    for group in group_contract["groups"]:
        metadata = group["metadata"]
        slot_count = int(metadata.get("Length", 0))
        p_model = payload_model(int(group["payload_count"]), slot_count)
        s_model = slot_model(slot_count)
        family = layout_family(group)
        family_counts[family["kind"]] += 1
        slot_model_counts[s_model["kind"]] += 1
        payload_model_counts[p_model["kind"]] += 1
        total_runtime_slots += slot_count
        group_owned_asset_ids = {
            payload["asset"]["asset_id"] for payload in group["sprite_payloads"]
        }
        pointer_entry = pointer_entries[int(group["overworld_sprite_id"])]
        base_runtime_slots = runtime_slots(slot_count)
        grouping_record, resolved_slots, resolutions, ownerships = read_grouping_slots(
            rom,
            pointer_entry,
            slot_count,
            base_runtime_slots,
            group_owned_asset_ids,
            asset_lookup,
        )
        slot_resolution_counts.update(resolutions)
        slot_ownership_counts.update(ownerships)
        for slot in resolved_slots:
            pointer_flag_counts[str(slot["pointer_flags"])] += 1
        record_end = int(pointer_entry["target_offset"]) + int(grouping_record["record_bytes"])
        max_grouping_record_end = max(max_grouping_record_end, record_end)
        unresolved_slots = resolutions["unresolved"]
        frame_role_status = (
            "no_runtime_slots_to_resolve"
            if slot_count == 0
            else "runtime_slots_partially_unresolved_pointer_table_extracted"
            if unresolved_slots
            else "runtime_slots_resolved_to_payloads_direction_role_still_hypothesis"
        )
        groups.append(
            {
                "label": group["label"],
                "enum_name": group["enum_name"],
                "overworld_sprite_id": group["overworld_sprite_id"],
                "pointer_table_entry": {
                    "index": pointer_entry["index"],
                    "address": pointer_entry["table_address"],
                    "target": pointer_entry["target"],
                    "padding": hex_byte(pointer_entry["padding"]),
                },
                "sprite_grouping_record": grouping_record,
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
                "runtime_slots": resolved_slots,
                "payload_count": group["payload_count"],
                "payload_model": p_model,
                "layout_family": family,
                "payloads": payload_entries(group),
                "frame_role_status": frame_role_status,
            }
        )

    pointer_table_end = POINTER_TABLE_OFFSET + (POINTER_TABLE_ENTRIES * 4)
    data_start = min(entry["target_offset"] for entry in pointer_entries)
    data_end = max(SPRITE_GROUPING_DATA_END, max_grouping_record_end)
    resolved_runtime_slots = (
        slot_resolution_counts["exact"] + slot_resolution_counts["masked_low_two_bits"]
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
        "rom": {
            "sha1": rom_info.sha1,
            "verified": True,
        },
        "references": [
            "notes/overworld-sprite-groups.json",
            "refs/ebsrc-main/ebsrc-main/include/structs.asm",
            "refs/ebsrc-main/ebsrc-main/include/enums.asm",
            "refs/ebsrc-main/ebsrc-main/include/symbols/bank2f.inc.asm",
            "notes/bank-ef-asset-data-map.md",
        ],
        "summary": {
            "group_count": len(groups),
            "pointer_table": {
                "entries": POINTER_TABLE_ENTRIES,
                "range": bank_range(POINTER_TABLE_BANK, POINTER_TABLE_OFFSET, pointer_table_end),
                "record_width_bytes": 4,
            },
            "sprite_grouping_data": {
                "range": bank_range(POINTER_TABLE_BANK, data_start, data_end),
                "used_group_record_end": bank_addr(POINTER_TABLE_BANK, max_grouping_record_end),
            },
            "total_runtime_slots": total_runtime_slots,
            "resolved_runtime_slots": resolved_runtime_slots,
            "unresolved_runtime_slots": slot_resolution_counts["unresolved"],
            "slot_resolution_counts": dict(sorted(slot_resolution_counts.items())),
            "pointer_flag_counts": dict(sorted(pointer_flag_counts.items())),
            "slot_asset_ownership": dict(sorted(slot_ownership_counts.items())),
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
            "status": "slot_order_hint_only_exact_pointer_targets_are_extracted",
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
        "This note summarizes `notes/overworld-sprite-frame-contracts.json`, a ROM-resolved "
        "frame-semantics layer over `notes/overworld-sprite-groups.json`.",
        "",
        "## Coverage",
        "",
        f"- Sprite groups classified: {summary['group_count']}",
        f"- Group-linked sprite payloads: {summary['group_contract_referenced_payloads']}",
        f"- Ungrouped D1-D5 sprite payloads carried from the group contract: {summary['group_contract_unreferenced_payloads']}",
        f"- Overflow payload labels past group pointer length: {summary['group_contract_overflow_payloads']}",
        f"- Sprite grouping pointer table: `{summary['pointer_table']['range']}` ({summary['pointer_table']['entries']} entries)",
        f"- Sprite grouping record data: `{summary['sprite_grouping_data']['range']}`",
        f"- Runtime pointer slots resolved: {summary['resolved_runtime_slots']} / {summary['total_runtime_slots']}",
        f"- Runtime pointer slots unresolved: {summary['unresolved_runtime_slots']}",
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
        ["", "## Pointer Slot Resolution", "", "| Resolution | Slots |", "| --- | ---: |"]
    )
    for key, count in summary["slot_resolution_counts"].items():
        lines.append(f"| `{key}` | {count} |")

    lines.extend(
        ["", "## Pointer Flag Bits", "", "| Low-bit value | Slots |", "| --- | ---: |"]
    )
    for key, count in summary["pointer_flag_counts"].items():
        lines.append(f"| `{key}` | {count} |")

    lines.extend(
        ["", "## Slot Asset Ownership", "", "| Ownership | Slots |", "| --- | ---: |"]
    )
    for key, count in summary["slot_asset_ownership"].items():
        lines.append(f"| `{key}` | {count} |")

    lines.extend(
        [
            "",
            "## Interpretation Rules",
            "",
            "- `runtime_slot_count` comes from EBDecomp `sprite_groups.yml` `Length`, matching the variable `spritepointerarray` size described by ebsrc `sprite_grouping`.",
            "- `runtime_slots` now record the exact ROM pointer word, normalized D1-D5 graphics offset, low two pointer flag bits, and resolved asset ID for every slot.",
            "- Direction and phase labels still use the ebsrc `DIRECTION` enum order as semantic hints until verified against runtime animation code.",
            "- `payload_model` describes how many unique D1-D5 payloads are available relative to the runtime slot count.",
            "- `layout_family` is a deterministic classification from payload count, slot count, size, and collision metadata; it is not yet a final animation name.",
            "- ROM-derived graphics remain generated under `build/` and are not committed.",
            "",
            "## Next Step",
            "",
            "Name the low-bit pointer flags against renderer behavior, then use these exact slot mappings to build composed directional preview sheets for overworld sprite groups.",
        ]
    )

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    group_contract_path = Path(args.group_contract)
    group_contract = json.loads(group_contract_path.read_text(encoding="utf-8"))
    document = build_frame_contract(group_contract, args.rom)
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
