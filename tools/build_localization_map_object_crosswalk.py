#!/usr/bin/env python3
"""Join recovered localization records to ROM-backed map objects.

This reads the ignored local localization metadata manifest and public-safe map
contracts, then writes an ignored detailed crosswalk plus a tracked structural
summary. The detailed JSON may contain recovered metadata values, so keep it in
build/.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import build_text_bank_manifest as text_manifest


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LOCALIZATION_MANIFEST = ROOT / "build" / "localization-script-metadata-records.json"
DEFAULT_MAP_OBJECTS = ROOT / "notes" / "map-object-bundles.json"
DEFAULT_YML = ROOT / "refs" / "ebsrc-main" / "ebsrc-main" / "earthbound.yml"
DEFAULT_JSON = ROOT / "build" / "localization-map-object-crosswalk.json"
DEFAULT_NOTE = ROOT / "notes" / "localization-map-object-crosswalk.md"
DEFAULT_BANKS = ["C5", "C6", "C7", "C8", "C9"]


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def normalize_cpu(value: str | None) -> str | None:
    if not value:
        return None
    text = value.strip()
    if not text or text in {"$0", "0", "0x0"}:
        return None
    text = text.removeprefix("$").removeprefix("0x").upper()
    if ":" in text:
        bank, offset = text.split(":", 1)
        return f"{bank.zfill(2)}:{offset.zfill(4)}"
    if len(text) >= 6:
        return f"{text[:2]}:{text[-4:]}"
    return text


def build_text_label_index(banks: list[str], yml_path: Path) -> dict[str, Any]:
    metas = text_manifest.parse_text_segment_meta(yml_path)
    labels = text_manifest.parse_rename_labels(yml_path)
    by_label: dict[str, dict[str, Any]] = {}
    by_cpu: dict[str, dict[str, Any]] = {}
    duplicate_labels: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for bank in banks:
        for include in text_manifest.parse_bank_includes(bank):
            meta = metas.get(include.name)
            if meta is None:
                continue
            for offset, label in labels.get(include.name, []):
                cpu = text_manifest.cpu_for_file_offset(meta.offset + offset)
                row = {
                    "bank": bank,
                    "segment": include.name,
                    "bank_segment": include.segment_group,
                    "offset": f"0x{offset:04X}",
                    "cpu": cpu,
                    "label": label,
                }
                if label in by_label:
                    duplicate_labels[label].append(row)
                else:
                    by_label[label] = row
                by_cpu[cpu.upper()] = row

    return {
        "by_label": by_label,
        "by_cpu": by_cpu,
        "duplicate_labels": dict(duplicate_labels),
    }


def record_key(record: dict[str, Any]) -> str:
    return f"{record['file']}#{record['ordinal']:04d}"


def build_crosswalk(
    localization: dict[str, Any],
    map_objects: dict[str, Any],
    text_index: dict[str, Any],
    localization_path: Path,
    map_objects_path: Path,
    yml_path: Path,
) -> dict[str, Any]:
    text_by_label = text_index["by_label"]
    text_by_cpu = text_index["by_cpu"]

    records_by_message: dict[str, list[dict[str, Any]]] = defaultdict(list)
    record_label_joins = []
    for record in localization["records"]:
        metadata = record["metadata"]
        message = metadata.get("Message") or record.get("entry_label") or ""
        if message and message != "0":
            records_by_message[message].append(record)
        joined_fields = {}
        for field in ("Message", "GoodsMessage", "CheckMessage"):
            label = metadata.get(field, "")
            if label and label != "0":
                joined_fields[field] = text_by_label.get(label)
        record_label_joins.append(
            {
                "record_key": record_key(record),
                "file": record["file"],
                "ordinal": record["ordinal"],
                "entry_label": record.get("entry_label", ""),
                "joined_fields": joined_fields,
            }
        )

    object_rows = []
    matched_objects = set()
    matched_record_keys = set()
    unmatched_text_labels = Counter()
    descriptor_movement_counts: dict[str, Counter[int]] = defaultdict(Counter)
    descriptor_bucket_counts: dict[str, Counter[str]] = defaultdict(Counter)
    movement_descriptor_counts: dict[int, Counter[str]] = defaultdict(Counter)

    for obj in map_objects["objects"]:
        interaction = obj["interaction"]
        behavior = obj["behavior"]
        text_slots = []
        object_matched = False
        for slot in ("text_pointer_1", "text_pointer_2"):
            cpu = normalize_cpu(interaction.get(slot))
            label_row = text_by_cpu.get(cpu) if cpu else None
            label = label_row["label"] if label_row else ""
            records = records_by_message.get(label, []) if label else []
            text_slots.append(
                {
                    "slot": slot,
                    "cpu": cpu,
                    "label": label,
                    "text_segment": label_row["segment"] if label_row else "",
                    "localization_record_keys": [record_key(record) for record in records],
                }
            )
            if records:
                object_matched = True
                for record in records:
                    key = record_key(record)
                    matched_record_keys.add(key)
                    descriptor = record["metadata"].get("ActionScript", "")
                    if descriptor:
                        movement_id = int(behavior["movement_id"])
                        descriptor_movement_counts[descriptor][movement_id] += 1
                        descriptor_bucket_counts[descriptor][behavior["behavior_bucket"]] += 1
                        movement_descriptor_counts[movement_id][descriptor] += 1
            elif label:
                unmatched_text_labels[label] += 1

        if object_matched:
            matched_objects.add(obj["object_id"])
        object_rows.append(
            {
                "object_id": obj["object_id"],
                "npc_id": obj["npc_id"],
                "sector": obj["sector"],
                "position": obj["position"],
                "sprite_label": obj["visual"]["sprite_label"],
                "movement_id": behavior["movement_id"],
                "movement_target": behavior["target_label"],
                "behavior_bucket": behavior["behavior_bucket"],
                "text_slots": text_slots,
            }
        )

    descriptor_summary = []
    for descriptor, movement_counts in descriptor_movement_counts.items():
        descriptor_summary.append(
            {
                "actionscript_descriptor": descriptor,
                "matched_objects": sum(movement_counts.values()),
                "movement_ids": [
                    {"movement_id": movement_id, "count": count}
                    for movement_id, count in movement_counts.most_common()
                ],
                "behavior_buckets": [
                    {"bucket": bucket, "count": count}
                    for bucket, count in descriptor_bucket_counts[descriptor].most_common()
                ],
            }
        )
    descriptor_summary.sort(key=lambda row: (-row["matched_objects"], row["actionscript_descriptor"]))

    movement_summary = []
    for movement_id, descriptor_counts in movement_descriptor_counts.items():
        movement_summary.append(
            {
                "movement_id": movement_id,
                "descriptors": [
                    {"actionscript_descriptor": descriptor, "count": count}
                    for descriptor, count in descriptor_counts.most_common()
                ],
            }
        )
    movement_summary.sort(key=lambda row: row["movement_id"])

    records_with_text_label = {
        record_key(record)
        for record in localization["records"]
        if (record["metadata"].get("Message") or "") in text_by_label
    }

    return {
        "sources": {
            "localization_manifest": str(localization_path.relative_to(ROOT)),
            "map_objects": str(map_objects_path.relative_to(ROOT)),
            "earthbound_yml": str(yml_path.relative_to(ROOT)),
        },
        "summary": {
            "localization_records": len(localization["records"]),
            "text_labels_indexed": len(text_by_label),
            "map_objects": len(map_objects["objects"]),
            "records_with_message_label_in_text_banks": len(records_with_text_label),
            "records_matched_to_map_object_text_pointer": len(matched_record_keys),
            "map_objects_matched_to_localization_record": len(matched_objects),
            "unique_actionscript_descriptors_matched": len(descriptor_summary),
            "text_labels_seen_on_objects_without_localization_record": len(unmatched_text_labels),
        },
        "duplicate_text_labels": text_index["duplicate_labels"],
        "record_label_joins": record_label_joins,
        "map_object_rows": object_rows,
        "actionscript_descriptor_summary": descriptor_summary,
        "movement_descriptor_summary": movement_summary,
        "unmatched_object_text_labels": [
            {"label": label, "object_pointer_count": count}
            for label, count in unmatched_text_labels.most_common(80)
        ],
    }


def write_note(crosswalk: dict[str, Any], note_path: Path) -> None:
    summary = crosswalk["summary"]
    movement_descriptor_rows = []
    for row in crosswalk["movement_descriptor_summary"]:
        total = sum(item["count"] for item in row["descriptors"])
        movement_descriptor_rows.append((total, len(row["descriptors"]), row["movement_id"]))
    movement_descriptor_rows.sort(reverse=True)

    lines = [
        "# Localization map-object crosswalk",
        "",
        "Generated by `tools/build_localization_map_object_crosswalk.py`.",
        "",
        "This note records only structural counts. The detailed generated JSON is",
        "`build/localization-map-object-crosswalk.json` and intentionally stays",
        "ignored because it contains recovered authoring metadata values.",
        "",
        "## Summary",
        "",
    ]
    for key, value in summary.items():
        lines.append(f"- {key.replace('_', ' ')}: `{value}`")

    lines.extend(
        [
            "",
            "## What This Joins",
            "",
            "- Recovered source `;@Message:` labels to ebsrc text-bank labels.",
            "- Map-object primary/secondary text pointers to those text labels.",
            "- Matched placed objects to local recovered metadata records.",
            "- Local `;@ActionScript:` behavior descriptors to ROM-backed movement IDs.",
            "",
            "## Safe Use",
            "",
            "- Use the ignored JSON for local naming and cross-checks.",
            "- Promote only derived names/counts/contracts into tracked public docs.",
            "- Treat descriptor-to-movement matches as evidence from text-pointer joins,",
            "  not as proof that every object using the same movement ID shares the same",
            "  semantic role.",
            "",
            "## Top Descriptor-Matched Movement IDs",
            "",
            "| Movement ID | Matched objects | Descriptor classes |",
            "| ---: | ---: | ---: |",
        ]
    )
    for total, descriptor_count, movement_id in movement_descriptor_rows[:12]:
        lines.append(f"| {movement_id} | {total} | {descriptor_count} |")

    lines.extend(
        [
            "",
            "## Top Object Text Labels Without Recovered Metadata Records",
            "",
            "These are usually reusable service/container/global text labels rather than",
            "NPC-style authoring records.",
            "",
            "| Label | Object pointer count |",
            "| --- | ---: |",
        ]
    )
    for row in crosswalk["unmatched_object_text_labels"][:16]:
        lines.append(f"| `{row['label']}` | {row['object_pointer_count']} |")
    lines.append("")

    note_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--localization-manifest", type=Path, default=DEFAULT_LOCALIZATION_MANIFEST)
    parser.add_argument("--map-objects", type=Path, default=DEFAULT_MAP_OBJECTS)
    parser.add_argument("--yml", type=Path, default=DEFAULT_YML)
    parser.add_argument("--banks", nargs="+", default=DEFAULT_BANKS)
    parser.add_argument("--json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--note", type=Path, default=DEFAULT_NOTE)
    args = parser.parse_args()

    localization = load_json(args.localization_manifest)
    map_objects = load_json(args.map_objects)
    text_index = build_text_label_index([bank.upper() for bank in args.banks], args.yml)
    crosswalk = build_crosswalk(
        localization,
        map_objects,
        text_index,
        args.localization_manifest,
        args.map_objects,
        args.yml,
    )

    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(crosswalk, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    write_note(crosswalk, args.note)

    print(f"wrote {args.json}")
    print(f"wrote {args.note}")
    print(
        "objects_matched={map_objects_matched_to_localization_record} "
        "records_matched={records_matched_to_map_object_text_pointer} "
        "descriptors={unique_actionscript_descriptors_matched}".format(**crosswalk["summary"])
    )


if __name__ == "__main__":
    main()
