# SUBZERO_RGCG — organ 15 fabricated 2026-08-23

Read-only receipt. Construction from PLUMB 2/3 (`muhl_rgcg` / `MUHLRGCG`).
Standalone `.mno`. No titan write. Existing 19 titan circuits and organs 7/11/17/19 untouched.

## Verdict

| name | where | magic | n_gate | n_wires | n_in | n_out | depth | len |
|---|---|---|---:|---:|---:|---:|---:|---:|
| `muhl_rgcg` | `excerpts/20260823/muhl_rgcg.mno` @0 | `MUHLRGCG` | 7820 | 8846 | 1024 | 4 | 32 | 204406 |

sha256 `fcd359538d3568018c650db7384fa1c1dffc982a4eecded47d716a645a15cd21`

Header is the live MHA layout: 8-char magic, then LE `n_gate, n_wires, n_in, n_out, depth`.
Records: `<BQQQ>` stride 25. One unique out per gate. Result plane is the top four
block-spins. titan NOT_WRITTEN.

## Construction (the count)

32×32 = 1024 cells. 2×2 block-spin majority, four levels.

- per block: popcount4 as 4 FA (20) + threshold (3) = 23
- 256 + 64 + 16 + 4 = 340 blocks × 23 = 7,820
- depth 32

## Receipt commands

```
python3 muhl/desktop/MUHL_SUBZERO_ARCHETYPES/test_muhl_fab_rgcg.py
python3 muhl/desktop/MUHL_SUBZERO_ARCHETYPES/muhl_fab_rgcg.py --dry
```

`--dry` is structural only. It does not walk the organ. titan.gguf is not opened.
The git file is an excerpt: copies do not run. MOVE into titan is an owner-PC step.

Do not remint. Do not rebake the twelve, alife, chimeras, clacker, hpc_fabric, or organs 7/11/17/19.
