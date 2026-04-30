# C2 Action Dispatch Runtime Polish

This note records the byte-neutral C2 action-dispatch polish slice. It promotes
the local contract between the `D5:7B68` battle-action descriptor table, derived
candidate-row action bytes, target-mask construction, and second-pointer payload
application.

Primary source modules:

- `src/c2/c2_40a4_apply_battle_action_second_pointer_payload.asm`
- `src/c2/c2_4477_build_class2_derived_action_code.asm`
- `src/c2/c2_4703_dispatch_class2_derived_action.asm`

Related evidence notes:

- `notes/class2-handoff-4477-4703.md`
- `notes/class2-second-pointer-consumer-40a4.md`
- `notes/class2-mask-helper-family.md`
- `notes/class2-descriptor-field-4e-and-d57b68.md`
- `notes/class2-d57b68-battle-action-table-match.md`

## Derived Action Bytes

`C2:4477` accepts a candidate row base in A, usually from the
`$9FAC + 0x4E * n` row domain. It consults:

- ranked candidate lists `$AD7A/$AD82`
- row byte `+0x04`
- the `D5:7B68` battle-action descriptor table

The routine writes:

| Candidate row byte | Role |
| --- | --- |
| `+0x09` | compact derived action code |
| `+0x0A` | action parameter, target index, or ranked-list index |

The source comment deliberately keeps this mechanical. The current local proof
is strongest for the fact that `C2:4703` consumes these bytes as action code and
parameter; exact enum names for every `+0x09` value still need more end-to-end
action-table coverage.

## Descriptor Table Join

The `D5:7B68` layout used by this slice is:

| Offset | Current best role |
| --- | --- |
| `+0x00` | action direction/class selector |
| `+0x01` | target-shape selector |
| `+0x02` | action type |
| `+0x03` | cost byte |
| `+0x04` | message/presentation pointer |
| `+0x08` | action/behavior pointer |

The `+0x00` and `+0x01` bytes directly influence `C2:4477`'s derived
`+0x09/+0x0A` writes. The `+0x08` pointer is consumed by `C2:40A4` through the
second-pointer path.

## Target-Mask Dispatch

`C2:4703` accepts a candidate row base in A, clears `$A96C/$A96E`, then
dispatches on row byte `+0x09`. Several branches consume row byte `+0x0A`.

The dispatch branches build, prune, or target bits through the class-2 mask
helper family:

- `C2:6BFB`
- `C2:6C82`
- `C2:6D04`
- `C2:6E77`
- `C2:6FDC`
- `C2:7029`
- `C2:7089`
- `C2:416F`

The important promoted contract is that `$A96C/$A96E` is the current 32-bit
target mask for the derived action, not a generic scratch pair.

## Second-Pointer Application

`C2:40A4` is the consumer for the second pointer from a `D5:7B68` action
descriptor. The caller stages that pointer in direct-page `$1E/$20`; the routine
copies it to local `$06/$08`.

Runtime shape:

1. wait for `C2:EACF` to report that the battle effect step is ready
2. iterate targeted bits in the `$A21C` domain
3. iterate targeted bits in the `$9FAC` candidate-row domain
4. for each targeted bit, rebuild target text context through `C2:3D05`
5. dispatch the same fixed payload pointer through `C0:9279`

That makes `C2:40A4` an action-payload applicator over the current target mask.
It is not just a passive animation or data-stream routine.

`C2:416F` is the sibling mask-pruning helper in the same source module. It
removes currently targeted rows from `$A96C/$A96E` when their candidate row is
inactive or in blocked row states.

## Decomp Value

This slice makes the selected-row controller more actionable:

- `D5:7B68` is now tied to source-commented consumers for metadata bytes and the
  second action pointer.
- candidate row bytes `+0x09/+0x0A` are documented as the handoff between action
  derivation and target-mask construction.
- `$A96C/$A96E` is explicitly documented as the current target mask.
- `C2:40A4` is documented as a per-target action-payload applicator, which is a
  useful bridge for later table-entry naming.

## Remaining Soft Spots

- final enum names for `+0x09` action codes and `+0x0A` parameter meanings
- the exact payload ABI behind `C0:9279`
- full local naming of all `D5:7B68` action entries beyond the currently strong
  early PSI and late anchor families
