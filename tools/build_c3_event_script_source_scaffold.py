from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from rom_tools import find_rom, hirom_to_file_offset, load_rom


ROOT = Path(__file__).resolve().parent.parent
BANK = "C3"
BANK_NUM = 0xC3
DEFAULT_OUTPUT = ROOT / "src" / "c3" / "bank_c3_event_scripts_source_pilot.asar.asm"
DEFAULT_MANIFEST = ROOT / "build" / "c3-event-script-source-scaffold.json"
DEFAULT_RANGES = ROOT / "build" / "c3-event-script-source-scaffold-ranges.json"
DEFAULT_REPORT = ROOT / "notes" / "c3-event-script-source-scaffold.md"
DEFAULT_START = 0x0000
DEFAULT_END = 0xE450
SCHEMA = "earthbound-decomp.c3-event-script-source-scaffold.v1"

CONST_RE = re.compile(r"^(![A-Za-z_][A-Za-z0-9_]*)\s*=\s*(\S+)\s*$")
MACRO_RE = re.compile(r"^macro\s+([A-Za-z_][A-Za-z0-9_]*)\b")
ORG_RE = re.compile(r"^org\s+\$C3([0-9A-Fa-f]{4})\s*$")
LABEL_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*):$")


@dataclass(frozen=True)
class Span:
    start: int
    end: int
    source: str
    family: str
    name: str
    size: int
    sha1: str

    @property
    def address(self) -> str:
        return f"{BANK}:{self.start:04X}..{BANK}:{self.end:04X}"


@dataclass(frozen=True)
class Gap:
    start: int
    end: int
    sha1: str

    @property
    def address(self) -> str:
        return f"{BANK}:{self.start:04X}..{BANK}:{self.end:04X}"

    @property
    def size(self) -> int:
        return self.end - self.start


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def resolve(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def parse_address(raw: str) -> int:
    bank, offset = raw.split(":", 1)
    if bank.upper() != BANK:
        raise ValueError(f"expected {BANK} address, got {raw}")
    return int(offset, 16)


def span_from_row(row: dict[str, Any], *, manifest: dict[str, Any]) -> Span:
    raw_address = str(row["address"])
    if ".." in raw_address:
        start_raw, end_raw = raw_address.split("..", 1)
        start = parse_address(start_raw)
        end = parse_address(end_raw)
    else:
        start = parse_address(raw_address)
        end = parse_address(str(row["ends_at"]))
    size = int(row["size"])
    if end - start != size:
        raise ValueError(f"{raw_address} size mismatch: {size} != {end - start}")
    return Span(
        start=start,
        end=end,
        source=str(manifest["source"]),
        family=str(manifest["family"]),
        name=str(row["name"]),
        size=size,
        sha1=str(row["sha1"]),
    )


def load_pilot_spans(manifest_glob: str) -> list[Span]:
    manifests = sorted(ROOT.glob(manifest_glob))
    spans: list[Span] = []
    for path in manifests:
        manifest = json.loads(path.read_text(encoding="utf-8"))
        if manifest.get("schema") != "earthbound-decomp.c3-event-script-source-pilot.v1":
            continue
        if manifest.get("validation", {}).get("status") != "pass":
            raise ValueError(f"{rel(path)} is not validation-pass")
        for row in manifest.get("rows", []):
            spans.append(span_from_row(row, manifest=manifest))
    return sorted(spans, key=lambda span: (span.start, span.end, span.source))


def validate_no_overlaps(spans: list[Span]) -> None:
    previous: Span | None = None
    for span in spans:
        if previous and span.start < previous.end:
            raise ValueError(f"overlap: {previous.address} ({previous.source}) vs {span.address} ({span.source})")
        previous = span


def choose_nonoverlapping_spans(spans: list[Span]) -> tuple[list[Span], list[Span]]:
    selected: list[Span] = []
    skipped: list[Span] = []
    for span in sorted(spans, key=lambda item: (item.start, -(item.end - item.start), item.source)):
        if not selected or span.start >= selected[-1].end:
            selected.append(span)
            continue
        previous = selected[-1]
        if span.end <= previous.end:
            skipped.append(span)
            continue
        raise ValueError(f"partial overlap: {previous.address} ({previous.source}) vs {span.address} ({span.source})")
    return sorted(selected, key=lambda span: (span.start, span.end, span.source)), skipped


def merged_intervals(spans: list[Span]) -> list[tuple[int, int]]:
    intervals: list[tuple[int, int]] = []
    for span in spans:
        if not intervals or span.start > intervals[-1][1]:
            intervals.append((span.start, span.end))
        else:
            start, end = intervals[-1]
            intervals[-1] = (start, max(end, span.end))
    return intervals


def gap_bytes(rom: bytes, start: int, end: int) -> bytes:
    start_offset = hirom_to_file_offset(BANK_NUM, start, len(rom))
    end_offset = hirom_to_file_offset(BANK_NUM, end, len(rom))
    if start_offset is None or end_offset is None:
        raise ValueError(f"unable to map {BANK}:{start:04X}..{BANK}:{end:04X}")
    return rom[start_offset:end_offset]


def find_gaps(spans: list[Span], rom: bytes, *, start: int, end: int) -> list[Gap]:
    gaps: list[Gap] = []
    cursor = start
    for covered_start, covered_end in merged_intervals(spans):
        if covered_start > cursor:
            raw = gap_bytes(rom, cursor, covered_start)
            gaps.append(Gap(cursor, covered_start, hashlib.sha1(raw).hexdigest()))
        cursor = max(cursor, covered_end)
    if cursor < end:
        raw = gap_bytes(rom, cursor, end)
        gaps.append(Gap(cursor, end, hashlib.sha1(raw).hexdigest()))
    return gaps


def render_db_bytes(data: bytes) -> list[str]:
    return ["    db " + ",".join(f"${byte:02X}" for byte in data[index : index + 16]) for index in range(0, len(data), 16)]


def normalize_macro_block(lines: list[str]) -> str:
    return "\n".join(line.rstrip() for line in lines).strip()


def source_slug(source: str) -> str:
    return re.sub(r"[^A-Za-z0-9_]", "_", Path(source).stem)


def collect_source_labels(path: Path, *, allowed_orgs: set[int]) -> set[str]:
    labels: set[str] = set()
    lines = path.read_text(encoding="utf-8").splitlines()
    emitting = False
    for line in lines:
        stripped = line.strip()
        org_match = ORG_RE.match(stripped)
        if org_match:
            emitting = int(org_match.group(1), 16) in allowed_orgs
            continue
        if not emitting:
            continue
        label_match = LABEL_RE.match(stripped)
        if label_match:
            labels.add(label_match.group(1))
    return labels


def rename_labels_in_line(line: str, renames: dict[str, str]) -> str:
    if not renames:
        return line
    code, separator, comment = line.partition(";")
    for old, new in sorted(renames.items(), key=lambda item: len(item[0]), reverse=True):
        code = re.sub(rf"(?<![!A-Za-z0-9_]){re.escape(old)}\b", new, code)
    return code + (separator + comment if separator else "")


def render_source_body(
    path: Path,
    *,
    constants: dict[str, str],
    macros: dict[str, str],
    allowed_orgs: set[int],
    label_renames: dict[str, str],
) -> tuple[list[str], int, int]:
    lines = path.read_text(encoding="utf-8").splitlines()
    out: list[str] = []
    skipped_constants = 0
    skipped_macros = 0
    index = 0
    while index < len(lines):
        line = lines[index]
        stripped = line.strip()
        if stripped == "hirom":
            index += 1
            continue

        org_match = ORG_RE.match(stripped)
        if org_match and int(org_match.group(1), 16) not in allowed_orgs:
            index += 1
            while index < len(lines):
                if ORG_RE.match(lines[index].strip()):
                    break
                index += 1
            continue

        const_match = CONST_RE.match(stripped)
        if const_match:
            name, value = const_match.groups()
            existing = constants.get(name)
            if existing is None:
                constants[name] = value
                out.append(rename_labels_in_line(line, label_renames))
            elif existing == value:
                skipped_constants += 1
            else:
                raise ValueError(f"constant conflict in {rel(path)}: {name} {existing} vs {value}")
            index += 1
            continue

        macro_match = MACRO_RE.match(stripped)
        if macro_match:
            name = macro_match.group(1)
            block = [line]
            index += 1
            while index < len(lines):
                block.append(lines[index])
                if lines[index].strip() == "endmacro":
                    index += 1
                    break
                index += 1
            normalized = normalize_macro_block(block)
            existing = macros.get(name)
            if existing is None:
                macros[name] = normalized
                out.extend(rename_labels_in_line(block_line, label_renames) for block_line in block)
            elif existing == normalized:
                skipped_macros += 1
            else:
                raise ValueError(f"macro conflict in {rel(path)}: {name}")
            continue

        out.append(rename_labels_in_line(line, label_renames))
        index += 1
    return out, skipped_constants, skipped_macros


def render_scaffold(spans: list[Span], gaps: list[Gap], rom: bytes, *, start: int, end: int) -> tuple[str, dict[str, int]]:
    sources = sorted({span.source for span in spans}, key=lambda source: min(span.start for span in spans if span.source == source))
    allowed_orgs_by_source = {
        source: {span.start for span in spans if span.source == source}
        for source in sources
    }
    label_sources: dict[str, list[str]] = {}
    for source in sources:
        for label in collect_source_labels(ROOT / source, allowed_orgs=allowed_orgs_by_source[source]):
            label_sources.setdefault(label, []).append(source)
    duplicate_label_renames = {
        source: {
            label: f"{source_slug(source)}_{label}"
            for label, label_owners in label_sources.items()
            if len(label_owners) > 1 and source in label_owners
        }
        for source in sources
    }
    constants: dict[str, str] = {}
    macros: dict[str, str] = {}
    skipped_constants = 0
    skipped_macros = 0
    lines = [
        "; Generated by tools/build_c3_event_script_source_scaffold.py",
        "; Durable C3 event/actionscript source-pilot integration scaffold.",
        ";",
        "; This file is included by bank_c3_helpers_asar.asm. It assembles all",
        "; validated C3 event/actionscript source pilots plus preserved raw gaps for",
        f"; {BANK}:{start:04X}..{BANK}:{end:04X}.",
        "",
        "hirom",
        "",
    ]

    for source in sources:
        path = ROOT / source
        lines.extend(["", f"; ---------------------------------------------------------------------------", f"; Source pilot: {source}", ""])
        body, const_skips, macro_skips = render_source_body(
            path,
            constants=constants,
            macros=macros,
            allowed_orgs=allowed_orgs_by_source[source],
            label_renames=duplicate_label_renames[source],
        )
        skipped_constants += const_skips
        skipped_macros += macro_skips
        lines.extend(body)

    lines.extend(["", "; ---------------------------------------------------------------------------", "; Preserved non-event/source-adjacent gaps", ""])
    for gap in gaps:
        raw = gap_bytes(rom, gap.start, gap.end)
        lines.extend([f"org ${BANK}{gap.start:04X}", f"C3{gap.start:04X}_PreservedEventScriptScaffoldGap:"])
        lines.extend(render_db_bytes(raw))
        lines.append("")

    return "\n".join(lines).rstrip() + "\n", {
        "sources": len(sources),
        "constants": len(constants),
        "macros": len(macros),
        "skipped_duplicate_constants": skipped_constants,
        "skipped_duplicate_macros": skipped_macros,
        "renamed_duplicate_labels": sum(len(renames) for renames in duplicate_label_renames.values()),
    }


def write_ranges(path: Path, output: Path, *, start: int, end: int, sha1: str) -> None:
    manifest = {
        "schema": "earthbound-decomp.c3-event-script-source-scaffold-ranges.v1",
        "generated_by": "tools/build_c3_event_script_source_scaffold.py",
        "summary": {
            "ranges": 1,
            "total_bytes": end - start,
            "source_bytes": end - start,
            "data_gap_bytes": 0,
        },
        "ranges": [
            {
                "source_path": rel(output),
                "subsystem": "C3 event/actionscript source-pilot integration scaffold",
                "level": "build-candidate",
                "start": f"{BANK}:{start:04X}",
                "end": f"{BANK}:{end:04X}",
                "size": end - start,
                "file_offset_start": f"0x{hirom_to_file_offset(BANK_NUM, start, 0x400000):06X}",
                "file_offset_end": f"0x{hirom_to_file_offset(BANK_NUM, end, 0x400000):06X}",
                "sha1": sha1,
                "labels": [],
                "data_gaps": [],
            }
        ],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def write_manifest(
    path: Path,
    *,
    output: Path,
    ranges: Path,
    spans: list[Span],
    gaps: list[Gap],
    render_stats: dict[str, int],
    skipped_spans: list[Span],
    start: int,
    end: int,
) -> dict[str, Any]:
    manifest = {
        "schema": SCHEMA,
        "generated_by": "tools/build_c3_event_script_source_scaffold.py",
        "output": rel(output),
        "ranges": rel(ranges),
        "covered_range": f"{BANK}:{start:04X}..{BANK}:{end:04X}",
        "summary": {
            "source_pilot_files": render_stats["sources"],
            "source_spans": len(spans),
            "source_bytes": sum(span.size for span in spans),
            "preserved_gap_count": len(gaps),
            "preserved_gap_bytes": sum(gap.size for gap in gaps),
            **render_stats,
            "duplicate_source_spans_skipped": len(skipped_spans),
        },
        "spans": [
            {
                "address": span.address,
                "source": span.source,
                "family": span.family,
                "name": span.name,
                "size": span.size,
                "sha1": span.sha1,
            }
            for span in spans
        ],
        "preserved_gaps": [
            {
                "address": gap.address,
                "size": gap.size,
                "sha1": gap.sha1,
            }
            for gap in gaps
        ],
        "skipped_duplicate_spans": [
            {
                "address": span.address,
                "source": span.source,
                "family": span.family,
                "name": span.name,
                "size": span.size,
                "sha1": span.sha1,
            }
            for span in skipped_spans
        ],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def write_report(path: Path, manifest: dict[str, Any]) -> None:
    summary = manifest["summary"]
    lines = [
        "# C3 Event Script Source Scaffold",
        "",
        "Generated by `tools/build_c3_event_script_source_scaffold.py`.",
        "",
        "## Summary",
        "",
        f"- Output: `{manifest['output']}`",
        f"- Range manifest: `{manifest['ranges']}`",
        f"- Covered range: `{manifest['covered_range']}`",
        f"- Source-pilot files: `{summary['source_pilot_files']}`",
        f"- Source spans: `{summary['source_spans']}`",
        f"- Source bytes: `{summary['source_bytes']}`",
        f"- Preserved raw gaps: `{summary['preserved_gap_count']}`",
        f"- Preserved raw gap bytes: `{summary['preserved_gap_bytes']}`",
        f"- Duplicate source spans skipped: `{summary['duplicate_source_spans_skipped']}`",
        f"- Unique macro definitions: `{summary['macros']}`",
        f"- Duplicate macro definitions skipped: `{summary['skipped_duplicate_macros']}`",
        f"- Duplicate local labels renamed: `{summary['renamed_duplicate_labels']}`",
        "",
        "This scaffold assembles every validated C3 event/actionscript source pilot together with the raw bytes that are not event/actionscript candidates. It is included by the canonical `src/c3/bank_c3_helpers_asar.asm` scaffold for the `C3:0000..E450` corridor.",
        "",
        "## Preserved Gaps",
        "",
        "| Range | Bytes | SHA1 |",
        "| --- | ---: | --- |",
    ]
    for gap in manifest["preserved_gaps"]:
        lines.append(f"| `{gap['address']}` | {gap['size']} | `{gap['sha1']}` |")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build a durable C3 event/actionscript source-pilot scaffold.")
    parser.add_argument("--manifest-glob", default="build/c3-*-source-pilot.json")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--ranges", type=Path, default=DEFAULT_RANGES)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--rom")
    parser.add_argument("--start", default=f"{DEFAULT_START:04X}")
    parser.add_argument("--end", default=f"{DEFAULT_END:04X}")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    start = int(str(args.start).removeprefix("0x"), 16)
    end = int(str(args.end).removeprefix("0x"), 16)
    output = resolve(args.output)
    manifest_path = resolve(args.manifest)
    ranges_path = resolve(args.ranges)
    report_path = resolve(args.report)
    rom = load_rom(find_rom(args.rom))

    spans = load_pilot_spans(args.manifest_glob)
    spans = [span for span in spans if start <= span.start and span.end <= end]
    spans, skipped_spans = choose_nonoverlapping_spans(spans)
    validate_no_overlaps(spans)
    gaps = find_gaps(spans, rom, start=start, end=end)
    text, render_stats = render_scaffold(spans, gaps, rom, start=start, end=end)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(text, encoding="utf-8")
    sha1 = hashlib.sha1(gap_bytes(rom, start, end)).hexdigest()
    write_ranges(ranges_path, output, start=start, end=end, sha1=sha1)
    manifest = write_manifest(
        manifest_path,
        output=output,
        ranges=ranges_path,
        spans=spans,
        gaps=gaps,
        render_stats=render_stats,
        skipped_spans=skipped_spans,
        start=start,
        end=end,
    )
    write_report(report_path, manifest)
    print(
        f"wrote {rel(output)}: {len(spans)} source spans, "
        f"{sum(span.size for span in spans)} source bytes, "
        f"{len(gaps)} preserved gaps / {sum(gap.size for gap in gaps)} bytes"
    )
    print(f"wrote {rel(manifest_path)}, {rel(ranges_path)}, {rel(report_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
