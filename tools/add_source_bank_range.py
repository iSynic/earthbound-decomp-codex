from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from rom_tools import find_rom, hirom_to_file_offset, load_rom


ROOT = Path(__file__).resolve().parent.parent


def parse_bank_address(raw: str) -> tuple[int, int]:
    bank, address = raw.split(":", 1)
    return int(bank, 16), int(address, 16)


def ranges_overlap(left_start: str, left_end: str, right_start: str, right_end: str) -> bool:
    left_bank, left_start_address = parse_bank_address(left_start)
    left_end_bank, left_end_address = parse_bank_address(left_end)
    right_bank, right_start_address = parse_bank_address(right_start)
    right_end_bank, right_end_address = parse_bank_address(right_end)
    if left_bank != left_end_bank or right_bank != right_end_bank:
        raise SystemExit("overlap replacement only supports same-bank ranges")
    if left_bank != right_bank:
        return False
    return left_start_address < right_end_address and right_start_address < left_end_address


def rom_bytes_for_range(rom: bytes, start: str, end: str) -> bytes:
    start_bank, start_address = parse_bank_address(start)
    end_bank, end_address = parse_bank_address(end)
    if start_bank != end_bank:
        raise SystemExit(f"range crosses banks: {start}..{end}")
    start_offset = hirom_to_file_offset(start_bank, start_address, len(rom))
    end_offset = hirom_to_file_offset(end_bank, end_address, len(rom))
    if start_offset is None or end_offset is None:
        raise SystemExit(f"could not convert {start}..{end} to ROM offsets")
    return rom[start_offset:end_offset]


def file_offset_for_address(rom: bytes, address: str) -> str:
    bank, addr = parse_bank_address(address)
    offset = hirom_to_file_offset(bank, addr, len(rom))
    if offset is None:
        raise SystemExit(f"could not convert {address} to ROM offset")
    return f"0x{offset:06X}"


def byte_preview(data: bytes, *, tail: bool = False) -> str:
    chunk = data[-16:] if tail else data[:16]
    return " ".join(f"{byte:02X}" for byte in chunk)


def recalculate_summary(manifest: dict[str, Any]) -> None:
    ranges = sorted(
        manifest.get("ranges", []),
        key=lambda item: parse_bank_address(item["start"]),
    )
    manifest["ranges"] = ranges
    total = sum(int(item["size"]) for item in ranges)
    source = sum(int(item.get("source_size", item["size"])) for item in ranges)
    data_gap = sum(int(item.get("data_gap_size", 0)) for item in ranges)
    manifest["summary"] = {
        "ranges": len(ranges),
        "total_bytes": total,
        "source_bytes": source,
        "data_gap_bytes": data_gap,
    }


def build_entry(args: argparse.Namespace, rom: bytes) -> dict[str, Any]:
    data = rom_bytes_for_range(rom, args.start, args.end)
    digest = hashlib.sha1(data).hexdigest()
    evidence = args.evidence or []
    segments = build_segments(args, rom, evidence)
    source_segments = [segment for segment in segments if segment["kind"] == "source"]
    data_gaps = [segment for segment in segments if segment["kind"] == "data-gap"]
    labels = [label for segment in segments for label in segment.get("labels", [])]
    if not labels:
        labels = [f"{args.start} {args.name}"]
    return {
        "source_path": args.source_path.as_posix(),
        "subsystem": args.subsystem,
        "level": "build-candidate",
        "start": args.start,
        "end": args.end,
        "size": len(data),
        "file_offset_start": file_offset_for_address(rom, args.start),
        "file_offset_end": file_offset_for_address(rom, args.end),
        "sha1": digest,
        "first_bytes": byte_preview(data),
        "last_bytes": byte_preview(data, tail=True),
        "labels": labels,
        "evidence": evidence,
        "source_size": sum(int(segment["size"]) for segment in source_segments),
        "data_gap_size": sum(int(segment["size"]) for segment in data_gaps),
        "source_segments": source_segments,
        "data_gaps": data_gaps,
    }


def parse_segment(raw: str) -> tuple[str, str, str]:
    parts = raw.split(",", 2)
    if len(parts) != 3:
        raise SystemExit(
            "--source-segment/--data-gap must look like START,END,Name"
        )
    start, end, name = (part.strip() for part in parts)
    if not start or not end or not name:
        raise SystemExit(
            "--source-segment/--data-gap must look like START,END,Name"
        )
    return start, end, name


def build_segment(
    *,
    kind: str,
    start: str,
    end: str,
    name: str,
    rom: bytes,
    evidence: list[str],
) -> dict[str, Any]:
    data = rom_bytes_for_range(rom, start, end)
    digest = hashlib.sha1(data).hexdigest()
    label = f"{start} {name}"
    segment = {
        "kind": kind,
        "start": start,
        "end": end,
        "size": len(data),
        "file_offset_start": file_offset_for_address(rom, start),
        "file_offset_end": file_offset_for_address(rom, end),
        "sha1": digest,
        "first_bytes": byte_preview(data),
        "last_bytes": byte_preview(data, tail=True),
        "name": name,
        "labels": [label],
        "evidence": evidence,
    }
    return segment


def build_segments(args: argparse.Namespace, rom: bytes, evidence: list[str]) -> list[dict[str, Any]]:
    if not args.source_segment and not args.data_gap:
        return [
            build_segment(
                kind="source",
                start=args.start,
                end=args.end,
                name=args.name,
                rom=rom,
                evidence=evidence,
            )
        ]

    segments: list[dict[str, Any]] = []
    for raw in args.source_segment:
        start, end, name = parse_segment(raw)
        segments.append(
            build_segment(
                kind="source",
                start=start,
                end=end,
                name=name,
                rom=rom,
                evidence=evidence,
            )
        )
    for raw in args.data_gap:
        start, end, name = parse_segment(raw)
        segments.append(
            build_segment(
                kind="data-gap",
                start=start,
                end=end,
                name=name,
                rom=rom,
                evidence=evidence,
            )
        )
    segments.sort(key=lambda item: parse_bank_address(item["start"]))
    return segments


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Append or replace one build-candidate source range manifest entry."
    )
    parser.add_argument("--bank", required=True)
    parser.add_argument("--source-path", type=Path, required=True)
    parser.add_argument("--subsystem", required=True)
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument(
        "--source-segment",
        action="append",
        default=[],
        help="optional START,END,Name source segment inside the range",
    )
    parser.add_argument(
        "--data-gap",
        action="append",
        default=[],
        help="optional START,END,Name preserved data gap inside the range",
    )
    parser.add_argument("--evidence", action="append", default=[])
    parser.add_argument("--rom")
    parser.add_argument("--manifest", type=Path)
    parser.add_argument(
        "--replace-overlaps",
        action="store_true",
        help="remove any existing manifest ranges that overlap the new range",
    )
    args = parser.parse_args()

    bank = args.bank.lower()
    manifest_path = args.manifest or ROOT / "build" / f"{bank}-build-candidate-ranges.json"
    if not manifest_path.is_absolute():
        manifest_path = ROOT / manifest_path

    rom = load_rom(find_rom(args.rom))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    entry = build_entry(args, rom)
    ranges = []
    for item in manifest.get("ranges", []):
        if item.get("source_path") == entry["source_path"]:
            continue
        if args.replace_overlaps and ranges_overlap(
            item["start"],
            item["end"],
            entry["start"],
            entry["end"],
        ):
            continue
        ranges.append(item)
    ranges.append(entry)
    manifest["ranges"] = ranges
    recalculate_summary(manifest)
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(
        "wrote {path}: {source} {start}..{end} ({size} bytes)".format(
            path=manifest_path.relative_to(ROOT),
            source=entry["source_path"],
            start=entry["start"],
            end=entry["end"],
            size=entry["size"],
        )
    )


if __name__ == "__main__":
    main()
