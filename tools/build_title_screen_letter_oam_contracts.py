from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_JSON_OUT = ROOT / "build" / "title-screen-letter-oam-contracts.json"
DEFAULT_MARKDOWN_OUT = ROOT / "notes" / "title-screen-letter-oam-contracts.md"
TABLE_PATH = ROOT / "build" / "assets" / "e1" / "tables" / "041_data_unknown_e1ce08_asm.bin"
POSITIONS_PATH = ROOT / "refs" / "eb-decompile-4ef92" / "TitleScreen" / "Chars" / "positions.yml"
LEGACY_PATH = (
    ROOT
    / "refs"
    / "earthbound-disasm-legacy"
    / "Earthbound Decomp"
    / "EB"
    / "Routine_Macros_EB.asm"
)


BASE_ADDRESS = 0xCE08
BANK = "E1"
LETTERS = list("EARTHOUND")
RECORD_SIZE = 0x2D
OAM_ENTRY_SIZE = 5
POINTER_TABLE_OFFSET = RECORD_SIZE * len(LETTERS)


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def signed_byte(value: int) -> int:
    return value - 0x100 if value >= 0x80 else value


def load_positions() -> dict[int, dict[str, int]]:
    positions: dict[int, dict[str, int]] = {}
    current: int | None = None
    stack: list[str] = []
    for raw_line in POSITIONS_PATH.read_text(encoding="utf-8").splitlines():
        if not raw_line.strip():
            continue
        indent = len(raw_line) - len(raw_line.lstrip(" "))
        line = raw_line.strip()
        if indent == 0 and line.endswith(":") and line[:-1].isdigit():
            current = int(line[:-1])
            positions[current] = {}
            stack = []
            continue
        if current is None:
            continue
        if line.endswith(":"):
            key = line[:-1]
            if indent == 2:
                stack = [key]
            continue
        if ":" not in line:
            continue
        key, value = [part.strip() for part in line.split(":", 1)]
        if indent == 4 and stack:
            positions[current][f"{stack[-1]}_{key}"] = int(value)
        elif indent == 2:
            positions[current][key] = int(value)
    return positions


def parse_oam_entry(raw: bytes, index: int) -> dict[str, Any]:
    y, tile, attributes, x, control = raw
    return {
        "index": index,
        "y": y,
        "y_signed": signed_byte(y),
        "tile": tile,
        "attributes": attributes,
        "x": x,
        "x_signed": signed_byte(x),
        "control": control,
        "control_high_bit_set": bool(control & 0x80),
        "raw": [f"0x{value:02X}" for value in raw],
    }


def parse_table(data: bytes) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if len(data) != POINTER_TABLE_OFFSET + len(LETTERS) * 2:
        raise ValueError(f"Unexpected E1:CE08 table size: {len(data)}")
    records = []
    for index, letter in enumerate(LETTERS):
        start = index * RECORD_SIZE
        end = start + RECORD_SIZE
        raw = data[start:end]
        entries = [
            parse_oam_entry(raw[offset : offset + OAM_ENTRY_SIZE], offset // OAM_ENTRY_SIZE)
            for offset in range(0, RECORD_SIZE, OAM_ENTRY_SIZE)
        ]
        records.append(
            {
                "index": index,
                "letter": letter,
                "address": f"{BANK}:{BASE_ADDRESS + start:04X}",
                "range": f"{BANK}:{BASE_ADDRESS + start:04X}..{BANK}:{BASE_ADDRESS + end:04X}",
                "bytes": len(raw),
                "entry_count": len(entries),
                "entries": entries,
                "terminal_entry_control_has_high_bit": bool(entries[-1]["control_high_bit_set"]),
            }
        )

    pointers = []
    for index in range(len(LETTERS)):
        offset = POINTER_TABLE_OFFSET + index * 2
        target = data[offset] | (data[offset + 1] << 8)
        expected = BASE_ADDRESS + index * RECORD_SIZE
        pointers.append(
            {
                "index": index,
                "letter": LETTERS[index],
                "address": f"{BANK}:{BASE_ADDRESS + offset:04X}",
                "target": f"{BANK}:{target:04X}",
                "expected_target": f"{BANK}:{expected:04X}",
                "matches_record": target == expected,
            }
        )
    return records, pointers


def legacy_evidence_found() -> dict[str, Any]:
    text = LEGACY_PATH.read_text(encoding="utf-8", errors="replace")
    fragments = [
        "TitleScreenLetterOAMData:",
        "TitleScreenLetterOAMData_E",
        "TitleScreenLetterOAMData_A",
        "TitleScreenLetterOAMData_R",
        "TitleScreenLetterOAMData_T",
        "TitleScreenLetterOAMData_H",
        "TitleScreenLetterOAMData_O",
        "TitleScreenLetterOAMData_U",
        "TitleScreenLetterOAMData_N",
        "TitleScreenLetterOAMData_D",
        "DATA_E1CF9D:",
    ]
    missing = [fragment for fragment in fragments if fragment not in text]
    return {"path": rel(LEGACY_PATH), "required_fragments_found": not missing, "missing_fragments": missing}


def build_contract() -> dict[str, Any]:
    data = TABLE_PATH.read_bytes()
    positions = load_positions()
    records, pointers = parse_table(data)
    for record in records:
        pos = positions.get(int(record["index"]), {})
        record["ebdecomp_position"] = pos
        record["ebdecomp_letter_width"] = pos.get("width")
        record["ebdecomp_letter_height"] = pos.get("height")

    return {
        "schema": "earthbound-decomp.title-screen-letter-oam-contracts.v1",
        "scope": "E1:CE08 title-screen letter OAM records and E1:CF9D pointer table",
        "inputs": {
            "table_bytes": rel(TABLE_PATH),
            "ebdecomp_positions": rel(POSITIONS_PATH),
            "legacy_oam_labels": rel(LEGACY_PATH),
        },
        "generated_json": rel(DEFAULT_JSON_OUT),
        "tracked_markdown": rel(DEFAULT_MARKDOWN_OUT),
        "summary": {
            "source_range": "E1:CE08..E1:CFAF",
            "total_bytes": len(data),
            "letter_records": len(records),
            "letter_record_size": RECORD_SIZE,
            "oam_entry_size": OAM_ENTRY_SIZE,
            "oam_entries_per_letter": RECORD_SIZE // OAM_ENTRY_SIZE,
            "pointer_table_range": f"E1:{BASE_ADDRESS + POINTER_TABLE_OFFSET:04X}..E1:{BASE_ADDRESS + len(data):04X}",
            "pointer_count": len(pointers),
            "letters": "".join(LETTERS),
            "record_set_note": "The animated OAM record set is EARTHOUND; no separate B record is present in E1:CE08.",
        },
        "validation": {
            "total_size_is_423_bytes": len(data) == 423,
            "record_area_is_9_records_of_0x2d": POINTER_TABLE_OFFSET == 405,
            "all_records_have_9_oam_entries": all(record["entry_count"] == 9 for record in records),
            "all_pointer_targets_match_record_starts": all(pointer["matches_record"] for pointer in pointers),
            "all_terminal_controls_have_high_bit": all(
                record["terminal_entry_control_has_high_bit"] for record in records
            ),
            "ebdecomp_has_9_position_rows": len(positions) == len(LETTERS),
            "legacy_oam_labels_found": legacy_evidence_found()["required_fragments_found"],
        },
        "records": records,
        "pointer_table": pointers,
        "legacy_evidence": legacy_evidence_found(),
        "runtime_context": [
            {
                "source": "refs/earthbound-disasm-legacy/Earthbound Decomp/EB/Routine_Macros_EB.asm",
                "role": "Names E1:CE08 as `TitleScreenLetterOAMData`, labels records `.E` through `.D`, and defines the `DATA_E1CF9D` pointer table.",
            },
            {
                "source": "refs/eb-decompile-4ef92/TitleScreen/Chars/positions.yml",
                "role": "Provides nine title-character rows with 24x48 dimensions and top-left offsets used as higher-level visual refs.",
            },
            {
                "source": "notes/title-screen-logo-palette-event-helpers-c0ebe0-c0ee53.md",
                "role": "Documents the adjacent C0 title logo/palette event helpers that load title graphics and advance the title palette animation.",
            },
        ],
        "open_questions": [
            "Name the five OAM-entry bytes precisely from the renderer/caller that consumes E1:CF9D.",
            "Tie EBDecomp's 24x48 per-letter position rows to the exact per-sprite offset convention used by these nine-entry records.",
        ],
    }


def render_markdown(contract: dict[str, Any]) -> str:
    summary = contract["summary"]
    lines = [
        "# Title-Screen Letter OAM Contracts",
        "",
        "Generated by `tools/build_title_screen_letter_oam_contracts.py`. This promotes the former `data/unknown/E1CE08.asm` span into the legacy-corroborated title-screen letter OAM table.",
        "",
        "No ROM-derived table bytes are checked in by this report.",
        "",
        "## Snapshot",
        "",
        f"- source range: `{summary['source_range']}`",
        f"- total bytes: `{summary['total_bytes']}`",
        f"- letter records: `{summary['letter_records']}`",
        f"- record size: `0x{summary['letter_record_size']:02X}`",
        f"- OAM-ish entry size: `{summary['oam_entry_size']}`",
        f"- entries per letter: `{summary['oam_entries_per_letter']}`",
        f"- pointer table: `{summary['pointer_table_range']}`",
        f"- pointer count: `{summary['pointer_count']}`",
        f"- record letters: `{summary['letters']}`",
        f"- record-set note: {summary['record_set_note']}",
        "",
        "## Validation",
        "",
    ]
    for key, value in contract["validation"].items():
        lines.append(f"- `{key}`: `{str(value).lower()}`")

    lines.extend(
        [
            "",
            "## Letter Records",
            "",
            "| Index | Letter | Range | Entries | EBDecomp x/y | EBDecomp size | Terminal high bit |",
            "| ---: | --- | --- | ---: | --- | --- | --- |",
        ]
    )
    for record in contract["records"]:
        pos = record["ebdecomp_position"]
        lines.append(
            "| {index} | `{letter}` | `{range}` | {entries} | `{x},{y}` | `{width}x{height}` | `{terminal}` |".format(
                index=record["index"],
                letter=record["letter"],
                range=record["range"],
                entries=record["entry_count"],
                x=pos.get("x"),
                y=pos.get("y"),
                width=pos.get("width"),
                height=pos.get("height"),
                terminal=str(record["terminal_entry_control_has_high_bit"]).lower(),
            )
        )

    lines.extend(
        [
            "",
            "## Pointer Table",
            "",
            "| Index | Letter | Pointer address | Target | Matches record |",
            "| ---: | --- | --- | --- | --- |",
        ]
    )
    for pointer in contract["pointer_table"]:
        lines.append(
            f"| {pointer['index']} | `{pointer['letter']}` | `{pointer['address']}` | `{pointer['target']}` | `{str(pointer['matches_record']).lower()}` |"
        )

    lines.extend(["", "## Record Entry Bytes", ""])
    for record in contract["records"]:
        lines.append(f"### {record['letter']} `{record['address']}`")
        lines.append("")
        lines.append("| Entry | y | tile | attrs | x | control | raw |")
        lines.append("| ---: | ---: | --- | --- | ---: | --- | --- |")
        for entry in record["entries"]:
            lines.append(
                "| {index} | {y_signed} | `{tile}` | `{attrs}` | {x_signed} | `{control}` | {raw} |".format(
                    index=entry["index"],
                    y_signed=entry["y_signed"],
                    tile=f"0x{entry['tile']:02X}",
                    attrs=f"0x{entry['attributes']:02X}",
                    x_signed=entry["x_signed"],
                    control=f"0x{entry['control']:02X}",
                    raw=", ".join(f"`{value}`" for value in entry["raw"]),
                )
            )
        lines.append("")

    lines.extend(["## Runtime Context", ""])
    for item in contract["runtime_context"]:
        lines.append(f"- `{item['source']}`: {item['role']}")

    lines.extend(["", "## Open Questions", ""])
    for question in contract["open_questions"]:
        lines.append(f"- {question}")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build title-screen letter OAM contracts.")
    parser.add_argument("--json-out", default=str(DEFAULT_JSON_OUT))
    parser.add_argument("--markdown-out", default=str(DEFAULT_MARKDOWN_OUT))
    args = parser.parse_args()

    contract = build_contract()
    json_out = Path(args.json_out)
    json_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(json.dumps(contract, indent=2) + "\n", encoding="utf-8")

    markdown_out = Path(args.markdown_out)
    markdown_out.parent.mkdir(parents=True, exist_ok=True)
    markdown_out.write_text(render_markdown(contract), encoding="utf-8")

    summary = contract["summary"]
    print(
        "title letter OAM: "
        f"{summary['letter_records']} records, "
        f"{summary['pointer_count']} pointers, "
        f"{summary['total_bytes']} bytes"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
