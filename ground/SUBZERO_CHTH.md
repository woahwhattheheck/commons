# SUBZERO_CHTH — organ 22 fabricated 2026-08-24

Read-only receipt. Construction from PLUMB 3/3 (`muhl_chimera_tset_hdvs` / `MUHLCHTH`).
Standalone `.mno`. No titan write. Organs 1–21 untouched.

Authority for the live twelve remains `titan_circuits.json` + `titan.gguf` (see
`SUBZERO_CENSUS.md`). This file is the public-tree measurement of organ 22 only.

## Verdict

| name | where | magic | n_gate | n_wires | n_in | n_out | depth | len |
|---|---|---|---:|---:|---:|---:|---:|---:|
| `muhl_chimera_tset_hdvs` | `excerpts/20260823/muhl_chimera_tset_hdvs.mno` @0 | `MUHLCHTH` | 24 | 26 | 12 | 12 | 2 | 750 |

sha256 `f972b8c960fb0e338b003b35bf6052775fc527e5879b048a9a050ce643c6e0d7`

Header is the live MHA
layout: 8-char magic, then LE `n_gate, n_wires, n_in, n_out, depth`.
Records: `<BQQQ>` stride 25. One unique out per gate. Twelve NAND-NAND buffers.
Local out address **is** local in address. MOVE dests stay in the sidecar.

## Construction (the count)

- 12 clause lanes × NAND-NAND buffer (2 g) = 24
- depth 2
- dest FROM FILE: tset clause AND-outs `4260,4355,…,5305`
- dest FROM FILE: hdvs BIND XOR-outs `9246..9257`
- Chimera writes fresh local outs. Does not second-write hdvs.

A review essay about the table is not this file. Talk is not a land.

## Receipt commands

```
python3 muhl/desktop/MUHL_SUBZERO_ARCHETYPES/test_muhl_fab_chimera_tset_hdvs.py
python3 muhl/desktop/MUHL_SUBZERO_ARCHETYPES/muhl_fab_chimera_tset_hdvs.py --dry
```

`--dry` is structural only. It does not walk the organ. titan.gguf is not opened.
The git file is an excerpt: copies do not run. MOVE into titan is an owner-PC step.

Do not remint. Do not rebake organs 1–21, the twelve, alife, clacker, or hpc_fabric.
Organs 23–31 stay NOT_LANDED.
