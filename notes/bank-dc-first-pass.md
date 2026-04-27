# Bank DC First Pass

## Main result

Bank `DC` is a mixed map/audio data bank. It contains six compressed map
arrangements, one compressed tileset graphics payload, an inferred per-sector
music table, and two audio packs.

Primary artifacts:

- `notes/bank-dc-asset-data-map.md`
- `build/asset-bank-dc.json`

The generated map accounts for:

- binary assets: `9`
- binary asset bytes: `62866`
- asset mix: `6` compressed arrangements, `1` compressed graphics payload, and
  `2` audio packs
- inferred generated table bytes: `2560`
- coverage gap bytes: `110`
- missing payload metadata: `0`

## Bank layout

The high-level DC layout is:

- `DC:0000..DC:1FC9`: `MAP_DATA_TILE_ARRANGEMENT_12`, `8138` bytes.
- `DC:1FCA..DC:593B`: `MAP_DATA_TILE_ARRANGEMENT_13`, `14706` bytes.
- `DC:593C..DC:687A`: `MAP_DATA_TILE_ARRANGEMENT_14`, `3903` bytes.
- `DC:687B..DC:72BF`: `MAP_DATA_TILE_ARRANGEMENT_15`, `2629` bytes.
- `DC:72C0..DC:8E49`: `MAP_DATA_TILE_ARRANGEMENT_18`, `7050` bytes.
- `DC:8E4A..DC:B022`: `MAP_DATA_TILE_ARRANGEMENT_19`, `8665` bytes.
- `DC:B023..DC:D636`: `MAP_DATA_TILE_SET_GRAPHICS_14`, `9748` bytes.
- `DC:D637..DC:E036`: `data/map/per-sector_music.asm`, inferred as
  `2560` bytes.
- `DC:E037..DC:F8BE`: `AUDIO_PACK_156`, `6280` bytes.
- `DC:F8BF..DC:FF91`: `AUDIO_PACK_79`, `1747` bytes.
- `DC:FF92..DC:FFFF`: tail slack, `110` bytes.

## Per-Sector Music

The checked-in source tree does not contain
`data/map/per-sector_music.asm`, but the next known binary asset starts at
`DC:E037`. The manifest therefore safely infers the per-sector music table as
`DC:D637..DC:E036`.

## Current DC confidence boundary

High confidence:

- DC is data/assets, not executable code.
- Arrangement, graphics, inferred per-sector music, and audio spans are exact
  for the US retail build.
- Only `110` bytes at the end of the bank are unclaimed slack.

Still intentionally out of scope:

- Per-sector music table format and indexing.
- Decompressing or rendering arrangements/tileset graphics.
- Audio-pack internals.

## Recommended next move

Proceed to `DD`. Its bank config appears to continue compressed map graphics
payloads and audio data, so the manifest should likely close another bank
quickly before we need a format-specific decoder.
