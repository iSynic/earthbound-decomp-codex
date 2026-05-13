from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from rom_tools import find_rom, hirom_to_file_offset, load_rom


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PLAN = ROOT / "build" / "c3-source-emission-plan.json"
SCHEMA = "earthbound-decomp.c3-build-candidate-ranges.v1"


@dataclass(frozen=True)
class RangePart:
    kind: str
    start: str
    end: str
    size: int
    file_offset_start: str
    file_offset_end: str
    sha1: str
    first_bytes: str
    last_bytes: str
    name: str | None = None
    labels: tuple[str, ...] = ()
    evidence: tuple[str, ...] = ()


@dataclass(frozen=True)
class BuildCandidateRange:
    source_path: str
    subsystem: str
    level: str | None
    start: str
    end: str
    size: int
    source_size: int
    data_gap_size: int
    file_offset_start: str
    file_offset_end: str
    sha1: str
    first_bytes: str
    last_bytes: str
    labels: tuple[str, ...]
    evidence: tuple[str, ...]
    source_segments: tuple[RangePart, ...]
    data_gaps: tuple[RangePart, ...]


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def resolve_path(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def format_address(value: int) -> str:
    return f"C3:{value:04X}"


def bytes_preview(data: bytes, count: int = 16) -> str:
    return " ".join(f"{byte:02X}" for byte in data[:count])


def rom_slice(rom: bytes, start: int, end: int) -> tuple[int, int, bytes]:
    if end <= start:
        raise ValueError(f"invalid range {start:04X}..{end:04X}")
    file_start = hirom_to_file_offset(0xC3, start, len(rom))
    file_end = hirom_to_file_offset(0xC3, end - 1, len(rom))
    if file_start is None or file_end is None:
        raise ValueError(f"range {format_address(start)}..{format_address(end)} is not mappable to ROM")
    return file_start, file_end + 1, rom[file_start : file_end + 1]


def build_part(
    *,
    kind: str,
    start: int,
    end: int,
    rom: bytes,
    name: str | None = None,
    labels: tuple[str, ...] = (),
    evidence: tuple[str, ...] = (),
) -> RangePart:
    file_start, file_end, data = rom_slice(rom, start, end)
    return RangePart(
        kind=kind,
        start=format_address(start),
        end=format_address(end),
        size=len(data),
        file_offset_start=f"0x{file_start:06X}",
        file_offset_end=f"0x{file_end:06X}",
        sha1=hashlib.sha1(data).hexdigest(),
        first_bytes=bytes_preview(data),
        last_bytes=bytes_preview(data[-16:]),
        name=name,
        labels=labels,
        evidence=tuple(dict.fromkeys(evidence)),
    )


def select_modules(plan: dict[str, Any], module_filter: str | None) -> list[dict[str, Any]]:
    modules = list(plan.get("modules", []))
    if not module_filter:
        return [module for module in modules if module.get("prototype_level") == "build-candidate"]
    needle = module_filter.lower()
    return [
        module
        for module in modules
        if needle in f"{module['source_path']} {module['subsystem']}".lower()
    ]


def build_range(module: dict[str, Any], rom: bytes) -> BuildCandidateRange:
    start = int(module["start"])
    end = module.get("end")
    if end is None:
        raise ValueError(f"{module['source_path']} has no closed range end")
    end = int(end)
    if end <= start:
        raise ValueError(f"{module['source_path']} has invalid range {start:04X}..{end:04X}")
    file_start, file_end, data = rom_slice(rom, start, end)
    labels = tuple(
        f"{label['address']} {label['name']}"
        for unit in module.get("units", [])
        for label in unit.get("labels", [])
    )
    evidence = tuple(
        str(item)
        for unit in module.get("units", [])
        for item in unit.get("evidence", [])
    )
    source_segments: list[RangePart] = []
    for unit in sorted(module.get("units", []), key=lambda item: int(item["start"])):
        unit_end = unit.get("end")
        if unit_end is None:
            raise ValueError(f"{module['source_path']} has open-ended unit {unit.get('address')}")
        unit_labels = tuple(
            f"{label['address']} {label['name']}"
            for label in unit.get("labels", [])
        )
        source_segments.append(
            build_part(
                kind="source",
                start=int(unit["start"]),
                end=int(unit_end),
                rom=rom,
                name=str(unit["name"]),
                labels=unit_labels,
                evidence=tuple(str(item) for item in unit.get("evidence", [])),
            )
        )

    data_gaps: list[RangePart] = []
    cursor = start
    for segment in source_segments:
        segment_start = int(segment.start.split(":", 1)[1], 16)
        segment_end = int(segment.end.split(":", 1)[1], 16)
        if segment_start > cursor:
            data_gaps.append(build_part(kind="data-gap", start=cursor, end=segment_start, rom=rom))
        cursor = max(cursor, segment_end)
    if cursor < end:
        data_gaps.append(build_part(kind="data-gap", start=cursor, end=end, rom=rom))

    return BuildCandidateRange(
        source_path=str(module["source_path"]),
        subsystem=str(module["subsystem"]),
        level=module.get("prototype_level"),
        start=format_address(start),
        end=format_address(end),
        size=len(data),
        source_size=sum(segment.size for segment in source_segments),
        data_gap_size=sum(gap.size for gap in data_gaps),
        file_offset_start=f"0x{file_start:06X}",
        file_offset_end=f"0x{file_end:06X}",
        sha1=hashlib.sha1(data).hexdigest(),
        first_bytes=bytes_preview(data),
        last_bytes=bytes_preview(data[-16:]),
        labels=labels,
        evidence=tuple(dict.fromkeys(evidence)),
        source_segments=tuple(source_segments),
        data_gaps=tuple(data_gaps),
    )


def build_manifest(plan_path: Path, rom_path: Path, module_filter: str | None) -> dict[str, Any]:
    plan = load_json(plan_path)
    rom = load_rom(rom_path)
    ranges = [build_range(module, rom) for module in select_modules(plan, module_filter)]
    return {
        "schema": SCHEMA,
        "generated_by": "tools/build_c3_build_candidate_ranges.py",
        "inputs": {
            "source_emission_plan": rel(plan_path),
            "rom": rel(rom_path),
            "module_filter": module_filter,
        },
        "summary": {
            "ranges": len(ranges),
            "total_bytes": sum(item.size for item in ranges),
            "source_bytes": sum(item.source_size for item in ranges),
            "data_gap_bytes": sum(item.data_gap_size for item in ranges),
        },
        "ranges": [asdict(item) for item in ranges],
    }


def render_markdown(manifest: dict[str, Any]) -> str:
    lines = [
        "# C3 build-candidate byte ranges",
        "",
        "This manifest records ROM byte ranges for C3 helper modules at build-candidate level. It pins source-emission metadata to concrete ROM slices for generated Asar companions, durable scaffold integration, and byte-equivalence validation.",
        "",
        "## Summary",
        "",
        f"- ranges: `{manifest['summary']['ranges']}`",
        f"- total bytes: `{manifest['summary']['total_bytes']}`",
        f"- source bytes: `{manifest['summary']['source_bytes']}`",
        f"- data gap bytes: `{manifest['summary']['data_gap_bytes']}`",
        "",
        "## Ranges",
        "",
        "| Level | Source Path | Range | Span Bytes | Source Bytes | Data Gap Bytes | SHA-1 |",
        "| --- | --- | --- | ---: | ---: | ---: | --- |",
    ]
    for item in manifest["ranges"]:
        lines.append(
            f"| `{item.get('level') or ''}` | `{item['source_path']}` | `{item['start']}..{item['end']}` | {item['size']} | {item['source_size']} | {item['data_gap_size']} | `{item['sha1']}` |"
        )
    lines.extend(["", "## Source Segments", ""])
    for item in manifest["ranges"]:
        lines.extend([f"### `{item['source_path']}`", ""])
        lines.extend(["| Range | Size | Name | SHA-1 |", "| --- | ---: | --- | --- |"])
        for segment in item["source_segments"]:
            lines.append(
                f"| `{segment['start']}..{segment['end']}` | {segment['size']} | `{segment.get('name') or ''}` | `{segment['sha1']}` |"
            )
        if item["data_gaps"]:
            lines.extend(["", "Data gaps inside protected span:", ""])
            for gap in item["data_gaps"]:
                lines.append(
                    f"- `{gap['start']}..{gap['end']}` ({gap['size']} bytes, SHA-1 `{gap['sha1']}`)"
                )
        lines.append("")
    lines.extend(["", "## Labels", ""])
    for item in manifest["ranges"]:
        lines.extend([f"### `{item['source_path']}`", ""])
        for label in item["labels"]:
            lines.append(f"- `{label}`")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build C3 build-candidate ROM byte range manifest.")
    parser.add_argument("--plan", type=Path, default=DEFAULT_PLAN)
    parser.add_argument("--rom", help="explicit ROM path")
    parser.add_argument("--module", help="substring filter for source path/subsystem; default: all build-candidate modules")
    parser.add_argument("--json-out", type=Path, default=ROOT / "build" / "c3-build-candidate-ranges.json")
    parser.add_argument("--markdown-out", type=Path, default=ROOT / "notes" / "c3-build-candidate-ranges.md")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    plan_path = resolve_path(args.plan)
    rom_path = find_rom(args.rom)
    manifest = build_manifest(plan_path, rom_path, args.module)

    json_out = resolve_path(args.json_out)
    json_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    markdown_out = resolve_path(args.markdown_out)
    markdown_out.parent.mkdir(parents=True, exist_ok=True)
    markdown_out.write_text(render_markdown(manifest), encoding="utf-8")

    print(
        f"Wrote {rel(json_out)} and {rel(markdown_out)} "
        f"({manifest['summary']['ranges']} range(s), {manifest['summary']['total_bytes']} bytes)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
