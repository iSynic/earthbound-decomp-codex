#!/usr/bin/env python3
"""Build a structured expansion model for localization authoring macros.

This consumes the generated macro-expansion frontier and turns the already
documented control/display/inventory split into a stable, queryable model. It
does not read recovered dialogue source and does not assign new Text VM opcodes.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FRONTIER = ROOT / "build" / "localization-macro-expansion-frontier.json"
DEFAULT_JSON = ROOT / "build" / "localization-macro-expansion-model.json"
DEFAULT_MARKDOWN = ROOT / "notes" / "localization-macro-expansion-model.md"


CONTROL_MODELS: dict[str, dict[str, Any]] = {
    "@SET_LOOPREG": {
        "source_role": "stage a source-local loop/register value before repeated calls, comparisons, or list-style helper expansion",
        "confidence": "high",
        "vm_primitives": ["0x08 CALL_TEXT", "0x0D/0x0E arg-memory copy/store", "0x1B memory/context helpers"],
        "evidence_notes": [
            "Documented as the strongest cross-file stage-then-call motif.",
            "Keep decimal and symbolic operands as source syntax until the exact storage slot is proven.",
        ],
        "open_questions": [
            "whether work memory, arg memory, scratch memory, or source-tool locals hold the staged value",
            "whether repeated SET_LOOPREG chains emit repeated stores or a compact source-tool expansion",
        ],
    },
    "@LOAD_REG": {
        "source_role": "restore a source-local register into the active text context",
        "confidence": "medium",
        "vm_primitives": ["0x0D/0x0E arg-memory copy/store", "0x1B memory/context helpers"],
        "evidence_notes": ["Part of the register/memory helper group in the control macro model."],
        "open_questions": ["exact VM slot restored into the active context"],
    },
    "@SAVE_REG": {
        "source_role": "save active text context into a source-local register",
        "confidence": "medium",
        "vm_primitives": ["0x0D/0x0E arg-memory copy/store", "0x1B memory/context helpers"],
        "evidence_notes": ["Part of the register/memory helper group in the control macro model."],
        "open_questions": ["exact VM slot copied out of the active context"],
    },
    "@SET_REG": {
        "source_role": "set a general source-local register to an immediate or symbolic value",
        "confidence": "medium",
        "vm_primitives": ["0x0D/0x0E arg-memory copy/store", "0x1B memory/context helpers"],
        "evidence_notes": ["Kept distinct from SET_LOOPREG because its command neighborhoods differ."],
        "open_questions": ["whether SET_REG and SET_LOOPREG share a lower-level storage primitive"],
    },
    "@LOAD_GLOBAL_REG": {
        "source_role": "restore a global source register into active text context",
        "confidence": "medium",
        "vm_primitives": ["0x0D/0x0E arg-memory copy/store", "0x1B memory/context helpers"],
        "evidence_notes": ["Classified with register/memory helpers; global lifetime remains source-level."],
        "open_questions": ["exact distinction between local and global source register storage"],
    },
    "@SAVE_GLOBAL_REG": {
        "source_role": "save active text context into a global source register",
        "confidence": "medium",
        "vm_primitives": ["0x0D/0x0E arg-memory copy/store", "0x1B memory/context helpers"],
        "evidence_notes": ["Classified with register/memory helpers; global lifetime remains source-level."],
        "open_questions": ["exact distinction between local and global source register storage"],
    },
    "@INC": {
        "source_role": "increment the current staged working-memory or source-register value",
        "confidence": "medium",
        "vm_primitives": ["0x0F increment working memory", "0x1B memory/context helpers"],
        "evidence_notes": ["Part of the staged register helper set."],
        "open_questions": ["whether the increment always targets live work memory or a compiler-local register"],
    },
    "@SUB": {
        "source_role": "subtract from or adjust the current staged source-register value",
        "confidence": "medium",
        "vm_primitives": ["0x0B/0x0C parameterized tests", "0x0D/0x0E arg-memory copy/store", "0x1B memory/context helpers"],
        "evidence_notes": ["Rare source-register arithmetic helper in the control macro lane."],
        "open_questions": ["exact arithmetic lowering and target storage"],
    },
    "@NOT": {
        "source_role": "invert or negate a staged predicate before branch use",
        "confidence": "low",
        "vm_primitives": ["0x1B 02/03 false/true branches", "0x1B memory/context helpers"],
        "evidence_notes": ["Low-count predicate helper; keep source form until a focused proof exists."],
        "open_questions": ["whether NOT flips a boolean slot, branch sense, or source-tool predicate state"],
    },
    "@CMP": {
        "source_role": "compare two staged values before a branch or conditional call macro",
        "confidence": "medium",
        "vm_primitives": ["0x0B/0x0C parameterized tests", "0x0D/0x0E arg-memory copy/store", "0x1B 02/03 false/true branches"],
        "evidence_notes": [
            "The dominant CMP > ONGOSUB motif is a repeated compare followed by a one-label conditional call.",
        ],
        "open_questions": ["which operand is the subject and which is the compared value"],
    },
    "@EQ": {
        "source_role": "test equality against the current staged/register value",
        "confidence": "medium",
        "vm_primitives": ["0x0B/0x0C parameterized tests", "0x1B 02/03 false/true branches"],
        "evidence_notes": ["Adjacent to register helpers, display commands, inventory commands, and branches."],
        "open_questions": ["whether EQ is a shorthand compare or a separate source predicate helper"],
    },
    "@ONGOSUB": {
        "source_role": "conditional call or source-level multi-way call syntax over the current comparison/selector state",
        "confidence": "high",
        "vm_primitives": ["0x08 CALL_TEXT", "0x09 JUMP_MULTI", "0x1B 02/03 false/true branches"],
        "evidence_notes": [
            "One-label ONGOSUB after CMP is the strongest proven shape.",
            "Multi-argument forms remain modeled separately from the dominant compare/call motif.",
        ],
        "open_questions": ["whether multi-argument forms lower to call chains, JUMP_MULTI-like tables, or another source-tool expansion"],
    },
    "@ONGOTO": {
        "source_role": "source-level multi-way jump syntax over current comparison or selector state",
        "confidence": "medium",
        "vm_primitives": ["0x09 JUMP_MULTI", "0x0A JUMP", "0x1B 02/03 false/true branches"],
        "evidence_notes": ["Likely jump counterpart to ONGOSUB, but rarer and less proved."],
        "open_questions": ["whether every arity shares one branch-table lowering shape"],
    },
    "@SELGOTO": {
        "source_role": "selection-result branch over the most recent menu or selection value",
        "confidence": "high",
        "vm_primitives": ["0x09 JUMP_MULTI", "0x0A JUMP", "0x11 CREATE_SELECTION_MENU", "0x1A menu/selection family", "0x1C 05 PRINT_ITEM_NAME"],
        "evidence_notes": [
            "The dominant two-target form follows item display or helper-call selection setup.",
            "Preserve SELGOTO as source syntax above JUMP_MULTI.",
        ],
        "open_questions": ["whether all two-argument forms emit a literal two-entry JUMP_MULTI at the macro site"],
    },
    "@SEL_TEL_GOSUB": {
        "source_role": "teleport-selection call helper over selection and call semantics",
        "confidence": "low",
        "vm_primitives": ["0x08 CALL_TEXT", "0x09 JUMP_MULTI", "0x1A menu/selection family"],
        "evidence_notes": ["Very low-count selection/call wrapper; retain as source macro."],
        "open_questions": ["exact relationship to teleport menu setup and call targets"],
    },
}


DIRECT_DISPLAY_ALIASES: dict[str, dict[str, str]] = {
    "@DSP_STS": {"source_role": "print a stat/status value", "expected_opcode": "0x1C", "expected_subopcode": "0x01"},
    "@DSP_NAME": {"source_role": "print a character name", "expected_opcode": "0x1C", "expected_subopcode": "0x02"},
    "@DSP_GOODS": {"source_role": "print an item/goods name", "expected_opcode": "0x1C", "expected_subopcode": "0x05"},
    "@DSP_ITEM": {"source_role": "print an item/goods name in selection-oriented contexts", "expected_opcode": "0x1C", "expected_subopcode": "0x05"},
    "@DSP_NUM": {"source_role": "print a staged numeric value", "expected_opcode": "0x1C", "expected_subopcode": "0x0A"},
    "@DSP_CNUM": {"source_role": "print a current or staged number source variant", "expected_opcode": "0x1C", "expected_subopcode": "0x0A"},
    "@DSP_PSI": {"source_role": "print a PSI name", "expected_opcode": "0x1C", "expected_subopcode": "0x12"},
    "@DSP_CHAR": {"source_role": "print one character or glyph-style value", "expected_opcode": "0x1C", "expected_subopcode": "0x03"},
}


DIRECT_INVENTORY_ALIASES: dict[str, dict[str, str]] = {
    "@GOODSIN_PLAYER": {"source_role": "give an item/goods to a character", "expected_opcode": "0x1D", "expected_subopcode": "0x00"},
    "@GOODSIN": {"source_role": "give item/goods using the shorter source alias", "expected_opcode": "0x1D", "expected_subopcode": "0x00"},
    "@GOODSOUT_PLAYER": {"source_role": "remove item/goods from a character", "expected_opcode": "0x1D", "expected_subopcode": "0x01"},
    "@GOODSOUT": {"source_role": "remove item/goods using the shorter source alias", "expected_opcode": "0x1D", "expected_subopcode": "0x01"},
    "@Q_GOODSFULL": {"source_role": "test party or character inventory room", "expected_opcode": "0x1D", "expected_subopcode": "0x03"},
    "@Q_HAVE": {"source_role": "test possession of an item/goods", "expected_opcode": "0x1D", "expected_subopcode": "0x05"},
    "@MONEYIN": {"source_role": "add money to wallet", "expected_opcode": "0x1D", "expected_subopcode": "0x08"},
    "@MONEYOUT": {"source_role": "remove money from wallet", "expected_opcode": "0x1D", "expected_subopcode": "0x09"},
    "@Q_MONEY": {"source_role": "test wallet balance", "expected_opcode": "0x1D", "expected_subopcode": "0x14"},
    "@Q_BANK_MONEY": {"source_role": "test bank balance", "expected_opcode": "0x1D", "expected_subopcode": "0x17"},
    "@DEPOSIT_MONEY_BANK": {"source_role": "add to bank/ATM balance", "expected_opcode": "0x1D", "expected_subopcode": "0x06"},
    "@DRAW_MONEY_BANK": {"source_role": "remove from bank/ATM balance", "expected_opcode": "0x1D", "expected_subopcode": "0x07"},
    "@Q_MEMBER": {"source_role": "test party member count", "expected_opcode": "0x1D", "expected_subopcode": "0x19"},
    "@RAND": {"source_role": "stage a random number", "expected_opcode": "0x1D", "expected_subopcode": "0x21"},
    "@Q_EQUIP": {"source_role": "test equipped item/reference", "expected_opcode": "0x1D", "expected_subopcode": "0x10"},
}


DEFERRED_LANE_ROLES = {
    "event_actionscript_join": "defer movement, camera, actor, and visibility macros to C3/map-object action-script semantics",
    "text_vm_query_macro": "defer query predicates until they can be tied to checks, staged-memory tests, or branch macros",
    "text_vm_status_macro": "defer status condition toggles until the 0x1E/event-helper split is active",
    "battle_text_macro": "defer battle authoring macros to EF payload and C2 battle consumer work",
    "authoring_format_markup": "defer source layout markers until source-tool emission versus metadata is proven",
    "source_tooling_macro": "defer parser/tooling helpers until their source-tool behavior is documented",
    "direct_runtime_hint": "retain existing direct runtime hint outside the display/inventory alias scope",
}


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def load_frontier(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def runtime_alias(row: dict[str, Any]) -> dict[str, str] | None:
    hint = row.get("runtime_hint")
    if not hint:
        return None
    alias = {
        "opcode": hint["opcode"],
        "name": hint["name"],
        "confidence": hint["confidence"],
    }
    if "subopcode" in hint:
        alias["subopcode"] = hint["subopcode"]
    return alias


def assert_hint(row: dict[str, Any], spec: dict[str, str]) -> None:
    hint = row.get("runtime_hint")
    if not hint:
        raise SystemExit(f"{row['command']} is missing a runtime hint")
    if hint.get("opcode") != spec["expected_opcode"]:
        raise SystemExit(f"{row['command']} expected opcode {spec['expected_opcode']} but saw {hint.get('opcode')}")
    if hint.get("subopcode") != spec["expected_subopcode"]:
        raise SystemExit(
            f"{row['command']} expected subopcode {spec['expected_subopcode']} but saw {hint.get('subopcode')}"
        )


def control_row(row: dict[str, Any]) -> dict[str, Any]:
    model = CONTROL_MODELS[row["command"]]
    return {
        "command": row["command"],
        "expansion_class": "source_macro",
        "lowering_status": "source_macro_shape_proven",
        "source_role": model["source_role"],
        "confidence": model["confidence"],
        "runtime_alias": None,
        "vm_primitives": model["vm_primitives"],
        "preserve_source_form": True,
        "evidence_notes": model["evidence_notes"],
        "open_questions": model["open_questions"],
        "frontier": frontier_summary(row),
    }


def direct_alias_row(row: dict[str, Any], spec: dict[str, str], family: str) -> dict[str, Any]:
    assert_hint(row, spec)
    hint = row["runtime_hint"]
    return {
        "command": row["command"],
        "expansion_class": "direct_vm_alias",
        "lowering_status": "direct_vm_alias",
        "source_role": spec["source_role"],
        "confidence": hint["confidence"],
        "runtime_alias": runtime_alias(row),
        "vm_primitives": [f"{hint['opcode']} {hint['subopcode']} {hint['name']}"],
        "preserve_source_form": True,
        "evidence_notes": [
            f"Classified as a direct {family} alias by localization-display-inventory-aliases.md.",
            "Operand syntax still belongs to a later source-format pass.",
        ],
        "open_questions": ["exact operand syntax for reassembly-friendly source"],
        "frontier": frontier_summary(row),
    }


def unresolved_display_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "command": row["command"],
        "expansion_class": "source_macro",
        "lowering_status": "source_macro_unproven",
        "source_role": "unresolved display helper that likely stages actor, object, location, money, player, or item context before display",
        "confidence": "medium",
        "runtime_alias": None,
        "vm_primitives": ["0x19 data/substitution family", "0x1C print/display family", "event/actionscript context"],
        "preserve_source_form": True,
        "evidence_notes": [
            "Display alias note keeps this out of direct 0x1C leaves until context staging is proven.",
        ],
        "open_questions": ["whether the helper depends on event/actionscript state, text memory state, or both"],
        "frontier": frontier_summary(row),
    }


def unresolved_inventory_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "command": row["command"],
        "expansion_class": "source_macro",
        "lowering_status": "source_macro_unproven",
        "source_role": "unresolved inventory, shop, Tracy/Escargo, transfer, or item-selection source helper",
        "confidence": "medium",
        "runtime_alias": None,
        "vm_primitives": ["0x1A menu/selection family", "0x19 data/substitution family", "0x1C print/display family", "0x1D inventory/money family"],
        "preserve_source_form": True,
        "evidence_notes": [
            "Display/inventory alias note treats this as a likely multi-command source macro.",
        ],
        "open_questions": ["exact multi-command lowering shape"],
        "frontier": frontier_summary(row),
    }


def deferred_row(row: dict[str, Any]) -> dict[str, Any]:
    lane = row["expansion_lane"]
    alias = runtime_alias(row)
    return {
        "command": row["command"],
        "expansion_class": "deferred" if lane != "direct_runtime_hint" else "direct_runtime_hint",
        "lowering_status": "defer_to_other_subsystem",
        "source_role": DEFERRED_LANE_ROLES.get(lane, "retain current frontier status for a later focused pass"),
        "confidence": alias["confidence"] if alias else "-",
        "runtime_alias": alias,
        "vm_primitives": [],
        "preserve_source_form": lane != "direct_runtime_hint",
        "evidence_notes": [f"Retained from frontier lane {lane}; outside this implementation scope."],
        "open_questions": [row.get("next_seam", "Classify expansion lane.")],
        "frontier": frontier_summary(row),
    }


def frontier_summary(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "expansion_lane": row["expansion_lane"],
        "bucket": row["bucket"],
        "count": row["count"],
        "files": row["files"],
        "metadata_records": row["metadata_records"],
        "argument_shapes": row["argument_shapes"],
    }


def build_model(frontier: dict[str, Any]) -> dict[str, Any]:
    rows = []
    seen_commands = set()
    frontier_rows = sorted(frontier["rows"], key=lambda row: row["command"])
    frontier_by_command = {row["command"]: row for row in frontier_rows}

    missing_controls = sorted(set(CONTROL_MODELS) - set(frontier_by_command))
    if missing_controls:
        raise SystemExit(f"control macros missing from frontier: {', '.join(missing_controls)}")

    for command, spec in DIRECT_DISPLAY_ALIASES.items():
        if command not in frontier_by_command:
            raise SystemExit(f"direct display alias missing from frontier: {command}")
        assert_hint(frontier_by_command[command], spec)
    for command, spec in DIRECT_INVENTORY_ALIASES.items():
        if command not in frontier_by_command:
            raise SystemExit(f"direct inventory alias missing from frontier: {command}")
        assert_hint(frontier_by_command[command], spec)

    for row in frontier_rows:
        command = row["command"]
        if command in CONTROL_MODELS:
            model_row = control_row(row)
        elif command in DIRECT_DISPLAY_ALIASES:
            model_row = direct_alias_row(row, DIRECT_DISPLAY_ALIASES[command], "display")
        elif command in DIRECT_INVENTORY_ALIASES:
            model_row = direct_alias_row(row, DIRECT_INVENTORY_ALIASES[command], "inventory/money")
        elif row["expansion_lane"] == "text_vm_display_macro":
            model_row = unresolved_display_row(row)
        elif row["expansion_lane"] == "text_vm_inventory_macro":
            model_row = unresolved_inventory_row(row)
        else:
            model_row = deferred_row(row)
        rows.append(model_row)
        seen_commands.add(command)

    status_counts = Counter(row["lowering_status"] for row in rows)
    class_counts = Counter(row["expansion_class"] for row in rows)
    return {
        "generated_by": "tools/build_localization_macro_expansion_model.py",
        "source_frontier": rel(DEFAULT_FRONTIER),
        "summary": {
            "commands": len(rows),
            "source_macro_shape_proven": status_counts["source_macro_shape_proven"],
            "source_macro_unproven": status_counts["source_macro_unproven"],
            "direct_vm_alias": status_counts["direct_vm_alias"],
            "defer_to_other_subsystem": status_counts["defer_to_other_subsystem"],
            "expansion_classes": dict(sorted(class_counts.items())),
        },
        "rows": rows,
    }


def markdown_table_rows(rows: list[dict[str, Any]], status: str | None = None) -> list[dict[str, Any]]:
    if status is None:
        return rows
    return [row for row in rows if row["lowering_status"] == status]


def primitive_label(row: dict[str, Any]) -> str:
    return ", ".join(row["vm_primitives"]) or "-"


def alias_label(row: dict[str, Any]) -> str:
    alias = row["runtime_alias"]
    if not alias:
        return "-"
    opcode = alias["opcode"]
    if "subopcode" in alias:
        opcode = f"{opcode} {alias['subopcode']}"
    return f"`{opcode}` `{alias['name']}` ({alias['confidence']})"


def write_markdown(model: dict[str, Any], output_path: Path) -> None:
    summary = model["summary"]
    rows = model["rows"]
    lines = [
        "# Localization Macro Expansion Model",
        "",
        "Generated by `tools/build_localization_macro_expansion_model.py` from",
        "`build/localization-macro-expansion-frontier.json`.",
        "",
        "This model turns the current frontier into source-level expansion",
        "semantics without checking in dialogue bodies or inventing new Text VM",
        "opcodes.",
        "",
        "## Summary",
        "",
        f"- Commands modeled: `{summary['commands']}`",
        f"- Proven source macro shapes: `{summary['source_macro_shape_proven']}`",
        f"- Unproven source macro shapes: `{summary['source_macro_unproven']}`",
        f"- Direct VM aliases: `{summary['direct_vm_alias']}`",
        f"- Deferred to other subsystem or pass: `{summary['defer_to_other_subsystem']}`",
        "",
        "## Proven Control / Register / Branch Macros",
        "",
        "These are source macros over existing bank-`01` Text VM primitives, not",
        "native runtime opcodes.",
        "",
        "| Command | Confidence | Source role | Likely VM primitives |",
        "| --- | --- | --- | --- |",
    ]
    for row in markdown_table_rows(rows, "source_macro_shape_proven"):
        lines.append(
            f"| `{row['command']}` | {row['confidence']} | {row['source_role']} | {primitive_label(row)} |"
        )

    lines.extend(
        [
            "",
            "## Direct Display / Inventory Aliases",
            "",
            "These aliases preserve readable source names while lowering through already",
            "documented Text VM leaves.",
            "",
            "| Command | Runtime alias | Source role |",
            "| --- | --- | --- |",
        ]
    )
    direct_rows = sorted(markdown_table_rows(rows, "direct_vm_alias"), key=lambda row: row["command"])
    for row in direct_rows:
        lines.append(f"| `{row['command']}` | {alias_label(row)} | {row['source_role']} |")

    lines.extend(
        [
            "",
            "## Unproven Display / Inventory Source Macros",
            "",
            "These remain source macros until exact multi-command lowering is proven.",
            "",
            "| Command | Frontier lane | Source role | Likely VM families |",
            "| --- | --- | --- | --- |",
        ]
    )
    for row in markdown_table_rows(rows, "source_macro_unproven"):
        lane = row["frontier"]["expansion_lane"]
        lines.append(f"| `{row['command']}` | `{lane}` | {row['source_role']} | {primitive_label(row)} |")

    lines.extend(
        [
            "",
            "## Deferred Rows",
            "",
            "The remaining commands retain their frontier status for later focused",
            "subsystem work.",
            "",
            "| Lowering status | Count |",
            "| --- | ---: |",
        ]
    )
    deferred_by_lane = Counter(row["frontier"]["expansion_lane"] for row in markdown_table_rows(rows, "defer_to_other_subsystem"))
    for lane, count in sorted(deferred_by_lane.items()):
        lines.append(f"| `{lane}` | {count} |")

    lines.extend(
        [
            "",
            "## Source Contract",
            "",
            "- preserve control/register/branch macros as source syntax until exact byte templates are proven",
            "- preserve direct display and inventory aliases as readable source forms over known VM leaves",
            "- preserve unresolved display, shop, Tracy/Escargo, and item-selection helpers as source macros",
            "- do not introduce new runtime opcodes for authoring conveniences",
            "",
        ]
    )
    output_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--frontier", type=Path, default=DEFAULT_FRONTIER)
    parser.add_argument("--json-out", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown-out", type=Path, default=DEFAULT_MARKDOWN)
    args = parser.parse_args()

    frontier = load_frontier(args.frontier)
    model = build_model(frontier)
    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.markdown_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(json.dumps(model, indent=2, sort_keys=True), encoding="utf-8")
    write_markdown(model, args.markdown_out)
    print(f"wrote {args.json_out}")
    print(f"wrote {args.markdown_out}")
    print(
        "commands={commands} proven={source_macro_shape_proven} direct_alias={direct_vm_alias} unproven={source_macro_unproven}".format(
            **model["summary"]
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
