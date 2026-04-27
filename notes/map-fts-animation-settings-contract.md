# Map FTS Animation/Settings Contract

This contract maps the variable 290-character section of each local EBDecomp
`.fts` tileset export. It keeps the payload opaque but records the stable
row/block shape needed for a later animation/settings decoder.

The working interpretation is tile-animation/settings metadata. This is based
on its position in the `.fts` export, its variable row count, and reference
labels for map tile animation graphics/properties near the map tileset data.

## Summary

- tilesets audited: `20`
- rows: `168`
- row count range per tileset: `1-52`
- blocks: `840`
- row shape: `variable rows per tileset; each row is 5 blocks of 58 base32-like characters`
- unique row IDs: `168`
- duplicate row IDs: `none`
- character set: `0123456789abcdefghijklmnopqrstuv`

## Row ID Distribution

- groups: `0`:4, `1`:3, `2`:4, `3`:2, `4`:2, `5`:4, `6`:7, `7`:1, `8`:2, `9`:6, `a`:8, `b`:8, `c`:8, `d`:4, `e`:8, `f`:8, `g`:4, `h`:8, `i`:1, `j`:7, `k`:8, `l`:5, `m`:5, `n`:4, `o`:5, `p`:8, `q`:6, `r`:5, `s`:6, `t`:6, `u`:3, `v`:8
- slots: `0`:32, `1`:30, `2`:27, `3`:25, `4`:19, `5`:15, `6`:11, `7`:9

## Per-Tileset Shape

| Tileset | Rows | Blocks | Row IDs |
| ---: | ---: | ---: | --- |
| 0 | 12 | 60 | `00, 01, 02, 03, v0, v1, v2, v3, v4, v5, v6, v7` |
| 1 | 3 | 15 | `10, 11, 12` |
| 2 | 4 | 20 | `20, 21, 22, 23` |
| 3 | 2 | 10 | `30, 31` |
| 4 | 2 | 10 | `40, 41` |
| 5 | 4 | 20 | `50, 51, 52, 53` |
| 6 | 7 | 35 | `60, 61, 62, 63, 64, 65, 66` |
| 7 | 1 | 5 | `70` |
| 8 | 2 | 10 | `80, 81` |
| 9 | 6 | 30 | `90, 91, 92, 93, 94, 95` |
| 10 | 52 | 260 | `a0, a1, a2, a3, a4, a5, a6, a7, b0, b1, b2, b3, b4, b5, b6, b7, c0, c1, c2, c3, c4, c5, c6, c7, e0, e1, e2, e3, e4, e5, e6, e7, f0, f1, f2, f3, f4, f5, f6, f7, g0, g1, g2, g3, h0, h1, h2, h3, h4, h5, h6, h7` |
| 11 | 14 | 70 | `l0, l1, l2, l3, l4, m0, m1, m2, m3, m4, n0, n1, n2, n3` |
| 12 | 8 | 40 | `k0, k1, k2, k3, k4, k5, k6, k7` |
| 13 | 20 | 100 | `r0, r1, r2, r3, r4, s0, s1, s2, s3, s4, s5, t0, t1, t2, t3, t4, t5, u0, u1, u2` |
| 14 | 8 | 40 | `p0, p1, p2, p3, p4, p5, p6, p7` |
| 15 | 5 | 25 | `o0, o1, o2, o3, o4` |
| 16 | 7 | 35 | `j0, j1, j2, j3, j4, j5, j6` |
| 17 | 4 | 20 | `d0, d1, d2, d3` |
| 18 | 1 | 5 | `i0` |
| 19 | 6 | 30 | `q0, q1, q2, q3, q4, q5` |

## Machine-Readable Data

`notes/map-fts-animation-settings-contract.json` records one row per
direct `.fts` export with row IDs, row/block SHA-1 hashes, character sets,
and fixed-shape counts. It intentionally omits raw row content.
