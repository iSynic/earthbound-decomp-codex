# C2 PP loss and call-for-help width helpers

This note covers two C2 unknowns in the late battle-routine region:

- `C2:BCB9`, immediately before the named `LOSE_HP_STATUS`
- `C2:BD13`, immediately before the named `CALL_FOR_HELP_COMMON`

Both are small helpers that become straightforward once compared with their named neighbors.

## Working Names

- `C2:BCB9` = `ApplyBattlerPpTargetLoss`
- `C2:BD13` = `SumActiveEnemyBattleSpriteWidths`

## `C2:BCB9` - PP target loss wrapper

Suggested working name: `LosePpStatus`

Known robust caller:

- `C2:5B79`, in the main battle command/effect flow

`C2:BCB9` takes a battler pointer in `A` and an amount in `X`. It subtracts that amount from the battler's PP target, floors at zero, and calls `C2:7191` / `SetBattlerPpTarget`.

Observed structure:

```asm
STX $08          ; amount
STA $06          ; battler pointer
TAX
LDA $9FC5,X      ; battler::pp_target
SEC
SBC $08
BPL .nonnegative
LDA #$0000
.nonnegative
LDX $06
JSL SetBattlerPpTarget ; C2:7191
RTL
```

Relevant battler fields:

- `$9FC5` = `BATTLERS_TABLE + 0x19`, `pp_target`
- `$9FBF` = `BATTLERS_TABLE + 0x13`, `hp_target`

This mirrors the adjacent named `LOSE_HP_STATUS` routine, which performs the same clamp/subtract/set operation for `hp_target` and then calls `C2:7126` / `SetBattlerHpTarget`. The nearby local routine at `C2:BCE6` is another HP-target wrapper with the same shape and should be treated as a sibling of the named HP-loss helper.

## `C2:BD13` - sum active enemy battle sprite widths

Suggested working name: `SumActiveEnemyBattleSpriteWidths`

Named caller context:

- `CALL_FOR_HELP_COMMON`

`C2:BD13` scans the enemy side of the battler table and returns the total battle-sprite width contribution for conscious enemies.

Observed behavior:

- starts at `$A21C`, which is `BATTLERS_TABLE + 8 * 0x4E`
- loops battler slots `8..31`
- skips entries whose `consciousness` field at `+0x0C` is not `1`
- reads each active enemy's battle sprite id at `+0x02`
- calls `GET_BATTLE_SPRITE_WIDTH` (`C2:EFFD`)
- accumulates the returned width bucket
- returns the total in `A`

`GET_BATTLE_SPRITE_WIDTH` indexes the battle-sprite metadata table in bank CE and maps metadata classes to width buckets:

- classes `1` and `3` -> `0x04`
- classes `2` and `4` -> `0x08`
- classes `5` and `6` -> `0x10`
- anything else -> `0x00`

`CALL_FOR_HELP_COMMON` uses `C2:BD13` while deciding whether a newly called enemy can fit on screen. It obtains the candidate enemy's sprite width, calls this routine to total existing conscious enemy widths, adds the two values, and rejects the call-for-help path if the sum is at least `0x20`.

That makes the routine a layout/capacity helper for enemy reinforcements rather than a generic battler-table scanner.
