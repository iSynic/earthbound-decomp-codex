from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import rom_tools


ROOT = Path(__file__).resolve().parent.parent


def bank_sequence(start: str, end: str) -> list[str]:
    start_int = int(start, 16)
    end_int = int(end, 16)
    return [f"{bank:02X}" for bank in range(start_int, end_int + 1)]


def load_manifest(bank: str) -> dict[str, object]:
    path = ROOT / "build" / f"asset-bank-{bank.lower()}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def summarize_gap_bytes(rom: bytes, gap: dict[str, object]) -> dict[str, object]:
    start = int(str(gap["file_start"]), 16)
    end = int(str(gap["file_end"]), 16)
    data = rom[start : end + 1]
    unique = sorted(set(data))
    summary: dict[str, object] = {
        "cpu_start": gap["cpu_start"],
        "cpu_end": gap["cpu_end"],
        "size": gap["size"],
        "unique_byte_count": len(unique),
    }
    if len(unique) == 1:
        summary["fill_byte"] = f"0x{unique[0]:02X}"
    else:
        summary["first_bytes"] = " ".join(f"{byte:02X}" for byte in data[:16])
        summary["last_bytes"] = " ".join(f"{byte:02X}" for byte in data[-16:])
    return summary


def build_summary(start: str, end: str, rom_path: Path | None) -> dict[str, object]:
    rom = rom_tools.load_rom(rom_path or rom_tools.find_rom(None))
    banks = []
    for bank in bank_sequence(start, end):
        manifest = load_manifest(bank)
        summary = manifest["summary"]
        assert isinstance(summary, dict)
        gaps = manifest["coverage_gaps"]
        assert isinstance(gaps, list)
        banks.append(
            {
                "bank": bank,
                "reference_bank": manifest["bank_index"],
                "binary_assets": summary["binary_assets"],
                "binary_asset_bytes": summary["binary_asset_bytes"],
                "table_includes": summary["table_includes"],
                "table_bytes": summary["table_bytes"],
                "coverage_gap_bytes": summary["coverage_gap_bytes"],
                "coverage_gaps": [summarize_gap_bytes(rom, gap) for gap in gaps],
            }
        )
    return {
        "schema": "earthbound-decomp.asset-bank-rollup.v1",
        "start_bank": start.upper(),
        "end_bank": end.upper(),
        "banks": banks,
        "totals": {
            "binary_assets": sum(int(bank["binary_assets"]) for bank in banks),
            "binary_asset_bytes": sum(int(bank["binary_asset_bytes"]) for bank in banks),
            "table_includes": sum(int(bank["table_includes"]) for bank in banks),
            "table_bytes": sum(int(bank["table_bytes"]) for bank in banks),
            "coverage_gap_bytes": sum(int(bank["coverage_gap_bytes"]) for bank in banks),
        },
    }


def render_markdown(summary: dict[str, object]) -> str:
    banks = summary["banks"]
    totals = summary["totals"]
    assert isinstance(banks, list)
    assert isinstance(totals, dict)
    lines = [
        f"# Asset Bank Rollup {summary['start_bank']}-{summary['end_bank']}",
        "",
        "| Bank | Ref | Binary assets | Binary bytes | Table includes | Table bytes | Gap bytes | Gap notes |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for bank in banks:
        assert isinstance(bank, dict)
        gap_notes = []
        gaps = bank["coverage_gaps"]
        assert isinstance(gaps, list)
        for gap in gaps:
            assert isinstance(gap, dict)
            if gap.get("fill_byte") is not None:
                gap_notes.append(f"`{gap['cpu_start']}..{gap['cpu_end']}` fill {gap['fill_byte']}")
            else:
                gap_notes.append(f"`{gap['cpu_start']}..{gap['cpu_end']}` mixed")
        lines.append(
            "| `{bank}` | `{ref}` | {binary_assets} | {binary_bytes} | {table_includes} | {table_bytes} | {gap_bytes} | {gap_notes} |".format(
                bank=bank["bank"],
                ref=bank["reference_bank"],
                binary_assets=bank["binary_assets"],
                binary_bytes=bank["binary_asset_bytes"],
                table_includes=bank["table_includes"],
                table_bytes=bank["table_bytes"],
                gap_bytes=bank["coverage_gap_bytes"],
                gap_notes="<br>".join(gap_notes) or "-",
            )
        )
    lines.extend(
        [
            "",
            "## Totals",
            "",
            f"- binary assets: `{totals['binary_assets']}`",
            f"- binary asset bytes: `{totals['binary_asset_bytes']}`",
            f"- table includes: `{totals['table_includes']}`",
            f"- table bytes: `{totals['table_bytes']}`",
            f"- coverage gap bytes: `{totals['coverage_gap_bytes']}`",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Summarize generated asset bank manifests.")
    parser.add_argument("start_bank", help="Start bank, e.g. D5.")
    parser.add_argument("end_bank", help="End bank, e.g. EE.")
    parser.add_argument("--rom", help="Optional explicit ROM path.")
    parser.add_argument("--json-out", help="Output JSON path.")
    parser.add_argument("--markdown-out", help="Output Markdown path.")
    args = parser.parse_args()

    summary = build_summary(args.start_bank.upper(), args.end_bank.upper(), Path(args.rom) if args.rom else None)
    if args.json_out:
        json_path = Path(args.json_out)
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    if args.markdown_out:
        markdown_path = Path(args.markdown_out)
        markdown_path.parent.mkdir(parents=True, exist_ok=True)
        markdown_path.write_text(render_markdown(summary), encoding="utf-8")

    totals = summary["totals"]
    assert isinstance(totals, dict)
    print(
        f"{args.start_bank.upper()}-{args.end_bank.upper()}: "
        f"{totals['binary_assets']} binary assets, "
        f"{totals['binary_asset_bytes']} binary bytes, "
        f"{totals['table_bytes']} table bytes, "
        f"{totals['coverage_gap_bytes']} gap bytes"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
