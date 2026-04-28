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


def build_block(index: int, block: bytes) -> dict[str, Any]:
    checksum = struct.unpack_from("<H", block, 0x1C)[0]
    checksum_complement = struct.unpack_from("<H", block, 0x1E)[0]
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
            "ebsrc_save_block_fragments_found": ebsrc_struct_evidence()["required_fragments_found"],
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
        ],
        "open_questions": [
            "Name the eight template blocks as primary, backup, or scenario seed slots after following the save initialization/copy routine.",
            "Document the checksum algorithm and when the checksum/complement fields are recalculated.",
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
            "| Block | Payload range | Nonzero bytes | SHA-1 | Signature | Checksum | Complement | Padding zero |",
            "| ---: | --- | ---: | --- | --- | --- | --- | --- |",
        ]
    )
    for block in contract["blocks"]:
        padding = next(section for section in block["sections"] if section["id"] == "padding")
        lines.append(
            "| {index} | `{range}` | {nonzero} | `{sha1}` | `{signature}` | `{checksum}` | `{complement}` | `{padding}` |".format(
                index=block["index"],
                range=block["range_in_payload"],
                nonzero=block["nonzero_bytes"],
                sha1=block["sha1"],
                signature=block["signature_ascii"],
                checksum=block["checksum"],
                complement=block["checksum_complement"],
                padding=str(padding["all_zero"]).lower(),
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
