# ebsrc Knowns Integration Candidates

Status: restored ebsrc knowns are classified for curated integration; local source semantics remain primary.

## Summary

- banks audited: `['C0', 'C1', 'C2', 'C3', 'C4', 'EF']`
- candidates: `8384`
- source rename default: `do_not_rename_when_local_name_is_more_specific`
- first curated adoption policy: `apply only high-confidence exact symbols, table names, constants, and fields after local role/byte-equivalence review`

## Candidate Classes

| Class | Count | Action |
| --- | ---: | --- |
| `adopt_constant_or_field_name` | 4249 | use as contract/comment vocabulary when touching the related semantic builder |
| `adopt_exact_symbol` | 18 | consider a reviewed source label promotion while preserving old address-prefixed aliases |
| `adopt_table_name` | 1 | use as table-name corroboration when local role and byte range already agree |
| `blocked_unaddressed_or_payload_only` | 660 | keep as reference-only until there is exact local source or reader-path evidence |
| `keep_local_supersedes` | 1814 | keep local semantic name/classification primary; cite ebsrc as corroborating reference |
| `macro_vocab_reference` | 1396 | feed into event/text/actionscript decoder vocabulary only after local opcode proof |
| `manual_review` | 246 | review address, role, and naming superiority before any source/doc adoption |

## Lane Counts

| Lane | Count |
| --- | ---: |
| `audio-spc700` | 322 |
| `bank-c0` | 473 |
| `bank-c1` | 184 |
| `bank-c2` | 120 |
| `bank-c3` | 43 |
| `bank-ef` | 86 |
| `battle-runtime` | 290 |
| `data-records` | 230 |
| `event-actionscript` | 886 |
| `macro-vocabulary` | 510 |
| `map-data` | 13 |
| `overworld-runtime` | 199 |
| `ppu-window-presentation` | 478 |
| `shared-constants` | 3700 |
| `shared-struct-fields` | 549 |
| `text-vm` | 301 |

## First Curated Adoption Batch

These are review-ready candidates only; source labels should be promoted separately with byte-equivalence validation.

| Target | Lane | Reference | ebsrc Name | Local Name | Reason |
| --- | --- | --- | --- | --- | --- |
| `C1:488C` | `text-vm` | `text/ccs/set_secmem.asm` | `SET_SECMEM` | `` | exact-covered named code has a non-placeholder ebsrc symbol and generic local name |
| `C1:DD3B` | `text-vm` | `text/show_hppp_windows_redirect.asm` | `SHOW_HPPP_WINDOWS_REDIRECT` | `RedirectShowHpppWindows` | exact-covered named code has a non-placeholder ebsrc symbol and generic local name |
| `C1:DD41` | `text-vm` | `text/hide_hppp_windows_redirect.asm` | `HIDE_HPPP_WINDOWS_REDIRECT` | `RedirectHideHpppWindows` | exact-covered named code has a non-placeholder ebsrc symbol and generic local name |
| `C1:DD47` | `text-vm` | `text/create_window_redirect.asm` | `CREATE_WINDOW_REDIRECT` | `RedirectCreateWindow` | exact-covered named code has a non-placeholder ebsrc symbol and generic local name |
| `C1:DD4D` | `text-vm` | `text/set_window_focus_redirect.asm` | `SET_WINDOW_FOCUS_REDIRECT` | `RedirectSetWindowFocus` | exact-covered named code has a non-placeholder ebsrc symbol and generic local name |
| `C1:DD59` | `text-vm` | `text/close_focus_window_redirect.asm` | `CLOSE_FOCUS_WINDOW_REDIRECT` | `RedirectCloseFocusWindow` | exact-covered named code has a non-placeholder ebsrc symbol and generic local name |
| `C1:DDC6` | `bank-c1` | `misc/remove_item_from_inventory_redirect.asm` | `REMOVE_ITEM_FROM_INVENTORY_REDIRECT` | `RedirectRemoveItemFromInventory` | exact-covered named code has a non-placeholder ebsrc symbol and generic local name |
| `C1:E1A2` | `text-vm` | `text/print_menu_items_redirect.asm` | `PRINT_MENU_ITEMS_REDIRECT` | `NullFarCallback` | exact-covered named code has a non-placeholder ebsrc symbol and generic local name |
| `C2:955F` | `battle-runtime` | `battle/actions/psi_rockin_alpha.asm` | `PSI_ROCKIN_ALPHA` | `` | exact-covered named code has a non-placeholder ebsrc symbol and generic local name |
| `C2:9568` | `battle-runtime` | `battle/actions/psi_rockin_beta.asm` | `PSI_ROCKIN_BETA` | `` | exact-covered named code has a non-placeholder ebsrc symbol and generic local name |
| `C2:9571` | `battle-runtime` | `battle/actions/psi_rockin_gamma.asm` | `PSI_ROCKIN_GAMMA` | `` | exact-covered named code has a non-placeholder ebsrc symbol and generic local name |
| `C2:95B4` | `battle-runtime` | `battle/actions/psi_fire_alpha.asm` | `PSI_FIRE_ALPHA` | `` | exact-covered named code has a non-placeholder ebsrc symbol and generic local name |
| `C2:95BD` | `battle-runtime` | `battle/actions/psi_fire_beta.asm` | `PSI_FIRE_BETA` | `` | exact-covered named code has a non-placeholder ebsrc symbol and generic local name |
| `C2:95C6` | `battle-runtime` | `battle/actions/psi_fire_gamma.asm` | `PSI_FIRE_GAMMA` | `` | exact-covered named code has a non-placeholder ebsrc symbol and generic local name |
| `C2:9650` | `battle-runtime` | `battle/actions/psi_freeze_alpha.asm` | `PSI_FREEZE_ALPHA` | `` | exact-covered named code has a non-placeholder ebsrc symbol and generic local name |
| `C2:9659` | `battle-runtime` | `battle/actions/psi_freeze_beta.asm` | `PSI_FREEZE_BETA` | `` | exact-covered named code has a non-placeholder ebsrc symbol and generic local name |
| `C2:9662` | `battle-runtime` | `battle/actions/psi_freeze_gamma.asm` | `PSI_FREEZE_GAMMA` | `` | exact-covered named code has a non-placeholder ebsrc symbol and generic local name |
| `C3:FB1F` | `data-records` | `data/hp_meter_speeds.asm` | `HP_METER_SPEEDS` | `DATA_C3FB1F` | exact-covered named data table can corroborate local table naming |
| `C4:EDA3` | `ppu-window-presentation` | `ending/play_cast_scene.asm` | `PLAY_CAST_SCENE` | `UnusedCastNameScratchRenderer` | exact-covered named code has a non-placeholder ebsrc symbol and generic local name |
| `NO_EFFECT` | `shared-constants` | `refs/ebsrc-main/ebsrc-main/include/constants/actions.asm` | `NO_EFFECT` | `` | restored ebsrc constant/enum vocabulary can improve local semantic contracts |
| `USE_NO_EFFECT` | `shared-constants` | `refs/ebsrc-main/ebsrc-main/include/constants/actions.asm` | `USE_NO_EFFECT` | `` | restored ebsrc constant/enum vocabulary can improve local semantic contracts |
| `ACTION_002` | `shared-constants` | `refs/ebsrc-main/ebsrc-main/include/constants/actions.asm` | `ACTION_002` | `` | restored ebsrc constant/enum vocabulary can improve local semantic contracts |
| `ACTION_003` | `shared-constants` | `refs/ebsrc-main/ebsrc-main/include/constants/actions.asm` | `ACTION_003` | `` | restored ebsrc constant/enum vocabulary can improve local semantic contracts |
| `BASH` | `shared-constants` | `refs/ebsrc-main/ebsrc-main/include/constants/actions.asm` | `BASH` | `` | restored ebsrc constant/enum vocabulary can improve local semantic contracts |
| `SHOOT` | `shared-constants` | `refs/ebsrc-main/ebsrc-main/include/constants/actions.asm` | `SHOOT` | `` | restored ebsrc constant/enum vocabulary can improve local semantic contracts |
| `SPY` | `shared-constants` | `refs/ebsrc-main/ebsrc-main/include/constants/actions.asm` | `SPY` | `` | restored ebsrc constant/enum vocabulary can improve local semantic contracts |
| `PRAY` | `shared-constants` | `refs/ebsrc-main/ebsrc-main/include/constants/actions.asm` | `PRAY` | `` | restored ebsrc constant/enum vocabulary can improve local semantic contracts |
| `GUARD` | `shared-constants` | `refs/ebsrc-main/ebsrc-main/include/constants/actions.asm` | `GUARD` | `` | restored ebsrc constant/enum vocabulary can improve local semantic contracts |
| `ACTION_009` | `shared-constants` | `refs/ebsrc-main/ebsrc-main/include/constants/actions.asm` | `ACTION_009` | `` | restored ebsrc constant/enum vocabulary can improve local semantic contracts |
| `PSI_ROCKIN_ALPHA` | `shared-constants` | `refs/ebsrc-main/ebsrc-main/include/constants/actions.asm` | `PSI_ROCKIN_ALPHA` | `` | restored ebsrc constant/enum vocabulary can improve local semantic contracts |
| `PSI_ROCKIN_BETA` | `shared-constants` | `refs/ebsrc-main/ebsrc-main/include/constants/actions.asm` | `PSI_ROCKIN_BETA` | `` | restored ebsrc constant/enum vocabulary can improve local semantic contracts |
| `PSI_ROCKIN_GAMMA` | `shared-constants` | `refs/ebsrc-main/ebsrc-main/include/constants/actions.asm` | `PSI_ROCKIN_GAMMA` | `` | restored ebsrc constant/enum vocabulary can improve local semantic contracts |
| `PSI_ROCKIN_OMEGA` | `shared-constants` | `refs/ebsrc-main/ebsrc-main/include/constants/actions.asm` | `PSI_ROCKIN_OMEGA` | `` | restored ebsrc constant/enum vocabulary can improve local semantic contracts |
| `PSI_FIRE_ALPHA` | `shared-constants` | `refs/ebsrc-main/ebsrc-main/include/constants/actions.asm` | `PSI_FIRE_ALPHA` | `` | restored ebsrc constant/enum vocabulary can improve local semantic contracts |
| `PSI_FIRE_BETA` | `shared-constants` | `refs/ebsrc-main/ebsrc-main/include/constants/actions.asm` | `PSI_FIRE_BETA` | `` | restored ebsrc constant/enum vocabulary can improve local semantic contracts |
| `PSI_FIRE_GAMMA` | `shared-constants` | `refs/ebsrc-main/ebsrc-main/include/constants/actions.asm` | `PSI_FIRE_GAMMA` | `` | restored ebsrc constant/enum vocabulary can improve local semantic contracts |
| `PSI_FIRE_OMEGA` | `shared-constants` | `refs/ebsrc-main/ebsrc-main/include/constants/actions.asm` | `PSI_FIRE_OMEGA` | `` | restored ebsrc constant/enum vocabulary can improve local semantic contracts |
| `PSI_FREEZE_ALPHA` | `shared-constants` | `refs/ebsrc-main/ebsrc-main/include/constants/actions.asm` | `PSI_FREEZE_ALPHA` | `` | restored ebsrc constant/enum vocabulary can improve local semantic contracts |
| `PSI_FREEZE_BETA` | `shared-constants` | `refs/ebsrc-main/ebsrc-main/include/constants/actions.asm` | `PSI_FREEZE_BETA` | `` | restored ebsrc constant/enum vocabulary can improve local semantic contracts |
| `PSI_FREEZE_GAMMA` | `shared-constants` | `refs/ebsrc-main/ebsrc-main/include/constants/actions.asm` | `PSI_FREEZE_GAMMA` | `` | restored ebsrc constant/enum vocabulary can improve local semantic contracts |

## Samples By Class

### `adopt_exact_symbol`

| Target | Lane | Reference | ebsrc Name | Local Name | Reason |
| --- | --- | --- | --- | --- | --- |
| `C1:488C` | `text-vm` | `text/ccs/set_secmem.asm` | `SET_SECMEM` | `` | exact-covered named code has a non-placeholder ebsrc symbol and generic local name |
| `C1:DD3B` | `text-vm` | `text/show_hppp_windows_redirect.asm` | `SHOW_HPPP_WINDOWS_REDIRECT` | `RedirectShowHpppWindows` | exact-covered named code has a non-placeholder ebsrc symbol and generic local name |
| `C1:DD41` | `text-vm` | `text/hide_hppp_windows_redirect.asm` | `HIDE_HPPP_WINDOWS_REDIRECT` | `RedirectHideHpppWindows` | exact-covered named code has a non-placeholder ebsrc symbol and generic local name |
| `C1:DD47` | `text-vm` | `text/create_window_redirect.asm` | `CREATE_WINDOW_REDIRECT` | `RedirectCreateWindow` | exact-covered named code has a non-placeholder ebsrc symbol and generic local name |
| `C1:DD4D` | `text-vm` | `text/set_window_focus_redirect.asm` | `SET_WINDOW_FOCUS_REDIRECT` | `RedirectSetWindowFocus` | exact-covered named code has a non-placeholder ebsrc symbol and generic local name |
| `C1:DD59` | `text-vm` | `text/close_focus_window_redirect.asm` | `CLOSE_FOCUS_WINDOW_REDIRECT` | `RedirectCloseFocusWindow` | exact-covered named code has a non-placeholder ebsrc symbol and generic local name |
| `C1:DDC6` | `bank-c1` | `misc/remove_item_from_inventory_redirect.asm` | `REMOVE_ITEM_FROM_INVENTORY_REDIRECT` | `RedirectRemoveItemFromInventory` | exact-covered named code has a non-placeholder ebsrc symbol and generic local name |
| `C1:E1A2` | `text-vm` | `text/print_menu_items_redirect.asm` | `PRINT_MENU_ITEMS_REDIRECT` | `NullFarCallback` | exact-covered named code has a non-placeholder ebsrc symbol and generic local name |
| `C2:955F` | `battle-runtime` | `battle/actions/psi_rockin_alpha.asm` | `PSI_ROCKIN_ALPHA` | `` | exact-covered named code has a non-placeholder ebsrc symbol and generic local name |
| `C2:9568` | `battle-runtime` | `battle/actions/psi_rockin_beta.asm` | `PSI_ROCKIN_BETA` | `` | exact-covered named code has a non-placeholder ebsrc symbol and generic local name |
| `C2:9571` | `battle-runtime` | `battle/actions/psi_rockin_gamma.asm` | `PSI_ROCKIN_GAMMA` | `` | exact-covered named code has a non-placeholder ebsrc symbol and generic local name |
| `C2:95B4` | `battle-runtime` | `battle/actions/psi_fire_alpha.asm` | `PSI_FIRE_ALPHA` | `` | exact-covered named code has a non-placeholder ebsrc symbol and generic local name |
| `C2:95BD` | `battle-runtime` | `battle/actions/psi_fire_beta.asm` | `PSI_FIRE_BETA` | `` | exact-covered named code has a non-placeholder ebsrc symbol and generic local name |
| `C2:95C6` | `battle-runtime` | `battle/actions/psi_fire_gamma.asm` | `PSI_FIRE_GAMMA` | `` | exact-covered named code has a non-placeholder ebsrc symbol and generic local name |
| `C2:9650` | `battle-runtime` | `battle/actions/psi_freeze_alpha.asm` | `PSI_FREEZE_ALPHA` | `` | exact-covered named code has a non-placeholder ebsrc symbol and generic local name |
| `C2:9659` | `battle-runtime` | `battle/actions/psi_freeze_beta.asm` | `PSI_FREEZE_BETA` | `` | exact-covered named code has a non-placeholder ebsrc symbol and generic local name |
| `C2:9662` | `battle-runtime` | `battle/actions/psi_freeze_gamma.asm` | `PSI_FREEZE_GAMMA` | `` | exact-covered named code has a non-placeholder ebsrc symbol and generic local name |
| `C4:EDA3` | `ppu-window-presentation` | `ending/play_cast_scene.asm` | `PLAY_CAST_SCENE` | `UnusedCastNameScratchRenderer` | exact-covered named code has a non-placeholder ebsrc symbol and generic local name |

### `adopt_constant_or_field_name`

| Target | Lane | Reference | ebsrc Name | Local Name | Reason |
| --- | --- | --- | --- | --- | --- |
| `NO_EFFECT` | `shared-constants` | `refs/ebsrc-main/ebsrc-main/include/constants/actions.asm` | `NO_EFFECT` | `` | restored ebsrc constant/enum vocabulary can improve local semantic contracts |
| `USE_NO_EFFECT` | `shared-constants` | `refs/ebsrc-main/ebsrc-main/include/constants/actions.asm` | `USE_NO_EFFECT` | `` | restored ebsrc constant/enum vocabulary can improve local semantic contracts |
| `ACTION_002` | `shared-constants` | `refs/ebsrc-main/ebsrc-main/include/constants/actions.asm` | `ACTION_002` | `` | restored ebsrc constant/enum vocabulary can improve local semantic contracts |
| `ACTION_003` | `shared-constants` | `refs/ebsrc-main/ebsrc-main/include/constants/actions.asm` | `ACTION_003` | `` | restored ebsrc constant/enum vocabulary can improve local semantic contracts |
| `BASH` | `shared-constants` | `refs/ebsrc-main/ebsrc-main/include/constants/actions.asm` | `BASH` | `` | restored ebsrc constant/enum vocabulary can improve local semantic contracts |
| `SHOOT` | `shared-constants` | `refs/ebsrc-main/ebsrc-main/include/constants/actions.asm` | `SHOOT` | `` | restored ebsrc constant/enum vocabulary can improve local semantic contracts |
| `SPY` | `shared-constants` | `refs/ebsrc-main/ebsrc-main/include/constants/actions.asm` | `SPY` | `` | restored ebsrc constant/enum vocabulary can improve local semantic contracts |
| `PRAY` | `shared-constants` | `refs/ebsrc-main/ebsrc-main/include/constants/actions.asm` | `PRAY` | `` | restored ebsrc constant/enum vocabulary can improve local semantic contracts |
| `GUARD` | `shared-constants` | `refs/ebsrc-main/ebsrc-main/include/constants/actions.asm` | `GUARD` | `` | restored ebsrc constant/enum vocabulary can improve local semantic contracts |
| `ACTION_009` | `shared-constants` | `refs/ebsrc-main/ebsrc-main/include/constants/actions.asm` | `ACTION_009` | `` | restored ebsrc constant/enum vocabulary can improve local semantic contracts |
| `PSI_ROCKIN_ALPHA` | `shared-constants` | `refs/ebsrc-main/ebsrc-main/include/constants/actions.asm` | `PSI_ROCKIN_ALPHA` | `` | restored ebsrc constant/enum vocabulary can improve local semantic contracts |
| `PSI_ROCKIN_BETA` | `shared-constants` | `refs/ebsrc-main/ebsrc-main/include/constants/actions.asm` | `PSI_ROCKIN_BETA` | `` | restored ebsrc constant/enum vocabulary can improve local semantic contracts |
| `PSI_ROCKIN_GAMMA` | `shared-constants` | `refs/ebsrc-main/ebsrc-main/include/constants/actions.asm` | `PSI_ROCKIN_GAMMA` | `` | restored ebsrc constant/enum vocabulary can improve local semantic contracts |
| `PSI_ROCKIN_OMEGA` | `shared-constants` | `refs/ebsrc-main/ebsrc-main/include/constants/actions.asm` | `PSI_ROCKIN_OMEGA` | `` | restored ebsrc constant/enum vocabulary can improve local semantic contracts |
| `PSI_FIRE_ALPHA` | `shared-constants` | `refs/ebsrc-main/ebsrc-main/include/constants/actions.asm` | `PSI_FIRE_ALPHA` | `` | restored ebsrc constant/enum vocabulary can improve local semantic contracts |
| `PSI_FIRE_BETA` | `shared-constants` | `refs/ebsrc-main/ebsrc-main/include/constants/actions.asm` | `PSI_FIRE_BETA` | `` | restored ebsrc constant/enum vocabulary can improve local semantic contracts |
| `PSI_FIRE_GAMMA` | `shared-constants` | `refs/ebsrc-main/ebsrc-main/include/constants/actions.asm` | `PSI_FIRE_GAMMA` | `` | restored ebsrc constant/enum vocabulary can improve local semantic contracts |
| `PSI_FIRE_OMEGA` | `shared-constants` | `refs/ebsrc-main/ebsrc-main/include/constants/actions.asm` | `PSI_FIRE_OMEGA` | `` | restored ebsrc constant/enum vocabulary can improve local semantic contracts |
| `PSI_FREEZE_ALPHA` | `shared-constants` | `refs/ebsrc-main/ebsrc-main/include/constants/actions.asm` | `PSI_FREEZE_ALPHA` | `` | restored ebsrc constant/enum vocabulary can improve local semantic contracts |
| `PSI_FREEZE_BETA` | `shared-constants` | `refs/ebsrc-main/ebsrc-main/include/constants/actions.asm` | `PSI_FREEZE_BETA` | `` | restored ebsrc constant/enum vocabulary can improve local semantic contracts |

### `adopt_table_name`

| Target | Lane | Reference | ebsrc Name | Local Name | Reason |
| --- | --- | --- | --- | --- | --- |
| `C3:FB1F` | `data-records` | `data/hp_meter_speeds.asm` | `HP_METER_SPEEDS` | `DATA_C3FB1F` | exact-covered named data table can corroborate local table naming |

### `macro_vocab_reference`

| Target | Lane | Reference | ebsrc Name | Local Name | Reason |
| --- | --- | --- | --- | --- | --- |
| `C0:AD8A` | `event-actionscript` | `data/events/scripts/786.asm` | `EVENT_786` | `Event786_CurrentSlotOrbitScript` | event script label/macro vocabulary reference; no behavior claim from ebsrc alone |
| `C2:FFB7` | `event-actionscript` | `data/events/scripts/000.asm` | `EVENT_000` | `C2FFB7_BankEndTailBytes` | event script label/macro vocabulary reference; no behavior claim from ebsrc alone |
| `C3:0295` | `event-actionscript` | `data/events/scripts/221.asm` | `EVENT_221` | `MoveActiveEntityLeftToScriptVarsAndWait` | event script label/macro vocabulary reference; no behavior claim from ebsrc alone |
| `C3:098B` | `event-actionscript` | `data/events/scripts/222.asm` | `EVENT_222` | `C3098B_MoveActiveEntityLeftToScriptVarsAndWaitEnd` | event script label/macro vocabulary reference; no behavior claim from ebsrc alone |
| `C3:0A1F` | `event-actionscript` | `data/events/scripts/223.asm` | `EVENT_223` | `C30A1F_C3098BEventScriptEnd` | event script label/macro vocabulary reference; no behavior claim from ebsrc alone |
| `C3:0C55` | `event-actionscript` | `data/events/scripts/224.asm` | `EVENT_224` | `C30C55_C30A1FEventScriptEnd` | event script label/macro vocabulary reference; no behavior claim from ebsrc alone |
| `C3:098B` | `event-actionscript` | `data/events/scripts/225+226+227.asm` | `225+226+227` | `C3098B_MoveActiveEntityLeftToScriptVarsAndWaitEnd` | event script label/macro vocabulary reference; no behavior claim from ebsrc alone |
| `C3:0A1F` | `event-actionscript` | `data/events/scripts/228.asm` | `EVENT_228` | `C30A1F_C3098BEventScriptEnd` | event script label/macro vocabulary reference; no behavior claim from ebsrc alone |
| `C3:0C55` | `event-actionscript` | `data/events/scripts/229.asm` | `EVENT_229` | `C30C55_C30A1FEventScriptEnd` | event script label/macro vocabulary reference; no behavior claim from ebsrc alone |
| `C3:0C67` | `event-actionscript` | `data/events/scripts/230.asm` | `EVENT_230` | `C30C67_C30C55EventScriptEnd` | event script label/macro vocabulary reference; no behavior claim from ebsrc alone |
| `C3:1D2D` | `event-actionscript` | `data/events/scripts/231.asm` | `EVENT_231` | `C31D2D_C30C67EventScriptEnd` | event script label/macro vocabulary reference; no behavior claim from ebsrc alone |
| `C3:1D4F` | `event-actionscript` | `data/events/scripts/232.asm` | `EVENT_232` | `C31D4F_C31D2DEventScriptEnd` | event script label/macro vocabulary reference; no behavior claim from ebsrc alone |
| `C3:1DF4` | `event-actionscript` | `data/events/scripts/228+229+230+231+232_common.asm` | `228+229+230+231+232_COMMON` | `C31DF4_C31D4FEventScriptEnd` | event script label/macro vocabulary reference; no behavior claim from ebsrc alone |
| `C3:1E2D` | `event-actionscript` | `data/events/scripts/233+234+235+236+237.asm` | `233+234+235+236+237` | `C31E2D_C31DF4EventScriptEnd` | event script label/macro vocabulary reference; no behavior claim from ebsrc alone |
| `C3:1EC1` | `event-actionscript` | `data/events/scripts/238.asm` | `EVENT_238` | `C31EC1_C31E2DEventScriptEnd` | event script label/macro vocabulary reference; no behavior claim from ebsrc alone |
| `C3:1ED8` | `event-actionscript` | `data/events/scripts/239.asm` | `EVENT_239` | `C31ED8_C31EC1EventScriptEnd` | event script label/macro vocabulary reference; no behavior claim from ebsrc alone |
| `C3:1EEF` | `event-actionscript` | `data/events/scripts/240.asm` | `EVENT_240` | `C31EEF_C31ED8EventScriptEnd` | event script label/macro vocabulary reference; no behavior claim from ebsrc alone |
| `C3:2138` | `event-actionscript` | `data/events/scripts/241.asm` | `EVENT_241` | `C32138_C31EEFEventScriptEnd` | event script label/macro vocabulary reference; no behavior claim from ebsrc alone |
| `C3:2CD2` | `event-actionscript` | `data/events/scripts/242+243.asm` | `242+243` | `C32CD2_C32138EventScriptEnd` | event script label/macro vocabulary reference; no behavior claim from ebsrc alone |
| `C3:3399` | `event-actionscript` | `data/events/scripts/244.asm` | `EVENT_244` | `C33399_C32CD2EventScriptEnd` | event script label/macro vocabulary reference; no behavior claim from ebsrc alone |

### `keep_local_supersedes`

| Target | Lane | Reference | ebsrc Name | Local Name | Reason |
| --- | --- | --- | --- | --- | --- |
| `C0:0E16` | `bank-c0` | `unknown/C0/C00E16.asm` | `` | `Upload_VerticalMovementMapStrip` | restored ebsrc still marks this span unknown; keep local semantic classification |
| `C0:0FCB` | `bank-c0` | `unknown/C0/C00FCB.asm` | `` | `Upload_HorizontalMovementMapStrip` | restored ebsrc still marks this span unknown; keep local semantic classification |
| `C0:1181` | `bank-c0` | `unknown/C0/C01181.asm` | `` | `Upload_AuxiliaryMovementMapStrip` | restored ebsrc still marks this span unknown; keep local semantic classification |
| `C0:1731` | `bank-c0` | `unknown/C0/C01731.asm` | `` | `` | restored ebsrc still marks this span unknown; keep local semantic classification |
| `C0:17EA` | `bank-c0` | `unknown/C0/C017EA.asm` | `` | `AccumulateOverworldCameraStep` | restored ebsrc still marks this span unknown; keep local semantic classification |
| `C0:19E2` | `overworld-runtime` | `overworld/reload_map.asm` | `RELOAD_MAP` | `Refresh_MapStripsAroundCamera` | local code name is already more specific; keep as primary and record ebsrc as corroboration |
| `C0:1A63` | `overworld-runtime` | `overworld/initialize_map.asm` | `INITIALIZE_MAP` | `Refresh_MapStripVia0E16_FarWrapper` | local code name is already more specific; keep as primary and record ebsrc as corroboration |
| `C0:19E2` | `bank-c0` | `unknown/C0/C019E2.asm` | `` | `Refresh_MapStripsAroundCamera` | restored ebsrc still marks this span unknown; keep local semantic classification |
| `C0:1A63` | `bank-c0` | `unknown/C0/C01A63.asm` | `` | `Refresh_MapStripVia0E16_FarWrapper` | restored ebsrc still marks this span unknown; keep local semantic classification |
| `C0:1A69` | `overworld-runtime` | `overworld/initialize_misc_object_data.asm` | `INITIALIZE_MISC_OBJECT_DATA` | `Reset_EntitySlotStateTables` | restored ebsrc semantic name is already present in the local source module |
| `C0:1A86` | `bank-c0` | `unknown/C0/C01A86.asm` | `` | `Reset_EntityBytePool467E` | restored ebsrc still marks this span unknown; keep local semantic classification |
| `C0:1A9D` | `overworld-runtime` | `overworld/find_free_space_7E4682.asm` | `FIND_FREE_SPACE_7E4682` | `Find_FreeEntityBytePoolRun467E` | local code name is already more specific; keep as primary and record ebsrc as corroboration |
| `C0:1B15` | `bank-c0` | `unknown/C0/C01B15.asm` | `` | `Release_EntityBytePoolRun467E` | restored ebsrc still marks this span unknown; keep local semantic classification |
| `C0:1B96` | `bank-c0` | `unknown/C0/C01B96.asm` | `` | `Reserve_VisualMemorySpan4A00` | restored ebsrc still marks this span unknown; keep local semantic classification |
| `C0:1C11` | `bank-c0` | `system/alloc_sprite_mem.asm` | `ALLOC_SPRITE_MEM` | `Rewrite_VisualMemoryReservations4A00` | restored ebsrc semantic name is already present in the local source module |
| `C0:1C52` | `bank-c0` | `unknown/C0/C01C52.asm` | `` | `ReserveAndUpload_EntityVisualTiles` | restored ebsrc still marks this span unknown; keep local semantic classification |
| `C0:1D38` | `bank-c0` | `unknown/C0/C01D38.asm` | `` | `Build_EntityVisualRecords467E` | restored ebsrc still marks this span unknown; keep local semantic classification |
| `C0:1DED` | `bank-c0` | `unknown/C0/C01DED.asm` | `` | `Read_SpritePoseVisualDescriptor` | restored ebsrc still marks this span unknown; keep local semantic classification |
| `C0:1E49` | `overworld-runtime` | `overworld/create_entity.asm` | `CREATE_ENTITY` | `Initialize_EntityWithSpritePose` | restored ebsrc semantic name is already present in the local source module |
| `C0:20F1` | `bank-c0` | `unknown/C0/C020F1.asm` | `` | `ScriptRelease_CurrentEntityVisualState` | restored ebsrc still marks this span unknown; keep local semantic classification |

### `blocked_unaddressed_or_payload_only`

| Target | Lane | Reference | ebsrc Name | Local Name | Reason |
| --- | --- | --- | --- | --- | --- |
| `` | `bank-c0` | `common.asm` | `COMMON` | `` | support include; useful as reference but not a local semantic target |
| `` | `bank-c0` | `config.asm` | `CONFIG` | `` | support include; useful as reference but not a local semantic target |
| `` | `bank-c0` | `eventmacros.asm` | `EVENTMACROS` | `` | support include; useful as reference but not a local semantic target |
| `` | `bank-c0` | `structs.asm` | `STRUCTS` | `` | support include; useful as reference but not a local semantic target |
| `` | `bank-c0` | `symbols/bank00.inc.asm` | `BANK00.INC` | `` | support include; useful as reference but not a local semantic target |
| `` | `bank-c0` | `symbols/bank01.inc.asm` | `BANK01.INC` | `` | support include; useful as reference but not a local semantic target |
| `` | `bank-c0` | `symbols/bank02.inc.asm` | `BANK02.INC` | `` | support include; useful as reference but not a local semantic target |
| `` | `bank-c0` | `symbols/bank03.inc.asm` | `BANK03.INC` | `` | support include; useful as reference but not a local semantic target |
| `` | `bank-c0` | `symbols/bank04.inc.asm` | `BANK04.INC` | `` | support include; useful as reference but not a local semantic target |
| `` | `bank-c0` | `symbols/bank2f.inc.asm` | `BANK2F.INC` | `` | support include; useful as reference but not a local semantic target |
| `` | `bank-c0` | `symbols/doors.inc.asm` | `DOORS.INC` | `` | support include; useful as reference but not a local semantic target |
| `` | `bank-c0` | `symbols/globals.inc.asm` | `GLOBALS.INC` | `` | support include; useful as reference but not a local semantic target |
| `` | `map-data` | `symbols/map.inc.asm` | `MAP.INC` | `` | support include; useful as reference but not a local semantic target |
| `` | `bank-c0` | `symbols/misc.inc.asm` | `MISC.INC` | `` | support include; useful as reference but not a local semantic target |
| `` | `bank-c0` | `symbols/sram.inc.asm` | `SRAM.INC` | `` | support include; useful as reference but not a local semantic target |
| `` | `text-vm` | `symbols/text.inc.asm` | `TEXT.INC` | `` | support include; useful as reference but not a local semantic target |
| `` | `overworld-runtime` | `overworld/actionscript/clear_entity_draw_sorting_table.asm` | `CLEAR_ENTITY_DRAW_SORTING_TABLE` | `` | semantic reference is not exact-covered by local source |
| `` | `overworld-runtime` | `overworld/setup_vram.asm` | `OVERWORLD_SETUP_VRAM` | `` | semantic reference is not exact-covered by local source |
| `` | `overworld-runtime` | `overworld/initialize.asm` | `OVERWORLD_INITIALIZE` | `` | semantic reference is not exact-covered by local source |
| `` | `ppu-window-presentation` | `system/load_tileset_anim.asm` | `LOAD_TILESET_ANIM` | `` | semantic reference is not exact-covered by local source |

### `manual_review`

| Target | Lane | Reference | ebsrc Name | Local Name | Reason |
| --- | --- | --- | --- | --- | --- |
| `C0:8CD5` | `data-records` | `data/C08C58_jumps.asm` | `` | `Apply_DisplayRendererQueueRecord` | exact-covered semantic include has no non-placeholder ebsrc symbol or table stem |
| `C0:943C` | `data-records` | `data/palette_dma_parameters.asm` | `PALETTE_DMA_PARAMETERS` | `MarkWorldObjectChainForSetup` | named ebsrc data overlaps a non-generic local source name; review before adopting |
| `C0:94AA` | `data-records` | `data/dma_table.asm` | `DMA_TABLE` | `Process_ActiveTaskSlots` | named ebsrc data overlaps a non-generic local source name; review before adopting |
| `C0:9558` | `data-records` | `data/movement_control_codes_pointer_table.asm` | `MOVEMENT_CONTROL_CODES_POINTER_TABLE` | `ScriptOpcodePointerTable` | named ebsrc data overlaps a non-generic local source name; review before adopting |
| `C0:9B09` | `data-records` | `data/events/entity_script_var_tables.asm` | `ENTITY_SCRIPT_VAR_TABLES` | `ScriptOp_InitCurrentTaskRecordDefaults` | named ebsrc data overlaps a non-generic local source name; review before adopting |
| `C0:AC3A` | `data-records` | `data/stereo_mono_data.asm` | `STEREO_MONO_DATA` | `SendApuPort2Byte` | named ebsrc data overlaps a non-generic local source name; review before adopting |
| `C0:C4F7` | `map-data` | `data/map/opposite_directions.asm` | `OPPOSITE_DIRECTIONS` | `GetDirectionFromPlayerToEntity` | named ebsrc data overlaps a non-generic local source name; review before adopting |
| `C1:E1A2` | `bank-c1` | `misc/null/C1E1A2.asm` | `` | `NullFarCallback` | exact-covered semantic include has no non-placeholder ebsrc symbol or table stem |
| `C2:09A0` | `text-vm` | `data/text/the.asm` | `THE` | `CloseAndClearCurrentWindowTilemap` | named ebsrc data overlaps a non-generic local source name; review before adopting |
| `C3:0295` | `data-records` | `data/events/C30295.asm` | `` | `MoveActiveEntityLeftToScriptVarsAndWait` | exact-covered semantic include has no non-placeholder ebsrc symbol or table stem |
| `C3:098B` | `data-records` | `data/events/C3098B.asm` | `` | `C3098B_MoveActiveEntityLeftToScriptVarsAndWaitEnd` | exact-covered semantic include has no non-placeholder ebsrc symbol or table stem |
| `C3:0A1F` | `data-records` | `data/events/C30A1F.asm` | `` | `C30A1F_C3098BEventScriptEnd` | exact-covered semantic include has no non-placeholder ebsrc symbol or table stem |
| `C3:0C55` | `data-records` | `data/events/C30C55.asm` | `` | `C30C55_C30A1FEventScriptEnd` | exact-covered semantic include has no non-placeholder ebsrc symbol or table stem |
| `C3:0C67` | `data-records` | `data/events/C30C67.asm` | `` | `C30C67_C30C55EventScriptEnd` | exact-covered semantic include has no non-placeholder ebsrc symbol or table stem |
| `C3:1D2D` | `data-records` | `data/events/C31D2D.asm` | `` | `C31D2D_C30C67EventScriptEnd` | exact-covered semantic include has no non-placeholder ebsrc symbol or table stem |
| `C3:1D4F` | `data-records` | `data/events/C31D4F.asm` | `` | `C31D4F_C31D2DEventScriptEnd` | exact-covered semantic include has no non-placeholder ebsrc symbol or table stem |
| `C3:1DF4` | `data-records` | `data/events/C31DF4.asm` | `` | `C31DF4_C31D4FEventScriptEnd` | exact-covered semantic include has no non-placeholder ebsrc symbol or table stem |
| `C3:1E2D` | `data-records` | `data/events/C31E2D.asm` | `` | `C31E2D_C31DF4EventScriptEnd` | exact-covered semantic include has no non-placeholder ebsrc symbol or table stem |
| `C3:1EC1` | `data-records` | `data/events/C31EC1.asm` | `` | `C31EC1_C31E2DEventScriptEnd` | exact-covered semantic include has no non-placeholder ebsrc symbol or table stem |
| `C3:1ED8` | `data-records` | `data/events/C31ED8.asm` | `` | `C31ED8_C31EC1EventScriptEnd` | exact-covered semantic include has no non-placeholder ebsrc symbol or table stem |

## Guardrails

- Do not bulk-import restored ebsrc `UNKNOWN` names.
- Keep local names when they are more specific than restored ebsrc names.
- Treat macro names and unaddressed payloads as decoder/reference input, not behavior proof.
- Run bank byte-equivalence checks before committing any source label promotion.
