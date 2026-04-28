from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_JSON_OUT = ROOT / "build" / "swirl-sequence-bundle-contracts.json"
DEFAULT_MARKDOWN_OUT = ROOT / "notes" / "swirl-sequence-bundle-contracts.md"
CE_MANIFEST = ROOT / "asset-manifests" / "bank-ce-assets.json"
EBSRC_SWIRL_POINTERS = ROOT / "refs" / "ebsrc-main" / "ebsrc-main" / "src" / "data" / "battle" / "swirl_pointers.asm"
EBDECOMP_SWIRLS = ROOT / "refs" / "eb-decompile-4ef92" / "Swirls"
POINTER_BIN = ROOT / "build" / "assets" / "ce" / "tables" / "214_data_battle_swirl_pointers_asm.bin"
PRIMARY_BIN = ROOT / "build" / "assets" / "ce" / "tables" / "215_inline_swirl_primary_table.bin"


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def parse_range(range_text: str) -> tuple[int, int]:
    match = re.fullmatch(r"CE:([0-9A-F]{4})\.\.CE:([0-9A-F]{4,5})", range_text)
    if not match:
        raise ValueError(f"Expected a CE range, got {range_text!r}")
    return int(match.group(1), 16), int(match.group(2), 16)


def load_ce_assets() -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    manifest = json.loads(CE_MANIFEST.read_text(encoding="utf-8"))
    payloads: list[dict[str, Any]] = []
    tables: dict[str, dict[str, Any]] = {}
    for asset in manifest["assets"]:
        asset_id = str(asset["id"])
        if asset_id.startswith("asset.ce.swirl_data_"):
            index = int(asset_id.rsplit("_", 1)[1])
            source = asset["source"]
            start, end = parse_range(source["range"])
            payloads.append(
                {
                    "index": index,
                    "asset_id": asset_id,
                    "title": asset["title"],
                    "range": source["range"],
                    "start": start,
                    "end": end,
                    "bytes": int(source["bytes"]),
                    "sha1": source.get("sha1"),
                }
            )
        elif "swirl" in asset_id:
            tables[asset_id] = asset
    payloads.sort(key=lambda item: item["index"])
    expected = list(range(126))
    actual = [item["index"] for item in payloads]
    if actual != expected:
        raise ValueError(f"Expected SWIRL_DATA_0..125, got {actual[:3]}..{actual[-3:]}")
    return payloads, tables


def load_ebsrc_pointer_labels() -> list[int]:
    text = EBSRC_SWIRL_POINTERS.read_text(encoding="utf-8")
    labels = [int(match.group(1)) for match in re.finditer(r"SWIRL_DATA_(\d+)", text)]
    if labels != list(range(126)):
        raise ValueError("ebsrc SWIRL_POINTER_TABLE does not enumerate SWIRL_DATA_0..125 in order")
    return labels


def load_pointer_words(payloads: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not POINTER_BIN.exists():
        raise FileNotFoundError(f"Missing local pointer table bytes: {rel(POINTER_BIN)}")
    data = POINTER_BIN.read_bytes()
    if len(data) != 252:
        raise ValueError(f"Expected 252 pointer bytes, got {len(data)}")
    words = [int.from_bytes(data[offset : offset + 2], "little") for offset in range(0, len(data), 2)]
    rows = []
    for index, word in enumerate(words):
        payload = payloads[index]
        rows.append(
            {
                "index": index,
                "pointer_word": f"${word:04X}",
                "expected_asset_start": f"CE:{payload['start']:04X}",
                "matches_asset_start": word == payload["start"],
                "asset_id": payload["asset_id"],
            }
        )
    if not all(row["matches_asset_start"] for row in rows):
        bad = [row for row in rows if not row["matches_asset_start"]][:5]
        raise ValueError(f"Swirl pointer words do not match payload starts: {bad}")
    return rows


def load_primary_rows() -> list[dict[str, Any]]:
    if not PRIMARY_BIN.exists():
        raise FileNotFoundError(f"Missing local primary table bytes: {rel(PRIMARY_BIN)}")
    data = PRIMARY_BIN.read_bytes()
    if len(data) != 28:
        raise ValueError(f"Expected 28 primary-table bytes, got {len(data)}")
    rows = []
    for sequence_id in range(7):
        offset = sequence_id * 4
        speed, first_frame, frame_count, reserved = data[offset : offset + 4]
        last_frame = first_frame + frame_count - 1 if frame_count else None
        rows.append(
            {
                "sequence_id": sequence_id,
                "speed": speed,
                "first_payload_index": first_frame,
                "frame_count": frame_count,
                "last_payload_index": last_frame,
                "reserved": reserved,
                "raw_bytes": " ".join(f"{byte:02X}" for byte in data[offset : offset + 4]),
            }
        )
    if rows[0] != {
        "sequence_id": 0,
        "speed": 0,
        "first_payload_index": 0,
        "frame_count": 0,
        "last_payload_index": None,
        "reserved": 0,
        "raw_bytes": "00 00 00 00",
    }:
        raise ValueError(f"Unexpected null swirl row: {rows[0]}")
    if any(row["reserved"] != 0 for row in rows):
        raise ValueError("Expected every primary-table reserved byte to be zero")
    return rows


def load_swirl_yaml() -> dict[int, dict[str, int]]:
    path = EBDECOMP_SWIRLS / "swirls.yml"
    if not path.exists():
        raise FileNotFoundError(f"Missing EBDecomp swirl metadata: {rel(path)}")
    result: dict[int, dict[str, int]] = {}
    current: int | None = None
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        if not raw_line.strip():
            continue
        if not raw_line.startswith(" "):
            current = int(raw_line.rstrip(":"))
            result[current] = {}
            continue
        if current is None:
            raise ValueError(f"Property before swirl id in {rel(path)}: {raw_line!r}")
        key, value = raw_line.strip().split(":", 1)
        result[current][key] = int(value.strip())
    if sorted(result) != list(range(7)):
        raise ValueError(f"Expected EBDecomp swirl ids 0..6, got {sorted(result)}")
    return result


def count_ref_pngs() -> dict[int, int]:
    counts: dict[int, int] = {0: 0}
    for sequence_id in range(1, 7):
        group_dir = EBDECOMP_SWIRLS / str(sequence_id)
        if not group_dir.exists():
            raise FileNotFoundError(f"Missing EBDecomp swirl frame dir: {rel(group_dir)}")
        counts[sequence_id] = len(list(group_dir.glob("*.png")))
    return counts


def build_sequences(
    payloads: list[dict[str, Any]],
    primary_rows: list[dict[str, Any]],
    yaml_rows: dict[int, dict[str, int]],
    png_counts: dict[int, int],
) -> list[dict[str, Any]]:
    sequences: list[dict[str, Any]] = []
    covered: list[int] = []
    for row in primary_rows:
        sequence_id = row["sequence_id"]
        first = int(row["first_payload_index"])
        count = int(row["frame_count"])
        last = row["last_payload_index"]
        if count:
            payload_slice = payloads[first : first + count]
            if len(payload_slice) != count:
                raise ValueError(f"Sequence {sequence_id} extends beyond known payloads")
            payload_ids = [int(payload["index"]) for payload in payload_slice]
            if payload_ids != list(range(first, first + count)):
                raise ValueError(f"Sequence {sequence_id} is not a contiguous payload run")
            covered.extend(payload_ids)
            first_asset = payload_slice[0]["asset_id"]
            last_asset = payload_slice[-1]["asset_id"]
            first_range = payload_slice[0]["range"]
            last_range = payload_slice[-1]["range"]
            byte_total = sum(int(payload["bytes"]) for payload in payload_slice)
            byte_min = min(int(payload["bytes"]) for payload in payload_slice)
            byte_max = max(int(payload["bytes"]) for payload in payload_slice)
        else:
            payload_ids = []
            first_asset = last_asset = first_range = last_range = None
            byte_total = byte_min = byte_max = 0

        yaml_row = yaml_rows[sequence_id]
        png_count = png_counts[sequence_id]
        if row["speed"] != yaml_row["speed"] or count != yaml_row["frames"]:
            raise ValueError(
                f"Sequence {sequence_id} primary row does not match EBDecomp YAML: "
                f"{row} vs {yaml_row}"
            )
        if png_count != count:
            raise ValueError(f"Sequence {sequence_id} has {png_count} PNG refs but {count} table frames")

        sequences.append(
            {
                "sequence_id": sequence_id,
                "speed": row["speed"],
                "first_payload_index": first,
                "last_payload_index": last,
                "frame_count": count,
                "reserved": row["reserved"],
                "raw_primary_row": row["raw_bytes"],
                "payload_indices": payload_ids,
                "first_asset": first_asset,
                "last_asset": last_asset,
                "first_range": first_range,
                "last_range": last_range,
                "payload_bytes": byte_total,
                "payload_byte_min": byte_min,
                "payload_byte_max": byte_max,
                "ebdecomp_frames": yaml_row["frames"],
                "ebdecomp_speed": yaml_row["speed"],
                "ebdecomp_png_count": png_count,
            }
        )

    if sorted(covered) != list(range(126)):
        raise ValueError(f"Visible swirl sequences do not cover payloads 0..125 exactly: {covered[:5]}..")
    return sequences


def build_contract() -> dict[str, Any]:
    payloads, tables = load_ce_assets()
    pointer_labels = load_ebsrc_pointer_labels()
    pointer_rows = load_pointer_words(payloads)
    primary_rows = load_primary_rows()
    yaml_rows = load_swirl_yaml()
    png_counts = count_ref_pngs()
    sequences = build_sequences(payloads, primary_rows, yaml_rows, png_counts)

    table_summaries = []
    for table_id in sorted(tables):
        table = tables[table_id]
        source = table["source"]
        table_summaries.append(
            {
                "id": table_id,
                "title": table["title"],
                "range": source["range"],
                "bytes": int(source["bytes"]),
            }
        )

    return {
        "schema": "earthbound-decomp.swirl-sequence-bundle-contracts.v1",
        "scope": "CE SWIRL_DATA payloads, CE swirl pointer/primary tables, C2/C4 runtime evidence, and ignored EBDecomp rendered swirl refs",
        "inputs": {
            "ce_manifest": rel(CE_MANIFEST),
            "ebsrc_pointer_table": rel(EBSRC_SWIRL_POINTERS),
            "local_pointer_table_bytes": rel(POINTER_BIN),
            "local_primary_table_bytes": rel(PRIMARY_BIN),
            "ebdecomp_swirl_metadata": rel(EBDECOMP_SWIRLS / "swirls.yml"),
        },
        "generated_json": rel(DEFAULT_JSON_OUT),
        "tracked_markdown": rel(DEFAULT_MARKDOWN_OUT),
        "totals": {
            "payload_assets": len(payloads),
            "payload_bytes": sum(int(payload["bytes"]) for payload in payloads),
            "pointer_rows": len(pointer_rows),
            "primary_rows": len(primary_rows),
            "visible_sequences": len([sequence for sequence in sequences if sequence["frame_count"]]),
            "visible_frames": sum(int(sequence["frame_count"]) for sequence in sequences),
            "ebdecomp_png_refs": sum(png_counts.values()),
        },
        "validation": {
            "manifest_has_swirl_data_0_to_125": True,
            "ebsrc_pointer_labels_match_payload_order": pointer_labels == list(range(126)),
            "pointer_table_bytes_match_payload_starts": all(
                row["matches_asset_start"] for row in pointer_rows
            ),
            "primary_rows_partition_visible_payloads": True,
            "primary_rows_match_ebdecomp_frames_and_speed": True,
            "ebdecomp_png_counts_match_primary_rows": True,
        },
        "primary_row_shape": {
            "bytes_per_row": 4,
            "fields": ["speed", "first_payload_index", "frame_count", "reserved_zero"],
            "evidence": [
                "Rows 1..6 match EBDecomp swirls.yml speed/frame counts.",
                "The first/frame counts partition SWIRL_DATA_0..125 without overlap or gaps.",
                "The pointer-table words match each SWIRL_DATA payload start address.",
            ],
        },
        "tables": table_summaries,
        "sequences": sequences,
        "pointer_rows": pointer_rows,
        "runtime_context": [
            {
                "source": "notes/c2-psi-swirl-overlay-tail-c2e6b3-c2ea74.md",
                "role": "C2 overlay helpers start, poll, and close battle swirl overlay scripts while C4 callers select modes.",
            },
            {
                "source": "notes/file-select-entity-scripts-and-swirl-transition-c4d830-c4d989.md",
                "role": "C4 file-select/transition corridor corroborates overworld-facing swirl transition use.",
            },
        ],
        "open_questions": [
            "Promote sequence ids 1..6 to player-facing names only when caller-side mode names are corroborated.",
            "Decode the internal SWIRL_DATA payload bytecode/shape if a future renderer or editor needs native geometry instead of preserved raw payloads.",
            "Keep rendered EBDecomp PNG refs ignored; future local tooling can render previews from user-ROM-derived payloads.",
        ],
    }


def render_markdown(contract: dict[str, Any]) -> str:
    totals = contract["totals"]
    lines = [
        "# Swirl Sequence Bundle Contracts",
        "",
        "Generated by `tools/build_swirl_sequence_bundle_contracts.py`. This joins the checked-in CE manifest, ebsrc `SWIRL_POINTER_TABLE`, local user-ROM-derived table bytes, and ignored EBDecomp swirl metadata into one payload-free contract.",
        "",
        "No rendered swirl frames or ROM-derived payload bytes are checked in by this report.",
        "",
        "## Snapshot",
        "",
        f"- CE `SWIRL_DATA` payload assets: `{totals['payload_assets']}`",
        f"- CE `SWIRL_DATA` payload bytes: `{totals['payload_bytes']}`",
        f"- pointer-table rows: `{totals['pointer_rows']}`",
        f"- primary-table rows: `{totals['primary_rows']}`",
        f"- visible sequences: `{totals['visible_sequences']}`",
        f"- visible sequence frames: `{totals['visible_frames']}`",
        f"- ignored EBDecomp PNG refs checked: `{totals['ebdecomp_png_refs']}`",
        "",
        "## Validation",
        "",
    ]
    for key, value in contract["validation"].items():
        lines.append(f"- `{key}`: `{str(value).lower()}`")

    row_shape = contract["primary_row_shape"]
    lines.extend(
        [
            "",
            "## Primary Row Shape",
            "",
            f"- bytes per row: `{row_shape['bytes_per_row']}`",
            f"- inferred fields: {', '.join(f'`{field}`' for field in row_shape['fields'])}",
            "",
        ]
    )
    for evidence in row_shape["evidence"]:
        lines.append(f"- {evidence}")

    lines.extend(
        [
            "",
            "## Sequence Rows",
            "",
            "| Sequence | Speed | First payload | Last payload | Frames | Primary bytes | Payload bytes | EBDecomp PNGs | Asset span |",
            "| ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | --- |",
        ]
    )
    for sequence in contract["sequences"]:
        if sequence["frame_count"]:
            span = (
                f"`{sequence['first_asset']}` `{sequence['first_range']}` to "
                f"`{sequence['last_asset']}` `{sequence['last_range']}`"
            )
            last_payload = sequence["last_payload_index"]
        else:
            span = "null/disabled row"
            last_payload = "-"
        lines.append(
            "| {sequence_id} | {speed} | {first} | {last} | {frames} | `{raw}` | {bytes} | {pngs} | {span} |".format(
                sequence_id=sequence["sequence_id"],
                speed=sequence["speed"],
                first=sequence["first_payload_index"],
                last=last_payload,
                frames=sequence["frame_count"],
                raw=sequence["raw_primary_row"],
                bytes=sequence["payload_bytes"],
                pngs=sequence["ebdecomp_png_count"],
                span=span,
            )
        )

    lines.extend(["", "## Runtime Contract", ""])
    lines.append(
        "The portable contract is `swirl_sequence.N`: a sequence id selects one primary-table row, which gives playback speed, first CE `SWIRL_DATA` payload index, and frame count. Each frame index resolves through `SWIRL_POINTER_TABLE` to a raw `SWIRL_DATA_N` payload."
    )
    lines.append("")
    lines.append(
        "The primary table is now structurally understood well enough for ports and editors to preserve sequence identity and frame order. The internal `SWIRL_DATA` payload bytecode remains raw-preserved until a renderer needs to decode its drawing commands."
    )

    lines.extend(["", "## Runtime Evidence", ""])
    for item in contract["runtime_context"]:
        lines.append(f"- `{item['source']}`: {item['role']}")

    lines.extend(["", "## Tables", ""])
    lines.append("| Table | Range | Bytes |")
    lines.append("| --- | --- | ---: |")
    for table in contract["tables"]:
        lines.append(f"| `{table['id']}` ({table['title']}) | `{table['range']}` | {table['bytes']} |")

    lines.extend(["", "## Open Questions", ""])
    for question in contract["open_questions"]:
        lines.append(f"- {question}")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build CE swirl sequence bundle contracts.")
    parser.add_argument("--json-out", default=str(DEFAULT_JSON_OUT))
    parser.add_argument("--markdown-out", default=str(DEFAULT_MARKDOWN_OUT))
    args = parser.parse_args()

    contract = build_contract()
    json_out = Path(args.json_out)
    json_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(json.dumps(contract, indent=2) + "\n", encoding="utf-8")

    markdown_out = Path(args.markdown_out)
    markdown_out.parent.mkdir(parents=True, exist_ok=True)
    markdown_out.write_text(render_markdown(contract), encoding="utf-8")

    totals = contract["totals"]
    print(
        "swirl sequence bundles: "
        f"{totals['visible_sequences']} sequences, "
        f"{totals['visible_frames']} frames, "
        f"{totals['payload_assets']} payloads"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
