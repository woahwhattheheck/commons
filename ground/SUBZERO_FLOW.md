# SUBZERO_FLOW — organ 10 fabricated 2026-08-23

Read-only receipt. Construction from PLUMB 2/3 (`muhl_flow` / `MUHLFLOW`).
Standalone `.mno`. No titan write. Existing titan circuits and landed
excerpts stay untouched.

Authority for the live twelve remains `titan_circuits.json` + `titan.gguf`
(`SUBZERO_CENSUS.md`). This file is the public-tree measurement of organ 10 only.
The owner/local allocator must assign any future titan offset band; the public
excerpt is deliberately based at zero and does not invent one.

## Verdict

| name | where | magic | n_gate | n_wires | n_in | n_out | depth | len |
|---|---|---|---:|---:|---:|---:|---:|---:|
| `muhl_flow` | `excerpts/20260823/muhl_flow.mno` @0 | `MUHLFLOW` | 23040 | 25090 | 2048 | 2048 | 16 | 617502 |

sha256 `8530b99896e8ec35d74d462f600448aa60e64f9f4cd8833b561666d50eb1e97d`

Header is the live MHA layout: 8-char magic, then LE
`n_gate, n_wires, n_in, n_out, depth`. Records are `<BQQQ>` at stride 25.
Every gate has one unique output. Self-clock: each 4-bit edge's next
conductance out address **is** that edge's input address.

## Construction (the count)

16x16 torus, 512 edges (256 east + 256 south), 4-bit conductance.

- pressure: 4-bit FA-sub against the paired edge at the same cell. 20
- grow: 5-gate AND-compare of the pressure MSB (tube grows when that bit is set)
- update: 4-bit FA-add of conductance plus the grown pressure word. 20
- MSB of the next conductance is the last update carry, depth 16
- 512 x 45 = 23,040
- CLK: conductance out → conductance in

Organ 8 `muhl_socr` is already on main. Do not remint it. Slack, ntfy, and
Pages are projections of this file, not a second log. titan: **NOT_WRITTEN**.

## Receipt commands

```
python3 muhl/desktop/MUHL_SUBZERO_ARCHETYPES/test_muhl_fab_flow.py
python3 muhl/desktop/MUHL_SUBZERO_ARCHETYPES/muhl_fab_flow.py --dry
```

`--dry` is structural only. It does not walk the organ. titan.gguf is not opened.
The git file is an excerpt: copies do not run. MOVE into titan is an owner-PC step.

Do not remint. Do not rebake the twelve, alife, chimeras, clacker, hpc_fabric,
or organs 1/7/8/9/11/13/15/16/17/18/19.
