# Bank D7 First Pass

## Main result

Bank `D7` is a map-data bank. It continues the map tile chunk run from `D6`,
then contains a generated palette/sector-attribute region, then starts the
compressed map arrangement stream.

Primary artifacts:

- `notes/bank-d7-asset-data-map.md`
- `notes/bank-d7-source-scaffold-handoff.md`
- `build/asset-bank-d7.json`
- `build/d7-build-candidate-ranges.json`
- `build/d7-byte-equivalence-validation.json`

The generated map accounts for:

- binary assets: `5`
- binary asset bytes: `56808`
- asset mix: `4` map tile chunks (`bin`) and `1` compressed arrangement
  payload (`arr`)
- inferred generated table bytes: `7680`
- coverage gap bytes: `1048`
- source scaffold protected bytes: `65536 / 65536`
- byte-equivalence scaffold validation: `durable-scaffold`, `7` modules,
  `0` non-OK modules, `0` byte mismatches
- missing payload metadata: `0`

## Bank layout

The high-level D7 layout is:

- `D7:0000..D7:27FF`: `MAP_DATA_TILE_TABLE_CHUNK_7`, `10240` bytes.
- `D7:2800..D7:4FFF`: `MAP_DATA_TILE_TABLE_CHUNK_8`, `10240` bytes.
- `D7:5000..D7:7FFF`: `MAP_DATA_TILE_TABLE_CHUNK_9`, `12288` bytes.
- `D7:8000..D7:A7FF`: `MAP_DATA_TILE_TABLE_CHUNK_10`, `10240` bytes.
- `D7:A800..D7:B1FF`: global map context byte table, `2560` bytes.
- `D7:B200..D7:C5FF`: per-sector attribute word table, `5120` bytes.
- `D7:C600..D7:FBE7`: `MAP_DATA_TILE_ARRANGEMENT_0`, `13800` bytes.
- `D7:FBE8..D7:FFFF`: tail slack, `1048` bytes.

## Generated Map Metadata

The bank config names two missing generated includes before the first
arrangement payload:

- `data/map/global_tileset_palette_data.asm`
- `data/map/per-sector_attributes.asm`

Those source files are absent from the checked-in reference tree. The next known
binary asset starts at `D7:C600`, so the source scaffold still preserves the
combined `D7:A800..D7:C5FF` span as one generated map metadata corridor.

The asset emitter now decodes that preserved corridor as two reproducible
runtime-consumer tables:

- `D7:A800..D7:B1FF`: `80 x 32` context bytes indexed as
  `sector_x * 32 + sector_y`; consumers use `byte >> 3` as the tileset/palette
  group and keep `byte & 7` as a variant/low-bit selector.
- `D7:B200..D7:C5FF`: `80 x 32` little-endian sector attribute words using the
  same index; `C0:0AA1` stores the full word as the position cell context, while
  `C0:2668` uses the low three bits for spawn-probe gating.

## Current D7 confidence boundary

High confidence:

- D7 is data/assets, not executable code.
- `D7:0000..D7:A7FF` completes map tile chunks `7` through `10`.
- `D7:A800..D7:C5FF` is generated map metadata named by the bank config and now
  has a typed extraction sidecar that exposes the context-byte and attribute-word
  halves without splitting the source scaffold.
- `D7:C600..D7:FBE7` is compressed map arrangement payload `0`.
- `src/d7/bank_d7_helpers_asar.asm` protects the full bank through the reusable
  source-bank scaffold pipeline.

Still intentionally out of scope:

- Internal split of the generated metadata span.
- Decoding/rendering map tile chunks.
- Decompressing or interpreting arrangement payload `0`.
- Explaining the `1048` bytes of tail slack.

## Recommended next move

D7 is now closed for byte-preserving scaffold purposes. The remaining D7 work is
render/decode depth: connect the map tile chunks and arrangement payloads to
render fixtures, then promote any additional per-sector attribute semantics as
their runtime callers are named.
