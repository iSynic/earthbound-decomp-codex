from __future__ import annotations

import argparse
import re
from pathlib import Path


DEFAULT_REF_ROOT = Path("refs") / "EB-M2-Listing-v1"
ADDRESS_RE = re.compile(r"^\s*([A-F0-9]{6}):")


def normalize_address(raw: str) -> tuple[str, str]:
    text = raw.strip().upper().replace("$", "")
    if ":" in text:
        bank_text, offset_text = text.split(":", 1)
        bank = int(bank_text, 16)
        offset = int(offset_text, 16)
        if bank >= 0xC0:
            long_addr = (bank << 16) | offset
            bank_index = bank - 0xC0
        else:
            long_addr = ((0xC0 + bank) << 16) | offset
            bank_index = bank
    else:
        value = int(text, 16)
        if value <= 0xFFFF:
            raise ValueError("bare addresses must be long addresses such as C00013")
        bank = (value >> 16) & 0xFF
        offset = value & 0xFFFF
        if bank < 0xC0:
            raise ValueError("expected a canonical C0-EF long address")
        bank_index = bank - 0xC0
        long_addr = (bank << 16) | offset

    if not 0 <= bank_index <= 0x2F:
        raise ValueError("address is outside C0-EF / bank00-bank2F")
    return f"{long_addr:06X}", f"{bank_index:02X}"


def read_lines(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8", errors="replace").splitlines()


def find_address(lines: list[str], address: str) -> list[int]:
    needle = f"{address}:"
    return [index for index, line in enumerate(lines) if needle in line]


def find_symbol(lines: list[str], symbol: str) -> list[int]:
    lowered = symbol.lower()
    return [index for index, line in enumerate(lines) if lowered in line.lower()]


def print_context(lines: list[str], indices: list[int], context: int, limit: int) -> None:
    for hit_no, index in enumerate(indices[:limit], start=1):
        start = max(0, index - context)
        end = min(len(lines), index + context + 1)
        print(f"--- hit {hit_no} line {index + 1} ---")
        for line_no in range(start, end):
            marker = ">" if line_no == index else " "
            print(f"{marker}{line_no + 1:8d}: {lines[line_no]}")

    if len(indices) > limit:
        print(f"... {len(indices) - limit} additional hits omitted")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Look up addresses or symbols in the EB-M2 listing reference."
    )
    parser.add_argument(
        "query",
        help="Address such as C0:0013/C00013, or a symbol when --symbol is used.",
    )
    parser.add_argument(
        "--symbol",
        action="store_true",
        help="Search for query as text instead of normalizing it as an address.",
    )
    parser.add_argument(
        "--region",
        choices=("US", "JP"),
        default="US",
        help="Listing region to search.",
    )
    parser.add_argument(
        "--bank",
        help="Limit --symbol searches to a bank index such as 00 or 2F.",
    )
    parser.add_argument(
        "--refs-root",
        default=str(DEFAULT_REF_ROOT),
        help="Path to the unpacked EB-M2-Listing-v1 directory.",
    )
    parser.add_argument("--context", type=int, default=12)
    parser.add_argument("--limit", type=int, default=8)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    ref_root = Path(args.refs_root)
    if not ref_root.is_dir():
        raise SystemExit(
            f"Reference root not found: {ref_root}\n"
            "Unpack EB-M2-Listing-v1.zip under refs/ first."
        )

    if args.symbol:
        if args.bank:
            bank = int(args.bank, 16)
            paths = [ref_root / args.region / f"bank{bank:02X}.txt"]
        else:
            paths = sorted((ref_root / args.region).glob("bank*.txt"))

        total = 0
        for path in paths:
            lines = read_lines(path)
            hits = find_symbol(lines, args.query)
            if not hits:
                continue
            total += len(hits)
            print(f"=== {path} ({len(hits)} hits) ===")
            print_context(lines, hits, args.context, args.limit)
        if total == 0:
            print("No matches.")
            return 1
        return 0

    address, bank = normalize_address(args.query)
    path = ref_root / args.region / f"bank{bank}.txt"
    if not path.is_file():
        raise SystemExit(f"Listing bank not found: {path}")
    lines = read_lines(path)
    hits = find_address(lines, address)
    if not hits:
        print(f"No matches for {address} in {path}.")
        return 1
    print(f"=== {path} ===")
    print_context(lines, hits, args.context, args.limit)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
