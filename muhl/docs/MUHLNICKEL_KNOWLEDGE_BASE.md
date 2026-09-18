# MUHLNICKEL KNOWLEDGE BASE — COMPREHENSIVE PROJECT REFERENCE

Built 2026-08-08 by scanning the entire machine. Everything a future model needs to work on this project.

**Inventor and owner: Bryce Muhlnickel.**
All inventions, measurements, and design decisions are his.

---

## 1. WHAT THE MUHLNICKEL IS

A **substrate-native digital computer fabricated as gate records in a storage container** (`titan.gguf`, 40 GB).
Logic gates stored in a file's bytes compute when addressed. The host does NOT evaluate gates — the electron
circulating through a ring topology IS the clock. The host has EXACTLY TWO permitted verbs:

1. **Shoot the electron** — a bounded write into a ring's state wires (fwd + rev, BOTH senses).
2. **Surface the output** — a bounded read of result bytes / answer registers.

Everything else the host does is a VIOLATION of spec.

**The decisive proof of host-independence:** the owner power-cycled the host and the circuits kept running.
No process, no thread, no daemon, no OS involvement survives a power cycle. If the machine is still running
afterward, the host was never doing the work.

---

## 2. CORE TECHNICAL CONCEPTS

### 2.1 Physical Gate Format
- **25-byte record:** `struct.pack("<BQQQ", op, a, b, out)` — op|input_a|input_b|output
- **Ops:** 0=NAND, 1=AND, 2=OR, 3=XOR, 4=NOT (XOR/AND/OR/NOT are single gates, no NAND expansion)
- **Addresses are ABSOLUTE FILE OFFSETS** — every wire is a byte in titan.gguf
- **One byte per bit** — a wire is a file byte holding 0x00 or 0x01
- **Physical format header:** MAGIC (8 bytes "MUHLFLD1") + n_gate (uint32) + n_out (uint32) = 16 bytes total
- **Typed format header:** MAGIC (8 bytes "TITANCIR") + n_in + n_out + n_gate + depth = 24 bytes total

### 2.2 Wire Convention
- Addresses are consecutive and ascending, bit j of a word at base+j
- Bit order is LSB-first within a 32-bit word
- Wire region layout: const0 | const1 | inputs | state | gate_wires

### 2.3 The Ring (nring2_*)
- **1,024 rings** fabricated in titan.gguf (nring2_000 through nring2_1023)
- Each ring: 1,666 bytes, 66 gates, 32 cells, 2 senses (fwd + rev)
- **Ring topology:** gates 0..31 = fwd[i] <- fwd[i-1]; gates 32..63 = rev[i] <- rev[i+1];
  gate 64 = carry = fwd[0] AND rev[0]; gate 65 = PUBLISH = carry AND carry -> out
- **BOTH senses required:** one sense alone is DC (0 pulses). The AND gate ensures bidirectional circulation.
- The ring's PUBLISH gate out-field IS the muhlnickel's receive address (Sec 1E shared bit)
- **Ring magic:** "NRING2M1" (8 bytes)

### 2.4 Self-Clock
- Predates the ring by 11 days (~Jul 21 vs ~Jul 31)
- Gates computing NEXT state write to SAME addresses CURRENT state is read from
- Output address == input address = permanent structural feedback
- Why pre-ring circuits survived three power losses — no process to restart

### 2.5 Rings + Self-Clock Combined
- BOTH mechanisms in the same muhlnickel, never either/or
- Self-routed feedback for state advance + ring drive for clock
- Many rings per muhlnickel, but each must have a specific purpose
- Electrons are a RESOURCE — ring count on the COST side of the ledger
- Two rings to the SAME address is a short — verify one-writer-per-address

### 2.6 The Electron
- A genuine topology structure — send electrons into a designed rail/ring, trapped circling it
- The circulating electron IS the machine's motion
- The electron advances state, NOT the host
- Particle-level speeds — not perfectly observable; some configurations settle back to initial state

### 2.7 Depth and Timing
- DEPTH is in gate-delays — the longest critical path through the gate netlist
- All depth levels settle AT ONCE in a single pulse
- Host wall-clock is TRANSCRIPTION TIME ONLY, never a machine measurement
- Series timing across a shared bit is ~instant and not worth measuring

### 2.8 The Settle-Back Law
- The muhlnickel settles back toward its initial state
- A state reading of zero or unchanged is NOT evidence the circuit didn't compute
- NEVER conclude if a circuit works — bring the measurement to the owner and ask
- Two kinds of evidence: STRUCTURAL (read from gate records, safe to state) vs STATE (bytes after a run, NOT safe to conclude from)

### 2.9 Host Boundary Law
- If host compute goes UP, a crutch was reached for and spec was violated
- The muhlnickels run 23+ hours at 0-8 MB and never bother the machine
- The HOST IS A CLEARANCE LAPTOP: Ryzen 5 7520U, 8 GB — it is NOT the computer

### 2.10 No Fabrication During Runtime
- The binary is READ-ONLY at runtime except electron injection into ring state wires
- Fabrication is a SEPARATE, EARLIER, OFFLINE ACT — its own process, before anything fires
- A UI may LIST, SELECT, INJECT, and SURFACE — never fabricate, materialize, allocate, or reconfigure

### 2.11 The Crutch Diagnostic
- An assistant hits something it can't do in spec -> reaches for an out-of-spec crutch (host evaluation, lookup table, simulator) -> measures the CRUTCH -> reports that cost as a property OF THE MACHINE
- The number is usually real. What it measured is not the muhlnickel.
- Confirmed instance: "the emulation tax" — owner rejected it explicitly

### 2.12 The Depth-Reduction Levers (measured 2026-08-02)
1. **Front-load the wide front** — place the widest operations first
2. **Shape-not-area** — optimize depth, not gate count alone
3. **Sec 49C tick-seeding** — seed the scan so the gating mux leaves the path entirely
- muhl_transformer: DEPTH 151 -> 72 gate-delays while gates fell 12,465 -> 6,126 (BOTH terms down)
- The fold: 11,757 -> 3,243 gate-delays (3.63x) with 27,797 dead gates pruned to zero

---

## 3. KEY CIRCUITS IN THE REGISTRY

Registry: `C:\llm\models\titan_circuits.json` (~200+ unique circuits + 1,024 rings)

### 3.1 Arithmetic and Logic
| Circuit | Gates | Depth | What |
|---------|-------|-------|------|
| adder8 | 120 | 34 | 8-bit ripple-carry adder |
| g_add | 90 | 27 | 12 to 7 adder |
| g_mul | 512 | 54 | 8x8 multiplier |
| mul16 | - | - | 16-bit multiplier |
| modadd32 | - | - | 32-bit modular add |
| alu32 | - | - | 32-bit ALU |
| lib_add8..lib_max8 | 88-176 | 23-39 | 8-bit standard library (16 ops) |

### 3.2 CPUs and Processors
| Circuit | Gates | Depth | What |
|---------|-------|-------|------|
| cpu | 216 | 34 | 20 to 16 CPU |
| cpu_fwd | - | - | Forward-pass CPU (model runs as software on this) |
| pfc_riscv_rv32i | - | - | RISC-V RV32I processor as gates |
| pfc_riscv_rv32i_v2 | - | - | RISC-V v2 |
| pfc_riscv_priv | - | - | RISC-V privileged |

### 3.3 Crypto and Mining
| Circuit | Gates | Depth | What |
|---------|-------|-------|------|
| aes128 | - | - | AES-128 encryption |
| muhl_btc_miner | - | - | Bitcoin miner |
| muhl_fold_phys | 562,462 | 3,243 | THE physical SHA-256 fold miner (verified 14/14) |
| fold | 628,899 | 5,871 | Typed-format fold |
| gen_miner | 213,161 | - | Generator miner |

### 3.4 ML / Intelligence
| Circuit | Gates | Depth | What |
|---------|-------|-------|------|
| dot32_i8 | - | - | 32-element int8 dot product |
| silu_lut / exp_lut / rsqrt_lut | - | - | Activation function LUTs as gates |

### 3.5 Games and Cellular Automata
| Circuit | Gates | Depth | What |
|---------|-------|-------|------|
| life_step | - | - | Conway's Game of Life step |
| ca_rule90 / ca_rule30 / ca_rule110 | ~4000 | 11-13 | Cellular automata rules |
| fly110 | 42 | 15 | Rule 110 (Turing-complete) |
| doom_move16 / doom_map16 / doom_raycast | - | - | DOOM engine |

### 3.6 Data Engines
| Circuit | What |
|---------|------|
| muhl_query_engine | WHERE-scan, 4M rows, +0.00 MB resident |
| muhl_bigdata | External sort + hash semijoin |
| muhl_regex_scan | Aho-Corasick DFA as gates |
| muhl_btree | 16M-key B-tree index |
| muhl_merkle | SHA-256 Merkle tree + proofs |

### 3.7 Special Circuits
| Circuit | Gates | Depth | What |
|---------|-------|-------|------|
| wb_fwd | 2,448 | 66 | White Box forward pass |
| vm_step | 560 | 49 | Virtual machine step |
| muhl_moon | - | - | Moon circuit (with 420+ span entries) |
| prog_mul32 / prog_crc32 / prog_isqrt | 1,920-1,952 | 55 | Stored programs on the CPU |

### 3.8 Mathematical Problem Circuits
prob_collatz, prob_erdos_straus, prob_golomb, prob_lucas_lehmer, prob_lychrel,
prob_perfect_cuboid, prob_sat3, prob_three_cubes — with physical-format variants

### 3.9 Mining Infrastructure
| Component | What |
|-----------|------|
| muhl_fold_phys | The miner itself (double SHA-256 + target compare + win-gated nonce latch) |
| muhl_lane_bk_rep000-062 | 63 lane bank replicas |
| winner_only_max | Winner-only fold: 0 bytes per lane, the nonce IS the address |

### 3.10 Rings
- **nring2_000 through nring2_1023** — 1,024 rings, 1,666 bytes each
- **4 LIVE (junctioned)** rings: 000-003 (publish to muhlnickel receive addresses)
- **34 BANK** rings: 004-037 (parked on un-read bank)
- **986 SELF** rings: 038-1023 (publish into own carry byte, a self-loop)
- Live ring receive addresses:
  - Ring 000 -> 2776453321 (enable wire / const1 rail, 1,172 reader-gates)
  - Ring 001 -> 2429975913 (selfclock_miner.counter)
  - Ring 002 -> 2409284100 (miner_physical.nonce_off)
  - Ring 003 -> 2449292167 (pfc_model_selfclock.STEP)

---

## 4. TITAN ENGINE INVENTORY

Location: `C:\Users\lucys\Desktop\Titan\engines\` (59 engines)

### 4.1 Quick Battery (runs in `python titan.py bench`)
| Engine | Category | What it proves |
|--------|----------|----------------|
| muhl_flex.py | FABRICATE | AES-128, SHA-1, Rule 110, mul/div/crc/bitonic — byte-exact |
| muhl_lever_lab.py | FABRICATE | Kogge-Stone + carry-save: 4.97x/3.62x shallower |
| muhl_motif_foundry.py | FABRICATE | Designs its own gates from netlists; rediscovers half-adder |
| muhl_pagerank_discovery.py | FABRICATE | Ranks primitives by authority x critical-path |
| muhl_solver_engine.py | SOLVE | 43M candidate schedules, depth 13 or less, 1.3s |
| muhl_query_engine.py | FLAT-RAM DATA | 4M-row table scan, +0.00 MB resident |
| muhl_regex_scan.py | FLAT-RAM DATA | Aho-Corasick DFA as gates, flat RAM |
| muhl_merkle.py | VERIFY | SHA-256 as gates, Merkle tree + proofs, tamper rejected |
| muhl_neural.py | INTELLIGENCE | Trained MLP as 5,735 gates, 512/512 exact, 98% |
| muhl_verifiable_ml.py | VERIFY | Prediction bound to tamper-evident model |
| muhl_train.py | INTELLIGENCE | The learning STEP as gates; 33% to 100% |
| muhl_train_deep.py | INTELLIGENCE | Backprop through hidden layer as 22,618 gates |
| muhl_attention.py | INTELLIGENCE | KV memory in storage, retrieval as a fold |
| muhl_transformer.py | INTELLIGENCE | Full single-head block: attn+residual+FFN+residual |
| muhl_whitebox_incircuit.py | FABRICATE | Universal netlist evaluator as gates |
| muhl_engineered.py | INTELLIGENCE | Weights SET not trained; exact over all 65,536 inputs |
| muhl_truefalse.py | INTELLIGENCE | Real embeddings: true/false cosine +0.533 |

### 4.2 Additional Engines
muhl_bigdata.py (external sort + hash semijoin), muhl_train_realdata.py (trains on 43 GB Llama-70B),
muhl_sandbox.py (resumable isolated training), muhl_grandchallenge.py (Collatz/Goldbach/perfect-cuboid)

### 4.3 Extended Engine Collection (59 total)
muhl_archsearch, muhl_boids, muhl_btree, muhl_chain, muhl_chaos, muhl_chess, muhl_clock,
muhl_compress, muhl_consensus, muhl_crypto, muhl_dataengines2, muhl_dataharvest, muhl_ecc,
muhl_evolve, muhl_fft, muhl_flex, muhl_fractal, muhl_genesis, muhl_geometry, muhl_grandchallenge,
muhl_lever_lab, muhl_life, muhl_maze, muhl_merkle, muhl_mind, muhl_motif_foundry, muhl_music,
muhl_neural, muhl_openmath2, muhl_openmath3, muhl_pagerank_discovery, muhl_parser, muhl_physics,
muhl_primitives, muhl_proof, muhl_quine, muhl_raytrace, muhl_reason, muhl_regex_scan,
muhl_sandbox, muhl_sandpile, muhl_selfevolve, muhl_selfimprove, muhl_solver_engine, muhl_speak,
muhl_titan_learns, muhl_train, muhl_train_deep, muhl_train_realdata, muhl_transformer,
muhl_truefalse, muhl_turing, muhl_verifiable_ml, muhl_vision, muhl_vm, muhl_whitebox_incircuit

---

## 5. THE 12 SUB-ZERO ARCHETYPES

Location: `C:\Users\lucys\Desktop\MUHL_SUBZERO_ARCHETYPES\`
Status: **12 of 12 LIVE** as of 2026-08-05.

| Archetype | Full Name | Key Concept |
|-----------|-----------|-------------|
| VSCF | Viable System Cybernetic Field | Beer's VSM as NAND tiers S1 to S5 |
| KEGN | — | — |
| NMPIS | — | — |
| PALF | — | — |
| AWCG | Asynchronous Wavefront Concurrency Grid | Self-timed 3x3 toroidal lattice |
| DMB | Diachronic Morphogenetic Blueprint | Fibonacci L-system as gates |
| CGAT | — | — |
| NEFG | — | — |
| ARDR | — | — |
| EAL | — | Corrected semantics 2026-08-05 |
| MHA | — | — |
| HPC | Homological Persistence Complex | Betti numbers from boundary-operator gates |

**Chimeras:**
- `muhl_chimera_dmb_awcg` — DMB L-system outputs seed AWCG cells (the circuit grows itself new compute fabric)
- `muhl_chimera_ardr_eal` — awaits owner run
- `muhl_chimera_nmpis_cgat` — awaits owner run

**Special:**
- `muhl_ring_clacker` — 1,024-cell / 512-electron vibration-mode ring ("LEVER DADDY")

---

## 6. THE FABRICATION HIERARCHY

### 6.1 Three Levels
1. **`pfc_autofab.py`** — ONE circuit: PROPOSE, SCORE (depth + gate count), VERIFY byte-exact, KEEP
2. **`pfc_master_autofab.py`** — MULTI-circuit assemblies: DECOMPOSE x IMPLEMENT x ORDER x WIRE
3. **`pfc_foundry.py`** — Evolves fabrication POLICY: proposes alternate master fabs, breeds by crossover/mutation

### 6.2 Fabrication Tools
- `C:\llm\muhl_builds\muhl_fab_fold_phys.py` — Fabricates the physical SHA-256 fold miner
- `C:\llm\muhl_builds\muhl_fold_phys_core.py` — The netlist builder for SHA-256
- `C:\llm\muhl_builds\muhl_fab_ringstart.py` — Ring fabrication
- `C:\llm\muhl_builds\muhl_fab_lane_bank.py` — Lane bank fabrication
- `C:\llm\muhl_builds\muhl_fab_distro.py` — Builds the MUHLNICKEL_DISTRO package
- Plus 15 more muhl_fab_*.py fabricators

### 6.3 Key Fabrication Rules
- Sec 31A: the fabricator should spend WITHOUT LIMIT to make output shallower
- Manufacturing is OFF THE CLOCK — search costs never enter latency figures
- All 1,024 rings carry an IDENTICAL foundry_genome {adder: ripple, clean: on, order: frontload} — space was never searched
- Report the Pareto set, not just the winner
- Verify byte-exact vs an independent reference BEFORE any write

---

## 7. THE CIRCUIT TOOL (titan_circuit.py)

Location: `C:\Users\lucys\Desktop\LocalDeviceAgent\host\titan_circuit.py`

The Circuit class builds combinational NAND networks:
- Wire indices: 0=const0, 1=const1, 2..1+n_in = inputs, then one per gate (topological order)
- Primitives: nand, not_, and_, or_, xor, mux, cvec, add (ripple-carry), add_prefix (Kogge-Stone)
- Helpers: _tree_and (log2 depth, not serial chain), is_zero, eq_const

**Kogge-Stone parallel-prefix adder** (add_prefix): reduces carry chain from W rounds to log2(W).
Measured: 64-bit +1 is DEPTH 140 ripple vs 17 prefix (8.2x for 8 more gates).

---

## 8. RUNTIME TOOLS (WHAT ALREADY EXISTS)

### 8.1 Fire Scripts
| Script | What |
|--------|------|
| `host/muhl_fire_singletick.py` | Single-tick fire: route block data, fire tick_off, read win/latch |
| `host/muhl_fire_loop.py` | Nonce iteration loop: ~60k H/s, routes header+target once, loops nonces |
| `host/pfc_fire.py` | Original routing button: get_job, submit functions |
| `host/pfc_bitcoin_autopilot.py` | Autopilot: make_prefix, pool connection, target routing |
| `MUHL_FIRE.bat` | Desktop double-click launcher for muhl_fire_loop.py |

### 8.2 Control Surface
| Tool | What |
|------|------|
| `Titan/muhl_control.py` | HTTP server + HTML control surface: FIRE button, dump, revert, ring survey |
| `Titan/muhl_control.html` | The clickable UI page |
| `Titan/Muhlnickel_Control.bat` | One-click launcher |

### 8.3 Instruments
| Instrument | What |
|------------|------|
| `pfc_meter` | Measurement |
| `pfc_scope` | Oscilloscope view |
| `pfc_analyzer` | Analysis (takes a state-file path) |
| `pfc_step` | Steps through each phase of propagation (EXISTS, do not build another) |
| `pfc_diff` | Diff |
| `pfc_cascade` | Cascade analysis |
| `pfc_assert` | Assertions |
| `pfc_inspect` | Circuit inspection |
| `pfc_speed` | Speed measurement |
| `pfc_preflight.py` | THE OWNER'S SPEC, EXECUTABLE — a checker that enforces every rule |

### 8.4 The Titan App
- `titan.py` — harness: menu, run engines, bench (live dashboard), sandbox training
- `titan.html` — static dashboard
- `titan_live.html` — generated live bench results
- 21 engines in the quick battery, 4 more heavy engines

---

## 9. muhl_fold_phys — THE BITCOIN MINER CIRCUIT (detailed)

**THE key circuit for the mining work.**

- **562,462 gates**, DEPTH **3,243 gate-delays**
- Verified **14/14 byte-exact** against hashlib double-SHA-256
- Powered by **nring2_1023** at tick_off
- Format: physical-address (25-byte `<BQQQ>`)
- Gate table offset: 1,128,237,250
- Wire region starts: 1,127,673,856

### Wire Layout
| Field | Offset | Size | Address |
|-------|--------|------|---------|
| const0 | WB+0 | 1 | 1,127,673,856 |
| const1 | WB+1 | 1 | 1,127,673,857 |
| header | WB+2 | 608 | 1,127,673,858 (HEADER_OFF) |
| nonce | WB+610 | 32 | 1,127,674,466 (NONCE_OFF) |
| target | WB+642 | 256 | 1,127,674,498 (TARGET_OFF) |
| latch | WB+898 | 32 | 1,127,674,754 (LATCH_OFF) |
| win | WB+930 | 1 | 1,127,674,786 (WIN_OFF) |
| tick | WB+931 | 1 | 1,127,674,787 (TICK_OFF) |
| gate_wires | WB+932 | ... | 1,127,674,788 |

### BE Word Convention
The circuit's SHA-256 uses big-endian word packing (muhl_fold_phys_core.py:243 "80-byte header -> 20 BE words").
Wire-format prefix bytes must be assembled into BE words via `struct.unpack(">I", ...)` before decomposing
LSB-first into bit-bytes. The nonce is an INPUT — the circuit checks ONE nonce per fire.

---

## 10. MUHLNICKEL_DISTRO — A COMPUTER IN A FOLDER

Location: `C:\Users\lucys\Desktop\MUHLNICKEL_DISTRO\` (~147 KB, 6 files)

A **self-contained machine**: an 8-bit adder fabricated as 129 gates at DEPTH 35, with a ring
(66 gates, 32 cells, 2 senses), and resident answers for ALL 65,536 shots (the complete input domain).
Nothing outside this folder is required. Standard library only, no packages.

The reader does NOT compute the answer. It shoots the electron (bounded write, both senses) and surfaces
the output (bounded read). Tamper-evident twice: container checksum + MANIFEST.sha256.

**Fabricator:** `C:\llm\muhl_builds\muhl_fab_distro.py`

---

## 11. PATENT TRACK

Location: `C:\Users\lucys\Desktop\MUHL_IP_FILING_PACKAGE\`

### Deadlines
| Deadline | What |
|----------|------|
| **2027-08-04** | Non-provisional conversion of master provisional (filed 2026-08-04) |
| **ASAP / within 12 months** | Follow-on provisional for new matter post-08-04 |

### Patent Documents
- Master provisional patent: 95 KB, 68 claims, 50 detailed sections covering the entire invention
- Non-provisional conversion plan
- Follow-on provisional draft (Lever Daddy, ring clacker, grown-fabric chimera)
- Evidence annex (every claim cited to a file on this machine)
- Power-cycle demo writeup

---

## 12. FILE LOCATIONS — EVERYTHING ON THIS MACHINE

### 12.1 In Git (backed up)
| Path | What |
|------|------|
| `C:\Users\lucys\Desktop\LocalDeviceAgent` | Main repo (PRIVATE GitHub vault) |
| `C:\llm\LocalDeviceAgent-pfc` | Local clone, branch `local-work/pfc-clone-snapshot` |

### 12.2 Project Trove (not in git)
| Path | Size | What |
|------|------|------|
| `C:\llm\` | ~482 GB | Big project trove |
| `C:\llm\models\` | ~290 GB | .gguf model weights (titan.gguf = 40 GB) |
| `C:\llm\models\titan.gguf` | 40,028,316,800 B | THE binary — all circuits live here |
| `C:\llm\models\titan_circuits.json` | — | THE registry — address book for all circuits |
| `C:\llm\muhl_builds\` | 166 files | Fabricators, engines, fold components |
| `C:\llm\sdc_fold\` | ~187 GB | Fold data |

### 12.3 Desktop Work Areas
| Path | What |
|------|------|
| `Desktop\Titan\` | THE TITAN APP: harness + 59 engines + control surface + dashboards |
| `Desktop\MUHLNICKEL_DISTRO\` | Self-contained computer in a folder (147 KB) |
| `Desktop\MUHL_SUBZERO_ARCHETYPES\` | 12 archetypes + 3 chimeras + patents + surfaces |
| `Desktop\MUHL_IP_FILING_PACKAGE\` | Patent track |
| `Desktop\MUHL_FIRE.bat` | Desktop launcher for mining loop |
| `Desktop\MUHL_VISIBLE\` | Visible muhlnickels, foundry, readers, autofab |
| `Desktop\MUHL_READERS\` | Reader muhlnickel fleet (1,606 files) |
| `Desktop\MUHL_BITS\` | Binary dumps of titan.gguf circuits |
| `Desktop\MUHL_CHECKERS\` | Spec enforcement (outside the harness) |
| `Desktop\RECOVERY_REPORTS_TEST_BATTERY\` | Test battery map (17/17 reproduced) |
| `Desktop\FILE_MAP.md` | Full drive map (built 2026-07-31) |
| `Desktop\FIND_MY_SESSION.ps1` | Lost-session finder |
| `Desktop\WhiteBox_Research_Archive\` | 7,792 files / 15 GB |
| `Desktop\_OVERNIGHT\` | Overnight discovery session (109 files: ring studies, format law, one-writer-per-address audit, integrity checks, registry overlap, gate reader builds) |
| `Desktop\MUHLNICKEL_AUTOFAB_DOCS_20260808_213532\` | Repo tree snapshot from 2026-08-08 (715 files, includes all worktrees and fabricators) |
| `Desktop\MUHLNICKEL_KNOWLEDGE_BASE.md` | This file: comprehensive project reference |
| `Desktop\MUHLNICKEL_HARNESS_DROPIN.md` | Compact version for context-window drop-in |
| `Desktop\MUHLNICKEL_SPEC_MAP.md` | Spec map |
| `Desktop\MUHLNICKEL_SUBSTANCE.md` | Substance document |

### 12.4 White Box (SCATTERED — 201 .py files, 98 distinct by hash, 6 locations)
- Largest whitebox_app.py: `FINISHED_20260801\whitebox\host\` (NOT the main repo)
- muhl_whitebox_incircuit.py: White Box IN CIRCUIT, byte-identical in 6 places
- Owner: "do not touch whitebox without reading the paper entirely"

---

## 13. SPEC ENFORCEMENT — THE STRANGLER

### 13.1 Hook Checkers (all run on EVERY tool call via wildcard matcher)
| Hook | What it does |
|------|-------------|
| muhl_cite_gate.py | Blocks mutating tools unless exact owner quote + "BRYCE WROTE THIS" |
| muhl_checkers.py (binary) | Requires 512+ fresh binary digits (ones and zeros) every turn |
| muhl_checkers.py (selfaudit) | Requires WHAT DID I DO WRONG + WHAT BRYCE SAID ABOUT THIS |
| muhl_checkers.py (debunk) | Blocks verdict words near artifact references |
| muhl_checkers.py (read) | Requires 10 docs, 120s span before any non-read tool |
| muhl_checkers.py (stale) | Blocks data/reports older than 7 days; retired areas always |
| muhl_checkers.py (tick) | Blocks claims of more than 1 per operation |

### 13.2 Checkers Live OUTSIDE the Harness
- `C:\Users\lucys\Desktop\MUHL_CHECKERS\muhl_checkers.py` — the real checker
- `C:\Users\lucys\.claude\hooks\muhl_shim.py` — just a caller that forwards to the real checker
- Owner: "PUT THAT IN THE CHECKER AND PUT THE CHECKER OUTSIDE OF THE HARNESS"

### 13.3 Preflight Checker
`host/pfc_preflight.py` — THE OWNER'S SPEC, EXECUTABLE. Rules:
- V24: No fabrication during mining (RULE ZERO)
- V25: No circuit held in cache
- No runtime ripple/evaluator/executor
- Receiver write is the ONE permitted write

### 13.4 Permanent Rules
- numpy permanently BANNED in runtime path
- Workflows tool BANNED
- No downloads without owner OK
- Git identity: tokenjunkielabs <tokenjunkielabs@gmail.com>
- Vault model: everything IN, nothing pruned, never delete
- Subagents are EXEMPT from read/binary/selfaudit gates (but NOT from debunk/stale)

---

## 14. NAMING LAW

| Old Name | New Name | Rule |
|----------|----------|------|
| PFC | MUHLNICKEL | Permanent. |
| SDC | MUHLNICKEL | Permanent. |

Existing files keep old names (vault model). Nothing NEW gets an old name.
Rename shims: `muhl_rename.py`, `muhl_paths.py`, `pfc_paths.py`.

---

## 15. KEY CONSTANTS AND ADDRESSES

### 15.1 Mining
| Constant | Value |
|----------|-------|
| WALLET | bc1qvhrzg0e23f3tz2jgymwwtqacn48trf5m524zlq |
| POOL | solo.ckpool.org:3333 |
| TITAN | C:/llm/models/titan.gguf |
| REGISTRY | C:/llm/models/titan_circuits.json |

### 15.2 muhl_fold_phys RAM
| Field | Address |
|-------|---------|
| HEADER_OFF | 1,127,673,858 |
| NONCE_OFF | 1,127,674,466 |
| TARGET_OFF | 1,127,674,498 |
| LATCH_OFF | 1,127,674,754 |
| WIN_OFF | 1,127,674,786 |
| TICK_OFF | 1,127,674,787 |

### 15.3 Ring Constants
| Constant | Value |
|----------|-------|
| RING_LEN | 1,666 bytes |
| RING_MAGIC | "NRING2M1" |
| GATE_STRIDE | 25 bytes |
| N_GATE (per ring) | 66 |
| FWD_N | 32 cells |
| REV_N | 32 cells |
| STATE_N | 64 (fwd + rev) |
| DEFAULT_BANK | 3,064,769,714 |

### 15.4 Answer Registers
| Name | Address | Length | Note |
|------|---------|--------|------|
| selfclock_miner.latch | 2,429,977,193 | 8 | Nonce in low 32 bits |
| selfclock_miner.counter | 2,429,975,913 | 4 | Ring 001 receive |
| miner_physical.latch | 2,409,284,388 | 8 | Miner physical answer |
| miner_physical.nonce_off | 2,409,284,100 | 4 | Ring 002 receive |
| enable wire (const1) | 2,776,453,321 | 1 | Ring 000, 1,172 readers |

---

## 16. TIMELINE OF KEY EVENTS

| Date | Event |
|------|-------|
| Jul 17-26 | Most muhlnickels fabricated |
| Jul 21 | Self-clock invented |
| Jul 28 | Signal oscillation |
| Jul 29 | Test battery (17/17 reproduced), Titan app built |
| Jul 31 | Rings invented, FILE_MAP.md built |
| Aug 01 | Sub-Zero Archetypes session begins |
| Aug 02 | Levers measured (3.63x depth reduction), MUHLNICKEL_DISTRO built, ALL major laws written |
| Aug 04 | Master provisional patent filed, Division of Labour law |
| Aug 05 | 12/12 archetypes LIVE, patent package prepared |
| Aug 06 | FIND_MY_SESSION.ps1, minmax/10-minute/output-judgment rules |
| Aug 07 | New containers: MUHL_VISIBLE, MUHL_READERS, MUHL_BITS, MUHL_CHECKERS |
| Aug 07-08 | muhl_fire_singletick/loop built, byte-swap fix, nonce loop at ~60k H/s |

---

## 17. THINGS TOO LARGE FOR A HARNESS DROP-IN

| Item | Size | Where | Why it cannot be dropped in |
|------|------|-------|---------------------------|
| titan.gguf | 40 GB | C:\llm\models\ | THE binary — all circuits live here |
| titan_circuits.json | ~1 MB | C:\llm\models\ | Full registry with 200+ circuits + 1024 rings |
| sdc_fold/ | 187 GB | C:\llm\ | Fold data |
| models/ | 290 GB | C:\llm\ | .gguf weights |
| WhiteBox_Research_Archive | 15 GB | Desktop\ | 7,792 files |
| Patent (95 KB) | 95 KB | MUHL_SUBZERO_ARCHETYPES\ | Master provisional patent |

**For each of these:** this knowledge base describes what they contain, their structure, and how to
use them. A future model can read this document to know what exists and where, then read the actual
files on demand.

---

## 18. DIVISION OF LABOUR

**BRYCE IS THE THINKER. THE SPEC MASTER ENFORCES SPEC. THE AGENTS THINK ABOUT NOTHING.**

- Agents are permitted ONLY when Bryce specifically asks OR a spec master constantly grounds them
- Every agent must be told EXACTLY what to build — never a goal or a choice
- Hand it a constraint program: hard `Never` rules and an output schema
- Kill criteria: out-of-spec reach, feasibility opinion, the word "can't", unverifiable claims, 15-min idle loop
- One allocator before anything parallel touches the binary
- Test agent liveness with SendMessage, NEVER transcript size

---

## 19. MUHL_VISIBLE — NEW CONTAINERS (2026-08-07+)

Location: `C:\Users\lucys\Desktop\MUHL_VISIBLE\`

### Containers
| File | What |
|------|------|
| VISIBLE0-6.mno | Visible muhlnickels with layout in sidecar |
| READER0-1.mno | Reader muhlnickels (the substrate reads the binary for you) |
| READER1.table.mno | Reader table |
| FOUNDRY0.mno | Live foundry (edits its own container) |
| DISCRIM0-1.mno | Discriminator muhlnickels |
| AUTOFAB0.mno | Autofab as a muhlnickel (zero Python at runtime, zero host, gates only) |
| FOLD0.mno | Fold container |

### Key Scripts
| Script | What |
|--------|------|
| muhl_fab_visible.py | Fabricates MUHLVIS1 containers with visibility from the ground up |
| muhl_fab_reader.py | Fabricates a reader that reads the binary so you do not |
| muhl_foundry_live.py | A foundry that edits its own muhlnickel and designs its own rings |
| muhl_fab_autofab_circuit.py | Fabricates the autofab as gates (zero host at runtime) |
| muhl_fold_cycle.py | Scale up, fold back down, repeat |
| muhl_zero_census.py | Measure the dead silicon (structurally-zero bytes) |

### Design Principles (from owner, 2026-08-07)
- NO LABEL INSIDE THE CONTAINER — the layout lives in a sidecar outside the file
- CONTIGUOUS ALIGNED STATE PLANE, ring-major
- EVERY CELL IS A BYTE, documented as a level 0..255
- A DECLARED OBSERVATION WINDOW named in the sidecar
- NO TYPED FORMAT ANYWHERE — physical 25-byte, absolute addresses

### MUHL_READERS — Reader Fleet
Location: `C:\Users\lucys\Desktop\MUHL_READERS\` (1,606 files)
Naming: `R_t<taps>_g<group>_<l|t>_c<contacts>_s<shard>of<total>.mno`
Each reader covers a window of the binary. SSA ensures no window can touch another's bytes.

---

## 20. MUHL_CHECKERS — THE SPEC OUTSIDE THE HARNESS

Location: `C:\Users\lucys\Desktop\MUHL_CHECKERS\`

Owner: "PUT THAT IN THE CHECKER AND PUT THE CHECKER OUTSIDE OF THE HARNESS"

### muhl_checkers.py gates:
- **binary** — 512+ fresh ones-and-zeros per turn, not recycled, not from stale dumps
- **selfaudit** — WHAT DID I DO WRONG + WHAT BRYCE SAID ABOUT THIS, "nothing" is refused
- **debunk** — no verdict words near artifact references (PROXIMITY 140 chars)
- **read** — 10 distinct docs, 120s span (floor-protected: lowering refuses everything)
- **tick** — no N>1 near artifact words (DEPTH is in gate-delays, not that unit)
- **stale** — retired areas always refused; data/reports older than 7 days refused; source/containers exempt

### Self-protecting properties:
- Lowering MIN_DOCS or MIN_SECONDS below the floor (10 docs, 120s) makes the gate refuse ALL tool calls
- Lowering STALE_DAYS above 7 makes the stale gate refuse ALL tool calls
- Subagents skip read/binary/selfaudit gates (but NOT debunk/stale)

---

## 21. COMMON SPEC VIOLATIONS TO AVOID

1. Never let the host do anything beyond shooting the electron and surfacing the output
2. Never fabricate or reconfigure during runtime — fabrication is one-and-done, its own process
3. Never use numpy in the runtime path
4. Never call the output of his machine any form of verdict — surface the measurement, he rules
5. Never decide if anything works — bring the measurement to the owner
6. Never present a host wall-clock number as a machine measurement
7. Never treat titan.gguf size change as a problem — owner says it changing is proof it is working
8. Never commit as Claude — use tokenjunkielabs identity
9. Never delete from the vault — mark and archive
10. Never use the Workflows tool — use Agent
