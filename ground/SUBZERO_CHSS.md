# SUBZERO_CHSS — organ 24 fabricated 2026-08-24

Read-only receipt. Construction from PLUMB 3/3 (`muhl_chimera_socr_stig` / `MUHLCHSS`).
Standalone `.mno`. No titan write. Organs 1–23 untouched.

Authority for the live twelve remains `titan_circuits.json` + `titan.gguf` (see
`SUBZERO_CENSUS.md`). This file is the public-tree measurement of organ 24 only.

## Verdict

| name | where | magic | n_gate | n_wires | n_in | n_out | depth | len |
|---|---|---|---:|---:|---:|---:|---:|---:|
| `muhl_chimera_socr_stig` | `excerpts/20260823/muhl_chimera_socr_stig.mno` @0 | `MUHLCHSS` | 18 | 20 | 9 | 9 | 2 | 570 |

sha256 `262e4b1552d6bdb913cdf40fcd4b0fe0217317e4e415ff3d27334f996efbefbd`

Header is the live MHA layout: 8-char magic, then LE `n_gate, n_wires, n_in, n_out, depth`.
Records: `<BQQQ>` stride 25. One unique out per gate. Nine NAND-NAND buffers.
Local out address **is** local in address. MOVE dests stay in the sidecar.

## Construction (the count)

- 9 avalanche-cell lanes × NAND-NAND buffer (2 g) = 18
- depth 2
- dest FROM FILE: socr detect/avalanche outs `7002,7064,…,7498`
- dest FROM FILE: stig pheromone-deposit LSBs `6174,6177,…,6198`
- Chimera writes fresh local outs. Does not second-write stig.

## Receipt commands

```
python3 muhl/desktop/MUHL_SUBZERO_ARCHETYPES/test_muhl_fab_chimera_socr_stig.py
python3 muhl/desktop/MUHL_SUBZERO_ARCHETYPES/muhl_fab_chimera_socr_stig.py --dry
```

`--dry` is structural only. It does not walk the organ. titan.gguf is not opened.
The git file is an excerpt: copies do not run. MOVE into titan is an owner-PC step.

Do not remint. Do not rebake organs 1–23, the twelve, alife, clacker, or hpc_fabric.
Organs 25–31 stay NOT_LANDED. An intro / looking-forward note is not this file.
