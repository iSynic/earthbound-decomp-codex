from __future__ import annotations

import argparse
from pathlib import Path

from rom_tools import find_rom, load_rom

SETTER_PATTERN = bytes.fromhex('22 1C 85 C0')
RESET_PATTERN = bytes.fromhex('22 22 85 C0')


def canonical_address(file_offset: int) -> str:
    bank = 0xC0 + (file_offset // 0x10000)
    address = file_offset % 0x10000
    return f'{bank:02X}:{address:04X}'


def find_all(data: bytes, pattern: bytes) -> list[int]:
    offsets: list[int] = []
    start = 0
    while True:
        idx = data.find(pattern, start)
        if idx == -1:
            return offsets
        offsets.append(idx)
        start = idx + 1


def build_report(rom_path: Path) -> str:
    data = load_rom(rom_path)
    lines = [
        '# Frame Callback Cross-References',
        '',
        f'- ROM: `{rom_path}`',
        '- Callback dispatcher: `C0:8518` (`JMP ($0020)`)',
        '- Callback setter: `C0:851C`',
        '- Default callback stub: `C0:851B`',
        '- Default-reset helper: `C0:8522`',
        '',
        '## Direct Callback Installs',
        '',
        '| Call Site | Target | Evidence |',
        '| --- | --- | --- |',
    ]

    for call_offset in find_all(data, SETTER_PATTERN):
        target_text = 'unknown'
        evidence = 'no immediate 16-bit load found'
        if call_offset >= 3 and data[call_offset - 3] == 0xA9:
            target = data[call_offset - 2] | (data[call_offset - 1] << 8)
            target_text = f'C0:{target:04X}'
            evidence = f'LDA #${target:04X} ; JSL $C0851C'
        lines.append(
            f'| `{canonical_address(call_offset)}` | `{target_text}` | `{evidence}` |'
        )

    lines.extend([
        '',
        '## Explicit Resets To Default Callback',
        '',
        '| Call Site | Behavior |',
        '| --- | --- |',
    ])

    for call_offset in find_all(data, RESET_PATTERN):
        lines.append(
            f'| `{canonical_address(call_offset)}` | `JSL C0:8522`, which writes `#$851B` to `$20/$21` |'
        )

    lines.extend([
        '',
        '## Observations',
        '',
        '- All discovered installed callback targets are `C0:` addresses, which matches the 16-bit indirect `JMP ($0020)` dispatcher in bank `C0`.',
        '- `C0:B6C8`, `C4:F6FE`, and `EF:E2C7` all install `C0:DC4E`.',
        '- `C4:F592` installs `C0:F41E`.',
        '- `C4:F673` explicitly restores the default callback stub through `C0:8522`.',
        '- `NMI_FinalizeFrame` runs the callback with `DBR=7E` and `DP=0200` immediately before returning from interrupt.',
    ])

    return '\n'.join(lines) + '\n'


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Scan the ROM for frame callback install and reset call sites.'
    )
    parser.add_argument('--rom', help='Optional ROM path override.')
    parser.add_argument('--output', help='Optional Markdown output path.')
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    rom_path = find_rom(args.rom)
    report = build_report(rom_path)
    if args.output:
        Path(args.output).write_text(report, encoding='ascii')
    print(report)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

