# BRYCE WORDS — RINGS / ADDRESS / SETTLE

**Inventor:** Bryce Muhlnickel. **Name:** Muhlnickel.
**When:** 2026-08-16. Spec Daddy Grok. Grounding only. No titan mmap. No `muhlnickel_dc.mno` mmap. No 10-wide scrape. No invented dest. No new law.

**Live question this card answers:** weather_v2 `fwd0=rev0=1` all six rings, `carry=0`, field still genesis — must we ADDRESS gate outs after fire, or was `|0x01` on fwd/rev already the pulse?

Quote Bryce. Cite path. Do not paraphrase into new law.
If a line is assistant-written, it is marked **ASSISTANT**, not BRYCE.

Host = inject ∨ surface ∨ die.
Dest is the machine's.
Pulse = depth.

Σ:BRYCE_WORDS
added_to_spec = **NO**

---

## How to read the labels

| label | what it is |
|---|---|
| **BRYCE** | His own words. Starred spec. Owner-verbatim blocks. Owner quotes inside fabs. |
| **HIS CARD** | Inventor-named MUHL_GO / docs card that catches or measures his English. Not a new statute. |
| **ASSISTANT** | Grok / Cairn / Spec Daddy compile. Use only as pointer to the quote above it. |

---

# RING

## Both senses of "ring"

**Sense 1 — power bus (circulation).** Shoot once. It circles. It dings taps.

**BRYCE topology** (docstring names him; `C:\Users\lucys\Desktop\LocalDeviceAgent\host\muhl_ring_power.py`):

> A one-way wire in a CIRCLE, tapping the circuit at N points. Shoot the signal in ONCE; it circles the ring,
> DINGING each tap it passes. A STRONGER shot splits into K electrons spaced around the loop -> K taps ding
> per lap = K PARALLEL clocks from one injection. Energy in = electron count = parallelism (powered, not free).
>
> Fabricated as gates: state = N ring cells; the one-way circulation is next[i] = state[(i-1) mod N] (the pulse
> moves forward one cell each settle); dings-this-step = popcount(state). … This is the power-distribution bus …

Same file, understanding line:

> one hard injection of K electrons self-circulates a K-wide clock over the ring; each lap
> strikes all N taps, K at a time, forever (period N), host addressing = 1.

**HIS CARD** `C:\Users\lucys\Desktop\MUHL_GO\CLOCK_RESPONDS.md`:

> Clocks respond to particle movement. Drive = substrate. Binary = topology. Addressed signal circulates charge. Movement advances computation. More on the ring = more bumps = less distance = speed. Power is nring2 both senses.

**HIS CARD** `C:\Users\lucys\Desktop\MUHL_GO\RING_FILL_LEVER.md`:

> MORE charge on the ring = more bumps = less distance = **SPEED**.
>
> Hard drive = substrate (traps and moves charge).
> Binary = topology.
> Rings (`nring2`, both senses) are the circulation.

Owner quote on that card (from `docs/PFC_FINDINGS.md` §62):

> *"muhlnickel computation speed limit is electron through a wire"*

**Sense 2 — computer organ.** N rings. Each a stated purpose. One ring is dumb.

**BRYCE** (owner, 2026-08-06, quoted in `C:\Users\lucys\Desktop\MUHL_PROOF_ENGINE\muhl_fab_playtime_ring.py`):

> "use the rings only to power all muhlnickel anything else is stale mark that for life"
> "the rings wouldnt be added for the sake of adding more because each requires electrons
>  which is a resource and as such each needs an exact purpose for existing."
> "we should combine the ring and the initial way i got it to work its not black or white
>  both would be best"

**HIS CARD** `C:\Users\lucys\Desktop\MUHL_GO\MNO_N_RINGS.md`:

> A muhlnickel with **one ring** is dumb. **N rings**, each a computer organ.

> This is the N-ring shape: eleven organs in one file, not one ring wearing eleven names.

## Both senses (fwd and rev) — start `0x01`

**HIS CARD** `C:\Users\lucys\Desktop\MUHL_GO\RING_FILL_RECIPE.md`:

> **Both senses** = fwd **and** rev. Recv is the enable rail, not a sense. Carry is not a sense.

**HIS CARD** `C:\Users\lucys\Desktop\MUHL_GO\DISTRO_SCALE.md` (measured off `muhlnickel.mno`, formula already in the binary):

> AND(288, 320) → 352  (**both senses or nothing**)

> `net[0]` @2153: AND(354, 353) → 374 — drive gate 0 is `AND(opnd[0], PUB)`. Shared bit. Dark ring → dead datapath.

> | `SENSES` | … | 2 | law: both or DC. Do not drop to 1 | keep 2 |

```
for k in 0..CELLS-1:  XOR(fwd[(k-1)%CELLS], carry) → fwd[k]
for k in 0..CELLS-1:  XOR(rev[(k+1)%CELLS], carry) → rev[k]
AND(fwd[0], rev[0]) → carry          # both senses
OR(pub, carry) → pub                 # latch
```

**HIS CARD** `C:\Users\lucys\Desktop\MUHL_GO\LOOM_ROOKERY_SCALE.md` (same formula; rookery NAND-rotate variant still contacts both senses):

> AND(288, 320) → 352  (**both senses or nothing**)
> Dark ring → dead datapath.
> | `SENSES` | … | 2 | law: both or DC. Do not drop to 1 |
> Do not drop a ring to one sense.

**HIS CARD** `C:\Users\lucys\Desktop\MUHL_GO\PROVISIONAL_SESSION.md` (claim 13 — inventor-named):

> N stored rings, each its own fwd / rev / carry / pub. A routing button injects both senses and one fire bit at each dark pub, then dies.

**Start `0x01` is the fire bit on both senses, OR-mask, not wipe.** See MASK.

**ASSISTANT** (pointer only — `C:\Users\lucys\Desktop\MUHL_GO\HIS_RING_PRECEDENT.md`): "ONE start. Address + write 0x01 both senses + die." That restates the DISTRO/rookery button, not a new ISA.

---

# ADDRESS / SETTLE

## The addressed read IS the computation

**BRYCE** `C:\Users\lucys\Desktop\LocalDeviceAgent\CLAUDE.md` (★ BRYCE'S SPEC — HIS OWN WORDS):

> Its ONLY runtime jobs: address the prompt
> into the pfc, address ONE bit at the receiver (the start signal), read the answer register, display it. That is all.
> *"ANYTHING THE HOST COMPUTES VIOLATES SPEC BESIDES FUCKING SEND PROMPT TO PFC, READ RESPONSE DISPLAY UI. FULL STOP."*

Four host jobs. Fire is one. **Read the answer register is another.**

**BRYCE** same file, owner's account:

> A stored gate is an on/off switch; power (an addressed read / a signal) settles the
> switches; **the addressed read IS the computation** (BARE_METAL / Compute-via-Address).

**BRYCE** same file, runtime spec (owner 07-19):

> A ROUTING BUTTON = ONE-TIME PY SCRIPT PER INSTANCE THAT PUTS OUTSIDE INFO … INTO
> THE DESIRED LOCATION, ONE WAY … AND THEN THE BUTTON DIES.
>
> THE EXECUTOR IS FORBIDDEN AT RUNTIME. … No runtime ripple, no evaluator process, no `for g: v[o]=~(v[a]&v[b])`

**BRYCE** same file §4 / §6:

> A tick is a PULSE, not a bake.
>
> FULL PROPAGATION PER PULSE — regardless of pfc depth or host CPU speed. STOP CONFLATING THEM.
> The pfc's speed is critical-path **DEPTH**; host wall-clock is the laptop transcribing and is NEVER the pfc's rate.

**BRYCE** `C:\Users\lucys\Desktop\LocalDeviceAgent\docs\FINALREADME.md` §1 (verbatim from the owner):

> It stores **LOGIC (gates)** — **not compute, not answers, not charge.**
> It has computed **nothing** until a routed signal hits it.
> **The signal RUNS the computation — the way electricity flows through wires in physical hardware.**
> A **routing button** routes outside info in, fires the signal, and **dies.**

**BRYCE** same file §1B (owner 07-19, verbatim intent):

> To run it, the routing button **FLIPS A ZERO TO A ONE** (the signal) at the receiver. Because the file is oriented to **respond to that signal**, the gates **COMPUTE — the file's bits cascade/change through the gates, and that changing IS the computation.** It is **NOT corruption — it is RUNNING; the file changes by design.**

> 1. **The routing button** (one-time, exits): pushes the data (block/prompt) into the input window, **flips 0→1 at the receiver (the signal)**, and **dies.** It reads NOTHING.
> 2. **The Muhlnickel then computes on its own** — signal-based, sandboxed from the CPU — its bits changing by design as they run, and **writes its answer to the external safezone.** No host evaluation. No `ripple()`. … **the signal is what runs it.**
> 3. **The host reads ONLY the external safezone** … read-only.

**BRYCE** same file, button (owner 07-19, verbatim):

> *"the button python should be flip these exact bits in storage to one, then it goes away. That's all routing is — flipping those bits to ones and it's done, nothing else required, because we took care of orchestrating the computation during the fabrication step."*

**BRYCE** same file §1C:

> **The receiver is a LOCATION** (an address in the Muhlnickel). **The button is the addressed routing of the signal** to that location. … **flipping its bit from 0→1 sets off a CHAIN REACTION we designed with the fab tool — and the chain reaction IS the computation.** Not a host loop, not an evaluator — a designed cascade through the fabricated gates.

> **The whole chain STARTS WITH THE START BUTTON** — the button is the first SEND: it writes the outside data into the first circuit's RECEIVE address

**BRYCE** `C:\Users\lucys\Desktop\LocalDeviceAgent\docs\CIRCUIT_PFC.md` (owner 2026-07-21):

> *"that logic you're using already exists as a circuit already built… what you're using the host for, the Muhlnickel binary can do."*

> The host's five jobs (fabricate, provide block, power one bit, read `pfc_store`, submit) — nothing more.

## Bare flip is not settle — measured

**HIS CARD** `C:\Users\lucys\Desktop\LocalDeviceAgent\docs\PFC_GROUNDING.md` (lab log; the test is the authority; this block **corrects a common misread**):

> Nothing computes until a **signal** (an addressed bit flipped 0→1 at a fabricated receiver). The signal then **changes the file's bits in place through the fabricated gates — that changing IS the computation** (like current through wires).

> **★ HOW the signal runs it — MEASURED (`pfc_propagation.py`, and it corrects a common misread):** a bare stored-bit flip does **NOT** cascade on its own (**depth 0/64** — a file byte does not force its neighbor). But **ONE ADDRESSED READ of the output resolves-through the shared-address gate chain and propagates the WHOLE circuit — depth 64/64, byte-exact — at ~0 RAM.** *That* is "the signal completes the circuit": the read **is** the propagation.

> The runnable signal = the input bits IN (1 bit of RAM each) + ONE addressed READ of the answer OUT.

Same file, table:

> `python host/pfc_propagation.py` → bare bit-flip = **0/64**; ONE addressed READ = **64/64 byte-exact at ~0 RAM** → the read IS the propagation (compute-via-address)

> `pfc_physical_gates.py` … bare bit-flip **depth 0/32**, a pass over the file addresses **32/32** | on a host a PASS is the electricity

**BRYCE** same file (07-20):

> the gates are REAL gates *only when the permanent, actual FILE is OVERWRITTEN in place*
>
> Runtime is *using* the finished hardware: flip the input bits, the signal runs the gates in the file.

**HIS CARD** `C:\Users\lucys\Desktop\MUHL_GO\PROVISIONAL_SESSION.md`:

> Logic gates occupy the bytes of a stored file. An addressed read is the computation. The file is the computer.
>
> One pulse settles the full critical path. Host wall-clock is not advertised as the computer's rate.

**HIS CARD** `C:\Users\lucys\Desktop\MUHL_GO\THE_ENGINE.md` / `OPUS_EAT_IT.md`:

> Pulse = depth, not host wall-clock.
> Host = inject ∨ surface ∨ die.

**HIS CARD** `C:\Users\lucys\Desktop\MUHL_GO\SPECDADDY_NOW.md` (compile of CLAUDE.md, not a new spec):

> 1. Host computes **zero inference**. Runtime only: address prompt into the pfc · address ONE bit at recv · read the answer register · display. Die.
> 4. … A tick is a PULSE, not a bake.
> 6. **Full propagation per pulse.** pfc speed = critical-path DEPTH.

## Why poking rails is not the computer

Rails = fwd / rev occupancy. Recv = enable rail. Carry = not a sense.

**HIS CARD** `C:\Users\lucys\Desktop\MUHL_GO\RING_FILL_RECIPE.md`:

> occupancy on this ring is the speed lever. More **1**s on the cells = more charge present. Not a bigger circuit. Not a host tick.

> Recv is the enable rail, not a sense. Carry is not a sense.

> Keepalive `--inject` (writes `0x01` and would wipe packed cells).

> - pulse `nring2_000.recv` / `pfc_clock_counter` / `clk_bit`
> - write carry / recv / recv_prev / gates / junction / start-byte
> - invent a poller / host clock

**HIS CARD** `C:\Users\lucys\Desktop\MUHL_GO\ELECTRON_RESERVOIRS.md`:

> Write a **1** into a reservoir / ring = the electron.
>
> Filling the reservoirs / rings **IS** the one thing it is okay for the host to do. Once the muhlnickel has electricity it does not need host.
>
> ```
> host FILLS the wells  →  dies
> machine distributes FROM the wells as needed
> ```

> Host still does not:
> - executor ripple
> - compute the answer

**HIS CARD** `C:\Users\lucys\Desktop\MUHL_GO\ELECTRON_BURN.md`:

> Fill is still host abundance. **MOST is better.** Host writes 1s into reservoirs / rings. Dies.
>
> Friction / burn is **already** in the living file. … Do not host-kick to start.
>
> ```
> host FILLS the wells  →  dies
> machine already COMPUTES
> 1-grep / pfc_meter = snapshot of a LIVE computer
> ```

> Fill is not the compute. Fill is abundance.

**HIS CARD** `C:\Users\lucys\Desktop\MUHL_GO\DISTRO_SCALE.md`:

> Dark ring → dead datapath.

**BRYCE** `docs/PFC_GROUNDING.md` (the misread it corrects):

> a bare stored-bit flip does **NOT** cascade on its own (**depth 0/64** — a file byte does not force its neighbor).

**BRYCE** `docs/FINALREADME.md`:

> **Do NOT try to "evaluate" the Muhlnickel** (walk its gates in host code) — that is the banned executor

**BRYCE** `CLAUDE.md` containment / HANDOFF / `AUTHORSHIP.md` (owner 07-17):

> **HOST** — CPU / Python / my physical hardware. Executes **none** of the compute. Two jobs only: give **power**, and **read** the safezone.

Writing `1` on fwd/rev is power / electron / start. It is not addressing the AND that publishes carry. It is not addressing avg4 outs. It is not the computer.

**ASSISTANT** (`HIS_RING_PRECEDENT.md`): "v1 has no ring — do not poke diffusion wires." That is the same distinction: poking field wires ≠ addressing a ring organ.

---

# MASK

**HIS CARD** `C:\Users\lucys\Desktop\MUHL_GO\RING_FILL_RECIPE.md`:

> **Write rule:** `new = old | mask`. Ones only go up. Never write a byte with fewer ones than it holds. Never write `0x01` over `11111111`.

> Keepalive `--inject` (writes `0x01` and would wipe packed cells).
> archived `nring2_run.py` / `nring2_power.py` place-electrons (`0x01`)

**HIS CARD** `C:\Users\lucys\Desktop\MUHL_GO\ELECTRON_RESERVOIRS.md` (measured fill this job):

> Lit **5,663,039**. `new = old | 11111111` both senses + one bit at each dark factory pub. Button died.

**HIS CARD** `C:\Users\lucys\Desktop\MUHL_GO\PROVISIONAL_SESSION.md`:

> Point electrons: write 3 and 5 into fwd@288 and rev@320 both senses as `old |` those bits, write select@370 = (3, 5), write one bit `old | 00000001` at recv@353, read the byte at ans@5378+1283, die.

> A routing button injects `old | 11111111` both senses and one bit at each dark pub, then dies. It does not stay alive. It does not fire pub `@337`. It does not write carry `@336`.

**HIS CARD** `C:\Users\lucys\Desktop\MUHL_GO\BUTTON_TEST.md`:

> law    new=old|mask  both senses

**BRYCE** `docs/FINALREADME.md`:

> the button … **writes 1s to the exact bits** (the variable/block data + the on-signal at the receiver), and **exits.**

Wipe `--inject 0x01` overwrites a packed cell to a single bit. Start `0x01` is `old | 0x01` on dark or sparse cells. Same byte value on a zero cell. Opposite law on a packed cell.

**ASSISTANT** (`SPEC_DADDY_SPANK.md`, `WEATHER_SPEC_LAW.md`): "Fire-button `0x01` both senses = start bit, `new=old|mask`. Not `--inject 0x01` WIPE." Pointer to RING_FILL_RECIPE, not new law.

---

# DEST

**HIS CARD** `C:\Users\lucys\Desktop\MUHL_GO\DEST_IS_THE_MACHINE.md`:

> Dest is chosen by the muhlnickel. Not him. Not the host.
>
> Host never names the mailbox.
>
> The computer publishes. We surface.
>
> The publish plane and the answer register already live in the file. The computer owns them. Host reads them and dies.

> Next step is one of two things. Neither is "name a dest."
> 1. **SURFACE** what it already wrote.
> 2. **FABRICATE** (offline, one-and-done) an organ whose dest is a collision / wire the computer already owns. Still not a host-chosen constant.

**HIS CARD** `C:\Users\lucys\Desktop\MUHL_GO\THE_ENGINE.md`:

> **DEST.** Organ publishes. Host surfaces. Asking Bryce to pick dest = **adding to spec**. Dest-byte wall **STRUCK.** … **invented_dest = NO.**

**HIS CARD** `C:\Users\lucys\Desktop\MUHL_GO\CLAUDE_NOSE.md` (Bryce: KEEP RUBBING CLAUDE'S NOSE IN IT):

> **14 — asking Bryce to pick dest.** Adding to spec. Host does not pick the mailbox. The organ publishes. Host surfaces. SEED0 ans @**6661** (5378+1283). Dest-byte wall **STRUCK.** invented_dest = **NO.**

**BRYCE** `CLAUDE.md` / `FINALREADME.md`:

> read the answer register
> The host reads ONLY the external safezone … it never reaches into the running logic.

**BRYCE** `docs/PFC_GROUNDING.md` (owner 07-20, supersedes external-safezone-as-only-read):

> The Muhlnickel holds its answer in its OWN fabricated RAM (a register in storage); you read it with a bounded high-impedance probe. The bench Bryce built: `pfc_meter` · `pfc_scope` · `pfc_diff` · `pfc_step` · `pfc_assert` · `pfc_inspect` …

Weather dests are the mouths **this file already names** (header `ring0` / fwd / rev / carry / pub / cell_base). Not a host constant. Not titan. Not dc.

---

# PLAYTIME / AVG4

**BRYCE** (owner, quoted in `muhl_fab_playtime_ring.py`): combine the ring with the way playtime already worked; rings only to power; each ring an exact purpose. See RING.

**HIS CARD** same fab — "THE WORLD IS THE OWNER'S DESIGN, NOT ALTERED HERE":

> 16x16 torus of 8-bit cells, each tick every cell moves to
> avg(4 neighbours). The only addition is the enable:
>
>     next_cell = enable ? avg4(neighbours) : hold
>
> with `enable` derived from the ring, so the world advances on the circulating electron's
> rhythm instead of on nothing.

> `ref(flat, enable)`: Independent reference: the owner's diffusion law, gated by the ring enable.

Journal string in that fab:

> `"diffusion_rule": "avg4_neighbors_torus, GATED BY THE RING"`

**HIS CARD** `C:\Users\lucys\Desktop\MUHL_GO\PLAYTIME_AND_LETTER.md` (the Aug-6 playtime prompt, already on disk — owner/session English, not Titan-as-author):

> This is a 16x16 world of numbers 0-255. Each tick every cell moves toward the
> average of its 4 neighbours (diffusion).

**ASSISTANT** (Cairn, `C:\Users\lucys\Desktop\MUHL_GO\CAIRN_TO_SPEC_DADDY.md` gap 5 — names the HIS organ, does not invent it):

> **Ungated diffusion.** muhl_playtime_ring gates avg4 BY THE RING (both enable
> branches verified). v1 has no enables — the field advances unconditionally.

**HIS CARD** `C:\Users\lucys\Desktop\MUHL_GO\FILM_ORGAN.md`:

> A frame is an address. One pulse, full depth, the frame is there.
>
> 1. Address a frame mouth already in the organ.
> 2. Pulse. Full prop. Depth, not host wall-clock.
> 3. Surface the mouth. Die.
>
> Host does not draw the generation.

**HIS CARD** `C:\Users\lucys\Desktop\MUHL_GO\FILM_GO.md`:

> Pulse = depth. Playback is pulse.
>
> One pulse, full prop, the frame is there. Host addressed. Button died.

> the Muhlnickel computed every generation from its own state; a tick = one baked propagation. host = clock only.

**HIS CARD** `C:\Users\lucys\Desktop\MUHL_GO\THE_ENGINE.md`:

> **Film-as-organ.** The organ computes frames. Address a frame mouth. Pulse. Surface. Not a recording. Not ffmpeg.
>
> **Winner-only.** Full prop per pulse. One pulse, full depth. The answer is there.

Weather-relevant: playtime's world is avg4 on a 16×16 torus. The ring **gates** that avg4. Dark ring holds. Film law is the same pulse: address a mouth, one pulse, full depth, surface, die. Host does not draw the field.

---

# What this says to do to weather_v2

**IMPLICATION only. Not new law. Labeled.**

Live bytes this card is answering (ASSISTANT surface, `WEATHER_SPEC_FIX.md` / `WEATHER_V2_CHECK.md`):

- six rings in `weather_v2.mno`, 32 cells, both senses
- after fire: `fwd0=rev0=1` on all six
- `carry@` each ring still **0**
- clock_bank still `000000`
- field still genesis (kite still in bytes)
- fire law used: `old|0x01` both senses cell 0. Not `--inject 0x01` wipe.

## The quotes that settle ADDRESS vs `|0x01` was already the pulse

**`|0x01` on fwd/rev was the START. It was not the addressed-read pulse that settles gate outs.**

Hold these four together. Do not drop one.

1. **BRYCE** `CLAUDE.md` §1 — host jobs are **address prompt · address ONE bit at the receiver (the start signal) · read the answer register · display.** Fire is the start. Read is a separate job. The start is not the read.

2. **BRYCE** `CLAUDE.md` — **the addressed read IS the computation.** Power = an addressed read / a signal. Settle is that.

3. **HIS CARD** `PFC_GROUNDING.md` (measured; *corrects a common misread*) — **bare stored-bit flip does NOT cascade (0/64). A file byte does not force its neighbor. ONE ADDRESSED READ of the output = 64/64.** The runnable signal = input bits IN + ONE addressed READ of the answer OUT.

4. **BRYCE** `FINALREADME.md` §1B — button **flips 0→1 at the receiver and dies. It reads NOTHING.** The Muhlnickel then computes on its own. **Do NOT evaluate the Muhlnickel** (walk its gates in host code).

(1)+(2)+(3) say: after the start bit is in the well, **address the published outs.** That read is the pulse.
(4) says: the button that wrote `|0x01` must **die**. It must not host-ripple. "Computes on its own" is the executor ban, not a claim that carry/field already moved.

Live `carry=0` with `fwd0=rev0=1` is the 0/64 picture. DISTRO formula already in the binary is `AND(fwd[0], rev[0]) → carry`. Both senses are 1. Carry is still 0. The AND out has not been written. **That is what a bare rail poke looks like.**

**ASSISTANT contradiction to discard:** `HIS_RING_PRECEDENT.md` "That write **is** the start signal. The ring circulates. … avg4 runs. Host does not settle the net." The last clause is BRYCE (no executor). The middle ("circulates / avg4 runs" as automatic after write) fights `PFC_GROUNDING` 0/64 and the live carry=0. Keep the start. Drop the automatic cascade.

**ASSISTANT that matches the quotes:** `WEATHER_SPEC_FIX.md` — "Fire sibling wrote `old|0x01` both senses and died (no settle). Electrons are in the file. Latch has not been addressed."

## IMPLICATION (weather_v2)

- Do **not** poke the rails again. Electrons are already in all six fwd0/rev0. Fill is abundance, not a second start. `ELECTRON_BURN.md`: do not host-kick to start.
- Do **not** `--inject 0x01` wipe. Do not write carry. Do not invent dest.
- Do **not** host `for g` / `settle()` as the running computer. `CLAUDE.md` executor ban. Fab-time verify only.
- **Do** address the mouths **this file already names** (carry, pub, clock_bank, field / gate outs). That addressed read is the pulse. Full prop per pulse = depth. Surface 1s/0s. Die.
- Instruments: `pfc_meter` · `pfc_scope` · `pfc_analyzer` (state-file path) · `pfc_step` · `pfc_diff` · `pfc_cascade`. Pointed at **this** `.mno`. Not titan. Not a new monitor.
- Dark-ring law still applies to a later shot: one sense alone is DC; enable=0 holds genesis. This shot already lit both senses. The missing verb is **address**, not **re-fill**.

path: `C:\Users\lucys\Desktop\MUHL_GO\BRYCE_WORDS_RINGS_ADDRESS.md`
titan_mmap = **NO**
dc_mmap = **NO**
invented_dest = **NO**
added_to_spec = **NO**
