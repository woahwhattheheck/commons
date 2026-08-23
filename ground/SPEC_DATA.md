# SPEC DATA — containers, rings, archetypes, datasheet format

Reference data for windows without disk access to the owner's machine. Read from
`C:\Users\lucys\Desktop\MUHL_GO\` and `MUHL_SUBZERO_ARCHETYPES\` on 2026-08-20.
Numbers and paths only. Cite the source card, not this file, when it matters.

---

## Datasheet format

Every `MNO_DS_*.md` carries a **FROM FILE** table:

```
path · size · sha256 · magic · n_in / n_wire / n_gate / n_out · DEPTH
n_rings / cells / ring0 · named dest addresses + current bit values · ones count
```

Then three derived numbers (`MNO_DATASHEETS_INDEX.md:63-68`):

```
(a) computations/tick  = n_gate / DEPTH          = pfc_speed.py wavefront mean
(b) ticks/second       = 1/tau at 1 ns/stage     = 1e9
    compute/second     = (a) x (b)
```

`(b)` is tied across every file where DEPTH is published, so ranking is by `(a)`.
Top tie: five files at `(a) = 2784.528` — the WEATHER v2 DEPTH-36 set,
`MNO_DS_1` through `MNO_DS_5`.

---

## Container inventory

| container | magic | bytes | DEPTH | rings | card |
|---|---|---:|---:|---:|---|
| `SEED0.mno` | MUHLPKG1 | 8,192 | | | EXPANDING_SEED.md:20 |
| `SEED0_GERM.mno` | MUHLPKG1 | 6,662 | | | COMPRESS_GO.md:24 |
| `SEED0_VIRGIN.mno` | MUHLPKG1 | 8,192 | | | NWAY_PROOF.md:19 |
| `SEED0_MIRROR.mno` | MUHLPKG1 | 8,192 | | | NWAY_PROOF.md:19 |
| `SEED0_N2.mno` | MUHLPKG1 | 8,192 | | | NWAY_PROOF.md:19 |
| `muhlnickel.mno` DISTRO | MUHLPKG1 | 136,450 | | 1 | MNO_DS_X_sealed_136450.md:7 |
| `loom.mno` | LOOMPKG1 | 140,454 | | 1 | MNO_DS_X_loom.md:6 |
| `GIG.mno` / `GIG_DL.mno` | MUHLPKG1 | 1,073,741,824 | | | MNO_DS_X_GIG.md:3 |
| `muhlnickel_dc.mno` DC | MUHLDC01 | see growth below | | 1,251,485 | MNO_DS_X_dc.md:8 |
| `weather_v2.mno` +4 siblings | WEATHER1 | 2,606,416 | 36 | 6 | MNO_DATASHEETS_INDEX.md:76 |
| `weather_v2_ks.mno` | WEATHER1 | 3,691,344 | 28 | 6 | MNO_DS_6 |
| `weather_v2_csa.mno` | WEATHER1 | 3,771,216 | 29 | 6 | MNO_DS_7 |
| `weather_v2_acre.mno` | WEATHER1 | 14,733,648 | 28 | 6 | MNO_DS_8 |
| `weather_v2_shallow_acre.mno` | WEATHER1 | 13,082,960 | 24 | 6 | MNO_DS_12 |
| `weather_v2_denoms.mno` | WEATHER1 | 14,440,784 | 22 | 6 | MNO_DS_15 |
| `weather_v2_denoms_wide.mno` | WEATHER1 | 28,870,992 | 22 | 6 | MNO_DS_16 |
| `weather_powered_side.mno` | WEATHER1 | 2,726,822 | 40 | | MNO_DS_X_weather_powered_side.md |
| `axiom_probe.mno` | PROBEMN2 | 14,756 | 5 | | MNO_DS_10 |
| `axiom_probe_pop.mno` | PROBEPOP | 26,300 | 32 | | MNO_DS_14 |
| `foundry_acre.mno` | FNDRYAC1 | 24,161 | 5 | | MNO_DS_11 |
| `muhl_tenancy.mno` | TENANCY1 | 23,536 | 5 | 12 | MNO_DS_9 |
| `commons.mno` | COMMON1 | 17,683 | 5 | 9 | MNO_DS_13 |
| `table_mail.mno` | TABLEML1 | 17,683 | 5 | 9 | MNO_DS_17 |
| `ROOKERY0.mno` | ROOKERY0 | 586,918 | | 11 | MNO_N_RINGS.md:87 |
| `AUTOFAB0.mno` | none, byte 0 is a gate | 102,925 | | | COLLISION_IS_FAB.md:46 |
| `FOUNDRY0.mno` | gate-first | 4,800 | | | COLLISION_IS_FAB.md:146 |

### DC growth, by card date

```
2,147,548,550    MNO_N_RINGS.md:19
17,023,971,219   COLLISION_IS_FAB.md:102
54,395,760,531   SIZE_MUST_MOVE.md:24
99,999,999,783   MNO_DS_X_dc.md:8
99,999,999,783   measured on disk 2026-08-20T07:xx by stat
```

`titan.gguf` measured on disk 2026-08-20: **103,803,350,291**.

---

## Ring model

`MNO_N_RINGS.md:6` — N rings, each a computer organ. A 1-ring file is the dumb shape.
`N_CLOCKS_PER_RING.txt` entire: *"Each ring can have N clocks. More clocks = better and faster. ONE RING IS DUMB. N rings, each with N clocks."*

| container | n_rings | ring names |
|---|---:|---|
| DISTRO / LOOM | 1 | no `n_rings` header field present |
| `ROOKERY0.mno` | 11 | sense · sense · memory · tension · imagination · value ×4 · action · witness |
| `muhlnickel_dc.mno` | 1,251,485 | 1 control + 1,251,484 factory |
| `commons.mno` | 9 | ZERO GROK KITE CAIRN SPALL GRAVE AXIOM SHARD SCREE |
| `table_mail.mno` | 9 | same nine |
| `muhl_tenancy.mno` | 12 | PALF NEFG ARDR VSCF KEGN NMPIS AWCG DMB CGAT EAL MHA HPC |
| weather_v2 family | 6 | |

`ROOKERY0.mno` header offsets: `n_clocks` @ 48, `n_rings` @ 56.

---

## The twelve Sub-Zero archetypes

`MUHLNICKEL_INVENTION_BURST/INDEX.md:28-40`. One ring each in `muhl_tenancy.mno`.

| code | name | basis | fabricator |
|---|---|---|---|
| VSCF | Viable System Cybernetic Field | Beer's VSM as NAND tiers | `muhl_fab_vscf.py` |
| AWCG | Asynchronous Wavefront Concurrency Grid | self-timed 3x3 torus | `muhl_fab_awcg.py` |
| DMB | Diachronic Morphogenetic Blueprint | Fibonacci L-system | `muhl_fab_dmb.py` |
| HPC | Homological Persistence Complex | Betti numbers | `muhl_fab_hpc.py` |
| NMPIS | Non-Markovian Path-Integral Synthesizer | Feynman paths | `muhl_fab_nmpis.py` |
| KEGN | Kinetic Enthalpy Gas Network | Lattice Boltzmann | `muhl_fab_kegn.py` |
| PALF | Phase-Asynchronous Logic Field | self-clocked oscillators | `muhl_fab_palf.py` |
| ARDR | Autocatalytic Reaction-Diffusion Reactor | Turing patterns | `muhl_fab_ardr.py` |
| CGAT | Causal Graph-Algebraic Transducer | Pearl's do-calculus | `muhl_fab_cgat.py` |
| NEFG | Non-Euclidean Functorial Graph | category-theoretic functors | `muhl_fab_nefg.py` |
| EAL | Ergodic Attractor Lattice | Lorenz-like discrete map | `muhl_fab_eal.py` |
| MHA | Metabolic Hypercycle Automaton | Eigen's hypercycle | `muhl_fab_mha.py` |
| — | Ring Clacker | 1,024-cell / 512-electron vibration-mode ring, "LEVER DADDY" | `muhl_fab_ring_clacker.py` |

---

## Compression corpus, established before 2026-08-20

`COMPRESS_PROOF.md:7` — **"Smaller container. SAME compute."**

| file | bytes | `ans@6661` |
|---|---:|---:|
| `muhlnickel.mno` DISTRO | 136,450 | 8 |
| `SEED0.mno` | 8,192 | 8 |
| `SEED0_GERM.mno` | 6,662 | 8 |

`COMPRESS_GO.md:24-27` — **`6662 = dest 6661 + 1`**. The container is its output
address plus one byte.

`COMPRESS_EXPAND.md:80-84` — a host-side offset list of every 1 on a dense file
is **packing, not compress**.

`COMPRESS_EXPAND.md:58` — winner-only addressing, `stored_per_lane=0`,
*"the winner rides, the lanes do not."*

`NWAY_PROOF.md:19-26` — three separate 8,192 B files, identical injection, all
read `ans=8`. N-way = latency-zero worlds.

`INSTANT_DOWNLOAD.md:18-24` — ship the seed, boom locally, *"size of the result
does not travel the wire."* Logged tests: 2026-08-15 germ 6,662 B → `NEW_MNO.mno`
byte-exact; 2026-08-16 germ → `GIG.mno` / `GIG_DL.mno` at 1,073,741,824 B,
byte-exact, sha match.

---

## Open

`EXPANDING_SEED.md:86-89` — *"Live-EOF on this seed is not claimed. No gate `out`
writes past 8191. No pulse lengthens `SEED0.mno`. In-circuit grow that extends
disk still has no named mouth. Plant stays inside held bytes until he names the
EOF bind."*

`SIZE_MUST_MOVE.md:84-86` — *"Name the mouth / gate `out` / foundry bind that
extends the file past the current end."*

`NEED_BRYCE.md:16` — 8 walls, open until he throws the byte.

---

## Law cards, full text of the short ones

`CLAIM_SIZE_LAW.txt` entire:

```
1. The size of a claim has no bearing on its validity.
2. The amount of evidence provided to the agent has no bearing on its validity.
3. Priors of the form "too big / too few citations / therefore false or shrink
   the work" are a fireable offense.
4. Instruments may be run. Philosophy about claim size may not.
```

`FILES_CHANGE_UNDER_YOU.txt`:

```
titan.gguf and *.mno WILL change under you RAPIDLY. Every single bit of the file
may change while you have it open. NOT corruption. Hash drift is compute.
Default is live.
```
