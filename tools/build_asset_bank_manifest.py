from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import rom_tools


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_YML = ROOT / "refs" / "ebsrc-main" / "ebsrc-main" / "earthbound.yml"
BANK_CONFIG_ROOT = ROOT / "refs" / "ebsrc-main" / "ebsrc-main" / "src" / "bankconfig"
SRC_ROOT = ROOT / "refs" / "ebsrc-main" / "ebsrc-main" / "src"
INCLUDE_RE = re.compile(r'\.INCLUDE\s+"([^"]+)"', re.IGNORECASE)
LOCALEINCLUDE_RE = re.compile(r'\bLOCALEINCLUDE\s+"([^"]+)"', re.IGNORECASE)
BINARY_SLICE_RE = re.compile(r'\b(?:LOCALEBINARY|BINARY)\s+"([^"]+)"\s*,\s*([^,\s]+)\s*,\s*([^,\s]+)', re.IGNORECASE)
BINARY_RE = re.compile(r'\b(LOCALEBINARY|BINARY)\s+"([^"]+)"', re.IGNORECASE)
INCBIN_RE = re.compile(r'\.INCBIN\s+"([^"]+)"(?:\s*,\s*([^,\s]+))?(?:\s*,\s*([^,\s]+))?', re.IGNORECASE)
INSERT_AUDIO_PACK_RE = re.compile(r"\bINSERT_AUDIO_PACK\s+([0-9]+)\b", re.IGNORECASE)
LABEL_RE = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*):")
DIRECTIVE_RE = re.compile(r"^\.(BYTE|WORD|DWORD)\s+(.+)$", re.IGNORECASE)
IF_RE = re.compile(r"\.IF\s+(.+)$", re.IGNORECASE)
DEFINED_TERM_RE = re.compile(r"(!?)\.DEFINED\(([^)]+)\)", re.IGNORECASE)
ELSE_RE = re.compile(r"\.ELSE\b", re.IGNORECASE)
ENDIF_RE = re.compile(r"\.ENDIF\b", re.IGNORECASE)
ASSIGN_RE = re.compile(r"^(@[A-Za-z0-9_]+)\s*=\s*(.+)$")
REPEAT_RE = re.compile(r"\.REPEAT\s+(.+)$", re.IGNORECASE)
ENDREPEAT_RE = re.compile(r"\.ENDREPEAT\b", re.IGNORECASE)
PADDED_TEXT_RE = re.compile(r'\b(PADDEDEBTEXT|PADDEDASCII)\s+"(?:\\.|[^"])*"\s*,\s*([^,\s]+)', re.IGNORECASE)
STAFF_TEXT_RE = re.compile(r'\b(EBSTAFF_SMALLTEXT|EBSTAFF_BIGTEXT)\s+"((?:\\.|[^"])*)"', re.IGNORECASE)
STAFF_VERTICAL_SPACE_RE = re.compile(r"\bEBSTAFF_VERTICALSPACE\s+([^,\s]+)", re.IGNORECASE)
STAFF_SINGLE_BYTE_RE = re.compile(r"\b(EBSTAFF_PRINTPLAYER|EBSTAFF_ENDCREDITS|EBSTAFF_END)\b", re.IGNORECASE)
US_RETAIL_DEFINES = {
    "USA": True,
    "JPN": False,
    "PROTOTYPE19950327": False,
}
US_RETAIL_CONSTANTS = {
    "PSI_NAME_SIZE": 25,
}


def eval_defined_condition(expression: str) -> bool:
    or_terms = expression.split("||")
    for or_term in or_terms:
        and_value = True
        for and_term in or_term.split("&&"):
            match = DEFINED_TERM_RE.search(and_term.strip())
            if not match:
                and_value = False
                continue
            symbol = match.group(2).upper()
            value = US_RETAIL_DEFINES.get(symbol, False)
            if match.group(1):
                value = not value
            and_value = and_value and value
        if and_value:
            return True
    return False


def eval_asm_int(expression: str, variables: dict[str, int]) -> int:
    expression = expression.split(";", 1)[0].strip()
    if expression in variables:
        return variables[expression]
    if expression in US_RETAIL_CONSTANTS:
        return US_RETAIL_CONSTANTS[expression]
    if expression.startswith("$"):
        return int(expression[1:], 16)
    return int(expression, 0)


@dataclass(frozen=True)
class SourceItem:
    order: int
    kind: str
    source_path: str
    label: str | None
    payload_path: str | None = None
    directive: str | None = None
    inline_size: int = 0
    byte_values: int = 0
    word_values: int = 0
    dword_values: int = 0


@dataclass(frozen=True)
class YmlAsset:
    subdir: str
    name: str
    offset: int
    size: int
    extension: str
    compressed: bool


def bank_index(bank: str) -> str:
    bank = bank.upper()
    if len(bank) == 2 and bank[0] in {"C", "D", "E", "F"}:
        return f"{int(bank, 16) - 0xC0:02X}"
    return bank[-2:]


def cpu_for_file_offset(offset: int) -> str:
    return f"{rom_tools.canonical_bank_for_file_offset(offset):02X}:{offset & 0xFFFF:04X}"


def parse_bank_source(path: Path, seen: set[Path] | None = None, order_start: int = 0) -> list[SourceItem]:
    if seen is None:
        seen = set()
    path = path.resolve()
    if path in seen:
        return []
    seen.add(path)

    items: list[SourceItem] = []
    pending_label: str | None = None
    order = order_start
    condition_stack: list[tuple[bool, bool]] = [(True, True)]
    variables: dict[str, int] = {}
    repeat_stack: list[int] = []

    def active() -> bool:
        parent_active, condition_active = condition_stack[-1]
        return parent_active and condition_active

    for raw_line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        stripped = raw_line.split(";", 1)[0].strip()
        if_match = IF_RE.search(stripped)
        if if_match:
            condition_stack.append((active(), eval_defined_condition(if_match.group(1))))
            pending_label = None
            continue
        if ELSE_RE.search(stripped):
            if len(condition_stack) > 1:
                parent_active, condition_active = condition_stack[-1]
                condition_stack[-1] = (parent_active, not condition_active)
            pending_label = None
            continue
        if ENDIF_RE.search(stripped):
            if len(condition_stack) > 1:
                condition_stack.pop()
            pending_label = None
            continue
        if not active():
            continue

        assign_match = ASSIGN_RE.match(stripped)
        if assign_match:
            variables[assign_match.group(1)] = eval_asm_int(assign_match.group(2), variables)
            pending_label = None
            continue
        repeat_match = REPEAT_RE.search(stripped)
        if repeat_match:
            repeat_stack.append(eval_asm_int(repeat_match.group(1), variables))
            pending_label = None
            continue
        if ENDREPEAT_RE.search(stripped):
            if repeat_stack:
                repeat_stack.pop()
            pending_label = None
            continue

        label_match = LABEL_RE.match(raw_line)
        if label_match:
            pending_label = label_match.group(1)
            continue

        binary_slice_match = BINARY_SLICE_RE.search(raw_line)
        if binary_slice_match:
            size = eval_asm_int(binary_slice_match.group(3), variables)
            items.append(
                SourceItem(
                    order=order,
                    kind="inline",
                    source_path=path.relative_to(ROOT).as_posix(),
                    label=pending_label,
                    directive="BINARY_SLICE",
                    inline_size=size,
                    byte_values=size,
                )
            )
            order += 1
            pending_label = None
            continue

        incbin_match = INCBIN_RE.search(raw_line)
        if incbin_match:
            source = incbin_match.group(1)
            offset = eval_asm_int(incbin_match.group(2), variables) if incbin_match.group(2) else 0
            size = 0
            if incbin_match.group(3):
                size = eval_asm_int(incbin_match.group(3), variables)
            else:
                incbin_path = SRC_ROOT / source
                if incbin_path.exists():
                    size = incbin_path.stat().st_size - offset
            if size:
                items.append(
                    SourceItem(
                        order=order,
                        kind="inline",
                        source_path=path.relative_to(ROOT).as_posix(),
                        label=pending_label,
                        directive="INCBIN",
                        inline_size=size,
                        byte_values=size,
                    )
                )
            else:
                items.append(
                    SourceItem(
                        order=order,
                        kind="include",
                        source_path=path.relative_to(ROOT).as_posix(),
                        label=pending_label,
                        payload_path=f"incbin:{source}",
                    )
                )
            order += 1
            pending_label = None
            continue

        binary_match = BINARY_RE.search(raw_line)
        if binary_match:
            directive = binary_match.group(1).upper()
            payload_path = binary_match.group(2)
            items.append(
                SourceItem(
                    order=order,
                    kind="binary",
                    source_path=path.relative_to(ROOT).as_posix(),
                    label=pending_label,
                    payload_path=payload_path,
                    directive=directive,
                )
            )
            order += 1
            pending_label = None
            continue

        audio_pack_match = INSERT_AUDIO_PACK_RE.search(raw_line)
        if audio_pack_match:
            pack_id = audio_pack_match.group(1)
            items.append(
                SourceItem(
                    order=order,
                    kind="binary",
                    source_path=path.relative_to(ROOT).as_posix(),
                    label=f"AUDIO_PACK_{pack_id}",
                    payload_path=f"audiopacks/{pack_id}.ebm",
                    directive="INSERT_AUDIO_PACK",
                )
            )
            order += 1
            pending_label = None
            continue

        directive_match = DIRECTIVE_RE.match(stripped)
        if directive_match:
            directive = directive_match.group(1).lower()
            values = [value for value in directive_match.group(2).split(",") if value.strip()]
            multiplier = 1
            for repeat_count in repeat_stack:
                multiplier *= repeat_count
            byte_values = len(values) * multiplier if directive == "byte" else 0
            word_values = len(values) * multiplier if directive == "word" else 0
            dword_values = len(values) * multiplier if directive == "dword" else 0
            size = byte_values + (word_values * 2) + (dword_values * 4)
            items.append(
                SourceItem(
                    order=order,
                    kind="inline",
                    source_path=path.relative_to(ROOT).as_posix(),
                    label=pending_label,
                    directive=directive.upper(),
                    inline_size=size,
                    byte_values=byte_values,
                    word_values=word_values,
                    dword_values=dword_values,
                )
            )
            order += 1
            pending_label = None
            continue

        include_match = INCLUDE_RE.search(raw_line)
        if include_match:
            include = include_match.group(1)
            if include in {"common.asm", "config.asm", "structs.asm", "flyovermacros.asm"} or include.startswith("symbols/"):
                pending_label = None
                continue
            if include.startswith("bankconfig/"):
                nested = SRC_ROOT / include
                nested_items = parse_bank_source(nested, seen, order)
                items.extend(nested_items)
                order += len(nested_items)
                pending_label = None
                continue
            items.append(
                SourceItem(
                    order=order,
                    kind="include",
                    source_path=path.relative_to(ROOT).as_posix(),
                    label=None,
                    payload_path=include,
                )
            )
            order += 1
            pending_label = None
            continue

        localeinclude_match = LOCALEINCLUDE_RE.search(raw_line)
        if localeinclude_match:
            include = localeinclude_match.group(1)
            items.append(
                SourceItem(
                    order=order,
                    kind="include",
                    source_path=path.relative_to(ROOT).as_posix(),
                    label=pending_label,
                    payload_path=f"localeinclude:{include}",
                )
            )
            order += 1
            pending_label = None

    return items


def parse_yml_assets(yml_path: Path) -> dict[tuple[str, str, str], YmlAsset]:
    assets: dict[tuple[str, str, str], YmlAsset] = {}
    current: dict[str, object] | None = None

    def flush() -> None:
        nonlocal current
        if not current:
            return
        required = {"subdir", "name", "offset", "size", "extension", "compressed"}
        if required <= set(current):
            asset = YmlAsset(
                subdir=str(current["subdir"]),
                name=str(current["name"]),
                offset=int(str(current["offset"]), 0),
                size=int(str(current["size"]), 0),
                extension=str(current["extension"]),
                compressed=str(current["compressed"]).lower() == "true",
            )
            assets[(asset.subdir, asset.name, asset.extension)] = asset
        current = None

    for raw_line in yml_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        stripped = raw_line.strip()
        if stripped.startswith("- subdir:"):
            flush()
            current = {"subdir": stripped.split(":", 1)[1].strip().strip("'\"")}
            continue
        if current is None or ":" not in stripped:
            continue
        key, value = stripped.split(":", 1)
        current[key.strip()] = value.strip().strip("'\"")
    flush()
    return assets


def payload_key(payload_path: str) -> tuple[str, str, str] | None:
    parts = payload_path.split("/")
    subdir = "/".join(parts[:-1]) if len(parts) > 1 else ""
    filename = parts[-1]
    bits = filename.split(".")
    if len(bits) < 2:
        return None
    return subdir, bits[0], bits[1]


def lookup_asset_for_item(item: SourceItem, yml_assets: dict[tuple[str, str, str], YmlAsset]) -> YmlAsset | None:
    if item.payload_path is None:
        return None
    key = payload_key(item.payload_path)
    asset = yml_assets.get(key) if key else None
    if asset is not None or item.directive != "LOCALEBINARY" or key is None:
        return asset
    subdir, name, extension = key
    return yml_assets.get((f"US/{subdir}", name, extension))


def estimate_asm_size(path: Path) -> dict[str, int]:
    counts = {"byte": 0, "word": 0, "dword": 0}
    label_count = 0
    condition_stack: list[tuple[bool, bool]] = [(True, True)]

    def active() -> bool:
        parent_active, condition_active = condition_stack[-1]
        return parent_active and condition_active

    for raw_line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        stripped = raw_line.split(";", 1)[0].strip()
        if_match = IF_RE.search(stripped)
        if if_match:
            condition_stack.append((active(), eval_defined_condition(if_match.group(1))))
            continue
        if ELSE_RE.search(stripped):
            if len(condition_stack) > 1:
                parent_active, condition_active = condition_stack[-1]
                condition_stack[-1] = (parent_active, not condition_active)
            continue
        if ENDIF_RE.search(stripped):
            if len(condition_stack) > 1:
                condition_stack.pop()
            continue
        if not active():
            continue
        if LABEL_RE.match(raw_line):
            label_count += 1
        match = DIRECTIVE_RE.match(stripped)
        if not match:
            padded_match = PADDED_TEXT_RE.search(stripped)
            if padded_match:
                try:
                    counts["byte"] += eval_asm_int(padded_match.group(2), {})
                except ValueError:
                    pass
                continue
            staff_text_match = STAFF_TEXT_RE.search(stripped)
            if staff_text_match:
                counts["byte"] += len(staff_text_match.group(2)) + 2
                continue
            staff_vertical_space_match = STAFF_VERTICAL_SPACE_RE.search(stripped)
            if staff_vertical_space_match:
                counts["byte"] += 2
                continue
            if STAFF_SINGLE_BYTE_RE.search(stripped):
                counts["byte"] += 1
            continue
        directive = match.group(1).lower()
        values = [value for value in match.group(2).split(",") if value.strip()]
        counts[directive] += len(values)
    size = counts["byte"] + (counts["word"] * 2) + (counts["dword"] * 4)
    return {
        "size": size,
        "labels": label_count,
        "byte_values": counts["byte"],
        "word_values": counts["word"],
        "dword_values": counts["dword"],
    }


def build_manifest(bank: str, yml_path: Path, rom_path: Path) -> dict[str, object]:
    bank = bank.upper()
    index = bank_index(bank)
    bank_start = int(index, 16) * 0x10000
    bank_end = bank_start + 0xFFFF
    config = BANK_CONFIG_ROOT / "US" / f"bank{index}.asm"
    source_items = parse_bank_source(config)
    yml_assets = parse_yml_assets(yml_path)
    rom = rom_tools.load_rom(rom_path)

    binary_entries: list[dict[str, object]] = []
    table_entries: list[dict[str, object]] = []
    missing_payload_metadata: list[str] = []
    cursor = bank_start
    layout_blocked_by_missing_include: str | None = None

    def next_known_binary_offset(after_order: int) -> int | None:
        offsets = []
        for candidate in source_items:
            if candidate.order <= after_order or candidate.kind != "binary":
                continue
            asset = lookup_asset_for_item(candidate, yml_assets)
            if asset is not None:
                offsets.append(asset.offset)
        return min(offsets) if offsets else None

    for item in source_items:
        if item.kind == "binary" and item.payload_path is not None:
            asset = lookup_asset_for_item(item, yml_assets)
            if asset is None:
                missing_payload_metadata.append(item.payload_path)
                next_offset = next_known_binary_offset(item.order)
                if next_offset is not None and next_offset > cursor:
                    key = payload_key(item.payload_path)
                    subdir, name, extension = key if key else ("", item.payload_path, "")
                    size = next_offset - cursor
                    entry = {
                        "order": item.order,
                        "label": item.label,
                        "payload_path": item.payload_path,
                        "subdir": subdir,
                        "name": name,
                        "extension": extension,
                        "compressed": item.payload_path.lower().endswith(".lzhal"),
                        "file_offset": f"0x{cursor:06X}",
                        "cpu_start": cpu_for_file_offset(cursor),
                        "cpu_end": cpu_for_file_offset(cursor + size - 1),
                        "size": size,
                        "first_bytes": " ".join(f"{byte:02X}" for byte in rom[cursor:cursor + min(size, 8)]),
                        "inferred_from_next_asset": True,
                        "missing_yml_metadata": True,
                    }
                    binary_entries.append(entry)
                    cursor = next_offset
                continue
            layout_blocked_by_missing_include = None
            entry = {
                "order": item.order,
                "label": item.label,
                "payload_path": item.payload_path,
                "subdir": asset.subdir,
                "name": asset.name,
                "extension": asset.extension,
                "compressed": asset.compressed,
                "file_offset": f"0x{asset.offset:06X}",
                "cpu_start": cpu_for_file_offset(asset.offset),
                "cpu_end": cpu_for_file_offset(asset.offset + asset.size - 1),
                "size": asset.size,
                "first_bytes": " ".join(f"{byte:02X}" for byte in rom[asset.offset:asset.offset + min(asset.size, 8)]),
            }
            binary_entries.append(entry)
            cursor = max(cursor, asset.offset + asset.size)
            continue

        if item.kind == "inline":
            if layout_blocked_by_missing_include:
                table_entries.append(
                    {
                        "order": item.order,
                        "include": f"inline:{item.label or item.directive or 'data'}",
                        "error": f"offset blocked by missing prior include: {layout_blocked_by_missing_include}",
                    }
                )
                continue
            size = item.inline_size
            next_offset = next_known_binary_offset(item.order)
            if next_offset is not None and cursor >= next_offset:
                table_entries.append(
                    {
                        "order": item.order,
                        "include": f"inline:{item.label or item.directive or 'data'}",
                        "error": "covered by prior inferred generated table block",
                    }
                )
                continue
            table_entries.append(
                {
                    "order": item.order,
                    "include": f"inline:{item.label or item.directive or 'data'}",
                    "file_offset": f"0x{cursor:06X}",
                    "cpu_start": cpu_for_file_offset(cursor),
                    "cpu_end": cpu_for_file_offset(cursor + size - 1) if size else cpu_for_file_offset(cursor),
                    "size": size,
                    "labels": 1 if item.label else 0,
                    "byte_values": item.byte_values,
                    "word_values": item.word_values,
                    "dword_values": item.dword_values,
                    "source_path": item.source_path,
                }
            )
            cursor += size
            continue

        if item.kind != "include" or item.payload_path is None:
            continue
        include_path = SRC_ROOT / item.payload_path
        next_offset = next_known_binary_offset(item.order)
        if next_offset is not None and cursor >= next_offset:
            table_entries.append(
                {
                    "order": item.order,
                    "include": item.payload_path,
                    "error": "covered by prior inferred generated table block",
                }
            )
            continue
        if not include_path.exists():
            if next_offset is not None and next_offset > cursor:
                size = next_offset - cursor
                table_entries.append(
                    {
                        "order": item.order,
                        "include": item.payload_path,
                        "file_offset": f"0x{cursor:06X}",
                        "cpu_start": cpu_for_file_offset(cursor),
                        "cpu_end": cpu_for_file_offset(cursor + size - 1) if size else cpu_for_file_offset(cursor),
                        "size": size,
                        "labels": 0,
                        "byte_values": 0,
                        "word_values": 0,
                        "dword_values": 0,
                        "inferred_from_next_asset": True,
                    }
                )
                cursor += size
                continue
            table_entries.append(
                {
                    "order": item.order,
                    "include": item.payload_path,
                    "error": "missing include source; subsequent offsets blocked",
                }
            )
            layout_blocked_by_missing_include = item.payload_path
            continue
        if layout_blocked_by_missing_include:
            table_entries.append(
                {
                    "order": item.order,
                    "include": item.payload_path,
                    "error": f"offset blocked by missing prior include: {layout_blocked_by_missing_include}",
                }
            )
            continue
        estimate = estimate_asm_size(include_path)
        size = estimate["size"]
        entry = {
            "order": item.order,
            "include": item.payload_path,
            "file_offset": f"0x{cursor:06X}",
            "cpu_start": cpu_for_file_offset(cursor),
            "cpu_end": cpu_for_file_offset(cursor + size - 1) if size else cpu_for_file_offset(cursor),
            "size": size,
            **estimate,
        }
        table_entries.append(entry)
        cursor += size

    covered_ranges: list[tuple[int, int]] = []
    for entry in binary_entries + table_entries:
        if "file_offset" not in entry or "size" not in entry:
            continue
        start = int(str(entry["file_offset"]), 16)
        size = int(entry["size"])
        if size:
            covered_ranges.append((start, start + size - 1))

    coverage_gaps: list[dict[str, object]] = []
    range_cursor = bank_start
    for start, end in sorted(covered_ranges):
        if start > range_cursor:
            coverage_gaps.append(
                {
                    "file_start": f"0x{range_cursor:06X}",
                    "file_end": f"0x{start - 1:06X}",
                    "cpu_start": cpu_for_file_offset(range_cursor),
                    "cpu_end": cpu_for_file_offset(start - 1),
                    "size": start - range_cursor,
                }
            )
        range_cursor = max(range_cursor, end + 1)
    if range_cursor <= bank_end:
        coverage_gaps.append(
            {
                "file_start": f"0x{range_cursor:06X}",
                "file_end": f"0x{bank_end:06X}",
                "cpu_start": cpu_for_file_offset(range_cursor),
                "cpu_end": cpu_for_file_offset(bank_end),
                "size": bank_end - range_cursor + 1,
            }
        )

    binary_by_kind: dict[str, int] = {}
    for entry in binary_entries:
        key = str(entry["extension"])
        binary_by_kind[key] = binary_by_kind.get(key, 0) + 1

    return {
        "schema": "earthbound-decomp.asset-bank.v1",
        "bank": bank,
        "bank_index": index,
        "config": config.relative_to(ROOT).as_posix(),
        "yml": yml_path.relative_to(ROOT).as_posix() if yml_path.is_relative_to(ROOT) else str(yml_path),
        "rom": rom_path.relative_to(ROOT).as_posix() if rom_path.is_relative_to(ROOT) else str(rom_path),
        "summary": {
            "binary_assets": len(binary_entries),
            "binary_assets_by_extension": binary_by_kind,
            "binary_asset_bytes": sum(int(entry["size"]) for entry in binary_entries),
            "table_includes": len(table_entries),
            "table_bytes": sum(int(entry.get("size", 0)) for entry in table_entries),
            "coverage_gaps": len(coverage_gaps),
            "coverage_gap_bytes": sum(int(gap["size"]) for gap in coverage_gaps),
            "missing_payload_metadata": len(missing_payload_metadata),
        },
        "binary_assets": binary_entries,
        "table_includes": table_entries,
        "coverage_gaps": coverage_gaps,
        "missing_payload_metadata": missing_payload_metadata,
    }


def render_markdown(manifest: dict[str, object]) -> str:
    summary = manifest["summary"]
    assert isinstance(summary, dict)
    binary_assets = manifest["binary_assets"]
    table_includes = manifest["table_includes"]
    coverage_gaps = manifest["coverage_gaps"]
    assert isinstance(binary_assets, list)
    assert isinstance(table_includes, list)
    assert isinstance(coverage_gaps, list)

    by_extension = summary["binary_assets_by_extension"]
    assert isinstance(by_extension, dict)
    by_ext_text = ", ".join(f"`{key}`: `{value}`" for key, value in sorted(by_extension.items())) or "-"

    lines = [
        f"# Bank {manifest['bank']} Asset Data Map",
        "",
        "Generated by `tools/build_asset_bank_manifest.py` from ebsrc bank config/source tables, `earthbound.yml`, and the local ROM.",
        "",
        "## Summary",
        "",
        f"- bank: `{manifest['bank']}` / reference bank `{manifest['bank_index']}`",
        f"- binary assets: `{summary['binary_assets']}` ({by_ext_text})",
        f"- binary asset bytes: `{summary['binary_asset_bytes']}`",
        f"- table includes: `{summary['table_includes']}`",
        f"- table bytes: `{summary['table_bytes']}`",
        f"- coverage gap bytes: `{summary['coverage_gap_bytes']}` across `{summary['coverage_gaps']}` gaps",
        f"- missing payload metadata: `{summary['missing_payload_metadata']}`",
        "",
        "## Binary Assets",
        "",
        "| Order | Label | Payload | CPU span | File offset | Bytes | First bytes |",
        "| ---: | --- | --- | --- | ---: | ---: | --- |",
    ]

    for entry in sorted(binary_assets, key=lambda row: int(row["order"])):
        assert isinstance(entry, dict)
        payload = str(entry["payload_path"])
        if entry.get("inferred_from_next_asset"):
            payload = f"{payload} (inferred span; missing yml metadata)"
        lines.append(
            "| {order} | `{label}` | `{payload}` | `{cpu_start}..{cpu_end}` | `{file_offset}` | {size} | `{first_bytes}` |".format(
                order=entry["order"],
                label=entry.get("label") or "?",
                payload=payload,
                cpu_start=entry["cpu_start"],
                cpu_end=entry["cpu_end"],
                file_offset=entry["file_offset"],
                size=entry["size"],
                first_bytes=entry["first_bytes"],
            )
        )

    lines.extend(
        [
            "",
            "## Table Includes",
            "",
            "| Order | Include | CPU span | File offset | Bytes | Directive counts |",
            "| ---: | --- | --- | ---: | ---: | --- |",
        ]
    )
    for entry in sorted(table_includes, key=lambda row: int(row["order"])):
        assert isinstance(entry, dict)
        if "error" in entry:
            lines.append(f"| {entry['order']} | `{entry['include']}` | - | - | - | {entry['error']} |")
            continue
        if entry.get("inferred_from_next_asset"):
            counts = "inferred generated table span"
        else:
            counts = f"{entry['byte_values']} byte, {entry['word_values']} word, {entry['dword_values']} dword"
        lines.append(
            f"| {entry['order']} | `{entry['include']}` | `{entry['cpu_start']}..{entry['cpu_end']}` | `{entry['file_offset']}` | {entry['size']} | {counts} |"
        )

    if coverage_gaps:
        lines.extend(
            [
                "",
                "## Coverage Gaps",
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

    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a manifest for an asset/data bank.")
    parser.add_argument("bank", help="Canonical bank, for example CA.")
    parser.add_argument("--rom", help="Optional explicit ROM path.")
    parser.add_argument("--yml", default=str(DEFAULT_YML), help="Path to earthbound.yml.")
    parser.add_argument("--json-out", help="Output JSON path.")
    parser.add_argument("--markdown-out", help="Output Markdown path.")
    args = parser.parse_args()

    yml_path = Path(args.yml)
    rom_path = rom_tools.find_rom(args.rom)
    manifest = build_manifest(args.bank.upper(), yml_path, rom_path)

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
        f"Bank {args.bank.upper()}: {summary['binary_assets']} binary assets, "
        f"{summary['binary_asset_bytes']} asset bytes, {summary['table_includes']} table includes, "
        f"{summary['table_bytes']} table bytes, {summary['coverage_gap_bytes']} gap bytes"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
