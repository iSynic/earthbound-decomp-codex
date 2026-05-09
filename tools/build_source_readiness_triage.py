from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class BankTriage:
    bank: str
    primary_mode: str
    readiness: str
    priority: int
    next_action: str
    blockers: tuple[str, ...]
    ready_regions: tuple[str, ...]
    note: str


def bank_sequence(start: str, end: str) -> list[str]:
    return [f"{bank:02X}" for bank in range(int(start, 16), int(end, 16) + 1)]


def note_path(bank: str) -> str:
    return f"notes/bank-{bank.lower()}-first-pass.md"


def entry(
    bank: str,
    primary_mode: str,
    readiness: str,
    priority: int,
    next_action: str,
    blockers: list[str] | None = None,
    ready_regions: list[str] | None = None,
) -> BankTriage:
    return BankTriage(
        bank=bank,
        primary_mode=primary_mode,
        readiness=readiness,
        priority=priority,
        next_action=next_action,
        blockers=tuple(blockers or ()),
        ready_regions=tuple(ready_regions or ()),
        note=note_path(bank),
    )


def build_triage() -> list[BankTriage]:
    rows: list[BankTriage] = [
        entry(
            "C0",
            "overworld/runtime source",
            "source-integration-ready",
            1,
            "Readable-source closure is complete; next C0 work is semantic naming/comment polish around entity/task, movement, interaction, collision, teleport, and PPU helper contracts.",
            ["large bank; semantic polish should happen by subsystem, not as one monolith"],
            ["entity/task runtime", "movement and interaction helpers", "teleport and transition helpers", "PPU/window utility helpers"],
        ),
        entry(
            "C1",
            "text/menu/UI source",
            "source-integration-ready",
            1,
            "The readable-source closure audit now counts C1 as decoded-asm closed; next C1 work should be semantic naming/comment polish and C2/C4/EF contract joins rather than corridor closure.",
            ["some final semantics depend on C2 battle internals and C4 renderer internals"],
            ["text engine and CCS command leaves", "inventory/equipment menus", "battle PSI/item selection", "file-select and text-input flows"],
        ),
        entry(
            "C2",
            "battle runtime source",
            "source-integration-ready",
            1,
            "Readable-source closure is complete; next C2 work is semantic naming/comment polish for target selection, action dispatch, status/affliction families, PSI common handlers, Final Prayer, and battle visual tails.",
            ["many class-2 action leaves still need final naming polish"],
            ["battle action dispatch", "status/resource effects", "PSI and item action families", "battle background/sprite/palette tails"],
        ),
        entry(
            "C3",
            "script/data/helper bank",
            "script-and-data-ready",
            2,
            "C3 has no unexplained raw follow-up frontier; next C3 work is event/actionscript opcode semantics, operand names, callback argument contracts, and source/script emission polish.",
            ["script payloads remain bytecode assets until the event/actionscript VM contract is richer"],
            ["movement and interaction tables", "title/cursor tile data", "battle visual tables", "window/text helper tail"],
        ),
        entry(
            "C4",
            "visual/render source",
            "source-integration-ready",
            1,
            "Promote C4 renderer-facing contracts one subsystem at a time: text tile staging, movement presentation, window/color HDMA, file-select/town-map rendering, and landing/Sound Stone presentation.",
            ["PPU/HDMA/color side effects need subsystem-level source comments"],
            ["text tile staging", "movement pulse presentation", "window and color HDMA helpers", "file-select/town-map/landing presentation"],
        ),
    ]

    for bank in bank_sequence("C5", "C7"):
        rows.append(
            entry(
                bank,
                "locale text bank",
                "text-script-ready",
                3,
                "Export locale text segments as text-script assets; defer deeper semantics unless the text command decoder reports unknown commands.",
                ["port-ready text requires text command VM semantics, not just segment boundaries"],
                ["locale text segments"],
            )
        )
    rows.append(
        entry(
            "C8",
            "text plus dictionary data",
            "text-script-ready",
            3,
            "Export locale text and split the compressed-text dictionary island as a named data asset.",
            ["dictionary data needs a tighter contract if text compression is reimplemented"],
            ["locale text segments", "compressed-text dictionary/pointer island"],
        )
    )
    rows.append(
        entry(
            "C9",
            "locale text bank",
            "text-script-ready",
            3,
            "Treat as structurally complete text; use it as a clean decoder regression case because it parses with zero unknown command starts.",
            ["port-ready text still depends on the text command VM"],
            ["locale text segments", "door/event-heavy text labels"],
        )
    )

    rows.extend(
        [
            entry(
                "CA",
                "battle background assets",
                "asset-and-table-ready",
                3,
                "Extract battle background graphics, arrangements, palettes, and pointer/config tables as asset source.",
                ["table names are structurally good but not all consumer-commented"],
                ["battle background graphics", "arrangements", "palettes", "pointer tables"],
            ),
            entry(
                "CB",
                "battle background assets",
                "asset-and-table-ready",
                3,
                "Extract battle background asset run plus battle-entry background layer table and audio tail.",
                ["battle-entry layer table deserves consumer comments"],
                ["battle background graphics/arrangements/palettes", "battle-entry layer table", "audio packs"],
            ),
            entry(
                "CC",
                "animation/PSI assets",
                "asset-and-table-ready",
                3,
                "Extract animation, PSI animation, palette, and generated pointer/config assets.",
                ["two generated PSI tables are bounded but should get exact contracts"],
                ["animation payloads", "PSI arrangements/graphics/palettes", "pointer/config tables"],
            ),
            entry(
                "CD",
                "battle sprite graphics",
                "asset-ready",
                4,
                "Emit the full-bank battle sprite payload run as binary/compressed graphics assets.",
                [],
                ["battle sprite graphics payloads"],
            ),
            entry(
                "CE",
                "battle/swirls/Sound Stone assets",
                "asset-and-table-ready",
                3,
                "Extract battle sprite tail, sprite pointer/palette tables, swirl data, Sound Stone graphics/palettes, and audio tail.",
                ["swirl/Sound Stone table consumers need comments before source polish"],
                ["battle sprites", "battle sprite pointers/palettes", "swirl data", "Sound Stone assets"],
            ),
            entry(
                "CF",
                "generated map data",
                "data-contract-ready",
                3,
                "Emit CF as exact generated map-data tables plus audio tail using `notes/cf-table-splits.md`, the CF sector-list/event-music contracts, the CF door-data payload contract, and the CF movement-trigger/event-music source-emission summaries.",
                ["remaining trigger selector gameplay labels are optional polish; source-emission tooling still needs to consume the promoted row artifacts and preserve type 5 no-op payload words as numeric values"],
                ["door pointers", "door lists", "event music", "sprite placement", "NPC config", "audio tail"],
            ),
        ]
    )

    rows.append(
        entry(
            "D0",
            "generated map/battle data",
            "data-contract-ready",
            3,
            "Emit D0 as exact generated map/battle tables plus audio tail using `notes/d0-table-splits.md`, the promoted D0 manifest contracts, `notes/d0-tile-event-contracts.md`, and `notes/d0-variable-list-contracts.md` for variable-list ownership, BTL entry distributions, and the unpointed battle-group gap.",
            ["source include generation still needs to consume the promoted D0 row artifacts and preserve the D0:D531..D0:D54C unpointed battle-group gap"],
            ["door pointers", "screen transitions", "tile events", "enemy placement", "battle entry pointers", "battle-group gap accounting", "audio tail"],
        )
    )
    for bank in bank_sequence("D1", "D4"):
        rows.append(
            entry(
                bank,
                "overworld sprite graphics",
                "asset-ready",
                4,
                "Emit overworld sprite graphics payloads as source assets; no code extraction needed.",
                [],
                ["overworld sprite graphics"],
            )
        )
    rows.append(
        entry(
            "D5",
            "sprite tail plus gameplay tables",
            "data-contract-ready",
            3,
            "Emit D5 as sprite assets plus exact table source includes using `notes/d5-table-splits.md`, the promoted D5 contracts, and `notes/d5-timed-delivery-row-contracts.md` for effective controller rows, selector coverage, pointer-bank/timer/speed distributions, and source-window byte ownership.",
            ["story-specific timed-delivery row labels remain optional; source include tooling should preserve the D5:F649 source window versus D5:F645 effective controller base and its 4/196/4 byte ownership model"],
            ["overworld sprite tail", "explicit zero pad", "exact D5 table splits", "promoted D5 data contracts", "timed-delivery controller rows", "timed-delivery source-window ownership"],
        )
    )
    rows.append(
        entry(
            "D6",
            "map tile data",
            "asset-ready",
            4,
            "Emit the complete map tile chunk bank as binary map assets.",
            [],
            ["map tile chunks"],
        )
    )
    rows.append(
        entry(
            "D7",
            "map tiles/palette/arrangement",
            "asset-and-table-ready",
            3,
            "Extract map tile chunks and use `notes/d7-sector-metadata-contracts.md` for the consumer-backed sector tables, source-emission rows, full value counts for bounded unresolved planes, and numeric-preserve context-word high bits.",
            ["two bounded D7 metadata planes and context-word high bits remain unnamed until caller evidence proves them; source emission should preserve them numerically"],
            ["map tile chunks", "consumer-backed sector metadata tables", "source-emission metadata planes", "bounded unresolved metadata planes", "compressed arrangement stream"],
        )
    )
    rows.append(
        entry(
            "D8",
            "map collision plus error/audio assets",
            "data-contract-ready",
            3,
            "Emit D8 as exact collision data, collision pointer tables, warning assets, and audio tail using `notes/d8-table-splits.md`, the central D8 collision contracts, and `notes/d8-collision-subrecord-contracts.md` for source-emission rows, pointer handling, value counts, and runtime-backed bit families.",
            ["low surface modifier gameplay labels remain optional; row shape, pointer ownership, value counts, and runtime mask roles are already contract-backed"],
            ["tile collision data", "20 collision pointer tables", "4x4 collision subrecords", "anti-piracy/faulty-game-pak assets", "audio pack"],
        )
    )

    for bank in ["D9", "DB", "DD", "DE"]:
        rows.append(
            entry(
                bank,
                "map/audio assets",
                "asset-ready",
                4,
                "Emit compressed map graphics/arrangement assets and audio packs as source assets.",
                [],
                ["map graphics or arrangement payloads", "audio pack"],
            )
        )
    rows.append(
        entry(
            "DA",
            "map arrangement/palette/audio assets",
            "asset-and-table-ready",
            3,
            "Extract arrangements and palettes using `notes/da-map-palette-subrecord-contracts.md` for the pointer/variant rows, metadata-word distributions, and script-side palette usage joins.",
            ["event-palette selector runtime dispatch semantics remain deferred"],
            ["compressed arrangements", "map palette pointer/variant rows", "metadata-word and script-usage summaries", "audio pack"],
        )
    )
    rows.append(
        entry(
            "DC",
            "map arrangement/music/audio data",
            "asset-and-table-ready",
            3,
            "Extract arrangements and audio packs, and use `notes/cf-event-music-context-contracts.md` for the CF/DC event-music source-emission rows, selector plane, full second-plane value counts, and numeric-preserve second-plane policy.",
            ["the second per-sector music byte plane and broader map_music option-list semantics remain intentionally unnamed without direct consumers; source emission should preserve the second plane numerically"],
            ["compressed arrangements", "consumer-backed event-music selector plane", "numeric-preserve second music byte plane", "audio packs"],
        )
    )
    rows.append(
        entry(
            "DF",
            "map graphics plus palette animation data",
            "asset-and-table-ready",
            3,
            "Extract tileset/animation graphics and landing palette-animation data using `notes/df-landing-palette-animation-contracts.md` for the pointer table, variable profile records, compressed payload rows, and zero-step/audio-boundary sentinel policy.",
            ["human-facing profile meanings remain optional; table/profile/payload source-emission rows are contract-backed"],
            ["tileset graphics", "animation graphics", "landing palette-animation source-emission rows", "zero-step sentinel boundary", "audio pack"],
        )
    )

    rows.extend(
        [
            entry(
                "E0",
                "UI/font/town-map/audio assets",
                "asset-and-table-ready",
                3,
                "Extract text-window graphics, fonts, town maps, and audio packs using `notes/ui-font-town-map-asset-contracts.md` for text-window source-emission rows, the E0 town-map graphics pointer table, and the SRAM save-template preserve policy.",
                ["reserved SRAM template blocks and per-palette-row presentation labels remain optional semantic polish; source emission should preserve them with the documented numeric policies"],
                ["text-window graphics", "font data", "SRAM save-template source row", "text-window/town-map source-emission rows", "town maps", "audio packs"],
            ),
            entry(
                "E1",
                "text/font/intro/ending/town-map assets",
                "asset-and-table-ready",
                3,
                "Extract flyover text, font, intro/title/ending/cast/town-map assets using `notes/ui-font-town-map-asset-contracts.md` for E1 town-map descriptor/pointer/blink/variable-list rows, title palette/OAM source rows, and landing/cast bundle rows.",
                ["flyover, photographer, cast-formatting, credits-adjacent, public scene labels, and remaining unknown table field names need caller evidence before promotion"],
                ["flyover text", "intro/title visual source rows", "ending cast visual source rows", "town-map labels/icons/variable lists", "audio pack"],
            ),
        ]
    )

    for bank in bank_sequence("E2", "E5"):
        rows.append(
            entry(
                bank,
                "audio packs",
                "asset-ready",
                5,
                "Emit audio packs as binary audio assets; no code extraction needed.",
                [],
                ["audio packs"],
            )
        )
    rows.append(
        entry(
            "E6",
            "audio pack assembly",
            "asset-and-table-ready",
            4,
            "Preserve the hand-authored AUDIO_PACK_1 assembly block and emit the remaining packs as audio assets.",
            ["custom inline audio pack block should not be flattened blindly"],
            ["custom AUDIO_PACK_1 block", "audio packs"],
        )
    )
    for bank in bank_sequence("E7", "ED"):
        rows.append(
            entry(
                bank,
                "audio packs",
                "asset-ready",
                5,
                "Emit audio packs as binary audio assets; no code extraction needed.",
                [],
                ["audio packs"],
            )
        )
    rows.append(
        entry(
            "EE",
            "audio packs plus empty tail",
            "asset-ready-with-tail-question",
            4,
            "Emit audio packs and decide whether the zero/unclaimed tail should be represented as explicit padding.",
            ["large EE tail is unclaimed/zero-filled and needs a policy decision"],
            ["audio packs", "zero/unclaimed tail"],
        )
    )
    rows.append(
        entry(
            "EF",
            "mixed save/map/text/debug source/data",
            "source-integration-ready",
            1,
            "Readable-source closure is complete; next EF work is semantic polish for save/SRAM, debug/menu routines, map tileset/sprite grouping tables, text/help script runs, glyph mask tables, and named late tail data.",
            ["large text run still needs stronger text/script semantics"],
            ["debug font/cursor graphics", "Sound Stone data", "PSI help text anchors", "glyph mask tables", "save helper family"],
        )
    )

    by_bank = {row.bank: row for row in rows}
    expected = bank_sequence("C0", "EF")
    missing = [bank for bank in expected if bank not in by_bank]
    extra = [bank for bank in by_bank if bank not in expected]
    if missing or extra:
        raise ValueError(f"Bad triage coverage; missing={missing}, extra={extra}")
    return [by_bank[bank] for bank in expected]


def validate_notes(rows: list[BankTriage]) -> list[str]:
    missing = []
    for row in rows:
        if not (ROOT / row.note).exists():
            missing.append(row.note)
    return missing


def row_to_json(row: BankTriage) -> dict[str, object]:
    data = asdict(row)
    data["blockers"] = list(row.blockers)
    data["ready_regions"] = list(row.ready_regions)
    return data


def build_payload(rows: list[BankTriage]) -> dict[str, object]:
    return {
        "schema": "earthbound-decomp.source-readiness-triage.v1",
        "coverage": {
            "start_bank": "C0",
            "end_bank": "EF",
            "banks": len(rows),
            "missing_first_pass_notes": validate_notes(rows),
        },
        "summary": {
            "by_readiness": dict(sorted(Counter(row.readiness for row in rows).items())),
            "by_primary_mode": dict(sorted(Counter(row.primary_mode for row in rows).items())),
            "by_priority": dict(sorted(Counter(str(row.priority) for row in rows).items())),
        },
        "banks": [row_to_json(row) for row in rows],
    }


def render_markdown(payload: dict[str, object]) -> str:
    rows = [BankTriage(**row) for row in payload["banks"]]  # type: ignore[arg-type]
    summary = payload["summary"]
    coverage = payload["coverage"]
    assert isinstance(summary, dict)
    assert isinstance(coverage, dict)

    lines: list[str] = [
        "# Source Readiness Triage",
        "",
        "Generated by `tools/build_source_readiness_triage.py` from the curated bank-readiness matrix and the first-pass wrapper notes.",
        "",
        "## Main result",
        "",
        f"- coverage: `{coverage['banks']} / 48` banks from `C0` through `EF`",
        f"- missing first-pass notes: `{len(coverage['missing_first_pass_notes'])}`",
        "- first semantic priorities: `C0`, `C1`, `C2`, `C4`, and `EF`",
        "- first bytecode/text priorities: C3 event/actionscript semantics and C5-C9 text-script export",
        "- readable source-bank closure status: `0` preserved source corridors in audited source-heavy banks",
        "- readable source-bank closure dashboard: `notes/readable-source-bank-closure.md`",
        "- restored ebsrc drift audit: `notes/ebsrc-restored-reference-drift-audit.md`",
        "",
        "## Readiness Counts",
        "",
        "| Readiness | Banks |",
        "| --- | ---: |",
    ]
    by_readiness = summary["by_readiness"]
    assert isinstance(by_readiness, dict)
    for readiness, count in by_readiness.items():
        lines.append(f"| `{readiness}` | {count} |")

    lines.extend(
        [
            "",
            "## Priority Queue",
            "",
            "| Priority | Banks | What this means |",
            "| ---: | --- | --- |",
        ]
    )
    rows_by_priority: dict[int, list[BankTriage]] = defaultdict(list)
    for row in rows:
        rows_by_priority[row.priority].append(row)
    meanings = {
        1: "Highest leverage for runtime semantic polish.",
        2: "Highest leverage for VM/data-contract polish.",
        3: "Structurally mapped data/text/asset work with useful table polish.",
        4: "Mostly asset emission or one policy decision.",
        5: "Closed audio-pack payload emission.",
    }
    for priority in sorted(rows_by_priority):
        banks = ", ".join(f"`{row.bank}`" for row in rows_by_priority[priority])
        lines.append(f"| {priority} | {banks} | {meanings[priority]} |")

    lines.extend(
        [
            "",
            "## Immediate Workstreams",
            "",
            "### Source and runtime semantics",
            "",
            "- `C0`: overworld/entity/task/movement/runtime contracts.",
            "- `C1`: text engine, CCS leaves, menus, battle front ends, file select.",
            "- `C2`: battle runtime, action dispatch, status/effect families, battle visuals.",
            "- `C4`: renderer, text tiles, HDMA/color/window helpers, movement presentation.",
            "- `EF`: save/SRAM, debug/menu routines, reusable late helpers, and text/data tails.",
            "",
            "### Data-contract splitters",
            "",
            "- `D5`, `CF`, `D0`, and `D8`: complete as first table splitters; CF trigger/door/event-music rows and trigger-type/event-music source-emission summaries, D0 tile-event and placement/battle variable lists, D5 timed-delivery controller rows/source-window ownership, and D8 collision rows/pointer/value-count summaries now have promoted subrecord semantics, with remaining work concentrated in source/data emission and optional gameplay labels.",
            "- `D7`, `DA`, `DC`, `DF`, `E0`, `E1`: D7, DA, DF, E0, and E1 now have promoted table/subrecord contracts; D7 includes source-emission rows and numeric-preserve policies for its unresolved planes/context high bits, DA has metadata-word and script-usage summaries for palette source emission, DF has landing palette-animation pointer/profile/payload rows plus the zero-step/audio-boundary sentinel policy, and E0/E1 carry source-emission rows for text-window palettes, town-map variable lists, title palette/OAM rows, landing/cast bundles, and SRAM template blocks. Remaining work is smaller inferred table/pointer contract polish.",
            "",
            "### Script, text, and VM assets",
            "",
            "- `C3`: source/data split is mapped; improve event/actionscript opcode semantics, operand names, and callback contracts.",
            "- `C5..C9`: text-script export and text command decoder regression corpus.",
            "- `EF`: split large help/battle/menu text run using D5/C1 consumers.",
            "",
            "### Raw asset emission",
            "",
            "- `CA..CE`: battle background, battle sprite, animation, PSI, swirl, and Sound Stone assets.",
            "- `D1..D4`: full-bank overworld sprite graphics slabs.",
            "- `D6..DF`: map tile, arrangement, graphics, palette, and audio payloads.",
            "- `E2..EE`: audio-pack banks; `EE` needs an explicit padding/tail policy.",
            "",
            "## Per-Bank Queue",
            "",
            "| Bank | Mode | Readiness | P | Next action | Blockers |",
            "| --- | --- | --- | ---: | --- | --- |",
        ]
    )
    for row in rows:
        blockers = "<br>".join(row.blockers) if row.blockers else "-"
        lines.append(
            f"| `{row.bank}` | {row.primary_mode} | `{row.readiness}` | {row.priority} | {row.next_action} | {blockers} |"
        )

    lines.extend(
        [
            "",
            "## How to use this",
            "",
            "Use this as the implementation queue, not as proof that a bank is semantically done. A bank marked `asset-ready` can be emitted as assets with little code archaeology. A bank marked `source-integration-ready` has readable source closure for the current phase, but still needs careful labels, comments, and tests/verification around side effects. A bank marked `data-contract-ready` needs format-specific table-reader or emitter polish before pretending it has row-level semantics.",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Build source-readiness triage artifacts for C0-EF.")
    parser.add_argument("--json-out", type=Path, default=ROOT / "build" / "source-readiness-triage.json")
    parser.add_argument("--markdown-out", type=Path, default=ROOT / "notes" / "source-readiness-triage.md")
    args = parser.parse_args()

    rows = build_triage()
    payload = build_payload(rows)
    missing = payload["coverage"]["missing_first_pass_notes"]  # type: ignore[index]
    if missing:
        raise SystemExit(f"Missing first-pass notes: {missing}")

    json_out = args.json_out if args.json_out.is_absolute() else ROOT / args.json_out
    markdown_out = args.markdown_out if args.markdown_out.is_absolute() else ROOT / args.markdown_out
    json_out.parent.mkdir(parents=True, exist_ok=True)
    markdown_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    markdown_out.write_text(render_markdown(payload), encoding="utf-8")
    print(f"Wrote {json_out.relative_to(ROOT).as_posix()} and {markdown_out.relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
