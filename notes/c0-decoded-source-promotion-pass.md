# C0 Decoded Source Promotion Pass

This note tracks the first C0 pass that replaces working-name byte corridors
with decoded mnemonic 65816 source while preserving full-bank byte-equivalence.

## Result

- Promoted C0 source modules: `50 / 504`
- Decoded mnemonic lines in `src/c0`: `6408`
- Remaining byte-corridor modules: `454`
- Full C0 byte-equivalence: `OK`
- Mismatches: `0`

Validation command:

```powershell
python tools/validate_source_bank_byte_equivalence.py --bank C0 --module all --combined --scaffold src/c0/bank_c0_helpers_asar.asm --strict
```

## Promoted Ranges

### Landing Display And Scroll Setup

- `C0:0085..C0:0172` `Install_LandingAnimatedGraphicsStrip`
- `C0:0172..C0:023F` `Tick_LandingProfileAnimatedVramUploads`
- `C0:023F..C0:030F` `Build_LandingProfileStepSequencer`
- `C0:030F..C0:0391` `Advance_LandingProfileStepSequencer`
- `C0:0391..C0:0480` `Sum_LandingTemplateComponents`
- `C0:0480..C0:062A` `Build_LandingPackedRowTable0200`
- `C0:062A..C0:0778` `Load_LandingHdmaDispatchBlock`
- `C0:0778..C0:07B6` `Build_LandingActiveRowCache0300`
- `C0:07B6..C0:08CF` `Install_LandingProfileTemplateBlock0240`
- `C0:08CF..C0:0974` `Derive_LandingRegionProfileFromDestination`
- `C0:0974..C0:097B` `Check_LandingRegionCacheAndMaybeRebuild`
- `C0:097B..C0:0A95` `Commit_LandingProfileSelector`
- `C0:0A95..C0:0A9A` `Commit_LandingRegionClass`
- `C0:0A9A..C0:0AA1` `Commit_LandingRegionVariant`
- `C0:0AA1..C0:0AC5` `Lookup_PositionCellContextWord`
- `C0:0AC5..C0:0BDC` `Load_VerticalMovementMapStripPayload`
- `C0:0BDC..C0:0CF3` `Load_HorizontalMovementMapStripPayload`
- `C0:0CF3..C0:0D7E` `Load_VerticalMovementCollisionStripPayload`
- `C0:0D7E..C0:0E16` `Assemble_LandingHdmaParameterBlock`
- `C0:0E16..C0:0FCB` `Upload_VerticalMovementMapStrip`
- `C0:0FCB..C0:1181` `Upload_HorizontalMovementMapStrip`
- `C0:1181..C0:1558` `Upload_AuxiliaryMovementMapStrip`
- `C0:1558..C0:17EA` `Update_RuntimeScrollShadowsAndIncrementalRefresh`
- `C0:17EA..C0:19E2` `Accumulate_OverworldCameraStep`

### Entity And Visual Allocation Setup

- `C0:19E2..C0:1A63` `Refresh_MapStripsAroundCamera`
- `C0:1A63..C0:1A69` `Refresh_MapStripVia0E16FarWrapper`
- `C0:1A69..C0:1A86` `Reset_EntitySlotStateTables`
- `C0:1A86..C0:1A9D` `Reset_EntityBytePool467E`
- `C0:1A9D..C0:1B15` `Find_FreeEntityBytePoolRun467E`
- `C0:1B15..C0:1B96` `Release_EntityBytePoolRun467E`
- `C0:1B96..C0:1C11` `Reserve_VisualMemorySpan4A00`
- `C0:1C11..C0:1C52` `Rewrite_VisualMemoryReservations4A00`
- `C0:1C52..C0:1CA8` `Reserve_AndUploadEntityVisualTiles`
- `C0:1CA8..C0:1D38` `Upload_CompanionVisualTiles4000Band`
- `C0:1D38..C0:1DED` `Build_EntityVisualRecords467E`
- `C0:1DED..C0:1E49` `Read_SpritePoseVisualDescriptor`
- `C0:1E49..C0:20F1` `Initialize_EntityWithSpritePose`
- `C0:20F1..C0:2140` `Script_ReleaseCurrentEntityVisualState`
- `C0:2140..C0:2291` `Release_EntitySlotAndVisualState`
- `C0:2291..C0:2547` `Test_SecondaryDescriptorLeadingPieceContext`
- `C0:2547..C0:255C` `Seed_SpawnCandidateDirectionClass`
- `C0:255C..C0:25CF` `Run_VerticalCompanionSpawnProducer`
- `C0:25CF..C0:263D` `Run_HorizontalCompanionSpawnProducer`
- `C0:263D..C0:2668` `Lookup_PlacementTileWordD01880`
- `C0:2668..C0:28E7` `Resolve_SpawnProbeCandidateList`
- `C0:28E7..C0:2957` `Try_PlaceSpawnCandidateFromListEntry`
- `C0:2957..C0:2A50` `Initialize_SpawnedCandidateEntitySlot`
- `C0:2A50..C0:2A6B` `Iterate_SpawnCandidateList`
- `C0:2A6B..C0:2B55` `Spawn_Horizontal`
- `C0:2B55..C0:329F` `Spawn_Vertical`

## Tooling

Added `tools/promote_linear_range_to_decoded_source.py` to make this repeatable.
It decodes one byte-corridor range with `emit_linear_source_module.py` logic,
updates the local build-candidate range manifest so the range becomes a source
segment, and leaves the full-bank scaffold generator/validator workflow intact.

Example:

```powershell
python tools/promote_linear_range_to_decoded_source.py --bank C0 --module c0_0085_install_landing_animated_graphics_strip --subsystem landing-display-decoded-source
python tools/build_source_bank_scaffold.py --bank C0
python tools/validate_source_bank_byte_equivalence.py --bank C0 --module all --combined --scaffold src/c0/bank_c0_helpers_asar.asm --strict
```

## Next Seam

Continue at `C0:329F`. The next cluster begins with character-affliction and
mushroomized-walking helpers, then moves into bicycle/registry, interaction,
collision, movement trigger, task/actionscript, and teleport systems.
