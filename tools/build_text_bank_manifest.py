from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import disasm_ebtext_script as ebscript
import find_ebtext_command
import rom_tools


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_YML = ROOT / "refs" / "ebsrc-main" / "ebsrc-main" / "earthbound.yml"
BANK_CONFIG_TEMPLATE = ROOT / "refs" / "ebsrc-main" / "ebsrc-main" / "src" / "bankconfig" / "US" / "bank{index}.asm"
LOCALE_INCLUDE_RE = re.compile(r'LOCALEINCLUDE\s+"text_data/([^"]+)\.ebtxt"', re.IGNORECASE)
SEGMENT_RE = re.compile(r'\.SEGMENT\s+"([^"]+)"', re.IGNORECASE)
RENAME_LABEL_SEGMENT_RE = re.compile(r"^\s{2}([A-Za-z0-9_]+):\s*$")
RENAME_LABEL_RE = re.compile(r"^\s{4}0x([0-9A-Fa-f]+):\s*([A-Za-z_][A-Za-z0-9_]*)\s*$")


@dataclass(frozen=True)
class BankTextInclude:
    order: int
    segment_group: str
    name: str


@dataclass(frozen=True)
class TextSegmentMeta:
    name: str
    offset: int
    size: int
    compressed: bool

    @property
    def cpu_start(self) -> str:
        return cpu_for_file_offset(self.offset)

    @property
    def cpu_end(self) -> str:
        return cpu_for_file_offset(self.offset + self.size - 1)


def bank_index(bank: str) -> str:
    bank = bank.upper()
    if bank.startswith("C"):
        return f"{int(bank, 16) - 0xC0:02X}"
    return bank[-2:]


def cpu_for_file_offset(offset: int) -> str:
    return f"{rom_tools.canonical_bank_for_file_offset(offset):02X}:{offset & 0xFFFF:04X}"


def parse_bank_includes(bank: str) -> list[BankTextInclude]:
    config = BANK_CONFIG_TEMPLATE.with_name(f"bank{bank_index(bank)}.asm")
    includes: list[BankTextInclude] = []
    current_segment = ""
    for raw_line in config.read_text(encoding="utf-8", errors="ignore").splitlines():
        segment_match = SEGMENT_RE.search(raw_line)
        if segment_match:
            current_segment = segment_match.group(1)
            continue
        include_match = LOCALE_INCLUDE_RE.search(raw_line)
        if include_match:
            includes.append(
                BankTextInclude(
                    order=len(includes),
                    segment_group=current_segment,
                    name=include_match.group(1),
                )
            )
    return includes


def parse_text_segment_meta(yml_path: Path) -> dict[str, TextSegmentMeta]:
    metas: dict[str, TextSegmentMeta] = {}
    current: dict[str, object] | None = None
    in_text_data = False

    def flush() -> None:
        nonlocal current
        if not in_text_data or not current:
            current = None
            return
        if {"name", "offset", "size", "compressed"} <= set(current):
            name = str(current["name"])
            metas[name] = TextSegmentMeta(
                name=name,
                offset=int(current["offset"]),
                size=int(current["size"]),
                compressed=bool(current["compressed"]),
            )
        current = None

    for raw_line in yml_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        stripped = raw_line.strip()
        if stripped.startswith("- subdir:"):
            flush()
            in_text_data = "text_data" in stripped
            current = {} if in_text_data else None
            continue
        if not in_text_data or current is None:
            continue
        if stripped.startswith("name:"):
            current["name"] = stripped.split(":", 1)[1].strip().strip("'\"")
        elif stripped.startswith("offset:"):
            current["offset"] = int(stripped.split(":", 1)[1].strip(), 0)
        elif stripped.startswith("size:"):
            current["size"] = int(stripped.split(":", 1)[1].strip(), 0)
        elif stripped.startswith("compressed:"):
            value = stripped.split(":", 1)[1].strip().lower()
            current["compressed"] = value == "true"
    flush()
    return metas


def parse_rename_labels(yml_path: Path) -> dict[str, list[tuple[int, str]]]:
    labels: dict[str, list[tuple[int, str]]] = {}
    in_rename_labels = False
    current_segment: str | None = None

    for raw_line in yml_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if raw_line.startswith("renameLabels:"):
            in_rename_labels = True
            current_segment = None
            continue
        if not in_rename_labels:
            continue
        if raw_line and not raw_line.startswith(" "):
            current_segment = None
            continue
        segment_match = RENAME_LABEL_SEGMENT_RE.match(raw_line)
        if segment_match:
            current_segment = segment_match.group(1)
            labels.setdefault(current_segment, [])
            continue
        label_match = RENAME_LABEL_RE.match(raw_line)
        if label_match and current_segment is not None:
            labels.setdefault(current_segment, []).append(
                (int(label_match.group(1), 16), label_match.group(2))
            )

    for values in labels.values():
        values.sort()
    return labels


def analyze_segment(rom: bytes, meta: TextSegmentMeta) -> dict[str, object]:
    data = rom[meta.offset:meta.offset + meta.size]
    top = Counter()
    sub = Counter()
    text_runs = 0
    command_count = 0
    truncated = 0
    unknown = 0
    unknown_samples: list[dict[str, object]] = []
    largest_text_run = 0
    i = 0
    start_address = (rom_tools.canonical_bank_for_file_offset(meta.offset) << 16) | (meta.offset & 0xFFFF)

    while i < len(data):
        if data[i] >= 0x20:
            _, size = ebscript.decode_text_run(data, i)
            text_runs += 1
            largest_text_run = max(largest_text_run, size)
            i += max(size, 1)
            continue
        op = data[i]
        top[op] += 1
        command_count += 1
        is_unknown = False
        subop: int | None = None
        if op in ebscript.SUBCOMMAND_NAMES and i + 1 < len(data):
            subop = data[i + 1]
            sub[(op, subop)] += 1
            if subop not in ebscript.SUBCOMMAND_NAMES[op]:
                is_unknown = True
        elif op not in ebscript.TOP_LEVEL_NAMES:
            is_unknown = True
        if is_unknown:
            unknown += 1
            if len(unknown_samples) < 32:
                sample: dict[str, object] = {
                    "cpu": f"{(start_address + i) >> 16:02X}:{(start_address + i) & 0xFFFF:04X}",
                    "opcode": f"0x{op:02X}",
                    "name": find_ebtext_command.command_name_for(op, subop),
                }
                if subop is not None:
                    sample["subopcode"] = f"0x{subop:02X}"
                unknown_samples.append(sample)
        try:
            _, size = ebscript.parse_command(data, i)
        except IndexError:
            truncated += 1
            break
        if size <= 0:
            size = 1
        i += size

    top_items = [
        {
            "opcode": f"0x{op:02X}",
            "name": find_ebtext_command.command_name_for(op, None),
            "count": count,
        }
        for op, count in top.most_common()
    ]
    sub_items = [
        {
            "opcode": f"0x{op:02X}",
            "subopcode": f"0x{subop:02X}",
            "name": find_ebtext_command.command_name_for(op, subop),
            "count": count,
        }
        for (op, subop), count in sub.most_common()
    ]

    return {
        "cpu_start": f"{(start_address >> 16) & 0xFF:02X}:{start_address & 0xFFFF:04X}",
        "text_runs": text_runs,
        "largest_text_run": largest_text_run,
        "commands": command_count,
        "unknown_commands": unknown,
        "unknown_command_samples": unknown_samples,
        "truncated_commands": truncated,
        "top_opcodes": top_items,
        "top_subcommands": sub_items,
    }


def build_manifest(bank: str, yml_path: Path, rom_path: Path) -> dict[str, object]:
    rom = rom_tools.load_rom(rom_path)
    includes = parse_bank_includes(bank)
    metas = parse_text_segment_meta(yml_path)
    labels = parse_rename_labels(yml_path)
    segments: list[dict[str, object]] = []
    bank_start = int(bank_index(bank), 16) * 0x10000
    bank_end = bank_start + 0x10000 - 1
    covered_ranges: list[tuple[int, int, str]] = []

    for include in includes:
        meta = metas.get(include.name)
        if meta is None:
            segments.append(
                {
                    "order": include.order,
                    "bank_segment": include.segment_group,
                    "name": include.name,
                    "error": "missing yml text_data entry",
                }
            )
            continue
        segment_labels = labels.get(include.name, [])
        public_labels = [name for _, name in segment_labels if not name.startswith("_")]
        private_labels = [name for _, name in segment_labels if name.startswith("_")]
        analysis = analyze_segment(rom, meta)
        covered_ranges.append((meta.offset, meta.offset + meta.size - 1, include.name))
        segments.append(
            {
                "order": include.order,
                "bank_segment": include.segment_group,
                "name": include.name,
                "file_offset": f"0x{meta.offset:06X}",
                "size": meta.size,
                "cpu_start": meta.cpu_start,
                "cpu_end": meta.cpu_end,
                "compressed": meta.compressed,
                "labels": len(segment_labels),
                "public_labels": len(public_labels),
                "private_labels": len(private_labels),
                "first_labels": [
                    {
                        "offset": f"0x{offset:04X}",
                        "cpu": cpu_for_file_offset(meta.offset + offset),
                        "name": name,
                    }
                    for offset, name in segment_labels[:8]
                ],
                "analysis": analysis,
            }
        )

    coverage_gaps: list[dict[str, object]] = []
    cursor = bank_start
    for start, end, _name in sorted(covered_ranges):
        if start > cursor:
            coverage_gaps.append(
                {
                    "file_start": f"0x{cursor:06X}",
                    "file_end": f"0x{start - 1:06X}",
                    "cpu_start": cpu_for_file_offset(cursor),
                    "cpu_end": cpu_for_file_offset(start - 1),
                    "size": start - cursor,
                }
            )
        cursor = max(cursor, end + 1)
    if cursor <= bank_end:
        coverage_gaps.append(
            {
                "file_start": f"0x{cursor:06X}",
                "file_end": f"0x{bank_end:06X}",
                "cpu_start": cpu_for_file_offset(cursor),
                "cpu_end": cpu_for_file_offset(bank_end),
                "size": bank_end - cursor + 1,
            }
        )

    return {
        "schema": "earthbound-decomp.text-bank.v1",
        "bank": bank.upper(),
        "bank_index": bank_index(bank),
        "config": str(BANK_CONFIG_TEMPLATE.with_name(f"bank{bank_index(bank)}.asm").relative_to(ROOT)),
        "yml": str(yml_path.relative_to(ROOT)) if yml_path.is_relative_to(ROOT) else str(yml_path),
        "rom": str(rom_path.relative_to(ROOT)) if rom_path.is_relative_to(ROOT) else str(rom_path),
        "summary": {
            "segments": len(segments),
            "bytes": sum(int(segment.get("size", 0)) for segment in segments),
            "coverage_gaps": len(coverage_gaps),
            "coverage_gap_bytes": sum(int(gap["size"]) for gap in coverage_gaps),
            "labels": sum(int(segment.get("labels", 0)) for segment in segments),
            "commands": sum(int(segment.get("analysis", {}).get("commands", 0)) for segment in segments),
            "unknown_commands": sum(int(segment.get("analysis", {}).get("unknown_commands", 0)) for segment in segments),
        },
        "segments": segments,
        "coverage_gaps": coverage_gaps,
    }


def render_markdown(manifest: dict[str, object]) -> str:
    segments = manifest["segments"]
    assert isinstance(segments, list)
    summary = manifest["summary"]
    assert isinstance(summary, dict)

    lines = [
        f"# Bank {manifest['bank']} Text Data Map",
        "",
        "Generated by `tools/build_text_bank_manifest.py` from the ebsrc US bank config, `earthbound.yml`, and the local ROM.",
        "",
        "## Summary",
        "",
        f"- bank: `{manifest['bank']}` / reference bank `{manifest['bank_index']}`",
        f"- text segments: `{summary['segments']}`",
        f"- total bytes: `{summary['bytes']}`",
        f"- non-locale/gap bytes: `{summary.get('coverage_gap_bytes', 0)}` across `{summary.get('coverage_gaps', 0)}` gaps",
        f"- labels: `{summary['labels']}`",
        f"- parsed control commands: `{summary['commands']}`",
        f"- unknown parsed commands: `{summary['unknown_commands']}`",
        "",
        "## Segment Overview",
        "",
        "| Order | Segment | Bank segment | CPU span | File offset | Bytes | Labels | Commands | Unknown commands | Top opcodes |",
        "| ---: | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |",
    ]

    for segment in segments:
        assert isinstance(segment, dict)
        analysis = segment.get("analysis", {})
        assert isinstance(analysis, dict)
        top_opcodes = analysis.get("top_opcodes", [])
        assert isinstance(top_opcodes, list)
        top_bits = []
        for item in top_opcodes[:5]:
            assert isinstance(item, dict)
            top_bits.append(f"`{item['opcode']}` {item['name']} ({item['count']})")
        lines.append(
            "| {order} | `{name}` | `{bank_segment}` | `{cpu_start}..{cpu_end}` | `{file_offset}` | {size} | {labels} | {commands} | {unknown} | {top} |".format(
                order=segment["order"],
                name=segment["name"],
                bank_segment=segment["bank_segment"],
                cpu_start=segment.get("cpu_start", "?"),
                cpu_end=segment.get("cpu_end", "?"),
                file_offset=segment.get("file_offset", "?"),
                size=segment.get("size", "?"),
                labels=segment.get("labels", "?"),
                commands=analysis.get("commands", "?"),
                unknown=analysis.get("unknown_commands", "?"),
                top=", ".join(top_bits) or "-",
            )
        )

    coverage_gaps = manifest.get("coverage_gaps", [])
    assert isinstance(coverage_gaps, list)
    if coverage_gaps:
        lines.extend(
            [
                "",
                "## Coverage Gaps",
                "",
                "These spans are not covered by locale text-data entries in this bank. They may be support data includes, alignment/padding, or tail slack; cross-check the bank config before assigning semantics.",
                "",
                "| CPU span | File span | Bytes |",
                "| --- | --- | ---: |",
            ]
        )
        for gap in coverage_gaps:
            assert isinstance(gap, dict)
            lines.append(
                f"| `{gap['cpu_start']}..{gap['cpu_end']}` | `{gap['file_start']}..{gap['file_end']}` | {gap['size']} |"
            )

    unknown_rows: list[tuple[str, dict[str, object]]] = []
    for segment in segments:
        assert isinstance(segment, dict)
        analysis = segment.get("analysis", {})
        assert isinstance(analysis, dict)
        for item in analysis.get("top_subcommands", []):
            assert isinstance(item, dict)
            if str(item.get("name", "")).startswith("UNKNOWN"):
                unknown_rows.append((str(segment["name"]), item))
    if unknown_rows:
        lines.extend(
            [
                "",
                "## Unknown Parser Hits",
                "",
                "These are parsed command starts whose subcommand byte is not in the local text-command map yet. In dense text data, especially debug/event script regions, these should be treated as candidates for parser desync until checked from a known label boundary.",
                "",
                "| Segment | Opcode | Subopcode | Name | Count | Samples |",
                "| --- | --- | --- | --- | ---: | --- |",
            ]
        )
        for segment_name, item in sorted(unknown_rows, key=lambda row: (-int(row[1]["count"]), row[0], row[1]["name"])):
            samples: list[str] = []
            for segment in segments:
                assert isinstance(segment, dict)
                if segment["name"] != segment_name:
                    continue
                analysis = segment.get("analysis", {})
                assert isinstance(analysis, dict)
                for sample in analysis.get("unknown_command_samples", []):
                    assert isinstance(sample, dict)
                    if sample.get("name") == item["name"]:
                        samples.append(str(sample["cpu"]))
            lines.append(
                f"| `{segment_name}` | `{item['opcode']}` | `{item['subopcode']}` | `{item['name']}` | {item['count']} | {', '.join(f'`{sample}`' for sample in samples[:5]) or '-'} |"
            )

    lines.extend(["", "## Segments", ""])

    for segment in segments:
        assert isinstance(segment, dict)
        analysis = segment.get("analysis", {})
        assert isinstance(analysis, dict)
        lines.extend(
            [
                f"### {segment['name']}",
                "",
                f"- bank segment: `{segment['bank_segment']}`",
                f"- CPU span: `{segment.get('cpu_start', '?')}..{segment.get('cpu_end', '?')}`",
                f"- file offset: `{segment.get('file_offset', '?')}`",
                f"- bytes: `{segment.get('size', '?')}`",
                f"- labels: `{segment.get('labels', '?')}` (`{segment.get('public_labels', '?')}` public, `{segment.get('private_labels', '?')}` private/internal)",
                f"- text runs: `{analysis.get('text_runs', '?')}`; largest text run: `{analysis.get('largest_text_run', '?')}` bytes",
                f"- parsed commands: `{analysis.get('commands', '?')}`; unknown commands: `{analysis.get('unknown_commands', '?')}`; truncated commands: `{analysis.get('truncated_commands', '?')}`",
                "",
                "First labels:",
                "",
            ]
        )
        first_labels = segment.get("first_labels", [])
        assert isinstance(first_labels, list)
        for label in first_labels:
            assert isinstance(label, dict)
            lines.append(f"- `{label['cpu']}` `{label['name']}` ({label['offset']})")
        if not first_labels:
            lines.append("- none")

        lines.extend(["", "Top opcodes:", ""])
        top_opcodes = analysis.get("top_opcodes", [])
        assert isinstance(top_opcodes, list)
        for item in top_opcodes[:12]:
            assert isinstance(item, dict)
            lines.append(f"- `{item['opcode']}` `{item['name']}`: `{item['count']}`")
        if not top_opcodes:
            lines.append("- none")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a manifest for one ebsrc locale text-data bank.")
    parser.add_argument("bank", help="Canonical bank, for example C5.")
    parser.add_argument("--rom", help="Optional explicit ROM path.")
    parser.add_argument("--yml", default=str(DEFAULT_YML), help="Path to earthbound.yml.")
    parser.add_argument("--json-out", help="Output JSON path.")
    parser.add_argument("--markdown-out", help="Output Markdown path.")
    args = parser.parse_args()

    bank = args.bank.upper()
    yml_path = Path(args.yml)
    rom_path = rom_tools.find_rom(args.rom)
    manifest = build_manifest(bank, yml_path, rom_path)

    if args.json_out:
        json_path = Path(args.json_out)
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    if args.markdown_out:
        markdown_path = Path(args.markdown_out)
        markdown_path.parent.mkdir(parents=True, exist_ok=True)
        markdown_path.write_text(render_markdown(manifest), encoding="utf-8")

    summary = manifest["summary"]
    assert isinstance(summary, dict)
    print(
        f"Bank {bank}: {summary['segments']} text segments, "
        f"{summary['bytes']} bytes, {summary['labels']} labels, "
        f"{summary['commands']} parsed commands, {summary['unknown_commands']} unknown commands"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
