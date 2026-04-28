from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from decode_event_script import (
    Address,
    CALL_ARG_COUNTS,
    CALL_TARGET_SEMANTICS,
    OPCODES,
    decode_script,
    load_names,
    parse_address,
)
from rom_tools import find_rom, hirom_to_file_offset, load_rom


ROOT = Path(__file__).resolve().parent.parent
SCHEMA = "earthbound-decomp.c3-actionscript-semantics-audit.v1"
DEFAULT_SOURCE_MAP = ROOT / "build" / "c3-source-data-map.json"
DEFAULT_INDEX = ROOT / "build" / "ref-index.json"
DEFAULT_JSON_OUT = ROOT / "build" / "c3-actionscript-semantics-audit.json"
DEFAULT_MARKDOWN_OUT = ROOT / "notes" / "c3-actionscript-semantics-audit.md"

SCRIPT_CLASSES = {
    "event-script-asset",
    "event-bytecode-asset",
    "event-bytecode-label",
}

CALLROUTINE_RE = re.compile(r"EVENT_CALLROUTINE\s+\$([0-9A-F]{2}:[0-9A-F]{4})")
TARGET_RE = re.compile(r"\$([0-9A-F]{2}:[0-9A-F]{4})")
UNKNOWN_OPCODE_RE = re.compile(r"^([0-9A-F]{2}:[0-9A-F]{4}).*unknown event opcode")
UNKNOWN_CALL_TARGET_RE = re.compile(
    r"EVENT_CALLROUTINE\s+\$([0-9A-F]{2}:[0-9A-F]{4}).*args unknown"
)


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def resolve_path(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def address_sort_key(address: str) -> int:
    parsed = parse_address(address)
    return parsed.long


def rom_offset_for(rom: bytes, address: Address) -> int | None:
    offset = hirom_to_file_offset(address.bank, address.offset, len(rom))
    if offset is None or offset >= len(rom):
        return None
    return offset


def raw_preview(rom: bytes, address: Address, length: int = 16) -> str:
    offset = rom_offset_for(rom, address)
    if offset is None:
        return ""
    return " ".join(f"{byte:02X}" for byte in rom[offset : offset + length])


def first_opcode(rom: bytes, address: Address) -> dict[str, Any]:
    offset = rom_offset_for(rom, address)
    if offset is None:
        return {"byte": None, "name": "unmapped", "known": False}
    value = rom[offset]
    opcode = OPCODES.get(value)
    return {
        "byte": f"${value:02X}",
        "name": opcode.name if opcode else "UNKNOWN_EVENT_OPCODE",
        "known": opcode is not None,
        "operands": list(opcode.args) if opcode else [],
        "terminal": bool(opcode.terminal) if opcode else False,
    }


def normalize_evidence(items: Any) -> list[str]:
    evidence: list[str] = []
    if not isinstance(items, list):
        return evidence
    for item in items:
        if isinstance(item, str):
            value = item
        elif isinstance(item, dict):
            note = str(item.get("note", ""))
            line = item.get("line")
            value = f"{note}:{line}" if note and line else note
        else:
            value = str(item)
        if value and value not in evidence:
            evidence.append(value)
    return evidence


def merge_entry(entries: dict[str, dict[str, Any]], entry: dict[str, Any]) -> None:
    address = str(entry["address"])
    current = entries.get(address)
    if current is None:
        entries[address] = entry
        return

    for source in entry.get("sources", []):
        if source not in current["sources"]:
            current["sources"].append(source)
    for extraction_class in entry.get("extraction_classes", []):
        if extraction_class not in current["extraction_classes"]:
            current["extraction_classes"].append(extraction_class)
    if current.get("primary_class") == "event-script-asset" and entry.get("primary_class") != "event-script-asset":
        current["primary_class"] = entry["primary_class"]
    if not current.get("name") and entry.get("name"):
        current["name"] = entry["name"]
    if not current.get("path") and entry.get("path"):
        current["path"] = entry["path"]
    if current.get("size") is None and entry.get("size") is not None:
        current["size"] = entry["size"]
    for evidence in entry.get("evidence", []):
        if evidence not in current["evidence"]:
            current["evidence"].append(evidence)


def load_script_entries(source_map: dict[str, Any]) -> list[dict[str, Any]]:
    entries: dict[str, dict[str, Any]] = {}

    for row in source_map.get("include_rows", []):
        address = row.get("address")
        extraction_class = str(row.get("extraction_class", ""))
        if not address or extraction_class not in SCRIPT_CLASSES:
            continue
        merge_entry(
            entries,
            {
                "address": str(address),
                "name": row.get("name"),
                "path": row.get("path"),
                "size": row.get("size"),
                "primary_class": extraction_class,
                "extraction_classes": [extraction_class],
                "sources": ["include-row"],
                "source_kind": row.get("source_kind"),
                "source_decode_status": row.get("script_decode_status"),
                "evidence": normalize_evidence(row.get("evidence", [])),
            },
        )

    for label in source_map.get("supplemental_labels", []):
        address = label.get("address")
        extraction_class = str(label.get("extraction_class", ""))
        if not address or extraction_class not in SCRIPT_CLASSES:
            continue
        merge_entry(
            entries,
            {
                "address": str(address),
                "name": label.get("name"),
                "path": None,
                "size": None,
                "primary_class": extraction_class,
                "extraction_classes": [extraction_class],
                "sources": [f"supplemental-{label.get('source', 'label')}"],
                "source_kind": None,
                "source_decode_status": label.get("script_decode_status"),
                "evidence": normalize_evidence(label.get("evidence", [])),
            },
        )

    return sorted(entries.values(), key=lambda item: address_sort_key(str(item["address"])))


def decoded_instruction_count(lines: list[str]) -> int:
    return sum(1 for line in lines if line and not line.startswith(";"))


def decode_status(lines: list[str]) -> str:
    if not lines:
        return "not-decoded"
    joined = "\n".join(lines)
    if "unknown event opcode" in joined:
        return "partial-unknown-opcode"
    if "args unknown" in joined:
        return "partial-unknown-call-args"
    last = lines[-1]
    if last.startswith("; stopped at byte limit"):
        return "limit-byte"
    if last.startswith("; stopped at instruction limit"):
        return "limit-instruction"
    return "complete"


def stop_reason(lines: list[str]) -> str:
    if not lines:
        return "not-decoded"
    joined = "\n".join(lines)
    if "unknown event opcode" in joined:
        match = UNKNOWN_OPCODE_RE.search(joined)
        return f"unknown opcode at {match.group(1)}" if match else "unknown opcode"
    if "args unknown" in joined:
        for line in lines:
            if "args unknown" in line:
                return f"unknown call args in {line.split()[0]}"
        return "unknown call args"
    last = lines[-1]
    if last.startswith("; stopped at byte limit"):
        return "byte limit"
    if last.startswith("; stopped at instruction limit"):
        return "instruction limit"
    return "terminal/control-flow stop"


def extract_targets(lines: list[str]) -> tuple[list[str], list[str]]:
    callbacks: list[str] = []
    c3_targets: list[str] = []
    for line in lines:
        if "EVENT_CALLROUTINE" in line:
            match = CALLROUTINE_RE.search(line)
            if match and match.group(1) not in callbacks:
                callbacks.append(match.group(1))
        for target in TARGET_RE.findall(line):
            if target.startswith("C3:") and target not in c3_targets:
                c3_targets.append(target)
    return callbacks, c3_targets


def unknown_callback_target(lines: list[str]) -> str | None:
    for line in lines:
        match = UNKNOWN_CALL_TARGET_RE.search(line)
        if match:
            return match.group(1)
    return None


def inferred_callback_group(target: str, preferred_name: str | None) -> str:
    semantics = CALL_TARGET_SEMANTICS.get(target)
    if semantics:
        return semantics["group"]
    name = preferred_name or ""
    if target.startswith("EF:"):
        return "ef-helper"
    if "Text" in name or "Window" in name or "Presentation" in name:
        return "text-presentation"
    if "Visual" in name or "Animation" in name or "Frame" in name:
        return "visual-profile"
    if "Collision" in name or "Footprint" in name:
        return "collision"
    if "Direction" in name or "Vector" in name or "Movement" in name:
        return "movement"
    if "CurrentSlot" in name or "Slot" in name:
        return "current-slot-state"
    if target.startswith("C2:"):
        return "battle-runtime"
    if target.startswith("C4:"):
        return "presentation-render"
    if target.startswith("C0:"):
        return "overworld-runtime"
    return "other"


def inferred_callback_contract(target: str, arg_bytes: int | None) -> str:
    semantics = CALL_TARGET_SEMANTICS.get(target)
    if semantics:
        return semantics["contract"]
    if arg_bytes is None:
        return "argument byte count is not known"
    if arg_bytes == 0:
        return "no inline argument bytes"
    return f"{arg_bytes} inline argument byte(s); semantic fields not named yet"


def inferred_argument_schema(target: str, arg_bytes: int | None) -> str:
    semantics = CALL_TARGET_SEMANTICS.get(target)
    if semantics and semantics.get("args"):
        return semantics["args"]
    if arg_bytes is None:
        return "unknown"
    if arg_bytes == 0:
        return "-"
    return ", ".join(f"arg{i}_byte" for i in range(arg_bytes))


def audit_entry(
    entry: dict[str, Any],
    rom: bytes,
    names: dict[str, list[str]],
    *,
    max_instructions: int,
    max_bytes: int,
) -> dict[str, Any]:
    address = parse_address(str(entry["address"]))
    size = entry.get("size")
    decode_bytes = max_bytes
    if isinstance(size, int) and size > 0:
        decode_bytes = min(size, max_bytes)

    lines = decode_script(
        rom,
        address,
        max_instructions=max_instructions,
        max_bytes=decode_bytes,
        stop_at_terminal=True,
        names=names,
    )
    callbacks, c3_targets = extract_targets(lines)
    unknown_callback = unknown_callback_target(lines)
    return {
        **entry,
        "raw_preview": raw_preview(rom, address),
        "first_opcode": first_opcode(rom, address),
        "decode_status": decode_status(lines),
        "stop_reason": stop_reason(lines),
        "unknown_callback_target": unknown_callback,
        "decode_bounds": {
            "max_instructions": max_instructions,
            "max_bytes": decode_bytes,
        },
        "decoded_instruction_count": decoded_instruction_count(lines),
        "callback_targets": callbacks,
        "c3_targets": c3_targets,
        "decoded": lines,
    }


def build_audit(
    source_map_path: Path,
    index_path: Path,
    rom_path: str | None,
    *,
    max_instructions: int,
    max_bytes: int,
) -> dict[str, Any]:
    source_map = load_json(source_map_path)
    rom = load_rom(find_rom(rom_path))
    names = load_names(index_path)
    rows = [
        audit_entry(
            entry,
            rom,
            names,
            max_instructions=max_instructions,
            max_bytes=max_bytes,
        )
        for entry in load_script_entries(source_map)
    ]

    by_class = Counter(str(row["primary_class"]) for row in rows)
    by_status = Counter(str(row["decode_status"]) for row in rows)
    first_opcodes = Counter(
        f"{row['first_opcode']['byte']} {row['first_opcode']['name']}" for row in rows
    )
    callbacks = Counter(target for row in rows for target in row["callback_targets"])
    unknown_callbacks = Counter(
        str(row["unknown_callback_target"])
        for row in rows
        if row.get("unknown_callback_target")
    )
    c3_targets = Counter(target for row in rows for target in row["c3_targets"])
    callback_contracts = []
    for target, count in callbacks.most_common():
        preferred_name = names.get(target, [None])[0]
        arg_bytes = CALL_ARG_COUNTS.get(target)
        callback_contracts.append(
            {
                "target": target,
                "preferred_name": preferred_name,
                "calls": count,
                "arg_bytes": arg_bytes,
                "semantic_group": inferred_callback_group(target, preferred_name),
                "argument_contract": inferred_callback_contract(target, arg_bytes),
                "argument_schema": inferred_argument_schema(target, arg_bytes),
                "status": "byte-count-known" if target in CALL_ARG_COUNTS else "missing-byte-count",
            }
        )
    callback_groups = Counter(str(contract["semantic_group"]) for contract in callback_contracts)

    return {
        "schema": SCHEMA,
        "generated_by": "tools/build_c3_actionscript_semantics_audit.py",
        "inputs": {
            "source_map": rel(source_map_path),
            "ref_index": rel(index_path),
        },
        "decode_bounds": {
            "max_instructions": max_instructions,
            "max_bytes": max_bytes,
        },
        "summary": {
            "rows": len(rows),
            "by_extraction_class": dict(sorted(by_class.items())),
            "by_decode_status": dict(sorted(by_status.items())),
            "top_first_opcodes": dict(first_opcodes.most_common(12)),
            "top_callback_targets": dict(callbacks.most_common(16)),
            "unknown_callback_targets": dict(unknown_callbacks.most_common()),
            "top_c3_targets": dict(c3_targets.most_common(16)),
            "callback_contracts": len(callback_contracts),
            "callback_groups": dict(callback_groups.most_common()),
        },
        "callback_contracts": callback_contracts,
        "rows": rows,
    }


def markdown_escape(text: Any) -> str:
    return str(text if text is not None else "").replace("|", "\\|")


def format_list(values: list[str], limit: int = 4) -> str:
    if not values:
        return "-"
    visible = values[:limit]
    suffix = f", +{len(values) - limit}" if len(values) > limit else ""
    return ", ".join(f"`{value}`" for value in visible) + suffix


def render_markdown(audit: dict[str, Any]) -> str:
    summary = audit["summary"]
    rows = audit["rows"]
    frontier_rows = [row for row in rows if row["decode_status"] != "complete"]

    lines = [
        "# C3 actionscript semantics audit",
        "",
        "Generated from `notes/c3-source-data-map.md` via `tools/build_c3_actionscript_semantics_audit.py`. This report is the first semantic frontier for C3 event/actionscript payloads after byte-equivalent source-bank closure.",
        "",
        "## Summary",
        "",
        f"- schema: `{audit['schema']}`",
        f"- script rows audited: `{summary['rows']}`",
        f"- by extraction class: `{summary['by_extraction_class']}`",
        f"- by decode status: `{summary['by_decode_status']}`",
        f"- native callback contract seeds: `{summary['callback_contracts']}`",
        f"- decode bounds: `{audit['decode_bounds']['max_instructions']}` instructions, `{audit['decode_bounds']['max_bytes']:#x}` bytes per row unless the source-map row is shorter",
        "",
        "## Top opcode and target signals",
        "",
        f"- top first opcodes: `{summary['top_first_opcodes']}`",
        f"- top native callback targets: `{summary['top_callback_targets']}`",
        f"- callback semantic groups: `{summary['callback_groups']}`",
        f"- unknown callback targets: `{summary['unknown_callback_targets']}`",
        f"- top C3 script targets: `{summary['top_c3_targets']}`",
        "",
        "## Frontier rows",
        "",
    ]

    if frontier_rows:
        lines.extend(
            [
                "| Address | Name | Class | Decode | Stop reason | Unknown callback | First opcode |",
                "| --- | --- | --- | --- | --- | --- | --- |",
            ]
        )
        for row in frontier_rows:
            first = row["first_opcode"]
            lines.append(
                "| `{address}` | `{name}` | `{kind}` | `{decode}` | {reason} | {unknown} | `{opcode}` |".format(
                    address=row["address"],
                    name=markdown_escape(row.get("name") or ""),
                    kind=row["primary_class"],
                    decode=row["decode_status"],
                    reason=markdown_escape(row["stop_reason"]),
                    unknown=f"`{row['unknown_callback_target']}`" if row.get("unknown_callback_target") else "-",
                    opcode=f"{first['byte']} {first['name']}",
                )
            )
    else:
        lines.append("No syntactic decode frontiers at the current bounds.")

    lines.extend(
        [
            "",
            "## Native callback contract seed",
            "",
            "| Target | Preferred name | Group | Calls | Arg bytes | Args | Contract | Status |",
            "| --- | --- | --- | ---: | ---: | --- | --- | --- |",
        ]
    )
    for contract in audit["callback_contracts"]:
        arg_bytes = contract["arg_bytes"]
        lines.append(
            "| `{target}` | `{name}` | `{group}` | {calls} | {arg_bytes} | `{argument_schema}` | {argument_contract} | `{status}` |".format(
                target=contract["target"],
                name=markdown_escape(contract.get("preferred_name") or ""),
                group=contract["semantic_group"],
                calls=contract["calls"],
                arg_bytes="-" if arg_bytes is None else arg_bytes,
                argument_schema=markdown_escape(contract["argument_schema"]),
                argument_contract=markdown_escape(contract["argument_contract"]),
                status=contract["status"],
            )
        )

    lines.extend(
        [
            "",
            "## Full script inventory",
            "",
            "| Address | Name | Class | Decode | Instr. | First opcode | Callbacks | C3 targets |",
            "| --- | --- | --- | --- | ---: | --- | --- | --- |",
        ]
    )
    for row in rows:
        first = row["first_opcode"]
        lines.append(
            "| `{address}` | `{name}` | `{kind}` | `{decode}` | {count} | `{opcode}` | {callbacks} | {targets} |".format(
                address=row["address"],
                name=markdown_escape(row.get("name") or ""),
                kind=row["primary_class"],
                decode=row["decode_status"],
                count=row["decoded_instruction_count"],
                opcode=f"{first['byte']} {first['name']}",
                callbacks=format_list(row["callback_targets"]),
                targets=format_list(row["c3_targets"]),
            )
        )

    lines.extend(["", "## Decode excerpts", ""])
    for row in rows:
        if row["decode_status"] == "complete" and row["primary_class"] == "event-script-asset":
            continue
        lines.extend(
            [
                f"### {row['address']} {row.get('name') or ''}".rstrip(),
                "",
                f"- class: `{row['primary_class']}`",
                f"- decode status: `{row['decode_status']}`",
                f"- stop reason: {row['stop_reason']}",
                f"- raw preview: `{row['raw_preview']}`",
                "",
                "```text",
                *row["decoded"][:16],
            ]
        )
        if len(row["decoded"]) > 16:
            lines.append(f"; ... {len(row['decoded']) - 16} more decoded lines in JSON output")
        lines.extend(["```", ""])

    return "\n".join(lines).rstrip() + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build a C3 event/actionscript semantic frontier audit.")
    parser.add_argument("--source-map", type=Path, default=DEFAULT_SOURCE_MAP)
    parser.add_argument("--index", type=Path, default=DEFAULT_INDEX)
    parser.add_argument("--rom", help="path to EarthBound (USA).sfc")
    parser.add_argument("--max-instructions", type=int, default=120)
    parser.add_argument("--max-bytes", type=lambda text: int(text, 0), default=0x400)
    parser.add_argument("--json-out", type=Path, default=DEFAULT_JSON_OUT)
    parser.add_argument("--markdown-out", type=Path, default=DEFAULT_MARKDOWN_OUT)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    audit = build_audit(
        resolve_path(args.source_map),
        resolve_path(args.index),
        args.rom,
        max_instructions=args.max_instructions,
        max_bytes=args.max_bytes,
    )

    json_out = resolve_path(args.json_out)
    json_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")

    markdown_out = resolve_path(args.markdown_out)
    markdown_out.parent.mkdir(parents=True, exist_ok=True)
    markdown_out.write_text(render_markdown(audit), encoding="utf-8")

    summary = audit["summary"]
    print(
        f"Wrote {json_out} and {markdown_out} "
        f"({summary['rows']} rows, {summary['by_decode_status']})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
