# Asset Manifest Generation Status

Date: 2026-04-27

## Current Coverage

The ROM-backed asset manifest pipeline now has checked-in manifests for every currently mapped asset/data bank from `CA` through `EE`, plus the hand-curated EF debug seed manifest.

- manifests: `38`
- assets: `2218`
- output recipes: `5028`
- raw ROM-backed outputs: `2218`
- LZHAL decompressed outputs: `466`
- SNES palette JSON recipes: `216`
- SNES palette swatch PNG recipes: `216`
- LZHAL-decompressed SNES palette JSON recipes: `10`
- LZHAL-decompressed SNES palette swatch PNG recipes: `10`
- LZHAL-decompressed battle-background palette-aware 4bpp preview PNG recipes: `68`
- LZHAL-decompressed battle-sprite palette-aware 4bpp preview PNG recipes: `166`
- LZHAL-decompressed battle-sprite composed PNG recipes: `166`
  - 32x32 composed previews: `35`
  - 32x64 composed previews: `64`
  - 64x32 composed previews: `6`
  - 64x64 composed previews: `55`
  - 128x64 composed previews: `5`
  - 128x128 composed previews: `1`
- LZHAL-decompressed battle-background composed arrangement preview PNG recipes: `103`
  - 2bpp composed previews: `43`
  - 4bpp composed previews: `60`
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
- `tools/snes_palette.py` decodes SNES BGR555 palette words and writes JSON plus PNG swatch previews.
- `tools/validate_asset_manifests.py` validates every manifest, checks duplicate IDs, and can run the full extraction pass.

## Validation

Last full validation command:

```powershell
python tools\validate_asset_manifests.py --extract
```

Result:

- validated `38` manifests
- validated `2218` assets
- validated `5028` output recipes
- extracted every manifest against the local EarthBound US ROM
- all manifest range SHA-1 checks passed
- generated reports stayed under ignored `build/assets/`

## Notes

- Generated table IDs include source order so repeated generic includes such as `inline:WORD` cannot collide.
- Uncompressed `.gfx` payloads whose byte length is a multiple of 32 get a grayscale `snes_4bpp_tiles_png` preview recipe.
- Compressed `.lzhal` assets now emit decompressed local outputs. Decompressed `.gfx` payloads whose byte length is a multiple of 32 also get grayscale `earthbound_lzhal_snes_4bpp_tiles_png` preview recipes.
- Uncompressed `.pal` payloads now emit decoded SNES BGR555 JSON plus RGB swatch PNG previews. Compressed `.pal.lzhal` payloads get the same decoded outputs after LZHAL decompression.
- Battle background `.gfx` payloads with matching same-numbered 16-color `.pal` payloads now get palette-aware 4bpp tile-sheet previews. The recipe records the palette ROM range and SHA-1 directly so extraction does not depend on manifest run order.
- Battle background `.arr` payloads now get composed 32x32 tilemap PNG previews when matching same-numbered graphics/palette payloads line up mechanically. The renderer supports both 2bpp and 4bpp arrangement previews and records the graphics and palette source ranges in the extraction report.
- Battle sprite `.gfx` payloads now get palette-aware 4bpp tile-sheet previews for observed enemy-table sprite/palette combinations. This currently covers `166` combinations across `110` mapped battle sprite graphics and all `32` battle sprite palette IDs.
- Battle sprite `.gfx` payloads also get size-aware composed PNG previews for the same `166` observed enemy-table sprite/palette combinations. Dimensions come from `refs/ebsrc-main/ebsrc-main/src/data/battle/battle_sprites_pointers.asm`.

## Next Useful Decoders

1. Palette-aware PNG rendering for overworld sprites.
2. Palette table splitting for pointer/table corridors that are not standalone `.pal` payloads yet.
3. Sprite group metadata decoding so overworld sprite graphics can become engine-facing animation/frame records.
4. BRR/audio pack manifests split into sample/song/pack-level contracts.
