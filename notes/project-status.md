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
- `notes/readable-source-bank-closure.md` is the stricter dashboard for the
  completed readable-source closure phase: decoded asm versus preserved
  corridors in the source-heavy banks.
- `notes/source-readiness-triage.md` is the implementation queue for the next
  semantic phase.

## What Is Complete

The structural scaffold phase is complete across the configured ROM banks.

That means the project can reproduce and protect every byte in banks `C0..EF`
through checked-in assembler scaffold files. The scaffolds are stable enough to
use as an organizing layer for romhacking, source extraction, table work, asset
emission, and future porting research.

Readable source-bank closure is also complete for the audited source-heavy
banks: `C0`, `C1`, `C2`, `C4`, and `EF` all report `0` preserved source
corridors in `notes/readable-source-bank-closure.md`.

## Terminology

Use these terms carefully:

- **Scaffold-backed**: bytes are represented in checked-in assembler artifacts
  and pass byte-equivalence validation.
- **Decoded source**: bytes have been converted into instruction-by-instruction
  assembly, table definitions, or typed data emitters.
- **Semantically understood**: decoded source has reliable names, comments,
  call/data evidence, and subsystem contracts.

All banks are scaffold-backed. The native-code-heavy banks have no remaining
preserved source corridors by the current audit. The next distinction is
semantic: byte-true source/data is not the same as fully documented script,
text, table, graphics, audio, or runtime behavior.

## What Is Not Complete

The project is not yet a full decompilation.

A closed scaffold and a closed readable-source audit prove that the bytes are
accounted for and that native-source corridors are no longer hidden in the
audited source-heavy banks. They do not prove that every routine, data record,
script opcode, text command, or asset payload is semantically understood.

Remaining work is mostly:

- promoting local working names and comments into stable source-facing contracts
- turning table and WRAM contracts into typed source/data definitions
- documenting event, action, and text bytecode VM semantics
- making script/text assets reassembly-friendly
- adding render/decode fixtures for graphics, audio, text, and map assets
- building enough semantic models to support higher-level C or engine work

## Bank Groups

| Banks | Current role | Next kind of work |
| --- | --- | --- |
| `C0` | overworld/runtime source | Tighten entity, movement, interaction, collision, teleport, and task semantics. |
| `C1` | text/menu/UI source | Tighten text engine, menu, file-select, and battle front-end semantics. |
| `C2` | battle runtime source | Tighten action dispatch, target selection, status/effect, PSI, and battle visual semantics. |
| `C3` | script/data/helper bank | Promote event/actionscript VM opcodes, operand shapes, and control-flow contracts. |
| `C4` | visual/render source | Tighten text tile, window, color/HDMA, file-select, town-map, and presentation side effects. |
| `C5..C9` | text/script banks | Strengthen text-command VM semantics and text extraction/reinsertion contracts. |
| `CA..CE` | battle graphics/animation/asset banks | Add typed emitters and optional render/decode fixtures. |
| `CF..D0`, `D5`, `D7`, `D8` | generated data/table banks | Expand table contracts and variable subrecord semantics. |
| `D1..D4`, `D6`, `D9..DF` | map/sprite/asset banks | Add asset render/decode fixtures and stronger metadata names. |
| `E0..E1` | UI/font/town-map/data banks | Refine UI/font/town-map payload contracts. |
| `E2..EE` | audio/data banks | Inventory or decode audio-pack payloads when audio work becomes a priority. |
| `EF` | mixed save/debug/text/data bank | Refine save/debug/text/glyph/map-data contracts and text payload semantics. |

## Best Next Manual Work

The highest leverage work is now semantic, starting with bytecode and payloads
that romhackers need to edit confidently:

1. `C3`: event/actionscript opcode and operand semantics. The first audit is
   now in `notes/c3-actionscript-semantics-audit.md`: `177` rows audited and
   `177` syntactically complete with the current decoder, with `85` native
   callback byte-count seeds captured. `116` source-form pilots are checked in
   under `src/c3/event_scripts/` and cover `46146` validated bytes. Recent
   additions include cast-screen orbit/step-spawn continuations, party-member
   orbit damping, Threed escaper arc/landing continuations, T-Stage/T-Stage 3
   performance routes, meteorite/window paths, bus-driver attention/Magic
   Butterfly releases, Winters route transitions, and flyover palette/random
   movement paths.
   `notes/c3-source-pilot-frontier.md` now ranks remaining source-pilot seams;
   the current frontier has `11` gaps and `0` ready-ranked gaps. The next best
   manual seam is `C3:199E..C3:1A04`, blocked on the unpinned `C0:18F3`
   callback contract.
2. `C1` plus `C5..C9`/`EF`: text-command VM semantics and reassembly-friendly
   text payloads.
3. `C0`/`C2`/`C4`: subsystem side-effect docs for overworld, battle, and
   rendering workflows.
4. Asset/data banks: render/decode fixtures and public-safe extraction planning
   after the semantics work is stronger.

## Key References

- `notes/source-scaffold-status.md`
- `notes/source-readiness-triage.md`
- `notes/source-bank-graduation-pipeline.md`
- `notes/c3-actionscript-semantics-roadmap.md`
- `notes/c3-actionscript-semantics-audit.md`
- `notes/c3-event-script-source-pilot.md`
- `notes/c3-timed-delivery-source-pilot.md`
- `notes/c3-service-event-movement-source-pilot.md`
- `notes/c3-service-animation-source-pilot.md`
- `notes/c3-service-presentation-effects-source-pilot.md`
- `notes/c3-itoi-production-intro-source-pilot.md`
- `notes/c3-intro-presentation-paths-source-pilot.md`
- `notes/c3-intro-cast-scroll-setup-source-pilot.md`
- `notes/c3-intro-cast-member-paths-source-pilot.md`
- `notes/c3-party-look-window-gfx-paths-source-pilot.md`
- `notes/c3-temp-flag-door-close-paths-source-pilot.md`
- `notes/c3-teleport-destination-paths-source-pilot.md`
- `notes/c3-tunnel-ghost-zombie-paths-source-pilot.md`
- `notes/c3-tunnel-ghost-follower-paths-source-pilot.md`
- `notes/c3-tunnel-ghost-entity-setup-paths-source-pilot.md`
- `notes/c3-vehicle-coordinate-paths-source-pilot.md`
- `notes/c3-boogy-tent-city-bus-paths-source-pilot.md`
- `notes/c3-palette-fade-coordinate-paths-source-pilot.md`
- `notes/c3-falling-bounce-yield-paths-source-pilot.md`
- `notes/c3-teleport-destination-prelude-paths-source-pilot.md`
- `notes/c3-bus-tunnel-bridge-paths-source-pilot.md`
- `notes/c3-anim-port-flag-switch-source-pilot.md`
- `notes/c3-leftward-bounds-release-paths-source-pilot.md`
- `notes/c3-anim-port-direction-tasks-source-pilot.md`
- `notes/c3-rightward-live-area-bounce-yield-source-pilot.md`
- `notes/c3-var4-animation-side-step-helpers-source-pilot.md`
- `notes/c3-window-gfx-loader-prologue-source-pilot.md`
- `notes/c3-tunnel-ghost-warp-text-helpers-source-pilot.md`
- `notes/c3-movement-vector-core-helpers-source-pilot.md`
- `notes/c3-facing-pulse-helpers-source-pilot.md`
- `notes/c3-teleport-flyover-pulse-helpers-source-pilot.md`
- `notes/c3-sky-runner-electric-effect-helpers-source-pilot.md`
- `notes/c3-small-terminal-helper-cleanup-source-pilot.md`
- `notes/c3-cast-screen-tenda-king-paths-source-pilot.md`
- `notes/c3-live-area-facing-movement-paths-source-pilot.md`
- `notes/c3-onett-townhall-movement-paths-source-pilot.md`
- `notes/c3-onett-townhall-door-paths-source-pilot.md`
- `notes/c3-position-text-door-sound-paths-source-pilot.md`
- `notes/c3-bubble-monkey-route-paths-source-pilot.md`
- `notes/c3-pokey-bubble-monkey-paths-source-pilot.md`
- `notes/c3-direction-tracker-townhall-paths-source-pilot.md`
- `notes/c3-tstage-performance-movement-paths-source-pilot.md`
- `notes/c3-stage-visual-pulse-paths-source-pilot.md`
- `notes/c3-var0-animation-collision-probe-source-pilot.md`
- `notes/c3-area-wait-random-wander-helpers-source-pilot.md`
- `notes/c3-teleport-flyover-coordinate-helpers-source-pilot.md`
- `notes/c3-threed-fight-matent-paths-source-pilot.md`
- `notes/c3-position-door-close-helpers-source-pilot.md`
- `notes/c3-position-text-yield-paths-source-pilot.md`
- `notes/c3-monotoly-coordinate-text-paths-source-pilot.md`
- `notes/c3-tstage-dance-sequence-paths-source-pilot.md`
- `notes/c3-gum-machine-flyover-paths-source-pilot.md`
- `notes/c3-flyover-scene-wait-paths-source-pilot.md`
- `notes/c3-position-watch-new-entity-paths-source-pilot.md`
- `notes/c3-townhall-direction-common-paths-source-pilot.md`
- `notes/c3-townhall-coffee-tea-gatekeeper-paths-source-pilot.md`
- `notes/c3-bus-transition-route-paths-source-pilot.md`
- `notes/c3-twoson-bus-route-paths-source-pilot.md`
- `notes/c3-bus-tunnel-desert-route-paths-source-pilot.md`
- `notes/c3-space-tunnel-crash-paths-source-pilot.md`
- `notes/c3-skyrunner-crash-winter-paths-source-pilot.md`
- `notes/c3-party-member-tracker-winter-paths-source-pilot.md`
- `notes/c3-winters-ride-launch-paths-source-pilot.md`
- `notes/c3-early-pose-coordinate-pair-paths-source-pilot.md`
- `notes/c3-early-party-look-coordinate-paths-source-pilot.md`
- `notes/c3-party-look-meteorite-paths-source-pilot.md`
- `notes/c3-winter-target-release-paths-source-pilot.md`
- `notes/c3-onett-door-close-gate-paths-source-pilot.md`
- `notes/c3-onett-door-close-coordinate-paths-source-pilot.md`
- `notes/c3-bus-bridge-obscured-route-paths-source-pilot.md`
- `notes/c3-sky-runner-electric-effect-release-paths-source-pilot.md`
- `notes/c3-window-gfx-sequence-release-paths-source-pilot.md`
- `notes/c3-intro-cast-followup-paths-source-pilot.md`
- `notes/c3-threed-escaper-appear-paths-source-pilot.md`
- `notes/c3-bus-bridge-route-terminal-paths-source-pilot.md`
- `notes/c3-battle-swirl-interaction-paths-source-pilot.md`
- `notes/c3-battle-swirl-visual-countdown-paths-source-pilot.md`
- `notes/c3-npc-attention-path-helpers-source-pilot.md`
- `notes/c3-party-member-hop-text-paths-source-pilot.md`
- `notes/c3-visual-countdown-anchor-followers-source-pilot.md`
- `notes/c3-flyover-intro-text-release-paths-source-pilot.md`
- `notes/c3-direction-follower-display-reset-paths-source-pilot.md`
- `notes/c3-stage-brightness-terminal-helpers-source-pilot.md`
- `notes/c3-party-member-orbit-damping-paths-source-pilot.md`
- `notes/c3-cast-screen-orbit-continuation-source-pilot.md`
- `notes/c3-cast-screen-step-spawn-continuation-source-pilot.md`
- `notes/c3-threed-escaper-arc-continuation-source-pilot.md`
- `notes/c3-threed-escaper-landing-continuation-source-pilot.md`
- `notes/c3-tstage-dance-followup-paths-source-pilot.md`
- `notes/c3-tstage-dual-window-position-paths-source-pilot.md`
- `notes/c3-tstage-performance-upper-corridor-source-pilot.md`
- `notes/c3-tstage3-performance-routes-source-pilot.md`
- `notes/c3-tstage-long-choreography-release-source-pilot.md`
- `notes/c3-tstage-vstage-route-release-paths-source-pilot.md`
- `notes/c3-photo-scene-jump-release-source-pilot.md`
- `notes/c3-bus-driver-attention-coordinator-source-pilot.md`
- `notes/c3-npc-attention-wide-distance-gate-source-pilot.md`
- `notes/c3-meteorite-window-party-approach-paths-source-pilot.md`
- `notes/c3-bus-driver-attention-release-source-pilot.md`
- `notes/c3-magic-butterfly-pp-restore-release-source-pilot.md`
- `notes/c3-boogy-city-bus-movement-dispatch-source-pilot.md`
- `notes/c3-winters-ride-input-and-route-release-source-pilot.md`
- `notes/c3-winter-input-bubble-monkey-routes-source-pilot.md`
- `notes/c3-winter-coordinate-facing-routes-source-pilot.md`
- `notes/c3-winter-coordinate-transition-routes-source-pilot.md`
- `notes/c3-winter-input-battle-bg-transition-source-pilot.md`
- `notes/c3-flyover-palette-random-movement-paths-source-pilot.md`
- `notes/c3-source-pilot-frontier.md`
- `notes/bank-first-pass-coverage-index.md`
- `notes/data-contracts-c0-c4.md`
- `notes/reference-first-workflow.md`
- `notes/earthbound-localization-script-authoring-format.md`
- `notes/localization-script-source-index.md`
- `notes/localization-map-object-crosswalk.md`
- `notes/localization-movement-evidence.md`
