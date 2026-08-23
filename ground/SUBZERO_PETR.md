# SUBZERO_PETR — organ 13 fabricated 2026-08-23

Read-only receipt. Construction from PLUMB 2/3 (`muhl_petr` / `MUHLPETR`).
Standalone `.mno`. No titan write. Existing titan circuits and organ 7 untouched.

Authority for the live twelve remains `titan_circuits.json` + `titan.gguf` (see
`SUBZERO_CENSUS.md`). This file is the public-tree measurement of organ 13 only.
The owner/local allocator must assign any future titan offset band; the public
excerpt is deliberately based at zero and does not invent one.

## Verdict

| name | where | magic | n_gate | n_wires | n_in | n_out | depth | len |
|---|---|---|---:|---:|---:|---:|---:|---:|
| `muhl_petr` | `excerpts/20260823/muhl_petr.mno` @0 | `MUHLPETR` | 3552 | 3810 | 256 | 256 | 14 | 94686 |

First 28 bytes at offset 0:

```
4d55484c50455452 e00d0000 e20e0000 00010000 00010000 0e000000
= MUHLPETR + 3552 + 3810 + 256 + 256 + 14
```

sha256 `55a52541c1bbee1c4b7115d4ca745b6c04f71eec2832307f2b5d19c398148f44`

Header is the live MHA layout: 8-char magic, then LE
`n_gate, n_wires, n_in, n_out, depth`. Records are `<BQQQ>` at stride 25.
Every gate has one unique output. The 256 marking outputs are remapped onto
the same 256 marking input addresses: marking out **is** marking in.

## Construction (the count)

The field has 64 four-bit places and 32 transitions. Transition `t` owns the
disjoint pair `P(2t), P(2t+1)` and implements the chemical reaction
`2A + B -> 2B`. Its three input arcs are `A,A,B`; its two output arcs are
`B,B`. The five arc arithmetic blocks run in parallel; aggregate roots compile
the net effects `A-2` and `B-1+2`, while the remaining blocks retain per-arc
witnesses. Witnesses are emitted before the final marking roots, so no gate
reads a marking address after a self-clock write. Every block is conditional
on the enabled wire; a disabled transition preserves both markings without a
host/runtime sequence.

- enabled: 3 × OR4 (9 gates) + AND3 (2 gates) = 11
- consume: 3 × four-bit ripple subtract (20 gates each) = 60
- produce: 2 × four-bit ripple add (20 gates each) = 40
- per transition: 111 gates
- 32 × 111 = 3,552 gates, declared depth 14

The sidecar `excerpts/20260823/petr_circuits.json` records every transition's
place arcs, the physical input/output addresses, and the same byte receipt.

## Receipt commands

```
python3 muhl/desktop/MUHL_SUBZERO_ARCHETYPES/test_muhl_fab_petr.py
python3 muhl/desktop/MUHL_SUBZERO_ARCHETYPES/muhl_fab_petr.py --dry
```

The structural battery is 9/9. `--dry` manufactures and checks bytes in memory
only; it never evaluates or schedules the organ and writes no files. The fab is
deterministic Python stdlib and does not open `titan.gguf`.

Titan: **NOT_WRITTEN**. Do not remint. Do not rebake the twelve, alife,
chimeras, clacker, hpc_fabric, or organ 7. MOVE into titan is an owner-PC step
after a fresh band is allocated locally.
