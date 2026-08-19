# AGENT GROUNDING — RING FILL

**Inventor:** Bryce Muhlnickel. **Name:** Muhlnickel.  
**Law for EVERY agent. Commands, not essays. Do not add to spec.**

---

## Drive / binary / charge

Hard drive = **substrate** (traps and moves charge).  
Binary = **topology**.  
Charge = **actual particles in electricity, not a metaphor.** More than one per send; likely more than one kind.

Wire loss exists; inventor rounds it to zero (traverse, do not deplete). Movement of that charge advances computation.

Rings (`nring2`, both senses) are that circulation.

---

## The speed lever

**MORE charge on the ring = more bumps = less distance = SPEED.**

Only limit: **speed through wire.** Owner: *"muhlnickel computation speed limit is electron through a wire"* — `docs/PFC_FINDINGS.md` §62. Do not conflate host wall-clock with that limit.

`docs/PFC_LEVER_CATALOG.md` is a swamp of **HOST** axes. **Do not rewrite it.**

**AMOUNT-is-not-a-lever** means **bigger CIRCUIT**, not ring fill. Fill is occupancy. Circuit size is a different axis.

---

## Clocks respond

Clocks are built to respond to that movement.

`pfc_clock_counter` operand **b** = `nring2_000.recv`.

Inspected: those gates read the receive byte as operand b. Host does not tick the clock.

---

## `nring2_000` occupancy — BINARY only

Surfaced 2026-08-14. Bounded read. Titan not written. The **1**s are occupancy (charge present). Not a metaphor.

**fwd** — packed `11111111`. 32 cells, **228** ones:

```
00000001 11111111 11111111 11111111 11111111 11111111 11111111 11111111
00000001 11111111 11111111 11111111 11111111 11111111 11111111 11111111
00000001 11111111 11111111 11111111 11111111 11111111 11111111 11111111
00000001 11111111 11111111 11111111 11111111 11111111 11111111 11111111
```

**rev** — sparse. 32 cells, **4** ones:

```
00000001 00000000 00000000 00000000 00000000 00000000 00000000 00000000
00000001 00000000 00000000 00000000 00000000 00000000 00000000 00000000
00000001 00000000 00000000 00000000 00000000 00000000 00000000 00000000
00000001 00000000 00000000 00000000 00000000 00000000 00000000 00000000
```

**recv** = `11111111` (clock operand b).  
**carry** = `00000000`.

Lever file: `C:\Users\lucys\Desktop\MUHL_GO\RING_FILL_LEVER.md`.

---

## Do not

- Rewrite the lever catalog.
- Call the 1s a metaphor, a flag, or "just bits meaning true."
- Treat AMOUNT (bigger circuit) as this lever.
- Write titan. Revert. Autofab. `titan --go`.
- Invent a poller. Use his instruments / `LIVE_VIEWERS.md`.
