from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
SCHEMA = "earthbound-decomp.c3-source-emission-plan.v1"
DEFAULT_CANDIDATES = ROOT / "build" / "c3-source-extraction-candidates.json"
DEFAULT_SPLIT_PLAN = ROOT / "build" / "c3-mixed-source-split-plan.json"


MODULE_POLICY: dict[str, dict[str, Any]] = {
    "window and battle text helpers": {
        "source_path": "src/c3/window_text_helpers.asm",
        "phase": "build-candidate",
        "strategy": "emit as annotated 65816 source with internal callable labels preserved",
        "dependencies": [
            "$8650 window record table",
            "$88E0/$88E2 open-window chain heads",
            "$88E4 logical-window-to-record map",
            "$8958 focused window id",
        ],
    },
    "inventory equipment and tracked items": {
        "source_path": "src/c3/inventory_equipment_tracked_items.asm",
        "phase": "build-candidate",
        "strategy": "emit first prototype module; covers embedded split slices, ordinary helpers, and timed-item table contracts",
        "dependencies": [
            "C3:E84E mixed data/source split plan",
            "$99F1 character inventory bytes",
            "$99FF..$9A02 equipped inventory-slot references",
            "D5:F4BB TIMED_ITEM_TRANSFORMATION_TABLE",
            "$9F1A tracked-item pulse registry",
        ],
    },
    "HP PP stat adjustment helpers": {
        "source_path": "src/c3/hp_pp_adjustment_helpers.asm",
        "phase": "build-candidate",
        "strategy": "emit as small arithmetic helper quartet sharing the Y/direct-amount contract",
        "dependencies": [
            "$99D8 max HP/PP fields",
            "$9A15 current HP/PP fields",
            "$9A19 HP-present paired marker",
        ],
    },
    "equipment and battle selector helpers": {
        "source_path": "src/c3/equipment_battle_selector_helpers.asm",
        "phase": "build-candidate",
        "strategy": "emit as selector/refresh helpers with external C1/C4 table contracts referenced",
        "dependencies": [
            "C4:58AB equipment slot mask helper",
            "C4:550F statistic selector records",
            "$B4A8 active visual/presentation handle",
        ],
    },
    "Jeff repair and PSI menu helpers": {
        "source_path": "src/c3/jeff_repair_psi_helpers.asm",
        "phase": "build-candidate",
        "strategy": "emit Jeff repair helper with C1:D038 mapper contract kept as an external source dependency",
        "dependencies": [
            "D5:5000 item configuration table",
            "$9AAF Jeff inventory bytes",
            "$9AA7 Jeff IQ value",
            "C1:D038 MapBrokenItemToRepairedItem",
        ],
    },
    "file-select visual transition helper": {
        "source_path": "src/c3/file_select_visual_transition_helper.asm",
        "phase": "build-candidate",
        "strategy": "emit embedded C3:F3C5 helper as annotated 65816 source while preserving adjacent C3:F2B1..F3C5 tables as data",
        "dependencies": [
            "C3:F2B1 level-up stat growth variance table",
            "C3:F2B5 visual selector pose row table",
            "$9F75 transition mode argument latch",
            "$9641 file-select/entity-script busy state",
        ],
    },
    "battle visual effect helpers": {
        "source_path": "src/c3/battle_visual_effect_helpers.asm",
        "phase": "build-candidate",
        "strategy": "emit transfer/effect dispatch helpers while preserving adjacent C3 effect tables as data",
        "dependencies": [
            "C3:F951 BattleVisualToken23To2dColourTriples",
            "C3:F972 BattleVisualToken31To35ColourTriples",
            "C3:F819 BattleSwirlOverlayMode2Script",
            "EF:EB3D fixed visual tile source",
        ],
    },
}


@dataclass(frozen=True)
class SourceLabel:
    address: str
    name: str
    offset: int
    role: str


@dataclass(frozen=True)
class EmissionUnit:
    address: str
    start: int
    end: int | None
    size: int | None
    name: str
    unit_kind: str
    include: str
    readiness: str
    labels: tuple[SourceLabel, ...]
    evidence: tuple[str, ...]
    notes: tuple[str, ...]
    containing_include: str | None


@dataclass(frozen=True)
class EmissionModule:
    source_path: str
    subsystem: str
    phase: str
    artifact_status: str
    prototype_level: str | None
    strategy: str
    start: int
    end: int | None
    units: tuple[EmissionUnit, ...]
    dependencies: tuple[str, ...]


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def resolve_path(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def find_prototype_level(path: Path) -> str | None:
    if not path.exists():
        return None
    text = path.read_text(encoding="utf-8", errors="ignore")
    match = re.search(r"Prototype level:\s*([A-Za-z0-9_-]+)", text)
    if not match:
        return None
    return match.group(1)


def parse_address(address: str) -> int:
    return int(address.split(":", 1)[1], 16)


def format_address(value: int | None) -> str:
    if value is None:
        return "unknown"
    return f"C3:{value:04X}"


def collect_split_notes(split_plan: dict[str, Any]) -> dict[str, str]:
    notes: dict[str, str] = {}
    for row in split_plan.get("mixed_rows", []):
        for slice_info in row.get("slices", []):
            if slice_info.get("kind") != "source-helper":
                continue
            notes[str(slice_info["address"])] = (
                f"slice {format_address(int(slice_info['start']))}.."
                f"{format_address(int(slice_info['end']))} from `{row['include']}`"
            )
    return notes


def build_unit(unit: dict[str, Any], split_notes: dict[str, str]) -> EmissionUnit:
    start = int(unit["start"])
    size = unit.get("size")
    end = start + int(size) if size is not None else None
    labels = [
        SourceLabel(
            address=str(unit["address"]),
            name=str(unit["name"]),
            offset=0,
            role="entry",
        )
    ]
    for entry in unit.get("internal_entries", []):
        labels.append(
            SourceLabel(
                address=str(entry["address"]),
                name=str(entry["name"]),
                offset=int(entry["offset"]),
                role="internal-callable-label",
            )
        )
    notes = [str(item) for item in unit.get("notes", [])]
    if split_note := split_notes.get(str(unit["address"])):
        notes.append(split_note)
    return EmissionUnit(
        address=str(unit["address"]),
        start=start,
        end=end,
        size=int(size) if size is not None else None,
        name=str(unit["name"]),
        unit_kind=str(unit["unit_kind"]),
        include=str(unit["include"]),
        readiness=str(unit["readiness"]),
        labels=tuple(labels),
        evidence=tuple(str(item) for item in unit.get("evidence", [])),
        notes=tuple(notes),
        containing_include=unit.get("containing_include"),
    )


def build_manifest(candidates_path: Path, split_plan_path: Path) -> dict[str, Any]:
    candidates = load_json(candidates_path)
    split_plan = load_json(split_plan_path) if split_plan_path.exists() else {}
    split_notes = collect_split_notes(split_plan)

    units_by_subsystem: dict[str, list[EmissionUnit]] = defaultdict(list)
    for unit in candidates.get("source_units", []):
        if unit.get("readiness") != "source-ready":
            continue
        units_by_subsystem[str(unit["subsystem"])].append(build_unit(unit, split_notes))

    modules: list[EmissionModule] = []
    for subsystem, units in sorted(
        units_by_subsystem.items(),
        key=lambda item: min(unit.start for unit in item[1]),
    ):
        units.sort(key=lambda unit: unit.start)
        policy = MODULE_POLICY.get(
            subsystem,
            {
                "source_path": f"src/c3/{subsystem.replace(' ', '_')}.asm",
                "phase": "module-ready",
                "strategy": "emit as annotated 65816 source",
                "dependencies": [],
            },
        )
        source_path = ROOT / str(policy["source_path"])
        known_ends = [unit.end for unit in units if unit.end is not None]
        modules.append(
            EmissionModule(
                source_path=str(policy["source_path"]),
                subsystem=subsystem,
                phase=str(policy["phase"]),
                artifact_status=(
                    "prototype-file-present"
                    if source_path.exists()
                    else "planned"
                ),
                prototype_level=find_prototype_level(source_path),
                strategy=str(policy["strategy"]),
                start=min(unit.start for unit in units),
                end=max(known_ends) if known_ends and len(known_ends) == len(units) else None,
                units=tuple(units),
                dependencies=tuple(str(item) for item in policy.get("dependencies", [])),
            )
        )

    source_ready = candidates.get("summary", {}).get("by_readiness", {}).get("source-ready", 0)
    prototype_modules_present = [
        module.source_path for module in modules if module.artifact_status == "prototype-file-present"
    ]
    return {
        "schema": SCHEMA,
        "generated_by": "tools/build_c3_source_emission_plan.py",
        "inputs": {
            "source_candidates": rel(candidates_path),
            "mixed_source_split_plan": rel(split_plan_path),
        },
        "summary": {
            "modules": len(modules),
            "source_units": sum(len(module.units) for module in modules),
            "source_ready_units_from_queue": source_ready,
            "prototype_module": next(
                (
                    module.source_path
                    for module in modules
                    if module.source_path == "src/c3/inventory_equipment_tracked_items.asm"
                ),
                None,
            ),
            "prototype_modules_present": prototype_modules_present,
            "by_phase": {
                phase: sum(1 for module in modules if module.phase == phase)
                for phase in sorted({module.phase for module in modules})
            },
            "by_artifact_status": {
                status: sum(1 for module in modules if module.artifact_status == status)
                for status in sorted({module.artifact_status for module in modules})
            },
            "by_prototype_level": {
                level: sum(1 for module in modules if module.prototype_level == level)
                for level in sorted(
                    {module.prototype_level for module in modules if module.prototype_level is not None}
                )
            },
        },
        "modules": [asdict(module) for module in modules],
    }


def markdown_escape(text: str) -> str:
    return text.replace("|", "\\|")


def render_markdown(manifest: dict[str, Any]) -> str:
    summary = manifest["summary"]
    lines = [
        "# C3 source emission plan",
        "",
        "Generated from the source-ready C3 extraction queue. This is not source code yet; it is the module/file plan that turns documented C3 helpers into source-emission work items.",
        "",
        "## Summary",
        "",
        f"- schema: `{manifest['schema']}`",
        f"- modules: `{summary['modules']}`",
        f"- source units: `{summary['source_units']}`",
        f"- source-ready queue units: `{summary['source_ready_units_from_queue']}`",
        f"- prototype module: `{summary['prototype_module']}`",
        f"- prototype modules present: `{summary.get('prototype_modules_present', [])}`",
        f"- by phase: `{summary['by_phase']}`",
        f"- by artifact status: `{summary['by_artifact_status']}`",
        f"- by prototype level: `{summary.get('by_prototype_level', {})}`",
        "",
        "## Module Queue",
        "",
        "| Phase | Status | Level | Source Path | Range | Units | Subsystem | Strategy |",
        "| --- | --- | --- | --- | --- | ---: | --- | --- |",
    ]
    for module in manifest["modules"]:
        lines.append(
            "| `{phase}` | `{status}` | `{level}` | `{path}` | `{start}..{end}` | {units} | {subsystem} | {strategy} |".format(
                phase=module["phase"],
                status=module["artifact_status"],
                level=module.get("prototype_level") or "",
                path=module["source_path"],
                start=format_address(int(module["start"])),
                end=format_address(module["end"]),
                units=len(module["units"]),
                subsystem=markdown_escape(module["subsystem"]),
                strategy=markdown_escape(module["strategy"]),
            )
        )

    lines.extend(["", "## Modules", ""])
    for module in manifest["modules"]:
        lines.extend(
            [
                f"### `{module['source_path']}`",
                "",
                f"- subsystem: `{module['subsystem']}`",
                f"- phase: `{module['phase']}`",
                f"- artifact status: `{module['artifact_status']}`",
                f"- prototype level: `{module.get('prototype_level')}`",
                f"- range: `{format_address(int(module['start']))}..{format_address(module['end'])}`",
                f"- strategy: {module['strategy']}",
            ]
        )
        if module.get("dependencies"):
            lines.append("- dependencies: " + "; ".join(f"`{item}`" for item in module["dependencies"]))
        lines.extend(
            [
                "",
                "| Address | Range | Size | Kind | Name | Labels | Evidence |",
                "| --- | --- | ---: | --- | --- | --- | --- |",
            ]
        )
        for unit in module["units"]:
            labels = "<br>".join(
                f"`{label['address']}` `{markdown_escape(label['name'])}` ({label['role']})"
                for label in unit["labels"]
            )
            evidence = "<br>".join(f"`{markdown_escape(item)}`" for item in unit["evidence"][:3])
            size = f"0x{int(unit['size']):X}" if unit.get("size") is not None else ""
            lines.append(
                "| `{address}` | `{start}..{end}` | {size} | `{kind}` | `{name}` | {labels} | {evidence} |".format(
                    address=unit["address"],
                    start=format_address(int(unit["start"])),
                    end=format_address(unit["end"]),
                    size=size,
                    kind=unit["unit_kind"],
                    name=markdown_escape(unit["name"]),
                    labels=labels,
                    evidence=evidence,
                )
            )
        lines.append("")

    present_build_candidates = [
        module["source_path"]
        for module in manifest["modules"]
        if module["artifact_status"] == "prototype-file-present"
        and module.get("prototype_level") == "build-candidate"
    ]
    lines.extend(
        [
            "## Prototype Status",
            "",
            "`src/c3/inventory_equipment_tracked_items.asm` remains the first source-emission prototype and is now a build candidate. It is the best structural test case because it covers:",
            "",
            "- embedded source slices from a mixed data/source row",
            "- direct character inventory access",
            "- equipped-slot reference checks",
            "- item-family lifecycle refresh hooks",
            "- one structured external table contract at `D5:F4BB`",
            "",
            f"`{len(present_build_candidates)}` planned C3 helper modules now have prototype artifacts at `build-candidate` level: "
            + ", ".join(f"`{path}`" for path in present_build_candidates)
            + ". The remaining C3 source work is broader build-candidate hardening: assembler syntax, byte matching, external symbol naming, and preserving adjacent visual/script data tables as separate source assets.",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build the C3 source emission plan.")
    parser.add_argument("--candidates", type=Path, default=DEFAULT_CANDIDATES)
    parser.add_argument("--split-plan", type=Path, default=DEFAULT_SPLIT_PLAN)
    parser.add_argument("--json-out", type=Path, default=ROOT / "build" / "c3-source-emission-plan.json")
    parser.add_argument("--markdown-out", type=Path, default=ROOT / "notes" / "c3-source-emission-plan.md")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    candidates_path = resolve_path(args.candidates)
    split_plan_path = resolve_path(args.split_plan)
    manifest = build_manifest(candidates_path, split_plan_path)

    json_out = resolve_path(args.json_out)
    json_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    markdown_out = resolve_path(args.markdown_out)
    markdown_out.parent.mkdir(parents=True, exist_ok=True)
    markdown_out.write_text(render_markdown(manifest), encoding="utf-8")
    print(
        f"Wrote {rel(json_out)} and {rel(markdown_out)} "
        f"({manifest['summary']['modules']} modules, {manifest['summary']['source_units']} source units)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
