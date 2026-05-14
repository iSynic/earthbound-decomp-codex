#!/usr/bin/env python3
"""Validate an ignored local C2 battle trace fixture config."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from run_c2_battle_trace_oracle_mesen import WRAM_PATCH_PROFILES, normalize_wram_patch


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_FIXTURES = ROOT / "build" / "c2" / "battle-trace-oracles" / "local-fixtures.json"
DEFAULT_PACKET = ROOT / "manifests" / "c2-battle-trace-oracle-packet.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate C2 battle trace local fixture config.")
    parser.add_argument("fixtures", nargs="?", default=str(DEFAULT_FIXTURES))
    parser.add_argument("--packet", default=str(DEFAULT_PACKET))
    parser.add_argument("--allow-template-placeholders", action="store_true")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def looks_placeholder(value: str) -> bool:
    return value.startswith("<") and value.endswith(">")


def validate_path(path_text: str, *, label: str, allow_placeholder: bool) -> None:
    require(isinstance(path_text, str) and path_text, f"{label} must be a non-empty string")
    if looks_placeholder(path_text):
        require(allow_placeholder, f"{label} is still a placeholder: {path_text}")
        return
    require(Path(path_text).is_file(), f"{label} not found: {path_text}")


def validate_optional_path(path_text: Any, *, label: str, allow_placeholder: bool) -> None:
    if path_text is None:
        return
    validate_path(str(path_text), label=label, allow_placeholder=allow_placeholder)


def listish(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def validate(data: dict[str, Any], packet: dict[str, Any], *, allow_placeholders: bool) -> None:
    require(data.get("schema") == "earthbound-decomp.c2-battle-trace-local-fixtures.v1", "bad schema")
    validate_path(str(data.get("default_mesen_path", "")), label="default_mesen_path", allow_placeholder=allow_placeholders)
    validate_path(str(data.get("default_rom_path", "")), label="default_rom_path", allow_placeholder=allow_placeholders)
    jobs_by_oracle = {str(job.get("oracle_id")): job for job in packet.get("jobs", [])}
    fixtures = data.get("fixtures", [])
    require(isinstance(fixtures, list) and fixtures, "fixtures must be a non-empty list")
    ids: set[str] = set()
    for fixture in fixtures:
        fixture_id = str(fixture.get("id", ""))
        require(fixture_id, "fixture missing id")
        require(fixture_id not in ids, f"duplicate fixture id {fixture_id}")
        ids.add(fixture_id)
        role = fixture.get("role")
        require(
            role in {"battle_save_state", "fixture_rom_autostart"},
            f"{fixture_id}: role must be battle_save_state or fixture_rom_autostart",
        )
        if role == "battle_save_state":
            validate_path(
                str(fixture.get("save_state_path", "")),
                label=f"{fixture_id} save_state_path",
                allow_placeholder=allow_placeholders,
            )
        if role == "fixture_rom_autostart":
            validate_path(
                str(fixture.get("rom_path", "")),
                label=f"{fixture_id} rom_path",
                allow_placeholder=allow_placeholders,
            )
            validate_optional_path(
                fixture.get("save_state_path"),
                label=f"{fixture_id} optional save_state_path",
                allow_placeholder=allow_placeholders,
            )
        oracle_ids = fixture.get("oracle_ids", [])
        require(isinstance(oracle_ids, list) and oracle_ids, f"{fixture_id}: oracle_ids must be non-empty")
        for oracle_id in oracle_ids:
            require(str(oracle_id) in jobs_by_oracle, f"{fixture_id}: unknown oracle id {oracle_id}")
        input_pattern = fixture.get("input_pattern")
        if input_pattern is not None:
            require(isinstance(input_pattern, str) and input_pattern, f"{fixture_id}: input_pattern must be non-empty string")
        for patch in listish(fixture.get("wram_patches")):
            normalized = normalize_wram_patch(patch)
            require(":" in normalized, f"{fixture_id}: wram_patches entry must be address:bytes form")
            address, payload = normalized.split(":", 1)
            require(address.strip(), f"{fixture_id}: wram_patches entry missing address")
            require(payload.strip(), f"{fixture_id}: wram_patches entry missing bytes")
        for profile_id in listish(fixture.get("wram_patch_profiles")):
            require(
                str(profile_id) in WRAM_PATCH_PROFILES,
                f"{fixture_id}: unknown wram_patch_profiles entry {profile_id}",
            )
        timing = fixture.get("wram_patch_timing")
        if timing is not None:
            require(
                timing in {"initial", "first-breakpoint"},
                f"{fixture_id}: wram_patch_timing must be initial or first-breakpoint",
            )
        require(isinstance(fixture.get("notes", ""), str), f"{fixture_id}: notes must be a string")


def main() -> int:
    args = parse_args()
    data = load_json(Path(args.fixtures))
    packet = load_json(Path(args.packet))
    validate(data, packet, allow_placeholders=args.allow_template_placeholders)
    print(f"C2 battle trace local fixture config validation OK: {len(data['fixtures'])} fixtures")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
