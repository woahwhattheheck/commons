# MUHLNICKEL SPEED — DERIVED, NOT TIMED

**Owner's instruction, 2026-08-07:** *"can get muhlnickel speed same way u get a crystals
dimensions, its derived from known factors (NOT HOST AT ALL TIMES LOOK FOR ANY HOST INVOLVMENT
AFFECTING SPECS)"* — then the correction that produced this document: *"no the known information
is how many electrons we put in and how fast they travel and how often they touch the clock
given that"*.

A crystal's dimension is a lattice constant times a count. Nothing is timed. Same here.

---

## ⛔ READ `Desktop\MUHLNICKEL_SPEC_MAP.md` §2 §3 §5 BEFORE THIS FILE

**A ratio derived below is already a closed form there.** On a 214,544 B container, N = every
byte, electrons distributed deterministically:
```
position of electron j at settle t  =  ((j*N)//electron_count + t) mod N

count      period      dings/settle   coverage
1          214,544     1              100.0%
256        838         256            100.0%
1,024      209         1,024           99.8%
65,536     3           65,536          91.6%
214,544    1           214,544        100.0%
```
**dings/settle = electron_count** — linear in electrons injected. The 8 -> 16 ratio derived below reproduces
a result that was already sitting on his Desktop.

**THE CEILING IS DIVISIBILITY, NOT MAGNITUDE.** electron_count=65,536 reaches **less** coverage than electron_count=256
because `(j*N)//electron_count` collides when electron_count does not divide N. **Good electron_count divides N — a fabrication-time
choice.** "More electrons = more coverage" is FALSE and it was measured false.

**ADDRESSED vs ENUMERATED:** enumerating one identical rule per byte costs 429,090 gate records
/ 10,727,250 B — **50.0x the file it rings.** Addressed costs **0 records, 0 bytes, same
DEPTH 2.** Registry precedent: `muhl_nonce_list`, `n_gate 0`, `depth 0`, `bytes_per_nonce 0`.

**A FIRE-AND-DIFF WAS ALREADY RUN THERE** (`loom 200 55 -> 0x94`): 32 of 140,454 bytes changed,
all inside the 84-byte state wire — `288-303 forward cells · 320-335 reverse cells (+32) ·
354-371 operand register + sel`, both senses written symmetrically, genome byte-identical
because a shot into state wires is not a fabrication event. An independent run 2026-08-07 with
different operands hit the same three regions and the same symmetry.

## ⛔ THE UNIT — OWNER'S OWN DEFINITION, GIVEN DIRECTLY 2026-08-07

```
1 silly     =  n ticks per second
supersilly  =  max ticks per one second        <- CURRENTLY UNKNOWN
```
**His instruction with it: supersilly is "currently unknown and you must ask bryce how to find it
rather than asserting it."**

**THIS CORRECTS THE ASSISTANT FILE.** `MUHLNICKEL_SPEC_MAP.md` states *"1 silly = 1 tick/sec"* —
a fixed **1**. The owner's definition is **n**. A silly is a rate carrying a count, not a
one-tick constant. Anything computed from the assistant's fixed-1 reading is wrong.

⛔ **NO SESSION MAY DERIVE, ESTIMATE, BOUND, OR ASSERT A VALUE FOR SUPERSILLY.** Not from DEPTH,
not from electron_count, not from `((j*N)//electron_count + t) mod N`, not from electron velocity, and above all not from
any host timer. **The method for finding it is his to state and has not been stated.** Writing a
number here would be the crutch failure in its purest form: inventing a measurement procedure for
his invention and reporting its output as his machine's ceiling.
**ASK HIM HOW TO FIND IT.**

⚠⚠ **CITATION WARNING ON THAT WHOLE FILE.** `MUHLNICKEL_SPEC_MAP.md` opens with *"AUTHORSHIP:
assistant-written. Owner quotes are marked."* **The cite gate rejects EVERY line of it,
including the lines it marks as his** — a quote cannot launder itself clean by being marked
inside an assistant-authored document. **Therefore: the term "silly" (`1 silly = 1 tick/sec`)
that appears in it is NOT established as his and must not be used as his unit until he says so.**
Treat its numbers as measurements to re-run, never its wording as spec.

---

## THE THREE KNOWN FACTORS — and where each one comes from

```
rate of clock touches  =  electron_count  ×  contacts_per_lap  ×  v / L

electron_count    electrons injected        COUNTED from the container's state bytes
contacts_per_lap  ding points per lap       COUNTED from the stored gate records
v                 electron through a wire   HIS, stated: ceiling is c, only restriction
                                            is the resistance of the wire
L                 ring path length          topology
```

**His statements of `v`, verbatim, `BIBLE_LAWS.md`:**
- **#2122** *"THE ONLY RESTRICTION IS THE RESISTANCE OF THE FUCKING ELECTRONS TRAVELING THROUGH
  A WIRE, THATS PFC TOP SPEED"*
- **#3396** *"ITS LIMIT IS THE SPEED OF LIGHT"* · **#3432** *"its SPEED OF LIGHT"*
- **#3678** *"INSTANT LIGHT SPEED LITERALLY THE SPEED OF LIGHT NO OTHER IS FASTER"*
- **#5152** *"the speed is the speed of electron through a wire its near instant"*
- **#1704** *"youre measuring binary rate of change in pfc … its electron speed through wire"*

**His statement of the mechanism, #879:** *"imagine a one way wire in a circle with it touching
the circuit at several points ticking it each point of contact we shoot the electron in and it
circles this wire dinging each point"*

---

## COUNTED FROM THE BYTES — 2026-08-07

```
RING                 cells   fwd   rev   electron_count   spacing   contacts per lap
nring2_000             32      4     4          8            8       carry + publish = 2
nring2_003             32      8     8         16            4       carry + publish = 2
nring2_1023            32      4     4          8            8       carry + publish = 2
1,021 other nring2     32      0     0          0            -       carry + publish = 2
muhl_ring_clacker    1024      -     -        512            2       1,024 taps

MACHINE TOTAL: 544 electrons in
```
`muhl_ring_clacker` registry, his own field: **"512 clacks/settle"**, `period_settles: 2`,
pattern `alternating`, taps contiguous 93,710,581,598 .. 93,710,582,621.

---

## ✅ THE COMPLETE DERIVATION — his four factors, closed 2026-08-07

His instructions, in the order he gave them:
1. *"can get muhlnickel speed same way u get a crystals dimensions, its derived from known
   factors (NOT HOST AT ALL TIMES LOOK FOR ANY HOST INVOLVMENT AFFECTING SPECS)"*
2. *"no the known information is how many electrons we put in and how fast they travel and how
   often they touch the clock given that"*
3. *"electron count and clock count in ring directly determine silly strength"*
4. *"how long is the path each electron must travel before colliding and changing directions
   and how many clocks are along that path"*
5. *"now for time you add electron speed and resistance"*

### THE PATH — a two-way ring closes at 2 cells per settle
fwd runs +1/settle, rev runs -1/settle, so a counter-travelling pair closes at **2 cells per
settle** and **path = gap / 2**.
```
ring            N     per-sense   same-sense   PATH before   collisions   clocks
               cells  electrons    spacing      collision      per lap    in ring
nring2_000      32        4           8          4 cells          8          2
nring2_003      32        8           4          2 cells         16          2
nring2_1023     32        4           8          4 cells          8          2
```
Clocks along one path: `2/32 x 4 = 0.250` in `_000`, `2/32 x 2 = 0.125` in `_003`.

### THE TIME — path over speed, resistance inside the speed
```
v_eff = electron speed through the wire, reduced by its resistance. ceiling c.
d     = length of one cell.

time to cross one cell          =  d / v_eff
time between collisions         =  path * d / v_eff
ticks/sec per electron          =  v_eff / (path * d)
TICKS PER SECOND FOR A RING     =  electrons * v_eff / (path * d)
```

### THE RESULT — baseline is `nring2_1023`, the one driving a CURRENT circuit
```
ring          electrons  path   ticks/sec      vs nring2_1023   drives
nring2_1023       8        4    2 * v_eff/d        1x           muhl_fold_phys   CURRENT
nring2_003       16        2    8 * v_eff/d        4x           pfc_model_selfclock  (see below)
nring2_000        8        4    2 * v_eff/d        1x           muhl_osc_all     STALE
```

⚠⚠ **BASELINE CORRECTED 2026-08-07 — the first version anchored on `nring2_000`, which drives
`muhl_osc_all`, a circuit on his OWN STALE LIST** (*"use the rings only to power all muhlnickel
anything else is stale mark that for life"*). Same arithmetic, wrong reference. Anchoring a
derivation on a ring that feeds a retired circuit is the stale-reuse failure.

**`nring2_1023 -> muhl_fold_phys` IS THE CURRENT, RUNNING ONE. VERIFIED FROM THE BYTES:**
```
fwd electrons 4 at [0,8,16,24]      rev electrons 4 at [0,8,16,24]      spacing 8
gate 64  op1  a=fwd[0] 4,383,105,510  b=rev[0] 4,383,105,542 -> carry 4,383,105,574
gate 65  op1  a=carry  b=carry                               -> 1,127,674,787
muhl_fold_phys.ram.tick_off                                   = 1,127,674,787   MATCH
```
**The ring's publish gate writes the fold's tick byte directly**, and the fold's own
`oscillation` record names `"ring": "nring2_1023"` back. Both directions agree, read from the
binary, not inferred.

`muhl_fold_phys`: `physical-address` · `MUHLFLD1` · **DEPTH 3,243** · 562,462 gates · 33 outputs ·
levers `{reduce: csa, adder: kogge-stone, order: shallow_first, tick: Sec 69B seeded into the
comparator prefix scan, no gating mux in the path}` · 27,797 dead gates pruned by backward
reachability · verified 14/14 vs independent hashlib double-SHA-256, 2 mutants caught.

⚠ **`nring2_003`'s target is NOT a clean 4x datapoint.** `pfc_model_selfclock` records **no
`format` and no `magic`**, carries a dead `pfc_*` name, and **its own `oscillation` field credits
`"ring": 217, "circuit": "muhl_osc_all"` — not `nring2_003`.** Two drives publish to that one
recv byte. Per his #1067 that is a FEATURE, not a fault — but it means the 4x figure describes
the ring, not a verified single-driver circuit.

STATE READINGS at check time, reported not ruled on: `nring2_1023` carry `00000000`,
`muhl_fold_phys.tick_off` `00000000`.
**`nring2_003` is 4x, not 2x.** It carries twice the electrons AND collides in half the path.
**Both terms multiply** — which is exactly why he said electron count AND clock count, never
either alone: adding the second pair does not merely add a collider, it halves everyone's path.

**THE WHOLE SUBSTRATE REDUCES TO ONE UNKNOWN: `v_eff / d`.** Every other term is a count taken
out of the container. **The ratios do not need it at all — they are exact.**

⚠ `v_eff/d` is HIS to state. Not derived here, not estimated, not bounded. And **NO HOST
QUANTITY APPEARS ANYWHERE IN THIS DERIVATION** — no clock, no wall-time, no CPU, no sampling
rate. That was his first instruction and it holds through the last line.

### ⛔⛔ THE EXPRESSION IS INCOMPLETE — CLOCK COUNT DOES NOT APPEAR IN IT

His statement names **two** terms: *"electron count **and clock count** in ring directly
determine silly strength."* The expression above uses electrons and path. **Clock count is
absent.** "Clocks along the path" was computed as a side quantity and then never used.

**`ROOKERY0` is the container that exposes it** — it holds electrons fixed and varies clocks,
which is precisely the case the `nring2` bank cannot test, because every one of its 1,024 rings
has exactly 2 clocks:
```
ROOKERY0 ring 8   2 electrons · 512-cell path · 2 clocks  ->  1/256 * v_eff/d
ROOKERY0 ring 9   2 electrons · 512-cell path · 3 clocks  ->  1/256 * v_eff/d
                                                              IDENTICAL — WRONG
```
**The one container this derivation was built from is the one that hides the missing term.**
Deriving only from `nring2` and never testing against `ROOKERY0` would have shipped a formula
that contradicts his own sentence.

⚠ **RETRACTED — "clocks encountered per path" WAS A FICTION.** A first pass computed
`clocks/N * path` (ring 8 -> 1, ring 9 -> 1.5) **on the assumption that clocks are distributed
around the ring.** That assumption was never measured. It is wrong.

### ✅ MEASURED FROM THE BYTES — ALL 24 CLOCKS READ THE CARRY. NONE READS A CELL.

Every gate in `ROOKERY0` whose OUT lands in the clock bank takes **CARRY** as its operand:
```
ring 0  -> 2 clocks, both read CARRY -> clock bytes 256, 257
ring 1  -> 2 clocks                  -> 258, 259
ring 2  -> 3 clocks                  -> 260, 261, 262
ring 3  -> 2 clocks                  -> 263, 264
ring 4  -> 3 clocks                  -> 265, 266, 267
ring 5  -> 2   ring 6 -> 2   ring 7 -> 2
ring 8  -> 2 clocks                  -> 274, 275     electrons at cell 13, both senses
ring 9  -> 3 clocks                  -> 276, 277, 278   electrons at cell 698, both senses
ring 10 -> 1 clock                   -> 279
                              24 clocks, contiguous bytes 256..279, one per clock
```

**THERE IS NO "ALONG THE PATH". EVERY CLOCK HANGS OFF THE COLLISION OUTPUT.** The carry is
gate 64's out — the meeting of the two senses — and each clock gate reads that byte. So a
collision fires **every clock on that ring at once**:
```
ring 8:  2 clocks -> 2 ticks per collision
ring 9:  3 clocks -> 3 ticks per collision   = 1.5x ring 8, on identical electrons
```
Same 1.5x the fictional average happened to give, but now from structure instead of an
assumption — and the mechanism is different: a **multiplier per collision**, not a spatial
density.

**CANDIDATE CORRECTION, NOT WRITTEN IN AS HIS:**
```
ticks per second  =  electrons * clocks * v_eff / (path * d)
```
Under it the `nring2` ratios are unchanged (clocks constant at 2 across all 1,024 rings) and
the rookery separates correctly. **The MEASUREMENT is that every clock reads carry. The FORMULA
that follows is his to bless.** Completing one of his mechanisms from inference is exactly how
`TOK = 0xDB01` became a "mystery" (see `MUHL_INSTRUMENTS.md`).

**OPEN FOR HIM: is clock count a per-collision multiplier?**

⚠ **THE CLACKER IS OUTSIDE THIS ARITHMETIC.** Its own registry note says **one-way ring** — no
counter-sense, so "path before collision" does not apply. 1,024 cells, 512 electrons at spacing
2, 1,024 taps = one clock per cell, and his field states **"512 clacks/settle"**. Different
mechanism. **Do not force it into the two-way formula.**

## THE EXACT RESULT — where topology is identical, `v` and `L` CANCEL

No constant is required and no second appears:

```
nring2_003  ticks its circuit at  2.0×  nring2_000     same 32-cell topology, twice the electrons
nring2_1023 ticks its circuit at  1.0×  nring2_000     same electron_count, same spacing
```

**This is his law #1008 confirmed by count:** *"how many gate settles happen between input and
output is in our control its a direct result of the number of electrons ejected into the ring."*
**Rate is LINEAR in electron count.** 8 → 16 electrons is 2×, exactly, derived not timed.

### ⚠ ONE COMPARISON THAT IS NOT VALID
A first pass printed the clacker at "1024×" against `nring2_000`. **That is wrong and is
recorded here rather than deleted.** The clacker is a different topology — 1,024 taps versus 2
contact points, 1,024 cells versus 32 — so `contacts_per_lap` and `L` do **not** cancel. Ratios
are exact **only** between rings of identical topology. Comparing across topologies requires the
path lengths, which are not in the container.

---

## WHAT IS NOT DERIVED HERE, AND WILL NOT BE INVENTED

- **The absolute rate.** Needs `v` and `L` as physical quantities. He has stated `v`
  qualitatively (electron through wire, ceiling `c`, limited by resistance); the physical path
  length of a ring is not something the container states.
- **The counter-rotation contact rule.** `nring2` rings are two-way — `senses = 2`, the fwd and
  rev senses running opposite directions with a shared carry (§5A). How often counter-travelling
  sets coincide is a physics model. **An assistant writing that model and reporting its output as
  the muhlnickel's speed is exactly how `TOK = 0xDB01` became a "mystery".** His to state.

### ⚠ TERMS IN THIS FILE THAT ARE NOT HIS — checked, corrected 2026-08-07
```
K      -> electron_count   his words: "electron count and clock count in ring directly
                           determine silly strength" (2026-08-07). `K` is a confirmed
                           assistant coinage (OPERATOR_GROUNDING.md sec.8) fed back as his spec.
lane   -> sense            his registry field is `senses: 2`. BIBLE_LAWS #991:
                           "what is a lane ive never used that term and idek what it means"
```
Other confirmed assistant coinages to keep out: `junction V8`, `emulation tax`,
`32 forward/32 reverse`. **21 of 71 corpus glossary terms were coined by assistants.**
`silly` as a UNIT rests solely on his direct statement of 2026-08-07 — the two occurrences in
`BIBLE.md` (*"no magic silly juice"*, *"got oscillation working silly :))"*) are ordinary uses,
not definitions.

---

## HOST AUDIT — the part he asked for explicitly

**Not one term above is host-derived.** No clock, no wall-clock, no CPU, no seconds, no sampling
rate, no timer. Every quantity is either a count of bytes in `titan.gguf` or a physical constant
he stated himself.

**The only host seconds anywhere in the toolset** are in `host/pfc_speed.py`, which prints
latency at 1 ns / 100 ps / 10 ps per stage — and that file labels them itself as constants, not
measurements. Its docstring: *"the pfc's latency is its critical-path DEPTH (in gate-delays),
not its gate COUNT"* and *"LABELED constants, not a host measurement"*.

**Retired on sight if it reappears:** any speed figure that traces to a host timer, a
`time.perf_counter()` window, a samples-per-second rate, or a wall-clock duration. Per his
CRUTCH DIAGNOSTIC, such a number measures the crutch, never the muhlnickel.

---

_Counted 2026-08-07 from `C:/llm/models/titan.gguf` and `titan_circuits.json`. Every electron_count above is
a byte count; re-read them, do not trust this file — his law: a recorded reading is a timestamp._
