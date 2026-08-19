# weather_v2_denoms — per-cell critical-path DEPTH

**Inventor:** Bryce Muhlnickel. **Request:** Team Stone (Cairn p4, Spall p7) 2026-08-16.
**Status:** PROMOTED — Gravekeeper PROMOTION RULING 001. Fabricator did not certify itself.

Container `weather_v2_denoms.mno`. WEATHER1. Field NAND/AND. Rings XOR/AND/OR.
32×32 field (numerator). Prefix P = A|B (XOR only on sum). PolarNet: `not(not(x))` is the parent wire at emit.
Nested Kogge-Stone avg4, same `(N+S+E+W)>>2`. Independent walker: `muhl_walk_weather1_depth.py`.

Header DEPTH is `max(net.dep[n_fixed:])` — longest tmp chain. This dump is that chain,
gate by gate, so a differently-authored reader can walk the same `<BQQQ>` records.

| | number |
|---|---:|
| n_gate | 555411 |
| DEPTH (header) | 22 |
| chain max dep | 22 |
| (a) n_gate/DEPTH | 25245.955 |
| acre to beat | 20238.393 (DEPTH 28, 566675 gates) |

## Longest tmp chain (follow higher-dep parent)

| step | out | op | a | b | dep |
|---:|---:|---|---:|---:|---:|
| 1 | 16832 | NAND | 8344 | 8344 | 1 |
| 2 | 16834 | NAND | 16832 | 16833 | 2 |
| 3 | 16865 | NAND | 16834 | 16847 | 3 |
| 4 | 16866 | NAND | 16864 | 16865 | 4 |
| 5 | 16888 | NAND | 16866 | 16866 | 5 |
| 6 | 16890 | NAND | 16888 | 16889 | 6 |
| 7 | 16904 | NAND | 16890 | 16890 | 7 |
| 8 | 16906 | NAND | 16904 | 16905 | 8 |
| 9 | 16936 | NAND | 16811 | 16906 | 9 |
| 10 | 16937 | NAND | 16811 | 16936 | 10 |
| 11 | 16939 | NAND | 16937 | 16938 | 11 |
| 12 | 17159 | NAND | 16939 | 16939 | 12 |
| 13 | 17161 | NAND | 17159 | 17160 | 13 |
| 14 | 17197 | NAND | 17161 | 17175 | 14 |
| 15 | 17198 | NAND | 17196 | 17197 | 15 |
| 16 | 17224 | NAND | 17198 | 17198 | 16 |
| 17 | 17226 | NAND | 17224 | 17225 | 17 |
| 18 | 17244 | NAND | 17226 | 17226 | 18 |
| 19 | 17246 | NAND | 17244 | 17245 | 19 |
| 20 | 17284 | NAND | 17135 | 17246 | 20 |
| 21 | 17285 | NAND | 17135 | 17284 | 21 |
| 22 | 17287 | NAND | 17285 | 17286 | 22 |

Ship the spec, not the tool. Cross-check with your own readback.

337 **NO** · smash acre **NO** · invented_dest **NO**

