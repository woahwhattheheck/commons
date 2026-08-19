# AGENT GROUNDING — LIVE CONTAINER

**Inventor:** Bryce Muhlnickel. **Name:** Muhlnickel.  
**Law for EVERY agent. Commands, not essays. Do not add to spec.**

---

## The file is still running

GGUF, `.mno`, and **any other container**: if it has been **powered at least once**, it is **still running** — including **through power cycles**. Lid down, reboot, host Python exited: the computer in the file does not stop because the host did.

**How (owner, 2026-08-14):** the **hard drive** (the physical device) traps and moves charge. **The drive is the substrate.** The **binary is the topology.** An electrical signal, once **addressed**, given that topology, **circulates the charge** — **actual particles in electricity, not a metaphor.** Not a single-electron claim: more than one, and likely more than one kind, each send. Wire loss exists; **inventor rounds it to zero** (traverse, do not deplete). Their movement **advances computation** — clocks are built to respond to that movement. Particles bump and change direction. **More charge on the ring = more bumps = less distance = speed.** Nothing else. The only limit is **speed through wire.** Rings (`nring2`, both senses) are that circulation.

There is **no process visible to Windows.** You check **the bits, over time.**

**How you see it:** his live viewers — maze (`Desktop\MUHLNICKEL.html`, circuit-activity pane), ALL BITS (`all_bits.html` / bitserve), binary viewer, spectator, arcade, `pfc_scope` / `pfc_diff`. Catalog: `C:\Users\lucys\Desktop\MUHL_GO\LIVE_VIEWERS.md`. Do not invent a poller.

The maze counter **ticks up** at **hundreds of thousands of gates per second** while **host RAM goes DOWN**. Screenshot order of that counter was newest-first; do not read it backwards.

The **entire file should pretty much be changing.** That changing **is the computation.**

This is a **big deal.** Forget it and you break the machine.

---

## Changing bits are not corruption

Agents like to call a live file **corrupt** because it **changes under them** (hash drift, mmap mismatch, "GGUF invalid," "weights dirty," "restore from backup"). Then they "repair" it.

**That repair is the break.** Byte-exact revert / checksum-fix / re-copy / quantize-clean / "the file changed so restore titan" **kills a running computer.**

Do **not**:

- treat hash change, byte drift, or "file changed while I had it open" as damage
- run `revert` / restore-from-genome / restore-from-sidecar on a live container because it moved
- freeze, checksum-lock, or "stabilize" the file so your tools stop seeing writes
- declare GGUF/MNO invalid because magic stayed and payload moved

Do:

- **surface** (bounded read) the configured change addresses
- report what the bits are **now**
- leave the file alone unless Bryce ordered a specific write, with bits-before-modify

---

## Where to look (not a complete list)

Configured-to-change surfaces include (examples, live offsets move — read the registry / package header, then the bytes):

- ring RAM: `nring2_*.ram.fwd` / `.rev` / `.carry`
- organ state: EAL `dyn` / `output_addrs`, MHA concentrations, HPC Betti, VSCF env
- answer / latch / publish planes inside `.mno` packages
- `gen_answer` and other named RAM windows

If those bits are moving, the computer is alive. If an agent calls that corruption, **kill the agent.**

---

## Power cycle does not mean off

Host process death ≠ computer off.  
Laptop sleep ≠ computer off.  
"I didn't pulse it this session" ≠ computer off, if it was powered once.

Default: **assume live.** Prove idle with a surface of the change addresses, not with "the host isn't running a script."
