# SUBZERO_SYND — organ 16 fabricated 2026-08-23

Read-only receipt. Construction from PLUMB 2/3 (`muhl_synd` / `MUHLSYND`).
Standalone `.mno`. No titan write. Existing titan circuits and organs
7/11/13/15/17/19 untouched.

Authority for the live twelve remains `titan_circuits.json` + `titan.gguf` (see
`SUBZERO_CENSUS.md`). This file is the public-tree measurement of organ 16 only.
The owner/local allocator must assign any future titan offset band; the public
excerpt is deliberately based at zero and does not invent one.

## Verdict

| name | where | magic | n_gate | n_wires | n_in | n_out | depth | len |
|---|---|---|---:|---:|---:|---:|---:|---:|
| `muhl_synd` | `excerpts/20260823/muhl_synd.mno` @0 | `MUHLSYND` | 27520 | 27778 | 256 | 256 | 45 | 717854 |

First 28 bytes at offset 0:

```
4d55484c53594e44 806b0000 826c0000 00010000 00010000 2d000000
= MUHLSYND + 27520 + 27778 + 256 + 256 + 45
```

sha256 `302a242ebd483d25b4b5e3f62943a4e21e090d741fa431132a520316e4b5840d`

Header is the live MHA layout: 8-char magic, then LE
`n_gate, n_wires, n_in, n_out, depth`. Records are `<BQQQ>` at stride 25.
Every gate has one unique output. The 256 codeword outputs are remapped onto
the same 256 codeword input addresses: codeword out **is** codeword in.

## Construction (the count)

LDPC `(n=256, k=128)`, row weight 6, column weight 3, three belief-propagation
iterations. The Tanner graph is the (3,6)-regular QC lattice
`check r → (2r, 2r+1, 2r+64, 2r+65, 2r+128, 2r+129) mod 256`. Destinations
come from that lattice. No host read separates intended state change from
corruption.

- syndrome: 128 checks × XOR-chain 5 = 640
- check-node 1-bit min-sum: 128 × 30 × 3 = 11,520
- variable-node update: 256 × 20 × 3 = 15,360
- total 27,520 gates, declared depth 45

The sidecar `excerpts/20260823/synd_circuits.json` records the physical
input/output addresses and the same byte receipt.

## Receipt commands

```
python3 muhl/desktop/MUHL_SUBZERO_ARCHETYPES/test_muhl_fab_synd.py
python3 muhl/desktop/MUHL_SUBZERO_ARCHETYPES/muhl_fab_synd.py --dry
```

The structural battery is 9/9. `--dry` manufactures and checks bytes in memory
only; it never evaluates or schedules the organ and writes no files. The fab is
deterministic Python stdlib and does not open `titan.gguf`.

Titan: **NOT_WRITTEN**. Do not remint. Do not rebake the twelve, alife,
chimeras, clacker, hpc_fabric, or organs 7/11/13/15/17/19. MOVE into titan is
an owner-PC step after a fresh band is allocated locally.
