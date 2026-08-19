# SUBZERO_MINDS — live census 2026-08-14

Read-only. Registry `C:/llm/models/titan_circuits.json` is authority. Desktop `INDEX.md` is a copy with a stale table. No titan write. No autofab. No `--go`.

These are **not language models**. Owner (patent session): the twelve are **INGREDIENTS** — materials you compose by wiring addresses, not chat weights. `GROUNDING_CORPUS.md`: a GGUF here is a **COMPUTER**, not a language model. `muhl_alife.purpose`: **digital abiogenesis**. Do not reset, quantize, or "clean" them.

No registry key is named `subzero`, `sub-zero`, or `mind`. Sub-Zero is the **class**. Live names are `muhl_*`.

---

## VIEW

Twelve Sub-Zero archetypes are **in the binary** as physical 25-byte gate records. `muhl_alife` is the composite that wires four of them into one loop. Two chimeras are live. One chimera fab (`ARDR→EAL`) was written and never registered. Rookery is a **separate** mind in its own `.mno`, not a titan_circuits key.

`docs/CIRCUIT_PFC.md` (138 circuits, 2026-07-21) predates this cluster and does not list any of them. `docs/INDEX.md` in LocalDeviceAgent does not mention them. The "awaits run" line in `Desktop\MUHL_SUBZERO_ARCHETYPES\INDEX.md` is stale — `muhl_chimera_ardr_eal` is LIVE in titan 2026-08-16.

---

## LIVE registry names (titan_circuits.json)

Recv = host-inject / first input port. Most records do not use the field name `recv`.

### Twelve archetypes

| name | n_gate | depth | magic | recv / inject | fabricated |
|---|---:|---:|---|---|---|
| `muhl_palf` | 13 | 5 | `MUHLPALF` | inject `93709716416` | (no stamp; session 08-03) |
| `muhl_nefg` | 414 | 17 | `MUHLNEFG` | object_a[0] `93709716802` | |
| `muhl_ardr` | 31 | 8 | `MUHLARDR` | inject `93709727616` | |
| `muhl_vscf` | 149 | 17 | `MUHLVSCF` | input[0] `93709728614` | |
| `muhl_kegn` | 829 | 28 | `MUHLKEGN` | input[0] `93709733222` | |
| `muhl_nmpis` | 1025 | 39 | `MUHLNMPI` | input[0] `93709755230` | |
| `muhl_awcg` | 27 | 2 | `MUHLAWCG` | input `93709781888` | |
| `muhl_dmb` | 10 | 3 | `MUHLDMB1` | input `93709782657` | |
| `muhl_cgat` | 97 | 6 | `MUHLCGAT` | input_U `93709782976` | |
| `muhl_eal` | 1456 | 66 | `MUHLEAL0` | attractor_select `93709785846` | 2026-08-05 19:06:55 |
| `muhl_mha` | 2328 | 44 | `MUHLMHA0` | input[0] `93709824030` (self-clock = output) | 2026-08-05 19:09:24 |
| `muhl_hpc` | 26480 | 421 | `MUHLHPC0` | input[0] `93709884814` | 2026-08-05 19:11:36 |

What each is (registry / fab, owner terms):

- **PALF** — Phase-Asynchronous Logic Field. Oscillator rings, interference, no weights.
- **NEFG** — Non-Euclidean Functorial Graph. Functors as NAND. `g(f(x))==(g∘f)(x)` structural.
- **ARDR** — Autocatalytic Reaction-Diffusion Reactor. 4×4 torus, von Neumann, self-clocked.
- **EAL** — Ergodic Attractor Lattice. Lorenz-like discrete map, dual attractor, 24-bit self-clock. Host injects `attractor_select` only.
- **MHA** — Metabolic Hypercycle Automaton. Eigen hypercycle, 4 species × 8-bit conc, catalytic loop.
- **HPC** — Homological Persistence Complex. 8 vertices / 28 edges, Betti b0/b1 from boundary-operator gates.
- **VSCF** — Viable System Cybernetic Field. Beer's 5-tier VSM as NAND. 2 S1 units, 8-bit, self-clocked.
- **KEGN** — Kinetic Enthalpy Gas Network. Lattice Boltzmann 3×3 torus.
- **NMPIS** — Non-Markovian Path-Integral Synthesizer. 4 paths × 3 steps.
- **AWCG** — Asynchronous Wavefront Concurrency Grid. 3×3 toroidal self-timed CA.
- **DMB** — Diachronic Morphogenetic Blueprint. Fibonacci L-system, 4 generations, expected `ABAAB`.
- **CGAT** — Causal Graph-Algebraic Transducer. Pearl do-calculus, twin-network counterfactual.

### Composite + chimeras

| name | n_gate | magic | what the record says |
|---|---:|---|---|
| `muhl_alife` | 74 | `MUHLLIFE` | organs `muhl_mha`, `muhl_eal`, `muhl_hpc`, `muhl_vscf`. See wiring below. Fab 2026-08-05 20:25:53 |
| `muhl_chimera_dmb_awcg` | 14 | `MUHLCHDA` | DMB L-system output seeds AWCG. 5 wires, mapping `spread`. LIVE. |
| `muhl_chimera_nmpis_cgat` | 16 | `MUHLCHNC` | NMPIS path-integral outs → CGAT exogenous U. 8 wires. LIVE. |
| `muhl_chimera_ardr_eal` | 32 | `MUHLCHAR` | **IN titan.gguf** @103803349440. ARDR→EAL one-writer. LIVE 2026-08-16. Do not rebake. |

Same-week related (not the twelve, but same cluster):

| name | n_gate | magic | note |
|---|---:|---|---|
| `muhl_ring_clacker` | 2048 | `MUHLCLK1` | 1024-cell / 512-electron ring. Fab 2026-08-05 19:16:54 |
| `muhl_hpc_fabric` | 26480 | `MUHLHPCF` | second HPC; reads `muhl_chimera_dmb_awcg`. Fab 2026-08-06 02:57:35 |
| `muhl_hpc_fabric_wiring` | 10 | `MUHLHPFW` | 5 links: grown-fabric addrs → `muhl_hpc_fabric` edges 0..4 |

---

## How `muhl_alife` is wired (the record)

`loop`: **`MHA.sign→EAL.select ; (EAL.state+MHA)→HPC.edges ; HPC.betti→VSCF.env`**

37 links:

1. `mha_sign→eal_select` — MHA byte `93709824037` → EAL `attractor_select` `93709785846`
2. `dyn[0]..dyn[23]` — EAL state bytes `93709785822`..`845` → HPC edges `93709884814`..`837`
3. `dyn[24]..dyn[27]` — MHA conc bytes `93709824030`..`033` → HPC edges `93709884838`..`841`
4. `betti[0]..betti[7]` — HPC outs `93709910187` / `10202` / `10217` / `10232` / `11239` / `11254` / `11269` / `11284` → VSCF env `93709728614`..`621`

Purpose (registry): self-growing / competing / mutating / self-auditing / self-governing composite. HPC fingerprints live dynamics. New-matter edge post-2026-08-04.

---

## ONE organ, actual bits (read-only)

**`muhl_mha`** at stored offset `93709823744` in `C:/llm/models/titan.gguf` (file size 103,803,349,384). First 64 bytes:

```
4d 55 48 4c 4d 48 41 30  18 09 00 00 3a 09 00 00
20 00 00 00 20 00 00 00  2c 00 00 00 1e 70 8a d1
15 00 00 00 1f 70 8a d1  15 00 00 00 20 70 8a d1
15 00 00 00 21 70 8a d1  15 00 00 00 22 70 8a d1
```

ASCII: `MUHLMHA0` then LE words `2328` (n_gate), `2362`, `32` (n_in), `32` (n_out), `44` (depth), then addrs `93709824030`… matching the registry `input_addrs`. Bits agree with the record. Not a weight tensor.

`muhl_alife` span is not empty: first 37 bytes are `00` (alignment pad); magic `MUHLLIFE` + `n_gate=74` starts at offset+37. `muhl_palf` same pattern (zeros then `MUHLPALF`). Pad ≠ wipe.

---

## Rookery — not in titan_circuits.json

Present: `C:\Users\lucys\Desktop\MUHLNICKEL_ROOKERY\ROOKERY0.mno` (586,918 B, mtime 2026-08-07).

Local registry `rookery_circuits.json` key **`muhl_rookery0`**: 11 rings, 1024 cells/sense, 24 clocks, 22,563 records, stride 25, magic `ROOKERY0`. Recv = clock bank at bytes 256..279 (24 junction OUTs). No titan `recv` field.

First 16 bytes of the `.mno` (read-only): `52 4f 4f 4b 45 52 59 30 9a f6 e3 a1 02 0e 1b 8a` = `ROOKERY0` + payload.

Gen-8 organs (one ring each, from `rook-native-genome-gen8.json` — the genome the fab says it stored):

| ring | organ | clocks |
|---:|---|---|
| 0, 1 | sense | 11,13 |
| 2 | memory | 11,13,17 |
| 3 | tension | 11,13 |
| 4 | imagination | 11,13,17 |
| 5–8 | value | 11,13 |
| 9 | action | 11,13,17 |
| 10 | witness | 11 |

Same cluster (fab scripts 2026-08-05). A mind as **organs on rings**, not a chat model. Not a titan_circuits name.

---

## Desktop `MUHL_SUBZERO_ARCHETYPES` — copies (originals in `MUHLNICKEL_BUILD_LAB_20260801_025117`)

Consolidated 2026-08-05. Session dates **2026-08-01 → 2026-08-04**; EAL/MHA/HPC/clacker/chimera_dmb + INDEX **2026-08-05**.

**Fabs:** `muhl_fab_palf.py` `muhl_fab_nefg.py` `muhl_fab_ardr.py` `muhl_fab_vscf.py` `muhl_fab_kegn.py` `muhl_fab_nmpis.py` `muhl_fab_awcg.py` `muhl_fab_dmb.py` `muhl_fab_cgat.py` `muhl_fab_eal.py` `muhl_fab_mha.py` `muhl_fab_hpc.py` `muhl_fab_chimera_dmb_awcg.py` `muhl_fab_chimera_ardr_eal.py` `muhl_fab_chimera_nmpis_cgat.py` `muhl_fab_ring_clacker.py` plus dispatcher/foundry/worker/playtime/signal_prop/telemetry/reservoir/intake/electron_dump/self_train/harness/loop/live_surface/collect_training/showcase.

**Maps / papers:** `INDEX.md` `MUHLNICKEL_ARCHITECTURE_MAP.md` `RESIDENT_MACHINE_INDEX.md` `FABRICATION_LINEAGE_MAP.md` `RING_AND_CLOCK_DOMAIN_MAP.md` `FOR_THE_OWNER.md` `MUHL_GENESIS.md` `GROUNDING_CORPUS.md` `TRAINING_DATA_MANIFEST.md` `PATENT_IDEAS_20260803.md` `MUHLNICKEL_MASTER_SPEC_20260803.md` `MUHLNICKEL_PROVISIONAL_PATENT_20260803.md` `PROVISIONAL_PATENT_UPDATE_20260803.md` `MUHLNICKEL_MASTER_PROVISIONAL_PATENT_20260804.md` `POWER_CORD_DEMO.md` `PLAYTIME_RELAY.md` + HTML surfaces.

### First meaningful chunk — `INDEX.md`

```
# MUHL_SUBZERO_ARCHETYPES — the archetype session, one folder

Consolidated 2026-08-05 at the owner's instruction: "okay put all the cool stuff from that
session on my desktop in one folder". Everything here is a COPY — the originals are untouched
in Desktop\MUHLNICKEL_BUILD_LAB_20260801_025117\ (vault model, nothing moved or deleted).

All of this is Bryce Muhlnickel's design. Session dates: 2026-08-01 → 2026-08-04.

## The 12 Sub-Zero Archetype fabricators (muhl_fab_*.py)

**STATUS 2026-08-05: 12 OF 12 LIVE.** EAL, MHA, HPC fabricated 2026-08-05 ...
```

Then the **table still says** EAL / MHA / HPC = "written, awaits owner run" and the chimera bullets still say "awaits owner run." Header vs table disagree. Live registry matches the header for the twelve and for `dmb_awcg` + `nmpis_cgat`. Table/chimera bullets are stale. `ardr_eal` still awaits.

---

## INDEX / CIRCUIT_PFC vs live

| source | says | authority |
|---|---|---|
| `MUHL_SUBZERO_ARCHETYPES\INDEX.md` header | 12/12 LIVE (08-05) | agrees with registry |
| same file, status table | EAL MHA HPC "awaits owner run" | **STALE** |
| same file, chimeras | all three await | **STALE** for dmb_awcg and nmpis_cgat; **true** for ardr_eal |
| `docs/CIRCUIT_PFC.md` | 138 circuits, 07-21; no Sub-Zero names | **stale by omission** (predates the cluster) |
| `docs/INDEX.md` | no Sub-Zero / alife / rookery | silent |
| `titan_circuits.json` mtime 2026-08-13 | all twelve + alife + two chimeras + hpc_fabric | **LIVE** |

---

## Dates ("that time")

| when | what |
|---|---|
| 2026-08-01 | architecture / resident / lineage / ring maps (copies) |
| 2026-08-03 | most fab scripts, patent ideas, master spec, 9 of 12 archetypes written |
| 2026-08-04 | master provisional (95 KB) — §5.23 twelve archetypes, §5.24 chimeras |
| 2026-08-05 | EAL MHA HPC clacker chimera_dmb fabs; alife 20:25; folder INDEX; rookery fabs |
| 2026-08-06 | `muhl_hpc_fabric` |
| 2026-08-07 | `ROOKERY0.mno` mtime |
| 2026-08-13 | titan.gguf / registry later writes (cluster already in) |
