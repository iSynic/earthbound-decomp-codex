#!/usr/bin/env python3
"""Build a focused FD/FE fast-forward timing proof frontier."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_COMMAND_SEMANTICS = ROOT / "manifests" / "audio-sequence-command-semantics.json"
DEFAULT_CONTROL_READER = ROOT / "manifests" / "audio-spc700-control-reader-frontier.json"
DEFAULT_OUTPUT = ROOT / "manifests" / "audio-fd-fe-timing-frontier.json"
DEFAULT_NOTES = ROOT / "notes" / "audio-fd-fe-timing-frontier.md"
COMMANDS = ("0xFD", "0xFE")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build FD/FE fast-forward timing frontier.")
    parser.add_argument("--command-semantics", default=str(DEFAULT_COMMAND_SEMANTICS), help="Command semantics JSON.")
    parser.add_argument("--control-reader", default=str(DEFAULT_CONTROL_READER), help="SPC700 control reader frontier JSON.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Manifest output JSON.")
    parser.add_argument("--notes", default=str(DEFAULT_NOTES), help="Markdown output.")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def reader_records(control_reader: dict[str, Any], command: str) -> list[dict[str, Any]]:
    records = []
    for record in control_reader.get("reader_pcs", []):
        count = int(record.get("command_counts", {}).get(command, 0))
        if count <= 0:
            continue
        records.append(
            {
                "pc": record.get("pc"),
                "source_label": record.get("source_label"),
                "driver_offset": record.get("driver_offset"),
                "read_count": count,
                "sample_reads": [
                    sample for sample in record.get("sample_reads", []) if sample.get("command") == command
                ][:8],
            }
        )
    records.sort(key=lambda item: int(item["read_count"]), reverse=True)
    return records


def build_frontier(command_semantics: dict[str, Any], control_reader: dict[str, Any]) -> dict[str, Any]:
    commands = command_semantics.get("commands", {})
    records = []
    for command in COMMANDS:
        semantic = commands.get(command, {})
        trace = semantic.get("trace_evidence", {})
        records.append(
            {
                "command": command,
                "source_label": semantic.get("source_label"),
                "source_target": semantic.get("source_target"),
                "arg_length": semantic.get("arg_length"),
                "source_role": semantic.get("source_role"),
                "effect_proof_status": semantic.get("effect_proof_status"),
                "duration_promotion_status": semantic.get("duration_promotion_status"),
                "exact_duration_promotion_allowed": bool(semantic.get("exact_duration_promotion_allowed")),
                "sequence_control_read_count": int(trace.get("sequence_control_read_count", 0)),
                "reader_pc_records": reader_records(control_reader, command),
                "required_next_evidence": [
                    "capture fast-forward flag/timer and tempo state before the command read",
                    "capture fast-forward flag/timer and tempo state after the command effect",
                    "record whether playback time advances, skips, or resumes through the affected phrase",
                    "keep exact duration blocked until local timing effects are proven for both FD and FE",
                ],
            }
        )
    return {
        "schema": "earthbound-decomp.audio-fd-fe-timing-frontier.v1",
        "status": "fd_fe_source_backed_timing_effect_pending",
        "references": [
            "manifests/audio-sequence-command-semantics.json",
            "manifests/audio-spc700-control-reader-frontier.json",
            "refs/earthbound-sounddriver-byte-perfect/main.asm",
            "refs/earthbound-sounddriver-byte-perfect/ram.asm",
        ],
        "summary": {
            "command_count": len(records),
            "source_backed_vcmd_count": sum(1 for record in records if record.get("source_role") == "source_backed_vcmd"),
            "runtime_read_count": sum(int(record["sequence_control_read_count"]) for record in records),
            "reader_pc_count": sum(len(record["reader_pc_records"]) for record in records),
            "exact_duration_promotion_allowed": False,
            "semantic_status": "fd_fe_timing_effects_unproven",
        },
        "commands": records,
        "promotion_policy": [
            "FD and FE have source-backed VCMD labels and zero argument bytes.",
            "Source labels identify the timing lane, but do not prove export duration math.",
            "Exact-duration export remains blocked until local runtime timing effects are captured.",
        ],
        "next_work": [
            "trace reader PCs 0x0847 and 0x0957 for FD/FE observations",
            "join traces to fast_forward_flag, mfx_fastforward_timer, and tempo restore state",
            "feed confirmed timing effects back into sequence-command semantics before duration promotion",
        ],
    }


def render_markdown(data: dict[str, Any]) -> str:
    summary = data["summary"]
    rows = [
        "| `{command}` | `{label}` | `{target}` | `{arg_length}` | `{proof}` | {reads} | {pcs} |".format(
            command=record["command"],
            label=record["source_label"],
            target=record["source_target"],
            arg_length=record["arg_length"],
            proof=record["effect_proof_status"],
            reads=record["sequence_control_read_count"],
            pcs=len(record["reader_pc_records"]),
        )
        for record in data["commands"]
    ]
    return "\n".join(
        [
            "# Audio FD/FE Timing Frontier",
            "",
            "Status: FD/FE are source-backed VCMDs, but fast-forward timing effects remain unproven.",
            "",
            "## Summary",
            "",
            f"- commands: `{summary['command_count']}`",
            f"- source-backed VCMDs: `{summary['source_backed_vcmd_count']}`",
            f"- runtime reads: `{summary['runtime_read_count']}`",
            f"- reader PC links: `{summary['reader_pc_count']}`",
            f"- exact-duration promotion allowed: `{summary['exact_duration_promotion_allowed']}`",
            f"- semantic status: `{summary['semantic_status']}`",
            "",
            "## Commands",
            "",
            "| Command | Source label | Source target | Arg bytes | Effect proof | Runtime reads | Reader PCs |",
            "| --- | --- | ---: | ---: | --- | ---: | ---: |",
            *rows,
            "",
            "## Promotion Policy",
            "",
            *[f"- {item}" for item in data["promotion_policy"]],
            "",
            "## Next Work",
            "",
            *[f"- {item}" for item in data["next_work"]],
            "",
        ]
    )


def main() -> int:
    args = parse_args()
    data = build_frontier(load_json(Path(args.command_semantics)), load_json(Path(args.control_reader)))
    output = Path(args.output)
    notes = Path(args.notes)
    output.parent.mkdir(parents=True, exist_ok=True)
    notes.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    notes.write_text(render_markdown(data), encoding="utf-8")
    print(
        "Built audio FD/FE timing frontier: "
        f"{data['summary']['runtime_read_count']} reads, promotion blocked"
    )
    print(f"Wrote {output}")
    print(f"Wrote {notes}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
