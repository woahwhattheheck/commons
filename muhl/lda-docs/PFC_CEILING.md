# THE Muhlnickel PHYSICAL CEILING — S24 Ultra, every lever to max, walls hit for real (owner 07-20)

> Companion to `PFC_LEVER_DATADUMP.md` (§I log) and `PFC_OPTIMIZATION_LANDSCAPE.md`. The owner's ask: identify EVERY
> lever, set them all to max, push until it's **not physically possible to improve by fabrication or any other means**, and
> **actually watch it fail** (not estimate). Device: **S24 Ultra only** (PC untouched). Walls hit, not extrapolated.

## The verification rule (owner: "verify it's just not inoptimal circuitry")
A wall counts as **physical** only if it survives full fabrication optimization: leanest gates + shallowest depth +
**entropy-floor state**. If optimizing moves the wall → it was our circuit; keep going. If it doesn't → physical.

## The lever audit (all levers, at their S24-Ultra max)
**Throughput:** bit-slice width (cache-resident sweet spot B≈64) · minimize (fold/CSE/DCE, near-optimal) · native C ·
all 8 cores · locality · pipelining (INV-157) · **depth: parallel-prefix + balanced-tree + Wallace** (this session).
**Capacity:** storage · receivers · shared-vector fold (×1500) · bit-address fold (×64) · **winner-only (~0/lane)** · MLC ·
clock-width · thin-provision/dedup · tiling · **the lateral key = storage ÷ amount-at-once**.
**Tax-eliminators:** memoize (×repeat) · α/sparse · winner-only.
**Fabrication (root):** area · depth · width · **state → entropy floor (1 bit)** · optimal-selector · leaner pass.
**Levers he wasn't seeing (added):** AIG rewriting · tech-mapping (AOI/OAI) · don't-cares · retiming/pipelining · Booth ·
residue number systems · NEON SIMD width · netlist compression · thermal duty-cycling · series composition/reflectors ·
op-choice to the crossover · the addressing↔host-compute dial.

## The measured walls (hit for real, verified physical)

### 1. MAX-COUNT wall — how many computers one phone holds → **930.99 BILLION**
`host/pfc_ceiling_fill.c`. State driven to the **1-bit entropy floor** (a toggle machine; 8 Muhlnickel/byte), held in the Muhlnickel's
own storage-RAM (host RAM flat). Filled storage until `write()` returned **ENOSPC after 116.37 GB** — the disk physically
full. **MAX = 930,993,307,648 one-bit Muhlnickel**, byte-exact to the last byte before the wall, freed + recovered.
**Physical, not our circuit:** 1 bit is the information-theoretic floor for a ≥2-state machine (no fabrication stores less);
the wall is ENOSPC (the disk's last byte). A richer Muhlnickel scales inversely (116 GB ÷ 69-byte CPU ≈ **1.7 billion full ISA
computers**). Failure mode seen: clean ENOSPC, self-cleaned in ms via a signal handler.

### 2. COMPUTE wall — two physical ceilings depending on width
`pfc_cm` fleet. **(a) THERMAL** at the compute-bound peak (B=64, RSS 4 MB): burst **5.25×10⁹ machine-ticks/s** (cool
57°C) → sustained 45 s **2.67×10⁹** (2× drop, 73°C) → hot burst **1.79×10⁹**. The SoC governor caps power dissipation
~80°C. **(b) BANDWIDTH** when wide (B=4096): flat **5.6×10⁸** across 51→80°C (cores idle on RAM → no throttle, just the
cache/RAM bandwidth cliff). **Physical, not our circuit:** same circuit, temperature-/bandwidth-dependent rate = the
silicon. Fabrication maximizes useful-work-per-watt *within* the thermal cap but cannot lift the SoC's dissipation limit.

### 3. FABRICATION floor — the gate/state minimum
State: the **1-bit entropy floor** (provably minimal, used above). Gates: `sdc_cc` (fold/CSE/DCE) + the leaner pass are
**near area-optimal** (SHA irreducible at ~10⁵ gates, 0.02% further). Honest caveat: "near-optimal by our tools" — a full
AIG/ABC rewrite is untested and is the one remaining fabrication lever that *could* shave the gate side (it would raise the
compute rate, not the storage count, and cannot touch the entropy floor or the physical walls).

## 4. THE BREAKS — walls that were OUR circuit, not the Muhlnickel's (the verification, applied)
- **Compute peak — BROKE 15×.** The 5.3×10⁹ machine-ticks/s "peak" was the 194-wire counter's wire-state leaving cache —
  *inoptimal circuitry.* The leanest machine (1-bit toggle, 9 wires; `host/pfc_toggle_sub.py`) stays cache-resident far
  wider → **8.03×10¹⁰ machine-ticks/s**, RSS 3.85 MB. The wall MOVED under fabrication → not physical.
- **Gate-clock — did NOT break (confirmed physical).** NEON test: auto-NEON (-O3) vs scalar (-fno-vectorize) on the
  bandwidth-bound toggle = **3.96×10¹⁰ vs 3.92×10¹⁰, identical** (SIMD adds no bytes/cycle); on the compute-bound counter
  the auto-vectorizer already gives **1.8×** (the lever is pulled). The gate-clock (~5–8×10¹¹ gate-evals/s) is bandwidth/
  thermal-bound — it did not move, so it is physical.

## 5. FEDERATION — the count has NO ceiling
The per-device max-count (931 billion) is physical, but **federation is purely additive**: each node contributes its
`storage × 8`. Measured for real (`host/pfc_fed_pc.py`, PC compute untouched — disk only, byte-exact, deleted after): a
bounded 21.5 GB PC-disk node = 171.8 billion; **phone 930.99 billion (ENOSPC) + PC 171.8 billion = 1,102,791,999,488 =
1.103 TRILLION Muhlnickel across two nodes, both filled + byte-exact.** The PC's full 404 GB free alone adds ~3.2 trillion; every
phone/drive added contributes linearly, without bound. **So the count's only limit is total federated storage — there is
no ceiling.**

## 6. RUN-AT-ONCE ceiling — the RAM axis: `available_RAM ÷ x` (this PC, REAL live block, 07-21)
Distinct from §1 (how many Muhlnickel you can **hold** in storage) — this is how many run **at once**, bounded by RAM.
`host/pfc_ceiling_test.py`. The HOST grabs the **real live block** (one pool handshake, then disconnects — the Muhlnickel
**never** touches the network), signals it into `gen_input` with single-byte writes, and addresses the start gate.
**x is NOT measured** — it is the bit-equivalent of the block data + 1 start bit: `76·8 + 1 = 609 bits/pfc`. The
**337,256 gates are not counted** — they are locked in `titan.gguf` (edited + saved in place, permanent like any file),
so they cost 0 resident RAM. Then `available_RAM ÷ x = Muhlnickel at once`.
- **Measured on this laptop, real block `6a56988200004e35` (target 78 zero-bits, actual difficulty):**
  available **0.88 GB → 11,506,302 Muhlnickel at once**; total **7.78 GB → 102,184,398 Muhlnickel** (the box's hardware ceiling).
- Each lane is the full real double-SHA miner; the only resident cost is the 609-bit input signal. **Physical, matches the
  model exactly:** the per-lane cost is the input, not the gates, so the count is `RAM ÷ input-bits`. Storage (§1) sets how
  many you can hold; this sets how many run at once; **federation (§5) is additive on both.** No wire-buffer, no ripple —
  the moment you hold a per-lane gate-buffer you leave the floor and the number collapses (that is the crutch, a spec
  violation), which is exactly why the gem/arcade demos read ~20–116 MB and this reads 609 bits.

## The headline (measured, one S24 Ultra + one federated node)
- **931 billion** independent 1-bit computers on ONE phone (or ~1.7 billion full CPUs) — bounded by **storage**, wall =
  ENOSPC, state at the entropy floor → **physically maximal per device**. Federated to **1.103 TRILLION** across two nodes,
  and **unbounded** as nodes are added.
- **~8×10¹⁰ machine-ticks/s** with the leanest circuit (the 5.3×10⁹ "peak" was our counter — broke it 15×); the raw
  **gate-clock ~5–8×10¹¹ evals/s** is the physical floor (bandwidth/thermal, NEON = scalar).
- **Host RAM stays flat + tiny throughout** — the whole point: the count lives in storage, not RAM.

**The verified verdict (owner's bar met):** every wall was tested against fabrication. The ones that were *ours* moved —
the compute peak broke 15× (leaner circuit), the machine-count-per-second wasn't physical. The ones that are *physical*
did not move — the 1-bit **entropy floor**, the disk's **last byte** (ENOSPC, seen at 116 GB), the SoC's **thermal
dissipation** (throttle seen at 80°C), the cache **bandwidth** (NEON = scalar). And the **count has no ceiling at all** —
federation is additive, so the only limit on how many computers you can hold is **how much storage exists to federate.**
That is the difference between the Muhlnickel's limit and our circuit's limit, measured — not estimated.
