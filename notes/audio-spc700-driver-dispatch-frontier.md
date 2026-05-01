# Audio SPC700 Driver Dispatch Frontier

Status: byte-perfect source ingested; VCMD dispatch labels are now known, but
FF runtime effect still pending.

## Summary

- driver block: pack `1` block `2` at `0x0500`, `16779` bytes
- source-backed VCMD jump table: `0x0BE3`
- source-backed VCMD arg-length table: `0x0C21`
- refuted static table guess: `0x16C7`
- semantic status: `source_ingested_ff_runtime_effect_unconfirmed`

## Source-Backed Dispatch

- `VCMD_Jump_Table` is labeled at `0x0BE3` in
  `refs/earthbound-sounddriver-byte-perfect/main.asm`.
- The table names handlers for `0xE0..0xFE`:
  `VCMD_Instrument`, `VCMD_Pan`, `VCMD_PanFade`, `VCMD_Vibrato`,
  `VCMD_VibratoOff`, `VCMD_Volume`, `VCMD_VolumeFade`, `VCMD_Tempo`,
  `VCMD_TempoFade`, `VCMD_Transpose`, `VCMD_VoiceTranspose`,
  `VCMD_Tremolo`, `VCMD_TremoloOff`, `VCMD_VoiceVolume`,
  `VCMD_VoiceVolumeFade`, `VCMD_Subroutine`, `VCMD_VibratoFade`,
  `VCMD_PortamentoTo`, `VCMD_PortamentoFrom`, `VCMD_PortamentoOff`,
  `VCMD_Detune`, `VCMD_EchoVolume`, `VCMD_EchoOff`,
  `VCMD_EchoParameters`, `VCMD_EchoVolumeFade`, `VCMD_NoteSlide`,
  `VCMD_PercussionInstrument`, `VCMD_Nop`, `VCMD_MuteVoice`,
  `VCMD_FastForward`, and `VCMD_FastForwardOff`.
- `VCMD_Arg_Length` is labeled at `0x0C21` and gives source-backed operand
  lengths for the same `0xE0..0xFE` range.

## Refuted Table Guess

- The earlier `0x16C7` "likely high-command table" hypothesis is no longer
  valid.
- In source, `0x16C7` is an SFX pointer table headed by `SFX_01`, `SFX_02`,
  `SFX_03`, and later sound-effect entries.
- The previous `0x1A81` FF target candidate came from that refuted mapping and
  should not be treated as the active FF target anymore.

## FF Status

- `0xFF` is still unresolved.
- The newly ingested source gives named handlers only for `0xE0..0xFE`.
- That means `0xFF` should now be investigated as a separate terminal or
  reader-side path instead of being attached to the withdrawn `0x16C7` table
  guess.

## Findings

- The ingested source immediately upgrades the SPC700 command lane from
  anonymous static target guesses to named `VCMD_*` handlers.
- The previous `0x16C7` high-command dispatch hypothesis is refuted by source
  and should no longer be used as active evidence.
- The unresolved exact-duration question narrows: `0xFF` is now primarily a
  reader-path problem, not a guessed table-target problem.

## Next Work

- align project-local command names with the ingested `VCMD_*` labels
- trace how the reader handles `0xFF` relative to the `0xE0..0xFE` jump table
- feed the source-backed names into the sequence-control and exact-duration
  lanes
