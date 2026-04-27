# Asset Manifest Generation Status

Date: 2026-04-27

## Current Coverage

The ROM-backed asset manifest pipeline now has checked-in manifests for every currently mapped asset/data bank from `CA` through `EE`, plus the hand-curated EF debug seed manifest.

- manifests: `38`
- assets: `2218`
- output recipes: `6174`
- raw ROM-backed outputs: `2218`
- LZHAL decompressed outputs: `466`
- SNES palette JSON recipes: `216`
- SNES palette swatch PNG recipes: `216`
- LZHAL-decompressed SNES palette JSON recipes: `10`
- LZHAL-decompressed SNES palette swatch PNG recipes: `10`
- LZHAL-decompressed battle-background palette-aware 4bpp preview PNG recipes: `68`
- LZHAL-decompressed battle-sprite palette-aware 4bpp preview PNG recipes: `166`
- Default-palette overworld sprite 4bpp preview PNG recipes: `1146`
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
- `tools/build_overworld_sprite_group_manifest.py` builds `notes/overworld-sprite-groups.json`, a checked-in contract tying ebsrc sprite group labels to D1-D5 sprite payload assets and EBDecomp group metadata.
- `tools/build_overworld_sprite_frame_contract.py` builds `notes/overworld-sprite-frame-contracts.json`, a ROM-verified runtime slot/payload contract over the sprite group contract and EF sprite grouping pointer table, including named low-bit renderer effects.
- `tools/build_overworld_sprite_preview_sheets.py` builds ignored `build/overworld-sprite-preview-sheets/` PNG contact sheets and an index from the resolved frame contract.
- `tools/build_secondary_visual_descriptor_contract.py` builds `notes/secondary-visual-descriptor-contracts.json`, a ROM-verified contract for the C4 secondary visual descriptor pointer table and 5-byte piece records.
- `tools/build_overworld_sprite_composed_previews.py` builds ignored prototype composed overworld preview sheets from the frame contract, secondary visual descriptor contract, and generated D1-D5 palette-00 previews.

## Validation

Last full validation command:

```powershell
python tools\validate_asset_manifests.py --extract
```

Result:

- validated `38` manifests
- validated `2218` assets
- validated `6174` output recipes
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
- Overworld sprite `.gfx` payloads in `D1`-`D5` now get default-palette 4bpp tile-sheet previews. The palette source is the ROM-backed `SPRITE_GROUP_PALETTES` table at `C3:0000`, corroborated by `refs/ebsrc-main/ebsrc-main/src/bankconfig/US/bank03.asm`.
- Overworld sprite groups now have a machine-readable metadata contract covering all `267` ebsrc `SPRITE_GROUP_*` labels, `742` group-owned D1-D5 sprite payloads, and `267` EBDecomp size/collision metadata matches. `200` groups match the `OVERWORLD_SPRITE` enum directly; the remaining `67` are resolved by `notes/overworld-sprite-group-aliases.json`. The contract also records `224` overflow payload labels and `404` D1-D5 sprite payload assets that are not owned by a group label after bank-boundary and pointer-length guards are applied.
- Overworld sprite frame contracts now classify all `267` groups into runtime slot models, payload reuse models, and layout families, and extract the actual `spritepointerarray` records from `EF:133F..EF:4A40`. All `2438` runtime pointer slots resolve to concrete D1-D5 sprite payload assets; `1769` are exact pointer-word matches and `669` use masked low-two-bit flags. The low-bit effects are now named from renderer behavior: bit 0 `select_flipped_piece_record_pass` affects `657` slots, and bit 1 `suppress_auxiliary_c40be8_prepass` affects `16` slots. Direction/phase labels remain semantic hints from the ebsrc `DIRECTION` enum.
- Overworld sprite preview sheets can now be generated for all `267` sprite groups from the frame contract and extracted palette-00 tile previews. The generated PNGs and `index.json` stay under ignored `build/overworld-sprite-preview-sheets/`.
- Secondary visual descriptors now have a machine-readable C4 contract covering the `17` pointer-table entries at `C4:2B0D..C4:2B51`, `16` unique descriptor records at `C4:2B51..C4:2F45`, and the adjacent `C4:2F45..C4:2F8C` non-descriptor ranges before the tile-base and tile-word support tables.
- Prototype composed overworld preview sheets can now be generated under ignored `build/overworld-sprite-composed-previews/`. They combine resolved runtime slots with secondary descriptor piece positions and use pointer bit 0 to choose pass 0 or the horizontally flipped pass 1; the current renderer still uses 8x8 tile crops and does not yet apply larger sprite-size bits, palette variants, or priority-band visualization.

## Next Useful Decoders

1. Apply secondary descriptor trailing size/attribute bits so composed overworld previews graduate from 8x8-piece audit sheets toward in-game sprite/OAM previews.
2. Optional overworld sprite palette-variant rendering once entity/map palette selection is documented.
3. Palette table splitting for pointer/table corridors that are not standalone `.pal` payloads yet.
4. BRR/audio pack manifests split into sample/song/pack-level contracts.
