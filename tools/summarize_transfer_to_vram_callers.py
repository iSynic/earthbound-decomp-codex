from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from dataclasses import dataclass

from rom_tools import find_rom, load_rom


def parse_cpu_address(text: str) -> tuple[int, int]:
    cleaned = text.strip().upper()
    if ":" not in cleaned:
        raise argparse.ArgumentTypeError("address must look like C0:8616")
    bank_text, addr_text = cleaned.split(":", 1)
    if len(bank_text) != 2 or len(addr_text) != 4:
        raise argparse.ArgumentTypeError("address must look like C0:8616")
    return int(bank_text, 16), int(addr_text, 16)


def file_to_cpu(offset: int) -> tuple[int, int]:
    bank = 0xC0 + (offset // 0x10000)
    addr = offset % 0x10000
    return bank, addr


def format_cpu(bank: int, addr: int) -> str:
    return f"{bank:02X}:{addr:04X}"


@dataclass(frozen=True)
class CallerSummary:
    call_bank: int
    call_addr: int
    immediates: tuple[int, ...]
    adc_immediates: tuple[int, ...]
    lda_immediates: tuple[int, ...]
    source_markers: tuple[str, ...]
    dp_stores: tuple[str, ...]


def scan_callers(data: bytes, target_bytes: bytes) -> list[int]:
    hits: list[int] = []
    start = 0
    while True:
        idx = data.find(target_bytes, start)
        if idx == -1:
            break
        if idx >= 1 and data[idx - 1] == 0x22:
            hits.append(idx - 1)
        start = idx + 1
    return hits


def collect_immediates(window: bytes) -> tuple[list[int], list[int], list[int]]:
    alls: list[int] = []
    adcs: list[int] = []
    ldas: list[int] = []
    for i in range(len(window) - 2):
        opcode = window[i]
        if opcode not in (0x69, 0xA9):
            continue
        value = window[i + 1] | (window[i + 2] << 8)
        alls.append(value)
        if opcode == 0x69:
            adcs.append(value)
        else:
            ldas.append(value)
    return alls, adcs, ldas


def collect_markers(window: bytes) -> tuple[list[str], list[str]]:
    source_markers: list[str] = []
    dp_stores: list[str] = []
    for i in range(len(window) - 1):
        op = window[i]
        lo = window[i + 1]
        if op in (0x85, 0xA5, 0xA7, 0x86, 0x84) and lo in (0x91, 0x92, 0x94, 0x96, 0x97, 0x99):
            dp_stores.append(f"{op:02X}->{lo:02X}")
    for i in range(len(window) - 2):
        op = window[i]
        lo = window[i + 1]
        hi = window[i + 2]
        value = lo | (hi << 8)
        if op == 0xA9 and value in (0x0BE8, 0x2F8C, 0x3800, 0x3C00, 0x5800, 0x5C00):
            source_markers.append(f"LDA#{value:04X}")
        if op == 0x69 and 0x4000 <= value <= 0x5FFF:
            source_markers.append(f"ADC#{value:04X}")
        if op == 0x8D and value in (0x0092, 0x0094, 0x0096, 0x0097):
            dp_stores.append(f"8D->{value:04X}")
    return source_markers, dp_stores


def summarize_caller(data: bytes, caller_file: int, window_size: int) -> CallerSummary:
    start = max(0, caller_file - window_size)
    window = data[start:caller_file]
    immediates, adc_immediates, lda_immediates = collect_immediates(window)
    source_markers, dp_stores = collect_markers(window)
    bank, addr = file_to_cpu(caller_file)
    return CallerSummary(
        call_bank=bank,
        call_addr=addr,
        immediates=tuple(sorted(set(immediates))),
        adc_immediates=tuple(sorted(set(adc_immediates))),
        lda_immediates=tuple(sorted(set(lda_immediates))),
        source_markers=tuple(sorted(set(source_markers))),
        dp_stores=tuple(sorted(set(dp_stores))),
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Summarize direct JSL callers of TRANSFER_TO_VRAM-style targets by nearby immediates."
    )
    parser.add_argument("target", type=parse_cpu_address, help="callee address, e.g. C0:8616")
    parser.add_argument("--bank", type=lambda t: int(t, 16), help="only include callers from one bank, e.g. C0")
    parser.add_argument("--window", type=int, default=48, help="bytes before each call to scan")
    parser.add_argument("--limit", type=int, default=80, help="max callers to print")
    args = parser.parse_args()

    rom_path = find_rom()
    data = load_rom(rom_path)
    bank, addr = args.target
    target_bytes = bytes((addr & 0xFF, (addr >> 8) & 0xFF, bank))
    summaries = [summarize_caller(data, caller, args.window) for caller in scan_callers(data, target_bytes)]
    if args.bank is not None:
        summaries = [s for s in summaries if s.call_bank == args.bank]

    print(f"ROM: {rom_path}")
    print(f"Target: {format_cpu(bank, addr)}")
    print(f"Callers found: {len(summaries)}")
    print()

    adc_counter: Counter[int] = Counter()
    lda_counter: Counter[int] = Counter()
    marker_counter: Counter[str] = Counter()
    for summary in summaries:
        adc_counter.update(summary.adc_immediates)
        lda_counter.update(summary.lda_immediates)
        marker_counter.update(summary.source_markers)

    if adc_counter:
        print("Most common nearby ADC immediates:")
        for value, count in adc_counter.most_common(12):
            print(f"  #{value:04X}: {count}")
        print()

    if lda_counter:
        print("Most common nearby LDA immediates:")
        for value, count in lda_counter.most_common(12):
            print(f"  #{value:04X}: {count}")
        print()

    if marker_counter:
        print("Most common source/destination markers:")
        for marker, count in marker_counter.most_common(16):
            print(f"  {marker}: {count}")
        print()

    grouped: dict[tuple[tuple[int, ...], tuple[str, ...]], list[CallerSummary]] = defaultdict(list)
    for summary in summaries:
        grouped[(summary.adc_immediates, summary.source_markers)].append(summary)

    print("Caller clusters:")
    ordered_groups = sorted(grouped.items(), key=lambda item: (-len(item[1]), item[0]))
    for (adc_imms, markers), group in ordered_groups[:20]:
        adc_text = ", ".join(f"#{value:04X}" for value in adc_imms) if adc_imms else "(none)"
        marker_text = ", ".join(markers) if markers else "(none)"
        callers_text = ", ".join(format_cpu(s.call_bank, s.call_addr) for s in group[:8])
        if len(group) > 8:
            callers_text += ", ..."
        print(f"  {len(group):>2} callers | ADC {adc_text} | markers {marker_text}")
        print(f"     {callers_text}")
    print()

    print("Detailed callers:")
    for summary in summaries[: args.limit]:
        adc_text = ", ".join(f"#{value:04X}" for value in summary.adc_immediates) if summary.adc_immediates else "-"
        lda_text = ", ".join(f"#{value:04X}" for value in summary.lda_immediates[:6]) if summary.lda_immediates else "-"
        marker_text = ", ".join(summary.source_markers) if summary.source_markers else "-"
        store_text = ", ".join(summary.dp_stores) if summary.dp_stores else "-"
        print(
            f"  {format_cpu(summary.call_bank, summary.call_addr)} | "
            f"ADC {adc_text} | LDA {lda_text} | markers {marker_text} | stores {store_text}"
        )


if __name__ == "__main__":
    main()
