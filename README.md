# EarthBound Decomp Scaffold

This repository is a work-in-progress reverse-engineering scaffold for the US
headerless EarthBound ROM.

The goal is to turn the ROM into durable, byte-equivalent, human-readable source
modules with enough documentation to support romhacking, research, and eventual
higher-level source reconstruction.

It is not a ROM distribution. It is not yet a finished source port. Bring your
own legally obtained ROM.

## What This Is

This project currently focuses on three things:

- `src/`: source-bank scaffold modules that reproduce original ROM bytes
- `notes/`: research notes, subsystem maps, source handoffs, and validation docs
- `tools/`: Python helpers for ROM verification, decoding, cross-references,
  table inspection, source promotion, and byte-equivalence checks

The source scaffold is meant to preserve exact behavior while replacing opaque
byte ranges with named assembly/data modules. That gives future work a stable
base: romhackers can reason about routines and tables, and decompilation work can
promote known assembly into clearer abstractions over time.

## Current Status

The repo contains a closed byte-equivalent scaffold for all ROM banks currently
covered by the project. In practical terms, every bank has a scaffold that can be
validated against the original ROM bytes.

The stricter readable-source closure milestone is also complete for the audited
source-heavy banks: `C0`, `C1`, `C2`, `C4`, and `EF` now report `0` preserved
source corridors in `notes/readable-source-bank-closure.md`. Those banks are no
longer hiding native 65816 source behind coarse byte blobs.

That does not mean every routine is fully understood. The work is in layers:

1. Preserve every byte in a reproducible source scaffold.
2. Split code, data, tables, scripts, and assets into named source files.
3. Attach local evidence: callers, data contracts, reference corroboration, and
   notes.
4. Promote working names and structures into clearer source.
5. Eventually translate well-understood subsystems into higher-level code.

The next major work is semantic: turning byte-accurate source/data into
romhacker-grade contracts. The highest-priority gap is not hidden native source,
but game-specific bytecode and payload semantics: C3 event/actionscript assets,
text-command payloads, map/table contracts, graphics/audio asset metadata, and
the tooling needed to reassemble or safely modify those structures.

The C3 event/actionscript audit is now a concrete baseline: `177` script rows
decode syntactically with the current VM decoder, with `85` native callback
byte-count seeds captured for the next semantic naming pass.

## For Romhackers

This repo should be useful if you want to answer questions like:

- Where is this battle action, menu routine, table, or visual effect handled?
- What WRAM fields or ROM tables does a routine touch?
- Which banks contain code versus script/data/assets?
- How can a byte range be changed without losing track of exact ROM behavior?
- Which scripts, text commands, tables, or assets still need stronger semantic
  docs before they are comfortable to edit?
- What references already exist in `ebsrc`, legacy disassemblies, or local notes?

Good starting points:

- `notes/project-status.md`
- `notes/how-to-validate.md`
- `notes/python-tool-syntax-guide.md`
- `notes/readable-source-bank-closure.md`
- `notes/c3-actionscript-semantics-roadmap.md`
- `notes/c3-actionscript-semantics-audit.md`
- `notes/map-sprite-usage-contract.md`
- `notes/map-movement-usage-contract.md`
- `notes/map-object-bundles.md`
- `notes/map-object-layer-closure.md`
- `notes/map-milestone-closure.md`
- `notes/map-sector-bundles.md`
- `notes/map-tileset-bundles.md`
- `notes/map-fts-format-audit.md`
- `notes/map-fts-arrangement-contract.md`
- `notes/map-fts-animation-settings-contract.md`
- `notes/map-scene-composition-contract.md`
- `notes/map-collision-attribute-context.md`
- `notes/map-collision-pointer-contract.md`
- `notes/map-collision-runtime-bit-contract.md`
- `notes/map-palette-descriptor-context.md`
- `notes/map-palette-pointer-table-contract.md`
- `notes/map-palette-command-usage-contract.md`
- `notes/overworld-sprite-animation-roles.md`
- `notes/bank-c0-c2-closure.md`
- `notes/bank-c2-source-scaffold-handoff.md`
- `notes/source-scaffold-status.md`
- `notes/reference-first-workflow.md`
- `tools/inspect_battle_action.py`
- `tools/inspect_item.py`
- `tools/find_xrefs.py`
- `tools/decode_snippet.py`

## For Curious Readers

If you are not here to patch the ROM directly, the short version is this: the
project is turning a commercial SNES game ROM from a large stream of bytes into
named, testable parts.

That makes it easier to ask human questions about the game:

- Which code controls battles, menus, maps, text, audio, and save data?
- Which parts are executable program logic, and which parts are tables, scripts,
  graphics, or compressed assets?
- Where do fan tools and older disassemblies agree with the ROM, and where do we
  still need stronger evidence?
- What would need to be understood before a native port or reimplementation could
  be faithful?

The notes are written as working research, not polished articles, but they aim to
leave enough breadcrumbs that someone else can check the same evidence.

## Repository Layout

Tracked:

- `README.md` - this orientation guide
- `notes/` - durable research notes and generated human-readable reports
- `src/` - source scaffold modules by bank
- `tools/` - local analysis and validation tools

Ignored/local-only:

- `EarthBound (USA).sfc`
- `baserom/`
- `build/`
- `asm/`
- `dumps/`
- `refs/`
- `tmp_*.asm`

The `refs/` directory is intentionally local-only. Reference projects are useful
accelerators, but this repository should only publish conclusions that have been
locally checked or clearly labeled in notes.

## ROM Requirements

The tools expect the US headerless EarthBound ROM:

- Size: `3145728` bytes
- SHA-1: `D67A8EF36EF616BC39306AA1B486E1BD3047815A`
- Map mode: `0x31` (`HiROM/FastROM`)

Place the ROM at either:

```text
./EarthBound (USA).sfc
./baserom/EarthBound (USA).sfc
```

Then verify it:

```powershell
python tools/verify_rom.py
```

## Common Workflows

Validate one source bank:

```powershell
python tools/build_source_bank_scaffold.py --bank C2 --output src/c2/bank_c2_helpers_asar.asm
python tools/validate_source_bank_byte_equivalence.py --bank C2 --module all --combined --scaffold src/c2/bank_c2_helpers_asar.asm --strict
```

Regenerate source-bank docs:

```powershell
python tools/build_source_bank_candidate_ranges_doc.py --bank C2
python tools/build_source_bank_residual_map.py --bank C2
python tools/build_readable_source_bank_closure.py
```

Inspect a ROM table or gameplay record:

```powershell
python tools/inspect_item.py 0x11 --count 2
python tools/inspect_battle_action.py 78
python tools/inspect_table.py --contract ENEMY_CONFIGURATION_TABLE --index 0 --count 1 --field actions:w:0x46
```

Follow code and data references:

```powershell
python tools/find_xrefs.py C20ABC --limit 12
python tools/find_direct_callers.py C2:D121
python tools/decode_snippet.py C1:244C --count 20 --show-state --force-m8
python tools/trace_dp_window.py C2:7550 --count 16 --show-state --force-m16 --force-x16 --d 0x99CE
```

Work with EarthBound text/script payloads:

```powershell
python tools/extract_ebtext.py C2:0998 --length 4 --count 2 --stride 4
python tools/find_ebtext_command.py 1C 05 --limit 12
python tools/inspect_ebtext_hits.py 1D 24 --limit 2 --before 24 --after 56
python tools/decode_event_script.py C3:0295 C3:AB59
python tools/build_c3_actionscript_semantics_audit.py
```

Join map object visuals and behavior:

```powershell
python tools/build_map_sprite_usage_contract.py
python tools/build_map_movement_usage_contract.py
python tools/build_map_object_bundle_contract.py
python tools/build_map_sector_bundle_contract.py
python tools/build_map_tileset_bundle_contract.py
```

Regenerate the full checked-in map contract milestone:

```powershell
python tools/run_map_contracts.py
```

Build cross-bank naming or data-contract reports:

```powershell
python tools/build_working_name_manifest.py --banks C0 C1 C2 --output build/working-names-c0-c2.json
python tools/build_data_contract_manifest.py --json-out build/data-contracts-c0-c2.json --markdown-out notes/data-contracts-c0-c2.md
python tools/validate_data_contracts.py
```

## Tool Guide

High-use tools:

- `verify_rom.py`: confirm the local ROM is the expected input
- `split_rom.py`: split the ROM into per-bank build artifacts
- `find_xrefs.py`: scan for direct calls, likely memory accesses, and pointer hits
- `decode_snippet.py`: inspect 65816 code at a CPU address with optional width
  overrides
- `trace_dp_window.py`: track direct-page-heavy code paths
- `inspect_table.py`: inspect fixed-stride ROM tables
- `inspect_item.py`: decode item records
- `inspect_battle_action.py`: decode battle action records
- `lookup_wram_field.py`: map WRAM addresses to known reference structures
- `lookup_data_contract.py`: query curated ROM/WRAM data contracts
- `build_map_sprite_usage_contract.py`: join map placements to overworld
  sprite roles
- `build_map_movement_usage_contract.py`: join NPC movement IDs to ebsrc
  event/actionscript pointer targets
- `build_map_object_bundle_contract.py`: combine placed-object visuals,
  behavior entrypoints, event flags, text pointers, and map positions
- `build_map_sector_bundle_contract.py`: join sectors to objects, triggers,
  metadata, enemy groups, music options, hotspots, and map tile hashes
- `build_map_tileset_bundle_contract.py`: catalog map tileset IDs, `.fts`
  exports, palette settings, and sector dependencies
- `run_map_contracts.py`: regenerate the checked-in map contract milestone in
  dependency order
- `build_readable_source_bank_closure.py`: audit source-heavy banks for decoded
  asm versus preserved corridors after byte-equivalent scaffold closure
- `decode_event_script.py`: decode C3 event/actionscript payloads while the VM
  semantics are being promoted into durable docs
- `build_c3_actionscript_semantics_audit.py`: regenerate the C3
  event/actionscript frontier report from the source/data map and local ROM
- `emit_linear_source_module.py`: produce source-candidate assembly from a ROM
  range
- `promote_linear_range_to_decoded_source.py`: replace one byte corridor with
  decoded linear source and update the local range manifest
- `add_source_bank_range.py`: register a source range in a bank manifest
- `build_source_bank_scaffold.py`: regenerate a durable bank scaffold
- `validate_source_bank_byte_equivalence.py`: prove generated source bytes match
  the original ROM

See `notes/python-tool-syntax-guide.md` for common command forms, address
formats, and copy/paste examples.

Most generated output goes under `build/` and is intentionally ignored. Commit
durable conclusions in `notes/`, source modules in `src/`, and reusable tooling
in `tools/`.

## Source Scaffold Philosophy

The scaffold is intentionally conservative.

- Keep exact byte-equivalence first.
- Prefer small named source modules over huge anonymous byte corridors.
- Record evidence in notes before treating a name as settled.
- Distinguish code, tables, assets, text payloads, and event/action scripts.
- Use reference projects as accelerators, not unquestioned authority.
- Keep generated scratch out of Git unless it has become a durable report.

This lets the project support two tracks at once: practical romhacking today and
eventual decompilation or porting work later.

Terminology note: "scaffold-backed" means the bytes are accounted for in a
checked-in, byte-equivalent assembler artifact. It does not necessarily mean the
range has been converted into human-readable mnemonic assembly yet.

## Porting Outlook

Documenting every bank this way does not automatically produce C code, but it
does remove several hard blockers:

- control flow becomes findable and nameable
- tables and WRAM contracts become explicit
- asset/script banks can be separated from executable code
- byte-equivalent assembly can be refactored with validation
- higher-level systems can be lifted one subsystem at a time

Romhacks are not the limit. A future native engine or port is plausible, but it
depends on turning this source scaffold into stronger semantic models for battle,
menus, overworld scripts, rendering, audio, and save/state systems.

## Legal And Attribution Notes

This is an independent research project. It does not include a ROM and should
not be used to distribute copyrighted game data outside whatever legal framework
you are operating under.

Where local notes cite or borrow ideas from reference projects, keep the source
of that evidence visible. The goal is to make the work useful without hiding
uncertainty or provenance.
