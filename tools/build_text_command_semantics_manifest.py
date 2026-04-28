#!/usr/bin/env python3
"""Build a semantic manifest for the EarthBound text-command VM.

This joins four evidence layers without copying dialogue text into tracked
artifacts:

- decoded ROM text-bank command usage
- live C1 top-level and family dispatch ladders
- checked-in research-note coverage
- recovered localization source command-name counts, when available
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import census_ebtext_commands as census
import disasm_ebtext_script as ebscript
import find_ebtext_command
import rom_tools
import summarize_dispatch


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_YML = ROOT / "refs" / "ebsrc-main" / "ebsrc-main" / "earthbound.yml"
DEFAULT_NOTES_DIR = ROOT / "notes"
DEFAULT_LOCALIZATION_METADATA = ROOT / "build" / "localization-script-metadata-records.json"
DEFAULT_LOCALIZATION_INDEX = ROOT / "build" / "localization-script-source-index.json"
DEFAULT_JSON = ROOT / "build" / "text-command-semantics-manifest.json"
DEFAULT_MARKDOWN = ROOT / "notes" / "text-command-semantics-manifest.md"
TOP_DISPATCH = "C1:890E"
FAMILY_DISPATCHERS = {
    0x18: "C1:790B",
    0x19: "C1:79AA",
    0x1A: "C1:7B56",
    0x1B: "C1:7C36",
    0x1C: "C1:7D94",
    0x1D: "C1:7F11",
    0x1E: "C1:811F",
    0x1F: "C1:81BB",
}

PARSED_ARTIFACT_CANDIDATES = {
    (0x18, 0xA3): "EDEBUG pointer/table run near C5:997C",
    (0x19, 0x4F): "ENEWS pointer/table run near C8:4A49",
    (0x1A, 0x48): "ENEWS pointer/table run near C8:4345",
    (0x1D, 0x1C): "EBATTLE8 compressed/overlap artifact near EF:79DF",
    (0x1D, 0x85): "EDEBUG pointer/table/compressed overlap near C5:849F",
    (0x1D, 0xC7): "EHINT pointer/table cluster near C7:00EF",
    (0x1E, 0xC7): "EHINT pointer/table cluster near C7:00F7",
    (0x1F, 0x4E): "ENEWS pointer/table run near C8:4A59",
    (0x1F, 0xC7): "EHINT pointer/table cluster near C7:00FF",
}

FRONTIER_STATUSES = {
    "runtime_only",
    "parsed_only",
    "parsed_artifact_candidate",
    "needs_name",
    "unknown_parsed",
    "needs_note",
}


AUTHORING_HINTS = {
    "@SETF": {"opcode": "0x04", "name": "SET_EVENT_FLAG", "confidence": "high"},
    "@CLRF": {"opcode": "0x05", "name": "CLEAR_EVENT_FLAG", "confidence": "high"},
    "@CHKFGOTO": {"opcode": "0x06", "name": "JUMP_IF_FLAG_SET", "confidence": "high"},
    "@GOSUB": {"opcode": "0x08", "name": "CALL_TEXT", "confidence": "high"},
    "@CLOSEALL": {"opcode": "0x18", "subopcode": "0x04", "name": "CLOSE_ALL_WINDOWS", "confidence": "high"},
    "@OPEN": {"opcode": "0x18", "subopcode": "0x01", "name": "OPEN_WINDOW", "confidence": "high"},
    "@SE": {"opcode": "0x1F", "subopcode": "0x02", "name": "PLAY_SOUND", "confidence": "high"},
    "@BGMSTART": {"opcode": "0x1F", "subopcode": "0x00", "name": "PLAY_MUSIC", "confidence": "high"},
    "@FONTSTD": {"opcode": "0x1F", "subopcode": "0x30", "name": "USE_NORMAL_FONT", "confidence": "high"},
    "@FONTBAKA": {"opcode": "0x1F", "subopcode": "0x31", "name": "USE_MR_SATURN_FONT", "confidence": "high"},
    "@WAITSYS": {"opcode": "0x1F", "subopcode": "0x60", "name": "WAIT_FOR_TEXT_PROMPT_OR_INPUT_GATE", "confidence": "high"},
    "@WARP": {"opcode": "0x1F", "subopcode": "0x21", "name": "TELEPORT_TO", "confidence": "high"},
    "@XCHG": {"opcode": "0x1B", "subopcode": "0x04", "name": "SWAP_WORKING_AND_ARG_MEMORY", "confidence": "medium"},
    "@DSP_STS": {"opcode": "0x1C", "subopcode": "0x01", "name": "PRINT_STAT", "confidence": "medium"},
    "@DSP_NAME": {"opcode": "0x1C", "subopcode": "0x02", "name": "PRINT_CHAR_NAME", "confidence": "medium"},
    "@DSP_GOODS": {"opcode": "0x1C", "subopcode": "0x05", "name": "PRINT_ITEM_NAME", "confidence": "medium"},
    "@KEY": {"opcode": "0x03", "name": "HALT_WITH_PROMPT", "confidence": "medium"},
    "@KEYNP": {"opcode": "0x13", "name": "HALT_WITHOUT_PROMPT", "confidence": "medium"},
}


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def fmt_cpu(bank: int, addr: int | None) -> str | None:
    if addr is None:
        return None
    return f"{bank:02X}:{addr:04X}"


def command_status(
    *,
    has_runtime: bool,
    parsed_hits: int,
    has_name: bool,
    has_note: bool,
    artifact_reason: str | None = None,
) -> str:
    if artifact_reason and not has_runtime and parsed_hits:
        return "parsed_artifact_candidate"
    if has_runtime and parsed_hits and has_name and has_note:
        return "covered"
    if has_runtime and parsed_hits and has_name:
        return "needs_note"
    if has_runtime and not parsed_hits and has_name:
        return "runtime_only"
    if not has_runtime and parsed_hits and has_name:
        return "parsed_only"
    if has_runtime and not has_name:
        return "needs_name"
    if parsed_hits and not has_name:
        return "unknown_parsed"
    return "empty"


def parse_text_usage(rom: bytes, yml_path: Path) -> dict[str, Any]:
    segments = find_ebtext_command.load_segments(yml_path)
    top_counts: Counter[int] = Counter()
    sub_counts: Counter[tuple[int, int]] = Counter()
    top_segments: dict[int, Counter[str]] = defaultdict(Counter)
    sub_segments: dict[tuple[int, int], Counter[str]] = defaultdict(Counter)
    unknown_samples: list[dict[str, str]] = []
    truncated_commands = 0
    decoded_segments = 0

    for segment_name, file_offset, size in segments:
        data = rom[file_offset:file_offset + size]
        if not data:
            continue
        decoded_segments += 1
        start_address = find_ebtext_command.file_offset_to_canonical_hirom(file_offset)
        i = 0
        while i < len(data):
            if data[i] >= 0x20:
                _, run_size = ebscript.decode_text_run(data, i)
                i += max(run_size, 1)
                continue

            op = data[i]
            top_counts[op] += 1
            top_segments[op][segment_name] += 1
            subop: int | None = None
            if op in ebscript.SUBCOMMAND_NAMES and i + 1 < len(data):
                subop = data[i + 1]
                sub_counts[(op, subop)] += 1
                sub_segments[(op, subop)][segment_name] += 1
                if subop not in ebscript.SUBCOMMAND_NAMES[op] and len(unknown_samples) < 32:
                    address = start_address + i
                    unknown_samples.append(
                        {
                            "cpu": f"{address >> 16:02X}:{address & 0xFFFF:04X}",
                            "segment": segment_name,
                            "opcode": f"0x{op:02X}",
                            "subopcode": f"0x{subop:02X}",
                            "name": find_ebtext_command.command_name_for(op, subop),
                        }
                    )
            elif op not in ebscript.TOP_LEVEL_NAMES and len(unknown_samples) < 32:
                address = start_address + i
                unknown_samples.append(
                    {
                        "cpu": f"{address >> 16:02X}:{address & 0xFFFF:04X}",
                        "segment": segment_name,
                        "opcode": f"0x{op:02X}",
                        "name": find_ebtext_command.command_name_for(op, None),
                    }
                )

            try:
                _, command_size = ebscript.parse_command(data, i)
            except IndexError:
                truncated_commands += 1
                break
            i += max(command_size, 1)

    return {
        "segment_count": decoded_segments,
        "top_counts": top_counts,
        "sub_counts": sub_counts,
        "top_segments": top_segments,
        "sub_segments": sub_segments,
        "unknown_samples": unknown_samples,
        "truncated_commands": truncated_commands,
    }


def top_segment_summary(counter: Counter[str], limit: int = 5) -> list[dict[str, Any]]:
    return [{"segment": name, "count": count} for name, count in counter.most_common(limit)]


def load_record_metadata(path: Path) -> tuple[Counter[str], int]:
    if not path.exists():
        return Counter(), 0
    manifest = json.loads(path.read_text(encoding="utf-8-sig"))
    counts: Counter[str] = Counter()
    for record in manifest.get("records", []):
        counts.update(record.get("command_counts", {}))
    return counts, int(manifest.get("record_count", 0))


def load_authoring_counts(index_path: Path, metadata_path: Path) -> tuple[Counter[str], int, str]:
    if index_path.exists():
        manifest = json.loads(index_path.read_text(encoding="utf-8-sig"))
        records = sum(int(row.get("metadata_records", 0)) for row in manifest.get("files", []))
        return Counter(dict(manifest.get("top_commands", []))), records, str(index_path)
    counts, records = load_record_metadata(metadata_path)
    return counts, records, str(metadata_path)


def dispatch_case_map(rom: bytes, address: str, max_cases: int) -> tuple[dict[int, summarize_dispatch.CaseEntry], dict[str, Any]]:
    bank, addr = summarize_dispatch.parse_cpu_address(address)
    cases, guard, default_target, default_kind, default_value = summarize_dispatch.summarize_dispatch(
        rom, bank, addr, max_cases
    )
    payload: dict[str, Any] = {
        "address": address,
        "case_count": len(cases),
        "default_target": fmt_cpu(bank, default_target),
        "default_kind": default_kind,
        "default_value": f"0x{default_value:04X}" if default_value is not None else None,
    }
    if guard is not None:
        payload["guard"] = {
            "compare": f"0x{guard.value:04X}",
            "branch_op": guard.op,
            "branch_target": fmt_cpu(bank, guard.branch_target),
            "default_target": fmt_cpu(bank, guard.default_target),
        }
    return {entry.value: entry for entry in cases}, payload


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    rom_path = rom_tools.find_rom(args.rom)
    rom = rom_tools.load_rom(rom_path)
    yml_path = Path(args.yml)
    notes_dir = Path(args.notes_dir)
    usage = parse_text_usage(rom, yml_path)
    authoring_counts, authoring_records, authoring_source = load_authoring_counts(
        Path(args.localization_index),
        Path(args.localization_metadata),
    )

    top_runtime, top_dispatch = dispatch_case_map(rom, TOP_DISPATCH, 0x20)
    dispatcher_bank, _ = summarize_dispatch.parse_cpu_address(TOP_DISPATCH)
    top_level: list[dict[str, Any]] = []
    for opcode in range(0x20):
        name = find_ebtext_command.command_name_for(opcode, None)
        notes = census.iter_note_matches(notes_dir, opcode)
        runtime = top_runtime.get(opcode)
        parsed_hits = usage["top_counts"].get(opcode, 0)
        has_name = not name.startswith("UNKNOWN_")
        row = {
            "opcode": f"0x{opcode:02X}",
            "name": name,
            "status": command_status(
                has_runtime=runtime is not None,
                parsed_hits=parsed_hits,
                has_name=has_name,
                has_note=bool(notes),
            ),
            "parsed_hits": parsed_hits,
            "runtime_target": fmt_cpu(dispatcher_bank, runtime.target) if runtime is not None else None,
            "runtime_kind": runtime.target_kind if runtime is not None else None,
            "runtime_value": f"0x{runtime.target_value:04X}" if runtime and runtime.target_value is not None else None,
            "notes": [rel(note) for note in notes],
            "top_segments": top_segment_summary(usage["top_segments"].get(opcode, Counter())),
        }
        top_level.append(row)

    families: list[dict[str, Any]] = []
    for opcode, address in FAMILY_DISPATCHERS.items():
        family_runtime, dispatch = dispatch_case_map(rom, address, 0x100)
        named_subcommands = ebscript.SUBCOMMAND_NAMES.get(opcode, {})
        observed_subops = {sub for (op, sub), count in usage["sub_counts"].items() if op == opcode and count}
        all_subops = sorted(set(named_subcommands) | set(family_runtime) | observed_subops)
        subcommands: list[dict[str, Any]] = []
        for subop in all_subops:
            name = find_ebtext_command.command_name_for(opcode, subop)
            runtime = family_runtime.get(subop)
            parsed_hits = usage["sub_counts"].get((opcode, subop), 0)
            has_name = not name.startswith("UNKNOWN_")
            artifact_reason = PARSED_ARTIFACT_CANDIDATES.get((opcode, subop))
            subcommands.append(
                {
                    "subopcode": f"0x{subop:02X}",
                    "name": name,
                    "status": command_status(
                        has_runtime=runtime is not None,
                        parsed_hits=parsed_hits,
                        has_name=has_name,
                        has_note=True,
                        artifact_reason=artifact_reason,
                    ),
                    "parsed_hits": parsed_hits,
                    "runtime_target": fmt_cpu(dispatcher_bank, runtime.target) if runtime is not None else None,
                    "runtime_kind": runtime.target_kind if runtime is not None else None,
                    "runtime_value": f"0x{runtime.target_value:04X}" if runtime and runtime.target_value is not None else None,
                    "artifact_reason": artifact_reason,
                    "top_segments": top_segment_summary(usage["sub_segments"].get((opcode, subop), Counter()), 3),
                }
            )
        status_counts = Counter(row["status"] for row in subcommands)
        families.append(
            {
                "opcode": f"0x{opcode:02X}",
                "name": find_ebtext_command.command_name_for(opcode, None),
                "dispatcher": dispatch,
                "subcommand_count": len(subcommands),
                "status_counts": dict(sorted(status_counts.items())),
                "subcommands": subcommands,
            }
        )

    hinted_authoring = []
    for command, count in authoring_counts.most_common(80):
        hint = AUTHORING_HINTS.get(command)
        hinted_authoring.append(
            {
                "command": command,
                "count": count,
                "runtime_hint": hint,
            }
        )

    return {
        "generated_by": "tools/build_text_command_semantics_manifest.py",
        "rom": rel(rom_path),
        "yml": rel(yml_path),
        "notes_dir": rel(notes_dir),
        "source_metadata": rel(Path(args.localization_metadata)),
        "source_index": rel(Path(args.localization_index)),
        "authoring_count_source": rel(Path(authoring_source)),
        "summary": {
            "decoded_text_segments": usage["segment_count"],
            "top_level_commands": len(top_level),
            "covered_top_level": sum(1 for row in top_level if row["status"] == "covered"),
            "parsed_only_top_level": sum(1 for row in top_level if row["status"] == "parsed_only"),
            "families": len(families),
            "subcommands": sum(family["subcommand_count"] for family in families),
            "parsed_artifact_candidates": sum(
                family["status_counts"].get("parsed_artifact_candidate", 0) for family in families
            ),
            "unknown_decoded_samples": len(usage["unknown_samples"]),
            "truncated_commands": usage["truncated_commands"],
            "localization_records": authoring_records,
            "localization_top_commands_tracked": len(authoring_counts),
        },
        "top_dispatcher": top_dispatch,
        "top_level": top_level,
        "families": families,
        "authoring_command_hints": hinted_authoring,
        "unknown_samples": usage["unknown_samples"],
    }


def write_markdown(manifest: dict[str, Any], output_path: Path) -> None:
    summary = manifest["summary"]
    lines: list[str] = [
        "# Text Command Semantics Manifest",
        "",
        f"Generated by `tools/build_text_command_semantics_manifest.py`.",
        "",
        "## Summary",
        "",
        f"- Decoded text segments: `{summary['decoded_text_segments']}`",
        f"- Top-level commands: `{summary['top_level_commands']}`",
        f"- Covered top-level commands: `{summary['covered_top_level']}`",
        f"- Parser-only top-level pseudo-opcodes: `{summary['parsed_only_top_level']}`",
        f"- Structured families audited: `{summary['families']}`",
        f"- Family subcommands tracked: `{summary['subcommands']}`",
        f"- Parsed artifact candidates tracked: `{summary['parsed_artifact_candidates']}`",
        f"- Recovered localization records available: `{summary['localization_records']}`",
        f"- Recovered localization top commands tracked: `{summary['localization_top_commands_tracked']}`",
        "",
        "This manifest is the queryable bridge between the C1 text-command runtime,",
        "`C5..C9` text banks, checked-in text-command notes, and the recovered",
        "localization authoring source metadata. It intentionally records command",
        "names and counts only, not dialogue bodies.",
        "",
        "## Top-Level Commands",
        "",
        "| Opcode | Name | Status | Parsed hits | Runtime | Notes |",
        "| --- | --- | --- | ---: | --- | --- |",
    ]
    for row in manifest["top_level"]:
        runtime = row["runtime_target"] or "-"
        if row["runtime_kind"] == "callback":
            runtime = f"{runtime} callback={row['runtime_value']}"
        notes = ", ".join(Path(note).name for note in row["notes"][:3]) or "-"
        lines.append(
            f"| `{row['opcode']}` | `{row['name']}` | `{row['status']}` | "
            f"{row['parsed_hits']} | `{runtime}` | {notes} |"
        )

    lines.extend(
        [
            "",
            "## Structured Families",
            "",
            "| Family | Name | Dispatcher | Subcommands | Covered | Runtime only | Parsed only | Artifact candidates | Needs name |",
            "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for family in manifest["families"]:
        counts = family["status_counts"]
        lines.append(
            f"| `{family['opcode']}` | `{family['name']}` | "
            f"`{family['dispatcher']['address']}` | {family['subcommand_count']} | "
            f"{counts.get('covered', 0)} | {counts.get('runtime_only', 0)} | "
            f"{counts.get('parsed_only', 0)} | {counts.get('parsed_artifact_candidate', 0)} | "
            f"{counts.get('needs_name', 0) + counts.get('unknown_parsed', 0)} |"
        )

    lines.extend(
        [
            "",
            "## Family Frontiers",
            "",
            "Rows below are the cases most likely to deserve manual follow-up: runtime",
            "cases with no observed script hits, parser-observed cases outside the live",
            "dispatcher, or unknown names.",
            "",
        ]
    )
    for family in manifest["families"]:
        frontier = [
            row
            for row in family["subcommands"]
            if row["status"] in FRONTIER_STATUSES
        ]
        if not frontier:
            continue
        lines.append(f"### `{family['opcode']}` `{family['name']}`")
        lines.append("")
        lines.append("| Sub | Name | Status | Parsed hits | Runtime | Top segments | Evidence note |")
        lines.append("| --- | --- | --- | ---: | --- | --- | --- |")
        for row in frontier[:32]:
            runtime = row["runtime_target"] or "-"
            segments = ", ".join(f"{seg['segment']}:{seg['count']}" for seg in row["top_segments"]) or "-"
            evidence = row.get("artifact_reason") or "-"
            lines.append(
                f"| `{row['subopcode']}` | `{row['name']}` | `{row['status']}` | "
                f"{row['parsed_hits']} | `{runtime}` | {segments} | {evidence} |"
            )
        if len(frontier) > 32:
            lines.append(f"| ... | ... | ... | ... | ... | `{len(frontier) - 32}` more | ... |")
        lines.append("")

    lines.extend(
        [
            "## Recovered Authoring Syntax Signals",
            "",
            "These counts come from the ignored recovered localization `.MSG` source",
            "index. Runtime hints are conservative and should be treated as joins to",
            "check, not as a replacement for ROM-backed proof.",
            "",
            "| Source command | Count | Runtime hint | Confidence |",
            "| --- | ---: | --- | --- |",
        ]
    )
    for row in manifest["authoring_command_hints"][:40]:
        hint = row["runtime_hint"]
        if hint:
            opcode = hint["opcode"]
            if "subopcode" in hint:
                opcode = f"{opcode} {hint['subopcode']}"
            name = f"`{opcode}` `{hint['name']}`"
            confidence = hint["confidence"]
        else:
            name = "-"
            confidence = "-"
        lines.append(f"| `{row['command']}` | {row['count']} | {name} | {confidence} |")

    lines.extend(
        [
            "",
            "## Next Manual Seams",
            "",
            "- Reconcile `parsed_only` family subcommands against compressed-bank pseudo-opcode artifacts before treating them as live leaves.",
            "- Promote high-confidence source authoring aliases into per-command syntax notes after local ROM call paths are checked.",
            "- Use this manifest as the stable input for future text reassembly and C-port text VM modeling.",
            "",
        ]
    )
    output_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rom", help="Optional explicit ROM path")
    parser.add_argument("--yml", type=Path, default=DEFAULT_YML)
    parser.add_argument("--notes-dir", type=Path, default=DEFAULT_NOTES_DIR)
    parser.add_argument("--localization-metadata", type=Path, default=DEFAULT_LOCALIZATION_METADATA)
    parser.add_argument("--localization-index", type=Path, default=DEFAULT_LOCALIZATION_INDEX)
    parser.add_argument("--json-out", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown-out", type=Path, default=DEFAULT_MARKDOWN)
    args = parser.parse_args()

    manifest = build_manifest(args)
    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.markdown_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    write_markdown(manifest, args.markdown_out)

    summary = manifest["summary"]
    print(f"wrote {args.json_out}")
    print(f"wrote {args.markdown_out}")
    print(
        "top_covered={covered_top_level}/{top_level_commands} "
        "families={families} subcommands={subcommands} authoring_top_commands={localization_top_commands_tracked}".format(
            **summary
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
