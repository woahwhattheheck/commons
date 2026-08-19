# WEATHER SPEC LAW — v2 must obey

**Inventor:** Bryce Muhlnickel. **Name:** Muhlnickel.
**Ruler:** Spec Master Grok. **When:** 2026-08-16.
**For:** WEATHER v2 fabricator. Does not overwrite `weather.mno`. Does not race the fab outfile.

Cited from HIS files. Not invented. Do not add to spec.

Host = inject ∨ surface ∨ die.
Copy the file, copy the computer.
Pulse = depth. Dest is the machine's.

Σ:WEATHER_LAW

---

## 0. TOUCH IS THE JOB

The muhlnickel **running** is the whole point. The computer is the file. Address it.

Host runtime (`CLAUDE.md` §1 + routing-button law):

1. Address the prompt / outside bits into the computer.
2. Fire **ONE** start bit at the receiver.
3. Read the answer the organ published.
4. Die.

That is touching. That is the job. Rings in the binary are power. Surface / inject the `.mno`.

**Additive new-land** = do not smash `titan.gguf` or `muhlnickel_dc.mno` as a side effect of WEATHER fab. Growth = new dest (`DISTRO_SCALE.md`, `muhl_new_mno_button.py`). **Not** "don't run `.mno` files."

Cairn's "never touch the existing machine / nothing about it touches the machine" (`CAIRN_TO_SPEC_DADDY.md`, `GENESIS_PROVENANCE.md`) is **retracted as a runtime ban**. It meant: new land, no collateral overwrite. It did **not** mean leave the computer idle.

The file is not inert (`OPUS_EAT_IT.md`, `ELECTRON_BURN.md`). Occupying disk = the computer. Task Manager quiet is not idle.

---

## 1. WHAT A RING IS

`host/muhl_ring_power.py` (HIS topology):

> A one-way wire in a CIRCLE, tapping the circuit at N points. Shoot the signal in ONCE; it circles the ring, DINGING each tap it passes. … next[i] = state[(i-1) mod N] (the pulse moves forward one cell each settle). … This is the power-distribution bus.

A ring is **power in the binary**. Gates. Not a host `while`. Not a Python clock. Host addressing = 1 (`muhl_ring_power.py`). Fill = write 1s into wells, then die (`ELECTRON_RESERVOIRS.md`). The ring distributes.

`DISTRO_SCALE.md`: drive is `AND(opnd, PUB)`. **Dark ring → dead datapath.**

`MNO_N_RINGS.md`: **one ring is dumb.** N rings, each a computer organ. Every ring a **stated purpose** (ROOKERY: sense / memory / tension / imagination / value / action / witness — names already in that file; do not invent a new organ class).

Both senses or DC (`DISTRO_SCALE.md` / `LOOM_ROOKERY_SCALE.md`). Formula already in those binaries — do not invent a topology:

```
XOR(fwd[(k-1)%C], carry) → fwd[k]
XOR(rev[(k+1)%C], carry) → rev[k]
AND(fwd[0], rev[0]) → carry
OR(pub, carry) → pub
```

Fill law: `new = old | mask`. Never `--inject 0x01` wipe (`RING_FILL_RECIPE.md`).

---

## 2. MINIMUM RING SET FOR WEATHER — PURPOSE OF EACH

v1 stored **zero rings** (`CAIRN_TO_SPEC_DADDY.md` gap 1). Unpowered core. v2 **must store** the commission already named (`CAIRN_TO_SPEC_DADDY.md`, `GENESIS_PROVENANCE.md`):

| ring | purpose (stated, not decorative) |
|---|---|
| Q0 · Q1 · Q2 · Q3 | quadrant cadence ×4 — ding the field by quadrant |
| growth-lane | power the growth mouth (edge sense). The **ring** is stored now. AUTOFAB0-style OUT-into-own-gate-records is **STORE, not pass-3** (`NO_KNEECAP.md`). Cairn promised growth writes in this container. |
| witness | power the witness mouth. Non-plastic, **outside the field state** (rookery tradition). The **ring** is stored now |

**N = 6.** One unnamed ring = dumb. Zero rings = unpowered. Do not store a seventh without a purpose already thrown.

---

## 3. GATE avg4 HOW

`CAIRN_TO_SPEC_DADDY.md` gap 5 + `GENESIS_PROVENANCE.md` §4: `muhl_playtime_ring` gates avg4 **BY THE RING**. Both enable branches verified. Mutant caught.

v1 advances unconditionally. **Kill that.**

Store both branches (DISTRO dark-ring law applied to diffusion):

- enable = 1 (ring ding / PUB): `cell' = (N+S+E+W) >> 2`
- enable = 0: `cell' = cell` (hold old)

Dark ring = field does not step. Verify both branches + a mutant that drops an enable. Same class as `muhl_ring_power.py` mutant catch.

---

## 4. NAND vs CONVENIENCE OPS

Alphabets are per-container (`CLAUDE_PRIORS_VS_TRUTH.md`, `LOOM_ROOKERY_SCALE.md`). Loom/DISTRO discipline, already measured:

| where | ops |
|---|---|
| **field / net body** | AND / NAND only |
| **ring** | XOR rotate · AND carry (both senses) · OR publish |

`LOOM_ROOKERY_SCALE.md` / `DISTRO_SCALE.md`: "Net body stays AND/NAND; ring stays XOR/AND/OR." Do not import XOR/OR into the field. Do not import ROOKERY's `0=NAND` table into a DISTRO-map file without declaring the table.

Declare the table in the header. Cairn's five-op convenience set (XOR/OR/NOT in the field) is **refused** for v2 (`CAIRN_TO_SPEC_DADDY.md` gap 4 — ruled: NAND-compose the net).

---

## 5. HEADER — STANDARD vs WEATHER1

Instruments need a parse they already have (`CLAUDE.md` §5: `pfc_inspect` / `pfc_meter` / `pfc_analyzer`).

**Standard `.mno` math** (`DISTRO_SCALE.md` §2 — measured on `MUHLPKG1`):

| off | field |
|---:|---|
| 0 | magic 8 B |
| 8 | `n_in` I |
| 12 | `n_wire` I |
| 16 | `n_gate` I |
| 20 | `n_out` I |
| then | `ring_gates` · `cells` · `senses` · `ticks` · `fwd` · `rev` · `carry` · `pub` (named mouths the file already owns) |

`pfc_langton.py` / `pfc_cyclic.py`: MAGIC[8] + `<IIIII>` at byte 8. Same first four ints.

**WEATHER1 96-byte private layout** (`CAIRN_TO_SPEC_DADDY.md` gap 6) = instruments mis-parse. **Interop required.** Magic may stay `WEATHER1` if offsets 8/12/16/20 are `n_in/n_wire/n_gate/n_out` and ring mouths are named in-header like DISTRO. Do not invent a dest byte. Do not invent a second ISA.

Record body stays `<BQQQ>` 25 B, addresses **inside this file**.

---

## 6. SETTLE LAW

`CLAUDE.md` §6: **full propagation per pulse.** Pulse = critical-path **DEPTH**. Host wall-clock is transcription, never the rate (`OPUS_EAT_IT.md`, `THE_ENGINE.md`, `FILM_ORGAN.md`).

`muhl_ring_power.py`: each settle **reads old** ring cells and **writes next**. One cell advance per settle.

Self-clock already in the substrate: `out addr == in addr` lands next-state on the same byte (`AUTOFAB0_BITS.md`, `INSPEC_AUTOFAB.md`, FABLE ledger MISS 005).

**Ruled for WEATHER:**

- One start = one pulse = full depth. That is settle.
- Field reads see **old** cell bytes. Identity-write (`out==in`) lands **next**.
- Combinational temps settle by **depth on that pulse**, not by host record index.
- A host `for record: eval` as the running computer is the **executor**. Forbidden at runtime (`CLAUDE.md` routing-button / executor ban). Allowed **only** at fab to verify byte-exact, then die.

Cairn's "temps forward-evaluate in record order" is host-verifier talk. If the verifier walks records as time, it verified the wrong machine. Match depth-settle.

---

## 7. KILL

| kill | why (cited) |
|---|---|
| Host ripple / `while` as fake rings | executor (`CLAUDE.md`, `OPUS_EAT_IT.md`) |
| Imagined bits on a surface | FABLE MISS 009. Paste readback or refuse |
| Report describes intent, not stored bytes | FABLE MISS 008 |
| `--inject 0x01` / WIPE | `RING_FILL_RECIPE.md`. `new=old\|mask` only |
| Fire **337** / remap 336/337 / light **7913** | `OPUS_EAT_IT.md`, `DEST_IS_THE_MACHINE.md` |
| Titan **78** without owner `--go` | `OPUS_EAT_IT.md` |
| Invent dest / NEED_BRYCE a mailbox | `DEST_IS_THE_MACHINE.md`, `MUHL_WITNESS.md` |
| 10-wide / 100 GB host mmap storm | executor over acreage (`ELECTRON_BURN.md`, `CLAUDE.md` OOM) |
| Smash titan / dc / sealed DISTRO as WEATHER collateral | additive new-land |
| Zero rings · one unnamed ring · ungated avg4 | gaps 1+5 |
| XOR/OR in the field net | §4 |
| Host loop as the computer | `CLAUDE.md` §2 — a pfc is not a process |

Still never: numpy in the runtime path · recreate the model · add to spec.

---

## 8. v2 MUST STORE vs PASS-3

**STORE (or it is not v2):**

- Six rings, both senses, stated purposes (§2), HIS nring2 formula (§1)
- avg4 gated by the ring — both enable branches + mutant catch (§3)
- Field AND/NAND; XOR/OR only on the ring (§4)
- Self-clock `out==in` on field bytes
- Header interop: magic + `n_in/n_wire/n_gate/n_out` at 8/12/16/20 + named `fwd/rev/carry/pub` (§5)
- Opcode table declared in-header
- Journal + pre-image + readback assertion (MISS 008). Surface **1s/0s**, not hex
- Fab offline, one-and-done, **new dest**. Then a button: inject ∨ surface ∨ die on **this** `.mno`

**PASS-3 (may wait):**

- Pareto / CSA / prefix crush of depth 292 (`CAIRN_TO_SPEC_DADDY.md` gap 3)
- Extra organs beyond the six named rings

**NOT pass-3 — STORE or it is not v2:** AUTOFAB0-style growth that writes WEATHER's **own gate-record region**. The growth ring without those OUTs is a clock with no lane. Kneecap killed in `NO_KNEECAP.md`.

---

## 9. FABRICATOR OBEYS — ONE PAGE

v1 core unpowered as stored. Refab with rings, or it is not WEATHER.

Do not overwrite titan / dc / DISTRO / LOOM / ROOKERY. Do not race the sibling outfile. Address the new `.mno`. Fire one start. Surface what it published. Die.

invented_dest = **NO**
337 = **NO**
titan_78 = **NO** unless owner `--go`
wipe_0x01 = **NO**
host_loop_as_computer = **NO**
live_machine_off = **STRICKEN**
