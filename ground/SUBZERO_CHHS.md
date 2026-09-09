# SUBZERO_CHHS — organ 21 fabricated 2026-08-24

Read-only receipt. Construction from PLUMB 3/3 (`muhl_chimera_hopf_sdmk` / `MUHLCHHS`).
Standalone `.mno`. No titan write. Organs 1–20 untouched.

Authority for the live twelve remains `titan_circuits.json` + `titan.gguf` (see
`SUBZERO_CENSUS.md`). This file is the public-tree measurement of organ 21 only.

## Verdict

| name | where | magic | n_gate | n_wires | n_in | n_out | depth | len |
|---|---|---|---:|---:|---:|---:|---:|---:|
| `muhl_chimera_hopf_sdmk` | `excerpts/20260823/muhl_chimera_hopf_sdmk.mno` @0 | `MUHLCHHS` | 22 | 24 | 11 | 11 | 2 | 690 |

sha256 `c8301c2345e67dfe6f9b1f91127fab896224347a72ba8ac044313275fe948ee7`

Header is the live MHA layout: 8-char magic, then LE `n_gate, n_wires, n_in, n_out, depth`.
Records: `<BQQQ>` stride 25. One unique out per gate. Eleven NAND-NAND buffers.
Local out address **is** local in address. MOVE dests stay in the sidecar.

## Construction (the count)

- 11 location-hit lanes × NAND-NAND buffer (2 g) = 22
- depth 2
- dest FROM FILE: sdmk location-hit outs `1188,1963,…,8938`
- dest FROM FILE: hopf state-seed ins `542..552`
- Chimera writes fresh local outs. Does not second-write hopf.

## Receipt commands

```
python3 muhl/desktop/MUHL_SUBZERO_ARCHETYPES/test_muhl_fab_chimera_hopf_sdmk.py
python3 muhl/desktop/MUHL_SUBZERO_ARCHETYPES/muhl_fab_chimera_hopf_sdmk.py --dry
```

`--dry` is structural only. It does not walk the organ. titan.gguf is not opened.
The git file is an excerpt: copies do not run. MOVE into titan is an owner-PC step.

Do not remint. Do not rebake organs 1–20, the twelve, alife, clacker, or hpc_fabric.
Organs 22–31 stay NOT_LANDED.

## Live cash

Verified product pages only — no invented Stripe links.

- [$29 Autopsy checkout](../agent-rescue.html) — one failed coding-agent run
- [$199 dealer diagnostic](../dealer-service-lead-rescue.html)
- [$199 referral diagnostic](../referral-intake-completeness.html)
- [$199 repair diagnostic](../repair-booking-preflight.html)
- [$199 plant diagnostic](../plant-downtime-handoff.html)

Shelf: [tools-cash.html](../tools-cash.html). Catalog: [commerce.html](../commerce.html). Cite spy-ground-batch-live-cash-20260909-08 — do not remint.

## Contest product (titanmcp)

Live judge pad (≠ Commons Shared Pad / ≠ Commons `/mcp`): https://webmcp-pad.vercel.app/ — **titanmcp 1.4.5**, 24 tools, Agent Resources, `syncConsents`. Board: [titanmcp.html](../titanmcp.html). Cite Latch Pad KEEP. Submit/YouTube wait Bryce exact go.
