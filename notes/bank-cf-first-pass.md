# Bank CF First Pass

## Main result

Bank `CF` is a generated map-data bank with a small audio tail. It is not code
and not a normal binary-asset bank like `CA` through `CE`.
The follow-up CF splitter now resolves the generated map-data region into exact
source-order spans.

Follow-up source-scaffold status:

- durable scaffold: `src/cf/bank_cf_helpers_asar.asm`
- manifest: `build/cf-build-candidate-ranges.json`
- handoff: `notes/bank-cf-source-scaffold-handoff.md`
- protected bytes: `65536 / 65536`
- residual bytes: `0`
- modules: `11`
- byte-equivalence: `OK`, `0` mismatches

Primary artifacts:

- `notes/bank-cf-asset-data-map.md`
- `notes/cf-table-splits.md`
- `build/asset-bank-cf.json`
- `build/cf-table-splits.json`

The generated map accounts for:

- binary assets: `2`
- binary asset bytes: `3396`
- table/generator region bytes: `62133`
- exact generated-data split bytes: `62133`
- coverage gap bytes: `7`
- missing payload metadata: `0`

## Bank layout

The high-level CF layout is:

- `CF:0000..CF:F2B4`: generated map-data region, `62133` bytes.
- `CF:F2B5..CF:FF37`: `AUDIO_PACK_94`, `3203` bytes.
- `CF:FF38..CF:FFF8`: `AUDIO_PACK_96`, `193` bytes.
- `CF:FFF9..CF:FFFF`: `7` bytes of tail slack.

The checked-in bank config names the generated map-data sources in order:

- `data/map/door_data.asm`
- `data/map/door_config_table.asm`
- `data/map/overworld_event_music_pointer_table.asm`
- `data/map/overworld_event_music_table.asm`
- an inline ten-byte block
- `data/map/sprite_placement_pointer_table.asm`
- `data/map/sprite_placement_table.asm`
- `data/map/npc_config.asm`

Those files are referenced by `refs/ebsrc-main/ebsrc-main/src/bankconfig/common/bank0f.asm`,
but the actual generated source files are not present under the checked-in
`refs/ebsrc-main/ebsrc-main/src/data` tree. The dedicated splitter recovers
their exact byte ranges from D0 cross-bank door pointers, eb-decompile YAML
shapes, ebsrc struct sizes, the inline byte block, and ROM byte checks.

The exact split is:

- `CF:0000..CF:264E`: `DOOR_DATA`, `9807` bytes.
- `CF:264F..CF:58EE`: `DOOR_CONFIG_TABLE`, 1280 counted sector lists.
- `CF:58EF..CF:5A38`: `OVERWORLD_EVENT_MUSIC_POINTER_TABLE`, 165 word pointers.
- `CF:5A39..CF:61DC`: `OVERWORLD_EVENT_MUSIC_TABLE`, `1956` bytes.
- `CF:61DD..CF:61E6`: inline ten-byte event-music trailer.
- `CF:61E7..CF:6BE6`: `SPRITE_PLACEMENT_POINTER_TABLE`, 1280 word pointers.
- `CF:6BE7..CF:8984`: `SPRITE_PLACEMENT_TABLE`, 627 non-empty counted lists.
- `CF:8985..CF:F2B4`: `NPC_CONFIG_TABLE`, 1584 fixed `0x11`-byte rows.

## Tooling behavior

`tools/build_asset_bank_manifest.py` now skips `config.asm` includes and records
later absent generated includes as covered by the prior inferred generated table
block. This prevents bogus overlapping table spans when a generated region
contains multiple absent source includes before the next known binary asset.

## Current CF confidence boundary

High confidence:

- CF is data/audio, not executable code.
- The generated map-data block runs from `CF:0000` through `CF:F2B4`.
- The internal generated-data spans are exact in `notes/cf-table-splits.md`.
- The audio tail contains US retail `AUDIO_PACK_94` and `AUDIO_PACK_96`.
- Only `CF:FFF9..CF:FFFF` remains unclaimed tail slack.

Still intentionally out of scope:

- Subrecord semantics for `DOOR_DATA`, `DOOR_CONFIG_TABLE`,
  `OVERWORLD_EVENT_MUSIC_TABLE`, and `SPRITE_PLACEMENT_TABLE` remain variable
  list formats rather than fully expanded row contracts.
- Audio-pack internals remain opaque.

## Recommended next move

Treat CF as structurally complete and byte-protected for the current
bank-coverage phase. Continue the D0 splitter. CF now supplies the D0
door-pointer target contract, and the same pointer/list strategy should apply
to D0's enemy placement and battle-entry families.
