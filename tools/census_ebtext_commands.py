from __future__ import annotations

import argparse
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
import re
import sys
from typing import Iterable

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import find_ebtext_command as finder
import rom_tools
import summarize_dispatch


@dataclass
class CensusRow:
    opcode: int
    name: str
    runtime_target: int | None
    runtime_kind: str | None
    runtime_value: int | None
    parsed_hits: int
    segments: dict[str, int]
    notes: list[Path]


def fmt_cpu(bank: int, addr: int) -> str:
    return f"{bank:02X}:{addr:04X}"


NOTE_DIRECT_PATTERNS = (
    re.compile(r'^text-command-([0-9a-f]{2})-'),
    re.compile(r'^text-command-family-([0-9a-f]{2})-'),
)
NOTE_PAIR_PATTERN = re.compile(r'^text-commands-([0-9a-f]{2})-and-([0-9a-f]{2})-')
NOTE_RANGE_PATTERN = re.compile(r'^lower-bank01-text-control-strip-([0-9a-f]{2})-([0-9a-f]{2})$')
NOTE_FAMILY_NAME_PATTERN = re.compile(r'^text-command-family-([0-9a-f]{2})-(.+)$')
HEADER_OPCODE_RE = re.compile(r'Text Command(?: Family)? `0x([0-9A-Fa-f]{2})`')
HEADER_PAIR_RE = re.compile(r'Text Commands `0x([0-9A-Fa-f]{2})` and `0x([0-9A-Fa-f]{2})`')


def family_name_from_notes(opcode: int, notes: list[Path]) -> str | None:
    hex_byte = f'{opcode:02x}'
    for note in notes:
        m = NOTE_FAMILY_NAME_PATTERN.match(note.stem.lower())
        if not m or m.group(1) != hex_byte:
            continue
        slug = m.group(2)
        return slug.replace('-', '_').upper()
    return None


def iter_note_matches(notes_dir: Path, opcode: int) -> list[Path]:
    matches: list[Path] = []
    hex_byte = f'{opcode:02x}'
    for note in sorted(notes_dir.glob('*.md')):
        stem = note.stem.lower()
        matched = False
        for pattern in NOTE_DIRECT_PATTERNS:
            m = pattern.match(stem)
            if m and m.group(1) == hex_byte:
                matched = True
                break
        if not matched:
            m = NOTE_PAIR_PATTERN.match(stem)
            if m and hex_byte in {m.group(1), m.group(2)}:
                matched = True
        if not matched:
            m = NOTE_RANGE_PATTERN.match(stem)
            if m:
                lo = int(m.group(1), 16)
                hi = int(m.group(2), 16)
                if lo <= opcode <= hi:
                    matched = True
        if not matched:
            try:
                header = note.read_text(encoding='utf-8', errors='replace').splitlines()[:4]
            except OSError:
                header = []
            header_text = '\n'.join(header)
            for m in HEADER_OPCODE_RE.finditer(header_text):
                if int(m.group(1), 16) == opcode:
                    matched = True
                    break
            if not matched:
                for m in HEADER_PAIR_RE.finditer(header_text):
                    if opcode in {int(m.group(1), 16), int(m.group(2), 16)}:
                        matched = True
                        break
        if matched:
            matches.append(note)
    return matches


def load_rows(
    rom: bytes,
    segments: Iterable[tuple[str, int, int]],
    dispatcher: str,
    max_opcodes: int,
    notes_dir: Path,
) -> tuple[list[CensusRow], summarize_dispatch.GuardInfo | None, int | None, str | None, int | None]:
    bank, addr = summarize_dispatch.parse_cpu_address(dispatcher)
    cases, guard, default_target, default_kind, default_value = summarize_dispatch.summarize_dispatch(
        rom, bank, addr, max_opcodes
    )
    runtime_case_map = {entry.value: entry for entry in cases}

    rows: list[CensusRow] = []
    for opcode in range(max_opcodes):
        hits = finder.find_hits(rom, segments, opcode, None)
        by_segment: dict[str, int] = defaultdict(int)
        for seg_name, _, _ in hits:
            by_segment[seg_name] += 1
        runtime = runtime_case_map.get(opcode)
        notes = iter_note_matches(notes_dir, opcode)
        name = finder.command_name_for(opcode, None)
        if name.startswith('UNKNOWN_'):
            family_name = family_name_from_notes(opcode, notes)
            if family_name is not None:
                name = family_name
        rows.append(
            CensusRow(
                opcode=opcode,
                name=name,
                runtime_target=runtime.target if runtime is not None else None,
                runtime_kind=runtime.target_kind if runtime is not None else None,
                runtime_value=runtime.target_value if runtime is not None else None,
                parsed_hits=len(hits),
                segments=dict(sorted(by_segment.items(), key=lambda item: (-item[1], item[0]))),
                notes=notes,
            )
        )
    return rows, guard, default_target, default_kind, default_value


def row_status(row: CensusRow) -> str:
    has_runtime = row.runtime_target is not None
    has_parsed = row.parsed_hits > 0
    has_notes = bool(row.notes)
    if has_runtime and has_parsed and has_notes:
        return 'covered'
    if has_runtime and has_parsed:
        return 'needs_note'
    if has_runtime and has_notes:
        return 'runtime_only'
    if has_parsed and has_notes:
        return 'parsed_only'
    if has_runtime:
        return 'runtime_only'
    if has_parsed:
        return 'parsed_only'
    return 'empty'


def runtime_summary(row: CensusRow, dispatcher_bank: int) -> str:
    if row.runtime_target is None:
        return '-'
    text = fmt_cpu(dispatcher_bank, row.runtime_target)
    if row.runtime_kind == 'callback':
        text += f' callback=0x{row.runtime_value:04X}'
    elif row.runtime_kind == 'leaf':
        text += f' leaf=0x{row.runtime_value:04X}'
    return text


def write_markdown(
    rows: list[CensusRow],
    dispatcher: str,
    rom_path: Path,
    yml_path: Path,
    notes_dir: Path,
    out_path: Path,
    show_zero: bool,
) -> None:
    bank, _ = summarize_dispatch.parse_cpu_address(dispatcher)
    lines: list[str] = []
    lines.append('# EarthBound Text Command Census')
    lines.append('')
    lines.append(f'- ROM: `{rom_path}`')
    lines.append(f'- YML: `{yml_path}`')
    lines.append(f'- Dispatcher: `{dispatcher.upper()}`')
    lines.append(f'- Notes dir: `{notes_dir}`')
    lines.append('')
    lines.append('| Opcode | Name | Status | Runtime | Parsed hits | Top segments | Notes |')
    lines.append('| --- | --- | --- | --- | ---: | --- | --- |')
    for row in rows:
        if not show_zero and row.runtime_target is None and row.parsed_hits == 0:
            continue
        top_segments = ', '.join(f'{seg}:{count}' for seg, count in list(row.segments.items())[:3]) or '-'
        notes = ', '.join(note.name for note in row.notes) or '-'
        lines.append(
            f'| `0x{row.opcode:02X}` | `{row.name}` | `{row_status(row)}` | '
            f'`{runtime_summary(row, bank)}` | {row.parsed_hits} | {top_segments} | {notes} |'
        )
    out_path.write_text('\n'.join(lines) + '\n', encoding='utf-8')


def main() -> int:
    parser = argparse.ArgumentParser(
        description='Build a bank-01 text-command census that combines runtime dispatcher cases, parsed script hits, and note coverage.'
    )
    parser.add_argument('dispatcher', help='Live dispatcher CPU address like C1:890E')
    parser.add_argument('--rom', help='Optional explicit ROM path')
    parser.add_argument('--yml', default='refs/ebsrc-main/ebsrc-main/earthbound.yml', help='YAML file with text_data segment offsets')
    parser.add_argument('--notes-dir', default='notes', help='Directory containing research notes')
    parser.add_argument('--max-opcodes', type=int, default=0x20, help='Number of top-level opcode values to census')
    parser.add_argument('--limit', type=int, default=2, help='Maximum sample notes to list per opcode in plain-text output')
    parser.add_argument('--show-zero', action='store_true', help='Include opcodes with neither runtime cases nor parsed hits')
    parser.add_argument('--markdown-out', help='Optional path for a markdown report')
    args = parser.parse_args()

    rom_path = rom_tools.find_rom(args.rom)
    rom = rom_tools.load_rom(rom_path)
    yml_path = Path(args.yml)
    segments = finder.load_segments(yml_path)
    notes_dir = Path(args.notes_dir)
    rows, guard, default_target, default_kind, default_value = load_rows(
        rom, segments, args.dispatcher, args.max_opcodes, notes_dir
    )
    bank, _ = summarize_dispatch.parse_cpu_address(args.dispatcher)

    print(f'ROM: {rom_path}')
    print(f'YML: {yml_path}')
    print(f'Dispatcher: {args.dispatcher.upper()}')
    print(f'Notes dir: {notes_dir}')
    if guard is not None:
        print(
            f'Guard: cmp #0x{guard.value:04X} ; {guard.op} '
            f'{fmt_cpu(bank, guard.branch_target)} ; default {fmt_cpu(bank, guard.default_target)}'
        )
    if default_target is not None:
        line = f'Default: {fmt_cpu(bank, default_target)}'
        if default_kind == 'callback':
            line += f' callback=0x{default_value:04X}'
        elif default_kind == 'leaf':
            line += f' leaf=0x{default_value:04X}'
        print(line)
    print()

    header = f"{'Op':<4} {'Status':<11} {'Parsed':>6}  {'Runtime':<28} {'Notes':<5} Name"
    print(header)
    print('-' * len(header))
    for row in rows:
        if not args.show_zero and row.runtime_target is None and row.parsed_hits == 0:
            continue
        print(
            f"{row.opcode:02X}   {row_status(row):<11} {row.parsed_hits:>6}  "
            f"{runtime_summary(row, bank):<28} {len(row.notes):<5} {row.name}"
        )
        if row.segments:
            seg_text = ', '.join(f'{seg}:{count}' for seg, count in list(row.segments.items())[:4])
            print(f'     segments: {seg_text}')
        if row.notes:
            note_text = ', '.join(note.name for note in row.notes[:args.limit])
            if len(row.notes) > args.limit:
                note_text += f', ... +{len(row.notes) - args.limit} more'
            print(f'     notes: {note_text}')
        print()

    if args.markdown_out:
        out_path = Path(args.markdown_out)
        write_markdown(rows, args.dispatcher, Path(rom_path), yml_path, notes_dir, out_path, args.show_zero)
        print(f'Wrote markdown report: {out_path}')

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
