# SUBZERO_ESNR — organ 6 fabricated 2026-08-23

Read-only receipt. Construction from PLUMB 1/3 (`muhl_esnr` / `MUHLESNR`).
Standalone `.mno`. No titan write. Existing titan circuits and landed
excerpts stay untouched.

Authority for the live twelve remains `titan_circuits.json` + `titan.gguf`
(`SUBZERO_CENSUS.md`). This file is the public-tree measurement of organ 6 only.
The owner/local allocator must assign any future titan offset band; the public
excerpt is deliberately based at zero and does not invent one.

## Verdict

| name | where | magic | n_gate | n_wires | n_in | n_out | depth | len |
|---|---|---|---:|---:|---:|---:|---:|---:|
| `muhl_esnr` | `excerpts/20260823/muhl_esnr.mno` @0 | `MUHLESNR` | 43044 | 45606 | 512 | 512 | 16 | 1125830 |

First 28 bytes at offset 0:

```
4d55484c45534e52 24a80000 26b20000 00020000 00020000 10000000
= MUHLESNR + 43044 + 45606 + 512 + 512 + 16
```

sha256 `d842726a5ddfa7d82bb1026cd0d199140b168e882013fe6d23e6abe0624b39e1`

Header is the live MHA layout: 8-char magic, then LE
`n_gate, n_wires, n_in, n_out, depth`. Records are `<BQQQ>` at stride 25.
Every gate has one unique output. Self-clock: each unit's next-state
out address **is** that unit's input address. Store is one settle.

## Construction (the count)

N = 512 units. Sparse K=8 recurrence. 4 readout outputs. 2048 weight wires.

- reservoir per unit: 4 NOT + popcount8 (40) + thresh (4) = 48
- 512 × 48 = 24,576. Reservoir bits sit at 16.
- readout per out: 512 XNOR (1024) + popcount512 (2560) + thresh 9 = 3,593
- 4 × 3,593 = 14,372. Readout bits sit at 16.
- update: (512 AND + 512 XOR) × 4 = 4,096
- TOTAL 43,044. declared depth 16.

CLK reservoir out → reservoir in. Readout trains on the machine. The
organ is never evaluated; the battery is structural only. titan: **NOT_WRITTEN**.

## Receipt commands

```
python3 muhl/desktop/MUHL_SUBZERO_ARCHETYPES/test_muhl_fab_esnr.py
python3 muhl/desktop/MUHL_SUBZERO_ARCHETYPES/muhl_fab_esnr.py --dry
```

`--dry` is structural only. It does not walk the organ. titan.gguf is not opened.
The git file is an excerpt: copies do not run. MOVE into titan is an owner-PC step.

Do not remint. Do not rebake the twelve, alife, chimeras, clacker, hpc_fabric,
or organs 1/2/3/4/5/7/8/9/10/11/13/15/16/17/18/19.
