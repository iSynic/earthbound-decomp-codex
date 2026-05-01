# EF Battle Text Payload Runtime Polish

This note records the first EF text-payload split driven by the C1/C2
battle-text contract work.

## Source Slice

Primary source module:

- `src/ef/ef_4e20_c51b_text_payload_data.asm`

The module is still ROM-preserved text data, not decoded text macro source. The
new labels are zero-byte scaffold anchors that split the coarse
`EF:4E20..C51B` data gap around battle-text scripts already proved by C1/C2
callers.

## Promoted Payload Anchors

- `EF:69A1`, `EF:69BA`, and `EF:69D2` now mark HP maxed, HP recovered amount,
  and PP recovered amount text. The two amount scripts are consumed through
  `C1:DC66 -> C1:AD0A -> $9D12/$9D14 -> 1C 0F`.
- `EF:6AE0`, `EF:6C3A`, and `EF:6C55` now mark paralysis, strange, and asleep
  inflicted text. The EF decode shows `EF:6AE0` as the body-numb/paralysis
  message used by `BTLACT_PARALYSIS_A`.
- `EF:6F9A..707A` now marks the shield and timed substate result text pairs
  used by the hard-state recovery/status-result C2 corridor.
- `EF:766E`, `EF:7696`, and `EF:773F` now mark shared no-effect, no-visible
  effect, and PP-drain amount text. `EF:773F` is another `1C 0F` amount
  consumer.
- `EF:7B77`, `EF:7B85`, `EF:7BA2`, `EF:7BC1`, `EF:7BDF`, and `EF:7DD5` now
  mark the byte and pointer substitution examples in `EBATTLE8`: `19 1F` byte
  substitution for present item names and `19 1E` pointer substitution branches.
- `EF:843F`, `EF:8444`, `EF:8445`, `EF:845D`, and `EF:8477` now mark
  battle-start and random-action status text used by C2 direct `DC1C` callers.

## Correction

The EF decode corrected one local C2 naming drift: `C2:9FFE` is the
`BTLACT_PARALYSIS_A` body and its success script at `EF:6AE0` prints the
body-numb/paralysis result text. The source now names that path as paralysis
rather than poison. The actual poison-inflicted text remains the separate
`EF:6B18` script used by the item/status cluster.

## Validation

This slice should validate both touched banks:

```powershell
python tools\build_source_bank_scaffold.py --bank EF
python tools\validate_source_bank_byte_equivalence.py --bank EF --module all --combined --scaffold src\ef\bank_ef_helpers_asar.asm --strict
python tools\build_source_bank_scaffold.py --bank C2
python tools\validate_source_bank_byte_equivalence.py --bank C2 --module all --combined --scaffold src\c2\bank_c2_helpers_asar.asm --strict
```
