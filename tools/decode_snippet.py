from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

from rom_tools import find_rom, hirom_to_file_offset, load_rom


OPCODES = {
    0x00: ("brk", "imm8"),
    0x03: ("ora", "sr"),
    0x05: ("ora", "dp"),
    0x06: ("asl", "dp"),
    0x08: ("php", "impl"),
    0x09: ("ora", "imm_m"),
    0x0A: ("asl", "acc"),
    0x0B: ("phd", "impl"),
    0x0C: ("tsb", "abs"),
    0x0D: ("ora", "abs"),
    0x0E: ("asl", "abs"),
    0x0F: ("ora", "long"),
    0x10: ("bpl", "rel8"),
    0x11: ("ora", "dpindy"),
    0x12: ("ora", "dpind"),
    0x14: ("trb", "dp"),
    0x15: ("ora", "dpx"),
    0x16: ("asl", "dpx"),
    0x18: ("clc", "impl"),
    0x1A: ("inc", "acc"),
    0x1B: ("tcs", "impl"),
    0x1D: ("ora", "absx"),
    0x1F: ("ora", "longx"),
    0x20: ("jsr", "abs"),
    0x22: ("jsl", "long"),
    0x24: ("bit", "dp"),
    0x26: ("rol", "dp"),
    0x28: ("plp", "impl"),
    0x29: ("and", "imm_m"),
    0x2A: ("rol", "acc"),
    0x25: ("and", "dp"),
    0x2B: ("pld", "impl"),
    0x2C: ("bit", "abs"),
    0x2D: ("and", "abs"),
    0x2E: ("rol", "abs"),
    0x2F: ("and", "long"),
    0x30: ("bmi", "rel8"),
    0x35: ("and", "dpx"),
    0x38: ("sec", "impl"),
    0x39: ("and", "absy"),
    0x3A: ("dec", "acc"),
    0x3C: ("bit", "absx"),
    0x3D: ("and", "absx"),
    0x3F: ("and", "longx"),
    0x40: ("rti", "impl"),
    0x42: ("wdm", "imm8"),
    0x45: ("eor", "dp"),
    0x46: ("lsr", "dp"),
    0x48: ("pha", "impl"),
    0x49: ("eor", "imm_m"),
    0x4A: ("lsr", "acc"),
    0x4B: ("phk", "impl"),
    0x4C: ("jmp", "abs"),
    0x4D: ("eor", "abs"),
    0x4E: ("lsr", "abs"),
    0x4F: ("eor", "long"),
    0x50: ("bvc", "rel8"),
    0x54: ("mvn", "move"),
    0x55: ("eor", "dpx"),
    0x58: ("cli", "impl"),
    0x59: ("eor", "absy"),
    0x5A: ("phy", "impl"),
    0x5B: ("tcd", "impl"),
    0x5C: ("jml", "long"),
    0x5D: ("eor", "absx"),
    0x5F: ("eor", "longx"),
    0x60: ("rts", "impl"),
    0x64: ("stz", "dp"),
    0x65: ("adc", "dp"),
    0x66: ("ror", "dp"),
    0x68: ("pla", "impl"),
    0x69: ("adc", "imm_m"),
    0x6A: ("ror", "acc"),
    0x6B: ("rtl", "impl"),
    0x6C: ("jmp", "ind"),
    0x6D: ("adc", "abs"),
    0x6E: ("ror", "abs"),
    0x6F: ("adc", "long"),
    0x70: ("bvs", "rel8"),
    0x71: ("adc", "dpindy"),
    0x74: ("stz", "dpx"),
    0x75: ("adc", "dpx"),
    0x77: ("adc", "dp_long_y"),
    0x78: ("sei", "impl"),
    0x79: ("adc", "absy"),
    0x7A: ("ply", "impl"),
    0x7B: ("tdc", "impl"),
    0x7C: ("jmp", "absxind"),
    0x7D: ("adc", "absx"),
    0x7F: ("adc", "longx"),
    0x80: ("bra", "rel8"),
    0x81: ("sta", "dpxind"),
    0x83: ("sta", "sr"),
    0x84: ("sty", "dp"),
    0x85: ("sta", "dp"),
    0x86: ("stx", "dp"),
    0x87: ("sta", "dp_long"),
    0x88: ("dey", "impl"),
    0x89: ("bit", "imm_m"),
    0x8A: ("txa", "impl"),
    0x8B: ("phb", "impl"),
    0x8C: ("sty", "abs"),
    0x8D: ("sta", "abs"),
    0x8E: ("stx", "abs"),
    0x8F: ("sta", "long"),
    0x90: ("bcc", "rel8"),
    0x91: ("sta", "dpindy"),
    0x92: ("sta", "dpind"),
    0x95: ("sta", "dpx"),
    0x96: ("stx", "dpy"),
    0x97: ("sta", "dp_long_y"),
    0x98: ("tya", "impl"),
    0x99: ("sta", "absy"),
    0x9A: ("txs", "impl"),
    0x9B: ("txy", "impl"),
    0x9C: ("stz", "abs"),
    0x9D: ("sta", "absx"),
    0x9E: ("stz", "absx"),
    0x9F: ("sta", "longx"),
    0xA0: ("ldy", "imm_x"),
    0xA2: ("ldx", "imm_x"),
    0xA4: ("ldy", "dp"),
    0xA5: ("lda", "dp"),
    0xA6: ("ldx", "dp"),
    0xA7: ("lda", "dp_long"),
    0xA8: ("tay", "impl"),
    0xA9: ("lda", "imm_m"),
    0xAA: ("tax", "impl"),
    0xAB: ("plb", "impl"),
    0xAC: ("ldy", "abs"),
    0xAD: ("lda", "abs"),
    0xAE: ("ldx", "abs"),
    0xAF: ("lda", "long"),
    0xB0: ("bcs", "rel8"),
    0xB1: ("lda", "dpindy"),
    0xB2: ("lda", "dpind"),
    0xB4: ("ldy", "dpx"),
    0xB5: ("lda", "dpx"),
    0xB7: ("lda", "dp_long_y"),
    0xB8: ("clv", "impl"),
    0xB9: ("lda", "absy"),
    0xBB: ("tyx", "impl"),
    0xBC: ("ldy", "absx"),
    0xBD: ("lda", "absx"),
    0xBE: ("ldx", "absy"),
    0xBF: ("lda", "longx"),
    0xC0: ("cpy", "imm_x"),
    0xC2: ("rep", "imm8"),
    0xC4: ("cpy", "dp"),
    0xC5: ("cmp", "dp"),
    0xC6: ("dec", "dp"),
    0xC7: ("cmp", "dp_long"),
    0xC8: ("iny", "impl"),
    0xC9: ("cmp", "imm_m"),
    0xCA: ("dex", "impl"),
    0xCC: ("cpy", "abs"),
    0xCD: ("cmp", "abs"),
    0xCE: ("dec", "abs"),
    0xCF: ("cmp", "long"),
    0xD0: ("bne", "rel8"),
    0xD1: ("cmp", "dpindy"),
    0xD5: ("cmp", "dpx"),
    0xD6: ("dec", "dpx"),
    0xD7: ("cmp", "dp_long_y"),
    0xD8: ("cld", "impl"),
    0xD9: ("cmp", "absy"),
    0xDA: ("phx", "impl"),
    0xDC: ("jml", "ind_long"),
    0xDD: ("cmp", "absx"),
    0xDE: ("dec", "absx"),
    0xDF: ("cmp", "longx"),
    0xE0: ("cpx", "imm_x"),
    0xE2: ("sep", "imm8"),
    0xE4: ("cpx", "dp"),
    0xE5: ("sbc", "dp"),
    0xE6: ("inc", "dp"),
    0xE8: ("inx", "impl"),
    0xE9: ("sbc", "imm_m"),
    0xEA: ("nop", "impl"),
    0xEB: ("xba", "impl"),
    0xEC: ("cpx", "abs"),
    0xED: ("sbc", "abs"),
    0xEE: ("inc", "abs"),
    0xEF: ("sbc", "long"),
    0xF0: ("beq", "rel8"),
    0xF4: ("pea", "abs"),
    0xF5: ("sbc", "dpx"),
    0xF7: ("sbc", "dp_long_y"),
    0xF9: ("sbc", "absy"),
    0xFA: ("plx", "impl"),
    0xFB: ("xce", "impl"),
    0xFC: ("jsr", "absxind"),
    0xFD: ("sbc", "absx"),
    0xFE: ("inc", "absx"),
    0xFF: ("sbc", "longx"),
    0x01: ("ora", "dpxind"),
    0x02: ("cop", "imm8"),
    0x04: ("tsb", "dp"),
    0x07: ("ora", "dp_long"),
    0x13: ("ora", "srindy"),
    0x17: ("ora", "dp_long_y"),
    0x19: ("ora", "absy"),
    0x1C: ("trb", "abs"),
    0x1E: ("asl", "absx"),
    0x21: ("and", "dpxind"),
    0x23: ("and", "sr"),
    0x27: ("and", "dp_long"),
    0x31: ("and", "dpindy"),
    0x32: ("and", "dpind"),
    0x33: ("and", "srindy"),
    0x34: ("bit", "dpx"),
    0x36: ("rol", "dpx"),
    0x37: ("and", "dp_long_y"),
    0x3B: ("tsc", "impl"),
    0x3E: ("rol", "absx"),
    0x41: ("eor", "dpxind"),
    0x43: ("eor", "sr"),
    0x44: ("mvp", "move"),
    0x47: ("eor", "dp_long"),
    0x51: ("eor", "dpindy"),
    0x52: ("eor", "dpind"),
    0x53: ("eor", "srindy"),
    0x56: ("lsr", "dpx"),
    0x57: ("eor", "dp_long_y"),
    0x5E: ("lsr", "absx"),
    0x61: ("adc", "dpxind"),
    0x62: ("per", "rel16"),
    0x63: ("adc", "sr"),
    0x67: ("adc", "dp_long"),
    0x72: ("adc", "dpind"),
    0x73: ("adc", "srindy"),
    0x76: ("ror", "dpx"),
    0x7E: ("ror", "absx"),
    0x82: ("brl", "rel16"),
    0x93: ("sta", "srindy"),
    0x94: ("sty", "dpx"),
    0xA1: ("lda", "dpxind"),
    0xA3: ("lda", "sr"),
    0xB3: ("lda", "srindy"),
    0xB6: ("ldx", "dpy"),
    0xBA: ("tsx", "impl"),
    0xC1: ("cmp", "dpxind"),
    0xC3: ("cmp", "sr"),
    0xCB: ("wai", "impl"),
    0xD2: ("cmp", "dpind"),
    0xD3: ("cmp", "srindy"),
    0xD4: ("pei", "dpind"),
    0xDB: ("stp", "impl"),
    0xE1: ("sbc", "dpxind"),
    0xE3: ("sbc", "sr"),
    0xE7: ("sbc", "dp_long"),
    0xF1: ("sbc", "dpindy"),
    0xF2: ("sbc", "dpind"),
    0xF3: ("sbc", "srindy"),
    0xF6: ("inc", "dpx"),
    0xF8: ("sed", "impl"),
}


@dataclass
class CpuState:
    emulation: bool = False
    m8: bool = False
    x8: bool = False
    carry: bool | None = None
    force_m_bits: int | None = None
    force_x_bits: int | None = None

    def enforce_forces(self) -> None:
        if self.force_m_bits == 8:
            self.m8 = True
        elif self.force_m_bits == 16:
            self.m8 = False
        if self.force_x_bits == 8:
            self.x8 = True
        elif self.force_x_bits == 16:
            self.x8 = False

    def summary(self) -> str:
        m_width = f'{8 if self.m8 else 16}{"*" if self.force_m_bits is not None else ""}'
        x_width = f'{8 if self.x8 else 16}{"*" if self.force_x_bits is not None else ""}'
        carry = '?' if self.carry is None else ('1' if self.carry else '0')
        return f'E{1 if self.emulation else 0} M{m_width} X{x_width} C{carry}'


@dataclass
class DecodedInstruction:
    bank: int
    address: int
    size: int
    raw: bytes
    text: str
    annotation: str | None
    state_before: str
    state_after: str


BRANCHES = {'bra', 'bcc', 'bcs', 'beq', 'bmi', 'bne', 'bpl', 'bvc', 'bvs'}
CONTROL_FLOW = {'jsr', 'jsl', 'jmp', 'jml'}


def parse_cpu_address(text: str) -> tuple[int, int]:
    cleaned = text.strip().upper()
    if ':' not in cleaned:
        raise argparse.ArgumentTypeError('address must look like C1:244C')
    bank_text, addr_text = cleaned.split(':', 1)
    if len(bank_text) != 2 or len(addr_text) not in {4, 5}:
        raise argparse.ArgumentTypeError('address must look like C1:244C')
    try:
        bank = int(bank_text, 16)
        address = int(addr_text, 16)
    except ValueError as exc:
        raise argparse.ArgumentTypeError('address must look like C1:244C') from exc
    if address > 0x10000 or (len(addr_text) == 5 and address != 0x10000):
        raise argparse.ArgumentTypeError('address must look like C1:244C')
    return bank, address


def read_u16(data: bytes, offset: int) -> int:
    return data[offset] | (data[offset + 1] << 8)


def read_u24(data: bytes, offset: int) -> int:
    return data[offset] | (data[offset + 1] << 8) | (data[offset + 2] << 16)


def signed8(value: int) -> int:
    return value - 0x100 if value & 0x80 else value


def signed16(value: int) -> int:
    return value - 0x10000 if value & 0x8000 else value


def operand_size(mode: str, state: CpuState) -> int:
    if mode in {'impl', 'acc'}:
        return 0
    if mode in {'imm8', 'dp', 'dpx', 'dpy', 'dpind', 'dpxind', 'dp_long', 'dp_long_y', 'rel8', 'sr', 'srindy'}:
        return 1
    if mode in {'abs', 'absx', 'absy', 'ind', 'ind_long', 'absxind', 'rel16'}:
        return 2
    if mode in {'long', 'longx'}:
        return 3
    if mode == 'move':
        return 2
    if mode == 'imm_m':
        return 1 if state.m8 else 2
    if mode == 'imm_x':
        return 1 if state.x8 else 2
    if mode == 'dpindy':
        return 1
    raise ValueError(f'Unsupported addressing mode: {mode}')


def format_long(long_address: int) -> str:
    return f'{(long_address >> 16) & 0xFF:02X}:{long_address & 0xFFFF:04X}'


def format_operand(bank: int, address: int, mnemonic: str, mode: str, operand: bytes) -> tuple[str, str | None]:
    next_address = (address + 1 + len(operand)) & 0xFFFF
    if mode == 'impl':
        return '', None
    if mode == 'acc':
        return 'A', None
    if mode == 'imm8':
        return f'#$%02X' % operand[0], None
    if mode == 'imm_m' or mode == 'imm_x':
        value = operand[0] if len(operand) == 1 else read_u16(operand, 0)
        width = 2 if len(operand) == 1 else 4
        return f'#$%0{width}X' % value, None
    if mode == 'dp':
        return f'$%02X' % operand[0], 'direct page'
    if mode == 'dpx':
        return f'$%02X,X' % operand[0], 'direct page,X'
    if mode == 'dpy':
        return f'$%02X,Y' % operand[0], 'direct page,Y'
    if mode == 'dpind':
        return f'($%02X)' % operand[0], 'direct page indirect'
    if mode == 'dpxind':
        return f'($%02X,X)' % operand[0], 'direct page,X indirect'
    if mode == 'dpindy':
        return f'($%02X),Y' % operand[0], 'direct page indirect,Y'
    if mode == 'sr':
        return f'$%02X,S' % operand[0], 'stack relative'
    if mode == 'srindy':
        return f'($%02X,S),Y' % operand[0], 'stack relative indirect,Y'
    if mode == 'dp_long':
        return f'[$%02X]' % operand[0], 'direct page long'
    if mode == 'dp_long_y':
        return f'[$%02X],Y' % operand[0], 'direct page long,Y'
    if mode == 'abs':
        target = read_u16(operand, 0)
        if mnemonic in CONTROL_FLOW:
            return f'${target:04X}', f'-> {bank:02X}:{target:04X}'
        return f'${target:04X}', 'absolute'
    if mode == 'absx':
        target = read_u16(operand, 0)
        return f'${target:04X},X', 'absolute,X'
    if mode == 'absy':
        target = read_u16(operand, 0)
        return f'${target:04X},Y', 'absolute,Y'
    if mode == 'ind':
        target = read_u16(operand, 0)
        return f'(${target:04X})', 'indirect'
    if mode == 'ind_long':
        target = read_u16(operand, 0)
        return f'[{target:04X}]', 'indirect long'
    if mode == 'absxind':
        target = read_u16(operand, 0)
        return f'(${target:04X},X)', 'absolute,X indirect'
    if mode == 'long':
        target = read_u24(operand, 0)
        if mnemonic in CONTROL_FLOW:
            return f'${target:06X}', f'-> {format_long(target)}'
        return f'${target:06X}', f'long {format_long(target)}'
    if mode == 'longx':
        target = read_u24(operand, 0)
        return f'${target:06X},X', f'long,X {format_long(target)}'
    if mode == 'rel8':
        delta = signed8(operand[0])
        target = (next_address + delta) & 0xFFFF
        return f'${target:04X}', f'-> {bank:02X}:{target:04X}'
    if mode == 'rel16':
        delta = signed16(read_u16(operand, 0))
        target = (next_address + delta) & 0xFFFF
        return f'${target:04X}', f'-> {bank:02X}:{target:04X}'
    if mode == 'move':
        dst = operand[0]
        src = operand[1]
        return f'${dst:02X},${src:02X}', f'move src={src:02X} dst={dst:02X}'
    raise ValueError(f'Unsupported formatting mode: {mode}')


def apply_state_update(mnemonic: str, operand: bytes, state: CpuState) -> None:
    if mnemonic == 'rep' and operand:
        mask = operand[0]
        if mask & 0x20:
            state.m8 = False
        if mask & 0x10:
            state.x8 = False
        if mask & 0x01:
            state.carry = False
    elif mnemonic == 'sep' and operand:
        mask = operand[0]
        if mask & 0x20:
            state.m8 = True
        if mask & 0x10:
            state.x8 = True
        if mask & 0x01:
            state.carry = True
    elif mnemonic == 'xce':
        if state.carry is True:
            state.emulation = True
            state.m8 = True
            state.x8 = True
        elif state.carry is False:
            state.emulation = False
    elif mnemonic == 'clc':
        state.carry = False
    elif mnemonic == 'sec':
        state.carry = True
    state.enforce_forces()


def decode_instruction(rom: bytes, bank: int, address: int, state: CpuState) -> DecodedInstruction:
    offset = hirom_to_file_offset(bank, address, len(rom))
    if offset is None:
        raise ValueError(f'Address {bank:02X}:{address:04X} is not a valid ROM location')
    opcode = rom[offset]
    if opcode not in OPCODES:
        raw = rom[offset:offset + 1]
        return DecodedInstruction(bank, address, 1, raw, f'.db ${opcode:02X}', 'unknown opcode', state.summary(), state.summary())
    mnemonic, mode = OPCODES[opcode]
    before = state.summary()
    size = 1 + operand_size(mode, state)
    raw = rom[offset:offset + size]
    operand = raw[1:]
    operand_text, annotation = format_operand(bank, address, mnemonic, mode, operand)
    text = mnemonic if not operand_text else f'{mnemonic} {operand_text}'
    apply_state_update(mnemonic, operand, state)
    after = state.summary()
    if after != before and mnemonic in {'rep', 'sep', 'xce', 'clc', 'sec'}:
        annotation = f'{annotation}; {after}' if annotation else after
    return DecodedInstruction(bank, address, size, raw, text, annotation, before, after)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Decode and annotate a short 65816 ROM snippet by CPU address.')
    parser.add_argument('start', type=parse_cpu_address, help='start CPU address like C1:244C')
    parser.add_argument('--count', type=int, default=24, help='instruction count to decode (default: 24)')
    parser.add_argument('--rom', help='explicit ROM path')
    parser.add_argument('--m8', action='store_true', help='start with 8-bit accumulator')
    parser.add_argument('--x8', action='store_true', help='start with 8-bit index registers')
    parser.add_argument('--force-m8', action='store_true', help='lock the accumulator width to 8-bit even across REP/SEP/XCE')
    parser.add_argument('--force-m16', action='store_true', help='lock the accumulator width to 16-bit even across REP/SEP/XCE')
    parser.add_argument('--force-x8', action='store_true', help='lock the index width to 8-bit even across REP/SEP/XCE')
    parser.add_argument('--force-x16', action='store_true', help='lock the index width to 16-bit even across REP/SEP/XCE')
    parser.add_argument('--emulation', action='store_true', help='start in emulation mode')
    parser.add_argument('--show-state', action='store_true', help='include CPU state before every instruction')
    return parser


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
    state = CpuState(
        emulation=args.emulation,
        m8=args.m8 or args.emulation,
        x8=args.x8 or args.emulation,
        carry=None,
        force_m_bits=force_m_bits,
        force_x_bits=force_x_bits,
    )
    state.enforce_forces()

    print(f'ROM: {rom_path}')
    print(f'Start: {bank:02X}:{address:04X}')
    print(f'Initial state: {state.summary()}')
    print()

    current = address
    for _ in range(args.count):
        inst = decode_instruction(rom, bank, current, state)
        raw = ' '.join(f'{b:02X}' for b in inst.raw)
        parts = [f'{inst.bank:02X}:{inst.address:04X}', raw.ljust(15), inst.text]
        if args.show_state:
            parts.append(f'[{inst.state_before}]')
        line = '  '.join(parts)
        if inst.annotation:
            line += f'  ; {inst.annotation}'
        print(line)
        current = (current + inst.size) & 0xFFFF

    return 0


if __name__ == '__main__':
    raise SystemExit(main())

