from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
SCHEMA = "earthbound-decomp.c3-mixed-source-split-plan.v1"
DEFAULT_SOURCE_MAP = ROOT / "build" / "c3-source-data-map.json"


@dataclass(frozen=True)
class SplitSlice:
    address: str
    start: int
    end: int
    size: int
    kind: str
    name: str
    extraction_class: str
    source_expectation: str


@dataclass(frozen=True)
class MixedRowSplit:
    address: str
    include: str
    start: int
    end: int
    size: int
    slices: tuple[SplitSlice, ...]


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def resolve_path(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def parse_address(address: str) -> int:
    return int(address.split(":", 1)[1], 16)


def format_address(value: int) -> str:
    return f"C3:{value:04X}"


def load_source_map(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def source_labels_by_address(source_map: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(label["address"]): label
        for label in source_map.get("supplemental_labels", [])
        if label.get("extraction_class") == "source-helper"
    }


def build_manifest(source_map_path: Path) -> dict[str, Any]:
    source_map = load_source_map(source_map_path)
    source_labels = source_labels_by_address(source_map)
    rows: list[MixedRowSplit] = []

    for row in source_map.get("include_rows", []):
        if row.get("extraction_class") != "mixed-data-source-row":
            continue
        address = str(row["address"])
        start = int(row["start"])
        size = int(row["size"])
        end = start + size

        embedded = [
            label
            for label in source_labels.values()
            if start < parse_address(str(label["address"])) < end
        ]
        embedded.sort(key=lambda label: parse_address(str(label["address"])))
        if not embedded:
            continue

        slices: list[SplitSlice] = []
        first_source_start = parse_address(str(embedded[0]["address"]))
        if first_source_start > start:
            slices.append(
                SplitSlice(
                    address=address,
                    start=start,
                    end=first_source_start,
                    size=first_source_start - start,
                    kind="leading-data",
                    name=f"{address.replace(':', '')}_LeadingData",
                    extraction_class="raw-or-named-data",
                    source_expectation="preserve as data before embedded source-helper labels",
                )
            )

        for index, label in enumerate(embedded):
            label_address = str(label["address"])
            label_start = parse_address(label_address)
            next_start = (
                parse_address(str(embedded[index + 1]["address"]))
                if index + 1 < len(embedded)
                else end
            )
            slices.append(
                SplitSlice(
                    address=label_address,
                    start=label_start,
                    end=next_start,
                    size=next_start - label_start,
                    kind="source-helper",
                    name=str(label.get("name") or ""),
                    extraction_class="source-helper",
                    source_expectation="emit as standalone ordinary 65816 source helper from mixed include row",
                )
            )

        rows.append(
            MixedRowSplit(
                address=address,
                include=str(row["path"]),
                start=start,
                end=end,
                size=size,
                slices=tuple(slices),
            )
        )

    rows.sort(key=lambda item: item.start)
    source_slice_addresses = sorted(
        slice.address
        for row in rows
        for slice in row.slices
        if slice.kind == "source-helper"
    )
    return {
        "schema": SCHEMA,
        "generated_by": "tools/build_c3_mixed_source_split_plan.py",
        "inputs": {"source_data_map": rel(source_map_path)},
        "summary": {
            "mixed_rows": len(rows),
            "slices": sum(len(row.slices) for row in rows),
            "source_helper_slices": len(source_slice_addresses),
            "source_helper_addresses": source_slice_addresses,
        },
        "mixed_rows": [asdict(row) for row in rows],
    }


def markdown_escape(text: str) -> str:
    return text.replace("|", "\\|")


def render_markdown(manifest: dict[str, Any]) -> str:
    summary = manifest["summary"]
    lines = [
        "# C3 mixed data/source split plan",
        "",
        "Generated from `build/c3-source-data-map.json`. This file is the mechanical carving plan for addressed data includes that contain embedded ordinary 65816 source helpers.",
        "",
        "## Summary",
        "",
        f"- schema: `{manifest['schema']}`",
        f"- mixed rows: `{summary['mixed_rows']}`",
        f"- total slices: `{summary['slices']}`",
        f"- source-helper slices: `{summary['source_helper_slices']}`",
        f"- source-helper addresses: `{summary['source_helper_addresses']}`",
        "",
        "## Rows",
        "",
    ]
    for row in manifest["mixed_rows"]:
        lines.extend(
            [
                f"### `{row['address']}` `{row['include']}`",
                "",
                f"- range: `{row['address']}..{format_address(int(row['end']))}`",
                f"- size: `0x{int(row['size']):X}`",
                "",
                "| Slice | Range | Size | Kind | Name | Extraction Expectation |",
                "| --- | --- | ---: | --- | --- | --- |",
            ]
        )
        for slice in row["slices"]:
            lines.append(
                "| `{address}` | `{start}..{end}` | `0x{size:X}` | `{kind}` | `{name}` | {expectation} |".format(
                    address=slice["address"],
                    start=format_address(int(slice["start"])),
                    end=format_address(int(slice["end"])),
                    size=int(slice["size"]),
                    kind=slice["kind"],
                    name=markdown_escape(str(slice["name"])),
                    expectation=markdown_escape(str(slice["source_expectation"])),
                )
            )
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build the C3 mixed data/source split plan.")
    parser.add_argument("--source-map", type=Path, default=DEFAULT_SOURCE_MAP)
    parser.add_argument("--json-out", type=Path, default=ROOT / "build" / "c3-mixed-source-split-plan.json")
    parser.add_argument("--markdown-out", type=Path, default=ROOT / "notes" / "c3-mixed-source-split-plan.md")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    source_map = resolve_path(args.source_map)
    manifest = build_manifest(source_map)

    json_out = resolve_path(args.json_out)
    json_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    markdown_out = resolve_path(args.markdown_out)
    markdown_out.parent.mkdir(parents=True, exist_ok=True)
    markdown_out.write_text(render_markdown(manifest), encoding="utf-8")
    print(
        f"Wrote {rel(json_out)} and {rel(markdown_out)} "
        f"({manifest['summary']['mixed_rows']} mixed rows, "
        f"{manifest['summary']['source_helper_slices']} source slices)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
