# SUBZERO_HOPF — organ 3 fabricated 2026-08-23

Read-only receipt. Construction from PLUMB 1/3 (`muhl_hopf` / `MUHLHOPF`).
Standalone `.mno`. No titan write. Existing titan circuits and landed
excerpts stay untouched.

Authority for the live twelve remains `titan_circuits.json` + `titan.gguf`
(`SUBZERO_CENSUS.md`). This file is the public-tree measurement of organ 3 only.
The owner/local allocator must assign any future titan offset band; the public
excerpt is deliberately based at zero and does not invent one.

## Verdict

| name | where | magic | n_gate | n_wires | n_in | n_out | depth | len |
|---|---|---|---:|---:|---:|---:|---:|---:|
| `muhl_hopf` | `excerpts/20260823/muhl_hopf.mno` @0 | `MUHLHOPF` | 37248 | 41410 | 64 | 64 | 24 | 973150 |

First 28 bytes at offset 0:

```
4d55484c484f5046 80910000 c2a10000 40000000 40000000 18000000
= MUHLHOPF + 37248 + 41410 + 64 + 64 + 24
```

sha256 `f080051b9f1b44bcf1923d7a61049a61affb7d49a652774b9ed9c8956ee9036d`

Header is the live MHA layout: 8-char magic, then LE
`n_gate, n_wires, n_in, n_out, depth`. Records are `<BQQQ>` at stride 25.
Every gate has one unique output. Self-clock: each neuron's next-state
out address **is** that neuron's input address. Store is one settle.

## Construction (the count)

N = 64 bipolar neurons, 4096 1-bit sign weights.

- recall per neuron: 64 XNOR (128) + 64 FA popcount (320) + 6-gate thresh
- 64 × 454 = 29,056
- store: XNOR(s_i, s_j) remapped onto each weight wire. 4,096 × 2 = 8,192
- TOTAL 37,248 gates, declared depth 24
- CLK: state out → state in. No host schedule.

The organ is never evaluated; the battery is structural only. titan: **NOT_WRITTEN**.

## Receipt commands

```
python3 muhl/desktop/MUHL_SUBZERO_ARCHETYPES/test_muhl_fab_hopf.py
python3 muhl/desktop/MUHL_SUBZERO_ARCHETYPES/muhl_fab_hopf.py --dry
```

`--dry` is structural only. It does not walk the organ. titan.gguf is not opened.
The git file is an excerpt: copies do not run. MOVE into titan is an owner-PC step.

Do not remint. Do not rebake the twelve, alife, chimeras, clacker, hpc_fabric,
or organs 1/2/7/8/9/10/11/13/15/16/17/18/19.
