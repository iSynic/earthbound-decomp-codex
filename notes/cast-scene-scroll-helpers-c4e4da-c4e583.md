# Cast Scene Loader, Credits, And Audio Tail Helpers `C4:E369..C4:FD4B`

## Scope

This note records the first clean source-promoted islands inside the ending
cast-scene cluster after the Your Sanctuary corridor.

The surrounding ebsrc include order begins at `C4:E369`:

- `ending/load_cast_scene.asm`
- `ending/set_cast_scroll_threshold.asm`
- `ending/check_cast_scroll_threshold.asm`
- `ending/handle_cast_scrolling.asm`
- `ending/render_cast_name_text.asm`
- cast-name text/tilemap helpers, print wrappers, scene controller, and an
- unused scratch renderer, VWF conversion helper, credits/photo playback
  controller, music table block, and audio helper tail through `C4:FD4B`

The loader span at `C4:E369..C4:E4DA` needs several accumulator-width boundary
hints after byte-sized transfer calls, but with those boundaries pinned it is a
closed byte-equivalent routine. The three scroll helpers after it are also
closed routines and validate byte-for-byte in the C4 scaffold.

## Source Status

The promoted helper islands are:

- `src/c4/cast_scene_loader.asm` covers `C4:E369..C4:E4DA`
- `src/c4/cast_scroll_threshold_helpers.asm` covers `C4:E4DA..C4:E4F9`
- `src/c4/cast_scroll_threshold_check_helpers.asm` covers `C4:E4F9..C4:E51E`
- `src/c4/cast_scrolling_helpers.asm` covers `C4:E51E..C4:E583`
- `src/c4/cast_name_text_renderer.asm` covers `C4:E583..C4:E7AE`
- `src/c4/cast_name_tilemap_prepare_helpers.asm` covers `C4:E7AE..C4:EA9C`
- `src/c4/cast_name_tilemap_copy_helpers.asm` covers `C4:EA9C..C4:EB04`
- `src/c4/cast_name_print_helpers.asm` covers `C4:EB04..C4:EBAD`
- `src/c4/cast_name_party_print_helpers.asm` covers `C4:EBAD..C4:EC05`
- `src/c4/cast_name_entity_var0_print_helpers.asm` covers `C4:EC05..C4:EC52`
- `src/c4/cast_name_current_threshold_print_helpers.asm` covers `C4:EC52..C4:EC6E`
- `src/c4/special_cast_palette_upload_helpers.asm` covers `C4:EC6E..C4:ECAD`
- `src/c4/cast_entity_spawn_position_helpers.asm` covers `C4:ECAD..C4:ECE7`
- `src/c4/cast_entity_onscreen_check_helpers.asm` covers `C4:ECE7..C4:ED0E`
- `src/c4/cast_scene_play_controller.asm` covers `C4:ED0E..C4:EDA3`
- `src/c4/unused_cast_name_scratch_renderer.asm` covers `C4:EDA3..C4:EE9D`
- `src/c4/unused_cast_name_scratch_wrapper.asm` covers `C4:EE9D..C4:EEE1`
- `src/c4/vwf_2bpp_to_three_color_helpers.asm` covers `C4:EEE1..C4:EFC4`
- `src/c4/credits_dma_enqueue_helpers.asm` covers `C4:EFC4..C4:F01D`
- `src/c4/credits_dma_queue_process_helpers.asm` covers `C4:F01D..C4:F07D`
- `src/c4/credits_scene_initializer.asm` covers `C4:F07D..C4:F264`
- `src/c4/credits_photograph_render_helpers.asm` covers `C4:F264..C4:F433`
- `src/c4/credits_photo_flag_counter.asm` covers `C4:F433..C4:F46F`
- `src/c4/credits_photograph_slide_helpers.asm` covers `C4:F46F..C4:F554`
- `src/c4/credits_scene_playback_controller.asm` covers `C4:F554..C4:F70A`
- `src/c4/music_dataset_and_pack_pointer_tables.asm` covers `C4:F70A..C4:FB42`
  as two preserved table spans: `C4:F70A..C4:F947` for
  `MusicDatasetTable` and `C4:F947..C4:FB42` for `MusicPackPointerTable`
- `src/c4/audio_bank_resolver.asm` covers `C4:FB42..C4:FB58`
- `src/c4/music_subsystem_initializer.asm` covers `C4:FB58..C4:FBBD`
- `src/c4/music_change_pack_loader.asm` covers `C4:FBBD..C4:FD18`
- `src/c4/audio_channel_mode_loader.asm` covers `C4:FD18..C4:FD45`
- `src/c4/auto_sector_music_change_latch.asm` covers `C4:FD45..C4:FD4B`

They are included in `src/c4/bank_c4_helpers_asar.asm` and the combined C4
byte-equivalence check currently validates all `85` C4 scaffold modules with
`0` mismatches.

## Main Result

`C4:E369` initializes the cast scene display state. It resets active entity
slots, marks active entity records, loads battle BG preset `0x0117`, clears the
BG3 scroll words at `$0031..$003B`, clears and uploads staging buffers, expands
several `E1`/`C3` asset payloads through `C4:1A9E`, prepares the cast-name
tilemap, refreshes the window-flavor palette, sets `$0030 = 0x18` and
`$001A = 0x14`, clears `$B4CF/$B4D1`, and opens the display transition bracket.

`C4:E4DA` stores a BG3/cast-scroll threshold for the active cast slot. It uses
`$1A42` as the slot index, scales the incoming value by eight, adds the current
scroll position at `$003B`, and writes the result to `$0E5E + slot * 2`.

`C4:E4F9` checks whether the active slot has reached its stored threshold. It
compares `$0E5E + slot * 2` against `$003B` and returns `1` once the threshold
has been met or passed.

`C4:E51E` advances the cast scrolling state and queues a small BG3 VRAM row
transfer. It reads the active slot's scroll position via `$0BCA + slot * 2`,
updates a per-slot position word near `$1002 + slot * 2`, derives a `$7C00`
tilemap destination row, clears a word at `$7FFE`, and calls
`C0:8616`/`QueueVramTransfer_FromDpSource` for a `$40` byte transfer.

`C4:E583` renders cast-name text into the `$3492` scratch rows. It formats a
source name through the C1 file-select text layout helper, resolves glyph
metadata from the `C3:F054` table family, calls `C4:4B3A` to merge glyph runs
into scratch rows, and then copies the staged rows toward the local tilemap
buffer. The short `C4:E796..C4:E7AE` byte table is kept inline with the source
module because the renderer and the following preparation routine both use it
as local cast-name tilemap data.

`C4:E7AE..C4:EBAD` prepares and copies the cast-name tilemap rows, then queues
the row upload used by the ending cast display. The helpers share the
`C4:E796` tilemap patch data and use the C0 local-buffer copy/VRAM transfer
contracts already seen in earlier text/window helpers.

`C4:EBAD..C4:EC6E` are small print wrappers that select the party/current-slot
or entity-var0 source before entering the cast-name print path.

`C4:EC6E..C4:ED0E` covers a special cast palette upload helper and two entity
position/onscreen helpers used by the cast controller.

`C4:ED0E..C4:EDA3` is the promoted `PlayCastScene` controller. It brackets cast
scene loading, transition state, per-frame updates, and final entity cleanup.

`C4:EDA3..C4:EE9D` is ebsrc's following unused cast-name scratch renderer. It
shares the same glyph-run renderer and VRAM queue contracts as the live
cast-name path, but is kept as a separate module because ebsrc gives it a hard
unused include boundary.

`C4:EE9D..C4:EEE1` is the next unused wrapper over the scratch renderer. It
iterates the four `$B4D5` cast-name sources and a final `$B4DD` source before
returning.

`C4:EEE1..C4:EFC4` converts the staged VWF scratch rows from 2bpp into the
three-color format used by the ending/credits display path. The branch joins
need explicit accumulator-width hints during source emission, but the resulting
module validates byte-for-byte.

`C4:EFC4..C4:F07D` is the credits DMA queue pair. `C4:EFC4` appends a queue
record under `$B4F5`; `C4:F01D` drains records from `$B4F3` and calls the C0
VRAM-transfer queue helper.

`C4:F07D..C4:F70A` is the main credits scene block. It initializes the credits
display, checks which photograph flags are set, renders eligible photographs,
slides them while draining the credits DMA queue, and then restores the display
state after the credits presentation.

`C4:F70A..C4:F947` is the ebsrc-named music dataset table.
`C4:F947..C4:FB42` is the music pack pointer table selected by the audio
loader. The scaffold preserves both as data gaps rather than decoding them as
instructions.

`C4:FB42..C4:FD4B` is the compact audio helper tail: audio bank resolution,
music subsystem initialization, music change pack loading, stereo/mono channel
data loading, and the auto-sector music-change latch.

## Working Names

- `C4:E369` = `LoadCastScene`
- `C4:E4DA` = `SetCastScrollThreshold`
- `C4:E4F9` = `CheckCastScrollThreshold`
- `C4:E51E` = `HandleCastScrolling`
- `C4:E583` = `RenderCastNameText`
- `C4:E796` = `CastNameTextTilemapPatchTable`
- `C4:E7AE` = `PrepareCastNameTilemap`
- `C4:EA9C` = `CopyCastNameTilemap`
- `C4:EB04` = `PrintCastName`
- `C4:EBAD` = `PrintCastNameParty`
- `C4:EC05` = `PrintCastNameEntityVar0`
- `C4:EC52` = `PrintCastNameCurrentThreshold`
- `C4:EC6E` = `UploadSpecialCastPalette`
- `C4:ECAD` = `CreateEntityAtV01PlusBg3Y`
- `C4:ECE7` = `IsEntityStillOnCastScreen`
- `C4:ED0E` = `PlayCastScene`
- `C4:EDA3` = `UnusedCastNameScratchRenderer`
- `C4:EE9D` = `RenderUnusedCastNameScratchSet`
- `C4:EEE1` = `ConvertVwf2bppToThreeColor`
- `C4:EFC4` = `EnqueueCreditsDma`
- `C4:F01D` = `ProcessCreditsDmaQueue`
- `C4:F07D` = `InitializeCreditsScene`
- `C4:F264` = `TryRenderingPhotograph`
- `C4:F433` = `CountPhotoFlags`
- `C4:F46F` = `SlideCreditsPhotograph`
- `C4:F554` = `PlayCredits`
- `C4:F70A` = `MusicDatasetTable`
- `C4:F947` = `MusicPackPointerTable`
- `C4:FB42` = `GetAudioBank`
- `C4:FB58` = `InitializeMusicSubsystem`
- `C4:FBBD` = `ChangeMusic`
- `C4:FD18` = `SetAudioChannels`
- `C4:FD45` = `SetAutoSectorMusicChanges`

## Still Open

- The named ebsrc tail is source/data-covered through `C4:FD4B`; bank-end
  padding remains outside the source scaffold.
- Confirm the user-facing meaning of `$003B`, `$0BCA`, `$0E5E`, and the
  `$1002 + slot * 2` cast-scene position word against the wider ending scene.
