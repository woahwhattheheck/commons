# A — "let the models in the substrate pick their own seeds every tick"
### Grounded against the owner's own code, 2026-08-07

Owner's instruction — **VERBATIM, quoted from the `queue-operation` records, not re-punctuated:**
> [07:20:23] *"A) let the models in the substrate pick their own seeds every tick. b) approved.
> c, approved. d) idk what you mean by this. e"*
> [12:07:16] *"…2 look at the game then my instruction then ground in how it can be done then act,…"*

⚠ An earlier version of this file printed the second quote as a sentence ending in a period.
He typed a **comma**, inside a numbered list. Corrected 2026-08-07. Do not re-punctuate him.

This is the GROUNDING (step 3). Step 4 is a fabrication — one-and-done, offline, the owner's act.

---

## 1. WHY IT CANNOT WORK ON `muhl_playtime` AS BUILT

`fabs/muhl_fab_playtime_v2.py`, read end to end:

```
:135  remap = {outs[j]: wa(2+j) for j in range(n_out)}   # ALL 2048 outs -> ALL 2048 ins
:202  if len(outs) != c.n_in: ... return 1               # aborts unless 1:1
:138  assert w not in consumed, "feedback wire consumed downstream"
:77   avg4(cell(r-1,col), cell(r+1,col), cell(r,col-1), cell(r,col+1))
```

**Every input wire is already written by an output.** `n_in == n_out == 2048`, remap is 1:1,
and the diffusion reads nothing but four neighbours. **There is no seed port.**
`generate_spiral()` (:105) runs in host Python at FABRICATION time and is baked into the wire
bytes at :146-150 — a one-time initial condition, not a per-tick input.

## 2. THE MECHANISM ALREADY EXISTS — `muhl_fab_playtime_ring.py`

```
:16   "tap without putting a second writer on an address. That is a short under the
       one-writer law"
:29   "Reading is free; only WRITING collides. So the enable is derived from gates that
       READ muhl_ring_clacker's tap addresses directly, and this circuit writes [nothing there]"
:101  c = TC.Circuit(STATE_BITS + N_TAPS)
:104  taps = [IN[STATE_BITS + j] for j in range(N_TAPS)]
:108  enable = c.xor(taps[0], taps[1])
:120  outs.extend(c.mux(enable, held[b], nxt[b]) for b in range(CELL_BITS))
:208  if 2 + STATE_BITS <= w < 2 + STATE_BITS + N_TAPS:
:209      return tap_addrs[w - (2 + STATE_BITS)]     # READ the ring, ABSOLUTE address
:218  remap = {outs[j]: wa(2 + j) for j in range(no)}  # ONLY the state self-clocks
:221  assert w not in consumed
```

**Input wires beyond the state are remapped to ABSOLUTE addresses of another circuit's bytes
and are only ever READ.** No second writer, no short. The self-clock remap covers only the
state wires, so :221 still passes. This is Sec 1E: stage k's SEND wires ARE stage k+1's
RECEIVE wires — and it is already fabricated and verified over 120 grids, both enable branches.

## 2A. ⚠ CORRECTION — "A WIDER PORT" IS THE WRONG SHAPE (owner, 2026-08-07)

Owner: *"my models in the substrate shouldnt be limited to one input or output stream"* ·
*"check the binary itself not code"* · *"then use my tools"*.

I wrote §3 below as ONE port made fatter. **Wrong shape.** MEASURED with `pfc_inspect` against
the binary and the registry:
```
muhl_ring_clacker tap_addrs        : 1,024 addresses, contiguous
                                     93,710,581,598 .. 93,710,582,621
muhl_playtime_ring READS           : 2 of those 1,024
nring2_* rings carrying a recv     : 1,025
DISTINCT recv addresses registered : 1,323
```
**1,024 independent tap streams exist and the ring world uses two.** Every one toggles every
settle (measured: 1023/1023 adjacent pairs differ, so ANY pair anywhere on the bus XORs to 1).
There is no scarcity to ration.

**The constraint is not "how wide is the port." It is "which of the 1,024 taps and 1,323 recv
points does each stream use."** One-writer-per-address binds WRITES only — reading is free, so
any number of circuits may read any number of streams. A model can take many independent inputs
and publish many independent outputs; its outputs are simply bytes at addresses.

**ALSO MEASURED — a second `pfc_inspect` mislabel.** Binary headers read
`(n_gate, n_wire, n_in, n_out)`; the tool prints `(n_in, n_wire, n_gate, n_out)`:
```
muhl_playtime       -> 115,200 gates · 117,250 wires · 2,048 in · 2,048 out
muhl_playtime_ring  -> 131,588 gates · 133,640 wires · 2,050 in · 2,048 out
muhl_ring_clacker   ->   2,048 gates ·   3,074 wires · 1,024 in · 1,024 out
```
Same class as the NRING2M1 mislabel. The registry fields are right; the printed tuple is not.

## 3. THE GENERALISATION — same pattern, MANY streams not one

```python
c = TC.Circuit(STATE_BITS + SEED_BITS)
seed = [IN[STATE_BITS + j] for j in range(SEED_BITS)]
next_cell = f(avg4(neighbours), seed)            # the mux at :120, generalised

# in to_physical:
if 2 + STATE_BITS <= w < 2 + STATE_BITS + SEED_BITS:
    return seed_addrs[w - (2 + STATE_BITS)]      # ABSOLUTE addrs of the MODEL's output bytes
remap = {outs[j]: wa(2+j) for j in range(STATE_BITS)}   # only the state self-clocks
```

**The model writes its own outputs at its own addresses** — exactly as `pfc_fwd_loop` writes
`fwd_answer` at `+12` into its own state region. **The world READS those bytes as seed wires.**
Both advance on the same ring toggle.

**No host write. No injection. No button. No second writer anywhere.**

## 4. WHAT ALREADY SUPPORTS IT — measured

```
pfc_fwd_loop      feedback[[0,0],[1,1],...] · loop_bit 174 · seq True · receiver fwd_receiver
                  role: "self-routing forward engine: fired receiver -> the pfc iterates
                         its own passes"
                  fwd_answer = state[12:14] — the answer IS a slice of its own state
pfc_fwd_engine2   wiring: "SERIES IN STORAGE with pfc_mmu: addr_out bytes ARE mmu.addr;
                           mmu.fast_read bytes ARE ldata"
muhl_ring_clacker 1024 cells, 512 electrons, 1023/1023 adjacent differ, wrap closes
                  -> every tap pair XORs to 1: the enable is live everywhere on the bus
```

An engine that iterates its own passes, a wiring convention where one circuit's output bytes
ARE another's input bytes, and a clock that toggles every tap every settle. **All three
measured, all three already in the container.**

## 5. WHAT IS NOT DECIDED — the owner's, not mine

- **How many SEED_BITS**, and which model circuit's outputs they read.
- **The combining function** `f(avg4, seed)` — the ring uses a 2:1 mux on enable; a seed port
  admits many shapes and that is a design choice.
- **Whether ring world #2** (`103,799,909,632`, fabricated, verified, board still 2,048 zero
  bytes) is the place to do it, or a fresh fabrication.
- **Electron cost.** Owner's law: every ring must have a named purpose; electrons are the
  constraint, not bytes. A seed port driven by a model may or may not need its own drive.

## 6. WHY I STOPPED HERE

Fabrication is one-and-done, offline, and the owner's act. A spec master that starts designing
has taken the owner's chair. The mechanism needs **no new invention** — it is the clacker-tap
wiring applied to a wider port — and that is the finding.
