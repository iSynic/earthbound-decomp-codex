# Audio SPC700 Sound Driver Source Ingest

Status: byte-perfect SPC700-side source is now checked into `refs/` and linked
to the existing audio frontier notes.

## Provenance

- source archive: `C:/Users/Eric/Downloads/sounddriver.zip`
- archive SHA-256:
  `1BB195F9C2C4BB5B9440B28C5110209F48826B6AE07955848964F02BC50742F2`
- extracted root: `refs/earthbound-sounddriver-byte-perfect`
- manifest:
  `manifests/audio-spc700-sounddriver-source-ingest.json`

## Extracted Files

| File | Size | SHA-256 | Role |
| --- | ---: | --- | --- |
| `main.asm` | `150086` | `5C8C6C30E80F35B355DFFE86AEB920DF8A645A2806C4509CB2908FB20F63AEEE` | main SPC700 driver disassembly |
| `ram.asm` | `2992` | `21F396FA687509752BEBE8B27AF5078CDADCE20088AB818B3AD2A920CC68849F` | RAM layout and register aliases |
| `macros.asm` | `1836` | `BBF6E597ADE44B785941483CE7B23C03B96DA8C1B7170A7B5A7F01914F75BA5E` | assembler macros/constants |
| `sfx_sequences.asm` | `77332` | `188B5CF01DE8FA664D7706DF9860B789213F8CD018144D158E03B3EB36547F70` | sound-effect sequence data |

## Immediate Source-Backed Facts

- `main.asm` declares `base $0500` and states that assembling the file with
  asar yields a byte-accurate `engine.bin`.
- `0x0955` is labeled `GetNextByte` and `0x0957` is labeled `SkipByte`.
- `VCMD_Jump_Table` starts at `0x0BE3` and names handlers for `0xE0..0xFE`.
- `VCMD_Arg_Length` starts at `0x0C21` and gives per-command operand lengths
  for that same `0xE0..0xFE` range.
- `0x16C7` is not the music high-command dispatch table. In source it is a
  sound-effect pointer table rooted at `SFX_01`, `SFX_02`, and later entries.

## Repo Impact

- `notes/audio-spc700-control-reader-frontier.md` can now name the strongest
  reader PCs instead of treating them as anonymous windows.
- `notes/audio-spc700-driver-dispatch-frontier.md` should stop treating
  `0x16C7` as the likely `0xE0..0xFF` dispatch table.
- The next naming pass can lift `VCMD_*` labels directly from source before we
  decide whether to keep, rename, or split them into project-local semantics.

## Next Work

- rebuild the SPC700 command/dispatch naming from `VCMD_Jump_Table`
- trace how `0xFF` is handled relative to the named `0xE0..0xFE` VCMD table
- align the sequence/control-flow frontier notes with source-backed labels and
  RAM names from `ram.asm`
