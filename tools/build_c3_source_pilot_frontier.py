from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from build_c3_event_script_source_pilot import FAMILY_DEFAULTS, parse_address_key
from decode_event_script import CALL_ARG_COUNTS, OPCODES, TERMINAL_NAMES, Address, read_u16
from rom_tools import find_rom, hirom_to_file_offset, load_rom


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SOURCE_MAP = ROOT / "build" / "c3-source-data-map.json"
DEFAULT_REPORT = ROOT / "notes" / "c3-source-pilot-frontier.md"
DEFAULT_MANIFEST = ROOT / "build" / "c3-source-pilot-frontier.json"

SCRIPT_CLASSES = {
    "event-script-asset",
    "event-bytecode-asset",
    "event-bytecode-label",
}


@dataclass(frozen=True)
class Range:
    start: int
    end: int
    source: str


@dataclass(frozen=True)
class DecodeSummary:
    status: str
    start: str
    end: str
    bytes: int
    instruction_count: int
    terminal: bool
    reason: str
    c3_targets: tuple[str, ...]
    native_targets: tuple[str, ...]
    callroutine_targets: tuple[str, ...]


@dataclass(frozen=True)
class FrontierCandidate:
    rank: str
    suggested_action: str
    containing_row: str
    include_path: str
    gap: str
    gap_bytes: int
    suggested_span: str
    suggested_bytes: int
    first_decode_status: str
    full_decode_status: str
    blocker: str
    instruction_count: int
    native_targets: tuple[str, ...]
    c3_targets: tuple[str, ...]
    ref_hints: tuple[str, ...]


def address_long(key: str) -> int:
    address = parse_address_key(key)
    return address.long


def key_from_long(value: int) -> str:
    return f"{(value >> 16) & 0xFF:02X}:{value & 0xFFFF:04X}"


def add_to_address(address: Address, count: int) -> Address:
    return Address(address.bank, address.offset + count)


def range_text(start: int, end: int) -> str:
    return f"{key_from_long(start)}..{key_from_long(end)}"


def load_source_map(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def candidate_rows(source_map: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for row in source_map["include_rows"]:
        if row.get("address") and row.get("size") and row.get("extraction_class") in SCRIPT_CLASSES:
            rows.append(row)
    return rows


def pilot_ranges(source_map: dict[str, Any]) -> list[Range]:
    row_by_address = {row["address"]: row for row in source_map["include_rows"] if row.get("address")}
    ranges: list[Range] = []
    for family_id, family in FAMILY_DEFAULTS.items():
        for row_key in family["rows"]:
            row = row_by_address.get(row_key)
            if not row:
                continue
            start = address_long(row_key)
            ranges.append(Range(start, start + int(row["size"]), family_id))
        for start_key, end_key, _ in family["spans"]:
            ranges.append(Range(address_long(start_key), address_long(end_key), family_id))
    return merge_ranges(ranges)


def merge_ranges(ranges: list[Range]) -> list[Range]:
    if not ranges:
        return []
    ordered = sorted(ranges, key=lambda item: (item.start, item.end))
    merged: list[Range] = [ordered[0]]
    for item in ordered[1:]:
        prev = merged[-1]
        if item.start <= prev.end:
            source = prev.source if item.source in prev.source.split(",") else f"{prev.source},{item.source}"
            merged[-1] = Range(prev.start, max(prev.end, item.end), source)
        else:
            merged.append(item)
    return merged


def subtract_ranges(start: int, end: int, covered: list[Range]) -> list[tuple[int, int]]:
    gaps = [(start, end)]
    for item in covered:
        next_gaps: list[tuple[int, int]] = []
        for gap_start, gap_end in gaps:
            if item.end <= gap_start or item.start >= gap_end:
                next_gaps.append((gap_start, gap_end))
                continue
            if gap_start < item.start:
                next_gaps.append((gap_start, item.start))
            if item.end < gap_end:
                next_gaps.append((item.end, gap_end))
        gaps = next_gaps
    return [(gap_start, gap_end) for gap_start, gap_end in gaps if gap_start < gap_end]


def read_checked(rom: bytes, pos: int, count: int, end: int, address: Address) -> bytes | str:
    if pos + count > end:
        return f"instruction at {address.key} runs past decode limit"
    if pos + count > len(rom):
        return f"instruction at {address.key} runs past ROM"
    return rom[pos : pos + count]


def decode_range(
    rom: bytes,
    start: Address,
    end: Address,
    *,
    stop_at_terminal: bool,
) -> DecodeSummary:
    file_offset = hirom_to_file_offset(start.bank, start.offset, len(rom))
    if file_offset is None:
        return DecodeSummary("fail", start.key, start.key, 0, 0, False, "unmapped HiROM address", (), (), ())
    if start.bank != end.bank or end.offset <= start.offset:
        return DecodeSummary("fail", start.key, start.key, 0, 0, False, "invalid decode range", (), (), ())

    limit = file_offset + (end.offset - start.offset)
    pos = file_offset
    instruction_count = 0
    c3_targets: set[str] = set()
    native_targets: set[str] = set()
    callroutine_targets: set[str] = set()
    terminal = False

    while pos < limit:
        address = add_to_address(start, pos - file_offset)
        opcode_byte = rom[pos]
        pos += 1
        opcode = OPCODES.get(opcode_byte)
        if opcode is None:
            return DecodeSummary(
                "fail",
                start.key,
                address.key,
                pos - file_offset,
                instruction_count,
                False,
                f"unknown opcode ${opcode_byte:02X} at {address.key}",
                tuple(sorted(c3_targets)),
                tuple(sorted(native_targets)),
                tuple(sorted(callroutine_targets)),
            )

        for spec in opcode.args:
            if spec == "byte":
                raw = read_checked(rom, pos, 1, limit, address)
                if isinstance(raw, str):
                    return fail_summary(start, address, pos - file_offset, instruction_count, raw, c3_targets, native_targets, callroutine_targets)
                pos += 1
            elif spec == "word":
                raw = read_checked(rom, pos, 2, limit, address)
                if isinstance(raw, str):
                    return fail_summary(start, address, pos - file_offset, instruction_count, raw, c3_targets, native_targets, callroutine_targets)
                pos += 2
            elif spec == "shortptr":
                raw = read_checked(rom, pos, 2, limit, address)
                if isinstance(raw, str):
                    return fail_summary(start, address, pos - file_offset, instruction_count, raw, c3_targets, native_targets, callroutine_targets)
                c3_targets.add(Address(start.bank, read_u16(raw, 0)).key)
                pos += 2
            elif spec == "callbackptr":
                raw = read_checked(rom, pos, 2, limit, address)
                if isinstance(raw, str):
                    return fail_summary(start, address, pos - file_offset, instruction_count, raw, c3_targets, native_targets, callroutine_targets)
                native_targets.add(Address(0xC0, read_u16(raw, 0)).key)
                pos += 2
            elif spec == "ptr3":
                raw = read_checked(rom, pos, 3, limit, address)
                if isinstance(raw, str):
                    return fail_summary(start, address, pos - file_offset, instruction_count, raw, c3_targets, native_targets, callroutine_targets)
                target = Address(raw[2], read_u16(raw, 0))
                if target.bank == 0xC3:
                    c3_targets.add(target.key)
                else:
                    native_targets.add(target.key)
                pos += 3
            elif spec == "wordlist":
                raw = read_checked(rom, pos, 1, limit, address)
                if isinstance(raw, str):
                    return fail_summary(start, address, pos - file_offset, instruction_count, raw, c3_targets, native_targets, callroutine_targets)
                count = raw[0]
                pos += 1
                for _ in range(count):
                    raw = read_checked(rom, pos, 2, limit, address)
                    if isinstance(raw, str):
                        return fail_summary(start, address, pos - file_offset, instruction_count, raw, c3_targets, native_targets, callroutine_targets)
                    c3_targets.add(Address(start.bank, read_u16(raw, 0)).key)
                    pos += 2
            elif spec == "callroutine":
                raw = read_checked(rom, pos, 3, limit, address)
                if isinstance(raw, str):
                    return fail_summary(start, address, pos - file_offset, instruction_count, raw, c3_targets, native_targets, callroutine_targets)
                target = Address(raw[2], read_u16(raw, 0))
                callroutine_targets.add(target.key)
                native_targets.add(target.key)
                pos += 3
                if target.key == "C0:9F82":
                    raw = read_checked(rom, pos, 1, limit, address)
                    if isinstance(raw, str):
                        return fail_summary(start, address, pos - file_offset, instruction_count, raw, c3_targets, native_targets, callroutine_targets)
                    count = raw[0]
                    pos += 1
                    for _ in range(count):
                        raw = read_checked(rom, pos, 2, limit, address)
                        if isinstance(raw, str):
                            return fail_summary(start, address, pos - file_offset, instruction_count, raw, c3_targets, native_targets, callroutine_targets)
                        pos += 2
                    continue
                count = CALL_ARG_COUNTS.get(target.key)
                if count is None:
                    return fail_summary(
                        start,
                        address,
                        pos - file_offset,
                        instruction_count,
                        f"unknown EVENT_CALLROUTINE arg count for {target.key} at {address.key}",
                        c3_targets,
                        native_targets,
                        callroutine_targets,
                    )
                raw = read_checked(rom, pos, count, limit, address)
                if isinstance(raw, str):
                    return fail_summary(start, address, pos - file_offset, instruction_count, raw, c3_targets, native_targets, callroutine_targets)
                pos += count
            else:
                return fail_summary(
                    start,
                    address,
                    pos - file_offset,
                    instruction_count,
                    f"unhandled operand spec {spec!r}",
                    c3_targets,
                    native_targets,
                    callroutine_targets,
                )

        instruction_count += 1
        terminal = opcode.terminal or opcode.name in TERMINAL_NAMES
        if stop_at_terminal and terminal:
            break

    actual_end = add_to_address(start, pos - file_offset)
    reason = "terminal" if terminal else "range-end"
    return DecodeSummary(
        "complete",
        start.key,
        actual_end.key,
        pos - file_offset,
        instruction_count,
        terminal,
        reason,
        tuple(sorted(c3_targets)),
        tuple(sorted(native_targets)),
        tuple(sorted(callroutine_targets)),
    )


def fail_summary(
    start: Address,
    address: Address,
    byte_count: int,
    instruction_count: int,
    reason: str,
    c3_targets: set[str],
    native_targets: set[str],
    callroutine_targets: set[str],
) -> DecodeSummary:
    return DecodeSummary(
        "fail",
        start.key,
        address.key,
        byte_count,
        instruction_count,
        False,
        reason,
        tuple(sorted(c3_targets)),
        tuple(sorted(native_targets)),
        tuple(sorted(callroutine_targets)),
    )


def terminal_batch(rom: bytes, start: Address, end: Address, *, max_bytes: int, max_segments: int) -> DecodeSummary:
    current = start
    total_bytes = 0
    total_instructions = 0
    c3_targets: set[str] = set()
    native_targets: set[str] = set()
    callroutine_targets: set[str] = set()
    last_reason = "no segments decoded"

    for _ in range(max_segments):
        if current.offset >= end.offset or total_bytes >= max_bytes:
            break
        summary = decode_range(rom, current, end, stop_at_terminal=True)
        if summary.status != "complete":
            if total_bytes == 0:
                return summary
            last_reason = f"partial; next blocker: {summary.reason}"
            break
        total_bytes += summary.bytes
        total_instructions += summary.instruction_count
        c3_targets.update(summary.c3_targets)
        native_targets.update(summary.native_targets)
        callroutine_targets.update(summary.callroutine_targets)
        current = parse_address_key(summary.end)
        last_reason = "terminal batch"
        if current.offset >= end.offset or total_bytes >= max_bytes:
            break

    status = "complete" if total_bytes else "fail"
    return DecodeSummary(
        status,
        start.key,
        current.key,
        total_bytes,
        total_instructions,
        True,
        last_reason,
        tuple(sorted(c3_targets)),
        tuple(sorted(native_targets)),
        tuple(sorted(callroutine_targets)),
    )


def ref_hints_for_row(source_map: dict[str, Any], containing_row: dict[str, Any], limit: int = 8) -> tuple[str, ...]:
    rows = source_map["include_rows"]
    ordinal = int(containing_row["ordinal"])
    hints: list[str] = []
    for row in rows:
        row_ordinal = int(row["ordinal"])
        if row_ordinal <= ordinal:
            continue
        if row.get("address"):
            break
        path = str(row.get("path") or "")
        if path:
            hints.append(path)
        if len(hints) >= limit:
            break
    return tuple(hints)


def rank_candidate(gap_bytes: int, full: DecodeSummary, batch: DecodeSummary) -> tuple[str, str, DecodeSummary, str]:
    if full.status == "complete" and gap_bytes <= 0x400:
        return ("A", "promote full gap", full, "")
    if batch.status == "complete" and batch.bytes and batch.bytes <= 0x300:
        blocker = "" if "next blocker:" not in batch.reason else batch.reason
        return ("A-", "promote terminal batch", batch, blocker)
    if full.status == "complete" and gap_bytes <= 0x1000:
        return ("B", "promote full gap after review", full, "")
    if batch.status == "complete" and batch.bytes:
        return ("B-", "split first terminal batch", batch, batch.reason)
    if "unknown EVENT_CALLROUTINE arg count" in full.reason or "unknown EVENT_CALLROUTINE arg count" in batch.reason:
        return ("C", "name callback contract first", batch, batch.reason)
    return ("C-", "inspect manually", batch, batch.reason)


def build_candidates(
    rom: bytes,
    source_map: dict[str, Any],
    covered: list[Range],
    *,
    max_batch_bytes: int,
    max_batch_segments: int,
) -> list[FrontierCandidate]:
    output: list[FrontierCandidate] = []
    for row in candidate_rows(source_map):
        row_start = address_long(row["address"])
        row_end = row_start + int(row["size"])
        for gap_start, gap_end in subtract_ranges(row_start, row_end, covered):
            start = parse_address_key(key_from_long(gap_start))
            end = parse_address_key(key_from_long(gap_end))
            full = decode_range(rom, start, end, stop_at_terminal=False)
            batch = terminal_batch(
                rom,
                start,
                end,
                max_bytes=max_batch_bytes,
                max_segments=max_batch_segments,
            )
            rank, action, selected, blocker = rank_candidate(gap_end - gap_start, full, batch)
            if not blocker:
                blocker = full.reason if full.status != "complete" else ""
            output.append(
                FrontierCandidate(
                    rank=rank,
                    suggested_action=action,
                    containing_row=str(row["address"]),
                    include_path=str(row.get("path") or ""),
                    gap=range_text(gap_start, gap_end),
                    gap_bytes=gap_end - gap_start,
                    suggested_span=f"{selected.start}..{selected.end}",
                    suggested_bytes=selected.bytes,
                    first_decode_status=f"{batch.status}: {batch.reason}",
                    full_decode_status=f"{full.status}: {full.reason}",
                    blocker=blocker,
                    instruction_count=selected.instruction_count,
                    native_targets=selected.native_targets,
                    c3_targets=selected.c3_targets,
                    ref_hints=ref_hints_for_row(source_map, row),
                )
            )
    rank_order = {"A": 0, "A-": 1, "B": 2, "B-": 3, "C": 4, "C-": 5}
    return sorted(output, key=lambda item: (rank_order.get(item.rank, 9), -(item.suggested_bytes or 0), item.gap))


def render_report(
    source_map: dict[str, Any],
    covered: list[Range],
    candidates: list[FrontierCandidate],
) -> str:
    script_rows = candidate_rows(source_map)
    script_bytes = sum(int(row["size"]) for row in script_rows)
    covered_bytes = 0
    for row in script_rows:
        row_start = address_long(row["address"])
        row_end = row_start + int(row["size"])
        for item in covered:
            covered_bytes += max(0, min(row_end, item.end) - max(row_start, item.start))
    remaining_bytes = script_bytes - covered_bytes
    ready = [item for item in candidates if item.rank in {"A", "A-"}]

    lines = [
        "# C3 source-pilot frontier",
        "",
        "Generated by `tools/build_c3_source_pilot_frontier.py` from the C3 source/data map, current source-pilot families, and the local ROM.",
        "",
        "## Summary",
        "",
        f"- Event/actionscript candidate rows: `{len(script_rows)}`.",
        f"- Event/actionscript candidate bytes: `{script_bytes}`.",
        f"- Bytes already covered by source-form pilots: `{covered_bytes}`.",
        f"- Remaining candidate bytes: `{remaining_bytes}`.",
        f"- Frontier gaps: `{len(candidates)}`.",
        f"- Ready-ranked gaps: `{len(ready)}`.",
        "",
        "Rank meanings: `A` is ready as a full gap, `A-` is ready as a terminal-script batch, `B` needs review because it is larger, and `C` is blocked by missing callback/macro semantics or manual inspection.",
        "",
        "## Best Next Candidates",
        "",
        "| Rank | Suggested Span | Bytes | Action | Full Decode | Blocker | Ref Hints |",
        "| --- | --- | ---: | --- | --- | --- | --- |",
    ]
    for item in candidates[:15]:
        hints = ", ".join(item.ref_hints[:3])
        blocker = item.blocker.replace("|", "\\|") if item.blocker else ""
        lines.append(
            f"| `{item.rank}` | `{item.suggested_span}` | {item.suggested_bytes} | {item.suggested_action} | {item.full_decode_status} | {blocker} | {hints} |"
        )

    lines.extend(
        [
            "",
            "## Remaining Gaps",
            "",
            "| Gap | Bytes | Row | Rank | First Terminal Decode | Native Targets | C3 Targets |",
            "| --- | ---: | --- | --- | --- | --- | --- |",
        ]
    )
    for item in sorted(candidates, key=lambda value: value.gap):
        native = ", ".join(item.native_targets[:6])
        if len(item.native_targets) > 6:
            native += ", ..."
        c3 = ", ".join(item.c3_targets[:6])
        if len(item.c3_targets) > 6:
            c3 += ", ..."
        lines.append(
            f"| `{item.gap}` | {item.gap_bytes} | `{item.containing_row}` | `{item.rank}` | {item.first_decode_status} | {native} | {c3} |"
        )

    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- Ref hints are nearby ebsrc includes after the containing addressed include row; they are accelerators, not proof of final boundaries.",
            "- The report intentionally ranks small terminal-script batches highly because they are cheap to validate and accumulate reliable macro coverage.",
            "- Large `B` gaps are usually better split around internal event IDs or callback families before source promotion.",
        ]
    )
    return "\n".join(lines) + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Rank remaining C3 event/actionscript spans for source-pilot promotion.")
    parser.add_argument("--rom", help="path to EarthBound (USA).sfc")
    parser.add_argument("--source-map", type=Path, default=DEFAULT_SOURCE_MAP)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--max-batch-bytes", type=lambda text: int(text, 0), default=0x300)
    parser.add_argument("--max-batch-segments", type=int, default=8)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    source_map_path = args.source_map if args.source_map.is_absolute() else ROOT / args.source_map
    report_path = args.report if args.report.is_absolute() else ROOT / args.report
    manifest_path = args.manifest if args.manifest.is_absolute() else ROOT / args.manifest

    rom = load_rom(find_rom(args.rom))
    source_map = load_source_map(source_map_path)
    covered = pilot_ranges(source_map)
    candidates = build_candidates(
        rom,
        source_map,
        covered,
        max_batch_bytes=args.max_batch_bytes,
        max_batch_segments=args.max_batch_segments,
    )

    report_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(render_report(source_map, covered, candidates), encoding="utf-8")
    manifest = {
        "schema": "earthbound-decomp.c3-source-pilot-frontier.v1",
        "generated_by": "tools/build_c3_source_pilot_frontier.py",
        "report": report_path.relative_to(ROOT).as_posix(),
        "source_map": source_map_path.relative_to(ROOT).as_posix(),
        "covered_ranges": [asdict(item) for item in covered],
        "candidates": [asdict(item) for item in candidates],
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    ready = sum(1 for item in candidates if item.rank in {"A", "A-"})
    print(f"wrote {report_path.relative_to(ROOT).as_posix()}")
    print(f"wrote {manifest_path.relative_to(ROOT).as_posix()}")
    print(f"frontier_gaps={len(candidates)} ready={ready}")
    if candidates:
        first = candidates[0]
        print(f"best={first.rank} {first.suggested_span} {first.suggested_action}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
