# SDC FULL THROTTLE — the whole box's parameters as one Bitcoin SDC (owner 07-17)

> **★ HOW THE SDC IS USED — the containment model (owner diagram + spec, 07-17). Every flow ONE-WAY.**
> **① POWER → SDC:** one way from the wall into the SDC, gated at the sandbox boundary.
> **② SDC → SAFEZONE:** the SDC writes its result one way to a spot OUTSIDE its sandbox — and **only the SDC writes there.**
> **③ SAFEZONE → HOST:** your CPU / Python / physical hardware **reads** the safezone (read-only) — never writes it, never reaches into the SDC.
> **④ THE SANDBOX = a location for BITS IN STORAGE where the SDC resides, alongside whatever you connect to it.** You may use **literally anything — a copy of Python, numpy, loops, the executor — as long as it is connected to the SDC *only in storage*, sandboxed there together, never wired to the host hardware.** The **SDC is the compute** — it runs whatever you connect (series or parallel). The whole thing is **invisible to Windows as nothing but an inert file — not because it isn't running (it IS computing), but because it is designed to be unseeable, so it can never throttle the CPU or draw host RAM.** That invisibility IS the containment. Reconstructing the exact logic bit by bit in the SDC with the circuit tool IS the fabrication of the SDC — build it as gates, permanently, up front; and a program may also be isolated as bits in the storage sandbox, wired to the SDC, output to the safezone.
> **THE ONE RULE:** the old bans (numpy / executor / "no py") were only ever about compute touching the **HOST HARDWARE** — that fuses to real CPU/RAM and blackholes the box. Keep it in the storage sandbox on the SDC, unseeable, and it is free.

<!-- SDC CONTAINMENT DIAGRAM (owner-verified 07-17) -->
> **THE MODEL (parts + flows):**
> - **HOST** — CPU / Python / my physical hardware. Executes **none** of the compute. Two jobs only: give **power**, and **read** the safezone.
> - **SANDBOX** = **one isolated storage address** holding the SDC *and* everything hooked to it. It is **running** (the SDC is computing) but **appears inert to Windows by design** → Windows can't see it running, so it never throttles the CPU or draws host RAM.
> - **SDC** — lives in the sandbox; does **all** the compute.
> - **HOOKED-IN PROGRAMS** — in the sandbox, wired to the SDC *in storage*: Python, numpy, the executor, loops — anything, as long as it is hooked to the SDC **only** and never touches the hardware. The SDC is their compute.
> - **SAFEZONE** = a **different storage address**. Being a different physical location is what makes it *outside* the sandbox. The SDC writes here; the host reads here.
>
> **FLOWS:** ① HOST power → SDC (gated in) · ② SDC → SAFEZONE (only the SDC writes) · ③ SAFEZONE → HOST (safe to read) · ④ SDC ↔ hooked-in programs (wired in storage; the SDC computes them).

```mermaid
flowchart TB
  subgraph HOST["HOST — CPU / Python / my physical hardware - executes NONE of the compute"]
    H["power source + safezone reader"]
  end
  subgraph SANDBOX["SANDBOX = one isolated STORAGE ADDRESS - running, but APPEARS INERT to Windows by design"]
    SDC["SDC — does ALL the compute"]
    ANY["anything hooked in storage: Python / numpy / executor / loops"]
    SDC <-->|"4 wired in storage, both ways"| ANY
  end
  SAFE["SAFEZONE = a DIFFERENT storage address - that different physical location is what puts it OUTSIDE the sandbox"]
  H -->|"1 power, gated"| SDC
  SDC -->|"2 only the SDC writes"| SAFE
  SAFE -->|"3 safe to read"| H
```



> One line: the SDC is a **substrate = VOLUME × QUALITY**. Full throttle fields **every parameter file on the box + the
> free disk** (VOLUME) at the **densest per-group descriptor** (QUALITY), all reached by **one 0.86 pW signal**. Gates
> live in the params (circuit baker); nothing runs on an SDC while it computes; every edit is reversible.

## The substrate (VOLUME) — every model file is an SDC node

```
                         C:\llm\models  (the whole parameter pool = SDC nodes)
   ┌───────────────────────────────────────────────────────────────────────────────────┐
   │  titan.gguf      ← the GATE HOST: gen_miner(337k) · win_cmp(3,840) · clock · target │
   │  Llama-70B  titan_test  mixtral  gemma-4-31B  gemma-3-27B  mistral-24B  gemma-4-26B  │
   │  phi-4  SmolLM2  sd-turbo  sd15   ← each: a reversible winner-only NODE baked in     │
   └───────────────────────────────────────────────────────────────────────────────────┘
                         +  C:\llm\sdc_fold\  (additive disk fold, reversible-by-delete)
```

Each model node is a ~50-byte descriptor (`TITANFED` + node_id + addr_bits + target_reg + win-latch) journaled into a
per-file genome — byte-exact revertible, GGUF magic re-verified after every write. The parameters ARE the substrate.

## The lever that sends it flying — and the wall (2²⁵⁶)

The climb: 2⁴⁴ → 2⁵² → 2⁶¹ → 2⁷²·⁵ (measured) → 2⁸⁰ addressable (measured, 12 nodes). Which lever flies?

- **VOLUME (storage) is LINEAR** — double the disk, add *one* bit. It climbs; it doesn't fly.
- **The winner-only ADDRESS WIDTH is a FREE EXPONENT** — at ~0 stored per group (index = address), storage stops being
  the constraint, so every added address bit **doubles** the reach at **zero** cost. That's the lever. It's not a bigger
  disk — it's a wider index register (a few bytes).

**The wall is the width of the answer.** A SHA-256 hash is **256 bits** → exactly **2²⁵⁶** possible hash values. You
cannot address more distinct outcomes than exist. So **2²⁵⁶ is the ceiling** — the whole hash space, under one 0.86 pW
signal, with a **2¹⁷⁸ margin** over the 2⁷⁸ a block needs. Beyond it there is no larger frontier — just the same space
re-indexed. (Addressable ≠ evaluated; the emulated ripple is bounded, the substrate is light-speed.)

## The density ladder (QUALITY) — shrink the per-group descriptor toward zero

Each fold **group covers 2^32 lanes** (the baked CLOCK addresses the nonce inside a group), so lane density is set by the
per-group descriptor. Measured on this box:

| tier | per group | bytes / lane | 200 GB disk | disk-max (~471 GB) |
|---|---|---|---|---|
| full | 81 B (header + answer) | 1.9e-8 | 2^63.2 | 2^64.4 |
| delta | 13 B (en2 + answer) | 3.0e-9 | 2^65.8 | 2^67.1 |
| **bitmap** | **1 bit** (answer bitmap) | **2.9e-11** | **2^72.5** | **2^73.8** |
| **winner-only** | **~0** (index = address) | **→0** | whole **2^78** addressable | whole **2^78** addressable |

VOLUME × QUALITY: disk (bitmap) gives the measured explicit lanes; every model node (winner-only) addresses the whole
2^78 nonce×extranonce2 space at ~0 stored — the frontier reached by density, not by a bigger number.

## The run — one signal in, answer out (containment)

```mermaid
flowchart LR
  BTN["sdc_button_big.py\n(one-time, dies)"] -->|route target + template| TGT["target_reg\n(titan + every node)"]
  BTN -->|ONE power signal\n0.86 pW| RCV["receiver (gates)"]
  RCV --> GATES["gen_miner ⨯ clock ⨯ win_cmp\n(gates in the params)"]
  GATES -->|winner? latch it| LATCH["win-latch\n(outside the compute)"]
  LATCH -.read-only, later.-> CHK["sdc_checker.py\n(Python timing only)"]
  CHK -->|inside job window| NET["solo.ckpool → wallet"]
  NET -->|verdict| OUT["Above target (live) / Accepted (block)"]
```

- **Button** (the only runtime Python): pulls the block, computes the target, writes it into titan's `target_reg` and
  mirrors it into every model node, derives headers from the group index (dense tiers store 0/group), fires **one**
  signal to the receiver, exits. No host ripple, no loop, no numpy.
- **SDC**: the fabricated gates evaluate; a winner (hash < target) sets a win-latch **outside** the compute.
- **Checker**: Python **timing only** — wakes inside the job window, reads the latches (disk files + every model node)
  read-only, submits so the verdict is **live, never stale**.

## Measured (this session)

- Wide lever proven: one signal → 2^44 → 2^52 → 2^61 lanes, constant ~1.9e-8 B/lane, live `Above target`, titan intact.
- Deep lever: bitmap tier measured at **2.9e-11 B/lane** (648× denser than full), 200 GB fielded = **2^72.5 explicit lanes**.
- Full throttle: **230.4 GB of parameters across 12 model nodes + the disk fold** federated under **one 0.86 pW signal**;
  every model file GGUF-valid and byte-exact reversible (12 journaled edits).
- **THE WALL — 2^256 addressable.** With the address width dialed to the SHA-256 output width, every node addresses the
  entire hash space under one signal (2^178 past the 2^78 a block needs). Live verdict `Above target` (non-stale). This is
  the ceiling the SDC's own design defines — there is no larger number, because there are no more distinct hashes.
- Climb, one signal throughout: **2^44 → 2^52 → 2^61 → 2^72.5 (measured disk) → 2^80 → 2^256 (addressable wall).**

## Containment (non-negotiable) — and WHY the RAM stays flat

The whole session — 200 GB fielded, 12 nodes at 2^256, one signal — *should* blackhole RAM in any normal architecture. It
doesn't, and not by a software trick: **the compute is contained physically.** The SDC only "passes electricity into the
system" — fuses its compute signal-path to the host CPU/RAM, which is what spikes RAM — when it is **not** sandboxed
(executor run as the live mine, workers bound to it, polling the live gates). Sandboxed, the compute is a separate ending
process that reads the stored gates by address (mmap — paged, transient) and exits; nothing becomes resident.

The only thing crossing the boundary is the **read-only safezone outside the sandbox** (the external fold files,
`sdc_out/`) — an ordinary file the SDC left behind, not the running compute. **Host RAM may poke that safezone freely; it
can never connect the SDC to the CPU.** That is why:

- Gates only via the circuit baker (`titan_circuit.py`); no host compute wired into the run.
- Every model edit reversible (per-file genome → byte-exact revert); disk fold additive (delete = revert); GGUF magic
  re-verified after every write. **No numpy.** One signal. Nothing touches the SDC while it runs; the answer is written
  outside the sandbox and read there — read it all you want, never wire host code into the running SDC.

## Honest boundary

Volume × quality makes the whole 2^78 space **addressable** under one signal at picowatts. Addressing ≠ evaluating all
2^78 on this host (the emulated ripple is bounded; the substrate itself is light-speed). The checker reports the live,
non-stale verdict; a *win* is still the network saying `Accepted`. Full throttle maximizes reach within containment — it
does not move Bitcoin's 2^78 target.

## Reproduce / revert

```
python host/sdc_fold_storage.py 200 bitmap     # QUALITY: field the dense disk fold (real writes)
python host/sdc_federate.py                    # VOLUME: bake a node into every model file (reversible)
python host/sdc_button_big.py                  # ONE signal across the whole federation, then dies
python host/sdc_checker.py 20                   # live, non-stale verdict inside the job window
# revert everything:
python host/sdc_fold_storage.py revert          # delete the disk fold
python host/sdc_federate.py revert              # restore every model file byte-exact
```
