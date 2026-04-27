from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from data_contracts import load_manifest


WRAM_SIZE = 0x20000


@dataclass(frozen=True)
class FieldSpec:
    name: str
    offset: int
    kind: str
    note: str
    size: int = 1


def load_slot_contract():
    return load_manifest().require('PARTY_CHARACTERS')


def field_kind(size: int, count: int) -> tuple[str, int]:
    total = size * count
    if total == 1:
        return 'b', 1
    if total == 2:
        return 'w', 2
    return 'x', total


SLOT_CONTRACT = load_slot_contract()
SLOT_BASE = SLOT_CONTRACT.address.address
SLOT_STRIDE = SLOT_CONTRACT.stride
FIELDS: list[FieldSpec] = []
for data_field in SLOT_CONTRACT.fields:
    kind, size = field_kind(data_field.size, data_field.count)
    FIELDS.append(FieldSpec(data_field.name, data_field.offset, kind, data_field.note, size))


def parse_int(text: str) -> int:
    return int(text, 0)


def read_wram(path: str | None) -> bytes | None:
    if path is None:
        return None
    data = Path(path).read_bytes()
    if len(data) < WRAM_SIZE:
        raise SystemExit(
            f'WRAM dump is too short: expected at least 0x{WRAM_SIZE:X} bytes, got 0x{len(data):X}'
        )
    if len(data) > WRAM_SIZE:
        data = data[:WRAM_SIZE]
    return data


def read_u8(wram: bytes, address: int) -> int:
    return wram[address]


def read_u16(wram: bytes, address: int) -> int:
    return wram[address] | (wram[address + 1] << 8)


def format_value(field: FieldSpec, wram: bytes, address: int) -> str:
    if field.kind == 'b':
        value = read_u8(wram, address)
        return f'0x{value:02X} ({value})'
    if field.kind == 'w':
        value = read_u16(wram, address)
        return f'0x{value:04X} ({value})'
    blob = wram[address:address + field.size]
    return ' '.join(f'{byte:02X}' for byte in blob)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description='Inspect the recurring 0x5F-stride live slot family rooted at WRAM $99CE.'
    )
    parser.add_argument(
        'slot',
        nargs='+',
        type=parse_int,
        help='slot number(s); default interpretation is 1-based',
    )
    parser.add_argument(
        '--zero-based',
        action='store_true',
        help='treat input slot numbers as 0-based record indices',
    )
    parser.add_argument(
        '--wram',
        help='optional raw 128 KiB WRAM dump to show live values instead of addresses only',
    )
    return parser


def slot_index(raw_slot: int, zero_based: bool) -> int:
    index = raw_slot if zero_based else raw_slot - 1
    if index < 0:
        raise SystemExit(f'invalid slot {raw_slot}: resulting index is negative')
    return index


def print_slot(raw_slot: int, index: int, wram: bytes | None) -> None:
    base = SLOT_BASE + index * SLOT_STRIDE
    end = base + SLOT_STRIDE - 1
    print(f'Slot {raw_slot} (index {index})')
    print(f'  base: ${base:04X} .. ${end:04X}  (stride 0x{SLOT_STRIDE:X})')
    for field in FIELDS:
        address = base + field.offset
        line = f'  {field.name}: ${address:04X}'
        if wram is not None:
            line += f' = {format_value(field, wram, address)}'
        line += f'  ; {field.note}'
        print(line)
    print()


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    wram = read_wram(args.wram)
    if wram is not None:
        print(f'WRAM: {args.wram}')
    else:
        print('WRAM: <not provided; printing addresses only>')
    print(f'Slot family: ${SLOT_BASE:04X} stride 0x{SLOT_STRIDE:X}')
    print()
    for raw_slot in args.slot:
        index = slot_index(raw_slot, args.zero_based)
        print_slot(raw_slot, index, wram)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
