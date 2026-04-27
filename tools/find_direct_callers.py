from __future__ import annotations

import argparse
from pathlib import Path
import re

BANKS_DIR = Path('build/split/banks')


def parse_target(text: str) -> tuple[int, int]:
    text = text.strip().upper()
    m = re.fullmatch(r'([0-9A-F]{2}):([0-9A-F]{4})', text)
    if m:
        return int(m.group(1), 16), int(m.group(2), 16)
    m = re.fullmatch(r'([0-9A-F]{6})', text)
    if m:
        value = int(m.group(1), 16)
        return (value >> 16) & 0xFF, value & 0xFFFF
    raise argparse.ArgumentTypeError('target must look like C0:DBE6 or C0DBE6')


def scan_calls(bank_path: Path, target_bank: int, target_addr: int) -> list[tuple[int, str]]:
    data = bank_path.read_bytes()
    refs: list[tuple[int, str]] = []
    caller_bank = int(bank_path.stem.split('_')[1], 16)

    for i in range(len(data) - 3):
        if data[i] == 0x22 and data[i + 1] == (target_addr & 0xFF) and data[i + 2] == ((target_addr >> 8) & 0xFF) and data[i + 3] == target_bank:
            refs.append((i, 'JSL'))

    if caller_bank == target_bank:
        for i in range(len(data) - 2):
            if data[i] == 0x20 and data[i + 1] == (target_addr & 0xFF) and data[i + 2] == ((target_addr >> 8) & 0xFF):
                refs.append((i, 'JSR'))

    refs.sort()
    return refs


def render_markdown(target_bank: int, target_addr: int, results: dict[str, list[tuple[int, str]]]) -> str:
    lines = [
        f'# Direct Callers for {target_bank:02X}:{target_addr:04X}',
        '',
        'This report scans split banks for direct `JSL` and same-bank `JSR` references to the target routine.',
        '',
    ]

    total = sum(len(entries) for entries in results.values())
    lines.append(f'- Total direct call sites found: `{total}`')
    lines.append('')

    for bank_name in sorted(results):
        entries = results[bank_name]
        lines.append(f'## {bank_name}')
        lines.append('')
        for addr, kind in entries:
            lines.append(f'- `{kind}` at `{bank_name}:{addr:04X}`')
        lines.append('')

    return '\n'.join(lines).rstrip() + '\n'


def main() -> int:
    parser = argparse.ArgumentParser(description='Scan split banks for direct callers of an SNES routine.')
    parser.add_argument('target', type=parse_target, help='Target routine, for example C0:DBE6 or C0DBE6')
    parser.add_argument('--banks-dir', default=str(BANKS_DIR), help='Directory containing split bank_XX.bin files')
    parser.add_argument('--output', help='Optional Markdown output path')
    args = parser.parse_args()

    target_bank, target_addr = args.target
    banks_dir = Path(args.banks_dir)

    results: dict[str, list[tuple[int, str]]] = {}
    for bank_path in sorted(banks_dir.glob('bank_*.bin')):
        refs = scan_calls(bank_path, target_bank, target_addr)
        if refs:
            bank_name = bank_path.stem.split('_')[1]
            results[bank_name] = refs

    markdown = render_markdown(target_bank, target_addr, results)
    if args.output:
        Path(args.output).write_text(markdown, encoding='ascii')
    print(markdown)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
