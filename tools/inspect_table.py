from __future__ import annotations

import argparse
from dataclasses import dataclass
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from rom_tools import find_rom, load_rom, hirom_to_file_offset
from data_contracts import DataContract, load_manifest


@dataclass(frozen=True)
class CpuAddress:
    bank: int
    address: int

    @property
    def long(self) -> int:
        return (self.bank << 16) | self.address

    def __str__(self) -> str:
        return f"{self.bank:02X}:{self.address:04X}"


@dataclass(frozen=True)
class FieldSpec:
    name: str
    kind: str
    offset: int
    size: int | None = None


def parse_int(value: str) -> int:
    return int(value, 0)


def parse_cpu_address(text: str) -> CpuAddress:
    candidate = text.strip().upper()
    if ':' in candidate:
        bank_text, addr_text = candidate.split(':', 1)
    else:
        if len(candidate) != 6:
            raise argparse.ArgumentTypeError(
                'CPU address must look like D5:5000 or D55000'
            )
        bank_text, addr_text = candidate[:2], candidate[2:]

    try:
        bank = int(bank_text, 16)
        address = int(addr_text, 16)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            'CPU address must use hexadecimal digits'
        ) from exc

    if not 0 <= bank <= 0xFF or not 0 <= address <= 0xFFFF:
        raise argparse.ArgumentTypeError('CPU address is out of range')

    return CpuAddress(bank=bank, address=address)


def parse_field_spec(text: str) -> FieldSpec:
    parts = text.split(':')
    if len(parts) not in (3, 4):
        raise argparse.ArgumentTypeError(
            'field must look like name:kind:offset or name:kind:offset:size'
        )

    name = parts[0].strip()
    kind = parts[1].strip().lower()
    offset = parse_int(parts[2].strip())
    size = parse_int(parts[3].strip()) if len(parts) == 4 else None

    if not name:
        raise argparse.ArgumentTypeError('field name cannot be empty')
    if offset < 0:
        raise argparse.ArgumentTypeError('field offset must be non-negative')

    if kind not in {'b', 'w', 'd', 'x', 'a'}:
        raise argparse.ArgumentTypeError(
            "field kind must be one of: b, w, d, x, a"
        )

    if kind in {'x', 'a'}:
        if size is None or size <= 0:
            raise argparse.ArgumentTypeError(
                'field kinds x and a require a positive size'
            )
    else:
        if size is not None:
            raise argparse.ArgumentTypeError(
                'field kinds b, w, d do not take an explicit size'
            )

    return FieldSpec(name=name, kind=kind, offset=offset, size=size)


def read_u16_le(data: bytes, offset: int) -> int:
    return data[offset] | (data[offset + 1] << 8)


def read_u32_le(data: bytes, offset: int) -> int:
    return (
        data[offset]
        | (data[offset + 1] << 8)
        | (data[offset + 2] << 16)
        | (data[offset + 3] << 24)
    )


def format_ascii(blob: bytes) -> str:
    chars: list[str] = []
    for byte in blob:
        if 32 <= byte <= 126:
            chars.append(chr(byte))
        else:
            chars.append('.')
    return ''.join(chars)


def field_width(kind: str, explicit_size: int | None) -> int:
    if kind == 'b':
        return 1
    if kind == 'w':
        return 2
    if kind == 'd':
        return 4
    assert explicit_size is not None
    return explicit_size


def field_from_contract(data_field) -> FieldSpec:
    total_size = data_field.size * data_field.count
    if total_size == 1:
        kind = 'b'
        size = None
    elif total_size == 2:
        kind = 'w'
        size = None
    elif total_size == 4:
        kind = 'd'
        size = None
    else:
        kind = 'x'
        size = total_size
    return FieldSpec(name=data_field.name, kind=kind, offset=data_field.offset, size=size)


def base_from_contract(contract: DataContract) -> CpuAddress:
    return CpuAddress(bank=contract.address.bank, address=contract.address.address)


def file_offset_for(cpu: CpuAddress, rom_size: int) -> int:
    file_offset = hirom_to_file_offset(cpu.bank, cpu.address, rom_size)
    if file_offset is None:
        raise ValueError(f'{cpu} does not map to ROM data')
    return file_offset


def validate_bounds(record_size: int, fields: list[FieldSpec]) -> None:
    for field in fields:
        end = field.offset + field_width(field.kind, field.size)
        if end > record_size:
            raise ValueError(
                f"field '{field.name}' ends at 0x{end:X}, past record size 0x{record_size:X}"
            )


def format_field(record: bytes, field: FieldSpec) -> str:
    off = field.offset
    if field.kind == 'b':
        value = record[off]
        return f'0x{value:02X} ({value})'
    if field.kind == 'w':
        value = read_u16_le(record, off)
        return f'0x{value:04X} ({value})'
    if field.kind == 'd':
        value = read_u32_le(record, off)
        return f'0x{value:08X} ({value})'
    if field.kind == 'x':
        blob = record[off:off + field.size]
        return ' '.join(f'{byte:02X}' for byte in blob)
    blob = record[off:off + field.size]
    return f'"{format_ascii(blob)}"'


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            'Inspect a fixed-stride ROM table using SNES CPU addresses and named fields.'
        )
    )
    parser.add_argument('base', nargs='?', type=parse_cpu_address, help='table base CPU address')
    parser.add_argument('--rom', help='path to ROM file')
    parser.add_argument('--contract', help='contract id from build/data-contracts-c0-c3.json')
    parser.add_argument('--manifest', default=None, help='contract manifest path')
    parser.add_argument(
        '--stride',
        type=parse_int,
        help='record stride in bytes',
    )
    parser.add_argument(
        '--index',
        type=parse_int,
        default=0,
        help='first record index to print (default: 0)',
    )
    parser.add_argument(
        '--count',
        type=parse_int,
        default=1,
        help='number of records to print (default: 1)',
    )
    parser.add_argument(
        '--field',
        action='append',
        default=[],
        type=parse_field_spec,
        help='named field spec: name:kind:offset or name:kind:offset:size',
    )
    parser.add_argument(
        '--raw-bytes',
        type=parse_int,
        default=0,
        help='include a leading raw-byte preview of N bytes from each record',
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.index < 0:
        parser.error('--index must be non-negative')
    if args.count <= 0:
        parser.error('--count must be positive')
    if args.raw_bytes < 0:
        parser.error('--raw-bytes must be non-negative')

    contract: DataContract | None = None
    if args.contract:
        manifest = load_manifest(args.manifest)
        try:
            contract = manifest.require(args.contract)
        except KeyError as exc:
            parser.error(str(exc))
        if contract.domain not in {'rom-table', 'wram-root', 'wram-overlay'}:
            parser.error(f'unsupported contract domain: {contract.domain}')
        if args.base is None:
            args.base = base_from_contract(contract)
        if args.stride is None:
            args.stride = contract.stride
        if not args.field:
            args.field = [field_from_contract(field) for field in contract.fields]

    if args.base is None:
        parser.error('base is required unless --contract is provided')
    if args.stride is None:
        parser.error('--stride is required unless --contract is provided')
    if args.stride <= 0:
        parser.error('--stride must be positive')
    rom_path = find_rom(args.rom)
    rom_data = load_rom(rom_path)
    base_offset = file_offset_for(args.base, len(rom_data))

    fields: list[FieldSpec] = list(args.field)
    validate_bounds(args.stride, fields)

    print(f'ROM: {rom_path}')
    if contract is not None:
        print(f'Contract: {contract.id} ({contract.struct_name})')
    print(f'Table: {args.base} (file 0x{base_offset:06X})')
    print(f'Stride: 0x{args.stride:X} ({args.stride})')
    print(f'Index: {args.index}')
    print(f'Count: {args.count}')
    print()

    for index in range(args.index, args.index + args.count):
        record_offset = base_offset + (index * args.stride)
        record_end = record_offset + args.stride
        if record_end > len(rom_data):
            raise ValueError(
                f'record {index} runs past end of ROM at file 0x{record_end:06X}'
            )
        record = rom_data[record_offset:record_end]
        cpu_address = CpuAddress(
            bank=args.base.bank,
            address=(args.base.address + (index * args.stride)) & 0xFFFF,
        )
        print(f'Record {index} @ {cpu_address} (file 0x{record_offset:06X})')
        if args.raw_bytes:
            preview = record[:args.raw_bytes]
            print('  raw:', ' '.join(f'{byte:02X}' for byte in preview))
        if fields:
            for field in fields:
                print(f'  {field.name}: {format_field(record, field)}')
        else:
            print('  raw:', ' '.join(f'{byte:02X}' for byte in record))
        print()

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
