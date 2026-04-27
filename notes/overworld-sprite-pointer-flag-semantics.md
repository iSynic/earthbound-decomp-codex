# Overworld Sprite Pointer Flag Semantics

This note captures the current local read of the low bits in the `spritepointerarray` words inside the EF sprite grouping records.

The frame contract now resolves every runtime slot to a D1-D5 sprite payload by masking the low two bits of each pointer word. Those low bits are not disposable alignment noise: C0-side consumers preserve the raw word in `$341A` and branch on its low bits before building renderer/DMA records.

## Evidence

- `C0:A4C4` and `C0:A794` both load the selected frame word from the cached `2A06/29CA` descriptor stream and test `AND #$0002`.
- When bit 1 is set, both paths skip the optional fixed-source auxiliary pass rooted at `C4:0BE8` and continue to the main D1-D5 sprite payload stream.
- `C0:A3A4` later reads cached `$341A`, tests `AND #$0001`, and if set adds `$2916` to the display-record base pointer in `$8C` before queue submission.
- The selected word is also masked for source addressing before DMA descriptor generation, so the renderer consumes the aligned payload offset and the low-bit behavior separately.

## Current Names

| Bit | Name | Confidence | Meaning |
| ---: | --- | --- | --- |
| 0 | `display_record_base_bias` | medium | Adds the per-visual-profile `$2916` span to the display-record base pointer before the renderer queue path. The exact visual term still needs a friendlier name. |
| 1 | `suppress_auxiliary_c40be8_prepass` | high | Skips the optional `C4:0BE8` auxiliary render/DMA prepass and uses only the main D1-D5 payload stream for that slot. |

## Contract Counts

The generated frame contract currently reports:

- flag value `0`: `1769` slots
- flag value `1`: `653` slots
- flag value `2`: `12` slots
- flag value `3`: `4` slots

Interpreted as bit effects:

- `display_record_base_bias`: `657` slots
- `suppress_auxiliary_c40be8_prepass`: `16` slots

## Boundaries

These names describe observed renderer behavior, not yet final art-facing terminology. Bit 0 may eventually deserve a name like an alternate spritemap/body-half selector once the `$2916` display-record span is tied to the visual record structure. Bit 1 is much firmer because both relevant refresh paths branch directly on it before the auxiliary `C4:0BE8` pass.

## Preview Tool

`tools/build_overworld_sprite_preview_sheets.py` now consumes `notes/overworld-sprite-frame-contracts.json` and generated palette-00 tile previews to produce ignored slot contact sheets under `build/overworld-sprite-preview-sheets/`.

Those sheets apply the flag effects as metadata and colored cell borders first. They are not final in-game OAM composition yet; they are a visual QA layer over the exact slot-to-payload mapping.

## Next Step

Move from slot contact sheets toward in-game composed sprite/OAM previews once the display-record layout tied to `$2916`, `$341A`, and the secondary visual descriptor records is fully pinned.
