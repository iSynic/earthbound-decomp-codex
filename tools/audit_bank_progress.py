#!/usr/bin/env python3
"""Audit local bank documentation against quarantined reference maps."""

from __future__ import annotations

import argparse
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path


BANKS = {
    "C0": {
        "index": "00",
        "config": Path("refs/ebsrc-main/ebsrc-main/src/bankconfig/US/bank00.asm"),
        "symbols": Path("refs/ebsrc-main/ebsrc-main/include/symbols/bank00.inc.asm"),
    },
    "C1": {
        "index": "01",
        "config": Path("refs/ebsrc-main/ebsrc-main/src/bankconfig/US/bank01.asm"),
        "symbols": Path("refs/ebsrc-main/ebsrc-main/include/symbols/bank01.inc.asm"),
    },
    "C2": {
        "index": "02",
        "config": Path("refs/ebsrc-main/ebsrc-main/src/bankconfig/US/bank02.asm"),
        "symbols": Path("refs/ebsrc-main/ebsrc-main/include/symbols/bank02.inc.asm"),
    },
    "C3": {
        "index": "03",
        "config": Path("refs/ebsrc-main/ebsrc-main/src/bankconfig/US/bank03.asm"),
        "symbols": Path("refs/ebsrc-main/ebsrc-main/include/symbols/bank03.inc.asm"),
    },
    "C4": {
        "index": "04",
        "config": Path("refs/ebsrc-main/ebsrc-main/src/bankconfig/US/bank04.asm"),
        "symbols": Path("refs/ebsrc-main/ebsrc-main/include/symbols/bank04.inc.asm"),
    },
    "C5": {
        "index": "05",
        "config": Path("refs/ebsrc-main/ebsrc-main/src/bankconfig/US/bank05.asm"),
        "symbols": Path("refs/ebsrc-main/ebsrc-main/include/symbols/text.inc.asm"),
    },
    "C6": {
        "index": "06",
        "config": Path("refs/ebsrc-main/ebsrc-main/src/bankconfig/US/bank06.asm"),
        "symbols": Path("refs/ebsrc-main/ebsrc-main/include/symbols/text.inc.asm"),
    },
    "C7": {
        "index": "07",
        "config": Path("refs/ebsrc-main/ebsrc-main/src/bankconfig/US/bank07.asm"),
        "symbols": Path("refs/ebsrc-main/ebsrc-main/include/symbols/text.inc.asm"),
    },
    "C8": {
        "index": "08",
        "config": Path("refs/ebsrc-main/ebsrc-main/src/bankconfig/US/bank08.asm"),
        "symbols": Path("refs/ebsrc-main/ebsrc-main/include/symbols/text.inc.asm"),
    },
    "C9": {
        "index": "09",
        "config": Path("refs/ebsrc-main/ebsrc-main/src/bankconfig/US/bank09.asm"),
        "symbols": Path("refs/ebsrc-main/ebsrc-main/include/symbols/text.inc.asm"),
    },
}

NOTE_GLOB = "notes/*.md"
SKIP_NOTE_NAMES = {
    "bank-0-1-progress-audit.md",
    "bank-c0-progress-audit.md",
    "bank-c1-progress-audit.md",
    "bank-c2-progress-audit.md",
    "bank-c3-progress-audit.md",
    "bank-c4-progress-audit.md",
    "bank-c0-reference-frontier.md",
    "bank-c1-reference-frontier.md",
    "bank-c2-reference-frontier.md",
    "bank-c3-reference-frontier.md",
    "bank-c4-reference-frontier.md",
    "bank-c0-c2-closure.md",
    "bank-c3-closure.md",
    "bank-c4-closure.md",
    "data-contracts-c0-c2.md",
    "data-contracts-c0-c3.md",
    "data-contracts-c0-c4.md",
    "c3-source-data-map.md",
    "c3-source-extraction-candidates.md",
    "script-payloads-c3.md",
    "bank-c0-working-name-proposals.md",
    "bank-c1-working-name-proposals.md",
    "bank-c2-working-name-proposals.md",
    "bank-c3-working-name-proposals.md",
    "bank-c4-working-name-proposals.md",
}
SKIP_NOTE_RE = re.compile(
    r"bank-c[0-9a-f]-(?:cluster-map|progress-audit|reference-frontier|working-name-proposals)\.md$",
    re.IGNORECASE,
)
INCLUDE_RE = re.compile(r'(?:\.INCLUDE|LOCALEINCLUDE)\s+"([^"]+)"', re.IGNORECASE)
GLOBAL_RE = re.compile(r"\.GLOBAL\s+([A-Za-z0-9_]+)")
ADDR_RE = re.compile(r"\b(C[0-9A-Fa-f])[:_]?([0-9A-Fa-f]{4})\b")
FLAT_ADDR_RE = re.compile(r"\b(?:UNKNOWN_|REDIRECT_|DATA_|CODE_|NULL_)?(C[0-9A-Fa-f][0-9A-Fa-f]{4})\b")
KNOWNISH_PREFIXES = (
    "UNKNOWN_",
    "REDIRECT_",
    "NULL_",
)


@dataclass(frozen=True)
class IncludeEntry:
    bank: str
    path: str
    address: str | None
    named: bool


def workspace_root() -> Path:
    return Path(__file__).resolve().parent.parent


def normalize_addr(raw: str) -> str | None:
    raw = raw.upper().replace("$", "")
    match = ADDR_RE.fullmatch(raw)
    if match:
        return f"{match.group(1)}:{match.group(2)}"
    match = FLAT_ADDR_RE.fullmatch(raw)
    if match:
        flat = match.group(1)
        return f"{flat[:2]}:{flat[2:]}"
    return None


def address_from_text(text: str, bank: str) -> str | None:
    for match in FLAT_ADDR_RE.finditer(text.upper()):
        flat = match.group(1)
        if flat.startswith(bank):
            return f"{flat[:2]}:{flat[2:]}"
    for match in ADDR_RE.finditer(text.upper()):
        if match.group(1) == bank:
            return f"{match.group(1)}:{match.group(2)}"
    return None


def iter_notes(root: Path) -> list[Path]:
    return sorted(
        path
        for path in root.glob(NOTE_GLOB)
        if path.is_file() and path.name not in SKIP_NOTE_NAMES and not SKIP_NOTE_RE.fullmatch(path.name)
    )


def parse_note_mentions(root: Path) -> dict[str, dict[str, set[str]]]:
    mentions: dict[str, dict[str, set[str]]] = {
        bank: defaultdict(set) for bank in BANKS
    }
    for note in iter_notes(root):
        rel = note.relative_to(root).as_posix()
        text = note.read_text(encoding="utf-8", errors="ignore")
        upper = text.upper()
        for match in ADDR_RE.finditer(upper):
            bank = match.group(1)
            if bank in mentions:
                mentions[bank][f"{bank}:{match.group(2)}"].add(rel)
        for match in FLAT_ADDR_RE.finditer(upper):
            flat = match.group(1)
            bank = flat[:2]
            if bank in mentions:
                mentions[bank][f"{bank}:{flat[2:]}"].add(rel)
    return mentions


def parse_symbols(root: Path, bank: str) -> list[str]:
    path = root / BANKS[bank]["symbols"]
    if not path.exists():
        return []
    symbols: list[str] = []
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        match = GLOBAL_RE.search(line)
        if match:
            symbols.append(match.group(1))
    return symbols


def parse_includes(root: Path, bank: str) -> list[IncludeEntry]:
    path = root / BANKS[bank]["config"]
    if not path.exists():
        return []
    entries: list[IncludeEntry] = []
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        match = INCLUDE_RE.search(line)
        if not match:
            continue
        include = match.group(1)
        address = address_from_text(include, bank)
        first_part = include.split("/", 1)[0].lower()
        named = first_part != "unknown" and address is None
        entries.append(IncludeEntry(bank=bank, path=include, address=address, named=named))
    return entries


def symbol_address(symbol: str, bank: str) -> str | None:
    return address_from_text(symbol, bank)


def is_placeholder_symbol(symbol: str) -> bool:
    return symbol.startswith(KNOWNISH_PREFIXES)


def summarize_bank(
    root: Path,
    bank: str,
    mentions: dict[str, dict[str, set[str]]],
) -> list[str]:
    includes = parse_includes(root, bank)
    symbols = parse_symbols(root, bank)
    addressed_includes = [entry for entry in includes if entry.address]
    named_includes = [entry for entry in includes if entry.named]
    unknown_includes = [entry for entry in addressed_includes if "/unknown/" in f"/{entry.path}".lower()]
    symbolic_addresses = {
        addr
        for symbol in symbols
        if (addr := symbol_address(symbol, bank)) is not None
    }
    note_addresses = set(mentions[bank])
    ref_addresses = {entry.address for entry in addressed_includes if entry.address} | symbolic_addresses
    covered_ref_addresses = ref_addresses & note_addresses
    local_only_addresses = sorted(note_addresses - ref_addresses)
    unmentioned_unknown = [
        entry for entry in unknown_includes if entry.address not in note_addresses
    ]

    placeholder_symbols = [symbol for symbol in symbols if is_placeholder_symbol(symbol)]
    semantic_symbols = [symbol for symbol in symbols if not is_placeholder_symbol(symbol)]

    lines = [
        f"## Bank `{bank}` / reference bank `{BANKS[bank]['index']}`",
        "",
        f"- Reference include entries: `{len(includes)}`",
        f"- Reference named include entries without an address in the path: `{len(named_includes)}`",
        f"- Reference address-bearing include entries: `{len(addressed_includes)}`",
        f"- Address-bearing unknown include entries: `{len(unknown_includes)}`",
        f"- Reference symbols: `{len(symbols)}` (`{len(semantic_symbols)}` semantic-ish, `{len(placeholder_symbols)}` placeholder/redirect/null)",
        f"- Local notes mention `{len(note_addresses)}` distinct `{bank}:xxxx` addresses",
        f"- Reference addresses mentioned by local notes: `{len(covered_ref_addresses)}` / `{len(ref_addresses)}`",
        f"- Unknown include entries not directly mentioned in local notes: `{len(unmentioned_unknown)}`",
        "",
    ]

    if named_includes:
        lines.extend(
            [
                "### Reference-Named Include Families",
                "",
                "These are already semantically grouped by `ebsrc-main`; use them as corroborating names, not as final local proof.",
                "",
            ]
        )
        for entry in named_includes[:80]:
            lines.append(f"- `{entry.path}`")
        if len(named_includes) > 80:
            lines.append(f"- ... {len(named_includes) - 80} more")
        lines.append("")

    if unmentioned_unknown:
        lines.extend(
            [
                "### Highest-Risk Unknown Chunks With No Local Address Mention",
                "",
                "These are reference `unknown/...` chunks whose start address is not directly cited in `notes/*.md` yet.",
                "",
            ]
        )
        for entry in unmentioned_unknown[:80]:
            lines.append(f"- `{entry.address}` from `{entry.path}`")
        if len(unmentioned_unknown) > 80:
            lines.append(f"- ... {len(unmentioned_unknown) - 80} more")
        lines.append("")

    if covered_ref_addresses:
        lines.extend(
            [
                "### Locally Corroborated Reference Addresses",
                "",
            ]
        )
        for address in sorted(covered_ref_addresses)[:80]:
            note_list = ", ".join(sorted(mentions[bank][address])[:3])
            extra = len(mentions[bank][address]) - 3
            if extra > 0:
                note_list += f", +{extra} more"
            lines.append(f"- `{address}` -> {note_list}")
        if len(covered_ref_addresses) > 80:
            lines.append(f"- ... {len(covered_ref_addresses) - 80} more")
        lines.append("")

    if local_only_addresses:
        lines.extend(
            [
                "### Local-Only Address Mentions",
                "",
                "These may be derived local discoveries, cross-bank targets, or address forms absent from the reference include/symbol map.",
                "",
            ]
        )
        for address in local_only_addresses[:80]:
            note_list = ", ".join(sorted(mentions[bank][address])[:3])
            extra = len(mentions[bank][address]) - 3
            if extra > 0:
                note_list += f", +{extra} more"
            lines.append(f"- `{address}` -> {note_list}")
        if len(local_only_addresses) > 80:
            lines.append(f"- ... {len(local_only_addresses) - 80} more")
        lines.append("")

    return lines


def render_report(root: Path, banks: list[str]) -> str:
    mentions = parse_note_mentions(root)
    title_banks = "/".join(banks)
    lines = [
        f"# Bank {title_banks} Decompilation Progress Audit",
        "",
        "This report cross-checks the local `notes/*.md` corpus against the quarantined `ebsrc-main` US bank include maps and symbol lists.",
        "",
        "Treat reference names as corroboration only: a bank entry is not considered understood here just because a side reference gave it a label.",
        "",
    ]
    for bank in banks:
        lines.extend(summarize_bank(root, bank, mentions))
    lines.extend(
        [
            "## Suggested Workflow",
            "",
            "1. Pick an unmentioned `unknown/...` chunk from this report.",
            "2. Run `tools/decode_snippet.py` or a targeted helper around the address.",
            "3. Cross-check `refs/ebsrc-main` symbols, `refs/earthbound-disasm-legacy`, and any data table in `refs/eb-decompile-4ef92` that the routine touches.",
            "4. Write a focused note that states byte-level evidence, borrowed reference names, remaining uncertainty, and direct callers/xrefs.",
            "5. Rerun this audit and promote the next gap.",
            "",
        ]
    )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--bank",
        action="append",
        choices=sorted(BANKS),
        help="Bank to audit. May be passed multiple times. Defaults to every configured bank.",
    )
    parser.add_argument(
        "--output",
        help="Optional Markdown output path.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = workspace_root()
    banks = args.bank or sorted(BANKS)
    report = render_report(root, banks)
    if args.output:
        (root / args.output).write_text(report + "\n", encoding="ascii")
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
