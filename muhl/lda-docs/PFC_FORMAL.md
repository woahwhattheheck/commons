# THE Muhlnickel, FORMALIZED — a 300-ft view (Bryce Muhlnickel; written up 2026-07-26)

Not a proof document. A statement of what the object *is*, what its operations are, and which of its properties
have been measured on this machine. Everything marked **[M]** is measured; everything else is definitional.

---

## 1. THE OBJECT

Let `S` be the byte-addressable locations of a file.

A **gate** is a tuple `g = (op, a, b, o)` with `a, b, o ∈ S` — two operand addresses and an output address.
It asserts a constraint on the file's contents:

```
value(o) = op( value(a), value(b) )
```

A **Muhlnickel** `P` is a finite set of such gates forming a DAG over `S`.

Three things follow immediately, and they are the whole architecture:

- **A gate is a relation between storage locations**, not an instruction executed by anything.
- **The "program" is the gate set. It lives in storage.** There is no separate code.
- **The "state" is the file's bytes.** There is no separate memory.

**Inputs** `in(P)` = locations no gate writes. **Outputs** `out(P)` = locations the caller reads.

---

## 2. THE OPERATION — computation is settling, not execution

Fix the bytes at `in(P)`. Because `P` is a DAG, the constraints determine the bytes at every other location
uniquely. **That determination is the computation.** Nothing "runs"; the configuration resolves.

This is why addressing the outputs *is* evaluating the function — the answer is the value those locations are
constrained to hold.

---

## 3. THE TWO COSTS

| quantity | definition | what it is |
|---|---|---|
| **DEPTH** `D(P)` | longest path in the DAG | **latency** — every gate at the same depth settles together |
| **AREA** `\|P\|` | number of gates | **capacity cost** — storage consumed |

**Latency = `D · τ`** for a per-stage settle time `τ`. Area does not appear. This is the single most important
consequence: *the size of a Muhlnickel does not slow it down; only its longest dependency chain does.*

Host wall-clock is a third quantity and belongs to a different machine — it is the laptop walking the DAG serially,
and it scales with **AREA**, not depth. Never mix it with the two above.

---

## 4. COMPOSITION — the wire is an address, not a channel

`P₁` feeds `P₂` **iff** `out(P₁) ∩ in(P₂) ≠ ∅`.

Connection is *identity of location*, not transfer. There is no copy, no message, no protocol — two circuits are
wired when they name the same byte. (`FINALREADME` §1E: SEND and RECEIVE at one shared address; the bit's state is
the switch.)

**[M] Composition is sub-additive in depth.** `D(P₁ ⊕ P₂) ≤ D(P₁) + D(P₂)`, usually far less, because wavefronts
overlap — stage 2's low bits can settle while stage 1's high bits are still resolving. Measured: chained ripple
stages compose at **first = 66, then +6 each**, constant across 32 stages and identical for constant, self, and
variable operands.

**[M] Composition depth depends on ORDER at fixed content.** Same stage multiset, same gate count, different
depth — front-loading wide-wavefront stages is monotonically better. Wallace: 288 vs 308. Kogge-Stone: 136 vs 156.
Once the wide-front work is behind you, position stops mattering (validated by a correctly-predicted null result).

---

## 5. REPLICATION — the second axis, and where "more compute" lives

For `k` **independent** copies of `P`:

```
D(k·P) = D(P)          area(k·P) = k·|P|          latency per result = D(P)/k
```

**[M] Depth flat at 88 for 1, 2, and 4 independent dots; gates linear; latency-per-result 88 → 44 → 22.**

So the fabricator's objective splits cleanly:

- **dependent chain** → minimise `D` (speed = `1/D`)
- **independent work** → replicate into area (speed = `k/D`, results per settle)

**Independent work costs area and is free in latency. Dependent work costs depth.** Since storage is the abundant
resource and RAM is not involved at all, area is the cheap axis — which is why *more compute is better* is a
theorem here and not a slogan.

---

## 6. FABRICATION — the third operation

`fab: (P, ΔG) → P'` — a **byte edit** adding or changing gate tuples. **[M] 0.03–0.05 s.**

Discipline: build → verify byte-exact **in the tool** → write the edit → drop the in-memory copy. Fabrication is
never a fabrication-time event, and the circuit is never retained outside the file.

`revert` is the inverse, via a journal of overwritten bytes.

---

## 7. THE INVERSION — why any of this is possible

| | classical software | Muhlnickel |
|---|---|---|
| program | inert in storage | **the gate set, in storage** |
| execution | loaded into RAM, becomes a process | **settling of the stored relation** |
| state | RAM, volatile, dies with the process | **the file's bytes** |
| scarce resource | RAM | storage (abundant, federates additively) |
| composition | IPC / copies / serialisation | **shared address** |
| persistence | an explicit save step | **automatic — compute happens in the durable medium** |
| load time | proportional to size | **none — addressed, not loaded** |
| copy / fork / diff | impossible for a live process | **it is a file** |

**Classical: inert in storage, dynamic in memory. Muhlnickel: dynamic in storage, memory uninvolved.**

Everything above is downstream of that single inversion.

---

## 8. MEMORY — revert is the consolidation boundary

`fab` then `revert` = **working memory** (scratch; the change did not survive).
`fab` and **withhold** `revert` = **long-term memory** (the change is now part of the machine).

The machine learns by *choosing not to undo*. The journal is the mechanism that decides which experiences become
permanent, and the file's current state **is** its accumulated history of what was worth keeping.

Corollary: **circuits move, never delete.** Deletion is amnesia. Capability is monotone in retained edits —
capability only ever accumulates, which is why throwing more problems at the system makes it better: each problem
leaves behind primitives the next one can use.

---

## 9. WHAT THIS MAKES THE MACHINE

A substrate where:

1. the **artifact and the measurement apparatus are the same object** — you learn its physics by reading it;
2. the **cost model is predictable** (§4, §5 predicted results before they were measured, including a null result);
3. **fabrication is milliseconds**, so the design-space-exploration loop that costs months in silicon runs in a loop;
4. **verification is byte-exact** before anything is kept.

Predictable cost + millisecond fabrication + exact verification = **a searchable design space**. That is what makes
AUTOFAB (propose → score → verify → keep) possible at all, and why the endgame is a fabricator that designs its own
circuits — and eventually its own primitives — against a need.

**The forward pass is the first serious client of this substrate. It is not the point of it.**

---

## 10. STATUS — measured · projected · not yet built

No entry below is a limit. Each says which of the three a number is, so none gets read as the other two.

- **MEASURED:** `D` is a structural property of the netlist, counted directly off the gate arrays.
- **PROJECTED:** the `τ` figures (1 ns / 100 ps / 10 ps per stage) are stated-τ projections, not timings.
  Nothing here has been clocked at electron speed.
- **MEASURED:** junction composition, proven to **32 stages** and on a real neuron.
- **NOT YET BUILT:** the same on a full transformer layer.
- **NOT YET BUILT:** the fabricated forward pass. Until it exists the host stays in the loop in practice
  (measured: 384,368,640 block-dots for a 32-layer decode). That figure measures **the unbuilt piece**, and
  says nothing about the substrate (§7).
