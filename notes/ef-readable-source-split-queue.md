# EF Readable Source Split Queue

This note translates the EF first-pass map into the next readable source-bank
closure queue.

The immediate problem is measurable now: `notes/readable-source-bank-closure.md`
shows `EF` as the dominant preserved-corridor debt, with `EF:0000..EF:EB5F`
still emitted as one coarse `db` corridor. That is byte-safe, but it is not
readable source.

## Current Boundary

- Structural scaffold: closed and byte-equivalent.
- Readable source closure: open.
- Main debt: `EF:0000..EF:EB5F`, `60255` bytes.
- Secondary debts: `EF:EF70..EF:EFB7`, `71` bytes, and the late named tail
  `EF:F0D7..EF:FFFF`, already noted as blocked by missing includes in the asset
  map.

## Source Order From Refs

The strongest global guide is still:

- `refs/ebsrc-main/ebsrc-main/src/bankconfig/US/bank2f.asm`
- `notes/bank-ef-first-pass.md`
- `notes/bank-ef-reference-frontier.md`
- `notes/bank-ef-asset-data-map.md`

Those refs do not give us every local file body, but they do give source order,
include names, and many encoded address anchors. That is enough to split the
coarse corridor into safer lanes.

## Split Lanes

| Lane | Range | Current Read | Closure Type | Best Evidence |
| --- | --- | --- | --- | --- |
| EF front helpers | `EF:0000..EF:05A5` | Enemy flashing, audio pause/resume, early unknown helpers, SRAM signature setup. | decoded source plus small data | `bank2f.asm`, C1/C2 local mentions |
| Save/SRAM family | `EF:05A6..EF:0C3C` | Save block/slot erase, copy, checksum, integrity, load/save helpers. | decoded source | named `system/saves/*` includes |
| Delivery/selector helpers | `EF:0C3D..EF:101A` | Timed-delivery/service row helpers around `D5:F645`, plus adjacent unknown helpers. | decoded source first | `notes/delivery-row-helpers-ef0e67-ef0ead.md`, `notes/selector-row-config-family-ef0ee8.md` |
| Map tables | `EF:101B..EF:4A3F` | Tileset table, graphics/arrangement/palette/collision/animation pointer tables, animation properties, sprite grouping pointers/data. | typed data contracts | map milestone contracts, EF sprite grouping pointer table users |
| Sound Stone data | `EF:4A40..EF:4E1F` | Sound Stone presentation data. | typed data/asset | `C4:AC57` pointer table anchors |
| Text run | `EF:4E20..EF:C51A` | PSI help, battle text, goods text, command/status text, keyboard/name input, unknown text, town-map data. | text/script asset split | D5 PSI pointers, C1 text/menu consumers |
| Glyph masks | `EF:C51B..EF:D56E` | Text-token glyph merge mask and carry-mask regions. | typed data contracts | `C4:4B3A` consumers |
| Debug/menu source | `EF:D56F..EF:EB5E` | Debug strings, debug overlay helpers, cursor/menu processing, and remaining unknown routines. | decoded source plus data | `notes/debug-menu-reachability-c0-c1-ef.md`, `bank2f.asm` |
| Exact debug graphics | `EF:EB5F..EF:EF6F`, `EF:EFB7..EF:F0D6` | Debug font and cursor graphics. | already exact assets | `asset-manifests/ef-debug-assets.json` |
| Late tail | `EF:F0D7..EF:FFFF` | Named unknown/version/unused/debug cursor spritemap tail. | typed data split | `bank2f.asm`, asset map gap |

## First Practical Promotion Target

The best first readable-source promotion seam is:

```text
EF:0CA7..EF:0FF6
```

Why this one first:

- It is executable helper code, not text or opaque asset data.
- Existing notes already explain most of the semantics.
- It connects to a typed D5 table contract (`D5:F645`) instead of relying only
  on local instruction shape.
- It should be small enough to split out of the coarse EF corridor without
  redesigning the whole EF scaffold at once.

Expected source-facing labels:

- `EF:0CA7` delivery retry threshold helper
- `EF:0D23` current-row retry wait getter
- `EF:0D46` seed current-row delivery countdown
- `EF:0D73` decrement current-row delivery countdown
- `EF:0D8D` queue current-row pointer 1
- `EF:0DFA` queue current-row pointer 2
- `EF:0E67` current-row enter-speed getter
- `EF:0E8A` current-row exit-speed getter
- `EF:0EAD` instantiate delivery row sprite/placeholder
- `EF:0EE8` scan delivery/service rows by event flag

## Second Practical Target

After that, split `EF:101B..EF:4A3F` as typed data, not source. This will not
make EF "more decoded asm," but it will remove a large amount of false source
debt from the preserved corridor by reclassifying map tables and sprite grouping
tables into explicit data contracts.

## Success Criteria

The next EF readable-source pass should:

1. split one EF lane out of `src/ef/table_002_unknown_ef_ef00bb_asm.asm`
2. preserve byte equivalence with `validate_source_bank_byte_equivalence.py`
3. rerun `tools/build_readable_source_bank_closure.py`
4. reduce EF preserved-corridor bytes or move known data into the
   `known data/assets` bucket
5. leave the unresolved text and debug lanes documented rather than hidden

That gives us a clean loop: source split, validate, rerun the closure dashboard,
then choose the next lane by measured remaining debt.
