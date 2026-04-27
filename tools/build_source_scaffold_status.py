#!/usr/bin/env python3
"""Summarize source-bank scaffold coverage and byte-equivalence status."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
BANKS = [f"{value:02X}" for value in range(0xC0, 0xF0)]


def load_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def bank_row(bank: str) -> dict[str, Any]:
    lower = bank.lower()
    ranges = load_json(ROOT / "build" / f"{lower}-build-candidate-ranges.json")
    residual = load_json(ROOT / "build" / f"{lower}-source-residual-map.json")
    validation = load_json(ROOT / "build" / f"{lower}-byte-equivalence-validation.json")
    scaffold = ROOT / "src" / lower / f"bank_{lower}_helpers_asar.asm"
    if not ranges or not residual:
        return {
            "bank": bank,
            "status": "open",
            "ranges": 0,
            "protected_bytes": 0,
            "residual_bytes": 65536,
            "byte_equivalence": "not-run",
            "mismatches": None,
            "scaffold": None,
        }

    residual_summary = residual["summary"]
    validation_summary = validation["summary"] if validation else {}
    closed = residual_summary["residual_bytes"] == 0
    ok = validation_summary.get("status") == "OK"
    return {
        "bank": bank,
        "status": "closed" if closed and ok else "partial",
        "ranges": ranges["summary"]["ranges"],
        "protected_bytes": residual_summary["protected_bytes"],
        "residual_bytes": residual_summary["residual_bytes"],
        "byte_equivalence": validation_summary.get("status", "not-run"),
        "mismatches": validation_summary.get("mismatch_count"),
        "scaffold": scaffold.relative_to(ROOT).as_posix() if scaffold.exists() else None,
    }


def build_status() -> dict[str, Any]:
    rows = [bank_row(bank) for bank in BANKS]
    closed = [row for row in rows if row["status"] == "closed"]
    partial = [row for row in rows if row["status"] == "partial"]
    open_rows = [row for row in rows if row["status"] == "open"]
    return {
        "schema": "earthbound-decomp.source-scaffold-status.v1",
        "generated_by": "tools/build_source_scaffold_status.py",
        "summary": {
            "banks": len(rows),
            "closed": len(closed),
            "partial": len(partial),
            "open": len(open_rows),
            "closed_banks": [row["bank"] for row in closed],
            "partial_banks": [row["bank"] for row in partial],
            "open_banks": [row["bank"] for row in open_rows],
        },
        "banks": rows,
    }


def render_markdown(status: dict[str, Any]) -> str:
    summary = status["summary"]
    open_banks = summary["open_banks"]
    next_frontier = [
        "",
        "## Next Frontier",
        "",
    ]
    if open_banks:
        next_frontier.append(
            f"- Open byte-scaffold banks: `{', '.join(open_banks)}`."
        )
    else:
        next_frontier.append("- Every bank has a closed byte-equivalent source scaffold.")
        next_frontier.append(
            "- The next frontier is semantic source conversion, especially the source-heavy C0-C2 runtime banks."
        )
    if {"C0", "C1", "C2"}.intersection(open_banks):
        next_frontier.append(
            "- `C0`, `C1`, and `C2` are source-heavy runtime banks and should stay on the source extraction track."
        )
    next_frontier.extend(
        [
            "- Byte scaffold closure is structural closure, not full semantic source completion.",
            "- Closed asset/table banks can still use typed emitter polish, render/decode fixtures, and stronger consumer comments.",
            "",
        ]
    )
    lines = [
        "# Source Scaffold Status",
        "",
        "This report summarizes bank-level source-scaffold coverage and byte-equivalence status.",
        "",
        "## Summary",
        "",
        f"- banks checked: `{summary['banks']}`",
        f"- closed banks: `{summary['closed']}`",
        f"- partial banks: `{summary['partial']}`",
        f"- open banks: `{summary['open']}`",
        f"- open bank list: `{', '.join(summary['open_banks']) or 'none'}`",
        "",
        "## Bank Table",
        "",
        "| Bank | Status | Ranges | Protected Bytes | Residual Bytes | Byte Equivalence | Mismatches | Scaffold |",
        "| --- | --- | ---: | ---: | ---: | --- | ---: | --- |",
    ]
    for row in status["banks"]:
        mismatches = "-" if row["mismatches"] is None else str(row["mismatches"])
        scaffold = f"`{row['scaffold']}`" if row["scaffold"] else "-"
        lines.append(
            f"| `{row['bank']}` | `{row['status']}` | {row['ranges']} | {row['protected_bytes']} | {row['residual_bytes']} | `{row['byte_equivalence']}` | {mismatches} | {scaffold} |"
        )
    lines.extend(next_frontier)
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json-out", type=Path, default=ROOT / "build" / "source-scaffold-status.json")
    parser.add_argument("--markdown-out", type=Path, default=ROOT / "notes" / "source-scaffold-status.md")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    json_out = args.json_out if args.json_out.is_absolute() else ROOT / args.json_out
    markdown_out = args.markdown_out if args.markdown_out.is_absolute() else ROOT / args.markdown_out
    status = build_status()
    json_out.parent.mkdir(parents=True, exist_ok=True)
    markdown_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8")
    markdown_out.write_text(render_markdown(status), encoding="utf-8", newline="\n")
    summary = status["summary"]
    print(
        f"source scaffold status: {summary['closed']} closed, "
        f"{summary['partial']} partial, {summary['open']} open."
    )
    print(f"open banks: {', '.join(summary['open_banks']) or 'none'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
