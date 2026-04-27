# Map Movement Usage Contract

This reference-derived contract joins map object movement IDs to ebsrc event/actionscript pointers.
It is the behavior-side companion to `notes/map-sprite-usage-contract.md`: the sprite contract
answers what a placed NPC looks like, while this contract answers which event/actionscript payload
drives that object's idle loop, physics callback, task startup, or scripted behavior.

## Summary

- NPC config rows: `1584`
- map placements: `1582`
- event script pointer entries: `895`
- script labels indexed from refs: `971`
- unique movement IDs used by NPC configs: `136`
- unique movement IDs used by placed NPC configs: `135`
- movement IDs resolved to ebsrc script files: `115`
- movement IDs without script-file resolution: `21`
- movement IDs with expected but missing ref script files: `21`
- unique pointer targets used: `136`
- shared pointer targets used: `2`

## Behavior Buckets

| Bucket | Movement IDs |
| --- | ---: |
| `debug_cursor_loop` | 1 |
| `event_actionscript_payload` | 9 |
| `physics_callback_movement` | 16 |
| `script_loop_or_wait` | 61 |
| `task_backed_actionscript` | 28 |
| `unresolved_pointer_target` | 21 |

## Top Movement IDs By Placement Count

| Movement | Target | Bucket | NPC configs | Placements | Top sprites | Source file |
| ---: | --- | --- | ---: | ---: | --- | --- |
| 8 | `EVENT_8` | `physics_callback_movement` | 393 | 393 | SPRITE_GROUP_SIGN (21), OVERWORLD_SPRITE::ATM_MACHINE (20), OVERWORLD_SPRITE::STREET_SIGN (17) | `refs/ebsrc-main/ebsrc-main/src/data/events/scripts/008.asm` |
| 12 | `EVENT_6_12` | `task_backed_actionscript` | 253 | 253 | SPRITE_GROUP_SURFER (11), SPRITE_GROUP_YOUNG_BLONDE_GUY_IN_BLUE (7), SPRITE_GROUP_MR_SATURN (7) | `refs/ebsrc-main/ebsrc-main/src/data/events/scripts/006+012.asm` |
| 606 | `EVENT_606` | `task_backed_actionscript` | 240 | 240 | SPRITE_GROUP_NERDY_REDHEAD (11), SPRITE_GROUP_MR_SATURN (11), SPRITE_GROUP_COP_IN_SUNGLASSES (9) | `refs/ebsrc-main/ebsrc-main/src/data/events/scripts/606.asm` |
| 9 | `EVENT_9` | `physics_callback_movement` | 177 | 177 | OVERWORLD_SPRITE::GIFT_BOX (118), OVERWORLD_SPRITE::TRASH_CAN (25), OVERWORLD_SPRITE::DALAAM_PRESENT (21) | `refs/ebsrc-main/ebsrc-main/src/data/events/scripts/009.asm` |
| 10 | `EVENT_10_11` | `physics_callback_movement` | 144 | 143 | OVERWORLD_SPRITE::MONKEY (24), OVERWORLD_SPRITE::INSANE_CULTIST (13), SPRITE_GROUP_MR_SATURN (6) | `refs/ebsrc-main/ebsrc-main/src/data/events/scripts/010+011.asm` |
| 605 | `EVENT_605` | `task_backed_actionscript` | 108 | 108 | OVERWORLD_SPRITE::DOCTOR (7), OVERWORLD_SPRITE::NURSE (6), SPRITE_GROUP_SORTA_BALD_GUY_IN_SUIT (5) | `refs/ebsrc-main/ebsrc-main/src/data/events/scripts/605.asm` |
| 13 | `EVENT_13` | `script_loop_or_wait` | 41 | 41 | SPRITE_GROUP_MR_SATURN (4), SPRITE_GROUP_CAT (3), OVERWORLD_SPRITE::MONKEY (3) | `refs/ebsrc-main/ebsrc-main/src/data/events/scripts/013.asm` |
| 599 | `EVENT_599` | `script_loop_or_wait` | 27 | 27 | OVERWORLD_SPRITE::GUARDIAN_HIEROGLYPH (15), OVERWORLD_SPRITE::LETHAL_ASP_HIEROGLYPH (9), OVERWORLD_SPRITE::PETRIFIED_ROYAL_GUARD (2) | `refs/ebsrc-main/ebsrc-main/src/data/events/scripts/599.asm` |
| 16 | `EVENT_16` | `script_loop_or_wait` | 11 | 11 | OVERWORLD_SPRITE::YELLOW_CLOTHES_BLONDE (2), SPRITE_GROUP_YOUNG_BLONDE_GUY_IN_BLUE (1), SPRITE_GROUP_MR_T (1) | `refs/ebsrc-main/ebsrc-main/src/data/events/scripts/016.asm` |
| 600 | `EVENT_600` | `task_backed_actionscript` | 10 | 10 | OVERWORLD_SPRITE::GUARDIAN_DIGGER (5), SPRITE_GROUP_SLIMY_PILE (3), OVERWORLD_SPRITE::ROWDY_MOUSE (2) | `refs/ebsrc-main/ebsrc-main/src/data/events/scripts/600.asm` |
| 693 | `EVENT_693` | `physics_callback_movement` | 10 | 10 | SPRITE_GROUP_YOUR_SANCTUARY_BOSS (8), SPRITE_GROUP_SPRING (1), SPRITE_GROUP_FLAME (1) | `refs/ebsrc-main/ebsrc-main/src/data/events/scripts/693.asm` |
| 602 | `EVENT_602` | `task_backed_actionscript` | 9 | 9 | OVERWORLD_SPRITE::SENTRY_ROBOT (5), SPRITE_GROUP_KRAKEN (3), SPRITE_GROUP_CLUMSY_ROBOT (1) | `refs/ebsrc-main/ebsrc-main/src/data/events/scripts/602.asm` |
| 769 | `EVENT_769` | `task_backed_actionscript` | 7 | 7 | OVERWORLD_SPRITE::UNDERWATER_NPC (7) | `refs/ebsrc-main/ebsrc-main/src/data/events/scripts/769.asm` |
| 607 | `EVENT_607` | `script_loop_or_wait` | 6 | 6 | OVERWORLD_SPRITE::SCUZZY_GUY (1), OVERWORLD_SPRITE::YELLOW_CLOTHES_BLONDE (1), OVERWORLD_SPRITE::I_LOVE_QOWGA_SHIRT_GUY (1) | `refs/ebsrc-main/ebsrc-main/src/data/events/scripts/607.asm` |
| 80 | `EVENT_80` | `event_actionscript_payload` | 5 | 5 | OVERWORLD_SPRITE::URBAN_ZOMBIE (2), OVERWORLD_SPRITE::ZOMBIE_POSSESSOR (2), SPRITE_GROUP_ZOMBIE_LADY (1) | `refs/ebsrc-main/ebsrc-main/src/data/events/scripts/080.asm` |
| 784 | `EVENT_784` | `task_backed_actionscript` | 5 | 5 | OVERWORLD_SPRITE::OVAL_CLOUD (5) | `refs/ebsrc-main/ebsrc-main/src/data/events/scripts/784.asm` |
| 598 | `EVENT_598` | `task_backed_actionscript` | 4 | 4 | OVERWORLD_SPRITE::SKATE_PUNK (2), OVERWORLD_SPRITE::MAD_DUCK (2) | `refs/ebsrc-main/ebsrc-main/src/data/events/scripts/598.asm` |
| 608 | `EVENT_608` | `script_loop_or_wait` | 4 | 4 | SPRITE_GROUP_TRAVELLING_ENTERTAINER (2), OVERWORLD_SPRITE::SCUZZY_GUY (1), SPRITE_GROUP_DOG (1) | `refs/ebsrc-main/ebsrc-main/src/data/events/scripts/608.asm` |
| 609 | `EVENT_609` | `script_loop_or_wait` | 4 | 4 | SPRITE_GROUP_DARK_HAIRED_GUY_IN_SUIT (1), OVERWORLD_SPRITE::BLONDE_GUY_IN_BLUE_SUIT (1), SPRITE_GROUP_BLONDE_SHOPPING_LADY (1) | `refs/ebsrc-main/ebsrc-main/src/data/events/scripts/609.asm` |
| 7 | `EVENT_7` | `physics_callback_movement` | 3 | 3 | OVERWORLD_SPRITE::INVISIBLE_2 (1), OVERWORLD_SPRITE::DONT_ENTER_SIGN (1), OVERWORLD_SPRITE::SECRET_DOOR_IN_MONOTOLI_BUILDING (1) | `refs/ebsrc-main/ebsrc-main/src/data/events/scripts/007.asm` |

## Shared Pointer Targets

Some movement IDs deliberately point at the same script label. These are aliases in the
NPC config movement field, not duplicate script bodies.

| Target | Movement IDs |
| --- | --- |
| `EVENT_10_11` | `10, 11` |
| `EVENT_6_12` | `6, 12` |

## Unresolved Movement IDs

These movement IDs are used by NPC configs but did not resolve to a script file label in refs.

`870`, `871`, `872`, `873`, `875`, `876`, `877`, `878`, `879`, `880`, `881`, `882`, `883`, `884`, `885`, `886`, `887`, `888`, `889`, `890`, `891`

## Machine-Readable Data

The JSON contract records one row per used movement ID with target label, source file, behavior
bucket, NPC/map placement counts, top sprites, event macro profile, referenced C3 labels, and
example NPC config IDs.

- JSON: `notes/map-movement-usage-contract.json`
- generator: `tools/build_map_movement_usage_contract.py`
