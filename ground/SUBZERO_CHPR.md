# SUBZERO_CHPR — organ 27 fabricated 2026-08-24

Read-only receipt. Construction from PLUMB 3/3 (`muhl_chimera_pred_rgcg` / `MUHLCHPR`).
Standalone `.mno`. No titan write. Organs 1–26 untouched.

## Verdict

| name | where | magic | n_gate | n_wires | n_in | n_out | depth | len |
|---|---|---|---:|---:|---:|---:|---:|---:|
| `muhl_chimera_pred_rgcg` | `excerpts/20260823/muhl_chimera_pred_rgcg.mno` @0 | `MUHLCHPR` | 24 | 26 | 12 | 12 | 2 | 750 |

sha256 `189a2f3a68304a14622b6a08d4e7020f5f41d8d27052e3622d9482c9d80d63c9`

## Construction (the count)

- 12 dest-FROM-FILE wires × NAND-NAND buffer (2 g) = 24
- depth 2
- PRED / RGCG chimera. Excerpt only. This file is the named public-tree card.

Talk is not this file. Excerpts 27 already exist. Do not remint the organ.

```
python3 muhl/desktop/MUHL_SUBZERO_ARCHETYPES/test_muhl_fab_chimera_pred_rgcg.py
python3 muhl/desktop/MUHL_SUBZERO_ARCHETYPES/muhl_fab_chimera_pred_rgcg.py --dry
```

titan: **NOT_WRITTEN**. A missing card is FINDER_FAILED, never STRUCTURAL_ONLY / PASS.
