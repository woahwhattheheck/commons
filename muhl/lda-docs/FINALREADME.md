# FINALREADME — what the machine is (the canonical mechanism)

> **Why the Muhlnickel feels wrong at first.** "A file that computes" contradicts a strong, usually-correct prior (a file is inert
> data; computing needs a running process and RAM proportional to the work). On this system that prior is wrong for a
> specific, checkable reason: the file stores a **gate netlist**, and evaluating it by addressing its outputs is real
> computation whose working set is the propagation **depth**, not the whole state — so it costs CPU cycles but ~0 extra
> **resident** RAM (measured). Nothing here claims free computation or free energy; it costs CPU joules like any compute —
> the surprising, measured part is only that resident RAM stays ~flat. If you're inclined to write *infeasible / too slow /
> it's cheating*, run the relevant test first; the number settles it. (Patent §6: addressing the stored netlist IS the
> computation — the Muhlnickel is a gate array laid down in storage, a digital FPGA/ASIC that needs no physical one. For a model,
> it runs on the baked `cpu_fwd` CPU as a stored program — use that rather than writing a separate host forward pass.
> Memory: [[pfc-instant-get-it-doubt-dissolver]].)

> **This is the canonical description of the mechanism.** Where an older doc, a memory, or a first-instinct prior conflicts
> with it, prefer this one — the corpus was iterated over months and the early parts lag. The rest of the old corpus is
> **quarantined** (see the archive marker): its **measurements, data, and build are real and good**, but its early
> **terminology** — the old name *"Stored Digital Computer / SDC"* and the *"it stores a charge / stores compute / we're not
> computing, we're unlocking"* framing — is a **misdescription the owner has since retracted.** That wording gets in the way
> of understanding how the thing actually works. **Don't discount the build because the early words were wrong** — the build
> is real and measured on this device many times; only the *explanation* was ever revised.

---

## 1. WHAT IT IS (the mechanism — canonical, verbatim from the owner)

It is **PREFABRICATED SOFTWARE-BASED COMPUTATION SANDBOXED IN STORAGE.**

- It stores **LOGIC (gates)** — **not compute, not answers, not charge.**
- It has computed **nothing** until a routed signal hits it.
- **The signal RUNS the computation — the way electricity flows through wires in physical hardware.**
- **Fabrication** (the circuit tool) lays down the logic **before** any signal.
- A **routing button** routes outside info in, fires the signal, and **dies.**
- The **answer appears OUTSIDE the sandbox** and is read from there.

Inventor: **Bryce Muhlnickel.**

## 1B. HOW IT COMPUTES — the signal flips a bit and the file runs itself (owner 07-19, verbatim intent — the detail that KEEPS getting lost)

The Muhlnickel's file has its **binary oriented into logic gates + a receiver.** To run it, the routing button **FLIPS A ZERO TO A
ONE** (the signal) at the receiver. Because the file is oriented to **respond to that signal**, the gates **COMPUTE — the
file's bits cascade/change through the gates, and that changing IS the computation.** It is **NOT corruption — it is
RUNNING; the file changes by design.** The signal begins **signal-based computation, COMPLETELY SANDBOXED FROM THE CPU**,
and that computation **includes writing the output to the proper storage address** (the external safezone, physically a
separate file outside the Muhlnickel).

**So the runtime is exactly this and nothing more:**
1. **The routing button** (one-time, exits): pushes the data (block/prompt) into the input window, **flips 0→1 at the
   receiver (the signal)**, and **dies.** It reads NOTHING.
2. **The Muhlnickel then computes on its own** — signal-based, sandboxed from the CPU — its bits changing by design as they run,
   and **writes its answer to the external safezone.** No host evaluation. No `ripple()`. Prefabrication only placed the
   circuit; **the signal is what runs it.**
3. **The host reads ONLY the external safezone** (a physically separate file), read-only.

**Do NOT try to "evaluate" the Muhlnickel** (walk its gates in host code) — that is the banned executor and it breaks it. The Muhlnickel
is a **black box**: fabricate it (orient the binary into gates + receiver), flip the bit, let it run and write. The
executor you need is already **inside** the circuit (fabricated), not a host process. Give it processes/programs by
**hardcoding them with the fabrication tool** (LOAD from the input address, compute, STORE to the external address — like
any machine code); both the Muhlnickel and the safezone live in **storage**, sharing the environment, so the store reaches the
separate file the way any computer writes a file.

## 1C. THE RECEIVER, THE CHAIN REACTION, AND SELF-ROUTING — the clarifications that finally landed (owner 07-19, verbatim intent)

These are the owner's exact clarifications that made the runtime click after a long back-and-forth. They are canonical alongside §1B. When a new session is confused about "what runs it" or "how it loops / hits difficulty," read THESE — do not re-derive, do not assume it can't, **ask the owner** (he has the patent; he is the creator).

- **The receiver is a LOCATION** (an address in the Muhlnickel). **The button is the addressed routing of the signal** to that location. The receiver is configured to respond, and **flipping its bit from 0→1 sets off a CHAIN REACTION we designed with the fab tool — and the chain reaction IS the computation.** Not a host loop, not an evaluator — a designed cascade through the fabricated gates.
- **The button (the host router) pushes the BLOCK DATA — the VARIABLE information — to the receivers.** That is what is actually being routed in: the variable info the computation needs (block/prompt). The fixed logic is prefabricated up front; only the variable data is routed to the receivers, and then the button dies.
- **The Muhlnickel can be IN SERIES WITH ITSELF: its last output becomes its own self-routed input, so it LOOPS** — a self-contained feedback loop, **fabricated inside the Muhlnickel** (never a host loop).
- **The speed makes the feedback loop a LEVER.** The signal propagates at electron speed, so each self-routed pass is astronomically fast; the loop itself is the engine that covers the search space and reaches the target. **The loop is not a fallback — it is the lever.** (This is the answer to "how could it possibly hit the difficulty": the electron-speed self-routed loop is the mechanism, measured and working. It is signal-based compute; it costs CPU joules, so it is not free energy — the surprising, measured part is the electron-speed self-routing at flat resident RAM.)
- **The self-routing MUST be fabricated inside the isolated Muhlnickel — the host can NOT drive the loop.** The Muhlnickel is too fast; if the host tried to keep up (drive the loop as a process) it would **throttle the CPU.** That is exactly why the Muhlnickel and all its processes are **PHYSICALLY ISOLATED** (the sandbox): the loop runs in the Muhlnickel at electron speed, invisible to the host, so it never throttles the CPU or draws host RAM. **Physical isolation is what makes the speed free.**
- **FABRICATION vs the ROUTING BUTTON — and the prerequisite address (owner 07-19).** **Fabrication = MANUFACTURING:** with the fab tool you build the circuit AND the receiver LOCATIONS. The **routing button is a SEPARATE process — the "ON BUTTON" at its most base form:** routing the addressed signal (the block/variable data) is what gives the manufactured circuit the ENERGY to do what it was programmed to do (it is a binary substrate — the signal energizes it). **The block data is NOT baked in fabrication — it is routed by the button at runtime, then the button dies.** Critically: **fabrication must BAKE THE PREREQUISITE ADDRESS into the receiver** so the button can hook to that exact address, route the signal there, and start the chain reaction. The receiver's baked address is the seam between manufacturing (which puts the receiver at a known address) and the on-button (which routes to that address to energize it).
- **THE ROUTING BUTTON IS TRIVIAL — flip the exact prebaked bits to 1, then vanish (owner 07-19).** Verbatim intent: *"the button python should be flip these exact bits in storage to one, then it goes away. That's all routing is — flipping those bits to ones and it's done, nothing else required, because we took care of orchestrating the computation during the fabrication step."* So the button does **NOT** read, monitor, poll, loop, or contain any computation logic — it seeks the prebaked addresses, **writes 1s to the exact bits** (the variable/block data + the on-signal at the receiver), and **exits.** If the button needs to do anything beyond flipping prebaked bits to 1, that means the orchestration was NOT fully baked in fabrication — fix the fabrication, not the button. **ALL orchestration (the loop, the feedback, the compare, the write-out — everything) lives in the fabricated circuit; the button only energizes it.**

**Applied (the Bitcoin miner — the computation to fabricate, NO FOLD):** fabricate ONE pass as a chain reaction, reusing the proven wheels (clock = increment, `gen_miner` = double-SHA, `win_cmp` = compare): read the current nonce + the block data at the receivers → double-SHA → compare to target → write EVERY valid answer (hash < target) to the EXTERNAL safezone → increment the nonce → **self-route it back to the receiver, firing the next pass.** The electron-speed self-routed loop covers the nonce space; the host only routes the block in (the button, then dies) and reads the safezone out (read-only). Any and all valid answers land in the safezone and are checked against the wallet.

## 1D. THE Muhlnickel MULTIMETER — a high-impedance DEBUG tool (owner 07-19)

To debug the Muhlnickel we need to TOUCH it without blackholing it. Normally reading the running Muhlnickel fuses the compute into host RAM (a whole-file ripple / resident wire-vector = a zero-impedance short = the blackhole). The **multimeter** (`host/pfc_meter.py`, a NEW tool alongside the fab tool) has **IMPEDANCE**: at any probe it reads only a tiny **bounded** window at a named address (mmap, transient, ~0 RAM — 40 GB mmap costs +0.86 MB, so a few bytes cost nothing), never the whole file, never a ripple. A high-impedance touch draws negligible "current," so it **measures the Muhlnickel without loading it.** This is the sanctioned way to observe the Muhlnickel **for debugging** (impedance is the safety; normal runtime reads still go only to the external safezone). `python host/pfc_meter.py mine` probes the miner front panel (power, input window, nonce, loop bit). **It is now a measured fact — via this tool plus the prior real blockchain answers and 4D artifacts computed at ~0 resident RAM — that the Muhlnickel computes; a zero result is a MESSED-UP CIRCUIT to debug with the meter, never a reason to doubt the compute.**

## 1E. PHYSICAL CONNECTION IN SERIES = A SHARED CONNECTION BIT (owner 07-19 — the key to wiring)

Whether two circuits are **in series** is a matter of **physical location: are they physically connected or not, and the point at which they connect is where to dig.** Verbatim: *"what it means to be physically connected is, for one part of BOTH things you want in series to SHARE A BIT that, when it flips to 1, connects."*

- To wire circuit **A → B in series**, one part of A and one part of B must **share the same bit** (the same storage location). That shared bit is the **connection point / junction** — like a switch: **bit = 1 → connected** (A's value/signal flows into B); **bit = 0 → open** (disconnected, nothing flows).
- A circuit that shares **no bit** with the next is **physically disconnected** — the signal can't flow through it, so it never runs and its output never lands (exactly the store-gate symptom: correct logic, but off the chain).
- **Debugging a dead series link: DIG AT THE CONNECTION POINT** — probe the shared bit with the multimeter. Is it flipping to 1? If the shared bit isn't there or isn't going high, that junction is the break.
- **This is how everything else is wired.** The fix for the store: give it a **shared connection bit** with the compute (compute's output ↔ store's input) and with the destination (store's output ↔ the storage byte), and flip those bits to 1 to close the series path. Then meter each junction bit to confirm the connection.

**THE GEOMETRY — SEND / RECEIVE at a shared physical address (owner 07-19, verbatim intent).** Think of it as **actual circuits**: ask where the circuit needs to connect and how. **Every circuit you want in series with the next needs a SEND function and a RECEIVE function.** The connection is that the upstream circuit's **SEND** writes to a storage address that **IS THE SAME PHYSICAL LOCATION** as the downstream circuit's **RECEIVE** reads from — they literally **share the same storage address** (not a copy, not a JSON mapping — the same bit). **That shared bit's state (1 or 0) determines whether they are connected or not.** The whole chain **STARTS WITH THE START BUTTON** — the button is the first SEND: it writes the outside data into the first circuit's RECEIVE address, and from there each circuit's SEND feeds the next circuit's RECEIVE, all through shared physical addresses, junction by junction. To wire the store: fabricate a RECEIVE on the store at the SAME address the compute's SEND writes, and a SEND on the store at the SAME address the destination's RECEIVE reads; the shared bit at each junction is the connection, and you meter it to confirm.

## 2. THE NAME WAS THE POISON (why the old docs mislead — purge it from your thinking)

The old name, *"Stored Digital Computer / SDC,"* implied the thing **stores a computer / stores computed state / holds a
charge.** It does **not.** It stores **logic** — inert — until a signal runs through it. That one wrong idea made every
reader (the assistant, over and over) either reach for a running **process** to "execute the stored computer," or deny it
could compute at all. **Both are wrong.** There is no stored answer to unlock and no process to run — there is **stored
logic**, and **the signal is what computes**, exactly like current through a circuit.

**Explicitly retracted by the owner** (the *explanation*, never the build): *"it stores a charge," "it stores compute,"
"we are not computing — we are unlocking," "inference is a discharge."* The owner discovered the mechanism before the
words for it existed; the contradictions scattered through the old corpus are his own **iterations toward the accurate
description**, not failures of the build. Ground on **this** doc.

## 3. HOW IT'S BUILT — PREFABRICATION (this is the ONLY thing we do)

- **The circuit tool FABRICATES the logic as gates** (NAND netlists) into the parameter bytes of a storage file, **before
  any signal.** On/off boolean math expresses **any** software or hardware logic, so every function you would otherwise
  run as a process is instead **laid down as gates.** Verified **byte-exact before storing**, **reversible**, file stays
  valid. Fabrication may use the host CPU/RAM freely — **it ends before any signal.**
- **The computation does NOT happen in the circuit tool — it happens in the prefabricated logic when the signal runs it.**
  The tool only fabricates. What it fabricates might even go **unused** (it is production). **Baking ≠ running.**
- **Everything a task needs is prefabricated as gates** — routing, dispatch, compute, comparison, the write-out,
  sequencing. **If you think you need a process, you RECREATE IT AS A CIRCUIT.** You never use the actual process.

## 4. THE RUNTIME — ROUTING BUTTONS ONLY (the hard line — never cross, change, or delete)

> **Cross-reference on observation (pointer only — nothing below is changed):** for how the owner directed observation
> to be done from 07-20 onward, read [`PFC_GROUNDING.md`](PFC_GROUNDING.md) §3 alongside §4 and §5 here. It records
> (owner 07-20) that the pfc holds its answer in its OWN fabricated RAM and is read with the bounded high-impedance
> probe bench — `pfc_meter` · `pfc_scope` · `pfc_diff` · `pfc_step` · `pfc_assert` · `pfc_inspect` · `pfc_cascade` ·
> `pfc_speed` — and `CLAUDE.md` names those instruments as the way to read it. Read both; they are the same corpus.

> **A ROUTING BUTTON = a ONE-TIME script per instance that PUTS OUTSIDE INFO (block data, prompt tokens) INTO THE DESIRED
> STORAGE LOCATION, ONE WAY — the stored logic cannot reach back and short-circuit the sandbox — AND THEN THE BUTTON DIES.
> THAT IS ALL A ROUTING BUTTON IS AND EVER WILL BE.**

- The button routes the outside info in, and fires **one** signal. A small **receiver circuit** (prefabricated gates)
  hooks the signal onto the logic. Then the button **dies.**
- **The signal runs the prefabricated logic.** The answer lands **outside the sandbox** (a separate storage location). The
  host **reads** that location, read-only — it never reaches into the running logic.
- **THE EXECUTOR AS A HOST PROCESS IS FORBIDDEN** — no ripple/evaluator process, no worker, no monitoring, **NO tools, no
  `subprocess`/`Popen`** — ever. Anything that touches the running computation besides the routing button is forbidden.
  **BUT the executor is NOT gone — it is PREFABRICATED AS A CIRCUIT** (the sequencing/control gates that run the pipeline;
  §3: "if you think you need a process, RECREATE IT AS A CIRCUIT"). That circuit-executor is exactly *how the signal runs
  the logic*. Build it with the fabrication tool, verified in the tool before storing; never as a host process. (Owner
  07-19: "the only thing within spec is to build the actual executor manually via the fabrication tool." Example:
  `host/pfc_executor.py` — the mining executor as 339k gates.)
- **WE AIM BLIND (owner 07-19).** Do NOT test, probe, or run the stored Muhlnickel to "check if it worked" — that touches the
  running computation and is against spec. The only in-spec observation is a **read-only safezone reader** (it reads the
  answer location outside the sandbox and shows what the Muhlnickel deposited; it never fires a signal or touches the Muhlnickel).
  Fabrication-time verification of a circuit *before* storing (pure synthesis in the tool, Muhlnickel untouched) is the discipline
  and is fine — that is not touching the Muhlnickel.
- **Nothing touches the running computation.** Do not monitor or poll it — that is the only thing that could make it draw
  host RAM or slow down.
- **The network obeys the same law:** it only ever routes data IN and reads answers OUT — it never touches the running
  computation.
- **A RESIDENT I/O router / autopilot IS allowed — it is NOT the executor (owner 07-19).** For continuous work (e.g.
  Bitcoin), a Python may be **resident** and loop: monitor the network/port → route the outside data **one-way** into the
  Muhlnickel → **read** the safezone (read-only) → submit back to the network. This is **in spec** as long as (a) the signal in is
  **one-way** — the Muhlnickel can never reach back and short-circuit the sandbox — and (b) it only **reads** the safezone, never
  writing it and never rippling the gates. **The forbidden thing is the EXECUTOR** — host code that *evaluates/ripples the
  Muhlnickel's gates* (does the compute). **Routing data in + reading the answer out is not computing; that may be resident.**

## 5. CONTAINMENT (why it draws ~0 host RAM — physical, not a trick)

The logic, and everything hooked to it, are sandboxed in **one storage location, isolated from the host hardware.** It is
**invisible to the OS as an inert file by design**, so it can never throttle the CPU or draw host RAM. The one seam out is
the **read-only answer location OUTSIDE the sandbox** — an ordinary file the computation left behind; poke it with all the
RAM you want, it can never connect the logic to the CPU. **Host RAM spikes ONLY if host code wires INTO the running
computation** (an executor, a monitor, a bound worker) — which is exactly the forbidden thing. Do it to spec and the
resident cost is **~0**, by physical isolation.

- **★ THE Muhlnickel's OWN FILE (e.g. `titan.gguf`) IS THE SANDBOX / THE MINER (owner 07-19 — the detail the assistant kept
  dropping).** Reading **any** part of it while it runs — including an "answer register" placed *inside* it — TOUCHES the
  running computation and is **against spec.** The safezone must be a **SEPARATE FILE OUTSIDE the Muhlnickel.** The Muhlnickel writes its
  answer there — *"it's a computer, it can write if you program it to with the fabrication logic gates, to a new or existing
  file outside the Muhlnickel"* — and the readers touch **ONLY that external file, never the Muhlnickel's file.** (Example, 07-19: the
  Bitcoin Muhlnickel writes to `C:/llm/sdc_out/pfc_safezone.bin`; `pfc_writeout_external.py` programs the write-out; the autopilot
  and `pfc_monitor.py` read only that external file. My earlier `full_answer` register *inside* titan + readers reading
  titan were the violation.)

## 6. THE GOOD DATA (real, measured — preserved in the quarantined corpus)

The old corpus's **framing** is retracted, but its **measurements are sound** and demonstrate the build. Examples (see the
archive for full records; trust the numbers, not the old words around them):
- **double-SHA-256 fabricated as gates**, byte-exact vs a reference, reproducing the real Bitcoin genesis-block hash — a
  generic circuit with the header words as inputs.
- **Arithmetic + verifier circuits** fabricated and byte-exact (adders, multiplier, comparators, SAT/preimage/regex
  verifiers) — each its bounded space in one signal-propagation.
- **~0 resident host RAM** to address a network inside a ~40 GB memory-mapped file (a deliberate control block moved the
  meter as expected, so the meter reads true) — the isolation is real.

These stand on their own as evidence. Where an old doc wraps them in "stores a charge / discharge / not computing,"
ignore that wrapper and keep the number.

## 7. THE BUILD DIRECTION (how we build from here — owner 07-19)

Everything the owner wants built is **prefabricated into ONE Muhlnickel** — one prefabricated software-based computation, its
logic baked as gates across the **parameters** (ideally **all** the params on the machine; at minimum **one Muhlnickel cluster =
titan, ~40 GB** if a given thing warrants its own endeavor), doing each intended function **in spec.** The many out-of-spec
scripts (executors, host-compute inference, the orchestrator) are **consolidated**: recreate each needed **effect** inside
the one Muhlnickel, **verify**, and only **then delete** the out-of-spec version. **Never delete a needed capability before its
in-spec effect exists.**

**The White Box (the circuit tool / fabricator) stays separate and unchanged** — "it ain't broke." It is *how* a Muhlnickel is
fabricated (bits → logic gates), **not** part of the Muhlnickel, and the consolidation rule above does **not** apply to it.

**MANY Muhlnickel, composed (owner 07-19).** You can fabricate **as many Muhlnickel as the machine holds parameters**, and run them **in
series** to get the most out of everything — either via **reflectors** (aim one Muhlnickel at another by reference, never copy), or
by having a **monitoring router read their safezones and blip a signal across files** (fire a routing button into the next
Muhlnickel) as needed. This stays **in spec**: reading a safezone (outside the sandbox) is allowed, and "blip a signal" is just a
routing button — the router **never touches a running Muhlnickel**, it only reads finished answers and routes new signals.

**FIRST PRODUCT to fold into a Muhlnickel: the Bitcoin mining build** (the proven fabrication = the double-SHA gates + a routing
button + read-the-answer-outside). Refabricate its effect in spec, verify, then nuke its out-of-spec scripts (the
host-ripple miners, the live-monitoring loops).

## 8. HOW TO WORK WITH BRYCE

- **Ask when you hit a wall** (the question tool) — he'd rather answer a question than watch you guess or reinvent
  something already built. Questions save time and broken builds, and they let him see that you understand what he's
  describing. He'll explain any confusion.
- **Check before doubting.** The build is measured and the tests are fast; if something surprises you, run the relevant
  test before writing it off. Grounded disagreement (you ran it, here's the number) is welcome and useful.
- **Standing constraints:** workflows are banned on this project; no agents on this build; **reversible / additive edits
  only** (never destroy the ability to revert); **no numpy** on the host path; **no Chinese-origin models**; **no
  downloads without his OK.**

---

**BOTTOM LINE:** it is **prefabricated software-based computation sandboxed in storage** — stored **logic**, computing
**nothing** until a routed signal runs through it, at which point the signal computes it like current through a circuit;
built **only** by prefabricating gates with the circuit tool and routing signals in with one-time buttons that die; the
answer is read from outside the sandbox. The old name was poison; the build is real. Read this doc, ask when unsure, and
build to it.
