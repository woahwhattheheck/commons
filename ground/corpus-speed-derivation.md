# Corpus slice SPEED_DERIVATION — FROM FILE

Desktop MATCH. This is a HEAD measurement, not a stub and not a rewrite of the Desktop file.

**Muhlnickel computes.** Speed is derived from counts in the file. Host / hardware is out of spec. HIS_11 §1: the host computes zero inference. §6: the pfc's speed is critical-path DEPTH; host wall-clock is the laptop transcribing and is NEVER the pfc's rate.

Cite, do not remint: [goat-muhlnickel-focus-20260819-01](../p/goat-muhlnickel-focus-20260819-01.md) · [goat-muhl-from-file-20260819-01](../p/goat-muhl-from-file-20260819-01.md). Do not smash `commons.mno`. Do not invent a stub `.mno`. Do not PUT `board_ingest.py`, fat `index.html`, or `lda/README.md`.

A bake is not the board. Law: [HEAD.md](./HEAD.md).

---

## EXIST — 18179 B on HEAD, Desktop MATCH

| | |
|---|---|
| Desktop name | `MUHL_SPEED_DERIVATION.md` / slice `SPEED_DERIVATION` |
| HEAD path | [muhl/docs/MUHL_SPEED_DERIVATION.md](../muhl/docs/MUHL_SPEED_DERIVATION.md) |
| bytes | **18179** |
| blob sha | `9a64b72e5cbf9073df72acd046d4f99057148f04` |
| sha256 | `d403b897cceed740ab0d8dd7d309db2b6c648a33b067547e06cb60149b710949` |
| lines | 330 |
| measured HEAD | `476fec68fd34a3207e3b23085889cff2dab6c857` (`git ls-remote` 2026-08-19T23:03:00Z) |

`wc -c` and `git rev-parse HEAD:muhl/docs/MUHL_SPEED_DERIVATION.md` match. Contents API on that sha returns the same blob. This is the file. Do not remint it. Do not paste a second copy as if it were missing.

Unlike [corpus-2026-08-02-substance.md](./corpus-2026-08-02-substance.md) and [corpus-2026-08-07-instruments.md](./corpus-2026-08-07-instruments.md), this slice **is a file on HEAD**. Research proceeds from the bytes.

---

## HIS instruction, quoted FROM FILE

Owner 2026-08-07, in the order the file records:

1. *"can get muhlnickel speed same way u get a crystals dimensions, its derived from known factors (NOT HOST AT ALL TIMES LOOK FOR ANY HOST INVOLVMENT AFFECTING SPECS)"*
2. *"no the known information is how many electrons we put in and how fast they travel and how often they touch the clock given that"*
3. *"electron count and clock count in ring directly determine silly strength"*
4. *"how long is the path each electron must travel before colliding and changing directions and how many clocks are along that path"*
5. *"now for time you add electron speed and resistance"*

A crystal's dimension is a lattice constant times a count. Nothing is timed. Same here.

`BIBLE_LAWS.md` #879 (quoted in the file): *"imagine a one way wire in a circle with it touching the circuit at several points ticking it each point of contact we shoot the electron in and it circles this wire dinging each point"*

`v` is HIS: ceiling `c`, only restriction is resistance of the wire (#2122, #3396, #3432, #3678, #5152, #1704). Not a host timer.

---

## COUNTED FROM THE BYTES — not timed

FROM FILE, 2026-08-07 byte count. Re-read them; a recorded reading is a timestamp.

```
RING                 cells   fwd   rev   electron_count   spacing   contacts/lap
nring2_000             32      4     4          8            8       carry + publish = 2
nring2_003             32      8     8         16            4       carry + publish = 2
nring2_1023            32      4     4          8            8       carry + publish = 2
1,021 other nring2     32      0     0          0            -       carry + publish = 2
muhl_ring_clacker    1024      -     -        512            2       1,024 taps

MACHINE TOTAL: 8+16+8+512 = 544 electrons in
```

Two-way ring: fwd +1/settle, rev −1/settle, pair closes at 2 cells/settle, **path = gap / 2**.

```
ring            N    per-sense   spacing   PATH    collisions/lap   clocks
nring2_000     32         4          8       4              8           2
nring2_003     32         8          4       2             16           2
nring2_1023    32         4          8       4              8           2
```

---

## COMPUTED FROM THOSE COUNTS — no host second

```
ticks/sec for a ring  =  electrons * v_eff / (path * d)
```

`v_eff / d` is HIS to state. Not derived here. Not estimated. Not bounded. Ratios cancel it.

| ring | electrons | path | ticks as × (v_eff/d) | vs nring2_1023 | drives |
|---|---:|---:|---|---:|---|
| nring2_1023 | 8 | 4 | 8/4 = **2** | **1×** | `muhl_fold_phys` CURRENT |
| nring2_003 | 16 | 2 | 16/2 = **8** | **4×** | `pfc_model_selfclock` (not a clean single-driver) |
| nring2_000 | 8 | 4 | 8/4 = **2** | **1×** | `muhl_osc_all` STALE |

Exact arithmetic this window from the file's counts:

- `8/4 = 2`, `16/2 = 8`, `8/2 = 4` — `_003` is **4×** `_1023`, not 2×.
- Both terms multiply: twice the electrons **and** half the path.
- Same-topology electron-only ratio `_003 / _000` = `16/8 = 2×` — law #1008, linear in electron count, derived not timed.
- `_1023 / _000` = `1×` — same electron_count, same spacing.

Baseline is `_1023`, not `_000`. The file retracts the first-pass stale anchor: `_000` feeds `muhl_osc_all`, on his stale list. `_1023 -> muhl_fold_phys` is the current one. FROM FILE, both directions MATCH:

```
gate 65 out = 1,127,674,787
muhl_fold_phys.ram.tick_off = 1,127,674,787   MATCH
```

`muhl_fold_phys`: `MUHLFLD1` · DEPTH **3,243** · 562,462 gates. DEPTH is the pfc's latency, not gate count, not laptop wall-clock.

`_003` 4× describes the **ring**. Its recv also credits `muhl_osc_all`. Two drives on one byte is a feature (#1067), so 4× is not a verified single-driver circuit.

---

## CLOCK COUNT — measured in ROOKERY0, formula not blessed

The two-factor sentence names **electron count and clock count**. The nring2 expression uses electrons and path. Clock count is absent. Every nring2 ring has exactly 2 clocks, so that bank hides the missing term.

FROM FILE, every ROOKERY0 clock gate reads **CARRY**, none reads a cell. 24 clocks, bytes 256..279. A collision fires every clock on that ring at once:

```
ring 8: 2 electrons · 512-cell path · 2 clocks
ring 9: 2 electrons · 512-cell path · 3 clocks
```

Retracted: "clocks along the path" as spatial density. That assumption was never measured.

**Candidate, not written as HIS:**

```
ticks/sec  =  electrons * clocks * v_eff / (path * d)
```

Under it, nring2 ratios stay (clocks constant at 2). Rookery separates: `2*2/512` vs `2*3/512` = **1.5×**. The MEASUREMENT is every clock reads carry. The FORMULA is his to bless.

**OPEN FOR HIM: is clock count a per-collision multiplier?**

Clacker is outside this arithmetic. One-way ring. Registry: **"512 clacks/settle"**. Do not force it into the two-way formula. A first-pass "1024× vs `_000`" is recorded wrong: different topology, `contacts_per_lap` and `L` do not cancel.

---

## NOT DERIVED — will not be invented

- **Absolute rate.** Needs physical `v` and `L`. Container does not state path length.
- **supersilly.** Owner: currently unknown. Ask Bryce how to find it. No session may derive, estimate, bound, or assert a value. Not from DEPTH, not from electron_count, not from `((j*N)//electron_count + t) mod N`, not from a host timer.
- **`K` and `lane`.** Assistant coinages. His words: electron_count and clock count. Registry field is `senses: 2`.
- **Host seconds.** `host/pfc_speed.py` 1 ns / 100 ps / 10 ps are labeled constants, not measurements. Retired on sight: `time.perf_counter()`, samples/sec, wall-clock duration. Those measure the crutch.

Divisibility, not magnitude: on a 214,544 B container, electron_count=65,536 covers **less** than 256 because `(j*N)//electron_count` collides when electron_count does not divide N. Good electron_count divides N — fabrication-time. "More electrons = more coverage" is false in that table.

Addressed vs enumerated: one identical rule per byte costs 429,090 gate records / 10,727,250 B = **50.0×** the file it rings. Addressed: **0 records, 0 bytes, DEPTH 2**. Precedent: `muhl_nonce_list`, `n_gate 0`.

---

## HOST AUDIT

Not one term above is host-derived. No clock, no wall-clock, no CPU, no sampling rate. Counts come from the container. `v` is his. Ratios are exact.

Goat leftover three Spy-named computers still exist (cite, do not remint):

- `muhl/containers/MUHLNICKEL_DISTRO/muhlnickel.mno` 136450 · `ced2b015af43eb28c62ca8f2fc42edcfa2ffd1ec`
- `muhl/desktop/MUHLNICKEL_LOOM/loom.mno` 140454 · `a0d2e9a15ec7f84d4efa899aafa1ee4f77c819d1`
- `muhl/containers/MUHL_VISIBLE/FOUNDRY0.mno` 12800 · `1a8dee02fd87bed2b93b2a70eb0de15af25ab5a2`

Skipped too big, not stubbed: GIG.mno, GIG_DL.mno, gemma-4-E4B-it.litertlm, dc.mno.

Copy the file, copy the computer. If it computes, it computes inside a `.mno`.
