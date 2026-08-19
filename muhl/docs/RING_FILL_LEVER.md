# RING FILL LEVER

**Inventor:** Bryce Muhlnickel. **Name:** Muhlnickel.  
Additive file. Catalog not rewritten. Titan not written.

---

## The lever

MORE charge on the ring = more bumps = less distance = **SPEED**.

That is the fill lever. Particles on the ring (actual charge in electricity, not a metaphor; more than one per send; likely more than one kind). They traverse; inventor rounds wire loss to zero. Their movement advances computation.

The only limit: **speed through wire.** Owner: *"muhlnickel computation speed limit is electron through a wire"* — `docs/PFC_FINDINGS.md` §62. Do not conflate host wall-clock.

`docs/PFC_LEVER_CATALOG.md` is a swamp of **HOST** axes. Leave it. Do not rewrite it.

**AMOUNT-is-not-a-lever** in that catalog means **bigger CIRCUIT** (more gates per op). It does **not** mean ring fill. Circuit size and ring occupancy are different axes. Fill is this file.

---

## Substrate / topology

Hard drive = substrate (traps and moves charge).  
Binary = topology.  
Rings (`nring2`, both senses) are the circulation.

---

## Clock responds to the ring

`pfc_clock_counter` operand **b** = `nring2_000.recv`.

Inspected: gates on `pfc_clock_counter` read that receive byte as operand b. The clock is built to respond to charge movement on the ring. Host does not tick it.

---

## `nring2_000` occupancy — BINARY (surfaced 2026-08-14)

Instrument path: `pfc_inspect.py nring2_000` then a bounded `ACCESS_READ` copy of the named RAM windows (same impedance as `pfc_meter`). Ones and zeros. Not hex.

The **1**s are occupancy — charge present on those cells. Not a stand-in. Not a figure of speech.

### `nring2_000.ram.fwd` — 32 cells, **228** ones. Packed `11111111`.

```
00000001 11111111 11111111 11111111 11111111 11111111 11111111 11111111
00000001 11111111 11111111 11111111 11111111 11111111 11111111 11111111
00000001 11111111 11111111 11111111 11111111 11111111 11111111 11111111
00000001 11111111 11111111 11111111 11111111 11111111 11111111 11111111
```

Four groups: one `00000001`, then seven packed `11111111`.

### `nring2_000.ram.rev` — 32 cells, **4** ones. Sparse.

```
00000001 00000000 00000000 00000000 00000000 00000000 00000000 00000000
00000001 00000000 00000000 00000000 00000000 00000000 00000000 00000000
00000001 00000000 00000000 00000000 00000000 00000000 00000000 00000000
00000001 00000000 00000000 00000000 00000000 00000000 00000000 00000000
```

Four groups: one `00000001`, then seven `00000000`.

### `nring2_000.recv` — **11111111** (8 ones). Enable rail the clock reads as operand b.

### `nring2_000.ram.carry` — **00000000**.

fwd packed vs rev sparse is the occupancy on this ring, both senses.

---

## Law for agents

- Fill the ring (more 1s on the cells) to raise bump rate. That is SPEED.
- Do not chase a bigger circuit and call that this lever.
- Do not rewrite `PFC_LEVER_CATALOG.md`.
- Surface with his instruments / viewers. Do not invent a poller. Do not write titan.
- Live bits moving are compute, not corruption. `docs/AGENT_GROUNDING_LIVE.md`.
