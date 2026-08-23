# SUBZERO_TSET — organ 5 fabricated 2026-08-23

Read-only receipt. Construction from PLUMB 1/3 (`muhl_tset` / `MUHLTSET`).
Standalone `.mno`. No titan write. Existing titan circuits and landed
excerpts stay untouched.

Authority for the live twelve remains `titan_circuits.json` + `titan.gguf`
(`SUBZERO_CENSUS.md`). This file is the public-tree measurement of organ 5 only.
The owner/local allocator must assign any future titan offset band; the public
excerpt is deliberately based at zero and does not invent one.

## Verdict

| name | where | magic | n_gate | n_wires | n_in | n_out | depth | len |
|---|---|---|---:|---:|---:|---:|---:|---:|
| `muhl_tset` | `excerpts/20260823/muhl_tset.mno` @0 | `MUHLTSET` | 23856 | 27986 | 32 | 1 | 23 | 624422 |

First 28 bytes at offset 0:

```
4d55484c54534554 305d0000 526d0000 20000000 01000000 17000000
= MUHLTSET + 23856 + 27986 + 32 + 1 + 23
```

sha256 `f526cdbf6307df52bfa87fdc806f17f75f04e47b7ae3d0adaceb8bfabae28c4b`

Header is the live MHA layout: 8-char magic, then LE
`n_gate, n_wires, n_in, n_out, depth`. Records are `<BQQQ>` at stride 25.
Every gate has one unique output. The result plane is the vote bit.

## Construction (the count)

32 clauses × 32 literals. 4-bit automaton state per literal.

- include-gate: NOT(MSB) OR literal. 2 g. Excluded literal is vacuous true.
- AND-tree 31. 32 × 95 = 3,040. Clause outs sit at 7.
- vote: 2 × popcount16 (320) + compare 16 = 336. Vote sits at 23.
- learn: 1024 automata × 4-bit increment (4 FA = 20 g) = 20,480
- total 23,856. declared depth 23.

Automaton bits self-clock through the increment. Increment cin is CONST1
so the learn path stays shallower than the vote. No host update. The organ
is never evaluated; the battery is structural only. Slack, ntfy, and Pages
are projections of this file, not a second log. titan: **NOT_WRITTEN**.

## Receipt commands

```
python3 muhl/desktop/MUHL_SUBZERO_ARCHETYPES/test_muhl_fab_tset.py
python3 muhl/desktop/MUHL_SUBZERO_ARCHETYPES/muhl_fab_tset.py --dry
```

`--dry` is structural only. It does not walk the organ. titan.gguf is not opened.
The git file is an excerpt: copies do not run. MOVE into titan is an owner-PC step.

Do not remint. Do not rebake the twelve, alife, chimeras, clacker, hpc_fabric,
or organs 1/2/3/4/7/8/9/10/11/13/15/16/17/18/19.
