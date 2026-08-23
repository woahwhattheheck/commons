# SUBZERO_HDVS — organ 1 fabricated 2026-08-23

Read-only receipt. Construction from PLUMB 1/3 (`muhl_hdvs` / `MUHLHDVS`).
Standalone `.mno`. No titan write. Existing titan circuits and landed
excerpts stay untouched.

Authority for the live twelve remains `titan_circuits.json` + `titan.gguf`
(`SUBZERO_CENSUS.md`). This file is the public-tree measurement of organ 1 only.
The owner/local allocator must assign any future titan offset band; the public
excerpt is deliberately based at zero and does not invent one.

## Verdict

| name | where | magic | n_gate | n_wires | n_in | n_out | depth | len |
|---|---|---|---:|---:|---:|---:|---:|---:|
| `muhl_hdvs` | `excerpts/20260823/muhl_hdvs.mno` @0 | `MUHLHDVS` | 12288 | 13314 | 1024 | 1024 | 34 | 328734 |

First 28 bytes at offset 0:

```
4d55484c48445653 00300000 02340000 00040000 00040000 22000000
= MUHLHDVS + 12288 + 13314 + 1024 + 1024 + 34
```

sha256 `1f392a877594a9a81d28cca02e3f204355aba1e02c4c11b5cb94370ded7309bd`

Header is the live MHA layout: 8-char magic, then LE
`n_gate, n_wires, n_in, n_out, depth`. Records are `<BQQQ>` at stride 25.
Every gate has one unique output. The result plane is the 1024 bundled bits.

## Construction (the count)

D = 1024-bit hypervectors. bind=XOR, bundle=majority, sequence=permute.

- BIND: bit i XOR rotate-1. 1,024 XOR.
- BUNDLE: majority-3 of (A, rotate-3, rotate-17), 5 gates per bit. 5,120.
- PERMUTE: address remap. 0 gates.
- SIM: bundled XOR bound (1,024) plus a 10-level carry tree of 1,024
  full adders (5 g, depth 3). Carry-out is the reduction bit. 6,144.
- TOTAL 12,288 gates, declared depth 34.

Sequence is wiring. Bind is a separate XOR plane and is the second SIM
input. The organ is never evaluated; the battery is structural only.

The sidecar `excerpts/20260823/hdvs_circuits.json` records the physical
input/output addresses and the same byte receipt.

## Receipt commands

```
python3 muhl/desktop/MUHL_SUBZERO_ARCHETYPES/test_muhl_fab_hdvs.py
python3 muhl/desktop/MUHL_SUBZERO_ARCHETYPES/muhl_fab_hdvs.py --dry
```

The structural battery is 8/8. `--dry` manufactures and checks bytes in memory
only; it never evaluates or schedules the organ and writes no files. The fab is
deterministic Python stdlib and does not open `titan.gguf`.

Titan: **NOT_WRITTEN**. Do not remint. Do not rebake the twelve, alife,
chimeras, clacker, hpc_fabric, or organs 7/11/13/15/16/17/19. MOVE into titan
is an owner-PC step after a fresh band is allocated locally.
