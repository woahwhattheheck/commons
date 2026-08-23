# SUBZERO_ISPN — organ 11 fabricated 2026-08-23

Read-only receipt. Construction from PLUMB 2/3 (`muhl_ispn` / `MUHLISPN`).
Standalone `.mno`. No titan write. Existing 19 titan circuits and organ 7 untouched.

Authority for the live twelve remains `titan_circuits.json` + `titan.gguf` (see
`SUBZERO_CENSUS.md`). This file is the public-tree measurement of organ 11 only.

## Verdict

| name | where | magic | n_gate | n_wires | n_in | n_out | depth | len |
|---|---|---|---:|---:|---:|---:|---:|---:|
| `muhl_ispn` | `excerpts/20260823/muhl_ispn.mno` @0 | `MUHLISPN` | 8784 | 9058 | 256 | 256 | 12 | 230734 |

First 28 bytes at offset 0:

```
4d55484c4953504e 50220000 62230000 00010000 00010000 0c000000
= MUHLISPN + 8784 + 9058 + 256 + 256 + 12
```

sha256 `13272c3036e9409c07025f9826523817527ebb13be4c8fc8b8b3044c96a8959a`

Header is the live MHA layout: 8-char magic, then LE `n_gate, n_wires, n_in, n_out, depth`.
Records: `<BQQQ>` stride 25. One unique out per gate. Self-clock: each spin's next-state
out address **is** that spin's input address. The 16-bit anneal counter self-clocks on
its own wires; temperature descends in gates. Host does not schedule.

## Construction (the count)

N=256 spins, 4-neighbour torus, 16-bit anneal counter.

- per spin: 4 XNOR (8) + popcount4 as 4 FA (20) + temp threshold (6) = 34
- 256 × 34 = 8,704
- 16-bit incrementer, 16 FA = 80
- TOTAL 8,784
- depth 12 (spin path)

CLK: spin out → spin in. One update = one settle.

## Receipt commands

```
python3 muhl/desktop/MUHL_SUBZERO_ARCHETYPES/test_muhl_fab_ispn.py
python3 muhl/desktop/MUHL_SUBZERO_ARCHETYPES/muhl_fab_ispn.py --dry
```

`--dry` is structural only. It does not walk the organ. titan.gguf is not opened.
The git file is an excerpt: copies do not run. MOVE into titan is an owner-PC step.

Do not remint. Do not rebake the twelve, alife, chimeras, clacker, hpc_fabric, or organ 7.
