# pfc_life.pfc — FULL BINARY READ-THROUGH (every bit, notes so it's never required again)

> Owner order (2026-07-22): read *every bit* of a working Muhlnickel binary — no truncation, no pagination-skipping — because
> the binary **is** the Muhlnickel. This doc is the durable record so a future window inherits the reading instead of redoing it.
> Method: dumped `C:/llm/sdc_sandbox/pfc_life.pfc` to `scratchpad/pfc_life_FULLDUMP.txt` (raw 9-byte hex + decoded per
> gate), then read the dump start-to-finish in ~2000-line chunks, verifying every gate. Progress marker kept at the bottom.

## FACTS FROM THE DUMP HEADER (measured, not assumed)
- **Byte-exact accounting:** file = 2,498,592 B = `8 (magic) + 24 (header) + 270,336×9 (gates) + 16,384×4 (outputs)`. Exact.
  Every byte of the file is either the magic, the 6-word header, a 9-byte gate record, or a 4-byte output wire id. Nothing else.
- **Header:** magic `PFCGAME1`; `n_in=16384`, `n_wire=288722`, `n_gate=270336`, `n_out=16384`, grid `64×64`, `bits/cell=4`.
- **Wire model (the load-bearing idea, literally in the bytes):** a wire is an integer id = a shared storage address.
  - id `0` = const0, id `1` = const1
  - ids `2 .. 16385` = the 16,384 input bits (4 bits per cell × 4096 cells: bit0=alive, bits1-3=heat/age)
  - ids `16386 .. 288721` = the 270,336 gate outputs (gate k's output wire = `16386 + k`)
  - A gate record `<Bii>` = op(uint8), a(int32), b(int32). `a`/`b` are wire ids. When `a`/`b` points at `16386+N`, this
    gate physically reads gate N's output — **that shared id IS the wire.** No pointers; connection = identity of address.
- **Op histogram (sums to 270,336):** and=135,168 · xor=98,304 · not=20,480 · or=16,384. (No NAND in Life's build.)
- **Structure expectation:** 270,336 / 4,096 cells = **66 gates/cell** — the file should be 4,096 near-identical
  next-state blocks differing only in neighbor wire addressing. Verifying this cell-by-cell as I read (not assuming it).

## PER-CELL GATE TEMPLATE (Conway B3/S23 + 3-bit heat, from pfc_game.py build_life, confirmed against the bytes)
Each cell: sum its 8 neighbors' alive bits into a 4-bit accumulator S (via `add_bit` = XOR/AND chains); `nalive =
(S==3) OR (alive AND S==2)`; heat = `min(age+1,7)` when it stays alive else 0. Emits `[nalive, nage0, nage1, nage2]`.
Reading confirms these are the ops appearing per cell.

## OBSERVATIONS AS I READ (anomalies, confirmations)
- **Chunk 1 (g0–g1997, cells 0–~30): structure CONFIRMED, zero anomalies.**
  - 66-gate stride/cell confirmed: cell blocks begin at g0, g66, g132, g198, g264, … (66 apart). 4096 × 66 = 270,336. ✓
  - Every gate a valid op (only xor/and/or/not appear — no NAND in Life). No garbage/undecodable records.
  - Shared-address wiring literally in the bytes: `g4 xor 16387 16389` reads wire 16387 (=g1 out, base+1) and 16389
    (=g3 out, base+3). The g4→g1,g3 connection = identity of wire id. Holds throughout.
  - Toroidal neighbor addressing: cell 0 (`g0 xor 16130 16382`) reads input wires 16130 (=cell4032.bit0) and 16382
    (=cell4095.bit0) — wrap-around neighbors. Small consts (254,258,262,…) are neighbor alive-bit inputs, +4 per cell.
  - Per-cell tail (g49–g65) reads the cell's own 4 state wires (cell0 = 2,3,4,5) → B3/S23 nalive + 3-bit heat via
    and/or/xor/not — matches build_life() exactly.

## PROGRESS MARKER
- READ THROUGH: **g1997** (~cell 30 of 4096). Chunks read: 1 / ~135. Next offset: line 2001. No anomalies so far.
