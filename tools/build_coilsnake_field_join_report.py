from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import rom_tools


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CROSSWALK = ROOT / "manifests" / "coilsnake-crosswalk.json"
DEFAULT_JSON_OUT = ROOT / "build" / "coilsnake" / "reports" / "coilsnake-field-join-report.json"
DEFAULT_MARKDOWN_OUT = ROOT / "notes" / "coilsnake-field-join-report.md"


@dataclass(frozen=True)
class Address:
    file_offset: int
    bank: int
    address: int

    @property
    def bank_text(self) -> str:
        return f"{self.bank:02X}"

    @property
    def address_text(self) -> str:
        return f"{self.address:04X}"

    @property
    def hirom(self) -> str:
        return f"{self.bank_text}:{self.address_text}"

    @property
    def long(self) -> str:
        return f"0x{self.bank:02X}{self.address:04X}"

    @property
    def offset_text(self) -> str:
        return f"0x{self.file_offset:06X}"


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def parse_hex(value: str) -> int:
    return int(value, 16)


def offset_to_address(file_offset: int) -> Address:
    bank = rom_tools.canonical_bank_for_file_offset(file_offset)
    return Address(file_offset=file_offset, bank=bank, address=file_offset % 0x10000)


RANGE_RE = re.compile(
    r"^(?P<start_bank>[0-9A-Fa-f]{2}):(?P<start>[0-9A-Fa-f]{4,5})\.\."
    r"(?P<end_bank>[0-9A-Fa-f]{2}):(?P<end>[0-9A-Fa-f]{4,5})$"
)
RANGE_IN_LINE_RE = re.compile(
    r"(?P<start_bank>[0-9A-Fa-f]{2}):(?P<start>[0-9A-Fa-f]{4,5})\.\."
    r"(?P<end_bank>[0-9A-Fa-f]{2}):(?P<end>[0-9A-Fa-f]{4,5})"
)


def parse_manifest_range(text: str) -> tuple[int, int, int, int] | None:
    match = RANGE_RE.match(text)
    if not match:
        return None
    return (
        int(match.group("start_bank"), 16),
        int(match.group("start"), 16),
        int(match.group("end_bank"), 16),
        int(match.group("end"), 16),
    )


def address_in_range(address: Address, range_text: str) -> bool:
    parsed = parse_manifest_range(range_text)
    if parsed is None:
        return False
    start_bank, start, end_bank, end = parsed
    if start_bank != end_bank or address.bank != start_bank:
        return False
    return start <= address.address < end


def address_in_note_range(address: Address, range_text: str) -> bool:
    parsed = parse_manifest_range(range_text)
    if parsed is None:
        return False
    start_bank, start, end_bank, end = parsed
    if start_bank != end_bank or address.bank != start_bank:
        return False
    return start <= address.address <= end


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_asset_entries(asset_manifest_dir: Path) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for path in sorted(asset_manifest_dir.glob("*.json")):
        data = load_json(path)
        for asset in data.get("assets", []):
            source = asset.get("source", {})
            range_text = source.get("range")
            if not isinstance(range_text, str):
                continue
            entries.append(
                {
                    "manifest": rel(path),
                    "id": asset.get("id"),
                    "title": asset.get("title"),
                    "category": asset.get("category"),
                    "range": range_text,
                    "bytes": source.get("bytes"),
                    "output_kinds": sorted(
                        {
                            output.get("kind")
                            for output in asset.get("outputs", [])
                            if isinstance(output, dict) and output.get("kind")
                        }
                    ),
                    "notes": [
                        note
                        for note in asset.get("notes", [])
                        if isinstance(note, str)
                        and (
                            note.startswith("Source ")
                            or note.startswith("Original file")
                            or "compressed" in note.lower()
                            or "coverage gap" in note.lower()
                        )
                    ][:4],
                }
            )
    return entries


def matching_assets(entries: list[dict[str, Any]], address: Address) -> list[dict[str, Any]]:
    return [
        entry
        for entry in entries
        if isinstance(entry.get("range"), str) and address_in_range(address, entry["range"])
    ]


def normalize_tokens(*values: str) -> list[str]:
    stopwords = {
        "asm",
        "asset",
        "configuration",
        "data",
        "map",
        "settings",
        "table",
        "tables",
        "text",
        "yaml",
        "yml",
    }
    tokens: list[str] = []
    for value in values:
        stem = Path(value).stem.lower()
        for token in re.split(r"[^a-z0-9]+", stem):
            if len(token) >= 3 and token not in stopwords:
                tokens.append(token)
    seen: set[str] = set()
    return [token for token in tokens if not (token in seen or seen.add(token))]


def range_hits_in_line(address: Address, line: str) -> list[str]:
    hits: list[str] = []
    for match in RANGE_IN_LINE_RE.finditer(line):
        range_text = match.group(0)
        if address_in_note_range(address, range_text):
            hits.append(range_text)
    return hits


def find_source_matches(source_root: Path, address: Address, source_file: str) -> list[dict[str, Any]]:
    bank_dir = source_root / address.bank_text.lower()
    if not bank_dir.is_dir():
        return []

    tokens = normalize_tokens(source_file)
    address_terms = {
        address.hirom.lower(),
        address.long.lower(),
        address.offset_text.lower(),
        f"${address.address_text}".lower(),
    }

    matches: list[dict[str, Any]] = []
    for path in sorted(bank_dir.glob("*.asm")):
        path_text = path.name.lower()
        filename_hits = [token for token in tokens if token in path_text]
        content_hits: list[dict[str, Any]] = []
        try:
            with path.open("r", encoding="utf-8", errors="ignore") as handle:
                for line_number, line in enumerate(handle, start=1):
                    lower = line.lower()
                    hit_terms = sorted(term for term in address_terms if term in lower)
                    hit_terms.extend(range_hits_in_line(address, line))
                    if hit_terms:
                        content_hits.append(
                            {
                                "line": line_number,
                                "terms": hit_terms,
                            }
                        )
                    if len(content_hits) >= 4:
                        break
        except OSError:
            continue

        if filename_hits or content_hits:
            matches.append(
                {
                    "path": rel(path),
                    "filename_token_hits": filename_hits,
                    "address_hits": content_hits,
                }
            )

    def score(match: dict[str, Any]) -> tuple[int, str]:
        return (len(match["address_hits"]) * 10 + len(match["filename_token_hits"]), match["path"])

    return sorted(matches, key=score, reverse=True)[:12]


def range_span(range_text: str) -> int:
    parsed = parse_manifest_range(range_text)
    if parsed is None:
        return 0x1000000
    start_bank, start, end_bank, end = parsed
    if start_bank != end_bank:
        return 0x1000000
    return max(0, end - start)


def find_contract_range_matches(notes_root: Path, address: Address) -> list[dict[str, Any]]:
    matches: list[dict[str, Any]] = []
    for path in sorted(notes_root.glob("*.md")):
        if path.name == DEFAULT_MARKDOWN_OUT.name:
            continue
        try:
            lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        except OSError:
            continue
        for line_number, line in enumerate(lines, start=1):
            ranges = range_hits_in_line(address, line)
            if not ranges:
                continue
            label_match = re.search(r"`([^`]+)`", line)
            matches.append(
                {
                    "path": rel(path),
                    "line": line_number,
                    "ranges": ranges,
                    "span": min(range_span(range_text) for range_text in ranges),
                    "label": label_match.group(1) if label_match else None,
                }
            )
    return sorted(matches, key=lambda match: (match["span"], match["path"], match["line"]))[:16]


def find_note_matches(notes_root: Path, address: Address, experiment: dict[str, Any]) -> list[dict[str, Any]]:
    source_file = str(experiment.get("source_file", ""))
    source_stem = Path(source_file).stem.lower()
    source_phrase = source_stem.replace("_", " ")
    edit = str(experiment.get("edit", "")).lower()
    terms = {
        address.hirom.lower(),
        address.long.lower(),
        address.offset_text.lower(),
        source_file.lower(),
        source_stem,
        source_phrase,
    }
    for phrase in ("teddy bear", "auto fight", "sprite palette"):
        if phrase in edit:
            terms.add(phrase)
    terms = {term for term in terms if term}

    matches: list[dict[str, Any]] = []
    for path in sorted(notes_root.glob("*.md")):
        if path.name == DEFAULT_MARKDOWN_OUT.name:
            continue
        try:
            lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        except OSError:
            continue
        for line_number, line in enumerate(lines, start=1):
            lower = line.lower()
            hit_terms = sorted(term for term in terms if term in lower)
            if hit_terms:
                matches.append(
                    {
                        "path": rel(path),
                        "line": line_number,
                        "terms": hit_terms[:8],
                    }
                )
                break
    return matches[:16]


def family_lookup(crosswalk: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        family["id"]: family
        for family in crosswalk.get("families", [])
        if isinstance(family, dict) and isinstance(family.get("id"), str)
    }


def classify_status(
    experiment: dict[str, Any],
    assets: list[dict[str, Any]],
    source_matches: list[dict[str, Any]],
    contract_matches: list[dict[str, Any]],
    note_matches: list[dict[str, Any]],
) -> str:
    if contract_matches:
        return "local-range-confirmed"
    if source_matches and any(match["address_hits"] for match in source_matches):
        return "source-range-confirmed"
    if assets and all(asset.get("category") == "raw-gap" for asset in assets):
        return "raw-gap-source-candidate" if source_matches else "raw-gap-range-candidate"
    if assets and source_matches:
        return "asset-source-candidate"
    if assets:
        return "asset-range-candidate"
    if note_matches or source_matches:
        return "local-note-candidate"
    if experiment.get("evidence_level") == "diff-confirmed":
        return "diff-only-needs-local-join"
    return "needs-triage"


def relocation_warning(
    experiment: dict[str, Any],
    assets: list[dict[str, Any]],
    contract_matches: list[dict[str, Any]],
) -> str | None:
    source_file = str(experiment.get("source_file", "")).lower()
    if not assets:
        return None
    source_tokens = set(normalize_tokens(source_file))
    contract_text = " ".join(str(match.get("label", "")).lower() for match in contract_matches)
    if source_tokens and any(token in contract_text for token in source_tokens):
        return None
    asset_text = " ".join(
        str(asset.get(key, "")).lower() for asset in assets for key in ("id", "title", "range")
    )
    if source_tokens and not any(token in asset_text for token in source_tokens):
        return (
            "Changed offset falls in a local asset range whose vocabulary does not match the "
            "CoilSnake source file; treat as a relocation/compiler-normalization candidate "
            "until a runtime consumer or pointer table is joined."
        )
    return None


def build_join(
    experiment_id: str,
    experiment: dict[str, Any],
    asset_entries: list[dict[str, Any]],
    families: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    diff = experiment.get("diff", {})
    offset_text = diff.get("first_changed_offset")
    if not isinstance(offset_text, str):
        raise ValueError(f"{experiment_id}: missing diff.first_changed_offset")

    address = offset_to_address(parse_hex(offset_text))
    assets = matching_assets(asset_entries, address)
    source_matches = find_source_matches(ROOT / "src", address, str(experiment.get("source_file", "")))
    contract_matches = find_contract_range_matches(ROOT / "notes", address)
    note_matches = find_note_matches(ROOT / "notes", address, experiment)
    family = families.get(str(experiment.get("resource_family", "")), {})
    warning = relocation_warning(experiment, assets, contract_matches)

    join: dict[str, Any] = {
        "experiment_id": experiment_id,
        "coilsnake_file": experiment.get("source_file"),
        "edit": experiment.get("edit"),
        "comparison_base": experiment.get("comparison_base"),
        "evidence_level": experiment.get("evidence_level"),
        "diff_summary": {
            "changed_bytes": diff.get("changed_bytes"),
            "contiguous_changed_runs": diff.get("contiguous_changed_runs"),
            "first_changed_offset": address.offset_text,
            "last_changed_offset_exclusive": diff.get("last_changed_offset_exclusive"),
            "edit_behavior": "fixed-size byte" if diff.get("changed_bytes") == 1 else "span-or-repoint",
        },
        "address": {
            "file_offset": address.offset_text,
            "hirom": address.hirom,
            "canonical_long": address.long,
            "source_bank": address.bank_text,
        },
        "resource_family": {
            "id": experiment.get("resource_family"),
            "label": family.get("label"),
            "local_status": family.get("local_status"),
            "related_local_docs": family.get("related_local_docs", []),
        },
        "local_asset_matches": assets,
        "local_contract_matches": contract_matches,
        "source_scaffold_matches": source_matches,
        "note_matches": note_matches,
        "join_status": classify_status(experiment, assets, source_matches, contract_matches, note_matches),
        "lookup_status": (
            "known-runtime-consumer-not-yet-claimed"
            if not any(match["address_hits"] for match in source_matches)
            else "address-hit-in-source-scaffold"
        ),
    }
    if warning:
        join["warning"] = warning
    return join


def render_markdown(report: dict[str, Any]) -> str:
    rows = []
    for join in report["joins"]:
        asset = join["local_asset_matches"][0] if join["local_asset_matches"] else None
        contract = join["local_contract_matches"][0] if join["local_contract_matches"] else None
        source = join["source_scaffold_matches"][0] if join["source_scaffold_matches"] else None
        warning = "yes" if join.get("warning") else "no"
        rows.append(
            "| {experiment} | `{file}` | `{offset}` | `{hirom}` | `{asset}` | `{source}` | `{status}` | {warning} |".format(
                experiment=join["experiment_id"],
                file=join["coilsnake_file"],
                offset=join["address"]["file_offset"],
                hirom=join["address"]["hirom"],
                asset=(contract["label"] if contract else asset["id"] if asset else "none"),
                source=(source["path"] if source else "none"),
                status=join["join_status"],
                warning=warning,
            )
        )

    detail_lines: list[str] = []
    for join in report["joins"]:
        detail_lines.extend(
            [
                f"## {join['experiment_id']}",
                "",
                f"- CoilSnake edit: `{join['coilsnake_file']}` - {join['edit']}",
                f"- Diff result: `{join['diff_summary']['changed_bytes']}` byte(s), first changed offset `{join['address']['file_offset']}` -> `{join['address']['hirom']}` / `{join['address']['canonical_long']}`.",
                f"- Evidence: `{join['evidence_level']}`; behavior: `{join['diff_summary']['edit_behavior']}`.",
                f"- Join status: `{join['join_status']}`; lookup status: `{join['lookup_status']}`.",
            ]
        )
        if join["local_asset_matches"]:
            detail_lines.append("- Local asset/data range matches:")
            for asset in join["local_asset_matches"][:4]:
                detail_lines.append(
                    f"  - `{asset['id']}` `{asset['range']}` in `{asset['manifest']}` ({asset.get('category')})"
                )
        else:
            detail_lines.append("- Local asset/data range matches: none in checked-in asset manifests.")

        if join["local_contract_matches"]:
            detail_lines.append("- Local contract/note range matches:")
            for match in join["local_contract_matches"][:5]:
                label = f" `{match['label']}`" if match.get("label") else ""
                detail_lines.append(
                    f"  -{label} `{', '.join(match['ranges'])}` in `{match['path']}` line {match['line']}"
                )
        else:
            detail_lines.append("- Local contract/note range matches: none found.")

        if join["source_scaffold_matches"]:
            detail_lines.append("- Source scaffold candidates:")
            for match in join["source_scaffold_matches"][:5]:
                hits = []
                if match["filename_token_hits"]:
                    hits.append("filename:" + ",".join(match["filename_token_hits"]))
                if match["address_hits"]:
                    hits.append(
                        "address-lines:" + ",".join(str(hit["line"]) for hit in match["address_hits"])
                    )
                detail_lines.append(f"  - `{match['path']}` ({'; '.join(hits)})")
        else:
            detail_lines.append("- Source scaffold candidates: none found by filename token or address search.")

        if join["note_matches"]:
            detail_lines.append("- Existing note anchors:")
            for match in join["note_matches"][:5]:
                detail_lines.append(f"  - `{match['path']}` line {match['line']}")
        else:
            detail_lines.append("- Existing note anchors: none found.")

        if join.get("warning"):
            detail_lines.append(f"- Warning: {join['warning']}")
        detail_lines.append("")

    return "\n".join(
        [
            "# CoilSnake Field Join Report",
            "",
            "Generated by `tools/build_coilsnake_field_join_report.py` from `manifests/coilsnake-crosswalk.json`.",
            "This note records offsets, ranges, and local anchors only; it does not contain ROM-derived payload bytes.",
            "",
            "## Summary",
            "",
            "| Experiment | CoilSnake file | Offset | HiROM | Local range | Source candidate | Join status | Warning |",
            "| --- | --- | --- | --- | --- | --- | --- | --- |",
            *rows,
            "",
            "## Interpretation Rules",
            "",
            "- Diff offsets are measured against `build/coilsnake/baseline-rebuild.sfc`, not the original 3 MiB ROM.",
            "- `diff-confirmed` means the CoilSnake edit/rebuild changed the reported span; runtime naming still needs local caller or source evidence.",
            "- A local range match whose vocabulary disagrees with the CoilSnake file is a relocation or compiler-normalization candidate, not a promoted runtime claim.",
            "",
            *detail_lines,
        ]
    ).rstrip() + "\n"


def build_report(crosswalk_path: Path, asset_manifest_dir: Path) -> dict[str, Any]:
    crosswalk = load_json(crosswalk_path)
    asset_entries = load_asset_entries(asset_manifest_dir)
    families = family_lookup(crosswalk)

    joins = [
        build_join(experiment_id, experiment, asset_entries, families)
        for experiment_id, experiment in sorted(crosswalk.get("controlled_experiments", {}).items())
    ]

    return {
        "schema": "earthbound-decomp.coilsnake-field-join-report.v1",
        "generated_by": "tools/build_coilsnake_field_join_report.py",
        "source_manifest": rel(crosswalk_path),
        "asset_manifest_dir": rel(asset_manifest_dir),
        "summary": {
            "experiment_count": len(joins),
            "diff_confirmed_count": sum(1 for join in joins if join.get("evidence_level") == "diff-confirmed"),
            "range_matched_count": sum(1 for join in joins if join.get("local_asset_matches")),
            "contract_range_matched_count": sum(1 for join in joins if join.get("local_contract_matches")),
            "source_candidate_count": sum(1 for join in joins if join.get("source_scaffold_matches")),
            "warning_count": sum(1 for join in joins if join.get("warning")),
        },
        "joins": joins,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Join CoilSnake edit/rebuild diff offsets to local ranges, source scaffolds, and notes."
    )
    parser.add_argument("--crosswalk", type=Path, default=DEFAULT_CROSSWALK)
    parser.add_argument("--asset-manifest-dir", type=Path, default=ROOT / "asset-manifests")
    parser.add_argument("--json-out", type=Path, default=DEFAULT_JSON_OUT)
    parser.add_argument("--markdown-out", type=Path, default=DEFAULT_MARKDOWN_OUT)
    args = parser.parse_args()

    crosswalk = args.crosswalk.resolve()
    asset_manifest_dir = args.asset_manifest_dir.resolve()
    if not crosswalk.is_file():
        print(f"Crosswalk manifest not found: {crosswalk}", file=sys.stderr)
        return 2
    if not asset_manifest_dir.is_dir():
        print(f"Asset manifest directory not found: {asset_manifest_dir}", file=sys.stderr)
        return 2

    report = build_report(crosswalk, asset_manifest_dir)

    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    args.markdown_out.parent.mkdir(parents=True, exist_ok=True)
    args.markdown_out.write_text(render_markdown(report), encoding="utf-8")

    print(f"Wrote {rel(args.json_out.resolve())}")
    print(f"Wrote {rel(args.markdown_out.resolve())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
