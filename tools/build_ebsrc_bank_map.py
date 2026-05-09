#!/usr/bin/env python3
"""Build a reference-led bank map from ebsrc include order plus local source spans."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
EBSRC_ROOT = ROOT / "refs" / "ebsrc-main" / "ebsrc-main"
BANKCONFIG_TEMPLATE = EBSRC_ROOT / "src" / "bankconfig" / "US" / "bank{index}.asm"
SYMBOL_TEMPLATE = EBSRC_ROOT / "include" / "symbols" / "bank{index}.inc.asm"
INCLUDE_RE = re.compile(r'(?:\.INCLUDE|LOCALEINCLUDE)\s+"([^"]+)"', re.IGNORECASE)
FLAT_ADDR_RE = re.compile(r"\b(?:UNKNOWN_|REDIRECT_|DATA_|CODE_|NULL_)?([C-E][0-9A-F][0-9A-F]{4})\b", re.IGNORECASE)
ADDR_RE = re.compile(r"\b([C-E][0-9A-F])[:_]?([0-9A-F]{4})\b", re.IGNORECASE)
GLOBAL_RE = re.compile(r"\.GLOBAL\s+([A-Z0-9_]+)\s*:", re.IGNORECASE)
LABEL_RE = re.compile(r"^([C-E][0-9A-F]):([0-9A-F]{4})\s+(.+)$", re.IGNORECASE)


@dataclass(frozen=True)
class Span:
    start: int
    end: int
    source_path: str
    label: str | None = None

    def contains(self, address: int) -> bool:
        return self.start <= address < self.end


def bank_index(bank: str) -> str:
    value = int(bank.upper(), 16)
    if 0xC0 <= value <= 0xEF:
        return f"{value - 0xC0:02X}"
    return f"{value:02X}"


def parse_cpu_address(raw: str) -> tuple[str, int]:
    value = raw.strip().upper().replace("$", "")
    if ":" in value:
        bank, address = value.split(":", 1)
        return bank.zfill(2), int(address, 16)
    if len(value) == 6:
        return value[:2], int(value[2:], 16)
    raise ValueError(f"cannot parse CPU address {raw!r}")


def format_address(bank: str, address: int | None) -> str | None:
    if address is None or address > 0xFFFF:
        return None
    return f"{bank}:{address:04X}"


def address_from_text(text: str, bank: str) -> int | None:
    upper = text.upper()
    for match in FLAT_ADDR_RE.finditer(upper):
        flat = match.group(1).upper()
        if flat.startswith(bank):
            return int(flat[2:], 16)
    for match in ADDR_RE.finditer(upper):
        if match.group(1).upper() == bank:
            return int(match.group(2), 16)
    return None


def classify_include(path: str) -> tuple[str, str]:
    lower = path.lower()
    top = lower.split("/", 1)[0]
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
        return "named-data", "data"
    if top == "unknown":
        return "unknown-code", "unknown code"
    if top in {"misc", "overworld", "intro", "text", "audio", "battle", "system"}:
        return "named-code", f"{top} code"
    if top == "symbols":
        return "support", "symbols"
    if path.lower().endswith(".asm") and "/" not in path:
        return "support", "support includes"
    return "named-include", top


def symbol_candidates(include_path: str, bank: str, start: int | None) -> list[str]:
    path = include_path.replace("\\", "/")
    stem = Path(path).stem.upper()
    candidates: list[str] = []
    if start is not None:
        candidates.append(f"UNKNOWN_{bank}{start:04X}")
    if stem:
        candidates.append(stem)
        if stem.startswith(f"{bank}"):
            candidates.append(f"UNKNOWN_{stem}")
        if stem.isdecimal():
            candidates.append(f"EVENT_{stem}")
    if "/" in path:
        parts = [part.upper() for part in Path(path).with_suffix("").parts]
        if parts:
            candidates.append("_".join(parts[-2:]))
            candidates.append("_".join(parts))
    seen: set[str] = set()
    out: list[str] = []
    for candidate in candidates:
        candidate = re.sub(r"[^A-Z0-9_]", "_", candidate)
        if candidate and candidate not in seen:
            seen.add(candidate)
            out.append(candidate)
    return out


def parse_bank_config(bank: str) -> list[dict[str, Any]]:
    path = BANKCONFIG_TEMPLATE.with_name(f"bank{bank_index(bank)}.asm")
    entries: list[dict[str, Any]] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8", errors="ignore").splitlines(), start=1):
        match = INCLUDE_RE.search(line)
        if not match:
            continue
        include_path = match.group(1)
        kind, family = classify_include(include_path)
        explicit_start = address_from_text(include_path, bank)
        entries.append(
            {
                "ordinal": len(entries),
                "line": line_no,
                "include_path": include_path,
                "kind": kind,
                "family": family,
                "explicit_start": explicit_start,
            }
        )
    return entries


def load_symbols(bank: str) -> set[str]:
    path = SYMBOL_TEMPLATE.with_name(f"bank{bank_index(bank)}.inc.asm")
    if not path.exists():
        return set()
    return {
        match.group(1).upper()
        for match in GLOBAL_RE.finditer(path.read_text(encoding="utf-8", errors="ignore"))
    }


def labels_from_range(range_entry: dict[str, Any], bank: str) -> list[tuple[int, str]]:
    labels: list[tuple[int, str]] = []
    for raw in range_entry.get("labels", []):
        match = LABEL_RE.match(raw)
        if match and match.group(1).upper() == bank:
            labels.append((int(match.group(2), 16), match.group(3).strip()))
    return sorted(set(labels))


def load_source_spans(bank: str) -> tuple[list[Span], dict[int, Span]]:
    manifest = ROOT / "build" / f"{bank.lower()}-build-candidate-ranges.json"
    if not manifest.exists():
        return [], {}
    data = json.loads(manifest.read_text(encoding="utf-8"))
    range_spans: list[Span] = []
    label_spans: dict[int, Span] = {}
    for entry in data.get("ranges", []):
        _start_bank, start = parse_cpu_address(entry["start"])
        _end_bank, end = parse_cpu_address(entry["end"])
        range_spans.append(Span(start=start, end=end, source_path=entry["source_path"]))
        labels = labels_from_range(entry, bank)
        for index, (label_addr, label_name) in enumerate(labels):
            next_label = labels[index + 1][0] if index + 1 < len(labels) else end
            if start <= label_addr < next_label <= end:
                label_spans[label_addr] = Span(
                    start=label_addr,
                    end=next_label,
                    source_path=entry["source_path"],
                    label=label_name,
                )
    return range_spans, label_spans


def load_working_names(bank: str) -> dict[int, str]:
    path = ROOT / "build" / f"working-names-c0-c4.json"
    if not path.exists():
        path = ROOT / "build" / f"working-names-{bank.lower()}.json"
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    out: dict[int, str] = {}
    for entry in data.get("entries", []):
        address = entry.get("address")
        name = entry.get("name")
        if not address or not name:
            continue
        entry_bank, entry_addr = parse_cpu_address(address)
        if entry_bank == bank:
            out[entry_addr] = name
    return out


def coverage_for(range_spans: list[Span], start: int | None, end: int | None) -> Span | None:
    if start is None:
        return None
    for span in range_spans:
        if end is None:
            if span.contains(start):
                return span
        elif span.start <= start and end <= span.end:
            return span
    return None


def next_explicit_start(entries: list[dict[str, Any]], index: int) -> int | None:
    if index + 1 < len(entries) and entries[index + 1].get("explicit_start") is not None:
        return entries[index + 1]["explicit_start"]
    return None


def resolve_entries(bank: str, entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    symbols = load_symbols(bank)
    range_spans, label_spans = load_source_spans(bank)
    working_names = load_working_names(bank)

    cursor: int | None = None
    resolved: list[dict[str, Any]] = []
    for index, entry in enumerate(entries):
        explicit_start = entry["explicit_start"]
        start_source = "explicit" if explicit_start is not None else None
        start = explicit_start
        if start is None and cursor is not None:
            start = cursor
            start_source = "inferred-from-previous-end"

        end: int | None = None
        end_source: str | None = None
        if start is not None and start in label_spans:
            end = label_spans[start].end
            end_source = "local-source-label-span"
        elif start is not None and next_explicit_start(entries, index) is not None:
            end = next_explicit_start(entries, index)
            end_source = "next-ebsrc-explicit-include"

        if start is not None and end is None:
            covering = coverage_for(range_spans, start, None)
            if covering is not None and covering.start == start:
                end = covering.end
                end_source = "local-source-range"

        if end is not None:
            cursor = end
        elif explicit_start is not None:
            cursor = None

        covering_span = coverage_for(range_spans, start, end)
        ebsrc_symbol = None
        for candidate in symbol_candidates(entry["include_path"], bank, start):
            if candidate in symbols:
                ebsrc_symbol = candidate
                break

        status = "exact" if start is not None and end is not None else "open"
        if entry["kind"] == "support":
            status = "support"

        out = {
            "ordinal": entry["ordinal"],
            "bankconfig_line": entry["line"],
            "include_path": entry["include_path"],
            "kind": entry["kind"],
            "family": entry["family"],
            "explicit_start": format_address(bank, explicit_start),
            "start": format_address(bank, start),
            "end": format_address(bank, end),
            "size": None if start is None or end is None else end - start,
            "start_source": start_source,
            "end_source": end_source,
            "status": status,
            "ebsrc_symbol": ebsrc_symbol,
            "local_name": working_names.get(start) if start is not None else None,
            "promoted": covering_span is not None and start is not None and end is not None,
            "covered_by": covering_span.source_path if covering_span is not None else None,
            "promotion_candidate": (
                status == "exact"
                and covering_span is None
                and entry["kind"] in {"unknown-code", "named-code", "named-include"}
            ),
        }
        resolved.append(out)
    return resolved


def render_markdown(bank: str, data: dict[str, Any]) -> str:
    summary = data["summary"]
    frontier = summary.get("latest_promoted_end")
    lines = [
        f"# ebsrc Bank {bank} Reference Map",
        "",
        "Generated from ebsrc bankconfig include order, ebsrc bank symbols, and local source-bank build-candidate spans.",
        "",
        "## Summary",
        "",
        f"- includes: `{summary['includes']}`",
        f"- exact spans: `{summary['exact_spans']}`",
        f"- promoted exact spans: `{summary['promoted_exact_spans']}`",
        f"- promotion candidates: `{summary['promotion_candidates']}`",
        f"- open/unresolved entries: `{summary['open_entries']}`",
        f"- latest promoted end: `{frontier or ''}`",
        "",
        "## Current Open Frontier",
        "",
        "| Start | End | Size | Status | Include | ebsrc Symbol | Local Name | Kind |",
        "| --- | --- | ---: | --- | --- | --- | --- | --- |",
    ]
    frontier_index = None
    if frontier is not None:
        for index, entry in enumerate(data["entries"]):
            if entry.get("start") == frontier:
                frontier_index = index
                break
    if frontier_index is not None:
        for entry in data["entries"][frontier_index : frontier_index + 8]:
            lines.append(
                "| {start} | {end} | {size} | `{status}` | `{include}` | `{symbol}` | `{name}` | `{kind}` |".format(
                    start=entry["start"] or "",
                    end=entry["end"] or "",
                    size=entry["size"] or 0,
                    status=entry["status"],
                    include=entry["include_path"],
                    symbol=entry["ebsrc_symbol"] or "",
                    name=entry["local_name"] or "",
                    kind=entry["kind"],
                )
            )
    lines.extend([
        "",
        "## Current Exact Frontier Candidates",
        "",
        "| Start | End | Size | Include | ebsrc Symbol | Local Name | Kind |",
        "| --- | --- | ---: | --- | --- | --- | --- |",
    ])
    candidates = [entry for entry in data["entries"] if entry["promotion_candidate"]]
    frontier_candidates = [
        entry for entry in candidates if frontier is None or (entry["start"] or "") >= frontier
    ]
    for entry in frontier_candidates[:20]:
        lines.append(
            "| {start} | {end} | {size} | `{include}` | `{symbol}` | `{name}` | `{kind}` |".format(
                start=entry["start"] or "",
                end=entry["end"] or "",
                size=entry["size"] or 0,
                include=entry["include_path"],
                symbol=entry["ebsrc_symbol"] or "",
                name=entry["local_name"] or "",
                kind=entry["kind"],
            )
        )
    lines.extend(
        [
            "",
            "## Candidate Backlog",
            "",
            "| Start | End | Size | Include | ebsrc Symbol | Local Name | Kind |",
            "| --- | --- | ---: | --- | --- | --- | --- |",
        ]
    )
    for entry in candidates[:40]:
        lines.append(
            "| {start} | {end} | {size} | `{include}` | `{symbol}` | `{name}` | `{kind}` |".format(
                start=entry["start"] or "",
                end=entry["end"] or "",
                size=entry["size"] or 0,
                include=entry["include_path"],
                symbol=entry["ebsrc_symbol"] or "",
                name=entry["local_name"] or "",
                kind=entry["kind"],
            )
        )
    lines.extend(
        [
            "",
            "## Include Map",
            "",
            "| # | Start | End | Size | Status | Promoted | Include | ebsrc Symbol | Local Name |",
            "| ---: | --- | --- | ---: | --- | --- | --- | --- | --- |",
        ]
    )
    for entry in data["entries"]:
        lines.append(
            "| {ordinal} | {start} | {end} | {size} | `{status}` | {promoted} | `{include}` | `{symbol}` | `{name}` |".format(
                ordinal=entry["ordinal"],
                start=entry["start"] or "",
                end=entry["end"] or "",
                size=entry["size"] or 0,
                status=entry["status"],
                promoted="yes" if entry["promoted"] else "",
                include=entry["include_path"],
                symbol=entry["ebsrc_symbol"] or "",
                name=entry["local_name"] or "",
            )
        )
    return "\n".join(lines).rstrip() + "\n"


def build(bank: str) -> dict[str, Any]:
    entries = resolve_entries(bank, parse_bank_config(bank))
    exact = [entry for entry in entries if entry["status"] == "exact"]
    candidates = [entry for entry in entries if entry["promotion_candidate"]]
    promoted_ends = [entry["end"] for entry in exact if entry["promoted"] and entry.get("end")]
    return {
        "schema": "earthbound-decomp.ebsrc-bank-map.v1",
        "generated_by": "tools/build_ebsrc_bank_map.py",
        "bank": bank,
        "inputs": {
            "bankconfig": f"refs/ebsrc-main/ebsrc-main/src/bankconfig/US/bank{bank_index(bank)}.asm",
            "symbols": f"refs/ebsrc-main/ebsrc-main/include/symbols/bank{bank_index(bank)}.inc.asm",
            "source_ranges": f"build/{bank.lower()}-build-candidate-ranges.json",
        },
        "summary": {
            "includes": len(entries),
            "exact_spans": len(exact),
            "promoted_exact_spans": sum(1 for entry in exact if entry["promoted"]),
            "promotion_candidates": len(candidates),
            "open_entries": sum(1 for entry in entries if entry["status"] == "open"),
            "latest_promoted_end": max(promoted_ends) if promoted_ends else None,
        },
        "entries": entries,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bank", default="C4")
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--markdown-out", type=Path)
    args = parser.parse_args()

    bank = args.bank.upper()
    data = build(bank)
    json_out = args.json_out or ROOT / "build" / f"ebsrc-bank-{bank.lower()}-map.json"
    markdown_out = args.markdown_out or ROOT / "notes" / f"ebsrc-bank-{bank.lower()}-map.md"
    json_out.parent.mkdir(parents=True, exist_ok=True)
    markdown_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    markdown_out.write_text(render_markdown(bank, data), encoding="utf-8")
    summary = data["summary"]
    print(
        f"{bank}: {summary['includes']} includes, {summary['exact_spans']} exact spans, "
        f"{summary['promotion_candidates']} promotion candidates."
    )
    print(f"Wrote {json_out.relative_to(ROOT)} and {markdown_out.relative_to(ROOT)}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
