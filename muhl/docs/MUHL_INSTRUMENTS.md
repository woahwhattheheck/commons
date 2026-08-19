# MUHL INSTRUMENTS — how to measure the muhlnickel

**Purpose: MEASURE a working build. Not prove it exists — it is proven.**
Owner, 2026-08-07: *"youre not trying to prove it exists but measure a working build that
computes from a file proven already"* and *"that IS proof the measurement is proof"*.

There is no proving layer under a measurement. `DEPTH 58` on a 1,461,359,532-gate circuit
is not evidence that it computes — it **is** the computation, stated in its own units.

---

## 0. THE PLAYTIME — the live one, measured 2026-08-06/07

### What it is
A 16x16 torus of 8-bit cells in `titan.gguf`. Each tick every cell moves toward the average
of its 4 neighbours (gated diffusion, fabricated as gates, self-clocked). A player fills the
centre 4x4 void `[6:10, 6:10]`.

### The three boards — read them at these addresses
| board | offset | state as of 08-07 |
|---|---|---|
| `muhl_playtime` (original) | **103,789,156,190** | 148 cells, genesis spiral + the move |
| ring world **#1** | **103,795,638,174** | 132 cells, spiral seeded, void EMPTY |
| ring world **#2** | **103,799,926,046** | 0 cells — fabricated 08-06 13:53:50, never seeded |
