from __future__ import annotations

import argparse
from pathlib import Path
import sys

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import disasm_ebtext_script as ebscript
import find_ebtext_command as findcmd
import rom_tools


def canonical_to_file_offset(addr: int, rom_len: int) -> int | None:
    bank = (addr >> 16) & 0xFF
    address = addr & 0xFFFF
    return rom_tools.hirom_to_file_offset(bank, address, rom_len)


def locate_segment(segments: list[tuple[str, int, int]], file_offset: int) -> tuple[str, int, int] | None:
    for seg_name, seg_off, seg_size in segments:
        if seg_off <= file_offset < seg_off + seg_size:
            return seg_name, seg_off, seg_size
    return None


def main() -> int:
    parser = argparse.ArgumentParser(
        description='Show parsed EarthBound text-command hits with nearby disassembly context.'
    )
    parser.add_argument('opcode', help='Top-level command byte, for example 1D')
    parser.add_argument('subopcode', nargs='?', help='Optional subcommand byte, for example 24')
    parser.add_argument('--rom', help='Optional explicit ROM path')
    parser.add_argument('--yml', default='refs/ebsrc-main/ebsrc-main/earthbound.yml', help='YAML file with text_data segment offsets')
    parser.add_argument('--limit', type=int, default=8, help='Maximum hits to show')
    parser.add_argument('--before', type=int, default=32, help='Raw bytes before each hit to decode')
    parser.add_argument('--after', type=int, default=64, help='Raw bytes after each hit to decode')
    args = parser.parse_args()

    rom_path = rom_tools.find_rom(args.rom)
    rom = rom_tools.load_rom(rom_path)
    yml_path = Path(args.yml)
    segments = findcmd.load_segments(yml_path)
    op = findcmd.parse_hex_byte(args.opcode)
    sub = findcmd.parse_hex_byte(args.subopcode) if args.subopcode is not None else None
    hits = findcmd.find_hits(rom, segments, op, sub)

    print(f'ROM: {rom_path}')
    print(f'YML: {yml_path}')
    print(f'Command: {findcmd.command_name_for(op, sub)}')
    print(f'Exact parsed hits: {len(hits)}')
    print()

    for index, (seg_name, address, text) in enumerate(hits[:args.limit], start=1):
        file_offset = canonical_to_file_offset(address, len(rom))
        if file_offset is None:
            print(f'[{index}] {ebscript.fmt_addr(address)} {seg_name}')
            print('  Unable to map hit back to ROM file offset.')
            print()
            continue
        located = locate_segment(segments, file_offset)
        if located is None:
            print(f'[{index}] {ebscript.fmt_addr(address)} {seg_name}')
            print('  Hit is not inside an exposed text_data segment range.')
            print()
            continue
        _, seg_off, seg_size = located
        hit_idx = file_offset - seg_off
        start_idx = max(0, hit_idx - args.before)
        end_idx = min(seg_size, hit_idx + args.after)
        data = rom[seg_off + start_idx:seg_off + end_idx]
        start_address = findcmd.file_offset_to_canonical_hirom(seg_off + start_idx)

        print(f'[{index}] {ebscript.fmt_addr(address)}  {seg_name}  {text}')
        print(f'  Window: file 0x{seg_off + start_idx:06X}-0x{seg_off + end_idx:06X}')
        for line in ebscript.decode_script(data, start_address):
            marker = '>>' if line.address == address else '  '
            print(f'{marker} {ebscript.fmt_addr(line.address)}  {line.text}')
        print()

    remaining = len(hits) - min(len(hits), args.limit)
    if remaining > 0:
        print(f'... {remaining} more hits not shown')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
