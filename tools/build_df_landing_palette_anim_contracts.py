from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from data_contracts import ContractField, DataContract, load_manifest


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_JSON_OUT = ROOT / "notes" / "df-landing-palette-animation-contracts.json"
DEFAULT_MARKDOWN_OUT = ROOT / "notes" / "df-landing-palette-animation-contracts.md"

PROFILE_RE = re.compile(r"^LANDING_PALETTE_ANIM_PROFILE_(\d+)$")
PAYLOAD_RE = re.compile(r"^LANDING_PALETTE_ANIM_PAYLOAD_(\d+)$")
DECOMPRESS_TARGET_RE = re.compile(r"decompresses\s+(DF:[0-9A-F]{4})", re.IGNORECASE)

EVIDENCE = [
    "build/data-contracts-c0-c4.json",
    "notes/bank-df-first-pass.md",
    "notes/landing-profile-cache-436e-4474.md",
    "src/c0/c0_023f_build_landing_profile_step_sequencer.asm",
    "src/c0/c0_030f_advance_landing_profile_step_sequencer.asm",
]


@dataclass(frozen=True)
class ProfileRow:
    profile: int
    address: str
    payload: str
    step_count: int
    profile_bytes: int
    status: str


@dataclass(frozen=True)
class PayloadRow:
    payload: int
    range: str
    bytes: int
    selected_by_profiles: list[int]


def contract_end(contract: DataContract) -> str:
    return str(contract.address.add(contract.stride * (contract.count or 1) - 1))


def contract_range(contract: DataContract) -> str:
    return f"{contract.address}..{contract_end(contract)}"


def require_field(contract: DataContract, field_name: str) -> ContractField:
    field = contract.field_named(field_name)
    if field is None:
        raise ValueError(f"{contract.id} is missing field {field_name}")
    return field


def profile_index(contract: DataContract) -> int | None:
    match = PROFILE_RE.match(contract.id)
    if match is None:
        return None
    return int(match.group(1))


def payload_index(contract: DataContract) -> int | None:
    match = PAYLOAD_RE.match(contract.id)
    if match is None:
        return None
    return int(match.group(1))


def profile_payload_target(contract: DataContract) -> str:
    match = DECOMPRESS_TARGET_RE.search(contract.note)
    if match is None:
        raise ValueError(f"{contract.id} note does not name a decompressed DF payload target")
    return match.group(1).upper()


def profile_step_count(contract: DataContract) -> int:
    require_field(contract, "compressed_palette_payload_pointer")
    require_field(contract, "step_count")
    field = contract.field_named("step_durations")
    return field.count if field is not None else 0


def collect_profiles(manifest) -> list[tuple[int, DataContract]]:
    rows = [(index, contract) for contract in manifest.contracts if (index := profile_index(contract)) is not None]
    rows.sort(key=lambda row: row[0])
    expected = list(range(31))
    actual = [index for index, _contract in rows]
    if actual != expected:
        raise ValueError(f"Expected landing palette profiles {expected}, found {actual}")
    return rows


def collect_payloads(manifest) -> list[tuple[int, DataContract]]:
    rows = [(index, contract) for contract in manifest.contracts if (index := payload_index(contract)) is not None]
    rows.sort(key=lambda row: row[0])
    expected = list(range(8))
    actual = [index for index, _contract in rows]
    if actual != expected:
        raise ValueError(f"Expected landing palette payloads {expected}, found {actual}")
    return rows


def build_payload(manifest_path: Path | None = None) -> dict[str, object]:
    manifest = load_manifest(manifest_path)
    pointer_table = manifest.require("LANDING_PALETTE_ANIM_PROFILE_POINTER_TABLE")
    profiles = collect_profiles(manifest)
    payloads = collect_payloads(manifest)

    if pointer_table.address.long != profiles[0][1].address.long - pointer_table.stride * 31:
        raise ValueError("Pointer table does not end immediately before the profile records")
    if pointer_table.count != 31:
        raise ValueError(f"Pointer table count should be 31, found {pointer_table.count}")

    profile_rows = []
    profile_target_by_index = {}
    for index, contract in profiles:
        target = profile_payload_target(contract)
        step_count = profile_step_count(contract)
        profile_target_by_index[index] = target
        profile_rows.append(
            ProfileRow(
                profile=index,
                address=str(contract.address),
                payload=target,
                step_count=step_count,
                profile_bytes=contract.stride,
                status="active-payload" if step_count else "empty-sentinel",
            )
        )

    payload_rows = []
    for index, contract in payloads:
        selected_by = [profile for profile, target in profile_target_by_index.items() if target == str(contract.address)]
        payload_rows.append(
            PayloadRow(
                payload=index,
                range=contract_range(contract),
                bytes=contract.stride,
                selected_by_profiles=selected_by,
            )
        )

    non_empty_profiles = [row for row in profile_rows if row.step_count]
    empty_profiles = [row for row in profile_rows if not row.step_count]
    payload_bytes = sum(row.bytes for row in payload_rows)
    profile_bytes = sum(row.profile_bytes for row in profile_rows)

    profile_start = profiles[0][1].address
    profile_end = profiles[-1][1].address.add(profiles[-1][1].stride - 1)
    payload_start = payloads[0][1].address
    payload_end = payloads[-1][1].address.add(payloads[-1][1].stride - 1)

    return {
        "schema": "earthbound-decomp.df-landing-palette-animation-contracts.v1",
        "source_manifest": str(manifest.path.relative_to(ROOT).as_posix()),
        "evidence": EVIDENCE,
        "summary": {
            "pointer_table": str(pointer_table.address),
            "pointer_count": pointer_table.count,
            "profile_count": len(profile_rows),
            "non_empty_profiles": len(non_empty_profiles),
            "empty_profiles": len(empty_profiles),
            "profile_span": f"{profile_start}..{profile_end}",
            "profile_bytes": profile_bytes,
            "payload_count": len(payload_rows),
            "payload_span": f"{payload_start}..{payload_end}",
            "payload_bytes": payload_bytes,
            "zero_step_sentinel": "DF:EC46",
            "step_counts": [row.step_count for row in profile_rows],
            "nonzero_step_bytes": sum(row.step_count for row in non_empty_profiles),
        },
        "record_shape": [
            {
                "offset": "0x00",
                "name": "compressed_palette_payload_pointer",
                "size": 4,
                "meaning": "C0:023F decompresses this payload to 7E:B800.",
            },
            {
                "offset": "0x04",
                "name": "step_count",
                "size": 1,
                "meaning": "Zero skips sequencer setup; otherwise bounds the C0:023F copy into $4460.",
            },
            {
                "offset": "0x05",
                "name": "step_durations",
                "size": "step_count",
                "meaning": "One-byte sequencer values copied into $4460 and consumed by C0:030F.",
            },
        ],
        "profiles": [asdict(row) for row in profile_rows],
        "payloads": [asdict(row) for row in payload_rows],
        "interpretation_boundary": [
            "C0:023F proves the far-pointer table, compressed payload pointer, step_count, and step_durations fields.",
            "C0:023F decompresses active payloads to 7E:B800, seeds $445C/$445E, and marks $4474 active.",
            "C0:030F consumes the $4460 sequencer values and advances the landing palette animation.",
            "DF:EC46 is the zero-step terminal sentinel used by empty profiles, not a named compressed payload here.",
            "Human-facing profile meanings and the decompressed palette-row format remain intentionally unnamed.",
        ],
    }


def format_profile_table(rows: list[dict[str, object]]) -> list[str]:
    lines = [
        "| Profile | Address | Payload | Step count | Profile bytes | Status |",
        "| ---: | --- | --- | ---: | ---: | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['profile']} | `{row['address']}` | `{row['payload']}` | {row['step_count']} | {row['profile_bytes']} | `{row['status']}` |"
        )
    return lines


def format_payload_table(rows: list[dict[str, object]]) -> list[str]:
    lines = [
        "| Payload | Range | Bytes | Selected by profiles |",
        "| ---: | --- | ---: | --- |",
    ]
    for row in rows:
        selected_by = ", ".join(str(item) for item in row["selected_by_profiles"]) or "-"
        lines.append(f"| {row['payload']} | `{row['range']}` | {row['bytes']} | {selected_by} |")
    return lines


def render_markdown(payload: dict[str, object]) -> str:
    summary = payload["summary"]
    assert isinstance(summary, dict)
    profiles = payload["profiles"]
    payloads = payload["payloads"]
    record_shape = payload["record_shape"]
    interpretation_boundary = payload["interpretation_boundary"]
    assert isinstance(profiles, list)
    assert isinstance(payloads, list)
    assert isinstance(record_shape, list)
    assert isinstance(interpretation_boundary, list)

    lines = [
        "# DF Landing Palette-Animation Contracts",
        "",
        "Generated by `tools/build_df_landing_palette_anim_contracts.py` from the central data-contract manifest and C0 landing-profile consumers.",
        "",
        "## Main result",
        "",
        f"- pointer table: `{summary['pointer_table']}`, `{summary['pointer_count']}` far pointers",
        f"- profile records: `{summary['profile_count']}` records across `{summary['profile_span']}`, `{summary['profile_bytes']}` bytes",
        f"- active profiles: `{summary['non_empty_profiles']}`; empty sentinel profiles: `{summary['empty_profiles']}`",
        f"- compressed payloads: `{summary['payload_count']}` payloads across `{summary['payload_span']}`, `{summary['payload_bytes']}` bytes",
        f"- zero-step sentinel: `{summary['zero_step_sentinel']}`",
        f"- nonzero step bytes copied into `$4460`: `{summary['nonzero_step_bytes']}`",
        "",
        "## Record shape",
        "",
        "| Offset | Field | Size | Consumer-backed meaning |",
        "| --- | --- | ---: | --- |",
    ]
    for field in record_shape:
        assert isinstance(field, dict)
        lines.append(f"| `{field['offset']}` | `{field['name']}` | {field['size']} | {field['meaning']} |")

    lines.extend(
        [
            "",
            "## Profile rows",
            "",
            *format_profile_table(profiles),
            "",
            "## Payload rows",
            "",
            *format_payload_table(payloads),
            "",
            "## Interpretation boundary",
            "",
        ]
    )
    for item in interpretation_boundary:
        lines.append(f"- {item}")

    lines.extend(
        [
            "",
            "## Evidence",
            "",
        ]
    )
    for path in payload["evidence"]:
        lines.append(f"- `{path}`")
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Build DF landing palette-animation contract notes.")
    parser.add_argument("--manifest", default=None, help="Data-contract manifest path")
    parser.add_argument("--json-out", default=str(DEFAULT_JSON_OUT))
    parser.add_argument("--markdown-out", default=str(DEFAULT_MARKDOWN_OUT))
    args = parser.parse_args()

    manifest_path = Path(args.manifest) if args.manifest else None
    payload = build_payload(manifest_path)

    json_out = Path(args.json_out)
    if not json_out.is_absolute():
        json_out = ROOT / json_out
    markdown_out = Path(args.markdown_out)
    if not markdown_out.is_absolute():
        markdown_out = ROOT / markdown_out

    json_out.parent.mkdir(parents=True, exist_ok=True)
    markdown_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    markdown_out.write_text(render_markdown(payload), encoding="utf-8")
    print(f"Wrote {json_out.relative_to(ROOT).as_posix()} and {markdown_out.relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
