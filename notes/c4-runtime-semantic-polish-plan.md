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
- 2026-05-01 init-intro dispatcher: promoted state ids, session/presentation
  flags, screen-origin reset fields, forced-blank checks, color/display latches,
  Sound Stone melody ids, title still-image arguments, and file-select swirl
  mode values. See
  `notes/file-select-entity-scripts-and-swirl-transition-c4d830-c4d989.md`.
- 2026-05-01 Sound Stone start: promoted the presentation controller's CE
  graphics/palette payloads, 7F work buffer, VRAM transfer sizes, sprite
  resource args, staging tile blocks, eight-Sanctuary state record bases,
  state values, and primary timers. See
  `notes/sound-stone-presentation-data-c4ac57.md`.
- 2026-05-01 Sound Stone continuation: promoted the animation loop's
  phrase/stinger timing, EF payload pointer walk, per-Sanctuary orbit
  angle/phase/glyph fields, spinner frame, battle-visual script ids, input exit
  mask, and closeout fade/busy gates. See
  `notes/sound-stone-presentation-data-c4ac57.md`.
- 2026-05-01 landing display streams: promoted the landing asset stream
  helper's subpiece pointer-table, descriptor-count/table, no-subpiece
  sentinel, source-bank/list offsets, paired-plane VRAM transfer, and the four
  stream pointer families seeded by `C4:B26B`. See
  `notes/landing-display-assembly-cluster-c007b6-c4b26b.md`.
- 2026-05-01 landing child anchors: promoted the child-anchor/spawn helper's
  placement modes, `$B3F8/$B3FA` anchor pair, live entity table families,
  child-definition field offsets, signed-offset masks, spawn descriptor, and
  attached-parent tag. See `notes/child-entity-spawn-c4b3d0-c40de8.md`.
- 2026-05-01 landing child lookup: promoted the attached-child clear/lookup
  wrapper's `$103E` scan table, tagged-parent mask, live-slot loop bounds,
  default base-slot arguments, and resolver-backed spawn call contract. See
  `notes/child-entity-spawn-c4b3d0-c40de8.md`.
- 2026-05-01 landing palette touch-up: promoted RGB555 scale/repack
  thresholds, high-component normalization, WRAM-low selectors, palette
  first-word/fade sentinels, and the existing-work selector bit in the landing
  palette/display helper. See
  `notes/landing-and-coffee-tea-visual-helpers-c492d2-c49d1e.md`.
- 2026-05-01 saved landing setup: promoted the saved landing display
  initializer's init latch, stage cursor/scratch latches, E1 asset pointers, BG
  and VRAM transfer values, palette staging offsets, intro display state, and
  phase staging buffer constants. See
  `notes/saved-landing-display-stage-c4c2de-c4c64d.md`.
- 2026-05-01 saved landing fades: promoted the saved landing fade helpers'
  abort latch, success/abort sentinels, palette restore source/scale/commit
  values, long/short phase frame counts, phase stage ids, text/event gate
  pointers, and no-source fade counters. See
  `notes/saved-landing-display-stage-c4c2de-c4c64d.md`.
- 2026-05-01 saved landing reload: promoted the saved-coordinate reload
  wrapper's snapshot pair, abort transition args, restore fade and sound/counter
  ids, return-to-world display state, map-record cleanup fields, event-loop
  bounds, `$289E` reset table, and final world-refresh fade count. See
  `notes/saved-landing-display-stage-c4c2de-c4c64d.md`.
- 2026-05-01 actionscript camera callbacks: promoted the callback strip's
  current-slot index, callback flag bit, active entity registry scan tables,
  live world/screen/offset coordinate tables, camera origin pair, facing table,
  and half-octant direction rounding constants. See
  `notes/c3-actionscript-callback-contracts.md`.
- 2026-05-01 staged movement pulses: promoted the movement pulse accumulator
  and path-builder's first index, active run flag, minimum delta, signed-word
  inversion mask, direction rounding spans, and repeated-pulse loop sentinel.
  See `notes/staged-movement-pulse-and-tracked-item-registry-c48c59-c48f98.md`.
- 2026-05-01 tracked-item pulse registry: promoted the tracked item pulse
  helpers' active/inactive return values, blocked overworld state, first-slot
  and first-pulse sentinels, low-byte masks, and full-value C1 item pulse
  argument. See
  `notes/staged-movement-pulse-and-tracked-item-registry-c48c59-c48f98.md`.
- 2026-05-01 magic-truffle direction helper: promoted the immediate text
  command helper's truffle pose descriptor, missing-slot sentinel, range and
  minimum-distance gates, result values, live entity/player coordinate fields,
  signed delta inversion mask, and direction octant rounding constants. See
  `notes/text-command-family-1f-deferred-callbacks.md`.
- 2026-05-01 landing profile interpolation: promoted the adjacent landing
  profile color/display helper contracts for the `$7F:7900..7E00` component
  planes, `0x0240` template buffer, RGB555 masks, `EF:10FB` descriptor table,
  row stride, transfer blocks, wait selectors, display cache latch, and busy
  byte. See `notes/landing-and-coffee-tea-visual-helpers-c492d2-c49d1e.md`.
- 2026-05-01 coffee/tea tile buffer: promoted row-mask byte/pass counts,
  token metadata field offsets, dirty-range and scroll sentinels, row-reveal
  and high-byte masks, tile-source plane/trailer offsets, work-bank value, and
  visual tile transfer arguments. See
  `notes/landing-and-coffee-tea-visual-helpers-c492d2-c49d1e.md`.
- 2026-05-01 coffee/tea and flyover tail: promoted the scene interpreters'
  prompt token ids, initial window index, shared command bytes, byte masks,
  flyover pointer offset, display-bracket arguments, clear region,
  busy-complete sentinel, flyover wait count, display modes, and `$10E4`
  state-mask/restore contract. See
  `notes/landing-and-coffee-tea-visual-helpers-c492d2-c49d1e.md`.
- 2026-05-01 gas-station intro loader: promoted the C4-side intro asset
  loader's display mode, clear/upload selectors, pointer bank-field offset,
  tilemap attribute rewrite fields, battle-visual tile-state/chunk staging
  values, script start value, and mask/sentinel literals. See
  `notes/gas-station-intro-asset-loader-c4a377.md`.
- 2026-05-01 battle overlay island: split the adjacent transition data into
  the static wave table and four named open/close script payload blocks, then
  promoted shared `$AEC2..$AEE6` state names, flag bits, script/frame tables,
  record stride/sentinel fields, effect position/size deltas, special-mode
  ladder values, and C0 window/offset helper contracts. See
  `notes/battle-overlay-script-state-c4a67e-c4a7b0.md`.
- 2026-05-06 credits presentation follow-up: tightened the C4 credits queue
  and playback controller around the newly polished C0 command-stream callback.
  The source now names the frame-callback install/reset calls, 9-byte credits
  DMA queue records, `$B4E3/$B4E5/$B4E7..$B4ED` command-stream/scroll fields,
  E1:2F8A photographer record stride/count, photograph render state, and the
  BG3 scroll/progress comparison at `$003B`. See
  `notes/cast-scene-scroll-helpers-c4e4da-c4e583.md` and
  `notes/frame-callback-bodies.md`.
- 2026-05-06 cast-scroll presentation follow-up: tightened the ending cast
  loader/scroll helpers, cast-name tilemap copy/print path, cast entity
  spawn/onscreen helpers, and `PlayCastScene` controller. The source now names
  the event-801 scroll threshold polling contract, `$0BCA` live-Y source,
  `$1002` blank-row upload cursor, `$B4D1` cast-name tile offset, `$9641`
  completion latch, and the C0 cleanup helper calls without assigning those
  per-slot tables a global meaning. See
  `notes/cast-scene-scroll-helpers-c4e4da-c4e583.md`.
- 2026-05-06 audio tail follow-up: tightened the final C4 audio block around
  the music dataset row fields, audio pack pointer row shape, US bank resolver
  mask reset, cold-start bootstrap shared pack, `ChangeMusic` primary,
  secondary, and sequence pack roles, Sound Stone recording transition
  exception, stereo/mono stream loader, and auto-sector music-change latch. See
  `notes/cast-scene-scroll-helpers-c4e4da-c4e583.md` and
  `notes/audio-pack-format-and-renderer-frontier.md`.
- 2026-05-06 PPU/presentation contract follow-up: added conservative
  side-effect comments for the C4 color-window and WH0/WH2 HDMA helpers,
  clarified that the battle overlay initializer owns the `$AEC2..$AEE6`
  callee-side state layout, attached local movement-presentation WRAM names to
  the current-slot vector/bounds helper corridor, and split the Sound Stone
  presentation data block into labeled EF payload, coordinate, melody,
  phrase-length, and event tables. See
  `notes/c4-window-color-math-and-palette-helpers-23dc-26ed.md`,
  `notes/battle-overlay-script-state-c4a67e-c4a7b0.md`,
  `notes/movement-target-bounds-and-vector-refresh-c46ef8-c47369.md`, and
  `notes/sound-stone-presentation-data-c4ac57.md`.
- 2026-05-06 visual table follow-up: split the coarse
  `C4:2A1F..30EC` footprint / secondary visual descriptor corridor into
  labeled footprint geometry tables, the secondary descriptor pointer table,
  descriptor rows, the preserved callback byte island, map-tile chunk pointers,
  and visual tile-word ladders. Also documented the side effects for the visual
  frame-word copy helpers, render-strip wrapper, and `$212C` main-screen HDMA
  starter. See
  `notes/c4-visual-frame-copy-and-footprint-tables-283f-2b0d.md` and
  `notes/secondary-visual-descriptor-contracts.md`.
- 2026-05-06 coffee/tea interpreter follow-up: tightened side-effect comments
  for the shared coffee/tea tile-buffer helpers and scene interpreters, naming
  the local `$3492`, `$7DFE/$7E00`, `$9F2D/$9F2F/$9F31`, and `$3C14..$3C20`
  ownership boundary while leaving C0/C2 transfer and battle-background callee
  behavior to those banks. The flyover text pointer table is now row-split with
  only the three locally corroborated intro-string roles called out. See
  `notes/landing-and-coffee-tea-visual-helpers-c492d2-c49d1e.md`.
- 2026-05-06 window mask / indexed graphics follow-up: tightened the
  C4-local contracts for generated WH0/WH2 mask streams, the `$0E5E`
  toggle-versus-index boundary, the `CC:2DE1` indexed graphics loaders, the
  window graphics cache rebuild, the `$0200` window-flavour palette refresh,
  and the flyover-undraw return-to-world presentation side effects. C0/C2
  transfer and cleanup callees remain documented only as caller joins where C4
  writes their local arguments. See
  `notes/window-mask-and-indexed-gfx-c47501-c47b77.md`.

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
