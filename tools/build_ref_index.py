from __future__ import annotations

import argparse
import fnmatch
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


SCHEMA = "earthbound-decomp.ref-index.v1"

ROOT = Path(__file__).resolve().parent.parent
EBSRC_ROOT = ROOT / "refs" / "ebsrc-main" / "ebsrc-main"
EBSRC_US_BANKCONFIG = EBSRC_ROOT / "src" / "bankconfig" / "US"
EBSRC_SYMBOLS = EBSRC_ROOT / "include" / "symbols"
LEGACY_ROOT = ROOT / "refs" / "earthbound-disasm-legacy" / "Earthbound Decomp"
LEGACY_ROUTINES = LEGACY_ROOT / "EB" / "Routine_Macros_EB.asm"
EB_DECOMPILE_ROOT = ROOT / "refs" / "eb-decompile-4ef92"
WORKING_NAMES_DEFAULT = ROOT / "build" / "working-names-c0-c4.json"
DATA_CONTRACTS_DEFAULT = ROOT / "build" / "data-contracts-c0-c4.json"
SCRIPT_PAYLOADS_DEFAULT = ROOT / "build" / "script-payloads-c3.json"
GENERATED_NOTE_PATTERNS = (
    "bank-*-reference-frontier.md",
    "bank-*-working-name-proposals.md",
    "bank-*-progress-audit.md",
    "bank-0-1-progress-audit.md",
    "bank-*-closure.md",
    "script-payloads-*.md",
    "data-contracts-*.md",
    "*source-data-map.md",
    "*source-extraction-candidates.md",
)

TEXT_SUFFIXES = {".asm", ".inc", ".txt", ".md", ".yml", ".yaml", ".json", ".cfg", ".py", ".toml", ".csv"}
INCLUDE_RE = re.compile(r'(?:\.INCLUDE|LOCALEINCLUDE)\s+"([^"]+)"', re.IGNORECASE)
GLOBAL_RE = re.compile(r"^\s*\.GLOBAL\s+([A-Za-z0-9_]+)(?::\s*([A-Za-z0-9_]+))?", re.IGNORECASE)
LABEL_RE = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*):")
LEGACY_ADDR_LABEL_RE = re.compile(r"^(?:label|DATA)_([C-F][0-9A-F])([0-9A-F]{4})$", re.IGNORECASE)
ADDR_TOKEN_RE = re.compile(r"\b([C-F][0-9A-F])[:_]?([0-9A-F]{4})\b", re.IGNORECASE)
FLAT_ADDR_RE = re.compile(r"\b(?:UNKNOWN_|REDIRECT_|DATA_|CODE_|NULL_)?([C-F][0-9A-F][0-9A-F]{4})\b", re.IGNORECASE)


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def canonical_bank(index: int) -> str:
    return f"{0xC0 + index:02X}"


def normalize_address(bank: str, address: str) -> str:
    return f"{bank.upper()}:{address.upper()}"


def address_from_text(text: str, preferred_bank: str | None = None) -> str | None:
    for match in ADDR_TOKEN_RE.finditer(text):
        bank = match.group(1).upper()
        if preferred_bank is None or bank == preferred_bank:
            return normalize_address(bank, match.group(2))
    for match in FLAT_ADDR_RE.finditer(text):
        flat = match.group(1).upper()
        bank = flat[:2]
        if preferred_bank is None or bank == preferred_bank:
            return normalize_address(bank, flat[2:])
    return None


def address_from_symbol(name: str) -> str | None:
    legacy = LEGACY_ADDR_LABEL_RE.match(name)
    if legacy:
        return normalize_address(legacy.group(1), legacy.group(2))
    return address_from_text(name)


def iter_text_files(base: Path):
    if not base.exists():
        return
    for path in sorted(base.rglob("*")):
        if not path.is_file():
            continue
        if any(part in {".git", "__pycache__", "build"} for part in path.parts):
            continue
        if path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        yield path


def append_address_entry(entries: list[dict[str, Any]], *, address: str | None, name: str, kind: str, source: str, path: Path, line: int | None = None, extra: dict[str, Any] | None = None) -> None:
    item: dict[str, Any] = {
        "name": name,
        "kind": kind,
        "source": source,
        "path": rel(path),
    }
    if address:
        item["address"] = address
        item["bank"] = address[:2]
    if line is not None:
        item["line"] = line
    if extra:
        item.update(extra)
    entries.append(item)


def parse_ebsrc_bank_includes() -> list[dict[str, Any]]:
    includes: list[dict[str, Any]] = []
    if not EBSRC_US_BANKCONFIG.exists():
        return includes
    for path in sorted(EBSRC_US_BANKCONFIG.glob("bank*.asm")):
        match = re.fullmatch(r"bank([0-9a-fA-F]{2})\.asm", path.name)
        if not match:
            continue
        bank_index = int(match.group(1), 16)
        bank = canonical_bank(bank_index)
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        for lineno, line in enumerate(lines, start=1):
            include_match = INCLUDE_RE.search(line)
            if not include_match:
                continue
            include = include_match.group(1)
            if include.startswith(("symbols/", "common.asm", "config.asm", "structs.asm", "eventmacros.asm")):
                continue
            first_part = include.split("/", 1)[0].lower()
            address = address_from_text(include, bank)
            includes.append(
                {
                    "bank": bank,
                    "bank_index": f"{bank_index:02X}",
                    "include": include,
                    "address": address,
                    "kind": "bank-include",
                    "named": first_part != "unknown" and address is None,
                    "path": rel(path),
                    "line": lineno,
                    "source": "ebsrc-main",
                }
            )
    return includes


def parse_ebsrc_symbols() -> list[dict[str, Any]]:
    symbols: list[dict[str, Any]] = []
    if not EBSRC_SYMBOLS.exists():
        return symbols
    for path in sorted(EBSRC_SYMBOLS.glob("*.asm")):
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        for lineno, line in enumerate(lines, start=1):
            match = GLOBAL_RE.search(line)
            if not match:
                continue
            name = match.group(1)
            symbols.append(
                {
                    "name": name,
                    "kind": "global-symbol",
                    "source": "ebsrc-main",
                    "path": rel(path),
                    "line": lineno,
                    "address": address_from_symbol(name),
                    "scope": path.stem,
                    "storage": match.group(2) or "",
                }
            )
    return symbols


def parse_ebsrc_source_labels() -> list[dict[str, Any]]:
    labels: list[dict[str, Any]] = []
    src = EBSRC_ROOT / "src"
    for path in iter_text_files(src):
        if path.suffix.lower() != ".asm":
            continue
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        for lineno, line in enumerate(lines, start=1):
            match = LABEL_RE.match(line)
            if not match:
                continue
            name = match.group(1)
            if name.startswith((".", "@")):
                continue
            labels.append(
                {
                    "name": name,
                    "kind": "source-label",
                    "source": "ebsrc-main",
                    "path": rel(path),
                    "line": lineno,
                    "address": address_from_symbol(name),
                }
            )
    return labels


def parse_legacy_labels() -> list[dict[str, Any]]:
    labels: list[dict[str, Any]] = []
    if not LEGACY_ROUTINES.exists():
        return labels
    lines = LEGACY_ROUTINES.read_text(encoding="utf-8", errors="ignore").splitlines()
    current_macro = ""
    for lineno, line in enumerate(lines, start=1):
        stripped = line.strip()
        if stripped.lower().startswith("macro "):
            current_macro = stripped
        match = LABEL_RE.match(line)
        if not match:
            continue
        name = match.group(1)
        labels.append(
            {
                "name": name,
                "kind": "legacy-label",
                "source": "earthbound-disasm-legacy",
                "path": rel(LEGACY_ROUTINES),
                "line": lineno,
                "address": address_from_symbol(name),
                "macro": current_macro,
            }
        )
    return labels


def parse_eb_decompile_assets() -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for path in iter_text_files(EB_DECOMPILE_ROOT):
        if not path.suffix.lower() in {".yml", ".yaml"}:
            continue
        entries.append(
            {
                "name": path.stem,
                "kind": "data-table-yml",
                "source": "eb-decompile-4ef92",
                "path": rel(path),
            }
        )
    return entries


def parse_note_mentions() -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    notes_dir = ROOT / "notes"
    if not notes_dir.exists():
        return entries
    for path in sorted(notes_dir.glob("*.md")):
        if any(fnmatch.fnmatch(path.name, pattern) for pattern in GENERATED_NOTE_PATTERNS):
            continue
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        title = ""
        for lineno, line in enumerate(lines, start=1):
            if not title and line.startswith("#"):
                title = line.lstrip("#").strip()
            seen: set[str] = set()
            for match in ADDR_TOKEN_RE.finditer(line):
                address = normalize_address(match.group(1), match.group(2))
                if address in seen:
                    continue
                seen.add(address)
                entries.append(
                    {
                        "address": address,
                        "bank": address[:2],
                        "name": title or path.stem,
                        "kind": "note-mention",
                        "source": "local-notes",
                        "path": rel(path),
                        "line": lineno,
                        "text": line.strip()[:240],
                    }
                )
            for match in FLAT_ADDR_RE.finditer(line):
                flat = match.group(1).upper()
                address = normalize_address(flat[:2], flat[2:])
                if address in seen:
                    continue
                seen.add(address)
                entries.append(
                    {
                        "address": address,
                        "bank": address[:2],
                        "name": title or path.stem,
                        "kind": "note-mention",
                        "source": "local-notes",
                        "path": rel(path),
                        "line": lineno,
                        "text": line.strip()[:240],
                    }
                )
    return entries


def parse_working_names(path: Path) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    if not path.exists():
        return entries
    data = json.loads(path.read_text(encoding="utf-8"))
    for entry in data.get("entries", []):
        address = entry.get("address")
        if not address:
            continue
        entries.append(
            {
                "address": address,
                "bank": address[:2],
                "name": entry.get("name", ""),
                "kind": "working-name",
                "source": "local-working-names",
                "path": rel(path),
                "confidence": entry.get("confidence", ""),
                "tags": entry.get("tags", []),
            }
        )
    return entries


def parse_data_contracts(path: Path) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    if not path.exists():
        return entries
    data = json.loads(path.read_text(encoding="utf-8"))
    for contract in data.get("contracts", []):
        entries.append(
            {
                "name": contract.get("id", ""),
                "kind": "data-contract",
                "source": "local-data-contracts",
                "path": rel(path),
                "address": contract.get("address"),
                "domain": contract.get("domain"),
                "stride": contract.get("stride"),
                "count": contract.get("count"),
                "struct": contract.get("struct"),
            }
        )
    return entries


def parse_script_payloads(path: Path) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    if not path.exists():
        return entries
    data = json.loads(path.read_text(encoding="utf-8"))
    for payload in data.get("payloads", []):
        address = payload.get("address")
        if not address:
            continue
        entries.append(
            {
                "address": address,
                "bank": address[:2],
                "name": payload.get("name", ""),
                "kind": "script-payload",
                "source": "local-script-payloads",
                "path": rel(path),
                "payload_kind": payload.get("kind", ""),
                "decode_status": payload.get("decode_status", "not-decoded"),
            }
        )
    return entries


def build_index(working_names: Path, data_contracts: Path, script_payloads: Path) -> dict[str, Any]:
    bank_includes = parse_ebsrc_bank_includes()
    ebsrc_symbols = parse_ebsrc_symbols()
    ebsrc_labels = parse_ebsrc_source_labels()
    legacy_labels = parse_legacy_labels()
    decompile_assets = parse_eb_decompile_assets()
    note_mentions = parse_note_mentions()
    working_name_entries = parse_working_names(working_names)
    data_contract_entries = parse_data_contracts(data_contracts)
    script_payload_entries = parse_script_payloads(script_payloads)

    entries: list[dict[str, Any]] = []
    entries.extend(ebsrc_symbols)
    entries.extend(ebsrc_labels)
    entries.extend(legacy_labels)
    entries.extend(decompile_assets)
    entries.extend(note_mentions)
    entries.extend(working_name_entries)
    entries.extend(data_contract_entries)
    entries.extend(script_payload_entries)

    for item in bank_includes:
        entries.append(
            {
                "name": item["include"],
                "kind": "bank-include",
                "source": "ebsrc-main",
                "path": item["path"],
                "line": item["line"],
                "address": item.get("address"),
                "bank": item["bank"],
                "bank_index": item["bank_index"],
                "named": item["named"],
            }
        )

    by_source = Counter(item.get("source", "") for item in entries)
    by_kind = Counter(item.get("kind", "") for item in entries)
    by_bank = Counter(item["address"][:2] for item in entries if item.get("address") and ":" in item["address"])
    addressed = [item for item in entries if item.get("address")]

    return {
        "schema": SCHEMA,
        "generated_by": "tools/build_ref_index.py",
        "summary": {
            "entries": len(entries),
            "addressed_entries": len(addressed),
            "bank_includes": len(bank_includes),
            "by_source": dict(sorted(by_source.items())),
            "by_kind": dict(sorted(by_kind.items())),
            "by_bank": dict(sorted(by_bank.items())),
        },
        "sources": {
            "ebsrc-main": rel(EBSRC_ROOT),
            "earthbound-disasm-legacy": rel(LEGACY_ROOT),
            "eb-decompile-4ef92": rel(EB_DECOMPILE_ROOT),
            "working-names": rel(working_names),
            "data-contracts": rel(data_contracts),
            "script-payloads": rel(script_payloads),
        },
        "entries": entries,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a searchable index over local reference docs and manifests.")
    parser.add_argument("--output", type=Path, default=ROOT / "build" / "ref-index.json")
    parser.add_argument("--working-names", type=Path, default=WORKING_NAMES_DEFAULT)
    parser.add_argument("--data-contracts", type=Path, default=DATA_CONTRACTS_DEFAULT)
    parser.add_argument("--script-payloads", type=Path, default=SCRIPT_PAYLOADS_DEFAULT)
    args = parser.parse_args()

    output = args.output if args.output.is_absolute() else ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    index = build_index(
        args.working_names if args.working_names.is_absolute() else ROOT / args.working_names,
        args.data_contracts if args.data_contracts.is_absolute() else ROOT / args.data_contracts,
        args.script_payloads if args.script_payloads.is_absolute() else ROOT / args.script_payloads,
    )
    output.write_text(json.dumps(index, indent=2) + "\n", encoding="utf-8")
    summary = index["summary"]
    print(
        f"Wrote {rel(output)} with {summary['entries']} entries "
        f"({summary['addressed_entries']} addressed)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
