# Bank D8 First Pass

## Main result

Bank `D8` is a mixed map/error/audio data bank. Most of the bank is generated
map tile collision data and collision pointer data; the tail contains compressed
anti-piracy/faulty-game-pak warning assets and an audio pack. The follow-up D8
splitter now resolves the generated collision-data region into exact spans.

Follow-up source-scaffold status:

- durable scaffold: `src/d8/bank_d8_helpers_asar.asm`
- manifest: `build/d8-build-candidate-ranges.json`
- handoff: `notes/bank-d8-source-scaffold-handoff.md`
- protected bytes: `65536 / 65536`
- residual bytes: `0`
- modules: `28`
- byte-equivalence: `OK`, `0` mismatches

Primary artifacts:

- `notes/bank-d8-asset-data-map.md`
- `notes/d8-table-splits.md`
- `build/asset-bank-d8.json`
- `build/d8-table-splits.json`

The generated map accounts for:

- binary assets: `6`
- binary asset bytes: `3979`
- asset mix: `2` compressed arrangements, `2` compressed graphics payloads,
  `1` palette, and `1` audio pack
- inferred generated table bytes: `61534`
- exact generated collision split bytes: `61534`
- coverage gap bytes: `23`
- missing payload metadata: `0`

## Bank layout

The high-level D8 layout is:

- `D8:0000..D8:F05D`: generated tile collision data/pointer region, `61534`
  bytes.
- `D8:F05E..D8:F20C`: `ANTI_PIRACY_NOTICE_ARRANGEMENT`, `431` bytes.
- `D8:F20D..D8:F3BD`: `ANTI_PIRACY_NOTICE_GRAPHICS`, `433` bytes.
- `D8:F3BE..D8:F3C5`: `WARNING_PALETTE`, `8` bytes.
- `D8:F3C6..D8:F5C3`: `FAULTY_GAME_PAK_ARRANGEMENT`, `510` bytes.
- `D8:F5C4..D8:F6B6`: `FAULTY_GAME_PAK_GRAPHICS`, `243` bytes.
- `D8:F6B7..D8:FFE8`: `AUDIO_PACK_61`, `2354` bytes.
- `D8:FFE9..D8:FFFF`: tail slack, `23` bytes.

## Generated Collision Data

The bank config names this generated family before the warning assets:

- `data/map/tile_collision_data.asm`
- `data/map/tile_collision_pointers_00.asm` through
  `data/map/tile_collision_pointers_19.asm`

Those generated files are absent from the checked-in reference tree. Because the
next known binary asset starts at `D8:F05E`, the first pass safely treated
`D8:0000..D8:F05D` as one combined generated collision-data span.

The dedicated splitter recovers the exact internal split from the 20-entry
`EF:117B` tileset-collision long-pointer table and the first warning-asset
anchor:

- `D8:0000..D8:8F4F`: `MAP_TILE_COLLISION_DATA`, `36688` bytes.
- `D8:8F50..D8:F05D`: `MAP_DATA_TILE_COLLISION_POINTERS_0..19`, 20 exact
  word-offset tables.
- `D8:F05E`: first warning-screen asset byte.

## Current D8 confidence boundary

High confidence:

- D8 is data/assets, not executable code.
- `D8:0000..D8:F05D` is map collision data/pointers named by the bank config.
- The collision data/pointer boundary and all 20 pointer-table spans are exact
  in `notes/d8-table-splits.md`.
- The warning assets and `AUDIO_PACK_61` have exact spans.
- Only `23` bytes at the end of the bank are unclaimed slack.

Still intentionally out of scope:

- Tile collision format decoding.
- Row-level semantic decoding of the pointed collision rows.
- Rendering/decompressing the warning screen assets.
- Audio-pack internals.

## Recommended next move

Treat D8 as structurally complete and byte-protected for the current
bank-coverage phase. For D8 itself, the next step is collision row semantics
rather than boundary discovery. At the project level, the remaining priority-2
non-source blocker is C3 script/actionscript separation.
