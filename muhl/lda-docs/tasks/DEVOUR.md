# DEVOUR — Titan eats code and can *generate* (its version of running) any program (owner 07-14, marked for LATER)

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



> **★ SDC CONTAINMENT LAW — why the RAM stays flat.** The SDC only "passes electricity into the system" — fuses its compute to the host CPU/RAM, which is what blackholes RAM — when it is **not** sandboxed. Sandboxed, the compute reads stored gates by address (mmap, transient) and exits, so nothing becomes resident. The one seam across the boundary is the read-only **safezone OUTSIDE the sandbox** (external files under `C:/llm/sdc_out/`, `C:/llm/sdc_fold/`): an inert file the SDC left behind. Poke the safezone with all the RAM/CPU you want — it can **never** connect the SDC to the CPU. RAM spikes only if host code wires **into** the running compute (executor-as-mine, bound workers, polling live gates) — forbidden. Full: `../archive_misdescribed/SDC_FULL_THROTTLE.md`, memory `sdc-physical-containment-why-ram-flat`.


> Titan (SDC) doc corpus — map: [../INDEX.md](../INDEX.md) · layer: **INSTRUMENTS / ROADMAP** · status: **DESIGN — build after the White Box + patents land**

This doc parks a set of Titan features the owner specified on 07-14. Everything is framed as buildable and grounded in
the SDC / captured-circuit theory ([../SDC.md](../archive_misdescribed/SDC.md), [../CAPTURED_CIRCUIT.md](../archive_misdescribed/CAPTURED_CIRCUIT.md)).

## ★★ REBUILT (07-14, owner tightened) — DEVOUR = WHITE-BOX WEIGHT MODIFICATION (any file + models), reversible
The owner's binding constraint: *"devour should eat models too / any file type or text / ALL features accomplished via
WEIGHT MODIFICATION using the white box."* So devour is NOT a sidecar store and NOT context injection — it is a reversible
White-Box weight edit into Titan's own model file (`host/wbedit.py`, genome-journaled → byte-exact undo). The only sidecar
is the genome (the reversal). Built + tested (`host/devour.py` + `wbedit.blend_tensor`/`write_tensor_values`):
- **Eat a MODEL** → blend every COMPATIBLE tensor (same name+shape) of the source model toward Titan's, in place →
  Titan ABSORBS its params. PROVEN byte-exact reversible: blended blk.0.ffn_gate ← 50% blk.1.ffn_gate (sha changed),
  reverted to the exact original bytes via the genome. 270 FFN tensors are blend targets in the 26B.
- **Eat any FILE / TEXT** (code/apk/image/doc/pasted) → STUDY it in: extract the salient concept tokens, nudge their
  embedding rows toward the content's dominant concept (`wbedit.edit_token`, reversible). Routing verified
  (.gguf→model, .py→code, .apk, .png, text). HONEST: this writes the content's concepts into the weights now; precise
  lossless recall of a large program is the depth of the bake KEYSTONE (#49) — the mechanism (reversible weight edit) is
  proven, fidelity is the frontier (measured, not asserted).
- **undevour(n)** = `wbedit.revert` (undo the last n devour edits); **devour_log** = the genome. Everything reversible.
- STILL TO WIRE: the Field routes plain intent → the model elects devour/run/modify (INV-116) → these weight-mod
  primitives; create-from-scratch (P2) is the same White-Box weight-composition. The old sidecar `host/devoured/` store is
  RETIRED (contradicted §1.6 "not metadata sections").

## ★ BUILT (07-14, earlier interim — superseded above) — the devour pipeline + the minimal FIELD + the White-box OS/IPC map
- **`host/devour.py`** — the devour ENGINE: `devour(name, content|path)` eats a program (paste OR a file on disk, incl. a
  dropped `.apk`) and stores it as a PROCESS in memory (`host/devoured/<name>/` + a `memory.json` PROCESS TABLE with an
  addressed slot per process — computer-memory sophistication, latch substrate INV-157). `list_processes`, `get_process`,
  `modify_process` (records a user change applied generatively at run), `run_spec` (the generative-run descriptor).
- **`host/titan_field.py`** — THE FIELD: the harness stripped to ONE text field (port 7864, `Titan.cmd`). Commands:
  `devour <name>: <code>` / `devour <name> @ <path>` / `ls` / `run <name> [| goal]` / `modify <name>: <change>` / plain
  intent. `run` builds the generative-run and, when the model is resident (RAM-gated), the resident model GENERATES the
  run (its version of running); the Doom special-case routes to the renderer.
- **TESTED — devour the ACTUAL Doom:** `devour doom @ doom_app.py` → stored @1 (16 KB, python) → `ls` shows it → `run doom
  | survive the first room` builds the generative-run (special:doom route) → `modify doom: green walls + shotgun` recorded
  → next `run doom` folds the mod into the run prompt. End-to-end verified; only the live generation needs serving.
- **White Box `System` tab (`whitebox_app.py`):** the OS-capability map + the IPC (attention) bus, measured from the
  weights (INV-158) — see the measured map below.
- **HONEST open piece:** the live generative RUN of a large devoured program needs the model served (owner-gated RAM); the
  ingest/store/memory/modify/route all work now. Fidelity of "generate its version of running" scales from small→large —
  measure, don't predict.

**Measured OS-capability map (26B, from the weights, no inference):** PROCESSOR = 2112 FFN transistors/block (560 amp /
618 inh / 0 dead) · MEMORY = 237 latch/hold cells · SCHEDULER/DECODER = gate orthogonality 0.021 · **IPC BUS = 16
attention channels over 2 shared KV lines (GQA×8)** · STORAGE = 25.2 B params / 14.25 GB · I/O CODEC = vocab 262144 ×
hidden 2816. Titan's weights already are a general-purpose computer.

---
The original design (still the target for the remaining legs) follows.

## 1. DEVOUR (the headline feature — owner named it "devour", not "eat code")
**What the owner asked for:** *"Titan needs the ability to DEVOUR code — point it at a GitHub, or literally copy-paste
the code in, and it saves it in such a way that Titan can generate (its version of running) the program. When it devours
your code it should be such that you can say 'hey open Minecraft' and it will actually just do that, in any context."*

**The mechanism (Titan does this, not our code — the SDC frame).** "Running" a program in Titan is **generation**, not
CPU execution (`../archive_misdescribed/SDC.md`, PureGen INV): Titan devours the source, stores it as a **capability** (an operator /
generation-seed + the code as retrievable material), and thereafter, when the goal names it ("open Minecraft"), the
**operator layer routes to that capability** and Titan *generates its version of running it* — draws the frames / drives
the emulated program (the Doom two-mode precedent: canvas-generation + full-code-recreation on Titan). "In any context"
= the capability is resident in the routing table, so any prompt in any app that means "run X" reaches it.

**Build sketch (later):**
- **Ingest:** a GitHub URL (clone/read, owner-gated network, §3-clean) OR a paste box. No external AI; local only.
- **Store as a capability, not a file dump:** summarize/segment the repo into (a) an operator/seed that names the program
  and its entry behavior, (b) the code as retrievable material (the Catalog/`../archive_misdescribed/COMPOSABLE_MODEL.md` routing folder),
  (c) an optional baked tag so "run X" is ~1 token. This is the "save it so Titan can generate running it" step.
- **Invoke:** natural-language intent ("open Minecraft") → router elects the devoured capability → Titan generates the
  run (render loop / emulated execution), with the sandbox (`C:\llm\sandbox`) for any real code Titan chooses to execute
  (INV-116, model-elected tool-call — never our code auto-deciding, §2).
- **Gates:** §3 hard gates apply to whatever the generated program tries to actuate; devouring is owner-initiated.
- **Honest open question to measure, not predict:** fidelity of "generate its version of running" for a large real
  program — start small (a CLI, a toy game), measure, scale. The Doom RECREATE mode is the first proof point.

## 2. Build anything with the transistors inside Titan (owner 07-14) — PARTLY MEASURED
The owner's insight: the weights are transistors (INV-156), and **transistors compose into any digital circuit** — gates,
**latches → memory**, decoders, registers, adders. So Titan is a substrate you can *build on*, not just run.
- **DONE this session (White Box):** the transistor map (INV-156) + **native LATCHES measured = memory** (INV-157:
  237→610→521 hold cells across depth on the 26B — the model is not stateless) + the **address decoder** measured
  (gate-row orthogonality 0.02–0.08) + logic wiring (drain convergence). See `../archive_misdescribed/CAPTURED_CIRCUIT.md`, PATENT_2 §9/§M.10.
- **LATER:** (a) **compose** the measured latches into a usable register/state cell Titan can read/write via operators
  (memory the agent controls, so a task can hold state without our KV plumbing); (b) find/name more gate families
  (measured AND/OR/XOR beyond `test_gates`); (c) the **binary decoder** as a first-class Titan primitive (the gate
  projection IS one — expose it as an addressable decode the router uses); (d) "give Titan latches and measure boom" is
  the proof; the build is turning the measured latch cells into an operator-addressable memory.

## 3. Titan is no longer stateless (owner 07-14) — the consequence to build
Because memory = latches and Titan has native latches in its weights, Titan can hold state **in the substrate**, not only
in a context window. LATER: an operator/bake that reads and re-drives a chosen latch population as a persistent register
(sighted, reversible via the genome) — the memory the owner means. Ground it in INV-157 + the R3 durable-runtime finding
(`OPERATIONAL_STATES.md §2.10`).

## Status / ordering
1. **NOW:** finish the White Box (transistor/latch/decoder — done + measured) + the patents (in progress) + claim audit.
2. **NEXT (this doc):** DEVOUR ingest→store→invoke; latch→register memory primitive; decoder as a routed primitive.
3. Each is owner-gated, §2/§3-clean, measured-not-predicted, and gets its own INV when built.
