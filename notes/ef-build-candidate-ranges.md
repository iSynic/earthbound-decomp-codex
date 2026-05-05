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
- `EF:7186..EF:75AB` (`1061` bytes, SHA-1 `d9bc54b2be269050c6fff70a778cd425edf280cd`) `EBattle4StatusEventPreludeText`
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
- `EF:7858..EF:7B77` (`799` bytes, SHA-1 `86833bd8daa945b5d02f70b7a05e510f45dad7ed`) `EBattle8AppearVictoryLevelUpText`
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
- `EF:7E25..EF:843F` (`1562` bytes, SHA-1 `efa6270325aec8cbac88465ebe4dc1b864e62d0c`) `EBattle2AndPreStartBattleText`
- `EF:843F..EF:8444` (`5` bytes, SHA-1 `d296611446d215d359e8c7664e0a30f31aa7b62e`) `EBattle0MsgAtStartAsleep`
- `EF:8444..EF:8445` (`1` bytes, SHA-1 `c4ea21bb365bbeeaf5f2c654883e56d11e43c44e`) `EBattle0MsgAtStartPsiSeal`
- `EF:8445..EF:845D` (`24` bytes, SHA-1 `290b309cbe7864982914515bbac8838cfec3ec00`) `EBattle0MsgAtStartStrange`
- `EF:845D..EF:8477` (`26` bytes, SHA-1 `b9cc80704b48261d7854d1582bd91cdb057d291d`) `EBattle0MsgRandomActStrange`
- `EF:8477..EF:848C` (`21` bytes, SHA-1 `e8df4e1a416a16e883880dddfb6f8cfea9620e20`) `EBattle0MsgRandomActMushroom`
- `EF:848C..EF:C51B` (`16527` bytes, SHA-1 `dab5835771e09fd99e15ea184f8f4fc7da9eab54`) `EfPostBattleTextPayloadData`

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
- `EF:7186 EBattle4StatusEventPreludeText`
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
- `EF:7858 EBattle8AppearVictoryLevelUpText`
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
- `EF:7E25 EBattle2AndPreStartBattleText`
- `EF:843F EBattle0MsgAtStartAsleep`
- `EF:8444 EBattle0MsgAtStartPsiSeal`
- `EF:8445 EBattle0MsgAtStartStrange`
- `EF:845D EBattle0MsgRandomActStrange`
- `EF:8477 EBattle0MsgRandomActMushroom`
- `EF:848C EfPostBattleTextPayloadData`

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
