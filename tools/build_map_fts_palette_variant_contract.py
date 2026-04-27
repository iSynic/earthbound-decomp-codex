from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from rom_tools import find_rom, hirom_to_file_offset, load_rom


ROOT = Path(__file__).resolve().parent.parent
REFS = ROOT / "refs" / "eb-decompile-4ef92"
DEFAULT_TILESET_DIR = REFS / "Tilesets"
DEFAULT_TILESET_BUNDLES = ROOT / "notes" / "map-tileset-bundles.json"
DEFAULT_PALETTE_MANIFEST = ROOT / "asset-manifests" / "bank-da-assets.json"
DEFAULT_JSON_OUT = ROOT / "notes" / "map-fts-palette-variant-contract.json"
DEFAULT_MARKDOWN_OUT = ROOT / "notes" / "map-fts-palette-variant-contract.md"
SCHEMA = "earthbound-decomp.map-fts-palette-variant-contract.v1"
BASE32_ALPHABET = "0123456789abcdefghijklmnopqrstuv"
ROW_RE = re.compile(r"^[0-9a-v]{290}$")
MAP_PALETTE_VARIANT_BYTES = 192
MAP_PALETTE_VARIANT_WORDS = MAP_PALETTE_VARIANT_BYTES // 2
MAP_PALETTE_SUBPALETTES = 6
MAP_PALETTE_SUBPALETTE_COLORS = 16
RESERVED_WORDS = {
    0: "event_flag",
    16: "event_palette_selector_word",
    32: "sprite_palette",
    48: "flash_effect",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Verify the EBDecomp .fts 290-character rows as map palette "
            "variant visual payloads."
        )
    )
    parser.add_argument("--tileset-dir", default=str(DEFAULT_TILESET_DIR))
    parser.add_argument("--tileset-bundles", default=str(DEFAULT_TILESET_BUNDLES))
    parser.add_argument("--palette-manifest", default=str(DEFAULT_PALETTE_MANIFEST))
    parser.add_argument("--rom", help="EarthBound US ROM path.")
    parser.add_argument("--json-out", default=str(DEFAULT_JSON_OUT))
    parser.add_argument("--markdown-out", default=str(DEFAULT_MARKDOWN_OUT))
    return parser.parse_args()


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def sha1_bytes(data: bytes) -> str:
    return hashlib.sha1(data).hexdigest()


def sha1_text(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


def base32_value(text: str) -> int:
    value = 0
    for char in text:
        if char not in BASE32_ALPHABET:
            raise ValueError(f"Not a map base32 character: {char!r}")
        value = value * 32 + BASE32_ALPHABET.index(char)
    return value


def base32_digit(value: int) -> str:
    if not 0 <= value < len(BASE32_ALPHABET):
        raise ValueError(f"Value is outside one-character base32 domain: {value}")
    return BASE32_ALPHABET[value]


def parse_cpu_range_start(text: str) -> tuple[int, int]:
    start = text.split("..", 1)[0]
    bank_text, address_text = start.split(":", 1)
    return int(bank_text, 16), int(address_text, 16)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def extract_rows(path: Path) -> list[str]:
    rows = [
        line.strip().lower()
        for line in path.read_text(encoding="utf-8", errors="ignore").splitlines()
        if len(line.strip()) == 290
    ]
    bad = [row for row in rows if ROW_RE.fullmatch(row) is None]
    if bad:
        raise ValueError(f"{path} has non-base32-like 290-character rows")
    return rows


def load_fts_rows(tileset_dir: Path) -> dict[tuple[int, int], dict[str, Any]]:
    rows: dict[tuple[int, int], dict[str, Any]] = {}
    duplicates: list[str] = []
    for path in sorted(tileset_dir.glob("*.fts")):
        match = re.fullmatch(r"(\d{2})\.fts", path.name)
        owner_tileset_id = int(match.group(1)) if match else None
        for row in extract_rows(path):
            row_id = row[:2]
            key = (base32_value(row_id[0]), base32_value(row_id[1]))
            if key in rows:
                duplicates.append(row_id)
                continue
            rows[key] = {
                "row_id": row_id,
                "tileset_id": key[0],
                "variant": key[1],
                "expected_row_id": f"{base32_digit(key[0])}{base32_digit(key[1])}",
                "owner_fts": rel(path),
                "owner_fts_tileset_id": owner_tileset_id,
                "row_sha1": sha1_text(row),
                "payload_text_sha1": sha1_text(row[2:]),
                "payload": row[2:],
            }
    if duplicates:
        raise ValueError(f"Duplicate .fts palette row IDs: {', '.join(sorted(duplicates))}")
    return rows


def decode_palette_payload(payload: str) -> bytes:
    if len(payload) != MAP_PALETTE_VARIANT_WORDS * 3:
        raise ValueError(f"Palette payload has {len(payload)} chars, expected 288")
    if any(char not in BASE32_ALPHABET for char in payload):
        raise ValueError("Palette payload contains characters outside 0-v alphabet")

    out = bytearray()
    for index in range(0, len(payload), 3):
        triplet = payload[index : index + 3]
        word = (
            BASE32_ALPHABET.index(triplet[0])
            | (BASE32_ALPHABET.index(triplet[1]) << 5)
            | (BASE32_ALPHABET.index(triplet[2]) << 10)
        )
        out.extend((word & 0xFF, word >> 8))
    return bytes(out)


def words_from_bytes(data: bytes) -> list[int]:
    if len(data) % 2:
        raise ValueError("Palette data must have an even byte count")
    return [data[index] | (data[index + 1] << 8) for index in range(0, len(data), 2)]


def palette_assets_by_id(manifest: dict[str, Any]) -> dict[int, dict[str, Any]]:
    assets: dict[int, dict[str, Any]] = {}
    for asset in manifest["assets"]:
        title = str(asset["title"])
        if not title.startswith("MAP_DATA_PALETTE_"):
            continue
        palette_id = int(title.rsplit("_", 1)[1])
        source = asset["source"]
        bank, address = parse_cpu_range_start(str(source["range"]))
        assets[palette_id] = {
            "id": asset["id"],
            "title": title,
            "source_range": source["range"],
            "source_sha1": source["sha1"],
            "source_bytes": int(source["bytes"]),
            "bank": bank,
            "address": address,
            "variant_count": int(source["bytes"]) // MAP_PALETTE_VARIANT_BYTES,
            "variant_remainder_bytes": int(source["bytes"]) % MAP_PALETTE_VARIANT_BYTES,
            "raw_output": next(
                output["path"]
                for output in asset["outputs"]
                if output["kind"] == "raw"
            ),
        }
    return assets


def palette_settings_by_key(tileset_bundles: dict[str, Any]) -> dict[tuple[int, int], dict[str, Any]]:
    settings: dict[tuple[int, int], dict[str, Any]] = {}
    for tileset in tileset_bundles["tilesets"]:
        tileset_id = int(tileset["tileset_id"])
        for setting in tileset["palette_settings"]:
            key = (tileset_id, int(setting["variant"]))
            settings[key] = {
                **setting,
                "tileset_dependency": {
                    "tileset_id": tileset_id,
                    "sector_count": int(tileset.get("sector_count", 0)),
                    "has_direct_fts_export": bool(tileset.get("has_direct_fts_export", False)),
                    "dependency_status": tileset.get("dependency_status"),
                    "palette_setting_count": int(tileset.get("palette_setting_count", 0)),
                },
            }
    return settings


def read_palette_variant_bytes(
    asset: dict[str, Any],
    variant: int,
    rom_data: bytes,
) -> bytes:
    if int(asset["variant_remainder_bytes"]) != 0:
        raise ValueError(f"{asset['title']} is not a whole number of variants")
    if not 0 <= variant < int(asset["variant_count"]):
        raise ValueError(f"{asset['title']} has no variant {variant}")
    offset = hirom_to_file_offset(int(asset["bank"]), int(asset["address"]), len(rom_data))
    if offset is None:
        raise ValueError(f"{asset['source_range']} does not map to ROM data")
    start = offset + variant * MAP_PALETTE_VARIANT_BYTES
    return rom_data[start : start + MAP_PALETTE_VARIANT_BYTES]


def normalized_rom_variant(raw: bytes) -> bytes:
    normalized = bytearray(raw)
    for word_index in RESERVED_WORDS:
        byte_index = word_index * 2
        normalized[byte_index] = 0
        normalized[byte_index + 1] = 0
    return bytes(normalized)


def setting_word_checks(
    raw_words: list[int],
    row_words: list[int],
    setting: dict[str, Any],
) -> dict[str, Any]:
    checks = {
        "event_flag_word_matches_setting": raw_words[0] == int(setting.get("Event Flag", 0)),
        "sprite_palette_word_matches_setting": raw_words[32] == int(setting.get("Sprite Palette", 0)),
        "flash_effect_word_matches_setting": raw_words[48] == int(setting.get("Flash Effect", 0)),
        "event_palette_selector_word": raw_words[16],
        "event_palette_selector_present": raw_words[16] != 0,
        "event_palette_color_payload_present": bool(setting.get("Event Palette Colors")),
        "reserved_words_zeroed_in_fts": all(row_words[index] == 0 for index in RESERVED_WORDS),
    }
    checks["event_palette_selector_presence_matches_setting"] = (
        checks["event_palette_selector_present"]
        == checks["event_palette_color_payload_present"]
    )
    checks["metadata_words_match_settings"] = all(
        [
            checks["event_flag_word_matches_setting"],
            checks["sprite_palette_word_matches_setting"],
            checks["flash_effect_word_matches_setting"],
            checks["event_palette_selector_presence_matches_setting"],
        ]
    )
    return checks


def classify_row(
    row: dict[str, Any],
    setting: dict[str, Any],
    asset: dict[str, Any],
    rom_data: bytes,
) -> dict[str, Any]:
    decoded = decode_palette_payload(row["payload"])
    raw = read_palette_variant_bytes(asset, int(row["variant"]), rom_data)
    row_words = words_from_bytes(decoded)
    raw_words = words_from_bytes(raw)
    different_words = [index for index, pair in enumerate(zip(raw_words, row_words)) if pair[0] != pair[1]]
    reserved_different_words = [
        {
            "word_index": index,
            "role": RESERVED_WORDS[index],
            "rom_word": raw_words[index],
            "fts_word": row_words[index],
        }
        for index in different_words
        if index in RESERVED_WORDS
    ]
    unexpected_different_words = [index for index in different_words if index not in RESERVED_WORDS]
    checks = setting_word_checks(raw_words, row_words, setting)
    normalized = normalized_rom_variant(raw)
    exact_match = decoded == raw
    normalized_match = decoded == normalized
    if exact_match:
        status = "exact_rom_palette_variant_match"
    elif normalized_match and checks["metadata_words_match_settings"]:
        status = "matches_rom_variant_after_reserved_metadata_zeroing"
    else:
        status = "unexplained_mismatch"

    event_colors = setting.get("Event Palette Colors")
    event_palette_payload: dict[str, Any] | None = None
    if event_colors:
        event_bytes = decode_palette_payload(str(event_colors).lower())
        event_palette_payload = {
            "payload_text_sha1": sha1_text(str(event_colors).lower()),
            "decoded_payload_sha1": sha1_bytes(event_bytes),
            "word_count": len(event_bytes) // 2,
            "byte_count": len(event_bytes),
        }

    return {
        "row_id": row["row_id"],
        "tileset_id": int(row["tileset_id"]),
        "variant": int(row["variant"]),
        "expected_row_id": row["expected_row_id"],
        "owner_fts": row["owner_fts"],
        "owner_fts_tileset_id": row["owner_fts_tileset_id"],
        "row_sha1": row["row_sha1"],
        "payload_text_sha1": row["payload_text_sha1"],
        "decoded_visual_payload_sha1": sha1_bytes(decoded),
        "rom_variant_sha1": sha1_bytes(raw),
        "normalized_rom_visual_payload_sha1": sha1_bytes(normalized),
        "asset": {
            "id": asset["id"],
            "title": asset["title"],
            "source_range": asset["source_range"],
            "raw_output": asset["raw_output"],
        },
        "tileset_dependency": setting["tileset_dependency"],
        "setting_summary": {
            "event_flag": int(setting.get("Event Flag", 0)),
            "flash_effect": int(setting.get("Flash Effect", 0)),
            "sprite_palette": int(setting.get("Sprite Palette", 0)),
            "has_event_palette": bool(setting.get("has_event_palette", False)),
        },
        "event_palette_payload": event_palette_payload,
        "status": status,
        "exact_rom_palette_variant_match": exact_match,
        "normalized_rom_visual_payload_match": normalized_match,
        "different_word_count": len(different_words),
        "different_words_are_reserved_metadata": not unexpected_different_words,
        "reserved_different_words": reserved_different_words,
        "unexpected_different_word_indexes": unexpected_different_words,
        "setting_word_checks": checks,
    }


def build_contract(args: argparse.Namespace) -> dict[str, Any]:
    tileset_dir = Path(args.tileset_dir)
    tileset_bundles_path = Path(args.tileset_bundles)
    palette_manifest_path = Path(args.palette_manifest)
    rows = load_fts_rows(tileset_dir)
    bundles = load_json(tileset_bundles_path)
    settings = palette_settings_by_key(bundles)
    assets = palette_assets_by_id(load_json(palette_manifest_path))
    rom_data = load_rom(find_rom(args.rom))

    missing_settings = sorted(set(rows) - set(settings))
    settings_without_rows = sorted(set(settings) - set(rows))
    missing_assets = sorted(key for key in rows if key[0] not in assets)
    if missing_settings or settings_without_rows or missing_assets:
        raise ValueError(
            "Unable to build complete .fts palette contract: "
            f"rows missing settings={missing_settings[:8]}, "
            f"settings missing rows={settings_without_rows[:8]}, "
            f"rows missing assets={missing_assets[:8]}"
        )

    entries = [
        classify_row(rows[key], settings[key], assets[key[0]], rom_data)
        for key in sorted(rows)
    ]

    status_counts = Counter(entry["status"] for entry in entries)
    reserved_word_counts: dict[str, int] = defaultdict(int)
    for entry in entries:
        for diff in entry["reserved_different_words"]:
            reserved_word_counts[str(diff["role"])] += 1

    tilesets: list[dict[str, Any]] = []
    for tileset_id in sorted({entry["tileset_id"] for entry in entries}):
        group_entries = [entry for entry in entries if entry["tileset_id"] == tileset_id]
        owner_files = sorted({entry["owner_fts"] for entry in group_entries})
        dependency = group_entries[0]["tileset_dependency"]
        tilesets.append(
            {
                "tileset_id": tileset_id,
                "row_group": base32_digit(tileset_id),
                "owner_fts": owner_files,
                "variant_count": len(group_entries),
                "row_ids": [entry["row_id"] for entry in group_entries],
                "status_counts": dict(Counter(entry["status"] for entry in group_entries)),
                "sector_count": dependency["sector_count"],
                "dependency_status": dependency["dependency_status"],
                "has_direct_fts_export": dependency["has_direct_fts_export"],
            }
        )

    event_payloads = [entry for entry in entries if entry["event_palette_payload"] is not None]
    return {
        "schema": SCHEMA,
        "title": "Map FTS Palette Variant Contract",
        "generator": "tools/build_map_fts_palette_variant_contract.py",
        "source_policy": (
            "ROM-verified/reference-derived contract. This records row IDs, "
            "hashes, counts, and small metadata words only; it does not commit "
            "raw .fts rows or decoded 192-byte palette payload arrays."
        ),
        "sources": {
            "tileset_dir": rel(tileset_dir),
            "tileset_bundles": rel(tileset_bundles_path),
            "palette_manifest": rel(palette_manifest_path),
            "palette_settings_ref": "refs/eb-decompile-4ef92/map_palette_settings.yml",
        },
        "decoding_model": {
            "row_length_chars": 290,
            "row_id_chars": 2,
            "payload_chars": 288,
            "row_id_model": (
                "row_id[0] is the 0-v tileset/palette asset id; row_id[1] is "
                "the palette variant id."
            ),
            "payload_model": (
                "The payload is 96 SNES BGR555 words encoded as three 0-v "
                "base32-like characters per word, least-significant five-bit "
                "digit first."
            ),
            "payload_bytes": MAP_PALETTE_VARIANT_BYTES,
            "payload_words": MAP_PALETTE_VARIANT_WORDS,
            "subpalettes": MAP_PALETTE_SUBPALETTES,
            "colors_per_subpalette": MAP_PALETTE_SUBPALETTE_COLORS,
            "reserved_metadata_words": [
                {"word_index": index, "role": role}
                for index, role in RESERVED_WORDS.items()
            ],
            "normalization": (
                "Raw DA palette variants carry palette-setting metadata in "
                "reserved color-word slots 0, 16, 32, and 48. The .fts visual "
                "palette rows zero those reserved slots."
            ),
        },
        "summary": {
            "row_count": len(entries),
            "palette_setting_variant_count": len(settings),
            "row_key_matches_palette_setting_keys": len(entries),
            "tileset_id_domain": len(tilesets),
            "exact_rom_palette_variant_matches": status_counts["exact_rom_palette_variant_match"],
            "reserved_metadata_zeroed_matches": status_counts[
                "matches_rom_variant_after_reserved_metadata_zeroing"
            ],
            "unexplained_mismatches": status_counts["unexplained_mismatch"],
            "event_palette_payload_count": len(event_payloads),
            "event_palette_payload_shape_matches": sum(
                1
                for entry in event_payloads
                if entry["event_palette_payload"]["byte_count"] == MAP_PALETTE_VARIANT_BYTES
            ),
            "reserved_metadata_difference_counts": dict(sorted(reserved_word_counts.items())),
            "metadata_word_setting_mismatches": sum(
                1
                for entry in entries
                if not entry["setting_word_checks"]["metadata_words_match_settings"]
            ),
            "unexpected_different_word_rows": sum(
                1
                for entry in entries
                if entry["unexpected_different_word_indexes"]
            ),
        },
        "tilesets": tilesets,
        "entries": entries,
    }


def write_markdown(contract: dict[str, Any], path: Path) -> None:
    summary = contract["summary"]
    model = contract["decoding_model"]
    lines = [
        "# Map FTS Palette Variant Contract",
        "",
        "This contract resolves the 290-character variable rows in EBDecomp",
        "`.fts` exports as map palette variant rows. The earlier structural audit",
        "kept those rows opaque; this pass verifies their byte model against the",
        "bank DA `MAP_DATA_PALETTE_N` assets and `map_palette_settings.yml`.",
        "",
        "## Summary",
        "",
        f"- `.fts` palette rows: `{summary['row_count']}`",
        f"- matching palette-setting keys: `{summary['row_key_matches_palette_setting_keys']}`",
        f"- tileset/palette IDs covered: `{summary['tileset_id_domain']}`",
        f"- exact raw ROM palette variant matches: `{summary['exact_rom_palette_variant_matches']}`",
        f"- matches after reserved metadata zeroing: `{summary['reserved_metadata_zeroed_matches']}`",
        f"- unexplained mismatches: `{summary['unexplained_mismatches']}`",
        f"- event-palette override payloads referenced by settings: `{summary['event_palette_payload_count']}`",
        f"- event-palette payloads with 192-byte shape: `{summary['event_palette_payload_shape_matches']}`",
        f"- metadata-word/setting mismatches: `{summary['metadata_word_setting_mismatches']}`",
        "",
        "## Decoding Model",
        "",
        f"- row length: `{model['row_length_chars']}` characters",
        "- row ID: first two characters",
        "- payload: remaining `288` characters",
        f"- decoded payload: `{model['payload_words']}` SNES BGR555 words "
        f"(`{model['payload_bytes']}` bytes), arranged as `{model['subpalettes']}` "
        f"subpalettes of `{model['colors_per_subpalette']}` colors",
        "- encoding: three `0-v` characters per word, least-significant five-bit digit first",
        "- row ID model: `row_id[0] == tileset/palette asset id`, `row_id[1] == palette variant id`",
        "",
        "Raw DA palette variants include small setting fields in reserved color-word",
        "slots. The `.fts` rows are the visual palette payload with those slots",
        "zeroed. This explains every row that does not match the raw ROM bytes",
        "exactly.",
        "",
        "| Word Index | Role | Rows Differing From Raw ROM |",
        "| ---: | --- | ---: |",
    ]
    reserved_counts = summary["reserved_metadata_difference_counts"]
    for reserved in model["reserved_metadata_words"]:
        role = reserved["role"]
        lines.append(
            f"| {reserved['word_index']} | `{role}` | `{reserved_counts.get(role, 0)}` |"
        )
    lines.extend(
        [
            "",
            "## Per-Tileset Coverage",
            "",
            "| Tileset/Palette ID | Row Group | Variants | Owner `.fts` Export(s) | Status Counts | Sector Count | Dependency |",
            "| ---: | --- | ---: | --- | --- | ---: | --- |",
        ]
    )
    for row in contract["tilesets"]:
        status_counts = ", ".join(
            f"`{key}`:{value}" for key, value in sorted(row["status_counts"].items())
        )
        lines.append(
            f"| {row['tileset_id']} | `{row['row_group']}` | {row['variant_count']} | "
            f"`{', '.join(row['owner_fts'])}` | {status_counts} | "
            f"{row['sector_count']} | `{row['dependency_status']}` |"
        )
    lines.extend(
        [
            "",
            "## Interpretation Boundary",
            "",
            "This closes the `.fts` 290-row byte shape and ties it to the DA palette",
            "assets. Event-palette override color strings in `map_palette_settings.yml`",
            "are separate 192-byte-shaped payloads referenced by settings; they are",
            "not the base visual row stored inline in the `.fts` palette row.",
            "",
            "The map tile-animation runtime path remains documented separately in",
            "`notes/map-tile-animation-runtime-contract.md`.",
            "",
            "## Machine-Readable Data",
            "",
            "`notes/map-fts-palette-variant-contract.json` records one row per",
            "palette variant with row IDs, owner export, hashes, ROM asset identity,",
            "reserved metadata-word checks, and mismatch classification.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    contract = build_contract(args)
    json_path = Path(args.json_out)
    markdown_path = Path(args.markdown_out)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(contract, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_markdown(contract, markdown_path)
    print(f"Wrote {rel(json_path)} and {rel(markdown_path)}")


if __name__ == "__main__":
    main()
