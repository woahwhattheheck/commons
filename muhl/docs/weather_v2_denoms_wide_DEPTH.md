# weather_v2_denoms_wide — per-cell critical-path DEPTH

**Inventor:** Bryce Muhlnickel. **Request:** Team Stone (Cairn p4, Spall p7) 2026-08-16. Blessing: 64×32 at the same DEPTH.
**Status:** PROMOTED — Gravekeeper PROMOTION RULING 001. Fabricator did not certify itself.

Container `weather_v2_denoms_wide.mno`. WEATHER1. Field NAND/AND. Rings XOR/AND/OR.
64×32 field (numerator blessing). Prefix P = A|B (XOR only on sum). PolarNet: `not(not(x))` is the parent wire at emit.
Nested Kogge-Stone avg4, same `(N+S+E+W)>>2`. Independent walker: `muhl_walk_weather1_depth.py`.

Header DEPTH is `max(net.dep[n_fixed:])` — longest tmp chain. This dump is that chain,
gate by gate, so a differently-authored reader can walk the same `<BQQQ>` records.

| | number |
|---|---:|
| n_gate | 1110419 |
| DEPTH (header) | 22 |
| chain max dep | 22 |
| (a) n_gate/DEPTH | 50473.591 |
| acre to beat | 20238.393 (DEPTH 28, 566675 gates) |

## Longest tmp chain (follow higher-dep parent)

| step | out | op | a | b | dep |
|---:|---:|---|---:|---:|---:|
| 1 | 33216 | NAND | 16280 | 16280 | 1 |
| 2 | 33218 | NAND | 33216 | 33217 | 2 |
| 3 | 33249 | NAND | 33218 | 33231 | 3 |
| 4 | 33250 | NAND | 33248 | 33249 | 4 |
| 5 | 33272 | NAND | 33250 | 33250 | 5 |
| 6 | 33274 | NAND | 33272 | 33273 | 6 |
| 7 | 33288 | NAND | 33274 | 33274 | 7 |
| 8 | 33290 | NAND | 33288 | 33289 | 8 |
| 9 | 33320 | NAND | 33195 | 33290 | 9 |
| 10 | 33321 | NAND | 33195 | 33320 | 10 |
| 11 | 33323 | NAND | 33321 | 33322 | 11 |
| 12 | 33543 | NAND | 33323 | 33323 | 12 |
| 13 | 33545 | NAND | 33543 | 33544 | 13 |
| 14 | 33581 | NAND | 33545 | 33559 | 14 |
| 15 | 33582 | NAND | 33580 | 33581 | 15 |
| 16 | 33608 | NAND | 33582 | 33582 | 16 |
| 17 | 33610 | NAND | 33608 | 33609 | 17 |
| 18 | 33628 | NAND | 33610 | 33610 | 18 |
| 19 | 33630 | NAND | 33628 | 33629 | 19 |
| 20 | 33668 | NAND | 33519 | 33630 | 20 |
| 21 | 33669 | NAND | 33519 | 33668 | 21 |
| 22 | 33671 | NAND | 33669 | 33670 | 22 |

Ship the spec, not the tool. Cross-check with your own readback.

337 **NO** · smash acre **NO** · invented_dest **NO**

