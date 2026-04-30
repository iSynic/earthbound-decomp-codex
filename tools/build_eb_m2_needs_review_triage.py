from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CROSSWALK = Path("manifests") / "eb-m2-name-crosswalk.json"
DEFAULT_MANIFEST = Path("manifests") / "eb-m2-needs-review-triage.json"
DEFAULT_NOTES = Path("notes") / "eb-m2-needs-review-triage.md"


def normalized_name(name: str) -> str:
    name = re.sub(r"^[A-F0-9]{6}_", "", name)
    name = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", name)
    name = re.sub(r"[^A-Za-z0-9]+", "_", name)
    return name.strip("_").upper()


def similarity(left: str, right: str) -> float:
    return SequenceMatcher(None, normalized_name(left), normalized_name(right)).ratio()


def evidence_modules(entry: dict[str, Any]) -> list[str]:
    modules: list[str] = []
    for evidence in entry.get("eb_m2_evidence", []):
        module = str(evidence.get("module") or "")
        if module and module not in modules:
            modules.append(module)
    return modules


def evidence_sources(entry: dict[str, Any]) -> list[str]:
    sources: list[str] = []
    for evidence in entry.get("local_evidence", []):
        source = str(evidence.get("source") or "")
        if source and source not in sources:
            sources.append(source)
    return sources


def is_boundary_end_name(name: str) -> bool:
    return bool(re.search(r"(?:End|TailBytes)$", name))


def name_tokens(entry: dict[str, Any]) -> set[str]:
    names = [entry.get("canonical_name"), entry.get("old_symbol")]
    names.extend(entry.get("eb_m2_names", []))
    names.extend(entry.get("local_names", []))
    tokens: set[str] = set()
    for raw in names:
        if not raw:
            continue
        tokens.update(token for token in normalized_name(str(raw)).split("_") if token)
    return tokens


def classify(entry: dict[str, Any]) -> tuple[str, str, str, int]:
    role = entry.get("role", {})
    eb_role = str(role.get("eb_m2", "unknown"))
    local_role = str(role.get("local", "unknown"))
    old_symbol = str(entry.get("old_symbol") or "")
    local_names = [str(name) for name in entry.get("local_names", [])]
    canonical = str(entry.get("canonical_name") or "")
    modules = evidence_modules(entry)
    tokens = name_tokens(entry)
    boundary_end = is_boundary_end_name(old_symbol) or any(is_boundary_end_name(name) for name in local_names)

    if "BankEndTailBytes" in old_symbol:
        return (
            "bank-tail-vs-eb-m2-script",
            "defer-source-promotion",
            "Local source treats the address as bank tail bytes while EB-M2 names a script start. Confirm the decoded payload and bank-end range before adopting the EB-M2 name.",
            1,
        )

    if any("data/events/scripts" in module for module in modules) or canonical.startswith("EVENT_"):
        return (
            "event-script-boundary",
            "review-script-boundary",
            "EB-M2 appears to name an event/actionscript payload boundary. Compare the script decoder span and preserve the local end alias until the script source unit is confirmed.",
            2,
        )

    if boundary_end and eb_role == "data" and local_role == "code":
        return (
            "code-to-data-boundary",
            "review-module-boundary",
            "Local evidence lands on executable code at or before the address while EB-M2 names following data. Confirm whether the local label is an end-of-code alias before promoting the data label.",
            1,
        )

    if boundary_end and eb_role == "code" and local_role == "data":
        return (
            "data-to-code-boundary",
            "review-module-boundary",
            "Local evidence marks the end of a data blob while EB-M2 names following code/script. Confirm the start address and source unit boundary before promotion.",
            1,
        )

    if boundary_end:
        return (
            "terminal-boundary-alias",
            "review-module-boundary",
            "The local name looks like a terminal alias for the previous unit. Confirm both neighboring spans, then promote only if the canonical label anchors the start unit.",
            2,
        )

    if {"PTR", "POINTER", "TABLE", "CONFIG", "DATA"} & tokens:
        return (
            "table-role-conflict",
            "manual-role-review",
            "The names suggest table/data semantics but the role evidence disagrees. Inspect nearby bytes and references before changing the canonical source label.",
            2,
        )

    return (
        "role-conflict",
        "manual-role-review",
        "EB-M2 and local role evidence disagree without an obvious terminal-boundary clue. Treat as a real conflict until a reviewer inspects the bytes and references.",
        3,
    )


def triage_entry(entry: dict[str, Any]) -> dict[str, Any]:
    bucket, suggested_action, rationale, priority = classify(entry)
    old_symbol = str(entry.get("old_symbol") or "")
    canonical = str(entry.get("canonical_name") or "")
    role = entry.get("role", {})
    return {
        "address": entry["address"],
        "bank": entry["bank"],
        "bucket": bucket,
        "priority": priority,
        "suggested_action": suggested_action,
        "suggested_decision": "keep-local-until-reviewed",
        "canonical_name": canonical,
        "old_symbol": old_symbol,
        "role": {
            "eb_m2": role.get("eb_m2", "unknown"),
            "local": role.get("local", "unknown"),
            "compatible": role.get("compatible", False),
        },
        "name_similarity": round(similarity(canonical, old_symbol), 3) if canonical and old_symbol else 0.0,
        "conflict_reason": entry.get("conflict_reason"),
        "rationale": rationale,
        "eb_m2_names": entry.get("eb_m2_names", []),
        "local_names": entry.get("local_names", []),
        "eb_m2_modules": evidence_modules(entry),
        "local_sources": evidence_sources(entry),
        "eb_m2_evidence": entry.get("eb_m2_evidence", []),
        "local_evidence": entry.get("local_evidence", []),
    }


def counter_dict(counter: Counter[Any]) -> dict[str, int]:
    return {str(key): count for key, count in sorted(counter.items(), key=lambda item: str(item[0]))}


def build_triage(crosswalk: Path) -> dict[str, Any]:
    payload = json.loads(crosswalk.read_text(encoding="utf-8"))
    conflicts = [
        entry
        for entry in payload["entries"]
        if entry.get("recommended_action") == "needs-review"
    ]
    entries = sorted(
        (triage_entry(entry) for entry in conflicts),
        key=lambda entry: (entry["priority"], entry["bank"], entry["address"], entry["canonical_name"]),
    )
    summary = {
        "entries": len(entries),
        "by_bank": counter_dict(Counter(entry["bank"] for entry in entries)),
        "by_bucket": counter_dict(Counter(entry["bucket"] for entry in entries)),
        "by_role_pair": counter_dict(Counter(f"{entry['role']['eb_m2']}->{entry['role']['local']}" for entry in entries)),
        "by_suggested_action": counter_dict(Counter(entry["suggested_action"] for entry in entries)),
        "by_priority": counter_dict(Counter(entry["priority"] for entry in entries)),
    }
    return {
        "schema": "earthbound-decomp.eb-m2-needs-review-triage.v1",
        "generated_by": "tools/build_eb_m2_needs_review_triage.py",
        "source_crosswalk": crosswalk.as_posix(),
        "policy": {
            "source_changes": "none",
            "default_decision": "keep-local-until-reviewed",
            "promotion_rule": "No triaged conflict is promoted without manual byte/reference review.",
        },
        "summary": summary,
        "entries": entries,
    }


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, separators=(",", ":")) + "\n", encoding="utf-8")


def table_rows(entries: list[dict[str, Any]], limit: int | None = None) -> list[str]:
    selected = entries if limit is None else entries[:limit]
    lines = [
        "| Priority | Address | Bucket | Suggested action | EB-M2 | Local | Role |",
        "| ---: | --- | --- | --- | --- | --- | --- |",
    ]
    for entry in selected:
        role = entry["role"]
        lines.append(
            "| `{priority}` | `{address}` | `{bucket}` | `{action}` | `{canonical}` | `{old}` | `{eb}->{local}` |".format(
                priority=entry["priority"],
                address=entry["address"],
                bucket=entry["bucket"],
                action=entry["suggested_action"],
                canonical=entry["canonical_name"],
                old=entry["old_symbol"],
                eb=role["eb_m2"],
                local=role["local"],
            )
        )
    if limit is not None and len(entries) > limit:
        lines.append(f"| ... | ... | ... | {len(entries) - limit} additional entries omitted | ... | ... | ... |")
    return lines


def write_markdown(path: Path, triage: dict[str, Any]) -> None:
    summary = triage["summary"]
    entries = triage["entries"]
    lines = [
        "# EB-M2 Needs-Review Triage",
        "",
        "Generated by `tools/build_eb_m2_needs_review_triage.py`.",
        "",
        "This is a review-only triage layer for EB-M2/local naming conflicts.",
        "It does not authorize source promotion; every entry remains local-canonical until a reviewer checks bytes, boundaries, and references.",
        "",
        "## Summary",
        "",
        f"- entries: `{summary['entries']}`",
        "",
        "By bucket:",
        "",
    ]
    for bucket, count in summary["by_bucket"].items():
        lines.append(f"- `{bucket}`: `{count}`")
    lines.extend(["", "By role pair:", ""])
    for role_pair, count in summary["by_role_pair"].items():
        lines.append(f"- `{role_pair}`: `{count}`")
    lines.extend(["", "By bank:", ""])
    for bank, count in summary["by_bank"].items():
        lines.append(f"- `{bank}`: `{count}`")
    lines.extend(
        [
            "",
            "## Review Queue",
            "",
            "Priority `1` entries are likely boundary mistakes or bank-tail/script boundaries and should be reviewed first because they may unlock clean alias-only fixes. Priority `3` entries are less patterned and need deeper byte/reference inspection.",
            "",
            *table_rows(entries, limit=None),
            "",
            "## Bucket Guidance",
            "",
            "- `bank-tail-vs-eb-m2-script`: confirm whether the local bank tail is actually decoded script payload before any rename.",
            "- `event-script-boundary`: compare EB-M2 script boundaries against local C3/C4 event/actionscript payload spans.",
            "- `code-to-data-boundary` / `data-to-code-boundary`: inspect both neighboring source units and keep terminal aliases separate from start labels.",
            "- `terminal-boundary-alias`: likely a source-unit end label; confirm before promoting the EB-M2 start name.",
            "- `table-role-conflict`: table-like naming with contradictory role evidence; inspect references and table contracts.",
            "- `role-conflict`: no obvious pattern; treat as a real conflict.",
            "",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a review-only triage report for EB-M2 needs-review name conflicts."
    )
    parser.add_argument("--crosswalk", type=Path, default=DEFAULT_CROSSWALK)
    parser.add_argument("--manifest-out", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--notes-out", type=Path, default=DEFAULT_NOTES)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    crosswalk = args.crosswalk if args.crosswalk.is_absolute() else ROOT / args.crosswalk
    manifest_out = args.manifest_out if args.manifest_out.is_absolute() else ROOT / args.manifest_out
    notes_out = args.notes_out if args.notes_out.is_absolute() else ROOT / args.notes_out
    triage = build_triage(crosswalk)
    write_json(manifest_out, triage)
    write_markdown(notes_out, triage)
    print(f"Wrote {manifest_out.relative_to(ROOT).as_posix()} and {notes_out.relative_to(ROOT).as_posix()}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
