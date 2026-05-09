#!/usr/bin/env python3
"""Build curated restored-ebsrc semantic knowns integration candidates."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from build_ebsrc_bank_map import build as build_ebsrc_bank_map

import audio_spc700_source


EBSRC_ROOT = ROOT / "refs" / "ebsrc-main" / "ebsrc-main"
DEFAULT_BANKS = ("C0", "C1", "C2", "C3", "C4", "EF")
DEFAULT_OUTPUT = ROOT / "manifests" / "ebsrc-knowns-integration-candidates.json"
DEFAULT_NOTES = ROOT / "notes" / "ebsrc-knowns-integration-candidates.md"
DEFAULT_COMMUNITY_NOTES = ROOT / "notes" / "ebsrc-community-crosswalk.md"
SOURCE_BACKED_AUDIO_INGEST = ROOT / "manifests" / "audio-spc700-sounddriver-source-ingest.json"
CLASSES = (
    "adopt_exact_symbol",
    "adopt_constant_or_field_name",
    "adopt_table_name",
    "macro_vocab_reference",
    "keep_local_supersedes",
    "blocked_unaddressed_or_payload_only",
    "manual_review",
)
COMMUNITY_STATUSES = (
    "source_alias_ready",
    "source_alias_integrated",
    "docs_crosswalk_only",
    "local_primary_stronger",
    "blocked_conflict_or_unproven",
)
PLACEHOLDER_RE = re.compile(r"^(UNKNOWN|NULL|DATA|CODE|UNUSED|UNK)(?:$|_|[0-9])", re.IGNORECASE)
GENERIC_LOCAL_RE = re.compile(
    r"^(?:[c-e][0-9]_[0-9a-f]{4}(?:_[0-9a-f]{4})?|[A-F0-9]{6}(?:_(?:UNKNOWN|DATA|CODE|NULL|UNUSED).*)?|.*RawData)$",
    re.IGNORECASE,
)
LABEL_RE = re.compile(r"^([C-E][0-9]):([0-9A-F]{4})\s+(.+)$", re.IGNORECASE)
ENUM_RE = re.compile(r"^\s*\.ENUM\s+([A-Za-z_][A-Za-z0-9_]*)", re.IGNORECASE)
STRUCT_RE = re.compile(r"^\s*\.STRUCT\s+([A-Za-z_][A-Za-z0-9_]*)", re.IGNORECASE)
MACRO_RE = re.compile(r"^\s*\.MACRO\s+([A-Za-z_][A-Za-z0-9_]*)\b", re.IGNORECASE)
SYMBOL_RE = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\b")
ASSIGN_RE = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*(?:=|\.EQU)\s*(.+)$", re.IGNORECASE)
SPC_LABEL_RE = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*):")
GLOBAL_SOURCE_SYMBOLS: set[str] | None = None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bank", action="append", choices=DEFAULT_BANKS, help="Bank to include. Defaults to priority banks.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--notes", type=Path, default=DEFAULT_NOTES)
    parser.add_argument("--community-notes", type=Path, default=DEFAULT_COMMUNITY_NOTES)
    return parser.parse_args()


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT)).replace("\\", "/")


def clean_symbol(name: str | None) -> str | None:
    if not name:
        return None
    stripped = str(name).strip()
    if not stripped:
        return None
    return stripped


def is_placeholder(name: str | None) -> bool:
    cleaned = clean_symbol(name)
    return cleaned is None or PLACEHOLDER_RE.match(cleaned) is not None


def is_generic_local(name: str | None) -> bool:
    cleaned = clean_symbol(name)
    if cleaned is None:
        return True
    return GENERIC_LOCAL_RE.match(cleaned) is not None or is_placeholder(cleaned)


def normalize_name(name: str | None) -> str:
    return re.sub(r"[^A-Z0-9]+", "_", name or "").strip("_").upper()


def name_tokens(*parts: Any) -> set[str]:
    text = " ".join(str(part or "") for part in parts)
    split = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    raw = re.split(r"[^A-Za-z0-9]+", split)
    stopwords = {
        "A",
        "AN",
        "AND",
        "ASM",
        "BANK",
        "BY",
        "C0",
        "C1",
        "C2",
        "C3",
        "C4",
        "CODE",
        "COMMON",
        "COPY",
        "CREATE",
        "DATA",
        "EB",
        "EBSRC",
        "EF",
        "FIND",
        "FOR",
        "FROM",
        "GET",
        "GIVE",
        "HELPER",
        "IN",
        "INCLUDE",
        "INIT",
        "INITIALIZE",
        "JUMP",
        "LOAD",
        "LOCAL",
        "OPEN",
        "OF",
        "OR",
        "PAUSE",
        "PREPARE",
        "QUEUE",
        "READ",
        "RELOAD",
        "RUN",
        "SET",
        "SHOW",
        "SPAWN",
        "SRC",
        "SOURCE",
        "STORE",
        "SUB",
        "SUBMIT",
        "TAKE",
        "TEST",
        "THE",
        "TO",
        "TOGGLE",
        "TRANSFER",
        "TRIGGER",
        "UNKNOWN",
        "UPDATE",
        "USE",
        "WITH",
    }
    return {token.upper() for token in raw if len(token) > 2 and token.upper() not in stopwords}


def alias_token_aligned(record: dict[str, Any]) -> bool:
    ebsrc_tokens = name_tokens(record.get("ebsrc_symbol"), Path(str(record.get("include_path") or "")).stem)
    local_tokens = name_tokens(record.get("local_name"), Path(str(record.get("local_source_path") or "")).stem)
    return bool(ebsrc_tokens) and ebsrc_tokens <= local_tokens


def ebsrc_name_for_entry(entry: dict[str, Any]) -> str | None:
    symbol = clean_symbol(entry.get("ebsrc_symbol"))
    if symbol and not is_placeholder(symbol):
        return symbol
    include_path = str(entry.get("include_path") or "")
    stem = Path(include_path).stem.upper()
    if stem and not stem.startswith(("C0", "C1", "C2", "C3", "C4", "EF")) and not stem.isdecimal():
        return stem
    if stem.isdecimal():
        return f"EVENT_{stem}"
    return None


def labels_from_source_range(bank: str, address: str | None) -> list[str]:
    if address is None:
        return []
    ranges_path = ROOT / "build" / f"{bank.lower()}-build-candidate-ranges.json"
    if not ranges_path.exists():
        return []
    payload = json.loads(ranges_path.read_text(encoding="utf-8"))
    for record in payload.get("ranges", []):
        labels: list[str] = []
        for segment in record.get("source_segments", []):
            for raw in segment.get("labels", []):
                match = LABEL_RE.match(raw)
                if match and f"{match.group(1).upper()}:{match.group(2).upper()}" == address:
                    labels.append(match.group(3).strip())
        for raw in record.get("labels", []):
            match = LABEL_RE.match(raw)
            if match and f"{match.group(1).upper()}:{match.group(2).upper()}" == address:
                labels.append(match.group(3).strip())
        if labels:
            return labels
    return []


def labels_from_source_file(source_path: str | None, address: str | None) -> list[str]:
    if not source_path or not address:
        return []
    path = ROOT / source_path
    if not path.exists():
        return []
    flat = address.replace(":", "")
    label_re = re.compile(rf"^\s*({re.escape(flat)}_[A-Za-z0-9_]+)\s*(?::|=)", re.IGNORECASE)
    labels: list[str] = []
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        match = label_re.match(line)
        if match:
            labels.append(match.group(1).strip())
    return labels


def local_name_for_entry(bank: str, entry: dict[str, Any]) -> str | None:
    local = clean_symbol(entry.get("local_name"))
    if local:
        return local
    file_labels = labels_from_source_file(entry.get("covered_by"), entry.get("start"))
    if file_labels:
        return file_labels[0]
    labels = labels_from_source_range(bank, entry.get("start"))
    return labels[0] if labels else None


def source_contains_symbol(source_path: str | None, symbol: str | None) -> bool:
    if not source_path or not symbol:
        return False
    path = ROOT / source_path
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8", errors="ignore")
    pattern = re.compile(rf"^\s*{re.escape(symbol)}\s*(?::|=)", re.MULTILINE)
    return pattern.search(text) is not None


def source_contains_symbol_anywhere(symbol: str | None) -> bool:
    global GLOBAL_SOURCE_SYMBOLS
    if not symbol:
        return False
    if GLOBAL_SOURCE_SYMBOLS is None:
        symbols: set[str] = set()
        definition_re = re.compile(r"^\s*!?([A-Za-z_][A-Za-z0-9_]*)\s*(?::|=)", re.MULTILINE)
        for path in sorted((ROOT / "src").rglob("*.asm")):
            text = path.read_text(encoding="utf-8", errors="ignore")
            symbols.update(match.group(1) for match in definition_re.finditer(text))
        GLOBAL_SOURCE_SYMBOLS = symbols
    return symbol in GLOBAL_SOURCE_SYMBOLS


def community_status(record: dict[str, Any]) -> str:
    candidate_class = str(record.get("candidate_class") or "")
    source_kind = str(record.get("source_kind") or "")
    reason = str(record.get("reason") or "")
    ebsrc_symbol = clean_symbol(record.get("ebsrc_symbol"))
    local_source_path = clean_symbol(record.get("local_source_path"))

    if source_kind != "bank-include":
        return "docs_crosswalk_only"
    if candidate_class in {"blocked_unaddressed_or_payload_only", "manual_review"}:
        return "blocked_conflict_or_unproven"
    if candidate_class in {"adopt_constant_or_field_name", "macro_vocab_reference"}:
        return "docs_crosswalk_only"
    if not ebsrc_symbol or not local_source_path:
        return "docs_crosswalk_only"
    if is_placeholder(ebsrc_symbol):
        return "blocked_conflict_or_unproven"
    if source_contains_symbol(local_source_path, ebsrc_symbol) or normalize_name(record.get("local_name")) == normalize_name(ebsrc_symbol):
        return "source_alias_integrated"
    if source_contains_symbol_anywhere(ebsrc_symbol):
        return "blocked_conflict_or_unproven"
    if candidate_class in {"adopt_exact_symbol", "adopt_table_name"}:
        return "source_alias_ready"
    if candidate_class == "keep_local_supersedes":
        if reason == "local code name is already more specific; keep as primary and record ebsrc as corroboration":
            if alias_token_aligned(record):
                return "source_alias_ready"
            return "local_primary_stronger"
        if reason == "named ebsrc data overlaps a non-generic local source name; review before adopting":
            return "local_primary_stronger"
        if "unknown" in reason.lower():
            return "blocked_conflict_or_unproven"
        return "local_primary_stronger"
    return "blocked_conflict_or_unproven"


def lane_for_bank_entry(bank: str, entry: dict[str, Any]) -> str:
    include = str(entry.get("include_path") or "").lower()
    family = str(entry.get("family") or "").lower()
    if "audio" in include:
        return "audio-spc700"
    if "/events/scripts/" in include or include.startswith("data/events/scripts/"):
        return "event-actionscript"
    if "text" in include:
        return "text-vm"
    if "battle" in include:
        return "battle-runtime"
    if "overworld" in include:
        return "overworld-runtime"
    if "window" in include or "tile" in include or bank == "C4":
        return "ppu-window-presentation"
    if "map" in include:
        return "map-data"
    if "data" in family or include.startswith("data/"):
        return "data-records"
    return f"bank-{bank.lower()}"


def classify_bank_entry(bank: str, entry: dict[str, Any], local_name: str | None, ebsrc_name: str | None) -> tuple[str, str]:
    kind = str(entry.get("kind") or "")
    include = str(entry.get("include_path") or "")
    promoted = bool(entry.get("promoted"))
    exact = entry.get("status") == "exact"

    if kind == "support":
        return "blocked_unaddressed_or_payload_only", "support include; useful as reference but not a local semantic target"
    if include.lower().startswith("unknown/") or "/unknown/" in include.lower():
        if promoted:
            return "keep_local_supersedes", "restored ebsrc still marks this span unknown; keep local semantic classification"
        return "blocked_unaddressed_or_payload_only", "restored ebsrc unknown has no safe local coverage target"
    if "/events/scripts/" in include.lower():
        return "macro_vocab_reference", "event script label/macro vocabulary reference; no behavior claim from ebsrc alone"
    if not entry.get("start") or not exact or not promoted:
        return "blocked_unaddressed_or_payload_only", "semantic reference is not exact-covered by local source"
    if not ebsrc_name:
        return "manual_review", "exact-covered semantic include has no non-placeholder ebsrc symbol or table stem"
    if source_contains_symbol(entry.get("covered_by"), ebsrc_name):
        return "keep_local_supersedes", "restored ebsrc semantic name is already present in the local source module"
    if local_name and normalize_name(local_name) == normalize_name(ebsrc_name):
        return "keep_local_supersedes", "local name already matches the restored ebsrc semantic name"
    if kind in {"named-data", "battle-data", "text-data", "map-data", "event-data"} and is_generic_local(local_name):
        return "adopt_table_name", "exact-covered named data table can corroborate local table naming"
    if kind in {"named-data", "battle-data", "text-data", "map-data", "event-data"}:
        return "manual_review", "named ebsrc data overlaps a non-generic local source name; review before adopting"
    if kind in {"named-code", "named-include"} and is_generic_local(local_name):
        return "adopt_exact_symbol", "exact-covered named code has a non-placeholder ebsrc symbol and generic local name"
    if kind in {"named-code", "named-include"}:
        return "keep_local_supersedes", "local code name is already more specific; keep as primary and record ebsrc as corroboration"
    return "manual_review", "exact-covered semantic reference needs manual role comparison"


def build_bank_candidates(bank: str) -> list[dict[str, Any]]:
    bank_map = build_ebsrc_bank_map(bank)
    candidates: list[dict[str, Any]] = []
    for entry in bank_map.get("entries", []):
        ebsrc_name = ebsrc_name_for_entry(entry)
        local_name = local_name_for_entry(bank, entry)
        candidate_class, reason = classify_bank_entry(bank, entry, local_name, ebsrc_name)
        record = {
                "candidate_class": candidate_class,
                "lane": lane_for_bank_entry(bank, entry),
                "source_kind": "bank-include",
                "bank": bank,
                "start": entry.get("start"),
                "end": entry.get("end"),
                "size": entry.get("size"),
                "include_path": entry.get("include_path"),
                "ebsrc_symbol": ebsrc_name,
                "local_name": local_name,
                "local_source_path": entry.get("covered_by"),
                "ebsrc_kind": entry.get("kind"),
                "reason": reason,
                "recommended_action": recommended_action(candidate_class),
            }
        candidates.append(with_community_status(record))
    return candidates


def recommended_action(candidate_class: str) -> str:
    return {
        "adopt_exact_symbol": "consider a reviewed source label promotion while preserving old address-prefixed aliases",
        "adopt_constant_or_field_name": "use as contract/comment vocabulary when touching the related semantic builder",
        "adopt_table_name": "use as table-name corroboration when local role and byte range already agree",
        "macro_vocab_reference": "feed into event/text/actionscript decoder vocabulary only after local opcode proof",
        "keep_local_supersedes": "keep local semantic name/classification primary; cite ebsrc as corroborating reference",
        "blocked_unaddressed_or_payload_only": "keep as reference-only until there is exact local source or reader-path evidence",
        "manual_review": "review address, role, and naming superiority before any source/doc adoption",
    }[candidate_class]


def community_action(status: str) -> str:
    return {
        "source_alias_ready": "safe source-visible compatibility alias candidate; preserve local primary name",
        "source_alias_integrated": "ebsrc name is already searchable in source as a primary label or alias",
        "docs_crosswalk_only": "document as vocabulary or navigation reference, without source aliasing",
        "local_primary_stronger": "keep local C-port semantic name primary; use the crosswalk for ebsrc lookup",
        "blocked_conflict_or_unproven": "keep out of source until conflict, placeholder, or behavioral proof gap is resolved",
    }[status]


def with_community_status(record: dict[str, Any]) -> dict[str, Any]:
    record["community_alignment_status"] = community_status(record)
    record["community_alignment_confidence"] = community_confidence(record)
    return record


def community_confidence(record: dict[str, Any]) -> str:
    status = record.get("community_alignment_status")
    if status == "source_alias_integrated":
        return "exact_address_alias_or_primary_already_present"
    if status == "source_alias_ready":
        if record.get("candidate_class") in {"adopt_exact_symbol", "adopt_table_name"}:
            return "exact_address_review_ready"
        return "exact_address_role_compatible_token_aligned"
    if status == "local_primary_stronger":
        return "exact_address_local_name_more_specific_docs_crosswalk"
    if status == "blocked_conflict_or_unproven" and source_contains_symbol_anywhere(record.get("ebsrc_symbol")):
        return "source_symbol_collision_elsewhere_docs_crosswalk"
    if status == "docs_crosswalk_only":
        return "reference_vocabulary_or_payload_without_source_alias_target"
    return "conflict_unproven_or_placeholder_reference"


def include_records() -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    include_root = EBSRC_ROOT / "include"

    for path in sorted((include_root / "constants").glob("*.asm")) + [include_root / "enums.asm"]:
        if not path.exists():
            continue
        current_enum: str | None = None
        ordinal = 0
        for line_no, line in enumerate(path.read_text(encoding="utf-8", errors="ignore").splitlines(), start=1):
            stripped = line.split(";", 1)[0].strip()
            if not stripped:
                continue
            enum_match = ENUM_RE.match(stripped)
            if enum_match:
                current_enum = enum_match.group(1)
                ordinal = 0
                continue
            if stripped.upper().startswith(".ENDENUM"):
                current_enum = None
                continue
            assign_match = ASSIGN_RE.match(stripped)
            symbol_match = SYMBOL_RE.match(stripped)
            name = assign_match.group(1) if assign_match else symbol_match.group(1) if current_enum and symbol_match else None
            if name and not name.startswith(".") and not is_placeholder(name):
                records.append(
                    with_community_status(
                        {
                        "candidate_class": "adopt_constant_or_field_name",
                        "lane": "shared-constants",
                        "source_kind": "constant-enum",
                        "reference_path": rel(path),
                        "line": line_no,
                        "container": current_enum,
                        "name": name,
                        "value": ordinal if current_enum else (assign_match.group(2).strip() if assign_match else None),
                        "reason": "restored ebsrc constant/enum vocabulary can improve local semantic contracts",
                        "recommended_action": recommended_action("adopt_constant_or_field_name"),
                    }
                    )
                )
                if current_enum:
                    ordinal += 1

    structs = include_root / "structs.asm"
    current_struct: str | None = None
    for line_no, line in enumerate(structs.read_text(encoding="utf-8", errors="ignore").splitlines(), start=1):
        stripped = line.split(";", 1)[0].strip()
        struct_match = STRUCT_RE.match(stripped)
        if struct_match:
            current_struct = struct_match.group(1)
            continue
        if stripped.upper().startswith(".ENDSTRUCT"):
            current_struct = None
            continue
        if not current_struct or not stripped or stripped.startswith("."):
            continue
        match = SYMBOL_RE.match(stripped)
        if match and not is_placeholder(match.group(1)):
            records.append(
                with_community_status(
                    {
                    "candidate_class": "adopt_constant_or_field_name",
                    "lane": "shared-struct-fields",
                    "source_kind": "struct-field",
                    "reference_path": rel(structs),
                    "line": line_no,
                    "container": current_struct,
                    "name": match.group(1),
                    "reason": "restored ebsrc struct field vocabulary can improve local RAM/table contracts",
                    "recommended_action": recommended_action("adopt_constant_or_field_name"),
                }
                )
            )

    for path in [include_root / "eventmacros.asm", include_root / "textmacros.asm", include_root / "staffmacros.asm"]:
        if not path.exists():
            continue
        for line_no, line in enumerate(path.read_text(encoding="utf-8", errors="ignore").splitlines(), start=1):
            match = MACRO_RE.match(line)
            if not match:
                continue
            records.append(
                with_community_status(
                    {
                    "candidate_class": "macro_vocab_reference",
                    "lane": "macro-vocabulary",
                    "source_kind": "macro",
                    "reference_path": rel(path),
                    "line": line_no,
                    "name": match.group(1),
                    "reason": "restored ebsrc macro vocabulary is decoder/reference input, not behavior proof",
                    "recommended_action": recommended_action("macro_vocab_reference"),
                }
                )
            )
    return records


def audio_records() -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    if SOURCE_BACKED_AUDIO_INGEST.exists():
        ingest = json.loads(SOURCE_BACKED_AUDIO_INGEST.read_text(encoding="utf-8"))
        nav = ingest.get("source_navigation", {})
        records.append(
            with_community_status(
                {
                "candidate_class": "keep_local_supersedes",
                "lane": "audio-spc700",
                "source_kind": "source-backed-audio-ingest",
                "reference_path": "manifests/audio-spc700-sounddriver-source-ingest.json",
                "name": "source_backed_vcmd_navigation",
                "source_backed_vcmd_count": nav.get("vcmd_entry_count"),
                "reason": "byte-perfect sound-driver source remains the audio command authority; restored ebsrc audio names are secondary corroboration",
                "recommended_action": recommended_action("keep_local_supersedes"),
                }
            )
        )
    try:
        for entry in audio_spc700_source.vcmd_entry_records():
            records.append(
                with_community_status(
                    {
                    "candidate_class": "keep_local_supersedes",
                    "lane": "audio-spc700",
                    "source_kind": "source-backed-vcmd",
                    "reference_path": "refs/earthbound-sounddriver-byte-perfect/main.asm",
                    "command": entry["command"],
                    "name": entry["source_label"],
                    "source_target": entry["source_target"],
                    "arg_length": entry["arg_length"],
                    "reason": "source-backed VCMD label and argument length already integrated into audio semantics",
                    "recommended_action": recommended_action("keep_local_supersedes"),
                    }
                )
            )
    except (FileNotFoundError, ValueError):
        pass

    for path in sorted((EBSRC_ROOT / "src" / "spc700").glob("*.s*")):
        for line_no, line in enumerate(path.read_text(encoding="utf-8", errors="ignore").splitlines(), start=1):
            match = SPC_LABEL_RE.match(line)
            if not match or is_placeholder(match.group(1)):
                continue
            records.append(
                with_community_status(
                    {
                    "candidate_class": "blocked_unaddressed_or_payload_only",
                    "lane": "audio-spc700",
                    "source_kind": "restored-ebsrc-spc700-label",
                    "reference_path": rel(path),
                    "line": line_no,
                    "name": match.group(1),
                    "reason": "restored ebsrc SPC700 label is useful for comparison, but byte-perfect sound-driver source remains authoritative",
                    "recommended_action": recommended_action("blocked_unaddressed_or_payload_only"),
                    }
                )
            )
    return records


def summarize(candidates: list[dict[str, Any]], banks: list[str]) -> dict[str, Any]:
    class_counts = Counter(record["candidate_class"] for record in candidates)
    lane_counts = Counter(record["lane"] for record in candidates)
    source_counts = Counter(record["source_kind"] for record in candidates)
    community_counts = Counter(record["community_alignment_status"] for record in candidates)
    source_integrated = sum(
        1
        for record in candidates
        if record.get("candidate_class") == "keep_local_supersedes"
        and record.get("reason") == "restored ebsrc semantic name is already present in the local source module"
    )
    for name in CLASSES:
        class_counts.setdefault(name, 0)
    for name in COMMUNITY_STATUSES:
        community_counts.setdefault(name, 0)
    return {
        "bank_count": len(banks),
        "banks": banks,
        "candidate_count": len(candidates),
        "class_counts": dict(sorted(class_counts.items())),
        "community_alignment_counts": dict(sorted(community_counts.items())),
        "lane_counts": dict(sorted(lane_counts.items())),
        "source_kind_counts": dict(sorted(source_counts.items())),
        "source_integrated_ebsrc_symbol_count": source_integrated,
        "first_curated_adoption_policy": "apply only high-confidence exact symbols, table names, constants, and fields after local role/byte-equivalence review",
        "source_rename_default": "do_not_rename_when_local_name_is_more_specific",
    }


def build(banks: list[str]) -> dict[str, Any]:
    candidates: list[dict[str, Any]] = []
    for bank in banks:
        candidates.extend(build_bank_candidates(bank))
    candidates.extend(include_records())
    candidates.extend(audio_records())
    summary = summarize(candidates, banks)
    by_class: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in candidates:
        by_class[record["candidate_class"]].append(record)
    source_integrated_examples = [
        record
        for record in candidates
        if record.get("candidate_class") == "keep_local_supersedes"
        and record.get("reason") == "restored ebsrc semantic name is already present in the local source module"
    ][:40]
    return {
        "schema": "earthbound-decomp.ebsrc-knowns-integration-candidates.v1",
        "status": "restored_ebsrc_knowns_classified_for_curated_integration",
        "generated_by": "tools/build_ebsrc_knowns_integration_candidates.py",
        "references": [
            "refs/ebsrc-main/ebsrc-main/README.md",
            "refs/ebsrc-main/ebsrc-main/src/bankconfig/US",
            "refs/ebsrc-main/ebsrc-main/include/constants",
            "refs/ebsrc-main/ebsrc-main/include/structs.asm",
            "refs/ebsrc-main/ebsrc-main/include/eventmacros.asm",
            "refs/ebsrc-main/ebsrc-main/include/textmacros.asm",
            "manifests/ebsrc-restored-reference-drift-audit.json",
            "notes/ebsrc-restored-reference-drift-audit.md",
            "manifests/audio-spc700-sounddriver-source-ingest.json",
            "notes/source-readiness-triage.md",
            "notes/project-status.md",
        ],
        "summary": summary,
        "candidate_classes": {name: recommended_action(name) for name in CLASSES},
        "community_alignment_statuses": {name: community_action(name) for name in COMMUNITY_STATUSES},
        "source_integrated_ebsrc_symbol_examples": source_integrated_examples,
        "sample_candidates_by_class": {name: by_class.get(name, [])[:20] for name in CLASSES},
        "candidates": candidates,
    }


def table_row(record: dict[str, Any]) -> str:
    target = record.get("start") or record.get("name") or record.get("command") or ""
    reference = record.get("include_path") or record.get("reference_path") or ""
    ebsrc = record.get("ebsrc_symbol") or record.get("name") or ""
    local = record.get("local_name") or ""
    lane = record.get("lane") or ""
    return f"| `{target}` | `{lane}` | `{reference}` | `{ebsrc}` | `{local}` | {record.get('reason', '')} |"


def community_table_row(record: dict[str, Any]) -> str:
    target = record.get("start") or record.get("name") or record.get("command") or ""
    reference = record.get("include_path") or record.get("reference_path") or ""
    ebsrc = record.get("ebsrc_symbol") or record.get("name") or ""
    local = record.get("local_name") or ""
    confidence = record.get("community_alignment_confidence") or ""
    action = record.get("recommended_action") or ""
    return f"| `{target}` | `{record.get('lane', '')}` | `{reference}` | `{ebsrc}` | `{local}` | `{confidence}` | {action} |"


def render_markdown(data: dict[str, Any]) -> str:
    summary = data["summary"]
    lines = [
        "# ebsrc Knowns Integration Candidates",
        "",
        "Status: restored ebsrc knowns are classified for curated integration; local source semantics remain primary.",
        "",
        "## Summary",
        "",
        f"- banks audited: `{summary['banks']}`",
        f"- candidates: `{summary['candidate_count']}`",
        f"- source rename default: `{summary['source_rename_default']}`",
        f"- first curated adoption policy: `{summary['first_curated_adoption_policy']}`",
        f"- ebsrc symbols already integrated in local source: `{summary['source_integrated_ebsrc_symbol_count']}`",
        "",
        "## How to Read This Repo Against ebsrc",
        "",
        "Local semantic names remain the primary source of truth for C-port work. Exact-address restored ebsrc names are compatibility navigation: when a source-visible alias is safe, the source keeps the local primary label and adds an ebsrc alias; when a name is weaker, conflicting, unaddressed, or macro-only, this manifest keeps it in the crosswalk instead of changing source labels.",
        "",
        "## Candidate Classes",
        "",
        "| Class | Count | Action |",
        "| --- | ---: | --- |",
    ]
    for name, count in summary["class_counts"].items():
        lines.append(f"| `{name}` | {count} | {data['candidate_classes'][name]} |")
    lines.extend(
        [
            "",
            "## Community Alignment Statuses",
            "",
            "| Status | Count | Action |",
            "| --- | ---: | --- |",
        ]
    )
    for name, count in summary["community_alignment_counts"].items():
        lines.append(f"| `{name}` | {count} | {data['community_alignment_statuses'][name]} |")
    lines.extend(
        [
            "",
            "## Lane Counts",
            "",
            "| Lane | Count |",
            "| --- | ---: |",
        ]
    )
    for name, count in summary["lane_counts"].items():
        lines.append(f"| `{name}` | {count} |")
    lines.extend(
        [
            "",
            "## Source-Integrated ebsrc Symbols",
            "",
            "These exact-address ebsrc names are already present in local source as primary labels or compatibility aliases.",
            "",
            "| Target | Lane | Reference | ebsrc Name | Local Name | Reason |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
    )
    for record in data.get("source_integrated_ebsrc_symbol_examples", []):
        lines.append(table_row(record))
    lines.extend(
        [
            "",
            "## Remaining Exact/Table Adoption Batch",
            "",
            "These are review-ready exact source/table candidates only. An empty table means this pass either integrated or rejected the safe source-facing batch.",
            "",
            "| Target | Lane | Reference | ebsrc Name | Local Name | Reason |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
    )
    adoption_pool = [
        record
        for record in data["candidates"]
        if record["candidate_class"] in {"adopt_exact_symbol", "adopt_table_name"}
    ]
    for record in adoption_pool[:40]:
        lines.append(table_row(record))
    lines.extend(
        [
            "",
            "## Constants And Field Vocabulary",
            "",
            "These restored ebsrc names are vocabulary inputs for semantic contracts and comments, not bulk source-renaming targets.",
            "",
            "| Target | Lane | Reference | ebsrc Name | Local Name | Reason |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
    )
    for record in [
        item
        for item in data["candidates"]
        if item["candidate_class"] == "adopt_constant_or_field_name"
    ][:40]:
        lines.append(table_row(record))
    lines.extend(["", "## Samples By Class", ""])
    for class_name in CLASSES:
        lines.extend(
            [
                f"### `{class_name}`",
                "",
                "| Target | Lane | Reference | ebsrc Name | Local Name | Reason |",
                "| --- | --- | --- | --- | --- | --- |",
            ]
        )
        for record in data["sample_candidates_by_class"].get(class_name, []):
            lines.append(table_row(record))
        lines.append("")
    lines.extend(
        [
            "## Guardrails",
            "",
            "- Do not bulk-import restored ebsrc `UNKNOWN` names.",
            "- Keep local names when they are more specific than restored ebsrc names.",
            "- Treat macro names and unaddressed payloads as decoder/reference input, not behavior proof.",
            "- Run bank byte-equivalence checks before committing any source label promotion.",
            "",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def render_community_markdown(data: dict[str, Any]) -> str:
    summary = data["summary"]
    lines = [
        "# ebsrc Community Crosswalk",
        "",
        "Status: alias-first community navigation is generated from exact-address restored ebsrc references while local C-port semantic names remain primary.",
        "",
        "## How to Read This Repo Against ebsrc",
        "",
        "When a local name is stronger, source keeps that local primary name. Safe exact-address ebsrc names are added as compatibility aliases such as `EBSRC_NAME = LocalPrimaryName`; otherwise the ebsrc name stays in this crosswalk as searchable provenance. Macro vocabulary, placeholders, and unaddressed payload names are reference-only until local opcode or reader-path evidence exists.",
        "",
        "## Status Counts",
        "",
        "| Status | Count | Meaning |",
        "| --- | ---: | --- |",
    ]
    for name, count in summary["community_alignment_counts"].items():
        lines.append(f"| `{name}` | {count} | {data['community_alignment_statuses'][name]} |")
    lines.extend(
        [
            "",
            "## Source Alias Integrated",
            "",
            "| Target | Lane | ebsrc Path | ebsrc Name | Local Primary | Confidence | Action |",
            "| --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    integrated = [
        record
        for record in data["candidates"]
        if record.get("community_alignment_status") == "source_alias_integrated"
    ]
    for record in integrated[:80]:
        lines.append(community_table_row(record))
    lines.extend(
        [
            "",
            "## Source Alias Ready",
            "",
            "These exact-address entries are safe candidates for source-visible compatibility aliases. A non-empty table is a backlog for the alias applier or manual review.",
            "",
            "| Target | Lane | ebsrc Path | ebsrc Name | Local Primary | Confidence | Action |",
            "| --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    ready = [
        record
        for record in data["candidates"]
        if record.get("community_alignment_status") == "source_alias_ready"
    ]
    for record in ready[:80]:
        lines.append(community_table_row(record))
    lines.extend(
        [
            "",
            "## Crosswalk Samples By Lane",
            "",
            "| Target | Lane | ebsrc Path | ebsrc Name | Local Primary | Confidence | Action |",
            "| --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    seen_lanes: set[str] = set()
    for record in data["candidates"]:
        lane = str(record.get("lane") or "")
        if lane in seen_lanes:
            continue
        if record.get("community_alignment_status") in {"docs_crosswalk_only", "local_primary_stronger", "blocked_conflict_or_unproven"}:
            lines.append(community_table_row(record))
            seen_lanes.add(lane)
    lines.extend(
        [
            "",
            "## Guardrails",
            "",
            "- Do not rename local semantic labels away from their C-port-oriented names.",
            "- Add source aliases only for exact-address, role-compatible ebsrc names.",
            "- Keep ebsrc `UNKNOWN`, generic payload, and macro-only names in docs until local proof exists.",
            "- Run byte-equivalence for every bank touched by source-visible aliases.",
            "",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    args = parse_args()
    banks = [bank.upper() for bank in (args.bank or list(DEFAULT_BANKS))]
    data = build(banks)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.notes.parent.mkdir(parents=True, exist_ok=True)
    args.community_notes.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    args.notes.write_text(render_markdown(data), encoding="utf-8")
    args.community_notes.write_text(render_community_markdown(data), encoding="utf-8")
    print(
        "Built ebsrc knowns integration candidates: "
        f"{data['summary']['candidate_count']} candidates across {len(banks)} banks"
    )
    print(f"Wrote {args.output}")
    print(f"Wrote {args.notes}")
    print(f"Wrote {args.community_notes}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
