from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from lookup_wram_field import FieldSpec, ROOTS


SCHEMA = "earthbound-decomp.data-contracts.v1"


@dataclass(frozen=True)
class Contract:
    id: str
    domain: str
    address: str
    stride: int
    count: int | None
    struct_name: str
    confidence: str
    note: str
    evidence: tuple[str, ...]
    fields: tuple[FieldSpec, ...]


def field(
    name: str,
    offset: int,
    size: int,
    count: int = 1,
    note: str = "",
    element_names: tuple[str, ...] = (),
) -> FieldSpec:
    return FieldSpec(name, offset, size, count, note, element_names)


BATTLE_ACTION_FIELDS = (
    field("direction", 0x00, 1, note="enemy/ally/immediate direction selector"),
    field("target", 0x01, 1, note="target subtype consumed by the C1 targetting resolver"),
    field("type", 0x02, 1, note="battle action type"),
    field("pp_cost", 0x03, 1, note="PSI/action PP cost; CoilSnake `battle-action-pp-cost-probe` is runtime-correlated to the C1:CC39 battle PSI PP guard"),
    field("description_text_pointer", 0x04, 4, note="battle text pointer"),
    field("battle_function_pointer", 0x08, 4, note="battle action handler pointer"),
)

ITEM_FIELDS = (
    field("name", 0x00, 1, 25, "USA item-name buffer"),
    field("packed_class_and_slot", 0x19, 1, note="item type byte; local notes decode class/equipment slot packing"),
    field("cost", 0x1A, 2, note="store cost; CoilSnake `item-cost-probe` is runtime-correlated to the shop item row builder"),
    field("flags", 0x1C, 1, note="item flags"),
    field("effect", 0x1D, 2, note="item effect id"),
    field("params", 0x1F, 4, note="item parameter dword"),
    field("help_text", 0x23, 4, note="help text pointer"),
)

ENEMY_FIELDS = (
    field("the_flag", 0x00, 1),
    field("name", 0x01, 1, 25, "USA enemy-name buffer"),
    field("gender", 0x1A, 1),
    field("type", 0x1B, 1),
    field("battle_sprite", 0x1C, 2),
    field("overworld_sprite", 0x1E, 2),
    field("run_flag", 0x20, 1),
    field("hp", 0x21, 2),
    field("pp", 0x23, 2),
    field("exp", 0x25, 4),
    field("money", 0x29, 2),
    field("event_script", 0x2B, 2),
    field("encounter_text_ptr", 0x2D, 4),
    field("death_text_ptr", 0x31, 4),
    field("battle_sprite_palette", 0x35, 1),
    field("level", 0x36, 1),
    field("music", 0x37, 1),
    field("offense", 0x38, 2),
    field("defense", 0x3A, 2),
    field("speed", 0x3C, 1),
    field("guts", 0x3D, 1),
    field("luck", 0x3E, 1),
    field("fire_vulnerability", 0x3F, 1),
    field("freeze_vulnerability", 0x40, 1),
    field("flash_vulnerability", 0x41, 1),
    field("paralysis_vulnerability", 0x42, 1),
    field("hypnosis_brainshock_vulnerability", 0x43, 1),
    field("miss_rate", 0x44, 1),
    field("action_order", 0x45, 1),
    field("actions", 0x46, 2, 4, "normal action ids; CoilSnake `enemy-insane-cultist-action1-probe` is runtime-correlated to the C2:5024 enemy action-slot staging path"),
    field("final_action", 0x4E, 2),
    field("action_args", 0x50, 1, 4, "arguments for normal actions"),
    field("final_action_arg", 0x54, 1),
    field("iq", 0x55, 1),
    field("boss", 0x56, 1),
    field("item_drop_rate", 0x57, 1, note="locally still softer than the core 0x5E enemy record match"),
    field("item_dropped", 0x58, 1, note="locally still softer than the core 0x5E enemy record match"),
    field("initial_status", 0x59, 1),
    field("death_type", 0x5A, 1),
    field("row", 0x5B, 1),
    field("max_called", 0x5C, 1),
    field("mirror_success", 0x5D, 1),
)

PSI_ABILITY_FIELDS = (
    field("name", 0x00, 1, note="PSI name id"),
    field("level", 0x01, 1, note="PSI alpha/beta/gamma/omega level"),
    field("category", 0x02, 1),
    field("usability", 0x03, 1, note="menu/use gating byte"),
    field("battle_action", 0x04, 2, note="linked D5:7B68 battle action id"),
    field("ness_level", 0x06, 1),
    field("paula_level", 0x07, 1),
    field("poo_level", 0x08, 1),
    field("menu_x", 0x09, 1),
    field("menu_y", 0x0A, 1),
    field("text", 0x0B, 4, note="description text pointer"),
)

STORE_INVENTORY_FIELDS = tuple(
    field(f"item_id_{index}", index, 1)
    for index in range(7)
)

PSI_TELEPORT_DESTINATION_FIELDS = (
    field("name", 0x00, 1, 25, "fixed-width USA destination name"),
    field("event_flag", 0x19, 2),
    field("x", 0x1B, 2),
    field("y", 0x1D, 2),
)

TELEPHONE_CONTACT_FIELDS = (
    field("name", 0x00, 1, 25, "fixed-width USA phone contact name"),
    field("event_flag", 0x19, 2),
    field("text_pointer", 0x1B, 4),
)

PSI_NAME_FIELDS = (field("name", 0x00, 1, 25, "fixed-width USA PSI name"),)

BYTE_VALUE_FIELD = (field("value", 0x00, 1),)

EXP_CURVE_FIELDS = (
    field("level_1_to_100_exp", 0x00, 4, 100, "little-endian EXP thresholds"),
)

STATS_GROWTH_VAR_FIELDS = (
    field("offense", 0x00, 1),
    field("defense", 0x01, 1),
    field("speed", 0x02, 1),
    field("guts", 0x03, 1),
    field("vitality", 0x04, 1),
    field("iq", 0x05, 1),
    field("luck", 0x06, 1),
)

CONDIMENT_FIELDS = (
    field("food", 0x00, 1),
    field("condiment_1", 0x01, 1),
    field("condiment_2", 0x02, 1),
    field("effect", 0x03, 1),
    field("good_recover", 0x04, 1),
    field("bad_recover", 0x05, 1),
    field("run_time", 0x06, 1),
)

TELEPORT_DESTINATION_FIELDS = (
    field("x", 0x00, 2),
    field("y", 0x02, 2),
    field("direction", 0x04, 1),
    field("warp_style", 0x05, 1),
    field("unknown", 0x06, 1),
    field("reserved", 0x07, 1),
)

MAP_HOTSPOT_FIELDS = (
    field("x1", 0x00, 2),
    field("y1", 0x02, 2),
    field("x2", 0x04, 2),
    field("y2", 0x06, 2),
)

TIMED_ITEM_TRANSFORMATION_FIELDS = (
    field("item_id", 0x00, 1),
    field("sound_effect", 0x01, 1),
    field("sound_frequency", 0x02, 1),
    field("new_item", 0x03, 1),
    field("delay", 0x04, 1),
)

DONT_CARE_NAME_FIELDS = tuple(
    field(f"name_{index + 1}", index * 6, 1, 6, "fixed-width USA name")
    for index in range(7)
)

INITIAL_STATS_FIELDS = (
    field("unknown", 0x00, 1, 4),
    field("money", 0x04, 2),
    field("level", 0x06, 1),
    field("experience_points", 0x07, 4),
    field("items_possessed", 0x0B, 1, 10),
)

TIMED_DELIVERY_FIELDS = (
    field(
        "source_window_bytes",
        0x00,
        1,
        0x14,
        "20-byte source-order window beginning at D5:F649; this starts at +0x04 into effective controller row 0, so use TIMED_DELIVERY_CONTROLLER_TABLE for row-aligned fields",
    ),
)

TIMED_DELIVERY_CONTROLLER_FIELDS = (
    field("sprite_object_descriptor", 0x00, 2, note="record word 0; EF:0EAD/EF:0EE8 pass this descriptor to C0:1E49, with a placeholder fallback when zero"),
    field("event_flag_gate", 0x02, 2, note="record word 1; EF:0EE8 tests this through C2:1628 before selecting the row"),
    field("retry_threshold", 0x04, 2, note="record word 2; EF:0CA7 compares the row-local retry counter against this threshold, with 0xFFFF supported as an immediate-success sentinel"),
    field("retry_wait_seconds", 0x06, 2, note="record word 3; EF:0D23 returns this to the 499+500_common one-second retry loop"),
    field("delivery_time", 0x08, 2, note="record word 4; EF:0D46 seeds the row-local countdown from this field"),
    field("success_pointer_low_word", 0x0A, 2, note="low word of pointer 1; EF:0D8D queues this as staged queue type 0x0008"),
    field("success_pointer_bank", 0x0C, 1, note="bank byte of pointer 1"),
    field("failure_pointer_low_word", 0x0D, 2, note="low word of pointer 2; EF:0DFA queues this as staged queue type 0x000A"),
    field("failure_pointer_bank", 0x0F, 1, note="bank byte of pointer 2"),
    field("enter_speed", 0x10, 2, note="record word 8; EF:0E67 returns this for the arrival-side movement branch"),
    field("exit_speed", 0x12, 2, note="record word 9; EF:0E8A returns this for the departure-side movement branch"),
)

RAW_CF_DOOR_DATA_FIELDS = (
    field(
        "raw_payload",
        0x00,
        1,
        0x264F,
        "exact CF door-data payload block; see notes/cf-door-data-contracts.json for consumer-backed type 0 event-gated script pointers, type 2 door-transition records, and type 6 cached interaction pointers",
    ),
)

RAW_CF_DOOR_CONFIG_LIST_FIELDS = (
    field(
        "counted_door_sector_lists",
        0x00,
        1,
        0x32A0,
        "1280 D0-pointer-addressed counted sector door/trigger lists; see notes/cf-sector-list-contracts.json for complete decoded lists and notes/cf-movement-trigger-contracts.json for trigger_payload_word meanings by movement_trigger_type",
    ),
)

D0_DOOR_POINTER_FIELDS = (
    field("door_sector_list_pointer_low_word", 0x00, 2, note="low word of a CF door sector-list start inside CF:264F..CF:58EE"),
    field("door_sector_list_pointer_bank", 0x02, 1, note="bank byte; validated as CF for all 1280 rows"),
    field("reserved", 0x03, 1, note="zero pad byte in the four-byte long-pointer row"),
)

FAR_POINTER_FIELDS = (
    field("pointer", 0x00, 4),
)

WORD_POINTER_FIELDS = (
    field("pointer", 0x00, 2),
)

RAW_CF_EVENT_MUSIC_TABLE_FIELDS = (
    field(
        "raw_event_music_context_rows",
        0x00,
        1,
        0x07A4,
        "164 CF selector-addressed variable chains; see notes/cf-event-music-context-contracts.json for decoded event-flag condition/default rows and music/SFX bytes",
    ),
)

RAW_CF_INLINE_EVENT_MUSIC_TRAILER_FIELDS = (
    field("byte", 0x00, 1, 10, "inline bank0f byte block"),
)

RAW_CF_SPRITE_PLACEMENT_LIST_FIELDS = (
    field(
        "counted_sprite_placement_sector_lists",
        0x00,
        1,
        0x1D9E,
        "627 counted sprite-placement sector lists; see notes/cf-sector-list-contracts.json for complete decoded lists and npc_config_id/sector_local_y/sector_local_x entries",
    ),
)

SPRITE_PLACEMENT_POINTER_FIELDS = (
    field(
        "sprite_placement_list_offset",
        0x00,
        2,
        note="zero means empty sector; nonzero is a CPU low word into CF:6BE7..CF:8984",
    ),
)

NPC_CONFIG_FIELDS = (
    field("type", 0x00, 1),
    field("sprite", 0x01, 2),
    field("direction", 0x03, 1),
    field("event_script", 0x04, 2),
    field("event_flag", 0x06, 2),
    field("appearance_style", 0x08, 1),
    field("text_pointer", 0x09, 4),
    field("secondary_payload", 0x0D, 4, note="union: item byte or second text pointer depending on NPC type"),
)

SCREEN_TRANSITION_CONFIG_FIELDS = (
    field("duration", 0x00, 1),
    field("animation_id", 0x01, 1),
    field("animation_flags", 0x02, 1),
    field("fade_style", 0x03, 1),
    field("direction", 0x04, 1),
    field("unknown5", 0x05, 1),
    field("slide_speed", 0x06, 1),
    field("start_sound_effect", 0x07, 1),
    field("secondary_duration", 0x08, 1),
    field("secondary_animation_id", 0x09, 1),
    field("secondary_animation_flags", 0x0A, 1),
    field("ending_sound_effect", 0x0B, 1),
)

RAW_D0_TILE_EVENT_CONTROL_FIELDS = (
    field(
        "raw_event_chains",
        0x00,
        1,
        0x02C0,
        "20 variable MAP_TILE_EVENT chains; see notes/d0-tile-event-contracts.json for decoded event-condition headers and replacement pairs",
    ),
)

MAP_ENEMY_PLACEMENT_FIELDS = (
    field("enemy_map_group", 0x00, 2),
)

RAW_D0_ENEMY_PLACEMENT_GROUP_FIELDS = (
    field(
        "raw_group_lists",
        0x00,
        1,
        0x0A61,
        "203 variable enemy placement group lists; see notes/d0-variable-list-contracts.json for decoded headers and weighted entries",
    ),
)

BATTLE_ENTRY_POINTER_FIELDS = (
    field("enemy_list_pointer", 0x00, 4, note="long pointer to a D0:D52D enemy battle-group list"),
    field("run_away_flag", 0x04, 2),
    field("run_away_flag_state", 0x06, 1),
    field("presentation_sprite_style", 0x07, 1, note="C2 battle presentation paths pass this byte as Y to C2:D121 LoadPresentationSpriteResource"),
)

RAW_D0_BATTLE_GROUP_FIELDS = (
    field(
        "raw_battle_groups",
        0x00,
        1,
        0x0A87,
        "consumer-visible battle group pointer slices; see notes/d0-variable-list-contracts.json for repeat-count enemy entries",
    ),
)

RAW_D8_COLLISION_DATA_FIELDS = (
    field("raw_collision_data", 0x00, 1, 0x8F50, "raw tile collision data addressed by the D8 collision pointer tables"),
)

D8_SURFACE_COLLISION_FLAGS_NOTE = (
    "surface/collision flags for one 4x4 metatile cell; D8 pointer tables expand "
    "these records into the .fts collision grid, and C0 runtime masks define "
    "0x80 as observed high collision, 0x10 as special-surface coordinate latch, "
    "0x04/0x08 as entity terrain-compatibility class, and 0x01/0x02 as preserved "
    "low surface modifiers with provisional gameplay labels"
)

MAP_TILE_COLLISION_ROW_FIELDS = tuple(
    field(
        f"cell_r{row}_c{column}_surface_collision_flags",
        row * 4 + column,
        1,
        note=D8_SURFACE_COLLISION_FLAGS_NOTE,
    )
    for row in range(4)
    for column in range(4)
)

D8_COLLISION_RECORD_OFFSET_FIELDS = (
    field(
        "collision_record_offset",
        0x00,
        2,
        note="16-byte-aligned offset into D8:0000 MAP_TILE_COLLISION_DATA; 0x0000 is a real collision record, not a null pointer",
    ),
)

D7_SECTOR_TILESET_PALETTE_FIELDS = (
    field(
        "packed_tileset_palette",
        0x00,
        1,
        note="bits 3..7 are tileset_id and bits 0..2 are palette_variant; exact join to map-sector metadata and D7A800 consumers",
    ),
)

D7_SECTOR_CONTEXT_WORD_FIELDS = (
    field(
        "sector_context_word",
        0x00,
        2,
        note="per-sector context word loaded by C0:0AA1 into $438E; low three bits match map-sector Setting and are consumed by the C0:2668 spawn candidate resolver",
    ),
)

SNES_LONG_POINTER24_FIELDS = (
    field("target_low_word", 0x00, 2),
    field("target_bank", 0x02, 1),
)

PER_SECTOR_MUSIC_FIELDS = (
    field("music_options_index", 0x00, 2, note="40x32 sector-indexed word joined to map_music.yml option lists by the map sector bundle contract"),
)

CURRENT_POSITION_EVENT_MUSIC_SELECTOR_FIELDS = (
    field(
        "event_music_context_selector",
        0x00,
        1,
        note="byte-indexed first plane at DC:D637; C0:68F4 and the EF debug overlay use this selector to index CF:58EF",
    ),
)

TEXT_WINDOW_FLAVOR_SELECTOR_FIELDS = (
    field("palette_block_offset", 0x00, 2, note="offset from E0:1FC8 selected by C4:7F87/C1:9D49 for the current text-window flavour"),
    field("selector_aux_byte", 0x02, 1, note="third selector byte preserved by the checked E0 window-skin contract"),
)

WINDOW_PALETTE_BLOCK_FIELDS = tuple(
    field(
        f"palette_row_{index}",
        index * 8,
        2,
        4,
        "four SNES BGR555 colours copied as part of a 0x40-byte text-window palette block",
    )
    for index in range(8)
)

PALETTE_ROW_4_FIELDS = (
    field("colour_0", 0x00, 2),
    field("colour_1", 0x02, 2),
    field("colour_2", 0x04, 2),
    field("colour_3", 0x06, 2),
)

DA_MAP_PALETTE_VARIANT_FIELDS = (
    field(
        "event_flag",
        0x00,
        2,
        note="raw ROM metadata word matching map_palette_settings; zeroed in .fts visual palette rows",
    ),
    field(
        "map_subpalette_0_colours",
        0x00,
        2,
        16,
        "16 SNES BGR555 colours for arrangement descriptor palette 2 / CGRAM $0240..$025F; colour 0 overlaps event_flag in raw ROM",
    ),
    field(
        "event_palette_selector_word",
        0x20,
        2,
        note="raw ROM metadata word whose presence matches event-palette payload settings; runtime dispatch semantics remain deferred",
    ),
    field(
        "map_subpalette_1_colours",
        0x20,
        2,
        16,
        "16 SNES BGR555 colours for arrangement descriptor palette 3 / CGRAM $0260..$027F; colour 0 overlaps event_palette_selector_word in raw ROM",
    ),
    field(
        "sprite_palette",
        0x40,
        2,
        note="raw ROM metadata word matching map_palette_settings Sprite Palette; zeroed in .fts visual palette rows",
    ),
    field(
        "map_subpalette_2_colours",
        0x40,
        2,
        16,
        "16 SNES BGR555 colours for arrangement descriptor palette 4 / CGRAM $0280..$029F; colour 0 overlaps sprite_palette in raw ROM",
    ),
    field(
        "flash_effect",
        0x60,
        2,
        note="raw ROM metadata word matching map_palette_settings Flash Effect; zeroed in .fts visual palette rows",
    ),
    field(
        "map_subpalette_3_colours",
        0x60,
        2,
        16,
        "16 SNES BGR555 colours for arrangement descriptor palette 5 / CGRAM $02A0..$02BF; colour 0 overlaps flash_effect in raw ROM",
    ),
    field(
        "map_subpalette_4_colours",
        0x80,
        2,
        16,
        "16 SNES BGR555 colours for arrangement descriptor palette 6 / CGRAM $02C0..$02DF",
    ),
    field(
        "map_subpalette_5_colours",
        0xA0,
        2,
        16,
        "16 SNES BGR555 colours for arrangement descriptor palette 7 / CGRAM $02E0..$02FF",
    ),
)

LANDING_PALETTE_ANIM_PROFILE_BASE_FIELDS = (
    field("compressed_palette_payload_pointer", 0x00, 4, note="C0:023F decompresses this payload to 7E:B800"),
    field("step_count", 0x04, 1, note="C0:023F uses zero to skip loading the sequencer, otherwise bounds the step-duration copy"),
)

TOWN_MAP_ICON_GRAPHIC_DESCRIPTOR_FIELDS = (
    field("relative_y_offset", 0x00, 1, note="signed Y offset consumed by C0:8C54/C0:8CD5"),
    field("tile_attribute_word", 0x01, 2, note="tile/attribute word staged by the town-map icon renderer"),
    field("relative_x_offset", 0x03, 1, note="signed X offset consumed by C0:8C54/C0:8CD5"),
    field("control_flags", 0x04, 1, note="bit 7 terminates the descriptor list; bit 0 feeds C0:8CD5's packed renderer mask/attribute bit"),
)

TOWN_MAP_ICON_PLACEMENT_FIELDS = (
    field("x", 0x00, 1, note="base X coordinate passed to C0:8C54 by C4:D43F"),
    field("y", 0x01, 1, note="base Y coordinate passed to C0:8C54 by C4:D43F"),
    field("icon_id", 0x02, 1, note="town-map icon id remapped through the E1:F44C graphic pointer table"),
    field("event_flag_with_draw_polarity", 0x03, 2, note="event flag word; high bit means draw when set, clear high bit means draw when clear"),
)

PHOTOGRAPHER_CONFIG_FIELDS = (
    field("event_flag_gate", 0x00, 2, note="credits/photo helpers test this event flag before counting or rendering a photo scene"),
    field("map_load_x_tile", 0x02, 2, note="C4:F264 shifts this word left three before calling C0:13F6 LoadMapAtPosition"),
    field("map_load_y_tile", 0x04, 2, note="C4:F264 shifts this word left three before calling C0:13F6 LoadMapAtPosition"),
    field("slide_angle", 0x08, 1, note="C4:F46F projects the credits photograph slide vector from this angle byte"),
    field("slide_duration", 0x09, 1, note="C4:F46F scales this byte into the slide frame count"),
    field("photo_scene_x_tile", 0x0A, 2, note="C4:6D4B shifts this word left three and writes the current slot live X"),
    field("photo_scene_y_tile", 0x0C, 2, note="C4:6D4B shifts this word left three and writes the current slot live Y"),
) + tuple(
    field(name, offset, 2, note=note)
    for index in range(6)
    for name, offset, note in (
        (f"attached_visual_{index}_x_tile", 0x0E + index * 4, "C4:F264 shifts this attached visual X tile coordinate left three before spawning"),
        (f"attached_visual_{index}_y_tile", 0x10 + index * 4, "C4:F264 shifts this attached visual Y tile coordinate left three before spawning"),
    )
) + tuple(
    field(name, offset, 2, note=note)
    for index in range(4)
    for name, offset, note in (
        (f"photo_entity_{index}_x_tile", 0x26 + index * 6, "C4:F264 shifts this live photo-entity X tile coordinate left three before spawning"),
        (f"photo_entity_{index}_y_tile", 0x28 + index * 6, "C4:F264 shifts this live photo-entity Y tile coordinate left three before spawning"),
        (f"photo_entity_{index}_descriptor", 0x2A + index * 6, "C4:F264 skips this live photo-entity slot when the descriptor word is zero"),
    )
)

TITLE_SCREEN_LETTER_OAM_RECORD_FIELDS = (
    field("oam_entries", 0x00, 5, 9, "nine OAM-ish entries: y, tile, attrs, x, control; terminal entries have bit 7 set in control"),
)

C3_WORD_TABLE_VALUE_FIELD = (field("value", 0x00, 2),)

PATHFINDING_TILE_CONTEXT_GATE_FIELDS = (
    field(
        "gate_enabled",
        0x00,
        1,
        note="nonzero allows the C0:C0B4/C0:C19B path consumer to continue after C0:0AA1",
    ),
)

INPUT_DIRECTION_PERMISSION_MASK_FIELDS = (
    field("permission_mask", 0x00, 2, note="bitmask consumed by C0:404F MapInputToDirection"),
)

INTERACTION_PROBE_DIRECTION_OFFSET_FIELDS = (
    field("offset_pixels", 0x00, 2, note="signed probe offset in pixels for one direction index"),
)

INTERACTION_RESULT_FACING_REMAP_FIELDS = (
    field("target_facing_state", 0x00, 2, note="stored into $2AF6[target] by C0:42C2"),
)

DOOR_CANDIDATE_DIRECTION_OFFSET_FIELDS = (
    field("cell_delta", 0x00, 2, note="signed coarse-cell offset added by C4:334A"),
)

MENU_CURSOR_TILE_RUN_FIELDS = (
    field("tile_0", 0x00, 2),
    field("tile_1", 0x02, 2),
    field("tile_2", 0x04, 2),
    field("tile_3", 0x06, 2),
)

MENU_CURSOR_THREE_TILE_RUN_FIELDS = (
    field("tile_0", 0x00, 2),
    field("tile_1", 0x02, 2),
    field("tile_2", 0x04, 2),
)

BATTLE_PSI_KNOWN_STATE_GATE_ROW_FIELDS = tuple(
    field(f"psi_slot_{index}_gate", index * 2, 2)
    for index in range(7)
)

BATTLE_PSI_GROUP_RENDER_METADATA_FIELDS = (
    field("raw_group_render_metadata_and_labels", 0x00, 1, 0x5C),
)

BATTLE_PSI_MENU_ENTRY_FIXED_TAIL_FIELDS = (
    field("encoded_tail", 0x00, 1, 8),
)

BATTLE_PSI_MENU_ENTRY_ROW_FIELDS = (
    field("encoded_text", 0x00, 1, 20),
)

LEVEL_UP_STAT_GROWTH_VARIANCE_FIELDS = (
    field("variance", 0x00, 1, note="byte added to the C4:5F7B random result by C1:D08B"),
)

VISUAL_SELECTOR_POSE_ROW_FIELDS = tuple(
    field(f"bucket_{index}_pose", index * 2, 2)
    for index in range(8)
)

BATTLE_VISUAL_STRIP_OFFSET_FIELDS = (
    field("strip_0_offset", 0x00, 2),
    field("strip_1_offset", 0x02, 2),
    field("strip_2_offset", 0x04, 2),
    field("strip_3_offset", 0x06, 2),
)

BATTLE_VISUAL_OAM_TILE_GRID_FIELDS = (
    field("tile_0", 0x00, 2),
    field("tile_1", 0x02, 2),
    field("tile_2", 0x04, 2),
    field("tile_3", 0x06, 2),
    field("tile_4", 0x08, 2),
    field("tile_5", 0x0A, 2),
    field("tile_6", 0x0C, 2),
    field("tile_7", 0x0E, 2),
)

BATTLE_PALETTE_ROW_FIELDS = tuple(
    field(f"rgb555_colour_{index}", index * 2, 2)
    for index in range(16)
)

BATTLE_VISUAL_COLOUR_TRIPLE_FIELDS = (
    field("red_component", 0x00, 1, note="table byte 0; passed through Y to SetFixedColourRgbComponents"),
    field("green_component", 0x01, 1, note="table byte 1; passed through X to SetFixedColourRgbComponents"),
    field("blue_component", 0x02, 1, note="table byte 2; passed through A to SetFixedColourRgbComponents"),
)

C4_BYTE_VALUE_FIELD = (field("value", 0x00, 1),)

C4_WORD_VALUE_FIELD = (field("value", 0x00, 2),)

BLANK_COMMON_TILE_SOURCE_FIELDS = (
    field("zero_byte", 0x00, 1, 0x200, note="all bytes are zero; copied as a blank graphics/tile source block"),
)

MOVEMENT_OCTANT_SIGNED_UNIT_DELTA_FIELDS = (
    field("component", 0x00, 2, 16, note="two eight-word signed unit-vector component arrays"),
)

YOUR_SANCTUARY_LOCATION_COORDINATE_FIELDS = (
    field("word_0", 0x00, 2, note="first coordinate/source word passed to C4:E13E"),
    field("word_1", 0x02, 2, note="second coordinate/source word passed to C4:E13E"),
)


BATTLE_SELECTION_SNAPSHOT_FIELDS = (
    field("user", 0x00, 1),
    field("param1", 0x01, 1),
    field("selected_action", 0x02, 2),
    field("targetting", 0x04, 1),
    field("selected_target", 0x05, 1),
    field("snapshot_active", 0x0C, 1, note="C2:B930 sets this byte to 1 when exporting a live slot snapshot"),
    field("snapshot_ally_or_enemy", 0x0E, 1, note="snapshot byte cleared by C2:B930; same offset family as battler::ally_or_enemy"),
    field("snapshot_npc_id", 0x0F, 1, note="snapshot byte cleared by C2:B930; same offset family as battler::npc_id"),
    field("selected_user_zero_based", 0x10, 1, note="zero-based selected user or battler id"),
    field("current_hp", 0x11, 2, note="copied from selected char_struct current_hp"),
    field("current_hp_target", 0x13, 2, note="copied from selected char_struct current_hp_target"),
    field("max_hp", 0x15, 2, note="copied from selected char_struct max_hp"),
    field("current_pp", 0x17, 2, note="copied from selected char_struct current_pp"),
    field("current_pp_target", 0x19, 2, note="copied from selected char_struct current_pp_target"),
    field("max_pp", 0x1B, 2, note="copied from selected char_struct max_pp"),
    field("afflictions", 0x1D, 1, 7, "copied from selected char_struct affliction/status bytes"),
    field("resistance_summary", 0x37, 1, 6, "derived from selected char_struct late resistance fields"),
)

LOADED_BG_DATA_FIELDS = (
    field("target_layer", 0x00, 1),
    field("bitdepth", 0x01, 1),
    field("freeze_palette_scrolling", 0x02, 1),
    field("palette_shifting_style", 0x03, 1),
    field("palette_cycle_1_first", 0x04, 1),
    field("palette_cycle_1_last", 0x05, 1),
    field("palette_cycle_2_first", 0x06, 1),
    field("palette_cycle_2_last", 0x07, 1),
    field("palette_cycle_1_step", 0x08, 1),
    field("palette_cycle_2_step", 0x09, 1),
    field("palette_change_speed", 0x0A, 1),
    field("palette_change_duration_left", 0x0B, 1),
    field("palette", 0x0C, 2, 16, "current RGB555 palette words"),
    field("palette2", 0x2C, 2, 16, "backup/original RGB555 palette words"),
    field("palette_pointer", 0x4C, 2, note="displayed palette destination pointer"),
    field("scrolling_movements", 0x4E, 1, 4),
    field("current_scrolling_movement", 0x52, 1),
    field("scrolling_duration_left", 0x53, 2),
    field("horizontal_position", 0x55, 2),
    field("vertical_position", 0x57, 2),
    field("horizontal_velocity", 0x59, 2),
    field("vertical_velocity", 0x5B, 2),
    field("horizontal_acceleration", 0x5D, 2),
    field("vertical_acceleration", 0x5F, 2),
    field("distortion_styles", 0x61, 1, 4),
    field("current_distortion_style_index", 0x65, 1),
    field("distortion_duration_left", 0x66, 2),
    field("distortion_type", 0x68, 1),
    field("distortion_ripple_frequency", 0x69, 2),
    field("distortion_ripple_amplitude", 0x6B, 2),
    field("distortion_speed", 0x6D, 1),
    field("distortion_compression_rate", 0x6E, 2),
    field("distortion_ripple_frequency_acceleration", 0x70, 2),
    field("distortion_ripple_amplitude_acceleration", 0x72, 2),
    field("distortion_speed_acceleration", 0x74, 1),
    field("distortion_compression_acceleration", 0x75, 2),
)


def wram_address(address: int) -> str:
    return f"7E:{address:04X}"


def root_contracts() -> list[Contract]:
    evidence = (
        "tools/lookup_wram_field.py",
        "refs/ebsrc-main/ebsrc-main/include/structs.asm",
        "refs/ebsrc-main/ebsrc-main/src/bankconfig/common/ram.asm",
    )
    return [
        Contract(
            id=root.name,
            domain="wram-root",
            address=wram_address(root.base),
            stride=root.stride,
            count=root.count,
            struct_name=root.struct_name,
            confidence="corroborated",
            note=root.note,
            evidence=evidence,
            fields=root.fields,
        )
        for root in ROOTS
    ]


def d8_collision_pointer_contracts() -> list[Contract]:
    specs = (
        (0, "D8:8F50", 832),
        (1, "D8:95D0", 845),
        (2, "D8:9C6A", 827),
        (3, "D8:A2E0", 524),
        (4, "D8:A6F8", 935),
        (5, "D8:AE46", 287),
        (6, "D8:B084", 875),
        (7, "D8:B75A", 749),
        (8, "D8:BD34", 628),
        (9, "D8:C21C", 933),
        (10, "D8:C966", 871),
        (11, "D8:D034", 713),
        (12, "D8:D5C6", 462),
        (13, "D8:D962", 882),
        (14, "D8:E046", 203),
        (15, "D8:E1DC", 143),
        (16, "D8:E2FA", 390),
        (17, "D8:E606", 343),
        (18, "D8:E8B4", 445),
        (19, "D8:EC2E", 536),
    )
    return [
        Contract(
            id=f"MAP_DATA_TILE_COLLISION_POINTERS_{index}",
            domain="rom-table",
            address=address,
            stride=0x02,
            count=count,
            struct_name="map_tile_collision_record_offset",
            confidence="exact",
            note="16-byte-aligned word offsets into MAP_TILE_COLLISION_DATA for one tileset/profile collision table.",
            evidence=(
                "refs/ebsrc-main/ebsrc-main/src/bankconfig/common/bank18.asm",
                "notes/d8-table-splits.md",
                "notes/map-collision-pointer-contract.md",
            ),
            fields=D8_COLLISION_RECORD_OFFSET_FIELDS,
        )
        for index, address, count in specs
    ]


def town_map_icon_placement_list_contracts() -> list[Contract]:
    specs = (
        (0, "E1:F4A9", 7, "E1:F4CC"),
        (1, "E1:F4CD", 8, "E1:F4F5"),
        (2, "E1:F4F6", 9, "E1:F523"),
        (3, "E1:F524", 7, "E1:F547"),
        (4, "E1:F548", 5, "E1:F561"),
        (5, "E1:F562", 6, "E1:F580"),
    )
    return [
        Contract(
            id=f"TOWN_MAP_ICON_PLACEMENT_LIST_{index}",
            domain="rom-variable-table",
            address=address,
            stride=0x05,
            count=count,
            struct_name="town_map_icon_placement_record",
            confidence="runtime-corroborated-shape",
            note=f"Town-map icon placement list {index}; C4:D43F walks five-byte records until the FF terminator at {terminator}.",
            evidence=(
                "notes/ui-font-town-map-asset-contracts.md",
                "notes/town-map-selection-rendering-c4d274-c4d744.md",
            ),
            fields=TOWN_MAP_ICON_PLACEMENT_FIELDS,
        )
        for index, address, count, terminator in specs
    ]


def landing_palette_anim_profile_fields(step_count: int) -> tuple[FieldSpec, ...]:
    if step_count == 0:
        return LANDING_PALETTE_ANIM_PROFILE_BASE_FIELDS
    return LANDING_PALETTE_ANIM_PROFILE_BASE_FIELDS + (
        field(
            "step_durations",
            0x05,
            1,
            step_count,
            "one-byte sequencer values copied to $4460 by C0:023F and consumed by C0:030F",
        ),
    )


def landing_palette_anim_profile_contracts() -> list[Contract]:
    specs = (
        (0, "DF:E55D", "DF:E61B", 4),
        (1, "DF:E566", "DF:E6B2", 4),
        (2, "DF:E56F", "DF:E73D", 6),
        (3, "DF:E57A", "DF:E8E0", 3),
        (4, "DF:E582", "DF:E96C", 4),
        (5, "DF:E58B", "DF:EA56", 3),
        (6, "DF:E593", "DF:EB31", 3),
        (7, "DF:E59B", "DF:EBAC", 8),
        (8, "DF:E5A8", "DF:EC46", 0),
        (9, "DF:E5AD", "DF:EC46", 0),
        (10, "DF:E5B2", "DF:EC46", 0),
        (11, "DF:E5B7", "DF:EC46", 0),
        (12, "DF:E5BC", "DF:EC46", 0),
        (13, "DF:E5C1", "DF:EC46", 0),
        (14, "DF:E5C6", "DF:EC46", 0),
        (15, "DF:E5CB", "DF:EC46", 0),
        (16, "DF:E5D0", "DF:EC46", 0),
        (17, "DF:E5D5", "DF:EC46", 0),
        (18, "DF:E5DA", "DF:EC46", 0),
        (19, "DF:E5DF", "DF:EC46", 0),
        (20, "DF:E5E4", "DF:EC46", 0),
        (21, "DF:E5E9", "DF:EC46", 0),
        (22, "DF:E5EE", "DF:EC46", 0),
        (23, "DF:E5F3", "DF:EC46", 0),
        (24, "DF:E5F8", "DF:EC46", 0),
        (25, "DF:E5FD", "DF:EC46", 0),
        (26, "DF:E602", "DF:EC46", 0),
        (27, "DF:E607", "DF:EC46", 0),
        (28, "DF:E60C", "DF:EC46", 0),
        (29, "DF:E611", "DF:EC46", 0),
        (30, "DF:E616", "DF:EC46", 0),
    )
    return [
        Contract(
            id=f"LANDING_PALETTE_ANIM_PROFILE_{index}",
            domain="rom-variable-table",
            address=address,
            stride=0x05 + step_count,
            count=1,
            struct_name="landing_palette_anim_profile",
            confidence="runtime-corroborated-shape",
            note=f"Landing palette-animation profile {index}; C0:023F selects this record through DF:E4E1, decompresses {payload_address}, and copies {step_count} step bytes after the payload pointer.",
            evidence=(
                "notes/bank-df-first-pass.md",
                "notes/landing-profile-cache-436e-4474.md",
                "src/c0/c0_023f_build_landing_profile_step_sequencer.asm",
                "src/c0/c0_030f_advance_landing_profile_step_sequencer.asm",
            ),
            fields=landing_palette_anim_profile_fields(step_count),
        )
        for index, address, payload_address, step_count in specs
    ]


def landing_palette_anim_payload_contracts() -> list[Contract]:
    specs = (
        (0, "DF:E61B", 0x97),
        (1, "DF:E6B2", 0x8B),
        (2, "DF:E73D", 0x1A3),
        (3, "DF:E8E0", 0x8C),
        (4, "DF:E96C", 0xEA),
        (5, "DF:EA56", 0xDB),
        (6, "DF:EB31", 0x7B),
        (7, "DF:EBAC", 0x9A),
    )
    return [
        Contract(
            id=f"LANDING_PALETTE_ANIM_PAYLOAD_{index}",
            domain="rom-compressed-payload",
            address=address,
            stride=size,
            count=1,
            struct_name="landing_palette_anim_compressed_payload",
            confidence="pointer-bounded",
            note="Compressed palette-animation payload selected by a non-empty DF landing palette-animation profile and decompressed by C0:023F.",
            evidence=(
                "notes/bank-df-first-pass.md",
                "notes/landing-profile-cache-436e-4474.md",
                "src/c0/c0_023f_build_landing_profile_step_sequencer.asm",
                "src/df/bank_df_helpers_asar.asm",
            ),
            fields=(field("compressed_payload", 0x00, 1, size, "C4:1A9E-compatible compressed payload bytes"),),
        )
        for index, address, size in specs
    ]


def extra_contracts() -> list[Contract]:
    return [
        Contract(
            id="ITEM_CONFIGURATION_TABLE",
            domain="rom-table",
            address="D5:5000",
            stride=0x27,
            count=254,
            struct_name="item",
            confidence="corroborated",
            note="Fixed-stride item table used by C1/C2 inventory, equipment, and item-effect helpers.",
            evidence=(
                "refs/ebsrc-main/ebsrc-main/include/structs.asm",
                "refs/ebsrc-main/ebsrc-main/include/symbols/misc.inc.asm",
                "notes/d5-table-splits.md",
                "notes/item-byte-19-packed-class-and-slot.md",
                "manifests/coilsnake-field-semantics.json",
            ),
            fields=ITEM_FIELDS,
        ),
        Contract(
            id="STORE_TABLE",
            domain="rom-table",
            address="D5:76B2",
            stride=0x07,
            count=66,
            struct_name="store_inventory",
            confidence="corroborated",
            note="Store inventory rows immediately following the 254-row item table.",
            evidence=(
                "refs/eb-decompile-4ef92/store_table.yml",
                "notes/d5-table-splits.md",
            ),
            fields=STORE_INVENTORY_FIELDS,
        ),
        Contract(
            id="PSI_TELEPORT_DEST_TABLE",
            domain="rom-table",
            address="D5:7880",
            stride=0x1F,
            count=16,
            struct_name="psi_teleport_destination",
            confidence="corroborated",
            note="Teleport-menu destination rows with fixed-width name, event flag, and map coordinates.",
            evidence=(
                "refs/eb-decompile-4ef92/psi_teleport_dest_table.yml",
                "notes/landing-destination-table-d57880.md",
                "notes/d5-table-splits.md",
            ),
            fields=PSI_TELEPORT_DESTINATION_FIELDS,
        ),
        Contract(
            id="TELEPHONE_CONTACTS_TABLE",
            domain="rom-table",
            address="D5:7AAE",
            stride=0x1F,
            count=6,
            struct_name="telephone_contact",
            confidence="corroborated",
            note="Phone contact rows with fixed-width name, event flag, and text pointer.",
            evidence=(
                "refs/eb-decompile-4ef92/telephone_contacts_table.yml",
                "notes/d5-table-splits.md",
                "CoilSnake telephone-dad-text-pointer-probe",
            ),
            fields=TELEPHONE_CONTACT_FIELDS,
        ),
        Contract(
            id="BATTLE_ACTION_TABLE",
            domain="rom-table",
            address="D5:7B68",
            stride=0x0C,
            count=318,
            struct_name="battle_action",
            confidence="corroborated",
            note="Battle action rows consumed by targetting, menu, PP-cost, text, and battle-function dispatch paths.",
            evidence=(
                "refs/ebsrc-main/ebsrc-main/include/structs.asm",
                "refs/ebsrc-main/ebsrc-main/src/data/battle/action_table.asm",
                "notes/d5-table-splits.md",
                "notes/battle-targetting-resolver-c1adb4-af50.md",
                "notes/battle-psi-menu-controller-c1cc39-ce73.md",
                "manifests/coilsnake-field-semantics.json",
            ),
            fields=BATTLE_ACTION_FIELDS,
        ),
        Contract(
            id="PSI_ABILITY_TABLE",
            domain="rom-table",
            address="D5:8A50",
            stride=0x0F,
            count=54,
            struct_name="psi_ability",
            confidence="corroborated",
            note="PSI menu metadata table, including linked battle action ids and learn levels.",
            evidence=(
                "refs/ebsrc-main/ebsrc-main/include/structs.asm",
                "refs/ebsrc-main/ebsrc-main/include/symbols/misc.inc.asm",
                "notes/d5-table-splits.md",
                "notes/battle-psi-ability-table-d58a50.md",
            ),
            fields=PSI_ABILITY_FIELDS,
        ),
        Contract(
            id="PSI_NAME_TABLE",
            domain="rom-table",
            address="D5:8D7A",
            stride=0x19,
            count=17,
            struct_name="psi_name",
            confidence="corroborated",
            note="Fixed-width PSI display names.",
            evidence=(
                "refs/eb-decompile-4ef92/psi_name_table.yml",
                "notes/d5-table-splits.md",
            ),
            fields=PSI_NAME_FIELDS,
        ),
        Contract(
            id="NPC_AI_TABLE",
            domain="rom-table",
            address="D5:8F23",
            stride=0x01,
            count=38,
            struct_name="npc_ai_selector",
            confidence="corroborated",
            note="One-byte NPC battle AI selector table.",
            evidence=(
                "refs/ebsrc-main/ebsrc-main/src/data/battle/npc_ai_table.asm",
                "notes/d5-table-splits.md",
            ),
            fields=BYTE_VALUE_FIELD,
        ),
        Contract(
            id="EXP_TABLE",
            domain="rom-table",
            address="D5:8F49",
            stride=0x190,
            count=4,
            struct_name="character_exp_curve",
            confidence="corroborated",
            note="Four character EXP curves with 100 32-bit thresholds per curve.",
            evidence=(
                "refs/eb-decompile-4ef92/exp_table.yml",
                "notes/d5-table-splits.md",
            ),
            fields=EXP_CURVE_FIELDS,
        ),
        Contract(
            id="ENEMY_CONFIGURATION_TABLE",
            domain="rom-table",
            address="D5:9589",
            stride=0x5E,
            count=231,
            struct_name="enemy_data",
            confidence="corroborated",
            note="Enemy configuration records copied into battler slots by the C2 battle-init paths.",
            evidence=(
                "refs/ebsrc-main/ebsrc-main/include/structs.asm",
                "refs/ebsrc-main/ebsrc-main/include/symbols/misc.inc.asm",
                "notes/d5-table-splits.md",
                "notes/class2-005e-record-domain.md",
                "notes/class2-local-enemy-id-to-battler-init-chain.md",
                "notes/class2-d59589-enemy-data-crosswalk.md",
                "manifests/coilsnake-field-semantics.json",
            ),
            fields=ENEMY_FIELDS,
        ),
        Contract(
            id="STATS_GROWTH_VARS",
            domain="rom-table",
            address="D5:EA5B",
            stride=0x07,
            count=4,
            struct_name="stats_growth_vars",
            confidence="corroborated",
            note="Seven-byte per-character stat growth parameter rows.",
            evidence=(
                "refs/eb-decompile-4ef92/stats_growth_vars.yml",
                "notes/d5-table-splits.md",
                "CoilSnake stats-growth-ness-offense-probe",
            ),
            fields=STATS_GROWTH_VAR_FIELDS,
        ),
        Contract(
            id="CONDIMENT_TABLE",
            domain="rom-table",
            address="D5:EA77",
            stride=0x07,
            count=44,
            struct_name="condiment_rule",
            confidence="corroborated",
            note="Food/condiment pairing table with recovery and runtime effect bytes.",
            evidence=(
                "refs/eb-decompile-4ef92/condiment_table.yml",
                "notes/d5-table-splits.md",
            ),
            fields=CONDIMENT_FIELDS,
        ),
        Contract(
            id="TELEPORT_DESTINATION_TABLE",
            domain="rom-table",
            address="D5:EBAB",
            stride=0x08,
            count=234,
            struct_name="teleport_destination",
            confidence="corroborated",
            note="Map teleport destination coordinate/style rows.",
            evidence=(
                "refs/eb-decompile-4ef92/teleport_destination_table.yml",
                "notes/d5-table-splits.md",
            ),
            fields=TELEPORT_DESTINATION_FIELDS,
        ),
        Contract(
            id="MAP_HOTSPOTS",
            domain="rom-table",
            address="D5:F2FB",
            stride=0x08,
            count=56,
            struct_name="map_hotspot",
            confidence="corroborated",
            note="Rectangular map hotspot coordinate records.",
            evidence=(
                "refs/eb-decompile-4ef92/map_hotspots.yml",
                "notes/d5-table-splits.md",
            ),
            fields=MAP_HOTSPOT_FIELDS,
        ),
        Contract(
            id="TIMED_ITEM_TRANSFORMATION_TABLE",
            domain="rom-table",
            address="D5:F4BB",
            stride=0x05,
            count=4,
            struct_name="timed_item_transformation",
            confidence="corroborated",
            note="Timed item conversion rows for delayed item changes and sound feedback.",
            evidence=(
                "refs/eb-decompile-4ef92/timed_item_transformation_table.yml",
                "notes/d5-table-splits.md",
                "CoilSnake timed-item-transform-delay-probe",
            ),
            fields=TIMED_ITEM_TRANSFORMATION_FIELDS,
        ),
        Contract(
            id="DONT_CARE_NAMES",
            domain="rom-table",
            address="D5:F4CF",
            stride=0x2A,
            count=7,
            struct_name="default_name_set",
            confidence="corroborated",
            note="Default naming-screen choices as seven fixed-width names per row.",
            evidence=(
                "refs/eb-decompile-4ef92/dont_care_names.yml",
                "notes/d5-table-splits.md",
            ),
            fields=DONT_CARE_NAME_FIELDS,
        ),
        Contract(
            id="INITIAL_STATS",
            domain="rom-table",
            address="D5:F5F5",
            stride=0x15,
            count=4,
            struct_name="initial_party_member_stats",
            confidence="corroborated",
            note="Initial character setup rows with level, money, EXP, and starting inventory.",
            evidence=(
                "refs/eb-decompile-4ef92/initial_stats.yml",
                "notes/d5-table-splits.md",
                "CoilSnake initial-stats-ness-money-probe",
            ),
            fields=INITIAL_STATS_FIELDS,
        ),
        Contract(
            id="TIMED_DELIVERY_TABLE",
            domain="rom-table",
            address="D5:F649",
            stride=0x14,
            count=10,
            struct_name="timed_delivery_source_window",
            confidence="exact-source-window",
            note="Exact source-order timed-delivery split window; it starts four bytes into the EF consumer-effective controller rows at D5:F645 and ends with four zero padding bytes.",
            evidence=(
                "refs/eb-decompile-4ef92/timed_delivery_table.yml",
                "notes/d5-table-splits.md",
                "notes/delivery-row-helpers-ef0e67-ef0ead.md",
                "notes/d5-timed-delivery-row-contracts.md",
                "CoilSnake timed-delivery-first-timer-probe",
            ),
            fields=TIMED_DELIVERY_FIELDS,
        ),
        Contract(
            id="TIMED_DELIVERY_CONTROLLER_TABLE",
            domain="rom-table",
            address="D5:F645",
            stride=0x14,
            count=10,
            struct_name="timed_delivery_controller_row",
            confidence="consumer-corroborated",
            note="Consumer-effective timed-delivery/service table base used by the EF:0CA7..0EE8 helper family and the C1 1F D3 row-selector callback.",
            evidence=(
                "notes/d5-timed-delivery-row-contracts.md",
                "notes/delivery-row-helpers-ef0e67-ef0ead.md",
                "notes/timed-delivery-controller-499-500-common.md",
                "notes/timed-delivery-row-index-command-1f-d3.md",
                "notes/selector-row-config-family-ef0ee8.md",
                "src/ef/ef_0ca7_delivery_selector_helper_cluster.asm",
                "notes/coilsnake-field-join-report.md",
            ),
            fields=TIMED_DELIVERY_CONTROLLER_FIELDS,
        ),
        Contract(
            id="CF_DOOR_DATA",
            domain="rom-block",
            address="CF:0000",
            stride=0x264F,
            count=1,
            struct_name="cf_door_data_payload",
            confidence="consumer-corroborated-partial",
            note="CF door-data payload block before the 1280 counted sector door-list records. Type 0, type 2, and type 6 payload shapes are decoded by the CF door-data contract; remaining trigger-type parameters stay bounded/raw.",
            evidence=(
                "notes/cf-table-splits.md",
                "notes/cf-sector-list-contracts.md",
                "notes/cf-door-data-contracts.md",
                "refs/ebsrc-main/ebsrc-main/src/bankconfig/common/bank0f.asm",
                "src/c0/c0_6a1b_movement_trigger_type0_queue_door_destination.asm",
                "src/c0/c0_6aca_movement_trigger_type2_queue_door_transition.asm",
                "src/c0/c0_6bff_run_deferred_script_pointer_and_refresh_transition_state.asm",
                "src/c0/c0_65c2_probe_type6_door_candidate.asm",
            ),
            fields=RAW_CF_DOOR_DATA_FIELDS,
        ),
        Contract(
            id="CF_DOOR_CONFIG_TABLE",
            domain="rom-variable-table",
            address="CF:264F",
            stride=0x32A0,
            count=1,
            struct_name="door_sector_list_block",
            confidence="exact-variable-lists",
            note="1280 D0-pointer-addressed counted door/trigger sector lists with complete decoded rows in notes/cf-sector-list-contracts.json and per-type trigger payload semantics in notes/cf-movement-trigger-contracts.json. Source-order physical rows match the map_doors bundle count; a small set of pointer starts overlap prior counted-list tails, so consumers should follow D0 pointers rather than assume a flat sequential table.",
            evidence=(
                "notes/cf-table-splits.md",
                "notes/cf-sector-list-contracts.md",
                "notes/cf-movement-trigger-contracts.md",
                "refs/ebsrc-main/ebsrc-main/src/bankconfig/common/bank0f.asm",
            ),
            fields=RAW_CF_DOOR_CONFIG_LIST_FIELDS,
        ),
        Contract(
            id="D0_DOOR_POINTER_TABLE",
            domain="rom-table",
            address="D0:0000",
            stride=0x04,
            count=1280,
            struct_name="door_sector_list_far_pointer",
            confidence="exact",
            note="40x32 long-pointer grid into the CF door sector lists.",
            evidence=(
                "notes/cf-table-splits.md",
                "notes/cf-sector-list-contracts.md",
                "refs/ebsrc-main/ebsrc-main/src/bankconfig/common/bank10.asm",
            ),
            fields=D0_DOOR_POINTER_FIELDS,
        ),
        Contract(
            id="SCREEN_TRANSITION_CONFIG_TABLE",
            domain="rom-table",
            address="D0:1400",
            stride=0x0C,
            count=34,
            struct_name="screen_transition_config",
            confidence="corroborated",
            note="Fixed-size screen transition configuration rows before the event-control pointer table.",
            evidence=(
                "refs/ebsrc-main/ebsrc-main/include/structs.asm",
                "notes/d0-table-splits.md",
            ),
            fields=SCREEN_TRANSITION_CONFIG_FIELDS,
        ),
        Contract(
            id="EVENT_CONTROL_PTR_TABLE",
            domain="rom-table",
            address="D0:1598",
            stride=0x02,
            count=20,
            struct_name="word_pointer",
            confidence="exact",
            note="Word offsets to the 20 MAP_TILE_EVENT chains; C0:0703 indexes this table by tileset/event-control id.",
            evidence=(
                "refs/ebsrc-main/ebsrc-main/src/data/event_control_ptr_table.asm",
                "notes/d0-table-splits.md",
                "notes/d0-tile-event-contracts.md",
            ),
            fields=WORD_POINTER_FIELDS,
        ),
        Contract(
            id="MAP_TILE_EVENT_CONTROL_TABLE",
            domain="rom-variable-table",
            address="D0:15C0",
            stride=0x02C0,
            count=1,
            struct_name="map_tile_event_chain_block",
            confidence="exact-variable-chains",
            note="20 variable MAP_TILE_EVENT chains. Each nonzero condition header is event_flag_condition_word plus replacement_pair_count, followed by target/source replacement-block pairs consumed by C0:062A.",
            evidence=(
                "refs/ebsrc-main/ebsrc-main/include/structs.asm",
                "notes/d0-table-splits.md",
                "notes/d0-tile-event-contracts.md",
            ),
            fields=RAW_D0_TILE_EVENT_CONTROL_FIELDS,
        ),
        Contract(
            id="MAP_ENEMY_PLACEMENT",
            domain="rom-table",
            address="D0:1880",
            stride=0x02,
            count=20480,
            struct_name="map_enemy_placement",
            confidence="corroborated",
            note="20480 word enemy-map-group entries.",
            evidence=(
                "refs/eb-decompile-4ef92/map_enemy_placement.yml",
                "notes/d0-table-splits.md",
            ),
            fields=MAP_ENEMY_PLACEMENT_FIELDS,
        ),
        Contract(
            id="ENEMY_PLACEMENT_GROUPS_PTR_TABLE",
            domain="rom-table",
            address="D0:B880",
            stride=0x04,
            count=203,
            struct_name="far_pointer",
            confidence="exact",
            note="Long pointers into ENEMY_PLACEMENT_GROUPS_TABLE.",
            evidence=(
                "refs/eb-decompile-4ef92/map_enemy_groups.yml",
                "notes/d0-table-splits.md",
            ),
            fields=FAR_POINTER_FIELDS,
        ),
        Contract(
            id="ENEMY_PLACEMENT_GROUPS_TABLE",
            domain="rom-variable-table",
            address="D0:BBAC",
            stride=0x0A61,
            count=1,
            struct_name="enemy_placement_group_lists",
            confidence="exact-variable-lists",
            note="203 variable enemy placement group lists: event_flag_gate, primary_spawn_chance, flagged_spawn_chance, then selection_weight + battle_group_id entries consumed by C0:2668.",
            evidence=(
                "refs/eb-decompile-4ef92/map_enemy_groups.yml",
                "notes/d0-table-splits.md",
                "notes/d0-variable-list-contracts.md",
            ),
            fields=RAW_D0_ENEMY_PLACEMENT_GROUP_FIELDS,
        ),
        Contract(
            id="BTL_ENTRY_PTR_TABLE",
            domain="rom-table",
            address="D0:C60D",
            stride=0x08,
            count=484,
            struct_name="battle_entry_ptr_entry",
            confidence="corroborated",
            note="Battle-entry pointer records with run-away and letterbox metadata.",
            evidence=(
                "refs/ebsrc-main/ebsrc-main/include/structs.asm",
                "refs/eb-decompile-4ef92/enemy_groups.yml",
                "notes/d0-table-splits.md",
            ),
            fields=BATTLE_ENTRY_POINTER_FIELDS,
        ),
        Contract(
            id="ENEMY_BATTLE_GROUPS_TABLE",
            domain="rom-variable-table",
            address="D0:D52D",
            stride=0x0A87,
            count=1,
            struct_name="enemy_battle_group_payloads",
            confidence="exact-variable-lists",
            note="Consumer-visible suffix slices addressed by BTL_ENTRY_PTR_TABLE; entries are repeat_count + enemy_id until an FF terminator and are consumed by C2 battle setup, sprite loading, and call-for-help selection.",
            evidence=(
                "refs/eb-decompile-4ef92/enemy_groups.yml",
                "notes/d0-table-splits.md",
                "notes/d0-variable-list-contracts.md",
            ),
            fields=RAW_D0_BATTLE_GROUP_FIELDS,
        ),
        Contract(
            id="D7_SECTOR_TILESET_PALETTE_TABLE",
            domain="rom-table",
            address="D7:A800",
            stride=0x01,
            count=1280,
            struct_name="map_sector_tileset_palette",
            confidence="consumer-corroborated",
            note="40x32 sector table whose packed byte is bits 3..7 tileset_id and bits 0..2 palette_variant; every row matches map-sector metadata and multiple C0/C4 consumers.",
            evidence=(
                "notes/d7-sector-metadata-contracts.md",
                "notes/map-sector-bundles.md",
                "src/c0/c0_08cf_derive_landing_region_profile_from_destination.asm",
                "src/c0/c0_0ac5_load_vertical_movement_map_strip_payload.asm",
                "src/c0/c0_0bdc_load_horizontal_movement_map_strip_payload.asm",
                "src/c4/your_sanctuary_tile_arrangement_helpers.asm",
            ),
            fields=D7_SECTOR_TILESET_PALETTE_FIELDS,
        ),
        Contract(
            id="D7_SECTOR_CONTEXT_WORD_TABLE",
            domain="rom-table",
            address="D7:B200",
            stride=0x02,
            count=1280,
            struct_name="map_sector_context_word",
            confidence="consumer-corroborated-low3",
            note="40x32 sector context-word table. C0:0AA1 loads the full word to $438E; C0:2668 consumes the low three bits, which match map-sector Setting for every row.",
            evidence=(
                "notes/d7-sector-metadata-contracts.md",
                "notes/map-sector-bundles.md",
                "src/c0/c0_0aa1_lookup_position_cell_context_word.asm",
                "src/c0/c0_2668_resolve_spawn_probe_candidate_list.asm",
            ),
            fields=D7_SECTOR_CONTEXT_WORD_FIELDS,
        ),
        Contract(
            id="MAP_TILE_COLLISION_DATA",
            domain="rom-table",
            address="D8:0000",
            stride=0x10,
            count=2293,
            struct_name="map_tile_collision_record",
            confidence="consumer-corroborated",
            note="Contiguous pool of 16-byte metatile collision records; every D8 pointer-table entry resolves to one 4x4 surface/collision flag grid.",
            evidence=(
                "refs/ebsrc-main/ebsrc-main/src/bankconfig/common/bank18.asm",
                "notes/d8-table-splits.md",
                "notes/map-collision-pointer-contract.md",
                "notes/map-collision-runtime-bit-contract.md",
                "notes/d8-collision-subrecord-contracts.md",
            ),
            fields=MAP_TILE_COLLISION_ROW_FIELDS,
        ),
        Contract(
            id="MAP_DATA_TILE_COLLISION_PTR_TABLE",
            domain="rom-table",
            address="EF:117B",
            stride=0x04,
            count=20,
            struct_name="far_pointer",
            confidence="exact",
            note="20-entry long-pointer table anchoring the D8 tileset collision pointer-table family.",
            evidence=(
                "refs/ebsrc-main/ebsrc-main/src/bankconfig/US/bank2f.asm",
                "notes/d8-table-splits.md",
                "notes/landing-hdma-dispatch-family-ef117b-c00d7e.md",
            ),
            fields=FAR_POINTER_FIELDS,
        ),
        *d8_collision_pointer_contracts(),
        Contract(
            id="MAP_PALETTE_POINTER_TABLE",
            domain="rom-table",
            address="DA:FAA7",
            stride=0x03,
            count=32,
            struct_name="snes_long_pointer24",
            confidence="verified",
            note="Thirty-two 24-bit pointers to the bank DA map-palette payloads; each entry matches the corresponding MAP_DATA_PALETTE_N asset.",
            evidence=(
                "notes/bank-da-asset-data-map.md",
                "notes/map-palette-pointer-table-contract.md",
                "notes/map-palette-descriptor-context.md",
            ),
            fields=SNES_LONG_POINTER24_FIELDS,
        ),
        Contract(
            id="DA_MAP_PALETTE_VARIANT_TABLE",
            domain="rom-table",
            address="DA:7CA7",
            stride=0xC0,
            count=168,
            struct_name="da_map_palette_variant",
            confidence="tool-and-script-corroborated",
            note="Contiguous physical DA map-palette variant rows. Each row is six 16-colour SNES BGR555 subpalettes; the first words of subpalettes 0..3 carry raw-ROM metadata that matches map_palette_settings and is zeroed in .fts visual rows.",
            evidence=(
                "notes/da-map-palette-subrecord-contracts.md",
                "notes/map-fts-palette-variant-contract.md",
                "notes/map-palette-pointer-table-contract.md",
                "notes/map-palette-descriptor-context.md",
                "notes/map-palette-command-usage-contract.md",
            ),
            fields=DA_MAP_PALETTE_VARIANT_FIELDS,
        ),
        Contract(
            id="PER_SECTOR_MUSIC_TABLE",
            domain="rom-table",
            address="DC:D637",
            stride=0x02,
            count=1280,
            struct_name="per_sector_music_options_index",
            confidence="structural-corroborated",
            note="40x32 sector-indexed music-options table used by the map sector bundle inventory. The overlapping C0 byte-indexed selector plane is tracked separately as CURRENT_POSITION_EVENT_MUSIC_SELECTOR_TABLE.",
            evidence=(
                "notes/bank-dc-asset-data-map.md",
                "notes/map-sector-bundles.md",
                "tools/build_map_sector_bundle_contract.py",
            ),
            fields=PER_SECTOR_MUSIC_FIELDS,
        ),
        Contract(
            id="CURRENT_POSITION_EVENT_MUSIC_SELECTOR_TABLE",
            domain="rom-table",
            address="DC:D637",
            stride=0x01,
            count=1280,
            struct_name="current_position_event_music_context_selector",
            confidence="consumer-corroborated",
            note="The byte-indexed first plane of DC:D637..DC:E036. C0:68F4 computes sector_y*32 + sector_x, reads this byte, and uses it as the selector into CF:58EF.",
            evidence=(
                "notes/cf-event-music-context-contracts.md",
                "notes/c0-current-position-music-refresh-c068f4-c069af.md",
                "src/c0/c0_65c2_probe_type6_door_candidate.asm",
                "src/ef/ef_dcbc_de1a_debug_check_position_overlay.asm",
            ),
            fields=CURRENT_POSITION_EVENT_MUSIC_SELECTOR_FIELDS,
        ),
        Contract(
            id="LANDING_PALETTE_ANIM_PROFILE_POINTER_TABLE",
            domain="rom-table",
            address="DF:E4E1",
            stride=0x04,
            count=31,
            struct_name="far_pointer",
            confidence="runtime-corroborated",
            note="Thirty-one long pointers from landing palette/profile selector ($02A0 - 1) to DF:E55D..DF:E61B profile records.",
            evidence=(
                "notes/bank-df-first-pass.md",
                "notes/landing-profile-cache-436e-4474.md",
                "src/c0/c0_023f_build_landing_profile_step_sequencer.asm",
            ),
            fields=FAR_POINTER_FIELDS,
        ),
        *landing_palette_anim_profile_contracts(),
        *landing_palette_anim_payload_contracts(),
        Contract(
            id="TEXT_WINDOW_FLAVOR_SELECTOR_TABLE",
            domain="rom-table",
            address="E0:1FB9",
            stride=0x03,
            count=5,
            struct_name="text_window_flavor_selector",
            confidence="runtime-corroborated",
            note="Five selectable text-window flavour rows; C4:7F87 and C1:9D49 use the low word as an offset from E0:1FC8.",
            evidence=(
                "notes/text-window-skin-bundle-contracts.md",
                "notes/ui-font-town-map-asset-contracts.md",
            ),
            fields=TEXT_WINDOW_FLAVOR_SELECTOR_FIELDS,
        ),
        Contract(
            id="TEXT_WINDOW_PALETTE_BLOCKS",
            domain="rom-table",
            address="E0:1FC8",
            stride=0x40,
            count=7,
            struct_name="text_window_palette_block",
            confidence="runtime-corroborated",
            note="Seven 0x40-byte text-window palette blocks; blocks 0..4 are selectable, block 5 is the lead-entity override, and block 6 is preserved as nonselectable/extra.",
            evidence=(
                "notes/text-window-skin-bundle-contracts.md",
                "notes/ui-font-town-map-asset-contracts.md",
            ),
            fields=WINDOW_PALETTE_BLOCK_FIELDS,
        ),
        Contract(
            id="MOVEMENT_TEXT_STRING_PALETTE",
            domain="rom-table",
            address="E0:2188",
            stride=0x08,
            count=1,
            struct_name="four_colour_palette_row",
            confidence="structural-corroborated",
            note="Standalone four-colour movement-text palette row between the text-window palette blocks and the town-map pointer tail.",
            evidence=(
                "notes/text-window-skin-bundle-contracts.md",
                "notes/bank-e0-asset-data-map.md",
            ),
            fields=PALETTE_ROW_4_FIELDS,
        ),
        Contract(
            id="TOWN_MAP_GFX_POINTER_TABLE",
            domain="rom-table",
            address="E0:2190",
            stride=0x04,
            count=6,
            struct_name="far_pointer",
            confidence="runtime-corroborated",
            note="Six long pointers consumed by C4:D553 to decompress the selected E0 town-map graphics payload.",
            evidence=(
                "notes/text-window-skin-bundle-contracts.md",
                "notes/ui-font-town-map-asset-contracts.md",
                "notes/town-map-selection-rendering-c4d274-c4d744.md",
            ),
            fields=FAR_POINTER_FIELDS,
        ),
        Contract(
            id="TITLE_SCREEN_LETTER_OAM_RECORDS",
            domain="rom-table",
            address="E1:CE08",
            stride=0x2D,
            count=9,
            struct_name="title_screen_letter_oam_record",
            confidence="verified",
            note="Nine animated letter OAM record rows for EARTHOUND; each row contains nine 5-byte OAM-ish entries.",
            evidence=(
                "notes/title-screen-letter-oam-contracts.md",
                "notes/intro-title-visual-bundle-contracts.md",
                "notes/ui-font-town-map-asset-contracts.md",
            ),
            fields=TITLE_SCREEN_LETTER_OAM_RECORD_FIELDS,
        ),
        Contract(
            id="TITLE_SCREEN_LETTER_OAM_POINTER_TABLE",
            domain="rom-table",
            address="E1:CF9D",
            stride=0x02,
            count=9,
            struct_name="word_pointer",
            confidence="verified",
            note="Nine local pointers whose targets match the E1:CE08 title-screen letter OAM record starts.",
            evidence=("notes/title-screen-letter-oam-contracts.md",),
            fields=WORD_POINTER_FIELDS,
        ),
        Contract(
            id="PHOTOGRAPHER_CONFIG_TABLE",
            domain="rom-table",
            address="E1:2F8A",
            stride=0x3E,
            count=32,
            struct_name="photographer_config_record",
            confidence="consumer-corroborated-partial",
            note="Thirty-two photographer/photo-scene configuration records; named fields are limited to offsets read by C4 photo, credits, and current-slot consumers.",
            evidence=(
                "notes/bank-e1-asset-data-map.md",
                "notes/current-slot-position-staging-c46b8d-c46d4b.md",
                "src/c4/credits_photo_flag_counter.asm",
                "src/c4/credits_photograph_render_helpers.asm",
                "src/c4/credits_photograph_slide_helpers.asm",
            ),
            fields=PHOTOGRAPHER_CONFIG_FIELDS,
        ),
        Contract(
            id="TOWN_MAP_ICON_GRAPHIC_DESCRIPTOR_RECORDS",
            domain="rom-table",
            address="E1:F203",
            stride=0x05,
            count=117,
            struct_name="town_map_icon_graphic_descriptor",
            confidence="runtime-corroborated-shape",
            note="Five-byte town-map icon graphic descriptors split by the E1:F44C icon pointer table and consumed by C0:8C54/C0:8CD5.",
            evidence=(
                "notes/ui-font-town-map-asset-contracts.md",
                "notes/town-map-selection-rendering-c4d274-c4d744.md",
            ),
            fields=TOWN_MAP_ICON_GRAPHIC_DESCRIPTOR_FIELDS,
        ),
        Contract(
            id="TOWN_MAP_ICON_GRAPHIC_POINTER_TABLE",
            domain="rom-table",
            address="E1:F44C",
            stride=0x02,
            count=23,
            struct_name="word_pointer",
            confidence="runtime-corroborated",
            note="Twenty-three local pointers mapping town-map icon ids to E1:F203 five-byte graphic descriptor lists.",
            evidence=("notes/ui-font-town-map-asset-contracts.md",),
            fields=WORD_POINTER_FIELDS,
        ),
        Contract(
            id="TOWN_MAP_BLINK_SUPPRESS_TABLE",
            domain="rom-table",
            address="E1:F47A",
            stride=0x01,
            count=23,
            struct_name="town_map_blink_suppress_flag",
            confidence="runtime-corroborated",
            note="Town-map icon blink/suppression flags checked before static icon drawing.",
            evidence=("notes/ui-font-town-map-asset-contracts.md",),
            fields=BYTE_VALUE_FIELD,
        ),
        Contract(
            id="TOWN_MAP_ICON_PLACEMENT_POINTER_TABLE",
            domain="rom-table",
            address="E1:F491",
            stride=0x04,
            count=6,
            struct_name="far_pointer",
            confidence="runtime-corroborated",
            note="Six long pointers from selected town-map id to variable icon placement lists in E1:F4A9..E1:F581.",
            evidence=(
                "notes/ui-font-town-map-asset-contracts.md",
                "notes/town-map-selection-rendering-c4d274-c4d744.md",
            ),
            fields=FAR_POINTER_FIELDS,
        ),
        *town_map_icon_placement_list_contracts(),
        Contract(
            id="OVERWORLD_EVENT_MUSIC_POINTER_TABLE",
            domain="rom-table",
            address="CF:58EF",
            stride=0x02,
            count=165,
            struct_name="word_pointer",
            confidence="consumer-corroborated",
            note="Selector-indexed low-word pointers into the CF current-position event-music context chains; selector 0 is null and selectors 1..164 target CF:5A39..CF:61DC.",
            evidence=(
                "refs/eb-decompile-4ef92/map_music.yml",
                "notes/cf-table-splits.md",
                "notes/cf-event-music-context-contracts.md",
                "src/c0/c0_65c2_probe_type6_door_candidate.asm",
            ),
            fields=WORD_POINTER_FIELDS,
        ),
        Contract(
            id="OVERWORLD_EVENT_MUSIC_TABLE",
            domain="rom-variable-table",
            address="CF:5A39",
            stride=0x07A4,
            count=1,
            struct_name="overworld_event_music_rows",
            confidence="consumer-corroborated",
            note="Variable-length current-position event-music context chains ending at the inline bank0f byte block; each four-byte row is an event-condition/default row plus music-track and screen-transition-SFX bytes.",
            evidence=(
                "refs/eb-decompile-4ef92/map_music.yml",
                "notes/cf-table-splits.md",
                "notes/cf-event-music-context-contracts.md",
                "notes/c0-current-position-music-refresh-c068f4-c069af.md",
                "src/c0/c0_65c2_probe_type6_door_candidate.asm",
            ),
            fields=RAW_CF_EVENT_MUSIC_TABLE_FIELDS,
        ),
        Contract(
            id="CF_INLINE_EVENT_MUSIC_TRAILER",
            domain="rom-block",
            address="CF:61DD",
            stride=0x0A,
            count=1,
            struct_name="inline_event_music_trailer",
            confidence="exact",
            note="Inline ten-byte bank0f block between event music and sprite placement pointers.",
            evidence=(
                "refs/ebsrc-main/ebsrc-main/src/bankconfig/common/bank0f.asm",
                "notes/cf-table-splits.md",
            ),
            fields=RAW_CF_INLINE_EVENT_MUSIC_TRAILER_FIELDS,
        ),
        Contract(
            id="SPRITE_PLACEMENT_POINTER_TABLE",
            domain="rom-table",
            address="CF:61E7",
            stride=0x02,
            count=1280,
            struct_name="sprite_placement_sector_pointer",
            confidence="exact",
            note="40x32 sector pointer grid into the CF sprite placement table; zero means empty.",
            evidence=(
                "refs/eb-decompile-4ef92/map_sprites.yml",
                "notes/cf-table-splits.md",
                "notes/cf-sector-list-contracts.md",
            ),
            fields=SPRITE_PLACEMENT_POINTER_FIELDS,
        ),
        Contract(
            id="SPRITE_PLACEMENT_TABLE",
            domain="rom-variable-table",
            address="CF:6BE7",
            stride=0x1D9E,
            count=1,
            struct_name="sprite_placement_sector_list_block",
            confidence="exact-variable-lists",
            note="627 counted sprite-placement sector lists with complete decoded rows in notes/cf-sector-list-contracts.json; each four-byte row is npc_config_id plus sector-local Y/X placement bytes.",
            evidence=(
                "refs/ebsrc-main/ebsrc-main/include/structs.asm",
                "refs/eb-decompile-4ef92/map_sprites.yml",
                "notes/cf-table-splits.md",
                "notes/cf-sector-list-contracts.md",
                "notes/coilsnake-field-join-report.md",
            ),
            fields=RAW_CF_SPRITE_PLACEMENT_LIST_FIELDS,
        ),
        Contract(
            id="NPC_CONFIG_TABLE",
            domain="rom-table",
            address="CF:8985",
            stride=0x11,
            count=1584,
            struct_name="npc_config",
            confidence="corroborated",
            note="Fixed-size NPC configuration rows ending exactly at CF's audio tail.",
            evidence=(
                "refs/ebsrc-main/ebsrc-main/include/structs.asm",
                "refs/eb-decompile-4ef92/npc_config_table.yml",
                "notes/cf-table-splits.md",
            ),
            fields=NPC_CONFIG_FIELDS,
        ),
        Contract(
            id="BATTLE_SELECTION_SNAPSHOT",
            domain="wram-overlay",
            address="7E:9FFA",
            stride=0x4E,
            count=1,
            struct_name="battle_menu_selection_header_plus_snapshot",
            confidence="corroborated-overlay",
            note="Formal battle_menu_selection header at the front of a larger C2:B930 selected-slot snapshot overlay. This base overlaps BATTLERS_TABLE[1] in local address terms, so consumers should treat it as an overlay/scratch contract rather than an independent root.",
            evidence=(
                "refs/ebsrc-main/ebsrc-main/include/structs.asm",
                "notes/battle-selection-snapshot-export-c2b930.md",
                "notes/battle-targetting-resolver-c1adb4-af50.md",
            ),
            fields=BATTLE_SELECTION_SNAPSHOT_FIELDS,
        ),
        Contract(
            id="LOADED_BG_DATA_LAYER1",
            domain="wram-root",
            address="7E:ADD4",
            stride=0x77,
            count=1,
            struct_name="loaded_bg_data",
            confidence="corroborated",
            note="Layer 1 runtime state for battle background palette, scroll, and distortion effects.",
            evidence=(
                "refs/ebsrc-main/ebsrc-main/include/structs.asm",
                "refs/ebsrc-main/ebsrc-main/src/bankconfig/common/ram.asm",
                "notes/c2-battlebg-load-and-palette-effect-corridor-c2cfe5-c2e0e7.md",
            ),
            fields=LOADED_BG_DATA_FIELDS,
        ),
        Contract(
            id="LOADED_BG_DATA_LAYER2",
            domain="wram-root",
            address="7E:AE4B",
            stride=0x77,
            count=1,
            struct_name="loaded_bg_data",
            confidence="corroborated",
            note="Layer 2 runtime state for battle background palette, scroll, and distortion effects.",
            evidence=(
                "refs/ebsrc-main/ebsrc-main/include/structs.asm",
                "refs/ebsrc-main/ebsrc-main/src/bankconfig/common/ram.asm",
                "notes/c2-battlebg-load-and-palette-effect-corridor-c2cfe5-c2e0e7.md",
            ),
            fields=LOADED_BG_DATA_FIELDS,
        ),
        Contract(
            id="PATHFINDING_TILE_CONTEXT_GATE_TABLE",
            domain="rom-table",
            address="C3:DFE8",
            stride=0x01,
            count=8,
            struct_name="pathfinding_tile_context_gate",
            confidence="corroborated",
            note="Low-byte tile-context gate table consumed by C0:C0B4 and C0:C19B after C0:0AA1; zero aborts the path lane copy before pathfinding.",
            evidence=(
                "notes/pathfinding-consumers-direction-helpers-c0bd96-c0c7db.md",
                "notes/c3-late-interaction-table-contracts.md",
            ),
            fields=PATHFINDING_TILE_CONTEXT_GATE_FIELDS,
        ),
        Contract(
            id="INPUT_DIRECTION_PERMISSION_MASK_TABLE",
            domain="rom-table",
            address="C3:E12C",
            stride=0x02,
            count=14,
            struct_name="input_direction_permission_mask",
            confidence="corroborated",
            note="Direction permission mask table consumed by C0:404F MapInputToDirection.",
            evidence=(
                "notes/input-direction-and-interaction-probes-c0402b-c04116.md",
                "refs/earthbound-disasm-legacy/Earthbound Decomp/EB/Routine_Macros_EB.asm",
            ),
            fields=INPUT_DIRECTION_PERMISSION_MASK_FIELDS,
        ),
        Contract(
            id="INTERACTION_PROBE_DIRECTION_X_OFFSETS",
            domain="rom-table",
            address="C3:E148",
            stride=0x02,
            count=8,
            struct_name="signed_direction_offset_word",
            confidence="corroborated",
            note="Signed X probe offsets used by C0:4116 for one facing-direction interaction probe.",
            evidence=(
                "notes/input-direction-and-interaction-probes-c0402b-c04116.md",
                "notes/front-interaction-flow.md",
            ),
            fields=INTERACTION_PROBE_DIRECTION_OFFSET_FIELDS,
        ),
        Contract(
            id="INTERACTION_PROBE_DIRECTION_Y_OFFSETS",
            domain="rom-table",
            address="C3:E158",
            stride=0x02,
            count=8,
            struct_name="signed_direction_offset_word",
            confidence="corroborated",
            note="Signed Y probe offsets used by C0:4116 for one facing-direction interaction probe.",
            evidence=(
                "notes/input-direction-and-interaction-probes-c0402b-c04116.md",
                "notes/front-interaction-flow.md",
            ),
            fields=INTERACTION_PROBE_DIRECTION_OFFSET_FIELDS,
        ),
        Contract(
            id="INTERACTION_RESULT_FACING_REMAP_TABLE",
            domain="rom-table",
            address="C3:E168",
            stride=0x02,
            count=8,
            struct_name="interaction_result_facing_remap",
            confidence="corroborated",
            note="Facing/result-state remap consumed by C0:42C2; the selected word is stored to $2AF6[target] for class-1 interaction results.",
            evidence=(
                "notes/interaction-result-classes.md",
                "notes/interaction-result-consumers.md",
                "notes/c3-late-interaction-table-contracts.md",
            ),
            fields=INTERACTION_RESULT_FACING_REMAP_FIELDS,
        ),
        Contract(
            id="MAP_ENTITY_PLACEMENT_DIRECTION_PARAM_TABLE",
            domain="rom-table",
            address="C3:E1D8",
            stride=0x02,
            count=4,
            struct_name="map_entity_placement_direction_param",
            confidence="proposed",
            note="First word page consumed by the C0 entity placement path around C0:6D27/C0:6D91.",
            evidence=(
                "notes/c3-map-movement-parameter-table-e1d8-e240.md",
                "notes/staged-movement-wrapper-70cb.md",
            ),
            fields=C3_WORD_TABLE_VALUE_FIELD,
        ),
        Contract(
            id="MAP_ENTITY_PLACEMENT_DIRECTION_PARAM_TABLE_PAGE1",
            domain="rom-table",
            address="C3:E1E0",
            stride=0x02,
            count=16,
            struct_name="map_entity_placement_direction_param",
            confidence="proposed",
            note="Second word page in the C0 entity placement direction parameter family.",
            evidence=("notes/c3-map-movement-parameter-table-e1d8-e240.md",),
            fields=C3_WORD_TABLE_VALUE_FIELD,
        ),
        Contract(
            id="STAGED_MOVEMENT_PRIMARY_DIRECTION_PARAM_TABLE",
            domain="rom-table",
            address="C3:E200",
            stride=0x02,
            count=4,
            struct_name="staged_movement_direction_param",
            confidence="corroborated",
            note="Primary direction parameter words consumed by staged movement setup.",
            evidence=("notes/c3-map-movement-parameter-table-e1d8-e240.md",),
            fields=C3_WORD_TABLE_VALUE_FIELD,
        ),
        Contract(
            id="STAGED_MOVEMENT_ALTERNATE_DIRECTION_PARAM_TABLE",
            domain="rom-table",
            address="C3:E208",
            stride=0x02,
            count=4,
            struct_name="staged_movement_direction_param",
            confidence="corroborated",
            note="Alternate direction parameter words consumed by staged movement setup.",
            evidence=("notes/c3-map-movement-parameter-table-e1d8-e240.md",),
            fields=C3_WORD_TABLE_VALUE_FIELD,
        ),
        Contract(
            id="STAGED_MOVEMENT_SUBTILE_OFFSET_SET_A_X",
            domain="rom-table",
            address="C3:E210",
            stride=0x02,
            count=4,
            struct_name="signed_subtile_offset_word",
            confidence="corroborated",
            note="X offsets for staged movement subtile offset set A.",
            evidence=("notes/c3-map-movement-parameter-table-e1d8-e240.md",),
            fields=C3_WORD_TABLE_VALUE_FIELD,
        ),
        Contract(
            id="STAGED_MOVEMENT_SUBTILE_OFFSET_SET_A_Y",
            domain="rom-table",
            address="C3:E218",
            stride=0x02,
            count=4,
            struct_name="signed_subtile_offset_word",
            confidence="corroborated",
            note="Y offsets for staged movement subtile offset set A.",
            evidence=("notes/c3-map-movement-parameter-table-e1d8-e240.md",),
            fields=C3_WORD_TABLE_VALUE_FIELD,
        ),
        Contract(
            id="STAGED_MOVEMENT_SUBTILE_OFFSET_SET_B_X",
            domain="rom-table",
            address="C3:E220",
            stride=0x02,
            count=4,
            struct_name="signed_subtile_offset_word",
            confidence="corroborated",
            note="X offsets for staged movement subtile offset set B.",
            evidence=("notes/c3-map-movement-parameter-table-e1d8-e240.md",),
            fields=C3_WORD_TABLE_VALUE_FIELD,
        ),
        Contract(
            id="STAGED_MOVEMENT_SUBTILE_OFFSET_SET_B_Y",
            domain="rom-table",
            address="C3:E228",
            stride=0x02,
            count=4,
            struct_name="signed_subtile_offset_word",
            confidence="corroborated",
            note="Y offsets for staged movement subtile offset set B.",
            evidence=("notes/c3-map-movement-parameter-table-e1d8-e240.md",),
            fields=C3_WORD_TABLE_VALUE_FIELD,
        ),
        Contract(
            id="DOOR_CANDIDATE_DIRECTION_OFFSET_X",
            domain="rom-table",
            address="C3:E230",
            stride=0x02,
            count=8,
            struct_name="door_candidate_direction_offset_word",
            confidence="corroborated",
            note="X coarse-cell direction offsets consumed by C4:334A while probing cached door fallback candidates.",
            evidence=(
                "notes/c3-map-movement-parameter-table-e1d8-e240.md",
                "notes/c3-late-interaction-table-contracts.md",
            ),
            fields=DOOR_CANDIDATE_DIRECTION_OFFSET_FIELDS,
        ),
        Contract(
            id="DOOR_CANDIDATE_DIRECTION_OFFSET_Y",
            domain="rom-table",
            address="C3:E240",
            stride=0x02,
            count=8,
            struct_name="door_candidate_direction_offset_word",
            confidence="corroborated",
            note="Y coarse-cell direction offsets consumed by C4:334A while probing cached door fallback candidates.",
            evidence=(
                "notes/c3-map-movement-parameter-table-e1d8-e240.md",
                "notes/c3-late-interaction-table-contracts.md",
            ),
            fields=DOOR_CANDIDATE_DIRECTION_OFFSET_FIELDS,
        ),
        Contract(
            id="MENU_CURSOR_TILE_PREFIX_TABLE",
            domain="rom-table",
            address="C3:E3F8",
            stride=0x02,
            count=7,
            struct_name="menu_cursor_tile_prefix_word",
            confidence="proposed",
            note="Seven tile/attribute words before the legacy animated menu cursor right-pointing tile run.",
            evidence=("notes/c3-menu-cursor-tile-data-e3f8-e450.md",),
            fields=C3_WORD_TABLE_VALUE_FIELD,
        ),
        Contract(
            id="ANIMATED_MENU_CURSOR_POINT_RIGHT_TILES",
            domain="rom-table",
            address="C3:E406",
            stride=0x08,
            count=1,
            struct_name="four_tile_word_run",
            confidence="corroborated",
            note="Legacy AnimatedMenuCursorTiles.PointRight four-tile run.",
            evidence=(
                "notes/c3-menu-cursor-tile-data-e3f8-e450.md",
                "refs/earthbound-disasm-legacy/Earthbound Decomp/EB/Routine_Macros_EB.asm",
            ),
            fields=MENU_CURSOR_TILE_RUN_FIELDS,
        ),
        Contract(
            id="TITLE_NAME_BUFFER_CURSOR_TILE_RUN",
            domain="rom-table",
            address="C3:E40E",
            stride=0x08,
            count=1,
            struct_name="four_tile_word_run",
            confidence="corroborated",
            note="Four tile/attribute words copied by C2:0266 into the title/name upload buffer.",
            evidence=(
                "notes/c3-menu-cursor-tile-data-e3f8-e450.md",
                "notes/c2-window-hppp-and-menu-selection-helpers-c20266-c2108c.md",
            ),
            fields=MENU_CURSOR_TILE_RUN_FIELDS,
        ),
        Contract(
            id="BLINKING_TRIANGLE_BASE_TILES",
            domain="rom-table",
            address="C3:E416",
            stride=0x06,
            count=1,
            struct_name="three_tile_word_run",
            confidence="corroborated",
            note="Three base/down-cursor tile words immediately before the four blinking triangle wait frames.",
            evidence=("notes/c3-menu-cursor-tile-data-e3f8-e450.md",),
            fields=MENU_CURSOR_THREE_TILE_RUN_FIELDS,
        ),
        Contract(
            id="BLINKING_TRIANGLE_WAIT_FRAME_TILES",
            domain="rom-table",
            address="C3:E41C",
            stride=0x08,
            count=4,
            struct_name="four_tile_word_frame",
            confidence="corroborated",
            note="Four 4-word blinking/down cursor frames selected by the long pointer table at C3:E43C.",
            evidence=("notes/c3-menu-cursor-tile-data-e3f8-e450.md",),
            fields=MENU_CURSOR_TILE_RUN_FIELDS,
        ),
        Contract(
            id="BLINKING_TRIANGLE_WAIT_FRAME_POINTER_TABLE",
            domain="rom-table",
            address="C3:E43C",
            stride=0x04,
            count=4,
            struct_name="far_pointer",
            confidence="corroborated",
            note="Long pointers selecting the four blinking triangle wait frames at C3:E41C/C3:E424/C3:E42C/C3:E434.",
            evidence=("notes/c3-menu-cursor-tile-data-e3f8-e450.md",),
            fields=FAR_POINTER_FIELDS,
        ),
        Contract(
            id="WINDOW_TICK_TRANSFER_PRELUDE_WORDS",
            domain="rom-table",
            address="C3:E44C",
            stride=0x02,
            count=2,
            struct_name="window_tick_transfer_prelude_word",
            confidence="proposed",
            note="Two-word data island immediately before the C3:E450 window tick transfer helper.",
            evidence=(
                "notes/c3-menu-cursor-tile-data-e3f8-e450.md",
                "notes/active-text-entry-chain-layout-c451fa.md",
            ),
            fields=C3_WORD_TABLE_VALUE_FIELD,
        ),
        Contract(
            id="BATTLE_PSI_MENU_SELECTOR_GROUP_TABLE",
            domain="rom-table",
            address="C3:EF26",
            stride=0x01,
            count=0xF0,
            struct_name="battle_psi_menu_selector_group",
            confidence="corroborated",
            note="Selector-minus-0x10 byte table consumed by C1:C046; zero means print the raw selector, nonzero selects a grouped PSI-list row.",
            evidence=(
                "notes/battle-psi-menu-table-helpers-c1c046-c1c165.md",
                "notes/c3-battle-psi-menu-data-contracts.md",
            ),
            fields=BYTE_VALUE_FIELD,
        ),
        Contract(
            id="BATTLE_PSI_MENU_GROUP_SLICE_COUNT_TABLE",
            domain="rom-table",
            address="C3:F016",
            stride=0x01,
            count=0x3E,
            struct_name="battle_psi_menu_group_slice_count",
            confidence="corroborated",
            note="Grouped PSI-list slice count/width byte indexed after the C3:EF26 selector-group remap.",
            evidence=(
                "notes/battle-psi-menu-table-helpers-c1c046-c1c165.md",
                "notes/c3-shared-helper-working-name-promotion.md",
                "notes/c3-battle-psi-menu-data-contracts.md",
            ),
            fields=BYTE_VALUE_FIELD,
        ),
        Contract(
            id="BATTLE_PSI_GROUP_RENDER_METADATA_AND_LABELS",
            domain="rom-block",
            address="C3:F054",
            stride=0x5C,
            count=1,
            struct_name="battle_psi_group_render_metadata_and_labels",
            confidence="proposed",
            note="Raw render metadata and encoded labels between the PSI selector-group slice table and the known-state gate table.",
            evidence=(
                "notes/c3-shared-helper-working-name-promotion.md",
                "notes/c3-battle-psi-menu-data-contracts.md",
            ),
            fields=BATTLE_PSI_GROUP_RENDER_METADATA_FIELDS,
        ),
        Contract(
            id="BATTLE_PSI_KNOWN_STATE_GATE_TABLE",
            domain="rom-table",
            address="C3:F0B0",
            stride=0x0E,
            count=7,
            struct_name="battle_psi_known_state_gate_row",
            confidence="corroborated",
            note="Seven 7-word live PSI-state gate rows consumed by C1:C165 while scanning a character's live PSI bytes.",
            evidence=(
                "notes/battle-psi-menu-table-helpers-c1c046-c1c165.md",
                "notes/c3-battle-psi-menu-data-contracts.md",
            ),
            fields=BATTLE_PSI_KNOWN_STATE_GATE_ROW_FIELDS,
        ),
        Contract(
            id="BATTLE_PSI_RANK_SUFFIX_TABLE",
            domain="rom-table",
            address="C3:F112",
            stride=0x02,
            count=5,
            struct_name="battle_psi_rank_suffix_token",
            confidence="corroborated",
            note="Five PSI rank/suffix token words used by the PSI name/menu row formatting family.",
            evidence=(
                "notes/battle-psi-name-builder-family-c1c8bc-ca06-c3f112-f124.md",
                "notes/c3-shared-helper-working-name-promotion.md",
                "notes/c3-battle-psi-menu-data-contracts.md",
            ),
            fields=C3_WORD_TABLE_VALUE_FIELD,
        ),
        Contract(
            id="BATTLE_PSI_MENU_ENTRY_FIXED_TAIL",
            domain="rom-block",
            address="C3:F11C",
            stride=0x08,
            count=1,
            struct_name="battle_psi_menu_entry_fixed_tail",
            confidence="corroborated",
            note="Eight encoded bytes appended after a formatted PSI menu-entry row.",
            evidence=(
                "notes/battle-psi-name-builder-family-c1c8bc-ca06-c3f112-f124.md",
                "notes/c3-shared-helper-working-name-promotion.md",
                "notes/c3-battle-psi-menu-data-contracts.md",
            ),
            fields=BATTLE_PSI_MENU_ENTRY_FIXED_TAIL_FIELDS,
        ),
        Contract(
            id="BATTLE_PSI_MENU_ENTRY_ROW_TABLE",
            domain="rom-table",
            address="C3:F124",
            stride=0x14,
            count=10,
            struct_name="battle_psi_menu_entry_row",
            confidence="corroborated",
            note="Ten fixed-width encoded PSI menu-entry text rows.",
            evidence=(
                "notes/battle-psi-name-builder-family-c1c8bc-ca06-c3f112-f124.md",
                "notes/c3-shared-helper-working-name-promotion.md",
                "notes/c3-battle-psi-menu-data-contracts.md",
            ),
            fields=BATTLE_PSI_MENU_ENTRY_ROW_FIELDS,
        ),
        Contract(
            id="LEVEL_UP_STAT_GROWTH_VARIANCE_TABLE",
            domain="rom-table",
            address="C3:F2B1",
            stride=0x01,
            count=4,
            struct_name="level_up_stat_growth_variance",
            confidence="corroborated",
            note="Four-byte variance table consumed by C1:D08B while computing level-up stat growth deltas.",
            evidence=(
                "notes/level-up-stat-growth-helper-c1d08b.md",
                "notes/c3-battle-visual-data-and-file-select-transition-split.md",
            ),
            fields=LEVEL_UP_STAT_GROWTH_VARIANCE_FIELDS,
        ),
        Contract(
            id="VISUAL_SELECTOR_POSE_ROW_TABLE",
            domain="rom-table",
            address="C3:F2B5",
            stride=0x10,
            count=17,
            struct_name="visual_selector_pose_row",
            confidence="corroborated",
            note="Seventeen 8-word pose-resolution rows consumed by C0:780F/C0:79EC to map higher-level visual selectors to concrete pose indices.",
            evidence=(
                "notes/visual-selector-family-c0780f-c3f2b5.md",
                "notes/position-derived-visual-context-class-9887.md",
                "notes/c3-battle-visual-data-and-file-select-transition-split.md",
            ),
            fields=VISUAL_SELECTOR_POSE_ROW_FIELDS,
        ),
        Contract(
            id="BATTLE_VISUAL_GRAPHICS_SOURCE_STRIP_OFFSETS",
            domain="rom-table",
            address="C3:F871",
            stride=0x08,
            count=8,
            struct_name="battle_visual_strip_offset_page",
            confidence="corroborated",
            note="Eight pages of four source-strip offsets into the $7F:0000 battle visual work buffer.",
            evidence=(
                "notes/c3-battle-visual-offset-tables-f871-f8f1.md",
                "notes/c3-battle-visual-table-and-token-sublabels.md",
            ),
            fields=BATTLE_VISUAL_STRIP_OFFSET_FIELDS,
        ),
        Contract(
            id="BATTLE_VISUAL_OAM_TILE_INDEX_GRID",
            domain="rom-table",
            address="C3:F8B1",
            stride=0x10,
            count=4,
            struct_name="battle_visual_oam_tile_index_row",
            confidence="corroborated",
            note="Four-row OAM tile-index grid consumed by the C2 battle visual sprite renderer.",
            evidence=(
                "notes/c3-battle-visual-offset-tables-f871-f8f1.md",
                "notes/c3-battle-visual-table-and-token-sublabels.md",
            ),
            fields=BATTLE_VISUAL_OAM_TILE_GRID_FIELDS,
        ),
        Contract(
            id="BATTLE_PALETTE_SET_ROWS",
            domain="rom-table",
            address="C3:F8F1",
            stride=0x20,
            count=3,
            struct_name="rgb555_palette_row",
            confidence="corroborated",
            note="Three confirmed 16-colour palette rows selected by C2:FEF9.",
            evidence=(
                "notes/c3-battle-visual-offset-tables-f871-f8f1.md",
                "notes/c3-battle-visual-table-and-token-sublabels.md",
            ),
            fields=BATTLE_PALETTE_ROW_FIELDS,
        ),
        Contract(
            id="BATTLE_VISUAL_TOKEN_23_TO_2D_COLOUR_TRIPLES",
            domain="rom-table",
            address="C3:F951",
            stride=0x03,
            count=11,
            struct_name="battle_visual_fixed_colour_triple",
            confidence="corroborated",
            note="RGB component triples for visual tokens #$23..#$2D.",
            evidence=("notes/c3-battle-visual-table-and-token-sublabels.md",),
            fields=BATTLE_VISUAL_COLOUR_TRIPLE_FIELDS,
        ),
        Contract(
            id="BATTLE_VISUAL_TOKEN_31_TO_35_COLOUR_TRIPLES",
            domain="rom-table",
            address="C3:F972",
            stride=0x03,
            count=5,
            struct_name="battle_visual_fixed_colour_triple",
            confidence="corroborated",
            note="RGB component triples for visual tokens #$31..#$35.",
            evidence=("notes/c3-battle-visual-table-and-token-sublabels.md",),
            fields=BATTLE_VISUAL_COLOUR_TRIPLE_FIELDS,
        ),
        Contract(
            id="BLANK_COMMON_TILE_SOURCE_BLOCK",
            domain="rom-table",
            address="C4:0BE8",
            stride=0x200,
            count=1,
            struct_name="blank_common_tile_source_block",
            confidence="corroborated",
            note="Zero-filled C4 source block used by setup/visual paths as a common blank graphics or tile-memory seed.",
            evidence=(
                "notes/landing-and-coffee-tea-visual-helpers-c492d2-c49d1e.md",
                "notes/bank-c4-progress-audit.md",
            ),
            fields=BLANK_COMMON_TILE_SOURCE_FIELDS,
        ),
        Contract(
            id="WH_WINDOW_SPAN_RADIUS_RAMP_TABLE",
            domain="rom-table",
            address="C4:74F6",
            stride=0x01,
            count=11,
            struct_name="wh_window_span_radius_ramp_entry",
            confidence="corroborated",
            note="Half-width/radius bytes indexed in reverse by C4:7501 while generating tapered WH window spans.",
            evidence=("notes/window-mask-and-indexed-gfx-c47501-c47b77.md",),
            fields=C4_BYTE_VALUE_FIELD,
        ),
        Contract(
            id="MOVEMENT_OCTANT_TO_PULSE_SELECTOR_TABLE",
            domain="rom-table",
            address="C4:8C59",
            stride=0x02,
            count=8,
            struct_name="movement_octant_pulse_selector",
            confidence="corroborated",
            note="Eight word selectors mapping rounded movement octants to generated movement pulse ids.",
            evidence=("notes/staged-movement-pulse-and-tracked-item-registry-c48c59-c48f98.md",),
            fields=C4_WORD_VALUE_FIELD,
        ),
        Contract(
            id="MOVEMENT_OCTANT_SIGNED_UNIT_DELTA_TABLE",
            domain="rom-table",
            address="C4:8D38",
            stride=0x20,
            count=1,
            struct_name="movement_octant_signed_unit_delta_components",
            confidence="proposed",
            note="Sixteen signed words forming two eight-entry unit-delta component arrays adjacent to the staged movement builder.",
            evidence=("notes/staged-movement-pulse-and-tracked-item-registry-c48c59-c48f98.md",),
            fields=MOVEMENT_OCTANT_SIGNED_UNIT_DELTA_FIELDS,
        ),
        Contract(
            id="YOUR_SANCTUARY_LOCATION_COORDINATE_TABLE",
            domain="rom-table",
            address="C4:DE78",
            stride=0x04,
            count=8,
            struct_name="your_sanctuary_location_coordinate_pair",
            confidence="corroborated",
            note="Eight two-word coordinate/source records consumed by the Your Sanctuary display loader at C4:E281.",
            evidence=("notes/your-sanctuary-location-coordinate-table-c4de78.md",),
            fields=YOUR_SANCTUARY_LOCATION_COORDINATE_FIELDS,
        ),
    ]


def field_to_json(spec: FieldSpec) -> dict[str, object]:
    data: dict[str, object] = {
        "name": spec.name,
        "offset": spec.offset,
        "offset_hex": f"0x{spec.offset:X}",
        "size": spec.size,
    }
    if spec.count != 1:
        data["count"] = spec.count
    if spec.note:
        data["note"] = spec.note
    if spec.element_names:
        data["element_names"] = list(spec.element_names)
    return data


def contract_to_json(contract: Contract) -> dict[str, object]:
    data: dict[str, object] = {
        "id": contract.id,
        "domain": contract.domain,
        "address": contract.address,
        "stride": contract.stride,
        "stride_hex": f"0x{contract.stride:X}",
        "struct": contract.struct_name,
        "confidence": contract.confidence,
        "note": contract.note,
        "evidence": list(contract.evidence),
        "fields": [field_to_json(spec) for spec in contract.fields],
    }
    if contract.count is not None:
        data["count"] = contract.count
    return data


def build_manifest() -> dict[str, object]:
    contracts = root_contracts() + extra_contracts()
    domains = Counter(contract.domain for contract in contracts)
    field_count = sum(len(contract.fields) for contract in contracts)
    return {
        "schema": SCHEMA,
        "summary": {
            "contracts": len(contracts),
            "fields": field_count,
            "by_domain": dict(sorted(domains.items())),
        },
        "contracts": [contract_to_json(contract) for contract in contracts],
    }


def markdown_escape(text: str) -> str:
    return text.replace("|", "\\|")


def evidence_label(text: str) -> str:
    if text.startswith("CoilSnake "):
        return "CoilSnake `" + text.removeprefix("CoilSnake ") + "`"
    return f"`{text}`"


def render_markdown(manifest: dict[str, object]) -> str:
    contracts = manifest["contracts"]
    assert isinstance(contracts, list)
    summary = manifest["summary"]
    assert isinstance(summary, dict)

    lines = [
        "# Cross-bank data contract manifest",
        "",
        "Generated from local notes plus quarantined reference structs. This is the machine-readable struct/table front door for source and data emission work; edit `tools/build_data_contract_manifest.py`, then regenerate this file.",
        "",
        "## Summary",
        "",
        f"- schema: `{manifest['schema']}`",
        f"- contracts: `{summary['contracts']}`",
        f"- fields: `{summary['fields']}`",
        "",
        "| Contract | Domain | Address | Stride | Count | Struct | Fields | Confidence |",
        "| --- | --- | --- | ---: | ---: | --- | ---: | --- |",
    ]

    for contract in contracts:
        assert isinstance(contract, dict)
        count = contract.get("count", "")
        lines.append(
            "| {id} | {domain} | `{address}` | `{stride}` | {count} | `{struct}` | {fields} | {confidence} |".format(
                id=markdown_escape(str(contract["id"])),
                domain=markdown_escape(str(contract["domain"])),
                address=contract["address"],
                stride=contract["stride_hex"],
                count=count,
                struct=contract["struct"],
                fields=len(contract["fields"]),
                confidence=contract["confidence"],
            )
        )

    lines.extend(["", "## Contracts", ""])

    for contract in contracts:
        assert isinstance(contract, dict)
        lines.extend(
            [
                f"### {contract['id']}",
                "",
                f"- domain: `{contract['domain']}`",
                f"- address: `{contract['address']}`",
                f"- stride: `{contract['stride_hex']}`",
                f"- count: `{contract.get('count', 'unknown')}`",
                f"- struct: `{contract['struct']}`",
                f"- confidence: `{contract['confidence']}`",
                f"- note: {contract['note']}",
                f"- evidence: {', '.join(evidence_label(str(item)) for item in contract['evidence'])}",
                "",
                "| Offset | Field | Size | Count | Note |",
                "| ---: | --- | ---: | ---: | --- |",
            ]
        )
        for spec in contract["fields"]:
            assert isinstance(spec, dict)
            lines.append(
                "| `{offset}` | `{name}` | {size} | {count} | {note} |".format(
                    offset=spec["offset_hex"],
                    name=markdown_escape(str(spec["name"])),
                    size=spec["size"],
                    count=spec.get("count", 1),
                    note=markdown_escape(str(spec.get("note", ""))),
                )
            )
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build the cross-bank data contract manifest.")
    parser.add_argument("--json-out", default="build/data-contracts-c0-c4.json")
    parser.add_argument("--markdown-out", default="notes/data-contracts-c0-c4.md")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    manifest = build_manifest()

    json_path = Path(args.json_out)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    markdown_path = Path(args.markdown_out)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text(render_markdown(manifest), encoding="utf-8")

    summary = manifest["summary"]
    assert isinstance(summary, dict)
    print(
        f"Wrote {json_path} and {markdown_path} "
        f"({summary['contracts']} contracts, {summary['fields']} fields)"
    )


if __name__ == "__main__":
    main()
