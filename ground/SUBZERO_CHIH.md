# SUBZERO_CHIH — organ 20 fabricated 2026-08-24

Read-only receipt. Construction from PLUMB 3/3 (`muhl_chimera_immn_hdvs` / `MUHLCHIH`).
Standalone `.mno`. No titan write. Organs 1–19 untouched.

Authority for the live twelve remains `titan_circuits.json` + `titan.gguf` (see
`SUBZERO_CENSUS.md`). This file is the public-tree measurement of organ 20 only.

## Verdict

| name | where | magic | n_gate | n_wires | n_in | n_out | depth | len |
|---|---|---|---:|---:|---:|---:|---:|---:|
| `muhl_chimera_immn_hdvs` | `excerpts/20260823/muhl_chimera_immn_hdvs.mno` @0 | `MUHLCHIH` | 20 | 32 | 10 | 10 | 2 | 640 |

sha256 `8d3afc33c0483531919cac9d0cf46d89c573bc1e39c097850dda528c8dc160d7`

Header is the live MHA layout: 8-char magic, then LE `n_gate, n_wires, n_in, n_out, depth`.
Records: `<BQQQ>` stride 25. One unique out per gate. Ten NOT-NOT buffers.
Local out address **is** local in address. MOVE dests stay in the sidecar.

## Construction (the count)

- 10 detector bits × NOT-NOT buffer (2 g) = 20
- depth 2
- dest FROM FILE: immn detector-bank bits 0..9 at `70..79`
- dest FROM FILE: hdvs BUNDLE inject / vector inputs at `8222..8231`
- Chimera writes fresh local outs. Does not second-write hdvs.

## Receipt commands

```
python3 muhl/desktop/MUHL_SUBZERO_ARCHETYPES/test_muhl_fab_chimera_immn_hdvs.py
python3 muhl/desktop/MUHL_SUBZERO_ARCHETYPES/muhl_fab_chimera_immn_hdvs.py --dry
```

`--dry` is structural only. It does not walk the organ. titan.gguf is not opened.
The git file is an excerpt: copies do not run. MOVE into titan is an owner-PC step.

Do not remint. Do not rebake organs 1–19, the twelve, alife, chimeras already in titan,
clacker, or hpc_fabric.
