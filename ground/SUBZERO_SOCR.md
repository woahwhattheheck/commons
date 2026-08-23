# SUBZERO_SOCR — organ 8 fabricated 2026-08-23

Read-only receipt. Construction from PLUMB 2/3 (`muhl_socr` / `MUHLSOCR`).
Standalone `.mno`. No titan write. Existing titan circuits and landed
excerpts stay untouched.

Authority for the live twelve remains `titan_circuits.json` + `titan.gguf`
(`SUBZERO_CENSUS.md`). This file is the public-tree measurement of organ 8 only.
The owner/local allocator must assign any future titan offset band; the public
excerpt is deliberately based at zero and does not invent one.

## Verdict

| name | where | magic | n_gate | n_wires | n_in | n_out | depth | len |
|---|---|---|---:|---:|---:|---:|---:|---:|
| `muhl_socr` | `excerpts/20260823/muhl_socr.mno` @0 | `MUHLSOCR` | 15872 | 16642 | 768 | 768 | 14 | 419614 |

sha256 `d3af1a99d99e3c7779438abbd9644461627a655fd2fac374f337049ea37c360b`

Header is the live MHA layout: 8-char magic, then LE
`n_gate, n_wires, n_in, n_out, depth`. Records are `<BQQQ>` at stride 25.
Every gate has one unique output. Self-clock: each 3-bit cell's next height
out address **is** that cell's input address.

## Construction (the count)

16x16 = 256 cells, 3-bit height, topple at 4. No tuning parameter.

- four neighbour 3-bit adds: 4 x 15 = 60
- detect: AND of accumulated MSB (height >= 4)
- clear: XOR-with-0 pad of detect to declared depth 14
- 256 x 62 = 15,872
- CLK: height out → height in

Organ 9 `muhl_stig` is already on main. Do not remint it. Slack, ntfy, and
Pages are projections of this file, not a second log. titan: **NOT_WRITTEN**.

## Receipt commands

```
python3 muhl/desktop/MUHL_SUBZERO_ARCHETYPES/test_muhl_fab_socr.py
python3 muhl/desktop/MUHL_SUBZERO_ARCHETYPES/muhl_fab_socr.py --dry
```

`--dry` is structural only. It does not walk the organ. titan.gguf is not opened.
The git file is an excerpt: copies do not run. MOVE into titan is an owner-PC step.

Do not remint. Do not rebake the twelve, alife, chimeras, clacker, hpc_fabric,
or organs 1/7/9/11/13/15/16/17/18/19.
