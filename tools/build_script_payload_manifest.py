from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from decode_event_script import Address, decode_script, load_names, parse_address
from rom_tools import find_rom, hirom_to_file_offset, load_rom


ROOT = Path(__file__).resolve().parent.parent
SCHEMA = "earthbound-decomp.script-payloads.v1"
DEFAULT_WORKING_NAMES = ROOT / "build" / "working-names-c0-c3.json"
DEFAULT_INDEX = ROOT / "build" / "ref-index.json"


SCRIPT_NOTE_PATHS = {
    "notes/c3-intro-script-frontier-9ff2-a07f.md",
    "notes/c3-event-222-224-movement-helper-cluster.md",
    "notes/c3-actionscript-movement-pulse-presets-a0b2-ab26.md",
    "notes/c3-temporary-actor-movement-and-release-scripts.md",
    "notes/c3-timed-delivery-controller-working-names.md",
}

EFFECT_SCRIPT_ADDRESSES = {"C3:F819"}

NON_EVENT_NAME_RE = re.compile(r"(Pattern|PointerTable|PreludeData|Table|Tiles|Rows|Grid|Triples)$")
BRANCH_NAME_RE = re.compile(r"^(Loop|Return|Finish|Hold|Wait|Clear|Start)")
EVENT_NAME_RE = re.compile(
    r"(Script|Event|Pulse|Preset|Movement|Delivery|Actor|ActiveEntity|WaitUntil|"
    r"LoopParty|CameraPan|Halt|Refresh|Init)"
)


def normalize_path(path: str) -> str:
    return path.replace("\\", "/")


def evidence_notes(entry: dict[str, Any]) -> tuple[str, ...]:
    notes: list[str] = []
    for item in entry.get("evidence", []):
        note = normalize_path(str(item.get("note", "")))
        if note and note not in notes:
            notes.append(note)
    return tuple(notes)


def load_working_entries(path: Path) -> list[dict[str, Any]]:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    entries = []
    for entry in manifest.get("entries", []):
        address = str(entry.get("address", ""))
        if not address.startswith("C3:"):
            continue
        notes = evidence_notes(entry)
        if not notes:
            continue
        if any(note in SCRIPT_NOTE_PATHS for note in notes) or str(entry.get("address")) in EFFECT_SCRIPT_ADDRESSES:
            entries.append(entry)
    return sorted(entries, key=lambda item: int(str(item["address"]).split(":", 1)[1], 16))


def byte_at(rom: bytes, address: Address) -> int | None:
    offset = hirom_to_file_offset(address.bank, address.offset, len(rom))
    if offset is None or offset >= len(rom):
        return None
    return rom[offset]


def raw_preview(rom: bytes, address: Address, length: int = 16) -> str:
    offset = hirom_to_file_offset(address.bank, address.offset, len(rom))
    if offset is None:
        return ""
    return " ".join(f"{byte:02X}" for byte in rom[offset : offset + length])


def classify(entry: dict[str, Any], rom: bytes) -> tuple[str, str]:
    address = parse_address(str(entry["address"]))
    name = str(entry["name"])
    notes = evidence_notes(entry)
    first_byte = byte_at(rom, address)

    if str(entry["address"]) in EFFECT_SCRIPT_ADDRESSES:
        return "effect-script-payload", "battle visual effect-script payload; not decoded by the event VM"
    if name.startswith("IntroMovementPattern") or NON_EVENT_NAME_RE.search(name):
        return "movement-pattern-record", "documented as compact data, not event bytecode"
    if first_byte is None:
        return "unmapped", "address does not map to ROM data"
    if first_byte > 0x44:
        return "data-or-branch-label", "first byte is outside the currently known event opcode range"
    if BRANCH_NAME_RE.search(name) and "Script" not in name and "Event" not in name:
        return "event-branch-label", "promoted branch/helper label inside event bytecode"
    if EVENT_NAME_RE.search(name):
        return "event-bytecode", "decoded with tools/decode_event_script.py"
    return "event-bytecode", "selected from C3 script notes and decodable opcode prefix"


def decode_for_manifest(rom: bytes, address: Address, names: dict[str, list[str]]) -> list[str]:
    return decode_script(
        rom,
        address,
        max_instructions=40,
        max_bytes=0x120,
        stop_at_terminal=True,
        names=names,
    )


def decode_status(lines: list[str]) -> str:
    if not lines:
        return "not-decoded"
    joined = "\n".join(lines)
    if "unknown event opcode" in joined or "args unknown" in joined:
        return "partial"
    if lines[-1].startswith("; stopped"):
        return "limit"
    return "complete"


def build_manifest(working_names: Path, index: Path, rom_path: str | None) -> dict[str, Any]:
    entries = load_working_entries(working_names)
    rom = load_rom(find_rom(rom_path))
    names = load_names(index)
    payloads: list[dict[str, Any]] = []

    for entry in entries:
        address = parse_address(str(entry["address"]))
        kind, reason = classify(entry, rom)
        decoded: list[str] = []
        if kind in {"event-bytecode", "event-branch-label"}:
            decoded = decode_for_manifest(rom, address, names)
        payload = {
            "address": entry["address"],
            "name": entry["name"],
            "kind": kind,
            "classification_note": reason,
            "decode_status": "pending",
            "evidence": [
                {
                    "note": normalize_path(str(item.get("note", ""))),
                    "line": item.get("line"),
                    "section": item.get("section"),
                }
                for item in entry.get("evidence", [])
            ],
            "raw_preview": raw_preview(rom, address, 16),
        }
        if decoded:
            payload["decode_status"] = decode_status(decoded)
            payload["decoded"] = decoded
        elif kind in {"effect-script-payload", "movement-pattern-record"}:
            payload["decode_status"] = "not-applicable"
        else:
            payload["decode_status"] = "not-decoded"
        payloads.append(payload)

    by_kind = Counter(str(item["kind"]) for item in payloads)
    by_decode = Counter(str(item.get("decode_status", "not-decoded")) for item in payloads)
    return {
        "schema": SCHEMA,
        "generated_by": "tools/build_script_payload_manifest.py",
        "working_names": str(working_names.relative_to(ROOT) if working_names.is_relative_to(ROOT) else working_names),
        "ref_index": str(index.relative_to(ROOT) if index.is_relative_to(ROOT) else index),
        "summary": {
            "payloads": len(payloads),
            "by_kind": dict(sorted(by_kind.items())),
            "by_decode_status": dict(sorted(by_decode.items())),
        },
        "payloads": payloads,
    }


def markdown_escape(text: str) -> str:
    return text.replace("|", "\\|")


def render_markdown(manifest: dict[str, Any]) -> str:
    summary = manifest["summary"]
    payloads = manifest["payloads"]
    lines = [
        "# C3 script payload manifest",
        "",
        "Generated from promoted C3 working names in script-oriented notes. This is a machine-readable front door for event/actionscript bytecode and neighboring script-shaped payloads; edit `tools/build_script_payload_manifest.py`, then regenerate this file.",
        "",
        "## Summary",
        "",
        f"- schema: `{manifest['schema']}`",
        f"- payloads: `{summary['payloads']}`",
        f"- by kind: `{summary['by_kind']}`",
        f"- by decode status: `{summary['by_decode_status']}`",
        "",
        "| Address | Name | Kind | Decode | Note |",
        "| --- | --- | --- | --- | --- |",
    ]
    for payload in payloads:
        evidence = payload.get("evidence", [])
        note = ""
        if evidence:
            first = evidence[0]
            note = str(first.get("note", ""))
            if first.get("line"):
                note += f":{first['line']}"
        lines.append(
            "| `{address}` | `{name}` | `{kind}` | `{decode}` | {note} |".format(
                address=payload["address"],
                name=markdown_escape(str(payload["name"])),
                kind=payload["kind"],
                decode=payload.get("decode_status", "not-decoded"),
                note=markdown_escape(note),
            )
        )

    lines.extend(["", "## Payloads", ""])
    for payload in payloads:
        lines.extend(
            [
                f"### {payload['address']} {payload['name']}",
                "",
                f"- kind: `{payload['kind']}`",
                f"- decode status: `{payload.get('decode_status', 'not-decoded')}`",
                f"- classification: {payload['classification_note']}",
                f"- raw preview: `{payload['raw_preview']}`",
                "",
            ]
        )
        decoded = payload.get("decoded")
        if decoded:
            lines.extend(["```text", *decoded[:18]])
            if len(decoded) > 18:
                lines.append(f"; ... {len(decoded) - 18} more decoded lines in JSON manifest")
            lines.extend(["```", ""])
    return "\n".join(lines).rstrip() + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build the C3 event/actionscript payload manifest.")
    parser.add_argument("--working-names", type=Path, default=DEFAULT_WORKING_NAMES)
    parser.add_argument("--index", type=Path, default=DEFAULT_INDEX)
    parser.add_argument("--rom", help="path to EarthBound (USA).sfc")
    parser.add_argument("--json-out", type=Path, default=ROOT / "build" / "script-payloads-c3.json")
    parser.add_argument("--markdown-out", type=Path, default=ROOT / "notes" / "script-payloads-c3.md")
    return parser


def resolve_path(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def main() -> int:
    args = build_parser().parse_args()
    manifest = build_manifest(resolve_path(args.working_names), resolve_path(args.index), args.rom)

    json_out = resolve_path(args.json_out)
    json_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    markdown_out = resolve_path(args.markdown_out)
    markdown_out.parent.mkdir(parents=True, exist_ok=True)
    markdown_out.write_text(render_markdown(manifest), encoding="utf-8")

    summary = manifest["summary"]
    print(
        f"Wrote {json_out} and {markdown_out} "
        f"({summary['payloads']} payloads)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
