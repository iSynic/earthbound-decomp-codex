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
- `EF:69EA` and `EF:69FF` now mark the Spy offense and defense amount
  readouts. Both scripts are `1C 0F` amount consumers reached through the C2
  Spy setup and the `C1:DC66` amount-print contract.
- `EF:6A0D`, `EF:6A24`, `EF:6A3C`, `EF:6A54`, `EF:6A6C`, and `EF:6A7F`
  now mark the Spy vulnerability/susceptibility direct readout text for fire,
  freeze, flash, paralysis, hypnosis, and Brain Shock. C2 gates these direct
  scripts from battler resistance bytes before issuing the `DC1C` display call.
- `EF:6A99` and `EF:6AB3` now mark metamorphose success/failure text used by
  the C2 normalization tail. `EF:6AC7` now marks the diamondized inflicted
  text adjacent to the existing paralysis/status payload split.
- `EF:6AE0`, `EF:6B18`, `EF:6BEF`, `EF:6C3A`, and `EF:6C55` now mark
  paralysis, poison, solidification, strange, and asleep inflicted text. The EF
  decode shows `EF:6AE0` as the body-numb/paralysis message used by
  `BTLACT_PARALYSIS_A`, while actual poison remains the separate `EF:6B18`
  script used by the item/status cluster.
- `EF:6AFB..6C0B` is now split around the adjacent sick/cold/mushroomized,
  possessed, crying, immobilized, solidification, and PSI-seal status payloads
  instead of one broad affliction corridor.
- `EF:6F9A/6FBD`, `EF:6FD3/6FF4`, `EF:700C/7032`, and `EF:7050/707A`
  now mark the installed/strengthened text pairs for shield, power shield,
  psychic shield, and psychic power shield.
- `EF:7099`, `EF:70B1`, `EF:70D2`, `EF:70FA`, `EF:7123`, `EF:7142`, and
  `EF:7160` now mark the shield-expired, shield-reflection, PSI-name
  shield-nullify, Neutralizer, and Franklin Badge text tail used by C2 timed
  substate and Thunder reflection helpers.
- `EF:766E`, `EF:7696`, and `EF:773F` now mark shared no-effect, no-visible
  effect, and PP-drain amount text. `EF:773F` is another `1C 0F` amount
  consumer.
- `EF:77FD`, `EF:7810`, `EF:7824`, and `EF:7830` now mark the four
  call-for-help result scripts selected by the C2 reinforcement prefix/body:
  ordinary success, seed/sprout success, ordinary failure, and seed/sprout
  failure. They are direct `C1:DC1C` text exits.
- `EF:7843` now marks the Time Stop return text used by the C2 hit-resolution
  cluster. `EF:7858..7B77` remains a larger EBATTLE8 appear/victory/level-up
  text run until more local consumers need finer labels.
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

## Spy Readout Follow-up

The C2 Spy refinement proved that the coarse `EF:69EA..6AE0` EBATTLE5 corridor
contains a compact set of distinct scripts, not one generic stat/status
prelude. Offense and defense use the same amount-print path as HP/PP recovery,
while the resistance readouts are direct display scripts selected only when C2
finds a vulnerable/susceptible resistance byte. The metamorphose and diamondized
neighbors were split in the same pass so the late C2 primary-status tail no
longer lands in an anonymous gap.

## Call-For-Help And Time Stop Follow-up

The C2 call-for-help polish proved four direct text exits in the front of
`EBATTLE8`: ordinary and seed/sprout success paths at `EF:77FD` and `EF:7810`,
plus ordinary and seed/sprout failure paths at `EF:7824` and `EF:7830`. The
same EBATTLE8 neighborhood also contains the `EF:7843` Time Stop return script
used by the C2 hit-resolution cluster. This split keeps those runtime-facing
messages visible while leaving the larger appear/victory/level-up tail coarse.

## Validation

This slice should validate both touched banks:

```powershell
python tools\build_source_bank_scaffold.py --bank EF
python tools\validate_source_bank_byte_equivalence.py --bank EF --module all --combined --scaffold src\ef\bank_ef_helpers_asar.asm --strict
python tools\build_source_bank_scaffold.py --bank C2
python tools\validate_source_bank_byte_equivalence.py --bank C2 --module all --combined --scaffold src\c2\bank_c2_helpers_asar.asm --strict
```
