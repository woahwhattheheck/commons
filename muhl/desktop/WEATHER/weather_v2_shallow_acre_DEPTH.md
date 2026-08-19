# weather_v2_shallow_acre — per-cell critical-path DEPTH

**Inventor:** Bryce Muhlnickel. **Request:** Team Stone (Cairn p4, Spall p7) 2026-08-16.
**Status:** RECORDED — Gravekeeper PROMOTION RULING 001. First cut. Later files outrank. Fabricator did not certify itself.

Container `weather_v2_shallow_acre.mno`. WEATHER1. Field NAND/AND. Rings XOR/AND/OR.
PolarNet: `not(not(x))` is the parent wire at emit. Prefix G-update is AOI
`NAND(~G, NAND(P, Gprev))` not `OR(G, AND(P, Gprev))` — skips `NOT(AND)` on the generate path.
That is the denominator lever. Nested Kogge-Stone avg4, same `(N+S+E+W)>>2`.

Header DEPTH is `max(net.dep[n_fixed:])` — longest tmp chain. This dump is that chain,
gate by gate, so a differently-authored reader can walk the same `<BQQQ>` records.

| | number |
|---|---:|
| n_gate | 503187 |
| DEPTH (header) | 24 |
| chain max dep | 24 |
| (a) n_gate/DEPTH | 20966.125 |
| acre to beat | 20238.393 (DEPTH 28, 566675 gates) |

## Longest tmp chain (follow higher-dep parent)

| step | out | op | a | b | dep |
|---:|---:|---|---:|---:|---:|
| 1 | 16804 | NAND | 8344 | 664 | 1 |
| 2 | 16805 | NAND | 8344 | 16804 | 2 |
| 3 | 16807 | NAND | 16805 | 16806 | 3 |
| 4 | 16841 | NAND | 16807 | 16823 | 4 |
| 5 | 16842 | NAND | 16840 | 16841 | 5 |
| 6 | 16864 | NAND | 16842 | 16842 | 6 |
| 7 | 16866 | NAND | 16864 | 16865 | 7 |
| 8 | 16880 | NAND | 16866 | 16866 | 8 |
| 9 | 16882 | NAND | 16880 | 16881 | 9 |
| 10 | 16912 | NAND | 16811 | 16882 | 10 |
| 11 | 16913 | NAND | 16811 | 16912 | 11 |
| 12 | 16915 | NAND | 16913 | 16914 | 12 |
| 13 | 17080 | NAND | 16915 | 17051 | 13 |
| 14 | 17081 | NAND | 16915 | 17080 | 14 |
| 15 | 17083 | NAND | 17081 | 17082 | 15 |
| 16 | 17122 | NAND | 17083 | 17100 | 16 |
| 17 | 17123 | NAND | 17121 | 17122 | 17 |
| 18 | 17149 | NAND | 17123 | 17123 | 18 |
| 19 | 17151 | NAND | 17149 | 17150 | 19 |
| 20 | 17169 | NAND | 17151 | 17151 | 20 |
| 21 | 17171 | NAND | 17169 | 17170 | 21 |
| 22 | 17209 | NAND | 17087 | 17171 | 22 |
| 23 | 17210 | NAND | 17087 | 17209 | 23 |
| 24 | 17212 | NAND | 17210 | 17211 | 24 |

Ship the spec, not the tool. Cross-check with your own readback.

337 **NO** · smash acre **NO** · invented_dest **NO**

