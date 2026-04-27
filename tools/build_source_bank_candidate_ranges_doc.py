from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent


def format_list(items: list[str]) -> list[str]:
    if not items:
        return ["- none"]
    return [f"- `{item}`" for item in items]


def render_manifest(bank: str, manifest: dict[str, Any]) -> str:
    summary = manifest["summary"]
    lines: list[str] = [
        f"# {bank} build-candidate byte ranges",
        "",
        "This manifest records source slices promoted into the reusable source-bank scaffold pipeline.",
        "",
        "## Summary",
        "",
        f"- ranges: `{summary['ranges']}`",
        f"- total bytes: `{summary['total_bytes']}`",
        f"- source bytes: `{summary['source_bytes']}`",
        f"- data gap bytes: `{summary['data_gap_bytes']}`",
        "",
        "## Ranges",
        "",
        "| Level | Source Path | Range | Span Bytes | Source Bytes | Data Gap Bytes | SHA-1 |",
        "| --- | --- | --- | ---: | ---: | ---: | --- |",
    ]

    for item in manifest["ranges"]:
        lines.append(
            "| `{level}` | `{source_path}` | `{start}..{end}` | {size} | {source_size} | {data_gap_size} | `{sha1}` |".format(
                **item
            )
        )

    lines.extend(["", "## Source Segments", ""])

    for item in manifest["ranges"]:
        lines.extend(
            [
                f"### `{item['source_path']}`",
                "",
                "| Range | Size | Name | SHA-1 |",
                "| --- | ---: | --- | --- |",
            ]
        )

        source_segments = item.get("source_segments", [])
        if source_segments:
            for segment in source_segments:
                lines.append(
                    "| `{start}..{end}` | {size} | `{name}` | `{sha1}` |".format(**segment)
                )
        else:
            lines.append("| n/a | 0 | `data-only protected span` | n/a |")

        data_gaps = item.get("data_gaps", [])
        if data_gaps:
            lines.extend(["", "Data gaps inside protected span:", ""])
            for gap in data_gaps:
                lines.append(
                    f"- `{gap['start']}..{gap['end']}` (`{gap['size']}` bytes, SHA-1 `{gap['sha1']}`) `{gap['name']}`"
                )

        lines.extend(["", "Labels:", ""])
        lines.extend(format_list(item.get("labels", [])))
        lines.extend(["", "Evidence:", ""])
        lines.extend(format_list(item.get("evidence", [])))
        lines.append("")

    lines.extend(
        [
            "## Notes",
            "",
            "The scaffold preserves intentional source-adjacent data gaps from the manifest and validates each protected span against the original ROM bytes.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bank", required=True, help="Bank id, for example C4")
    parser.add_argument(
        "--manifest",
        type=Path,
        help="Input build-candidate JSON manifest. Defaults to build/{bank}-build-candidate-ranges.json.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output markdown path. Defaults to notes/{bank}-build-candidate-ranges.md.",
    )
    args = parser.parse_args()

    bank = args.bank.upper()
    manifest_path = args.manifest or ROOT / "build" / f"{bank.lower()}-build-candidate-ranges.json"
    output_path = args.output or ROOT / "notes" / f"{bank.lower()}-build-candidate-ranges.md"

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    output_path.write_text(render_manifest(bank, manifest), encoding="utf-8", newline="\n")
    print(f"wrote {output_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
