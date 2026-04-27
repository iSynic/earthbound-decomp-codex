#!/usr/bin/env python3
"""Search quarantined reference trees for address-shaped symbol mentions."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REF_DIRS = [
    Path('refs/ebsrc-main/ebsrc-main'),
    Path('refs/earthbound-disasm-legacy'),
    Path('refs/eb-decompile-4ef92'),
]
TEXT_SUFFIXES = {
    '.asm', '.inc', '.cfg', '.txt', '.md', '.yml', '.yaml', '.ccs', '.json', '.py', '.csv', '.toml'
}
SKIP_DIRS = {'.git', '__pycache__', 'build'}


def normalize_patterns(raw: str) -> list[str]:
    raw = raw.strip().upper()
    patterns: list[str] = []
    if ':' in raw:
        bank, off = raw.split(':', 1)
        bank = bank.zfill(2)
        off = off.zfill(4)
        flat = f'{bank}{off}'
        patterns.extend([
            raw,
            flat,
            f'UNKNOWN_{flat}',
            f'UNKNOWN_{flat}',
            f'UNKNOWN_${flat}',
            f'CODE_{flat}',
            f'DATA_{flat}',
        ])
    else:
        raw = raw.removeprefix('$')
        flat = raw.zfill(6)
        patterns.extend([
            flat,
            f'UNKNOWN_{flat}',
            f'UNKNOWN_{flat}',
            f'UNKNOWN_${flat}',
            f'CODE_{flat}',
            f'DATA_{flat}',
        ])
        if len(flat) == 6:
            patterns.append(f'{flat[:2]}:{flat[2:]}')
    seen = set()
    out = []
    for p in patterns:
        if p not in seen:
            seen.add(p)
            out.append(p)
    return out


def iter_text_files(base: Path):
    for path in base.rglob('*'):
        if not path.is_file():
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        yield path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('address', help='CPU address like C4:B524 or flat hex like C4B524')
    parser.add_argument('--limit', type=int, default=20, help='Maximum matches to print')
    parser.add_argument('--dirs', nargs='*', default=None, help='Optional reference dirs to search')
    args = parser.parse_args()

    patterns = normalize_patterns(args.address)
    regex = re.compile('|'.join(re.escape(p) for p in patterns), re.IGNORECASE)

    bases = [Path(d) for d in args.dirs] if args.dirs else REF_DIRS
    print(f'Address: {args.address}')
    print('Patterns: ' + ', '.join(patterns))

    shown = 0
    for base in bases:
        if not base.exists():
            continue
        for path in iter_text_files(base):
            try:
                data = path.read_text(encoding='utf-8', errors='ignore').splitlines()
            except OSError:
                continue
            for lineno, line in enumerate(data, start=1):
                if regex.search(line):
                    rel = path.as_posix()
                    print(f'{rel}:{lineno}: {line.strip()}')
                    shown += 1
                    if shown >= args.limit:
                        return 0
    if shown == 0:
        print('No matches found.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
