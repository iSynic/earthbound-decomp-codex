# C3 actionscript semantics audit

Generated from `notes/c3-source-data-map.md` via `tools/build_c3_actionscript_semantics_audit.py`. This report is the first semantic frontier for C3 event/actionscript payloads after byte-equivalent source-bank closure.

## Summary

- schema: `earthbound-decomp.c3-actionscript-semantics-audit.v1`
- script rows audited: `177`
- by extraction class: `{'event-bytecode-asset': 37, 'event-bytecode-label': 35, 'event-script-asset': 105}`
- by decode status: `{'complete': 177}`
- native callback contract seeds: `85`
- decode bounds: `120` instructions, `0x400` bytes per row unless the source-map row is shorter

## Top opcode and target signals

- top first opcodes: `{'$42 EVENT_CALLROUTINE': 49, '$06 EVENT_PAUSE': 36, '$25 EVENT_SET_PHYSICS_CALLBACK': 24, '$1A EVENT_SHORTCALL': 14, '$0E EVENT_SET_VAR': 9, '$20 EVENT_WRITE_VAR_TO_TEMPVAR': 5, '$3B EVENT_SET_ANIMATION': 5, '$01 EVENT_LOOP': 5, '$23 EVENT_SET_POSITION_CHANGE_CALLBACK': 4, '$07 EVENT_START_TASK': 3, '$40 EVENT_SET_Y_VELOCITY': 2, '$39 EVENT_SET_VELOCITIES_ZERO': 2}`
- top native callback targets: `{'C0:A4BF': 29, 'C0:A685': 26, 'C0:A4B2': 26, 'C0:A4A8': 23, 'C0:AA6E': 15, 'C0:A65F': 10, 'C4:6E46': 8, 'C4:0015': 8, 'C0:9F82': 7, 'C0:20F1': 7, 'C0:C6B6': 6, 'C0:A864': 5, 'EF:0FF6': 5, 'C0:A88D': 5, 'C0:A68B': 4, 'C0:D98F': 4}`
- unknown callback targets: `{}`
- top C3 script targets: `{'C3:A204': 19, 'C3:AB59': 17, 'C3:A111': 7, 'C3:A0FE': 5, 'C3:AA1E': 5, 'C3:AA38': 4, 'C3:A1F3': 4, 'C3:A262': 4, 'C3:A11E': 4, 'C3:A3B7': 4, 'C3:43DB': 3, 'C3:443E': 3, 'C3:44FF': 3, 'C3:AB26': 3, 'C3:5F8B': 3, 'C3:A052': 3}`

## Frontier rows

No syntactic decode frontiers at the current bounds.

## Native callback contract seed

| Target | Preferred name | Calls | Arg bytes | Status |
| --- | --- | ---: | ---: | --- |
| `C0:A4BF` | `RefreshCurrentSlotVisualProfile_Mode0` | 29 | 0 | `byte-count-known` |
| `C0:A685` | `Script_SetCurrentSlotField2B32` | 26 | 2 | `byte-count-known` |
| `C0:A4B2` | `RefreshCurrentSlotVisualProfile_Mode1IfAligned` | 26 | 0 | `byte-count-known` |
| `C0:A4A8` | `RefreshCurrentSlotVisualProfile_Mode0IfAligned` | 23 | 0 | `byte-count-known` |
| `C0:AA6E` | `Script_ApplyCurrentSlotVisualCountdownState` | 15 | 2 | `byte-count-known` |
| `C0:A65F` | `SetCurrentSlotDirectionClassIfActive` | 10 | 0 | `byte-count-known` |
| `C4:6E46` | `SetYieldToTextLatch9641` | 8 | 0 | `byte-count-known` |
| `C4:0015` | `ClearCurrentSlot10f2RefreshVisualAndCheckLiveArea` | 8 | 0 | `byte-count-known` |
| `C0:9F82` | `ChooseRandomScriptWord` | 7 | 0 | `byte-count-known` |
| `C0:20F1` | `ScriptRelease_CurrentEntityVisualState` | 7 | 0 | `byte-count-known` |
| `C0:C6B6` | `CheckCurrentSlotInsideLiveAreaWindow` | 6 | 0 | `byte-count-known` |
| `C0:A864` | `Script_CopyRegistrySlotAnchorToCurrentSlot_ReadByte` | 5 | 1 | `byte-count-known` |
| `EF:0FF6` | `UNKNOWN_EF0FF6` | 5 | 0 | `byte-count-known` |
| `C0:A88D` | `ActionScript_QueueTextPointer` | 5 | 4 | `byte-count-known` |
| `C0:A68B` | `StoreAInCurrentSlotField2B32` | 4 | 0 | `byte-count-known` |
| `C0:D98F` | `Export_CurrentSlotAttentionTarget` | 4 | 0 | `byte-count-known` |
| `C4:6C87` | `RestoreCurrentSlotAnchorFromCachedTarget` | 4 | 0 | `byte-count-known` |
| `C0:A943` | `ActionScript_GetPositionOfPartyMember` | 3 | 1 | `byte-count-known` |
| `C0:A841` | `Script_PlaySoundEffectParameter` | 3 | 2 | `byte-count-known` |
| `C0:C7DB` | `UpdateCurrentSlotFootprintMask` | 3 | 0 | `byte-count-known` |
| `C2:0000` | `label_C20000` | 3 | 0 | `byte-count-known` |
| `C0:A6DA` | `label_C0A6DA` | 3 | 0 | `byte-count-known` |
| `C0:C83B` | `InstallScriptMovementVectorFromDirection` | 3 | 0 | `byte-count-known` |
| `C0:CA4E` | `SetMovementTaskTimerFromActiveVector` | 3 | 0 | `byte-count-known` |
| `C4:6ADB` | `ComputeCurrentSlotTargetDirectionOctant` | 3 | 0 | `byte-count-known` |
| `C4:7044` | `ProjectAngleIntoCurrentSlotVectorWords` | 3 | 0 | `byte-count-known` |
| `C4:6B0A` | `RoundAngleToOctantAndCacheCurrentSlot` | 3 | 0 | `byte-count-known` |
| `C0:A82F` | `` | 3 | 0 | `byte-count-known` |
| `C4:7B77` | `LoadIndexedWindowGfxAndReadVariantByte` | 2 | 0 | `byte-count-known` |
| `C0:A691` | `GetCurrentSlotField2B32` | 2 | 0 | `byte-count-known` |
| `EF:0F60` | `UNKNOWN_EF0F60` | 2 | 0 | `byte-count-known` |
| `EF:0DFA` | `UNKNOWN_EF0DFA` | 2 | 0 | `byte-count-known` |
| `C4:6EF8` | `CheckCurrentSlotWithinPlayerProximityThreshold` | 2 | 0 | `byte-count-known` |
| `C0:A959` | `ScriptWrapper_C469F1_ReadWord` | 2 | 2 | `byte-count-known` |
| `C0:A98B` | `ScriptWrapper_C46534_ReadThreeWords` | 2 | 4 | `byte-count-known` |
| `C0:A679` | `Script_SetCurrentSlotDisplayControlBits` | 2 | 1 | `byte-count-known` |
| `C4:0023` | `StoreLowNibble1a42ToCurrentScriptField1372` | 2 | 0 | `byte-count-known` |
| `C0:A84C` | `ScriptWrapper_C21628_ReadWord` | 2 | 2 | `byte-count-known` |
| `C0:A6E3` | `WatchAndRefreshCompanionVisualPhase` | 2 | 0 | `byte-count-known` |
| `C4:7269` | `ClassifyCurrentSlotAgainstAreaBounds` | 2 | 0 | `byte-count-known` |
| `C0:6478` | `Update_CurrentSlotNeighborCache_Priority` | 2 | 0 | `byte-count-known` |
| `C0:D5B0` | `Gate_NpcAttentionCoordinatorFromScript` | 2 | 0 | `byte-count-known` |
| `C0:A8DC` | `ScriptWrapper_C47143_Mode01` | 2 | 0 | `byte-count-known` |
| `C4:6E74` | `label_C46E74` | 2 | 0 | `byte-count-known` |
| `C4:8B3B` | `` | 2 | 0 | `byte-count-known` |
| `C0:A8C6` | `ScriptWrapper_C47143_Mode00` | 2 | 0 | `byte-count-known` |
| `C0:A907` | `ActionScript_PrepareNewEntityAtTeleportDestination` | 2 | 1 | `byte-count-known` |
| `C0:9FBB` | `ActionScript_FadeOutWrapper` | 2 | 2 | `byte-count-known` |
| `C4:7A9E` | `LoadCurrentEntityIndexedWindowGfxToVram` | 1 | 0 | `byte-count-known` |
| `C4:800B` | `label_C4800B` | 1 | 0 | `byte-count-known` |
| `C4:68B5` | `TestValueLeftOfCurrentAnchorX` | 1 | 0 | `byte-count-known` |
| `C4:68DC` | `TestValueAboveCurrentAnchorY` | 1 | 0 | `byte-count-known` |
| `EF:0CA7` | `UNKNOWN_EF0CA7` | 1 | 0 | `byte-count-known` |
| `EF:0D23` | `UNKNOWN_EF0D23` | 1 | 0 | `byte-count-known` |
| `C2:FF9A` | `CheckOverworldPositionHashThreshold3Of8` | 1 | 0 | `byte-count-known` |
| `C0:C19B` | `CopyPathToLane_FromPartyMemberRequest` | 1 | 0 | `byte-count-known` |
| `EF:0FDB` | `UNKNOWN_EF0FDB` | 1 | 0 | `byte-count-known` |
| `EF:0D8D` | `UNKNOWN_EF0D8D` | 1 | 0 | `byte-count-known` |
| `C0:C251` | `CopyPathToLane_FromCurrentEntityRequestReverse` | 1 | 0 | `byte-count-known` |
| `EF:0E8A` | `UNKNOWN_EF0E8A` | 1 | 0 | `byte-count-known` |
| `EF:0E67` | `UNKNOWN_EF0E67` | 1 | 0 | `byte-count-known` |
| `C4:ECE7` | `IsEntityStillOnCastScreen` | 1 | 0 | `byte-count-known` |
| `C0:D15C` | `HasUsableOverlapNeighborContext` | 1 | 0 | `byte-count-known` |
| `C4:681A` | `QueueCurrentVisualTypeMovementScript` | 1 | 0 | `byte-count-known` |
| `C4:6914` | `GetCurrentVisualTypeRecordByte03` | 1 | 0 | `byte-count-known` |
| `C4:6957` | `UpdateCurrentSlotFrameSelector` | 1 | 0 | `byte-count-known` |
| `C1:FFD3` | `label_C1FFD3` | 1 | 0 | `byte-count-known` |
| `C3:0100` | `DisplayAntiPiracyScreen` | 1 | 0 | `byte-count-known` |
| `C0:3DAA` | `Sync_CurrentSlotToPartyCharacterRecord` | 1 | 0 | `byte-count-known` |
| `C0:4EF0` | `Restore_CurrentSlotFromSnapshotRecord` | 1 | 0 | `byte-count-known` |
| `C0:5E76` | `Update_CurrentSlotCollisionCache` | 1 | 4 | `byte-count-known` |
| `C0:A964` | `ScriptWrapper_C47225_ReadTwoWords` | 1 | 4 | `byte-count-known` |
| `C0:A6B8` | `GetCurrentSlotHasNoCachedNeighborFlag` | 1 | 0 | `byte-count-known` |
| `C0:5E82` | `Update_CurrentSlotCollisionCache_WithTerrainCompatibility` | 1 | 0 | `byte-count-known` |
| `C0:5ECE` | `Update_CurrentSlotCollisionCache_FromHorizontalEdges` | 1 | 0 | `byte-count-known` |
| `C0:D59B` | `Check_NpcAttentionCoordinatorActive` | 1 | 0 | `byte-count-known` |
| `C4:6B37` | `RotateDirectionOctantHalfTurn` | 1 | 0 | `byte-count-known` |
| `C0:A8D1` | `ScriptWrapper_C47143_Mode10` | 1 | 0 | `byte-count-known` |
| `C0:A857` | `ScriptWrapper_C2165E_ReadWordPreserveMode` | 1 | 2 | `byte-count-known` |
| `C4:7333` | `ReadActiveOverworldRegistryCount` | 1 | 0 | `byte-count-known` |
| `C4:6C45` | `SnapshotCurrentSlotAnchorToStagedPosition` | 1 | 0 | `byte-count-known` |
| `C0:A94E` | `ScriptWrapper_C46984_ReadWord` | 1 | 2 | `byte-count-known` |
| `C0:A86F` | `Script_CopyPoseDescriptorSlotAnchorToCurrentSlot_ReadWord` | 1 | 2 | `byte-count-known` |
| `C0:A651` | `Script_SetDirectionClassAndField1A86` | 1 | 1 | `byte-count-known` |
| `C0:9451` | `UNKNOWN_C09451` | 1 | 0 | `byte-count-known` |

## Full script inventory

| Address | Name | Class | Decode | Instr. | First opcode | Callbacks | C3 targets |
| --- | --- | --- | --- | ---: | --- | --- | --- |
| `C3:0295` | `MoveActiveEntityLeftToScriptVarsAndWait` | `event-bytecode-asset` | `complete` | 6 | `$1A EVENT_SHORTCALL` | `C0:AA6E`, `C0:A685` | `C3:AA38`, `C3:AB59` |
| `C3:098B` | `` | `event-script-asset` | `complete` | 3 | `$1A EVENT_SHORTCALL` | `C4:6E46` | `C3:AB59` |
| `C3:0A1F` | `` | `event-script-asset` | `complete` | 8 | `$41 EVENT_SET_Z_VELOCITY` | - | - |
| `C3:0C55` | `` | `event-script-asset` | `complete` | 5 | `$1A EVENT_SHORTCALL` | `C0:A685`, `C0:A4BF` | `C3:AA2B` |
| `C3:0C67` | `` | `event-script-asset` | `complete` | 36 | `$06 EVENT_PAUSE` | - | `C3:AB59`, `C3:0C67` |
| `C3:1D2D` | `` | `event-script-asset` | `complete` | 11 | `$20 EVENT_WRITE_VAR_TO_TEMPVAR` | `C0:A4B2`, `C0:A4A8` | `C3:1D4A`, `C3:1D2D` |
| `C3:1D4F` | `` | `event-script-asset` | `complete` | 7 | `$25 EVENT_SET_PHYSICS_CALLBACK` | `C0:A4BF` | `C3:1D2D` |
| `C3:1DF4` | `` | `event-script-asset` | `complete` | 11 | `$42 EVENT_CALLROUTINE` | `C0:A864` | `C3:1E14`, `C3:AB59`, `C3:1E0C` |
| `C3:1E2D` | `` | `event-script-asset` | `complete` | 11 | `$25 EVENT_SET_PHYSICS_CALLBACK` | `C0:A943` | `C3:1E4D`, `C3:AB59`, `C3:1E45` |
| `C3:1EC1` | `` | `event-script-asset` | `complete` | 10 | `$06 EVENT_PAUSE` | `C0:A4B2`, `C0:A4A8` | - |
| `C3:1ED8` | `` | `event-script-asset` | `complete` | 10 | `$06 EVENT_PAUSE` | `C0:A4B2`, `C0:A4A8` | - |
| `C3:1EEF` | `` | `event-script-asset` | `complete` | 73 | `$3F EVENT_SET_X_VELOCITY` | `C0:AA6E`, `C0:A65F`, `C0:A4A8` | `C3:2138` |
| `C3:2138` | `` | `event-script-asset` | `complete` | 7 | `$3B EVENT_SET_ANIMATION` | `C0:A4A8`, `C0:A4B2` | - |
| `C3:2CD2` | `` | `event-script-asset` | `complete` | 14 | `$40 EVENT_SET_Y_VELOCITY` | - | `C3:2CD2` |
| `C3:3399` | `` | `event-script-asset` | `complete` | 5 | `$42 EVENT_CALLROUTINE` | `C0:AA6E` | - |
| `C3:33AA` | `` | `event-script-asset` | `complete` | 5 | `$42 EVENT_CALLROUTINE` | `C0:AA6E` | - |
| `C3:33BB` | `` | `event-script-asset` | `complete` | 5 | `$42 EVENT_CALLROUTINE` | `C0:AA6E` | - |
| `C3:33CC` | `` | `event-script-asset` | `complete` | 5 | `$42 EVENT_CALLROUTINE` | `C0:AA6E` | - |
| `C3:33DD` | `` | `event-script-asset` | `complete` | 19 | `$1A EVENT_SHORTCALL` | `C0:AA6E` | `C3:3399` |
| `C3:3549` | `` | `event-script-asset` | `complete` | 11 | `$42 EVENT_CALLROUTINE` | `C0:AA6E`, `C0:9F82` | `C3:3549` |
| `C3:3BFB` | `` | `event-script-asset` | `complete` | 9 | `$3B EVENT_SET_ANIMATION` | `C4:7A9E`, `C4:7B77` | `C3:3C18`, `C3:3C08` |
| `C3:3C18` | `` | `event-script-asset` | `complete` | 2 | `$42 EVENT_CALLROUTINE` | `C4:800B` | - |
| `C3:3C1D` | `` | `event-script-asset` | `complete` | 8 | `$20 EVENT_WRITE_VAR_TO_TEMPVAR` | `C4:7B77` | `C3:3C2F` |
| `C3:3DBE` | `` | `event-script-asset` | `complete` | 8 | `$01 EVENT_LOOP` | `C0:A691`, `C0:A68B` | - |
| `C3:4392` | `` | `event-script-asset` | `complete` | 9 | `$07 EVENT_START_TASK` | `C0:AA6E` | `C3:43AE`, `C3:A204` |
| `C3:43AE` | `` | `event-script-asset` | `complete` | 14 | `$06 EVENT_PAUSE` | `C4:68B5`, `C4:68DC` | `C3:43C4`, `C3:43D8`, `C3:43AE`, `C3:A204` |
| `C3:43DB` | `LoopTimedDeliveryDeparturePulseUntilOffscreen` | `event-bytecode-label` | `complete` | 13 | `$06 EVENT_PAUSE` | `C0:A4B2`, `C0:A4A8`, `C0:C6B6`, `EF:0FF6`, +1 | `C3:43E8`, `C3:43DB`, `C3:A204` |
| `C3:43E8` | `TimedDeliveryDeparturePulseAnimation0Half` | `event-bytecode-asset` | `complete` | 8 | `$06 EVENT_PAUSE` | `C0:A4A8`, `C0:C6B6`, `EF:0FF6`, `C4:6E46` | `C3:43DB`, `C3:A204` |
| `C3:443E` | `TimedDeliveryRetryWaitLoop` | `event-bytecode-asset` | `complete` | 9 | `$42 EVENT_CALLROUTINE` | `EF:0CA7`, `EF:0D23`, `EF:0F60` | `C3:447D`, `C3:4457`, `C3:443E` |
| `C3:444D` | `TimedDeliveryReadinessGate` | `event-bytecode-asset` | `complete` | 3 | `$42 EVENT_CALLROUTINE` | `EF:0F60` | `C3:4457`, `C3:443E` |
| `C3:4457` | `TimedDeliverySuccessGateAndPresentationSetup` | `event-bytecode-asset` | `complete` | 11 | `$42 EVENT_CALLROUTINE` | `C2:FF9A`, `C0:C19B`, `EF:0FDB`, `EF:0D8D` | `C3:447D`, `C3:443E`, `C3:447A`, `C3:4488`, +1 |
| `C3:447A` | `StartTimedDeliveryArrivalMovementTask` | `event-bytecode-label` | `complete` | 4 | `$1A EVENT_SHORTCALL` | `EF:0FF6`, `EF:0DFA` | `C3:44DE`, `C3:A204` |
| `C3:447D` | `TimedDeliveryFailureTeardown` | `event-bytecode-asset` | `complete` | 3 | `$42 EVENT_CALLROUTINE` | `EF:0FF6`, `EF:0DFA` | `C3:A204` |
| `C3:4488` | `PrepareTimedDeliveryActorForPresentation` | `event-bytecode-asset` | `complete` | 11 | `$3B EVENT_SET_ANIMATION` | `C0:A4BF`, `C4:6EF8` | `C3:A09F`, `C3:44A7`, `C3:4499` |
| `C3:4499` | `WaitTimedDeliveryActorPresentationPrep` | `event-bytecode-label` | `complete` | 6 | `$06 EVENT_PAUSE` | `C4:6EF8` | `C3:44A7`, `C3:4499` |
| `C3:44A7` | `ReturnFromTimedDeliveryActorPrep` | `event-bytecode-label` | `complete` | 1 | `$1B EVENT_SHORT_RETURN` | - | - |
| `C3:44A8` | `RunTimedDeliveryDepartureMovement` | `event-bytecode-asset` | `complete` | 15 | `$39 EVENT_SET_VELOCITIES_ZERO` | `C0:C251`, `EF:0E8A`, `C0:A68B`, `C0:D98F`, +1 | `C3:43DB`, `C3:44D2`, `C3:AB59`, `C3:44C1` |
| `C3:44C1` | `LoopTimedDeliveryDepartureMovement` | `event-bytecode-label` | `complete` | 5 | `$42 EVENT_CALLROUTINE` | `C0:D98F`, `C4:6C87` | `C3:44D2`, `C3:AB59`, `C3:44C1` |
| `C3:44D2` | `FinishTimedDeliveryDepartureAndYieldText` | `event-bytecode-label` | `complete` | 4 | `$39 EVENT_SET_VELOCITIES_ZERO` | `EF:0FF6`, `C4:6E46` | `C3:A204` |
| `C3:44DE` | `RunTimedDeliveryArrivalMovement` | `event-bytecode-asset` | `complete` | 9 | `$42 EVENT_CALLROUTINE` | `EF:0E67`, `C0:A68B`, `C0:D98F`, `C4:6C87` | `C3:44FF`, `C3:AB59`, `C3:44EE` |
| `C3:44EE` | `LoopTimedDeliveryArrivalMovement` | `event-bytecode-label` | `complete` | 5 | `$42 EVENT_CALLROUTINE` | `C0:D98F`, `C4:6C87` | `C3:44FF`, `C3:AB59`, `C3:44EE` |
| `C3:44FF` | `HoldTimedDeliveryArrivalCompletion` | `event-bytecode-label` | `complete` | 3 | `$0E EVENT_SET_VAR` | - | `C3:44FF` |
| `C3:48C4` | `` | `event-script-asset` | `complete` | 19 | `$1D EVENT_WRITE_WORD_TEMPVAR` | `C0:A65F`, `C0:A4BF` | - |
| `C3:4964` | `` | `event-script-asset` | `complete` | 4 | `$42 EVENT_CALLROUTINE` | `C0:A959` | `C3:4964` |
| `C3:4A61` | `` | `event-script-asset` | `complete` | 3 | `$42 EVENT_CALLROUTINE` | `C0:A959` | `C3:4A61` |
| `C3:4B62` | `` | `event-script-asset` | `complete` | 25 | `$42 EVENT_CALLROUTINE` | `C0:AA6E` | - |
| `C3:4D39` | `` | `event-script-asset` | `complete` | 13 | `$2A EVENT_SET_Z` | `C0:A841`, `C4:6E46` | `C3:AB26` |
| `C3:4E73` | `` | `event-script-asset` | `complete` | 6 | `$42 EVENT_CALLROUTINE` | `C0:A864` | - |
| `C3:5F8B` | `` | `event-script-asset` | `complete` | 15 | `$21 EVENT_WRITE_VAR_TO_WAIT_TIMER` | `C0:A4B2`, `C4:ECE7`, `C0:A4A8` | `C3:5F98`, `C3:5FB3`, `C3:5FAC`, `C3:5F8B`, +1 |
| `C3:5FB6` | `` | `event-script-asset` | `complete` | 9 | `$21 EVENT_WRITE_VAR_TO_WAIT_TIMER` | - | `C3:5F8B` |
| `C3:5FCD` | `` | `event-script-asset` | `complete` | 8 | `$0E EVENT_SET_VAR` | - | `C3:5F8B` |
| `C3:62C0` | `` | `event-script-asset` | `complete` | 9 | `$42 EVENT_CALLROUTINE` | `C0:AA6E` | - |
| `C3:6834` | `` | `event-script-asset` | `complete` | 2 | `$42 EVENT_CALLROUTINE` | `C0:A98B` | `C3:A204` |
| `C3:6A3E` | `` | `event-script-asset` | `complete` | 1 | `$19 EVENT_SHORTJUMP` | - | `C3:A204` |
| `C3:6A41` | `` | `event-script-asset` | `complete` | 7 | `$25 EVENT_SET_PHYSICS_CALLBACK` | `C0:A679` | `C3:A1F3`, `C3:A262` |
| `C3:6BB4` | `` | `event-script-asset` | `complete` | 7 | `$20 EVENT_WRITE_VAR_TO_TEMPVAR` | - | `C3:6BC1`, `C3:6BB4` |
| `C3:6BEA` | `` | `event-script-asset` | `complete` | 1 | `$00 EVENT_END` | - | - |
| `C3:6D18` | `` | `event-script-asset` | `complete` | 6 | `$06 EVENT_PAUSE` | `C0:D15C`, `C4:681A` | `C3:6D18`, `C3:9E01` |
| `C3:6E41` | `` | `event-script-asset` | `complete` | 5 | `$42 EVENT_CALLROUTINE` | `C4:0023`, `C4:6914`, `C4:6957` | `C3:6E45` |
| `C3:7439` | `` | `event-script-asset` | `complete` | 9 | `$25 EVENT_SET_PHYSICS_CALLBACK` | `C0:C7DB`, `C0:A4A8`, `C0:A685` | - |
| `C3:7545` | `` | `event-script-asset` | `complete` | 7 | `$01 EVENT_LOOP` | `C0:AA6E` | - |
| `C3:7559` | `` | `event-script-asset` | `complete` | 7 | `$01 EVENT_LOOP` | `C0:AA6E` | - |
| `C3:7A7C` | `` | `event-script-asset` | `complete` | 6 | `$25 EVENT_SET_PHYSICS_CALLBACK` | - | `C3:A15E` |
| `C3:835D` | `` | `event-script-asset` | `complete` | 2 | `$10 EVENT_SWITCH_JUMP_TEMPVAR` | - | `C3:8370`, `C3:8383`, `C3:8396`, `C3:83A9` |
| `C3:83BC` | `` | `event-script-asset` | `complete` | 2 | `$42 EVENT_CALLROUTINE` | `C0:9F82` | - |
| `C3:8978` | `` | `event-script-asset` | `complete` | 6 | `$20 EVENT_WRITE_VAR_TO_TEMPVAR` | `C0:A84C` | `C3:8992`, `C3:898C`, `C3:8995` |
| `C3:899E` | `` | `event-script-asset` | `complete` | 11 | `$3B EVENT_SET_ANIMATION` | `C0:A4A8`, `C0:A4B2` | `C3:899E` |
| `C3:9AC7` | `` | `event-script-asset` | `complete` | 7 | `$25 EVENT_SET_PHYSICS_CALLBACK` | `C0:C7DB`, `C0:A4BF` | `C3:9ABB` |
| `C3:9E01` | `` | `event-script-asset` | `complete` | 5 | `$1E EVENT_WRITE_WRAM_TEMPVAR` | - | `C3:9E0E` |
| `C3:A043` | `IntroCutsceneCameraPanGate` | `event-bytecode-asset` | `complete` | 9 | `$42 EVENT_CALLROUTINE` | `C1:FFD3`, `C3:0100`, `C2:0000` | `C3:A04E`, `C3:0100`, `C3:A052` |
| `C3:A04E` | `StartIntroCameraPanTickLoop` | `event-bytecode-label` | `complete` | 6 | `$08 EVENT_SET_TICK_CALLBACK` | `C2:0000` | `C3:A052` |
| `C3:A052` | `LoopIntroCameraPanWaitAndC2Step` | `event-bytecode-label` | `complete` | 5 | `$01 EVENT_LOOP` | `C2:0000` | `C3:A052` |
| `C3:A05E` | `IntroCutsceneSpriteObjectSetup` | `event-bytecode-asset` | `complete` | 10 | `$23 EVENT_SET_POSITION_CHANGE_CALLBACK` | `C0:3DAA`, `C0:4EF0`, `C0:A6DA`, `C0:A6E3` | `C3:A076` |
| `C3:A076` | `LoopIntroCompanionVisualRefresh` | `event-bytecode-label` | `complete` | 3 | `$42 EVENT_CALLROUTINE` | `C0:A6E3` | `C3:A076` |
| `C3:A07F` | `HaltEventScript` | `event-bytecode-asset` | `complete` | 1 | `$09 EVENT_HALT` | - | - |
| `C3:A09F` | `LoopActiveEntityWalkAnimationPulse` | `event-bytecode-label` | `complete` | 7 | `$06 EVENT_PAUSE` | `C0:A4B2`, `C0:A4A8` | `C3:A09F` |
| `C3:A0B2` | `LoopActiveEntityWalkPulse24Frame` | `event-bytecode-label` | `complete` | 7 | `$06 EVENT_PAUSE` | `C0:A4B2`, `C0:A4A8` | `C3:A0B2` |
| `C3:A0C5` | `LoopActiveEntityWalkPulse12Frame` | `event-bytecode-label` | `complete` | 7 | `$06 EVENT_PAUSE` | `C0:A4B2`, `C0:A4A8` | `C3:A0C5` |
| `C3:A0D8` | `LoopActiveEntityWalkPulse9FrameConditional` | `event-bytecode-label` | `complete` | 32 | `$06 EVENT_PAUSE` | `C0:A4B2`, `C0:A4A8` | `C3:A0D8`, `C3:A0EB`, `C3:A0FE`, `C3:A11E`, +1 |
| `C3:A0EB` | `LoopActiveEntityWalkPulse6FrameConditional` | `event-bytecode-label` | `complete` | 25 | `$06 EVENT_PAUSE` | `C0:A4B2`, `C0:A4A8` | `C3:A0EB`, `C3:A0FE`, `C3:A11E`, `C3:A111` |
| `C3:A0FE` | `LoopActiveEntityWalkPulse2FrameConditional` | `event-bytecode-label` | `complete` | 18 | `$06 EVENT_PAUSE` | `C0:A4B2`, `C0:A4A8` | `C3:A0FE`, `C3:A11E`, `C3:A111` |
| `C3:A111` | `LoopActiveEntityWalkPulseVar4Gate` | `event-bytecode-label` | `complete` | 11 | `$06 EVENT_PAUSE` | `C0:A4B2`, `C0:A4A8` | `C3:A11E`, `C3:A111` |
| `C3:A12E` | `LoopActiveEntityWalkPulseVar4Countdown` | `event-bytecode-label` | `complete` | 19 | `$20 EVENT_WRITE_VAR_TO_TEMPVAR` | `C0:A4B2`, `C0:A4A8` | `C3:A159`, `C3:A12E` |
| `C3:A15E` | `LoopC40015Var4GatedPulseUntilRelease` | `event-bytecode-label` | `complete` | 10 | `$42 EVENT_CALLROUTINE` | `C4:0023`, `C0:A4B2`, `C4:0015` | `C3:A16F`, `C3:A162`, `C3:A204` |
| `C3:A17B` | `LoopC40015SlowPulseUntilRelease` | `event-bytecode-label` | `complete` | 7 | `$06 EVENT_PAUSE` | `C0:A4B2`, `C4:0015` | `C3:A17B`, `C3:A204` |
| `C3:A18F` | `LoopC40015FastPulseUntilRelease` | `event-bytecode-label` | `complete` | 7 | `$06 EVENT_PAUSE` | `C0:A4B2`, `C4:0015` | `C3:A18F`, `C3:A204` |
| `C3:A1A3` | `` | `event-script-asset` | `complete` | 7 | `$06 EVENT_PAUSE` | `C0:A4B2`, `C4:0015` | `C3:A1A3`, `C3:A204` |
| `C3:A1B7` | `` | `event-script-asset` | `complete` | 7 | `$06 EVENT_PAUSE` | `C0:A4B2`, `C4:0015` | `C3:A1B7`, `C3:A204` |
| `C3:A1CB` | `` | `event-script-asset` | `complete` | 7 | `$06 EVENT_PAUSE` | `C0:A4B2`, `C4:0015` | `C3:A1CB`, `C3:A204` |
| `C3:A1DF` | `LoopActiveEntityWalkPulse2FrameC40015Branch` | `event-bytecode-label` | `complete` | 7 | `$06 EVENT_PAUSE` | `C0:A4B2`, `C4:0015` | `C3:A0FE`, `C3:A204` |
| `C3:A1F3` | `LoopC40015Pulse16FrameUntilRelease` | `event-bytecode-label` | `complete` | 8 | `$06 EVENT_PAUSE` | `C0:A4B2`, `C4:0015`, `C0:20F1` | `C3:A1F3` |
| `C3:A204` | `ReleaseCurrentVisualEntityAndEnd` | `event-bytecode-asset` | `complete` | 2 | `$42 EVENT_CALLROUTINE` | `C0:20F1` | - |
| `C3:A209` | `DelayThenReleaseCurrentVisualEntity` | `event-bytecode-asset` | `complete` | 2 | `$06 EVENT_PAUSE` | - | `C3:A204` |
| `C3:A20E` | `LoopVar0SelectedAnimationUntilOffscreen` | `event-bytecode-label` | `complete` | 7 | `$3B EVENT_SET_ANIMATION` | `C0:A4A8`, `C0:C6B6` | `C3:A22C`, `C3:A234`, `C3:A23D`, `C3:A24E`, +3 |
| `C3:A22C` | `Var0AnimationCase0Pulse8FrameOn` | `event-bytecode-asset` | `complete` | 7 | `$06 EVENT_PAUSE` | `C0:A4B2`, `C0:A4A8` | - |
| `C3:A234` | `Var0AnimationCase1Pulse8FrameOff` | `event-bytecode-asset` | `complete` | 4 | `$06 EVENT_PAUSE` | `C0:A4A8` | - |
| `C3:A23D` | `Var0AnimationCase2Pulse4Frame` | `event-bytecode-asset` | `complete` | 7 | `$06 EVENT_PAUSE` | `C0:A4B2`, `C0:A4A8` | - |
| `C3:A24E` | `Var0AnimationCase3Pulse32Frame` | `event-bytecode-asset` | `complete` | 7 | `$06 EVENT_PAUSE` | `C0:A4B2`, `C0:A4A8` | - |
| `C3:A25F` | `Var0AnimationCase4Wait16Frame` | `event-bytecode-asset` | `complete` | 2 | `$06 EVENT_PAUSE` | - | - |
| `C3:A262` | `LoopActiveEntityCollisionProbeRefresh` | `event-bytecode-label` | `complete` | 3 | `$42 EVENT_CALLROUTINE` | `C0:A6DA`, `C0:5E76` | `C3:A266` |
| `C3:A271` | `` | `event-script-asset` | `complete` | 1 | `$0C EVENT_END_TASK` | - | - |
| `C3:A272` | `` | `event-script-asset` | `complete` | 1 | `$0C EVENT_END_TASK` | - | - |
| `C3:A2AA` | `TrafficLightWaitUntilOffscreenAndRelease` | `event-bytecode-asset` | `complete` | 10 | `$25 EVENT_SET_PHYSICS_CALLBACK` | `C0:C7DB`, `C0:A4BF`, `C0:C6B6`, `C0:20F1` | `C3:A2B8` |
| `C3:A381` | `InitRandomWanderMovementWithCollisionProbe` | `event-bytecode-asset` | `complete` | 8 | `$25 EVENT_SET_PHYSICS_CALLBACK` | `C0:A4BF`, `C0:A685`, `C0:A964` | `C3:A111`, `C3:A262`, `C3:A3B7` |
| `C3:A3A1` | `InitC40015PulseWithCollisionProbe` | `event-bytecode-asset` | `complete` | 7 | `$25 EVENT_SET_PHYSICS_CALLBACK` | `C0:A4BF`, `C0:A685` | `C3:A15E`, `C3:A262` |
| `C3:A3B7` | `LoopRandomDirectionMovementWithRandomWait` | `event-bytecode-label` | `complete` | 5 | `$0E EVENT_SET_VAR` | `C4:7269` | `C3:A3C9`, `C3:A3D6` |
| `C3:A3C9` | `ChooseRandomCardinalDirection` | `event-bytecode-asset` | `complete` | 10 | `$42 EVENT_CALLROUTINE` | `C0:9F82`, `C0:A65F`, `C0:C83B`, `C0:CA4E` | `C3:A3B7` |
| `C3:A3D6` | `ApplyRandomDirectionAndMovementTimer` | `event-bytecode-asset` | `complete` | 9 | `$42 EVENT_CALLROUTINE` | `C0:A65F`, `C0:C83B`, `C0:9F82`, `C0:CA4E` | `C3:A3B7` |
| `C3:A3E7` | `SetMovementTimerThenRandomWait` | `event-bytecode-asset` | `complete` | 6 | `$42 EVENT_CALLROUTINE` | `C0:CA4E`, `C0:9F82` | `C3:A3B7` |
| `C3:A401` | `InitNpcAttentionPathIfNoCachedNeighbor` | `event-bytecode-asset` | `complete` | 12 | `$25 EVENT_SET_PHYSICS_CALLBACK` | `C0:A6DA`, `C0:A6B8`, `C0:A4BF` | `C3:A425`, `C3:A20E` |
| `C3:A426` | `StartNpcAttentionTerrainCollisionLoop` | `event-bytecode-label` | `complete` | 3 | `$1A EVENT_SHORTCALL` | - | `C3:A401`, `C3:A434` |
| `C3:A42D` | `StartNpcAttentionHorizontalCollisionLoop` | `event-bytecode-label` | `complete` | 3 | `$1A EVENT_SHORTCALL` | - | `C3:A401`, `C3:A448` |
| `C3:A434` | `LoopNpcAttentionTerrainCollision` | `event-bytecode-label` | `complete` | 6 | `$42 EVENT_CALLROUTINE` | `C0:6478`, `C0:5E82`, `C0:D5B0` | `C3:A45C`, `C3:A434` |
| `C3:A448` | `LoopNpcAttentionHorizontalCollision` | `event-bytecode-label` | `complete` | 6 | `$42 EVENT_CALLROUTINE` | `C0:6478`, `C0:5ECE`, `C0:D5B0` | `C3:A45C`, `C3:A448` |
| `C3:A45C` | `FinishNpcAttentionAndReleaseActor` | `event-bytecode-label` | `complete` | 16 | `$06 EVENT_PAUSE` | `C0:D59B`, `C0:20F1` | `C3:A45C` |
| `C3:A47C` | `ReleaseCurrentVisualEntityTail` | `event-bytecode-asset` | `complete` | 2 | `$42 EVENT_CALLROUTINE` | `C0:20F1` | - |
| `C3:AA1E` | `` | `event-script-asset` | `complete` | 4 | `$42 EVENT_CALLROUTINE` | `C0:A65F`, `C0:C83B`, `C0:A4BF` | - |
| `C3:AA2B` | `` | `event-script-asset` | `complete` | 6 | `$25 EVENT_SET_PHYSICS_CALLBACK` | - | `C3:A1F3`, `C3:A262` |
| `C3:AA38` | `InitActionScriptMovementState` | `event-bytecode-asset` | `complete` | 6 | `$25 EVENT_SET_PHYSICS_CALLBACK` | - | `C3:A111` |
| `C3:AA46` | `InitMovementPreset40_00Pulse24Frame` | `event-bytecode-asset` | `complete` | 7 | `$25 EVENT_SET_PHYSICS_CALLBACK` | `C0:A4BF`, `C0:A685` | `C3:A0B2` |
| `C3:AA5A` | `InitMovementPreset00_01Pulse12Frame` | `event-bytecode-asset` | `complete` | 7 | `$25 EVENT_SET_PHYSICS_CALLBACK` | `C0:A4BF`, `C0:A685` | `C3:A0C5` |
| `C3:AA6E` | `InitMovementPreset60_01Pulse9Frame` | `event-bytecode-asset` | `complete` | 7 | `$25 EVENT_SET_PHYSICS_CALLBACK` | `C0:A4BF`, `C0:A685` | `C3:A0D8` |
| `C3:AA82` | `InitMovementPreset00_02Pulse6Frame` | `event-bytecode-asset` | `complete` | 7 | `$25 EVENT_SET_PHYSICS_CALLBACK` | `C0:A4BF`, `C0:A685` | `C3:A0EB` |
| `C3:AA96` | `InitMovementPreset00_06Pulse2Frame` | `event-bytecode-asset` | `complete` | 7 | `$25 EVENT_SET_PHYSICS_CALLBACK` | `C0:A4BF`, `C0:A685` | `C3:A0FE` |
| `C3:AAAA` | `InitMovementPresetVar4Countdown` | `event-bytecode-asset` | `complete` | 6 | `$25 EVENT_SET_PHYSICS_CALLBACK` | - | `C3:A12E` |
| `C3:AAB8` | `` | `event-script-asset` | `complete` | 5 | `$25 EVENT_SET_PHYSICS_CALLBACK` | - | `C3:A1F3` |
| `C3:AAC2` | `` | `event-script-asset` | `complete` | 7 | `$25 EVENT_SET_PHYSICS_CALLBACK` | `C0:A4BF`, `C0:A685` | `C3:A18F` |
| `C3:AAD6` | `` | `event-script-asset` | `complete` | 7 | `$25 EVENT_SET_PHYSICS_CALLBACK` | `C0:A4BF`, `C0:A685` | `C3:A1A3` |
| `C3:AAEA` | `` | `event-script-asset` | `complete` | 7 | `$25 EVENT_SET_PHYSICS_CALLBACK` | `C0:A4BF`, `C0:A685` | `C3:A1B7` |
| `C3:AAFE` | `` | `event-script-asset` | `complete` | 7 | `$25 EVENT_SET_PHYSICS_CALLBACK` | `C0:A4BF`, `C0:A685` | `C3:A1CB` |
| `C3:AB12` | `InitMovementPreset00_06C40015Branch` | `event-bytecode-asset` | `complete` | 7 | `$25 EVENT_SET_PHYSICS_CALLBACK` | `C0:A4BF`, `C0:A685` | `C3:A1DF` |
| `C3:AB26` | `InitAlternatePhysicsVar4WalkPulse` | `event-bytecode-asset` | `complete` | 7 | `$23 EVENT_SET_POSITION_CHANGE_CALLBACK` | - | `C3:A111` |
| `C3:AB37` | `` | `event-script-asset` | `complete` | 5 | `$23 EVENT_SET_POSITION_CHANGE_CALLBACK` | - | - |
| `C3:AB44` | `RefreshActiveEntityDirectionAndVisualProfile` | `event-bytecode-asset` | `complete` | 6 | `$42 EVENT_CALLROUTINE` | `C4:6ADB`, `C4:7044`, `C4:6B0A`, `C0:A65F`, +1 | - |
| `C3:AB59` | `WaitForActiveEntityMovementToFinish` | `event-bytecode-label` | `complete` | 6 | `$1A EVENT_SHORTCALL` | `C0:A8DC` | `C3:AB44`, `C3:AB5C` |
| `C3:AB67` | `` | `event-script-asset` | `complete` | 11 | `$42 EVENT_CALLROUTINE` | `C4:6ADB`, `C4:7044`, `C4:6B0A`, `C4:6B37`, +3 | `C3:AB7F` |
| `C3:AB8A` | `WaitUntilPlayerLeavesActiveArea` | `event-bytecode-label` | `complete` | 4 | `$06 EVENT_PAUSE` | `C4:6E74` | `C3:AB8A` |
| `C3:AB94` | `` | `event-script-asset` | `complete` | 4 | `$06 EVENT_PAUSE` | `C4:6E74` | `C3:AB94` |
| `C3:AB9E` | `` | `event-script-asset` | `complete` | 4 | `$42 EVENT_CALLROUTINE` | `C4:7269` | `C3:ABAC`, `C3:ABB9` |
| `C3:ABE0` | `` | `event-script-asset` | `complete` | 5 | `$06 EVENT_PAUSE` | - | `C3:ABE0` |
| `C3:AFA3` | `LoopPartyLooksAtActiveEntity` | `event-bytecode-label` | `complete` | 3 | `$42 EVENT_CALLROUTINE` | `C4:8B3B` | `C3:AFA3` |
| `C3:B0B6` | `` | `event-script-asset` | `complete` | 19 | `$01 EVENT_LOOP` | `C0:A691`, `C0:A68B` | `C3:B0C7` |
| `C3:B431` | `` | `event-script-asset` | `complete` | 6 | `$06 EVENT_PAUSE` | `C0:C6B6`, `C0:A857`, `C0:20F1` | `C3:B431` |
| `C3:B70C` | `` | `event-script-asset` | `complete` | 27 | `$23 EVENT_SET_POSITION_CHANGE_CALLBACK` | `C0:A685`, `C4:6ADB`, `C4:7044`, `C4:6B0A`, +3 | `C3:B737` |
| `C3:BAA3` | `` | `event-script-asset` | `complete` | 9 | `$42 EVENT_CALLROUTINE` | `C0:A82F`, `C0:A88D`, `C0:A943`, `C0:A8C6` | `C3:BB5C`, `C3:BB73`, `C3:BAB5` |
| `C3:BAC4` | `` | `event-script-asset` | `complete` | 5 | `$42 EVENT_CALLROUTINE` | `C0:A82F`, `C0:A88D` | `C3:BB5C`, `C3:BB73` |
| `C3:BAD7` | `` | `event-script-asset` | `complete` | 5 | `$42 EVENT_CALLROUTINE` | `C0:A82F`, `C0:A88D` | `C3:BB5C`, `C3:BB73` |
| `C3:BB5C` | `` | `event-script-asset` | `complete` | 7 | `$1A EVENT_SHORTCALL` | `C0:A4BF`, `C4:6C45` | `C3:AAB8`, `C3:AB8A` |
| `C3:BB73` | `` | `event-script-asset` | `complete` | 9 | `$0E EVENT_SET_VAR` | `C0:A943`, `C0:A685`, `C0:A8C6` | `C3:AB44`, `C3:BB85` |
| `C3:BD03` | `` | `event-script-asset` | `complete` | 4 | `$1A EVENT_SHORTCALL` | `C0:A4BF` | `C3:AAB8`, `C3:AB8A` |
| `C3:BEA4` | `` | `event-script-asset` | `complete` | 13 | `$0E EVENT_SET_VAR` | `C0:A685`, `C0:AA6E`, `C4:6E46` | `C3:AA1E`, `C3:AB59` |
| `C3:BED4` | `` | `event-script-asset` | `complete` | 7 | `$0E EVENT_SET_VAR` | `C0:A685` | `C3:AB59` |
| `C3:C143` | `` | `event-script-asset` | `complete` | 11 | `$28 EVENT_SET_X` | `C0:A685`, `C0:A841` | `C3:AA38`, `C3:AA1E` |
| `C3:C1E0` | `` | `event-script-asset` | `complete` | 14 | `$1A EVENT_SHORTCALL` | `C0:A685`, `C0:A65F`, `C0:A4BF` | `C3:AA38`, `C3:C227`, `C3:AA1E`, `C3:AB59` |
| `C3:C20F` | `` | `event-script-asset` | `complete` | 6 | `$0E EVENT_SET_VAR` | `C0:A685`, `C0:A841` | `C3:AB59` |
| `C3:C227` | `` | `event-script-asset` | `complete` | 4 | `$42 EVENT_CALLROUTINE` | `C4:8B3B`, `C0:A94E` | `C3:C227` |
| `C3:C35D` | `` | `event-script-asset` | `complete` | 15 | `$1A EVENT_SHORTCALL` | `C0:A65F`, `C0:A4BF`, `C0:A84C`, `C0:A685` | `C3:AA38`, `C3:C36F`, `C3:AB59` |
| `C3:C810` | `` | `event-script-asset` | `complete` | 3 | `$14 EVENT_BINOP` | - | `C3:C810` |
| `C3:C81A` | `` | `event-script-asset` | `complete` | 3 | `$14 EVENT_BINOP` | - | `C3:C81A` |
| `C3:C824` | `` | `event-script-asset` | `complete` | 35 | `$06 EVENT_PAUSE` | - | `C3:C824` |
| `C3:C871` | `` | `event-script-asset` | `complete` | 26 | `$06 EVENT_PAUSE` | - | `C3:C871` |
| `C3:C8FD` | `` | `event-script-asset` | `complete` | 4 | `$1A EVENT_SHORTCALL` | `C0:A907`, `C4:6E46` | `C3:C94E`, `C3:A204` |
| `C3:C90C` | `` | `event-script-asset` | `complete` | 21 | `$42 EVENT_CALLROUTINE` | `C0:A864`, `C0:A4BF`, `C0:A685`, `C0:9FBB` | `C3:AB26`, `C3:AA1E`, `C3:ABE0` |
| `C3:C94E` | `` | `event-script-asset` | `complete` | 21 | `$42 EVENT_CALLROUTINE` | `C0:A864`, `C0:A4BF`, `C0:A685`, `C0:9FBB` | `C3:AB26`, `C3:AA1E`, `C3:ABE0` |
| `C3:CC24` | `` | `event-script-asset` | `complete` | 16 | `$0E EVENT_SET_VAR` | - | `C3:AB59` |
| `C3:CC5C` | `` | `event-script-asset` | `complete` | 16 | `$0E EVENT_SET_VAR` | - | `C3:AB59` |
| `C3:CC94` | `` | `event-script-asset` | `complete` | 10 | `$07 EVENT_START_TASK` | - | `C3:C824` |
| `C3:CCA8` | `` | `event-script-asset` | `complete` | 5 | `$2C EVENT_SET_Y_RELATIVE` | - | `C3:CCA8` |
| `C3:CEA2` | `` | `event-script-asset` | `complete` | 8 | `$06 EVENT_PAUSE` | `C0:A98B` | `C3:CEA2` |
| `C3:CEB9` | `` | `event-script-asset` | `complete` | 4 | `$42 EVENT_CALLROUTINE` | `C0:A86F` | `C3:CEB9` |
| `C3:D0A4` | `` | `event-script-asset` | `complete` | 9 | `$42 EVENT_CALLROUTINE` | `C0:AA6E` | - |
| `C3:D913` | `` | `event-script-asset` | `complete` | 2 | `$42 EVENT_CALLROUTINE` | `C0:A88D` | - |
| `C3:DB7A` | `` | `event-script-asset` | `complete` | 9 | `$1A EVENT_SHORTCALL` | `C0:A685`, `C0:A907`, `C0:A88D` | `C3:DBE0`, `C3:AB59` |
| `C3:DBDB` | `` | `event-script-asset` | `complete` | 7 | `$42 EVENT_CALLROUTINE` | `C0:A864`, `C0:A679` | - |
| `C3:DF90` | `` | `event-script-asset` | `complete` | 11 | `$07 EVENT_START_TASK` | `C0:A651`, `C0:A4BF`, `C0:C6B6`, `C0:20F1`, +2 | `C3:DFB5`, `C3:DF9F` |
| `C3:DFB5` | `` | `event-script-asset` | `complete` | 5 | `$42 EVENT_CALLROUTINE` | `C0:9F82` | `C3:DFD4`, `C3:DFE4` |
| `C3:DFD4` | `` | `event-script-asset` | `complete` | 4 | `$40 EVENT_SET_Y_VELOCITY` | `C0:9F82` | `C3:DFB5` |

## Decode excerpts

### C3:0295 MoveActiveEntityLeftToScriptVarsAndWait

- class: `event-bytecode-asset`
- decode status: `complete`
- stop reason: terminal/control-flow stop
- raw preview: `1A 38 AA 42 6E AA C0 06 00 42 85 A6 C0 00 01 0E`

```text
C3:0295  1A 38 AA             EVENT_SHORTCALL $C3:AA38 <InitActionScriptMovementState>
C3:0298  42 6E AA C0 06 00    EVENT_CALLROUTINE $C0:AA6E <Script_ApplyCurrentSlotVisualCountdownState>, $06, $00
C3:029E  42 85 A6 C0 00 01    EVENT_CALLROUTINE $C0:A685 <Script_SetCurrentSlotField2B32>, $00, $01
C3:02A4  0E 05 01 00          EVENT_SET_VAR $05, $0001
C3:02A8  1A 59 AB             EVENT_SHORTCALL $C3:AB59 <WaitForActiveEntityMovementToFinish>
C3:02AB  1B                   EVENT_SHORT_RETURN
```

### C3:43DB LoopTimedDeliveryDeparturePulseUntilOffscreen

- class: `event-bytecode-label`
- decode status: `complete`
- stop reason: terminal/control-flow stop
- raw preview: `06 08 20 04 0B E8 43 3B 01 42 B2 A4 C0 06 08 3B`

```text
C3:43DB  06 08                EVENT_PAUSE $08
C3:43DD  20 04                EVENT_WRITE_VAR_TO_TEMPVAR $04
C3:43DF  0B E8 43             EVENT_SHORTCALL_CONDITIONAL_NOT $C3:43E8 <TimedDeliveryDeparturePulseAnimation0Half>
C3:43E2  3B 01                EVENT_SET_ANIMATION $01
C3:43E4  42 B2 A4 C0          EVENT_CALLROUTINE $C0:A4B2 <RefreshCurrentSlotVisualProfile_Mode1IfAligned>
C3:43E8  06 08                EVENT_PAUSE $08
C3:43EA  3B 00                EVENT_SET_ANIMATION $00
C3:43EC  42 A8 A4 C0          EVENT_CALLROUTINE $C0:A4A8 <RefreshCurrentSlotVisualProfile_Mode0IfAligned>
C3:43F0  42 B6 C6 C0          EVENT_CALLROUTINE $C0:C6B6 <CheckCurrentSlotInsideLiveAreaWindow>
C3:43F4  0B DB 43             EVENT_SHORTCALL_CONDITIONAL_NOT $C3:43DB <LoopTimedDeliveryDeparturePulseUntilOffscreen>
C3:43F7  42 F6 0F EF          EVENT_CALLROUTINE $EF:0FF6 <UNKNOWN_EF0FF6>
C3:43FB  42 46 6E C4          EVENT_CALLROUTINE $C4:6E46 <SetYieldToTextLatch9641>
C3:43FF  19 04 A2             EVENT_SHORTJUMP $C3:A204 <ReleaseCurrentVisualEntityAndEnd>
```

### C3:43E8 TimedDeliveryDeparturePulseAnimation0Half

- class: `event-bytecode-asset`
- decode status: `complete`
- stop reason: terminal/control-flow stop
- raw preview: `06 08 3B 00 42 A8 A4 C0 42 B6 C6 C0 0B DB 43 42`

```text
C3:43E8  06 08                EVENT_PAUSE $08
C3:43EA  3B 00                EVENT_SET_ANIMATION $00
C3:43EC  42 A8 A4 C0          EVENT_CALLROUTINE $C0:A4A8 <RefreshCurrentSlotVisualProfile_Mode0IfAligned>
C3:43F0  42 B6 C6 C0          EVENT_CALLROUTINE $C0:C6B6 <CheckCurrentSlotInsideLiveAreaWindow>
C3:43F4  0B DB 43             EVENT_SHORTCALL_CONDITIONAL_NOT $C3:43DB <LoopTimedDeliveryDeparturePulseUntilOffscreen>
C3:43F7  42 F6 0F EF          EVENT_CALLROUTINE $EF:0FF6 <UNKNOWN_EF0FF6>
C3:43FB  42 46 6E C4          EVENT_CALLROUTINE $C4:6E46 <SetYieldToTextLatch9641>
C3:43FF  19 04 A2             EVENT_SHORTJUMP $C3:A204 <ReleaseCurrentVisualEntityAndEnd>
```

### C3:443E TimedDeliveryRetryWaitLoop

- class: `event-bytecode-asset`
- decode status: `complete`
- stop reason: terminal/control-flow stop
- raw preview: `42 A7 0C EF 0A 7D 44 42 23 0D EF 24 06 3C 02 42`

```text
C3:443E  42 A7 0C EF          EVENT_CALLROUTINE $EF:0CA7 <UNKNOWN_EF0CA7>
C3:4442  0A 7D 44             EVENT_SHORTCALL_CONDITIONAL $C3:447D <TimedDeliveryFailureTeardown>
C3:4445  42 23 0D EF          EVENT_CALLROUTINE $EF:0D23 <UNKNOWN_EF0D23>
C3:4449  24                   EVENT_LOOP_TEMPVAR
C3:444A  06 3C                EVENT_PAUSE $3C
C3:444C  02                   EVENT_LOOP_END
C3:444D  42 60 0F EF          EVENT_CALLROUTINE $EF:0F60 <UNKNOWN_EF0F60>
C3:4451  0A 57 44             EVENT_SHORTCALL_CONDITIONAL $C3:4457 <TimedDeliverySuccessGateAndPresentationSetup>
C3:4454  19 3E 44             EVENT_SHORTJUMP $C3:443E <TimedDeliveryRetryWaitLoop>
```

### C3:444D TimedDeliveryReadinessGate

- class: `event-bytecode-asset`
- decode status: `complete`
- stop reason: terminal/control-flow stop
- raw preview: `42 60 0F EF 0A 57 44 19 3E 44 42 9A FF C2 0B 7D`

```text
C3:444D  42 60 0F EF          EVENT_CALLROUTINE $EF:0F60 <UNKNOWN_EF0F60>
C3:4451  0A 57 44             EVENT_SHORTCALL_CONDITIONAL $C3:4457 <TimedDeliverySuccessGateAndPresentationSetup>
C3:4454  19 3E 44             EVENT_SHORTJUMP $C3:443E <TimedDeliveryRetryWaitLoop>
```

### C3:4457 TimedDeliverySuccessGateAndPresentationSetup

- class: `event-bytecode-asset`
- decode status: `complete`
- stop reason: terminal/control-flow stop
- raw preview: `42 9A FF C2 0B 7D 44 20 00 42 9B C1 C0 0B 3E 44`

```text
C3:4457  42 9A FF C2          EVENT_CALLROUTINE $C2:FF9A <CheckOverworldPositionHashThreshold3Of8>
C3:445B  0B 7D 44             EVENT_SHORTCALL_CONDITIONAL_NOT $C3:447D <TimedDeliveryFailureTeardown>
C3:445E  20 00                EVENT_WRITE_VAR_TO_TEMPVAR $00
C3:4460  42 9B C1 C0          EVENT_CALLROUTINE $C0:C19B <CopyPathToLane_FromPartyMemberRequest>
C3:4464  0B 3E 44             EVENT_SHORTCALL_CONDITIONAL_NOT $C3:443E <TimedDeliveryRetryWaitLoop>
C3:4467  07 7A 44             EVENT_START_TASK $C3:447A <StartTimedDeliveryArrivalMovementTask>
C3:446A  06 01                EVENT_PAUSE $01
C3:446C  42 DB 0F EF          EVENT_CALLROUTINE $EF:0FDB <UNKNOWN_EF0FDB>
C3:4470  1A 88 44             EVENT_SHORTCALL $C3:4488 <PrepareTimedDeliveryActorForPresentation>
C3:4473  42 8D 0D EF          EVENT_CALLROUTINE $EF:0D8D <UNKNOWN_EF0D8D>
C3:4477  19 A8 44             EVENT_SHORTJUMP $C3:44A8 <RunTimedDeliveryDepartureMovement>
```

### C3:447A StartTimedDeliveryArrivalMovementTask

- class: `event-bytecode-label`
- decode status: `complete`
- stop reason: terminal/control-flow stop
- raw preview: `1A DE 44 42 F6 0F EF 42 FA 0D EF 19 04 A2 3B 00`

```text
C3:447A  1A DE 44             EVENT_SHORTCALL $C3:44DE <RunTimedDeliveryArrivalMovement>
C3:447D  42 F6 0F EF          EVENT_CALLROUTINE $EF:0FF6 <UNKNOWN_EF0FF6>
C3:4481  42 FA 0D EF          EVENT_CALLROUTINE $EF:0DFA <UNKNOWN_EF0DFA>
C3:4485  19 04 A2             EVENT_SHORTJUMP $C3:A204 <ReleaseCurrentVisualEntityAndEnd>
```

### C3:447D TimedDeliveryFailureTeardown

- class: `event-bytecode-asset`
- decode status: `complete`
- stop reason: terminal/control-flow stop
- raw preview: `42 F6 0F EF 42 FA 0D EF 19 04 A2 3B 00 07 9F A0`

```text
C3:447D  42 F6 0F EF          EVENT_CALLROUTINE $EF:0FF6 <UNKNOWN_EF0FF6>
C3:4481  42 FA 0D EF          EVENT_CALLROUTINE $EF:0DFA <UNKNOWN_EF0DFA>
C3:4485  19 04 A2             EVENT_SHORTJUMP $C3:A204 <ReleaseCurrentVisualEntityAndEnd>
```

### C3:4488 PrepareTimedDeliveryActorForPresentation

- class: `event-bytecode-asset`
- decode status: `complete`
- stop reason: terminal/control-flow stop
- raw preview: `3B 00 07 9F A0 42 BF A4 C0 0E 02 16 00 0E 03 16`

```text
C3:4488  3B 00                EVENT_SET_ANIMATION $00
C3:448A  07 9F A0             EVENT_START_TASK $C3:A09F <LoopActiveEntityWalkAnimationPulse>
C3:448D  42 BF A4 C0          EVENT_CALLROUTINE $C0:A4BF <RefreshCurrentSlotVisualProfile_Mode0>
C3:4491  0E 02 16 00          EVENT_SET_VAR $02, $0016
C3:4495  0E 03 16 00          EVENT_SET_VAR $03, $0016
C3:4499  06 01                EVENT_PAUSE $01
C3:449B  20 04                EVENT_WRITE_VAR_TO_TEMPVAR $04
C3:449D  0B A7 44             EVENT_SHORTCALL_CONDITIONAL_NOT $C3:44A7 <ReturnFromTimedDeliveryActorPrep>
C3:44A0  42 F8 6E C4          EVENT_CALLROUTINE $C4:6EF8 <CheckCurrentSlotWithinPlayerProximityThreshold>
C3:44A4  0A 99 44             EVENT_SHORTCALL_CONDITIONAL $C3:4499 <WaitTimedDeliveryActorPresentationPrep>
C3:44A7  1B                   EVENT_SHORT_RETURN
```

### C3:4499 WaitTimedDeliveryActorPresentationPrep

- class: `event-bytecode-label`
- decode status: `complete`
- stop reason: terminal/control-flow stop
- raw preview: `06 01 20 04 0B A7 44 42 F8 6E C4 0A 99 44 1B 39`

```text
C3:4499  06 01                EVENT_PAUSE $01
C3:449B  20 04                EVENT_WRITE_VAR_TO_TEMPVAR $04
C3:449D  0B A7 44             EVENT_SHORTCALL_CONDITIONAL_NOT $C3:44A7 <ReturnFromTimedDeliveryActorPrep>
C3:44A0  42 F8 6E C4          EVENT_CALLROUTINE $C4:6EF8 <CheckCurrentSlotWithinPlayerProximityThreshold>
C3:44A4  0A 99 44             EVENT_SHORTCALL_CONDITIONAL $C3:4499 <WaitTimedDeliveryActorPresentationPrep>
C3:44A7  1B                   EVENT_SHORT_RETURN
```

### C3:44A7 ReturnFromTimedDeliveryActorPrep

- class: `event-bytecode-label`
- decode status: `complete`
- stop reason: terminal/control-flow stop
- raw preview: `1B 39 06 01 13 13 07 DB 43 20 00 42 51 C2 C0 0B`

```text
C3:44A7  1B                   EVENT_SHORT_RETURN
```

### C3:44A8 RunTimedDeliveryDepartureMovement

- class: `event-bytecode-asset`
- decode status: `complete`
- stop reason: terminal/control-flow stop
- raw preview: `39 06 01 13 13 07 DB 43 20 00 42 51 C2 C0 0B D2`

```text
C3:44A8  39                   EVENT_SET_VELOCITIES_ZERO
C3:44A9  06 01                EVENT_PAUSE $01
C3:44AB  13                   EVENT_END_LAST_TASK
C3:44AC  13                   EVENT_END_LAST_TASK
C3:44AD  07 DB 43             EVENT_START_TASK $C3:43DB <LoopTimedDeliveryDeparturePulseUntilOffscreen>
C3:44B0  20 00                EVENT_WRITE_VAR_TO_TEMPVAR $00
C3:44B2  42 51 C2 C0          EVENT_CALLROUTINE $C0:C251 <CopyPathToLane_FromCurrentEntityRequestReverse>
C3:44B6  0B D2 44             EVENT_SHORTCALL_CONDITIONAL_NOT $C3:44D2 <FinishTimedDeliveryDepartureAndYieldText>
C3:44B9  42 8A 0E EF          EVENT_CALLROUTINE $EF:0E8A <UNKNOWN_EF0E8A>
C3:44BD  42 8B A6 C0          EVENT_CALLROUTINE $C0:A68B <StoreAInCurrentSlotField2B32>
C3:44C1  42 8F D9 C0          EVENT_CALLROUTINE $C0:D98F <Export_CurrentSlotAttentionTarget>
C3:44C5  0A D2 44             EVENT_SHORTCALL_CONDITIONAL $C3:44D2 <FinishTimedDeliveryDepartureAndYieldText>
C3:44C8  1A 59 AB             EVENT_SHORTCALL $C3:AB59 <WaitForActiveEntityMovementToFinish>
C3:44CB  42 87 6C C4          EVENT_CALLROUTINE $C4:6C87 <RestoreCurrentSlotAnchorFromCachedTarget>
C3:44CF  19 C1 44             EVENT_SHORTJUMP $C3:44C1 <LoopTimedDeliveryDepartureMovement>
```

### C3:44C1 LoopTimedDeliveryDepartureMovement

- class: `event-bytecode-label`
- decode status: `complete`
- stop reason: terminal/control-flow stop
- raw preview: `42 8F D9 C0 0A D2 44 1A 59 AB 42 87 6C C4 19 C1`

```text
C3:44C1  42 8F D9 C0          EVENT_CALLROUTINE $C0:D98F <Export_CurrentSlotAttentionTarget>
C3:44C5  0A D2 44             EVENT_SHORTCALL_CONDITIONAL $C3:44D2 <FinishTimedDeliveryDepartureAndYieldText>
C3:44C8  1A 59 AB             EVENT_SHORTCALL $C3:AB59 <WaitForActiveEntityMovementToFinish>
C3:44CB  42 87 6C C4          EVENT_CALLROUTINE $C4:6C87 <RestoreCurrentSlotAnchorFromCachedTarget>
C3:44CF  19 C1 44             EVENT_SHORTJUMP $C3:44C1 <LoopTimedDeliveryDepartureMovement>
```

### C3:44D2 FinishTimedDeliveryDepartureAndYieldText

- class: `event-bytecode-label`
- decode status: `complete`
- stop reason: terminal/control-flow stop
- raw preview: `39 42 F6 0F EF 42 46 6E C4 19 04 A2 42 67 0E EF`

```text
C3:44D2  39                   EVENT_SET_VELOCITIES_ZERO
C3:44D3  42 F6 0F EF          EVENT_CALLROUTINE $EF:0FF6 <UNKNOWN_EF0FF6>
C3:44D7  42 46 6E C4          EVENT_CALLROUTINE $C4:6E46 <SetYieldToTextLatch9641>
C3:44DB  19 04 A2             EVENT_SHORTJUMP $C3:A204 <ReleaseCurrentVisualEntityAndEnd>
```

### C3:44DE RunTimedDeliveryArrivalMovement

- class: `event-bytecode-asset`
- decode status: `complete`
- stop reason: terminal/control-flow stop
- raw preview: `42 67 0E EF 42 8B A6 C0 0E 05 03 00 0E 04 00 00`

```text
C3:44DE  42 67 0E EF          EVENT_CALLROUTINE $EF:0E67 <UNKNOWN_EF0E67>
C3:44E2  42 8B A6 C0          EVENT_CALLROUTINE $C0:A68B <StoreAInCurrentSlotField2B32>
C3:44E6  0E 05 03 00          EVENT_SET_VAR $05, $0003
C3:44EA  0E 04 00 00          EVENT_SET_VAR $04, $0000
C3:44EE  42 8F D9 C0          EVENT_CALLROUTINE $C0:D98F <Export_CurrentSlotAttentionTarget>
C3:44F2  0A FF 44             EVENT_SHORTCALL_CONDITIONAL $C3:44FF <HoldTimedDeliveryArrivalCompletion>
C3:44F5  1A 59 AB             EVENT_SHORTCALL $C3:AB59 <WaitForActiveEntityMovementToFinish>
C3:44F8  42 87 6C C4          EVENT_CALLROUTINE $C4:6C87 <RestoreCurrentSlotAnchorFromCachedTarget>
C3:44FC  19 EE 44             EVENT_SHORTJUMP $C3:44EE <LoopTimedDeliveryArrivalMovement>
```

### C3:44EE LoopTimedDeliveryArrivalMovement

- class: `event-bytecode-label`
- decode status: `complete`
- stop reason: terminal/control-flow stop
- raw preview: `42 8F D9 C0 0A FF 44 1A 59 AB 42 87 6C C4 19 EE`

```text
C3:44EE  42 8F D9 C0          EVENT_CALLROUTINE $C0:D98F <Export_CurrentSlotAttentionTarget>
C3:44F2  0A FF 44             EVENT_SHORTCALL_CONDITIONAL $C3:44FF <HoldTimedDeliveryArrivalCompletion>
C3:44F5  1A 59 AB             EVENT_SHORTCALL $C3:AB59 <WaitForActiveEntityMovementToFinish>
C3:44F8  42 87 6C C4          EVENT_CALLROUTINE $C4:6C87 <RestoreCurrentSlotAnchorFromCachedTarget>
C3:44FC  19 EE 44             EVENT_SHORTJUMP $C3:44EE <LoopTimedDeliveryArrivalMovement>
```

### C3:44FF HoldTimedDeliveryArrivalCompletion

- class: `event-bytecode-label`
- decode status: `complete`
- stop reason: terminal/control-flow stop
- raw preview: `0E 04 01 00 06 F0 19 FF 44 42 64 A8 C0 FF 25 C8`

```text
C3:44FF  0E 04 01 00          EVENT_SET_VAR $04, $0001
C3:4503  06 F0                EVENT_PAUSE $F0
C3:4505  19 FF 44             EVENT_SHORTJUMP $C3:44FF <HoldTimedDeliveryArrivalCompletion>
```

### C3:A043 IntroCutsceneCameraPanGate

- class: `event-bytecode-asset`
- decode status: `complete`
- stop reason: terminal/control-flow stop
- raw preview: `42 D3 FF C1 0A 4E A0 42 00 01 C3 08 00 52 C0 01`

```text
C3:A043  42 D3 FF C1          EVENT_CALLROUTINE $C1:FFD3 <label_C1FFD3>
C3:A047  0A 4E A0             EVENT_SHORTCALL_CONDITIONAL $C3:A04E <StartIntroCameraPanTickLoop>
C3:A04A  42 00 01 C3          EVENT_CALLROUTINE $C3:0100 <DisplayAntiPiracyScreen>
C3:A04E  08 00 52 C0          EVENT_SET_TICK_CALLBACK $C0:5200 <Tick_OverworldPlayerPositionAndCallbacks>
C3:A052  01 06                EVENT_LOOP $06
C3:A054  06 C8                EVENT_PAUSE $C8
C3:A056  02                   EVENT_LOOP_END
C3:A057  42 00 00 C2          EVENT_CALLROUTINE $C2:0000 <label_C20000>
C3:A05B  19 52 A0             EVENT_SHORTJUMP $C3:A052 <LoopIntroCameraPanWaitAndC2Step>
```

### C3:A04E StartIntroCameraPanTickLoop

- class: `event-bytecode-label`
- decode status: `complete`
- stop reason: terminal/control-flow stop
- raw preview: `08 00 52 C0 01 06 06 C8 02 42 00 00 C2 19 52 A0`

```text
C3:A04E  08 00 52 C0          EVENT_SET_TICK_CALLBACK $C0:5200 <Tick_OverworldPlayerPositionAndCallbacks>
C3:A052  01 06                EVENT_LOOP $06
C3:A054  06 C8                EVENT_PAUSE $C8
C3:A056  02                   EVENT_LOOP_END
C3:A057  42 00 00 C2          EVENT_CALLROUTINE $C2:0000 <label_C20000>
C3:A05B  19 52 A0             EVENT_SHORTJUMP $C3:A052 <LoopIntroCameraPanWaitAndC2Step>
```

### C3:A052 LoopIntroCameraPanWaitAndC2Step

- class: `event-bytecode-label`
- decode status: `complete`
- stop reason: terminal/control-flow stop
- raw preview: `01 06 06 C8 02 42 00 00 C2 19 52 A0 23 39 A0 25`

```text
C3:A052  01 06                EVENT_LOOP $06
C3:A054  06 C8                EVENT_PAUSE $C8
C3:A056  02                   EVENT_LOOP_END
C3:A057  42 00 00 C2          EVENT_CALLROUTINE $C2:0000 <label_C20000>
C3:A05B  19 52 A0             EVENT_SHORTJUMP $C3:A052 <LoopIntroCameraPanWaitAndC2Step>
```

### C3:A05E IntroCutsceneSpriteObjectSetup

- class: `event-bytecode-asset`
- decode status: `complete`
- stop reason: terminal/control-flow stop
- raw preview: `23 39 A0 25 6B A2 3B 00 42 AA 3D C0 42 F0 4E C0`

```text
C3:A05E  23 39 A0             EVENT_SET_POSITION_CHANGE_CALLBACK $C0:A039 <UNKNOWN_C0A039>
C3:A061  25 6B A2             EVENT_SET_PHYSICS_CALLBACK $C0:A26B <PhysicsCallback_TargetComparisonAndProjection>
C3:A064  3B 00                EVENT_SET_ANIMATION $00
C3:A066  42 AA 3D C0          EVENT_CALLROUTINE $C0:3DAA <Sync_CurrentSlotToPartyCharacterRecord>
C3:A06A  42 F0 4E C0          EVENT_CALLROUTINE $C0:4EF0 <Restore_CurrentSlotFromSnapshotRecord>
C3:A06E  42 DA A6 C0          EVENT_CALLROUTINE $C0:A6DA <label_C0A6DA>
C3:A072  08 78 4D C0          EVENT_SET_TICK_CALLBACK $C0:4D78 <Tick_Event2SnapshotObjectReconcile>
C3:A076  42 E3 A6 C0          EVENT_CALLROUTINE $C0:A6E3 <WatchAndRefreshCompanionVisualPhase>
C3:A07A  06 01                EVENT_PAUSE $01
C3:A07C  19 76 A0             EVENT_SHORTJUMP $C3:A076 <LoopIntroCompanionVisualRefresh>
```

### C3:A076 LoopIntroCompanionVisualRefresh

- class: `event-bytecode-label`
- decode status: `complete`
- stop reason: terminal/control-flow stop
- raw preview: `42 E3 A6 C0 06 01 19 76 A0 09 23 39 A0 25 6B A2`

```text
C3:A076  42 E3 A6 C0          EVENT_CALLROUTINE $C0:A6E3 <WatchAndRefreshCompanionVisualPhase>
C3:A07A  06 01                EVENT_PAUSE $01
C3:A07C  19 76 A0             EVENT_SHORTJUMP $C3:A076 <LoopIntroCompanionVisualRefresh>
```

### C3:A07F HaltEventScript

- class: `event-bytecode-asset`
- decode status: `complete`
- stop reason: terminal/control-flow stop
- raw preview: `09 23 39 A0 25 6B A2 3B 00 42 7D 02 EF 08 1E 03`

```text
C3:A07F  09                   EVENT_HALT
```

### C3:A09F LoopActiveEntityWalkAnimationPulse

- class: `event-bytecode-label`
- decode status: `complete`
- stop reason: terminal/control-flow stop
- raw preview: `06 08 3B 01 42 B2 A4 C0 06 08 3B 00 42 A8 A4 C0`

```text
C3:A09F  06 08                EVENT_PAUSE $08
C3:A0A1  3B 01                EVENT_SET_ANIMATION $01
C3:A0A3  42 B2 A4 C0          EVENT_CALLROUTINE $C0:A4B2 <RefreshCurrentSlotVisualProfile_Mode1IfAligned>
C3:A0A7  06 08                EVENT_PAUSE $08
C3:A0A9  3B 00                EVENT_SET_ANIMATION $00
C3:A0AB  42 A8 A4 C0          EVENT_CALLROUTINE $C0:A4A8 <RefreshCurrentSlotVisualProfile_Mode0IfAligned>
C3:A0AF  19 9F A0             EVENT_SHORTJUMP $C3:A09F <LoopActiveEntityWalkAnimationPulse>
```

### C3:A0B2 LoopActiveEntityWalkPulse24Frame

- class: `event-bytecode-label`
- decode status: `complete`
- stop reason: terminal/control-flow stop
- raw preview: `06 18 3B 01 42 B2 A4 C0 06 18 3B 00 42 A8 A4 C0`

```text
C3:A0B2  06 18                EVENT_PAUSE $18
C3:A0B4  3B 01                EVENT_SET_ANIMATION $01
C3:A0B6  42 B2 A4 C0          EVENT_CALLROUTINE $C0:A4B2 <RefreshCurrentSlotVisualProfile_Mode1IfAligned>
C3:A0BA  06 18                EVENT_PAUSE $18
C3:A0BC  3B 00                EVENT_SET_ANIMATION $00
C3:A0BE  42 A8 A4 C0          EVENT_CALLROUTINE $C0:A4A8 <RefreshCurrentSlotVisualProfile_Mode0IfAligned>
C3:A0C2  19 B2 A0             EVENT_SHORTJUMP $C3:A0B2 <LoopActiveEntityWalkPulse24Frame>
```

### C3:A0C5 LoopActiveEntityWalkPulse12Frame

- class: `event-bytecode-label`
- decode status: `complete`
- stop reason: terminal/control-flow stop
- raw preview: `06 0C 3B 01 42 B2 A4 C0 06 0C 3B 00 42 A8 A4 C0`

```text
C3:A0C5  06 0C                EVENT_PAUSE $0C
C3:A0C7  3B 01                EVENT_SET_ANIMATION $01
C3:A0C9  42 B2 A4 C0          EVENT_CALLROUTINE $C0:A4B2 <RefreshCurrentSlotVisualProfile_Mode1IfAligned>
C3:A0CD  06 0C                EVENT_PAUSE $0C
C3:A0CF  3B 00                EVENT_SET_ANIMATION $00
C3:A0D1  42 A8 A4 C0          EVENT_CALLROUTINE $C0:A4A8 <RefreshCurrentSlotVisualProfile_Mode0IfAligned>
C3:A0D5  19 C5 A0             EVENT_SHORTJUMP $C3:A0C5 <LoopActiveEntityWalkPulse12Frame>
```

### C3:A0D8 LoopActiveEntityWalkPulse9FrameConditional

- class: `event-bytecode-label`
- decode status: `complete`
- stop reason: terminal/control-flow stop
- raw preview: `06 09 3B 01 42 B2 A4 C0 06 09 3B 00 42 A8 A4 C0`

```text
C3:A0D8  06 09                EVENT_PAUSE $09
C3:A0DA  3B 01                EVENT_SET_ANIMATION $01
C3:A0DC  42 B2 A4 C0          EVENT_CALLROUTINE $C0:A4B2 <RefreshCurrentSlotVisualProfile_Mode1IfAligned>
C3:A0E0  06 09                EVENT_PAUSE $09
C3:A0E2  3B 00                EVENT_SET_ANIMATION $00
C3:A0E4  42 A8 A4 C0          EVENT_CALLROUTINE $C0:A4A8 <RefreshCurrentSlotVisualProfile_Mode0IfAligned>
C3:A0E8  0B D8 A0             EVENT_SHORTCALL_CONDITIONAL_NOT $C3:A0D8 <LoopActiveEntityWalkPulse9FrameConditional>
C3:A0EB  06 06                EVENT_PAUSE $06
C3:A0ED  3B 01                EVENT_SET_ANIMATION $01
C3:A0EF  42 B2 A4 C0          EVENT_CALLROUTINE $C0:A4B2 <RefreshCurrentSlotVisualProfile_Mode1IfAligned>
C3:A0F3  06 06                EVENT_PAUSE $06
C3:A0F5  3B 00                EVENT_SET_ANIMATION $00
C3:A0F7  42 A8 A4 C0          EVENT_CALLROUTINE $C0:A4A8 <RefreshCurrentSlotVisualProfile_Mode0IfAligned>
C3:A0FB  0B EB A0             EVENT_SHORTCALL_CONDITIONAL_NOT $C3:A0EB <LoopActiveEntityWalkPulse6FrameConditional>
C3:A0FE  06 02                EVENT_PAUSE $02
C3:A100  3B 01                EVENT_SET_ANIMATION $01
; ... 16 more decoded lines in JSON output
```

### C3:A0EB LoopActiveEntityWalkPulse6FrameConditional

- class: `event-bytecode-label`
- decode status: `complete`
- stop reason: terminal/control-flow stop
- raw preview: `06 06 3B 01 42 B2 A4 C0 06 06 3B 00 42 A8 A4 C0`

```text
C3:A0EB  06 06                EVENT_PAUSE $06
C3:A0ED  3B 01                EVENT_SET_ANIMATION $01
C3:A0EF  42 B2 A4 C0          EVENT_CALLROUTINE $C0:A4B2 <RefreshCurrentSlotVisualProfile_Mode1IfAligned>
C3:A0F3  06 06                EVENT_PAUSE $06
C3:A0F5  3B 00                EVENT_SET_ANIMATION $00
C3:A0F7  42 A8 A4 C0          EVENT_CALLROUTINE $C0:A4A8 <RefreshCurrentSlotVisualProfile_Mode0IfAligned>
C3:A0FB  0B EB A0             EVENT_SHORTCALL_CONDITIONAL_NOT $C3:A0EB <LoopActiveEntityWalkPulse6FrameConditional>
C3:A0FE  06 02                EVENT_PAUSE $02
C3:A100  3B 01                EVENT_SET_ANIMATION $01
C3:A102  42 B2 A4 C0          EVENT_CALLROUTINE $C0:A4B2 <RefreshCurrentSlotVisualProfile_Mode1IfAligned>
C3:A106  06 02                EVENT_PAUSE $02
C3:A108  3B 00                EVENT_SET_ANIMATION $00
C3:A10A  42 A8 A4 C0          EVENT_CALLROUTINE $C0:A4A8 <RefreshCurrentSlotVisualProfile_Mode0IfAligned>
C3:A10E  0B FE A0             EVENT_SHORTCALL_CONDITIONAL_NOT $C3:A0FE <LoopActiveEntityWalkPulse2FrameConditional>
C3:A111  06 08                EVENT_PAUSE $08
C3:A113  20 04                EVENT_WRITE_VAR_TO_TEMPVAR $04
; ... 9 more decoded lines in JSON output
```

### C3:A0FE LoopActiveEntityWalkPulse2FrameConditional

- class: `event-bytecode-label`
- decode status: `complete`
- stop reason: terminal/control-flow stop
- raw preview: `06 02 3B 01 42 B2 A4 C0 06 02 3B 00 42 A8 A4 C0`

```text
C3:A0FE  06 02                EVENT_PAUSE $02
C3:A100  3B 01                EVENT_SET_ANIMATION $01
C3:A102  42 B2 A4 C0          EVENT_CALLROUTINE $C0:A4B2 <RefreshCurrentSlotVisualProfile_Mode1IfAligned>
C3:A106  06 02                EVENT_PAUSE $02
C3:A108  3B 00                EVENT_SET_ANIMATION $00
C3:A10A  42 A8 A4 C0          EVENT_CALLROUTINE $C0:A4A8 <RefreshCurrentSlotVisualProfile_Mode0IfAligned>
C3:A10E  0B FE A0             EVENT_SHORTCALL_CONDITIONAL_NOT $C3:A0FE <LoopActiveEntityWalkPulse2FrameConditional>
C3:A111  06 08                EVENT_PAUSE $08
C3:A113  20 04                EVENT_WRITE_VAR_TO_TEMPVAR $04
C3:A115  0B 1E A1             EVENT_SHORTCALL_CONDITIONAL_NOT $C3:A11E <DATA_C3A11E>
C3:A118  3B 01                EVENT_SET_ANIMATION $01
C3:A11A  42 B2 A4 C0          EVENT_CALLROUTINE $C0:A4B2 <RefreshCurrentSlotVisualProfile_Mode1IfAligned>
C3:A11E  06 08                EVENT_PAUSE $08
C3:A120  20 04                EVENT_WRITE_VAR_TO_TEMPVAR $04
C3:A122  0B 11 A1             EVENT_SHORTCALL_CONDITIONAL_NOT $C3:A111 <LoopActiveEntityWalkPulseVar4Gate>
C3:A125  3B 00                EVENT_SET_ANIMATION $00
; ... 2 more decoded lines in JSON output
```

### C3:A111 LoopActiveEntityWalkPulseVar4Gate

- class: `event-bytecode-label`
- decode status: `complete`
- stop reason: terminal/control-flow stop
- raw preview: `06 08 20 04 0B 1E A1 3B 01 42 B2 A4 C0 06 08 20`

```text
C3:A111  06 08                EVENT_PAUSE $08
C3:A113  20 04                EVENT_WRITE_VAR_TO_TEMPVAR $04
C3:A115  0B 1E A1             EVENT_SHORTCALL_CONDITIONAL_NOT $C3:A11E <DATA_C3A11E>
C3:A118  3B 01                EVENT_SET_ANIMATION $01
C3:A11A  42 B2 A4 C0          EVENT_CALLROUTINE $C0:A4B2 <RefreshCurrentSlotVisualProfile_Mode1IfAligned>
C3:A11E  06 08                EVENT_PAUSE $08
C3:A120  20 04                EVENT_WRITE_VAR_TO_TEMPVAR $04
C3:A122  0B 11 A1             EVENT_SHORTCALL_CONDITIONAL_NOT $C3:A111 <LoopActiveEntityWalkPulseVar4Gate>
C3:A125  3B 00                EVENT_SET_ANIMATION $00
C3:A127  42 A8 A4 C0          EVENT_CALLROUTINE $C0:A4A8 <RefreshCurrentSlotVisualProfile_Mode0IfAligned>
C3:A12B  19 11 A1             EVENT_SHORTJUMP $C3:A111 <LoopActiveEntityWalkPulseVar4Gate>
```

### C3:A12E LoopActiveEntityWalkPulseVar4Countdown

- class: `event-bytecode-label`
- decode status: `complete`
- stop reason: terminal/control-flow stop
- raw preview: `20 04 0A 59 A1 24 06 01 20 04 16 59 A1 02 3B 01`

```text
C3:A12E  20 04                EVENT_WRITE_VAR_TO_TEMPVAR $04
C3:A130  0A 59 A1             EVENT_SHORTCALL_CONDITIONAL $C3:A159 <UNKNOWN_C3A159>
C3:A133  24                   EVENT_LOOP_TEMPVAR
C3:A134  06 01                EVENT_PAUSE $01
C3:A136  20 04                EVENT_WRITE_VAR_TO_TEMPVAR $04
C3:A138  16 59 A1             EVENT_BREAK_IF_FALSE $C3:A159 <UNKNOWN_C3A159>
C3:A13B  02                   EVENT_LOOP_END
C3:A13C  3B 01                EVENT_SET_ANIMATION $01
C3:A13E  42 B2 A4 C0          EVENT_CALLROUTINE $C0:A4B2 <RefreshCurrentSlotVisualProfile_Mode1IfAligned>
C3:A142  20 04                EVENT_WRITE_VAR_TO_TEMPVAR $04
C3:A144  0A 59 A1             EVENT_SHORTCALL_CONDITIONAL $C3:A159 <UNKNOWN_C3A159>
C3:A147  24                   EVENT_LOOP_TEMPVAR
C3:A148  06 01                EVENT_PAUSE $01
C3:A14A  20 04                EVENT_WRITE_VAR_TO_TEMPVAR $04
C3:A14C  16 59 A1             EVENT_BREAK_IF_FALSE $C3:A159 <UNKNOWN_C3A159>
C3:A14F  02                   EVENT_LOOP_END
; ... 3 more decoded lines in JSON output
```

### C3:A15E LoopC40015Var4GatedPulseUntilRelease

- class: `event-bytecode-label`
- decode status: `complete`
- stop reason: terminal/control-flow stop
- raw preview: `42 23 00 C4 06 08 20 04 0B 6F A1 3B 01 42 B2 A4`

```text
C3:A15E  42 23 00 C4          EVENT_CALLROUTINE $C4:0023 <StoreLowNibble1a42ToCurrentScriptField1372>
C3:A162  06 08                EVENT_PAUSE $08
C3:A164  20 04                EVENT_WRITE_VAR_TO_TEMPVAR $04
C3:A166  0B 6F A1             EVENT_SHORTCALL_CONDITIONAL_NOT $C3:A16F
C3:A169  3B 01                EVENT_SET_ANIMATION $01
C3:A16B  42 B2 A4 C0          EVENT_CALLROUTINE $C0:A4B2 <RefreshCurrentSlotVisualProfile_Mode1IfAligned>
C3:A16F  06 08                EVENT_PAUSE $08
C3:A171  42 15 00 C4          EVENT_CALLROUTINE $C4:0015 <ClearCurrentSlot10f2RefreshVisualAndCheckLiveArea>
C3:A175  0B 62 A1             EVENT_SHORTCALL_CONDITIONAL_NOT $C3:A162
C3:A178  19 04 A2             EVENT_SHORTJUMP $C3:A204 <ReleaseCurrentVisualEntityAndEnd>
```

### C3:A17B LoopC40015SlowPulseUntilRelease

- class: `event-bytecode-label`
- decode status: `complete`
- stop reason: terminal/control-flow stop
- raw preview: `06 18 3B 01 42 B2 A4 C0 06 30 42 15 00 C4 0B 7B`

```text
C3:A17B  06 18                EVENT_PAUSE $18
C3:A17D  3B 01                EVENT_SET_ANIMATION $01
C3:A17F  42 B2 A4 C0          EVENT_CALLROUTINE $C0:A4B2 <RefreshCurrentSlotVisualProfile_Mode1IfAligned>
C3:A183  06 30                EVENT_PAUSE $30
C3:A185  42 15 00 C4          EVENT_CALLROUTINE $C4:0015 <ClearCurrentSlot10f2RefreshVisualAndCheckLiveArea>
C3:A189  0B 7B A1             EVENT_SHORTCALL_CONDITIONAL_NOT $C3:A17B <LoopC40015SlowPulseUntilRelease>
C3:A18C  19 04 A2             EVENT_SHORTJUMP $C3:A204 <ReleaseCurrentVisualEntityAndEnd>
```

### C3:A18F LoopC40015FastPulseUntilRelease

- class: `event-bytecode-label`
- decode status: `complete`
- stop reason: terminal/control-flow stop
- raw preview: `06 18 3B 01 42 B2 A4 C0 06 18 42 15 00 C4 0B 8F`

```text
C3:A18F  06 18                EVENT_PAUSE $18
C3:A191  3B 01                EVENT_SET_ANIMATION $01
C3:A193  42 B2 A4 C0          EVENT_CALLROUTINE $C0:A4B2 <RefreshCurrentSlotVisualProfile_Mode1IfAligned>
C3:A197  06 18                EVENT_PAUSE $18
C3:A199  42 15 00 C4          EVENT_CALLROUTINE $C4:0015 <ClearCurrentSlot10f2RefreshVisualAndCheckLiveArea>
C3:A19D  0B 8F A1             EVENT_SHORTCALL_CONDITIONAL_NOT $C3:A18F <LoopC40015FastPulseUntilRelease>
C3:A1A0  19 04 A2             EVENT_SHORTJUMP $C3:A204 <ReleaseCurrentVisualEntityAndEnd>
```

### C3:A1DF LoopActiveEntityWalkPulse2FrameC40015Branch

- class: `event-bytecode-label`
- decode status: `complete`
- stop reason: terminal/control-flow stop
- raw preview: `06 02 3B 01 42 B2 A4 C0 06 02 42 15 00 C4 0B FE`

```text
C3:A1DF  06 02                EVENT_PAUSE $02
C3:A1E1  3B 01                EVENT_SET_ANIMATION $01
C3:A1E3  42 B2 A4 C0          EVENT_CALLROUTINE $C0:A4B2 <RefreshCurrentSlotVisualProfile_Mode1IfAligned>
C3:A1E7  06 02                EVENT_PAUSE $02
C3:A1E9  42 15 00 C4          EVENT_CALLROUTINE $C4:0015 <ClearCurrentSlot10f2RefreshVisualAndCheckLiveArea>
C3:A1ED  0B FE A0             EVENT_SHORTCALL_CONDITIONAL_NOT $C3:A0FE <LoopActiveEntityWalkPulse2FrameConditional>
C3:A1F0  19 04 A2             EVENT_SHORTJUMP $C3:A204 <ReleaseCurrentVisualEntityAndEnd>
```

### C3:A1F3 LoopC40015Pulse16FrameUntilRelease

- class: `event-bytecode-label`
- decode status: `complete`
- stop reason: terminal/control-flow stop
- raw preview: `06 10 3B 01 42 B2 A4 C0 06 10 42 15 00 C4 0B F3`

```text
C3:A1F3  06 10                EVENT_PAUSE $10
C3:A1F5  3B 01                EVENT_SET_ANIMATION $01
C3:A1F7  42 B2 A4 C0          EVENT_CALLROUTINE $C0:A4B2 <RefreshCurrentSlotVisualProfile_Mode1IfAligned>
C3:A1FB  06 10                EVENT_PAUSE $10
C3:A1FD  42 15 00 C4          EVENT_CALLROUTINE $C4:0015 <ClearCurrentSlot10f2RefreshVisualAndCheckLiveArea>
C3:A201  0B F3 A1             EVENT_SHORTCALL_CONDITIONAL_NOT $C3:A1F3 <LoopC40015Pulse16FrameUntilRelease>
C3:A204  42 F1 20 C0          EVENT_CALLROUTINE $C0:20F1 <ScriptRelease_CurrentEntityVisualState>
C3:A208  00                   EVENT_END
```

### C3:A204 ReleaseCurrentVisualEntityAndEnd

- class: `event-bytecode-asset`
- decode status: `complete`
- stop reason: terminal/control-flow stop
- raw preview: `42 F1 20 C0 00 06 04 19 04 A2 3B 00 42 A8 A4 C0`

```text
C3:A204  42 F1 20 C0          EVENT_CALLROUTINE $C0:20F1 <ScriptRelease_CurrentEntityVisualState>
C3:A208  00                   EVENT_END
```

### C3:A209 DelayThenReleaseCurrentVisualEntity

- class: `event-bytecode-asset`
- decode status: `complete`
- stop reason: terminal/control-flow stop
- raw preview: `06 04 19 04 A2 3B 00 42 A8 A4 C0 20 00 11 05 2C`

```text
C3:A209  06 04                EVENT_PAUSE $04
C3:A20B  19 04 A2             EVENT_SHORTJUMP $C3:A204 <ReleaseCurrentVisualEntityAndEnd>
```

### C3:A20E LoopVar0SelectedAnimationUntilOffscreen

- class: `event-bytecode-label`
- decode status: `complete`
- stop reason: terminal/control-flow stop
- raw preview: `3B 00 42 A8 A4 C0 20 00 11 05 2C A2 34 A2 3D A2`

```text
C3:A20E  3B 00                EVENT_SET_ANIMATION $00
C3:A210  42 A8 A4 C0          EVENT_CALLROUTINE $C0:A4A8 <RefreshCurrentSlotVisualProfile_Mode0IfAligned>
C3:A214  20 00                EVENT_WRITE_VAR_TO_TEMPVAR $00
C3:A216  11 05 2C A2 34 A2 3D A2 4E A2 5F A2 EVENT_SWITCH_CALL_TEMPVAR count=5 [$C3:A22C <Var0AnimationCase0Pulse8FrameOn>, $C3:A234 <Var0AnimationCase1Pulse8FrameOff>, $C3:A23D <Var0AnimationCase2Pulse4Frame>, $C3:A24E <Var0AnimationCase3Pulse32Frame>, $C3:A25F <Var0AnimationCase4Wait16Frame>]
C3:A222  42 B6 C6 C0          EVENT_CALLROUTINE $C0:C6B6 <CheckCurrentSlotInsideLiveAreaWindow>
C3:A226  0B 14 A2             EVENT_SHORTCALL_CONDITIONAL_NOT $C3:A214
C3:A229  19 7C A4             EVENT_SHORTJUMP $C3:A47C <ReleaseCurrentVisualEntityTail>
```

### C3:A22C Var0AnimationCase0Pulse8FrameOn

- class: `event-bytecode-asset`
- decode status: `complete`
- stop reason: terminal/control-flow stop
- raw preview: `06 08 3B 01 42 B2 A4 C0 06 08 3B 00 42 A8 A4 C0`

```text
C3:A22C  06 08                EVENT_PAUSE $08
C3:A22E  3B 01                EVENT_SET_ANIMATION $01
C3:A230  42 B2 A4 C0          EVENT_CALLROUTINE $C0:A4B2 <RefreshCurrentSlotVisualProfile_Mode1IfAligned>
C3:A234  06 08                EVENT_PAUSE $08
C3:A236  3B 00                EVENT_SET_ANIMATION $00
C3:A238  42 A8 A4 C0          EVENT_CALLROUTINE $C0:A4A8 <RefreshCurrentSlotVisualProfile_Mode0IfAligned>
C3:A23C  1B                   EVENT_SHORT_RETURN
```

### C3:A234 Var0AnimationCase1Pulse8FrameOff

- class: `event-bytecode-asset`
- decode status: `complete`
- stop reason: terminal/control-flow stop
- raw preview: `06 08 3B 00 42 A8 A4 C0 1B 06 04 3B 01 42 B2 A4`

```text
C3:A234  06 08                EVENT_PAUSE $08
C3:A236  3B 00                EVENT_SET_ANIMATION $00
C3:A238  42 A8 A4 C0          EVENT_CALLROUTINE $C0:A4A8 <RefreshCurrentSlotVisualProfile_Mode0IfAligned>
C3:A23C  1B                   EVENT_SHORT_RETURN
```

### C3:A23D Var0AnimationCase2Pulse4Frame

- class: `event-bytecode-asset`
- decode status: `complete`
- stop reason: terminal/control-flow stop
- raw preview: `06 04 3B 01 42 B2 A4 C0 06 04 3B 00 42 A8 A4 C0`

```text
C3:A23D  06 04                EVENT_PAUSE $04
C3:A23F  3B 01                EVENT_SET_ANIMATION $01
C3:A241  42 B2 A4 C0          EVENT_CALLROUTINE $C0:A4B2 <RefreshCurrentSlotVisualProfile_Mode1IfAligned>
C3:A245  06 04                EVENT_PAUSE $04
C3:A247  3B 00                EVENT_SET_ANIMATION $00
C3:A249  42 A8 A4 C0          EVENT_CALLROUTINE $C0:A4A8 <RefreshCurrentSlotVisualProfile_Mode0IfAligned>
C3:A24D  1B                   EVENT_SHORT_RETURN
```

### C3:A24E Var0AnimationCase3Pulse32Frame

- class: `event-bytecode-asset`
- decode status: `complete`
- stop reason: terminal/control-flow stop
- raw preview: `06 20 3B 01 42 B2 A4 C0 06 20 3B 00 42 A8 A4 C0`

```text
C3:A24E  06 20                EVENT_PAUSE $20
C3:A250  3B 01                EVENT_SET_ANIMATION $01
C3:A252  42 B2 A4 C0          EVENT_CALLROUTINE $C0:A4B2 <RefreshCurrentSlotVisualProfile_Mode1IfAligned>
C3:A256  06 20                EVENT_PAUSE $20
C3:A258  3B 00                EVENT_SET_ANIMATION $00
C3:A25A  42 A8 A4 C0          EVENT_CALLROUTINE $C0:A4A8 <RefreshCurrentSlotVisualProfile_Mode0IfAligned>
C3:A25E  1B                   EVENT_SHORT_RETURN
```

### C3:A25F Var0AnimationCase4Wait16Frame

- class: `event-bytecode-asset`
- decode status: `complete`
- stop reason: terminal/control-flow stop
- raw preview: `06 10 1B 42 DA A6 C0 42 76 5E C0 F1 A6 64 C0 19`

```text
C3:A25F  06 10                EVENT_PAUSE $10
C3:A261  1B                   EVENT_SHORT_RETURN
```

### C3:A262 LoopActiveEntityCollisionProbeRefresh

- class: `event-bytecode-label`
- decode status: `complete`
- stop reason: terminal/control-flow stop
- raw preview: `42 DA A6 C0 42 76 5E C0 F1 A6 64 C0 19 66 A2 0C`

```text
C3:A262  42 DA A6 C0          EVENT_CALLROUTINE $C0:A6DA <label_C0A6DA>
C3:A266  42 76 5E C0 F1 A6 64 C0 EVENT_CALLROUTINE $C0:5E76 <Update_CurrentSlotCollisionCache>, $F1, $A6, $64, $C0
C3:A26E  19 66 A2             EVENT_SHORTJUMP $C3:A266 <DATA_C3A266>
```

### C3:A2AA TrafficLightWaitUntilOffscreenAndRelease

- class: `event-bytecode-asset`
- decode status: `complete`
- stop reason: terminal/control-flow stop
- raw preview: `25 F0 9F 3B 00 39 42 DB C7 C0 42 BF A4 C0 06 08`

```text
C3:A2AA  25 F0 9F             EVENT_SET_PHYSICS_CALLBACK $C0:9FF0 <label_C09FF0>
C3:A2AD  3B 00                EVENT_SET_ANIMATION $00
C3:A2AF  39                   EVENT_SET_VELOCITIES_ZERO
C3:A2B0  42 DB C7 C0          EVENT_CALLROUTINE $C0:C7DB <UpdateCurrentSlotFootprintMask>
C3:A2B4  42 BF A4 C0          EVENT_CALLROUTINE $C0:A4BF <RefreshCurrentSlotVisualProfile_Mode0>
C3:A2B8  06 08                EVENT_PAUSE $08
C3:A2BA  42 B6 C6 C0          EVENT_CALLROUTINE $C0:C6B6 <CheckCurrentSlotInsideLiveAreaWindow>
C3:A2BE  0B B8 A2             EVENT_SHORTCALL_CONDITIONAL_NOT $C3:A2B8 <DATA_C3A2B8>
C3:A2C1  42 F1 20 C0          EVENT_CALLROUTINE $C0:20F1 <ScriptRelease_CurrentEntityVisualState>
C3:A2C5  00                   EVENT_END
```

### C3:A381 InitRandomWanderMovementWithCollisionProbe

- class: `event-bytecode-asset`
- decode status: `complete`
- stop reason: terminal/control-flow stop
- raw preview: `25 60 A3 3B 00 07 11 A1 07 62 A2 42 BF A4 C0 42`

```text
C3:A381  25 60 A3             EVENT_SET_PHYSICS_CALLBACK $C0:A360 <UpdatePosition_WhenNoNeighbor_WithSpriteRefresh>
C3:A384  3B 00                EVENT_SET_ANIMATION $00
C3:A386  07 11 A1             EVENT_START_TASK $C3:A111 <LoopActiveEntityWalkPulseVar4Gate>
C3:A389  07 62 A2             EVENT_START_TASK $C3:A262 <LoopActiveEntityCollisionProbeRefresh>
C3:A38C  42 BF A4 C0          EVENT_CALLROUTINE $C0:A4BF <RefreshCurrentSlotVisualProfile_Mode0>
C3:A390  42 85 A6 C0 00 01    EVENT_CALLROUTINE $C0:A685 <Script_SetCurrentSlotField2B32>, $00, $01
C3:A396  42 64 A9 C0 08 00 08 00 EVENT_CALLROUTINE $C0:A964 <ScriptWrapper_C47225_ReadTwoWords>, $08, $00, $08, $00
C3:A39E  19 B7 A3             EVENT_SHORTJUMP $C3:A3B7 <LoopRandomDirectionMovementWithRandomWait>
```

### C3:A3A1 InitC40015PulseWithCollisionProbe

- class: `event-bytecode-asset`
- decode status: `complete`
- stop reason: terminal/control-flow stop
- raw preview: `25 60 A3 3B 00 07 5E A1 07 62 A2 42 BF A4 C0 42`

```text
C3:A3A1  25 60 A3             EVENT_SET_PHYSICS_CALLBACK $C0:A360 <UpdatePosition_WhenNoNeighbor_WithSpriteRefresh>
C3:A3A4  3B 00                EVENT_SET_ANIMATION $00
C3:A3A6  07 5E A1             EVENT_START_TASK $C3:A15E <LoopC40015Var4GatedPulseUntilRelease>
C3:A3A9  07 62 A2             EVENT_START_TASK $C3:A262 <LoopActiveEntityCollisionProbeRefresh>
C3:A3AC  42 BF A4 C0          EVENT_CALLROUTINE $C0:A4BF <RefreshCurrentSlotVisualProfile_Mode0>
C3:A3B0  42 85 A6 C0 00 01    EVENT_CALLROUTINE $C0:A685 <Script_SetCurrentSlotField2B32>, $00, $01
C3:A3B6  1B                   EVENT_SHORT_RETURN
```

### C3:A3B7 LoopRandomDirectionMovementWithRandomWait

- class: `event-bytecode-label`
- decode status: `complete`
- stop reason: terminal/control-flow stop
- raw preview: `0E 04 00 00 42 69 72 C4 0A C9 A3 27 02 FF FF 19`

```text
C3:A3B7  0E 04 00 00          EVENT_SET_VAR $04, $0000
C3:A3BB  42 69 72 C4          EVENT_CALLROUTINE $C4:7269 <ClassifyCurrentSlotAgainstAreaBounds>
C3:A3BF  0A C9 A3             EVENT_SHORTCALL_CONDITIONAL $C3:A3C9 <ChooseRandomCardinalDirection>
C3:A3C2  27 02 FF FF          EVENT_BINOP_TEMPVAR $02, $FFFF
C3:A3C6  19 D6 A3             EVENT_SHORTJUMP $C3:A3D6 <ApplyRandomDirectionAndMovementTimer>
```

### C3:A3C9 ChooseRandomCardinalDirection

- class: `event-bytecode-asset`
- decode status: `complete`
- stop reason: terminal/control-flow stop
- raw preview: `42 82 9F C0 04 00 00 02 00 04 00 06 00 42 5F A6`

```text
C3:A3C9  42 82 9F C0 04 00 00 02 00 04 00 06 00 EVENT_CALLROUTINE $C0:9F82 <ChooseRandomScriptWord>, choices=4 [$0000, $0002, $0004, $0006]
C3:A3D6  42 5F A6 C0          EVENT_CALLROUTINE $C0:A65F <SetCurrentSlotDirectionClassIfActive>
C3:A3DA  42 3B C8 C0          EVENT_CALLROUTINE $C0:C83B <InstallScriptMovementVectorFromDirection>
C3:A3DE  42 82 9F C0 02 08 00 10 00 EVENT_CALLROUTINE $C0:9F82 <ChooseRandomScriptWord>, choices=2 [$0008, $0010]
C3:A3E7  42 4E CA C0          EVENT_CALLROUTINE $C0:CA4E <SetMovementTaskTimerFromActiveVector>
C3:A3EB  39                   EVENT_SET_VELOCITIES_ZERO
C3:A3EC  0E 04 01 00          EVENT_SET_VAR $04, $0001
C3:A3F0  42 82 9F C0 04 1E 00 3C 00 5A 00 78 00 EVENT_CALLROUTINE $C0:9F82 <ChooseRandomScriptWord>, choices=4 [$001E, $003C, $005A, $0078]
C3:A3FD  44                   EVENT_WRITE_TEMPVAR_WAITTIMER
C3:A3FE  19 B7 A3             EVENT_SHORTJUMP $C3:A3B7 <LoopRandomDirectionMovementWithRandomWait>
```

### C3:A3D6 ApplyRandomDirectionAndMovementTimer

- class: `event-bytecode-asset`
- decode status: `complete`
- stop reason: terminal/control-flow stop
- raw preview: `42 5F A6 C0 42 3B C8 C0 42 82 9F C0 02 08 00 10`

```text
C3:A3D6  42 5F A6 C0          EVENT_CALLROUTINE $C0:A65F <SetCurrentSlotDirectionClassIfActive>
C3:A3DA  42 3B C8 C0          EVENT_CALLROUTINE $C0:C83B <InstallScriptMovementVectorFromDirection>
C3:A3DE  42 82 9F C0 02 08 00 10 00 EVENT_CALLROUTINE $C0:9F82 <ChooseRandomScriptWord>, choices=2 [$0008, $0010]
C3:A3E7  42 4E CA C0          EVENT_CALLROUTINE $C0:CA4E <SetMovementTaskTimerFromActiveVector>
C3:A3EB  39                   EVENT_SET_VELOCITIES_ZERO
C3:A3EC  0E 04 01 00          EVENT_SET_VAR $04, $0001
C3:A3F0  42 82 9F C0 04 1E 00 3C 00 5A 00 78 00 EVENT_CALLROUTINE $C0:9F82 <ChooseRandomScriptWord>, choices=4 [$001E, $003C, $005A, $0078]
C3:A3FD  44                   EVENT_WRITE_TEMPVAR_WAITTIMER
C3:A3FE  19 B7 A3             EVENT_SHORTJUMP $C3:A3B7 <LoopRandomDirectionMovementWithRandomWait>
```

### C3:A3E7 SetMovementTimerThenRandomWait

- class: `event-bytecode-asset`
- decode status: `complete`
- stop reason: terminal/control-flow stop
- raw preview: `42 4E CA C0 39 0E 04 01 00 42 82 9F C0 04 1E 00`

```text
C3:A3E7  42 4E CA C0          EVENT_CALLROUTINE $C0:CA4E <SetMovementTaskTimerFromActiveVector>
C3:A3EB  39                   EVENT_SET_VELOCITIES_ZERO
C3:A3EC  0E 04 01 00          EVENT_SET_VAR $04, $0001
C3:A3F0  42 82 9F C0 04 1E 00 3C 00 5A 00 78 00 EVENT_CALLROUTINE $C0:9F82 <ChooseRandomScriptWord>, choices=4 [$001E, $003C, $005A, $0078]
C3:A3FD  44                   EVENT_WRITE_TEMPVAR_WAITTIMER
C3:A3FE  19 B7 A3             EVENT_SHORTJUMP $C3:A3B7 <LoopRandomDirectionMovementWithRandomWait>
```

### C3:A401 InitNpcAttentionPathIfNoCachedNeighbor

- class: `event-bytecode-asset`
- decode status: `complete`
- stop reason: terminal/control-flow stop
- raw preview: `25 F0 9F 42 DA A6 C0 06 01 42 B8 A6 C0 0B 25 A4`

```text
C3:A401  25 F0 9F             EVENT_SET_PHYSICS_CALLBACK $C0:9FF0 <label_C09FF0>
C3:A404  42 DA A6 C0          EVENT_CALLROUTINE $C0:A6DA <label_C0A6DA>
C3:A408  06 01                EVENT_PAUSE $01
C3:A40A  42 B8 A6 C0          EVENT_CALLROUTINE $C0:A6B8 <GetCurrentSlotHasNoCachedNeighborFlag>
C3:A40E  0B 25 A4             EVENT_SHORTCALL_CONDITIONAL_NOT $C3:A425 <UNKNOWN_C3A425>
C3:A411  08 F7 D7 C0          EVENT_SET_TICK_CALLBACK $C0:D7F7 <Consume_CurrentSlotAttentionPath>
C3:A415  25 60 A3             EVENT_SET_PHYSICS_CALLBACK $C0:A360 <UpdatePosition_WhenNoNeighbor_WithSpriteRefresh>
C3:A418  3B 00                EVENT_SET_ANIMATION $00
C3:A41A  42 BF A4 C0          EVENT_CALLROUTINE $C0:A4BF <RefreshCurrentSlotVisualProfile_Mode0>
C3:A41E  0E 00 00 00          EVENT_SET_VAR $00, $0000
C3:A422  07 0E A2             EVENT_START_TASK $C3:A20E <LoopVar0SelectedAnimationUntilOffscreen>
C3:A425  1B                   EVENT_SHORT_RETURN
```

### C3:A426 StartNpcAttentionTerrainCollisionLoop

- class: `event-bytecode-label`
- decode status: `complete`
- stop reason: terminal/control-flow stop
- raw preview: `1A 01 A4 07 34 A4 1B 1A 01 A4 07 48 A4 1B 42 78`

```text
C3:A426  1A 01 A4             EVENT_SHORTCALL $C3:A401 <InitNpcAttentionPathIfNoCachedNeighbor>
C3:A429  07 34 A4             EVENT_START_TASK $C3:A434 <LoopNpcAttentionTerrainCollision>
C3:A42C  1B                   EVENT_SHORT_RETURN
```

### C3:A42D StartNpcAttentionHorizontalCollisionLoop

- class: `event-bytecode-label`
- decode status: `complete`
- stop reason: terminal/control-flow stop
- raw preview: `1A 01 A4 07 48 A4 1B 42 78 64 C0 42 82 5E C0 42`

```text
C3:A42D  1A 01 A4             EVENT_SHORTCALL $C3:A401 <InitNpcAttentionPathIfNoCachedNeighbor>
C3:A430  07 48 A4             EVENT_START_TASK $C3:A448 <LoopNpcAttentionHorizontalCollision>
C3:A433  1B                   EVENT_SHORT_RETURN
```

### C3:A434 LoopNpcAttentionTerrainCollision

- class: `event-bytecode-label`
- decode status: `complete`
- stop reason: terminal/control-flow stop
- raw preview: `42 78 64 C0 42 82 5E C0 42 B0 D5 C0 0B 5C A4 06`

```text
C3:A434  42 78 64 C0          EVENT_CALLROUTINE $C0:6478 <Update_CurrentSlotNeighborCache_Priority>
C3:A438  42 82 5E C0          EVENT_CALLROUTINE $C0:5E82 <Update_CurrentSlotCollisionCache_WithTerrainCompatibility>
C3:A43C  42 B0 D5 C0          EVENT_CALLROUTINE $C0:D5B0 <Gate_NpcAttentionCoordinatorFromScript>
C3:A440  0B 5C A4             EVENT_SHORTCALL_CONDITIONAL_NOT $C3:A45C <FinishNpcAttentionAndReleaseActor>
C3:A443  06 01                EVENT_PAUSE $01
C3:A445  19 34 A4             EVENT_SHORTJUMP $C3:A434 <LoopNpcAttentionTerrainCollision>
```

### C3:A448 LoopNpcAttentionHorizontalCollision

- class: `event-bytecode-label`
- decode status: `complete`
- stop reason: terminal/control-flow stop
- raw preview: `42 78 64 C0 42 CE 5E C0 42 B0 D5 C0 0B 5C A4 06`

```text
C3:A448  42 78 64 C0          EVENT_CALLROUTINE $C0:6478 <Update_CurrentSlotNeighborCache_Priority>
C3:A44C  42 CE 5E C0          EVENT_CALLROUTINE $C0:5ECE <Update_CurrentSlotCollisionCache_FromHorizontalEdges>
C3:A450  42 B0 D5 C0          EVENT_CALLROUTINE $C0:D5B0 <Gate_NpcAttentionCoordinatorFromScript>
C3:A454  0B 5C A4             EVENT_SHORTCALL_CONDITIONAL_NOT $C3:A45C <FinishNpcAttentionAndReleaseActor>
C3:A457  06 01                EVENT_PAUSE $01
C3:A459  19 48 A4             EVENT_SHORTJUMP $C3:A448 <LoopNpcAttentionHorizontalCollision>
```

### C3:A45C FinishNpcAttentionAndReleaseActor

- class: `event-bytecode-label`
- decode status: `complete`
- stop reason: terminal/control-flow stop
- raw preview: `06 01 42 9B D5 C0 0B 5C A4 3B 00 39 25 F0 9F 0E`

```text
C3:A45C  06 01                EVENT_PAUSE $01
C3:A45E  42 9B D5 C0          EVENT_CALLROUTINE $C0:D59B <Check_NpcAttentionCoordinatorActive>
C3:A462  0B 5C A4             EVENT_SHORTCALL_CONDITIONAL_NOT $C3:A45C <FinishNpcAttentionAndReleaseActor>
C3:A465  3B 00                EVENT_SET_ANIMATION $00
C3:A467  39                   EVENT_SET_VELOCITIES_ZERO
C3:A468  25 F0 9F             EVENT_SET_PHYSICS_CALLBACK $C0:9FF0 <label_C09FF0>
C3:A46B  0E 00 01 00          EVENT_SET_VAR $00, $0001
C3:A46F  06 01                EVENT_PAUSE $01
C3:A471  01 03                EVENT_LOOP $03
C3:A473  3B FF                EVENT_SET_ANIMATION $FF
C3:A475  06 05                EVENT_PAUSE $05
C3:A477  3B 00                EVENT_SET_ANIMATION $00
C3:A479  06 05                EVENT_PAUSE $05
C3:A47B  02                   EVENT_LOOP_END
C3:A47C  42 F1 20 C0          EVENT_CALLROUTINE $C0:20F1 <ScriptRelease_CurrentEntityVisualState>
C3:A480  00                   EVENT_END
```

### C3:A47C ReleaseCurrentVisualEntityTail

- class: `event-bytecode-asset`
- decode status: `complete`
- stop reason: terminal/control-flow stop
- raw preview: `42 F1 20 C0 00 42 BF A4 C0 3B 00 19 5C A4 1A 26`

```text
C3:A47C  42 F1 20 C0          EVENT_CALLROUTINE $C0:20F1 <ScriptRelease_CurrentEntityVisualState>
C3:A480  00                   EVENT_END
```

### C3:AA38 InitActionScriptMovementState

- class: `event-bytecode-asset`
- decode status: `complete`
- stop reason: terminal/control-flow stop
- raw preview: `25 7A A3 3B 00 07 11 A1 39 0E 04 00 00 1B 25 7A`

```text
C3:AA38  25 7A A3             EVENT_SET_PHYSICS_CALLBACK $C0:A37A <UpdatePosition_WhenNoNeighbor_WithSpriteRefresh_CurrentSlot>
C3:AA3B  3B 00                EVENT_SET_ANIMATION $00
C3:AA3D  07 11 A1             EVENT_START_TASK $C3:A111 <LoopActiveEntityWalkPulseVar4Gate>
C3:AA40  39                   EVENT_SET_VELOCITIES_ZERO
C3:AA41  0E 04 00 00          EVENT_SET_VAR $04, $0000
C3:AA45  1B                   EVENT_SHORT_RETURN
```

### C3:AA46 InitMovementPreset40_00Pulse24Frame

- class: `event-bytecode-asset`
- decode status: `complete`
- stop reason: terminal/control-flow stop
- raw preview: `25 7A A3 3B 00 07 B2 A0 39 42 BF A4 C0 42 85 A6`

```text
C3:AA46  25 7A A3             EVENT_SET_PHYSICS_CALLBACK $C0:A37A <UpdatePosition_WhenNoNeighbor_WithSpriteRefresh_CurrentSlot>
C3:AA49  3B 00                EVENT_SET_ANIMATION $00
C3:AA4B  07 B2 A0             EVENT_START_TASK $C3:A0B2 <LoopActiveEntityWalkPulse24Frame>
C3:AA4E  39                   EVENT_SET_VELOCITIES_ZERO
C3:AA4F  42 BF A4 C0          EVENT_CALLROUTINE $C0:A4BF <RefreshCurrentSlotVisualProfile_Mode0>
C3:AA53  42 85 A6 C0 40 00    EVENT_CALLROUTINE $C0:A685 <Script_SetCurrentSlotField2B32>, $40, $00
C3:AA59  1B                   EVENT_SHORT_RETURN
```

### C3:AA5A InitMovementPreset00_01Pulse12Frame

- class: `event-bytecode-asset`
- decode status: `complete`
- stop reason: terminal/control-flow stop
- raw preview: `25 7A A3 3B 00 07 C5 A0 39 42 BF A4 C0 42 85 A6`

```text
C3:AA5A  25 7A A3             EVENT_SET_PHYSICS_CALLBACK $C0:A37A <UpdatePosition_WhenNoNeighbor_WithSpriteRefresh_CurrentSlot>
C3:AA5D  3B 00                EVENT_SET_ANIMATION $00
C3:AA5F  07 C5 A0             EVENT_START_TASK $C3:A0C5 <LoopActiveEntityWalkPulse12Frame>
C3:AA62  39                   EVENT_SET_VELOCITIES_ZERO
C3:AA63  42 BF A4 C0          EVENT_CALLROUTINE $C0:A4BF <RefreshCurrentSlotVisualProfile_Mode0>
C3:AA67  42 85 A6 C0 00 01    EVENT_CALLROUTINE $C0:A685 <Script_SetCurrentSlotField2B32>, $00, $01
C3:AA6D  1B                   EVENT_SHORT_RETURN
```

### C3:AA6E InitMovementPreset60_01Pulse9Frame

- class: `event-bytecode-asset`
- decode status: `complete`
- stop reason: terminal/control-flow stop
- raw preview: `25 7A A3 3B 00 07 D8 A0 39 42 BF A4 C0 42 85 A6`

```text
C3:AA6E  25 7A A3             EVENT_SET_PHYSICS_CALLBACK $C0:A37A <UpdatePosition_WhenNoNeighbor_WithSpriteRefresh_CurrentSlot>
C3:AA71  3B 00                EVENT_SET_ANIMATION $00
C3:AA73  07 D8 A0             EVENT_START_TASK $C3:A0D8 <LoopActiveEntityWalkPulse9FrameConditional>
C3:AA76  39                   EVENT_SET_VELOCITIES_ZERO
C3:AA77  42 BF A4 C0          EVENT_CALLROUTINE $C0:A4BF <RefreshCurrentSlotVisualProfile_Mode0>
C3:AA7B  42 85 A6 C0 60 01    EVENT_CALLROUTINE $C0:A685 <Script_SetCurrentSlotField2B32>, $60, $01
C3:AA81  1B                   EVENT_SHORT_RETURN
```

### C3:AA82 InitMovementPreset00_02Pulse6Frame

- class: `event-bytecode-asset`
- decode status: `complete`
- stop reason: terminal/control-flow stop
- raw preview: `25 7A A3 3B 00 07 EB A0 39 42 BF A4 C0 42 85 A6`

```text
C3:AA82  25 7A A3             EVENT_SET_PHYSICS_CALLBACK $C0:A37A <UpdatePosition_WhenNoNeighbor_WithSpriteRefresh_CurrentSlot>
C3:AA85  3B 00                EVENT_SET_ANIMATION $00
C3:AA87  07 EB A0             EVENT_START_TASK $C3:A0EB <LoopActiveEntityWalkPulse6FrameConditional>
C3:AA8A  39                   EVENT_SET_VELOCITIES_ZERO
C3:AA8B  42 BF A4 C0          EVENT_CALLROUTINE $C0:A4BF <RefreshCurrentSlotVisualProfile_Mode0>
C3:AA8F  42 85 A6 C0 00 02    EVENT_CALLROUTINE $C0:A685 <Script_SetCurrentSlotField2B32>, $00, $02
C3:AA95  1B                   EVENT_SHORT_RETURN
```

### C3:AA96 InitMovementPreset00_06Pulse2Frame

- class: `event-bytecode-asset`
- decode status: `complete`
- stop reason: terminal/control-flow stop
- raw preview: `25 7A A3 3B 00 07 FE A0 39 42 BF A4 C0 42 85 A6`

```text
C3:AA96  25 7A A3             EVENT_SET_PHYSICS_CALLBACK $C0:A37A <UpdatePosition_WhenNoNeighbor_WithSpriteRefresh_CurrentSlot>
C3:AA99  3B 00                EVENT_SET_ANIMATION $00
C3:AA9B  07 FE A0             EVENT_START_TASK $C3:A0FE <LoopActiveEntityWalkPulse2FrameConditional>
C3:AA9E  39                   EVENT_SET_VELOCITIES_ZERO
C3:AA9F  42 BF A4 C0          EVENT_CALLROUTINE $C0:A4BF <RefreshCurrentSlotVisualProfile_Mode0>
C3:AAA3  42 85 A6 C0 00 06    EVENT_CALLROUTINE $C0:A685 <Script_SetCurrentSlotField2B32>, $00, $06
C3:AAA9  1B                   EVENT_SHORT_RETURN
```

### C3:AAAA InitMovementPresetVar4Countdown

- class: `event-bytecode-asset`
- decode status: `complete`
- stop reason: terminal/control-flow stop
- raw preview: `25 7A A3 3B 00 07 2E A1 39 0E 04 0C 00 1B 25 7A`

```text
C3:AAAA  25 7A A3             EVENT_SET_PHYSICS_CALLBACK $C0:A37A <UpdatePosition_WhenNoNeighbor_WithSpriteRefresh_CurrentSlot>
C3:AAAD  3B 00                EVENT_SET_ANIMATION $00
C3:AAAF  07 2E A1             EVENT_START_TASK $C3:A12E <LoopActiveEntityWalkPulseVar4Countdown>
C3:AAB2  39                   EVENT_SET_VELOCITIES_ZERO
C3:AAB3  0E 04 0C 00          EVENT_SET_VAR $04, $000C
C3:AAB7  1B                   EVENT_SHORT_RETURN
```

### C3:AB12 InitMovementPreset00_06C40015Branch

- class: `event-bytecode-asset`
- decode status: `complete`
- stop reason: terminal/control-flow stop
- raw preview: `25 7A A3 3B 00 07 DF A1 39 42 BF A4 C0 42 85 A6`

```text
C3:AB12  25 7A A3             EVENT_SET_PHYSICS_CALLBACK $C0:A37A <UpdatePosition_WhenNoNeighbor_WithSpriteRefresh_CurrentSlot>
C3:AB15  3B 00                EVENT_SET_ANIMATION $00
C3:AB17  07 DF A1             EVENT_START_TASK $C3:A1DF <LoopActiveEntityWalkPulse2FrameC40015Branch>
C3:AB1A  39                   EVENT_SET_VELOCITIES_ZERO
C3:AB1B  42 BF A4 C0          EVENT_CALLROUTINE $C0:A4BF <RefreshCurrentSlotVisualProfile_Mode0>
C3:AB1F  42 85 A6 C0 00 06    EVENT_CALLROUTINE $C0:A685 <Script_SetCurrentSlotField2B32>, $00, $06
C3:AB25  1B                   EVENT_SHORT_RETURN
```

### C3:AB26 InitAlternatePhysicsVar4WalkPulse

- class: `event-bytecode-asset`
- decode status: `complete`
- stop reason: terminal/control-flow stop
- raw preview: `23 3A A0 25 F1 9F 3B 00 07 11 A1 39 0E 04 00 00`

```text
C3:AB26  23 3A A0             EVENT_SET_POSITION_CHANGE_CALLBACK $C0:A03A <ProjectWorldToScreen_FromCamera31AndHeight>
C3:AB29  25 F1 9F             EVENT_SET_PHYSICS_CALLBACK $C0:9FF1 <Integrate_XYAndZVelocity_WithSpriteRefresh>
C3:AB2C  3B 00                EVENT_SET_ANIMATION $00
C3:AB2E  07 11 A1             EVENT_START_TASK $C3:A111 <LoopActiveEntityWalkPulseVar4Gate>
C3:AB31  39                   EVENT_SET_VELOCITIES_ZERO
C3:AB32  0E 04 00 00          EVENT_SET_VAR $04, $0000
C3:AB36  1B                   EVENT_SHORT_RETURN
```

### C3:AB44 RefreshActiveEntityDirectionAndVisualProfile

- class: `event-bytecode-asset`
- decode status: `complete`
- stop reason: terminal/control-flow stop
- raw preview: `42 DB 6A C4 42 44 70 C4 42 0A 6B C4 42 5F A6 C0`

```text
C3:AB44  42 DB 6A C4          EVENT_CALLROUTINE $C4:6ADB <ComputeCurrentSlotTargetDirectionOctant>
C3:AB48  42 44 70 C4          EVENT_CALLROUTINE $C4:7044 <ProjectAngleIntoCurrentSlotVectorWords>
C3:AB4C  42 0A 6B C4          EVENT_CALLROUTINE $C4:6B0A <RoundAngleToOctantAndCacheCurrentSlot>
C3:AB50  42 5F A6 C0          EVENT_CALLROUTINE $C0:A65F <SetCurrentSlotDirectionClassIfActive>
C3:AB54  42 BF A4 C0          EVENT_CALLROUTINE $C0:A4BF <RefreshCurrentSlotVisualProfile_Mode0>
C3:AB58  1B                   EVENT_SHORT_RETURN
```

### C3:AB59 WaitForActiveEntityMovementToFinish

- class: `event-bytecode-label`
- decode status: `complete`
- stop reason: terminal/control-flow stop
- raw preview: `1A 44 AB 06 01 42 DC A8 C0 0A 5C AB 39 1B 42 DB`

```text
C3:AB59  1A 44 AB             EVENT_SHORTCALL $C3:AB44 <RefreshActiveEntityDirectionAndVisualProfile>
C3:AB5C  06 01                EVENT_PAUSE $01
C3:AB5E  42 DC A8 C0          EVENT_CALLROUTINE $C0:A8DC <ScriptWrapper_C47143_Mode01>
C3:AB62  0A 5C AB             EVENT_SHORTCALL_CONDITIONAL $C3:AB5C <DATA_C3AB5C>
C3:AB65  39                   EVENT_SET_VELOCITIES_ZERO
C3:AB66  1B                   EVENT_SHORT_RETURN
```

### C3:AB8A WaitUntilPlayerLeavesActiveArea

- class: `event-bytecode-label`
- decode status: `complete`
- stop reason: terminal/control-flow stop
- raw preview: `06 01 42 74 6E C4 0A 8A AB 1B 06 01 42 74 6E C4`

```text
C3:AB8A  06 01                EVENT_PAUSE $01
C3:AB8C  42 74 6E C4          EVENT_CALLROUTINE $C4:6E74 <label_C46E74>
C3:AB90  0A 8A AB             EVENT_SHORTCALL_CONDITIONAL $C3:AB8A <WaitUntilPlayerLeavesActiveArea>
C3:AB93  1B                   EVENT_SHORT_RETURN
```

### C3:AFA3 LoopPartyLooksAtActiveEntity

- class: `event-bytecode-label`
- decode status: `complete`
- stop reason: terminal/control-flow stop
- raw preview: `42 3B 8B C4 06 03 19 A3 AF 25 7A A3 3B 00 07 7B`

```text
C3:AFA3  42 3B 8B C4          EVENT_CALLROUTINE $C4:8B3B
C3:AFA7  06 03                EVENT_PAUSE $03
C3:AFA9  19 A3 AF             EVENT_SHORTJUMP $C3:AFA3 <LoopPartyLooksAtActiveEntity>
```
