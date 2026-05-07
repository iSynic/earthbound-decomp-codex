#!/usr/bin/env python3
"""Build the checked-in SPC700 sound-driver source ingest manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import audio_spc700_source


DEFAULT_SOURCE_ROOT = ROOT / "refs" / "earthbound-sounddriver-byte-perfect"
DEFAULT_OUTPUT = ROOT / "manifests" / "audio-spc700-sounddriver-source-ingest.json"
DEFAULT_NOTES = ROOT / "notes" / "audio-spc700-sounddriver-source-ingest.md"

FILE_ROLES = {
    "main.asm": "main_driver_disassembly",
    "ram.asm": "spc700_ram_layout",
    "macros.asm": "assembler_macros_and_constants",
    "sfx_sequences.asm": "sound_effect_sequence_data",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build SPC700 sound-driver source ingest manifest.")
    parser.add_argument("--source-root", default=str(DEFAULT_SOURCE_ROOT), help="Extracted sound-driver source root.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Manifest output JSON.")
    parser.add_argument("--notes", default=str(DEFAULT_NOTES), help="Markdown output.")
    return parser.parse_args()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def file_records(source_root: Path) -> list[dict[str, Any]]:
    records = []
    for name, role in FILE_ROLES.items():
        path = source_root / name
        records.append(
            {
                "path": str(path.relative_to(ROOT)).replace("\\", "/"),
                "size": path.stat().st_size,
                "sha256": sha256(path),
                "role": role,
            }
        )
    return records


def build_manifest(source_root: Path) -> dict[str, Any]:
    source_summary = audio_spc700_source.source_table_summary(source_root / "main.asm", source_root / "ram.asm")
    return {
        "schema": "earthbound-decomp.audio-spc700-sounddriver-source-ingest.v1",
        "provenance": {
            "source_archive": "C:/Users/Eric/Downloads/sounddriver.zip",
            "archive_sha256": "1BB195F9C2C4BB5B9440B28C5110209F48826B6AE07955848964F02BC50742F2",
            "import_date": "2026-04-30",
        },
        "extracted_root": str(source_root.relative_to(ROOT)).replace("\\", "/"),
        "files": file_records(source_root),
        "source_navigation": source_summary,
        "source_backed_facts": [
            {
                "topic": "driver_base",
                "value": "main.asm declares base $0500 and presents a byte-accurate engine.bin build path through asar",
            },
            {
                "topic": "control_reader_labels",
                "value": f"{source_summary['get_next_byte']} is GetNextByte and {source_summary['skip_byte']} is SkipByte",
            },
            {
                "topic": "vcmd_dispatch",
                "value": f"VCMD_Jump_Table starts at {source_summary['vcmd_table']} and names handlers for {source_summary['vcmd_command_range']}",
            },
            {
                "topic": "vcmd_arg_lengths",
                "value": f"VCMD_Arg_Length starts at {source_summary['vcmd_arg_length_table']} and defines argument lengths for {source_summary['vcmd_command_range']}",
            },
            {
                "topic": "refuted_static_guess",
                "value": "0x16C7 is an SFX pointer table, not the music high-command dispatch table",
            },
        ],
        "related_notes": [
            "notes/audio-spc700-control-reader-frontier.md",
            "notes/audio-spc700-driver-dispatch-frontier.md",
            "notes/audio-sequence-command-semantics.md",
            "notes/audio-sequence-control-flow-frontier.md",
        ],
    }


def render_markdown(data: dict[str, Any]) -> str:
    files = [
        "| `{path}` | `{size}` | `{sha}` | {role} |".format(
            path=record["path"],
            size=record["size"],
            sha=record["sha256"],
            role=record["role"],
        )
        for record in data["files"]
    ]
    nav = data["source_navigation"]
    return "\n".join(
        [
            "# Audio SPC700 Sound Driver Source Ingest",
            "",
            "Status: byte-perfect SPC700-side source is checked in and linked to the audio frontier notes.",
            "",
            "## Provenance",
            "",
            f"- source archive: `{data['provenance']['source_archive']}`",
            f"- archive SHA-256: `{data['provenance']['archive_sha256']}`",
            f"- extracted root: `{data['extracted_root']}`",
            f"- manifest: `manifests/audio-spc700-sounddriver-source-ingest.json`",
            "",
            "## Extracted Files",
            "",
            "| File | Size | SHA-256 | Role |",
            "| --- | ---: | --- | --- |",
            *files,
            "",
            "## Source Navigation",
            "",
            f"- `VCMD_Jump_Table`: `{nav['vcmd_table']}`",
            f"- `VCMD_Arg_Length`: `{nav['vcmd_arg_length_table']}`",
            f"- `GetNextByte`: `{nav['get_next_byte']}`",
            f"- `SkipByte`: `{nav['skip_byte']}`",
            f"- VCMD command range: `{nav['vcmd_command_range']}`",
            f"- RAM aliases parsed: `{nav['ram_alias_count']}`",
            "",
            "## Immediate Source-Backed Facts",
            "",
            *[f"- {fact['value']}" for fact in data["source_backed_facts"]],
            "",
            "## Next Work",
            "",
            "- Keep command/effect promotion evidence-gated through the generated audio frontiers.",
            "- Use this source as the navigation layer for VCMD names, reader helpers, and RAM aliases.",
            "",
        ]
    )


def main() -> int:
    args = parse_args()
    data = build_manifest(Path(args.source_root))
    output = Path(args.output)
    notes = Path(args.notes)
    output.parent.mkdir(parents=True, exist_ok=True)
    notes.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    notes.write_text(render_markdown(data), encoding="utf-8")
    print(
        "Built audio SPC700 sound-driver source ingest: "
        f"{len(data['files'])} files, {data['source_navigation']['vcmd_entry_count']} VCMD entries"
    )
    print(f"Wrote {output}")
    print(f"Wrote {notes}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
