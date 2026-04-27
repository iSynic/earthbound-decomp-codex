# Bank DA First Pass

## Main result

Bank `DA` is a map arrangement/palette/audio bank. It starts with three
compressed map arrangements, then contains map palettes `0` through `31`, an
inferred palette pointer table, and an audio pack.

Primary artifacts:

- `notes/bank-da-asset-data-map.md`
- `build/asset-bank-da.json`

The generated map accounts for:

- binary assets: `36`
- binary asset bytes: `65422`
- asset mix: `3` compressed arrangements, `32` palettes, and `1` audio pack
- inferred generated table bytes: `96`
- coverage gap bytes: `18`
- missing payload metadata: `0`

## Bank layout

The high-level DA layout is:

- `DA:0000..DA:1341`: `MAP_DATA_TILE_ARRANGEMENT_5`, `4930` bytes.
- `DA:1342..DA:4EA2`: `MAP_DATA_TILE_ARRANGEMENT_6`, `15201` bytes.
- `DA:4EA3..DA:7CA6`: `MAP_DATA_TILE_ARRANGEMENT_7`, `11780` bytes.
- `DA:7CA7..DA:FAA6`: `MAP_DATA_PALETTE_0` through
  `MAP_DATA_PALETTE_31`, `32256` bytes total.
- `DA:FAA7..DA:FB06`: `data/map/unknown_map_palette_pointer_table.asm`,
  inferred as `96` bytes.
- `DA:FB07..DA:FFED`: `AUDIO_PACK_111`, `1255` bytes.
- `DA:FFEE..DA:FFFF`: tail slack, `18` bytes.

## Palette Data

All 32 map palette payloads are present in source order as
`maps/palettes/*.pal` assets. Their individual sizes vary from `192` bytes to
`1536` bytes, and the manifest records exact CPU spans for each payload.

The checked-in source tree does not contain
`data/map/unknown_map_palette_pointer_table.asm`, but the next known asset is
`AUDIO_PACK_111` at `DA:FB07`. The manifest therefore safely infers the pointer
table as `DA:FAA7..DA:FB06`.

## Current DA confidence boundary

High confidence:

- DA is data/assets, not executable code.
- Arrangement, palette, inferred pointer-table, and audio spans are exact for
  the US retail build.
- Only `18` bytes at the end of the bank are unclaimed slack.

Still intentionally out of scope:

- Meaning of the unknown map palette pointer table.
- Palette-to-sector/tileset assignment semantics.
- Decompressing or rendering arrangements `5` through `7`.
- Audio-pack internals.

## Recommended next move

Proceed to `DB`. The next bank continues compressed map arrangements and adds an
audio pack, so it should be another fast asset-boundary pass.
