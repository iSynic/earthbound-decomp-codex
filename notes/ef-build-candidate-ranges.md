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

- `EF:4E20..EF:69A1` (`7041` bytes, SHA-1 `01e65c5a7a785e159bf4ff974f298265569521e6`) `EfPreBattleTextPayloadData`
- `EF:69A1..EF:69BA` (`25` bytes, SHA-1 `33973d8aedbab180bc8c1d16f85be38becd9dfe7`) `EBattle5MsgBtlHpMaxRecovered`
- `EF:69BA..EF:69D2` (`24` bytes, SHA-1 `dee68da43f55467846a4643c14bd193aefad587d`) `EBattle5MsgBtlHpRecoveredAmount`
- `EF:69D2..EF:69EA` (`24` bytes, SHA-1 `178a8e52dbf9278e6a66f1bfc8b5e4d7dbc5065c`) `EBattle5MsgBtlPpRecoveredAmount`
- `EF:69EA..EF:69FF` (`21` bytes, SHA-1 `cbca03e002672de1af2ce08e0476abeb1818a953`) `EBattle5MsgBtlCheckOffenseAmount`
- `EF:69FF..EF:6A0D` (`14` bytes, SHA-1 `fb730cb9ad258a3376ee011615e57a6bb17319b9`) `EBattle5MsgBtlCheckDefenseAmount`
- `EF:6A0D..EF:6A24` (`23` bytes, SHA-1 `eaf532c68b3a87d9980a1732fc70a81627fc6cfd`) `EBattle5MsgBtlCheckAntiFire`
- `EF:6A24..EF:6A3C` (`24` bytes, SHA-1 `7bfa471b99fc69bf48792fe2102e215cc0abbcb2`) `EBattle5MsgBtlCheckAntiFreeze`
- `EF:6A3C..EF:6A54` (`24` bytes, SHA-1 `91e70fea8be98342875e635db61652bc75aac0ed`) `EBattle5MsgBtlCheckAntiFlash`
- `EF:6A54..EF:6A6C` (`24` bytes, SHA-1 `384312931078402facd3a775d197d37e6c2221cf`) `EBattle5MsgBtlCheckAntiParalysis`
- `EF:6A6C..EF:6A7F` (`19` bytes, SHA-1 `d35c8d638a6133af56367bfee05a00320394e969`) `EBattle5MsgBtlCheckBrainLevel0`
- `EF:6A7F..EF:6A99` (`26` bytes, SHA-1 `10763eb9cfd6b86fa000114461c0c0859e3a50ea`) `EBattle5MsgBtlCheckBrainLevel3`
- `EF:6A99..EF:6AB3` (`26` bytes, SHA-1 `bfaaec9540a8b30f2c7e48a7f999f357c1f45096`) `EBattle5MsgBtlMetamorphoseOk`
- `EF:6AB3..EF:6AC7` (`20` bytes, SHA-1 `d19194f31d229b82f858043b7526f136277ae4ab`) `EBattle5MsgBtlMetamorphoseFailed`
- `EF:6AC7..EF:6AE0` (`25` bytes, SHA-1 `1d28c385166c187b0eb36d3ad118adb8a44c2326`) `EBattle5MsgBtlDiamondized`
- `EF:6AE0..EF:6AFB` (`27` bytes, SHA-1 `77937f95269e6421b86b3d4693c44fd3843f5b7b`) `EBattle5MsgBtlParalysisInflicted`
- `EF:6AFB..EF:6B18` (`29` bytes, SHA-1 `3b3d3f415dce645e7699370021264b3c224e9266`) `EBattle5MsgBtlFeelingSickInflicted`
- `EF:6B18..EF:6B2F` (`23` bytes, SHA-1 `7812336a84bc28904a7bf104c7ec344f21c5819e`) `EBattle5MsgBtlPoisonInflicted`
- `EF:6B2F..EF:6B43` (`20` bytes, SHA-1 `07f8d05a02270dac2f4a6eaea27be633c7798cb8`) `EBattle5MsgBtlColdInflicted`
- `EF:6B43..EF:6B81` (`62` bytes, SHA-1 `df0b94b393a88f6993dcd766cc4571838b2a3e3e`) `EBattle5ObjectPronounSubtext`
- `EF:6B81..EF:6B98` (`23` bytes, SHA-1 `4fcd80b96a9421b4bc45dc0779d89f3291b6067c`) `EBattle5MsgBtlMushroomizedInflicted`
- `EF:6B98..EF:6BBB` (`35` bytes, SHA-1 `7ee966d54e30ac40a94c86441c2bec3492b67809`) `EBattle5MsgBtlPossessedInflicted`
- `EF:6BBB..EF:6BD3` (`24` bytes, SHA-1 `23f88af6a7604cc91dc3d3fa158a34a220fe16b7`) `EBattle5MsgBtlCryingInflicted`
- `EF:6BD3..EF:6BEF` (`28` bytes, SHA-1 `55c4d2930e8e056ca4cab10bbec98f0ab236360f`) `EBattle5MsgBtlImmobilizedInflicted`
- `EF:6BEF..EF:6C0B` (`28` bytes, SHA-1 `766017a093540d57429f454b420db0739f65a303`) `EBattle5MsgBtlSolidificationInflicted`
- `EF:6C0B..EF:6C3A` (`47` bytes, SHA-1 `30a911438fa0c874b4da136accd54ef893390ac5`) `EBattle5MsgBtlPsiSealInflicted`
- `EF:6C3A..EF:6C55` (`27` bytes, SHA-1 `af8d51b31d83087c92c0d9710c2f57976aa45e70`) `EBattle5MsgBtlStrangeInflicted`
- `EF:6C55..EF:6C6B` (`22` bytes, SHA-1 `4d5790f342b2e74a3d9baf1f2c69c44a5cf6e2a9`) `EBattle5MsgBtlAsleepInflicted`
- `EF:6C6B..EF:6C84` (`25` bytes, SHA-1 `5239e087feae40fca6e73094ad08a3a9a2700cd9`) `EBattle5MsgBtlIncapacitated`
- `EF:6C84..EF:6CC7` (`67` bytes, SHA-1 `9b17266ec30e32ad1633dbb3b8c70c20733d827f`) `EBattle5MsgSysNpcDeadFlyingMan`
- `EF:6CC7..EF:6CD0` (`9` bytes, SHA-1 `37c8b56b3e68d1f01245bd27c582578e20d4bb89`) `EBattle5FlyingManDeadBranchB`
- `EF:6CD0..EF:6CD9` (`9` bytes, SHA-1 `bac11a5d8dcd2becc5f3140ec40663275ff9fa96`) `EBattle5FlyingManDeadBranchC`
- `EF:6CD9..EF:6CE2` (`9` bytes, SHA-1 `e1ffb352ec6abd1b6e69f11fe10897371f250eca`) `EBattle5FlyingManDeadBranchD`
- `EF:6CE2..EF:6CEB` (`9` bytes, SHA-1 `0411f98368826c3c274b91e869979bd29b8c5894`) `EBattle5FlyingManDeadBranchE`
- `EF:6CEB..EF:6CFC` (`17` bytes, SHA-1 `8fabdceb9b80f856e60384c13517ca1e8f3538c7`) `EBattle5FlyingManRemovePartyMemberHelper`
- `EF:6CFC..EF:6D0A` (`14` bytes, SHA-1 `b28f114fc77d50a7abbd9735595c14530428c793`) `EBattle5FlyingManRemoveBranch2`
- `EF:6D0A..EF:6D18` (`14` bytes, SHA-1 `6803c77f9e4feb6a50f7126724d278419fa264e2`) `EBattle5FlyingManRemoveBranch3`
- `EF:6D18..EF:6D26` (`14` bytes, SHA-1 `32c251725020ca643d2e22839b21b6f579bd6f6c`) `EBattle5FlyingManRemoveBranch4`
- `EF:6D26..EF:6D2A` (`4` bytes, SHA-1 `f287881dd67b925df1531e0762bcc1b47a69fff1`) `EBattle5FlyingManRemoveBranch5`
- `EF:6D2A..EF:6D4C` (`34` bytes, SHA-1 `66e3b4d004b2cbe67b60093cc87a2587dad3e20d`) `EBattle5MsgSysNpcDeadTeddyBear`
- `EF:6D4C..EF:6D71` (`37` bytes, SHA-1 `1caf43c69b75eee750489f0cf121dd2e218876da`) `EBattle5MsgSysNpcDeadSuperPlushBear`
- `EF:6D71..EF:6D83` (`18` bytes, SHA-1 `fecde504825e2393a05568e18875e785481531f5`) `EBattle5MsgBtlEnemyDefeated`
- `EF:6D83..EF:6D96` (`19` bytes, SHA-1 `527d33a59d9804279c66b0a7cd83b4236874de51`) `EBattle5MsgBtlEnemyStoppedMoving`
- `EF:6D96..EF:6DA7` (`17` bytes, SHA-1 `ea833438b4ed642747c0190a152671889d2e2381`) `EBattle5MsgBtlEnemyBecameTame`
- `EF:6DA7..EF:6DB8` (`17` bytes, SHA-1 `c078f6115a03dcfc7e65035cb6ce43093994f26d`) `EBattle5MsgBtlEnemyDisappeared`
- `EF:6DB8..EF:6DD8` (`32` bytes, SHA-1 `135dd0b094f3e417766e94fc01ab38a4b98310b9`) `EBattle5MsgBtlEnemyMeltedAway`
- `EF:6DD8..EF:6DF0` (`24` bytes, SHA-1 `dd7e896c37e93caed82eeab43f111efc68324687`) `EBattle5MsgBtlEnemyBrokeIntoPieces`
- `EF:6DF0..EF:6E03` (`19` bytes, SHA-1 `0e8ac92ab6aaa62cfad2aa56ed8eed1af8fd76d1`) `EBattle5MsgBtlEnemyDestroyed`
- `EF:6E03..EF:6E19` (`22` bytes, SHA-1 `280ed6e4bf9525875d970089ca8a196f521a4446`) `EBattle5MsgBtlEnemyScrapped`
- `EF:6E19..EF:6E31` (`24` bytes, SHA-1 `954a4b24573c031af08645cd4eee93c55180f3d5`) `EBattle5MsgBtlEnemyReturnedToNormal`
- `EF:6E31..EF:6E4A` (`25` bytes, SHA-1 `b28bef70d6b861992262429f24ef463357850bfc`) `EBattle5MsgBtlEnemyReturnedToDust`
- `EF:6E4A..EF:6E67` (`29` bytes, SHA-1 `c6d274d913564c37c09cb02eb8a519422febc47c`) `EBattle5MsgBtlDiamondizedRecovered`
- `EF:6E67..EF:6E81` (`26` bytes, SHA-1 `d5c28bd7008e59e91d35fd8a238dfdab161bdce3`) `EBattle5MsgBtlParalysisRecovered`
- `EF:6E81..EF:6E97` (`22` bytes, SHA-1 `e4343b886d04ec9a5eb0807d4e98ad3d4a4f31db`) `EBattle5MsgBtlFeelingSickRecovered`
- `EF:6E97..EF:6EBC` (`37` bytes, SHA-1 `8c2836a58ae92c87ef94de7c948cb53687f7b637`) `EBattle5MsgBtlPoisonRemoved`
- `EF:6EBC..EF:6ED1` (`21` bytes, SHA-1 `42a2c1124dfdb1a894a49009bc0997dab13a340d`) `EBattle5MsgBtlColdRecovered`
- `EF:6ED1..EF:6EED` (`28` bytes, SHA-1 `34c08afa2f8f82674324e5b33f79aabb288b0794`) `EBattle5MsgBtlCryingRecovered`
- `EF:6EED..EF:6F0B` (`30` bytes, SHA-1 `7759e6d88ccd2107724e2effd474691264519a54`) `EBattle5MsgBtlImmobilizedRecovered`
- `EF:6F0B..EF:6F1E` (`19` bytes, SHA-1 `b9d1f92448dc963887cae2234364d16da454de28`) `EBattle5MsgBtlFrozenCanMove`
- `EF:6F1E..EF:6F38` (`26` bytes, SHA-1 `2115437f9f27384c25780b921af73ab04ad771ef`) `EBattle5MsgBtlStrangeRecovered`
- `EF:6F38..EF:6F54` (`28` bytes, SHA-1 `04314f2ae74e84c31b2b19944056b5b006e9aac9`) `EBattle5MsgBtlSunstrokeCured`
- `EF:6F54..EF:6F64` (`16` bytes, SHA-1 `7a0edecaff603fff5fbea3ab9a2c116a2abf63ba`) `EBattle5MsgBtlAsleepRecovered`
- `EF:6F64..EF:6F7C` (`24` bytes, SHA-1 `e835c44f305cf081f18da12269b343050e2048a8`) `EBattle5MsgBtlPsiSealRecovered`
- `EF:6F7C..EF:6F8E` (`18` bytes, SHA-1 `6c4ae3818b87052c84ba3a39b27e14c33bb92d44`) `EBattle5MsgBtlRevived`
- `EF:6F8E..EF:6F9A` (`12` bytes, SHA-1 `21ed1025a46bdab04851bccf116953f8bbeb000a`) `EBattle5MsgBtlReviveFailed`
- `EF:6F9A..EF:6FBD` (`35` bytes, SHA-1 `32b9f94859cc1256432748a68c7afd7904e57bfb`) `EBattle5MsgBtlShieldInstalled`
- `EF:6FBD..EF:6FD3` (`22` bytes, SHA-1 `75d0bac14ab6514e2ea88b25e1500ef00dbe9695`) `EBattle5MsgBtlShieldStrengthened`
- `EF:6FD3..EF:6FF4` (`33` bytes, SHA-1 `436ff24c2b098518d72aea4b6e92c7ae016598e4`) `EBattle5MsgBtlPowerShieldInstalled`
- `EF:6FF4..EF:700C` (`24` bytes, SHA-1 `91688e4579bfd0a98d936abb9eeb605696421bdb`) `EBattle5MsgBtlPowerShieldStrengthened`
- `EF:700C..EF:7032` (`38` bytes, SHA-1 `8e09d7147d7b1d6f5812c470721b0cf2a891391a`) `EBattle5MsgBtlPsychicShieldInstalled`
- `EF:7032..EF:7050` (`30` bytes, SHA-1 `95e260b622016c2efeadc2209d43bf3512c25816`) `EBattle5MsgBtlPsychicShieldStrengthened`
- `EF:7050..EF:707A` (`42` bytes, SHA-1 `ef9940bdeff8772e33413e1128347df7677d3049`) `EBattle5MsgBtlPsychicPowerShieldInstalled`
- `EF:707A..EF:7099` (`31` bytes, SHA-1 `b696662c257fbd2ce9510ea7933052b89d4fbf38`) `EBattle5MsgBtlPsychicPowerShieldStrengthened`
- `EF:7099..EF:70B1` (`24` bytes, SHA-1 `454c896efa3a20c3a15ce78eaf78527172fd73b1`) `EBattle5MsgBtlShieldExpired`
- `EF:70B1..EF:70D2` (`33` bytes, SHA-1 `e49767fe7e0ce9f98ca65b69ae3603fdb1521eb3`) `EBattle5MsgBtlPowerShieldReflectsAttack`
- `EF:70D2..EF:70FA` (`40` bytes, SHA-1 `1b955d8041a0b0aaf2eea5aa7d690e99a1ba285b`) `EBattle5MsgBtlPsychicPowerShieldReflectsPsiName`
- `EF:70FA..EF:7123` (`41` bytes, SHA-1 `03c5e8c29fe5f19b590afe6a060faa5889e44487`) `EBattle5MsgBtlPsychicShieldNullifiesPsiName`
- `EF:7123..EF:7142` (`31` bytes, SHA-1 `a3f610416e889477be5df78079b1d761d75480f8`) `EBattle5MsgBtlNeutralizeResult`
- `EF:7142..EF:7160` (`30` bytes, SHA-1 `146cd7f37e71519b0d2004be040ff876becb3cef`) `EBattle5MsgBtlNeutralizeMetamorph`
- `EF:7160..EF:7186` (`38` bytes, SHA-1 `594e1e727b025bec9e212a9aaadb94b68870fb34`) `EBattle5MsgBtlFranklinBadgeReflectsThunder`
- `EF:7186..EF:7192` (`12` bytes, SHA-1 `2084a70d00b0f28717b31a940e08dc392efd030a`) `EBattle4MsgBtlDiamondizedCannotMove`
- `EF:7192..EF:71B4` (`34` bytes, SHA-1 `ee123464ea5ef423e62887b3e7b8c0a900faf0a2`) `EBattle4MsgBtlParalysisCannotMove`
- `EF:71B4..EF:71CC` (`24` bytes, SHA-1 `56d7f2996d8139565c7d2080a335d91d2d2991c8`) `EBattle4MsgBtlNauseaCannotMove`
- `EF:71CC..EF:71DF` (`19` bytes, SHA-1 `936f8a6a64fe4a23f442f9c3bcaeeec34560b8c9`) `EBattle4MsgBtlPoisonStatus`
- `EF:71DF..EF:71F6` (`23` bytes, SHA-1 `414a41a2205d2aa0ede68bf9b4e640fa50158380`) `EBattle4MsgBtlAsleepStatus`
- `EF:71F6..EF:720C` (`22` bytes, SHA-1 `0991dca0b9526a694996eaedc929fd64a5cce488`) `EBattle4MsgBtlImmobilizedStatus`
- `EF:720C..EF:721E` (`18` bytes, SHA-1 `f88e28c612efd7475a9884c83b7096db8155978d`) `EBattle4MsgBtlPsiSealStatus`
- `EF:721E..EF:7221` (`3` bytes, SHA-1 `9a9dd4fc9529f0d0f21e55e79186969738ff5347`) `EBattle4PsiSealPlayerSideSoundBranch`
- `EF:7221..EF:7249` (`40` bytes, SHA-1 `dcfb9f7c3024d3ae05efc7ed93620eab47123ab9`) `EBattle4PsiSealResultText`
- `EF:7249..EF:725A` (`17` bytes, SHA-1 `e1e8b5c5040f3d970649b4b145463eaf03a3f380`) `EBattle4MsgBtlGuardOn`
- `EF:725A..EF:727F` (`37` bytes, SHA-1 `d358286d973116af553ce1a0f035ad1d45ab27ce`) `EBattle4MsgBtlFlyHoneyMindLost`
- `EF:727F..EF:72A0` (`33` bytes, SHA-1 `6bb0689abc8567d99a0b15ab932c3a0bf765117c`) `EBattle4MsgBtlHomesickRandom`
- `EF:72A0..EF:72B9` (`25` bytes, SHA-1 `e82ec910c7592d8d35e0390774f11d0b1f322757`) `EBattle4MsgBtlHomesickThoughtMom`
- `EF:72B9..EF:72DB` (`34` bytes, SHA-1 `2d9e60b39dd3262f51e1440eaca477ff6fb3fc0a`) `EBattle4MsgBtlHomesickCravingFood`
- `EF:72DB..EF:72F6` (`27` bytes, SHA-1 `34003ffbe658ce975f6ccf063e23d3fed6328071`) `EBattle4MsgBtlHomesickLostMotivation`
- `EF:72F6..EF:72F7` (`1` bytes, SHA-1 `c4ea21bb365bbeeaf5f2c654883e56d11e43c44e`) `EBattle4MsgBtlRunawayFiveBreakIn`
- `EF:72F7..EF:733D` (`70` bytes, SHA-1 `d196be4d816335a0625788e2688c097ac7643009`) `EBattle4MsgBtlRunawayFiveBreakInFailed`
- `EF:733D..EF:7415` (`216` bytes, SHA-1 `cbac0b9bda5afd16cfeb868e2ab0cca1e264a1f4`) `EBattle4MsgBtlRunawayFiveBreakInSucceeded`
- `EF:7415..EF:743B` (`38` bytes, SHA-1 `81313c365a179948200316a3ecdbd5af3b80cef3`) `EBattle4MsgBtlPooBreakIn`
- `EF:743B..EF:745F` (`36` bytes, SHA-1 `0c94d0a4d445894725aaefaee75c40ff2e9d39c1`) `EBattle4MsgBtlPooStarstormReveal`
- `EF:745F..EF:749D` (`62` bytes, SHA-1 `727799622495458a59d956ae265b52e126ff9e17`) `EBattle4MsgBtlPokeyTalkRandom`
- `EF:749D..EF:74B0` (`19` bytes, SHA-1 `6ff4d647c88229bd1f60ddf0a4bafd728e9b1e5b`) `EBattle4MsgBtlPokeyPlayedDead`
- `EF:74B0..EF:74C9` (`25` bytes, SHA-1 `62861e3d1b1b19fb77a2b8518e14ea9199f0343e`) `EBattle4MsgBtlPokeyPretendedCry`
- `EF:74C9..EF:74E6` (`29` bytes, SHA-1 `f993d969d77773f68e357daa1c19e75e0a99d69a`) `EBattle4MsgBtlPokeyApologized`
- `EF:74E6..EF:74FA` (`20` bytes, SHA-1 `e750f9faef3fc1bcf8ef9378a88b5f4778b47499`) `EBattle4MsgBtlPokeyThoughtToSelf`
- `EF:74FA..EF:7514` (`26` bytes, SHA-1 `4f14bd39c5448b7f9124ef6ac3f0700332d004f9`) `EBattle4MsgBtlPokeyActedInnocent`
- `EF:7514..EF:7530` (`28` bytes, SHA-1 `b7989bfe3e2065c2c0ef97b711ccf26d4706496f`) `EBattle4MsgBtlPokeySmiledSincerely`
- `EF:7530..EF:7548` (`24` bytes, SHA-1 `5929c9017c057517713d38a6ee897b3d29ff2915`) `EBattle4MsgBtlPokeyComplained`
- `EF:7548..EF:7569` (`33` bytes, SHA-1 `da8410480a860a2f8541bc06c10e87107d9bc134`) `EBattle4MsgBtlPokeyEdgedCloser`
- `EF:7569..EF:7579` (`16` bytes, SHA-1 `a5c0a43b5021b7c9d03729377bf61d1f51c06acb`) `EBattle4MsgBtlMyDogHowling`
- `EF:7579..EF:7591` (`24` bytes, SHA-1 `fe848981a1676bc95dc4b02c8262e536d9e6f80c`) `EBattle4MsgBtlPickeyTalk`
- `EF:7591..EF:7593` (`2` bytes, SHA-1 `0ca623e2855f2c75c842ad302fe820e41b4d197d`) `EBattle4MsgBtlTonyTalk`
- `EF:7593..EF:75AB` (`24` bytes, SHA-1 `d751fe2f17af56e2dc089f3204a9d23240a8ddf9`) `EBattle4MsgBtlBalmonTalk`
- `EF:75AB..EF:75C2` (`23` bytes, SHA-1 `3a053f08b2ec79049925f079d8b40170757597b4`) `EBattle4MsgBtlDamageAmount`
- `EF:75C2..EF:75D9` (`23` bytes, SHA-1 `edfab9740fc98f70467246c48b24749140cb7442`) `EBattle4MsgBtlMortalDamageAmount`
- `EF:75D9..EF:75F0` (`23` bytes, SHA-1 `3a053f08b2ec79049925f079d8b40170757597b4`) `EBattle4MsgBtlSmashDamageAmount`
- `EF:75F0..EF:7607` (`23` bytes, SHA-1 `edfab9740fc98f70467246c48b24749140cb7442`) `EBattle4MsgBtlMortalSmashDamageAmount`
- `EF:7607..EF:7624` (`29` bytes, SHA-1 `806a7ef398d67cb517fa40d0c53b297828f651d4`) `EBattle4MsgBtlDamageToDeathAmount`
- `EF:7624..EF:7630` (`12` bytes, SHA-1 `4ea6c0dfa6c448606b728bd676b9541a300edcc8`) `EBattle4MsgBtlSmashPlayer`
- `EF:7630..EF:763C` (`12` bytes, SHA-1 `d6e222f2f3092a8dbb1df396ebb3a8e82b71ff61`) `EBattle4MsgBtlSmashMonster`
- `EF:763C..EF:7655` (`25` bytes, SHA-1 `2f17677a234132a95abbcfc211c405e544cf70fc`) `EBattle4MsgBtlShootDodged`
- `EF:7655..EF:766E` (`25` bytes, SHA-1 `2f17677a234132a95abbcfc211c405e544cf70fc`) `EBattle4MsgBtlBashDodged`
- `EF:766E..EF:7682` (`20` bytes, SHA-1 `6097e90c945e2f040dfd0fac365f206f0fe77d8d`) `EBattle4MsgBtlStatusNoEffect`
- `EF:7682..EF:7696` (`20` bytes, SHA-1 `6097e90c945e2f040dfd0fac365f206f0fe77d8d`) `EBattle4AdjacentNoEffectText`
- `EF:7696..EF:76B3` (`29` bytes, SHA-1 `e4113ef4fa47015dc03660c723c49ae26e239e23`) `EBattle4MsgBtlNoVisibleEffect`
- `EF:76B3..EF:76C7` (`20` bytes, SHA-1 `6097e90c945e2f040dfd0fac365f206f0fe77d8d`) `EBattle4MsgBtlNoEffectVariantC`
- `EF:76C7..EF:76D8` (`17` bytes, SHA-1 `1110635d12eaf03417de5aa31df997cab60c78a3`) `EBattle4MsgBtlMissPhysical`
- `EF:76D8..EF:76FD` (`37` bytes, SHA-1 `033b47d37cc1f9de69b043c95cb3c5397bf50dd1`) `EBattle4MsgBtlMissShoot`
- `EF:76FD..EF:7710` (`19` bytes, SHA-1 `d96d3e5e48371da5b741502fdc4f7a176cbd001a`) `EBattle4MsgBtlTargetNotExist`
- `EF:7710..EF:7729` (`25` bytes, SHA-1 `3cbd6bb358b9f9607b00e49444509e19f0afa236`) `EBattle4MsgBtlHpSuckSelfDrain`
- `EF:7729..EF:773F` (`22` bytes, SHA-1 `f8dba4e9c54f6f73c48303350ff61ab1c781e140`) `EBattle4MsgBtlHpSuckAmount`
- `EF:773F..EF:7755` (`22` bytes, SHA-1 `6232b10ccb1d72f3eadde7a851e2688209a5c83a`) `EBattle4MsgBtlPpDrainAmount`
- `EF:7755..EF:7768` (`19` bytes, SHA-1 `97622bb4a3f2a58999cb73e624a6e6dd4a2bfe67`) `EBattle4MsgBtlPpDrainTarget`
- `EF:7768..EF:7787` (`31` bytes, SHA-1 `210944d8fe14331b7fab9ff513e052ec49376722`) `EBattle4MsgBtlStrangeDamage`
- `EF:7787..EF:77B1` (`42` bytes, SHA-1 `9b8f7fc7618de1531e7d1434952a808da5777b06`) `EBattle4MsgBtlPoisonDamage`
- `EF:77B1..EF:77DB` (`42` bytes, SHA-1 `e1107c8d05e467a473077d1c58c466c9a116e071`) `EBattle4MsgBtlSunstrokeDamage`
- `EF:77DB..EF:77FD` (`34` bytes, SHA-1 `128d1011da049119cb9abfd21c65fa7cfec2bab4`) `EBattle4MsgBtlColdDamage`
- `EF:77FD..EF:7810` (`19` bytes, SHA-1 `bf11a9604ab664ba99d8259cf9a94fd91e386065`) `EBattle8MsgBtlCallForHelpEnemyJoined`
- `EF:7810..EF:7824` (`20` bytes, SHA-1 `bc9c731025178de4aa8c5dd234c7df273376bf43`) `EBattle8MsgBtlCallForHelpSeedSprouted`
- `EF:7824..EF:7830` (`12` bytes, SHA-1 `37eb2ca0de50d3f88b762f3cefb361d0d5f08cae`) `EBattle8MsgBtlCallForHelpNoOneCame`
- `EF:7830..EF:7843` (`19` bytes, SHA-1 `0a637d9c7d18747424692410bf1e652aaff3533e`) `EBattle8MsgBtlCallForHelpSeedNoSprout`
- `EF:7843..EF:7858` (`21` bytes, SHA-1 `52dfe17ffa36d7b426f1aa12d86779148c6094ad`) `EBattle8MsgBtlTimeStopReturn`
- `EF:7858..EF:7866` (`14` bytes, SHA-1 `4d5a11d42293acfb56e1cf0d8374921883580b28`) `EBattle8MsgBtlAppearAttacked`
- `EF:7866..EF:7879` (`19` bytes, SHA-1 `a2a870ec7ee0273ca58ff0fbabc06ce35724819d`) `EBattle8MsgBtlAppearBlockedWay`
- `EF:7879..EF:788B` (`18` bytes, SHA-1 `601418a2ba5572f9579db119b2a2ae80bc99014b`) `EBattle8MsgBtlAppearCameAfterYou`
- `EF:788B..EF:789C` (`17` bytes, SHA-1 `5e7a280e02b5f6f0df4c30b2ed5064150d20ba32`) `EBattle8MsgBtlAppearTrappedYou`
- `EF:789C..EF:78AB` (`15` bytes, SHA-1 `f6eeb8fa2be831dc6287125509ba6b3cdfd6a6f1`) `EBattle8MsgBtlFinalEncounter4`
- `EF:78AB..EF:78B8` (`13` bytes, SHA-1 `278a3e4ed17a269f7ffc5ccee8e587fe2b5ba6fe`) `EBattle8MsgBtlFinalEncounter5`
- `EF:78B8..EF:78C7` (`15` bytes, SHA-1 `f05800508c53134fc535d6cd050404dae1eef43f`) `EBattle8MsgBtlFinalEncounter6`
- `EF:78C7..EF:78D8` (`17` bytes, SHA-1 `2080ccac7302058d749a169170a56a1ebb9bdfb2`) `EBattle8MsgBtlFinalEncounter7`
- `EF:78D8..EF:78F7` (`31` bytes, SHA-1 `26ee97fbd73c9c60ab94c8163458502711d6a0b3`) `EBattle8MsgBtlSurpriseOpeningPlayer`
- `EF:78F7..EF:790B` (`20` bytes, SHA-1 `90c7110d1d12d06be949f877d90c179117defef6`) `EBattle8MsgBtlSurpriseOpeningMonster`
- `EF:790B..EF:792B` (`32` bytes, SHA-1 `411101a02bc0b8a6fe05ac3ac40abea3ba061f6f`) `EBattle8GroupActorOpeningHelper`
- `EF:792B..EF:792E` (`3` bytes, SHA-1 `4a27df79273058f0219426b59dd2b8b9f2b7d78c`) `EBattle8GroupActorOpeningSingular`
- `EF:792E..EF:793C` (`14` bytes, SHA-1 `ee4e526a2a39700402be4dad3ef1a53cfcde90ee`) `EBattle8GroupActorOpeningCohort`
- `EF:793C..EF:794B` (`15` bytes, SHA-1 `575504d3e9b534fc31e2c3ed57f5a5ef06814f23`) `EBattle8GroupActorOpeningCohorts`
- `EF:794B..EF:796C` (`33` bytes, SHA-1 `19c340b43361fe13f2bcb709b89643f229c6236b`) `EBattle8GroupActorFinalHelper`
- `EF:796C..EF:7970` (`4` bytes, SHA-1 `56025a7a5d5a8ee1a1c68a2f5b88491a8d4e5976`) `EBattle8GroupActorFinalSingular`
- `EF:7970..EF:797F` (`15` bytes, SHA-1 `5c3eb0d5485504b3e04a52ec3da5d24b7bd36567`) `EBattle8GroupActorFinalCohort`
- `EF:797F..EF:798F` (`16` bytes, SHA-1 `4f96cd2005bdb1ee1cd918cb471cff574f07aa8d`) `EBattle8GroupActorFinalCohorts`
- `EF:798F..EF:79B1` (`34` bytes, SHA-1 `382d187af964992ccb3bc63695695030b0d277fe`) `EBattle8GroupActorSurpriseHelper`
- `EF:79B1..EF:79B6` (`5` bytes, SHA-1 `a10ad7f83b45f191f7dd962fa5ba655b21cc0a66`) `EBattle8GroupActorPossessiveSingular`
- `EF:79B6..EF:79C6` (`16` bytes, SHA-1 `1cbb5a4d47444c21001efd34672b4d656c444f4f`) `EBattle8GroupActorPossessiveCohort`
- `EF:79C6..EF:79D7` (`17` bytes, SHA-1 `d007527ebf6d4dc0c0c9d48da65c9fd8cfb6bbc8`) `EBattle8GroupActorPossessiveCohorts`
- `EF:79D7..EF:79E6` (`15` bytes, SHA-1 `221d916a6e712021994e7c4684b3a4e4461f3256`) `EBattle8MsgBtlPlayerWin`
- `EF:79E6..EF:79EF` (`9` bytes, SHA-1 `22fde23f6d3e83b620160063961a09dd94fb0224`) `EBattle8PlayerWinEventBranch`
- `EF:79EF..EF:7A0A` (`27` bytes, SHA-1 `b16daf1c08292f4100a4100aacce1e17463db462`) `EBattle8PlayerWinExperienceText`
- `EF:7A0A..EF:7A14` (`10` bytes, SHA-1 `a1bd985ecd904e4dc7f4b9196d65bc24312ebb85`) `EBattle8PlayerWinHomesickBranch`
- `EF:7A14..EF:7A28` (`20` bytes, SHA-1 `e05701efbb9a38a5cea8b6cfcbd2c2fd0ff16135`) `EBattle8MsgBtlPlayerWinBoss`
- `EF:7A28..EF:7A4D` (`37` bytes, SHA-1 `4d2e54e69418be3f2b2317a6b4bda0b7ed87a1a8`) `EBattle8MsgBtlPlayerWinForce`
- `EF:7A4D..EF:7A66` (`25` bytes, SHA-1 `672a4fbbe3b373a33f71987733c859a721c6a601`) `EBattle8MsgBtlMonsterWin`
- `EF:7A66..EF:7A7D` (`23` bytes, SHA-1 `984036287db549d282f5beff29201f2d2b9ca871`) `EBattle8MsgBtlLevelUp`
- `EF:7A7D..EF:7A97` (`26` bytes, SHA-1 `ec77fa82818ea8cecc7c4834eeabfd2c57885a80`) `EBattle8MsgBtlLevelOffenseUp`
- `EF:7A97..EF:7AB1` (`26` bytes, SHA-1 `9d2dc4ed5905762d1a852394c42a29488fd25c44`) `EBattle8MsgBtlLevelDefenseUp`
- `EF:7AB1..EF:7AC9` (`24` bytes, SHA-1 `39b68910ac9dd7206a5bee0f0e8f633911b62986`) `EBattle8MsgBtlLevelSpeedUp`
- `EF:7AC9..EF:7AE0` (`23` bytes, SHA-1 `4a7050baace11ee1ea47ee40d14fb3d7b638b6dc`) `EBattle8MsgBtlLevelGutsUp`
- `EF:7AE0..EF:7AFB` (`27` bytes, SHA-1 `df79e167961329b312903fb495c4f9be48264ce9`) `EBattle8MsgBtlLevelVitalityUp`
- `EF:7AFB..EF:7B11` (`22` bytes, SHA-1 `3bd4ef6250187c7e7ddce8351afe96909c3aaa0a`) `EBattle8MsgBtlLevelIqUp`
- `EF:7B11..EF:7B28` (`23` bytes, SHA-1 `ef0f8019e02b166fe0aba14ad12df591443834e7`) `EBattle8MsgBtlLevelLuckUp`
- `EF:7B28..EF:7B46` (`30` bytes, SHA-1 `ecb58cf466d840e103faca3c57ebf8972fd1d725`) `EBattle8MsgBtlLevelMaxHpUp`
- `EF:7B46..EF:7B64` (`30` bytes, SHA-1 `f319f6186d7ebe34933682c772778e6b1100214e`) `EBattle8MsgBtlLevelMaxPpUp`
- `EF:7B64..EF:7B77` (`19` bytes, SHA-1 `b9e211e8574e37ce78c2d391d2b43777f2eb3ff3`) `EBattle8MsgBtlLearnPsi`
- `EF:7B77..EF:7B83` (`12` bytes, SHA-1 `b6be0ba66868c82cafdd691ac712705f421cd14f`) `EBattle8ByteSubstitutionPsiNameText`
- `EF:7B83..EF:7B85` (`2` bytes, SHA-1 `d13061bfe442388f8bf8b53be38aa80ed585e8b5`) `EBattle8PointerSubstitutionIntroState`
- `EF:7B85..EF:7BA0` (`27` bytes, SHA-1 `0b507165fcb107b37b9f7d92fdf7728fb2dff65a`) `EBattle8PointerSubstitutionSweetBranch`
- `EF:7BA0..EF:7BA2` (`2` bytes, SHA-1 `d13061bfe442388f8bf8b53be38aa80ed585e8b5`) `EBattle8PointerSubstitutionBranch2State`
- `EF:7BA2..EF:7BBF` (`29` bytes, SHA-1 `4a8f6b390ce34f65d348108205b2f550d4323e90`) `EBattle8PointerSubstitutionTearsBranch`
- `EF:7BBF..EF:7BC1` (`2` bytes, SHA-1 `d13061bfe442388f8bf8b53be38aa80ed585e8b5`) `EBattle8PointerSubstitutionBranch3State`
- `EF:7BC1..EF:7BDF` (`30` bytes, SHA-1 `20ff702f734c16985cdf2024350476ddbae5485a`) `EBattle8PointerSubstitutionOhBabyBranch`
- `EF:7BDF..EF:7C42` (`99` bytes, SHA-1 `ac0008afdd533cbce642a6a974fdc139a6e12e2e`) `EBattle8MsgBtlPresentByteSubstitution`
- `EF:7C42..EF:7C73` (`49` bytes, SHA-1 `9883fd43ae25bfc47c43f439c44c7f9b697743ab`) `EBattle8PresentRecipientDeadText`
- `EF:7C73..EF:7C89` (`22` bytes, SHA-1 `8a967e4efbdbc4b30f8ce9df0b7383b475aafb7b`) `EBattle8PresentInventoryFullText`
- `EF:7C89..EF:7CB4` (`43` bytes, SHA-1 `6c65899112a80c79c027fd860a338bc055828858`) `EBattle8PresentThrowAwayPrompt`
- `EF:7CB4..EF:7CED` (`57` bytes, SHA-1 `cdf2ec69a05a549e316427fe56a0ce913d6853ba`) `EBattle8PresentAbandonPrompt`
- `EF:7CED..EF:7CF8` (`11` bytes, SHA-1 `fc32170687965f02c20effcc7bc3d9882392ae4b`) `EBattle8PresentAbandonRetryText`
- `EF:7CF8..EF:7D0F` (`23` bytes, SHA-1 `2049a2c4eb026d5a9e973d3a2c55b9b559cf1fd4`) `EBattle8PresentAbandonConfirmedText`
- `EF:7D0F..EF:7D83` (`116` bytes, SHA-1 `e03d93926ccfc1c23b3e4432788f9c8b83303541`) `EBattle8PresentDropSelectionPrompt`
- `EF:7D83..EF:7DBE` (`59` bytes, SHA-1 `de1a1a6d3283e8ab312a1f6c10c88035bb0d8796`) `EBattle8PresentDropConfirmedText`
- `EF:7DBE..EF:7DD5` (`23` bytes, SHA-1 `8b1dce22187c4631cb6f88b5cb74df4b81b50070`) `EBattle8PresentDropForbiddenText`
- `EF:7DD5..EF:7E25` (`80` bytes, SHA-1 `dafcd39be3495506595588a2d98ec0bee797af4f`) `EBattle8MsgBtlCheckPresentGetByteSubstitution`
- `EF:7E25..EF:7E3E` (`25` bytes, SHA-1 `326d9aa5613a268a7cf091c729ebce805764c396`) `EBattle2MsgBtlPpDown`
- `EF:7E3E..EF:7E55` (`23` bytes, SHA-1 `62b508e63eb223b99d8b88f4ced5c3d19c6ec3bf`) `EBattle2MsgBtlOkoru`
- `EF:7E55..EF:7E70` (`27` bytes, SHA-1 `ad403c9d5c62af3b63a0c2073426d080edae4595`) `EBattle2MsgBtlKitanaiKotoba`
- `EF:7E70..EF:7E88` (`24` bytes, SHA-1 `d4cc7c09fd548f062cece1a70ac73fd9964ef968`) `EBattle2MsgBtlSuibun`
- `EF:7E88..EF:7EAC` (`36` bytes, SHA-1 `7adc1d09fead93fcb2723913006fbb6a7583ebd4`) `EBattle2MsgBtlEnergy`
- `EF:7EAC..EF:7ED5` (`41` bytes, SHA-1 `0bb466bd8007c342c6a9297891c822d2673299ed`) `EBattle2MsgBtlDokuKamituki`
- `EF:7ED5..EF:7F02` (`45` bytes, SHA-1 `5d6e6f3b90307c29703ea2ea2a8b9269e44b7d37`) `EBattle2MsgBtlYoroMissile`
- `EF:7F02..EF:7F1E` (`28` bytes, SHA-1 `598fb84e36c1c4e781b7776dd6819c825c857d4f`) `EBattle2MsgBtlMultiAttack`
- `EF:7F1E..EF:7F32` (`20` bytes, SHA-1 `52fa387f2cbecca8ff2195b8de671309037c6804`) `EBattle2MsgBtlMigamae`
- `EF:7F32..EF:7F5A` (`40` bytes, SHA-1 `85f388be8449a78fd1d47b3faec59d47cf1a0f99`) `EBattle2MsgBtlFireball`
- `EF:7F5A..EF:7F7B` (`33` bytes, SHA-1 `b0142cf7c5087b89a62952b0991c1bd0dbd913fb`) `EBattle2MsgBtlGekitotu`
- `EF:7F7B..EF:7F9A` (`31` bytes, SHA-1 `a357002a69f1b46b6a76a7e9b3055c7bb0c77775`) `EBattle2MsgBtlKarate`
- `EF:7F9A..EF:7FC3` (`41` bytes, SHA-1 `75819d5a006c32395c7a2a2cc2bacff2436c788e`) `EBattle2MsgBtlTomoe`
- `EF:7FC3..EF:7FE0` (`29` bytes, SHA-1 `69f0796dc2b04c37be3fb915a1eda2ddb512dbc1`) `EBattle2MsgBtlBousou`
- `EF:7FE0..EF:7FFC` (`28` bytes, SHA-1 `3e2a4bdea4fc98b6be491c43db53802c41bde675`) `EBattle2MsgBtlKnife`
- `EF:7FFC..EF:8010` (`20` bytes, SHA-1 `5cd8bbe977488af7d4e836905a40f20d2543df07`) `EBattle2MsgBtlTossin`
- `EF:8010..EF:8026` (`22` bytes, SHA-1 `8425ae9463d5386f41bf5748ea3474b581fccdfd`) `EBattle2MsgBtlKamituki`
- `EF:8026..EF:804B` (`37` bytes, SHA-1 `f923668a1fc483512cc1b511ed685041e859caf3`) `EBattle2MsgBtlHikkaki`
- `EF:804B..EF:806D` (`34` bytes, SHA-1 `003a2d6cffe3fa65dd03c9665a3e70afdddc4ff1`) `EBattle2MsgBtlSippo`
- `EF:806D..EF:808D` (`32` bytes, SHA-1 `c683c425d77fd742eacc25e674d6f856cad46a72`) `EBattle2MsgBtlNoshikakari`
- `EF:808D..EF:80AC` (`31` bytes, SHA-1 `1d59a71f4c62e68ddf8b5529ee3d7a0c81c4b84a`) `EBattle2MsgBtlKamibukuro`
- `EF:80AC..EF:80C4` (`24` bytes, SHA-1 `68c5e94a8b1ecc6ec2ddac6e066621481fe6f4fe`) `EBattle2MsgBtlKonbou`
- `EF:80C4..EF:80E4` (`32` bytes, SHA-1 `be3cd61d6d790466e389c8d4a19deb52b8a4eda4`) `EBattle2MsgBtlTatumaki`
- `EF:80E4..EF:8109` (`37` bytes, SHA-1 `b3f9f938dce38896c987ec9240ded077a1bfdfbf`) `EBattle2MsgBtlWater`
- `EF:8109..EF:812B` (`34` bytes, SHA-1 `53867573d3ca72ac82a92a2691f1b2c1a0dc6a19`) `EBattle2MsgBtlFutekiSmile`
- `EF:812B..EF:814F` (`36` bytes, SHA-1 `e74b9c9ae63002c1db3ea7abf8cb17562ba686c6`) `EBattle2MsgBtlLoudSmile`
- `EF:814F..EF:8167` (`24` bytes, SHA-1 `1406b3b5c44491ee07f0035ec553474792d6a55f`) `EBattle2MsgBtlNijiriyoru`
- `EF:8167..EF:8186` (`31` bytes, SHA-1 `a6d127caa5d9da57e9250b5ff7efdb2c9a62ff2a`) `EBattle2MsgBtlTubuyaki1`
- `EF:8186..EF:81A5` (`31` bytes, SHA-1 `b72d3a435ff08c08ca000b008f4655333c269777`) `EBattle2MsgBtlTubuyaki2`
- `EF:81A5..EF:81C4` (`31` bytes, SHA-1 `e01da5c379b716391ea472922d569164ca7fc4a1`) `EBattle2MsgBtlTubuyaki3`
- `EF:81C4..EF:81D7` (`19` bytes, SHA-1 `c0fbd669a88ec949c2a21f88712018535491f99f`) `EBattle2MsgBtlKorobu`
- `EF:81D7..EF:81F1` (`26` bytes, SHA-1 `04b5000c1073ded928bc32f09a02e8652c54b772`) `EBattle2MsgBtlBootto`
- `EF:81F1..EF:8211` (`32` bytes, SHA-1 `4d2f2d2fc803360d542ab15691cb06621dc22e4e`) `EBattle2MsgBtlJyouki`
- `EF:8211..EF:8226` (`21` bytes, SHA-1 `fe763552f4afd02d5177d51edaee3b5686d705a0`) `EBattle2MsgBtlYoroyoro`
- `EF:8226..EF:8239` (`19` bytes, SHA-1 `796343d6f46509bee0764b341f85ab8e7d5e6951`) `EBattle2MsgBtlFurafura`
- `EF:8239..EF:825C` (`35` bytes, SHA-1 `55e8e7100f0546551f76ae0bc38ae504856ef4ed`) `EBattle2MsgBtlNitanita`
- `EF:825C..EF:8281` (`37` bytes, SHA-1 `9d1dfffbada6fb639a91c9ecda304fe52b8166af`) `EBattle2MsgBtlKokyuu`
- `EF:8281..EF:8299` (`24` bytes, SHA-1 `62a5b594ee81fff4b5989ab508d8cc00ec85c4aa`) `EBattle2MsgBtlAisatu`
- `EF:8299..EF:82BC` (`35` bytes, SHA-1 `9109b3c215aa6a5088aba3ad48e560a0e137f7b5`) `EBattle2MsgBtlUnari`
- `EF:82BC..EF:82D7` (`27` bytes, SHA-1 `4c0bde06d175c46ede6731980022ae937b9fe071`) `EBattle2MsgBtlKachikachi`
- `EF:82D7..EF:82F7` (`32` bytes, SHA-1 `5a3f46d35b42a7e4d4ba283dbe852b6cff01a407`) `EBattle2MsgBtlMabusiiHikari`
- `EF:82F7..EF:8317` (`32` bytes, SHA-1 `814782bd0c0fc50f71212577f6c07e33213a2e78`) `EBattle2MsgBtlBiribiri`
- `EF:8317..EF:833E` (`39` bytes, SHA-1 `05b7ffcb0b2d759a14805f3e8b751620a039b0f2`) `EBattle2MsgBtlKafun`
- `EF:833E..EF:835C` (`30` bytes, SHA-1 `f6dbe8e72962065aba0cb517f1b989878f798f5b`) `EBattle2MsgBtlColdHand`
- `EF:835C..EF:838A` (`46` bytes, SHA-1 `7b8d12313f204b74ba26d24358487f2eb82246a2`) `EBattle2MsgBtlPoisonBreath`
- `EF:838A..EF:83A8` (`30` bytes, SHA-1 `dc29ae79032986a73eca082ce7a40b7576c899e3`) `EBattle2MsgBtlHaikiGas`
- `EF:83A8..EF:83CA` (`34` bytes, SHA-1 `c34824f9fbb92f396328cd17f130aabe04b5ba49`) `EBattle2MsgBtlLaughHen`
- `EF:83CA..EF:83ED` (`35` bytes, SHA-1 `df48a364ea3ae15bff4a6c36865fb6bcb59d006c`) `EBattle2MsgBtlFue`
- `EF:83ED..EF:8413` (`38` bytes, SHA-1 `01f9156f8793463283afb295e0e2d387291bf972`) `EBattle2MsgBtlJumpToFace`
- `EF:8413..EF:843F` (`44` bytes, SHA-1 `bde83f459bf6244484edc67955bd6654773055be`) `EBattle2MsgBtlChouOnpa`
- `EF:843F..EF:8444` (`5` bytes, SHA-1 `d296611446d215d359e8c7664e0a30f31aa7b62e`) `EBattle0MsgAtStartAsleep`
- `EF:8444..EF:8445` (`1` bytes, SHA-1 `c4ea21bb365bbeeaf5f2c654883e56d11e43c44e`) `EBattle0MsgAtStartPsiSeal`
- `EF:8445..EF:845D` (`24` bytes, SHA-1 `290b309cbe7864982914515bbac8838cfec3ec00`) `EBattle0MsgAtStartStrange`
- `EF:845D..EF:8477` (`26` bytes, SHA-1 `b9cc80704b48261d7854d1582bd91cdb057d291d`) `EBattle0MsgRandomActStrange`
- `EF:8477..EF:848C` (`21` bytes, SHA-1 `e8df4e1a416a16e883880dddfb6f8cfea9620e20`) `EBattle0MsgRandomActMushroom`
- `EF:848C..EF:84A7` (`27` bytes, SHA-1 `e99323f03a7fecbf7430c1c5a4705be0f63e7bbe`) `EBattle1MsgBtlAttack`
- `EF:84A7..EF:84B6` (`15` bytes, SHA-1 `9c57f551049dbfdfe3f3e70588767d34b4dee5ee`) `EBattle1AttackPlayerSideBranch`
- `EF:84B6..EF:84C6` (`16` bytes, SHA-1 `6b8d415e3a2eb1313177e37f9276f39cf41b329c`) `EBattle1MsgBtlShoot`
- `EF:84C6..EF:84D4` (`14` bytes, SHA-1 `ae67ec66f07eb13a1bf5563e47b2d5d48d2a43fa`) `EBattle1MsgBtlGuard`
- `EF:84D4..EF:84F3` (`31` bytes, SHA-1 `a2324897cf11d3b03a6e89ccc07526c64949a6ab`) `EBattle1MsgBtlMetamorphose`
- `EF:84F3..EF:8511` (`30` bytes, SHA-1 `9aa5ecf35c8d1a4c6ed04410e38632dd3b3d20d9`) `EBattle1MsgBtlPlayerFlee`
- `EF:8511..EF:8530` (`31` bytes, SHA-1 `56bab7d7ebab3e80fc4e8caa0360e928e87ecfce`) `EBattle1MsgBtlPlayerFleeFailed`
- `EF:8530..EF:8543` (`19` bytes, SHA-1 `2e0e634a37bc7bb6b511a9912f101bfe9d4e2a08`) `EBattle1MsgBtlCheck`
- `EF:8543..EF:8568` (`37` bytes, SHA-1 `3c0205881fd711e75811d00d23d8eab375519aca`) `EBattle1MsgBtlPsi`
- `EF:8568..EF:857E` (`22` bytes, SHA-1 `eddea2b0a407599f67da715136320d0ad7df8434`) `EBattle1PsiPlayerSideBranch`
- `EF:857E..EF:864C` (`206` bytes, SHA-1 `ec707732de843dd8d0abe6f92b98fa0caf3e9b26`) `EBattle1PsiAnimationDispatch`
- `EF:864C..EF:866E` (`34` bytes, SHA-1 `ce2b90bbf03460d92795d3b257fcfebde934203c`) `EBattle1PsiEffectBranch1`
- `EF:866E..EF:8698` (`42` bytes, SHA-1 `218694e33ef698d221e4b70f886ec82f1d58b57b`) `EBattle1PsiEffectBranch2`
- `EF:8698..EF:86E2` (`74` bytes, SHA-1 `c8afd6c2732a2b05a59bb99d89bf0b318ccdab11`) `EBattle1PsiEffectBranch3`
- `EF:86E2..EF:874A` (`104` bytes, SHA-1 `ed5a9e5453145ff58972590b0c6a5129a226b296`) `EBattle1PsiEffectBranch4`
- `EF:874A..EF:875F` (`21` bytes, SHA-1 `77ef427c60e6f4661fe595a64c11ac1309fa0f17`) `EBattle1PsiEffectBranch5`
- `EF:875F..EF:8777` (`24` bytes, SHA-1 `0863376914292a310452e1f6d5cf9c8ec002fd25`) `EBattle1PsiEffectBranch6`
- `EF:8777..EF:878F` (`24` bytes, SHA-1 `8f0729f6aa5bf3250cc0316104003b2595dbf930`) `EBattle1PsiEffectBranch7`
- `EF:878F..EF:87AC` (`29` bytes, SHA-1 `9b91884c0ce8e8e378914cc23732e19f891535a0`) `EBattle1PsiEffectBranch8`
- `EF:87AC..EF:87C3` (`23` bytes, SHA-1 `6f9bf3f6f55d99837f9ddfb68e0df8d1de7d666c`) `EBattle1PsiEffectBranch9`
- `EF:87C3..EF:87DA` (`23` bytes, SHA-1 `eec8d005cba50856630e74edb227c1bf4ccfa251`) `EBattle1PsiEffectBranch10`
- `EF:87DA..EF:87F4` (`26` bytes, SHA-1 `6d54b1dfd7f86685bb26e0c7b5b3baa2f2311f5e`) `EBattle1PsiEffectBranch11`
- `EF:87F4..EF:8813` (`31` bytes, SHA-1 `076c405486c2f25ca4213396771efb5a162a1405`) `EBattle1PsiEffectBranch12`
- `EF:8813..EF:8814` (`1` bytes, SHA-1 `c4ea21bb365bbeeaf5f2c654883e56d11e43c44e`) `EBattle1PsiEffectBranch13`
- `EF:8814..EF:8823` (`15` bytes, SHA-1 `bacf80ef562971b5da5160d6dc5f1207a5a7e9f1`) `EBattle1MsgBtlThunderSmall`
- `EF:8823..EF:8837` (`20` bytes, SHA-1 `70e485664a175f6e96d22f420a2e64f0a19a7167`) `EBattle1MsgBtlThunderLarge`
- `EF:8837..EF:883D` (`6` bytes, SHA-1 `d578438044de353967285000e232ed6a3197dc6c`) `EBattle1MsgBtlThunderMissSound`
- `EF:883D..EF:8847` (`10` bytes, SHA-1 `f597df942fb9d6040573b05ffb6159cf8c203fe0`) `EBattle1PsiEffectBranch17`
- `EF:8847..EF:8851` (`10` bytes, SHA-1 `385acbf80d92ba740dfe7e2237138c14cb7af3fd`) `EBattle1PsiEffectBranch18`
- `EF:8851..EF:8868` (`23` bytes, SHA-1 `6466f9e55d028c83a18fcb91c353b5ab3348d8d9`) `EBattle1PsiEffectBranch19`
- `EF:8868..EF:8882` (`26` bytes, SHA-1 `23ff0c9a6d5f0785db34a8ee10a6becb17a4be31`) `EBattle1PsiEffectBranch20`
- `EF:8882..EF:88B8` (`54` bytes, SHA-1 `5c8f7e904dd0d302133cbe80c0d67499ecf8bfeb`) `EBattle1PsiEffectBranch21`
- `EF:88B8..EF:88E9` (`49` bytes, SHA-1 `6a15a90a432ef6f937a5fda1438af7fe230491b9`) `EBattle1PsiEffectBranch22`
- `EF:88E9..EF:88EC` (`3` bytes, SHA-1 `d683592bd8f0f4027832289929db6c4b17d8c1d8`) `EBattle1PsiEffectBranch23`
- `EF:88EC..EF:88F6` (`10` bytes, SHA-1 `d41331b297de5b85c40c27fec7922ca2c210bc82`) `EBattle1PsiEffectBranch31`
- `EF:88F6..EF:8900` (`10` bytes, SHA-1 `d41331b297de5b85c40c27fec7922ca2c210bc82`) `EBattle1PsiEffectBranch32`
- `EF:8900..EF:890A` (`10` bytes, SHA-1 `1d2de306edf4d102fd1e949a6f1a45552d0ead43`) `EBattle1PsiEffectBranch33`
- `EF:890A..EF:8914` (`10` bytes, SHA-1 `1d2de306edf4d102fd1e949a6f1a45552d0ead43`) `EBattle1PsiEffectBranch34`
- `EF:8914..EF:891E` (`10` bytes, SHA-1 `31138bbb7086ac62a11e26c82af0f29f57d34ee5`) `EBattle1PsiEffectBranch35`
- `EF:891E..EF:8928` (`10` bytes, SHA-1 `31138bbb7086ac62a11e26c82af0f29f57d34ee5`) `EBattle1PsiEffectBranch36`
- `EF:8928..EF:8932` (`10` bytes, SHA-1 `b345262ccbc40a82c3bf346b6dac5d39c51cd634`) `EBattle1PsiEffectBranch37`
- `EF:8932..EF:893C` (`10` bytes, SHA-1 `b345262ccbc40a82c3bf346b6dac5d39c51cd634`) `EBattle1PsiEffectBranch38`
- `EF:893C..EF:894C` (`16` bytes, SHA-1 `d0af558122f28e371aa5675c3dba7b576dab985d`) `EBattle1PsiEffectBranch41`
- `EF:894C..EF:895C` (`16` bytes, SHA-1 `84be21126a203362bced7549ed0899ddf8d4f760`) `EBattle1PsiEffectBranch42`
- `EF:895C..EF:896C` (`16` bytes, SHA-1 `3c40e5f79fb9ddf9520e5f9de17c78066105b0f7`) `EBattle1PsiEffectBranch43`
- `EF:896C..EF:897C` (`16` bytes, SHA-1 `c3317246f9f2e20b90a313b5c210562340583e90`) `EBattle1PsiEffectBranch44`
- `EF:897C..EF:898C` (`16` bytes, SHA-1 `be771ab8a27e5cd0a91a66896b20e7598d0c56b4`) `EBattle1PsiEffectBranch45`
- `EF:898C..EF:899C` (`16` bytes, SHA-1 `54efcb0927a24fcb20d757fe916f53fed32146ff`) `EBattle1PsiEffectBranch46`
- `EF:899C..EF:89AC` (`16` bytes, SHA-1 `dcc52620ced6474867a1bc52e9c368f2fa9bbed7`) `EBattle1PsiEffectBranch47`
- `EF:89AC..EF:89BC` (`16` bytes, SHA-1 `05a5c2915048697e801c8fb55fbed9b7575503b3`) `EBattle1PsiEffectBranch48`
- `EF:89BC..EF:89CE` (`18` bytes, SHA-1 `731b1615df090f21f79e7faef34ff2905d213bff`) `EBattle1PsiEffectBranch49`
- `EF:89CE..EF:89E0` (`18` bytes, SHA-1 `c14cb7a4b9b698376aec8d772ebe8cc2fcb90366`) `EBattle1PsiEffectBranch50`
- `EF:89E0..EF:89FE` (`30` bytes, SHA-1 `8afe90ada4dfe0b5def823aeba59fd3ad4a62b83`) `EBattle1MsgBtlPray`
- `EF:89FE..EF:8A18` (`26` bytes, SHA-1 `82516287de48a79fcc57c207a112334b7dc1e5d8`) `EBattle3MsgBtlJihibiki`
- `EF:8A18..EF:8A33` (`27` bytes, SHA-1 `b9cf25d951570548a9173205917a1e124c8e642e`) `EBattle3MsgBtlOsaetsuke`
- `EF:8A33..EF:8A52` (`31` bytes, SHA-1 `a9a6f80fa14e823657269b9d4b31ddfe73be7fff`) `EBattle3MsgBtlCurseWord`
- `EF:8A52..EF:8A6F` (`29` bytes, SHA-1 `4f91dc6da094af749a6e9d11f864a1ccc7385948`) `EBattle3MsgBtlJimi`
- `EF:8A6F..EF:8A8C` (`29` bytes, SHA-1 `b2d6de625aaec60f0c0a5fb3cd8960d9c86747cf`) `EBattle3MsgBtlPenki`
- `EF:8A8C..EF:8AA3` (`23` bytes, SHA-1 `fa89bcca9563639b4ab17e070bae0b505eabd87d`) `EBattle3MsgBtlNaguriKakari`
- `EF:8AA3..EF:8AC2` (`31` bytes, SHA-1 `7958bb3b03bfff1342284529767b16d6d187dbe7`) `EBattle3MsgBtlClaw`
- `EF:8AC2..EF:8ADD` (`27` bytes, SHA-1 `a91b11f0930f7946017719b45d7c40719d76d48f`) `EBattle3MsgBtlKuchibashi`
- `EF:8ADD..EF:8AF8` (`27` bytes, SHA-1 `9ce620a6a7cc254e98e62faaf3ec46964da1f001`) `EBattle3MsgBtlTsuno`
- `EF:8AF8..EF:8B11` (`25` bytes, SHA-1 `58b5a0c797894b84c4be5351b86664266a1de1df`) `EBattle3MsgBtlPunch`
- `EF:8B11..EF:8B2F` (`30` bytes, SHA-1 `78e6dd2a297ed89f0a39f966d95223e77084482c`) `EBattle3MsgBtlPumpkin`
- `EF:8B2F..EF:8B4A` (`27` bytes, SHA-1 `69d3dc47622dba92d8559a1b40437d128d75454f`) `EBattle3MsgBtlBeam`
- `EF:8B4A..EF:8B65` (`27` bytes, SHA-1 `bd4124fb9b77641746a3257a196d127f749d5266`) `EBattle3MsgBtlYari`
- `EF:8B65..EF:8B89` (`36` bytes, SHA-1 `9c048f1c73a7b16c2d40bb4b3cf6c4d796cd908a`) `EBattle3MsgBtlFumitsuke`
- `EF:8B89..EF:8BA8` (`31` bytes, SHA-1 `5417a382c51d8e4d0e5747665d0ebc805e87047e`) `EBattle3MsgBtlFurafuupu`
- `EF:8BA8..EF:8BC0` (`24` bytes, SHA-1 `3f23d1e935b11d01c3a5f0fd7c5ac3584f024507`) `EBattle3MsgBtlTaiatari`
- `EF:8BC0..EF:8BE8` (`40` bytes, SHA-1 `a5a34cf8340e55b1a1c0e3a907e0c1035772c0aa`) `EBattle3MsgBtlSkateboard`
- `EF:8BE8..EF:8BFB` (`19` bytes, SHA-1 `ae517ccac21dfd6f14940ad00e0afc12c3ae1dbd`) `EBattle3MsgBtlKamitsukiDiamond`
- `EF:8BFB..EF:8C1D` (`34` bytes, SHA-1 `8f38bb4bfe94c040267c40727b8865266ea1db9a`) `EBattle3MsgBtlKudamaki`
- `EF:8C1D..EF:8C3A` (`29` bytes, SHA-1 `501f385ddfdc187cbae2cad0900521f642b4aae2`) `EBattle3MsgBtlSekkyou`
- `EF:8C3A..EF:8C58` (`30` bytes, SHA-1 `c7e3eb9c98f5d814edd59d5b3bb46a3e5aa97cc5`) `EBattle3MsgBtlShikaritsuke`
- `EF:8C58..EF:8C75` (`29` bytes, SHA-1 `9b42d558d2e655d77fae4bad4cfd20e53ba2a43c`) `EBattle3MsgBtlBadSmell`
- `EF:8C75..EF:8C92` (`29` bytes, SHA-1 `b4982e8d6381eb7f10748d19f888653b69d8d4a9`) `EBattle3MsgBtlLoudVoice`
- `EF:8C92..EF:8CAC` (`26` bytes, SHA-1 `30917200a7b1000f96d516272cec8facb90f1cfc`) `EBattle3MsgBtlOtakebi`
- `EF:8CAC..EF:8CC7` (`27` bytes, SHA-1 `a6e12ad62550dfe21bbdefa92948f39f72b61d17`) `EBattle3MsgBtlFakeDead`
- `EF:8CC7..EF:8CDD` (`22` bytes, SHA-1 `c053dea2b746d7465ec36b4cbda8e7fde606dae4`) `EBattle3MsgBtlYudan`
- `EF:8CDD..EF:8CFB` (`30` bytes, SHA-1 `566d7352fc35a8042bbff3e69ded5685d144bdad`) `EBattle3MsgBtlYudan1`
- `EF:8CFB..EF:8D17` (`28` bytes, SHA-1 `a7e7834f9eb926f03d26dae91032cab9fe910ea2`) `EBattle3MsgBtlYudan2`
- `EF:8D17..EF:8D2F` (`24` bytes, SHA-1 `ffa8ca67550206b698c7d354dc445011b1c436fe`) `EBattle3MsgBtlYudan3`
- `EF:8D2F..EF:8D4C` (`29` bytes, SHA-1 `2a6d2c8d426340e2668e23b7004c71851b2038e4`) `EBattle3MsgBtlYudan4`
- `EF:8D4C..EF:8D72` (`38` bytes, SHA-1 `b8360b3a6defa5ef388b5156d8d5ffe4c99fe053`) `EBattle3MsgBtlYudanLifeup`
- `EF:8D72..EF:8D9F` (`45` bytes, SHA-1 `bfe6951299f51a254f8fc2c8a7ad342a71ee7849`) `EBattle3MsgBtlNebieBeam`
- `EF:8D9F..EF:8DC1` (`34` bytes, SHA-1 `f4ec5f481aa20e8c37e63a06f35875137d5091a2`) `EBattle3MsgBtlNeutralizeSparkle`
- `EF:8DC1..EF:8DDE` (`29` bytes, SHA-1 `937dfc5ae9d58e40fc26e3abf8c21d78635a4cb7`) `EBattle3MsgBtlMakitsuki`
- `EF:8DDE..EF:8E27` (`73` bytes, SHA-1 `a2be184479ff15037a0869f1ce3735092130949d`) `EBattle3MsgBtlToDiamondDog`
- `EF:8E27..EF:8E3C` (`21` bytes, SHA-1 `ed6bb71d52ce16b2c70f35a67f0f207f0b83571e`) `EBattle3MsgBtlWarpNear`
- `EF:8E3C..EF:8E5E` (`34` bytes, SHA-1 `8dd727c3912f31d6a832803481482da02856bb65`) `EBattle3MsgBtlAntipsi`
- `EF:8E5E..EF:8E7E` (`32` bytes, SHA-1 `cb9e63f7d89c72e768b383127b4fa45d1e1babb7`) `EBattle3MsgBtlHpsuck`
- `EF:8E7E..EF:8E9E` (`32` bytes, SHA-1 `416aeaab8b0876ccc0dd67be014af23b5e05f153`) `EBattle3MsgBtlHpsucksp`
- `EF:8E9E..EF:8EBE` (`32` bytes, SHA-1 `aac956c87de5ca8f08c162acb29102248e1e6ca9`) `EBattle3MsgBtlShieldkill`
- `EF:8EBE..EF:8EE2` (`36` bytes, SHA-1 `e1dbb11052439787f5983da25167064d3bbbe743`) `EBattle3MsgBtlBadSmellGas`
- `EF:8EE2..EF:8F17` (`53` bytes, SHA-1 `9d095da1f28789d8c787cfc7241d78a97b832eff`) `EBattle3MsgBtlLightning`
- `EF:8F17..EF:8F4A` (`51` bytes, SHA-1 `833abb473eaaedd8995dcddb89018c082eb03c8c`) `EBattle3MsgBtlLightningB`
- `EF:8F4A..EF:8F91` (`71` bytes, SHA-1 `886d431e469f10d4a3febb85630f90affcbdfa12`) `EBattle3MsgBtlLightningC`
- `EF:8F91..EF:8FAD` (`28` bytes, SHA-1 `9281e687823201e0c4448a95e648ee7cb050705f`) `EBattle3MsgBtlGyiyyig3`
- `EF:8FAD..EF:C51B` (`13678` bytes, SHA-1 `5f4aa78a8085cb7adb5cf8658ed4a532af56638d`) `EfPostEbattle3TextPayloadData`

Labels:

- `EF:4E20 EfPreBattleTextPayloadData`
- `EF:69A1 EBattle5MsgBtlHpMaxRecovered`
- `EF:69BA EBattle5MsgBtlHpRecoveredAmount`
- `EF:69D2 EBattle5MsgBtlPpRecoveredAmount`
- `EF:69EA EBattle5MsgBtlCheckOffenseAmount`
- `EF:69FF EBattle5MsgBtlCheckDefenseAmount`
- `EF:6A0D EBattle5MsgBtlCheckAntiFire`
- `EF:6A24 EBattle5MsgBtlCheckAntiFreeze`
- `EF:6A3C EBattle5MsgBtlCheckAntiFlash`
- `EF:6A54 EBattle5MsgBtlCheckAntiParalysis`
- `EF:6A6C EBattle5MsgBtlCheckBrainLevel0`
- `EF:6A7F EBattle5MsgBtlCheckBrainLevel3`
- `EF:6A99 EBattle5MsgBtlMetamorphoseOk`
- `EF:6AB3 EBattle5MsgBtlMetamorphoseFailed`
- `EF:6AC7 EBattle5MsgBtlDiamondized`
- `EF:6AE0 EBattle5MsgBtlParalysisInflicted`
- `EF:6AFB EBattle5MsgBtlFeelingSickInflicted`
- `EF:6B18 EBattle5MsgBtlPoisonInflicted`
- `EF:6B2F EBattle5MsgBtlColdInflicted`
- `EF:6B43 EBattle5ObjectPronounSubtext`
- `EF:6B81 EBattle5MsgBtlMushroomizedInflicted`
- `EF:6B98 EBattle5MsgBtlPossessedInflicted`
- `EF:6BBB EBattle5MsgBtlCryingInflicted`
- `EF:6BD3 EBattle5MsgBtlImmobilizedInflicted`
- `EF:6BEF EBattle5MsgBtlSolidificationInflicted`
- `EF:6C0B EBattle5MsgBtlPsiSealInflicted`
- `EF:6C3A EBattle5MsgBtlStrangeInflicted`
- `EF:6C55 EBattle5MsgBtlAsleepInflicted`
- `EF:6C6B EBattle5MsgBtlIncapacitated`
- `EF:6C84 EBattle5MsgSysNpcDeadFlyingMan`
- `EF:6CC7 EBattle5FlyingManDeadBranchB`
- `EF:6CD0 EBattle5FlyingManDeadBranchC`
- `EF:6CD9 EBattle5FlyingManDeadBranchD`
- `EF:6CE2 EBattle5FlyingManDeadBranchE`
- `EF:6CEB EBattle5FlyingManRemovePartyMemberHelper`
- `EF:6CFC EBattle5FlyingManRemoveBranch2`
- `EF:6D0A EBattle5FlyingManRemoveBranch3`
- `EF:6D18 EBattle5FlyingManRemoveBranch4`
- `EF:6D26 EBattle5FlyingManRemoveBranch5`
- `EF:6D2A EBattle5MsgSysNpcDeadTeddyBear`
- `EF:6D4C EBattle5MsgSysNpcDeadSuperPlushBear`
- `EF:6D71 EBattle5MsgBtlEnemyDefeated`
- `EF:6D83 EBattle5MsgBtlEnemyStoppedMoving`
- `EF:6D96 EBattle5MsgBtlEnemyBecameTame`
- `EF:6DA7 EBattle5MsgBtlEnemyDisappeared`
- `EF:6DB8 EBattle5MsgBtlEnemyMeltedAway`
- `EF:6DD8 EBattle5MsgBtlEnemyBrokeIntoPieces`
- `EF:6DF0 EBattle5MsgBtlEnemyDestroyed`
- `EF:6E03 EBattle5MsgBtlEnemyScrapped`
- `EF:6E19 EBattle5MsgBtlEnemyReturnedToNormal`
- `EF:6E31 EBattle5MsgBtlEnemyReturnedToDust`
- `EF:6E4A EBattle5MsgBtlDiamondizedRecovered`
- `EF:6E67 EBattle5MsgBtlParalysisRecovered`
- `EF:6E81 EBattle5MsgBtlFeelingSickRecovered`
- `EF:6E97 EBattle5MsgBtlPoisonRemoved`
- `EF:6EBC EBattle5MsgBtlColdRecovered`
- `EF:6ED1 EBattle5MsgBtlCryingRecovered`
- `EF:6EED EBattle5MsgBtlImmobilizedRecovered`
- `EF:6F0B EBattle5MsgBtlFrozenCanMove`
- `EF:6F1E EBattle5MsgBtlStrangeRecovered`
- `EF:6F38 EBattle5MsgBtlSunstrokeCured`
- `EF:6F54 EBattle5MsgBtlAsleepRecovered`
- `EF:6F64 EBattle5MsgBtlPsiSealRecovered`
- `EF:6F7C EBattle5MsgBtlRevived`
- `EF:6F8E EBattle5MsgBtlReviveFailed`
- `EF:6F9A EBattle5MsgBtlShieldInstalled`
- `EF:6FBD EBattle5MsgBtlShieldStrengthened`
- `EF:6FD3 EBattle5MsgBtlPowerShieldInstalled`
- `EF:6FF4 EBattle5MsgBtlPowerShieldStrengthened`
- `EF:700C EBattle5MsgBtlPsychicShieldInstalled`
- `EF:7032 EBattle5MsgBtlPsychicShieldStrengthened`
- `EF:7050 EBattle5MsgBtlPsychicPowerShieldInstalled`
- `EF:707A EBattle5MsgBtlPsychicPowerShieldStrengthened`
- `EF:7099 EBattle5MsgBtlShieldExpired`
- `EF:70B1 EBattle5MsgBtlPowerShieldReflectsAttack`
- `EF:70D2 EBattle5MsgBtlPsychicPowerShieldReflectsPsiName`
- `EF:70FA EBattle5MsgBtlPsychicShieldNullifiesPsiName`
- `EF:7123 EBattle5MsgBtlNeutralizeResult`
- `EF:7142 EBattle5MsgBtlNeutralizeMetamorph`
- `EF:7160 EBattle5MsgBtlFranklinBadgeReflectsThunder`
- `EF:7186 EBattle4MsgBtlDiamondizedCannotMove`
- `EF:7192 EBattle4MsgBtlParalysisCannotMove`
- `EF:71B4 EBattle4MsgBtlNauseaCannotMove`
- `EF:71CC EBattle4MsgBtlPoisonStatus`
- `EF:71DF EBattle4MsgBtlAsleepStatus`
- `EF:71F6 EBattle4MsgBtlImmobilizedStatus`
- `EF:720C EBattle4MsgBtlPsiSealStatus`
- `EF:721E EBattle4PsiSealPlayerSideSoundBranch`
- `EF:7221 EBattle4PsiSealResultText`
- `EF:7249 EBattle4MsgBtlGuardOn`
- `EF:725A EBattle4MsgBtlFlyHoneyMindLost`
- `EF:727F EBattle4MsgBtlHomesickRandom`
- `EF:72A0 EBattle4MsgBtlHomesickThoughtMom`
- `EF:72B9 EBattle4MsgBtlHomesickCravingFood`
- `EF:72DB EBattle4MsgBtlHomesickLostMotivation`
- `EF:72F6 EBattle4MsgBtlRunawayFiveBreakIn`
- `EF:72F7 EBattle4MsgBtlRunawayFiveBreakInFailed`
- `EF:733D EBattle4MsgBtlRunawayFiveBreakInSucceeded`
- `EF:7415 EBattle4MsgBtlPooBreakIn`
- `EF:743B EBattle4MsgBtlPooStarstormReveal`
- `EF:745F EBattle4MsgBtlPokeyTalkRandom`
- `EF:749D EBattle4MsgBtlPokeyPlayedDead`
- `EF:74B0 EBattle4MsgBtlPokeyPretendedCry`
- `EF:74C9 EBattle4MsgBtlPokeyApologized`
- `EF:74E6 EBattle4MsgBtlPokeyThoughtToSelf`
- `EF:74FA EBattle4MsgBtlPokeyActedInnocent`
- `EF:7514 EBattle4MsgBtlPokeySmiledSincerely`
- `EF:7530 EBattle4MsgBtlPokeyComplained`
- `EF:7548 EBattle4MsgBtlPokeyEdgedCloser`
- `EF:7569 EBattle4MsgBtlMyDogHowling`
- `EF:7579 EBattle4MsgBtlPickeyTalk`
- `EF:7591 EBattle4MsgBtlTonyTalk`
- `EF:7593 EBattle4MsgBtlBalmonTalk`
- `EF:75AB EBattle4MsgBtlDamageAmount`
- `EF:75C2 EBattle4MsgBtlMortalDamageAmount`
- `EF:75D9 EBattle4MsgBtlSmashDamageAmount`
- `EF:75F0 EBattle4MsgBtlMortalSmashDamageAmount`
- `EF:7607 EBattle4MsgBtlDamageToDeathAmount`
- `EF:7624 EBattle4MsgBtlSmashPlayer`
- `EF:7630 EBattle4MsgBtlSmashMonster`
- `EF:763C EBattle4MsgBtlShootDodged`
- `EF:7655 EBattle4MsgBtlBashDodged`
- `EF:766E EBattle4MsgBtlStatusNoEffect`
- `EF:7682 EBattle4AdjacentNoEffectText`
- `EF:7696 EBattle4MsgBtlNoVisibleEffect`
- `EF:76B3 EBattle4MsgBtlNoEffectVariantC`
- `EF:76C7 EBattle4MsgBtlMissPhysical`
- `EF:76D8 EBattle4MsgBtlMissShoot`
- `EF:76FD EBattle4MsgBtlTargetNotExist`
- `EF:7710 EBattle4MsgBtlHpSuckSelfDrain`
- `EF:7729 EBattle4MsgBtlHpSuckAmount`
- `EF:773F EBattle4MsgBtlPpDrainAmount`
- `EF:7755 EBattle4MsgBtlPpDrainTarget`
- `EF:7768 EBattle4MsgBtlStrangeDamage`
- `EF:7787 EBattle4MsgBtlPoisonDamage`
- `EF:77B1 EBattle4MsgBtlSunstrokeDamage`
- `EF:77DB EBattle4MsgBtlColdDamage`
- `EF:77FD EBattle8MsgBtlCallForHelpEnemyJoined`
- `EF:7810 EBattle8MsgBtlCallForHelpSeedSprouted`
- `EF:7824 EBattle8MsgBtlCallForHelpNoOneCame`
- `EF:7830 EBattle8MsgBtlCallForHelpSeedNoSprout`
- `EF:7843 EBattle8MsgBtlTimeStopReturn`
- `EF:7858 EBattle8MsgBtlAppearAttacked`
- `EF:7866 EBattle8MsgBtlAppearBlockedWay`
- `EF:7879 EBattle8MsgBtlAppearCameAfterYou`
- `EF:788B EBattle8MsgBtlAppearTrappedYou`
- `EF:789C EBattle8MsgBtlFinalEncounter4`
- `EF:78AB EBattle8MsgBtlFinalEncounter5`
- `EF:78B8 EBattle8MsgBtlFinalEncounter6`
- `EF:78C7 EBattle8MsgBtlFinalEncounter7`
- `EF:78D8 EBattle8MsgBtlSurpriseOpeningPlayer`
- `EF:78F7 EBattle8MsgBtlSurpriseOpeningMonster`
- `EF:790B EBattle8GroupActorOpeningHelper`
- `EF:792B EBattle8GroupActorOpeningSingular`
- `EF:792E EBattle8GroupActorOpeningCohort`
- `EF:793C EBattle8GroupActorOpeningCohorts`
- `EF:794B EBattle8GroupActorFinalHelper`
- `EF:796C EBattle8GroupActorFinalSingular`
- `EF:7970 EBattle8GroupActorFinalCohort`
- `EF:797F EBattle8GroupActorFinalCohorts`
- `EF:798F EBattle8GroupActorSurpriseHelper`
- `EF:79B1 EBattle8GroupActorPossessiveSingular`
- `EF:79B6 EBattle8GroupActorPossessiveCohort`
- `EF:79C6 EBattle8GroupActorPossessiveCohorts`
- `EF:79D7 EBattle8MsgBtlPlayerWin`
- `EF:79E6 EBattle8PlayerWinEventBranch`
- `EF:79EF EBattle8PlayerWinExperienceText`
- `EF:7A0A EBattle8PlayerWinHomesickBranch`
- `EF:7A14 EBattle8MsgBtlPlayerWinBoss`
- `EF:7A28 EBattle8MsgBtlPlayerWinForce`
- `EF:7A4D EBattle8MsgBtlMonsterWin`
- `EF:7A66 EBattle8MsgBtlLevelUp`
- `EF:7A7D EBattle8MsgBtlLevelOffenseUp`
- `EF:7A97 EBattle8MsgBtlLevelDefenseUp`
- `EF:7AB1 EBattle8MsgBtlLevelSpeedUp`
- `EF:7AC9 EBattle8MsgBtlLevelGutsUp`
- `EF:7AE0 EBattle8MsgBtlLevelVitalityUp`
- `EF:7AFB EBattle8MsgBtlLevelIqUp`
- `EF:7B11 EBattle8MsgBtlLevelLuckUp`
- `EF:7B28 EBattle8MsgBtlLevelMaxHpUp`
- `EF:7B46 EBattle8MsgBtlLevelMaxPpUp`
- `EF:7B64 EBattle8MsgBtlLearnPsi`
- `EF:7B77 EBattle8ByteSubstitutionPsiNameText`
- `EF:7B83 EBattle8PointerSubstitutionIntroState`
- `EF:7B85 EBattle8PointerSubstitutionSweetBranch`
- `EF:7BA0 EBattle8PointerSubstitutionBranch2State`
- `EF:7BA2 EBattle8PointerSubstitutionTearsBranch`
- `EF:7BBF EBattle8PointerSubstitutionBranch3State`
- `EF:7BC1 EBattle8PointerSubstitutionOhBabyBranch`
- `EF:7BDF EBattle8MsgBtlPresentByteSubstitution`
- `EF:7C42 EBattle8PresentRecipientDeadText`
- `EF:7C73 EBattle8PresentInventoryFullText`
- `EF:7C89 EBattle8PresentThrowAwayPrompt`
- `EF:7CB4 EBattle8PresentAbandonPrompt`
- `EF:7CED EBattle8PresentAbandonRetryText`
- `EF:7CF8 EBattle8PresentAbandonConfirmedText`
- `EF:7D0F EBattle8PresentDropSelectionPrompt`
- `EF:7D83 EBattle8PresentDropConfirmedText`
- `EF:7DBE EBattle8PresentDropForbiddenText`
- `EF:7DD5 EBattle8MsgBtlCheckPresentGetByteSubstitution`
- `EF:7E25 EBattle2MsgBtlPpDown`
- `EF:7E3E EBattle2MsgBtlOkoru`
- `EF:7E55 EBattle2MsgBtlKitanaiKotoba`
- `EF:7E70 EBattle2MsgBtlSuibun`
- `EF:7E88 EBattle2MsgBtlEnergy`
- `EF:7EAC EBattle2MsgBtlDokuKamituki`
- `EF:7ED5 EBattle2MsgBtlYoroMissile`
- `EF:7F02 EBattle2MsgBtlMultiAttack`
- `EF:7F1E EBattle2MsgBtlMigamae`
- `EF:7F32 EBattle2MsgBtlFireball`
- `EF:7F5A EBattle2MsgBtlGekitotu`
- `EF:7F7B EBattle2MsgBtlKarate`
- `EF:7F9A EBattle2MsgBtlTomoe`
- `EF:7FC3 EBattle2MsgBtlBousou`
- `EF:7FE0 EBattle2MsgBtlKnife`
- `EF:7FFC EBattle2MsgBtlTossin`
- `EF:8010 EBattle2MsgBtlKamituki`
- `EF:8026 EBattle2MsgBtlHikkaki`
- `EF:804B EBattle2MsgBtlSippo`
- `EF:806D EBattle2MsgBtlNoshikakari`
- `EF:808D EBattle2MsgBtlKamibukuro`
- `EF:80AC EBattle2MsgBtlKonbou`
- `EF:80C4 EBattle2MsgBtlTatumaki`
- `EF:80E4 EBattle2MsgBtlWater`
- `EF:8109 EBattle2MsgBtlFutekiSmile`
- `EF:812B EBattle2MsgBtlLoudSmile`
- `EF:814F EBattle2MsgBtlNijiriyoru`
- `EF:8167 EBattle2MsgBtlTubuyaki1`
- `EF:8186 EBattle2MsgBtlTubuyaki2`
- `EF:81A5 EBattle2MsgBtlTubuyaki3`
- `EF:81C4 EBattle2MsgBtlKorobu`
- `EF:81D7 EBattle2MsgBtlBootto`
- `EF:81F1 EBattle2MsgBtlJyouki`
- `EF:8211 EBattle2MsgBtlYoroyoro`
- `EF:8226 EBattle2MsgBtlFurafura`
- `EF:8239 EBattle2MsgBtlNitanita`
- `EF:825C EBattle2MsgBtlKokyuu`
- `EF:8281 EBattle2MsgBtlAisatu`
- `EF:8299 EBattle2MsgBtlUnari`
- `EF:82BC EBattle2MsgBtlKachikachi`
- `EF:82D7 EBattle2MsgBtlMabusiiHikari`
- `EF:82F7 EBattle2MsgBtlBiribiri`
- `EF:8317 EBattle2MsgBtlKafun`
- `EF:833E EBattle2MsgBtlColdHand`
- `EF:835C EBattle2MsgBtlPoisonBreath`
- `EF:838A EBattle2MsgBtlHaikiGas`
- `EF:83A8 EBattle2MsgBtlLaughHen`
- `EF:83CA EBattle2MsgBtlFue`
- `EF:83ED EBattle2MsgBtlJumpToFace`
- `EF:8413 EBattle2MsgBtlChouOnpa`
- `EF:843F EBattle0MsgAtStartAsleep`
- `EF:8444 EBattle0MsgAtStartPsiSeal`
- `EF:8445 EBattle0MsgAtStartStrange`
- `EF:845D EBattle0MsgRandomActStrange`
- `EF:8477 EBattle0MsgRandomActMushroom`
- `EF:848C EBattle1MsgBtlAttack`
- `EF:84A7 EBattle1AttackPlayerSideBranch`
- `EF:84B6 EBattle1MsgBtlShoot`
- `EF:84C6 EBattle1MsgBtlGuard`
- `EF:84D4 EBattle1MsgBtlMetamorphose`
- `EF:84F3 EBattle1MsgBtlPlayerFlee`
- `EF:8511 EBattle1MsgBtlPlayerFleeFailed`
- `EF:8530 EBattle1MsgBtlCheck`
- `EF:8543 EBattle1MsgBtlPsi`
- `EF:8568 EBattle1PsiPlayerSideBranch`
- `EF:857E EBattle1PsiAnimationDispatch`
- `EF:864C EBattle1PsiEffectBranch1`
- `EF:866E EBattle1PsiEffectBranch2`
- `EF:8698 EBattle1PsiEffectBranch3`
- `EF:86E2 EBattle1PsiEffectBranch4`
- `EF:874A EBattle1PsiEffectBranch5`
- `EF:875F EBattle1PsiEffectBranch6`
- `EF:8777 EBattle1PsiEffectBranch7`
- `EF:878F EBattle1PsiEffectBranch8`
- `EF:87AC EBattle1PsiEffectBranch9`
- `EF:87C3 EBattle1PsiEffectBranch10`
- `EF:87DA EBattle1PsiEffectBranch11`
- `EF:87F4 EBattle1PsiEffectBranch12`
- `EF:8813 EBattle1PsiEffectBranch13`
- `EF:8814 EBattle1MsgBtlThunderSmall`
- `EF:8823 EBattle1MsgBtlThunderLarge`
- `EF:8837 EBattle1MsgBtlThunderMissSound`
- `EF:883D EBattle1PsiEffectBranch17`
- `EF:8847 EBattle1PsiEffectBranch18`
- `EF:8851 EBattle1PsiEffectBranch19`
- `EF:8868 EBattle1PsiEffectBranch20`
- `EF:8882 EBattle1PsiEffectBranch21`
- `EF:88B8 EBattle1PsiEffectBranch22`
- `EF:88E9 EBattle1PsiEffectBranch23`
- `EF:88EC EBattle1PsiEffectBranch31`
- `EF:88F6 EBattle1PsiEffectBranch32`
- `EF:8900 EBattle1PsiEffectBranch33`
- `EF:890A EBattle1PsiEffectBranch34`
- `EF:8914 EBattle1PsiEffectBranch35`
- `EF:891E EBattle1PsiEffectBranch36`
- `EF:8928 EBattle1PsiEffectBranch37`
- `EF:8932 EBattle1PsiEffectBranch38`
- `EF:893C EBattle1PsiEffectBranch41`
- `EF:894C EBattle1PsiEffectBranch42`
- `EF:895C EBattle1PsiEffectBranch43`
- `EF:896C EBattle1PsiEffectBranch44`
- `EF:897C EBattle1PsiEffectBranch45`
- `EF:898C EBattle1PsiEffectBranch46`
- `EF:899C EBattle1PsiEffectBranch47`
- `EF:89AC EBattle1PsiEffectBranch48`
- `EF:89BC EBattle1PsiEffectBranch49`
- `EF:89CE EBattle1PsiEffectBranch50`
- `EF:89E0 EBattle1MsgBtlPray`
- `EF:89FE EBattle3MsgBtlJihibiki`
- `EF:8A18 EBattle3MsgBtlOsaetsuke`
- `EF:8A33 EBattle3MsgBtlCurseWord`
- `EF:8A52 EBattle3MsgBtlJimi`
- `EF:8A6F EBattle3MsgBtlPenki`
- `EF:8A8C EBattle3MsgBtlNaguriKakari`
- `EF:8AA3 EBattle3MsgBtlClaw`
- `EF:8AC2 EBattle3MsgBtlKuchibashi`
- `EF:8ADD EBattle3MsgBtlTsuno`
- `EF:8AF8 EBattle3MsgBtlPunch`
- `EF:8B11 EBattle3MsgBtlPumpkin`
- `EF:8B2F EBattle3MsgBtlBeam`
- `EF:8B4A EBattle3MsgBtlYari`
- `EF:8B65 EBattle3MsgBtlFumitsuke`
- `EF:8B89 EBattle3MsgBtlFurafuupu`
- `EF:8BA8 EBattle3MsgBtlTaiatari`
- `EF:8BC0 EBattle3MsgBtlSkateboard`
- `EF:8BE8 EBattle3MsgBtlKamitsukiDiamond`
- `EF:8BFB EBattle3MsgBtlKudamaki`
- `EF:8C1D EBattle3MsgBtlSekkyou`
- `EF:8C3A EBattle3MsgBtlShikaritsuke`
- `EF:8C58 EBattle3MsgBtlBadSmell`
- `EF:8C75 EBattle3MsgBtlLoudVoice`
- `EF:8C92 EBattle3MsgBtlOtakebi`
- `EF:8CAC EBattle3MsgBtlFakeDead`
- `EF:8CC7 EBattle3MsgBtlYudan`
- `EF:8CDD EBattle3MsgBtlYudan1`
- `EF:8CFB EBattle3MsgBtlYudan2`
- `EF:8D17 EBattle3MsgBtlYudan3`
- `EF:8D2F EBattle3MsgBtlYudan4`
- `EF:8D4C EBattle3MsgBtlYudanLifeup`
- `EF:8D72 EBattle3MsgBtlNebieBeam`
- `EF:8D9F EBattle3MsgBtlNeutralizeSparkle`
- `EF:8DC1 EBattle3MsgBtlMakitsuki`
- `EF:8DDE EBattle3MsgBtlToDiamondDog`
- `EF:8E27 EBattle3MsgBtlWarpNear`
- `EF:8E3C EBattle3MsgBtlAntipsi`
- `EF:8E5E EBattle3MsgBtlHpsuck`
- `EF:8E7E EBattle3MsgBtlHpsucksp`
- `EF:8E9E EBattle3MsgBtlShieldkill`
- `EF:8EBE EBattle3MsgBtlBadSmellGas`
- `EF:8EE2 EBattle3MsgBtlLightning`
- `EF:8F17 EBattle3MsgBtlLightningB`
- `EF:8F4A EBattle3MsgBtlLightningC`
- `EF:8F91 EBattle3MsgBtlGyiyyig3`
- `EF:8FAD EfPostEbattle3TextPayloadData`

Evidence:

- `notes/bank-ef-first-pass.md`
- `notes/ef-runtime-semantic-polish-plan.md`
- `notes/c2-ef-battle-text-contract-workahead.md`
- `notes/ef-battle-text-payload-runtime-polish.md`

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
