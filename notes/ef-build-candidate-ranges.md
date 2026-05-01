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
- `EF:69EA..EF:6AE0` (`246` bytes, SHA-1 `0d5c241896ccb7b02bfeb32ad4d86f31eba5f42d`) `EBattle5AmountAndStatusPreludeText`
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
- `EF:6C6B..EF:6F9A` (`815` bytes, SHA-1 `2fe86c65a91f609f7d72fe250b1deede5cda18c3`) `EBattle5StatusAndNpcDeathText`
- `EF:6F9A..EF:6FBD` (`35` bytes, SHA-1 `32b9f94859cc1256432748a68c7afd7904e57bfb`) `EBattle5MsgBtlShieldOn`
- `EF:6FBD..EF:6FD3` (`22` bytes, SHA-1 `75d0bac14ab6514e2ea88b25e1500ef00dbe9695`) `EBattle5MsgBtlShieldAdd`
- `EF:6FD3..EF:6FF4` (`33` bytes, SHA-1 `436ff24c2b098518d72aea4b6e92c7ae016598e4`) `EBattle5MsgBtlPowerShieldOn`
- `EF:6FF4..EF:700C` (`24` bytes, SHA-1 `91688e4579bfd0a98d936abb9eeb605696421bdb`) `EBattle5MsgBtlPowerShieldAdd`
- `EF:700C..EF:7032` (`38` bytes, SHA-1 `8e09d7147d7b1d6f5812c470721b0cf2a891391a`) `EBattle5MsgBtlPsychicShieldOn`
- `EF:7032..EF:7050` (`30` bytes, SHA-1 `95e260b622016c2efeadc2209d43bf3512c25816`) `EBattle5MsgBtlPsychicShieldAdd`
- `EF:7050..EF:707A` (`42` bytes, SHA-1 `ef9940bdeff8772e33413e1128347df7677d3049`) `EBattle5MsgBtlPsiPowerShieldOn`
- `EF:707A..EF:7099` (`31` bytes, SHA-1 `b696662c257fbd2ce9510ea7933052b89d4fbf38`) `EBattle5MsgBtlPsiPowerShieldAdd`
- `EF:7099..EF:7186` (`237` bytes, SHA-1 `e76fe16e4e367d440f1be13d535266373ed6fb20`) `EBattle5ShieldTurnAndNeutralizeText`
- `EF:7186..EF:766E` (`1256` bytes, SHA-1 `91b0965d6124e0d4c0f933e878f798917355e3ba`) `EBattle4PreNoEffectBattleText`
- `EF:766E..EF:7682` (`20` bytes, SHA-1 `6097e90c945e2f040dfd0fac365f206f0fe77d8d`) `EBattle4MsgBtlStatusNoEffect`
- `EF:7682..EF:7696` (`20` bytes, SHA-1 `6097e90c945e2f040dfd0fac365f206f0fe77d8d`) `EBattle4AdjacentNoEffectText`
- `EF:7696..EF:76B3` (`29` bytes, SHA-1 `e4113ef4fa47015dc03660c723c49ae26e239e23`) `EBattle4MsgBtlNoVisibleEffect`
- `EF:76B3..EF:773F` (`140` bytes, SHA-1 `575f13249e5df1ad8aca9ea0699944c0253db22d`) `EBattle4LateMissAndDrainPreludeText`
- `EF:773F..EF:7755` (`22` bytes, SHA-1 `6232b10ccb1d72f3eadde7a851e2688209a5c83a`) `EBattle4MsgBtlPpDrainAmount`
- `EF:7755..EF:77FD` (`168` bytes, SHA-1 `dd4beaa5a8c9cefefa6f4e5ba4eb2c9a6531450d`) `EBattle4RemainingDamageOverTimeText`
- `EF:77FD..EF:7B77` (`890` bytes, SHA-1 `58b1e4156748c4f82dba0ee374957988e2086fbd`) `EBattle8CallForHelpAndLevelUpText`
- `EF:7B77..EF:7B83` (`12` bytes, SHA-1 `b6be0ba66868c82cafdd691ac712705f421cd14f`) `EBattle8ByteSubstitutionPsiNameText`
- `EF:7B83..EF:7B85` (`2` bytes, SHA-1 `d13061bfe442388f8bf8b53be38aa80ed585e8b5`) `EBattle8PointerSubstitutionIntroState`
- `EF:7B85..EF:7BA0` (`27` bytes, SHA-1 `0b507165fcb107b37b9f7d92fdf7728fb2dff65a`) `EBattle8PointerSubstitutionSweetBranch`
- `EF:7BA0..EF:7BA2` (`2` bytes, SHA-1 `d13061bfe442388f8bf8b53be38aa80ed585e8b5`) `EBattle8PointerSubstitutionBranch2State`
- `EF:7BA2..EF:7BBF` (`29` bytes, SHA-1 `4a8f6b390ce34f65d348108205b2f550d4323e90`) `EBattle8PointerSubstitutionTearsBranch`
- `EF:7BBF..EF:7BC1` (`2` bytes, SHA-1 `d13061bfe442388f8bf8b53be38aa80ed585e8b5`) `EBattle8PointerSubstitutionBranch3State`
- `EF:7BC1..EF:7BDF` (`30` bytes, SHA-1 `20ff702f734c16985cdf2024350476ddbae5485a`) `EBattle8PointerSubstitutionOhBabyBranch`
- `EF:7BDF..EF:7C42` (`99` bytes, SHA-1 `ac0008afdd533cbce642a6a974fdc139a6e12e2e`) `EBattle8MsgBtlPresentByteSubstitution`
- `EF:7C42..EF:7DD5` (`403` bytes, SHA-1 `aad1b60802b5e4178d26960edcb9f969bd1b6fba`) `EBattle8PresentInventoryResultText`
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
- `EF:69EA EBattle5AmountAndStatusPreludeText`
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
- `EF:6C6B EBattle5StatusAndNpcDeathText`
- `EF:6F9A EBattle5MsgBtlShieldOn`
- `EF:6FBD EBattle5MsgBtlShieldAdd`
- `EF:6FD3 EBattle5MsgBtlPowerShieldOn`
- `EF:6FF4 EBattle5MsgBtlPowerShieldAdd`
- `EF:700C EBattle5MsgBtlPsychicShieldOn`
- `EF:7032 EBattle5MsgBtlPsychicShieldAdd`
- `EF:7050 EBattle5MsgBtlPsiPowerShieldOn`
- `EF:707A EBattle5MsgBtlPsiPowerShieldAdd`
- `EF:7099 EBattle5ShieldTurnAndNeutralizeText`
- `EF:7186 EBattle4PreNoEffectBattleText`
- `EF:766E EBattle4MsgBtlStatusNoEffect`
- `EF:7682 EBattle4AdjacentNoEffectText`
- `EF:7696 EBattle4MsgBtlNoVisibleEffect`
- `EF:76B3 EBattle4LateMissAndDrainPreludeText`
- `EF:773F EBattle4MsgBtlPpDrainAmount`
- `EF:7755 EBattle4RemainingDamageOverTimeText`
- `EF:77FD EBattle8CallForHelpAndLevelUpText`
- `EF:7B77 EBattle8ByteSubstitutionPsiNameText`
- `EF:7B83 EBattle8PointerSubstitutionIntroState`
- `EF:7B85 EBattle8PointerSubstitutionSweetBranch`
- `EF:7BA0 EBattle8PointerSubstitutionBranch2State`
- `EF:7BA2 EBattle8PointerSubstitutionTearsBranch`
- `EF:7BBF EBattle8PointerSubstitutionBranch3State`
- `EF:7BC1 EBattle8PointerSubstitutionOhBabyBranch`
- `EF:7BDF EBattle8MsgBtlPresentByteSubstitution`
- `EF:7C42 EBattle8PresentInventoryResultText`
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
