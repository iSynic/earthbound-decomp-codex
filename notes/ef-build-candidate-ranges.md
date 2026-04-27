# EF build-candidate byte ranges

This manifest records source slices promoted into the reusable source-bank scaffold pipeline.

## Summary

- ranges: `5`
- total bytes: `65536`
- source bytes: `65536`
- data gap bytes: `0`

## Ranges

| Level | Source Path | Range | Span Bytes | Source Bytes | Data Gap Bytes | SHA-1 |
| --- | --- | --- | ---: | ---: | ---: | --- |
| `build-candidate` | `src/ef/table_002_unknown_ef_ef00bb_asm.asm` | `EF:0000..EF:EB5F` | 60255 | 60255 | 0 | `72ac26c6a5d4500126dda954e33cace132286a4c` |
| `build-candidate` | `src/ef/asset_debug_menu_font.asm` | `EF:EB5F..EF:EF70` | 1041 | 1041 | 0 | `7d8195145f270d5d310df09b7c73a32cca868614` |
| `build-candidate` | `src/ef/table_141_data_unknown_efef70_asm.asm` | `EF:EF70..EF:EFB7` | 71 | 71 | 0 | `274b0fc73b39180dd07b1df5e5fd1077c481387d` |
| `build-candidate` | `src/ef/asset_debug_cursor_graphics.asm` | `EF:EFB7..EF:F0D7` | 288 | 288 | 0 | `d4aa5ac9ca83bf8da624ffab3ed1c95d0e85cdd8` |
| `build-candidate` | `src/ef/asset_bank_ef_gap_1_tailpadding.asm` | `EF:F0D7..EF:10000` | 3881 | 3881 | 0 | `8e09b47444551098bd77c1dd73e19f0a9ba0a71f` |

## Source Segments

### `src/ef/table_002_unknown_ef_ef00bb_asm.asm`

| Range | Size | Name | SHA-1 |
| --- | ---: | --- | --- |
| `EF:0000..EF:EB5F` | 60255 | `TableEf00bb` | `72ac26c6a5d4500126dda954e33cace132286a4c` |

Labels:

- `EF:0000 TableEf00bb`

Evidence:

- `refs/ebsrc-main/ebsrc-main/src/bankconfig/US/bank2F.asm`
- `refs/ebsrc-main/ebsrc-main/earthbound.yml`
- `build/asset-bank-ef.json`
- `notes/bank-ef-asset-data-map.md`

### `src/ef/asset_debug_menu_font.asm`

| Range | Size | Name | SHA-1 |
| --- | ---: | --- | --- |
| `EF:EB5F..EF:EF70` | 1041 | `AssetDebugMenuFont` | `7d8195145f270d5d310df09b7c73a32cca868614` |

Labels:

- `EF:EB5F AssetDebugMenuFont`

Evidence:

- `refs/ebsrc-main/ebsrc-main/src/bankconfig/US/bank2F.asm`
- `refs/ebsrc-main/ebsrc-main/earthbound.yml`
- `build/asset-bank-ef.json`
- `notes/bank-ef-asset-data-map.md`

### `src/ef/table_141_data_unknown_efef70_asm.asm`

| Range | Size | Name | SHA-1 |
| --- | ---: | --- | --- |
| `EF:EF70..EF:EFB7` | 71 | `TableEfef70` | `274b0fc73b39180dd07b1df5e5fd1077c481387d` |

Labels:

- `EF:EF70 TableEfef70`

Evidence:

- `refs/ebsrc-main/ebsrc-main/src/bankconfig/US/bank2F.asm`
- `refs/ebsrc-main/ebsrc-main/earthbound.yml`
- `build/asset-bank-ef.json`
- `notes/bank-ef-asset-data-map.md`

### `src/ef/asset_debug_cursor_graphics.asm`

| Range | Size | Name | SHA-1 |
| --- | ---: | --- | --- |
| `EF:EFB7..EF:F0D7` | 288 | `AssetDebugCursorGraphics` | `d4aa5ac9ca83bf8da624ffab3ed1c95d0e85cdd8` |

Labels:

- `EF:EFB7 AssetDebugCursorGraphics`

Evidence:

- `refs/ebsrc-main/ebsrc-main/src/bankconfig/US/bank2F.asm`
- `refs/ebsrc-main/ebsrc-main/earthbound.yml`
- `build/asset-bank-ef.json`
- `notes/bank-ef-asset-data-map.md`

### `src/ef/asset_bank_ef_gap_1_tailpadding.asm`

| Range | Size | Name | SHA-1 |
| --- | ---: | --- | --- |
| `EF:F0D7..EF:10000` | 3881 | `AssetBankEFGap1TailPadding` | `8e09b47444551098bd77c1dd73e19f0a9ba0a71f` |

Labels:

- `EF:F0D7 AssetBankEFGap1TailPadding`

Evidence:

- `refs/ebsrc-main/ebsrc-main/src/bankconfig/US/bank2F.asm`
- `refs/ebsrc-main/ebsrc-main/earthbound.yml`
- `build/asset-bank-ef.json`
- `notes/bank-ef-asset-data-map.md`

## Notes

The scaffold preserves intentional source-adjacent data gaps from the manifest and validates each protected span against the original ROM bytes.
