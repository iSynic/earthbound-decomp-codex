# Project Status

This note is the short, durable orientation for the current state of the
project. It summarizes what is complete, what "complete" means, and what remains
before this becomes true human-readable source.

## Current Baseline

- First-pass bank notes exist for all `48 / 48` configured banks from `C0`
  through `EF`.
- Byte-equivalent scaffolds exist for all `48 / 48` banks under `src/<bank>/`.
- Every current bank scaffold is byte-equivalent against the expected ROM:
  `65536` protected bytes, `0` residual bytes, and validation status `OK` for
  each bank.
- `notes/source-scaffold-status.md` is the dashboard for the full bank table.
- `notes/source-readiness-triage.md` is the implementation queue for the next
  semantic phase.

## What Is Complete

The structural scaffold phase is complete across the configured ROM banks.

That means the project can reproduce and protect every byte in banks `C0..EF`
through checked-in assembler scaffold files. The scaffolds are stable enough to
use as an organizing layer for romhacking, source extraction, table work, asset
emission, and future porting research.

## Terminology

Use these terms carefully:

- **Scaffold-backed**: bytes are represented in checked-in assembler artifacts
  and pass byte-equivalence validation.
- **Decoded source**: bytes have been converted into instruction-by-instruction
  assembly, table definitions, or typed data emitters.
- **Semantically understood**: decoded source has reliable names, comments,
  call/data evidence, and subsystem contracts.

Most banks are scaffold-backed. Code-heavy banks such as `C0`, `C1`, `C2`,
`C4`, and `EF` still need a lot of decoded source and semantic promotion.

## What Is Not Complete

The project is not yet a full decompilation.

The source scaffolds still contain many byte-preserved corridors. A closed
scaffold proves that the bytes are accounted for, not that every routine, data
record, script opcode, or asset payload is semantically understood.

Remaining work is mostly:

- replacing preserved source corridors with decoded, labeled 65816 assembly
- promoting local working names into stable source labels
- turning table and WRAM contracts into typed source/data definitions
- separating event, action, and text bytecode from ordinary CPU code
- adding render/decode fixtures for graphics, audio, text, and map assets
- building enough semantic models to support higher-level C or engine work

## Bank Groups

| Banks | Current role | Next kind of work |
| --- | --- | --- |
| `C0` | overworld/runtime source | Decode entity, movement, interaction, collision, teleport, and task slices. |
| `C1` | text/menu/UI source | Decode text engine, menu, file-select, and battle front-end helpers. |
| `C2` | battle runtime source | Decode action dispatch, target selection, status/effect, PSI, and battle visual slices. |
| `C3` | script/data/helper bank | Improve event/actionscript VM decoding and split ordinary helpers from bytecode payloads. |
| `C4` | visual/render source | Decode text tile, window, color/HDMA, file-select, town-map, and presentation helpers. |
| `C5..C9` | text/script banks | Export text segments and strengthen text-command VM semantics. |
| `CA..CE` | battle graphics/animation/asset banks | Add typed emitters and optional render/decode fixtures. |
| `CF..D0`, `D5`, `D7`, `D8` | generated data/table banks | Expand table contracts and variable subrecord semantics. |
| `D1..D4`, `D6`, `D9..DF` | map/sprite/asset banks | Add asset render/decode fixtures and stronger metadata names. |
| `E0..E1` | UI/font/town-map/data banks | Refine UI/font/town-map payload contracts. |
| `E2..EE` | audio/data banks | Inventory or decode audio-pack payloads when audio work becomes a priority. |
| `EF` | mixed save/debug/text/data bank | Split save/SRAM, debug/menu, text/help, glyph, and map/data contracts. |

## Best Next Manual Work

The highest leverage work is semantic source extraction from the source-heavy
runtime banks:

1. `C2`: battle runtime slices backed by D5 table contracts.
2. `C1`: text/menu/UI slices that connect to C2 battle text and C4 rendering.
3. `C0`: overworld runtime slices around entity, movement, and interaction
   systems.
4. `C4`: visual/render helper slices where byte closure is already strong but
   side-effect comments matter.
5. `EF`: final-bank save/debug/text/data split, after choosing a tighter splitter
   strategy.

## Key References

- `notes/source-scaffold-status.md`
- `notes/source-readiness-triage.md`
- `notes/source-bank-graduation-pipeline.md`
- `notes/bank-first-pass-coverage-index.md`
- `notes/data-contracts-c0-c4.md`
- `notes/reference-first-workflow.md`
