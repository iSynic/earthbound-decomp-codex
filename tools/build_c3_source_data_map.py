from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
SCHEMA = "earthbound-decomp.c3-source-data-map.v1"
DEFAULT_BANKCONFIG = ROOT / "refs" / "ebsrc-main" / "ebsrc-main" / "src" / "bankconfig" / "US" / "bank03.asm"
DEFAULT_WORKING_NAMES = ROOT / "build" / "working-names-c3.json"
DEFAULT_SCRIPT_PAYLOADS = ROOT / "build" / "script-payloads-c3.json"
DEFAULT_CONTRACTS = ROOT / "build" / "data-contracts-c0-c4.json"

INCLUDE_RE = re.compile(r'(?:\.INCLUDE|LOCALEINCLUDE)\s+"([^"]+)"', re.IGNORECASE)
FLAT_ADDR_RE = re.compile(r"\b(?:UNKNOWN_|REDIRECT_|DATA_|CODE_|NULL_)?(C3[0-9A-F]{4})\b")
ADDR_RE = re.compile(r"\b(C3)[:_]?([0-9A-F]{4})\b", re.IGNORECASE)

DATA_NAME_RE = re.compile(
    r"(Table|Tiles|Rows|Grid|Triples|Offsets|Palette|Palettes|Pointer|Pointers|"
    r"Text|Config|Configuration|Data|Flags|Speeds|Categories|Suffixes|Entities|"
    r"Registry|Request|Pairs|Checksum|Payload|FixedTail)"
)
SOURCE_NAME_RE = re.compile(
    r"^(Apply|Check|Choose|Clear|Close|Deplete|Dispatch|Display|Finalize|Find|Queue|Read|Recover|"
    r"Refresh|Release|Resolve|Return|Set|Sync|Tick)"
)

SOURCE_PATH_PREFIXES = (
    "system/",
    "text/",
    "misc/",
    "intro/",
    "unknown/C3/",
)

DATA_PATH_PREFIXES = (
    "data/",
    "text_data/",
)

INFERRED_NEXT_BOUNDARIES = {
    "C3:FB09": (
        "C3:FB1F",
        "refs/earthbound-disasm-legacy/Earthbound Decomp/EB/Routine_Macros_EB.asm:46125",
    ),
}


@dataclass(frozen=True)
class IncludeRow:
    ordinal: int
    path: str
    address: str | None
    start: int | None
    next_address: str | None
    size: int | None
    source_kind: str
    extraction_class: str
    source_expectation: str
    name: str | None
    working_name_confidence: str | None
    script_kind: str | None
    script_decode_status: str | None
    contract_id: str | None
    contract_confidence: str | None
    evidence: tuple[str, ...]


@dataclass(frozen=True)
class SupplementalLabel:
    address: str
    name: str
    extraction_class: str
    source: str
    script_kind: str | None
    script_decode_status: str | None
    contract_id: str | None
    evidence: tuple[str, ...]


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def resolve_path(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def address_from_text(text: str) -> tuple[str, int] | tuple[None, None]:
    upper = text.upper()
    for match in FLAT_ADDR_RE.finditer(upper):
        flat = match.group(1)
        return f"C3:{flat[2:]}", int(flat[2:], 16)
    for match in ADDR_RE.finditer(upper):
        return f"C3:{match.group(2).upper()}", int(match.group(2), 16)
    return None, None


def include_source_kind(path: str) -> str:
    lower = path.lower()
    if "/events/scripts/" in lower or "data/events/" in lower:
        return "event-script-include"
    if lower.startswith("data/unknown/"):
        return "unknown-data-include"
    if lower.startswith("unknown/c3/"):
        return "unknown-source-include"
    if lower.startswith(DATA_PATH_PREFIXES):
        return "named-data-include"
    if lower.startswith(SOURCE_PATH_PREFIXES):
        return "named-source-include"
    return "support-include"


def load_working_names(path: Path) -> dict[str, dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return {
        str(entry["address"]): entry
        for entry in data.get("entries", [])
        if str(entry.get("address", "")).startswith("C3:")
    }


def load_script_payloads(path: Path) -> dict[str, dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return {
        str(payload["address"]): payload
        for payload in data.get("payloads", [])
        if str(payload.get("address", "")).startswith("C3:")
    }


def load_contracts(path: Path) -> dict[str, dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return {
        str(contract["address"]): contract
        for contract in data.get("contracts", [])
        if str(contract.get("address", "")).startswith("C3:")
    }


def contract_byte_length(contract: dict[str, Any]) -> int | None:
    stride = contract.get("stride")
    count = contract.get("count")
    if not isinstance(stride, int) or not isinstance(count, int):
        return None
    return stride * count


def address_offset(address: str) -> int:
    return int(address.split(":", 1)[1], 16)


def contract_range(contract: dict[str, Any]) -> tuple[int, int] | None:
    size = contract_byte_length(contract)
    address = contract.get("address")
    if not isinstance(address, str) or size is None:
        return None
    start = address_offset(address)
    return start, start + size


def row_contract_coverage(
    row: dict[str, Any],
    contracts: dict[str, dict[str, Any]],
) -> tuple[bool, bool]:
    row_start = row.get("start")
    row_size = row.get("size")
    if not isinstance(row_start, int) or not isinstance(row_size, int):
        return False, False
    row_end = row_start + row_size
    spans: list[tuple[int, int]] = []
    for contract in contracts.values():
        contract_span = contract_range(contract)
        if contract_span is None:
            continue
        start, end = contract_span
        if row_start <= start < row_end:
            spans.append((start, min(end, row_end)))
    spans.sort()
    cursor = row_start
    saw_prefix = False
    for start, end in spans:
        if start > cursor:
            break
        if start == row_start:
            saw_prefix = True
        if end > cursor:
            cursor = end
        if cursor >= row_end:
            return True, saw_prefix
    return False, saw_prefix


def parse_bankconfig(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        match = INCLUDE_RE.search(line)
        if not match:
            continue
        include_path = match.group(1)
        address, start = address_from_text(include_path)
        rows.append(
            {
                "ordinal": len(rows),
                "path": include_path,
                "address": address,
                "start": start,
                "source_kind": include_source_kind(include_path),
            }
        )
    addressed = [row for row in rows if row["start"] is not None]
    for current, next_row in zip(addressed, addressed[1:]):
        if next_row["start"] > current["start"]:
            current["next_address"] = next_row["address"]
            current["size"] = next_row["start"] - current["start"]
    return rows


def evidence_for(entry: dict[str, Any] | None) -> tuple[str, ...]:
    if not entry:
        return ()
    notes: list[str] = []
    for item in entry.get("evidence", []):
        note = str(item.get("note", ""))
        if not note:
            continue
        line = item.get("line")
        if line:
            note = f"{note}:{line}"
        if note not in notes:
            notes.append(note)
    return tuple(notes)


def classify_row(
    row: dict[str, Any],
    working_names: dict[str, dict[str, Any]],
    script_payloads: dict[str, dict[str, Any]],
    contracts: dict[str, dict[str, Any]],
) -> tuple[str, str]:
    path = str(row["path"])
    address = row.get("address")
    source_kind = str(row["source_kind"])
    working = working_names.get(address) if address else None
    script = script_payloads.get(address) if address else None
    contract = contracts.get(address) if address else None
    name = str(working.get("name", "")) if working else ""

    if path.lower().startswith("misc/null/"):
        return "null-stub", "explicit null/padding stub; preserve as bank payload but do not treat as active source"

    if script:
        script_kind = str(script.get("kind"))
        if script_kind == "event-bytecode":
            return "event-bytecode-asset", "export as event/actionscript bytecode asset; VM source comes later"
        if script_kind == "event-branch-label":
            return "event-bytecode-label", "local label inside event/actionscript bytecode asset"
        if script_kind == "effect-script-payload":
            return "effect-script-asset", "export as battle visual effect-script asset"
        return "movement-pattern-data", "export as compact movement-pattern data"

    if contract:
        covered, saw_prefix = row_contract_coverage(row, contracts)
        if covered:
            return "contract-backed-data", "emit as structured ROM table spans from data-contract manifest"
        if saw_prefix:
            return (
                "contract-backed-data-prefix",
                "emit leading bytes from data-contract manifest; split or preserve the remaining include tail",
            )
        return "contract-backed-data", "emit as structured ROM table from data-contract manifest"

    if source_kind == "event-script-include":
        return "event-script-asset", "reference event script include; keep as script asset until VM semantics are richer"

    if source_kind in {"unknown-data-include", "named-data-include"}:
        if name and not DATA_NAME_RE.search(name) and address and int(address.split(":", 1)[1], 16) >= 0xE000:
            return "data-or-helper-frontier", "documented include start; keep cautious until direct consumer/source body pass"
        return "raw-or-named-data", "export as data asset or promote to contract when consumer shape is exact"

    if source_kind in {"unknown-source-include", "named-source-include"}:
        if name and SOURCE_NAME_RE.search(name):
            return "source-helper", "ordinary 65816 helper candidate for source extraction"
        if name and DATA_NAME_RE.search(name):
            return "source-adjacent-data", "named table/data block in source region; keep out of routine labels"
        return "source-helper", "ordinary 65816 helper candidate for source extraction"

    return "support-include", "assembler support include, not bank payload"


def classify_label(
    address: str,
    working: dict[str, Any] | None,
    script: dict[str, Any] | None,
    contract: dict[str, Any] | None,
) -> str:
    if script:
        script_kind = str(script.get("kind"))
        if script_kind == "event-bytecode":
            return "event-bytecode-asset"
        if script_kind == "event-branch-label":
            return "event-bytecode-label"
        if script_kind == "effect-script-payload":
            return "effect-script-asset"
        return "movement-pattern-data"
    if contract:
        return "contract-backed-data"
    name = str(working.get("name", "")) if working else ""
    if SOURCE_NAME_RE.search(name):
        return "source-helper"
    if DATA_NAME_RE.search(name):
        return "source-adjacent-data"
    return "working-label"


def build_manifest(
    bankconfig: Path,
    working_names_path: Path,
    script_payloads_path: Path,
    contracts_path: Path,
) -> dict[str, Any]:
    working_names = load_working_names(working_names_path)
    script_payloads = load_script_payloads(script_payloads_path)
    contracts = load_contracts(contracts_path)
    rows = parse_bankconfig(bankconfig)
    include_rows: list[IncludeRow] = []

    for row in rows:
        address = row.get("address")
        row = dict(row)
        inferred_evidence: tuple[str, ...] = ()
        if address in INFERRED_NEXT_BOUNDARIES and row.get("size") is None:
            next_address, evidence = INFERRED_NEXT_BOUNDARIES[str(address)]
            row["next_address"] = next_address
            row["size"] = int(next_address.split(":", 1)[1], 16) - int(str(address).split(":", 1)[1], 16)
            inferred_evidence = (evidence,)
        working = working_names.get(address) if address else None
        script = script_payloads.get(address) if address else None
        contract = contracts.get(address) if address else None
        extraction_class, expectation = classify_row(row, working_names, script_payloads, contracts)
        include_rows.append(
            IncludeRow(
                ordinal=int(row["ordinal"]),
                path=str(row["path"]),
                address=address,
                start=row.get("start"),
                next_address=row.get("next_address"),
                size=row.get("size"),
                source_kind=str(row["source_kind"]),
                extraction_class=extraction_class,
                source_expectation=expectation,
                name=str(working.get("name")) if working else None,
                working_name_confidence=str(working.get("confidence")) if working else None,
                script_kind=str(script.get("kind")) if script else None,
                script_decode_status=str(script.get("decode_status")) if script else None,
                contract_id=str(contract.get("id")) if contract else None,
                contract_confidence=str(contract.get("confidence")) if contract else None,
                evidence=evidence_for(working) + inferred_evidence,
            )
        )

    addressed_include_starts = {row.address for row in include_rows if row.address}
    supplemental_labels: list[SupplementalLabel] = []
    supplemental_addresses = sorted(
        set(working_names) | set(script_payloads) | set(contracts),
        key=lambda item: int(item.split(":", 1)[1], 16),
    )
    for address in supplemental_addresses:
        if address in addressed_include_starts:
            continue
        working = working_names.get(address)
        script = script_payloads.get(address)
        contract = contracts.get(address)
        name = (
            str(working.get("name"))
            if working
            else str(script.get("name"))
            if script
            else str(contract.get("id"))
            if contract
            else ""
        )
        source = "working-name"
        if script:
            source = "script-payload"
        elif contract:
            source = "data-contract"
        supplemental_labels.append(
            SupplementalLabel(
                address=address,
                name=name,
                extraction_class=classify_label(address, working, script, contract),
                source=source,
                script_kind=str(script.get("kind")) if script else None,
                script_decode_status=str(script.get("decode_status")) if script else None,
                contract_id=str(contract.get("id")) if contract else None,
                evidence=evidence_for(working),
            )
        )

    addressed_rows = [row for row in include_rows if row.address and row.start is not None]
    source_labels = [
        label
        for label in supplemental_labels
        if label.extraction_class == "source-helper"
    ]
    mixed_row_notes: dict[str, tuple[str, ...]] = {}
    for row in addressed_rows:
        if row.extraction_class not in {"raw-or-named-data", "data-or-helper-frontier"}:
            continue
        if row.size is None:
            continue
        row_end = row.start + row.size
        embedded = [
            label
            for label in source_labels
            if row.start < int(label.address.split(":", 1)[1], 16) < row_end
        ]
        if embedded:
            mixed_row_notes[row.address or ""] = tuple(
                f"{label.address} {label.name}" for label in embedded
            )

    if mixed_row_notes:
        updated_rows: list[IncludeRow] = []
        for row in include_rows:
            embedded = mixed_row_notes.get(row.address or "")
            if not embedded:
                updated_rows.append(row)
                continue
            updated_rows.append(
                replace(
                    row,
                    extraction_class="mixed-data-source-row",
                    source_expectation=(
                        "mixed row: split leading data from embedded source-helper labels "
                        + ", ".join(embedded)
                    ),
                    evidence=row.evidence + embedded,
                )
            )
        include_rows = updated_rows

    payload_rows = [row for row in include_rows if row.address]
    summary = {
        "include_rows": len(include_rows),
        "addressed_include_rows": len(payload_rows),
        "working_named_addressed_rows": sum(1 for row in payload_rows if row.name),
        "working_labels": len(working_names),
        "working_labels_not_at_include_starts": sum(
            1 for address in working_names
            if address not in addressed_include_starts
        ),
        "contract_backed_rows": sum(1 for row in payload_rows if row.contract_id),
        "contract_labels": len(contracts),
        "contract_labels_not_at_include_starts": sum(
            1 for address in contracts
            if address not in addressed_include_starts
        ),
        "script_payload_rows": sum(1 for row in payload_rows if row.script_kind),
        "script_payload_labels": len(script_payloads),
        "script_payload_labels_not_at_include_starts": sum(
            1 for address in script_payloads
            if address not in addressed_include_starts
        ),
        "by_extraction_class": dict(sorted(Counter(row.extraction_class for row in payload_rows).items())),
        "supplemental_by_extraction_class": dict(
            sorted(Counter(row.extraction_class for row in supplemental_labels).items())
        ),
        "by_source_kind": dict(sorted(Counter(row.source_kind for row in payload_rows).items())),
        "script_decode_status": dict(
            sorted(Counter(row.script_decode_status for row in payload_rows if row.script_decode_status).items())
        ),
    }
    return {
        "schema": SCHEMA,
        "generated_by": "tools/build_c3_source_data_map.py",
        "inputs": {
            "bankconfig": rel(bankconfig),
            "working_names": rel(working_names_path),
            "script_payloads": rel(script_payloads_path),
            "data_contracts": rel(contracts_path),
        },
        "summary": summary,
        "include_rows": [asdict(row) for row in include_rows],
        "supplemental_labels": [asdict(row) for row in supplemental_labels],
    }


def markdown_escape(text: str) -> str:
    return text.replace("|", "\\|")


def render_markdown(manifest: dict[str, Any]) -> str:
    summary = manifest["summary"]
    rows = [row for row in manifest["include_rows"] if row["address"]]
    supplemental = manifest["supplemental_labels"]
    lines = [
        "# C3 source/data extraction map",
        "",
        "Generated from the ebsrc bankconfig include order plus local working-name, script-payload, and data-contract manifests. This is the C3 split front door: it says which addressed includes should become 65816 source, which should stay script/data assets, and which already have structured table contracts.",
        "",
        "## Summary",
        "",
        f"- schema: `{manifest['schema']}`",
        f"- addressed include rows: `{summary['addressed_include_rows']}`",
        f"- working labels: `{summary['working_labels']}` (`{summary['working_labels_not_at_include_starts']}` internal or named-include labels)",
        f"- script payload labels: `{summary['script_payload_labels']}` (`{summary['script_payload_labels_not_at_include_starts']}` internal labels)",
        f"- data-contract labels: `{summary['contract_labels']}` (`{summary['contract_labels_not_at_include_starts']}` internal labels)",
        f"- working-named addressed rows: `{summary['working_named_addressed_rows']}`",
        f"- script payload include-start rows: `{summary['script_payload_rows']}`",
        f"- contract-backed include-start rows: `{summary['contract_backed_rows']}`",
        f"- by extraction class: `{summary['by_extraction_class']}`",
        f"- supplemental by extraction class: `{summary['supplemental_by_extraction_class']}`",
        f"- script decode status: `{summary['script_decode_status']}`",
        "",
        "## Extraction Classes",
        "",
        "| Class | Meaning |",
        "| --- | --- |",
        "| `source-helper` | Ordinary 65816 helper candidate for source extraction. |",
        "| `event-script-asset`, `event-bytecode-asset`, `event-bytecode-label` | Event/actionscript bytecode; export as script assets first. |",
        "| `movement-pattern-data`, `effect-script-asset` | VM-adjacent payloads, but not event bytecode. |",
        "| `contract-backed-data` | Structured ROM table with a data-contract entry. |",
        "| `contract-backed-data-prefix` | Include starts with a structured leading contract and a remaining tail that still needs splitting or preservation. |",
        "| `mixed-data-source-row` | Addressed data include that contains embedded ordinary source-helper labels and should be split before source emission. |",
        "| `raw-or-named-data`, `source-adjacent-data`, `data-or-helper-frontier` | Data/include starts that are documented but may need later consumer polishing. |",
        "| `null-stub` | Explicit null/padding stub; preserve, but keep out of source-helper worklists. |",
        "",
        "## Addressed Include Rows",
        "",
        "| Address | Size | Include | Class | Name / Contract | Decode |",
        "| --- | ---: | --- | --- | --- | --- |",
    ]

    for row in rows:
        name = row.get("name") or row.get("contract_id") or ""
        if row.get("contract_id") and row.get("name") and row["contract_id"] != row["name"]:
            name = f"{row['name']} / {row['contract_id']}"
        size = f"0x{row['size']:X}" if row.get("size") is not None else ""
        decode = row.get("script_decode_status") or ""
        lines.append(
            "| `{address}` | {size} | `{path}` | `{klass}` | {name} | {decode} |".format(
                address=row["address"],
                size=size,
                path=markdown_escape(str(row["path"])),
                klass=row["extraction_class"],
                name=f"`{markdown_escape(str(name))}`" if name else "",
                decode=f"`{decode}`" if decode else "",
            )
        )

    lines.extend(
        [
            "",
            "## Supplemental Labels",
            "",
            "These labels are not address-bearing include starts in the reference bankconfig. They are still important: most are internal event labels, named-source include entry points, or table sublabels needed by source comments.",
            "",
            "| Address | Class | Source | Name / Contract | Decode |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for row in supplemental:
        name = row.get("name") or row.get("contract_id") or ""
        decode = row.get("script_decode_status") or ""
        lines.append(
            "| `{address}` | `{klass}` | `{source}` | {name} | {decode} |".format(
                address=row["address"],
                klass=row["extraction_class"],
                source=row["source"],
                name=f"`{markdown_escape(str(name))}`" if name else "",
                decode=f"`{decode}`" if decode else "",
            )
        )

    lines.extend(
        [
            "",
            "## Source Extraction Slices",
            "",
            "These are the addressed rows currently classified as `source-helper`. They are the C3 rows most suitable for ordinary 65816 source extraction before deeper VM work.",
            "",
            "| Address | Include | Working Name | Expectation |",
            "| --- | --- | --- | --- |",
        ]
    )
    for row in rows:
        if row["extraction_class"] != "source-helper":
            continue
        lines.append(
            "| `{address}` | `{path}` | {name} | {expectation} |".format(
                address=row["address"],
                path=markdown_escape(str(row["path"])),
                name=f"`{markdown_escape(str(row.get('name') or ''))}`" if row.get("name") else "",
                expectation=markdown_escape(str(row["source_expectation"])),
            )
        )

    mixed_rows = [row for row in rows if row["extraction_class"] == "mixed-data-source-row"]
    if mixed_rows:
        lines.extend(
            [
                "",
                "## Mixed Data/Source Rows",
                "",
                "These addressed data includes contain embedded source-helper labels. Split them before emitting ordinary source.",
                "",
                "| Address | Include | Embedded Source Labels | Split Expectation |",
                "| --- | --- | --- | --- |",
            ]
        )
        for row in mixed_rows:
            embedded = "<br>".join(markdown_escape(str(item)) for item in row.get("evidence", ()))
            lines.append(
                "| `{address}` | `{path}` | {embedded} | {expectation} |".format(
                    address=row["address"],
                    path=markdown_escape(str(row["path"])),
                    embedded=embedded,
                    expectation=markdown_escape(str(row["source_expectation"])),
                )
            )

    lines.extend(
        [
            "",
            "## Follow-up Frontier",
            "",
            "Rows below are documented enough to split, but are intentionally not promoted to normal source helpers yet.",
            "",
            "| Address | Include | Class | Reason |",
            "| --- | --- | --- | --- |",
        ]
    )
    for row in rows:
        if row["extraction_class"] not in {"raw-or-named-data", "source-adjacent-data", "data-or-helper-frontier"}:
            continue
        lines.append(
            "| `{address}` | `{path}` | `{klass}` | {reason} |".format(
                address=row["address"],
                path=markdown_escape(str(row["path"])),
                klass=row["extraction_class"],
                reason=markdown_escape(str(row["source_expectation"])),
            )
        )
    return "\n".join(lines).rstrip() + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build the C3 source/data/script extraction map.")
    parser.add_argument("--bankconfig", type=Path, default=DEFAULT_BANKCONFIG)
    parser.add_argument("--working-names", type=Path, default=DEFAULT_WORKING_NAMES)
    parser.add_argument("--script-payloads", type=Path, default=DEFAULT_SCRIPT_PAYLOADS)
    parser.add_argument("--contracts", type=Path, default=DEFAULT_CONTRACTS)
    parser.add_argument("--json-out", type=Path, default=ROOT / "build" / "c3-source-data-map.json")
    parser.add_argument("--markdown-out", type=Path, default=ROOT / "notes" / "c3-source-data-map.md")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    manifest = build_manifest(
        resolve_path(args.bankconfig),
        resolve_path(args.working_names),
        resolve_path(args.script_payloads),
        resolve_path(args.contracts),
    )

    json_out = resolve_path(args.json_out)
    json_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    markdown_out = resolve_path(args.markdown_out)
    markdown_out.parent.mkdir(parents=True, exist_ok=True)
    markdown_out.write_text(render_markdown(manifest), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
