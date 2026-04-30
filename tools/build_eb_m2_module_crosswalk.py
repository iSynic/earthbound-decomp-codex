from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_REF_ROOT = Path("refs") / "EB-M2-Listing-v1"
DEFAULT_MANIFEST = Path("manifests") / "eb-m2-module-crosswalk.json"
DEFAULT_NOTES = Path("notes") / "eb-m2-module-crosswalk.md"

SECTION_RE = re.compile(r"^>>>\s+(.+?)\s*$")
ADDR_RE = re.compile(r"^\s*([A-F0-9]{6}):")
CORE_BANKS = ("C0", "C1", "C2", "C3", "C4", "EF")


@dataclass(frozen=True)
class Span:
    bank: str
    start: int
    end: int
    path: str
    role: str
    line: int | None = None

    @property
    def address(self) -> str:
        return f"{self.bank}:{self.start:04X}"

    @property
    def end_address(self) -> str:
        return f"{self.bank}:{self.end:04X}"

    @property
    def size(self) -> int:
        return max(0, self.end - self.start)


def bank_index_to_canonical(bank_index: int) -> str:
    return f"{0xC0 + bank_index:02X}"


def flat_to_bank_offset(flat: str) -> tuple[str, int]:
    value = int(flat, 16)
    return f"{(value >> 16) & 0xFF:02X}", value & 0xFFFF


def path_role(path: str, lines: list[str]) -> str:
    lower = path.lower()
    if lower.startswith("bankconfig/") or lower.endswith("common.asm") or "/symbols/" in lower:
        return "support"
    if "/data/" in lower or lower.startswith("data/"):
        return "data"
    byte_lines = 0
    opcode_lines = 0
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith(";") or stripped.startswith(">>>"):
            continue
        if ".INCLUDE" in stripped.upper():
            continue
        if re.search(r"\b(?:BYTE|DB|DW|DL|INCBIN)\b", stripped, re.IGNORECASE):
            byte_lines += 1
        if re.match(r"^[A-F0-9]{6}:\s+(?:[0-9A-F]{2}\s+)+\s+[A-Z]{2,4}\b", stripped):
            opcode_lines += 1
    if opcode_lines:
        return "code"
    if byte_lines:
        return "data"
    return "unknown"


def parse_eb_m2_sections(ref_root: Path, region: str) -> list[Span]:
    spans: list[Span] = []
    region_root = ref_root / region
    if not region_root.is_dir():
        raise FileNotFoundError(f"EB-M2 listing region not found: {region_root}")

    for path in sorted(region_root.glob("bank*.txt")):
        bank_index = int(path.stem.replace("bank", ""), 16)
        bank = bank_index_to_canonical(bank_index)
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        sections: list[dict[str, Any]] = []
        current: dict[str, Any] | None = None
        for line_no, line in enumerate(lines, start=1):
            section_match = SECTION_RE.match(line)
            if section_match:
                if current:
                    sections.append(current)
                current = {"path": section_match.group(1), "line": line_no, "lines": [], "addrs": []}
                continue
            if current is None:
                continue
            current["lines"].append(line)
            addr_match = ADDR_RE.match(line)
            if addr_match:
                addr_bank, offset = flat_to_bank_offset(addr_match.group(1))
                if addr_bank == bank:
                    current["addrs"].append(offset)
        if current:
            sections.append(current)

        raw_spans: list[Span] = []
        for section in sections:
            addrs = section["addrs"]
            if not addrs:
                continue
            start = min(addrs)
            role = path_role(section["path"], section["lines"])
            raw_spans.append(
                Span(
                    bank=bank,
                    start=start,
                    end=start,
                    path=section["path"],
                    role=role,
                    line=section["line"],
                )
            )

        for index, span in enumerate(raw_spans):
            later_starts = [candidate.start for candidate in raw_spans[index + 1 :] if candidate.start > span.start]
            end = min(later_starts) if later_starts else 0x10000
            if span.role == "support" or end <= span.start:
                continue
            spans.append(Span(span.bank, span.start, end, span.path, span.role, span.line))
    return spans


def parse_local_ranges(build_root: Path) -> list[Span]:
    spans: list[Span] = []
    for path in sorted(build_root.glob("*-build-candidate-ranges.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        bank = str(payload.get("bank", "")).upper()
        if not bank:
            continue
        for entry in payload.get("ranges", []):
            start_bank, start = str(entry["start"]).split(":")
            end_bank, end = str(entry["end"]).split(":")
            if start_bank.upper() != bank or end_bank.upper() != bank:
                continue
            source_path = str(entry.get("source_path", ""))
            role = "data" if "/data/" in source_path or "data" in str(entry.get("subsystem", "")).lower() else "code"
            spans.append(
                Span(
                    bank=bank,
                    start=int(start, 16),
                    end=int(end, 16),
                    path=source_path,
                    role=role,
                )
            )
    return spans


def overlaps(a: Span, b: Span) -> bool:
    return a.bank == b.bank and a.start < b.end and b.start < a.end


def classify(eb: Span, local_hits: list[Span], eb_by_local: dict[tuple[str, int, int, str], int]) -> str:
    if eb.role == "data":
        return "data-only"
    if not local_hits:
        return "absent"
    exact = [hit for hit in local_hits if hit.start == eb.start and hit.end == eb.end]
    if exact:
        return "aligned"
    if len(local_hits) > 1:
        return "split"
    hit = local_hits[0]
    local_key = (hit.bank, hit.start, hit.end, hit.path)
    if eb_by_local.get(local_key, 0) > 1:
        return "merged"
    if hit.start <= eb.start and hit.end >= eb.end:
        return "merged"
    if eb.start <= hit.start and eb.end >= hit.end:
        return "split"
    return "conflict"


def build_crosswalk(ref_root: Path, region: str) -> dict[str, Any]:
    eb_spans = parse_eb_m2_sections(ref_root, region)
    local_spans = parse_local_ranges(ROOT / "build")
    local_by_bank: dict[str, list[Span]] = {}
    for span in local_spans:
        local_by_bank.setdefault(span.bank, []).append(span)

    eb_by_local: dict[tuple[str, int, int, str], int] = {}
    for eb in eb_spans:
        for local in local_by_bank.get(eb.bank, []):
            if overlaps(eb, local):
                key = (local.bank, local.start, local.end, local.path)
                eb_by_local[key] = eb_by_local.get(key, 0) + 1

    entries: list[dict[str, Any]] = []
    by_status: dict[str, int] = {}
    by_bank: dict[str, int] = {}
    for eb in eb_spans:
        local_hits = [span for span in local_by_bank.get(eb.bank, []) if overlaps(eb, span)]
        status = classify(eb, local_hits, eb_by_local)
        by_status[status] = by_status.get(status, 0) + 1
        by_bank[eb.bank] = by_bank.get(eb.bank, 0) + 1
        entries.append(
            {
                "bank": eb.bank,
                "start": eb.address,
                "end": eb.end_address,
                "size": eb.size,
                "status": status,
                "role": eb.role,
                "eb_m2_module": eb.path,
                "eb_m2_line": eb.line,
                "local_overlaps": [
                    {
                        "start": hit.address,
                        "end": hit.end_address,
                        "size": hit.size,
                        "role": hit.role,
                        "source_path": hit.path,
                    }
                    for hit in local_hits[:8]
                ],
            }
        )

    return {
        "schema": "earthbound-decomp.eb-m2-module-crosswalk.v1",
        "generated_by": "tools/build_eb_m2_module_crosswalk.py",
        "region": region,
        "summary": {
            "entries": len(entries),
            "by_status": dict(sorted(by_status.items())),
            "by_bank": dict(sorted(by_bank.items())),
        },
        "entries": entries,
    }


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, separators=(",", ":")) + "\n", encoding="utf-8")


def write_markdown(path: Path, manifest: dict[str, Any]) -> None:
    entries = manifest["entries"]
    summary = manifest["summary"]
    lines = [
        "# EB-M2 Module Crosswalk",
        "",
        "Generated by `tools/build_eb_m2_module_crosswalk.py`.",
        "",
        "This report compares EB-M2 Listing include/module spans against local",
        "build-candidate source ranges. It is documentation-only: source files are",
        "not reorganized by this pass.",
        "",
        "## Summary",
        "",
        f"- entries: `{summary['entries']}`",
        "",
        "By status:",
        "",
    ]
    for status, count in summary["by_status"].items():
        lines.append(f"- `{status}`: `{count}`")
    lines.extend(["", "By bank:", ""])
    for bank, count in summary["by_bank"].items():
        lines.append(f"- `{bank}`: `{count}`")

    lines.extend(
        [
            "",
            "## Core-Bank Non-Aligned Examples",
            "",
            "| Start | End | Status | EB-M2 module | Local overlap |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    shown = 0
    for entry in entries:
        if entry["bank"] not in CORE_BANKS or entry["status"] == "aligned":
            continue
        local = entry["local_overlaps"][0]["source_path"] if entry["local_overlaps"] else ""
        lines.append(
            f"| `{entry['start']}` | `{entry['end']}` | `{entry['status']}` | "
            f"`{entry['eb_m2_module']}` | `{local}` |"
        )
        shown += 1
        if shown >= 80:
            break
    if shown == 0:
        lines.append("|  |  |  |  |  |")
    lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refs-root", type=Path, default=DEFAULT_REF_ROOT)
    parser.add_argument("--region", default="US", choices=("US", "JP"))
    parser.add_argument("--manifest-out", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--notes-out", type=Path, default=DEFAULT_NOTES)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    ref_root = args.refs_root if args.refs_root.is_absolute() else ROOT / args.refs_root
    manifest = build_crosswalk(ref_root, args.region)
    manifest_out = args.manifest_out if args.manifest_out.is_absolute() else ROOT / args.manifest_out
    notes_out = args.notes_out if args.notes_out.is_absolute() else ROOT / args.notes_out
    write_json(manifest_out, manifest)
    write_markdown(notes_out, manifest)
    print(f"Wrote {manifest_out.relative_to(ROOT).as_posix()} and {notes_out.relative_to(ROOT).as_posix()}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
