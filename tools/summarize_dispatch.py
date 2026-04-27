from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import sys

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import rom_tools


@dataclass
class CaseEntry:
    value: int
    cmp_addr: int
    target: int
    target_kind: str | None = None
    target_value: int | None = None


@dataclass
class GuardInfo:
    value: int
    op: str
    branch_target: int
    default_target: int


def parse_cpu_address(text: str) -> tuple[int, int]:
    text = text.strip().upper()
    if ':' not in text:
        raise ValueError(f"Expected BANK:ADDR format, got {text!r}")
    bank_s, addr_s = text.split(':', 1)
    bank = int(bank_s, 16)
    addr = int(addr_s, 16)
    if not (0 <= bank <= 0xFF and 0 <= addr <= 0xFFFF):
        raise ValueError(f"Out-of-range CPU address: {text}")
    return bank, addr


def fmt_cpu(bank: int, addr: int) -> str:
    return f"{bank:02X}:{addr:04X}"


def read_u8(data: bytes, offset: int) -> int:
    return data[offset]


def read_u16(data: bytes, offset: int) -> int:
    return data[offset] | (data[offset + 1] << 8)


def rel8_target(addr: int, rel: int) -> int:
    if rel & 0x80:
        rel -= 0x100
    return (addr + 2 + rel) & 0xFFFF


def cpu_to_offset(data: bytes, bank: int, addr: int) -> int:
    off = rom_tools.hirom_to_file_offset(bank, addr, len(data))
    if off is None:
        raise ValueError(f"Address {fmt_cpu(bank, addr)} is not a ROM-backed HiROM address")
    return off


def inspect_target(data: bytes, bank: int, addr: int) -> tuple[str | None, int | None]:
    off = cpu_to_offset(data, bank, addr)
    blob = data[off:off + 8]
    if len(blob) < 6:
        return None, None

    if blob[:6] == bytes([0xA0, blob[1], blob[2], 0x84, 0x1E, 0x4C]):
        return "callback", read_u16(blob, 1)

    if blob[0] == 0xA9:
        return "leaf", read_u16(blob, 1)

    return None, None


def describe_target(data: bytes, bank: int, target: int) -> tuple[str | None, int | None]:
    kind, value = inspect_target(data, bank, target)
    return kind, value


def detect_zero_case(data: bytes, bank: int, off: int, addr: int, first_cmp: int) -> CaseEntry | None:
    prefix = data[off:first_cmp]
    for idx in range(len(prefix) - 2):
        if prefix[idx] != 0x8A:
            continue
        here = addr + idx
        op = prefix[idx + 1]
        if op == 0xF0:
            target = rel8_target(here + 1, prefix[idx + 2])
            kind, value = describe_target(data, bank, target)
            return CaseEntry(0, here & 0xFFFF, target, kind, value)
        if op == 0xD0 and idx + 5 < len(prefix) and prefix[idx + 2] == 0x03 and prefix[idx + 3] == 0x4C:
            target = prefix[idx + 4] | (prefix[idx + 5] << 8)
            kind, value = describe_target(data, bank, target)
            return CaseEntry(0, here & 0xFFFF, target, kind, value)
    return None


def detect_guard(data: bytes, bank: int, cursor: int, addr: int, scan_limit: int) -> tuple[int, GuardInfo | None, int | None]:
    if cursor + 6 > len(data):
        return cursor, None, None
    if read_u8(data, cursor) != 0xC9:
        return cursor, None, None
    branch_op = read_u8(data, cursor + 3)
    if branch_op not in {0x90, 0xB0, 0x10, 0x30}:
        return cursor, None, None
    if read_u8(data, cursor + 5) != 0x4C:
        return cursor, None, None

    cmp_value = read_u16(data, cursor + 1)
    branch_addr = addr + (cursor - cpu_to_offset(data, bank, addr)) + 3
    branch_target = rel8_target(branch_addr, read_u8(data, cursor + 4))
    default_target = read_u16(data, cursor + 6)
    branch_off = cpu_to_offset(data, bank, branch_target)
    if not (cursor < branch_off < scan_limit):
        return cursor, None, None

    op_name = {0x90: 'bcc', 0xB0: 'bcs', 0x10: 'bpl', 0x30: 'bmi'}[branch_op]
    return branch_off, GuardInfo(cmp_value, op_name, branch_target, default_target), default_target


def summarize_dispatch(data: bytes, bank: int, addr: int, max_cases: int) -> tuple[list[CaseEntry], GuardInfo | None, int | None, str | None, int | None]:
    off = cpu_to_offset(data, bank, addr)
    cases: list[CaseEntry] = []
    default_target: int | None = None
    default_kind: str | None = None
    default_value: int | None = None
    guard: GuardInfo | None = None

    scan_limit = min(off + 0x120, len(data) - 8)
    first_cmp = off
    while first_cmp < scan_limit and read_u8(data, first_cmp) != 0xC9:
        first_cmp += 1
    if first_cmp >= scan_limit:
        return cases, None, None, None, None

    zero_case = detect_zero_case(data, bank, off, addr, first_cmp)
    if zero_case is not None:
        cases.append(zero_case)

    cursor, guard, guard_default = detect_guard(data, bank, first_cmp, addr, scan_limit)
    if guard is None:
        cursor = first_cmp
    else:
        default_target = guard_default
        default_kind, default_value = describe_target(data, bank, default_target)
        while cursor < scan_limit and read_u8(data, cursor) != 0xC9:
            cursor += 1

    consumed = len(cases)
    base_off = off
    while consumed < max_cases and cursor + 5 <= len(data):
        op = read_u8(data, cursor)
        if op != 0xC9:
            break
        value = read_u16(data, cursor + 1)
        branch_op = read_u8(data, cursor + 3)
        target: int | None = None
        step = 0

        if branch_op == 0xF0:
            cmp_addr = (addr + (cursor - base_off)) & 0xFFFF
            target = rel8_target(cmp_addr + 3, read_u8(data, cursor + 4))
            step = 5
        elif branch_op == 0xD0 and cursor + 8 <= len(data) and read_u8(data, cursor + 5) == 0x4C:
            target = read_u16(data, cursor + 6)
            step = 8
        else:
            break

        kind, kind_value = describe_target(data, bank, target)
        cases.append(CaseEntry(value, (addr + (cursor - base_off)) & 0xFFFF, target, kind, kind_value))
        cursor += step
        consumed += 1

    if cursor + 2 < len(data):
        op = read_u8(data, cursor)
        if op == 0x4C:
            default_target = read_u16(data, cursor + 1)
            default_kind, default_value = describe_target(data, bank, default_target)
        elif op == 0x80:
            default_target = rel8_target((addr + (cursor - base_off)) & 0xFFFF, read_u8(data, cursor + 1))
            default_kind, default_value = describe_target(data, bank, default_target)

    return cases, guard, default_target, default_kind, default_value


def main() -> int:
    parser = argparse.ArgumentParser(description="Summarize simple 65816 dispatch ladders in the ROM.")
    parser.add_argument("address", help="CPU address like C1:890E")
    parser.add_argument("--rom", help="Path to ROM file")
    parser.add_argument("--max-cases", type=int, default=64, help="Maximum number of cases to scan")
    args = parser.parse_args()

    rom_path = rom_tools.find_rom(args.rom)
    data = rom_tools.load_rom(rom_path)
    bank, addr = parse_cpu_address(args.address)
    cases, guard, default_target, default_kind, default_value = summarize_dispatch(data, bank, addr, args.max_cases)

    print(f"ROM: {rom_path}")
    print(f"Dispatch start: {fmt_cpu(bank, addr)}")
    if guard is not None:
        print(
            f"Guard: cmp #0x{guard.value:04X} ; {guard.op} {fmt_cpu(bank, guard.branch_target)} ; "
            f"default {fmt_cpu(bank, guard.default_target)}"
        )
    if not cases:
        print("No dispatch cases recognized.")
        return 1

    print(f"Cases: {len(cases)}")
    for entry in cases:
        line = f"  case 0x{entry.value:04X} @ {fmt_cpu(bank, entry.cmp_addr)} -> {fmt_cpu(bank, entry.target)}"
        if entry.target_kind == "callback":
            line += f"  (callback low word 0x{entry.target_value:04X})"
        elif entry.target_kind == "leaf":
            line += f"  (leaf low word 0x{entry.target_value:04X})"
        print(line)

    if default_target is not None:
        line = f"  default -> {fmt_cpu(bank, default_target)}"
        if default_kind == "callback":
            line += f"  (callback low word 0x{default_value:04X})"
        elif default_kind == "leaf":
            line += f"  (leaf low word 0x{default_value:04X})"
        print(line)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
