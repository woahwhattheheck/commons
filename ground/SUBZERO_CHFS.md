# SUBZERO_CHFS — organ 25 fabricated 2026-08-24

Read-only receipt. Construction from PLUMB 3/3 (`muhl_chimera_flow_stig` / `MUHLCHFS`).
Standalone `.mno`. No titan write. Organs 1–24 untouched.

## Verdict

| name | where | magic | n_gate | n_wires | n_in | n_out | depth | len |
|---|---|---|---:|---:|---:|---:|---:|---:|
| `muhl_chimera_flow_stig` | `excerpts/20260823/muhl_chimera_flow_stig.mno` @0 | `MUHLCHFS` | 18 | 20 | 9 | 9 | 2 | 570 |

sha256 `20a4a399e7c13216d029604da1f30e043bbdc44e2ea11491987c332309042aba`

## Construction (the count)

- 9 conductance lanes × NAND-NAND buffer (2 g) = 18
- depth 2
- dest FROM FILE: flow conductance outs `16414..16422`
- dest FROM FILE: stig evaporate-rate ins `6174..6182`

Talk is not this file. Organs 22–24 already on main; do not remint.

```
python3 muhl/desktop/MUHL_SUBZERO_ARCHETYPES/test_muhl_fab_chimera_flow_stig.py
python3 muhl/desktop/MUHL_SUBZERO_ARCHETYPES/muhl_fab_chimera_flow_stig.py --dry
```

titan: **NOT_WRITTEN**. Organs 26–31 stay NOT_LANDED.
