# SUBZERO_GRBN — organ 7 fabricated 2026-08-23

Read-only receipt. Construction from PLUMB 1/3 (`muhl_grbn` / `MUHLGRBN`).
Standalone `.mno`. No titan write. Existing 19 titan circuits untouched.

Authority for the live twelve remains `titan_circuits.json` + `titan.gguf` (see
`SUBZERO_CENSUS.md`). This file is the public-tree measurement of organ 7 only.

## Verdict

| name | where | magic | n_gate | n_wires | n_in | n_out | depth | len |
|---|---|---|---:|---:|---:|---:|---:|---:|
| `muhl_grbn` | `excerpts/20260823/muhl_grbn.mno` @0 | `MUHLGRBN` | 8704 | 8962 | 256 | 256 | 7 | 228638 |

First 28 bytes at offset 0:

```
4d55484c4752424e 00220000 02230000 00010000 00010000 07000000
= MUHLGRBN + 8704 + 8962 + 256 + 256 + 7
```

sha256 `09214540b3f3117ab93a4c509017a5e7b9c5f12d86545069af4ffcdae99c6632`

Header is the live MHA layout: 8-char magic, then LE `n_gate, n_wires, n_in, n_out, depth`.
PLUMB called the second word `len`; on `muhl_mha` that word is `n_wires` (2362). Same field here.

Records: `<BQQQ>` stride 25. One unique out per gate. Self-clock: each node's next-state
out address **is** that node's input address.

## Construction (the count)

N=256, K=3, truth table baked at fab.

- per node: 3 NOT + 16 decoder AND2 + 8 table AND + 7 OR = 34
- 256 × 34 = 8,704
- depth: NOT 1 → AND-tree 3 → table AND 4 → OR-tree 7

CLK: node state out → node state in. One update = one settle. Host does not schedule.

## Receipt commands

```
python3 muhl/desktop/MUHL_SUBZERO_ARCHETYPES/test_muhl_fab_grbn.py
python3 muhl/desktop/MUHL_SUBZERO_ARCHETYPES/muhl_fab_grbn.py --dry
```

`--dry` is structural only. It does not walk the organ. titan.gguf is not opened.
The git file is an excerpt: copies do not run. MOVE into titan is an owner-PC step.

Do not remint. Do not rebake the twelve, alife, chimeras, clacker, or hpc_fabric.
