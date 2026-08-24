# SUBZERO_TITX — organ 31 fabricated 2026-08-24

Read-only receipt. Construction from PLUMB 3/3 (`muhl_titanx_commons` / `MUHLTITX`).
Standalone `.mno`. No titan write. Organs 1–30 untouched.

## Verdict

| name | where | magic | n_gate | n_wires | n_in | n_out | depth | len |
|---|---|---|---:|---:|---:|---:|---:|---:|
| `muhl_titanx_commons` | `excerpts/20260823/muhl_titanx_commons.mno` @0 | `MUHLTITX` | 600 | 602 | 300 | 300 | 2 | 18030 |

sha256 `20e48ea737c37cca5c4bb4afe782eb9f945f429cdd5ad5949c0b6f5a31678e43`

## Construction (the count)

- 300 dest-FROM-FILE lanes × NAND-NAND buffer (2 g) = 600
- depth 2
- hops: hdvs 43 · sdmk 16 · hopf 16 · immn 1 · pdap 16 · stig 16 · flow 32 · byzq 16 · rgcg 4 · synd 16 · vscf 16 · cgat 16 · hpc 16 · mha 16 · eal 16 · dmb 10 · awcg 16 · 9 chimeras × 2
- dest FROM FILE: hdvs outs first 43 (`10274,10279,…`)
- dest FROM FILE: sdmk outs first 16 (`1188,1963,…`)
- dest FROM FILE: hopf outs `542..557`
- dest FROM FILE: immn alarm `29636` — flags non-self. DOOR STAYS OPEN.
- dest FROM FILE: pdap `286..301` · stig `6174..6189` · flow `16414..16445`
- dest FROM FILE: byzq / rgcg / synd sidecar outs
- dest FROM FILE: census vscf/cgat/hpc/mha/eal/dmb/awcg first dests
- dest FROM FILE: chimera 20–28 first two local outs
- to= routing IS address collision. No new routing mechanism.
- input plane = the other organs' planes. Local self-clocked commons bit plane.

Talk is not this file. A spatial tabletop essay is not this file. Organs 1–30 already on main; do not remint.

```
python3 muhl/desktop/MUHL_SUBZERO_ARCHETYPES/test_muhl_fab_titanx_commons.py
python3 muhl/desktop/MUHL_SUBZERO_ARCHETYPES/muhl_fab_titanx_commons.py --dry
```

titan: **NOT_WRITTEN**. PLUMB 1–31 excerpts are on this tree.
