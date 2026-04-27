# EF build-candidate byte ranges

This manifest records source slices promoted into the reusable source-bank scaffold pipeline.

## Summary

- ranges: `28`
- total bytes: `65536`
- source bytes: `14780`
- data gap bytes: `50756`

## Ranges

| Level | Source Path | Range | Span Bytes | Source Bytes | Data Gap Bytes | SHA-1 |
| --- | --- | --- | ---: | ---: | ---: | --- |
| `build-candidate` | `src/ef/ef_0000_00bb_enemy_flashing_helpers.asm` | `EF:0000..EF:00BB` | 187 | 187 | 0 | `77dd6f3f57c4a6fea5be7aa4af69a2691e32b8c7` |
| `build-candidate` | `src/ef/ef_00bb_0256_battle_overworld_visual_helpers.asm` | `EF:00BB..EF:0256` | 411 | 411 | 0 | `3c3e08e10a1dec3621ddfcfeef514509a9acc646` |
| `build-candidate` | `src/ef/ef_0256_027d_audio_pause_resume_flags.asm` | `EF:0256..EF:027D` | 39 | 39 | 0 | `9a99a99d847f6e82b9f4fa3bcd194daa2f18905d` |
| `build-candidate` | `src/ef/ef_027d_0591_overworld_entity_snapshot_helpers.asm` | `EF:027D..EF:0591` | 788 | 788 | 0 | `45d47823667c42199d00e777f6dc6110314aa187` |
| `build-candidate` | `src/ef/ef_0591_05a9_sram_signature_and_save_block_flags.asm` | `EF:0591..EF:05A9` | 24 | 0 | 24 | `7301afe764d5f3200bbbcab6bc2436e84975ecd4` |
| `build-candidate` | `src/ef/ef_05a9_0c3d_save_sram_helpers.asm` | `EF:05A9..EF:0C3D` | 1684 | 1684 | 0 | `e4fbde63d6b5388fcafd04510977c570aeed2702` |
| `build-candidate` | `src/ef/ef_0c3d_0ca7_front_unknown_tail_helpers.asm` | `EF:0C3D..EF:0CA7` | 106 | 106 | 0 | `1959bd78161c2d3b053fbb4a84349a3adbcdcdfa` |
| `build-candidate` | `src/ef/ef_0ca7_delivery_selector_helper_cluster.asm` | `EF:0CA7..EF:101B` | 884 | 884 | 0 | `67263f36ee80d3155ec61cce95d7194870b8c2d7` |
| `build-candidate` | `src/ef/ef_101b_4a40_map_tileset_sprite_table_data.asm` | `EF:101B..EF:4A40` | 14885 | 0 | 14885 | `6e3c7770032eabf33502d47f18c448999ffb2023` |
| `build-candidate` | `src/ef/ef_4a40_4e20_sound_stone_presentation_table_data.asm` | `EF:4A40..EF:4E20` | 992 | 0 | 992 | `ea78ee3d61cd39ebf81f5ac0793353e61ff7c41e` |
| `build-candidate` | `src/ef/ef_4e20_c51b_text_payload_data.asm` | `EF:4E20..EF:C51B` | 30459 | 0 | 30459 | `1419dd1b8b80745a5a22e78d498fcb67a60547aa` |
| `build-candidate` | `src/ef/ef_c51b_d56f_text_glyph_mask_tables.asm` | `EF:C51B..EF:D56F` | 4180 | 0 | 4180 | `73467ad28329342430e2add59df931780f2e488b` |
| `build-candidate` | `src/ef/ef_d56f_d6d4_debug_sound_menu_helpers.asm` | `EF:D56F..EF:D6D4` | 357 | 357 | 0 | `50ea92d8170a2fe213f113009bd9918f69a04d91` |
| `build-candidate` | `src/ef/ef_d6d4_d8b5_debug_sound_menu_controller.asm` | `EF:D6D4..EF:D8B5` | 481 | 481 | 0 | `7dfefdcb21fdb15ad5774c0b8e05d249a9456610` |
| `build-candidate` | `src/ef/ef_d8b5_d95e_debug_menu_option_strings.asm` | `EF:D8B5..EF:D95E` | 169 | 0 | 169 | `395083f64a645515a8e42c25127744e5764ec74c` |
| `build-candidate` | `src/ef/ef_d95e_dabd_debug_menu_graphics_state_init.asm` | `EF:D95E..EF:DABD` | 351 | 351 | 0 | `593aca35ad4b1bf4127ae9cc2d8ca981b37b8ac8` |
| `build-candidate` | `src/ef/ef_dabd_dcbc_debug_menu_text_number_helpers.asm` | `EF:DABD..EF:DCBC` | 511 | 511 | 0 | `69230efc6b0048c238d040518a61002058c4bc4c` |
| `build-candidate` | `src/ef/ef_dcbc_de1a_debug_check_position_overlay.asm` | `EF:DCBC..EF:DE1A` | 350 | 350 | 0 | `7be9bf793988efca02669a8a91b6ceea495b57bb` |
| `build-candidate` | `src/ef/ef_de1a_df0b_debug_view_character_overlay.asm` | `EF:DE1A..EF:DF0B` | 241 | 241 | 0 | `810ee840a220dbb001b044ad9d1df00b0b7b8895` |
| `build-candidate` | `src/ef/ef_df0b_e175_debug_overlay_tile_helpers.asm` | `EF:DF0B..EF:E175` | 618 | 618 | 0 | `15cd4ce61ad31ea3f03158483c285caf717d41d8` |
| `build-candidate` | `src/ef/ef_e175_eb1d_debug_menu_runtime_helpers.asm` | `EF:E175..EF:EB1D` | 2472 | 2472 | 0 | `622254c8aa62a39311c8331d5a5fc32a1dee77c6` |
| `build-candidate` | `src/ef/ef_eb1d_eb2a_debug_color_math_window_table.asm` | `EF:EB1D..EF:EB2A` | 13 | 0 | 13 | `49c3bca75bbbe59051ec87f6e80fc31946136449` |
| `build-candidate` | `src/ef/ef_eb2a_eb3d_debug_color_math_dma_reset.asm` | `EF:EB2A..EF:EB3D` | 19 | 19 | 0 | `b7703e2d448dca9da5dd3146081d989ae457fc32` |
| `build-candidate` | `src/ef/ef_eb3d_eb5f_debug_cursor_tilemap_data.asm` | `EF:EB3D..EF:EB5F` | 34 | 0 | 34 | `dd51f90c8b6debd5ab65cfcad48a0f1cf3a4fb6a` |
| `build-candidate` | `src/ef/asset_debug_menu_font.asm` | `EF:EB5F..EF:EF70` | 1041 | 1041 | 0 | `7d8195145f270d5d310df09b7c73a32cca868614` |
| `build-candidate` | `src/ef/table_141_data_unknown_efef70_asm.asm` | `EF:EF70..EF:EFB7` | 71 | 71 | 0 | `274b0fc73b39180dd07b1df5e5fd1077c481387d` |
| `build-candidate` | `src/ef/asset_debug_cursor_graphics.asm` | `EF:EFB7..EF:F0D7` | 288 | 288 | 0 | `d4aa5ac9ca83bf8da624ffab3ed1c95d0e85cdd8` |
| `build-candidate` | `src/ef/asset_bank_ef_gap_1_tailpadding.asm` | `EF:F0D7..EF:10000` | 3881 | 3881 | 0 | `8e09b47444551098bd77c1dd73e19f0a9ba0a71f` |

## Source Segments

### `src/ef/ef_0000_00bb_enemy_flashing_helpers.asm`

| Range | Size | Name | SHA-1 |
| --- | ---: | --- | --- |
| `EF:0000..EF:00BB` | 187 | `EnemyFlashingHelpers` | `77dd6f3f57c4a6fea5be7aa4af69a2691e32b8c7` |

Labels:

- `EF:0000 EnemyFlashingHelpers`

Evidence:

- `refs/ebsrc-main/ebsrc-main/src/bankconfig/US/bank2f.asm`
- `refs/ebsrc-main/ebsrc-main/src/battle/enemy_flashing_off.asm`
- `refs/ebsrc-main/ebsrc-main/src/battle/enemy_flashing_on.asm`
- `notes/bank-ef-first-pass.md`
- `notes/ef-readable-source-split-queue.md`
- `notes/ef-front-source-closure-0000-0ca7.md`

### `src/ef/ef_00bb_0256_battle_overworld_visual_helpers.asm`

| Range | Size | Name | SHA-1 |
| --- | ---: | --- | --- |
| `EF:00BB..EF:0256` | 411 | `BattleOverworldVisualHelpers` | `3c3e08e10a1dec3621ddfcfeef514509a9acc646` |

Labels:

- `EF:00BB BattleOverworldVisualHelpers`

Evidence:

- `refs/ebsrc-main/ebsrc-main/src/bankconfig/US/bank2f.asm`
- `notes/bank-ef-first-pass.md`
- `notes/ef-readable-source-split-queue.md`
- `notes/ef-front-source-closure-0000-0ca7.md`

### `src/ef/ef_0256_027d_audio_pause_resume_flags.asm`

| Range | Size | Name | SHA-1 |
| --- | ---: | --- | --- |
| `EF:0256..EF:027D` | 39 | `AudioPauseResumeFlags` | `9a99a99d847f6e82b9f4fa3bcd194daa2f18905d` |

Labels:

- `EF:0256 AudioPauseResumeFlags`

Evidence:

- `refs/ebsrc-main/ebsrc-main/src/bankconfig/US/bank2f.asm`
- `refs/ebsrc-main/ebsrc-main/src/audio/pause_music.asm`
- `refs/ebsrc-main/ebsrc-main/src/audio/resume_music.asm`
- `notes/bank-ef-first-pass.md`
- `notes/ef-readable-source-split-queue.md`
- `notes/ef-front-source-closure-0000-0ca7.md`

### `src/ef/ef_027d_0591_overworld_entity_snapshot_helpers.asm`

| Range | Size | Name | SHA-1 |
| --- | ---: | --- | --- |
| `EF:027D..EF:0591` | 788 | `OverworldEntitySnapshotHelpers` | `45d47823667c42199d00e777f6dc6110314aa187` |

Labels:

- `EF:027D OverworldEntitySnapshotHelpers`

Evidence:

- `refs/ebsrc-main/ebsrc-main/src/bankconfig/US/bank2f.asm`
- `notes/bank-ef-first-pass.md`
- `notes/ef-readable-source-split-queue.md`
- `notes/ef-front-source-closure-0000-0ca7.md`

### `src/ef/ef_0591_05a9_sram_signature_and_save_block_flags.asm`

| Range | Size | Name | SHA-1 |
| --- | ---: | --- | --- |
| n/a | 0 | `data-only protected span` | n/a |

Data gaps inside protected span:

- `EF:0591..EF:05A9` (`24` bytes, SHA-1 `7301afe764d5f3200bbbcab6bc2436e84975ecd4`) `EfSramSignatureAndSaveBlockFlags`

Labels:

- `EF:0591 EfSramSignatureAndSaveBlockFlags`

Evidence:

- `refs/ebsrc-main/ebsrc-main/src/bankconfig/US/bank2f.asm`
- `refs/ebsrc-main/ebsrc-main/include/symbols/bank2f.inc.asm`
- `notes/bank-ef-first-pass.md`
- `notes/ef-readable-source-split-queue.md`
- `notes/ef-front-source-closure-0000-0ca7.md`

### `src/ef/ef_05a9_0c3d_save_sram_helpers.asm`

| Range | Size | Name | SHA-1 |
| --- | ---: | --- | --- |
| `EF:05A9..EF:0C3D` | 1684 | `SaveSramHelperCluster` | `e4fbde63d6b5388fcafd04510977c570aeed2702` |

Labels:

- `EF:05A9 SaveSramHelperCluster`

Evidence:

- `refs/ebsrc-main/ebsrc-main/src/bankconfig/US/bank2f.asm`
- `refs/ebsrc-main/ebsrc-main/include/symbols/bank2f.inc.asm`
- `notes/bank-ef-first-pass.md`
- `notes/ef-readable-source-split-queue.md`
- `notes/ef-front-source-closure-0000-0ca7.md`

### `src/ef/ef_0c3d_0ca7_front_unknown_tail_helpers.asm`

| Range | Size | Name | SHA-1 |
| --- | ---: | --- | --- |
| `EF:0C3D..EF:0CA7` | 106 | `EfFrontUnknownTailHelpers` | `1959bd78161c2d3b053fbb4a84349a3adbcdcdfa` |

Labels:

- `EF:0C3D EfFrontUnknownTailHelpers`

Evidence:

- `refs/ebsrc-main/ebsrc-main/src/bankconfig/US/bank2f.asm`
- `refs/ebsrc-main/ebsrc-main/include/symbols/bank2f.inc.asm`
- `notes/bank-ef-first-pass.md`
- `notes/ef-readable-source-split-queue.md`
- `notes/ef-front-source-closure-0000-0ca7.md`

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

### `src/ef/ef_d6d4_d8b5_debug_sound_menu_controller.asm`

| Range | Size | Name | SHA-1 |
| --- | ---: | --- | --- |
| `EF:D6D4..EF:D8B5` | 481 | `DebugSoundMenuController` | `7dfefdcb21fdb15ad5774c0b8e05d249a9456610` |

Labels:

- `EF:D6D4 DebugSoundMenuController`

Evidence:

- `notes/debug-menu-reachability-c0-c1-ef.md`
- `notes/bank-ef-first-pass.md`
- `notes/ef-readable-source-split-queue.md`
- `notes/ef-debug-menu-controller-and-loader-d6d4-dabd.md`

### `src/ef/ef_d8b5_d95e_debug_menu_option_strings.asm`

| Range | Size | Name | SHA-1 |
| --- | ---: | --- | --- |
| n/a | 0 | `data-only protected span` | n/a |

Data gaps inside protected span:

- `EF:D8B5..EF:D95E` (`169` bytes, SHA-1 `395083f64a645515a8e42c25127744e5764ec74c`) `EfDebugMenuOptionStrings`

Labels:

- `EF:D8B5 EfDebugMenuOptionStrings`

Evidence:

- `refs/ebsrc-main/ebsrc-main/src/data/debug/menu_option_strings.asm`
- `notes/debug-menu-reachability-c0-c1-ef.md`
- `notes/bank-ef-first-pass.md`
- `notes/ef-debug-menu-controller-and-loader-d6d4-dabd.md`

### `src/ef/ef_d95e_dabd_debug_menu_graphics_state_init.asm`

| Range | Size | Name | SHA-1 |
| --- | ---: | --- | --- |
| `EF:D95E..EF:DABD` | 351 | `DebugMenuGraphicsAndStateInit` | `593aca35ad4b1bf4127ae9cc2d8ca981b37b8ac8` |

Labels:

- `EF:D95E DebugMenuGraphicsAndStateInit`

Evidence:

- `notes/debug-menu-reachability-c0-c1-ef.md`
- `notes/bank-ef-first-pass.md`
- `notes/ef-readable-source-split-queue.md`
- `notes/ef-debug-menu-controller-and-loader-d6d4-dabd.md`

### `src/ef/ef_dabd_dcbc_debug_menu_text_number_helpers.asm`

| Range | Size | Name | SHA-1 |
| --- | ---: | --- | --- |
| `EF:DABD..EF:DCBC` | 511 | `DebugMenuTextAndNumberHelpers` | `69230efc6b0048c238d040518a61002058c4bc4c` |

Labels:

- `EF:DABD DebugMenuTextAndNumberHelpers`

Evidence:

- `notes/debug-menu-reachability-c0-c1-ef.md`
- `notes/bank-ef-first-pass.md`
- `notes/ef-readable-source-split-queue.md`
- `notes/ef-debug-menu-runtime-closure-dabd-eb5f.md`

### `src/ef/ef_dcbc_de1a_debug_check_position_overlay.asm`

| Range | Size | Name | SHA-1 |
| --- | ---: | --- | --- |
| `EF:DCBC..EF:DE1A` | 350 | `DebugCheckPositionOverlayWriter` | `7be9bf793988efca02669a8a91b6ceea495b57bb` |

Labels:

- `EF:DCBC DebugCheckPositionOverlayWriter`

Evidence:

- `notes/debug-menu-reachability-c0-c1-ef.md`
- `notes/bank-ef-first-pass.md`
- `notes/ef-readable-source-split-queue.md`
- `notes/ef-debug-menu-runtime-closure-dabd-eb5f.md`

### `src/ef/ef_de1a_df0b_debug_view_character_overlay.asm`

| Range | Size | Name | SHA-1 |
| --- | ---: | --- | --- |
| `EF:DE1A..EF:DF0B` | 241 | `DebugViewCharacterOverlayWriter` | `810ee840a220dbb001b044ad9d1df00b0b7b8895` |

Labels:

- `EF:DE1A DebugViewCharacterOverlayWriter`

Evidence:

- `notes/debug-menu-reachability-c0-c1-ef.md`
- `notes/bank-ef-first-pass.md`
- `notes/ef-readable-source-split-queue.md`
- `notes/ef-debug-menu-runtime-closure-dabd-eb5f.md`

### `src/ef/ef_df0b_e175_debug_overlay_tile_helpers.asm`

| Range | Size | Name | SHA-1 |
| --- | ---: | --- | --- |
| `EF:DF0B..EF:E175` | 618 | `DebugOverlayTileHelpers` | `15cd4ce61ad31ea3f03158483c285caf717d41d8` |

Labels:

- `EF:DF0B DebugOverlayTileHelpers`

Evidence:

- `notes/debug-menu-reachability-c0-c1-ef.md`
- `notes/bank-ef-first-pass.md`
- `notes/ef-readable-source-split-queue.md`
- `notes/ef-debug-menu-runtime-closure-dabd-eb5f.md`

### `src/ef/ef_e175_eb1d_debug_menu_runtime_helpers.asm`

| Range | Size | Name | SHA-1 |
| --- | ---: | --- | --- |
| `EF:E175..EF:EB1D` | 2472 | `DebugMenuRuntimeAndMapViewHelpers` | `622254c8aa62a39311c8331d5a5fc32a1dee77c6` |

Labels:

- `EF:E175 DebugMenuRuntimeAndMapViewHelpers`

Evidence:

- `notes/debug-menu-reachability-c0-c1-ef.md`
- `notes/bank-ef-first-pass.md`
- `notes/ef-readable-source-split-queue.md`
- `notes/ef-debug-menu-runtime-closure-dabd-eb5f.md`

### `src/ef/ef_eb1d_eb2a_debug_color_math_window_table.asm`

| Range | Size | Name | SHA-1 |
| --- | ---: | --- | --- |
| n/a | 0 | `data-only protected span` | n/a |

Data gaps inside protected span:

- `EF:EB1D..EF:EB2A` (`13` bytes, SHA-1 `49c3bca75bbbe59051ec87f6e80fc31946136449`) `EfDebugColorMathWindowTable`

Labels:

- `EF:EB1D EfDebugColorMathWindowTable`

Evidence:

- `refs/ebsrc-main/ebsrc-main/src/bankconfig/US/bank2f.asm`
- `notes/bank-ef-first-pass.md`
- `notes/debug-menu-reachability-c0-c1-ef.md`
- `notes/ef-readable-source-split-queue.md`
- `notes/ef-debug-menu-runtime-closure-dabd-eb5f.md`

### `src/ef/ef_eb2a_eb3d_debug_color_math_dma_reset.asm`

| Range | Size | Name | SHA-1 |
| --- | ---: | --- | --- |
| `EF:EB2A..EF:EB3D` | 19 | `DebugColorMathDmaResetHelper` | `b7703e2d448dca9da5dd3146081d989ae457fc32` |

Labels:

- `EF:EB2A DebugColorMathDmaResetHelper`

Evidence:

- `refs/ebsrc-main/ebsrc-main/src/bankconfig/US/bank2f.asm`
- `notes/bank-ef-first-pass.md`
- `notes/debug-menu-reachability-c0-c1-ef.md`
- `notes/ef-readable-source-split-queue.md`
- `notes/ef-debug-menu-runtime-closure-dabd-eb5f.md`

### `src/ef/ef_eb3d_eb5f_debug_cursor_tilemap_data.asm`

| Range | Size | Name | SHA-1 |
| --- | ---: | --- | --- |
| n/a | 0 | `data-only protected span` | n/a |

Data gaps inside protected span:

- `EF:EB3D..EF:EB5F` (`34` bytes, SHA-1 `dd51f90c8b6debd5ab65cfcad48a0f1cf3a4fb6a`) `EfDebugCursorTilemapData`

Labels:

- `EF:EB3D EfDebugCursorTilemapData`

Evidence:

- `refs/ebsrc-main/ebsrc-main/src/bankconfig/US/bank2f.asm`
- `notes/bank-ef-first-pass.md`
- `notes/debug-menu-reachability-c0-c1-ef.md`
- `notes/ef-readable-source-split-queue.md`
- `notes/ef-debug-menu-runtime-closure-dabd-eb5f.md`

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
