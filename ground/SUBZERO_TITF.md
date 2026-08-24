# SUBZERO_TITF — organ 29 fabricated 2026-08-24

Read-only receipt. Construction from PLUMB 3/3 (`muhl_titanx_forge` / `MUHLTITF`).
Standalone `.mno`. No titan write. Organs 1–28 untouched.

## Verdict

| name | where | magic | n_gate | n_wires | n_in | n_out | depth | len |
|---|---|---|---:|---:|---:|---:|---:|---:|
| `muhl_titanx_forge` | `excerpts/20260823/muhl_titanx_forge.mno` @0 | `MUHLTITF` | 180 | 182 | 90 | 90 | 2 | 5430 |

sha256 `29fb6ee200b645c990e60b98ff61e060b7fe347e11229a746dc26ccbbdacf788`

## Construction (the count)

- 90 dest-FROM-FILE lanes × NAND-NAND buffer (2 g) = 180
- depth 2
- hops: lvin→ispn 32 · ispn→socr 20 · socr→nefg 8 · nefg→dmb 8 · grbn→petr 20 · petr→dmb 2
- dest FROM FILE: lvin outs `542..573` → ispn ins `2078..2109`
- dest FROM FILE: ispn outs `2078..2097` → socr ins `6174..6193`
- dest FROM FILE: socr outs `6174..6181` → NEFG object_a `93709716802..93709716809`
- dest FROM FILE: NEFG object_a → DMB rewrite `93709782658..93709782665`
- dest FROM FILE: grbn outs `2078..2097` → petr ins `2078..2097`
- dest FROM FILE: petr outs `2078..2079` → DMB rewrite `93709782666..93709782667`
- NEFG and DMB EXIST in titan (census). This excerpt does not write them.
- PROPOSES genomes only. NEVER fabricates during runtime.

Talk is not this file. A daily inventory is not this file. Organs 27–28 already on main; do not remint.

```
python3 muhl/desktop/MUHL_SUBZERO_ARCHETYPES/test_muhl_fab_titanx_forge.py
python3 muhl/desktop/MUHL_SUBZERO_ARCHETYPES/muhl_fab_titanx_forge.py --dry
```

titan: **NOT_WRITTEN**. Organs 30–31 stay NOT_LANDED.
