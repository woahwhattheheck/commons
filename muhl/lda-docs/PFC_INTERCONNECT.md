# MUHLNICKEL INTERCONNECT — how to add MORE Muhlnickel (the architecture, measured 2026-07-26)

> **Owner:** *"one Muhlnickel is a few mb, make a bajillion link them in series or parallel and boom = done"* ·
> *"more Muhlnickel each being added to boost performance can be specialized"* ·
> *"Muhlnickel can be interconnected without touching host"* ·
> *"there are various ways to hook Muhlnickel together and its not one size fits all"* ·
> **AVOID the safezone idea — crazy hard to pull off, not worth it.**

## 1. THE MECHANISM — §1E junctions (`FINALREADME.md` §1E, owner 07-19)

> *"Every circuit you want in series with the next needs a SEND function and a RECEIVE function. The upstream
> circuit's SEND writes to a storage address that **IS THE SAME PHYSICAL LOCATION** as the downstream circuit's
> RECEIVE reads from — not a copy, not a JSON mapping, **the same bit**. That shared bit's state (1 or 0) determines
> whether they are connected. The chain **STARTS WITH THE START BUTTON**."*

- **A junction is a shared storage location**, not a transfer. `A_out is B_in` — the same wires.
- **Debugging a dead link: probe the shared bit.** Not flipping to 1 ⇒ that junction is the break.
- The host addresses only the **first** RECEIVE and reads only the **last** SEND. It is never between stages.

## 2. THE SCALING LAW — MEASURED, byte-exact

| circuit | offset | what | result |
|---|---|---|---|
| `pfc_junction_ab` | 2496172268 | 2 stages (`y=x+1` → `z=y*2`) | 64/64 · depth **40**, not 34+40 |
| (4-stage chain) | — | sum → Wallace mul → reduce → bias | 40/40 · increments `66, +50, +6, +6` |
| `pfc_chain32` | 2496174244 | 32 specialised stages | 32/32 · **DEPTH 252** |

```
pfc_chain32 cumulative depth every 4 stages: 84 108 132 156 180 204 228 252
per-stage increment: first = 66, then min 6 / max 6 / mean 6.0   <- CONSTANT
```

**★ LAW: the first stage costs its own critical path; every junction-chained stage after it costs exactly +6
gate-delays.** Linear across 32 stages. Extrapolates: ~1,000 stages ≈ 6,000 gate-delays — still ONE settle.

**A junction adds the stage's own depth and nothing else. No round-trip.**


## 2b. A REAL NEURON, JUNCTIONED — `pfc_neuron32` @ 2496235772 (349,792 gates, byte-exact 8/8)

Both topologies at once: **lateral** for the independent multiplies, **series junctions** for reduce and bias.

```
stage 1  MUL  (32 LATERAL multiplies)  depth  58
stage 2  TREE (SERIES junction)        depth 131   (+73)
stage 3  BIAS (SERIES junction)        depth 137   (+6)
=> sum(w*x) + b in ONE addressed settle, depth 137, no host inside it
```
The `+6` on the bias stage is the junction law holding on a REAL circuit, not a toy chain.

**Scaling out:** a 4096-wide layer = 128 of these folded LATERALLY, junctioned into an accumulator tree. Depth grows
as log2(tile count), NOT as neuron count — a full layer lands in the low hundreds of gate-delays, ONE settle.
Compare the host-driven measurement the same night: **384,368,640 block-dots** for 32 layers x 32 tokens.

## 3. THE TOPOLOGIES — not one size fits all

| topology | use it for | measured |
|---|---|---|
| **§1E series junction** | pipeline stages (layer N → N+1) | proven above; depth sub-additive, +6/stage |
| **Lateral fold** | many instances, independent inputs | 3.22×10¹² addressable lanes at ~0 RAM |
| **Shared-vector / broadcast** | one input read by many circuits | ~1,500× denser than copying |
| **Winner-only** | N candidates, one answer; losers 0 bytes | ~10¹⁵ tier, bounded by #circuits not storage |
| **Federation** | across devices | additive, unbounded; 1.1×10¹² Muhlnickel measured |

**A forward pass needs SEVERAL at once:** layers are **series**, attention heads are **lateral**, the hidden state is
**broadcast**, vocab argmax is **winner-only**. Forcing one shape onto all of it is the error.

## 4. THE GEOMETRY (`PFC_LEVER_DATADUMP`)

> *"RAM = lateral (width — how many at once). Fabrication = depth (capability — how complex each pass).*
> ***Optimal Muhlnickel = (sophisticated, minimized DEPTH) × (WIDE lateral deployment).***
> *The design flaw = **UNDER-FABRICATION** — resources sit idle because the circuit is too small / shallow-serial /
> stateless to ASK for them."*

Capacity and throughput are **orthogonal**: capacity scales with storage + federation; throughput with fabrication +
fold width + cores. Addressing a lane ≠ computing it.

## 5. BUILD ORDER FOR REAL INFERENCE

1. **Specialise each stage** — most already exist: `pfc_dot_q4k_sub32` (Q4_K native, 40/40), `pfc_argmax` (26,272g),
   `pfc_rsqrt/sin/silu8/exp_shallow` (6.1× shallower, byte-exact 2,560/2,560), `pfc_ram`, `pfc_mmu`.
2. **Junction them** — each stage's SEND wires ARE the next stage's RECEIVE wires.
3. **Lateral-fold the heads** — independent, same circuit.
4. **Broadcast the hidden state** — one input, many readers.
5. **Winner-only the vocab** — argmax as address, losers cost nothing.

**NOT** "make one engine faster." That was the session's error.

## 6. THE ERROR THIS DOC EXISTS TO PREVENT

On 2026-07-25/26 an entire session optimised **one** general Muhlnickel — dot depth 131→42, glue 6.1× shallower, correctness
28.4%→0.680%. All real, all worth keeping. But the measured costs (1,677 s/token; **384,368,640 block-dots** for a
32-layer decode) were then attributed to "host serial addressing = the remaining problem."

**It was not a substrate limit.** It was the host sitting between stages that should have been wired to each other,
plus under-fabrication. The interconnect had been specified in `FINALREADME` §1E since 07-19 and never used.

Also: `pfc_llama_decode` defaulted to `--fold 4096` while the measured bit-slice sweet spot is **W=65,536** — a 16×
width kneecap that was likewise blamed on the host.
