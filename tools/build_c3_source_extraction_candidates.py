from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
SCHEMA = "earthbound-decomp.c3-source-extraction-candidates.v1"
DEFAULT_SOURCE_MAP = ROOT / "build" / "c3-source-data-map.json"
DEFAULT_SPLIT_PLAN = ROOT / "build" / "c3-mixed-source-split-plan.json"


@dataclass(frozen=True)
class InternalEntry:
    address: str
    offset: int
    name: str
    evidence: tuple[str, ...]


@dataclass(frozen=True)
class SourceUnit:
    unit_kind: str
    address: str
    start: int
    size: int | None
    include: str
    name: str
    subsystem: str
    extraction_priority: int
    readiness: str
    blocked_by: tuple[str, ...]
    notes: tuple[str, ...]
    evidence: tuple[str, ...]
    internal_entries: tuple[InternalEntry, ...]
    containing_include: str | None = None


@dataclass(frozen=True)
class OrphanSourceLabel:
    address: str
    name: str
    subsystem: str
    reason: str
    evidence: tuple[str, ...]


def resolve_path(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def parse_address(address: str) -> int:
    return int(address.split(":", 1)[1], 16)


def subsystem_for(address: str, name: str) -> str:
    start = parse_address(address)
    lower = name.lower()
    if start < 0x0188:
        return "system screens"
    if start < 0xE450:
        return "event VM helpers"
    if start < 0xE84E:
        return "window and battle text helpers"
    if start < 0xEC1F:
        return "inventory equipment and tracked items"
    if start < 0xEE14:
        return "HP PP stat adjustment helpers"
    if start < 0xEF23:
        return "equipment and battle selector helpers"
    if start < 0xF5F9:
        if "repair" in lower:
            return "Jeff repair and PSI menu helpers"
        return "battle PSI metadata helpers"
    return "battle visual effect helpers"


def unit_policy(
    address: str,
    name: str,
    size: int | None,
    internal_count: int,
    unit_kind: str = "include-row",
) -> tuple[int, str, tuple[str, ...], tuple[str, ...]]:
    start = parse_address(address)
    lower = name.lower()
    blocked: list[str] = []
    notes: list[str] = []
    priority = 3
    readiness = "source-ready"

    if start < 0x0188:
        return (
            3,
            "source-ready-with-system-context",
            ("system screen entry includes are represented as supplemental labels, not addressed unknown-source rows",),
            ("Keep paired C4 screen-render evidence nearby when extracting.",),
        )

    if 0xE450 <= start < 0xE84E:
        priority = 1
        notes.append("Window/text helper corridor has caller and state evidence.")
        if internal_count:
            notes.append("Internal entry labels should stay in the same source unit.")

    if 0xE977 <= start < 0xEC1F:
        priority = 1
        notes.append("Inventory/equipment contract is now corrected around equipped inventory-slot references.")
        if unit_kind == "embedded-label":
            readiness = "source-ready-embedded-in-mixed-row"
            blocked.append("split containing mixed data/source include before emitting as standalone source")
        if address == "C3:EBCA":
            notes.append("Tracked-item sync source contract closes the D5:F4BB accumulator-width caveat.")

    if 0xEC1F <= start < 0xEE14:
        priority = 1
        notes.append("HP/PP adjustment quartet shares one direct/dynamic amount contract.")

    if 0xEE14 <= start < 0xEF23:
        priority = 2
        notes.append("Equipment/statistic selector helpers now have source-contract notes.")

    if address == "C3:F1EC":
        priority = 2
        notes.append("Jeff repair source contract now pairs this mutating inventory repair helper with C1:D038.")

    if 0xF5F9 <= start:
        priority = 2
        notes.append("Battle visual queue/effect helpers are source-ready but depend on adjacent C3 visual tables.")
        if address == "C3:F981":
            notes.append("Battle visual effect dispatch source contract preserves the token colour tables.")

    if address == "C3:E4EF":
        notes.append("Window lifecycle source contract keeps C3:E4EF and internal C3:E521 in one source unit.")

    if size is not None and size >= 0x180 and address != "C3:E4EF":
        blocked.append("larger helper; extract after the small leaf helpers in the same subsystem")
        if readiness == "source-ready":
            readiness = "source-ready-large"

    return priority, readiness, tuple(blocked), tuple(notes)


def load_source_map(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_planned_source_splits(path: Path) -> set[str]:
    if not path.exists():
        return set()
    data = json.loads(path.read_text(encoding="utf-8"))
    return {
        str(address)
        for address in data.get("summary", {}).get("source_helper_addresses", [])
    }


def build_manifest(source_map_path: Path, split_plan_path: Path) -> dict[str, Any]:
    source_map = load_source_map(source_map_path)
    planned_source_splits = load_planned_source_splits(split_plan_path)
    all_addressed_rows = [
        row
        for row in source_map.get("include_rows", [])
        if row.get("address")
    ]
    all_addressed_rows.sort(key=lambda row: parse_address(str(row["address"])))
    include_rows = [
        row
        for row in all_addressed_rows
        if row.get("address") and row.get("extraction_class") == "source-helper"
    ]
    include_rows.sort(key=lambda row: parse_address(str(row["address"])))

    supplemental = [
        row
        for row in source_map.get("supplemental_labels", [])
        if row.get("extraction_class") == "source-helper"
    ]
    supplemental.sort(key=lambda row: parse_address(str(row["address"])))

    def containing_row_for(address: str) -> dict[str, Any] | None:
        value = parse_address(address)
        best: dict[str, Any] | None = None
        for row in all_addressed_rows:
            start = parse_address(str(row["address"]))
            if start > value:
                break
            best = row
        return best

    units: list[SourceUnit] = []
    claimed_supplemental: set[str] = set()
    for row in include_rows:
        address = str(row["address"])
        start = parse_address(address)
        size = row.get("size")
        end = start + int(size) if size is not None else None
        entries: list[InternalEntry] = []
        for label in supplemental:
            label_address = str(label["address"])
            label_start = parse_address(label_address)
            if label_start == start:
                continue
            if end is not None and start < label_start < end:
                entries.append(
                    InternalEntry(
                        address=label_address,
                        offset=label_start - start,
                        name=str(label.get("name") or ""),
                        evidence=tuple(str(item) for item in label.get("evidence", [])),
                    )
                )
                claimed_supplemental.add(label_address)
        name = str(row.get("name") or "")
        subsystem = subsystem_for(address, name)
        priority, readiness, blocked_by, notes = unit_policy(address, name, size, len(entries))
        units.append(
            SourceUnit(
                unit_kind="include-row",
                address=address,
                start=start,
                size=int(size) if size is not None else None,
                include=str(row["path"]),
                name=name,
                subsystem=subsystem,
                extraction_priority=priority,
                readiness=readiness,
                blocked_by=blocked_by,
                notes=notes,
                evidence=tuple(str(item) for item in row.get("evidence", [])),
                internal_entries=tuple(entries),
                containing_include=None,
            )
        )

    include_starts = {str(row["address"]) for row in include_rows}
    embedded_source_labels = [
        label
        for label in supplemental
        if str(label["address"]) not in include_starts
        and str(label["address"]) not in claimed_supplemental
        and (container := containing_row_for(str(label["address"]))) is not None
        and container.get("extraction_class") in {"raw-or-named-data", "data-or-helper-frontier", "mixed-data-source-row"}
    ]
    embedded_source_labels.sort(key=lambda row: parse_address(str(row["address"])))
    for index, label in enumerate(embedded_source_labels):
        address = str(label["address"])
        start = parse_address(address)
        container = containing_row_for(address)
        assert container is not None
        container_start = parse_address(str(container["address"]))
        container_size = container.get("size")
        container_end = container_start + int(container_size) if container_size is not None else None
        next_embedded_start: int | None = None
        for later in embedded_source_labels[index + 1:]:
            later_start = parse_address(str(later["address"]))
            if container_end is None or later_start < container_end:
                next_embedded_start = later_start
                break
        if next_embedded_start is None:
            for row in include_rows:
                row_start = parse_address(str(row["address"]))
                if row_start > start and (container_end is None or row_start <= container_end):
                    next_embedded_start = row_start
                    break
        size = (next_embedded_start - start) if next_embedded_start is not None and next_embedded_start > start else None
        name = str(label.get("name") or "")
        subsystem = subsystem_for(address, name)
        priority, readiness, blocked_by, notes = unit_policy(address, name, size, 0, unit_kind="embedded-label")
        if address in planned_source_splits:
            readiness = "source-ready"
            blocked_by = ()
            notes = notes + ("Mixed-row split plan provides standalone source-helper slice boundaries.",)
        notes = notes + (f"Contained by `{container['path']}` at `{container['address']}`.",)
        units.append(
            SourceUnit(
                unit_kind="embedded-label",
                address=address,
                start=start,
                size=size,
                include=f"{container['path']}#embedded",
                name=name,
                subsystem=subsystem,
                extraction_priority=priority,
                readiness=readiness,
                blocked_by=blocked_by,
                notes=notes,
                evidence=tuple(str(item) for item in label.get("evidence", [])),
                internal_entries=(),
                containing_include=str(container["path"]),
            )
        )
        claimed_supplemental.add(address)
    units.sort(key=lambda unit: unit.start)

    orphan_labels: list[OrphanSourceLabel] = []
    for label in supplemental:
        address = str(label["address"])
        if address in include_starts or address in claimed_supplemental:
            continue
        name = str(label.get("name") or "")
        reason = "source label outside addressed source-helper rows"
        if parse_address(address) < 0x0188:
            reason = "system entry point label before the first addressed bank payload include"
        orphan_labels.append(
            OrphanSourceLabel(
                address=address,
                name=name,
                subsystem=subsystem_for(address, name),
                reason=reason,
                evidence=tuple(str(item) for item in label.get("evidence", [])),
            )
        )

    by_subsystem = Counter(unit.subsystem for unit in units)
    by_readiness = Counter(unit.readiness for unit in units)
    by_priority = Counter(str(unit.extraction_priority) for unit in units)

    return {
        "schema": SCHEMA,
        "generated_by": "tools/build_c3_source_extraction_candidates.py",
        "inputs": {
            "source_data_map": rel(source_map_path),
            "mixed_source_split_plan": rel(split_plan_path),
        },
        "summary": {
            "source_units": len(units),
            "include_source_units": sum(1 for unit in units if unit.unit_kind == "include-row"),
            "embedded_source_units": sum(1 for unit in units if unit.unit_kind == "embedded-label"),
            "internal_source_entries": sum(len(unit.internal_entries) for unit in units),
            "orphan_source_labels": len(orphan_labels),
            "by_subsystem": dict(sorted(by_subsystem.items())),
            "by_readiness": dict(sorted(by_readiness.items())),
            "by_priority": dict(sorted(by_priority.items())),
        },
        "source_units": [asdict(unit) for unit in units],
        "orphan_source_labels": [asdict(label) for label in orphan_labels],
    }


def markdown_escape(text: str) -> str:
    return text.replace("|", "\\|")


def render_markdown(manifest: dict[str, Any]) -> str:
    summary = manifest["summary"]
    units = manifest["source_units"]
    orphan_labels = manifest["orphan_source_labels"]
    lines = [
        "# C3 source extraction candidates",
        "",
        "Generated from `build/c3-source-data-map.json`. This is the implementation queue for C3 rows that should become ordinary 65816 source before event/actionscript VM work.",
        "",
        "## Summary",
        "",
        f"- schema: `{manifest['schema']}`",
        f"- source units: `{summary['source_units']}`",
        f"- include-start source units: `{summary['include_source_units']}`",
        f"- embedded source units: `{summary['embedded_source_units']}`",
        f"- internal source entry labels: `{summary['internal_source_entries']}`",
        f"- orphan/source entry labels outside addressed source-helper rows: `{summary['orphan_source_labels']}`",
        f"- by subsystem: `{summary['by_subsystem']}`",
        f"- by readiness: `{summary['by_readiness']}`",
        f"- by priority: `{summary['by_priority']}`",
        "",
        "## Priority Queue",
        "",
        "| Priority | Kind | Address | Size | Subsystem | Name | Readiness | Blocked By |",
        "| ---: | --- | --- | ---: | --- | --- | --- | --- |",
    ]
    for unit in sorted(units, key=lambda item: (item["extraction_priority"], item["start"])):
        size = f"0x{unit['size']:X}" if unit.get("size") is not None else ""
        blocked = "<br>".join(markdown_escape(item) for item in unit.get("blocked_by", []))
        lines.append(
            "| {priority} | `{kind}` | `{address}` | {size} | {subsystem} | `{name}` | `{readiness}` | {blocked} |".format(
                priority=unit["extraction_priority"],
                kind=unit["unit_kind"],
                address=unit["address"],
                size=size,
                subsystem=markdown_escape(unit["subsystem"]),
                name=markdown_escape(unit["name"]),
                readiness=unit["readiness"],
                blocked=blocked,
            )
        )

    lines.extend(["", "## Source Units", ""])
    for unit in units:
        size = f"0x{unit['size']:X}" if unit.get("size") is not None else "unknown"
        lines.extend(
            [
                f"### `{unit['address']}` `{unit['name']}`",
                "",
                f"- include: `{unit['include']}`",
                f"- unit kind: `{unit['unit_kind']}`",
                f"- size: `{size}`",
                f"- subsystem: `{unit['subsystem']}`",
                f"- priority: `{unit['extraction_priority']}`",
                f"- readiness: `{unit['readiness']}`",
            ]
        )
        if unit.get("blocked_by"):
            lines.append(f"- blocked by: {'; '.join(markdown_escape(item) for item in unit['blocked_by'])}")
        if unit.get("containing_include"):
            lines.append(f"- containing include: `{unit['containing_include']}`")
        if unit.get("notes"):
            lines.append(f"- notes: {'; '.join(markdown_escape(item) for item in unit['notes'])}")
        if unit.get("internal_entries"):
            lines.extend(["", "| Internal Address | Offset | Name |", "| --- | ---: | --- |"])
            for entry in unit["internal_entries"]:
                lines.append(
                    f"| `{entry['address']}` | `+0x{entry['offset']:X}` | `{markdown_escape(entry['name'])}` |"
                )
        lines.append("")

    if orphan_labels:
        lines.extend(
            [
                "## Orphan Source Labels",
                "",
                "These source labels are not currently inside an addressed source-helper row. They need special handling during source carving.",
                "",
                "| Address | Subsystem | Name | Reason |",
                "| --- | --- | --- | --- |",
            ]
        )
        for label in orphan_labels:
            lines.append(
                "| `{address}` | {subsystem} | `{name}` | {reason} |".format(
                    address=label["address"],
                    subsystem=markdown_escape(label["subsystem"]),
                    name=markdown_escape(label["name"]),
                    reason=markdown_escape(label["reason"]),
                )
            )
    return "\n".join(lines).rstrip() + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build the C3 ordinary-source extraction candidate queue.")
    parser.add_argument("--source-map", type=Path, default=DEFAULT_SOURCE_MAP)
    parser.add_argument("--split-plan", type=Path, default=DEFAULT_SPLIT_PLAN)
    parser.add_argument("--json-out", type=Path, default=ROOT / "build" / "c3-source-extraction-candidates.json")
    parser.add_argument("--markdown-out", type=Path, default=ROOT / "notes" / "c3-source-extraction-candidates.md")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    source_map = resolve_path(args.source_map)
    split_plan = resolve_path(args.split_plan)
    manifest = build_manifest(source_map, split_plan)

    json_out = resolve_path(args.json_out)
    json_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    markdown_out = resolve_path(args.markdown_out)
    markdown_out.parent.mkdir(parents=True, exist_ok=True)
    markdown_out.write_text(render_markdown(manifest), encoding="utf-8")
    print(
        f"Wrote {rel(json_out)} and {rel(markdown_out)} "
        f"({manifest['summary']['source_units']} source units)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
