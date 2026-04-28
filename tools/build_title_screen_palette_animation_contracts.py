from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from decompress_c41a9e import decompress_blob


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_JSON_OUT = ROOT / "build" / "title-screen-palette-animation-contracts.json"
DEFAULT_MARKDOWN_OUT = ROOT / "notes" / "title-screen-palette-animation-contracts.md"
SOURCE_PATH = ROOT / "build" / "assets" / "e1" / "E1AE7C.bin.lzhal"
LEGACY_PATH = (
    ROOT
    / "refs"
    / "earthbound-disasm-legacy"
    / "Earthbound Decomp"
    / "EB"
    / "Routine_Macros_EB.asm"
)
EVENT_SCRIPT = ROOT / "refs" / "ebsrc-main" / "ebsrc-main" / "src" / "data" / "events" / "C42235.asm"
QUICK_SCRIPT = ROOT / "refs" / "ebsrc-main" / "ebsrc-main" / "src" / "data" / "events" / "scripts" / "789.asm"
C0_NOTE = ROOT / "notes" / "title-screen-logo-palette-event-helpers-c0ebe0-c0ee53.md"


SUBPAYLOADS: list[dict[str, Any]] = [
    {
        "id": "title.initial_animation_palette",
        "label": "Initial title-screen animation palette",
        "legacy_label": "InitialTitleScreenAnimationPalette",
        "range": "E1:AE7C..E1:AE83",
        "offset": 0,
        "source_bytes": 7,
        "expected_frames": 1,
        "runtime_role": "Initial 0x20-byte palette row loaded before title animation palette state is decompressed/advanced.",
    },
    {
        "id": "title.letter_palettes",
        "label": "Title-screen letter palettes",
        "legacy_label": "TitleScreenLetterPalettes",
        "range": "E1:AE83..E1:AEFD",
        "offset": 7,
        "source_bytes": 122,
        "expected_frames": 14,
        "runtime_role": "Letter palette animation frames loaded by C0:EC77(A=0) and advanced by C0:EDDA for 0x0E frames.",
    },
    {
        "id": "title.glow_palettes",
        "label": "Title-screen glow palettes",
        "legacy_label": "TitleScreenGlowPalettes",
        "range": "E1:AEFD..E1:AF7D",
        "offset": 129,
        "source_bytes": 128,
        "expected_frames": 20,
        "runtime_role": "Glow palette animation frames loaded by C0:EC77(A=1) and advanced by C0:EDDA for 0x14 frames.",
    },
]


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def sha1(data: bytes) -> str:
    return hashlib.sha1(data).hexdigest()


def decode_palette_words(data: bytes) -> list[str]:
    if len(data) % 2 != 0:
        raise ValueError(f"Palette payload must have even byte count, got {len(data)}")
    return [f"0x{data[index] | (data[index + 1] << 8):04X}" for index in range(0, len(data), 2)]


def build_subpayload(config: dict[str, Any], source: bytes) -> dict[str, Any]:
    start = int(config["offset"])
    end = start + int(config["source_bytes"])
    raw = source[start:end]
    decompressed, consumed = decompress_blob(raw, dest_base=0xC000)
    frames = [decompressed[index : index + 0x20] for index in range(0, len(decompressed), 0x20)]
    if any(len(frame) != 0x20 for frame in frames):
        raise ValueError(f"{config['id']} decompressed payload is not made of 0x20-byte palette rows")
    return {
        "id": config["id"],
        "label": config["label"],
        "legacy_label": config["legacy_label"],
        "range": config["range"],
        "source_offset_in_manifest_asset": start,
        "source_bytes": len(raw),
        "source_sha1": sha1(raw),
        "decompress_consumed_bytes": consumed,
        "decompressed_bytes": len(decompressed),
        "frame_count": len(frames),
        "expected_frames": config["expected_frames"],
        "frame_size": 0x20,
        "frames_match_expected": len(frames) == int(config["expected_frames"]),
        "runtime_role": config["runtime_role"],
        "first_frame_words": decode_palette_words(frames[0]) if frames else [],
        "last_frame_words": decode_palette_words(frames[-1]) if frames else [],
    }


def find_fragments(path: Path, fragments: list[str]) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8", errors="replace")
    missing = [fragment for fragment in fragments if fragment not in text]
    return {"path": rel(path), "found": not missing, "missing": missing}


def build_contract() -> dict[str, Any]:
    source = SOURCE_PATH.read_bytes()
    subpayloads = [build_subpayload(config, source) for config in SUBPAYLOADS]
    return {
        "schema": "earthbound-decomp.title-screen-palette-animation-contracts.v1",
        "scope": "E1:AE7C title-screen initial, letter, and glow palette animation payloads",
        "inputs": {
            "manifest_asset_raw_output": rel(SOURCE_PATH),
            "legacy_labels": rel(LEGACY_PATH),
            "event_flow": rel(EVENT_SCRIPT),
            "quick_title_script": rel(QUICK_SCRIPT),
            "c0_title_helper_note": rel(C0_NOTE),
        },
        "generated_json": rel(DEFAULT_JSON_OUT),
        "tracked_markdown": rel(DEFAULT_MARKDOWN_OUT),
        "summary": {
            "manifest_asset_range": "E1:AE7C..E1:AF7D",
            "manifest_asset_bytes": len(source),
            "subpayloads": len(subpayloads),
            "decompressed_palette_bytes": sum(int(item["decompressed_bytes"]) for item in subpayloads),
            "palette_frames_0x20": sum(int(item["frame_count"]) for item in subpayloads),
        },
        "validation": {
            "manifest_asset_size_is_257": len(source) == 257,
            "subpayload_source_bytes_sum_to_manifest_asset": sum(int(item["source_bytes"]) for item in subpayloads)
            == len(source),
            "all_subpayloads_decompress_exactly": all(
                int(item["decompress_consumed_bytes"]) == int(item["source_bytes"]) for item in subpayloads
            ),
            "all_frame_counts_match_expected": all(bool(item["frames_match_expected"]) for item in subpayloads),
            "legacy_labels_found": find_fragments(
                LEGACY_PATH,
                [
                    "InitialTitleScreenAnimationPalette:",
                    "TitleScreenLetterPalettes:",
                    "TitleScreenGlowPalettes:",
                ],
            )["found"],
            "normal_event_flow_uses_0x0e_and_0x14_frame_counts": find_fragments(
                EVENT_SCRIPT,
                ["EVENT_SET_VAR $02, $000E", "EVENT_LOOP $0E", "EVENT_SET_VAR $02, $0014", "EVENT_LOOP $14"],
            )["found"],
            "quick_path_calls_skipped_palette_state_builder": find_fragments(QUICK_SCRIPT, ["EVENT_UNKNOWN_C0ED5C"])[
                "found"
            ],
        },
        "subpayloads": subpayloads,
        "runtime_context": [
            {
                "source": "refs/earthbound-disasm-legacy/Earthbound Decomp/EB/Routine_Macros_EB.asm",
                "role": "Splits the current manifest's E1:AE7C..AF7D blob into InitialTitleScreenAnimationPalette, TitleScreenLetterPalettes, and TitleScreenGlowPalettes.",
            },
            {
                "source": "refs/ebsrc-main/ebsrc-main/src/data/events/C42235.asm",
                "role": "Normal title flow calls C0:EC77 with A=0 for a 0x0E-frame letter animation and A=1 for a 0x14-frame glow animation.",
            },
            {
                "source": "notes/title-screen-logo-palette-event-helpers-c0ebe0-c0ee53.md",
                "role": "Documents C0:EC77, C0:ED5C, and C0:EDDA; the skipped path copies final rows from decompressed offsets 0x01A0 and 0x0260, matching 14 and 20 palette frames.",
            },
        ],
        "open_questions": [
            "Decide whether to split asset.e1.unknown_e1ae7c into three manifest assets in a future manifest-normalization pass.",
            "Name the destination palette selector values used by the event temp vars (`$0008` for letters and `$0007` for glow) after following the C0 task variable mapping.",
        ],
    }


def render_words(words: list[str], limit: int = 8) -> str:
    shown = words[:limit]
    suffix = " ..." if len(words) > limit else ""
    return ", ".join(f"`{word}`" for word in shown) + suffix


def render_markdown(contract: dict[str, Any]) -> str:
    summary = contract["summary"]
    lines = [
        "# Title-Screen Palette Animation Contracts",
        "",
        "Generated by `tools/build_title_screen_palette_animation_contracts.py`. This promotes the former E1:AE7C followup into three legacy-corroborated title palette animation subpayloads.",
        "",
        "No ROM-derived palette bytes are checked in by this report.",
        "",
        "## Snapshot",
        "",
        f"- manifest asset range: `{summary['manifest_asset_range']}`",
        f"- manifest asset bytes: `{summary['manifest_asset_bytes']}`",
        f"- subpayloads: `{summary['subpayloads']}`",
        f"- decompressed palette bytes: `{summary['decompressed_palette_bytes']}`",
        f"- 0x20-byte palette frames: `{summary['palette_frames_0x20']}`",
        "",
        "## Validation",
        "",
    ]
    for key, value in contract["validation"].items():
        lines.append(f"- `{key}`: `{str(value).lower()}`")

    lines.extend(
        [
            "",
            "## Subpayloads",
            "",
            "| Subpayload | Range | Source bytes | Decompressed bytes | Frames | Role |",
            "| --- | --- | ---: | ---: | ---: | --- |",
        ]
    )
    for item in contract["subpayloads"]:
        lines.append(
            "| {label} | `{range}` | {source_bytes} | {decompressed} | {frames} | {role} |".format(
                label=item["label"],
                range=item["range"],
                source_bytes=item["source_bytes"],
                decompressed=item["decompressed_bytes"],
                frames=item["frame_count"],
                role=item["runtime_role"],
            )
        )

    lines.extend(["", "## Palette Row Samples", ""])
    for item in contract["subpayloads"]:
        lines.append(f"### {item['label']}")
        lines.append("")
        lines.append(f"- legacy label: `{item['legacy_label']}`")
        lines.append(f"- source SHA-1: `{item['source_sha1']}`")
        lines.append(f"- first frame words: {render_words(item['first_frame_words'])}")
        lines.append(f"- last frame words: {render_words(item['last_frame_words'])}")
        lines.append("")

    lines.extend(["## Runtime Context", ""])
    for item in contract["runtime_context"]:
        lines.append(f"- `{item['source']}`: {item['role']}")

    lines.extend(["", "## Open Questions", ""])
    for question in contract["open_questions"]:
        lines.append(f"- {question}")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build title-screen palette animation contracts.")
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

    summary = contract["summary"]
    print(
        "title palette animation: "
        f"{summary['subpayloads']} subpayloads, "
        f"{summary['palette_frames_0x20']} palette frames"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
