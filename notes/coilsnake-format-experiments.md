# CoilSnake Format Experiments

This note summarizes payload-free non-script format probes.
Generated projects, image assets, and rebuilt ROMs remain under ignored `build/coilsnake/`.

## Summary

- Experiments: `3`
- Missing expected reports: `0`
- Experiment root: `build/coilsnake/edit-experiments`

| Experiment | Family | Source | Comparison base | Changed bytes | Changed span | Evidence |
| --- | --- | --- | --- | ---: | --- | --- |
| `font0-width5-probe` | `ui-font` | `Fonts/0_widths.yml` | `build/coilsnake/baseline-rebuild.sfc` | `1` | `0x0F60DC` (`CF:60DC`)..`0x0F60DD` (`CF:60DD`) | `diff-confirmed` |
| `bg-data-distortion1-probe` | `battle-visual` | `bg_data_table.yml` | `build/coilsnake/baseline-rebuild.sfc` | `1` | `0x0ADCD0` (`CA:DCD0`)..`0x0ADCD1` (`CA:DCD1`) | `diff-confirmed` |
| `town-map-first-icon-x-probe` | `ui-town-map` | `TownMaps/icon_positions.yml` | `build/coilsnake/baseline-rebuild.sfc` | `1` | `0x2011A4` (`E0:11A4`)..`0x2011A5` (`E0:11A5`) | `diff-confirmed` |

## Interpretation

- These probes show whether CoilSnake format-facing fields lower to fixed rebuilt-ROM bytes or broader compiler rewrites.
- A one-byte diff proves edit locality in the CoilSnake baseline rebuild; runtime naming still needs local source or asset-contract correlation.
