from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from add_source_bank_range import ROOT, build_entry, recalculate_summary
from rom_tools import find_rom, load_rom


BANK = "C3"
BANK_SIZE = 0x10000


@dataclass(frozen=True)
class Span:
    start: int
    end: int
    name: str
    extraction_class: str
    source: str
    evidence: tuple[str, ...]


@dataclass(frozen=True)
class ModulePlan:
    source_path: Path
    name: str
    title: str
    subsystem: str
    start: int
    end: int


MODULE_PLANS = [
    ModulePlan(
        source_path=Path("src/c3/script_event_payloads_0000_e450.asm"),
        name="C3EventAndScriptPayloads0000E450",
        title="event and actionscript payload corridor C3:0000..C3:E450",
        subsystem="event/actionscript payloads and source-adjacent data",
        start=0x0000,
        end=0xE450,
    ),
    ModulePlan(
        source_path=Path("src/c3/data_debug_menu_mixed_inventory_prefix.asm"),
        name="C3DebugMenuMixedInventoryDataE84EE977",
        title="debug menu mixed-data corridor C3:E84E..C3:E977",
        subsystem="debug menu mixed data before embedded inventory helpers",
        start=0xE84E,
        end=0xE977,
    ),
    ModulePlan(
        source_path=Path("src/c3/data_battle_menu_tables_ef23_f1ec.asm"),
        name="C3BattleMenuDataEF23F1EC",
        title="battle menu data corridor C3:EF23..C3:F1EC",
        subsystem="battle menu and PSI selector data",
        start=0xEF23,
        end=0xF1EC,
    ),
    ModulePlan(
        source_path=Path("src/c3/data_battle_visual_tables_f2b1_f5f9.asm"),
        name="C3BattleVisualDataF2B1F5F9",
        title="battle visual table corridor C3:F2B1..C3:F5F9",
        subsystem="battle visual table data before renderer helpers",
        start=0xF2B1,
        end=0xF5F9,
    ),
    ModulePlan(
        source_path=Path("src/c3/data_battle_tail_and_delivery_payloads_fb1f_10000.asm"),
        name="C3BattleTailAndDeliveryPayloadsFB1F10000",
        title="battle tail and delivery payload corridor C3:FB1F..bank end",
        subsystem="battle visual tail and timed delivery payloads",
        start=0xFB1F,
        end=0x10000,
    ),
]


CLASS_PREFIXES = {
    "contract-backed-data": "contract",
    "data-or-helper-frontier": "frontier",
    "effect-script-asset": "effect_script",
    "event-bytecode-asset": "event_bytecode",
    "event-bytecode-label": "event_label",
    "event-script-asset": "event_script",
    "mixed-data-source-row": "mixed",
    "movement-pattern-data": "movement",
    "null-stub": "null",
    "raw-or-named-data": "raw_data",
    "source-adjacent-data": "source_adjacent",
    "unmapped-frontier": "unmapped",
}


def parse_bank_address(raw: str) -> tuple[str, int]:
    bank, address = raw.split(":", 1)
    return bank.upper(), int(address, 16)


def format_address(value: int) -> str:
    return f"{BANK}:{value:04X}" if value <= 0xFFFF else f"{BANK}:{value:X}"


def label_for(address: int, name: str) -> str:
    if address > 0xFFFF:
        return ""
    safe = re.sub(r"[^A-Za-z0-9_]", "_", name)
    if not safe or safe[0].isdigit():
        safe = f"C3{address:04X}_{safe}"
    return f"C3{address:04X}_{safe}End"


def pascalize(raw: str) -> str:
    words = re.split(r"[^A-Za-z0-9]+", raw)
    result = "".join(word[:1].upper() + word[1:] for word in words if word)
    return result or "UnmappedFrontier"


def default_name(start: int, extraction_class: str) -> str:
    return f"C3{start:04X}{pascalize(CLASS_PREFIXES.get(extraction_class, extraction_class))}"


def span_from_row(row: dict[str, Any]) -> Span | None:
    address = row.get("address")
    next_address = row.get("next_address")
    if not address or not next_address:
        return None
    start_bank, start = parse_bank_address(address)
    end_bank, end = parse_bank_address(next_address)
    if start_bank != BANK or end_bank != BANK or end <= start:
        return None
    extraction_class = row.get("extraction_class") or "unmapped-frontier"
    if extraction_class in {"support-include", "source-helper"}:
        return None
    name = row.get("name") or default_name(start, extraction_class)
    evidence = tuple(row.get("evidence") or [])
    source = row.get("path") or row.get("source_kind") or "c3-source-data-map"
    return Span(start, end, name, extraction_class, source, evidence)


def span_from_label(label: dict[str, Any], end: int) -> Span | None:
    address = label.get("address")
    if not address:
        return None
    bank, start = parse_bank_address(address)
    if bank != BANK or start >= end:
        return None
    extraction_class = label.get("extraction_class") or "unmapped-frontier"
    if extraction_class == "source-helper":
        return None
    name = label.get("name") or default_name(start, extraction_class)
    evidence = tuple(label.get("evidence") or [])
    source = label.get("source") or "supplemental-label"
    return Span(start, end, name, extraction_class, source, evidence)


def load_spans(map_path: Path) -> tuple[list[Span], list[Span]]:
    source_map = json.loads(map_path.read_text(encoding="utf-8"))
    rows = [
        span
        for row in source_map.get("include_rows", [])
        if (span := span_from_row(row)) is not None
    ]
    supplemental = [
        span
        for label in source_map.get("supplemental_labels", [])
        if (span := span_from_label(label, BANK_SIZE)) is not None
    ]
    return rows, supplemental


def protected_intervals(manifest: dict[str, Any], *, ignore_sources: set[str]) -> list[tuple[int, int]]:
    intervals: list[tuple[int, int]] = []
    for item in manifest.get("ranges", []):
        if item.get("source_path") in ignore_sources:
            continue
        start_bank, start = parse_bank_address(item["start"])
        end_bank, end = parse_bank_address(item["end"])
        if start_bank == BANK and end_bank == BANK:
            intervals.append((start, end))
    return sorted(intervals)


def interval_is_protected(start: int, end: int, intervals: list[tuple[int, int]]) -> bool:
    return any(protected_start <= start and end <= protected_end for protected_start, protected_end in intervals)


def best_span_for_segment(start: int, end: int, spans: list[Span], supplemental: list[Span]) -> Span:
    containing = [span for span in spans if span.start <= start and end <= span.end]
    if containing:
        return min(containing, key=lambda span: (span.end - span.start, span.start))
    starting_label = [span for span in supplemental if span.start == start]
    if starting_label:
        return starting_label[0]
    return Span(
        start=start,
        end=end,
        name=default_name(start, "unmapped-frontier"),
        extraction_class="unmapped-frontier",
        source="residual-synthesis",
        evidence=("build/c3-source-residual-map.json",),
    )


def segments_for_plan(
    plan: ModulePlan,
    *,
    spans: list[Span],
    supplemental: list[Span],
    protected: list[tuple[int, int]],
) -> list[Span]:
    boundaries = {plan.start, plan.end}
    for span in spans:
        start = max(plan.start, span.start)
        end = min(plan.end, span.end)
        if start < end:
            boundaries.add(start)
            boundaries.add(end)
    for span in supplemental:
        if plan.start < span.start < plan.end:
            boundaries.add(span.start)
    for start, end in protected:
        clipped_start = max(plan.start, start)
        clipped_end = min(plan.end, end)
        if clipped_start < clipped_end:
            boundaries.add(clipped_start)
            boundaries.add(clipped_end)

    ordered = sorted(boundaries)
    segments: list[Span] = []
    for start, end in zip(ordered, ordered[1:]):
        if start >= end or interval_is_protected(start, end, protected):
            continue
        base = best_span_for_segment(start, end, spans, supplemental)
        name = base.name if base.start == start else f"{base.name}Part{start:04X}"
        segments.append(
            Span(
                start=start,
                end=end,
                name=name,
                extraction_class=base.extraction_class,
                source=base.source,
                evidence=base.evidence,
            )
        )
    return segments


def write_stub(path: Path, plan: ModulePlan, segments: list[Span], *, force: bool) -> None:
    if path.exists() and not force:
        raise SystemExit(f"{path.relative_to(ROOT)} already exists; pass --force to replace it")
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f"; EarthBound {BANK} {plan.title}.",
        ";",
        "; Source-emission status:",
        "; - Prototype level: build-candidate data corridor.",
        "; - Generated by tools/promote_c3_classified_data_to_source_scaffold.py.",
        "; - The byte payloads remain opaque for now, but the labels below preserve",
        ";   C3 source-data-map boundaries for later event/actionscript decoding.",
        ";",
        "; Source units covered:",
    ]
    for segment in segments:
        lines.append(
            f"; - {format_address(segment.start)}..{format_address(segment.end)} "
            f"{segment.name} [{segment.extraction_class}]"
        )
    lines.append("")

    seen_labels: set[str] = set()
    for segment in segments:
        lines.extend(
            [
                "; ---------------------------------------------------------------------------",
                f"; {format_address(segment.start)}..{format_address(segment.end)}",
                f"; class: {segment.extraction_class}",
                f"; source: {segment.source}",
            ]
        )
        for evidence in segment.evidence:
            lines.append(f"; evidence: {evidence}")
        terminal = label_for(segment.end, segment.name)
        if terminal and terminal not in seen_labels:
            lines.extend(["", f"{terminal}:"])
            seen_labels.add(terminal)
        elif not terminal:
            lines.extend(["", f"; {segment.name} reaches the bank boundary."])
        lines.append("")

    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8", newline="\n")


def build_manifest_entry(plan: ModulePlan, segments: list[Span], rom: bytes) -> dict[str, Any]:
    evidence: list[str] = ["build/c3-source-data-map.json", "build/c3-source-residual-map.json"]
    for segment in segments:
        for item in segment.evidence:
            if item not in evidence:
                evidence.append(item)

    entry_args = argparse.Namespace(
        bank=BANK,
        source_path=plan.source_path,
        subsystem=plan.subsystem,
        start=format_address(segments[0].start),
        end=format_address(segments[-1].end),
        name=plan.name,
        source_segment=[],
        data_gap=[
            f"{format_address(segment.start)},{format_address(segment.end)},{segment.name}"
            for segment in segments
        ],
        evidence=evidence,
        rom=None,
        manifest=None,
    )
    entry = build_entry(entry_args, rom)
    for gap, segment in zip(entry["data_gaps"], segments):
        gap["evidence"] = list(segment.evidence)
    return entry


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Promote classified C3 script/data residual corridors into the source scaffold manifest."
    )
    parser.add_argument("--source-map", type=Path, default=ROOT / "build" / "c3-source-data-map.json")
    parser.add_argument("--manifest", type=Path, default=ROOT / "build" / "c3-build-candidate-ranges.json")
    parser.add_argument("--rom")
    parser.add_argument("--force", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    map_path = args.source_map if args.source_map.is_absolute() else ROOT / args.source_map
    manifest_path = args.manifest if args.manifest.is_absolute() else ROOT / args.manifest

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    managed_sources = {plan.source_path.as_posix() for plan in MODULE_PLANS}
    protected = protected_intervals(manifest, ignore_sources=managed_sources)
    spans, supplemental = load_spans(map_path)
    rom = load_rom(find_rom(args.rom))

    new_entries: list[dict[str, Any]] = []
    for plan in MODULE_PLANS:
        segments = segments_for_plan(plan, spans=spans, supplemental=supplemental, protected=protected)
        if not segments:
            continue
        write_stub(ROOT / plan.source_path, plan, segments, force=args.force)
        new_entries.append(build_manifest_entry(plan, segments, rom))

    existing_by_path = {
        item["source_path"]: item for item in manifest.get("ranges", [])
    }
    for entry in new_entries:
        existing_by_path[entry["source_path"]] = entry
    ranges = sorted(
        existing_by_path.values(),
        key=lambda item: parse_bank_address(item["start"])[1],
    )
    manifest["ranges"] = ranges
    manifest["generated_by"] = "tools/promote_c3_classified_data_to_source_scaffold.py"
    manifest.setdefault("inputs", {})["source_data_map"] = "build/c3-source-data-map.json"
    manifest.setdefault("inputs", {})["residual_map"] = "build/c3-source-residual-map.json"
    recalculate_summary(manifest)
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )

    protected_bytes = sum(entry["size"] for entry in manifest["ranges"])
    print(
        f"promoted {len(new_entries)} C3 data corridor(s); "
        f"manifest now protects {protected_bytes} byte(s) across {len(manifest['ranges'])} range(s)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
