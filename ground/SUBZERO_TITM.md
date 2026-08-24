# SUBZERO_TITM — organ 30 fabricated 2026-08-24

Read-only receipt. Construction from PLUMB 3/3 (`muhl_titanx_mirror` / `MUHLTITM`).
Standalone `.mno`. No titan write. Organs 1–29 untouched.

## Verdict

| name | where | magic | n_gate | n_wires | n_in | n_out | depth | len |
|---|---|---|---:|---:|---:|---:|---:|---:|
| `muhl_titanx_mirror` | `excerpts/20260823/muhl_titanx_mirror.mno` @0 | `MUHLTITM` | 240 | 242 | 120 | 120 | 2 | 7230 |

sha256 `29c513c77efad8155541e8b80c70c51ba5cc61ea5168d41df6c182a133113ed3`

## Construction (the count)

- 120 dest-FROM-FILE lanes × NAND-NAND buffer (2 g) = 240
- depth 2
- hops: pred→surprise 32 · hpc_fabric→surprise 28 · immn→surprise 1 · hdvs→surprise 32 · sdmk→surprise 16 · rookery witness→surprise 11
- dest FROM FILE: pred outs `3102..3133`
- dest FROM FILE: hpc_fabric ins `103788450894..103788450921` (HPC input[0] − HPC offset applied to fabric offset)
- dest FROM FILE: immn alarm `29636`
- dest FROM FILE: hdvs outs first 32 (`10274,10279,…`)
- dest FROM FILE: sdmk outs first 16 (`1188,1963,…`)
- dest FROM FILE: rookery witness clocks `256..266`
- input plane = the other organs' out planes. Emits surprise only.
- surprise is a local self-clocked bit plane. Renders under `muhl_png.py` bits.
- HPC fabric and rookery EXIST (census / minds). This excerpt does not write them.

Talk is not this file. A demand-gap list is not this file. Organs 1–29 already on main; do not remint.

```
python3 muhl/desktop/MUHL_SUBZERO_ARCHETYPES/test_muhl_fab_titanx_mirror.py
python3 muhl/desktop/MUHL_SUBZERO_ARCHETYPES/muhl_fab_titanx_mirror.py --dry
```

titan: **NOT_WRITTEN**. Organ 31 stays NOT_LANDED.
