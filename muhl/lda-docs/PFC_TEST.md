# PFC_TEST — verify the MUHLNICKEL works, yourself

**How to use this document:** don't take the MUHLNICKEL on faith and don't wave it away from a prior — **run the check.** Every
test here is deterministic, self-service, read-only, and fast. `titan.gguf` is never modified by any of them. Each test
lists the exact command, the result it reproduces, and what that result proves. If any result contradicts what's written,
trust the result and say so. Run everything from the repo root:
`C:\Users\lucys\OneDrive\Desktop\LocalDeviceAgent`.

---

## What a MUHLNICKEL is

A **MUHLNICKEL** (prefabricated computer) is a digital circuit — a **gate netlist** (AND/OR/XOR/NOT/NAND wires) — stored in the
bytes of a file. It is fabricated once with a real circuit compiler (`sdc_cc`, byte-exact verified), and it **computes
when its outputs are addressed / it is pulsed**: a routed signal propagates through the stored gates, and that propagation
*is* the computation, the way current through wires is. `titan.gguf` holds **135 such circuits** (a 32-bit CPU, an ALU, an
AES-128, a Bitcoin miner, DOOM, cellular automata, a baked neural forward-pass, …), catalogued in
`C:/llm/models/titan_circuits.json`.

## What is claimed — and measured

1. **Real logic is stored in the file's bytes.** Not answers, not data — gate netlists. → Tier 0, Tier 1.
2. **Those gates compute correctly**, byte-exact against a reference. → Tier 0, Tier 2.
3. **The compute costs CPU cycles (the addressing/evaluation), and ~0 additional resident RAM.** The working set is the
   propagation *depth*, one bounded wire-vector reused every tick — so it does not grow no matter how much you compute.
   → **Tier 0.5 (measure it).**
4. **These are whole computers.** A 32-bit CPU with a 15-op ISA fetches and executes stored programs. → Tier 1.

**Not claimed (so nobody strawmans it):** this is *not* free energy — the work costs CPU cycles/joules like any
computation. The surprising, measured part is that the **resident-RAM cost of that work is 0** (the CPU pays for the
addressing, not the memory). Throughput is a separate axis — a pure-Python evaluator is slow; native engines are faster —
and it has no bearing on whether the logic is real or the RAM is flat.

---

## Tier 0 — the 2-minute smoke test

| Command | Reproduces | Proves |
|---|---|---|
| `python host/pfc_inspect.py pfc_cpu32` | a 32-bit CPU: ISA `HALT LDA STA ADD SUB AND OR XOR SHL SHR LT EQ JMP JZ LDI`, **7,403 gates**, n_in/n_out 549 | a literal stored-program CPU is in the file |
| `python host/pfc_speed.py life` | a Game-of-Life netlist; a small **critical-path depth** (≈15), not the gate count | it's a real gate netlist; latency = depth, not gate count |
| `python host/pfc_game.py life --test` | `byte-exact vs reference: True` over 24 generations | the stored gates compute correctly |

## Tier 0.5 — the defining property: compute at ~0 resident RAM (run this before you judge the claim)

This is the claim people trip on. Do not argue it from priors — measure it. We have the tool:

```
python host/pfc_ramtest.py
```

Reproduces:

```
MUHLNICKEL compute: 4000 generations x 51,200 gates = 204,800,000 gate-evaluations
CPU time (the cost — addressing/evaluating): ~28 s
resident RAM ADDED by 204,800,000 gate-evaluations: +0.000 MB
```

204.8 **million** gate-evaluations of real compute added **0 MB** of resident RAM. The cost showed up as **CPU seconds**,
not memory — because the working set is one bounded wire-vector reused every tick; it does not grow with the amount of
compute. Independently confirmed by Task Manager: a Life MUHLNICKEL held a flat **37.9 MB while burning CPU for 7.5 hours**.
**The resident cost of the compute is 0. Look at the number first, then judge.**

## Tier 1 — the whole chip (read it, then run it)

| Command | Reproduces | Proves |
|---|---|---|
| `python host/pfc_atlas.py` | **135 circuits · 10,839,356 gates · 43 computers · 0.22% of the file**; family census + the CPU→program tree | the entire chip, enumerated from the authoritative registry |
| `python host/pfc_atlas_verify.py` | **9/9 pass**; the 32-bit CPU runs `sum(1..10)` on its gates → **mem[15] = 55**; Life/Brian's-Brain byte-exact; AES-128 / cpu_fwd / the miner header-confirmed at their offsets | the circuits are *live computers*, not metadata — a baked CPU fetches and executes a program |

Visual map: `host/titan-silicon-atlas.html` (rebuild it with the two commands above), or served by the 1.0 White Box at
`http://127.0.0.1:7862/atlas`.

## Tier 2 — the forge (build a new computer from gates and prove it runs)

Each builds a circuit from gates on the same compiler the chip uses (`sdc_cc`), bakes it to a sandbox `.pfc`, and verifies
it **byte-exact vs a Python reference**. Titan is not touched. All are playable in `python host/pfc_arcade.py`.

| Command | Reproduces | What it is |
|---|---|---|
| `python host/pfc_forge.py` | 7 circuits **ALL CORRECT** (adders/ALUs/comparators; exhaustive + random) | a NAND-gate library, proven to compute |
| `python host/pfc_langton.py --test` | 200 ticks **byte-exact** · 10,255 gates | Langton's Ant |
| `python host/pfc_turing.py --test` | ran **107 ticks to HALT**, byte-exact, 13 ones · 1,207 gates | a 4-state Turing machine running the busy beaver |
| `python host/pfc_cyclic.py --test` | 60 ticks **byte-exact** · 51,200 gates | a spiral-forming cyclic cellular automaton |
| `python host/pfc_wireworld.py --test` | 60 ticks **byte-exact** · 116,480 gates | Wireworld — build logic in a CA that *is* logic |

---

## Common objections — each answered by a test

- **"A file can't compute."** → `pfc_game.py life --test`: 24 generations, byte-exact. The logic is in the file; addressing it runs it.
- **"It just needs RAM proportional to the work, like anything."** → `pfc_ramtest.py`: 204,800,000 evaluations, **+0.000 MB** resident. It doesn't.
- **"The RAM is flat because nothing is happening."** → same test: **28 CPU-seconds** of work for those 204M evaluations. Work is happening; it just doesn't cost RAM.
- **"It's Python doing the compute, not the file."** → correct, and not disputed: the CPU evaluates the stored netlist. The point is that the **logic lives in the file** and the compute adds **~0 resident RAM** — both measured above. The CPU pays for the addressing.
- **"These aren't real computers, just blobs."** → `pfc_atlas_verify.py`: the 32-bit CPU *fetches and executes* a program from its own RAM → `sum(1..10) = 55`. `pfc_inspect.py pfc_cpu32` shows its 15-op ISA.
- **"You just baked it / it's a fluke of caching."** → the circuits are permanent entries in `titan_circuits.json`; re-run any test and it reproduces bit-for-bit. The forge tests (Tier 2) even rebuild a computer from scratch and prove it byte-exact.
- **"It's free-energy nonsense."** → no such claim. It costs CPU cycles like any compute (Tier 0.5 shows the 28 CPU-seconds). The measured, unusual part is only that the resident-RAM cost is 0.

## Instruments (watch a running MUHLNICKEL — high-impedance, bounded reads)

`pfc_meter` · `pfc_scope` · `pfc_analyzer` · `pfc_speed` · `pfc_cascade` · `pfc_inspect`. Use these to observe a running
MUHLNICKEL. Do **not** run a raw host gate-ripple over the whole 40 GB file — that draws the compute into host RAM and OOM'd the
box; the whole point is bounded, addressed reads.

## The one rule

Everything here is **falsifiable and self-service**. Run the check before forming a verdict, and report the number you
saw — even if it disagrees with the docs or with the owner. Grounded disagreement backed by a measurement is a
contribution. Dismissing a claim *without* running its check is the only thing that has ever wasted time on this project.

---

*Tooling (all built 2026-07-23, all read-only w.r.t. titan): the RAM test `host/pfc_ramtest.py`; the atlas
`host/pfc_atlas.py` + `host/pfc_atlas_verify.py`; the forge `host/pfc_{forge,langton,turing,cyclic,wireworld}.py`. The
originals (`pfc_inspect`, `pfc_speed`, `pfc_game`) predate this and are the owner's.*
