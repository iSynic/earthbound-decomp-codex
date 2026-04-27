# DD byte-equivalence validation

This report assembles an existing durable Asar source-bank scaffold into a clean ROM copy, then compares the protected byte ranges against the original ROM.

- status: `OK`
- mode: `durable-scaffold`
- modules: `8`
- non-OK modules: `0`
- mismatches: `0`

## Modules

| Status | Source Path | Range | Size | Mismatches | Generated ASM |
| --- | --- | --- | ---: | ---: | --- |
| `OK` | `src/dd/asset_map_data_tile_set_graphics_0.asm` | `DD:0000..DD:3294` | 12948 | 0 | `src/dd/bank_dd_helpers_asar.asm` |
| `OK` | `src/dd/asset_map_data_tile_set_graphics_1.asm` | `DD:3294..DD:5F17` | 11395 | 0 | `src/dd/bank_dd_helpers_asar.asm` |
| `OK` | `src/dd/asset_map_data_tile_set_graphics_9.asm` | `DD:5F17..DD:89A2` | 10891 | 0 | `src/dd/bank_dd_helpers_asar.asm` |
| `OK` | `src/dd/asset_map_data_tile_set_graphics_3.asm` | `DD:89A2..DD:B7D1` | 11823 | 0 | `src/dd/bank_dd_helpers_asar.asm` |
| `OK` | `src/dd/asset_map_data_tile_set_graphics_4.asm` | `DD:B7D1..DD:DF3B` | 10090 | 0 | `src/dd/bank_dd_helpers_asar.asm` |
| `OK` | `src/dd/asset_map_data_tile_set_graphics_5.asm` | `DD:DF3B..DD:FECE` | 8083 | 0 | `src/dd/bank_dd_helpers_asar.asm` |
| `OK` | `src/dd/asset_audio_pack_75.asm` | `DD:FECE..DD:FFF8` | 298 | 0 | `src/dd/bank_dd_helpers_asar.asm` |
| `OK` | `src/dd/asset_bank_dd_gap_1_tailpadding.asm` | `DD:FFF8..DD:10000` | 8 | 0 | `src/dd/bank_dd_helpers_asar.asm` |
