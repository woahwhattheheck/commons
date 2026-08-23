# SUBZERO_STIG — organ 9 fabricated 2026-08-23

Read-only receipt. Construction from PLUMB 2/3 (`muhl_stig` / `MUHLSTIG`).
Standalone `.mno`. No titan write. Existing titan circuits and landed
excerpts stay untouched.

Authority for the live twelve remains `titan_circuits.json` + `titan.gguf`
(`SUBZERO_CENSUS.md`). This file is the public-tree measurement of organ 9 only.
The owner/local allocator must assign any future titan offset band; the public
excerpt is deliberately based at zero and does not invent one.

## Verdict

| name | where | magic | n_gate | n_wires | n_in | n_out | depth | len |
|---|---|---|---:|---:|---:|---:|---:|---:|
| `muhl_stig` | `excerpts/20260823/muhl_stig.mno` @0 | `MUHLSTIG` | 15360 | 16130 | 768 | 768 | 18 | 406302 |

sha256 `a831192bfc624e04c261d26a0f0b83a010684fcd116d46451172ea2b407f0bab`

Header is the live MHA layout: 8-char magic, then LE
`n_gate, n_wires, n_in, n_out, depth`. Records are `<BQQQ>` at stride 25.
Every gate has one unique output. Self-clock: each 3-bit cell's next field
out address **is** that cell's input address.

## Construction (the count)

16x16 = 256 cells, 3-bit pheromone.

- diffuse: 3 neighbor 3-bit adds (9 FAs, 45)
- evaporate: x - (x>>3) is 0 on a 3-bit word; 15 AND-with-1 remainder (15)
- divide-by-4 is wiring
- 256 x 60 = 15,360
- declared depth 18
- CLK: field out → field in

Organ 18 `muhl_byzq` is already on main. Do not remint it. Slack, ntfy, and
Pages are projections of this file, not a second log. titan: **NOT_WRITTEN**.

## Receipt commands

```
python3 muhl/desktop/MUHL_SUBZERO_ARCHETYPES/test_muhl_fab_stig.py
python3 muhl/desktop/MUHL_SUBZERO_ARCHETYPES/muhl_fab_stig.py --dry
```

`--dry` is structural only. It does not walk the organ. titan.gguf is not opened.
The git file is an excerpt: copies do not run. MOVE into titan is an owner-PC step.

Do not remint. Do not rebake the twelve, alife, chimeras, clacker, hpc_fabric,
or organs 1/7/11/13/15/16/17/18/19.
