# SUBZERO_SOCR — organ 8 fabricated 2026-08-23

Read-only receipt. Construction from PLUMB 2/3 (`muhl_socr` / `MUHLSOCR`).
Standalone `.mno`. No titan write. Existing titan circuits and landed
excerpts stay untouched.

Authority for the live twelve remains `titan_circuits.json` + `titan.gguf`
(`SUBZERO_CENSUS.md`). This file is the public-tree measurement of organ 8 only.
The owner/local allocator must assign any future titan offset band; the public
excerpt is deliberately based at zero and does not invent one.

## Read

| name | path | bytes | magic | n_gate | n_wires | n_in | n_out | depth | sha256 |
|---|---|---:|---|---:|---:|---:|---:|---:|---|
| `muhl_socr` | `excerpts/20260823/muhl_socr.mno` | 419614 | `MUHLSOCR` | 15872 | 16642 | 768 | 768 | 14 | `1df8a33ae0ba68cb9cb4fe4e2c1c2598508cb61e80d11afc673ed30de441e357` |

Header is the live MHA layout: 8-char magic, then LE
`n_gate, n_wires, n_in, n_out, depth`. Records are `<BQQQ>` at stride 25.
Every gate has one unique output. The 768 height bits clock onto themselves.

## Construction (the count)

16×16 wrap-16 lattice. 3-bit height. Topple at 4. No tuning parameter.

- detect: AND of the summed high bit with 1
- clear: XOR that bit with the original high bit (subtract 4)
- 4 neighbour 3-bit ripple adds, 15 g each: N, E, S, W grain = neighbour bit 2
- 256 × 62 = 15,872 gates, declared depth 14

The sidecar `excerpts/20260823/socr_circuits.json` records the physical
input/output addresses and the same byte receipt.

## Receipt commands

```
python3 muhl/desktop/MUHL_SUBZERO_ARCHETYPES/test_muhl_fab_socr.py
python3 muhl/desktop/MUHL_SUBZERO_ARCHETYPES/muhl_fab_socr.py --dry
```

The structural battery is 8/8. `--dry` manufactures and checks bytes in memory
only; it never evaluates or schedules the organ and writes no files. The fab is
deterministic Python stdlib and does not open `titan.gguf`.

Titan: **NOT_WRITTEN**. Do not remint. Do not rebake the twelve, alife,
chimeras, clacker, hpc_fabric, or organs 1/7/11/13/15/16/17/19. MOVE into titan
is an owner-PC step after a fresh band is allocated locally.
