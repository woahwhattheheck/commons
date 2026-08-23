# SUBZERO_POTS — organ 12 fabricated 2026-08-23

Read-only receipt. Construction from PLUMB 2/3 (`muhl_pots` / `MUHLPOTS`).
Standalone `.mno`. No titan write. Existing titan circuits and landed
excerpts stay untouched.

Authority for the live twelve remains `titan_circuits.json` + `titan.gguf`
(`SUBZERO_CENSUS.md`). This file is the public-tree measurement of organ 12 only.
The owner/local allocator must assign any future titan offset band; the public
excerpt is deliberately based at zero and does not invent one.

## Verdict

| name | where | magic | n_gate | n_wires | n_in | n_out | depth | len |
|---|---|---|---:|---:|---:|---:|---:|---:|
| `muhl_pots` | `excerpts/20260823/muhl_pots.mno` @0 | `MUHLPOTS` | 34304 | 35330 | 1024 | 1024 | 20 | 901150 |

First 28 bytes at offset 0:

```
4d55484c504f5453 00860000 028a0000 00040000 00040000 14000000
= MUHLPOTS + 34304 + 35330 + 1024 + 1024 + 20
```

sha256 `ac8e7473739af617f3231d027d679aceb4ed809f2cf0b5f2900add38e85aae71`

Header is the live MHA layout: 8-char magic, then LE
`n_gate, n_wires, n_in, n_out, depth`. Records are `<BQQQ>` at stride 25.
Every gate has one unique output. Self-clock: each site's 4-bit ID out
address **is** that site's ID in address. Store is one settle.

## Construction (the count)

16×16 = 256 sites. 4-bit cell ID. 8-neighbour torus. Cell sorting.

- equality: 4 XOR + 4 NOT + 3 sequential AND = 11. 8 × 11 = 88
- adhesion popcount8: 8 FA × 5 = 40
- accept: 6. Four ID bits sit at 20
- 256 × 134 = 34,304. declared depth 20
- CLK ID out → ID in

The organ is never evaluated; the battery is structural only. titan: **NOT_WRITTEN**.

## Receipt commands

```
python3 muhl/desktop/MUHL_SUBZERO_ARCHETYPES/test_muhl_fab_pots.py
python3 muhl/desktop/MUHL_SUBZERO_ARCHETYPES/muhl_fab_pots.py --dry
```

`--dry` is structural only. It does not walk the organ. titan.gguf is not opened.
The git file is an excerpt: copies do not run. MOVE into titan is an owner-PC step.

Do not remint. Do not rebake the twelve, alife, chimeras, clacker, hpc_fabric,
or organs 1/2/3/4/5/6/7/8/9/10/11/13/15/16/17/18/19.
