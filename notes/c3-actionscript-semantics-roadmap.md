# C3 Event/Actionscript Semantics Roadmap

This is the front door for the semantic phase after readable source-bank
closure. C3 is byte-equivalent and scaffold-closed, but much of the bank is
interpreted event/actionscript bytecode rather than native 65816 source.

The goal of this phase is to make those scripts understandable, editable, and
eventually reassemblable without guessing.

## Current Baseline

- C3 source scaffold: `src/c3/bank_c3_helpers_asar.asm`
- C3 scaffold coverage: `65536 / 65536` bytes
- C3 residual ranges: `0`
- C3 byte-equivalence: `OK`, `0` mismatches
- Script manifest: `notes/script-payloads-c3.md`
- Source/data map: `notes/c3-source-data-map.md`
- Current promoted script payload labels: `80`
- Current promoted complete event-bytecode decodes: `72`
- Current non-event script-adjacent payloads: `8`
- Current source-form event/actionscript pilots: `13` families, `7899` validated
  bytes
- Source-pilot frontier: `notes/c3-source-pilot-frontier.md`

This means the byte layer is stable. The open work is semantic: opcode
contracts, operand meanings, script family roles, and reassembly-friendly source
forms.

## Current Audit

`tools/build_c3_actionscript_semantics_audit.py` regenerates the current
frontier report from `build/c3-source-data-map.json`, `build/ref-index.json`,
and the local ROM. The checked-in report is
`notes/c3-actionscript-semantics-audit.md`.

Current audit result:

- script/actionscript rows audited: `177`
- rows syntactically complete with the current decoder: `177`
- native callback byte-count contract seeds: `85`
- rows blocked by unknown native callback argument contracts: `0`
- unknown event opcodes found: `0`

This shifts the next pass away from opcode discovery and toward semantic
operand names, stable script labels, and script-family source forms.

## Milestone Definition

This milestone is complete when C3 event/actionscript payloads have:

1. an opcode catalog with operand shapes and confidence levels
2. a decoded include-start inventory for every event/actionscript payload row
3. stable labels for branch/call targets used by promoted script families
4. known external callback argument shapes for `EVENT_CALLROUTINE`
5. at least one script family emitted in a reassembly-friendly source form
6. a clear frontier list for unknown opcodes, unknown operands, and VM-adjacent
   payloads that are not event bytecode

## Terminology

- `event-bytecode-asset`: a script payload that should be decoded as event VM
  bytecode, not native 65816.
- `event-bytecode-label`: an internal label or branch target inside an event VM
  bytecode stream.
- `event-script-asset`: an ebsrc event include row that is known to be script
  payload, but has not yet been promoted into local decoded labels.
- `movement-pattern-data`: compact movement/pattern data adjacent to event
  scripts, but not decoded by the event VM.
- `effect-script-asset`: a battle visual effect script or other VM-adjacent
  payload that uses a different interpreter contract.

## Opcode Catalog Seed

The current decoder catalog is in `tools/decode_event_script.py`. Operand names
describe byte shape first; semantic names should tighten as C0/C4 callback and
WRAM contracts improve.

| Opcode | Name | Operands | Control-flow role |
| --- | --- | --- | --- |
| `$00` | `EVENT_END` | - | terminal |
| `$01` | `EVENT_LOOP` | `byte` | loop setup |
| `$02` | `EVENT_LOOP_END` | - | loop terminator |
| `$03` | `EVENT_LONGJUMP` | `ptr3` | terminal jump |
| `$04` | `EVENT_LONGCALL` | `ptr3` | subroutine call |
| `$05` | `EVENT_LONG_RETURN` | - | terminal return |
| `$06` | `EVENT_PAUSE` | `byte` | wait |
| `$07` | `EVENT_START_TASK` | `shortptr` | starts concurrent script task |
| `$08` | `EVENT_SET_TICK_CALLBACK` | `ptr3` | callback install |
| `$09` | `EVENT_HALT` | - | terminal halt |
| `$0A` | `EVENT_SHORTCALL_CONDITIONAL` | `shortptr` | conditional call |
| `$0B` | `EVENT_SHORTCALL_CONDITIONAL_NOT` | `shortptr` | inverted conditional call |
| `$0C` | `EVENT_END_TASK` | - | terminal task end |
| `$0E` | `EVENT_SET_VAR` | `byte`, `word` | action/script variable write |
| `$0F` | `EVENT_CLEAR_TICK_CALLBACK` | - | callback clear |
| `$10` | `EVENT_SWITCH_JUMP_TEMPVAR` | `wordlist` | tempvar-indexed jump |
| `$11` | `EVENT_SWITCH_CALL_TEMPVAR` | `wordlist` | tempvar-indexed call |
| `$12` | `EVENT_WRITE_BYTE_WRAM` | `word`, `byte` | WRAM byte write |
| `$13` | `EVENT_END_LAST_TASK` | - | task control |
| `$14` | `EVENT_BINOP` | `byte`, `byte`, `word` | variable operation |
| `$15` | `EVENT_WRITE_WORD_WRAM` | `word`, `word` | WRAM word write |
| `$16` | `EVENT_BREAK_IF_FALSE` | `shortptr` | conditional break |
| `$17` | `EVENT_BREAK_IF_TRUE` | `shortptr` | conditional break |
| `$18` | `EVENT_BINOP_WRAM` | `word`, `byte`, `byte` | WRAM/variable operation |
| `$19` | `EVENT_SHORTJUMP` | `shortptr` | terminal short jump |
| `$1A` | `EVENT_SHORTCALL` | `shortptr` | short call |
| `$1B` | `EVENT_SHORT_RETURN` | - | terminal return |
| `$1C` | `EVENT_SET_ANIMATION_POINTER` | `ptr3` | animation pointer install |
| `$1D` | `EVENT_WRITE_WORD_TEMPVAR` | `word` | tempvar write |
| `$1E` | `EVENT_WRITE_WRAM_TEMPVAR` | `word` | tempvar from WRAM |
| `$1F` | `EVENT_WRITE_TEMPVAR_TO_VAR` | `byte` | variable write from tempvar |
| `$20` | `EVENT_WRITE_VAR_TO_TEMPVAR` | `byte` | tempvar write from variable |
| `$21` | `EVENT_WRITE_VAR_TO_WAIT_TIMER` | `byte` | wait timer write |
| `$22` | `EVENT_SET_DRAW_CALLBACK` | `callbackptr` | C0 callback install |
| `$23` | `EVENT_SET_POSITION_CHANGE_CALLBACK` | `callbackptr` | C0 callback install |
| `$24` | `EVENT_LOOP_TEMPVAR` | - | loop count from tempvar |
| `$25` | `EVENT_SET_PHYSICS_CALLBACK` | `callbackptr` | C0 callback install |
| `$26` | `EVENT_SET_ANIMATION_FRAME_VAR` | `byte` | animation state |
| `$27` | `EVENT_BINOP_TEMPVAR` | `byte`, `word` | tempvar operation |
| `$28` | `EVENT_SET_X` | `word` | position write |
| `$29` | `EVENT_SET_Y` | `word` | position write |
| `$2A` | `EVENT_SET_Z` | `word` | position write |
| `$2B` | `EVENT_SET_X_RELATIVE` | `word` | relative position write |
| `$2C` | `EVENT_SET_Y_RELATIVE` | `word` | relative position write |
| `$2D` | `EVENT_SET_Z_RELATIVE` | `word` | relative position write |
| `$2E` | `EVENT_SET_X_VELOCITY_RELATIVE` | `word` | relative velocity write |
| `$2F` | `EVENT_SET_Y_VELOCITY_RELATIVE` | `word` | relative velocity write |
| `$30` | `EVENT_SET_Z_VELOCITY_RELATIVE` | `word` | relative velocity write |
| `$39` | `EVENT_SET_VELOCITIES_ZERO` | - | velocity clear |
| `$3B` | `EVENT_SET_ANIMATION` | `byte` | animation state |
| `$3C` | `EVENT_NEXT_ANIMATION_FRAME` | - | animation state |
| `$3D` | `EVENT_PREV_ANIMATION_FRAME` | - | animation state |
| `$3E` | `EVENT_SKIP_N_ANIMATION_FRAMES` | `byte` | animation state |
| `$3F` | `EVENT_SET_X_VELOCITY` | `word` | velocity write |
| `$40` | `EVENT_SET_Y_VELOCITY` | `word` | velocity write |
| `$41` | `EVENT_SET_Z_VELOCITY` | `word` | velocity write |
| `$42` | `EVENT_CALLROUTINE` | `callroutine` | native routine bridge |
| `$43` | `EVENT_SET_PRIORITY` | `byte` | priority/state write |
| `$44` | `EVENT_WRITE_TEMPVAR_WAITTIMER` | - | wait timer write from tempvar |

## First Work Packages

### 1. Decoder Coverage Audit

Status: first pass complete in `notes/c3-actionscript-semantics-audit.md`.

Build a report that walks every `event-script-asset`, `event-bytecode-asset`,
and `event-bytecode-label` in `notes/c3-source-data-map.md` and records:

- first opcode
- decoded length before terminal or unknown opcode
- unknown opcode address, if any
- external callback targets
- branch/call targets inside C3
- whether the decode stops by terminal, byte limit, instruction limit, or
  unknown operand shape

This turns the current named-payload manifest into a full C3 script frontier.

### 2. Callback Argument Contracts

`EVENT_CALLROUTINE` is the main semantic bridge from event bytecode into native
C0/C4/EF helpers. `tools/decode_event_script.py` already has a
`CALL_ARG_COUNTS` seed table; the next pass should turn those counts into named
argument contracts where evidence is strong.

High-value callback families:

- C0 current-slot movement and visual profile helpers
- C0 collision/cache wrappers
- C4 vector, display, and text-yield helpers
- EF timed-delivery row/state helpers

### 3. Reassembly-Friendly Script Family

Status: thirteen pilots complete.

- `notes/c3-event-script-source-pilot.md`: movement pulse presets,
  `27` source/data-map rows, `617` validated bytes.
- `notes/c3-timed-delivery-source-pilot.md`: timed-delivery controller proper,
  `C3:43DB..C3:4508`, `301` validated bytes.
- `notes/c3-service-event-movement-source-pilot.md`: adjacent service-event
  movement scripts, `C3:4508..C3:48C4`, `956` validated bytes.
- `notes/c3-service-animation-source-pilot.md`: neighboring service animation
  helpers and events, `C3:48C4..C3:4D39`, `1141` validated bytes.
- `notes/c3-service-presentation-effects-source-pilot.md`: neighboring
  presentation/effect corridor, `C3:4D39..C3:4E73`, `314` validated bytes.
- `notes/c3-itoi-production-intro-source-pilot.md`: first split from the large
  `C3:4E73..C3:5F8B` payload cluster, `C3:4E73..C3:4FC7`, `340` validated
  bytes.
- `notes/c3-intro-presentation-paths-source-pilot.md`: second split from the
  large `C3:4E73..C3:5F8B` payload cluster, `C3:4FC7..C3:51FD`, `566`
  validated bytes.
- `notes/c3-intro-cast-scroll-setup-source-pilot.md`: third split from the
  large `C3:4E73..C3:5F8B` payload cluster, `C3:51FD..C3:5231`, `52`
  validated bytes.
- `notes/c3-intro-cast-member-paths-source-pilot.md`: high-ranked frontier
  seam covering the cast-screen refresh helper task, flat/depth actor
  initializers, and ebsrc scripts 802-803 and 809-825, `C3:5F8B..C3:62C0`,
  `821` validated bytes.
- `notes/c3-teleport-destination-paths-source-pilot.md`: high-ranked frontier
  seam covering the reusable teleport-destination rise/fade helper and ebsrc
  scripts 153-160, `C3:C94E..C3:CC24`, `726` validated bytes.
- `notes/c3-temp-flag-door-close-paths-source-pilot.md`: high-ranked frontier
  seam covering the door-close/temp-flag handoff helpers, ebsrc scripts
  115-119, the shared party-look task, scripts 468-472, and the helper at
  `C3:C143`, `C3:BEA4..C3:C167`, `707` validated bytes.
- `notes/c3-party-look-window-gfx-paths-source-pilot.md`: high-ranked frontier
  seam covering the window-gfx variant loop, ebsrc script 467's random-facing
  idle loop, scripts 465-466 party-look movement paths, and the small
  `$2B32` pulse task at `C3:3DBE`, `C3:3C1D..C3:3DD4`, `439` validated
  bytes.
- `notes/c3-tunnel-ghost-zombie-paths-source-pilot.md`: high-ranked frontier
  seam covering the `C3:B70C` face-target/shake helper plus ebsrc scripts
  73-90, `C3:B70C..C3:BAA3`, `919` validated bytes.

`tools/build_c3_event_script_source_pilot.py` emits these as labeled
macro-source representations while validating against the local ROM bytes.

Candidate/follow-up families for this milestone:

- `C3:A0B2..C3:AB26` movement pulse preset family - pilot complete
- `C3:43DB..C3:4508` timed-delivery controller family - pilot complete
- `C3:4508..C3:48C4` adjacent service-event movement scripts - pilot complete
- `C3:48C4..C3:4D39` neighboring service animation helpers/events - pilot complete
- `C3:4D39..C3:4E73` neighboring service presentation/effect corridor - pilot complete
- `C3:4E73..C3:4FC7` Itoi production intro first split - pilot complete
- `C3:4FC7..C3:51FD` intro/presentation movement paths - pilot complete
- `C3:51FD..C3:5231` intro cast-scroll setup scripts 799-800 - pilot complete
- `C3:5231..C3:5F8B` script 801 cast-scroll/cast-spawn payload - blocked on
  additional native callback contracts and macro coverage before promotion
- `C3:5F8B..C3:62C0` intro cast-member path scripts 802-803 and 809-825 -
  pilot complete
- `C3:3C1D..C3:3DD4` party-look/window-gfx paths scripts 465-467 -
  pilot complete
- `C3:BEA4..C3:C167` temp-flag door-close path scripts 115-119 and 468-472 -
  pilot complete
- `C3:C94E..C3:CC24` teleport-destination paths scripts 153-160 - pilot complete
- `C3:B70C..C3:BAA3` tunnel ghost/zombie paths - pilot complete
- `C3:BAA3..C3:BD03` adjacent tunnel ghost common/warp helpers - natural
  follow-up seam
- `C3:0295..C3:AB8A` event 222-224 movement helper family

The next pilots should emit symbolic event bytecode with labels, opcodes, and
operands while preserving byte-equivalence against the ROM-backed scaffold.
Use `tools/build_c3_source_pilot_frontier.py` to rank ready seams before picking
the next family.

### 4. Non-Event Payload Split

Keep these out of the event VM decoder unless evidence changes:

- intro movement pattern records around `C3:9FF2`
- `C3:F819` battle visual effect-script payload
- `C3:FDBD` delivery placeholder sprite table
- compact raw/frontier data rows in `notes/c3-source-data-map.md`

## Suggested Immediate Target

The movement pulse preset family, timed-delivery controller, adjacent
service-event movement scripts, neighboring service-animation helper/event
cluster, presentation/effect corridor, first Itoi production intro split,
intro/presentation movement paths, cast-scroll setup scripts, intro
cast-member paths, party-look/window-gfx paths, temp-flag door-close paths,
teleport-destination paths, and tunnel ghost/zombie paths now have source-form
pilots. The refreshed frontier currently points at `C3:BB73..C3:BD03` as the
best ready seam; adjacent follow-ups include `C3:3DD4..C3:4392` once the
`C4:67E6` callback contract is pinned, `C3:C167..C1E0` once the `C0:C682`
callback contract is pinned, `C3:62C0..C3:6834` once the `C4:6B51` callback
contract is pinned, and the blocked `C3:5231` script 801
cast-scroll/cast-spawn payload.
