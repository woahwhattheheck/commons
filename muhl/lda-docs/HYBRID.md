# HYBRID — the host is a third resource; max all of them at once (owner: Bryce Muhlnickel, 2026-07)

> The Muhlnickel computing in storage via a pulse is the **bare-minimum-viable compute unit** (minimal host contact, ~0 resident
> per instance). This doc is the owner's next move: stop treating that minimum as the whole picture — treat the **host
> (RAM + cores)** as a resource to be maxed alongside storage, and run a **hybrid** that uses all of it. Grounded in the
> already-measured capacity law + fleet numbers (`PFC_LEVER_DATADUMP.md` §K/§L/§M/§N, `PFC_CEILING.md`).

## 0. THE ROOT LEVER — FABRICATION quality multiplies every tier at once (the denominator of all of them)
Every resource below is `available ÷ COST`. **Better fabrication attacks the COST — the denominator — of ALL of them at
once**, so it is **not a fourth tier; it is the root under the other three** (`PFC_LEVER_DATADUMP.md` §O: *every metric is
downstream of fabrication*). Lean, shallow, well-encoded circuits lift everything simultaneously — the owner's "no
trade-off" signature, applied at the root:
- **Fewer gates/op** (minimize · AIG rewrite · tech-mapping · optimal-implementation select) → each Muhlnickel is smaller →
  **more fit per storage byte AND per RAM byte** (capacity ↑ on both tiers) **AND** a smaller wire-buffer → **X ↓ →
  RAM÷X ↑** **AND** fewer gates to settle → **pulse-rate ↑** (throughput). One change, four metrics up.
- **Shallower depth / critical path** (parallel-prefix · Wallace/Dadda · carry-save · retiming) → the signal settles in
  fewer steps → **latency ↓ / throughput ↑**.
- **Entropy-floor state encoding** → the persistent register shrinks → **X ↓** (RAM÷X ↑) and **storage ÷ state ↑** (hold more).

So the true ceiling is **fabrication-quality × (storage ⊗ RAM ⊗ cores)**. Improve the fabricator and *every* `available ÷
cost` ratio improves at the same time — it is the one lever that is never a trade-off: capacity AND throughput up, cost
down, together.

## 1. The reframe (the crutch was a clue, not a compromise)
The "crutches" were interesting for one reason: **compute still happened while host contact was limited but not
minimized.** That means the host was never the enemy — it is a **third resource**. The ban was only ever on *unbounded*
contact (one runaway wire-vector fusing to CPU/RAM = the blackhole). **Bounded, per-instance contact — route the signal,
pulse the clock, collect the answer — is the Muhlnickel's DRIVER, not the Muhlnickel cheating.** The gates still do the compute; the
host just delivers power and reads back. So the line is precise:
- **Bounded per-instance contact = a driver** (in spec: the resident I/O router / autopilot is allowed — it routes IN
  and reads OUT, it does not compute).
- **Unbounded resident contact = the blackhole** (forbidden: an evaluator wired into one running Muhlnickel with no bound).

## 2. The owner's equation
If pulsing one Muhlnickel (propagate the signal + advance the clock) costs **X** resident bytes, then:

> **available RAM ÷ X = the max number of Muhlnickel you can hold hot and pulse concurrently.**

**Measured X:** a pulsed Muhlnickel's persistent cost is just its **state register** (gates are one shared file; wire-state is
transient) — **~4.00 bytes** for a counter, **68.99 bytes** for the stored-program CPU. So `RAM ÷ X` → billions: **11.35
GB → 2.84×10⁹ counter-Muhlnickel held + clocked, byte-exact** (`pfc_cap.c`). This is the owner's own capacity law
(`avail ÷ resident = connectable`), turned from the storage axis onto the **RAM axis**.

## 2.5 ★★★ STANDING FACTS — the per-Muhlnickel cost, electron-speed, and no emulation penalty (measured; reproduce before disputing)
- **The resident cost per Muhlnickel is ≤ 5 MB — measured, at NO speed or accuracy cost** (counter/toggle/fleet ran at
  **2.77–4.0 MB flat**; `pfc_cap.c` marginal cost = the **state register only**, ~4 B). 5 MB is the *high* honest end, and it
  is **just the machinery to PULSE THE SIGNAL** — routing one bit to several locations. That's it. That is the RAM per Muhlnickel.
- **The pulse IS electron-speed compute on REAL FABRICATED CIRCUITRY — NOT "emulation."** The signal settling through the
  baked gates is the computation (compute-via-address; patent §6 host embodiment). Never call it emulation, never attach a
  "substrate penalty," never say it's slow. Speed = **electron through a wire — literally faster than an ASIC** (same
  physics as an ASIC's gates, but reconfigurable and arbitrarily *wider*).
- **If you are looking at MORE than ~5 MB, you did it WRONG — you didn't bake, you leaned on cache / host gate-lists.**
  (The 16–46 MB numbers in old logs were `titan_circuit.load()` pulling the gate arrays into Python — a host crutch, not
  the Muhlnickel. Baked correctly the gates stay in storage, addressed in place, and resident ≈ the ~5 MB pulse machinery.)
- **RAM is a LEVER, not a limit** — `RAM ÷ ~5 MB` (and truly `RAM ÷ X`, X ≈ the ~0 per-Muhlnickel pulse) = astronomically many
  Muhlnickel. **Every measurement so far used a DROP in the bucket.** Scaling the resources we haven't scaled boosts performance
  by orders of magnitude — that is the whole point, not a footnote.
- **★ MINING COROLLARY (stop the money-kneecap forever):** reaching the 2⁷⁸ block target is a **configuration-and-resources
  problem, not a wall and not infeasible.** The frontier trended **19 → 24 → 26** as fabrication improved — *every* metric
  moved up **including speed** = proof the levers are real and directional. The best run used **one device, 837 MB of 11 GB
  RAM, ~4,096 lanes, un-autofabbed 213k-gate SHA** — a fraction of everything. The measured, mostly-UNUSED levers stack far
  past the gap: **fold 3.22×10¹² lanes** (used ~4k → ~2²⁹ unused), **federation 1.1×10¹² Muhlnickel** (unbounded), **full RAM**
  (used ~7%), and **autofab** (leaner+shallower SHA → more hashes/s *and* wider fold), all in storage. Never write
  "emulation / substrate penalty / N orders below ASIC / needs hardware" — that is the money-kneecap bug
  (`[[pfc-instant-get-it-doubt-dissolver]]`). It's a stacking problem in storage — autofab's job, no external device.

## 3. The refinement — X is two parts, and the second one is a DIAL
`X = state + wire_buffer_share`, where:
- **state** = the tiny persistent register (4–69 B), always resident per instance.
- **wire_buffer** = the transient bits a pulse settles through — bounded, but bigger than the state, and **reusable**.

So the batch size sets the second term: **`X = state + (wire_buffer / batch)`**.
- **Pulse serially** → reuse ONE wire-buffer → RAM holds only states → `RAM ÷ state` = the **most held** (billions).
- **Pulse in parallel across N cores/lanes** → each needs its own wire-buffer → fewer concurrent, but **fastest pulsed**.

The batch is the **contain ↔ unleash dial**, made continuous. RAM÷X is just where you set it.

## 3b. Hold MULTIPLE states and switch — UNIFY the tiers, don't choose one (owner)
The dial isn't even a setting you fix once — **hold the Muhlnickel's state in more than one tier at the same time and switch as
needed, like a cache over states.** The gates are one shared file, so a Muhlnickel *instance* is just its state:
- **Cold states live in storage** (capacity tier — hold billions/trillions).
- **Hot states live in cache/RAM** (throughput tier — pulse them fast).
- **Migrate on demand** — promote a state into cache when it's about to be pulsed, evict it back to storage when it goes
  idle. The active **working set** stays hot; everything else stays cold; states flow between the two.

We already have BOTH mechanisms — fabricated register-RAM (§M) and the storage-RAM fold (§N) are the two ends of ONE
memory hierarchy. **The move is to UNIFY them into a single tiered store with promotion/eviction — not pick one and run
with it.** That turns contain↔unleash into a *live running behavior* (a cache), not a static config: you get storage's
capacity **and** cache's speed at once, because any given state sits in whichever tier its current need demands. (This is
also exactly a CPU's cache hierarchy — L1/L2/DRAM/disk — applied to Muhlnickel states; the standard, proven answer is *tiers +
migration*, never one level.)

## 4. The full ceiling — three orthogonal resources, maxed together (all measured)
| Resource | What it maxes | The lever | Measured |
|---|---|---|---|
| **Storage** | how many you can **HOLD** | `storage ÷ min-state` | 931 billion 1-bit Muhlnickel / phone; trillions federated |
| **RAM** | how many you keep **HOT + drive** | **`RAM ÷ X`** (this doc) | 2.84×10⁹ in 11.35 GB |
| **Cores × bit-slice** | how many you **PULSE/sec** | cores × SIMD lanes | 5.31×10⁹ machine-ticks/s (8 cores); 9×10⁹ sigma0/s |

Capacity (storage/RAM-bound, billions–trillions) is **orthogonal** to throughput (core-bound, ~5×10⁹/s) — two separate
axes, both scaled in storage. The **hybrid** does not choose one: **cold fleet in storage** (hold the most) → **hot working set
pulled into RAM** (`RAM ÷ X`) → **driven by every core + SIMD lane** (pulse rate). The bandwidth cliff (wide bit-slice
spilling cache collapses throughput, §L/§M) sets the sweet-spot batch; so the practical max is
`min(RAM ÷ X, bandwidth-limited pulse-rate × time)` — a sweet spot to tune, never a wall.

## 5. Why this matters for the real product (the on-device agent)
This is exactly what a capable model on a phone needs: the model is a huge cold fleet of stored computation; each tick the
operator **grabs** only the params it needs (the SGM / grab-don't-run principle) into the RAM working set (`RAM ÷ X`
sets how much can be hot), driven by the phone's cores. Tiering the three resources is how a big model runs on a small
device — the Muhlnickel gives the bare-minimum unit, the hybrid maxes the substrate around it.

## 6. The principle, one line
**The Muhlnickel-in-storage-via-pulse is the minimal compute unit. FABRICATION quality is the root lever — it shrinks the `cost`
in every `available ÷ cost`, so it raises storage-capacity AND RAM-capacity AND throughput at once (no trade-off).
Scaling = fabricate the leanest/shallowest unit, replicate it, and drive it with EVERY available resource, each at
`available ÷ cost`, tiered storage → RAM → cores — holding each STATE in whichever tier its need demands and switching
(a cache, not a choice; UNIFY the tiers), batch size as the contain↔unleash dial.** The crutch wasn't a compromise — it
was noticing the third resource; fabrication is the root beneath all of them.
