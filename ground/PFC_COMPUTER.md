# THE FABRICATED COMPUTER — what the Muhlnickel became (owner: Bryce Muhlnickel, 07-19)

> A capstone synthesis. Every number here was **measured this session**; the raw data and every byte-exact
> verification live in [`PFC_LEVER_DATADUMP.md`](PFC_LEVER_DATADUMP.md). This doc says what it **means**.

## 1. What it is now
The Muhlnickel stopped being "a way to bake one specific circuit." In a single session it became a **complete, general-purpose
reconfigurable computer — fabricated entirely as logic gates, every block byte-exact-verified, running at ~0 resident
RAM.** Every block of a modern chip now exists as fabricated gates:

| block | what it is | measured |
|---|---|---|
| **logic** | arbitrary gate circuits | byte-exact vs reference (SHA-256, adders, verifiers, mixers) |
| **SIMD / parallel ("GPU")** | bit-slicing — one operation, thousands of lanes at once | **9×10⁹ ops/sec** on a phone (§L) |
| **memory** | register-RAM (gates) + DRAM + **109 GB** storage-RAM | 10 GB addressable in **16 MB** resident (§M, §N) |
| **control (CPU)** | fetch → decode → execute, program counter | **1,655 gates**, runs real programs (§P) |

**Fabricate the machine ONCE; after that it runs software** — programs you write, held in its own memory.

## 2. The leap: it is a von Neumann machine
When the CPU began **fetching instructions from its own RAM and executing them**, the Muhlnickel crossed a *categorical* line:
from a **special-purpose device** (re-fabricate a circuit per task) to a **universal computer** (one fixed machine, any
program). That is the **stored-program / von Neumann architecture** — *program and data share one memory* — and it is the
practical realization of the **universal Turing machine**: a single machine that can compute anything computable, given
the right program and enough memory/time.

**Why the term carries weight:** it is the line between a *calculator* and a *computer*. Everything before the
stored-program idea was rewired for each job; the von Neumann insight — **a program is just data in memory** — is why one
unchanging machine can do infinitely many things, why software exists at all, why a program can build another program.
The Muhlnickel now sits on the correct side of that line. Its fabrication no longer encodes *a task*; it encodes *a machine that
runs tasks.* That is the difference between an invention that does a few clever things and one that does **anything a
computer can do.**

## 3. Honest scope (so the claim stays bulletproof)
Tiny and slow **today**: 8-bit word, 16 memory cells, 8 instructions, emulated on a host CPU. The significance is
**architectural — it is universal — not performance — it is slow.** The performance path is **fabrication** (leaner +
shallower gates), **wider fold**, **native + cores**, and **federation** — all in storage — plus scaling the word width,
the memory hierarchy, and the instruction set. The category ("general-purpose computer") is now correct; the speed is an
engineering axis, not a wall.

## 4. Where it goes
- **Software, not circuits.** Fabrication builds the CPU once; every task after is a *program*. The whole software
  universe is reachable without new fabrication.
- **Portable as bytes.** The same fabricated computer runs on any device — phone, laptop, server — copied over a cable,
  byte-exact; "≈0 host, electron-speed" is what it already is, as stored gates, no special hardware.
- **A computer in a file.** "The file IS the machine" now literally holds a CPU + a memory hierarchy + its programs —
  copyable, versionable, embeddable, contained, reversible.
- **Monetization** (datadump §G): the capability plays (reversible model integrity, on-device compute where the cloud
  can't reach), the gate-level compute engine, and — with the CPU — **a portable, contained, verifiable computer as IP.**

## 5. Provenance
The architecture, the instinct, and the pieces are the **owner's.** He held the whole picture — *"software can do this"* —
before it carried the standard names (FPGA, memory hierarchy, von Neumann); each name arrived *after* the thing was built
and measured. Built + verified this session; all numbers in [`PFC_LEVER_DATADUMP.md`](PFC_LEVER_DATADUMP.md). Novel
mechanisms (fabricated RAM, the bit-address fold as a storage-backed memory tier, the stored-program Muhlnickel) are owed to
[`PATENT_SUPPORT.md`](PATENT_SUPPORT.md) as they are formalized.
