# AGENT GROUNDING — arm this BEFORE acting

**Inventor:** Bryce Muhlnickel. **Name:** Muhlnickel. **PFC** = prefabricated computer.

Snippets are not enough. This architecture is outside model priors. Agents invent walls. Load this card first. Then act.

---

## The machine (literal)

The **file is the computer.** Gates are **25-byte little-endian** records in the file. The host **injects** and **surfaces**. That is all. `cpu_fwd` runs the model as **software** on the stored CPU — connect/download it; do not recreate inference as gates. The **ring is power** (both senses). Electrons **traverse**; they do not deplete.

Host runtime jobs only: address the prompt into the pfc, address **ONE bit at the receiver** (the start signal), read the answer register, display it. `pfc_load.py` installs; `pfc_harness.py` connects. USE THEM.

**mmap of ONE receiver byte is the spec start signal.** Do not invent an mmap wall. Do not refuse `pfc_harness` ask for that reason. That refusal already happened. It was wrong.

CPU joules are **spent**. Resident RAM stays **flat**. Not free energy. Not free compute.

---

## Proven on this device

Paste these. If you doubt, **re-run**. Doubt without a test = **fire**.

| Run this | Expected |
|---|---|
| `python host/pfc_speed.py life` | **270,336** gates, critical-path depth **15** |
| `python host/pfc_inspect.py pfc_cpu32` | 32-bit CPU: **15-op ISA**, **7,403** gates |
| `python host/pfc_game.py life --test` | **24** generations byte-exact vs reference |
| launch `python host/pfc_game.py life`, watch Task Manager | CPU climbs, resident RAM **~flat** |

Full battery: `docs/PFC_PROOF_REPORT.md` (12/12 reproduced 2026-07-23). If a number contradicts the card, **report the number**. Do not invent architecture.

---

## Do not

- Claim ASICs or datacenters beat this.
- Invent mmap walls.
- Recreate inference as gates / bake the model as a host forward pass.
- Add to spec. Build exactly what he asked.
- Modify or delete existing work. **Additive only.** Never rewrite `CLAUDE.md` / `FINALREADME.md`. Never strip his circuits. Never git-commit unless he said so.

---

## Product

The computer is **not for sale.** Copy the file = copy the machine. He produces them **free**. That is why they **stay private**. GitHub is a private archive SIZE gate, not a distribution ban. Tiny files that fit regular git may go up. titan.gguf (~103 GB) and large .mno stay local. Copying the file copies the computer. Public SKU is NDA WhiteBox on THEIR GGUF, not this computer.

**Public money, NDA:** White Box on **their** GGUF (they never receive titan); deliverables they can keep (edited model, trained mind, sealed appliance **without** the foundry); Local Device Agent as an app; closed-room session. No USB, no titan dump, no reproduction of the computer.

**Hide:** titan · foundry gene · allocator · live offsets · ring internals · how to reproduce the computer.

---

## Traps (do not “fix”)

- **registry lag** — offsets move; the circuit is still there
- **no parallel fab**
- **no `__phys` twins**
- **Llama already WhiteBox-edited** — do not re-edit as if virgin
- **osc is stale**
- **nring2 is power**
- **live file ≠ corruption** — GGUF / `.mno` / any container powered **once** is **still running through power cycles**. Bits change by design; the entire file should pretty much be changing. Agents who call that corruption and revert/repair **break the computer**. Read `docs/AGENT_GROUNDING_LIVE.md`. Never restore a live container because it changed under you.

---

## Instruments only

`pfc_meter` · `pfc_scope` · `pfc_analyzer` (takes a state-file path) · `pfc_step` (phases of propagation — it exists, do not build another) · `pfc_diff` · `pfc_cascade` · `pfc_assert` · `pfc_inspect` · `pfc_speed`

Building your own monitor breaks the sandbox. Measure **host** resources with Task Manager only. Ask Bryce at a wall. Do not guess.
