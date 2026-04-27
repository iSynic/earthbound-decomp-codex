# E0 byte-equivalence validation

This report assembles an existing durable Asar source-bank scaffold into a clean ROM copy, then compares the protected byte ranges against the original ROM.

- status: `OK`
- mode: `durable-scaffold`
- modules: `16`
- non-OK modules: `0`
- mismatches: `0`

## Modules

| Status | Source Path | Range | Size | Mismatches | Generated ASM |
| --- | --- | --- | ---: | ---: | --- |
| `OK` | `src/e0/asset_text_window_gfx.asm` | `E0:0000..E0:0754` | 1876 | 0 | `src/e0/bank_e0_helpers_asar.asm` |
| `OK` | `src/e0/asset_flavoured_text_gfx.asm` | `E0:0754..E0:07A0` | 76 | 0 | `src/e0/bank_e0_helpers_asar.asm` |
| `OK` | `src/e0/asset_mother2_romaji_font.asm` | `E0:07A0..E0:09B4` | 532 | 0 | `src/e0/bank_e0_helpers_asar.asm` |
| `OK` | `src/e0/asset_compressed_sram.asm` | `E0:09B4..E0:1359` | 2469 | 0 | `src/e0/bank_e0_helpers_asar.asm` |
| `OK` | `src/e0/asset_mrsaturn_font_data.asm` | `E0:1359..E0:13B9` | 96 | 0 | `src/e0/bank_e0_helpers_asar.asm` |
| `OK` | `src/e0/asset_mrsaturn_font_gfx.asm` | `E0:13B9..E0:1FB9` | 3072 | 0 | `src/e0/bank_e0_helpers_asar.asm` |
| `OK` | `src/e0/table_006_data_text_window_properties_asm.asm` | `E0:1FB9..E0:21A8` | 495 | 0 | `src/e0/bank_e0_helpers_asar.asm` |
| `OK` | `src/e0/asset_town_map_onett.asm` | `E0:21A8..E0:4920` | 10104 | 0 | `src/e0/bank_e0_helpers_asar.asm` |
| `OK` | `src/e0/asset_town_map_twoson.asm` | `E0:4920..E0:6721` | 7681 | 0 | `src/e0/bank_e0_helpers_asar.asm` |
| `OK` | `src/e0/asset_town_map_threed.asm` | `E0:6721..E0:8379` | 7256 | 0 | `src/e0/bank_e0_helpers_asar.asm` |
| `OK` | `src/e0/asset_town_map_fourside.asm` | `E0:8379..E0:ADB4` | 10811 | 0 | `src/e0/bank_e0_helpers_asar.asm` |
| `OK` | `src/e0/asset_town_map_scaraba.asm` | `E0:ADB4..E0:C7F1` | 6717 | 0 | `src/e0/bank_e0_helpers_asar.asm` |
| `OK` | `src/e0/asset_town_map_summers.asm` | `E0:C7F1..E0:ED03` | 9490 | 0 | `src/e0/bank_e0_helpers_asar.asm` |
| `OK` | `src/e0/asset_audio_pack_110.asm` | `E0:ED03..E0:FCE1` | 4062 | 0 | `src/e0/bank_e0_helpers_asar.asm` |
| `OK` | `src/e0/asset_audio_pack_6.asm` | `E0:FCE1..E0:FFB3` | 722 | 0 | `src/e0/bank_e0_helpers_asar.asm` |
| `OK` | `src/e0/asset_bank_e0_gap_1_tailpadding.asm` | `E0:FFB3..E0:10000` | 77 | 0 | `src/e0/bank_e0_helpers_asar.asm` |
