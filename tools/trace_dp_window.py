from __future__ import annotations

import argparse
from dataclasses import dataclass, field

from decode_snippet import CpuState, OPCODES, operand_size, parse_cpu_address, decode_instruction
from lookup_wram_field import lookup_address
from rom_tools import find_rom, hirom_to_file_offset, load_rom


@dataclass
class TraceState:
    cpu: CpuState
    accumulator: int | None = None
    x_reg: int | None = None
    y_reg: int | None = None
    direct_page: int | None = None
    data_bank: int | None = None
    d_stack: list[int | None] = field(default_factory=list)
    dp_words: dict[int, int] = field(default_factory=dict)


@dataclass(frozen=True)
class TraceNote:
    note: str


def parse_int(text: str) -> int:
    return int(text, 0)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description='Trace a short ROM snippet while resolving direct-page and indexed-absolute accesses when local state is known.'
    )
    parser.add_argument('start', type=parse_cpu_address, help='start CPU address like C2:7550')
    parser.add_argument('--count', type=int, default=24, help='instruction count to decode (default: 24)')
    parser.add_argument('--rom', help='explicit ROM path')
    parser.add_argument('--m8', action='store_true', help='start with 8-bit accumulator')
    parser.add_argument('--x8', action='store_true', help='start with 8-bit index registers')
    parser.add_argument('--force-m8', action='store_true', help='lock the accumulator width to 8-bit even across REP/SEP/XCE')
    parser.add_argument('--force-m16', action='store_true', help='lock the accumulator width to 16-bit even across REP/SEP/XCE')
    parser.add_argument('--force-x8', action='store_true', help='lock the index width to 8-bit even across REP/SEP/XCE')
    parser.add_argument('--force-x16', action='store_true', help='lock the index width to 16-bit even across REP/SEP/XCE')
    parser.add_argument('--emulation', action='store_true', help='start in emulation mode')
    parser.add_argument('--show-state', action='store_true', help='include CPU and trace state before each instruction')
    parser.add_argument('--d', type=parse_int, help='optional initial direct-page register value, like 0x99CE')
    parser.add_argument('--db', type=parse_int, help='optional initial data-bank value, like 0x7E')
    parser.add_argument('--a', type=parse_int, help='optional initial 16-bit accumulator value')
    parser.add_argument('--x', type=parse_int, help='optional initial X register value')
    parser.add_argument('--y', type=parse_int, help='optional initial Y register value')
    return parser


def format_maybe(value: int | None) -> str:
    return '????' if value is None else f'{value:04X}'


def format_state(trace: TraceState) -> str:
    db_text = '??' if trace.data_bank is None else f'{trace.data_bank:02X}'
    return f'{trace.cpu.summary()} A={format_maybe(trace.accumulator)} X={format_maybe(trace.x_reg)} Y={format_maybe(trace.y_reg)} D={format_maybe(trace.direct_page)} DB={db_text}'


def operand_u16(operand: bytes) -> int:
    return operand[0] | (operand[1] << 8)


def operand_u8(operand: bytes) -> int:
    return operand[0]


def field_note(address: int) -> str | None:
    matches = lookup_address(address)
    if not matches:
        return None
    match = matches[0]
    if match.field is None:
        return f'{match.root.name}+0x{match.record_offset:X}'
    field_name, _ = match.field.describe(match.record_offset)
    if match.root.count > 1:
        return f'{match.root.struct_name}[{match.record_index}]::{field_name}'
    return f'{match.root.struct_name}::{field_name}'


def describe_absolute(address: int) -> str:
    note = field_note(address)
    return f'${address:04X}' + (f' -> {note}' if note else '')
def describe_long(address: int) -> str:
    bank = (address >> 16) & 0xFF
    word = address & 0xFFFF
    note = field_note(word) if bank in (0x7E, 0x7F) else None
    return f'{bank:02X}:{word:04X}' + (f' -> {note}' if note else '')


def dp_absolute(trace: TraceState, operand8: int) -> int | None:
    if trace.direct_page is None:
        return None
    return (trace.direct_page + operand8) & 0xFFFF


def read_dp_word(trace: TraceState, operand8: int) -> tuple[int | None, int | None]:
    absolute = dp_absolute(trace, operand8)
    if absolute is None:
        return None, None
    return absolute, trace.dp_words.get(absolute)


def pre_trace(mode: str, operand: bytes, trace: TraceState) -> list[str]:
    notes: list[str] = []
    if mode == 'dp':
        absolute, value = read_dp_word(trace, operand_u8(operand))
        if absolute is not None:
            note = f'DP {describe_absolute(absolute)}'
            if value is not None:
                note += f' value=${value:04X}'
            notes.append(note)
    elif mode in {'dpindy', 'dp_long', 'dp_long_y'}:
        absolute, value = read_dp_word(trace, operand_u8(operand))
        if absolute is not None:
            label = 'pointer word slot' if mode == 'dpindy' else 'pointer long slot'
            note = f'{label} {describe_absolute(absolute)}'
            if value is not None:
                note += f' low16=${value:04X}'
                if mode == 'dpindy' and trace.data_bank is not None:
                    base = ((trace.data_bank & 0xFF) << 16) | value
                    if trace.y_reg is not None:
                        note += f' deref=> {describe_long((base + trace.y_reg) & 0xFFFFFF)}'
                    else:
                        note += f' deref-base=> {describe_long(base)} (+Y unknown)'
                elif mode in {'dp_long', 'dp_long_y'}:
                    note += ' (24-bit bank unknown)'
            notes.append(note)
    elif mode == 'absx' and len(operand) == 2 and trace.x_reg is not None:
        target = (operand_u16(operand) + trace.x_reg) & 0xFFFF
        notes.append(f'abs,X => {describe_absolute(target)}')
    elif mode == 'absy' and len(operand) == 2 and trace.y_reg is not None:
        target = (operand_u16(operand) + trace.y_reg) & 0xFFFF
        notes.append(f'abs,Y => {describe_absolute(target)}')
    return notes


def invalidate_dp_aliases(trace: TraceState, absolute: int) -> None:
    trace.dp_words.pop(absolute, None)


def write_dp_word(trace: TraceState, operand8: int, value: int | None) -> None:
    absolute = dp_absolute(trace, operand8)
    if absolute is None:
        return
    if value is None:
        invalidate_dp_aliases(trace, absolute)
    else:
        trace.dp_words[absolute] = value & 0xFFFF


def update_trace(opcode: int, mode: str, operand: bytes, trace: TraceState) -> None:
    operand_len = len(operand)

    if opcode == 0xA9:
        trace.accumulator = operand_u16(operand) if operand_len == 2 else None
    elif opcode == 0xA2:
        trace.x_reg = operand_u16(operand) if operand_len == 2 else operand_u8(operand) if operand_len == 1 else None
    elif opcode == 0xA0:
        trace.y_reg = operand_u16(operand) if operand_len == 2 else operand_u8(operand) if operand_len == 1 else None
    elif opcode == 0x69:
        if operand_len == 2 and trace.accumulator is not None and trace.cpu.carry is not None:
            trace.accumulator = (trace.accumulator + operand_u16(operand) + (1 if trace.cpu.carry else 0)) & 0xFFFF
        else:
            trace.accumulator = None
    elif opcode == 0xE9:
        if operand_len == 2 and trace.accumulator is not None and trace.cpu.carry is not None:
            trace.accumulator = (trace.accumulator - operand_u16(operand) - (0 if trace.cpu.carry else 1)) & 0xFFFF
        else:
            trace.accumulator = None
    elif opcode == 0xAA:
        trace.x_reg = trace.accumulator
    elif opcode == 0xA8:
        trace.y_reg = trace.accumulator
    elif opcode == 0x8A:
        trace.accumulator = trace.x_reg
    elif opcode == 0x98:
        trace.accumulator = trace.y_reg
    elif opcode == 0xBB:
        trace.x_reg = trace.y_reg
    elif opcode == 0x9B:
        trace.y_reg = trace.x_reg
    elif opcode == 0xE8:
        trace.x_reg = None if trace.x_reg is None else (trace.x_reg + 1) & 0xFFFF
    elif opcode == 0xC8:
        trace.y_reg = None if trace.y_reg is None else (trace.y_reg + 1) & 0xFFFF
    elif opcode == 0xCA:
        trace.x_reg = None if trace.x_reg is None else (trace.x_reg - 1) & 0xFFFF
    elif opcode == 0x88:
        trace.y_reg = None if trace.y_reg is None else (trace.y_reg - 1) & 0xFFFF
    elif opcode == 0x5B:
        trace.direct_page = trace.accumulator
    elif opcode == 0x7B:
        trace.accumulator = trace.direct_page
    elif opcode == 0x0B:
        trace.d_stack.append(trace.direct_page)
    elif opcode == 0x2B:
        trace.direct_page = trace.d_stack.pop() if trace.d_stack else None
    elif opcode == 0xEB:
        if trace.accumulator is not None:
            low = trace.accumulator & 0xFF
            high = (trace.accumulator >> 8) & 0xFF
            trace.accumulator = (low << 8) | high
    elif opcode == 0x85:
        write_dp_word(trace, operand_u8(operand), trace.accumulator)
    elif opcode == 0x84:
        write_dp_word(trace, operand_u8(operand), trace.y_reg)
    elif opcode == 0x86:
        write_dp_word(trace, operand_u8(operand), trace.x_reg)
    elif opcode == 0x64:
        write_dp_word(trace, operand_u8(operand), 0)
    elif opcode == 0xA5:
        _, value = read_dp_word(trace, operand_u8(operand))
        trace.accumulator = value
    elif opcode == 0xA6:
        _, value = read_dp_word(trace, operand_u8(operand))
        trace.x_reg = value
    elif opcode == 0xA4:
        _, value = read_dp_word(trace, operand_u8(operand))
        trace.y_reg = value
    else:
        mnemonic = OPCODES.get(opcode, ('', ''))[0]
        if mode == 'absx' and mnemonic in {'lda', 'cmp', 'adc', 'sbc', 'and', 'ora', 'eor'}:
            trace.accumulator = None
        elif mode == 'absy' and mnemonic in {'lda', 'cmp', 'adc', 'sbc', 'and', 'ora', 'eor'}:
            trace.accumulator = None
        elif mnemonic in {'pla', 'plb', 'phk'}:
            trace.accumulator = None


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if args.force_m8 and args.force_m16:
        parser.error('choose at most one of --force-m8 and --force-m16')
    if args.force_x8 and args.force_x16:
        parser.error('choose at most one of --force-x8 and --force-x16')

    rom_path = find_rom(args.rom)
    rom = load_rom(rom_path)
    bank, address = args.start
    force_m_bits = 8 if args.force_m8 else 16 if args.force_m16 else None
    force_x_bits = 8 if args.force_x8 else 16 if args.force_x16 else None
    cpu = CpuState(
        emulation=args.emulation,
        m8=args.m8 or args.emulation,
        x8=args.x8 or args.emulation,
        carry=None,
        force_m_bits=force_m_bits,
        force_x_bits=force_x_bits,
    )
    cpu.enforce_forces()
    trace = TraceState(
        cpu=cpu,
        accumulator=args.a,
        x_reg=args.x,
        y_reg=args.y,
        direct_page=args.d,
        data_bank=args.db,
    )

    print(f'ROM: {rom_path}')
    print(f'Start: {bank:02X}:{address:04X}')
    print(f'Initial state: {format_state(trace)}')
    print()

    current = address
    for _ in range(args.count):
        offset = hirom_to_file_offset(bank, current, len(rom))
        if offset is None:
            raise SystemExit(f'invalid ROM address {bank:02X}:{current:04X}')
        opcode = rom[offset]
        if opcode in OPCODES:
            _, mode = OPCODES[opcode]
        else:
            mode = 'unknown'
        before = format_state(trace)
        inst = decode_instruction(rom, bank, current, trace.cpu)
        operand = inst.raw[1:]
        notes: list[str] = []
        if inst.annotation:
            notes.append(inst.annotation)
        notes.extend(pre_trace(mode, operand, trace))
        update_trace(opcode, mode, operand, trace)
        raw_text = ' '.join(f'{b:02X}' for b in inst.raw)
        parts = [f'{inst.bank:02X}:{inst.address:04X}', raw_text.ljust(15), inst.text]
        if args.show_state:
            parts.append(f'[{before}]')
        line = '  '.join(parts)
        if notes:
            line += '  ; ' + ' | '.join(notes)
        print(line)
        current = (current + inst.size) & 0xFFFF

    return 0


if __name__ == '__main__':
    raise SystemExit(main())

