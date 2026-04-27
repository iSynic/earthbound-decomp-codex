from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from disasm_ebtext_script import decode_text_run, parse_command
from data_contracts import load_manifest
from extract_ebtext import parse_snes_address
from rom_tools import find_rom, hirom_to_file_offset, load_rom

def contract_table_params(contract_id: str, fallback: tuple[int, int, int]) -> tuple[int, int, int]:
    try:
        contract = load_manifest().require(contract_id)
    except Exception:
        return fallback
    return contract.address.bank, contract.address.address, contract.stride


TABLE_BANK, TABLE_ADDR, ENTRY_SIZE = contract_table_params(
    'BATTLE_ACTION_TABLE',
    (0xD5, 0x7B68, 0x0C),
)
TABLE_FILE = Path(__file__).resolve().parent.parent / 'refs' / 'eb-decompile-4ef92' / 'battle_action_table.yml'
NOTES_DIR = Path(__file__).resolve().parent.parent / 'notes'
TEXT_PREVIEW_BYTES = 96
TEXT_PREVIEW_LINES = 12

DIRECTION_NAMES = {
    0: 'party',
    1: 'enemy',
}
TARGET_NAMES = {
    0: 'none',
    1: 'one',
    2: 'random',
    3: 'row',
    4: 'all',
}
TYPE_NAMES = {
    0: 'nothing',
    1: 'physical',
    2: 'piercing physical',
    3: 'psi',
    4: 'item',
    5: 'other',
}


@dataclass(frozen=True)
class BattleActionEntry:
    index: int
    cpu_address: str
    file_offset: int
    direction: int
    target: int
    action_type: int
    cost: int
    message_ptr: int
    action_ptr: int


def fmt_addr(long_addr: int) -> str:
    return f'{(long_addr >> 16) & 0xFF:02X}:{long_addr & 0xFFFF:04X}'


def read_u32_le(data: bytes, offset: int) -> int:
    return (
        data[offset]
        | (data[offset + 1] << 8)
        | (data[offset + 2] << 16)
        | (data[offset + 3] << 24)
    )


def parse_int(text: str) -> int:
    return int(text, 0)


def parse_entry_selector(text: str) -> tuple[str, int]:
    raw = text.strip()
    if ':' in raw:
        return ('code', parse_snes_address(raw))
    if re.fullmatch(r'[0-9A-Fa-f]{6}', raw):
        value = int(raw, 16)
        if value >= 0x10000:
            return ('code', value)
    return ('index', parse_int(raw))


def table_base_offset(rom: bytes) -> int:
    file_offset = hirom_to_file_offset(TABLE_BANK, TABLE_ADDR, len(rom))
    if file_offset is None:
        raise ValueError('battle action table does not map into ROM')
    return file_offset


def load_entry(rom: bytes, index: int) -> BattleActionEntry:
    if index < 0:
        raise ValueError('index must be non-negative')
    base = table_base_offset(rom)
    file_offset = base + index * ENTRY_SIZE
    raw = rom[file_offset:file_offset + ENTRY_SIZE]
    if len(raw) != ENTRY_SIZE:
        raise ValueError(f'entry {index} runs past end of ROM')
    return BattleActionEntry(
        index=index,
        cpu_address=f'{TABLE_BANK:02X}:{(TABLE_ADDR + index * ENTRY_SIZE) & 0xFFFF:04X}',
        file_offset=file_offset,
        direction=raw[0],
        target=raw[1],
        action_type=raw[2],
        cost=raw[3],
        message_ptr=read_u32_le(raw, 4),
        action_ptr=read_u32_le(raw, 8),
    )


def find_entries_by_code(rom: bytes, code_addr: int, limit: int | None = None) -> list[BattleActionEntry]:
    matches: list[BattleActionEntry] = []
    base = table_base_offset(rom)
    count = (len(rom) - base) // ENTRY_SIZE
    for index in range(count):
        entry = load_entry(rom, index)
        if entry.action_ptr == code_addr:
            matches.append(entry)
            if limit is not None and len(matches) >= limit:
                break
    return matches


def preview_text_lines(rom: bytes, start_addr: int, *, max_bytes: int = TEXT_PREVIEW_BYTES, max_lines: int = TEXT_PREVIEW_LINES) -> list[str]:
    bank = (start_addr >> 16) & 0xFF
    addr = start_addr & 0xFFFF
    file_offset = hirom_to_file_offset(bank, addr, len(rom))
    if file_offset is None:
        return ['<message pointer does not map into ROM>']
    data = rom[file_offset:file_offset + max_bytes]
    lines: list[str] = []
    i = 0
    while i < len(data) and len(lines) < max_lines:
        absolute = start_addr + i
        if data[i] >= 0x20:
            text, size = decode_text_run(data, i)
            lines.append(f'{fmt_addr(absolute)}  TEXT "{text}"')
            i += size
            continue
        try:
            rendered, size = parse_command(data, i)
        except Exception as exc:  # pragma: no cover - defensive fallback
            lines.append(f'{fmt_addr(absolute)}  <parse error: {exc}>')
            break
        lines.append(f'{fmt_addr(absolute)}  {rendered}')
        i += max(size, 1)
        if rendered == 'END_BLOCK':
            break
    return lines


def load_table_metadata() -> dict[int, dict[str, str]]:
    metadata: dict[int, dict[str, str]] = {}
    if not TABLE_FILE.is_file():
        return metadata
    current: int | None = None
    for line in TABLE_FILE.read_text(encoding='utf-8', errors='ignore').splitlines():
        m = re.match(r'^(\d+):\s*$', line)
        if m:
            current = int(m.group(1))
            metadata.setdefault(current, {})
            continue
        if current is None:
            continue
        m = re.match(r'^\s{2}([^:]+):\s*(.+?)\s*$', line)
        if not m:
            continue
        key = m.group(1).strip()
        value = m.group(2).strip()
        metadata[current][key] = value
    return metadata


def note_hits(long_addr: int, limit: int = 8) -> list[str]:
    addr_text = fmt_addr(long_addr).upper()
    patterns = {
        addr_text,
        f'{long_addr:06X}',
    }
    hits: list[str] = []
    if not NOTES_DIR.is_dir():
        return hits
    for path in sorted(NOTES_DIR.glob('*.md')):
        try:
            lines = path.read_text(encoding='utf-8', errors='ignore').splitlines()
        except OSError:
            continue
        matched = False
        for lineno, line in enumerate(lines, start=1):
            upper = line.upper()
            if any(pattern in upper for pattern in patterns):
                hits.append(f'{path.name}:{lineno}: {line.strip()}')
                matched = True
                break
        if matched and len(hits) >= limit:
            break
    return hits


def print_entry(entry: BattleActionEntry, metadata: dict[int, dict[str, str]], rom: bytes) -> None:
    print(f'Entry {entry.index} @ {entry.cpu_address} (file 0x{entry.file_offset:06X})')
    print(f'  direction: 0x{entry.direction:02X} ({DIRECTION_NAMES.get(entry.direction, "unknown")})')
    print(f'  target:    0x{entry.target:02X} ({TARGET_NAMES.get(entry.target, "unknown")})')
    print(f'  type:      0x{entry.action_type:02X} ({TYPE_NAMES.get(entry.action_type, "unknown")})')
    print(f'  cost:      0x{entry.cost:02X} ({entry.cost})')
    print(f'  message:   {fmt_addr(entry.message_ptr)}')
    print(f'  action:    {fmt_addr(entry.action_ptr)}')

    if entry.index in metadata:
        row = metadata[entry.index]
        print('  ref row:')
        for key in ('Direction', 'Target', 'Action type', 'PP Cost', 'Text Address', 'Code Address'):
            value = row.get(key)
            if value is not None:
                print(f'    {key}: {value}')

    print('  message preview:')
    for line in preview_text_lines(rom, entry.message_ptr):
        print(f'    {line}')

    hits = note_hits(entry.action_ptr)
    if hits:
        print('  note hits:')
        for hit in hits:
            print(f'    {hit}')
    print()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description='Inspect one or more EarthBound D5:7B68 battle action entries by index or code address.'
    )
    parser.add_argument('entry', help='entry index (decimal/hex) or code address like C2:8D5A')
    parser.add_argument('--rom', help='path to ROM file')
    parser.add_argument('--count', type=parse_int, default=1, help='number of consecutive entries to print when using an index')
    parser.add_argument('--limit', type=parse_int, default=8, help='maximum matches to print when searching by code address')
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if args.count <= 0:
        parser.error('--count must be positive')
    if args.limit <= 0:
        parser.error('--limit must be positive')

    rom_path = find_rom(args.rom)
    rom = load_rom(rom_path)
    metadata = load_table_metadata()
    mode, value = parse_entry_selector(args.entry)

    print(f'ROM: {rom_path}')
    print(f'Table: {TABLE_BANK:02X}:{TABLE_ADDR:04X} stride 0x{ENTRY_SIZE:X} (BATTLE_ACTION_TABLE)')
    print()

    if mode == 'index':
        for index in range(value, value + args.count):
            print_entry(load_entry(rom, index), metadata, rom)
        return 0

    matches = find_entries_by_code(rom, value, limit=args.limit)
    if not matches:
        print(f'No D5:7B68 entries found for action pointer {fmt_addr(value)}')
        return 0
    for entry in matches:
        print_entry(entry, metadata, rom)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
