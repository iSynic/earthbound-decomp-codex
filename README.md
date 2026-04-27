# EarthBound Decomp Scaffold

This workspace is set up for a matching EarthBound reverse-engineering project built around the US headerless ROM.

## Current layout

Tracked in this repository:

- `notes/` research notes, memory maps, source-scaffold reports, and format docs
- `src/` byte-equivalent source-bank scaffold modules
- `tools/` Python helper scripts

Local-only/generated:

- `EarthBound (USA).sfc` or `baserom/EarthBound (USA).sfc` local ROM input, never committed
- `build/` generated manifests, byte-equivalence outputs, labels, and scratch products
- `asm/` scratch hand-written or cleaned-up assembly
- `dumps/` extracted data and exploratory dumps
- `refs/` local reference checkouts; keep them quarantined and cite only what is corroborated in `notes/`

## ROM expectations

The verification script is currently pinned to the headerless US EarthBound ROM with:

- Size: `3145728` bytes
- SHA-1: `D67A8EF36EF616BC39306AA1B486E1BD3047815A`
- Map mode: `0x31` (`HiROM/FastROM`)

The scripts will look for the ROM in either of these places:

- `./EarthBound (USA).sfc`
- `./baserom/EarthBound (USA).sfc`

## Quick start

```powershell
python tools/verify_rom.py
python tools/split_rom.py
python tools/dump_header.py --json-out build/header.json --markdown-out notes/header-and-vectors.md
python tools/disasm_bank_c0.py --output notes/bank-c0-first-pass.md
python tools/extract_ebtext.py C2:0998 --length 4 --count 2 --stride 4
python tools/find_ebtext_command.py 1C 05 --limit 12
python tools/inspect_ebtext_hits.py 1D 24 --limit 2 --before 24 --after 56
python tools/summarize_ebtext_family.py 1C --max-subcommands 22 --limit 2
python tools/crosscheck_ebtext_family.py 1A C1:7B56 --max-subcommands 32 --limit 1
python tools/census_ebtext_commands.py C1:890E --max-opcodes 32 --limit 1
python tools/find_xrefs.py C20ABC --limit 12
python tools/inspect_table.py D5:5000 --stride 39 --index 4 --count 3 --field type:b:25 --field params:d:31
python tools/inspect_item.py 0x11 --count 2
python tools/inspect_battle_action.py 78
python tools/inspect_slot.py 1 2
python tools/lookup_wram_field.py 99DC 9FAC+1D
python tools/lookup_data_contract.py D5:9589+0x46 "BATTLERS_TABLE[3].afflictions" '$ADD4+0x61'
python tools/validate_data_contracts.py
python tools/build_ref_index.py --output build/ref-index.json
python tools/lookup_ref_context.py C3:0188 DISPLAY_ANTI_PIRACY_SCREEN
python tools/build_ref_bank_report.py C3 --output notes/bank-c3-reference-frontier.md --limit 160
python tools/decode_event_script.py C3:0295 C3:AB59
python tools/inspect_snes_palette.py C4:3492 --count 8
python tools/decode_snippet.py C1:244C --count 20 --show-state --force-m8
python tools/trace_dp_window.py C2:7550 --count 16 --show-state --force-m16 --force-x16 --d 0x99CE
python tools/summarize_dispatch.py C1:890E --max-cases 32
python tools/lookup_ref_symbol.py C4:B524 --limit 8
python tools/summarize_transfer_to_vram_callers.py C0:8616 --bank C0 --limit 20
python tools/audit_bank_progress.py --output notes/bank-0-1-progress-audit.md
python tools/build_working_name_manifest.py --banks C0 C1 C2 --output build/working-names-c0-c2.json
python tools/build_working_name_manifest.py --banks C0 C1 C2 C3 --output build/working-names-c0-c3.json
python tools/emit_source_labels.py --manifest build/working-names-c0-c2.json --output-dir build/labels --banks C0 C1 C2
python tools/build_data_contract_manifest.py --json-out build/data-contracts-c0-c2.json --markdown-out notes/data-contracts-c0-c2.md
python tools/inspect_table.py --contract ENEMY_CONFIGURATION_TABLE --index 0 --count 1 --field actions:w:0x46
```

The splitter writes per-bank files and a JSON manifest under `build/split/`.
The header dumper writes machine-readable metadata to `build/header.json` and a human-readable summary to `notes/header-and-vectors.md`.
The bank `C0` disassembler writes a first-pass recursive listing to `notes/bank-c0-first-pass.md`.
The text extractor decodes EarthBound US text bytes from CPU addresses, which is useful for checking battle text fragments, control bytes, and nearby phrase tables without doing the byte mapping by hand.
The command-aware text searcher finds exact parsed EarthBound text commands by opcode and subopcode across the exposed `text_data` segments, which is useful for separating real script uses from raw-byte false positives.
The hit inspector builds on that by showing exact parsed command hits together with a nearby decoded script window, which is useful for understanding rare or poorly named bank `01` leaves without manually hopping between the finder and the script disassembler.
The text-family summarizer scans one top-level text opcode across all exposed `text_data` segments and reports exact parsed subcommand hit counts, which is useful for mapping big bank `01` command families without running a dozen one-off searches.
The text-command census helper combines live dispatcher cases, exact parsed hit counts, and note-file coverage into one report, which is useful for consolidation passes when a bank `01` command range is mostly mapped and we want to see what is runtime-backed, parser-only, or still missing notes.
The xref scanner finds direct code calls, likely memory accesses, and raw pointer hits across the whole ROM, which is useful for following shared managers and WRAM-backed subsystems without hand-searching each bank.
The table inspector dumps fixed-stride ROM records by CPU address and named fields, which is useful for checking item/enemy/script tables without hand-computing every offset.
The item inspector is a specialized helper for `D5:5000` item records, which is useful for quickly decoding the packed item class byte, use/equip flags, repair bytes, and other repeatedly referenced item fields without rebuilding the field map each time.
The battle-action inspector is a specialized helper for the `D5:7B68` battle action table, which is useful for checking an action entry's direction/target/type/cost, message pointer, second-pointer code target, nearby text preview, and matching note coverage without manually decoding the table row each time.
The slot inspector is a specialized helper for the recurring `0x5F`-stride live slot family rooted at `$99CE`, which is useful for checking the addresses and optional live values of repeatedly referenced battler or party fields like `$99DC`, `$99E3..$99E9`, `$99FF..$9A02`, `$9A13..$9A24`, and `$9A25..$9A2C` without recomputing offsets by hand each time.
The WRAM field lookup helper maps high-value addresses like `$99DC` or `$9FAC+$1D` onto curated `ebsrc-main` roots and struct fields, which is useful for quickly checking whether a live address belongs to `game_state`, `char_struct`, or `battler` before we start naming it locally.
The data-contract lookup helper does the same job across the generated manifest, including ROM tables and declared overlays. It accepts literal addresses like `D5:9589+0x46`, record fields like `BATTLERS_TABLE[3].afflictions`, and battle-background state offsets like `$ADD4+0x61`.
The data-contract validator checks duplicate ids, field spans, and fixed-count WRAM root overlaps, with the known `GAME_STATE`/`PARTY_CHARACTERS` overlap handled explicitly.
The reference-index builder consolidates the quarantined refs, focused local notes, working names, and data contracts into `build/ref-index.json`; generated frontier/proposal/audit reports are skipped so they do not count as proof of coverage. The reference-context lookup helper is the new first stop for C3+ work: query an address like `C3:0188` or a semantic ref name like `DISPLAY_ANTI_PIRACY_SCREEN` before decoding locally. The bank report helper turns that index into a per-bank frontier map, and the event-script decoder reads C3-style action/event bytecode directly from the verified ROM so we do not accidentally treat script bytes as 65816 code.
The SNES palette inspector decodes packed 15-bit color words from either ROM CPU addresses or raw binary files, and can optionally diff two blocks or emit a simple swatch preview image. This is useful for palette-animation and color-work families like the current landing-display export path.
The snippet decoder prints a short annotated 65816 instruction stream from any CPU address, which is useful for reading branch-heavy bank snippets without doing manual byte slicing first.
The snippet decoder also supports locked-width flags like --force-m8, --force-m16, --force-x8, and --force-x16, which is useful when we start decoding from the middle of a function and want to hold one register width steady instead of trusting every nearby REP/SEP transition.
The direct-page trace helper builds on that and also tracks the `D` register, a small direct-page word cache, the main `A/X/Y` carry-through patterns, and optional `DB`-assisted `(dp),Y` pointer resolution. That is useful for mid-function `TCD`/slot-base code where ordinary xref scans miss writes like `STA $0E` until we know what direct page is live. When needed, seed it with `--d` and `--db` to tell it the incoming direct-page and data-bank values.
The dispatch summarizer extracts simple branch ladders, including zero-case `TXA` prefixes, range guards, and mixed `BEQ` versus `BNE/JMP` cases, which is useful for mapping the bank `01` text-command families without re-decoding every compare chain by hand.
The reference-symbol lookup helper scans the quarantined reference trees for address-shaped mentions like `C4:B524` or `UNKNOWN_C4B524`, which is useful for checking whether an address already has a named or semi-named home in the side references without doing manual tree-wide searches.

The TRANSFER_TO_VRAM caller summarizer clusters direct JSL callers by nearby ADC and LDA immediates plus setup stores, which is useful for quickly separating 0x4000+ companion uploads from 0x5800+ strip-family uploads without hand-walking every caller first.
The bank progress auditor cross-checks local `notes/*.md` address coverage against the quarantined `ebsrc-main` US bank `00/01` include maps and symbol lists, then writes a rerunnable gap report to `notes/bank-0-1-progress-audit.md`.
The working-name manifest builder consolidates explicit `Working Names` note bullets into a machine-readable symbol manifest. The source-label emitter consumes that manifest and writes generated Asar, ca65, debugger `.sym`, and TSV review artifacts under `build/labels/`.
The data-contract manifest builder consolidates the strongest C0-C2 WRAM roots, WRAM overlays, and ROM fixed-stride tables into `build/data-contracts-c0-c2.json`, with a readable companion note at `notes/data-contracts-c0-c2.md`. Use it before naming field-heavy code paths so `char_struct`, `battler`, selection snapshots, `enemy_data`, item records, battle actions, PSI ability rows, and loaded battle-background state all use the same offsets. The generic table inspector can consume these contracts with `--contract`, while the item, battle-action, and slot inspectors now read their base/stride dimensions from the manifest.
The reference-first workflow is documented in `notes/reference-first-workflow.md`. Treat refs as accelerators: `ref-suggested` until local bytes/callers/data shape confirm them, then promote to `local-confirmed` or `corroborated`.

## Suggested next steps

1. Use `tools/audit_bank_progress.py` to pick the next unmentioned `unknown/...` bank `00/01` chunk.
2. Decode the chunk locally, then corroborate with `refs/ebsrc-main`, `refs/earthbound-disasm-legacy`, and `refs/eb-decompile-4ef92` where applicable.
3. Write a focused note with byte-level evidence, callers, borrowed reference names, and remaining uncertainty.
4. Add an assembler toolchain once we choose one (`wla-65816` or `ca65`).




## High-value side refs

These are still quarantined side references, but they are high-leverage enough to check early when a subsystem starts touching shared RAM or battle state:

- `refs/ebsrc-main/ebsrc-main/include/structs.asm` for `char_struct`, `battler`, `game_state`, and related layouts
- `refs/ebsrc-main/ebsrc-main/include/constants/battle.asm` for battle status-group and PSI/action enums
- `refs/ebsrc-main/ebsrc-main/src/bankconfig/common/ram.asm` for named WRAM root labels like `GAME_STATE`, `PARTY_CHARACTERS`, and `BATTLERS_TABLE`
- `refs/ebsrc-main/ebsrc-main/src/battle/` when a local battle helper already has a plausible family and we want a fast cross-check on caller shape or enum usage
- `build/ref-index.json` plus `tools/lookup_ref_context.py` as the normal front door for all reference lookups





