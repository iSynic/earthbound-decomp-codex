from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_JSON_OUT = ROOT / "build" / "sram-template-contracts.json"
DEFAULT_MARKDOWN_OUT = ROOT / "notes" / "sram-template-contracts.md"
MANIFEST_PATH = ROOT / "asset-manifests" / "bank-e0-assets.json"
COMPRESSED_PATH = ROOT / "build" / "assets" / "e0" / "mystery_sram.bin.lzhal"
DECOMPRESSED_PATH = ROOT / "build" / "assets" / "e0" / "mystery_sram.bin"
EBSRC_STRUCTS = ROOT / "refs" / "ebsrc-main" / "ebsrc-main" / "include" / "structs.asm"
EBSRC_SRAM = ROOT / "refs" / "ebsrc-main" / "ebsrc-main" / "src" / "bankconfig" / "common" / "sram.asm"


SIGNATURE = b"HAL Laboratory, inc."
BLOCK_SIZE = 0x500
USER_SAVE_SLOT_COUNT = 3
USER_SAVE_BLOCK_COUNT = USER_SAVE_SLOT_COUNT * 2
SAVE_SLOT_MISSING_MASKS = [0x01, 0x02, 0x04]
SECTIONS = [
    {"id": "header", "start": 0x000, "end": 0x020, "role": "save_header: signature plus checksum fields"},
    {"id": "game_state", "start": 0x020, "end": 0x1F8, "role": "game_state struct"},
    {
        "id": "party_characters",
        "start": 0x1F8,
        "end": 0x42C,
        "role": "six char_struct records",
    },
    {"id": "event_flags", "start": 0x42C, "end": 0x4AC, "role": "EVENT_FLAG_COUNT / 8 bytes"},
    {"id": "padding", "start": 0x4AC, "end": 0x500, "role": "save_block trailing padding"},
]


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def sha1(data: bytes) -> str:
    return hashlib.sha1(data).hexdigest()


def load_manifest_asset() -> dict[str, Any]:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    for asset in manifest["assets"]:
        if asset.get("id") == "asset.e0.compressed_sram":
            return asset
    raise KeyError("asset.e0.compressed_sram not found in bank E0 manifest")


def nonzero_count(data: bytes) -> int:
    return sum(1 for value in data if value != 0)


def first_nonzero_offsets(data: bytes, limit: int = 12) -> list[str]:
    offsets = [offset for offset, value in enumerate(data) if value != 0]
    return [f"0x{offset:03X}" for offset in offsets[:limit]]


def build_section(block: bytes, section: dict[str, Any]) -> dict[str, Any]:
    chunk = block[int(section["start"]) : int(section["end"])]
    return {
        "id": section["id"],
        "range_in_block": f"0x{int(section['start']):03X}..0x{int(section['end']):03X}",
        "bytes": len(chunk),
        "nonzero_bytes": nonzero_count(chunk),
        "sha1": sha1(chunk),
        "role": section["role"],
        "first_nonzero_offsets": first_nonzero_offsets(chunk),
        "all_zero": all(value == 0 for value in chunk),
    }


def calc_checksum(block: bytes) -> int:
    return sum(block[0x20:BLOCK_SIZE]) & 0xFFFF


def calc_checksum_complement(block: bytes) -> int:
    value = 0
    for offset in range(0x20, BLOCK_SIZE, 2):
        value ^= struct.unpack_from("<H", block, offset)[0]
    return value


def block_runtime_role(index: int) -> dict[str, Any]:
    if index < USER_SAVE_BLOCK_COUNT:
        slot_index = index // 2
        copy_role = "primary" if index % 2 == 0 else "backup"
        partner_index = index + 1 if copy_role == "primary" else index - 1
        return {
            "runtime_owner": f"save_slot_{slot_index}_{copy_role}",
            "user_save_slot": slot_index,
            "copy_role": copy_role,
            "partner_block": partner_index,
            "checked_by_integrity_loop": True,
            "missing_slot_mask": f"0x{SAVE_SLOT_MISSING_MASKS[slot_index]:02X}",
            "role_note": (
                f"Retail save slot {slot_index} {copy_role} copy. EF:0825 validates block {slot_index * 2} "
                f"then block {slot_index * 2 + 1}; if one copy is valid, EF:06A2 repairs the other."
            ),
        }
    return {
        "runtime_owner": f"reserved_template_block_{index}",
        "user_save_slot": None,
        "copy_role": "reserved",
        "partner_block": None,
        "checked_by_integrity_loop": False,
        "missing_slot_mask": None,
        "role_note": (
            "Present in the decompressed E0 template and inside the 0x2000 SRAM clear range, "
            "but outside the three retail save-slot pairs checked by EF:0683/EF:0825 and outside "
            "the save/load/copy/erase slot wrappers."
        ),
    }


def build_block(index: int, block: bytes) -> dict[str, Any]:
    checksum = struct.unpack_from("<H", block, 0x1C)[0]
    checksum_complement = struct.unpack_from("<H", block, 0x1E)[0]
    computed_checksum = calc_checksum(block)
    computed_complement = calc_checksum_complement(block)
    signature = block[:0x1C].rstrip(b"\0")
    return {
        "index": index,
        "range_in_payload": f"0x{index * BLOCK_SIZE:04X}..0x{(index + 1) * BLOCK_SIZE:04X}",
        "bytes": len(block),
        "sha1": sha1(block),
        "nonzero_bytes": nonzero_count(block),
        "signature_ascii": signature.decode("ascii", errors="replace"),
        "signature_matches": signature == SIGNATURE,
        "checksum": f"0x{checksum:04X}",
        "checksum_complement": f"0x{checksum_complement:04X}",
        "computed_checksum": f"0x{computed_checksum:04X}",
        "computed_checksum_complement": f"0x{computed_complement:04X}",
        "checksum_matches_computed": checksum == computed_checksum,
        "checksum_complement_matches_computed": checksum_complement == computed_complement,
        "runtime_role": block_runtime_role(index),
        "sections": [build_section(block, section) for section in SECTIONS],
    }


def ebsrc_struct_evidence() -> dict[str, Any]:
    text = EBSRC_STRUCTS.read_text(encoding="utf-8")
    required = [
        ".STRUCT save_header",
        ".STRUCT save_block",
        "header .tag save_header ;0",
        "game_state .tag game_state ;32",
        "party_characters .tag char_struct 6 ;504",
        "event_flags .byte EVENT_FLAG_COUNT / 8 ;1068",
        ".byte 1280 -",
    ]
    missing = [item for item in required if item not in text]
    return {
        "path": rel(EBSRC_STRUCTS),
        "required_fragments_found": not missing,
        "missing_fragments": missing,
        "save_block_size_bytes": BLOCK_SIZE,
        "section_offsets": [
            {
                "id": section["id"],
                "range_in_block": f"0x{int(section['start']):03X}..0x{int(section['end']):03X}",
                "bytes": int(section["end"]) - int(section["start"]),
                "role": section["role"],
            }
            for section in SECTIONS
        ],
    }


def build_contract() -> dict[str, Any]:
    asset = load_manifest_asset()
    compressed = COMPRESSED_PATH.read_bytes()
    decompressed = DECOMPRESSED_PATH.read_bytes()
    if len(decompressed) % BLOCK_SIZE != 0:
        raise ValueError(f"Decompressed SRAM template is not block-aligned to 0x{BLOCK_SIZE:X}")
    blocks = [
        build_block(ordinal, decompressed[offset : offset + BLOCK_SIZE])
        for ordinal, offset in enumerate(range(0, len(decompressed), BLOCK_SIZE))
    ]

    source = asset.get("source", {})
    if not isinstance(source, dict):
        source = {}

    return {
        "schema": "earthbound-decomp.sram-template-contracts.v1",
        "scope": "Bank E0 compressed SRAM/save-block initialization template",
        "inputs": {
            "manifest": rel(MANIFEST_PATH),
            "compressed_local_output": rel(COMPRESSED_PATH),
            "decompressed_local_output": rel(DECOMPRESSED_PATH),
            "ebsrc_structs": rel(EBSRC_STRUCTS),
            "ebsrc_sram_map": rel(EBSRC_SRAM),
        },
        "generated_json": rel(DEFAULT_JSON_OUT),
        "tracked_markdown": rel(DEFAULT_MARKDOWN_OUT),
        "asset": {
            "id": asset["id"],
            "title": asset["title"],
            "source_range": source.get("range"),
            "source_bytes": int(source.get("bytes", 0) or 0),
            "source_sha1": source.get("sha1"),
            "compressed_output_bytes": len(compressed),
            "compressed_output_sha1": sha1(compressed),
            "decompressed_output_bytes": len(decompressed),
            "decompressed_output_sha1": sha1(decompressed),
            "compression_ratio": round(len(compressed) / len(decompressed), 6),
        },
        "structure": {
            "block_size": BLOCK_SIZE,
            "block_count": len(blocks),
            "user_save_slot_count": USER_SAVE_SLOT_COUNT,
            "user_save_block_count": USER_SAVE_BLOCK_COUNT,
            "reserved_template_block_count": max(0, len(blocks) - USER_SAVE_BLOCK_COUNT),
            "total_template_bytes": len(decompressed),
            "signature": SIGNATURE.decode("ascii"),
            "ebsrc_struct_evidence": ebsrc_struct_evidence(),
        },
        "validation": {
            "decompressed_size_is_0x2800": len(decompressed) == 0x2800,
            "block_count_is_8": len(blocks) == 8,
            "all_blocks_are_0x500_bytes": all(block["bytes"] == BLOCK_SIZE for block in blocks),
            "all_blocks_have_hal_signature": all(block["signature_matches"] for block in blocks),
            "all_padding_sections_are_zero": all(
                next(section for section in block["sections"] if section["id"] == "padding")["all_zero"]
                for block in blocks
            ),
            "all_checksum_fields_match_ef0734_sum": all(block["checksum_matches_computed"] for block in blocks),
            "all_complement_fields_match_ef077b_xor": all(
                block["checksum_complement_matches_computed"] for block in blocks
            ),
            "first_six_blocks_map_to_three_redundant_save_slots": all(
                blocks[index]["runtime_role"]["user_save_slot"] == index // 2
                for index in range(min(USER_SAVE_BLOCK_COUNT, len(blocks)))
            ),
            "blocks_6_7_are_outside_retail_save_slot_loops": len(blocks) == 8
            and all(not blocks[index]["runtime_role"]["checked_by_integrity_loop"] for index in [6, 7]),
            "ebsrc_save_block_fragments_found": ebsrc_struct_evidence()["required_fragments_found"],
        },
        "slot_pairs": [
            {
                "slot": slot,
                "primary_block": slot * 2,
                "backup_block": slot * 2 + 1,
                "missing_slot_mask": f"0x{SAVE_SLOT_MISSING_MASKS[slot]:02X}",
                "runtime_contract": (
                    f"EF:0A4D saves slot {slot} to blocks {slot * 2}/{slot * 2 + 1}; "
                    f"EF:0A68 loads from primary block {slot * 2}; EF:0825 validates/repairs "
                    f"the pair and sets missing-slot mask 0x{SAVE_SLOT_MISSING_MASKS[slot]:02X} if both copies fail."
                ),
            }
            for slot in range(USER_SAVE_SLOT_COUNT)
        ],
        "checksum_algorithms": {
            "checksum_field": "Header word +0x1C stores EF:0734, the 16-bit sum of bytes 0x020..0x4FF.",
            "checksum_complement_field": "Header word +0x1E stores EF:077B, the 16-bit XOR of little-endian words 0x020..0x4FF.",
            "recalculated_by": "EF:088F writes game_state/party/event_flags into a save block, writes EF:0734 at +0x1C, verifies it, then writes EF:077B at +0x1E and verifies it. EF:0A4D calls EF:088F for both copies in a slot.",
            "validated_by": "EF:07C0 recomputes both fields; EF:0825 uses it to repair primary/backup pairs and mark missing slots.",
        },
        "blocks": blocks,
        "runtime_context": [
            {
                "source": "refs/ebsrc-main/ebsrc-main/src/bankconfig/common/bank20.asm",
                "role": "The asset is inserted as `COMPRESSED_SRAM` immediately after the USA romaji font and before the Mr. Saturn font data.",
            },
            {
                "source": "refs/ebsrc-main/ebsrc-main/include/structs.asm",
                "role": "`save_block` is a 1280-byte structure whose section offsets exactly match each decompressed 0x500-byte block.",
            },
            {
                "source": "refs/ebsrc-main/ebsrc-main/src/bankconfig/common/sram.asm",
                "role": "The SRAM segment defines SAVE_BASE and the live game-state/character/event-flag SRAM regions used by save logic.",
            },
            {
                "source": "src/ef/ef_05a9_0c3d_save_sram_helpers.asm",
                "role": "EF save helpers map three user save slots to primary/backup block pairs 0/1, 2/3, and 4/5; blocks 6/7 are outside the normal slot loops.",
            },
        ],
        "open_questions": [
            "Confirm whether reserved template blocks 6 and 7 have any non-retail, prototype, or tool-facing use before treating them as generated reserve records.",
            "Decide whether future installers should emit this as one compressed template blob or split it into eight save-block records.",
        ],
    }


def render_markdown(contract: dict[str, Any]) -> str:
    asset = contract["asset"]
    structure = contract["structure"]
    evidence = structure["ebsrc_struct_evidence"]
    lines = [
        "# SRAM Template Contracts",
        "",
        "Generated by `tools/build_sram_template_contracts.py`. This resolves the former E0 `COMPRESSED_SRAM` / `mystery_sram.bin.lzhal` payload as a compressed SRAM save-block initialization template.",
        "",
        "No ROM-derived SRAM template bytes are checked in by this report.",
        "",
        "## Snapshot",
        "",
        f"- asset: `{asset['id']}`",
        f"- source range: `{asset['source_range']}`",
        f"- compressed bytes: `{asset['compressed_output_bytes']}`",
        f"- decompressed bytes: `{asset['decompressed_output_bytes']}`",
        f"- compression ratio: `{asset['compression_ratio']}`",
        f"- save-block size: `0x{structure['block_size']:X}`",
        f"- save-block count: `{structure['block_count']}`",
        f"- user save slots: `{structure['user_save_slot_count']}`",
        f"- reserved template blocks: `{structure['reserved_template_block_count']}`",
        f"- repeated signature: `{structure['signature']}`",
        "",
        "## Validation",
        "",
    ]
    for key, value in contract["validation"].items():
        lines.append(f"- `{key}`: `{str(value).lower()}`")

    lines.extend(
        [
            "",
            "## Save-Block Shape",
            "",
            f"- ebsrc struct evidence: `{evidence['path']}`",
            f"- required save-block fragments found: `{str(evidence['required_fragments_found']).lower()}`",
            "",
            "| Section | Range in block | Bytes | Role |",
            "| --- | --- | ---: | --- |",
        ]
    )
    for section in evidence["section_offsets"]:
        lines.append(
            f"| `{section['id']}` | `{section['range_in_block']}` | {section['bytes']} | {section['role']} |"
        )

    lines.extend(
        [
            "",
            "## Block Inventory",
            "",
            "| Block | Runtime role | Payload range | Nonzero bytes | SHA-1 | Signature | Checksum | Complement | Padding zero |",
            "| ---: | --- | --- | ---: | --- | --- | --- | --- | --- |",
        ]
    )
    for block in contract["blocks"]:
        padding = next(section for section in block["sections"] if section["id"] == "padding")
        lines.append(
            "| {index} | `{role}` | `{range}` | {nonzero} | `{sha1}` | `{signature}` | `{checksum}` | `{complement}` | `{padding}` |".format(
                index=block["index"],
                role=block["runtime_role"]["runtime_owner"],
                range=block["range_in_payload"],
                nonzero=block["nonzero_bytes"],
                sha1=block["sha1"],
                signature=block["signature_ascii"],
                checksum=block["checksum"],
                complement=block["checksum_complement"],
                padding=str(padding["all_zero"]).lower(),
            )
        )

    lines.extend(
        [
            "",
            "## Runtime Slot Ownership",
            "",
            "| Save slot | Primary block | Backup block | Missing-slot mask | Runtime contract |",
            "| ---: | ---: | ---: | --- | --- |",
        ]
    )
    for pair in contract["slot_pairs"]:
        lines.append(
            "| {slot} | {primary} | {backup} | `{mask}` | {contract_text} |".format(
                slot=pair["slot"],
                primary=pair["primary_block"],
                backup=pair["backup_block"],
                mask=pair["missing_slot_mask"],
                contract_text=pair["runtime_contract"],
            )
        )

    reserved = [block for block in contract["blocks"] if block["runtime_role"]["copy_role"] == "reserved"]
    if reserved:
        lines.extend(["", "Reserved template blocks:"])
        for block in reserved:
            lines.append(f"- block `{block['index']}`: {block['runtime_role']['role_note']}")

    algorithms = contract["checksum_algorithms"]
    lines.extend(
        [
            "",
            "## Checksum Algorithms",
            "",
            f"- checksum: {algorithms['checksum_field']}",
            f"- complement: {algorithms['checksum_complement_field']}",
            f"- recalculation: {algorithms['recalculated_by']}",
            f"- validation/repair: {algorithms['validated_by']}",
            "",
            "| Block | Stored checksum | Computed checksum | Stored complement | Computed complement |",
            "| ---: | --- | --- | --- | --- |",
        ]
    )
    for block in contract["blocks"]:
        lines.append(
            "| {index} | `{checksum}` | `{computed_checksum}` | `{complement}` | `{computed_complement}` |".format(
                index=block["index"],
                checksum=block["checksum"],
                computed_checksum=block["computed_checksum"],
                complement=block["checksum_complement"],
                computed_complement=block["computed_checksum_complement"],
            )
        )

    lines.extend(["", "## Section Nonzero Counts", ""])
    lines.append("| Block | Header | Game state | Party characters | Event flags | Padding |")
    lines.append("| ---: | ---: | ---: | ---: | ---: | ---: |")
    for block in contract["blocks"]:
        counts = {section["id"]: section["nonzero_bytes"] for section in block["sections"]}
        lines.append(
            "| {index} | {header} | {game_state} | {party_characters} | {event_flags} | {padding} |".format(
                index=block["index"],
                header=counts["header"],
                game_state=counts["game_state"],
                party_characters=counts["party_characters"],
                event_flags=counts["event_flags"],
                padding=counts["padding"],
            )
        )

    lines.extend(["", "## Runtime Context", ""])
    for item in contract["runtime_context"]:
        lines.append(f"- `{item['source']}`: {item['role']}")

    lines.extend(["", "## Open Questions", ""])
    for question in contract["open_questions"]:
        lines.append(f"- {question}")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build E0 SRAM template contracts.")
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

    structure = contract["structure"]
    asset = contract["asset"]
    print(
        "sram template: "
        f"{structure['block_count']} blocks, "
        f"0x{structure['block_size']:X} bytes each, "
        f"{asset['decompressed_output_bytes']} decompressed bytes"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
