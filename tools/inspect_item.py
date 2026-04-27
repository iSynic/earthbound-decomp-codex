from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from rom_tools import find_rom, load_rom, hirom_to_file_offset
from data_contracts import load_manifest

def contract_table_params(contract_id: str, fallback: tuple[int, int, int]) -> tuple[int, int, int]:
    try:
        contract = load_manifest().require(contract_id)
    except Exception:
        return fallback
    return contract.address.bank, contract.address.address, contract.stride


ITEM_TABLE_BANK, ITEM_TABLE_ADDR, ITEM_RECORD_SIZE = contract_table_params(
    'ITEM_CONFIGURATION_TABLE',
    (0xD5, 0x5000, 0x27),
)
ITEM_NAME_SOURCE = (
    Path(__file__).resolve().parent.parent
    / 'refs'
    / 'ebsrc-main'
    / 'ebsrc-main'
    / 'include'
    / 'constants'
    / 'items.asm'
)

BROAD_CLASS_NAMES = {
    1: 'general non-equippable item',
    2: 'equippable item',
    3: 'edible item',
    4: 'other usable item',
}
EQUIP_SUBTYPE_NAMES = {
    0x00: 'first equip subtype (weapon-like branch)',
    0x04: 'second equip subtype',
    0x08: 'third equip subtype',
    0x0C: 'fourth equip subtype',
}
USER_MASKS = [
    (0x01, 'Ness can use/equip'),
    (0x02, 'Paula can use/equip'),
    (0x04, 'Jeff can use/equip'),
    (0x08, 'Poo can use/equip'),
]
KNOWN_FLAG_BITS = [
    (0x10, 'egg/teddy-bear cleanup family bit'),
    (0x40, 'service/delivery eligibility bit'),
]


@dataclass(frozen=True)
class ItemRecord:
    item_id: int
    file_offset: int
    raw: bytes

    @property
    def cpu_address(self) -> str:
        return f'{ITEM_TABLE_BANK:02X}:{(ITEM_TABLE_ADDR + self.item_id * ITEM_RECORD_SIZE) & 0xFFFF:04X}'

    def byte(self, offset: int) -> int:
        return self.raw[offset]

    def word(self, offset: int) -> int:
        return self.raw[offset] | (self.raw[offset + 1] << 8)

    def dword(self, offset: int) -> int:
        return (
            self.raw[offset]
            | (self.raw[offset + 1] << 8)
            | (self.raw[offset + 2] << 16)
            | (self.raw[offset + 3] << 24)
        )


def parse_int(text: str) -> int:
    return int(text, 0)


def load_item_names() -> dict[int, str]:
    names: dict[int, str] = {}
    if not ITEM_NAME_SOURCE.is_file():
        return names
    pattern = re.compile(r'^\s*([A-Z0-9_]+)\s*=\s*\$([0-9A-F]{2})\s*$')
    for line in ITEM_NAME_SOURCE.read_text(encoding='ascii', errors='ignore').splitlines():
        match = pattern.match(line)
        if not match:
            continue
        symbol = match.group(1)
        item_id = int(match.group(2), 16)
        names[item_id] = symbol.lower().replace('_', ' ')
    return names


def broad_class(raw_byte19: int) -> int:
    masked = raw_byte19 & 0x30
    return ((masked >> 4) + 1) if masked in (0x00, 0x10, 0x20, 0x30) else 0


def equip_subtype(raw_byte19: int) -> int:
    return raw_byte19 & 0x0C


def format_money(value: int) -> str:
    return f'{value}'


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Inspect one or more EarthBound item records with note-backed field interpretations.'
    )
    parser.add_argument('item', type=parse_int, help='item id (decimal or hex, e.g. 0x5C)')
    parser.add_argument('--rom', help='path to ROM file')
    parser.add_argument('--count', type=parse_int, default=1, help='number of consecutive items to print')
    parser.add_argument('--raw-bytes', type=parse_int, default=0, help='include a leading raw-byte preview of N bytes')
    return parser.parse_args()


def item_record(rom_data: bytes, item_id: int) -> ItemRecord:
    if not 0 <= item_id <= 0xFF:
        raise ValueError(f'item id out of range: {item_id}')
    file_offset = hirom_to_file_offset(ITEM_TABLE_BANK, ITEM_TABLE_ADDR + item_id * ITEM_RECORD_SIZE, len(rom_data))
    if file_offset is None:
        raise ValueError(f'item {item_id} does not map to ROM data')
    raw = rom_data[file_offset:file_offset + ITEM_RECORD_SIZE]
    if len(raw) != ITEM_RECORD_SIZE:
        raise ValueError(f'item record {item_id} runs past end of ROM')
    return ItemRecord(item_id=item_id, file_offset=file_offset, raw=raw)


def print_record(record: ItemRecord, names: dict[int, str], raw_bytes: int) -> None:
    item_id = record.item_id
    name = names.get(item_id, '<unknown>')
    raw19 = record.byte(0x19)
    broad = broad_class(raw19)
    subtype = equip_subtype(raw19)
    flags = record.byte(0x1C)
    action = record.word(0x1D)
    params = record.dword(0x1F)
    help_ptr = record.dword(0x23)

    print(f'Item 0x{item_id:02X} ({item_id}) - {name}')
    print(f'  record: {record.cpu_address} (file 0x{record.file_offset:06X})')
    if raw_bytes:
        preview = record.raw[:raw_bytes]
        print('  raw:   ' + ' '.join(f'{byte:02X}' for byte in preview))

    print(f'  +0x19 packed type: 0x{raw19:02X}')
    if broad:
        print(f'    broad class: {broad} ({BROAD_CLASS_NAMES.get(broad, "unknown")})')
    else:
        print('    broad class: 0 (unrecognized)')
    if broad == 2:
        print(f'    equip subtype bits: 0x{subtype:02X} ({EQUIP_SUBTYPE_NAMES.get(subtype, "unrecognized subtype")})')
    else:
        print(f'    equip subtype bits: 0x{subtype:02X} (not interpreted for this broad class)')

    print(f'  +0x1C flags: 0x{flags:02X}')
    active_users = [label for mask, label in USER_MASKS if flags & mask]
    if active_users:
        print('    user bits: ' + '; '.join(active_users))
    else:
        print('    user bits: none')
    known_high = [label for mask, label in KNOWN_FLAG_BITS if flags & mask]
    if known_high:
        print('    other known bits: ' + '; '.join(known_high))
    unknown_mask = flags & ~(0x0F | 0x10 | 0x40)
    if unknown_mask:
        print(f'    unknown bits: 0x{unknown_mask:02X}')

    print(f'  +0x1D action/effect: 0x{action:04X} ({action})')
    print(f'  +0x1F params dword:  0x{params:08X}')
    print(f'    byte +0x1F: 0x{record.byte(0x1F):02X} ({record.byte(0x1F)})')
    print(f'    byte +0x20: 0x{record.byte(0x20):02X} ({record.byte(0x20)})')
    print(f'    byte +0x21: 0x{record.byte(0x21):02X} ({record.byte(0x21)})')
    print(f'    byte +0x22: 0x{record.byte(0x22):02X} ({record.byte(0x22)})')
    if broad == 2:
        print('    note: equippable class; +0x20/+0x21 are often equipment-stat payload bytes')
    if name.startswith('broken '):
        repaired = names.get(record.byte(0x21), '<unknown>')
        print(f'    broken-item read: repair IQ at +0x20 = {record.byte(0x20)}; repaired item id at +0x21 = 0x{record.byte(0x21):02X} ({repaired})')

    print(f'  +0x23 help pointer:  0x{help_ptr:08X}')
    print(f'  +0x1A cost:         {format_money(record.word(0x1A))}')
    print()


def main() -> int:
    args = parse_args()
    if args.count <= 0:
        raise SystemExit('--count must be positive')
    if args.raw_bytes < 0:
        raise SystemExit('--raw-bytes must be non-negative')

    rom_path = find_rom(args.rom)
    rom_data = load_rom(rom_path)
    names = load_item_names()

    print(f'ROM: {rom_path}')
    print(f'Table: {ITEM_TABLE_BANK:02X}:{ITEM_TABLE_ADDR:04X} stride 0x{ITEM_RECORD_SIZE:X} (ITEM_CONFIGURATION_TABLE)')
    print()
    for item_id in range(args.item, args.item + args.count):
        print_record(item_record(rom_data, item_id), names, args.raw_bytes)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
