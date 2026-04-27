# Map Palette Descriptor Context

This audit compares live-scene descriptor palette bits against the bank DA
map palette payload shape. Each map palette variant is `192` bytes, or
`96` SNES BGR555 colors: six 16-color subpalettes.

The arrangement descriptor still exposes a three-bit palette field. This
report keeps the field named literally and measures candidate offsets
instead of picking an unproven interpretation.

## Summary

- direct scenes sampled: `950`
- cells per scene: `1024`
- pixels per cell: `64`
- map palette variant colors: `96`
- available 16-color subpalettes per variant: `6`

## Descriptor Palette Counts

| Descriptor Palette | Cell Count | Pixel Count |
| ---: | ---: | ---: |
| 0 | 185419 | 11866816 |
| 1 | 106209 | 6797376 |
| 2 | 121553 | 7779392 |
| 3 | 108496 | 6943744 |
| 4 | 109510 | 7008640 |
| 5 | 75226 | 4814464 |
| 6 | 188674 | 12075136 |
| 7 | 77713 | 4973632 |

## Candidate Offset Fit

| Offset | Overflow Cells | Overflow Pixels | Overflow % |
| ---: | ---: | ---: | ---: |
| -2 | 291628 | 18664192 | 29.978% |
| -1 | 263132 | 16840448 | 27.049% |
| 0 | 266387 | 17048768 | 27.384% |

## Top Raw-Descriptor Overflow Scenes

| Scene | Sector | Tileset | Palette | Overflow Cells |
| --- | --- | ---: | ---: | ---: |
| `map_scene.0277` | `8,21` | 6 | 0 | 1008 |
| `map_scene.0121` | `3,25` | 6 | 1 | 937 |
| `map_scene.0249` | `7,25` | 6 | 1 | 918 |
| `map_scene.0278` | `8,22` | 6 | 0 | 905 |
| `map_scene.0217` | `6,25` | 6 | 1 | 901 |
| `map_scene.0153` | `4,25` | 6 | 1 | 889 |
| `map_scene.1103` | `34,15` | 4 | 0 | 886 |
| `map_scene.0594` | `18,18` | 6 | 0 | 875 |
| `map_scene.0924` | `28,28` | 4 | 1 | 874 |
| `map_scene.1135` | `35,15` | 4 | 0 | 855 |
| `map_scene.0506` | `15,26` | 6 | 1 | 854 |
| `map_scene.0310` | `9,22` | 6 | 0 | 851 |
| `map_scene.1002` | `31,10` | 4 | 0 | 844 |
| `map_scene.0927` | `28,31` | 4 | 1 | 832 |
| `map_scene.0247` | `7,23` | 6 | 0 | 819 |
| `map_scene.0185` | `5,25` | 6 | 1 | 810 |

## Machine-Readable Data

`notes/map-palette-descriptor-context.json` records global, per-tileset,
and per-tileset/palette descriptor counts plus offset fit statistics.
