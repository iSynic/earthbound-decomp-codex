#!/usr/bin/env python3
"""Build the source-backed 0xFF outside-VCMD proof lane."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DISPATCH = ROOT / "manifests" / "audio-spc700-driver-dispatch-frontier.json"
DEFAULT_CONTROL_READER = ROOT / "manifests" / "audio-spc700-control-reader-frontier.json"
DEFAULT_OUTPUT = ROOT / "manifests" / "audio-spc700-ff-target-review.json"
DEFAULT_NOTES = ROOT / "notes" / "audio-spc700-ff-target-review.md"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the SPC700 FF outside-VCMD proof lane.")
    parser.add_argument("--dispatch", default=str(DEFAULT_DISPATCH), help="SPC700 driver dispatch frontier JSON.")
    parser.add_argument("--control-reader", default=str(DEFAULT_CONTROL_READER), help="SPC700 control reader frontier JSON.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Manifest output JSON.")
    parser.add_argument("--notes", default=str(DEFAULT_NOTES), help="Markdown note output.")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def reader_records_for_ff(control_reader: dict[str, Any]) -> list[dict[str, Any]]:
    records = []
    for record in control_reader.get("reader_pcs", []):
        count = int(record.get("command_counts", {}).get("0xFF", 0))
        if count <= 0:
            continue
        records.append(
            {
                "pc": record.get("pc"),
                "source_label": record.get("source_label"),
                "driver_offset": record.get("driver_offset"),
                "read_count": count,
                "sample_reads": [
                    sample for sample in record.get("sample_reads", []) if sample.get("command") == "0xFF"
                ][:8],
            }
        )
    records.sort(key=lambda item: int(item["read_count"]), reverse=True)
    return records


def build_review(dispatch: dict[str, Any], control_reader: dict[str, Any]) -> dict[str, Any]:
    high = dispatch["high_command_dispatch_candidate"]
    entries = high.get("entries", [])
    commands = [entry.get("command") for entry in entries]
    ff_readers = reader_records_for_ff(control_reader)
    ff_in_vcmd_table = "0xFF" in commands
    return {
        "schema": "earthbound-decomp.audio-spc700-ff-target-review.v1",
        "status": "ff_outside_source_backed_vcmd_table_reader_effect_pending",
        "references": [
            "manifests/audio-spc700-driver-dispatch-frontier.json",
            "manifests/audio-spc700-control-reader-frontier.json",
            "refs/earthbound-sounddriver-byte-perfect/main.asm",
            "https://sneslab.net/wiki/N-SPC_Engine",
        ],
        "dispatch_context": {
            "source_backed_table_base": high["table_base"],
            "source_backed_arg_length_table_base": high["arg_length_table_base"],
            "source_backed_command_range": high["command_range"],
            "source_backed_entry_count": len(entries),
            "ff_in_source_backed_vcmd_table": ff_in_vcmd_table,
            "source_role": "outside_vcmd_table",
        },
        "ff_review": {
            "command": "0xFF",
            "source_label": None,
            "source_target": None,
            "arg_length": None,
            "source_role": "outside_vcmd_table",
            "effect_proof_status": "outside_vcmd_table_reader_effect_pending",
            "duration_promotion_status": "blocked_pending_local_effect_proof",
            "reader_pc_records": ff_readers,
            "required_next_evidence": [
                "prove whether FF bytes are consumed as reachable EarthBound sequence control",
                "record reader PC, sequence pointer, voice slot, and branch/effect immediately after read",
                "classify each observation as unreachable padding, data-like table byte, or EarthBound-specific control effect",
                "keep public exact-duration promotion blocked until a local effect is proven",
            ],
        },
        "summary": {
            "ff_in_source_backed_vcmd_table": ff_in_vcmd_table,
            "source_backed_command_range": high["command_range"],
            "source_backed_entry_count": len(entries),
            "ff_reader_pc_count": len(ff_readers),
            "ff_runtime_read_count": sum(int(record["read_count"]) for record in ff_readers),
            "exact_duration_promotion_allowed": False,
            "semantic_status": "outside_vcmd_table_reader_effect_pending",
        },
        "findings": [
            "The checked-in byte-perfect source backs VCMD entries for 0xE0..0xFE only.",
            "0xFF has no source-backed VCMD label, target, or argument length.",
            "Runtime reader traces still observe FF bytes, so FF remains a focused reader-effect proof lane rather than a dispatch-table entry.",
        ],
        "next_work": [
            "trace reader PC 0x0957 FF observations and record the post-read effect",
            "classify observed FF bytes as unreachable/data-like or EarthBound-specific control behavior",
            "feed only locally proven FF effects back into sequence command semantics",
        ],
    }


def render_markdown(data: dict[str, Any]) -> str:
    summary = data["summary"]
    review = data["ff_review"]
    rows = [
        "| `{pc}` | `{label}` | `{offset}` | {reads} |".format(
            pc=record["pc"],
            label=record.get("source_label"),
            offset=record.get("driver_offset"),
            reads=record["read_count"],
        )
        for record in review["reader_pc_records"]
    ]
    return "\n".join(
        [
            "# Audio SPC700 FF Target Review",
            "",
            "Status: FF is outside the source-backed VCMD table; reader effect proof is still pending.",
            "",
            "## Summary",
            "",
            f"- FF in source-backed VCMD table: `{summary['ff_in_source_backed_vcmd_table']}`",
            f"- source-backed command range: `{summary['source_backed_command_range']}`",
            f"- source-backed VCMD entries: `{summary['source_backed_entry_count']}`",
            f"- FF reader PCs: `{summary['ff_reader_pc_count']}`",
            f"- FF runtime reads: `{summary['ff_runtime_read_count']}`",
            f"- exact-duration promotion allowed: `{summary['exact_duration_promotion_allowed']}`",
            f"- semantic status: `{summary['semantic_status']}`",
            "",
            "## Source Boundary",
            "",
            f"- source role: `{review['source_role']}`",
            f"- source label: `{review['source_label']}`",
            f"- source target: `{review['source_target']}`",
            f"- arg length: `{review['arg_length']}`",
            f"- effect proof status: `{review['effect_proof_status']}`",
            "",
            "## Reader PCs",
            "",
            "| Reader PC | Source label | Driver offset | FF reads |",
            "| --- | --- | --- | ---: |",
            *rows,
            "",
            "## Findings",
            "",
            *[f"- {finding}" for finding in data["findings"]],
            "",
            "## Next Work",
            "",
            *[f"- {item}" for item in data["next_work"]],
            "",
        ]
    )


def main() -> int:
    args = parse_args()
    data = build_review(load_json(Path(args.dispatch)), load_json(Path(args.control_reader)))
    output = Path(args.output)
    notes = Path(args.notes)
    output.parent.mkdir(parents=True, exist_ok=True)
    notes.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    notes.write_text(render_markdown(data), encoding="utf-8")
    print(
        "Built audio SPC700 FF target review: "
        f"outside VCMD table={not data['summary']['ff_in_source_backed_vcmd_table']}, "
        f"{data['summary']['ff_runtime_read_count']} reader reads"
    )
    print(f"Wrote {output}")
    print(f"Wrote {notes}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
