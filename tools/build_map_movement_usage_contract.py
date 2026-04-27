from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MAP_USAGE = ROOT / "notes" / "map-sprite-usage-contract.json"
DEFAULT_SCRIPT_POINTERS = (
    ROOT / "refs" / "ebsrc-main" / "ebsrc-main" / "src" / "data" / "events" / "script_pointers.asm"
)
DEFAULT_SCRIPT_DIR = ROOT / "refs" / "ebsrc-main" / "ebsrc-main" / "src" / "data" / "events" / "scripts"
DEFAULT_BANKCONFIG = ROOT / "refs" / "ebsrc-main" / "ebsrc-main" / "src" / "bankconfig" / "US" / "bank03.asm"
DEFAULT_C3_SOURCE_MAP = ROOT / "build" / "c3-source-data-map.json"
DEFAULT_JSON_OUT = ROOT / "notes" / "map-movement-usage-contract.json"
DEFAULT_MARKDOWN_OUT = ROOT / "notes" / "map-movement-usage-contract.md"
SCHEMA = "earthbound-decomp.map-movement-usage.v1"

POINTER_RE = re.compile(r"^\s*PTR3\s+([A-Za-z0-9_@.]+)\b")
LABEL_RE = re.compile(r"^\s*([A-Za-z0-9_@.]+):")
EVENT_OP_RE = re.compile(r"^\s*(EVENT_[A-Z0-9_]+)\b")
ADDRESS_RE = re.compile(r"\b(?:UNKNOWN_|REDIRECT_|DATA_|CODE_|NULL_)?(C[0-9A-F]{5})\b", re.IGNORECASE)
EVENT_REF_RE = re.compile(r"\b(EVENT_[0-9A-Z_]+)\b")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Join map object movement IDs to ebsrc event/actionscript pointer targets."
    )
    parser.add_argument("--map-usage", default=str(DEFAULT_MAP_USAGE))
    parser.add_argument("--script-pointers", default=str(DEFAULT_SCRIPT_POINTERS))
    parser.add_argument("--script-dir", default=str(DEFAULT_SCRIPT_DIR))
    parser.add_argument("--bankconfig", default=str(DEFAULT_BANKCONFIG))
    parser.add_argument("--c3-source-map", default=str(DEFAULT_C3_SOURCE_MAP))
    parser.add_argument("--json-out", default=str(DEFAULT_JSON_OUT))
    parser.add_argument("--markdown-out", default=str(DEFAULT_MARKDOWN_OUT))
    return parser.parse_args()


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def top_counts(counter: Counter[Any], limit: int = 8) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for value, count in counter.most_common(limit):
        rows.append({"value": value, "count": count})
    return rows


def parse_script_pointers(path: Path) -> list[dict[str, Any]]:
    pointers: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        match = POINTER_RE.match(line)
        if match is None:
            continue
        pointers.append(
            {
                "movement_id": len(pointers),
                "target_label": match.group(1),
                "source_line": line_number,
            }
        )
    return pointers


def address_key(text: str) -> str:
    match = ADDRESS_RE.search(text)
    if match is None:
        return ""
    flat = match.group(1).upper()
    return f"{flat[:2]}:{flat[2:]}"


def script_ids_from_path(path: str) -> list[int]:
    filename = Path(path).stem
    return [int(value) for value in re.findall(r"\d+", filename)]


def parse_expected_scripts_from_bankconfig(path: Path) -> dict[int, str]:
    expected_scripts: dict[int, str] = {}
    if not path.exists():
        return expected_scripts
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        match = re.search(r'"(data/events/scripts/[^"]+\.asm)"', line)
        if match is None:
            continue
        include_path = match.group(1)
        for script_id in script_ids_from_path(include_path):
            expected_scripts[script_id] = include_path
    return expected_scripts


def load_c3_source_map(path: Path) -> tuple[dict[str, dict[str, Any]], dict[int, str]]:
    if not path.exists():
        return {}, {}
    data = json.loads(path.read_text(encoding="utf-8"))
    names: dict[str, dict[str, Any]] = {}
    expected_scripts: dict[int, str] = {}
    for row in data.get("include_rows", []):
        include_path = str(row.get("path", ""))
        if include_path.startswith("data/events/scripts/"):
            for script_id in script_ids_from_path(include_path):
                expected_scripts[script_id] = include_path
        address = row.get("address")
        if not address:
            continue
        names[str(address)] = {
            "name": row.get("name"),
            "extraction_class": row.get("extraction_class"),
            "script_kind": row.get("script_kind"),
            "script_decode_status": row.get("script_decode_status"),
            "source": "c3-source-data-map.include_rows",
        }
    for row in data.get("supplemental_labels", []):
        address = row.get("address")
        if not address:
            continue
        names[str(address)] = {
            "name": row.get("name"),
            "extraction_class": row.get("extraction_class"),
            "script_kind": row.get("script_kind"),
            "script_decode_status": row.get("script_decode_status"),
            "source": "c3-source-data-map.supplemental_labels",
        }
    return names, expected_scripts


def parse_script_files(path: Path, c3_names: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    labels: dict[str, dict[str, Any]] = {}
    for script_path in sorted(path.glob("*.asm")):
        lines = script_path.read_text(encoding="utf-8", errors="ignore").splitlines()
        file_labels: list[str] = []
        ops: Counter[str] = Counter()
        refs: Counter[str] = Counter()
        event_refs: Counter[str] = Counter()
        for line in lines:
            label_match = LABEL_RE.match(line)
            if label_match is not None:
                file_labels.append(label_match.group(1))
                continue
            op_match = EVENT_OP_RE.match(line)
            if op_match is not None:
                ops[op_match.group(1)] += 1
            for address_match in ADDRESS_RE.finditer(line):
                flat = address_match.group(1).upper()
                refs[f"{flat[:2]}:{flat[2:]}"] += 1
            for event_match in EVENT_REF_RE.finditer(line):
                event_refs[event_match.group(1)] += 1
        reference_rows: list[dict[str, Any]] = []
        for address, count in refs.most_common():
            name_row = c3_names.get(address, {})
            reference_rows.append(
                {
                    "address": address,
                    "name": name_row.get("name"),
                    "extraction_class": name_row.get("extraction_class"),
                    "count": count,
                }
            )
        file_info = {
            "source_file": rel(script_path),
            "byte_length": script_path.stat().st_size,
            "labels": file_labels,
            "event_op_count": sum(ops.values()),
            "top_event_ops": top_counts(ops, 12),
            "referenced_c3_labels": reference_rows[:16],
            "referenced_event_labels": top_counts(event_refs, 12),
        }
        for label in file_labels:
            labels[label] = file_info
    return labels


def movement_bucket(script_info: dict[str, Any] | None) -> str:
    if not script_info:
        return "unresolved_pointer_target"
    ops = {row["value"] for row in script_info.get("top_event_ops", [])}
    refs = {
        str(row.get("name") or row.get("address"))
        for row in script_info.get("referenced_c3_labels", [])
        if row.get("name") or row.get("address")
    }
    if "EVENT_LOAD_DEBUG_CURSOR_GRAPHICS" in ops:
        return "debug_cursor_loop"
    if "EVENT_START_TASK" in ops:
        return "task_backed_actionscript"
    if "EVENT_SET_POSITION_CHANGE_CALLBACK" in ops:
        return "position_callback_movement"
    if "EVENT_SET_PHYSICS_CALLBACK" in ops:
        return "physics_callback_movement"
    if any("Random" in ref or "Wander" in ref for ref in refs):
        return "random_or_wander_movement"
    if "EVENT_SHORTJUMP" in ops or "EVENT_PAUSE" in ops:
        return "script_loop_or_wait"
    return "event_actionscript_payload"


def summarize_usage(
    map_usage: dict[str, Any],
    pointers: list[dict[str, Any]],
    labels: dict[str, dict[str, Any]],
    expected_scripts: dict[int, str],
) -> dict[str, Any]:
    pointer_by_id = {int(row["movement_id"]): row for row in pointers}
    movement_to_npcs: dict[int, list[dict[str, Any]]] = defaultdict(list)
    movement_to_placement_count: Counter[int] = Counter()
    for npc in map_usage["npc_configs"]:
        movement_id = int(npc["movement"])
        movement_to_npcs[movement_id].append(npc)
        movement_to_placement_count[movement_id] += int(npc.get("map_placement_count", 0))

    shared_pointer_ids: dict[str, list[int]] = defaultdict(list)
    for pointer in pointers:
        shared_pointer_ids[str(pointer["target_label"])].append(int(pointer["movement_id"]))

    rows: list[dict[str, Any]] = []
    for movement_id in sorted(movement_to_npcs):
        npcs = movement_to_npcs[movement_id]
        pointer = pointer_by_id.get(movement_id)
        target_label = str(pointer["target_label"]) if pointer else None
        script_info = labels.get(target_label or "")
        expected_script = expected_scripts.get(movement_id)
        source_status = "script_file_present" if script_info else "script_file_missing"
        if pointer is None:
            source_status = "missing_pointer"
        elif not expected_script and not script_info:
            source_status = "missing_script_reference"
        sprite_counter: Counter[str] = Counter()
        type_counter: Counter[str] = Counter()
        direction_counter: Counter[str] = Counter()
        event_flag_counter: Counter[str] = Counter()
        role_counter: Counter[str] = Counter()
        for npc in npcs:
            sprite_counter[str(npc.get("sprite_label", npc.get("sprite_id")))] += 1
            type_counter[str(npc.get("type"))] += 1
            direction_counter[str(npc.get("direction"))] += 1
            event_flag_counter[str(npc.get("event_flag"))] += 1
            role_counter[str(npc.get("role_resolution"))] += 1

        rows.append(
            {
                "movement_id": movement_id,
                "target_label": target_label,
                "script_pointer_line": pointer.get("source_line") if pointer else None,
                "source_file": script_info.get("source_file") if script_info else None,
                "expected_source_file": expected_script if expected_script and not script_info else None,
                "source_status": source_status,
                "byte_length": script_info.get("byte_length") if script_info else None,
                "behavior_bucket": movement_bucket(script_info),
                "shared_pointer_ids": shared_pointer_ids.get(target_label or "", []),
                "npc_config_count": len(npcs),
                "map_placement_count": movement_to_placement_count[movement_id],
                "npc_types": top_counts(type_counter),
                "directions": top_counts(direction_counter),
                "event_flags": top_counts(event_flag_counter),
                "sprite_role_resolutions": top_counts(role_counter),
                "top_sprites": top_counts(sprite_counter, 10),
                "example_npc_ids": [int(npc["npc_id"]) for npc in npcs[:16]],
                "event_op_count": script_info.get("event_op_count") if script_info else None,
                "top_event_ops": script_info.get("top_event_ops", []) if script_info else [],
                "referenced_c3_labels": script_info.get("referenced_c3_labels", []) if script_info else [],
                "referenced_event_labels": script_info.get("referenced_event_labels", []) if script_info else [],
            }
        )
    return {
        "movement_usage": rows,
        "pointer_by_id": pointer_by_id,
        "shared_pointer_ids": shared_pointer_ids,
    }


def build_contract(args: argparse.Namespace) -> dict[str, Any]:
    map_usage_path = Path(args.map_usage)
    script_pointers_path = Path(args.script_pointers)
    script_dir = Path(args.script_dir)
    bankconfig_path = Path(args.bankconfig)
    c3_source_map_path = Path(args.c3_source_map)

    map_usage = json.loads(map_usage_path.read_text(encoding="utf-8"))
    pointers = parse_script_pointers(script_pointers_path)
    c3_names, expected_from_source_map = load_c3_source_map(c3_source_map_path)
    expected_scripts = parse_expected_scripts_from_bankconfig(bankconfig_path)
    for script_id, include_path in expected_from_source_map.items():
        expected_scripts.setdefault(script_id, include_path)
    labels = parse_script_files(script_dir, c3_names)
    usage = summarize_usage(map_usage, pointers, labels, expected_scripts)
    rows = usage["movement_usage"]

    unresolved = [row for row in rows if row["source_file"] is None]
    expected_missing = [row for row in rows if row["source_status"] == "script_file_missing"]
    pointer_targets_used = {row["target_label"] for row in rows if row["target_label"]}
    repeated_targets_used = [
        {"target_label": label, "movement_ids": ids}
        for label, ids in sorted(usage["shared_pointer_ids"].items())
        if label in pointer_targets_used and len(ids) > 1
    ]
    bucket_counts = Counter(row["behavior_bucket"] for row in rows)
    placed_rows = [row for row in rows if row["map_placement_count"] > 0]

    return {
        "schema": SCHEMA,
        "title": "Map Movement Usage Contract",
        "generator": "tools/build_map_movement_usage_contract.py",
        "source_policy": "Reference-derived behavior join; no ROM-derived event payload bytes are committed.",
        "sources": {
            "map_usage": rel(map_usage_path),
            "script_pointers": rel(script_pointers_path),
            "script_dir": rel(script_dir),
            "bankconfig": rel(bankconfig_path),
            "c3_source_map": rel(c3_source_map_path),
        },
        "summary": {
            "npc_config_count": len(map_usage["npc_configs"]),
            "map_placement_count": len(map_usage["placements"]),
            "movement_pointer_count": len(pointers),
            "script_label_count": len(labels),
            "unique_movement_ids_in_npc_configs": len(rows),
            "unique_movement_ids_with_map_placements": len(placed_rows),
            "movement_ids_with_script_file": len(rows) - len(unresolved),
            "movement_ids_without_script_file": len(unresolved),
            "movement_ids_with_expected_missing_ref_file": len(expected_missing),
            "unique_pointer_targets_used": len(pointer_targets_used),
            "shared_pointer_targets_used": len(repeated_targets_used),
            "behavior_bucket_counts": dict(sorted(bucket_counts.items())),
            "top_movements_by_map_placement_count": [
                {
                    "movement_id": row["movement_id"],
                    "target_label": row["target_label"],
                    "source_file": row["source_file"],
                    "behavior_bucket": row["behavior_bucket"],
                    "npc_config_count": row["npc_config_count"],
                    "map_placement_count": row["map_placement_count"],
                    "top_sprites": row["top_sprites"][:3],
                }
                for row in sorted(rows, key=lambda item: (-item["map_placement_count"], item["movement_id"]))[:20]
            ],
            "unresolved_movement_ids": [row["movement_id"] for row in unresolved],
        },
        "movement_usage": rows,
        "shared_pointer_targets": repeated_targets_used,
    }


def write_markdown(contract: dict[str, Any], path: Path) -> None:
    summary = contract["summary"]
    lines = [
        "# Map Movement Usage Contract",
        "",
        "This reference-derived contract joins map object movement IDs to ebsrc event/actionscript pointers.",
        "It is the behavior-side companion to `notes/map-sprite-usage-contract.md`: the sprite contract",
        "answers what a placed NPC looks like, while this contract answers which event/actionscript payload",
        "drives that object's idle loop, physics callback, task startup, or scripted behavior.",
        "",
        "## Summary",
        "",
        f"- NPC config rows: `{summary['npc_config_count']}`",
        f"- map placements: `{summary['map_placement_count']}`",
        f"- event script pointer entries: `{summary['movement_pointer_count']}`",
        f"- script labels indexed from refs: `{summary['script_label_count']}`",
        f"- unique movement IDs used by NPC configs: `{summary['unique_movement_ids_in_npc_configs']}`",
        f"- unique movement IDs used by placed NPC configs: `{summary['unique_movement_ids_with_map_placements']}`",
        f"- movement IDs resolved to ebsrc script files: `{summary['movement_ids_with_script_file']}`",
        f"- movement IDs without script-file resolution: `{summary['movement_ids_without_script_file']}`",
        f"- movement IDs with expected but missing ref script files: `{summary['movement_ids_with_expected_missing_ref_file']}`",
        f"- unique pointer targets used: `{summary['unique_pointer_targets_used']}`",
        f"- shared pointer targets used: `{summary['shared_pointer_targets_used']}`",
        "",
        "## Behavior Buckets",
        "",
        "| Bucket | Movement IDs |",
        "| --- | ---: |",
    ]
    for bucket, count in summary["behavior_bucket_counts"].items():
        lines.append(f"| `{bucket}` | {count} |")

    lines.extend(
        [
            "",
            "## Top Movement IDs By Placement Count",
            "",
            "| Movement | Target | Bucket | NPC configs | Placements | Top sprites | Source file |",
            "| ---: | --- | --- | ---: | ---: | --- | --- |",
        ]
    )
    for row in summary["top_movements_by_map_placement_count"]:
        sprites = ", ".join(f"{item['value']} ({item['count']})" for item in row["top_sprites"])
        lines.append(
            "| {movement_id} | `{target_label}` | `{behavior_bucket}` | {npc_config_count} | "
            "{map_placement_count} | {sprites} | `{source_file}` |".format(
                movement_id=row["movement_id"],
                target_label=row["target_label"],
                behavior_bucket=row["behavior_bucket"],
                npc_config_count=row["npc_config_count"],
                map_placement_count=row["map_placement_count"],
                sprites=sprites,
                source_file=row["source_file"],
            )
        )

    shared_targets = contract["shared_pointer_targets"][:20]
    if shared_targets:
        lines.extend(
            [
                "",
                "## Shared Pointer Targets",
                "",
                "Some movement IDs deliberately point at the same script label. These are aliases in the",
                "NPC config movement field, not duplicate script bodies.",
                "",
                "| Target | Movement IDs |",
                "| --- | --- |",
            ]
        )
        for row in shared_targets:
            lines.append(f"| `{row['target_label']}` | `{', '.join(str(item) for item in row['movement_ids'])}` |")

    unresolved = summary["unresolved_movement_ids"]
    if unresolved:
        lines.extend(
            [
                "",
                "## Unresolved Movement IDs",
                "",
                "These movement IDs are used by NPC configs but did not resolve to a script file label in refs.",
                "",
                ", ".join(f"`{item}`" for item in unresolved),
            ]
        )

    lines.extend(
        [
            "",
            "## Machine-Readable Data",
            "",
            "The JSON contract records one row per used movement ID with target label, source file, behavior",
            "bucket, NPC/map placement counts, top sprites, event macro profile, referenced C3 labels, and",
            "example NPC config IDs.",
            "",
            f"- JSON: `{contract['sources'].get('json_out', 'notes/map-movement-usage-contract.json')}`",
            f"- generator: `{contract['generator']}`",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    contract = build_contract(args)
    json_out = Path(args.json_out)
    markdown_out = Path(args.markdown_out)
    contract["sources"]["json_out"] = rel(json_out)
    json_out.write_text(json.dumps(contract, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_markdown(contract, markdown_out)


if __name__ == "__main__":
    main()
