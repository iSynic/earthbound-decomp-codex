# C0 Decoded Source Promotion Pass

This note tracks the first C0 pass that replaces working-name byte corridors
with decoded mnemonic 65816 source while preserving full-bank byte-equivalence.

## Result

- Promoted C0 source modules: `481 / 504`
- Decoded mnemonic lines in `src/c0`: `27603`
- Decoded source bytes: `58449`
- Remaining protected byte-corridor bytes: `7087`
- Remaining byte-corridor modules: `23`
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

## Follow-up Promotion Sweep

The second promotion sweep carried C0 through most of the runtime-heavy bank:

- `C0:329F..C0:6BFF`: party condition, mushroomized walking, bicycle,
  registry, interaction, collision, surface, movement-trigger, and staged
  movement helpers.
- `C0:6E1A..C0:8ED2`: staged movement continuation, NMI/PPU queue handling,
  input playback/recording, frame callbacks, display renderer queues, and
  register update helpers.
- `C0:8FE6..C0:9558`: hardware multiply/division helpers plus delayed action
  and task/actionscript setup.
- `C0:9AC5..C0:A1AE`: action-script target mutation handlers, script opcodes,
  task allocation/list helpers, projection helpers, and cached map property
  lookup code.
- `C0:A1CE..C0:A60B`: packed map-property selectors, task data rendering,
  physics comparison helpers, position update helpers, and visual profile
  refresh code.
- `C0:A643..C0:B2FF`: action-script wrappers, SPC/APU helpers, battle
  background DMA setup, color math/window helpers, and battle background offset
  table generation.
- `C0:B65F..C0:CEBE` and `C0:CF97..C0:F41E`: intro overworld setup,
  pathfinding, direction/encounter gates, movement-vector helpers, NPC
  attention coordination, delayed actions, teleport state machines, and
  title/intro loop control.

## Remaining Protected Corridors

Most remaining C0 corridors are intentional data tables. A few are mixed
code/data or multi-entry interpreter payloads that need a split-aware source
format before promotion.

- `C0:0000..C0:0085` bank prefix/prologue bytes.
- `C0:6BFF..C0:6E1A` deferred script transition helper with inline payload.
- `C0:8ED2..C0:8FC2` copy helper with embedded data tail.
- `C0:8FC2..C0:8FE6` VRAM port triple table tail.
- `C0:9558..C0:9ABD` script opcode pointer table.
- `C0:9ABD..C0:9AC5` script target mutation table.
- `C0:9AF9..C0:9B09` entity script variable pointer table.
- `C0:A1AE..C0:A1CE` cached map property shift dispatch table.
- `C0:A20C..C0:A21C` map buffer page source pointer table.
- `C0:A2AB..C0:A2B7` physics callback threshold table A.
- `C0:A30B..C0:A317` physics callback threshold table B.
- `C0:A350..C0:A360` physics callback comparison dispatch table.
- `C0:A60B..C0:A623` visual profile direction offset table.
- `C0:A623..C0:A643` visual profile secondary offset table.
- `C0:AE16..C0:AE1D` DMA channel flag table.
- `C0:AE1D..C0:AE26` battle background DMA B-bus register table.
- `C0:AE26..C0:AE34` battle background DMA source descriptor templates.
- `C0:AE44..C0:AFCD` inverse DMA channel mask table.
- `C0:B0A6..C0:B0AA` window mask nibble lookup table.
- `C0:B2FF..C0:B65F` battle background offset clamp lookup table.
- `C0:C4CF..C0:C4F7` player direction remap table.
- `C0:CEBE..C0:CF97` arc-phase turn helper with an inline byte table at
  `C0:CF58..C0:CF97`.
- `C0:F41E..C0:10000` command-stream frame callback/interpreter payload; the
  linear decoder crosses the bank end without entry-state annotations, so this
  needs split-aware handling.

## Next Seam

Implement a mixed code/data source-unit generator so the remaining non-table
payloads can be represented as readable code plus inline `db`/`dw` data while
preserving byte-equivalence.
