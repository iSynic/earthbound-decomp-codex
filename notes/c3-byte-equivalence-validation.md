# C3 byte-equivalence validation

This report assembles scratch Asar translations of C3 pilot modules into clean ROM copies at their original `org` addresses, then compares the protected byte ranges against the original ROM.

- status: `OK`
- mode: `per-module`
- modules: `1`
- non-OK modules: `0`
- mismatches: `0`

## Modules

| Status | Source Path | Range | Size | Mismatches | Generated ASM |
| --- | --- | --- | ---: | ---: | --- |
| `OK` | `src/c3/jeff_repair_psi_helpers.asm` | `C3:F1EC..C3:F2B1` | 197 | 0 | `build/c3-byte-equivalence/jeff-repair-psi.byte-equivalence.asar.asm` |
