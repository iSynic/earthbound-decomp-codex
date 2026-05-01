# EF Runtime Semantic Polish Plan

Primary queue context: `notes/source-readiness-triage.md` and
`notes/project-status.md`.

## Current State

`EF` is byte-complete but still coarse. The handoff in
`notes/bank-ef-source-scaffold-handoff.md` describes the bank as exact source
corridors for mixed save/map/text/debug content, mostly explicit `db` source
blocks rather than decoded 65816 routines. The next work is to split and name
runtime-facing helpers and payloads only where consumers prove semantics.

## Subsystem Slices

- Save/SRAM helpers: SRAM signature, save block flags, checksum/save helpers,
  file-select save/load callers.
- Debug/menu runtime: debug sound menu, graphics state init, overlays, cursor
  tilemap data, color math reset.
- Map/text/glyph data corridors: map tileset/sprite grouping tables, text
  payload runs, glyph mask tables, menu option strings.
- Sound Stone and presentation tables: Sound Stone table data and late visual
  presentation payloads shared with C0/C4 landing or presentation notes.
- C1/C2 battle-text payload joins: EF substitution payloads and battle text
  data consumed by C1 display wrappers and C2 action result lanes.

## First Pass Order

1. Start with save/SRAM helpers because C1 file-select already supplies stable
   caller evidence.
2. Split debug/menu runtime after save helpers, keeping executable helpers
   separate from font/cursor/table payloads.
3. Map C1/C2 battle-text substitution payload joins before broad text-run
   decoding, so runtime consumers drive the first names.
4. Defer wide map/text/glyph corridor splitting until D5/C1 consumers or text
   script tooling need concrete source assets.
5. Promote Sound Stone and presentation tables with C0/C4 evidence, not as
   isolated EF data labels.

## Evidence Inputs

- `notes/bank-ef-source-scaffold-handoff.md`
- `notes/bank-ef-first-pass.md`
- `notes/bank-ef-asset-data-map.md`
- `notes/ef-readable-source-split-queue.md`
- `notes/sram-template-contracts.md`
- `notes/debug-menu-reachability-c0-c1-ef.md`
- `notes/c2-ef-battle-text-contract-workahead.md`

## Expected Outputs

- A split queue that distinguishes executable EF helpers from opaque data/text
  corridors before any source promotion.
- Save/SRAM and debug/menu contract notes with C1 caller names and byte ranges.
- Battle-text substitution payload notes tied to C1 display wrappers and C2
  action-table message lanes.
- Deferred text/data corridor tasks for D5/C1/text-script follow-up work.

## Validation

Future implementation passes should use:

```powershell
python tools\promote_asset_bank_to_source_scaffold.py EF
python tools\build_source_bank_scaffold.py --bank EF
python tools\validate_source_bank_byte_equivalence.py --bank EF --module all --combined --scaffold src\ef\bank_ef_helpers_asar.asm --strict
python tools\build_source_bank_candidate_ranges_doc.py --bank EF
python tools\build_source_bank_residual_map.py --bank EF
```

This planning pass does not split EF source corridors or regenerate the bank.

## Implementation Notes

- 2026-05-01: EF save/SRAM helper polish landed as byte-neutral source
  aliases/constants plus `notes/ef-save-sram-runtime-polish.md`. The promoted
  contracts name the 0x500-byte save-block layout, primary/backup save-slot
  pair sizing, checksum/complement fields, live game-state/party/event-flag
  copy spans, `$9F79` missing-save mask, `EF:05A6` missing-save slot bit masks,
  `$30:7FFE` SRAM integrity marker, and the C0 multiply helper used to scale
  slot and block indices into SRAM offsets.
- 2026-05-01: EF debug sound-menu controller polish landed as byte-neutral
  source aliases. The promoted contracts name the controller row/window
  scratch, `$0069/$006D` input masks, `$B54B/$B54D/$B54F` BGM/SE/effect
  selectors, `$B545` temporary BGM restore slot, row cursor writeback through
  `$0BCA`, and wrap ranges for the BGM, SE, and effect selector rows.
