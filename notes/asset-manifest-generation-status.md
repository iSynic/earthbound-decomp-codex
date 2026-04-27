# Asset Manifest Generation Status

Date: 2026-04-27

## Current Coverage

The ROM-backed asset manifest pipeline now has checked-in manifests for every currently mapped asset/data bank from `CA` through `EE`, plus the hand-curated EF debug seed manifest.

- manifests: `38`
- assets: `2218`
- output recipes: `4073`
- raw ROM-backed outputs: `2218`
- LZHAL decompressed outputs: `466`
- SNES 4bpp preview PNG recipes: `1151`
- LZHAL-decompressed SNES 4bpp preview PNG recipes: `237`
- SNES 2bpp preview PNG recipes: `1`

Category breakdown:

- graphics: `1822`
- audio: `168`
- binary asset: `155`
- raw table: `40`
- raw gap: `31`
- raw preserved corridor: `2`

## Generated Manifest Set

- `asset-manifests/bank-ca-assets.json` through `asset-manifests/bank-ee-assets.json`
- `asset-manifests/ef-debug-assets.json`

EF remains hand-curated for now because its manifest intentionally names the debug font/cursor payloads and preserves the mixed EF front/tail corridors. A generated `bank-ef-assets.json` would duplicate that coverage less clearly.

## Tooling

- `tools/build_asset_extraction_manifest.py` converts `build/asset-bank-xx.json` layout data into `asset-manifest.v1`.
- `tools/extract_assets.py` extracts assets and writes per-manifest reports under ignored `build/assets/`.
- `tools/validate_asset_manifests.py` validates every manifest, checks duplicate IDs, and can run the full extraction pass.

## Validation

Last full validation command:

```powershell
python tools\validate_asset_manifests.py --extract
```

Result:

- validated `38` manifests
- validated `2218` assets
- validated `4073` output recipes
- extracted every manifest against the local EarthBound US ROM
- all manifest range SHA-1 checks passed
- generated reports stayed under ignored `build/assets/`

## Notes

- Generated table IDs include source order so repeated generic includes such as `inline:WORD` cannot collide.
- Uncompressed `.gfx` payloads whose byte length is a multiple of 32 get a grayscale `snes_4bpp_tiles_png` preview recipe.
- Compressed `.lzhal` assets now emit decompressed local outputs. Decompressed `.gfx` payloads whose byte length is a multiple of 32 also get grayscale `earthbound_lzhal_snes_4bpp_tiles_png` preview recipes.

## Next Useful Decoders

1. SNES palette decoding for `.pal` payloads and palette tables.
2. Palette-aware PNG rendering for decompressed battle backgrounds, battle sprites, and overworld sprites.
3. Sprite group metadata decoding so overworld sprite graphics can become engine-facing animation/frame records.
4. BRR/audio pack manifests split into sample/song/pack-level contracts.
