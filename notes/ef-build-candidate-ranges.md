# EF build-candidate byte ranges

This manifest records source slices promoted into the reusable source-bank scaffold pipeline.

## Summary

- ranges: `12`
- total bytes: `65536`
- source bytes: `6522`
- data gap bytes: `59014`

## Ranges

| Level | Source Path | Range | Span Bytes | Source Bytes | Data Gap Bytes | SHA-1 |
| --- | --- | --- | ---: | ---: | ---: | --- |
| `build-candidate` | `src/ef/ef_0000_0ca7_front_preserved_corridor.asm` | `EF:0000..EF:0CA7` | 3239 | 0 | 3239 | `b4010203684b333d3841ab3df35037ba4fa2825c` |
| `build-candidate` | `src/ef/ef_0ca7_delivery_selector_helper_cluster.asm` | `EF:0CA7..EF:101B` | 884 | 884 | 0 | `67263f36ee80d3155ec61cce95d7194870b8c2d7` |
| `build-candidate` | `src/ef/ef_101b_4a40_map_tileset_sprite_table_data.asm` | `EF:101B..EF:4A40` | 14885 | 0 | 14885 | `6e3c7770032eabf33502d47f18c448999ffb2023` |
| `build-candidate` | `src/ef/ef_4a40_4e20_sound_stone_presentation_table_data.asm` | `EF:4A40..EF:4E20` | 992 | 0 | 992 | `ea78ee3d61cd39ebf81f5ac0793353e61ff7c41e` |
| `build-candidate` | `src/ef/ef_4e20_c51b_text_payload_data.asm` | `EF:4E20..EF:C51B` | 30459 | 0 | 30459 | `1419dd1b8b80745a5a22e78d498fcb67a60547aa` |
| `build-candidate` | `src/ef/ef_c51b_d56f_text_glyph_mask_tables.asm` | `EF:C51B..EF:D56F` | 4180 | 0 | 4180 | `73467ad28329342430e2add59df931780f2e488b` |
| `build-candidate` | `src/ef/ef_d56f_d6d4_debug_sound_menu_helpers.asm` | `EF:D56F..EF:D6D4` | 357 | 357 | 0 | `50ea92d8170a2fe213f113009bd9918f69a04d91` |
| `build-candidate` | `src/ef/ef_d6d4_eb5f_debug_menu_mixed_preserved_corridor.asm` | `EF:D6D4..EF:EB5F` | 5259 | 0 | 5259 | `600d9fdf1e4e1282c9f2eaebae1c1ae0b7792f2b` |
| `build-candidate` | `src/ef/asset_debug_menu_font.asm` | `EF:EB5F..EF:EF70` | 1041 | 1041 | 0 | `7d8195145f270d5d310df09b7c73a32cca868614` |
| `build-candidate` | `src/ef/table_141_data_unknown_efef70_asm.asm` | `EF:EF70..EF:EFB7` | 71 | 71 | 0 | `274b0fc73b39180dd07b1df5e5fd1077c481387d` |
| `build-candidate` | `src/ef/asset_debug_cursor_graphics.asm` | `EF:EFB7..EF:F0D7` | 288 | 288 | 0 | `d4aa5ac9ca83bf8da624ffab3ed1c95d0e85cdd8` |
| `build-candidate` | `src/ef/asset_bank_ef_gap_1_tailpadding.asm` | `EF:F0D7..EF:10000` | 3881 | 3881 | 0 | `8e09b47444551098bd77c1dd73e19f0a9ba0a71f` |

## Source Segments

### `src/ef/ef_0000_0ca7_front_preserved_corridor.asm`

| Range | Size | Name | SHA-1 |
| --- | ---: | --- | --- |
| n/a | 0 | `data-only protected span` | n/a |

Data gaps inside protected span:

- `EF:0000..EF:0CA7` (`3239` bytes, SHA-1 `b4010203684b333d3841ab3df35037ba4fa2825c`) `EfFrontPreservedCorridor`

Labels:

- `EF:0000 EfFrontPreservedCorridor`

Evidence:

- `notes/bank-ef-first-pass.md`
- `notes/ef-readable-source-split-queue.md`

### `src/ef/ef_0ca7_delivery_selector_helper_cluster.asm`

| Range | Size | Name | SHA-1 |
| --- | ---: | --- | --- |
| `EF:0CA7..EF:101B` | 884 | `DeliverySelectorHelperCluster` | `67263f36ee80d3155ec61cce95d7194870b8c2d7` |

Labels:

- `EF:0CA7 DeliverySelectorHelperCluster`

Evidence:

- `notes/delivery-row-helpers-ef0e67-ef0ead.md`
- `notes/selector-row-config-family-ef0ee8.md`
- `notes/timed-delivery-state-helpers-ef0f60-fdb-ff6.md`
- `notes/ef-readable-source-split-queue.md`

### `src/ef/ef_101b_4a40_map_tileset_sprite_table_data.asm`

| Range | Size | Name | SHA-1 |
| --- | ---: | --- | --- |
| n/a | 0 | `data-only protected span` | n/a |

Data gaps inside protected span:

- `EF:101B..EF:4A40` (`14885` bytes, SHA-1 `6e3c7770032eabf33502d47f18c448999ffb2023`) `EfMapTilesetSpriteTableData`

Labels:

- `EF:101B EfMapTilesetSpriteTableData`

Evidence:

- `notes/bank-ef-first-pass.md`
- `notes/ef-readable-source-split-queue.md`
- `notes/landing-profile-asset-families-ef105b-10ab-11cb-121b.md`

### `src/ef/ef_4a40_4e20_sound_stone_presentation_table_data.asm`

| Range | Size | Name | SHA-1 |
| --- | ---: | --- | --- |
| n/a | 0 | `data-only protected span` | n/a |

Data gaps inside protected span:

- `EF:4A40..EF:4E20` (`992` bytes, SHA-1 `ea78ee3d61cd39ebf81f5ac0793353e61ff7c41e`) `EfSoundStonePresentationTableData`

Labels:

- `EF:4A40 EfSoundStonePresentationTableData`

Evidence:

- `notes/bank-ef-first-pass.md`
- `notes/sound-stone-presentation-data-c4ac57.md`
- `notes/ef-readable-source-split-queue.md`

### `src/ef/ef_4e20_c51b_text_payload_data.asm`

| Range | Size | Name | SHA-1 |
| --- | ---: | --- | --- |
| n/a | 0 | `data-only protected span` | n/a |

Data gaps inside protected span:

- `EF:4E20..EF:C51B` (`30459` bytes, SHA-1 `1419dd1b8b80745a5a22e78d498fcb67a60547aa`) `EfTextPayloadData`

Labels:

- `EF:4E20 EfTextPayloadData`

Evidence:

- `notes/bank-ef-first-pass.md`
- `notes/ef-readable-source-split-queue.md`
- `notes/c2-ef-battle-text-contract-workahead.md`

### `src/ef/ef_c51b_d56f_text_glyph_mask_tables.asm`

| Range | Size | Name | SHA-1 |
| --- | ---: | --- | --- |
| n/a | 0 | `data-only protected span` | n/a |

Data gaps inside protected span:

- `EF:C51B..EF:D56F` (`4180` bytes, SHA-1 `73467ad28329342430e2add59df931780f2e488b`) `EfTextGlyphMaskTables`

Labels:

- `EF:C51B EfTextGlyphMaskTables`

Evidence:

- `notes/bank-ef-first-pass.md`
- `notes/text-token-glyph-run-stager-c44b3a-c44e61.md`
- `notes/ef-readable-source-split-queue.md`

### `src/ef/ef_d56f_d6d4_debug_sound_menu_helpers.asm`

| Range | Size | Name | SHA-1 |
| --- | ---: | --- | --- |
| `EF:D56F..EF:D6D4` | 357 | `DebugSoundMenuHelpers` | `50ea92d8170a2fe213f113009bd9918f69a04d91` |

Labels:

- `EF:D56F DebugSoundMenuHelpers`

Evidence:

- `notes/debug-menu-reachability-c0-c1-ef.md`
- `notes/bank-ef-first-pass.md`
- `notes/ef-readable-source-split-queue.md`
- `notes/ef-debug-sound-menu-prefix-d56f-d6d4.md`

### `src/ef/ef_d6d4_eb5f_debug_menu_mixed_preserved_corridor.asm`

| Range | Size | Name | SHA-1 |
| --- | ---: | --- | --- |
| n/a | 0 | `data-only protected span` | n/a |

Data gaps inside protected span:

- `EF:D6D4..EF:EB5F` (`5259` bytes, SHA-1 `600d9fdf1e4e1282c9f2eaebae1c1ae0b7792f2b`) `EfDebugMenuMixedPreservedCorridor`

Labels:

- `EF:D6D4 EfDebugMenuMixedPreservedCorridor`

Evidence:

- `notes/bank-ef-first-pass.md`
- `notes/debug-menu-reachability-c0-c1-ef.md`
- `notes/ef-readable-source-split-queue.md`
- `notes/ef-debug-sound-menu-prefix-d56f-d6d4.md`

### `src/ef/asset_debug_menu_font.asm`

| Range | Size | Name | SHA-1 |
| --- | ---: | --- | --- |
| `EF:EB5F..EF:EF70` | 1041 | `AssetDebugMenuFont` | `7d8195145f270d5d310df09b7c73a32cca868614` |

Labels:

- `EF:EB5F AssetDebugMenuFont`

Evidence:

- `refs/ebsrc-main/ebsrc-main/src/bankconfig/US/bank2F.asm`
- `refs/ebsrc-main/ebsrc-main/earthbound.yml`
- `build/asset-bank-ef.json`
- `notes/bank-ef-asset-data-map.md`

### `src/ef/table_141_data_unknown_efef70_asm.asm`

| Range | Size | Name | SHA-1 |
| --- | ---: | --- | --- |
| `EF:EF70..EF:EFB7` | 71 | `TableEfef70` | `274b0fc73b39180dd07b1df5e5fd1077c481387d` |

Labels:

- `EF:EF70 TableEfef70`

Evidence:

- `refs/ebsrc-main/ebsrc-main/src/bankconfig/US/bank2F.asm`
- `refs/ebsrc-main/ebsrc-main/earthbound.yml`
- `build/asset-bank-ef.json`
- `notes/bank-ef-asset-data-map.md`

### `src/ef/asset_debug_cursor_graphics.asm`

| Range | Size | Name | SHA-1 |
| --- | ---: | --- | --- |
| `EF:EFB7..EF:F0D7` | 288 | `AssetDebugCursorGraphics` | `d4aa5ac9ca83bf8da624ffab3ed1c95d0e85cdd8` |

Labels:

- `EF:EFB7 AssetDebugCursorGraphics`

Evidence:

- `refs/ebsrc-main/ebsrc-main/src/bankconfig/US/bank2F.asm`
- `refs/ebsrc-main/ebsrc-main/earthbound.yml`
- `build/asset-bank-ef.json`
- `notes/bank-ef-asset-data-map.md`

### `src/ef/asset_bank_ef_gap_1_tailpadding.asm`

| Range | Size | Name | SHA-1 |
| --- | ---: | --- | --- |
| `EF:F0D7..EF:10000` | 3881 | `AssetBankEFGap1TailPadding` | `8e09b47444551098bd77c1dd73e19f0a9ba0a71f` |

Labels:

- `EF:F0D7 AssetBankEFGap1TailPadding`

Evidence:

- `refs/ebsrc-main/ebsrc-main/src/bankconfig/US/bank2F.asm`
- `refs/ebsrc-main/ebsrc-main/earthbound.yml`
- `build/asset-bank-ef.json`
- `notes/bank-ef-asset-data-map.md`

## Notes

The scaffold preserves intentional source-adjacent data gaps from the manifest and validates each protected span against the original ROM bytes.
