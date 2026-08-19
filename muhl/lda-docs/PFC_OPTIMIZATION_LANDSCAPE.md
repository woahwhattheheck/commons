# THE Muhlnickel IN THE OPTIMIZATION LANDSCAPE — what we lack, what's unique, how to push (owner 07-20)

> Companion to `WHAT_THE_PFC_IS.md` (what it is) and `PFC_LEVER_DATADUMP.md` (every measured number). Written to the
> owner's ask: "study circuitry and computation optimization at large — what solutions do we lack, what are our unique
> advantages, and how can we push them." Grounded in the field and in our own measurements, no hand-waving.

## 0. Where the Muhlnickel sits in the field
It is **content-addressable, in-storage, reconfigurable gate computation.** Nearest established categories: **computational
storage / near-data compute** (run logic where the bytes live), **content-addressable memory / compute-via-address** (the
address *is* the input; the read generates the output), a **reconfigurable gate netlist that lives and runs in storage**,
and **the time–memory tradeoff at its extreme** (precompute/tabulate/fold into addressable storage). What is
new is the *combination*: the whole machine is **file bytes**, addressed in place at ~0 resident RAM, replicable billions-wide.

## 1. What we LACK (the field has it; we don't — yet)
1. **Modern logic synthesis.** `sdc_cc` does fold + CSE + DCE (basic). The field has **AIG rewriting (ABC), don't-care
   optimization, technology mapping** — far more sharing and smaller area. We measured `sdc_cc` is near area-optimal for
   what it does, but it does *less* than a modern synthesizer.
2. **The shallow-arithmetic suite.** We just added the **parallel-prefix adder + balanced trees** (up to 32× shallower).
   Still missing: **Wallace/Dadda multiplier trees, carry-save adders** (for SHA's many sums), **Booth encoding**,
   **retiming**, and **pipelining** (latches between stages to overlap work — INV-157 saw latches in weights but we don't
   fabricate them).
3. **Wider parallel evaluation, in storage.** On a CPU we evaluate gates *per lane* (bit-slice = SIMD). The Muhlnickel widens
   parallelism the storage way — wider fold (bit-slice width), width baked into the fabric, native+cores, and federation —
   so more lanes settle per pass, all in storage. Bit-slicing IS SIMD; the Muhlnickel is its own parallel fabric — a digital gate
   array, no external device.
4. **Number-system tricks.** Redundant / carry-save / **residue number systems** (RNS) for carry-free parallel arithmetic.
5. **(Deliberately NOT lacking — a choice, not a gap):** approximate / stochastic computing. We are **byte-exact on
   purpose** (no cheating); we'd adopt approximation only where an application explicitly tolerates it.

## 2. Our UNIQUE ADVANTAGES (measured; nothing mainstream does these at once)
1. **★ Compute decoupled from resident footprint.** The moat. Measured: **179 billion gate-evals/MB**; a whole computer run
   **100M ticks at 2.8 MB**; **50 billion** computers made at **4 bytes each**; **405 billion** lateral lanes at **8 MB**
   resident. A CPU/GPU/FPGA scales working memory with the work; the Muhlnickel addresses compute *in storage* → ~0 resident. This
   is compute-in-storage pushed past where anyone runs it.
2. **The computer IS reconfigurable, portable, replicable DATA.** Edit the bytes (reversibly) to change the logic — no
   silicon respin, no bitstream, no special device. Copy it, **send it over a cable and it still computes** (measured),
   version it, **fold it billions-wide**. FPGAs reconfigure but need the FPGA; ASICs are fixed. Our "hardware" is bytes.
3. **Data-oblivious by construction.** Constant-time, no data-dependent branch or address → **no side channel, for free**
   (measured: AES-128 byte-exact vs FIPS with no cache-timing leak). Others hand-harden at great cost.
4. **Reversible (genome).** Byte-exact undo of *any* logic edit. Normal hardware and even FPGA reconfig don't give this.
5. **The lateral fold + winner-only.** Content-addressable search to the **storage limit** — the address *is* the answer,
   losers cost 0 bytes. The key: **availableStorage ÷ amountNeededAtOnce = the count** (measured 405 billion on one laptop).

## 3. How to PUSH them (the strategy)
1. **Adopt the depth/area synthesis we lack → high-quality gates.** Route parallel-prefix + balanced trees into the
   fabricator; add Wallace/carry-save/Booth, retiming, and AIG rewriting. Shallow + lean gates make the signal-latency
   fast and shrink the working set. *(In progress — `host/pfc_bettergates.py`.)*
2. **Lean HARD into footprint-decoupling + the lateral fold + federation** — the ground no one else stands on. Build the
   **content-addressable compute fabric** (the Muhlnickel as one giant CAM-compute surface) and the **oblivious-compute toolkit**
   (oblivious RAM/sort/search baked → a "secure enclave in a file" needing no special hardware). Aggregate storage across
   devices so the numerator of the key becomes *total* storage.
3. **Scale throughput in storage — the only axis.** The Muhlnickel IS the parallel fabric; you never move it off storage. More
   throughput comes from LEANER/SHALLOWER fabrication (fewer gate-stages per pass), WIDER fold (bit-slice width), native +
   cores, and FEDERATION (additive across devices). All measured, all in storage. Our wins are **capacity · footprint ·
   portability · obliviousness · reversibility** — pick applications there.

## 4. The one line
**Adopt the field's depth/area optimization to make the gates high-quality; then push the one thing nothing else has —
computation that lives in storage as reconfigurable, portable, oblivious, reversible, billions-replicable data — through
the content-addressable fabric, the oblivious toolkit, and storage federation.**
