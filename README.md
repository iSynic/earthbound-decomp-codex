# EarthBound Decomp Scaffold

This repository is a work-in-progress reverse-engineering scaffold for the US
headerless EarthBound ROM.

It does not contain a ROM, copyrighted game assets, or a finished source port.
Bring your own legally obtained ROM.

## Status Snapshot

The project has reached ROM-wide structural closure:

- `48 / 48` configured banks from `C0` through `EF` have checked-in
  byte-equivalent source scaffolds.
- Every bank scaffold validates against the expected ROM with `0` residual
  bytes and `0` byte-equivalence mismatches.
- The source-heavy native-code banks audited so far, `C0`, `C1`, `C2`, `C4`,
  and `EF`, report `0` preserved source corridors in
  `notes/readable-source-bank-closure.md`.
- C3's event/actionscript bank now has no unexplained raw follow-up frontier in
  `notes/c3-source-data-map.md`; remaining C3 work is semantic polish and
  source/script emission quality.
- The text-command VM has a generated semantics manifest at
  `notes/text-command-semantics-manifest.md`, with `29 / 32` top-level commands
  covered and the remaining `0x15..0x17` isolated as compressed-bank
  parser-only pseudo-opcodes.

In plain English: the ROM bytes are accounted for, and the known native-source
frontiers are closed. The remaining work is mostly semantics, editing workflow,
and asset/script polish.

## What This Is

The repo is an evidence-backed scaffold for understanding and modifying
EarthBound:

- `src/` contains source-bank scaffold modules that reproduce original ROM bytes.
- `notes/` contains research notes, subsystem maps, status dashboards, and
  generated human-readable reports.
- `tools/` contains Python helpers for ROM verification, disassembly, bytecode
  decoding, cross-reference search, table inspection, source promotion, and
  validation.

The source scaffold is intentionally conservative. It preserves exact behavior
while replacing opaque byte ranges with named assembly, tables, scripts, and
asset/data corridors.

## What Complete Means Here

Use these terms carefully:

- **Scaffold-backed** means a bank or range is represented by checked-in source
  artifacts and passes byte-equivalence validation.
- **Readable-source closed** means audited native 65816 source corridors have
  been promoted out of coarse byte blobs.
- **Semantically understood** means a routine, table, bytecode command, or asset
  has reliable names, evidence, consumers, and editing constraints.

This project is scaffold-backed across all configured banks. It is
readable-source closed for the audited source-heavy banks. It is not yet a full
semantic decompilation or C port.

## Current Good-Enough Boundary

For public romhacking/research use, a bank is considered good enough when:

1. It has byte-equivalent scaffold coverage.
2. It has no unexplained raw frontier, or any remaining prefix/padding is small,
   bounded, and documented.
3. Code, data, scripts, text, tables, and assets are classified separately.
4. Important names and contracts are machine-readable where possible.
5. A contributor can find the relevant validation command before editing.

By that definition, the ROM-wide scaffold phase is complete. C3 is understood
well enough for this phase; its remaining work is source/script polish, not
unknown-bank archaeology.

## What Is Still Not Complete

The next work is about confidence and usability:

- C3 event/actionscript opcode semantics, operand names, callback argument
  contracts, and reassembly-friendly script assets.
- C1 plus `C5..C9`/`EF` text-command and localization-script semantics.
- Stronger table, WRAM, map, graphics, font, UI, and audio payload contracts.
- Render/decode fixtures for major asset classes.
- A practical editing and validation guide for romhackers.
- Eventually, higher-level C or native-engine reconstruction one subsystem at a
  time.

Romhacks are not the limit, but a faithful port needs stronger semantic models
for battle, menus, overworld scripts, rendering, audio, text, and save/state
systems.

## Good Starting Points

- `notes/project-status.md` - durable project orientation
- `notes/source-scaffold-status.md` - all-bank byte-equivalent scaffold dashboard
- `notes/readable-source-bank-closure.md` - source-heavy bank closure dashboard
- `notes/c3-source-data-map.md` - C3 code/data/script split map
- `notes/c3-actionscript-semantics-audit.md` - C3 script decoder baseline
- `notes/text-command-semantics-manifest.md` - text-command VM coverage
- `notes/how-to-validate.md` - validation commands
- `notes/python-tool-syntax-guide.md` - common tool syntax
- `notes/reference-first-workflow.md` - how local refs are used without treating
  them as unquestioned truth

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
accelerators, but this repository should publish only conclusions that have been
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
python tools/validate_source_bank_byte_equivalence.py --bank C3
```

Regenerate core status dashboards:

```powershell
python tools/build_readable_source_bank_closure.py
python tools/build_c3_source_data_map.py
python tools/build_text_command_semantics_manifest.py
```

Inspect code, references, or data:

```powershell
python tools/find_xrefs.py C20ABC --limit 12
python tools/find_direct_callers.py C2:D121
python tools/decode_snippet.py C1:244C --count 20 --show-state
python tools/inspect_table.py --contract ENEMY_CONFIGURATION_TABLE --index 0 --count 1
```

Work with text and event/actionscript payloads:

```powershell
python tools/find_ebtext_command.py 1C 05 --limit 12
python tools/build_text_command_semantics_manifest.py
python tools/decode_event_script.py C3:0195 C3:0295 C3:AB59
python tools/build_c3_actionscript_semantics_audit.py
```

Most generated output goes under `build/` and is intentionally ignored. Commit
durable conclusions in `notes/`, source modules in `src/`, and reusable tooling
in `tools/`.

## Legal And Attribution Notes

This is an independent research project. It does not include a ROM and should
not be used to distribute copyrighted game data outside whatever legal framework
you are operating under.

Where local notes cite or borrow ideas from reference projects, keep the source
of that evidence visible. The goal is to make the work useful without hiding
uncertainty or provenance.
