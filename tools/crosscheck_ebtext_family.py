from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path
import sys

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import find_ebtext_command as finder
import rom_tools
import summarize_dispatch


def parse_hex_byte(text: str) -> int:
    text = text.strip().upper()
    if text.startswith('0X'):
        text = text[2:]
    value = int(text, 16)
    if not (0 <= value <= 0xFF):
        raise ValueError(f'Byte out of range: {text}')
    return value


def main() -> int:
    parser = argparse.ArgumentParser(
        description='Cross-check exact parsed EarthBound text-command hits against a live local dispatcher.'
    )
    parser.add_argument('opcode', help='Top-level command byte, for example 1A')
    parser.add_argument('dispatcher', help='Live dispatcher CPU address like C1:7B56')
    parser.add_argument('--rom', help='Optional explicit ROM path')
    parser.add_argument('--yml', default='refs/ebsrc-main/ebsrc-main/earthbound.yml', help='YAML file with text_data segment offsets')
    parser.add_argument('--max-subcommands', type=int, default=64, help='Maximum parsed subcommands to scan')
    parser.add_argument('--max-cases', type=int, default=64, help='Maximum dispatcher cases to scan')
    parser.add_argument('--show-zero', action='store_true', help='Include subcommands with neither parsed hits nor runtime cases')
    parser.add_argument('--limit', type=int, default=2, help='Maximum sample hits per parsed subcommand')
    args = parser.parse_args()

    rom_path = rom_tools.find_rom(args.rom)
    rom = rom_tools.load_rom(rom_path)
    yml_path = Path(args.yml)
    segments = finder.load_segments(yml_path)
    opcode = parse_hex_byte(args.opcode)
    bank, addr = summarize_dispatch.parse_cpu_address(args.dispatcher)

    cases, guard, default_target, default_kind, default_value = summarize_dispatch.summarize_dispatch(
        rom, bank, addr, args.max_cases
    )
    runtime_case_map = {entry.value: entry for entry in cases}

    print(f'ROM: {rom_path}')
    print(f'YML: {yml_path}')
    print(f'Opcode: 0x{opcode:02X} ({finder.command_name_for(opcode, None)})')
    print(f'Dispatcher: {args.dispatcher.upper()}')
    if guard is not None:
        print(
            f'Guard: cmp #0x{guard.value:04X} ; {guard.op} '
            f'{summarize_dispatch.fmt_cpu(bank, guard.branch_target)} ; '
            f'default {summarize_dispatch.fmt_cpu(bank, guard.default_target)}'
        )
    print()

    all_subs = set(runtime_case_map)
    parsed_hits_by_sub: dict[int, list[tuple[str, int, str]]] = {}
    parsed_segment_counts: dict[int, dict[str, int]] = {}
    for sub in range(args.max_subcommands):
        hits = finder.find_hits(rom, segments, opcode, sub)
        if hits:
            parsed_hits_by_sub[sub] = hits
            by_segment: dict[str, int] = defaultdict(int)
            for seg_name, _, _ in hits:
                by_segment[seg_name] += 1
            parsed_segment_counts[sub] = dict(sorted(by_segment.items(), key=lambda item: (-item[1], item[0])))
            all_subs.add(sub)

    rows = sorted(all_subs)
    for sub in rows:
        runtime = runtime_case_map.get(sub)
        hits = parsed_hits_by_sub.get(sub, [])
        if not args.show_zero and runtime is None and not hits:
            continue

        if runtime is not None and hits:
            status = 'both'
        elif runtime is not None:
            status = 'runtime_only'
        elif hits:
            status = 'parsed_only'
        else:
            status = 'none'

        name = finder.command_name_for(opcode, sub)
        print(f'0x{sub:02X}  {status:12}  {name}')
        if runtime is not None:
            line = f'  runtime: {summarize_dispatch.fmt_cpu(bank, runtime.target)}'
            if runtime.target_kind == 'callback':
                line += f'  callback=0x{runtime.target_value:04X}'
            elif runtime.target_kind == 'leaf':
                line += f'  leaf=0x{runtime.target_value:04X}'
            print(line)
        if hits:
            segments_text = ', '.join(
                f'{seg}:{count}' for seg, count in list(parsed_segment_counts[sub].items())[:4]
            )
            print(f'  parsed: hits={len(hits)}  segments={segments_text}')
            for seg_name, address, text in hits[:args.limit]:
                print(f'    sample: {finder.ebscript.fmt_addr(address)}  {seg_name}  {text}')
        print()

    if default_target is not None:
        line = f'default -> {summarize_dispatch.fmt_cpu(bank, default_target)}'
        if default_kind == 'callback':
            line += f'  callback=0x{default_value:04X}'
        elif default_kind == 'leaf':
            line += f'  leaf=0x{default_value:04X}'
        print(line)

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
