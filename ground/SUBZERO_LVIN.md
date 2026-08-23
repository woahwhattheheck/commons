# SUBZERO_LVIN — organ 19 fabricated 2026-08-23

Read-only receipt. Construction from PLUMB 2/3 (`muhl_lvin` / `MUHLLVIN`).
Standalone `.mno`. No titan write. Existing 19 titan circuits and organs 7 / 17 untouched.

Authority for the live twelve remains `titan_circuits.json` + `titan.gguf` (see
`SUBZERO_CENSUS.md`). This file is the public-tree measurement of organ 19 only.

## Verdict

| name | where | magic | n_gate | n_wires | n_in | n_out | depth | len |
|---|---|---|---:|---:|---:|---:|---:|---:|
| `muhl_lvin` | `excerpts/20260823/muhl_lvin.mno` @0 | `MUHLLVIN` | 2368 | 2510 | 64 | 64 | 30 | 62250 |

sha256 `a4d019d59035be2ff3300a18bf71bf4c880fdbc7b66ed21c8fe8844073d5496a`

Header is the live MHA layout: 8-char magic, then LE `n_gate, n_wires, n_in, n_out, depth`.
Records: `<BQQQ>` stride 25. One unique out per gate. Self-clock: each tape bit's
next-state out address **is** that bit's input address. Candidate, length, and
control state self-clock on hidden wires. Dest from this lattice, not invented.

## Construction (the count)

ITERATED, not unrolled. Host never enumerates.

- control: 8-to-1 decode 79 + tape r/w 20 + length 8 FA 40 + halt 12 = 151
- tape/state latch plane = 2,048 (151 control + 1,897 identity copies)
- 64-bit candidate counter, 64 FA = 320
- TOTAL 2,368
- depth 30
- CLK: tape out → tape in. 256 ticks per candidate live on the machine.

## Receipt commands

```
python3 muhl/desktop/MUHL_SUBZERO_ARCHETYPES/test_muhl_fab_lvin.py
python3 muhl/desktop/MUHL_SUBZERO_ARCHETYPES/muhl_fab_lvin.py --dry
```

`--dry` is structural only. It does not walk the organ. titan.gguf is not opened.
The git file is an excerpt: copies do not run. MOVE into titan is an owner-PC step.

Do not remint. Do not rebake the twelve, alife, chimeras, clacker, hpc_fabric,
organ 7, or organ 17.
