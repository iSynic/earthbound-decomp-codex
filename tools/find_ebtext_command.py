from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Iterable

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import disasm_ebtext_script as ebscript
import rom_tools


def load_segments(yml_path: Path) -> list[tuple[str, int, int]]:
    segments: list[tuple[str, int, int]] = []
    current_name: str | None = None
    current_offset: int | None = None
    current_size: int | None = None
    in_text_data = False

    for raw_line in yml_path.read_text(encoding='utf-8').splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()
        if stripped.startswith('- subdir:'):
            if in_text_data and current_name and current_offset is not None and current_size is not None:
                segments.append((current_name, current_offset, current_size))
            current_name = None
            current_offset = None
            current_size = None
            in_text_data = 'text_data' in stripped
            continue
        if not in_text_data:
            continue
        if stripped.startswith('name: '):
            current_name = stripped.split(':', 1)[1].strip().strip("'\"")
        elif stripped.startswith('offset: '):
            current_offset = int(stripped.split(':', 1)[1].strip(), 16)
        elif stripped.startswith('size: '):
            current_size = int(stripped.split(':', 1)[1].strip(), 0)

    if in_text_data and current_name and current_offset is not None and current_size is not None:
        segments.append((current_name, current_offset, current_size))
    return segments


def parse_hex_byte(text: str) -> int:
    text = text.strip().upper()
    if text.startswith('0X'):
        text = text[2:]
    return int(text, 16)


def command_name_for(op: int, sub: int | None) -> str:
    if sub is None:
        return ebscript.TOP_LEVEL_NAMES.get(op, f'UNKNOWN_{op:02X}')
    return ebscript.SUBCOMMAND_NAMES.get(op, {}).get(sub, f'UNKNOWN_{op:02X}_{sub:02X}')


def file_offset_to_canonical_hirom(file_offset: int) -> int:
    bank = rom_tools.canonical_bank_for_file_offset(file_offset)
    address = file_offset & 0xFFFF
    return (bank << 16) | address


def find_hits(rom: bytes, segments: Iterable[tuple[str, int, int]], op: int, sub: int | None) -> list[tuple[str, int, str]]:
    hits: list[tuple[str, int, str]] = []
    for seg_name, file_offset, size in segments:
        data = rom[file_offset:file_offset + size]
        start_address = file_offset_to_canonical_hirom(file_offset)
        for line in ebscript.decode_script(data, start_address):
            rel = line.address & 0xFFFF
            bank = (line.address >> 16) & 0xFF
            off = rom_tools.hirom_to_file_offset(bank, rel, len(rom))
            if off is None:
                continue
            idx = off - file_offset
            if idx < 0 or idx >= len(data):
                continue
            if data[idx] != op:
                continue
            if sub is not None:
                if idx + 1 >= len(data) or data[idx + 1] != sub:
                    continue
            hits.append((seg_name, line.address, line.text))
    return hits


def main() -> int:
    parser = argparse.ArgumentParser(description='Find exact parsed EarthBound text commands by opcode/subopcode.')
    parser.add_argument('opcode', help='Top-level command byte, for example 1C')
    parser.add_argument('subopcode', nargs='?', help='Optional subcommand byte, for example 05')
    parser.add_argument('--rom', help='Optional explicit ROM path')
    parser.add_argument('--yml', default='refs/ebsrc-main/ebsrc-main/earthbound.yml', help='YAML file with text_data segment offsets')
    parser.add_argument('--segment', action='append', help='Restrict to one or more text segment names, for example EDEBUG.')
    parser.add_argument('--limit', type=int, default=80, help='Maximum exact hits to print')
    args = parser.parse_args()

    rom_path = rom_tools.find_rom(args.rom)
    rom = rom_tools.load_rom(rom_path)
    yml_path = Path(args.yml)
    segments = load_segments(yml_path)
    if args.segment:
        wanted = {name.upper() for name in args.segment}
        segments = [entry for entry in segments if entry[0].upper() in wanted]
    op = parse_hex_byte(args.opcode)
    sub = parse_hex_byte(args.subopcode) if args.subopcode is not None else None
    hits = find_hits(rom, segments, op, sub)

    print(f'ROM: {rom_path}')
    print(f'YML: {yml_path}')
    print(f'Command: {command_name_for(op, sub)}')
    print(f'Opcode: 0x{op:02X}' + (f' subopcode: 0x{sub:02X}' if sub is not None else ''))
    print(f'Exact parsed hits: {len(hits)}')
    print()

    by_segment: dict[str, int] = {}
    for seg_name, _, _ in hits:
        by_segment[seg_name] = by_segment.get(seg_name, 0) + 1
    print('By segment:')
    for seg_name, count in sorted(by_segment.items(), key=lambda item: (-item[1], item[0])):
        print(f'  {seg_name}: {count}')

    if hits:
        print() 
        print('Exact hits:')
        for seg_name, address, text in hits[:args.limit]:
            print(f'  {ebscript.fmt_addr(address)}  {seg_name}  {text}')
        if len(hits) > args.limit:
            print(f'  ... {len(hits) - args.limit} more')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
