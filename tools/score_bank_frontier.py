#!/usr/bin/env python3
"""Score bank frontier chunks and render a cluster-first work map.

The normal progress audit is intentionally conservative: it tells us which
reference include starts have not been cited in local notes. This tool adds a
more tactical layer for planning: classify include-order neighborhoods, mark
likely code/data, count direct callers, and rank unknown chunks by likely payoff.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
BANK_CONFIG_TEMPLATE = "refs/ebsrc-main/ebsrc-main/src/bankconfig/US/bank{index}.asm"
BANKS_DIR = ROOT / "build" / "split" / "banks"
DEFAULT_WORKING_NAMES = ROOT / "build" / "working-names-c0-c4.json"
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
    "bank-c0-working-name-proposals.md",
    "bank-c1-working-name-proposals.md",
    "bank-c2-working-name-proposals.md",
    "bank-c3-working-name-proposals.md",
    "bank-c4-working-name-proposals.md",
    "bank-c4-cluster-map.md",
    "data-contracts-c0-c2.md",
    "data-contracts-c0-c3.md",
    "data-contracts-c0-c4.md",
    "c3-source-data-map.md",
    "c3-source-extraction-candidates.md",
    "script-payloads-c3.md",
}
SKIP_NOTE_RE = re.compile(
    r"bank-c[0-9a-f]-(?:cluster-map|progress-audit|reference-frontier|working-name-proposals)\.md$",
    re.IGNORECASE,
)
INCLUDE_RE = re.compile(r'(?:\.INCLUDE|LOCALEINCLUDE)\s+"([^"]+)"', re.IGNORECASE)
ADDR_RE = re.compile(r"\b(C[0-9A-F])[:_]?([0-9A-F]{4})\b")
FLAT_ADDR_RE = re.compile(r"\b(?:UNKNOWN_|REDIRECT_|DATA_|CODE_|NULL_)?(C[0-9A-F][0-9A-F]{4})\b")


@dataclass
class IncludeEntry:
    ordinal: int
    path: str
    address: str | None
    addr_int: int | None
    broad_kind: str
    family: str
    mentioned: bool = False
    working_name: str | None = None
    direct_callers: int = 0
    caller_banks: tuple[str, ...] = ()
    first_bytes: bytes = b""
    next_address: str | None = None
    size_hint: int | None = None


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def bank_index(bank: str) -> str:
    return f"{int(bank, 16) - 0xC0:02X}" if bank.startswith("C") else bank[-2:]


def address_from_text(text: str, bank: str) -> tuple[str, int] | tuple[None, None]:
    upper = text.upper()
    for match in FLAT_ADDR_RE.finditer(upper):
        flat = match.group(1)
        if flat.startswith(bank):
            return f"{bank}:{flat[2:]}", int(flat[2:], 16)
    for match in ADDR_RE.finditer(upper):
        if match.group(1) == bank:
            return f"{bank}:{match.group(2)}", int(match.group(2), 16)
    return None, None


def classify_include(path: str) -> tuple[str, str]:
    parts = path.split("/")
    top = parts[0]
    lower = path.lower()

    if top == "data":
        if "/events/scripts/" in lower:
            return "event-script-data", "event scripts"
        if "/events/" in lower:
            return "event-data", "event data"
        if "/text/" in lower:
            return "text-data", "text data"
        if "/map/" in lower:
            return "map-data", "map data"
        if "/battle/" in lower:
            return "battle-data", "battle data"
        if "unknown" in lower:
            return "unknown-data", "unknown data"
        return "named-data", top
    if top == "unknown":
        return "unknown-code", "unknown code"
    if top == "text":
        return "named-code", "text code"
    if top == "text_data":
        return "text-data", "text data"
    if top in {"misc", "overworld", "system", "audio"}:
        return "named-code", f"{top} code"
    if top in {"eventmacros.asm", "common.asm", "config.asm", "structs.asm"}:
        return "support", "support includes"
    if top == "symbols":
        return "symbols", "symbols"
    return "named-include", top


def parse_bank_config(bank: str) -> list[IncludeEntry]:
    index = bank_index(bank)
    path = ROOT / BANK_CONFIG_TEMPLATE.format(index=index)
    entries: list[IncludeEntry] = []
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        match = INCLUDE_RE.search(line)
        if not match:
            continue
        include_path = match.group(1)
        address, addr_int = address_from_text(include_path, bank)
        broad_kind, family = classify_include(include_path)
        entries.append(
            IncludeEntry(
                ordinal=len(entries),
                path=include_path,
                address=address,
                addr_int=addr_int,
                broad_kind=broad_kind,
                family=family,
            )
        )
    return entries


def iter_notes() -> list[Path]:
    return sorted(
        path
        for path in ROOT.glob(NOTE_GLOB)
        if path.is_file() and path.name not in SKIP_NOTE_NAMES and not SKIP_NOTE_RE.fullmatch(path.name)
    )


def parse_note_mentions(bank: str) -> set[str]:
    mentions: set[str] = set()
    for note in iter_notes():
        text = note.read_text(encoding="utf-8", errors="ignore").upper()
        for match in ADDR_RE.finditer(text):
            if match.group(1) == bank:
                mentions.add(f"{bank}:{match.group(2)}")
        for match in FLAT_ADDR_RE.finditer(text):
            flat = match.group(1)
            if flat.startswith(bank):
                mentions.add(f"{bank}:{flat[2:]}")
    return mentions


def load_working_names(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return {
        entry["address"]: entry["name"]
        for entry in data.get("entries", [])
        if entry.get("address") and entry.get("name")
    }


def load_bank_bytes() -> dict[int, bytes]:
    banks: dict[int, bytes] = {}
    for path in sorted(BANKS_DIR.glob("bank_*.bin")):
        bank = int(path.stem.split("_", 1)[1], 16)
        banks[bank] = path.read_bytes()
    return banks


def scan_direct_callers(
    bank_bytes: dict[int, bytes],
    target_bank: int,
    target_addr: int,
) -> tuple[int, tuple[str, ...]]:
    caller_banks: set[str] = set()
    total = 0
    lo = target_addr & 0xFF
    hi = (target_addr >> 8) & 0xFF
    for caller_bank, data in bank_bytes.items():
        found = False
        for i in range(len(data) - 3):
            if data[i] == 0x22 and data[i + 1] == lo and data[i + 2] == hi and data[i + 3] == target_bank:
                total += 1
                found = True
        if caller_bank == target_bank:
            for i in range(len(data) - 2):
                if data[i] == 0x20 and data[i + 1] == lo and data[i + 2] == hi:
                    total += 1
                    found = True
        if found:
            caller_banks.add(f"{caller_bank:02X}")
    return total, tuple(sorted(caller_banks))


def annotate_entries(
    entries: list[IncludeEntry],
    bank: str,
    mentions: set[str],
    working_names: dict[str, str],
    with_callers: bool,
) -> None:
    bank_num = int(bank, 16)
    bank_path = BANKS_DIR / f"bank_{bank}.bin"
    if not bank_path.exists():
        bank_path = BANKS_DIR / f"bank_{bank_num - 0xC0:02X}.bin"
    bank_data = bank_path.read_bytes() if bank_path.exists() else b""
    bank_bytes = load_bank_bytes() if with_callers else {}

    addressed = [entry for entry in entries if entry.addr_int is not None]
    for current, next_entry in zip(addressed, addressed[1:]):
        if current.addr_int is not None and next_entry.addr_int is not None and next_entry.addr_int > current.addr_int:
            current.next_address = next_entry.address
            current.size_hint = next_entry.addr_int - current.addr_int

    for entry in entries:
        if entry.address:
            entry.mentioned = entry.address in mentions
            entry.working_name = working_names.get(entry.address)
        if entry.addr_int is not None and bank_data:
            entry.first_bytes = bank_data[entry.addr_int:entry.addr_int + 12]
        if with_callers and entry.addr_int is not None and entry.broad_kind in {"unknown-code", "named-code"}:
            entry.direct_callers, entry.caller_banks = scan_direct_callers(bank_bytes, bank_num, entry.addr_int)


def chunk_clusters(entries: list[IncludeEntry]) -> list[list[IncludeEntry]]:
    clusters: list[list[IncludeEntry]] = []
    current: list[IncludeEntry] = []
    current_family: str | None = None
    for entry in entries:
        family = entry.family
        if not current:
            current = [entry]
            current_family = family
            continue
        prev = current[-1]
        same_family = family == current_family
        close_continuation = (
            entry.addr_int is not None
            and prev.addr_int is not None
            and entry.addr_int - prev.addr_int <= 0x180
            and entry.broad_kind == prev.broad_kind
        )
        support = entry.broad_kind in {"support", "symbols"}
        if same_family or close_continuation or support:
            current.append(entry)
        else:
            clusters.append(current)
            current = [entry]
            current_family = family
    if current:
        clusters.append(current)
    return clusters


def first_opcode_looks_code(data: bytes) -> bool:
    if not data:
        return False
    common = {
        0x08, 0x0B, 0x20, 0x22, 0x48, 0x4C, 0x5C, 0x6B, 0x80, 0x82, 0x8B,
        0x9C, 0xA0, 0xA2, 0xA9, 0xAD, 0xAE, 0xAF, 0xC2, 0xE2, 0xEE, 0xF0,
    }
    invalidish = {0x02, 0x03, 0x07, 0x0F, 0x12, 0x13, 0x22, 0x42, 0x44, 0x54, 0x62, 0xC2}
    if data[0] in common:
        return True
    # REP/SEP are code opcodes too; keep the duplicate-looking set above harmless.
    if data[0] in {0xC2, 0xE2}:
        return True
    if len(set(data[:8])) <= 2:
        return False
    return data[0] not in invalidish


def score_entry(entries: list[IncludeEntry], index: int) -> tuple[int, list[str]]:
    entry = entries[index]
    score = 0
    reasons: list[str] = []

    if entry.broad_kind == "unknown-code":
        score += 10
        reasons.append("unknown code include")
    elif entry.broad_kind == "unknown-data":
        score += 2
        reasons.append("unknown data include")
    elif entry.broad_kind.endswith("data"):
        score -= 6
        reasons.append("data-like include")

    if not entry.mentioned:
        score += 8
        reasons.append("no local note mention")
    if not entry.working_name:
        score += 5
        reasons.append("no working name")
    if entry.direct_callers:
        score += min(24, entry.direct_callers * 6)
        reasons.append(f"{entry.direct_callers} direct caller(s)")
    if entry.caller_banks:
        score += min(8, len(entry.caller_banks) * 2)
        reasons.append("cross-bank caller evidence" if len(entry.caller_banks) > 1 else "caller evidence")

    for label, neighbor in (("previous", entries[index - 1] if index > 0 else None), ("next", entries[index + 1] if index + 1 < len(entries) else None)):
        if neighbor and (neighbor.mentioned or neighbor.working_name):
            score += 4
            reasons.append(f"{label} neighbor locally covered")
        if neighbor and neighbor.family != entry.family and neighbor.broad_kind.startswith("named"):
            score += 1

    if entry.size_hint is not None:
        if entry.size_hint <= 0x40:
            score += 6
            reasons.append(f"small chunk ({entry.size_hint:#x})")
        elif entry.size_hint <= 0x120:
            score += 3
            reasons.append(f"bounded chunk ({entry.size_hint:#x})")
        elif entry.size_hint >= 0x500:
            score -= 3
            reasons.append(f"large chunk ({entry.size_hint:#x})")

    if first_opcode_looks_code(entry.first_bytes):
        score += 2
        reasons.append("code-like first bytes")
    elif entry.first_bytes:
        score -= 2
        reasons.append("data-like first bytes")

    return score, reasons


def hex_bytes(data: bytes) -> str:
    return " ".join(f"{byte:02X}" for byte in data[:8]) if data else ""


def summarize_cluster(cluster: list[IncludeEntry]) -> dict[str, Any]:
    addressed = [entry for entry in cluster if entry.address]
    unknown = [entry for entry in cluster if entry.broad_kind in {"unknown-code", "unknown-data"}]
    unmentioned = [entry for entry in unknown if not entry.mentioned]
    working = [entry for entry in cluster if entry.working_name]
    kinds = Counter(entry.broad_kind for entry in cluster)
    start = addressed[0].address if addressed else ""
    end = addressed[-1].address if addressed else ""
    return {
        "start": start,
        "end": end,
        "count": len(cluster),
        "unknown": len(unknown),
        "unmentioned": len(unmentioned),
        "working": len(working),
        "kinds": kinds,
    }


def recommend_clusters(
    clusters: list[list[IncludeEntry]],
    score_by_address: dict[str, tuple[int, list[str]]],
    limit: int = 6,
) -> list[tuple[int, int, int, dict[str, Any], list[IncludeEntry], str]]:
    rows: list[tuple[int, int, int, dict[str, Any], list[IncludeEntry], str]] = []
    for idx, cluster in enumerate(clusters, start=1):
        unfinished = [
            entry for entry in cluster
            if entry.address
            and entry.broad_kind in {"unknown-code", "unknown-data"}
            and not (entry.mentioned and entry.working_name)
        ]
        if not unfinished:
            continue

        scored = [
            (score_by_address.get(entry.address, (0, []))[0], entry)
            for entry in unfinished
        ]
        scored.sort(key=lambda row: (-row[0], row[1].addr_int or 0))
        total_score = sum(score for score, _entry in scored)
        max_score = scored[0][0] if scored else 0
        caller_hits = sum(entry.direct_callers for _score, entry in scored)
        top_entries = [entry for _score, entry in scored[:4]]

        cross_bank = any(len(entry.caller_banks) > 1 for _score, entry in scored)
        all_code = all(entry.broad_kind == "unknown-code" for _score, entry in scored)
        unmentioned = sum(1 for entry in unfinished if not entry.mentioned)
        reasons = []
        if caller_hits:
            reasons.append("caller-dense")
        if cross_bank:
            reasons.append("cross-bank")
        if unmentioned:
            reasons.append(f"{unmentioned} unmentioned")
        if all_code:
            reasons.append("all code")
        reason = ", ".join(reasons[:4]) or "unfinished cluster"

        summary = summarize_cluster(cluster)
        summary["index"] = idx
        rows.append((max_score, total_score, caller_hits, summary, top_entries, reason))

    rows.sort(key=lambda row: (-row[0], -row[1], -row[2], row[3]["start"] or ""))
    return rows[:limit]


def render_report(bank: str, entries: list[IncludeEntry], top: int) -> str:
    clusters = chunk_clusters(entries)
    candidates: list[tuple[int, IncludeEntry, list[str]]] = []
    for i, entry in enumerate(entries):
        if not entry.address:
            continue
        if entry.mentioned and entry.working_name:
            continue
        if entry.broad_kind not in {"unknown-code", "unknown-data"}:
            continue
        score, reasons = score_entry(entries, i)
        candidates.append((score, entry, reasons))
    candidates.sort(key=lambda row: (-row[0], row[1].addr_int or 0))
    score_by_address = {entry.address: (score, reasons) for score, entry, reasons in candidates if entry.address}

    total_unknown = sum(1 for entry in entries if entry.broad_kind in {"unknown-code", "unknown-data"} and entry.address)
    total_unmentioned = sum(1 for entry in entries if entry.broad_kind in {"unknown-code", "unknown-data"} and entry.address and not entry.mentioned)
    total_working = sum(1 for entry in entries if entry.working_name)

    lines = [
        f"# Bank {bank} Cluster Map And Frontier Scores",
        "",
        "Generated by `tools/score_bank_frontier.py`. This is a planning map, not proof of semantics.",
        "",
        "## Strategy Shift",
        "",
        "- Prefer cluster-sized passes over single-address marches.",
        "- Promote mechanical contracts early when they are byte-true, then refine user-facing names later.",
        "- Treat data-looking includes as classification/manifest work, not routine archaeology.",
        "- Use direct callers and locally covered neighbors to choose the next high-leverage seam.",
        "",
        "## Summary",
        "",
        f"- include entries: `{len(entries)}`",
        f"- clusters: `{len(clusters)}`",
        f"- address-bearing unknown code/data includes: `{total_unknown}`",
        f"- unknown code/data includes without local note mention: `{total_unmentioned}`",
        f"- local working names represented in include map: `{total_working}`",
        "",
        "## Recommended Batches",
        "",
        "| Rank | Cluster | Span | Unfinished | Caller hits | Top addresses | Why |",
        "| --- | ---: | --- | ---: | ---: | --- | --- |",
    ]
    for rank, (_max_score, _total_score, caller_hits, summary, top_entries, reason) in enumerate(
        recommend_clusters(clusters, score_by_address),
        start=1,
    ):
        addresses = ", ".join(f"`{entry.address}`" for entry in top_entries)
        lines.append(
            f"| {rank} | {summary['index']} | `{summary['start']}`-`{summary['end']}` | {summary['unknown']} | {caller_hits} | {addresses} | {reason} |"
        )

    lines.extend(
        [
            "",
        "## Top Frontier Targets",
        "",
        "| Rank | Score | Address | Include | Kind | Size | Callers | First bytes | Reasons |",
        "| --- | ---: | --- | --- | --- | ---: | ---: | --- | --- |",
        ]
    )
    for rank, (score, entry, reasons) in enumerate(candidates[:top], start=1):
        callers = f"{entry.direct_callers}"
        if entry.caller_banks:
            callers += f" ({','.join(entry.caller_banks)})"
        size = f"0x{entry.size_hint:X}" if entry.size_hint is not None else ""
        lines.append(
            f"| {rank} | {score} | `{entry.address}` | `{entry.path}` | `{entry.broad_kind}` | {size} | {callers} | `{hex_bytes(entry.first_bytes)}` | {'; '.join(reasons[:5])} |"
        )

    lines.extend(["", "## Cluster Overview", ""])
    for idx, cluster in enumerate(clusters, start=1):
        summary = summarize_cluster(cluster)
        if summary["unknown"] == 0 and summary["working"] == 0:
            continue
        kinds = ", ".join(f"{kind}:{count}" for kind, count in sorted(summary["kinds"].items()))
        lines.extend(
            [
                f"### Cluster {idx}: {summary['start'] or 'support'}-{summary['end'] or 'support'}",
                "",
                f"- entries: `{summary['count']}`",
                f"- unknown code/data: `{summary['unknown']}`",
                f"- unmentioned unknown: `{summary['unmentioned']}`",
                f"- working names: `{summary['working']}`",
                f"- kind mix: `{kinds}`",
                "",
            ]
        )
        notable = [
            entry for entry in cluster
            if entry.address and (entry.broad_kind in {"unknown-code", "unknown-data"} or entry.working_name)
        ][:18]
        for entry in notable:
            marker = "covered" if entry.mentioned or entry.working_name else "frontier"
            name = f" -> `{entry.working_name}`" if entry.working_name else ""
            callers = f", callers={entry.direct_callers}" if entry.direct_callers else ""
            lines.append(f"- `{entry.address}` `{entry.path}` ({marker}, {entry.broad_kind}{callers}){name}")
        if len(notable) < len([entry for entry in cluster if entry.address]):
            lines.append("- ...")
        lines.append("")

    lines.extend(
        [
            "## Recommended Operating Loop",
            "",
            "1. Pick a top target unless the cluster overview reveals an easier same-family batch.",
            "2. Decode the target plus immediate neighbors, then name the cluster mechanically.",
            "3. If first bytes or include path show table/text/data, classify the data and move on.",
            "4. Rerun this scorer and the normal audit after each batch.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Score and cluster a bank frontier.")
    parser.add_argument("bank", help="canonical bank such as C4")
    parser.add_argument("--working-names", type=Path, default=DEFAULT_WORKING_NAMES)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--top", type=int, default=40)
    parser.add_argument("--no-callers", action="store_true", help="Skip direct caller scanning for speed.")
    args = parser.parse_args()

    bank = args.bank.upper()
    if not re.fullmatch(r"C[0-9A-F]", bank):
        raise SystemExit("bank must look like C4")

    entries = parse_bank_config(bank)
    mentions = parse_note_mentions(bank)
    working_names = load_working_names(args.working_names if args.working_names.is_absolute() else ROOT / args.working_names)
    annotate_entries(entries, bank, mentions, working_names, with_callers=not args.no_callers)

    markdown = render_report(bank, entries, args.top)
    output = args.output or ROOT / "notes" / f"bank-{bank.lower()}-cluster-map.md"
    output = output if output.is_absolute() else ROOT / output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(markdown, encoding="utf-8")
    print(f"Wrote {rel(output)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
