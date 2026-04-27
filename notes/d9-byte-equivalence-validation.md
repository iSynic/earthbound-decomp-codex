# D9 byte-equivalence validation

This report assembles an existing durable Asar source-bank scaffold into a clean ROM copy, then compares the protected byte ranges against the original ROM.

- status: `OK`
- mode: `durable-scaffold`
- modules: `7`
- non-OK modules: `0`
- mismatches: `0`

## Modules

| Status | Source Path | Range | Size | Mismatches | Generated ASM |
| --- | --- | --- | ---: | ---: | --- |
| `OK` | `src/d9/asset_map_data_tile_arrangement_1.asm` | `D9:0000..D9:34E9` | 13545 | 0 | `src/d9/bank_d9_helpers_asar.asm` |
| `OK` | `src/d9/asset_map_data_tile_arrangement_2.asm` | `D9:34E9..D9:68AB` | 13250 | 0 | `src/d9/bank_d9_helpers_asar.asm` |
| `OK` | `src/d9/asset_map_data_tile_arrangement_3.asm` | `D9:68AB..D9:8DD5` | 9514 | 0 | `src/d9/bank_d9_helpers_asar.asm` |
| `OK` | `src/d9/asset_map_data_tile_arrangement_4.asm` | `D9:8DD5..D9:CE52` | 16509 | 0 | `src/d9/bank_d9_helpers_asar.asm` |
| `OK` | `src/d9/asset_map_data_tile_set_graphics_13.asm` | `D9:CE52..D9:FC18` | 11718 | 0 | `src/d9/bank_d9_helpers_asar.asm` |
| `OK` | `src/d9/asset_audio_pack_45.asm` | `D9:FC18..D9:FFE1` | 969 | 0 | `src/d9/bank_d9_helpers_asar.asm` |
| `OK` | `src/d9/asset_bank_d9_gap_1_tailpadding.asm` | `D9:FFE1..D9:10000` | 31 | 0 | `src/d9/bank_d9_helpers_asar.asm` |
