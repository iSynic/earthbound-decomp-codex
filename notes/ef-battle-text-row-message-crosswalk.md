# EF Battle Text Row-Message Crosswalk

This note is the first concrete crosswalk from the EF action-message islands to
source-backed `D5:7B68` battle-action rows. It expands the frontier note by
recording rows whose `+4` EF message pointer and `+8` C2 behavior pointer are
already joined by focused C2 notes.

Scope:

- EF row-message anchors in `src/ef/ef_4e20_c51b_text_payload_data.asm`
- C1 display lane: `C1:DD9F` row-message display from `C2:5C66`
- C2 behavior lane: `D5:7B68` row `+8` behavior pointers consumed through
  the C2 action-payload path

This is a consumer crosswalk, not an EB text macro decode. Exact `MSG_BTL_*`
labels remain stable unless the C2 behavior body proves a narrower result name.

## Status-Action Row Messages

These rows are the highest-value EF/C2 joins because the row message, behavior
body, success text, and fallback text are all visible.

| Row | Row `+4` EF message | Row `+8` C2 body | Behavior result payloads |
| ---: | --- | --- | --- |
| `75` | `EF:9C30` `MSG_BTL_HOUSHI` | `C2:8BBE` | Mushroomized/affliction+1 value `1`; emits `EF:6B81` or `EF:766E` |
| `76` | `EF:9C51` `MSG_BTL_TORITUKI` | `C2:8BFD` | Possessed/affliction+1 value `2`; emits `EF:6B98` or `EF:766E` |
| `78` | `EF:9CAD` `MSG_BTL_KABI_HOUSI` | `C2:8C69` | Crying/affliction+2 value `2`; emits `EF:6BBB` or `EF:766E` |
| `79..82` | `EF:9CD1`, `EF:9CF1`, `EF:9D14`, `EF:9D3E` | `C2:8CB8` | Immobilized/affliction+2 value `3`; emits `EF:6BD3` or `EF:766E` |
| `83` | `EF:9D62` `MSG_BTL_KOWAI_KOTOBA` | `C2:8CF1` | Solidified/affliction+2 value `4`; emits `EF:6BEF` or `EF:766E` |
| `84` | `EF:9D81` `MSG_BTL_AYASHI_KOTO` | `C2:8D3A -> C2:A056` | Strange/affliction+3 value `1`; emits `EF:6C3A` or `EF:766E` |
| `85` | `EF:9DA1` `MSG_BTL_FUUIN` | `C2:8D5A` | Concentration/PSI-seal affliction+4 value `4`; emits `EF:6C0B` or `EF:766E` |
| `86` | `EF:9DBD` `MSG_BTL_TACHIBA_THINK` | `C2:8DBB` | Direct strange/affliction+3 value `1`; emits `EF:6C3A` or `EF:766E` |
| `87` | `EF:9DDA` `MSG_BTL_KOGEPPU_IKI` | `C2:8DFC` | All-target crying-family sibling; grouped with the affliction+2 crying body |
| `90` | `EF:9E47` `MSG_BTL_MUSIC` | `C2:9F57 -> C2:9F06` | Asleep/affliction+2 value `1`; emits `EF:6C55` or `EF:766E` |
| `159` | `EF:8E3C` `MSG_BTL_ANTIPSI` | `C2:A3D1` | Item-side concentration/PSI-seal; emits `EF:6C0B` or `EF:766E` |
| `207` | `EF:83A8` `MSG_BTL_LAUGH_HEN` | `C2:8D3A -> C2:A056` | Strange-status wrapper reuse; emits `EF:6C3A` or `EF:766E` |

Important modeling point: the row `+4` message is the action presentation text
shown through `C1:DD9F`. The success/failure payloads listed above are separate
result scripts emitted later by the row `+8` behavior body through `DC1C`.

## Physical, Special, And Flavor Row Messages

These rows are also source-backed, but the behavior bodies are damage,
normalization, special-event, or message-only rather than simple affliction
writes.

| Row | Row `+4` EF message | Row `+8` C2 body | Current behavior read |
| ---: | --- | --- | --- |
| `100` | `EF:7EAC` `MSG_BTL_DOKU_KAMITUKI` | `C2:8F97` | Poison-on-hit physical action; secondary success text `EF:6B18` |
| `102` | `EF:7F02` `MSG_BTL_MULTI_ATTACK` | `C2:8FF9` | Exact double-bash wrapper over `C2:859F` |
| `104` | `EF:7F32` `MSG_BTL_FIREBALL` | `C2:900B` | One-target fire-damage wrapper |
| `117` | `EF:80C4` `MSG_BTL_TATUMAKI` | `C2:902C` | All-target physical wrapper over `C2:8651` |
| `118` | `EF:80E4` `MSG_BTL_WATER` | `C2:902C` | Same all-target physical wrapper reuse |
| `228` | `EF:8BE8` `MSG_BTL_KAMITSUKI_DIAMOND` | `C2:916E` | One-target diamondize action; emits `EF:6AC7` or `EF:7655` |
| `232` | `EF:8C58` `MSG_BTL_BAD_SMELL` | `C2:9254` | Odor/offense-reduction family; reports amount through C8 text via `DC66` |
| `247` | `EF:8E27` `MSG_BTL_WARP_NEAR` | `C2:90C6` | Battler normalization wrapper; can emit `EF:7142` and queue `EF:7123` |
| `248` | `EF:8D9F` `MSG_BTL_NEUTRALIZE_SPARKLE` | `C2:90C6` | Same normalization wrapper reuse |
| `273` | `EF:8EBE` `MSG_BTL_BAD_SMELL_GAS` | `C2:9254` | Odor/offense-reduction family reuse |
| `290` | `EF:8DDE` `MSG_BTL_TO_DIAMOND_DOG` | `C2:C14E` | Rainbow-colors / Master Belch-side special-event family |

Rows whose behavior body emits C8/C9 scripts should not force EF result names.
Keep the EF row-message labels as exact `MSG_BTL_*` anchors and document the
secondary script bank in the C2-focused note.

## Early Row-Message Anchors

The early row-message joins remain the cleanest `DD9F` examples:

| Row | Row `+4` EF message | Row `+8` C2 body | Current behavior read |
| ---: | --- | --- | --- |
| `4` | `EF:848C` | `C2:859F` | Bash |
| `5` | `EF:84B6` | `C2:8740` | Shoot |
| `6` | `EF:8530` | `C2:8770` | Spy |
| `7` | `EF:89E0` | `C2:AD1B` | Pray |
| `10..31` | `EF:8543` | PSI wrapper families | Shared PSI row message; byte-substitution PSI name |

## How To Use This Crosswalk

For future EF payload work:

- If a row `+4` message has a row-specific C2 body and a result script, name the
  EF row-message anchor conservatively around the exact `MSG_BTL_*` text and
  document the behavior in this crosswalk.
- If the C2 body emits a separate EF script through `DC1C` or `DC66`, keep that
  result payload named independently from the row-message text.
- If only table order or reference names are known, keep the anchor
  symbol-derived and leave it in the action-island frontier.

## Next Crosswalk Frontier

The next rows to mine are the numeric-effect and no-op flavor groups:

- rows `95..98`, `48`, `49`, and `96` from the stat/resource family
- rows with `C2:9033` and neighboring no-op tails from the late flavor-only run
- special-event rows `243`, `244`, and Final Prayer rows `291..299`, where
  many row messages live outside EF but the secondary result scripts still
  affect the battle-text contract
