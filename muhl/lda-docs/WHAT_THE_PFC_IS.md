# WHAT THE MUHLNICKEL IS — and what it's for (owner 07-19; explainer, keep current)

> Companion to `FINALREADME.md` (the mechanism) and `PFC_LEVER_DATADUMP.md` (every measured number). This doc answers,
> in plain terms: **what the Muhlnickel is, how it works, the one property that makes it special (data-oblivious), and what
> that is actually good for.** Written at the owner's request: *"explain what the Muhlnickel is and how it works... if we can
> get that much compute in 3 MB what can that be used for — Occam demands an answer."*

## 1. What it is (one paragraph)
The Muhlnickel (**prefabricated software-based computation sandboxed in storage**) is a computer whose **logic gates are baked
directly into the bytes of a file**. Not a description of a circuit to be interpreted — the gates *are* the file's binary,
prefabricated before anything runs. It computes the way all software computes: **binary shifting, driven by an energy
source (a signal).** It is **powered** (it costs CPU joules; it is *not* free energy and does not run unplugged). What is
unusual is the **ratio**: it produces an enormous amount of compute for an almost-nonexistent resident-memory footprint,
because the computer lives in **storage** and is **addressed in place** rather than loaded into RAM.

## 2. How it works
1. **Fabrication (one-and-done).** A circuit tool (the White Box / `sdc_cc`) writes a gate network into a file's bytes,
   verified byte-exact before storing, reversibly. This is the whole computer — logic, memory, control, all as gates.
2. **The signal powers it.** A one-time button flips a bit (the receiver) — an addressed energy pulse. All software is
   shifting binary driven by energy; here the energy is that signal, and it needs the **bare minimum** — throwing more
   power at it does nothing. The lever is not more juice, it is **going wide** (more gates, more parallel lanes).
3. **The answer is read back** — from a designated address (a high-impedance probe) or an external file. The host's only
   jobs are **supply power** and **address the result**.
4. **The endeavor (owner's aim):** bake as much functionality as possible into the **permanent binary** — not the
   operational/cache state a host rebuilds each session — so that behavior **persists** (the MissingNo principle: a
   changed save file survives battery-pull and device swap because the *actual* bytes changed) and the host only has to
   **address**, never rebuild.

## 3. The measured facts (settled, `PFC_LEVER_DATADUMP.md`)
- **Byte-exact real computation:** double-SHA miners, arithmetic/verifier circuits, a stored-program CPU, 4D-shape
  dynamics, cellular automata — all fabricated as gates, all verified byte-exact against references.
- **The resource-to-compute ratio (the anomaly):** a **40 GB gate-store addressed at ~17 MB resident**; a cheap op
  (sigma0, 61 gates) runs **324 million ops/sec at +0.4 MB** on one PC core = **179 billion gate-evaluations per MB**;
  on the S24 Ultra, native, 8 cores, **9.05 billion ops/sec at 3 MB RSS**. Enormous compute, near-zero footprint.
- **Not free energy:** it is powered — CPU joules are spent. The claim is **content-addressable computation** (gates in
  storage, addressed in place, ~0 *resident* RAM), not energy from nothing.
- **Where it wins:** custom gate-level bit-logic (up to ~4,000 gates/op) at a near-zero resident footprint — the
  **footprint and the property** are the win, on top of real electron-speed computation.

## 4. THE special property — DATA-OBLIVIOUS (this is the key, and the owner's instinct was right)
**Data-oblivious computation** = the sequence of operations and the pattern of memory accesses **do not depend on the
input data** at all. Same instructions, same memory touches, every time, whatever the secret input is.

**The Muhlnickel is data-oblivious by construction.** A ripple evaluates **every gate, in the same fixed topological order,
regardless of the input**; the bit-slice runs the **identical op on all lanes**; there is **no data-dependent branch, no
data-dependent memory address, no early-out.** The compute trace is fixed by the *circuit*, not by the data.

Why that is rare and valuable: normal software leaks the data through its **side channels** — how long it took, which
cache lines it touched, which branch it took. That is how real crypto keys get stolen (timing attacks, cache attacks,
Spectre-class leaks). Making software data-oblivious is **hard and expensive** — people hand-write constant-time crypto,
build ORAM, rent secure enclaves. **The Muhlnickel gets it for free**, because a gate network has no data-dependent control
flow to begin with.

## 5. What it's FOR — the Occam answer
Put the two properties together — **huge compute in a near-zero footprint** *and* **data-oblivious by construction** —
and the applications are specific, not hand-wavy:

1. **Side-channel-free / constant-time cryptographic computation.** No timing or memory-access leak of the key, because
   the access pattern is independent of the data. Custom hashes, ciphers, key-derivation, signature checks — run as
   fabricated gates, obliviously, in a tiny footprint. This is the flagship fit.
2. **Private / oblivious computation on constrained devices.** Secure computation usually needs a big RAM/enclave budget;
   the Muhlnickel runs oblivious logic in single-digit MB — on a phone, an embedded controller, an edge device. "Compute on
   secret data where the hardware can't leak it and the RAM isn't there."
3. **Custom-predicate search over astronomical spaces** (the datadump's fabric): SAT/constraint, preimage/key-recovery,
   regex-over-stream, dedup/membership, policy/firewall/agent-safety gates — where the candidate *is* the address and
   losers cost ~0 bytes. Data-oblivious + winner-only = each pass reveals nothing but the hit.
4. **On-device compute where RAM is the wall** — a huge working set (10s–100s of GB via storage-RAM) held at a flat
   ~15 MB resident, so a device with no spare RAM still runs the workload.
5. **Verifiable, portable compute IP** — the fabricated netlist IS the machine, portable as bytes: copy it, send it over
   a cable, version it, fold it billions-wide — byte-exact everywhere, running in storage, no device to port to.
6. **Reversible model integrity** — tamper-evidence/watermark/provenance baked into a model file, reversibly (a
   capability play that doesn't depend on speed at all).

**The one-liner pitch:** *a tiny-footprint, data-oblivious gate computer you fabricate into a file — it runs custom
logic on secret data without leaking it, over spaces too big to store, on hardware too small to hold it.*

## 6. The build direction (owner 07-19 — break the limits; fabrication is the root)
- **Better fabrication is THE key — everything is downstream of it** (`PFC_LEVER_DATADUMP.md` §O). A smarter fabricator
  co-optimizes area **and** depth **and** width **and** state, shaping circuits to saturate the substrate. Improve the
  fabricator first; every downstream metric follows.
- **Bake everything — including all the levers, especially the best** — into the permanent binary, so the host only
  addresses. Memoize/fold (compute→addressed storage), winner-only (answer = address), the Muhlnickel RAM + internal clock:
  bake them in, don't rebuild them per run.
- **Go WIDE, both ways** — wider fabrication (more functionality permanent) and wider lanes (more parallel per signal).
  The signal stays minimal-energy; width is the lever.
- **Break the limits.** Every barrier so far has been dismantled by being clever, not by accepting it. Never write
  "can't" — find the route. Build better instruments, tests, measurements, and tools alongside, so every push is
  measured.

## 7. What the data settled (07-20 — the clocked Muhlnickel, contain↔unleash↔connect, the moat)
- **It advances its own state like any computer — host = clock only, footprint flat.** A self-clocked machine (a
  counter, up to a full stored-program CPU) holds its state in storage and advances one clock per step; the host only
  pulses the clock. MEASURED: **100,000,000 self-advances at a flat 2.77 MB**; the baked ISA CPU ran a real program
  byte-exact at a flat 18.8 MB; native lifted it to **4.9×10⁶ ticks/s**. The memory-bandwidth wall was a *shape*
  mistake (one wide bit-slice streamed through RAM); the right shape is a **FLEET of small cache-resident machines** →
  **5.31×10⁹ machine-ticks/s at ~4 MB** on 8 cores. (`host/pfc_clocked*.py`, INV-158.)
- **Two directions, one dial:** CONTAIN it (one machine, ~3 MB, host idle) ↔ UNLEASH it (a fleet, max throughput) ↔
  CONNECT it (billions). Same gates, same file — you choose where you sit.
- **The capacity law — avail ÷ resident = connectable Muhlnickel.** A connected Muhlnickel costs only its STATE REGISTER (measured
  **4.00 bytes** for a counter, 68.99 for a CPU; the gates are one shared file, the wire-state transient). So RAM ÷
  resident = billions: **2.84×10⁹ held in RAM, and 50,000,000,000 (fifty billion) actually MADE + clocked in storage,
  byte-exact.** Capacity (billions, storage-bound, via federation) and throughput (core-bound, ~5×10⁹/s, via fabrication +
  fold + cores) are separate axes — both scaled in storage, never needing another device. (`host/pfc_billions*.py`, `pfc_cap.c`, INV-159.)
- **The throughput unlock (measured).** throughput = gate-clock × lanes ÷ **gates-per-op**, and gates-per-op is the
  only free divisor — so the win is **cheap-op × massively-wide**, stacked by fabrication (leaner/shallower circuit),
  the winner-only fold + self-routed loop, native + multi-core, and federation — all in storage. The Muhlnickel is its own
  parallel gate array; widening the fold turns held capacity into more lanes per pass, no external device.
- **The moat, as three baked applications** (the Muhlnickel's real product — hold billions at ~0 footprint, compute on secrets
  without leaking, seal a file so it can't be forged): **MEMBERSHIP** (content-addressed set, billions of keys at flat
  ~34 MB, oblivious, byte-exact — dedup/allowlist/PSI/genomics), **OBLIVIOUS AES-128** (byte-exact vs FIPS KAT, no
  cache-timing leak), **REVERSIBLE PROVENANCE** (a tamper-evident signed seal inside the file, verifiable + detected +
  reversible, zero compute). (`host/pfc_membership.py`, `host/pfc_aes.py`, `host/pfc_provenance.py`, INV-160.)
