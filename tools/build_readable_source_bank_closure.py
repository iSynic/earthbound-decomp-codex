#!/usr/bin/env python3
"""Audit readable source-bank closure beyond byte-equivalent scaffolds."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_BANKS = ("C0", "C1", "C2", "C4", "EF")

INSTRUCTION_MNEMONICS = {
    "adc",
    "and",
    "asl",
    "bcc",
    "bcs",
    "beq",
    "bit",
    "bmi",
    "bne",
    "bpl",
    "bra",
    "brk",
    "brl",
    "bvc",
    "bvs",
    "clc",
    "cld",
    "cli",
    "clv",
    "cmp",
    "cop",
    "cpx",
    "cpy",
    "dec",
    "dex",
    "dey",
    "eor",
    "inc",
    "inx",
    "iny",
    "jmp",
    "jml",
    "jsl",
    "jsr",
    "lda",
    "ldx",
    "ldy",
    "lsr",
    "mvn",
    "mvp",
    "nop",
    "ora",
    "pea",
    "pei",
    "per",
    "pha",
    "phb",
    "phd",
    "phk",
    "php",
    "phx",
    "phy",
    "pla",
    "plb",
    "pld",
    "plp",
    "plx",
    "ply",
    "rep",
    "rol",
    "ror",
    "rti",
    "rtl",
    "rts",
    "sbc",
    "sec",
    "sed",
    "sei",
    "sep",
    "sta",
    "stp",
    "stx",
    "sty",
    "stz",
    "tax",
    "tay",
    "tcd",
    "tcs",
    "tdc",
    "trb",
    "tsb",
    "tsc",
    "tsx",
    "txa",
    "txs",
    "txy",
    "tya",
    "tyx",
    "wai",
    "wdm",
    "xba",
    "xce",
}

DATA_DIRECTIVES = {"db", "dw", "dl", "dd", "byte", "word", "long"}
KNOWN_DATA_HINTS = (
    "asset",
    "audio",
    "bank-tail",
    "bank_end_tail",
    "dictionary",
    "font",
    "gfx",
    "graphics",
    "palette",
    "padding",
    "payload",
    "script",
    "sprite",
    "table",
    "text",
    "tile",
    "tail_bytes",
)
PRESERVED_HINTS = ("byte_corridor", "corridor", "unknown", "unmapped")


@dataclass(frozen=True)
class SourceMetrics:
    instruction_lines: int
    data_lines: int
    code_like_lines: int
    total_relevant_lines: int


@dataclass(frozen=True)
class RangeAudit:
    bank: str
    start: str
    end: str
    size: int
    source_path: str
    subsystem: str
    category: str
    reason: str
    instruction_lines: int
    data_lines: int


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def strip_inline_comment(line: str) -> str:
    return line.split(";", 1)[0].strip()


def line_token(line: str) -> str | None:
    stripped = strip_inline_comment(line).lower()
    if not stripped:
        return None
    if stripped.endswith(":") or "=" in stripped:
        return None
    match = re.match(r"([.a-z_][.a-z0-9_]*)\b", stripped)
    return match.group(1).lstrip(".") if match else None


def source_metrics(path: Path) -> SourceMetrics:
    if not path.exists():
        return SourceMetrics(0, 0, 0, 0)
    instruction_lines = 0
    data_lines = 0
    total_relevant_lines = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        token = line_token(line)
        if not token:
            continue
        total_relevant_lines += 1
        if token in INSTRUCTION_MNEMONICS:
            instruction_lines += 1
        elif token in DATA_DIRECTIVES:
            data_lines += 1
    return SourceMetrics(
        instruction_lines=instruction_lines,
        data_lines=data_lines,
        code_like_lines=instruction_lines,
        total_relevant_lines=total_relevant_lines,
    )


def normalized_text(*parts: str) -> str:
    return " ".join(parts).replace("\\", "/").lower()


def classify_range(row: dict[str, Any], metrics: SourceMetrics) -> tuple[str, str]:
    text = normalized_text(row.get("source_path", ""), row.get("subsystem", ""))
    has_known_data_hint = any(hint in text for hint in KNOWN_DATA_HINTS)
    has_preserved_hint = any(hint in text for hint in PRESERVED_HINTS)
    has_decoded_source_hint = "decoded-source" in text or text.endswith("-source")

    if has_known_data_hint and metrics.instruction_lines == 0:
        return "known-data-or-asset", "path/subsystem carries data, script, text, table, or asset hint"

    if has_preserved_hint and not (has_decoded_source_hint and metrics.instruction_lines > metrics.data_lines):
        return "preserved-corridor", "path/subsystem carries preserved or unknown corridor hint"

    if has_decoded_source_hint and metrics.instruction_lines > 0:
        return "decoded-asm", "source-marked file contains decoded 65816 instruction lines"

    if metrics.instruction_lines >= 2 and metrics.instruction_lines >= metrics.data_lines:
        return "decoded-asm", "contains decoded 65816 instruction lines"

    if has_known_data_hint:
        return "known-data-or-asset", "path/subsystem carries data, script, text, table, or asset hint"

    if metrics.instruction_lines >= 3:
        return "decoded-asm", "contains decoded 65816 instruction lines"

    return "preserved-corridor", "no strong decoded-source or known-data signal"


def range_audits_for_bank(bank: str) -> list[RangeAudit]:
    lower = bank.lower()
    manifest_path = ROOT / "build" / f"{lower}-build-candidate-ranges.json"
    if not manifest_path.exists():
        return []
    manifest = load_json(manifest_path)
    audits: list[RangeAudit] = []
    metrics_cache: dict[str, SourceMetrics] = {}
    for row in manifest.get("ranges", []):
        source_path = row["source_path"]
        if source_path not in metrics_cache:
            metrics_cache[source_path] = source_metrics(ROOT / source_path)
        metrics = metrics_cache[source_path]
        category, reason = classify_range(row, metrics)
        audits.append(
            RangeAudit(
                bank=bank,
                start=row["start"],
                end=row["end"],
                size=int(row["size"]),
                source_path=source_path,
                subsystem=row.get("subsystem", ""),
                category=category,
                reason=reason,
                instruction_lines=metrics.instruction_lines,
                data_lines=metrics.data_lines,
            )
        )
    return audits


def pct(part: int, whole: int) -> float:
    return round((part / whole) * 100, 2) if whole else 0.0


def summarize_bank(bank: str, audits: list[RangeAudit]) -> dict[str, Any]:
    totals = {
        "decoded_asm_bytes": 0,
        "known_data_or_asset_bytes": 0,
        "preserved_corridor_bytes": 0,
        "total_bytes": 0,
    }
    for audit in audits:
        totals["total_bytes"] += audit.size
        if audit.category == "decoded-asm":
            totals["decoded_asm_bytes"] += audit.size
        elif audit.category == "known-data-or-asset":
            totals["known_data_or_asset_bytes"] += audit.size
        else:
            totals["preserved_corridor_bytes"] += audit.size
    source_like = totals["decoded_asm_bytes"] + totals["preserved_corridor_bytes"]
    largest = sorted(
        [audit for audit in audits if audit.category == "preserved-corridor"],
        key=lambda audit: audit.size,
        reverse=True,
    )[:5]
    return {
        "bank": bank,
        **totals,
        "source_like_bytes": source_like,
        "readable_source_percent": pct(totals["decoded_asm_bytes"], source_like),
        "largest_preserved_corridors": [asdict(audit) for audit in largest],
    }


def build_report(banks: tuple[str, ...], top: int) -> dict[str, Any]:
    all_audits: list[RangeAudit] = []
    bank_rows = []
    for bank in banks:
        audits = range_audits_for_bank(bank)
        all_audits.extend(audits)
        bank_rows.append(summarize_bank(bank, audits))

    largest_corridors = sorted(
        [audit for audit in all_audits if audit.category == "preserved-corridor"],
        key=lambda audit: audit.size,
        reverse=True,
    )[:top]
    summary = {
        "banks": len(bank_rows),
        "bank_list": list(banks),
        "total_bytes": sum(row["total_bytes"] for row in bank_rows),
        "decoded_asm_bytes": sum(row["decoded_asm_bytes"] for row in bank_rows),
        "known_data_or_asset_bytes": sum(row["known_data_or_asset_bytes"] for row in bank_rows),
        "preserved_corridor_bytes": sum(row["preserved_corridor_bytes"] for row in bank_rows),
    }
    source_like = summary["decoded_asm_bytes"] + summary["preserved_corridor_bytes"]
    summary["source_like_bytes"] = source_like
    summary["readable_source_percent"] = pct(summary["decoded_asm_bytes"], source_like)
    return {
        "schema": "earthbound-decomp.readable-source-bank-closure.v1",
        "generated_by": "tools/build_readable_source_bank_closure.py",
        "summary": summary,
        "banks": bank_rows,
        "largest_preserved_corridors": [asdict(audit) for audit in largest_corridors],
    }


def render_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# Readable Source Bank Closure",
        "",
        "This report tracks the phase after byte-equivalent scaffold closure.",
        "It asks a stricter question: which source-heavy banks are represented by",
        "decoded, human-readable 65816 assembly, and which bytes are still preserved",
        "as coarse `db` corridors or known data/text/asset payloads?",
        "",
        "Generated by `tools/build_readable_source_bank_closure.py`.",
        "",
        "## Summary",
        "",
        f"- banks audited: `{', '.join(summary['bank_list'])}`",
        f"- total protected bytes audited: `{summary['total_bytes']}`",
        f"- decoded asm bytes: `{summary['decoded_asm_bytes']}`",
        f"- preserved corridor bytes: `{summary['preserved_corridor_bytes']}`",
        f"- known data/text/table/asset bytes: `{summary['known_data_or_asset_bytes']}`",
        f"- readable source percent, excluding known data/assets: `{summary['readable_source_percent']}%`",
        "",
        "Structural scaffold closure is already complete. This report is about the",
        "next milestone: readable source-bank closure.",
        "",
        "## Source-Heavy Bank Table",
        "",
        "| Bank | Decoded ASM | Preserved Corridors | Known Data/Assets | Readable Source % | Largest Preserved Corridor |",
        "| --- | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in report["banks"]:
        largest = row["largest_preserved_corridors"][0] if row["largest_preserved_corridors"] else None
        if largest:
            largest_text = f"`{largest['start']}..{largest['end']}` ({largest['size']} bytes)"
        else:
            largest_text = "-"
        lines.append(
            f"| `{row['bank']}` | {row['decoded_asm_bytes']} | {row['preserved_corridor_bytes']} | "
            f"{row['known_data_or_asset_bytes']} | {row['readable_source_percent']}% | {largest_text} |"
        )

    lines.extend(
        [
            "",
            "## Largest Preserved Corridors",
            "",
            "| Bank | Range | Bytes | Source Path | Reason | Next Action |",
            "| --- | --- | ---: | --- | --- | --- |",
        ]
    )
    for row in report["largest_preserved_corridors"]:
        next_action = corridor_next_action(row)
        lines.append(
            f"| `{row['bank']}` | `{row['start']}..{row['end']}` | {row['size']} | "
            f"`{row['source_path']}` | {row['reason']} | {next_action} |"
        )

    lines.extend(
        [
            "",
            "## How To Use This",
            "",
            "- Treat `decoded asm` as readable-source closure, not final semantic understanding.",
            "- Treat `preserved corridor` as the immediate source-bank closure queue.",
            "- Treat `known data/assets` as decoder maturity or asset-contract work, not ordinary CPU-source debt.",
            "- Regenerate after any source-promotion pass:",
            "",
            "```powershell",
            "python tools/build_readable_source_bank_closure.py",
            "```",
            "",
            "The best next closure pass should attack the largest preserved corridor that is",
            "actually source-bearing, then rerun this report and the relevant byte-equivalence",
            "validation.",
            "",
        ]
    )
    return "\n".join(lines)


def corridor_next_action(row: dict[str, Any]) -> str:
    source_path = row["source_path"].lower()
    subsystem = row["subsystem"].lower()
    text = f"{source_path} {subsystem}"
    if row["bank"] == "EF" and "unknown" in text:
        return "Split EF front run into save/debug/text/table source and data contracts."
    if "byte_corridor" in text or "corridor" in text:
        return "Decode or classify this raw byte corridor before counting it as readable source."
    if "unknown" in text or "unmapped" in text:
        return "Find refs/callers, then promote to decoded asm or typed data."
    return "Review and classify as decoded source or typed data."


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--banks",
        nargs="+",
        default=list(DEFAULT_BANKS),
        help="Banks to audit, defaulting to source-heavy C0 C1 C2 C4 EF.",
    )
    parser.add_argument("--top", type=int, default=20, help="Number of preserved corridors to list.")
    parser.add_argument(
        "--json-out",
        type=Path,
        default=ROOT / "notes" / "readable-source-bank-closure.json",
    )
    parser.add_argument(
        "--markdown-out",
        type=Path,
        default=ROOT / "notes" / "readable-source-bank-closure.md",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    banks = tuple(bank.upper() for bank in args.banks)
    report = build_report(banks, args.top)
    json_out = args.json_out if args.json_out.is_absolute() else ROOT / args.json_out
    markdown_out = args.markdown_out if args.markdown_out.is_absolute() else ROOT / args.markdown_out
    json_out.parent.mkdir(parents=True, exist_ok=True)
    markdown_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    markdown_out.write_text(render_markdown(report), encoding="utf-8", newline="\n")
    summary = report["summary"]
    print(
        "readable source closure: "
        f"{summary['decoded_asm_bytes']} decoded asm bytes, "
        f"{summary['preserved_corridor_bytes']} preserved corridor bytes, "
        f"{summary['known_data_or_asset_bytes']} known data/asset bytes."
    )
    print(f"readable source percent: {summary['readable_source_percent']}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
