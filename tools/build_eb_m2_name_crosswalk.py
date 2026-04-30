from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


DEFAULT_REF_ROOT = Path("refs") / "EB-M2-Listing-v1"
DEFAULT_MANIFEST = Path("manifests") / "eb-m2-name-crosswalk.json"
DEFAULT_NOTES = Path("notes") / "eb-m2-name-crosswalk.md"
DEFAULT_ALIASES = Path("manifests") / "symbol-aliases.json"
DEFAULT_READY = Path("notes") / "eb-m2-promote-ready.md"
DEFAULT_KEEP_LOCAL = Path("notes") / "eb-m2-keep-local.md"
DEFAULT_NEEDS_REVIEW = Path("notes") / "eb-m2-needs-review.md"

LISTING_LABEL_RE = re.compile(r"^\s*([A-F0-9]{6}):\s+([A-Za-z_][A-Za-z0-9_]*):\s*$")
LISTING_ADDR_RE = re.compile(r"^\s*([A-F0-9]{6}):\s+(?:(?:[0-9A-F]{2}\s+)+)?\s*([A-Za-z_.][A-Za-z0-9_.$]*)?")
LOCAL_LABEL_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*):\s*$")
LOCAL_ADDRESS_LABEL_RE = re.compile(r"^([A-F0-9]{6}_[A-Za-z0-9_]+):\s*$")
LOCAL_ADDRESS_ALIAS_RE = re.compile(r"^([A-F0-9]{6}_[A-Za-z0-9_]+)\s*=\s*([A-Za-z_][A-Za-z0-9_]*)\s*$")
SOURCE_FILE_RE = re.compile(r"^bank_([a-f0-9]{2})_helpers_asar\.asm$", re.IGNORECASE)
MNEMONIC_OR_DIRECTIVE_RE = re.compile(r"^\s*(?:[a-z]{2,4}|mvn|mvp|rep|sep|rtl|rts|rti|bra|j[a-z]{2}|b[a-z]{2}|\.?[A-Z][A-Z0-9_.]*)\b", re.IGNORECASE)


def workspace_root() -> Path:
    return Path(__file__).resolve().parent.parent


def bank_index_to_canonical(bank_index: int) -> str:
    return f"{0xC0 + bank_index:02X}"


def normalize_bank(raw: str) -> str:
    bank = raw.upper()
    if len(bank) == 2 and int(bank, 16) < 0xC0:
        return bank_index_to_canonical(int(bank, 16))
    return bank


def is_unknown(name: str) -> bool:
    return name.startswith("UNKNOWN_")


def meaningful_eb_names(names: list[str]) -> list[str]:
    return [name for name in names if not is_unknown(name)]


def role_from_token(token: str | None, fallback_path: str = "") -> str:
    if not token:
        if "/data/" in fallback_path or fallback_path.startswith("data/"):
            return "data"
        return "unknown"
    upper = token.upper().lstrip(".")
    if upper in {
        "BYTE",
        "DB",
        "DW",
        "DL",
        "WORD",
        "LONG",
        "ADDR",
        "INCBIN",
        "BINARY",
    }:
        return "data"
    if upper in {"INCLUDE", "INCLUDEDFILE", "ORG", "SEGMENT", "A16", "I16", "A8", "I8"}:
        return "support"
    if MNEMONIC_OR_DIRECTIVE_RE.match(token):
        return "code"
    return "unknown"


def next_role_from_lines(lines: list[str], index: int, fallback_path: str = "") -> str:
    for line in lines[index + 1 : min(len(lines), index + 9)]:
        stripped = line.strip()
        if not stripped or stripped.startswith(";"):
            continue
        if stripped.endswith(":"):
            continue
        if re.match(r"^[!A-Za-z_][A-Za-z0-9_!]*\s*=", stripped):
            continue
        listing_match = LISTING_ADDR_RE.match(line)
        if listing_match:
            return role_from_token(listing_match.group(2), fallback_path)
        token = stripped.split()[0] if stripped.split() else None
        return role_from_token(token, fallback_path)
    return role_from_token(None, fallback_path)


def parse_listing_labels(ref_root: Path, region: str) -> dict[str, list[dict[str, object]]]:
    labels: dict[str, list[dict[str, object]]] = defaultdict(list)
    region_root = ref_root / region
    if not region_root.is_dir():
        raise FileNotFoundError(f"EB-M2 listing region not found: {region_root}")

    for path in sorted(region_root.glob("bank*.txt")):
        bank_index = int(path.stem.replace("bank", ""), 16)
        bank = bank_index_to_canonical(bank_index)
        rel_source = f"{region}/bank{bank_index:02X}.txt"
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        current_module = ""
        for line_no, line in enumerate(lines, start=1):
            if line.startswith(">>> "):
                current_module = line[4:].strip()
                continue
            match = LISTING_LABEL_RE.match(line)
            if not match:
                continue
            address, name = match.groups()
            if address[:2] != bank:
                continue
            labels[address].append(
                {
                    "name": name,
                    "bank": bank,
                    "source": rel_source,
                    "line": line_no,
                    "module": current_module,
                    "role": next_role_from_lines(lines, line_no - 1, current_module),
                }
            )
    return labels


def parse_local_labels(src_root: Path) -> dict[str, list[dict[str, object]]]:
    labels: dict[str, list[dict[str, object]]] = defaultdict(list)
    for path in sorted(src_root.rglob("*.asm")):
        if "event_scripts" in path.parts:
            continue
        source_match = SOURCE_FILE_RE.match(path.name)
        if source_match:
            bank = normalize_bank(source_match.group(1))
        else:
            try:
                bank = normalize_bank(path.relative_to(src_root).parts[0])
            except (IndexError, ValueError):
                continue
            if not re.fullmatch(r"[C-F][0-9A-F]", bank):
                continue
        rel = path.relative_to(workspace_root()).as_posix()
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        pending_label: tuple[str, int] | None = None
        for line_no, line in enumerate(lines, start=1):
            address_label = LOCAL_ADDRESS_LABEL_RE.match(line)
            if address_label:
                name = address_label.group(1)
                address = name[:6]
                if address[:2] == bank:
                    labels[address].append(
                        {
                            "name": name,
                            "bank": bank,
                            "source": rel,
                            "line": line_no,
                            "role": next_role_from_lines(lines, line_no - 1, rel),
                            "kind": "address-label",
                        }
                    )
                pending_label = None
                continue

            alias_match = LOCAL_ADDRESS_ALIAS_RE.match(line)
            if alias_match:
                alias, target = alias_match.groups()
                address = alias[:6]
                if address[:2] == bank:
                    role = next_role_from_lines(lines, line_no - 1, rel)
                    labels[address].append(
                        {
                            "name": alias,
                            "bank": bank,
                            "source": rel,
                            "line": line_no,
                            "role": role,
                            "kind": "address-alias",
                            "target": target,
                        }
                    )
                    labels[address].append(
                        {
                            "name": target,
                            "bank": bank,
                            "source": rel,
                            "line": line_no,
                            "role": role,
                            "kind": "alias-target",
                            "alias": alias,
                        }
                    )
                pending_label = None
                continue

            label_match = LOCAL_LABEL_RE.match(line)
            if label_match:
                pending_label = (label_match.group(1), line_no)
                continue

            if pending_label:
                # Address-less labels become addressable once a preserved alias follows them.
                # If the next non-empty line is not such an alias, discard the pending label.
                stripped = line.strip()
                if stripped and not stripped.startswith(";"):
                    pending_label = None
    return labels


def choose_canonical(entries: list[dict[str, object]]) -> str:
    counts = Counter(str(entry["name"]) for entry in entries)
    return sorted(counts.items(), key=lambda item: (-item[1], item[0]))[0][0]


def dominant_role(entries: list[dict[str, object]]) -> str:
    roles = [str(entry.get("role", "unknown")) for entry in entries if entry.get("role") != "support"]
    if not roles:
        return "unknown"
    return Counter(roles).most_common(1)[0][0]


def roles_compatible(eb_role: str, local_role: str) -> bool:
    if "unknown" in {eb_role, local_role}:
        return True
    if "support" in {eb_role, local_role}:
        return True
    return eb_role == local_role


def address_prefixed_short_names(address: str, local_names: list[str]) -> set[str]:
    return {
        name.split("_", 1)[1]
        for name in local_names
        if name.startswith(address + "_") and "_" in name
    }


def classify(
    address: str,
    eb_entries: list[dict[str, object]],
    local_entries: list[dict[str, object]],
) -> dict[str, object]:
    eb_names = sorted({str(entry["name"]) for entry in eb_entries})
    local_names = sorted({str(entry["name"]) for entry in local_entries})
    meaningful = meaningful_eb_names(eb_names)
    eb_role = dominant_role(eb_entries)
    local_role = dominant_role(local_entries)
    compatible = roles_compatible(eb_role, local_role)
    local_short = address_prefixed_short_names(address, local_names)

    if eb_entries and local_entries:
        if set(meaningful) & (set(local_names) | local_short):
            return {
                "status": "adopted",
                "recommended_action": "keep",
                "review_status": "adopted",
                "confidence": "high",
                "conflict_reason": None,
            }
        if not meaningful:
            return {
                "status": "keep-local",
                "recommended_action": "keep-local",
                "review_status": "reviewed-by-policy",
                "confidence": "high",
                "conflict_reason": "EB-M2 has only UNKNOWN_* labels at this exact address.",
            }
        if compatible:
            return {
                "status": "promote",
                "recommended_action": "promote",
                "review_status": "ready-for-reviewed-batch",
                "confidence": "high",
                "conflict_reason": None,
            }
        return {
            "status": "conflict",
            "recommended_action": "needs-review",
            "review_status": "needs-review",
            "confidence": "low",
            "conflict_reason": f"Role mismatch: EB-M2 role={eb_role}, local role={local_role}.",
        }

    if eb_entries:
        return {
            "status": "eb-m2-only",
            "recommended_action": "reference-only",
            "review_status": "needs-local-match",
            "confidence": "medium" if meaningful else "low",
            "conflict_reason": None,
        }

    return {
        "status": "local-only",
        "recommended_action": "keep-local",
        "review_status": "local-only",
        "confidence": "medium",
        "conflict_reason": None,
    }


def canonical_for_entry(
    status: str,
    eb_entries: list[dict[str, object]],
    local_entries: list[dict[str, object]],
) -> tuple[str | None, str]:
    meaningful_entries = [
        entry for entry in eb_entries if not is_unknown(str(entry["name"]))
    ]
    local_names = sorted({str(entry["name"]) for entry in local_entries})
    if status in {"promote", "adopted"} and meaningful_entries:
        return choose_canonical(meaningful_entries), "EB-M2 Listing v1"
    if status == "keep-local" and local_names:
        non_target_aliases = [
            str(entry["name"])
            for entry in local_entries
            if entry.get("kind") in {"address-label", "alias-target"}
            and not str(entry["name"]).startswith("UNKNOWN_")
        ]
        return sorted(set(non_target_aliases or local_names))[0], "local"
    if meaningful_entries:
        return choose_canonical(meaningful_entries), "EB-M2 Listing v1"
    if eb_entries:
        return choose_canonical(eb_entries), "EB-M2 Listing v1"
    if local_names:
        return local_names[0], "local"
    return None, "none"


def old_and_new_symbols(
    status: str,
    canonical: str | None,
    address: str,
    local_names: list[str],
) -> tuple[str | None, str | None]:
    address_names = [name for name in local_names if name.startswith(address + "_")]
    non_end_names = [name for name in address_names if not name.endswith("_End")]
    old_symbol = (
        sorted(non_end_names)[0]
        if non_end_names
        else (sorted(address_names)[0] if address_names else (local_names[0] if local_names else None))
    )
    new_symbol = canonical if status in {"promote", "adopted"} else None
    return old_symbol, new_symbol


def build_crosswalk(root: Path, ref_root: Path, region: str) -> dict[str, object]:
    eb_labels = parse_listing_labels(ref_root, region)
    local_labels = parse_local_labels(root / "src")
    addresses = sorted(set(eb_labels) | set(local_labels))

    entries: list[dict[str, object]] = []
    aliases: list[dict[str, object]] = []
    by_status: Counter[str] = Counter()
    by_bank: Counter[str] = Counter()
    by_action: Counter[str] = Counter()

    for address in addresses:
        eb_entries = eb_labels.get(address, [])
        local_entries = local_labels.get(address, [])
        eb_names = sorted({str(entry["name"]) for entry in eb_entries})
        local_names = sorted({str(entry["name"]) for entry in local_entries})
        decision = classify(address, eb_entries, local_entries)
        status = str(decision["status"])
        canonical, canonical_source = canonical_for_entry(status, eb_entries, local_entries)
        old_symbol, new_symbol = old_and_new_symbols(status, canonical, address, local_names)
        bank = address[:2]
        role = {
            "eb_m2": dominant_role(eb_entries),
            "local": dominant_role(local_entries),
            "compatible": roles_compatible(dominant_role(eb_entries), dominant_role(local_entries)),
        }

        by_status[status] += 1
        by_bank[bank] += 1
        by_action[str(decision["recommended_action"])] += 1

        entry = {
            "address": address,
            "bank": bank,
            "canonical_name": canonical,
            "canonical_source": canonical_source,
            "status": status,
            "confidence": decision["confidence"],
            "role": role,
            "review_status": decision["review_status"],
            "recommended_action": decision["recommended_action"],
            "old_symbol": old_symbol,
            "new_symbol": new_symbol,
            "conflict_reason": decision["conflict_reason"],
            "eb_m2_names": eb_names,
            "local_names": local_names,
            "eb_m2_evidence": eb_entries[:6],
            "local_evidence": local_entries[:6],
        }
        entries.append(entry)

        if status == "keep-local":
            for eb_name in eb_names:
                aliases.append(
                    {
                        "address": address,
                        "canonical_name": canonical,
                        "alias": eb_name,
                        "alias_source": "EB-M2 Listing v1",
                        "status": "eb-m2-alias-for-local-canonical",
                    }
                )
        elif eb_entries and local_entries:
            for local_name in local_names:
                if local_name != canonical:
                    aliases.append(
                        {
                            "address": address,
                            "canonical_name": canonical,
                            "alias": local_name,
                            "alias_source": "local-scaffold",
                            "status": "alias-for-eb-m2-canonical",
                        }
                    )

    return {
        "schema": "earthbound-decomp.eb-m2-name-crosswalk.v2",
        "generated_by": "tools/build_eb_m2_name_crosswalk.py",
        "region": region,
        "policy": {
            "canonical_preference": "Prefer meaningful EB-M2 Listing v1 labels for exact-address public symbols after compatibility review.",
            "promotion_gate": "Promote only exact-address, non-UNKNOWN EB-M2 labels whose code/data role is compatible with local source evidence.",
            "unknown_name_policy": "If EB-M2 only has UNKNOWN_* and local has a descriptive exact-address name, prefer the local descriptive name and keep UNKNOWN_* as an alias.",
            "local_name_policy": "Retain local generated/descriptive names as aliases unless reviewed otherwise.",
        },
        "summary": {
            "entries": len(entries),
            "aliases": len(aliases),
            "by_status": dict(sorted(by_status.items())),
            "by_recommended_action": dict(sorted(by_action.items())),
            "by_bank": dict(sorted(by_bank.items())),
        },
        "entries": entries,
        "aliases": aliases,
    }


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, separators=(",", ":")) + "\n", encoding="utf-8")


def table_rows(entries: list[dict[str, Any]], limit: int | None = None) -> list[str]:
    rows = ["| Address | Status | Action | Canonical | Old/local | Confidence |", "| --- | --- | --- | --- | --- | --- |"]
    selected = entries if limit is None else entries[:limit]
    for entry in selected:
        rows.append(
            "| `{address}` | `{status}` | `{action}` | `{canonical}` | `{old}` | `{confidence}` |".format(
                address=entry["address"],
                status=entry["status"],
                action=entry["recommended_action"],
                canonical=entry.get("canonical_name") or "",
                old=entry.get("old_symbol") or "",
                confidence=entry.get("confidence") or "",
            )
        )
    if limit is not None and len(entries) > limit:
        rows.append(f"| ... | ... | ... | {len(entries) - limit} additional entries omitted | ... | ... |")
    return rows


def write_markdown(path: Path, manifest: dict[str, object]) -> None:
    summary = manifest["summary"]  # type: ignore[index]
    entries: list[dict[str, Any]] = manifest["entries"]  # type: ignore[assignment,index]
    by_status = summary["by_status"]  # type: ignore[index]
    by_action = summary["by_recommended_action"]  # type: ignore[index]
    by_bank = summary["by_bank"]  # type: ignore[index]
    ready = [entry for entry in entries if entry["recommended_action"] == "promote"]

    lines = [
        "# EB-M2 Name Crosswalk",
        "",
        "Generated by `tools/build_eb_m2_name_crosswalk.py`.",
        "",
        "## Policy",
        "",
        "EB-M2 Listing v1 is the preferred community-facing naming authority for",
        "exact-address labels only when the label is meaningful and compatible with",
        "local code/data evidence. `UNKNOWN_*` labels are never promoted; they remain",
        "aliases when local descriptive names exist.",
        "",
        "## Summary",
        "",
        f"- entries: `{summary['entries']}`",
        f"- alias records: `{summary['aliases']}`",
        "",
        "By status:",
        "",
    ]
    for status, count in by_status.items():
        lines.append(f"- `{status}`: `{count}`")
    lines.extend(["", "By recommended action:", ""])
    for action, count in by_action.items():
        lines.append(f"- `{action}`: `{count}`")
    lines.extend(["", "By bank:", ""])
    for bank, count in by_bank.items():
        lines.append(f"- `{bank}`: `{count}`")

    lines.extend(
        [
            "",
            "## Ready-To-Promote Examples",
            "",
            *table_rows(ready, limit=40),
            "",
            "## Next Use",
            "",
            "- Use `manifests/eb-m2-name-crosswalk.json` as the source of truth for canonical names and aliases.",
            "- Use `manifests/symbol-aliases.json` to keep older local names and EB-M2 unknown placeholders searchable.",
            "- Promote source symbols only in reviewed bank/subsystem batches, validating byte-equivalence after each batch.",
            "",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def write_report(path: Path, title: str, entries: list[dict[str, Any]], intro: list[str]) -> None:
    by_bank = Counter(str(entry["bank"]) for entry in entries)
    lines = [f"# {title}", "", *intro, "", "## Summary", "", f"- entries: `{len(entries)}`"]
    for bank, count in sorted(by_bank.items()):
        lines.append(f"- `{bank}`: `{count}`")
    lines.extend(["", "## Entries", "", *table_rows(entries, limit=None), ""])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def write_reports(
    ready_path: Path,
    keep_local_path: Path,
    needs_review_path: Path,
    manifest: dict[str, object],
) -> None:
    entries: list[dict[str, Any]] = manifest["entries"]  # type: ignore[assignment,index]
    ready = [entry for entry in entries if entry["recommended_action"] == "promote"]
    keep_local = [entry for entry in entries if entry["status"] == "keep-local"]
    needs_review = [entry for entry in entries if entry["recommended_action"] == "needs-review"]
    write_report(
        ready_path,
        "EB-M2 Ready-To-Promote Labels",
        ready,
        [
            "Exact-address labels whose EB-M2 names are meaningful and role-compatible.",
            "These are eligible for reviewed source-symbol promotion batches.",
        ],
    )
    write_report(
        keep_local_path,
        "EB-M2 Keep-Local Labels",
        keep_local,
        [
            "Exact-address labels where local names remain canonical.",
            "The common case is EB-M2 having only an `UNKNOWN_*` placeholder.",
        ],
    )
    write_report(
        needs_review_path,
        "EB-M2 Needs-Review Labels",
        needs_review,
        [
            "Labels with contradictory or insufficient evidence.",
            "Do not promote these until a human resolves the conflict.",
        ],
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refs-root", type=Path, default=DEFAULT_REF_ROOT)
    parser.add_argument("--region", default="US", choices=("US", "JP"))
    parser.add_argument("--manifest-out", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--notes-out", type=Path, default=DEFAULT_NOTES)
    parser.add_argument("--aliases-out", type=Path, default=DEFAULT_ALIASES)
    parser.add_argument("--ready-out", type=Path, default=DEFAULT_READY)
    parser.add_argument("--keep-local-out", type=Path, default=DEFAULT_KEEP_LOCAL)
    parser.add_argument("--needs-review-out", type=Path, default=DEFAULT_NEEDS_REVIEW)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = workspace_root()
    ref_root = args.refs_root if args.refs_root.is_absolute() else root / args.refs_root
    manifest = build_crosswalk(root, ref_root, args.region)

    manifest_out = args.manifest_out if args.manifest_out.is_absolute() else root / args.manifest_out
    notes_out = args.notes_out if args.notes_out.is_absolute() else root / args.notes_out
    aliases_out = args.aliases_out if args.aliases_out.is_absolute() else root / args.aliases_out
    ready_out = args.ready_out if args.ready_out.is_absolute() else root / args.ready_out
    keep_local_out = args.keep_local_out if args.keep_local_out.is_absolute() else root / args.keep_local_out
    needs_review_out = args.needs_review_out if args.needs_review_out.is_absolute() else root / args.needs_review_out

    write_json(manifest_out, manifest)
    write_json(
        aliases_out,
        {
            "schema": "earthbound-decomp.symbol-aliases.v2",
            "generated_by": "tools/build_eb_m2_name_crosswalk.py",
            "source_manifest": manifest_out.relative_to(root).as_posix(),
            "aliases": manifest["aliases"],
        },
    )
    write_markdown(notes_out, manifest)
    write_reports(ready_out, keep_local_out, needs_review_out, manifest)
    print(
        f"Wrote {manifest_out.relative_to(root).as_posix()}, "
        f"{aliases_out.relative_to(root).as_posix()}, "
        f"{notes_out.relative_to(root).as_posix()}, "
        f"{ready_out.relative_to(root).as_posix()}, "
        f"{keep_local_out.relative_to(root).as_posix()}, and "
        f"{needs_review_out.relative_to(root).as_posix()}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
