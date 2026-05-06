# EF Battle Text Action-Island Consumer Frontier

This note narrows the remaining EF battle-text frontier after the payload
suffix pass. The goal is not to decode EB text bytecode into macros yet; it is
to keep the large `MSG_BTL_*` action islands aligned with the C1 display lanes
and the C2 action-table consumers that are already source-backed.

Concrete crosswalk follow-up:

- `notes/ef-battle-text-consumer-lane-contracts.md`
- `notes/ef-battle-text-row-message-crosswalk.md`
- `notes/ef-battle-text-row-pointer-recovery-frontier.md`

Primary source module:

- `src/ef/ef_4e20_c51b_text_payload_data.asm`

Primary consumer notes:

- `notes/c2-ef-battle-text-contract-workahead.md`
- `notes/class2-d57b68-battle-action-table-match.md`
- `notes/c2-action-dispatch-runtime-polish.md`
- `notes/c2-psi-common-runtime-polish.md`
- `notes/class2-late-physical-special-family-c28f97-c2900b.md`
- `notes/class2-late-flavor-tail-c2902c-c2904e.md`

## Consumer Lanes

The action-island labels should be read through four distinct C1/C2 lanes:

- `C1:DD9F` row-message lane: `C2:5C66` selects the `D5:7B68` row `+4`
  message pointer and displays it in forced mode `1`.
- `C1:DC1C` direct-result lane: C2 callers stage a hardcoded EF pointer in
  `$0E/$10` and display a status/result script directly.
- `C1:DC66` `ActionAmount` lane: C2 callers stage an EF script plus a
  secondary payload consumed by `PRINT_ACTION_AMOUNT (1C 0F)`.
- `C1:DD7C` `ByteSubstitution` lane: C2 stages `$9D11` before displaying an EF
  script that executes `LOAD_BYTE_SUBSTITUTION (19 1F)`.

The late `D5:7B68` row `+8` pointer is a behavior/action payload consumed by
`C2:40A4`; it is not itself the EF message pointer. Its body may then emit
additional EF result scripts through `DC1C` or `DC66`.

## Proved Row-Message Joins

The front EBATTLE1 row-message joins are currently the strongest:

| Action-table row | Row `+4` EF pointer | Current consumer read |
| ---: | --- | --- |
| `0x0004` | `EF:848C` | Bash/attack row message via `DD9F` |
| `0x0005` | `EF:84B6` | Shoot row message via `DD9F` |
| `0x0006` | `EF:8530` | Spy/check row message via `DD9F` |
| `0x0007` | `EF:89E0` | Pray row message via `DD9F` |
| `0x000A..0x0019` | `EF:8543` | Shared PSI row message via `DD9F`, with PSI-name `ByteSubstitution` |

EBATTLE2 also has several late-table anchors that are strong enough to keep as
consumer-ready handoff points:

| Action-table row | Row `+4` EF pointer | Current consumer read |
| ---: | --- | --- |
| `99` | `EF:7E88` | Full-heal/fuel-supply row message |
| `100` | `EF:7EAC` | Poison-on-hit physical row message |
| `101` | `EF:7ED5` | Fired-missile projectile/explosive row message |
| `102` | `EF:7F02` | Double-bash / attack-continuously row message |
| `104` | `EF:7F32` | Fire-damage / flaming-fireball row message |
| `117` | `EF:80C4` | All-target physical wrapper, tornado text |
| `118` | `EF:80E4` | All-target physical wrapper, gigantic-blast text |

The EBATTLE1 action tail has a proved late status row-message cluster:

| Action-table row | Row `+4` EF pointer | Current consumer read |
| ---: | --- | --- |
| `75..76` | `EF:9C30/9C51` | Persistent-status row messages; behavior bodies emit success `EF:6B81/6B98` or fallback `EF:766E` |
| `78..87` | `EF:9CAD..9DDA` | Temporary-status row messages; behavior bodies emit success `EF:6BBB..6C3A` or fallback `EF:766E` |
| `90` | `EF:9E47` | Asleep row message; the `+8` body emits success `EF:6C55` or fallback `EF:766E` |

The row-message crosswalk expands this into the currently source-backed status
rows (`53`, `58`, `75`, `76`, `78..87`, `90`, `159`, and `207`) plus late
physical, special, item, and event rows (`99..102`, `104`, `117`, `118`,
`140`, `228`, `232`, `243`, `244`, `247`, `248`, `273`, and `290`).

Rows whose C2 behavior bodies are known but whose row `+4` EF pointers are not
locally recovered should stay out of the proved-join table. The current
behavior-known frontier includes numeric-effect rows `95..98`, `48`, `49`,
`96`, `233`, and `234`, PSI-side healing rows `32..35`,
projectile/explosive rows `64` and `65`, plus late no-op/flavor rows that
return through `C2:9033` and neighboring tiny no-op tails. These are good C2
behavior notes, but not yet EF row-message naming evidence.

## Direct Result Joins Adjacent To Action Islands

These are not row `+4` action messages, but they sit in the same EF payload
neighborhood and should remain visibly separate:

- `EF:843F`, `EF:8444`, and `EF:8445` are battle-start status announcements
  displayed after C2 builds target text context; the EF source now names them
  `BattleStart...StatusAnnouncementText`.
- `EF:845D` and `EF:8477` are random-action strange/mushroom status text
  emitted directly before the action-table row message selection; the EF source
  now names them `RandomAction...StatusText`.
- `EF:72F7`, `EF:733D`, and `EF:743B` are special-event continuations emitted
  by the row `243` and `244` behavior bodies after their row `+4` presentation
  messages at `EF:72F6` and `EF:7415`.
- `EF:6BEF` and `EF:766E` are result scripts emitted by item-side
  solidification rows whose row `+4` presentation text can live in C9 instead
  of EF.
- `EF:8814`, `EF:8823`, and `EF:8837` are Thunder presentation/miss scripts
  selected by the C2 Thunder common helper.
- `EF:7843` is the Time Stop return/result script; it is separate from the
  action row message at `EF:9B02`.

## Naming Policy For Remaining Action Islands

Keep the exact `MSG_BTL_*` anchor names for the unproved action islands until a
row `+4` pointer and row `+8` behavior body are joined:

- `EF:7E25..843F` EBATTLE2: late physical, special, and message-only action
  row-message candidates. Promote only the rows with local C2 body evidence.
- `EF:89FE..8FAD` EBATTLE3: enemy-action text include. Promoted anchors include
  rows `140/247`, `159`, `228`, `232`, `248`, `273`, and `290`; the remaining
  labels should stay symbol-derived until specific `D5:7B68` rows are mapped.
- `EF:9A47..9EF4` EBATTLE1 tail: status, flavor, item, and special action
  row-message candidates. Promote in small families, such as concentration
  seal, Time Stop, call-for-help, or breath/status-flavor, only after C2 bodies
  prove the runtime role.

Direct status/result scripts are different: if a C2 body chooses a hardcoded EF
pointer through `DC1C`, or an `ActionAmount` script through `DC66`, it is safe
to name the EF anchor around that result payload even when the surrounding
action island remains symbol-derived.

## Best Next Pass

The highest-value next EF/C2 join is recovering local row `+4` pointer evidence
for the behavior-known rows recorded in
`notes/ef-battle-text-row-pointer-recovery-frontier.md`. For each new row,
record:

- row id and row `+0..+3` metadata
- row `+4` EF message pointer
- row `+8` C2 behavior pointer
- any secondary EF result scripts emitted by the behavior body
- whether the row message can graduate from exact `MSG_BTL_*` anchor to a
  gameplay-facing name

Do not promote an EF row-message label from the row `+8` behavior body alone.
That body proves result lanes and gameplay effects, but the `C1:DD9F`
presentation text comes from the row `+4` field.
