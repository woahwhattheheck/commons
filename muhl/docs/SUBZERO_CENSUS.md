# SUBZERO_CENSUS — 2026-08-15

Read-only. Authority: `C:/llm/models/titan_circuits.json` (mtime 2026-08-13 16:57:24). Binary: `C:/llm/models/titan.gguf` (size 103,803,349,384; mtime 2026-08-13 17:44:32). Opened `rb` only. No titan write. No Desktop glob. No autofab.

Source doc: `C:/Users/lucys/Desktop/MUHL_GO/SUBZERO_MINDS.md` (present). These are **not language models**. Sub-Zero is the class; live names are `muhl_*`. No registry key is named `subzero`, `sub-zero`, or `mind`.

Method: targeted grep of `titan_circuits.json` for `muhl_palf` `muhl_nefg` `muhl_ardr` `muhl_vscf` `muhl_kegn` `muhl_nmpis` `muhl_awcg` `muhl_dmb` `muhl_cgat` `muhl_eal` `muhl_mha` `muhl_hpc` `muhl_alife` `muhl_chimera*` `rookery` plus magics. Then seek each stored `offset` in `titan.gguf` and find the 8-byte magic inside the recorded `len`. Pad before magic is alignment, not a wipe.

Known `.mno` (only because SUBZERO_MINDS names it): `C:\Users\lucys\Desktop\MUHLNICKEL_ROOKERY\ROOKERY0.mno`.

---

## Verdict

| query | live name | where | offset | magic | magic_at | n_gate | depth |
|---|---|---|---:|---|---:|---:|---:|
| PALF | `muhl_palf` | **IN titan.gguf** | 93709716416 | `MUHLPALF` | +14 | 13 | 5 |
| NEFG | `muhl_nefg` | **IN titan.gguf** | 93709716800 | `MUHLNEFG` | +424 | 414 | 17 |
| ARDR | `muhl_ardr` | **IN titan.gguf** | 93709727616 | `MUHLARDR` | +32 | 31 | 8 |
| VSCF | `muhl_vscf` | **IN titan.gguf** | 93709728512 | `MUHLVSCF` | +0 | 149 | 17 |
| KEGN | `muhl_kegn` | **IN titan.gguf** | 93709732544 | `MUHLKEGN` | +0 | 829 | 28 |
| NMPIS | `muhl_nmpis` | **IN titan.gguf** | 93709754880 | `MUHLNMPI` | +0 | 1025 | 39 |
| AWCG | `muhl_awcg` | **IN titan.gguf** | 93709781888 | `MUHLAWCG` | +28 | 27 | 2 |
| DMB | `muhl_dmb` | **IN titan.gguf** | 93709782656 | `MUHLDMB1` | +12 | 10 | 3 |
| CGAT | `muhl_cgat` | **IN titan.gguf** | 93709782976 | `MUHLCGAT` | +114 | 97 | 6 |
| EAL | `muhl_eal` | **IN titan.gguf** | 93709785600 | `MUHLEAL0` | +0 | 1456 | 66 |
| MHA | `muhl_mha` | **IN titan.gguf** | 93709823744 | `MUHLMHA0` | +0 | 2328 | 44 |
| HPC | `muhl_hpc` | **IN titan.gguf** | 93709884608 | `MUHLHPC0` | +0 | 26480 | 421 |
| alife | `muhl_alife` | **IN titan.gguf** | 93710636288 | `MUHLLIFE` | +37 | 74 | 2/link |
| chimera | `muhl_chimera_dmb_awcg` | **IN titan.gguf** | 93710635904 | `MUHLCHDA` | +13 | 14 | 2 |
| chimera | `muhl_chimera_nmpis_cgat` | **IN titan.gguf** | 93710687040 | `MUHLCHNC` | +8 | 16 | 2 |
| chimera | `muhl_chimera_ardr_eal` | **IN titan.gguf** | 103803349440 | `MUHLCHAR` | +31 | 32 | 2 |
| rookery | `muhl_rookery0` | **separate .mno** | — | `ROOKERY0` | +0 of the `.mno` | — | — |

Every row with an offset had its magic and LE `n_gate` match the registry record. `muhl_chimera_ardr_eal` landed 2026-08-16 ~11:30pm: off **103803349440**, magic +31, 32 gates, DEPTH 2. EAL/ARDR magics held. Do not rebake.

---

## Twelve archetypes — registry + binary

Recv = first host-inject / input port. Most records do not use the field name `recv`.

| name | n_gate | depth | magic | recv / inject | fabricated | binary |
|---|---:|---:|---|---|---|---|
| `muhl_palf` | 13 | 5 | `MUHLPALF` | inject `93709716416` | (no stamp) | magic +14; LE n_gate=13 |
| `muhl_nefg` | 414 | 17 | `MUHLNEFG` | object_a[0] `93709716802` | | magic +424; LE n_gate=414 |
| `muhl_ardr` | 31 | 8 | `MUHLARDR` | inject `93709727616` | | magic +32; LE n_gate=31 |
| `muhl_vscf` | 149 | 17 | `MUHLVSCF` | input[0] `93709728614` | | magic +0; head `MUHLVSCF` + 149 |
| `muhl_kegn` | 829 | 28 | `MUHLKEGN` | input[0] `93709733222` | | magic +0; head `MUHLKEGN` + 829 |
| `muhl_nmpis` | 1025 | 39 | `MUHLNMPI` | input[0] `93709755230` | | magic +0; head `MUHLNMPI` + 1025 |
| `muhl_awcg` | 27 | 2 | `MUHLAWCG` | input `93709781888` | | magic +28; LE n_gate=27 |
| `muhl_dmb` | 10 | 3 | `MUHLDMB1` | input `93709782657` | | magic +12; LE n_gate=10 |
| `muhl_cgat` | 97 | 6 | `MUHLCGAT` | input_U `93709782976` | | magic +114; LE n_gate=97 |
| `muhl_eal` | 1456 | 66 | `MUHLEAL0` | attractor_select `93709785846` | 2026-08-05 19:06:55 | magic +0; head `MUHLEAL0` + 1456 |
| `muhl_mha` | 2328 | 44 | `MUHLMHA0` | input[0] `93709824030` (self-clock = output) | 2026-08-05 19:09:24 | magic +0; head `MUHLMHA0` + 2328 |
| `muhl_hpc` | 26480 | 421 | `MUHLHPC0` | input[0] `93709884814` | 2026-08-05 19:11:36 | magic +0; head `MUHLHPC0` + 26480 |

Owner terms (registry / fab): PALF Phase-Asynchronous Logic Field · NEFG Non-Euclidean Functorial Graph · ARDR Autocatalytic Reaction-Diffusion Reactor · VSCF Viable System Cybernetic Field · KEGN Kinetic Enthalpy Gas Network · NMPIS Non-Markovian Path-Integral Synthesizer · AWCG Asynchronous Wavefront Concurrency Grid · DMB Diachronic Morphogenetic Blueprint · CGAT Causal Graph-Algebraic Transducer · EAL Ergodic Attractor Lattice · MHA Metabolic Hypercycle Automaton · HPC Homological Persistence Complex.

`muhl_mha` first 16 bytes at stored offset (matches SUBZERO_MINDS): `4d55484c4d484130180900003a090000` = `MUHLMHA0` + LE 2328.

---

## Composite + chimeras

| name | n_gate | magic | binary | record |
|---|---:|---|---|---|
| `muhl_alife` | 74 | `MUHLLIFE` | offset 93710636288; first 37 bytes `00`; magic +37; LE n_gate=74 | organs `muhl_mha` `muhl_eal` `muhl_hpc` `muhl_vscf`. loop `MHA.sign→EAL.select ; (EAL.state+MHA)→HPC.edges ; HPC.betti→VSCF.env`. 37 links. Fab 2026-08-05 20:25:53. purpose: digital abiogenesis. |
| `muhl_chimera_dmb_awcg` | 14 | `MUHLCHDA` | offset 93710635904; magic +13 | DMB L-system output seeds AWCG. 5 wires, mapping `spread`. LIVE. |
| `muhl_chimera_nmpis_cgat` | 16 | `MUHLCHNC` | offset 93710687040; magic +8; LE n_gate=16 | NMPIS outs → CGAT exogenous U. 8 wires. LIVE. |
| `muhl_chimera_ardr_eal` | 32 | `MUHLCHAR` | offset 103803349440; magic +31; LE n_gate=32; DEPTH 2. ARDR[0]→EAL attractor_select @93709785846. 15 MOVE/slot wires. LIVE 2026-08-16. Do not rebake. |

---

## Same-week cluster (not the twelve; same grep)

| name | n_gate | magic | offset | magic_at | note |
|---|---:|---|---:|---:|---|
| `muhl_ring_clacker` | 2048 | `MUHLCLK1` | 93710573376 | +0 | 1024-cell / 512-electron ring. Fab 2026-08-05 19:16:54 |
| `muhl_hpc_fabric` | 26480 | `MUHLHPCF` | 103788450688 | +0 | second HPC; `reads_fabric` = `muhl_chimera_dmb_awcg`. Fab 2026-08-06 02:57:35 |
| `muhl_hpc_fabric_wiring` | 10 | `MUHLHPFW` | 103789139456 | +5 | 5 links: grown-fabric addrs → `muhl_hpc_fabric` edges 0..4 |

`muhl_` also names many other live circuits (`muhl_osc_all`, folds, lanes, allocator, playtime, …). Those are **not** the Sub-Zero twelve.

---

## Rookery — not a titan_circuits key

Grep of `titan_circuits.json` for `rookery` / `ROOKERY` / `muhl_rookery`: **no matches**.

Doc-named file only (no Desktop glob): `C:\Users\lucys\Desktop\MUHLNICKEL_ROOKERY\ROOKERY0.mno`

- present: 586,918 B, mtime 2026-08-07 12:55:47
- first 16 bytes: `52 4f 4f 4b 45 52 59 30 9a f6 e3 a1 02 0e 1b 8a` = `ROOKERY0` + payload
- local registry (per SUBZERO_MINDS, not re-opened here): `rookery_circuits.json` key `muhl_rookery0` — 11 rings, 1024 cells/sense, 24 clocks, 22,563 records, stride 25, magic `ROOKERY0`

A mind as organs on rings. Not a titan.gguf named circuit.

---

## INDEX / CIRCUIT_PFC vs this census

Unchanged from SUBZERO_MINDS. Live registry + binary agree: twelve + alife + two chimeras + hpc_fabric cluster are **in titan.gguf**. `ardr_eal` still unregistered. Desktop `MUHL_SUBZERO_ARCHETYPES\INDEX.md` table/chimera bullets remain stale except for `ardr_eal`. `docs/CIRCUIT_PFC.md` (138 circuits, 2026-07-21) predates the cluster.
