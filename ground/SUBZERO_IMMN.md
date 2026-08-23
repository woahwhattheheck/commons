# SUBZERO_IMMN — organ 4 fabricated 2026-08-23

Read-only receipt. Construction from PLUMB 1/3 (`muhl_immn` / `MUHLIMMN`).
Standalone `.mno`. No titan write. Existing titan circuits and landed
excerpts stay untouched.

Authority for the live twelve remains `titan_circuits.json` + `titan.gguf`
(`SUBZERO_CENSUS.md`). This file is the public-tree measurement of organ 4 only.
The owner/local allocator must assign any future titan offset band; the public
excerpt is deliberately based at zero and does not invent one.

## Verdict

| name | where | magic | n_gate | n_wires | n_in | n_out | depth | len |
|---|---|---|---:|---:|---:|---:|---:|---:|
| `muhl_immn` | `excerpts/20260823/muhl_immn.mno` @0 | `MUHLIMMN` | 29951 | 34081 | 32 | 1 | 27 | 782892 |

First 28 bytes at offset 0:

```
4d55484c494d4d4e ff740000 21850000 20000000 01000000 1b000000
= MUHLIMMN + 29951 + 34081 + 32 + 1 + 27
```

sha256 `9aaa8c738f9c2e8a0eaa24f419da83ef7e3125897e80a1f732067db02fdac827`

Header is the live MHA layout: 8-char magic, then LE
`n_gate, n_wires, n_in, n_out, depth`. Records are `<BQQQ>` at stride 25.
Every gate has one unique output. The result plane is the alarm bit.
128 match flags exist as wires. FLAGS, NEVER GATES. The door stays open.

## Construction (the count)

128 detectors. 32-bit self-window. Negative selection.

- XOR: window bit i XOR baked detector bit. 32 XOR.
- popcount32: 32 full adders (5 g). One unused pad FA keeps the 5n
  budget. The other 31 are a 5-level carry tree. 160.
- thresh: hopf 6-gate 4+2 pad. Match flags sit at 20.
- 128 × 198 = 25,344
- alarm OR-tree: 127. Alarm sits at 27.
- mature: 32-bit Fibonacci LFSR, 3 tap XOR + 32 identity XOR. 128 × 35 = 4,480
- total 29,951. declared depth 27.

Detector bits self-clock through the LFSR. The organ is never evaluated;
the battery is structural only. Slack, ntfy, and Pages are projections of
this file, not a second log. titan: **NOT_WRITTEN**.

## Receipt commands

```
python3 muhl/desktop/MUHL_SUBZERO_ARCHETYPES/test_muhl_fab_immn.py
python3 muhl/desktop/MUHL_SUBZERO_ARCHETYPES/muhl_fab_immn.py --dry
```

`--dry` is structural only. It does not walk the organ. titan.gguf is not opened.
The git file is an excerpt: copies do not run. MOVE into titan is an owner-PC step.

Do not remint. Do not rebake the twelve, alife, chimeras, clacker, hpc_fabric,
or organs 1/2/3/7/8/9/10/11/13/15/16/17/18/19.
