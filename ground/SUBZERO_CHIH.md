# SUBZERO_CHIH — organ 20 fabricated 2026-08-24

Read-only receipt. Construction from PLUMB 3/3 (`muhl_chimera_immn_hdvs` / `MUHLCHIH`).
Standalone `.mno`. No titan write. Existing titan circuits and organs 1–19 untouched.

Authority for the live twelve remains `titan_circuits.json` + `titan.gguf` (see
`SUBZERO_CENSUS.md`). This file is the public-tree measurement of organ 20 only.
The owner/local allocator must assign any future titan offset band; the public
excerpt is deliberately based at zero and does not invent one.

## Verdict

| name | where | magic | n_gate | n_wires | n_in | n_out | depth | len |
|---|---|---|---:|---:|---:|---:|---:|---:|
| `muhl_chimera_immn_hdvs` | `excerpts/20260823/muhl_chimera_immn_hdvs.mno` @0 | `MUHLCHIH` | 20 | 22 | 10 | 10 | 2 | 630 |

First 28 bytes at offset 0:

```
4d55484c43484948 14000000 16000000 0a000000 0a000000 02000000
= MUHLCHIH + 20 + 22 + 10 + 10 + 2
```

sha256 `54418132f3c610b5cd5cfd6332a74928c3b19e52ca081569e18abc0ea8142445`

Header is the live MHA layout: 8-char magic, then LE
`n_gate, n_wires, n_in, n_out, depth`. Records are `<BQQQ>` at stride 25.
Every gate has one unique output. The 10 BUNDLE-plane slots are remapped onto
the same 10 detector-flag input addresses: bundle out **is** detector in.

## Construction (the count)

IMMN detector-bank match flags feed the HDVS BUNDLE plane. Ten lanes. Each
lane is the existing chimera double-negation NAND buffer (same shape as
`muhl_fab_chimera_ardr_eal.py`): `NAND(src,src)` then `NAND(tmp,tmp)`. That
is an identity buffer, depth 2, 2 gates per lane.

- 10 lanes × 2 NAND = 20 gates
- declared depth 2
- FLAGS, NEVER GATES. The door stays open.

The sidecar `excerpts/20260823/chimera_immn_hdvs_circuits.json` records the
ten lane addresses and the same byte receipt. Journaled MOVE packet recounts
20 excerpts. titan: NOT_WRITTEN.

## Receipt commands

```
python3 muhl/desktop/MUHL_SUBZERO_ARCHETYPES/test_muhl_fab_chimera_immn_hdvs.py
python3 muhl/desktop/MUHL_SUBZERO_ARCHETYPES/muhl_fab_chimera_immn_hdvs.py --dry
```

`--dry` manufactures and checks bytes in memory only; it never evaluates or
schedules the organ and writes no files. The fab is deterministic Python
stdlib and does not open `titan.gguf`.

Titan: **NOT_WRITTEN**. Do not remint. Do not rebake the twelve, alife,
clacker, hpc_fabric, or organs 1–19. MOVE into titan is an owner-PC step
after a fresh band is allocated locally. Organs 21–31 stay NOT_LANDED.
