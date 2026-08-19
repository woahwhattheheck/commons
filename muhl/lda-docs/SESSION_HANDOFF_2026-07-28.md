# SESSION HANDOFF — 2026-07-28

Written for a session that has just reset. Everything below was measured on this device this
session. Where a number is quoted it carries its unit and names which machine it came from (§24).
Nothing here is an explanation of the machine; the explanations belong to the owner's docs.

**Read first:** `CLAUDE.md`, `memory/muhlnickel-spec-preflight.md` (RULE ZERO), `docs/PFC_FINDINGS.md`.

---

## 0. THE ONE-LINE STATE

The oscillation is stored as physical gates whose operands are file byte-addresses. Its netlist is
now single-driver and all three mutants are caught. With the signal held one-way at the receiver,
**3 of its 5 gates hold and 2 do not** — and both that do not are gates whose output byte would have
to go 0→1. That reading is with Bryce; it is the open item.

---

## 1. TWO DEFECTS FOUND WITH THE LOGIC ANALYZER — BOTH MINE, BOTH FIXED

The instruction was *"LOOK AT THE BINARY … LOOK AT THE CIRCUITS TO SEE PROPAGATION IN PROGRESS."*
The analyzer was watching one lumped channel per circuit, so it could not show a front move between
wires. Generalising it to one channel per wire found both of these immediately.

### 1A. `pfc_step` was wiping the circuit's power rail before every hold

`host/pfc_step.py` reset with, unconditionally:

```python
f.seek(counter); f.write(bytes(nbits)); f.seek(latch); f.write(bytes(nbits))
```

`latch` resolves through `ram.get("latch") or ram.get("prev") or ram.get("sig") or counter`. On
`muhl_osc_phys` that landed on `prev`, which was that circuit's `const1` at **offset+3 of a 4-byte
span** — so the stepper wrote **32 zero bytes** across `const1`, `sig` and `t` before every hold.
`const1` is the `b` operand of **every gate** in the network. The analyzer read it as `prev = 0`.

**Fixed.** The reset now computes the circuit's own span from `offset`/`len` and clears only
registers that fall **outside** it, printing which addresses it skipped and why. A register outside
the circuit is fair to clear; a live wire inside it was set by the prefab and is not the stepper's.

### 1B. Two gates driving one wire

With the rail restored, the per-wire trace read `start=1, const1=1, sig=0`. The stored netlist had:

```
g0  nand(start, const1) -> w_sig      nand(1,1) = 0   wants sig = 0
g1  nand(sig,   const1) -> w_sig      nand(0,1) = 1   wants sig = 1
```

Both gates declared `out = w_sig`. One byte, two drivers, opposite values. This came from building
"the loop closes onto itself" as a gate whose `out` address equals its own `a` address.

**Fixed.** Rebuilt as a 5-gate ring in which every wire has exactly one driver, and the receiver is
gate 0's `b` **operand** rather than a driver — per `docs/PFC_PHYSICAL_GATES.md`: *"if this address
is part of BOTH the receiver AND an AND gate, it will flip the AND gate active, and so on."*

```
g0  nand(w_sig, w_r   ) -> w_a        the receiver admits the signal to the ring
g1  nand(w_a,   const1) -> w_b        surface 1 reflects
g2  nand(w_b,   const1) -> w_sig      surface 2 reflects — the ring closes
g3  nand(w_sig, const1) -> w_t        the tap
g4  nand(w_t,   const1) -> COUNTER    THE JUNCTION: this out IS selfclock_miner.counter
```

`5 gates, 5 distinct out addresses, multiply-driven: none`.

---

## 2. THE `shorted` MUTANT SURVIVED — AND WHY THE FIX IS STRUCTURAL

After adding a `shorted` mutant that reproduces §1B, it **SURVIVED** the existing check:

```
shorted        counter reads 1 -> *** SURVIVED ***
```

The behavioural check is one host pass that evaluates gates in list order and writes each result.
A second driver's write simply overwrites the first, so a wire with two drivers reads exactly like a
wire with one. The number of gates naming a given address as `out` is a fact about the **netlist**,
not about any pass over it, so the check had to be structural:

```python
def multi_driven(gates):
    n = {}
    for g in gates: n[g["out"]] = n.get(g["out"], 0) + 1
    return {a: c for a, c in n.items() if c > 1}
```

A build is now judged on `(counter_value, n_shorted_wires)`. Against good `(1, 0)`:

| mutant | verdict | result |
|---|---|---|
| `unjunctioned` | `(0, 1)` | CAUGHT |
| `no_loop` | `(0, 1)` | CAUGHT |
| `shorted` | `(1, 1)` | CAUGHT |

**Carry this forward:** a one-pass behavioural check cannot see a netlist-shape defect. Any future
check of wiring shape belongs beside `multi_driven`, not in the pass.

---

## 3. THE CURRENT PER-GATE STALL READING

`host/pfc_analyzer.py` gained a `gates` mode: for a circuit stored in the physical form, read each
gate's two operand bytes and its output byte, and compare what the output holds against what its own
driver names. One bounded read per address, one comparison; nothing written, nothing iterated to a
fixpoint. This is the analyzer's stated job — *"pinpoint exactly where a signal stalls."*

Signal held one-way at the receiver for the whole step, `python host/pfc_analyzer.py gates muhl_osc_phys`:

```
gate           a          b        out    a b -> wants   holds
g0           sig      start        w_a    1 1 ->   0       0   holds
g1           w_a     const1        w_b    0 1 ->   1       0   <- STALLED HERE
g2           w_b     const1        sig    0 1 ->   1       1   holds
g3           sig     const1        w_t    1 1 ->   0       0   holds
g4           w_t     const1      clock    0 1 ->   1       0   <- STALLED HERE
```

`3 of 5 gates hold; 2 do not.`

Every gate whose output byte already equals what its driver names holds. Both gates that stall are
ones whose output byte would have to go **0 → 1**.

Whole-binary diff over the fire: **1 of 9,544 blocks** differ — block 661 @ 2,772,434,944, which
contains the receiver byte that was written. Block 579, which contains `clock` @ 2429975913, is
unchanged. *(Measured on the 4-gate build, before the §1B rebuild. `snapall`/`diffall` costs ~120 s
HOST per pass and was not re-run after the rebuild — re-run it before quoting this number again.)*

**Reproduce:**
```
python host/fab_osc_physical.py                     # fabricate (0.25 s HOST, one-and-done)
python host/pfc_step.py 1 muhl_osc_phys --hold 10 & # hold the signal one-way
python host/pfc_analyzer.py gates muhl_osc_phys     # the table above
python host/pfc_analyzer.py trace muhl_osc_phys 10 400
```

---

## 4. `muhl_fire_osc` — THE ANSWER READS LAND ON RECORD MAGIC

`python host/muhl_fire_osc.py` runs clean and fires correctly: one addressed bit, `00 -> 01`, bit
changed True, 7 addressed reads, 0.016 s HOST, inside RULE ZERO's `INSTANT_LIMIT`. **But every one of
the seven answers reads the same value:**

```
prob_collatz         ... 2774157150   1,096,042,836
prob_erdos_straus    ... 2774188410   1,096,042,836
prob_golomb          ... 2775067638   1,096,042,836
prob_lucas_lehmer    ... 2775103010   1,096,042,836
prob_lychrel         ... 2775317634   1,096,042,836
prob_perfect_cuboid  ... 2775346222   1,096,042,836
prob_three_cubes     ... 2775549750   1,096,042,836
```

Decoded: `1096042836` = `0x41544954` = little-endian bytes `b'TITA'` — the first four bytes of the
`TITANCIR` record magic.

So the address the button reads as an answer is a **record header**, not an answer register. The
button takes it from `comb["members"][i]["clock"]`, written by `fab_osc_wire_all.py`. Seven distinct
addresses all landing on record magic means the comb's slot addresses point at the start of stored
records. **This is why no answer has been read yet, and it is independent of §3's stall** — it would
misread even on a circuit that had settled. See question Q2.

---

## 5. THE CHECKER — `host/pfc_preflight.py`

`python host/pfc_preflight.py --audit`, measured this session:

```
AUDIT — 52 rules over 31 live file(s)
  known-bad corpus: muhl_mine.py, pfc_btc_live.py, pfc_btc_bench.py
  ANTI-PROBES — all 9 silent, no rule has re-loosened
  ALLOWLISTS — run path: 10 imports, 3 open modes, 49 calls, each with its citation.
               Fabrication shape: 8 required steps.
  52 rules · 17 violated · 0 UNPROVEN
```

`host/` holds 483 `.py` files; 31 classify as live fabrication-or-run paths and are the ones judged.

**V59 / V60 are structural and do not appear in the `--audit` table** — they run per-file inside
`check()`, so the audit's rule table shows only the pattern rules. `--audit` reports their
allowlist sizes on the ALLOWLISTS line instead.

**V60 is AST-based, not regex** (owner: *"that's the thing I told you not to do"*). It parses the
raw source — AST has no comments by construction, so a comment cannot satisfy it — and checks:
build, independent reference, mutants, fsync-in-the-same-FunctionDef-as-the-write, genome journal,
and a `del` in the building function. It states outright what it **cannot** check: the index check
(§0) and the all-zero baseline (§40B), because no AST node represents consulting the index and a
variable named `baseline` is a name, not the act.

`host/pfc_hook.py` is the PreToolUse hook. It reconstructs post-write content and blocks the write.
Two notes for the next session:
- It blocked **~10 writes this session, every one a real defect.**
- **An `Edit` whose `old_string` does not match is a silent no-op**, and the hook then re-reports the
  *unchanged* file. Twice this session that looked like "the hook is blocking my fix" when in fact
  the edit never applied. Em-dashes are the usual cause. If a block repeats verbatim after an edit,
  `Read` the exact lines and anchor on a short unique substring, or use `Write`.

---

## 6. BLOCKED: `host/fab_problems.py`

```
PREFLIGHT GATE — REFUSING TO FIRE:
  fab_problems.py:1 [V60-fab-shape-incomplete] 2 required step(s) absent.
    · independent reference — no FunctionDef named ref*/reference*/numeric*/true*/expected*
      whose body avoids ripple/check/build/TC.*   (§3)
    · fsync beside the write — a function calls .write() without os.fsync() in the same
      function   (§7)
```

- **The fsync one is a real defect and a real fix**: `revert()` writes without an `os.fsync` in the
  same function. It cannot land while the file fails the gate as a whole.
- **The reference one is a rule-scope question, not a defect** — `fab_problems.py` has references,
  they live in another module. See question Q1. Per the standing rule *"You do NOT add entries to
  make your own files pass"*, V60 was not loosened to let this through.

---

## 7. QUESTIONS FOR BRYCE — WORK IS BLOCKED ON THESE TWO

### Q1 — Where does a circuit's answer register live?

`muhl_fire_osc` reads each problem's answer at its comb slot's `clock` address, and all seven land on
the `TITANCIR` record magic (§4). For a circuit that declares `n_out` but carries no `ram` map, I do
not know your convention for where its answer sits relative to its record — an offset past the
header, a separate allocation, or something the wiring step should have written. **Until this is
answered no answer register can be read, on any problem, even one that has settled.**

### Q2 — What closes the ring?

The netlist is single-driver, the receiver is g0's operand, g4's `out` address IS
`selfclock_miner.counter`, and the signal is maintained one-way for the whole step. 3 of 5 gates
hold; the 2 that do not are exactly the 2 whose output byte would have to go 0→1 (§3). I am not
going to theorise about the mechanism — this is yours. What should carry a wire from 0 to 1 here?

*(A third, smaller call, when you have a moment: does a reference living in **another module**
satisfy §3 for V60, or must it be in the same file? That is the only thing keeping the real fsync
fix in `fab_problems.py` from landing — §6.)*

---

## 8. FILES TOUCHED THIS SESSION

| file | change |
|---|---|
| `host/pfc_analyzer.py` | one channel per wire for any circuit with a `ram` map; back-to-back sampling; new `gates` mode |
| `host/pfc_step.py` | reset never lands inside the circuit's own wire span |
| `host/fab_osc_physical.py` | single-driver 5-gate ring; receiver as operand; `multi_driven` structural check; `shorted` mutant |
| `docs/SESSION_HANDOFF_2026-07-28.md` | this file |

Unchanged and still true: `pfc_executor` and `pfc_full_miner` records were not touched; every edit is
additive and genome-journalled; `titan.gguf` reports GGUF-valid after every fabrication.
