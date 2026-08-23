# SUBZERO_BYZQ — organ 18 fabricated 2026-08-23

Read-only receipt. Construction from PLUMB 2/3 (`muhl_byzq` / `MUHLBYZQ`).
Standalone `.mno`. No titan write. Existing titan circuits and landed
excerpts stay untouched.

Authority for the live twelve remains `titan_circuits.json` + `titan.gguf`
(`SUBZERO_CENSUS.md`). This file is the public-tree measurement of organ 18 only.
The owner/local allocator must assign any future titan offset band; the public
excerpt is deliberately based at zero and does not invent one.

## Verdict

| name | where | magic | n_gate | n_wires | n_in | n_out | depth | len |
|---|---|---|---:|---:|---:|---:|---:|---:|
| `muhl_byzq` | `excerpts/20260823/muhl_byzq.mno` @0 | `MUHLBYZQ` | 14880 | 14913 | 31 | 31 | 30 | 387189 |

First 28 bytes at offset 0:

```
4d55484c42595a51 203a0000 413a0000 1f000000 1f000000 1e000000
= MUHLBYZQ + 14880 + 14913 + 31 + 31 + 30
```

sha256 `83c3299088ae56b871af6e14443d3d63c5a9b8a9a123cc4aa9f98ed63fb30b7e`

Header is the live MHA layout: 8-char magic, then LE
`n_gate, n_wires, n_in, n_out, depth`. Records are `<BQQQ>` at stride 25.
Every gate has one unique output. The result plane is the 31 phase-3
quorum bits.

## Construction (the count)

n = 31 nodes, f = 10, PBFT 3 phases. Digests are the 31 vote wires.

- Per node per phase: popcount31 is 31 full adders (155 g). Threshold is
  one more FA (5 g). 160 g.
- 22 parallel FAs plus a 9-FA spine plus the threshold FA. Critical path
  is 10 FAs, depth 30.
- 31 × 3 units in parallel so the three phases do not stack depth.
- TOTAL 14,880 gates, declared depth 30.

The organ is never evaluated; the battery is structural only.

The sidecar `excerpts/20260823/byzq_circuits.json` records the physical
input/output addresses and the same byte receipt.

## Receipt commands

```
python3 muhl/desktop/MUHL_SUBZERO_ARCHETYPES/test_muhl_fab_byzq.py
python3 muhl/desktop/MUHL_SUBZERO_ARCHETYPES/muhl_fab_byzq.py --dry
```

The structural battery is 8/8. `--dry` manufactures and checks bytes in memory
only; it never evaluates or schedules the organ and writes no files. The fab is
deterministic Python stdlib and does not open `titan.gguf`.

Titan: **NOT_WRITTEN**. Do not remint. Do not rebake the twelve, alife,
chimeras, clacker, hpc_fabric, or organs 1/7/11/13/15/16/17/19. MOVE into titan
is an owner-PC step after a fresh band is allocated locally.
