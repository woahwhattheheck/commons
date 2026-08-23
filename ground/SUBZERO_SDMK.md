# SUBZERO_SDMK — organ 2 fabricated 2026-08-23

Read-only receipt. Construction from PLUMB 1/3 (`muhl_sdmk` / `MUHLSDMK`).
Standalone `.mno`. No titan write. Existing titan circuits and landed
excerpts stay untouched.

Authority for the live twelve remains `titan_circuits.json` + `titan.gguf`
(`SUBZERO_CENSUS.md`). This file is the public-tree measurement of organ 2 only.
The owner/local allocator must assign any future titan offset band; the public
excerpt is deliberately based at zero and does not invent one.

## Verdict

| name | where | magic | n_gate | n_wires | n_in | n_out | depth | len |
|---|---|---|---:|---:|---:|---:|---:|---:|
| `muhl_sdmk` | `excerpts/20260823/muhl_sdmk.mno` @0 | `MUHLSDMK` | 24800 | 24930 | 128 | 32 | 25 | 645214 |

First 28 bytes at offset 0:

```
4d55484c53444d4b e0600000 62610000 80000000 20000000 19000000
= MUHLSDMK + 24800 + 24930 + 128 + 32 + 25
```

sha256 `f07d86557d8c3b51414242639500082d8224a5e0473502a5fed0acd043fb003a`

Header is the live MHA layout: 8-char magic, then LE
`n_gate, n_wires, n_in, n_out, depth`. Records are `<BQQQ>` at stride 25.
Every gate has one unique output. The result plane is the 32 location
activation bits.

## Construction (the count)

M = 32 hard locations. D = 128 address bits.

- XOR: query bit i XOR baked location bit. 128 XOR.
- popcount128: 128 full adders (5 g). One unused pad FA keeps the 5n
  budget. The other 127 are a 7-level carry tree. 640.
- thresh: 4+2+1 gates on the reduction bit. 7.
- 32 × 775 = 24,800
- declared depth 25 (XOR 1 + 7 FA levels × 3 + thresh 3)

Hard addresses are baked at fab. The organ is never evaluated; the
battery is structural only. Slack, ntfy, and Pages are projections of
this file, not a second log. titan: **NOT_WRITTEN**.

## Receipt commands

```
python3 muhl/desktop/MUHL_SUBZERO_ARCHETYPES/test_muhl_fab_sdmk.py
python3 muhl/desktop/MUHL_SUBZERO_ARCHETYPES/muhl_fab_sdmk.py --dry
```

`--dry` is structural only. It does not walk the organ. titan.gguf is not opened.
The git file is an excerpt: copies do not run. MOVE into titan is an owner-PC step.

Do not remint. Do not rebake the twelve, alife, chimeras, clacker, hpc_fabric,
or organs 1/7/8/9/10/11/13/15/16/17/18/19.
