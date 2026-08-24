# SUBZERO_CHPD — organ 26 fabricated 2026-08-24

Read-only receipt. Construction from PLUMB 3/3 (`muhl_chimera_pots_dmb` / `MUHLCHPD`).
Standalone `.mno`. No titan write. Organs 1–25 untouched.

## Verdict

| name | where | magic | n_gate | n_wires | n_in | n_out | depth | len |
|---|---|---|---:|---:|---:|---:|---:|---:|
| `muhl_chimera_pots_dmb` | `excerpts/20260823/muhl_chimera_pots_dmb.mno` @0 | `MUHLCHPD` | 20 | 22 | 10 | 10 | 2 | 630 |

sha256 `997c53127e555de004862e602089bc19bf5d2a1d0eb4b853a875aef467b6da82`

## Construction (the count)

- 10 L-system rewrite dests × NAND-NAND buffer (2 g) = 20
- depth 2
- dest FROM FILE: DMB offset `93709782656` + rewrite wires `2..11` → `93709782658..93709782667`
- dest FROM FILE: pots ID ins `8222..8231`
- DMB EXISTS in titan (census). This excerpt does not write it.

Talk is not this file. A name-correction / mixup note is not this file. Organs 22–25 already on main; do not remint.

```
python3 muhl/desktop/MUHL_SUBZERO_ARCHETYPES/test_muhl_fab_chimera_pots_dmb.py
python3 muhl/desktop/MUHL_SUBZERO_ARCHETYPES/muhl_fab_chimera_pots_dmb.py --dry
```

titan: **NOT_WRITTEN**. Organs 27–31 stay NOT_LANDED.
