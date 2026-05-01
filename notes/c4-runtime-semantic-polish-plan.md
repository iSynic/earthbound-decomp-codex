# C4 Runtime Semantic Polish Plan

Primary queue context: `notes/source-readiness-triage.md` and
`notes/project-status.md`.

## Current State

`C4` is fully source-backed for the scaffold phase. The handoff in
`notes/bank-c4-source-scaffold-handoff.md` reports byte-equivalence `OK`, while
also noting that many explicit data source blocks are intentionally coarse
asset/table stubs. The next work is renderer-facing semantic polish, not byte
closure.

## Subsystem Slices

- Text tile staging: text tile bitset allocation, glyph mask rendering, dirty
  range tracking, text tile transfer submission.
- Window/color/HDMA helpers: fixed-color math, WH0/WH2 HDMA channel setup,
  window range presets, color math modes, palette interpolation.
- Movement presentation: direction projection, live entity position rebasing,
  visual frame copy helpers, footprint tables.
- File-select and town-map rendering: C1-visible renderer helpers, file-select
  text/window presentation, town-map payload contracts.
- Visual profile tables: entity footprint and secondary visual descriptor table
  rows where C0/C1 consumers prove stable field names.
- Event/presentation payload islands: event script pointer table, event payload
  islands, landing/Sound Stone presentation data.

## First Pass Order

1. Start with text tile staging and window/color/HDMA helpers because they are
   the highest-impact C1 renderer dependencies.
2. Promote movement presentation and visual profile table contracts alongside
   C0 entity/movement consumer evidence.
3. Polish file-select and town-map rendering paths with C1 call-site language.
4. Split or rename event/presentation payload islands only where C3 script or
   landing/Sound Stone notes prove the contract.

## Evidence Inputs

- `notes/bank-c4-source-scaffold-handoff.md`
- `notes/bank-c4-working-name-proposals.md`
- `notes/bank-c4-progress-audit.md`
- `notes/data-contracts-c0-c4.md`
- `notes/ui-font-town-map-asset-contracts.md`
- `notes/landing-cast-visual-contracts.md`
- `notes/landing-hdma-dispatch-family-ef117b-c00d7e.md`

## Expected Outputs

- Stable renderer-facing names/comments for text tile, color/window/HDMA, and
  movement presentation helpers.
- Typed table or row-contract notes for visual profile and footprint data where
  consumers prove field semantics.
- Deferred notes for event payload islands that still need C3 script semantics
  before source-quality naming.

## Implementation Notes

- 2026-05-01 first slice: promoted the early PPU/text tile allocator and
  transfer helpers with byte-neutral aliases for `INIDISP`, the display shadow,
  `$3492` text tile scratch rows, the C0 VRAM transfer parameter block,
  `$9E2B` transfer latch, `$1AD6` text tile bitset, and recovery script id
  `$0A2A`. See `notes/c4-early-ppu-and-text-tile-helpers-0000-0085.md`.
- 2026-05-01 text staging continuation: promoted the menu glyph scratch
  renderer/flush pair with byte-neutral names for the `$9D23` scratch rows,
  `$9E23/$9E25/$9E27` cursors, `$9E2B` transfer latch, `$7900` VRAM base,
  and `C0:8616` transfer-queue tag byte. See
  `notes/text-window-rendering-primitives-c1078d-c10d7c.md`.
- 2026-05-01 active text-token staging: promoted the `$3492` glyph scratch
  renderer and the adjacent `$9D23` reset helper with byte-neutral names for
  scratch-row bases, bit/row/upload cursors, cursor wraps, clear-fill bytes,
  merge masks, and the PSI-menu continuation flag. See
  `notes/text-token-glyph-run-stager-c44b3a-c44e61.md` and
  `notes/text-window-rendering-primitives-c1078d-c10d7c.md`.
- 2026-05-01 window/color touch-up: named the fixed-color `COLDATA`
  component selector bits and channel-4 WOBJSEL clear value in the
  window/color HDMA helper. See
  `notes/c4-window-color-math-and-palette-helpers-23dc-26ed.md`.
- 2026-05-01 movement/presentation start: confirmed the screen-position
  interpolation source already carries the local `$3C22..$3C30` and live-slot
  rebase contracts, then promoted visual-frame helper literals for directional
  frame-list stride, tile-column merge masks, and render-strip source fields.
  See `notes/c4-visual-frame-copy-and-footprint-tables-283f-2b0d.md`.
- 2026-05-01 file-select/town-map start: promoted town-map renderer/load
  constants for the `EF:A70F` sector lookup, E0/E1 asset tables, blink and
  palette timers, input masks, decompressor latch, display latches, and VRAM
  transfer destinations. See `notes/town-map-selection-rendering-c4d274-c4d744.md`.
- 2026-05-01 file-select continuation: promoted table, sentinel, live-entity
  wait-scan, fixed spawn, frame-selector, and tilemap priority-pass constants
  in the file-select entity/script helpers. See
  `notes/file-select-entity-scripts-and-swirl-transition-c4d830-c4d989.md`.
- 2026-05-01 file-select swirl: promoted the transition runner's reset
  callees, auto-sector music latch, camera/display seeds, party scratch clear,
  `C3:FD8D` text pointer table, overlay completion latch, input abort masks,
  busy byte, and return-value sentinels. See
  `notes/file-select-entity-scripts-and-swirl-transition-c4d830-c4d989.md`.

## Validation

Future implementation passes should use:

```powershell
python tools\build_source_bank_scaffold.py --bank C4
python tools\validate_source_bank_byte_equivalence.py --bank C4 --module all --combined --scaffold src\c4\bank_c4_helpers_asar.asm --strict
python tools\build_source_bank_candidate_ranges_doc.py --bank C4
python tools\build_ebsrc_bank_map.py --bank C4
python tools\build_source_bank_residual_map.py --bank C4
python tools\build_working_name_manifest.py --banks C0 C1 C2 C3 C4 --output build\working-names-c0-c4.json
python tools\validate_data_contracts.py
```

This planning pass does not split C4 data stubs or change source files.
