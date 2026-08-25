# SUBZERO_CHLS — organ 28 fabricated 2026-08-24

Read-only receipt. Construction from PLUMB 3/3 (`muhl_chimera_lvin_synd` / `MUHLCHLS`).
Standalone `.mno`. No titan write. Organs 1–27 untouched.

## Verdict

| name | where | magic | n_gate | n_wires | n_in | n_out | depth | len |
|---|---|---|---:|---:|---:|---:|---:|---:|
| `muhl_chimera_lvin_synd` | `excerpts/20260823/muhl_chimera_lvin_synd.mno` @0 | `MUHLCHLS` | 22 | 24 | 11 | 11 | 2 | 690 |

sha256 `43781849e21f4df0ff523966d47c0d9b2643e0c0abdaf0dd8f32b02fded71cae`

## Construction (the count)

- 11 dest-FROM-FILE wires × NAND-NAND buffer (2 g) = 22
- depth 2
- LVIN / SYND chimera. Excerpt only. This file is the named public-tree card.

Talk is not this file. Excerpts 28 already exist. Do not remint the organ.

```
python3 muhl/desktop/MUHL_SUBZERO_ARCHETYPES/test_muhl_fab_chimera_lvin_synd.py
python3 muhl/desktop/MUHL_SUBZERO_ARCHETYPES/muhl_fab_chimera_lvin_synd.py --dry
```

titan: **NOT_WRITTEN**. A missing card is FINDER_FAILED, never STRUCTURAL_ONLY / PASS.
