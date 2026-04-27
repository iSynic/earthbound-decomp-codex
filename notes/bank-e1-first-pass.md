# Bank E1 First Pass

## Main result

Bank `E1` is a mixed text/font/intro/ending/town-map/audio bank. It contains
flyover text, US font data, photographer/cast/credits data, intro logo and
title-screen assets, ending/cast assets, town-map label/icon assets, town-map
icon placement data, and one audio pack.

Primary artifacts:

- `notes/bank-e1-asset-data-map.md`
- `notes/bank-e1-source-scaffold-handoff.md`
- `build/asset-bank-e1.json`
- `build/e1-build-candidate-ranges.json`
- `build/e1-byte-equivalence-validation.json`

The generated map accounts for:

- binary assets: `43`
- binary asset bytes: `55125`
- asset mix: `8` arrangements, `17` graphics payloads, `12` palettes,
  `5` binary blobs, and `1` audio pack
- table/include bytes: `10397`
- coverage gap bytes: `14`
- source scaffold protected bytes: `65536 / 65536`
- byte-equivalence scaffold validation: `durable-scaffold`, `52` modules,
  `0` non-OK modules, `0` byte mismatches
- missing payload metadata: `4`

## Bank layout

The high-level E1 layout is:

- `E1:0000..E1:0C79`: locale flyover text span, `3194` bytes.
- `E1:0C7A..E1:2EF9`: main, battle, tiny, and large font data/graphics,
  `8832` bytes total.
- `E1:2EFA..E1:2F89`: `data/cast_sequence_formatting.asm`, `144` bytes.
- `E1:2F8A..E1:3749`: inferred photographer config span, `1984` bytes.
- `E1:374A..E1:413E`: `COMPRESSED_PALETTE_UNKNOWN`, `2549` bytes.
- `E1:413F..E1:4DE7`: `data/credits.asm`, `3241` bytes.
- `E1:4DE8..E1:4EC0`: inferred `unknown/E1/E14DE8.asm`, `217` bytes.
- `E1:4EC1..E1:AADE`: APE/HAL/Nintendo/gas-station intro logo assets,
  `23550` bytes total.
- `E1:AADF..E1:AE7B`: attract-mode produced-by/Nintendo-presentation assets,
  `925` bytes total.
- `E1:AE7C..E1:AF7C`: inferred pre-title unknown payload span, `257` bytes.
- `E1:AF7D..E1:CE07`: title-screen arrangement, graphics, letters, and
  palette, `7819` bytes total.
- `E1:CE08..E1:CFAE`: inferred `data/unknown/E1CE08.asm`, `423` bytes.
- `E1:CFAF..E1:D6E0`: unknown graphics/palette/arrangement assets,
  `1842` bytes total.
- `E1:D6E1..E1:D834`: inferred `UNKNOWN_E1D6E1`, `340` bytes.
- `E1:D835..E1:E923`: cast/credits ending graphics and palette/font data,
  `4335` bytes total.
- `E1:E924..E1:EA4F`: inferred ending/unknown table span, `300` bytes.
- `E1:EA50..E1:F202`: town-map label graphics and icon palette, `1971` bytes.
- `E1:F203..E1:F580`: inferred town-map icon placement span, `894` bytes.
- `E1:F581..E1:FFF1`: `AUDIO_PACK_123`, `2673` bytes.
- `E1:FFF2..E1:FFFF`: tail slack, `14` bytes.

## Flyover and Credits Handling

The bank config uses `LOCALEINCLUDE` for `coffee.flyover`, `tea.flyover`, and
`flyovers.flyover`. Those source payloads are not present as regular files in
the checked-in tree, but the next known asset begins at `E1:0C7A`, so the
manifest safely treats `E1:0000..E1:0C79` as one combined flyover text span.

`data/credits.asm` exists and uses `EBSTAFF_*` macros. The manifest tool now
counts the US retail byte sizes for those simple macros, so the credits text is
placed as `E1:413F..E1:4DE7` instead of being collapsed to a zero-byte source
include.

## Missing Payload Metadata

Four bank-config binary payloads are not present in `earthbound.yml`:

- `E1AE7C.bin.lzhal`
- `E1AE83.bin.lzhal`
- `E1AEFD.bin.lzhal`
- `E1D6E1.gfx.lzhal`

The manifest can infer the bracketing spans for the first pre-title unknown
group and for `UNKNOWN_E1D6E1`, but the exact split among `E1AE7C`, `E1AE83`,
and `E1AEFD` remains unresolved.

## Current E1 confidence boundary

High confidence:

- E1 is data/assets, not executable code.
- All major flyover, font, intro, title, ending, town-map, and audio regions are
  bounded for the US retail build.
- The only unclaimed space is `E1:FFF2..E1:FFFF`, `14` bytes.
- `src/e1/bank_e1_helpers_asar.asm` protects the full bank through the reusable
  source-bank scaffold pipeline. The inferred missing payload groups remain
  byte-exact but still need asset-level splits/names before individual asset
  extraction is semantically final.

Still intentionally out of scope:

- Exact split of the three missing pre-title unknown payloads.
- Semantic decoding of flyover scripts, photographer config, town-map icon
  placement, and unknown E1 table spans.
- Rendering/decompressing intro/title/ending graphics.
- Audio-pack internals.

## Recommended next move

E1 is now closed for byte-preserving scaffold purposes. The remaining work is
semantic: resolve the exact split among the pre-title missing payloads, name the
`E1D6E1` inferred graphics payload, promote photographer/flyover/town-map icon
placement spans into typed contracts, and optionally add render fixtures for the
intro/title/ending/town-map assets.
