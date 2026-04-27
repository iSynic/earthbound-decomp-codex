# Bank DF First Pass

## Main result

Bank `DF` is a mixed map/audio data bank. It contains compressed map tileset
graphics, compressed map animation graphics, an inferred palette-animation table
region, and one audio pack.

Primary artifacts:

- `notes/bank-df-asset-data-map.md`
- `build/asset-bank-df.json`

The generated map accounts for:

- binary assets: `22`
- binary asset bytes: `63625`
- asset mix: `21` compressed graphics payloads and `1` audio pack
- inferred generated table bytes: `1893`
- coverage gap bytes: `18`
- missing payload metadata: `0`

## Bank layout

The high-level DF layout is:

- `DF:0000..DF:C242`: `MAP_DATA_TILE_SET_GRAPHICS_12`, `16`, `17`, `18`,
  `19`, and `15`, `49731` bytes total.
- `DF:C243..DF:E4E0`: `MAP_DATA_TILE_ANIMATION_GFX_0` through
  `MAP_DATA_TILE_ANIMATION_GFX_14`, `8862` bytes total.
- `DF:E4E1..DF:EC45`: generated palette-animation table region, `1893` bytes.
- `DF:EC46..DF:FFED`: `AUDIO_PACK_4`, `5032` bytes.
- `DF:FFEE..DF:FFFF`: tail slack, `18` bytes.

## Generated Palette-Animation Data

The bank config names three missing generated includes between animation
graphics and the audio pack:

- `data/map/palette_anim_pointer_table.asm`
- `data/map/palette_anim_secondary_table.asm`
- `data/map/palette_anim_table.asm`

Those source files are absent from the checked-in reference tree. Because the
next known binary asset starts at `DF:EC46`, the manifest safely treats
`DF:E4E1..DF:EC45` as one combined generated palette-animation span.

## Current DF confidence boundary

High confidence:

- DF is data/assets, not executable code.
- Tileset graphics, animation graphics, inferred palette-animation data, and
  audio spans are exact for the US retail build.
- Only `18` bytes at the end of the bank are unclaimed slack.

Still intentionally out of scope:

- Internal splits of the palette-animation generated table region.
- Decompressing or rendering tileset/animation graphics.
- Audio-pack internals.

## Recommended next move

Proceed to `E0`. The next bank leaves the map-graphics run and moves into UI
graphics, fonts, town maps, and text/window-related tables.
