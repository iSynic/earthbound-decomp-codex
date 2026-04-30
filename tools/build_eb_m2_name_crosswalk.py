from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path


DEFAULT_REF_ROOT = Path("refs") / "EB-M2-Listing-v1"
DEFAULT_MANIFEST = Path("manifests") / "eb-m2-name-crosswalk.json"
DEFAULT_NOTES = Path("notes") / "eb-m2-name-crosswalk.md"
DEFAULT_ALIASES = Path("manifests") / "symbol-aliases.json"

LISTING_LABEL_RE = re.compile(r"^\s*([A-F0-9]{6}):\s+([A-Za-z_][A-Za-z0-9_]*):\s*$")
LOCAL_LABEL_RE = re.compile(r"^([A-F0-9]{6}_[A-Za-z0-9_]+):\s*$")
SOURCE_FILE_RE = re.compile(r"^bank_([a-f0-9]{2})_helpers_asar\.asm$", re.IGNORECASE)


def workspace_root() -> Path:
    return Path(__file__).resolve().parent.parent


def bank_index_to_canonical(bank_index: int) -> str:
    return f"{0xC0 + bank_index:02X}"


def normalize_bank(raw: str) -> str:
    bank = raw.upper()
    if len(bank) == 2 and int(bank, 16) < 0xC0:
        return bank_index_to_canonical(int(bank, 16))
    return bank


def parse_listing_labels(ref_root: Path, region: str) -> dict[str, list[dict[str, object]]]:
    labels: dict[str, list[dict[str, object]]] = defaultdict(list)
    region_root = ref_root / region
    if not region_root.is_dir():
        raise FileNotFoundError(f"EB-M2 listing region not found: {region_root}")

    for path in sorted(region_root.glob("bank*.txt")):
        bank_index = int(path.stem.replace("bank", ""), 16)
        bank = bank_index_to_canonical(bank_index)
        for line_no, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), start=1):
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
                    "source": f"{region}/bank{bank_index:02X}.txt",
                    "line": line_no,
                }
            )
    return labels


def parse_local_labels(src_root: Path) -> dict[str, list[dict[str, object]]]:
    labels: dict[str, list[dict[str, object]]] = defaultdict(list)
    for path in sorted(src_root.rglob("bank_*_helpers_asar.asm")):
        source_match = SOURCE_FILE_RE.match(path.name)
        if not source_match:
            continue
        bank = normalize_bank(source_match.group(1))
        rel = path.relative_to(workspace_root()).as_posix()
        for line_no, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), start=1):
            match = LOCAL_LABEL_RE.match(line)
            if not match:
                continue
            label = match.group(1)
            address = label[:6]
            if address[:2] != bank:
                continue
            labels[address].append(
                {
                    "name": label,
                    "bank": bank,
                    "source": rel,
                    "line": line_no,
                }
            )
    return labels


def choose_canonical(entries: list[dict[str, object]]) -> str:
    counts = Counter(str(entry["name"]) for entry in entries)
    return sorted(counts.items(), key=lambda item: (-item[1], item[0]))[0][0]


def meaningful_eb_names(names: list[str]) -> list[str]:
    return [name for name in names if not name.startswith("UNKNOWN_")]


def classify(address: str, eb_names: list[str], local_names: list[str]) -> str:
    meaningful = meaningful_eb_names(eb_names)
    if eb_names and local_names:
        local_short = {name.split("_", 1)[1] if "_" in name and name[:6] == address else name for name in local_names}
        if set(eb_names) & set(local_names) or set(eb_names) & local_short:
            return "same-name"
        if not meaningful:
            return "local-preferred-eb-m2-unknown"
        return "eb-m2-preferred-with-local-alias"
    if eb_names:
        return "eb-m2-only"
    return "local-only"


def build_crosswalk(root: Path, ref_root: Path, region: str) -> dict[str, object]:
    eb_labels = parse_listing_labels(ref_root, region)
    local_labels = parse_local_labels(root / "src")
    addresses = sorted(set(eb_labels) | set(local_labels))

    entries: list[dict[str, object]] = []
    aliases: list[dict[str, object]] = []
    by_status: Counter[str] = Counter()
    by_bank: Counter[str] = Counter()

    for address in addresses:
        eb_entries = eb_labels.get(address, [])
        local_entries = local_labels.get(address, [])
        eb_names = sorted({str(entry["name"]) for entry in eb_entries})
        local_names = sorted({str(entry["name"]) for entry in local_entries})
        status = classify(address, eb_names, local_names)
        meaningful_entries = [
            entry for entry in eb_entries if not str(entry["name"]).startswith("UNKNOWN_")
        ]
        if status == "local-preferred-eb-m2-unknown" and local_names:
            canonical = local_names[0]
            canonical_source = "local"
        elif meaningful_entries:
            canonical = choose_canonical(meaningful_entries)
            canonical_source = "EB-M2 Listing v1"
        elif eb_entries:
            canonical = choose_canonical(eb_entries)
            canonical_source = "EB-M2 Listing v1"
        else:
            canonical = local_names[0] if local_names else None
            canonical_source = "local"
        bank = address[:2]
        by_status[status] += 1
        by_bank[bank] += 1

        entry = {
            "address": address,
            "bank": bank,
            "canonical_name": canonical,
            "canonical_source": canonical_source,
            "status": status,
            "eb_m2_names": eb_names,
            "local_names": local_names,
            "eb_m2_evidence": eb_entries[:6],
            "local_evidence": local_entries[:6],
        }
        entries.append(entry)

        if status == "local-preferred-eb-m2-unknown":
            for eb_name in eb_names:
                aliases.append(
                    {
                        "address": address,
                        "canonical_name": canonical,
                        "alias": eb_name,
                        "alias_source": "EB-M2 Listing v1",
                        "status": "eb-m2-unknown-alias-for-local-canonical",
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
        "schema": "earthbound-decomp.eb-m2-name-crosswalk.v1",
        "generated_by": "tools/build_eb_m2_name_crosswalk.py",
        "region": region,
        "policy": {
            "canonical_preference": "Prefer meaningful EB-M2 Listing v1 labels for exact-address public symbols.",
            "unknown_name_policy": "If EB-M2 only has UNKNOWN_* and local has a descriptive exact-address name, prefer the local descriptive name and keep UNKNOWN_* as an alias.",
            "local_name_policy": "Retain local generated/descriptive names as aliases unless reviewed otherwise.",
        },
        "summary": {
            "entries": len(entries),
            "aliases": len(aliases),
            "by_status": dict(sorted(by_status.items())),
            "by_bank": dict(sorted(by_bank.items())),
        },
        "entries": entries,
        "aliases": aliases,
    }


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, separators=(",", ":")) + "\n", encoding="utf-8")


def write_markdown(path: Path, manifest: dict[str, object]) -> None:
    summary = manifest["summary"]  # type: ignore[index]
    entries = manifest["entries"]  # type: ignore[index]
    by_status = summary["by_status"]  # type: ignore[index]
    by_bank = summary["by_bank"]  # type: ignore[index]

    lines = [
        "# EB-M2 Name Crosswalk",
        "",
        "Generated by `tools/build_eb_m2_name_crosswalk.py`.",
        "",
        "## Policy",
        "",
        "For exact-address public labels, EB-M2 Listing v1 names are the",
        "preferred community-facing names when they are meaningful labels.",
        "When EB-M2 only has an `UNKNOWN_*` placeholder and this project has a",
        "descriptive exact-address name, the descriptive local name remains",
        "canonical and the EB-M2 placeholder is retained as an alias.",
        "Local generated/descriptive labels otherwise remain useful as aliases",
        "and evidence, but should not create a second competing public vocabulary.",
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

    lines.extend(["", "By bank:", ""])
    for bank, count in by_bank.items():
        lines.append(f"- `{bank}`: `{count}`")

    lines.extend(
        [
            "",
            "## High-Value Exact-Address Alias Examples",
            "",
            "| Address | EB-M2 canonical | Local alias |",
            "| --- | --- | --- |",
        ]
    )
    shown = 0
    for entry in entries:  # type: ignore[assignment]
        if entry["status"] != "eb-m2-preferred-with-local-alias":
            continue
        local_names = entry["local_names"]
        if not local_names:
            continue
        lines.append(
            f"| `{entry['address']}` | `{entry['canonical_name']}` | `{local_names[0]}` |"
        )
        shown += 1
        if shown >= 40:
            break

    lines.extend(
        [
            "",
            "## Next Use",
            "",
            "- Use `manifests/eb-m2-name-crosswalk.json` to update docs, lookup",
            "  tools, and the Encyclopedia with EB-M2 canonical names.",
            "- Use `manifests/symbol-aliases.json` to keep older local names",
            "  searchable.",
            "- Do source renames in reviewed batches, preserving byte-equivalence",
            "  validation after each batch.",
            "",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refs-root", type=Path, default=DEFAULT_REF_ROOT)
    parser.add_argument("--region", default="US", choices=("US", "JP"))
    parser.add_argument("--manifest-out", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--notes-out", type=Path, default=DEFAULT_NOTES)
    parser.add_argument("--aliases-out", type=Path, default=DEFAULT_ALIASES)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = workspace_root()
    ref_root = args.refs_root if args.refs_root.is_absolute() else root / args.refs_root
    manifest = build_crosswalk(root, ref_root, args.region)

    manifest_out = args.manifest_out if args.manifest_out.is_absolute() else root / args.manifest_out
    notes_out = args.notes_out if args.notes_out.is_absolute() else root / args.notes_out
    aliases_out = args.aliases_out if args.aliases_out.is_absolute() else root / args.aliases_out

    write_json(manifest_out, manifest)
    write_json(
        aliases_out,
        {
            "schema": "earthbound-decomp.symbol-aliases.v1",
            "generated_by": "tools/build_eb_m2_name_crosswalk.py",
            "source_manifest": manifest_out.relative_to(root).as_posix(),
            "aliases": manifest["aliases"],
        },
    )
    write_markdown(notes_out, manifest)
    print(
        f"Wrote {manifest_out.relative_to(root).as_posix()}, "
        f"{aliases_out.relative_to(root).as_posix()}, and "
        f"{notes_out.relative_to(root).as_posix()}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
