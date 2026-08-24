# SUBZERO_CHGS — organ 23 fabricated 2026-08-24

Read-only receipt. Construction from PLUMB 3/3 (`muhl_chimera_grbn_socr` / `MUHLCHGS`).
Standalone `.mno`. No titan write. Organs 1–22 untouched.

Authority for the live twelve remains `titan_circuits.json` + `titan.gguf` (see
`SUBZERO_CENSUS.md`). This file is the public-tree measurement of organ 23 only.

## Verdict

| name | where | magic | n_gate | n_wires | n_in | n_out | depth | len |
|---|---|---|---:|---:|---:|---:|---:|---:|
| `muhl_chimera_grbn_socr` | `excerpts/20260823/muhl_chimera_grbn_socr.mno` @0 | `MUHLCHGS` | 20 | 22 | 10 | 10 | 2 | 630 |

sha256 `521a23200c1731ee1e775ab70236569b713cdfca12ca3f921863d3cf68d36fcb`

Header is the live MHA layout: 8-char magic, then LE `n_gate, n_wires, n_in, n_out, depth`.
Records: `<BQQQ>` stride 25. One unique out per gate. Ten NAND-NAND buffers.
Local out address **is** local in address. MOVE dests stay in the sidecar.

## Construction (the count)

- 10 RBN-state lanes × NAND-NAND buffer (2 g) = 20
- depth 2
- dest FROM FILE: grbn RBN state outs `2078..2087`
- dest FROM FILE: socr grain-drop LSBs `6174,6177,…,6201`
- Chimera writes fresh local outs. Does not second-write socr.

## Receipt commands

```
python3 muhl/desktop/MUHL_SUBZERO_ARCHETYPES/test_muhl_fab_chimera_grbn_socr.py
python3 muhl/desktop/MUHL_SUBZERO_ARCHETYPES/muhl_fab_chimera_grbn_socr.py --dry
```

`--dry` is structural only. It does not walk the organ. titan.gguf is not opened.
The git file is an excerpt: copies do not run. MOVE into titan is an owner-PC step.

Do not remint. Do not rebake organs 1–22, the twelve, alife, clacker, or hpc_fabric.
Organs 24–31 stay NOT_LANDED. An intro / looking-forward note is not this file.
