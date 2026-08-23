# SUBZERO_PRED — organ 14 fabricated 2026-08-23

Read-only receipt. Construction from PLUMB 2/3 (`muhl_pred` / `MUHLPRED`).
Standalone `.mno`. No titan write. Existing titan circuits and landed
excerpts stay untouched.

Authority for the live twelve remains `titan_circuits.json` + `titan.gguf`
(`SUBZERO_CENSUS.md`). This file is the public-tree measurement of organ 14 only.
The owner/local allocator must assign any future titan offset band; the public
excerpt is deliberately based at zero and does not invent one.

## Verdict

| name | where | magic | n_gate | n_wires | n_in | n_out | depth | len |
|---|---|---|---:|---:|---:|---:|---:|---:|
| `muhl_pred` | `excerpts/20260823/muhl_pred.mno` @0 | `MUHLPRED` | 17664 | 18050 | 384 | 384 | 42 | 462750 |

First 28 bytes at offset 0:

```
4d55484c50524544 00450000 82460000 80010000 80010000 2a000000
= MUHLPRED + 17664 + 18050 + 384 + 384 + 42
```

sha256 `be5ba528497b2cc2c8f14cfb433d8fdc2a49d1bf6477159ca92e844b6f665658`

Header is the live MHA layout: 8-char magic, then LE
`n_gate, n_wires, n_in, n_out, depth`. Records are `<BQQQ>` at stride 25.
Every gate has one unique output. Self-clock: error out address **is**
next-tick prediction in. Store is one settle.

## Construction (the count)

3 layers × 128 units. Each layer predicts below and transmits ERROR ONLY.

- majority-8: popcount8 (40) + thresh 4 = 44
- error XOR + transmit = 46
- 384 × 46 = 17,664
- one layer sits at 14. Three stacked layers put layer-2 transmit at 42.
- CLK error out → next-tick prediction in

The organ is never evaluated; the battery is structural only. titan: **NOT_WRITTEN**.

## Receipt commands

```
python3 muhl/desktop/MUHL_SUBZERO_ARCHETYPES/test_muhl_fab_pred.py
python3 muhl/desktop/MUHL_SUBZERO_ARCHETYPES/muhl_fab_pred.py --dry
```

`--dry` is structural only. It does not walk the organ. titan.gguf is not opened.
The git file is an excerpt: copies do not run. MOVE into titan is an owner-PC step.

Do not remint. Do not rebake the twelve, alife, chimeras, clacker, hpc_fabric,
or organs 1/2/3/4/5/6/7/8/9/10/11/12/13/15/16/17/18/19.
