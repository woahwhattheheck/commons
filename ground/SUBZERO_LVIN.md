# SUBZERO_LVIN — organ 19 fabricated 2026-08-23

Read-only receipt. Construction from PLUMB 2/3 (`muhl_lvin` / `MUHLLVIN`).
Standalone `.mno`. No titan write. Existing 19 titan circuits and organs 7/11/17 untouched.

Authority for the live twelve remains `titan_circuits.json` + `titan.gguf` (see
`SUBZERO_CENSUS.md`). This file is the public-tree measurement of organ 19 only.

## Verdict

| name | where | magic | n_gate | n_wires | n_in | n_out | depth | len |
|---|---|---|---:|---:|---:|---:|---:|---:|
| `muhl_lvin` | `excerpts/20260823/muhl_lvin.mno` @0 | `MUHLLVIN` | 2368 | 2511 | 64 | 64 | 30 | 62251 |

sha256 `1d12c627097b6bee501ba1c2b99c282dcc72fd646e3f77d3084ef1316fd83655`

Header is the live MHA layout: 8-char magic, then LE `n_gate, n_wires, n_in, n_out, depth`.
Records: `<BQQQ>` stride 25. One unique out per gate. Self-clock: each tape bit's next-state
out address **is** that tape bit's input address. Candidate counter and control bits
self-clock on their own wires. Host does not enumerate.

## Construction (the count)

ITERATED, not unrolled.

- tape/state latch plane: 64 bits × 32 = 2,048
- 64-bit candidate enumeration counter: 64 FA = 320
- TOTAL 2,368
- depth 30

CLK: tape out → tape in. One settle = one machine tick. 256 ticks per candidate
is a clock fact, not a host loop.

## Receipt commands

```
python3 muhl/desktop/MUHL_SUBZERO_ARCHETYPES/test_muhl_fab_lvin.py
python3 muhl/desktop/MUHL_SUBZERO_ARCHETYPES/muhl_fab_lvin.py --dry
```

`--dry` is structural only. It does not walk the organ. titan.gguf is not opened.
The git file is an excerpt: copies do not run. MOVE into titan is an owner-PC step.

Do not remint. Do not rebake the twelve, alife, chimeras, clacker, hpc_fabric, or organs 7/11/17.
