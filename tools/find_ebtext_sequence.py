from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

from rom_tools import canonical_bank_for_file_offset, find_rom, load_rom


DEFAULT_YML = Path('refs/ebsrc-main/ebsrc-main/earthbound.yml')


def parse_bytes(text: str) -> bytes:
    cleaned = text.replace(' ', '').replace(',', '').replace('_', '')
    if len(cleaned) % 2 != 0:
        raise argparse.ArgumentTypeError('byte sequence must contain an even number of hex digits')
    try:
        return bytes.fromhex(cleaned)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc


def load_text_segments(path: Path) -> list[tuple[int, int, str]]:
    lines = path.read_text(encoding='utf-8').splitlines()
    entries: list[tuple[int, int, str]] = []
    for i, line in enumerate(lines):
        if line.startswith('- subdir: US/text_data'):
            name = lines[i + 1].split("'", 2)[1]
            offset = int(lines[i + 2].split(':', 1)[1].strip(), 16)
            size = int(lines[i + 3].split(':', 1)[1].strip())
            entries.append((offset, offset + size, name))
    return entries


def fmt_cpu(offset: int) -> str:
    bank = canonical_bank_for_file_offset(offset)
    addr = offset & 0xFFFF
    return f'{bank:02X}:{addr:04X}'


def main() -> int:
    parser = argparse.ArgumentParser(description='Find a byte sequence inside EarthBound text-data segments.')
    parser.add_argument('sequence', type=parse_bytes, help='Hex byte sequence, for example "19 1F"')
    parser.add_argument('--rom', help='Optional explicit ROM path')
    parser.add_argument('--yml', default=str(DEFAULT_YML), help='Path to earthbound.yml (default: refs/ebsrc-main/ebsrc-main/earthbound.yml)')
    parser.add_argument('--segment', action='append', help='Restrict to one or more text segment names, for example EBATTLE8')
    parser.add_argument('--limit', type=int, default=200, help='Maximum exact hits to print (default: 200)')
    args = parser.parse_args()

    yml_path = Path(args.yml)
    if not yml_path.is_file():
        raise SystemExit(f'earthbound.yml not found: {yml_path}')

    rom_path = find_rom(args.rom)
    rom = load_rom(rom_path)
    segments = load_text_segments(yml_path)
    if args.segment:
        wanted = {name.upper() for name in args.segment}
        segments = [entry for entry in segments if entry[2].upper() in wanted]

    hits: list[tuple[int, str]] = []
    for start, end, name in segments:
        pos = start
        while True:
            pos = rom.find(args.sequence, pos, end)
            if pos < 0:
                break
            hits.append((pos, name))
            pos += 1

    counts = Counter(name for _, name in hits)
    seq_text = ' '.join(f'{b:02X}' for b in args.sequence)

    print(f'ROM: {rom_path}')
    print(f'YML: {yml_path}')
    print(f'Sequence: {seq_text}')
    print(f'Text hits: {len(hits)}')
    print()
    print('By segment:')
    for name, count in counts.most_common():
        print(f'  {name}: {count}')

    if not hits:
        return 0

    print()
    print('Exact hits:')
    for offset, name in hits[:args.limit]:
        print(f'  {fmt_cpu(offset)}  file 0x{offset:06X}  {name}')
    if len(hits) > args.limit:
        print(f'  ... {len(hits) - args.limit} more')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
