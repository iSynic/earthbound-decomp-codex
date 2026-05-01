# C2 ↔ C1 Battle Text + EF Script Contracts (Workahead)

Scope: scout battle text and EF text-script contracts that should drive **C2 source naming / promotion**, with emphasis on:

- C2 callers into `C1:DC1C`, `C1:DC66`, `C1:DD9F`
- EF battle-text payloads and their control-code structure
- substitution commands (`0x19` family) and amount/status-result text (`0x1C` family)

This is a **workahead contract note** (no source/manifest edits). It consolidates local callers + `refs/ebsrc` text-bank maps + existing note conclusions so manual integration can promote the right C2 corridors with stable semantics.

## Implementation status

- 2026-04-30: first runtime semantic-polish pass landed byte-neutral source
  comments/local aliases for the pinned `C1:DC1C`, `C1:DC66`, `C1:DD9F`,
  `C1:AD0A`, and `C1:AD26` contracts plus the C2 HP/PP amount-message callers
  and the `D5:7B68` action-table mode-1 message lane. The wider 39-call
  `DC66` sweep and remaining status-result callers are still future work.
- 2026-04-30: second pass named the local EF status-result scripts for
  resist-checked crying, solidified, asleep, poison, strange, PP drain, and
  timed shield/substate messages. These source aliases are intentionally local
  to the C2 callers until a wider EF text payload naming pass promotes shared
  script labels.
- 2026-04-30: third pass removed the remaining local
  `C1DC66_DisplayBattleTextWithNumber` aliases from C2 source modules and
  named the C8/EF amount-result scripts for PP, guts, offense, and defense
  stat/resource deltas, plus the C8 IQ-increase amount script.
- 2026-04-30: fourth pass promoted the direct stat-increase consequence leaves
  (`C2:B3D8..B5E3`) and the `C2:A056` 1d4/random stat-up wrappers so their
  selected-row offsets, C8 amount scripts, C8 script bank, and `C1:DC66`
  substitution-payload calls are named at the source sites. The `B3D8..B573`
  direct leaves also name the live character mirror bytes and derived-stat
  refresh helpers used before printing the amount.
- 2026-04-30: fifth pass promoted the `C2:A3D1..A5EC` item-side text surface.
  The source now names direct `DC1C` messages for concentration/PSI-seal,
  shield-clear, solidification, no-effect, and HP-sucker self-drain, and names
  the `DC66` amount-bearing HP-sucker script at `EF:7729`.
- 2026-05-01: sixth pass promoted the `C2:A89D..AF1F` item/status cluster.
  The source now names poison, solidification, asleep, strange, and shared
  no-effect direct-text scripts, the C8 doubled-guts and defense-up amount
  scripts, and the `DC66` amount-bearing calls used by Sudden Guts Pill and the
  item-side defense-up wrapper.
- 2026-05-01: seventh pass promoted the short item/status helper leaves at
  `C2:A39D`, `C2:A630`, `C2:A82A`, and `C2:A86B`. These now name poison-removed
  `EF:6E97`, solidification `EF:6BEF`, no-effect `EF:766E`, the EF text bank,
  and their `DC1C` direct-text calls.
- 2026-05-01: eighth pass promoted the late normalization/odor continuation
  seam. `C2:AF1F` now names the metamorphose success/failure scripts
  (`EF:6A99` / `EF:6AB3`) and `C2:B172` names the condiment spice hit/miss
  scripts (`C9:7C9D` / `C9:7CB1`) plus the shared no-effect fallback
  (`EF:766E`) and their `DC1C` direct-text dispatches.

## Key C1 entrypoints (contracts that drive C2 naming)

Primary family writeup: `notes/battle-text-entry-family-c1dc1c-dd7c.md`, `notes/battle-text-entry-tail-dd82-dd9f.md`.

### Direct-page argument-slot mapping (why C2 stages `$0E/$10` and `$12/$14`)

These battle-text wrappers all use the generated prologue pattern:

- `phd ; tdc ; adc #$FFEE ; tcd`

That means their “argument” direct-page slots alias the **caller’s** frame:

- callee `$20/$22` == caller `$0E/$10` (because `0x20 - 0x12 = 0x0E`)
- callee `$24/$26` == caller `$12/$14` (because `0x24 - 0x12 = 0x12`)

**C2 naming implication:** `$0E/$10` and `$12/$14` are not random scratch here; they are *battle-text argument staging* for `DC1C` / `DC66` / `DD9F`.

### `C1:DC1C` — `DisplayBattleTextFromPointer`

Best current behavior contract:

- **Input**: far pointer staged by the caller in `$0E/$10` (low word / bank word), which aliases callee `$20/$22` under the DP frame shift
- **Effect**: dispatches the pointed EF text script through the generic textbox processor at `C1:86B1`
- **C2 implication**: any C2 routine that stages `$0E/$10` and `JSL C1:DC1C` is a *battle-text emission site* (not “random string data”); name the routine around the message being selected.

Concrete C2 caller example:

- `C2:4F03` (`src/c2/c2_4f00_display_battle_encounter_text.asm`) loads `enemy_data::encounter_text_ptr` into `$0E/$10` then `JSL C1:DC1C`.

### `C1:DC66` — `DisplayBattleTextWithSubstitutionPayload` (amount-bearing wrapper)

Best current behavior contract (from `notes/battle-text-entry-family-c1dc1c-dd7c.md`):

- **Inputs**: two caller-provided far arguments
  - **primary script pointer** staged by the caller in `$0E/$10` (aliases callee `$20/$22`)
  - **secondary payload** staged by the caller in `$12/$14` (aliases callee `$24/$26`), then committed via `C1:AD0A -> $9D12/$9D14`
    - often consumed as an **amount-like payload** by `PRINT_ACTION_AMOUNT` (`0x1C 0x0F`) via `C1:AD26`
    - sometimes consumed as a **pointer substitution payload** by `LOAD_POINTER_SUBSTITUTION` (`0x19 0x1E`) via `C1:7AE3`
- **Why it matters**: the *secondary payload* is later consumed by `PRINT_ACTION_AMOUNT` (`0x1C 0x0F`) via the getter path (`C1:AD26`).
- **C2 implication**: when C2 uses `DC66`, it is **promising** that the chosen EF script will read `PRINT_ACTION_AMOUNT` (or another `$9D12/$9D14` consumer). Name the C2 routine around “apply delta + print amount-bearing battle text”, not around a generic “display string”.

Concrete C2 caller examples:

- `C2:7294` (`src/c2/c2_7294_apply_battler_hp_recovery_feedback.asm`): success path chooses `EF:69BA`, stages `{delta}` as the secondary payload, then `JSL C1:DC66`.
- `C2:7318` (`src/c2/c2_7318_apply_battler_pp_recovery_feedback.asm`): chooses `EF:69D2`, stages `{delta}`, then `JSL C1:DC66`.
- Late action-table numeric effects (`notes/class2-late-stat-and-resource-family-c28e42-c29e38.md`) repeatedly “mutate stat/resource → print `{delta}` via `DC66`”.

### `C1:DD9F` — `DisplayCurrentActionTableTextMode1` (mode-1 wrapper)

Best current behavior contract (from `notes/battle-text-entry-tail-dd82-dd9f.md`):

- **Input**: far pointer staged by the caller in `$0E/$10` (aliases callee `$20/$22`), then it forces display mode `1` via `JSR $0036`, stages pointer to `$0E/$10`, and dispatches via `C1:86B1`.
- **Caller contract**: pinned local caller `C2:5C66` displays a `D5:7B68`-selected action-table message through `DD9F`, then the caller owns the wait/tick loop itself (consistent with the “NO_PROMPT” export mapping).
- **C2 implication**: treat `DD9F` as a specialized “battle action-table text, mode=1” emission path (don’t collapse it into the general `DC1C` naming without evidence).

#### Unique C2 caller (`C2:5C66`) with concrete selection formula

ROM scan for `JSL $C1DD9F` bytes (`22 9F DD C1`) yields exactly one callsite in bank `C2`: `C2:5C66`.

Decoded snippet (`tools/decode_snippet.py C2:5BE8`, trimmed to the selection core):

- loads base long pointer `D5:7B68` into `$0A/$0C`
- reads an action-table index byte from `($A970 + 0x0004)`
- computes `offset = 0x0C * index + 0x0004`
- loads a far pointer at `D5:7B68 + offset + {0,2}` and stages it to `$0E/$10`
- `JSL C1:DD9F`

So the contract is:

- `D5:7B68` is an action-table message table with stride `0x0C`
- the script far pointer field lives at `+0x04` inside each `0x0C` record
- `DD9F` is the “action-table row message, forced mode=1” lane (caller owns the followup tick/wait loop)

This corridor also conditionally emits two hardcoded EF scripts via `DC1C` before selecting the action-table row script:

- `EF:845D` (user-name message: “@… acted unusual.”)
- `EF:8477` (user-name message: “@… felt funky.”)

## Substitution-slot contracts that appear inside EF battle scripts

These are the *script-level* contracts C2 is implicitly relying on when it chooses particular EF pointers.

### Byte substitution: `$9D11` ↔ `0x19 0x1F` (`LOAD_BYTE_SUBSTITUTION`)

Pinned by `notes/class2-c1acf8-substitution-byte-family.md` and `notes/class2-c1-display-text-substitution-handler-7af3.md`:

- `C1:ACF8` stores low 8 bits of `A` to `$9D11` (setter)
- `C1:DD7C` is the far-call wrapper for `C1:ACF8`
- `C1:AD02` reads `$9D11` (getter)
- `C1:7AF3` loads `$9D11` and stages it into the display-text pipeline
- Text control code `0x19 0x1F` dispatches to `C1:7AF3` and is named `LOAD_BYTE_SUBSTITUTION` in `tools/disasm_ebtext_script.py`

**Concrete C2 caller bridge (present/UFO path):**

- `C2:6003` and `C2:8881` (see `notes/class2-ufo-present-message-family.md`) load `$AA10`, call `JSL C1:DD7C`, then dispatch EF scripts (`EF:7BDF`, `EF:7DD5`) through `C1:DC1C`.

EF script evidence (decoded from ROM with `tools/disasm_ebtext_script.py`):

- `EF:7BDF` (`EBATTLE8` `MSG_BTL_PRESENT`) contains:
  - `LOAD_BYTE_SUBSTITUTION` (`19 1F`)
  - `SWAP_WORKING_AND_ARG_MEMORY` (`1B 04`)
  - `PRINT_ITEM_NAME 0x00` (`1C 05 00`)
- `EF:7DD5` (`EBATTLE8` `MSG_BTL_CHECK_PRESENT_GET`) contains:
  - `01 70 1C 0D` = `START_NEW_LINE`, `"@"`, `PRINT_ACTION_USER_NAME`
  - later: `LOAD_BYTE_SUBSTITUTION` (`19 1F`) → `PRINT_ITEM_NAME 0x00`

**C2 promotion guidance:** if a C2 corridor does `JSL C1:DD7C` immediately before `JSL C1:DC1C`, it’s not “mystery pre-text state”; it is **script-argument staging** for an EF message that is about to execute `LOAD_BYTE_SUBSTITUTION`.

### Pointer substitution: `$9D12/$9D14` ↔ `0x19 0x1E` (`LOAD_POINTER_SUBSTITUTION`)

Pinned by `notes/text-command-family-19-data-and-substitution.md` plus the source-backed leaves:

- `C1:AD0A` (`src/c1/c1_ad0a_stage_battle_text_substitution_pointer.asm`) commits a caller-provided payload into `$9D12/$9D14`
- `C1:7AE3` (`src/c1/c1_7ae3_load_display_text_pointer_substitution_slot.asm`) is the display-side loader used by text command `0x19 0x1E`

Concrete script evidence (exact parsed hits via `tools/find_ebtext_command.py 19 1E`):

- `EF:7B85`, `EF:7BA2`, `EF:7BC1` (all in `EBATTLE8`)

These occur in the same decoded script region as the present/UFO byte-substitution examples (see `tools/disasm_ebtext_script.py EF:7B70`):

- `EF:7B77` uses `LOAD_BYTE_SUBSTITUTION` (`19 1F`) and prints a PSI name
- `EF:7B85` / `EF:7BA2` / `EF:7BC1` use `LOAD_POINTER_SUBSTITUTION` (`19 1E`) and branch on active-memory values

**C2 promotion guidance:** a `DC66` caller is not always “display-with-number.” If the displayed script consumes `19 1E` rather than `1C 0F`, name the C2 corridor around “stage pointer-substitution payload, then display battle script.”

### Amount substitution: `$9D12/$9D14` ↔ `0x1C 0x0F` (`PRINT_ACTION_AMOUNT`)

Pinned in `notes/battle-text-entry-family-c1dc1c-dd7c.md` and summarized in `notes/text-command-family-1c-print-display.md`:

- `PRINT_ACTION_AMOUNT` is control code `1C 0F`
- Its getter side routes through `C1:AD26`, which reloads the staged `$9D12/$9D14` payload
- `C1:DC66` is the high-value wrapper that *commits* that payload before displaying the EF script

**C2 promotion guidance:** when C2 prints `EF:*` scripts that contain `PRINT_ACTION_AMOUNT`, prefer naming the C2 routine around “compute delta + stage + emit amount-bearing battle text” and keep the staged value type explicit (`delta_hp`, `delta_pp`, `delta_offense`, etc.).

## EF battle scripts used as amount/status-result text (concrete addresses + opcode bytes)

These were decoded directly from the local ROM with `tools/disasm_ebtext_script.py` and corroborated with `refs/ebsrc-main/ebsrc-main/earthbound.yml` text-bank bases.

### `EBATTLE5` (base `EF:69A1`, `refs/ebsrc` offset `0x2F69A1`)

These are core “amount/status result” scripts used by C2 feedback helpers.

- `EF:69A1` (“HP maxed out”)
  - starts `01 70 1C 0E` = `START_NEW_LINE`, `"@"`, `PRINT_ACTION_TARGET_NAME`
  - ends with `PLAY_SOUND 0x24` (`1F 02 24`) and `HALT_WITH_PROMPT` (`03`)
- `EF:69BA` (“recovered {delta} HP!”)
  - `01 70 1C 0E` … then `PRINT_ACTION_AMOUNT` (`1C 0F`) … `" HP!"`
  - ends with `PLAY_SOUND 0x24` and `HALT_WITH_PROMPT`
  - **C2 caller**: `C2:7294` (`src/c2/c2_7294_apply_battler_hp_recovery_feedback.asm`) uses `DC66` here.
- `EF:69D2` (“recovered {delta} PP!”)
  - same structure as `EF:69BA`, but prints `" PP!"`
  - **C2 caller**: `C2:7318` (`src/c2/c2_7318_apply_battler_pp_recovery_feedback.asm`) uses `DC66` here.

- `EF:6AE0` (poison inflicted message)
  - starts `01 70 1C 0E` = `START_NEW_LINE`, `"@"`, `PRINT_ACTION_TARGET_NAME`
  - **C2 caller**: `C2:9FFE` (in `src/c2/c2_9f57_run_asleep_status_wrapper_action.asm`, `RunResistCheckedPoisonStatusAction`) chooses `EF:6AE0` vs `EF:766E`.
- `EF:6C55` (asleep inflicted message)
  - starts `01 70 1C 0E` = `START_NEW_LINE`, `"@"`, `PRINT_ACTION_TARGET_NAME`
  - **C2 caller**: `C2:9F06` (`src/c2/c2_9f06_run_resist_checked_asleep_status_action.asm`) chooses `EF:6C55` vs `EF:766E`.
- `EF:6C3A` (feel strange inflicted message)
  - starts `01 70 1C 0E` = `START_NEW_LINE`, `"@"`, `PRINT_ACTION_TARGET_NAME`
  - **C2 caller**: `C2:A056` (`src/c2/c2_a056_run_resist_checked_strange_status_action.asm`) chooses `EF:6C3A` vs `EF:766E`.

- timed substate messages (paired success/fail scripts)
  - **C2 caller**: `src/c2/c2_9cb8_try_recover_selected_battler_hard_state.asm` dispatches:
    - `EF:6FBD` vs `EF:6F9A` (substate 4)
    - `EF:6FF4` vs `EF:6FD3` (substate 3)
    - `EF:7032` vs `EF:700C` (substate 2)
    - `EF:707A` vs `EF:7050` (substate 1)

### `EBATTLE6` (base `EF:7186`, `refs/ebsrc` offset `0x2F7186`)

- `EF:7696` (“It had no visible effect on {target}!”)
  - starts with `START_NEW_LINE` and prints `PRINT_ACTION_TARGET_NAME` (`1C 0E`)
  - **C2 caller**: `C2:7294` uses `DC1C` to emit this on a blocked-row path.

- `EF:766E` (shared resist/no-effect “didn’t work” message)
  - contains `PRINT_ACTION_TARGET_NAME` (`1C 0E`) and ends with `... 51 03 02`
  - **C2 callers**: `C2:9F06` (asleep), `C2:9FFE` (poison), `C2:A056` (strange) all fall back to `EF:766E` via `DC1C`.

### `EBATTLE8` (base `EF:77FD`, `refs/ebsrc` offset `0x2F77FD`)

From `refs/ebsrc-main/ebsrc-main/earthbound.yml`:

- `0x03E2` = `MSG_BTL_PRESENT` → `EF:7BDF`
- `0x05D8` = `MSG_BTL_CHECK_PRESENT_GET` → `EF:7DD5`

These are the canonical “byte substitution” examples:

- `EF:7BDF` uses `LOAD_BYTE_SUBSTITUTION` (`19 1F`) → `PRINT_ITEM_NAME 0`
- `EF:7DD5` uses `PRINT_ACTION_USER_NAME` (`1C 0D`) and later the same `LOAD_BYTE_SUBSTITUTION` → `PRINT_ITEM_NAME 0`

- `EF:773F` (PP drain amount message)
  - contains `PRINT_ACTION_AMOUNT` (`1C 0F`)
  - **C2 caller**: `C2:9F5E` (in `src/c2/c2_9f57_run_asleep_status_wrapper_action.asm`, `RunHpSuckerStylePpDrainAction`) stages `{delta_pp}` and uses `DC66`.

### `EBATTLE0` (base `EF:843F`, `refs/ebsrc` offset `0x2F843F`)

Battle-start status-message cluster used by the `C2:4F62+` path (`notes/class2-concrete-battle-text-call-paths.md`):

- `EF:8445` begins:
  - `01 70 1C 0E` = `START_NEW_LINE`, `"@"`, `PRINT_ACTION_TARGET_NAME`
  - then compressed tokens + punctuation + `HALT_WITH_PROMPT` (`03`)

These are staged as hardcoded EF pointers immediately after `C2:3D05` (target-side context build) and dispatched through `C1:DC1C`.

## Concrete C2 caller examples that should drive promotions/names

These are “good promotion candidates” because the call sites encode real contracts (pointer selection + substitution staging + EF opcode expectations).

### Encounter/death pointer emission (`DC1C` pointer contract)

- `C2:4F03` (`src/c2/c2_4f00_display_battle_encounter_text.asm`)
  - loads `enemy_data::encounter_text_ptr` (`D5:9589 + 0x2D`) into `$0E/$10`
  - `JSL C1:DC1C`
- `C2:7680+` (`src/c2/c2_7680_display_enemy_death_text.asm`)
  - loads `enemy_data::death_text_ptr` (`D5:9589 + 0x31`) into `$0E/$10`
  - `JSL C1:DC1C`

Promotion effect: name these callers as “select enemy record pointer + emit battle text”, not “unknown message handler”.

### HP/PP recovery feedback (paired `DC1C` + `DC66` contract)

- `C2:7294` (`src/c2/c2_7294_apply_battler_hp_recovery_feedback.asm`)
  - chooses among `EF:69A1` (maxed), `EF:69BA` (amount-bearing), `EF:7696` (no visible effect)
  - uses `DC66` only on the path where the EF script prints `PRINT_ACTION_AMOUNT` (`1C 0F`)
- `C2:7318` (`src/c2/c2_7318_apply_battler_pp_recovery_feedback.asm`)
  - emits `EF:69D2` via `DC66` (amount-bearing PP recovered)

Promotion effect: keep the “amount-bearing EF script requires staged delta” invariant explicit in naming and parameter shaping.

### Start-of-battle status messages (context → emit)

From `notes/class2-concrete-battle-text-call-paths.md`:

- `C2:4F62+` first calls `C2:3D05` (target text context) then emits hardcoded EF pointers (`EF:843F`, `EF:8444`, `EF:8445`) through `DC1C`.

Promotion effect: this should become a clear “battle-start status announcement” routine, not a generic “emit message list”.

Source-scaffold status:

- `C2:4F52..5024` is decoded source in `src/c2/c2_4f52_display_battle_start_status_messages_prelude.asm`.
- `C2:5024..6189` is now decoded source split across `src/c2/c2_5024_run_battle_start_candidate_controller_front.asm` and `src/c2/c2_5afb_run_battle_start_candidate_controller_back.asm`, with the heavier `5540` controller joins forced at the source-module boundaries and known post-call width joins.

### Present/UFO byte-substitution bridge (`DD7C` → `DC1C` → `19 1F`)

From `notes/class2-ufo-present-message-family.md`:

- `C2:6003` and `C2:8881`:
  - `$AA10` → `JSL C1:DD7C` (sets `$9D11`)
  - then `JSL C1:DC1C` on `EF:7BDF` / `EF:7DD5`
  - those scripts execute `LOAD_BYTE_SUBSTITUTION` (`19 1F`) before `PRINT_ITEM_NAME 0`

Promotion effect: model `$AA10` as “byte substitution argument” for a specific EF script family; don’t let this degenerate into “mystery battle-start flag”.

### Resist-checked affliction actions (paired EF success/fail scripts via `DC1C`)

- `C2:9F06` (`src/c2/c2_9f06_run_resist_checked_asleep_status_action.asm`) chooses `EF:6C55` (success) vs `EF:766E` (no effect)
- `C2:9FFE` (in `src/c2/c2_9f57_run_asleep_status_wrapper_action.asm`, `RunResistCheckedPoisonStatusAction`) chooses `EF:6AE0` vs `EF:766E`
- `C2:A056` (`src/c2/c2_a056_run_resist_checked_strange_status_action.asm`) chooses `EF:6C3A` vs `EF:766E`

Promotion effect: these corridors are stable “status result” emitters; promote with status-specific names rather than generic “display text”.

### PP drain amount text (`DC66` + `PRINT_ACTION_AMOUNT`)

- `C2:9F5E` (in `src/c2/c2_9f57_run_asleep_status_wrapper_action.asm`, `RunHpSuckerStylePpDrainAction`) stages `{delta_pp}` and uses `DC66` with `EF:773F` (script contains `1C 0F`)

Promotion effect: keep the staged value type explicit (delta PP) and preserve the invariant “`DC66` only on `1C 0F` scripts”.

### Timed substate message pairs (EF scripts via `DC1C`)

- `src/c2/c2_9cb8_try_recover_selected_battler_hard_state.asm` dispatches paired success/fail scripts:
  - `EF:6FBD` vs `EF:6F9A`
  - `EF:6FF4` vs `EF:6FD3`
  - `EF:7032` vs `EF:700C`
  - `EF:707A` vs `EF:7050`

Promotion effect: promote as an internally consistent “apply timed substate then emit paired result text” family; defer the gameplay names of each substate index.

## Naming proposals (workahead)

These are the “contracts-first” names that should influence C2 source promotion and call-site signatures:

- `C1:DC1C` → `DisplayBattleTextFromPointer` (consume `$0E/$10` far ptr)
- `C1:DC66` → `DisplayBattleTextWithSubstitutionPayload` (commit `$9D12/$9D14` then display EF script)
  - acceptable narrower alias when used with `1C 0F`: `DisplayBattleTextWithActionAmount`
- `C1:DD9F` → `DisplayCurrentActionTableTextMode1` (action-table message, mode `1`)
- `C1:DD7C` / `C1:ACF8` → `SetBattleTextByteSubstitution` (set `$9D11`)

And for the most actionable C2 call-site families:

- `C2:3BCF` → `BuildBattleAttackerTextContext` (ends at `C1:DD70`)
- `C2:3D05` → `BuildBattleTargetTextContext` (ends at `C1:DD76`)
- `C2:4F03` → `DisplayBattleEncounterText` (enemy record pointer → `DC1C`)
- `C2:4F62+` → `DisplayBattleStartStatusMessages` (target context → hardcoded EF pointers)
- `C2:7294` → `ApplyBattlerHpRecoveryFeedback` (chooses maxed/amount/no-effect scripts, uses `DC66` iff `1C 0F`)
- `C2:7318` → `ApplyBattlerPpRecoveryFeedback` (amount-bearing `DC66` path)

## Integration checklist (manual)

When promoting additional C2 corridors that call into the battle-text cluster:

1. If you see `JSL C1:DC1C`, confirm the caller staged `$0E/$10` (far ptr contract) and annotate the chosen EF pointer(s).
2. If you see `JSL C1:DC66`, verify the EF script(s) contain `PRINT_ACTION_AMOUNT` (`1C 0F`) or another `$9D12/$9D14` consumer; name the staged value accordingly.
3. If you see `JSL C1:DD7C` shortly before a `DC1C` dispatch, decode the EF script and look for `LOAD_BYTE_SUBSTITUTION` (`19 1F`) + downstream printers (`PRINT_ITEM_NAME`, `PRINT_PSI_NAME`, etc.).
4. Treat `DD9F` call sites as a distinct lane (mode forcing + “no prompt” behavior); don’t collapse into the main `DC1C` wrapper without evidence.
