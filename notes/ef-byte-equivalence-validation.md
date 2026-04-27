# EF byte-equivalence validation

This report assembles an existing durable Asar source-bank scaffold into a clean ROM copy, then compares the protected byte ranges against the original ROM.

- status: `OK`
- mode: `durable-scaffold`
- modules: `7`
- non-OK modules: `0`
- mismatches: `0`

## Modules

| Status | Source Path | Range | Size | Mismatches | Generated ASM |
| --- | --- | --- | ---: | ---: | --- |
| `OK` | `src/ef/ef_0000_0ca7_front_preserved_corridor.asm` | `EF:0000..EF:0CA7` | 3239 | 0 | `src/ef/bank_ef_helpers_asar.asm` |
| `OK` | `src/ef/ef_0ca7_delivery_selector_helper_cluster.asm` | `EF:0CA7..EF:101B` | 884 | 0 | `src/ef/bank_ef_helpers_asar.asm` |
| `OK` | `src/ef/ef_101b_eb5f_map_text_debug_preserved_corridor.asm` | `EF:101B..EF:EB5F` | 56132 | 0 | `src/ef/bank_ef_helpers_asar.asm` |
| `OK` | `src/ef/asset_debug_menu_font.asm` | `EF:EB5F..EF:EF70` | 1041 | 0 | `src/ef/bank_ef_helpers_asar.asm` |
| `OK` | `src/ef/table_141_data_unknown_efef70_asm.asm` | `EF:EF70..EF:EFB7` | 71 | 0 | `src/ef/bank_ef_helpers_asar.asm` |
| `OK` | `src/ef/asset_debug_cursor_graphics.asm` | `EF:EFB7..EF:F0D7` | 288 | 0 | `src/ef/bank_ef_helpers_asar.asm` |
| `OK` | `src/ef/asset_bank_ef_gap_1_tailpadding.asm` | `EF:F0D7..EF:10000` | 3881 | 0 | `src/ef/bank_ef_helpers_asar.asm` |
