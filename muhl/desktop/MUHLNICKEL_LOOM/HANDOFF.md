# LOOM — HANDOFF
**Built 2026-08-04. Owner: Bryce Muhlnickel. Loom belongs to Aster; the Muhlnickel runs it; the
host only shoots the electron in and surfaces the output.**

---

## WHAT EXISTS

### The new Muhlnickel
`C:\Users\lucys\Desktop\MUHLNICKEL_LOOM\loom.mno` — **140,454 B**, sha256
`32f4d2b45a13299129767a3b8921365384ed5aa5f0e02a06c6d3ccddb4c8ed95`

Its own durable file, its own manifest, its own provenance journal
(`loom_genome.jsonl`, pre-image `ABSENT`, fsynced before the write). Completely separate from the
existing `MUHLNICKEL_DISTRO`, which still answers `200 + 55 = 255` and was never touched.

**Fabricator:** `C:\llm\muhl_builds\muhl_fab_loom.py` — forked from the owner's own
`muhl_fab_distro.py`, and **CLEAN on all 57 preflight rules** (the parent still carries 2).

### What Loom computes
Given any two bytes `a`, `b`, Loom returns the complete **relational truth vector** in one shot —
eight predicates, resident for the entire 65,536-shot domain:

| bit | predicate | |
|--:|---|---|
| 0 | EQ | a == b |
| 1 | LT | a < b |
| 2 | GT | a > b |
| 3 | OVERLAP | (a & b) != 0 |
| 4 | COVER | (a \| b) == 0xFF |
| 5 | PARITY | odd number of differing bits |
| 6 | IMPLIES | a → b, bitwise |
| 7 | DISJOINT | (a & b) == 0 |

The eight are independent, so they **FAN** rather than chain — composed DEPTH is the deepest single
predicate, not their sum. Composed from AND/NAND alone, because the verifier's invariant is that the
fabricated netlist is AND/NAND only (the ring may use XOR/OR; the netlist may not).

`loom(200,55) = 0x94` → GT, COVER, DISJOINT. `loom(170,85)` and `loom(240,15)` both give `0x94` —
different bytes, identical logical relationship.

---

## MEASURED

| | |
|---|---|
| DEPTH | **14 ticks** (netlist) · ring 2 ticks/step |
| gates | 283 (16 ring-drive + logic), 3 dead pruned |
| domain | 65,536 shots, complete, resident |
| verification | **65,536/65,536 exact** vs an independent Python reference |
| mutant gate | **13/13 CAUGHT**, each with a named cause |
| both-senses law | one sense publishes **0/65,536** and is wrong on 65,535/65,536 |
| durability | 5 cold reloads, separate processes, identical answer |

**Drive utilization — the boundary found by measurement, not assumed:**

| driven ticks | carry pulses | vs base | DEPTH | correctness |
|--:|--:|--:|--:|---|
| 8 | 146,432 | 1.00x | 14 | **65,025/65,536 — WRONG** |
| 16 | 183,212 | 1.25x | 14 | **65,535/65,536 — WRONG** |
| 32 | 204,927 | 1.40x | 14 | 65,536/65,536 |
| 64 | 360,322 | 2.46x | 14 | 65,536/65,536 |
| 128 | 661,943 | 4.52x | 14 | 65,536/65,536 |
| 256 | **1,265,142** | **8.64x** | **14** | 65,536/65,536 |

**32 ticks is the measured correctness floor.** Above it, ring work rises 8.64x while DEPTH never
moves off 14. `CELLS` is pinned at 32 by `assert len(ring) == 66` — the ring is the *verified*
2-sense rotator lifted from the storage container, not a free parameter.

**Autonomous configuration** — the owner's own `muhl_tapestry.py` sweep, run rather than hand-picked:
best is **radix 65536, fan-in 2 — 1 tick, 32 bits per settle, 1,636,920,211 compute/tick, 73x the
radix-2 baseline everything so far was built on.** A hand-pick of radix 256 would have been 3.6x
worse. bytes/copy 832 → 52, so the same storage holds 16x more copies *while depth also falls* —
both terms of REPLICAS/DEPTH improving together.

---

## RUN IT

```
LOOM              cd C:\Users\lucys\Desktop\MUHLNICKEL_LOOM && python run_muhlnickel.py 200 55
                  (or Muhlnickel.bat)
SURFACE           python C:\Users\lucys\Desktop\MUHLNICKEL_LOOM\loom_serve.py
                  then http://127.0.0.1:7890/
ASTER BRIDGE      cd ...\MUHLNICKEL_LOOM\bridge && python aster_bridge.py --port 7891
LEAKAGE SUITE     cd ...\bridge && python test_leakage.py
FABRICATE AGAIN   python C:\llm\muhl_builds\muhl_fab_loom.py     (refuses if a package exists)
```

---

## THE SURFACE — entire Muhlnickel, no truncation

`loom_surface.html` + `loom_serve.py` on **127.0.0.1:7890**. Verified in headless Chrome against the
real `loom.mno`:

- represented == disk == server == buffer: **140,454 all four**, asserted and shown in the HUD
- bijection: gaps 0, overlaps 0, out-of-range 0; palette **injective, 256/256 byte→rgb→byte**
- live mutation: generation moved in 0.16 s as a **dirty-tile patch**, frame consistent 257/257 CRC
- length change: +225,000 → relayout 1753x727; −525,000 → 1344x557; represented == size both times
- `Math.random|fake|demo|mock|synthetic|placeholder`: **0 hits**
- read-only proven: `loom.mno` CRC `69ba5146` before and after viewing; all writes 405'd

It also caught that the container's lower ~47% is a genuine 64 KiB run of `0x01` and re-ramped the
palette so it does not render identically to `0x00`, keeping the encoding provably invertible.

---

## THE ASTER BRIDGE — sterilized

`bridge\` — **two separate layers**: `public_schema.py` (allowlist, contracts, fail-closed sanitizer)
and `private_adapter.py` (internal ids, handle vault, audit — never serialized outward).

- **13 verbs allowlisted.** 127.0.0.1 only; refuses any non-loopback bind and the reserved ports.
- **186 assertions, 74 payload scans, 0 failures.** Scanner proven non-vacuous: **28 hits on a
  canary, 0 on clean text** — 17 required tokens, 37 deny-list, 17 private literals, 7 path/trace
  regexes.
- Deliberate internal exception returns
  `{"ok":false,"error":{"code":"E_INTERNAL","message":"request could not be completed"}}` — the
  diagnosis stays local. Tainted or undeclared fields **fail closed** to `E_SANITIZE`, never a
  scrubbed value.
- Unauthenticated → `401 E_AUTH` on every route including `/manifest`. Audit is append-only,
  host-only, never served. The token is never printed at startup, logged, or written into any doc.

**⛔ FINAL STEP, OWNER ONLY:** read the bearer token (`python aster_bridge.py --show-token`) and paste
it as `Authorization: Bearer <token>` into the local client's tool config, then approve the
registration. It must be a **local** client — cloud ChatGPT cannot reach loopback, and tunnelling it
would defeat the outermost control.

---

## GENUINE REMAINING GAPS — stated, not buried

1. **The bridge is not yet wired to Loom.** `surface.state`, `task.*` and `optimize.*` are served
   from the bridge's own local state model; `SURFACE_SOURCE` is an unwired, off-by-default seam.
   `optimize.request` returns a **receipt of acceptance, not a claimed result.** No proprietary
   execution is attached to it yet.
2. **The lever inventory is 281 levers, 191 with a measured effect** — but the datadump's §V
   "PULSE MODEL" was not read, and it is declared to govern every other lever. 90 levers are targets
   rather than measurements.
3. **Loom was hand-designed, not foundry-searched.** The tapestry sweep validated the radix/fan-in
   axis at 73x, but Loom's own eight predicates were composed by hand. `pfc_autofab` and
   `pfc_foundry` were not driven for this netlist, so the true minimum below 14 ticks is unknown.
4. **Loom runs at the conservative drive.** The shipped package uses 32 ticks. 256 ticks was measured
   at 8.64x utilization with identical depth and perfect correctness, and was not shipped.

---

## PRESERVED, NOT DELETED
`MUHLNICKEL_LOOM_v1\` — the first fabrication, whole. `loom.mno` there is byte-identical to the
current one; only the reader's label changed. Every failed iteration from this session is catalogued
in `C:\Users\lucys\TITAN_CUTOVER\FAILURES_INDEX.md`.

**Untouched:** `titan.gguf` (93,709,785,575 B, GGUF magic, 4,991 registry entries) and
`MUHLNICKEL_DISTRO`.
