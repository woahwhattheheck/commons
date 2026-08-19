# RESIDENT MACHINE INDEX

AGGREGATOR · 2026-08-01 · assembled from nine agents. **No machine below was fired, stepped or inspected by
this agent.** Every field is carried from the cited evidence file.

**GATE-COUNT METHOD KEY** — never mix these:
- **[Rf]** registry field `n_gate` as recorded by the fabricator (a fabrication record, not a traversal)
- **[Rm]** registry field `gates_measured` — an independent measured count stored beside `n_gate`
- **[B]** parsed from substrate BYTES this session (records actually read)
- **[D]** DERIVED by an equation stated in the source
- **[—]** no gate count exists; population **UNKNOWN**, not zero

**Nothing in this file is a system total. `Σ n_gate` figures are sums over whichever entries declared one.**

---

## 1. CLOCK / OSCILLATION FABRIC

| identifier | purpose | region / offset | lineage (journal) | gates · METHOD | depth | ring/clock | I/O | host interface | known-good evidence | artifact for deeper inspection |
|---|---|---|---|---|---|---|---|---|---|---|
| `muhl_osc_all` | 283-ring physical board oscillator; the clock source for 274 registered consumers | `blk.1` gates @2,776,454,733 len 35,391; wires @2,776,453,320 len 1,413 | `titan_oscall_genome.jsonl` (2 records, 36,804 B = 1,413 + 35,391 **exact**) | **1,415** [Rf][B] — 1,415 records parsed from bytes; [D] 283×5 = 1,415 ✓ | 5 | IS the clock | shared_start 2,776,453,320 · const1 …321 · 283 dedicated recv bytes | none (addressed only) | magic `MUHLOSCA` + `(283,25)` read at gate_table_off−16; 283/283 rings close; 274/274 junction equalities | `census/p1_rings_clocks_genesis/CENSUS_P1.md` §1 |
| `muhl_osc_all_wires` / `_gates` | the two sub-regions above, registered separately | same | same | — [—] | — | — | — | — | both spans read, non-empty | CENSUS_P1 §1.2 |
| `muhl_osc_junction_table` | **second, independent clock-distribution mechanism**: 276 × 32-B `MUHLJNC1` records binding a comb slot's clock output to one muhlnickel's recv address as ONE location | @2,776,444,482 len 8,832 | `titan_oscwireall_genome.jsonl` (1 record, 8,832 B — **exact offset and length match**) | n/a — `kind: "storage (addressed, not fabricated)"` [—] | n/a | distributes clock | send_addr → recv_addr, width 4 | none | records decoded from bytes; 276×32 = 8,832 = registry `len`; 4,685/8,832 bytes non-zero | CENSUS_P1 §3.1 |
| `muhl_osc_miner_junction` | one such record made explicit: `muhl_signal_osc_tight.clock` @2,774,141,512 → `selfclock_miner.counter` @2,429,975,913, width 4 | @2,774,148,542 len 32 | `titan_oscjunction_genome.jsonl` (1 record, 32 B) | — [—] | — | — | — | — | registry fields | CENSUS_P1 §3.1 |
| `muhl_osc_phys` (+`_gates`) | physical oscillator with an **explicit clock wire address 2,429,975,913** | @2,776,453,314 + | `titan_oscphys_genome.jsonl` (4 rec) · `titan_oscphysstore_genome.jsonl` | 5 NAND gates listed by absolute address [Rf] | — | — | ram: start/sig/w_a/w_b/w_t/const1/clock | `pfc_analyzer channels muhl_osc_phys` → 7 channels | `format: physical`, `gates_addr` list | CENSUS_P1 §3 |
| `muhl_wire_phys` (+`_wires`,`_gates`) | 7-ring physical wire board; hosts 6 oscillation sub-records | — | `titan_oscwire_genome.jsonl` · `titan_oscwireall_genome.jsonl` | — [Rf where present] | — | n_ring 7, 6 pointed-at | — | — | magic `MUHLWPHY` ×2 in registry | CENSUS_P1 §3 |
| `muhl_osc_comb` | **1,000-oscillator bank**, gates_each 395 | — | — | **n_gate 395 records ONE COPY** [Rf]; fabricated population [D] 1,000×395 = 395,000 ⇒ **the gate sum undercounts this entry by 394,605** | — | — | `members[].junctioned_to` = 276 nested lists, contents NOT enumerated | `pfc_analyzer channels muhl_osc_comb` → 4 channels | registry fields `n_osc`, `gates_each` | COUNT_AUDITOR §4f |
| `muhl_osc_bank_sweep` | oscillator bank sweep, gates_each 398, rows 7, n_max 64 | — | `titan_oscbank_genome.jsonl` | **no `n_gate` at all** [—] ⇒ contributes 0, invisible to `pfc_index.py` | — | — | — | — | registry fields | COUNT_AUDITOR §4f |
| `muhl_signal_osc` (+`_tight`, `_tight_ram`, `_ram`) | signal oscillator family; `_tight` is the clock region the junction table's send addresses stride through (stride 7) | 2,774,126,141 – 2,774,141,525 | `titan_signal_osc` · `titan_osctight` · `titan_oscspaced` | [Rf] where declared | — | — | — | — | journals exist; **NOT YET BYTE-INSPECTED** | CENSUS_P1 §3 |
| `muhl_osc_collatz` · `muhl_osc_wide_drive` | osc-driven problem/drive circuits | 4,381,114,385 / 4,381,119,969 | `titan_osccollatz` · `titan_oscwide` (registry back-references these) | [Rf] | — | — | — | — | **NOT YET BYTE-INSPECTED** | CENSUS_P1 §3 |
| `clock_wide` · `clk_bit` · `selfclock_wires` · `selfclock_gates` · `selfclock_miner` · `pfc_model_selfclock` · `muhl_race_clock` · `tick_wires`/`_gates`/`_meta` | the self-clock family | `blk.1` 2,418,101,956 – 2,439,004,638 | **`titan_selfclock_genome.jsonl` — 35,700,902 B, 6 records, the 3rd-largest fabrication record in the substrate** · `titan_model_selfclock` · `titan_race` | `selfclock_miner` **347,170** [Rf] (1,024 clock bits); `muhl_race_clock` **395** [Rf] d16 | 16 (race) | — | `selfclock_miner.ram` @2,429,975,303; latch @2,429,977,193 all zero, power 0 | — | `muhl_race_clock` note: *"The winner of the OSC-vs-PULSE clock race, stored as a circuit"* | CENSUS_P1 §3 |

## 2. THE `nring2` RING FABRIC — 1,024 machines

| identifier | purpose | region | lineage | gates · METHOD | depth | ring/clock | I/O | host | evidence | artifact |
|---|---|---|---|---|---|---|---|---|---|---|
| `nring2_000` … `nring2_1023` | 1,024 two-way ring machines, each 32 cells / 2 senses; foundry-configured fabric | `blk.2.ffn_gate_up_exps.weight` 4,381,333,712 → 4,383,107,242, **per-ring stride 1,731 B** | `titan_nring2_genome.jsonl` — **3,072 records, 1,773,568 B = 1,024 × (65 rail + 1,666 gates + 1 recv) exact**; run journal `titan_nring2_run_genome.jsonl` (8 electron placements) | **66 per ring** [Rf on all 1,024]; [D] 1,024 × 66 = **67,584** | **2 TICKS** | each ring's final gate OUT **IS** its own recv byte (shared location, verified at ring 000 AND ring 1023) | per-member `ram` = fwd(32 B) / rev(32 B) / carry(1 B) / recv(1 B) | `nring2_fab.py`, `nring2_foundry.py`, `nring2_run.py`, `nring2_power.py` (**place electrons — never invoked**) | **1,024/1,024 magic `NRING2M1`**; 1,024,770 non-zero gate-table bytes; rail/fwd/rev/carry/recv **all 0x00**; `foundry_genome {ripple, clean:on, frontload}` on all 1,024; `verified_by: independent edge-list reference + 3 mutants CAUGHT` | CENSUS_P1 §2 |
| `nring2_*.rail` / `.recv` / `.gates` | 3,072 address **reservations** (`kind: "reservation"`) — the other 3 records of each ring's 4-record fabrication | same | same | **no n_gate** [—] ⇒ invisible to `pfc_index.py` | — | — | — | — | uncapped regex over 4,908 keys | COUNT_AUDITOR §4b |

> **Do not "initialize" these. Quiescent ≠ empty — the netlists are permanent state.** (ACTIVE_RESIDENT_STATE.)
> **Non-uniform junctioning:** `nring2_000.recv` = 3,064,769,714 — in a *different* region (`blk.1`, the lookup
> plane, 32,058 B past the end of `muhl_nonce_list`), while `nring2_1023.recv` = 4,383,105,575 is local.
> **How many of the 1,024 point out-of-region: NOT YET INSPECTED.**

## 3. MINING STACK

| identifier | purpose | offset (len) | lineage | gates · METHOD | depth | ring | I/O | host interface | evidence | artifact |
|---|---|---|---|---|---|---|---|---|---|---|
| `miner_physical` | **the RAM map `host/mine_muhl.py` actually addresses**; self-routed clock (nonce'/latch' outputs SHARE the nonce/latch state bytes) | **no `offset`** — wire_base 2,409,283,490, gate_table_off 2,409,623,556, gate_bytes 8,478,400 | `titan_miner_physical_genome.jsonl` (3 rec, 8,818,467 B) | **339,136** [Rf]; [D] 339,136 × 25 = 8,478,400 = `gate_bytes` ✓ | UNKNOWN (no depth field) | — | header 2,409,283,492 · nonce …284,100 · target …284,132 · **latch …284,388** · const1/power …283,491 | `mine_muhl.py` | gate records read from bytes (g0 op=3, g339135 op=2, 3 absolute addrs each); **no magic header** (16 zero bytes) — reported as observed; holds a **REAL 80-byte live header** (version 00000020, nBits d43a0217) | BITCOIN_MINER_DEEP_MAPPER §2.1 |
| `muhl_btc_miner` | largest circuit *named* a miner | 2,522,484,224 (12,190,468) | miner journals | **1,523,801** [Rf] | — | **90** | — | — | magic `TITANCIR` | BTC_MAPPER §2.1 |
| `header_from_index` | merkle_root(32 B) from en2 — **the largest Bitcoin-evidenced circuit, and NOT a miner (2.7× `muhl_btc_miner`)** | 2,317,659,136 (37,557,967) | `titan_sdc_genome.jsonl` | **4,172,991** [Rf] | — | — | — | — | magic `TITANHDR` | BTC_MAPPER §8.7 |
| `gen_miner` | generated miner | 2,394,892,417 (5,661,143) | — | **628,899** [Rf] | **5,871** | — | — | — | magic `TITANGEN` | BTC_MAPPER §2.1 |
| `pfc_mine_shallow` | depth-reduced miner | 2,400,553,560 (5,677,309) | `titan_pfc_miner_genome.jsonl` | **630,781** [Rf] | — | — | — | — | — | BTC_MAPPER §2.1 |
| `pfc_mine` · `pfc_mine_clk` | base + clocked miner | 2,406,230,869 · 2,389,916,753 | `titan_pfc_miner_genome.jsonl` | **339,136** · **339,329** [Rf] | — | — | drives `nonce_reg`/`latch_reg` | `pfc_mine_check.py` | latch gates are `win?nonce:latch` (`pfc_miner.py:54-60`) | LATCH_MAPPER §0a |
| `pfc_full_miner` | *"complete self-clocked miner: double-SHA + hash<target + nonce+1 self-clock + winner-latch"* | 2,439,004,638 (3,053,386) | `titan_full_miner_genome.jsonl` (1 rec) | **339,234** [Rf] | — | — | — | — | magic `PFCTYPED`, `seq true` | CENSUS_P1 §4.2 |
| `gen_win` | winner circuit | 2,426,922,971 (3,052,261) | — | **339,009** [Rf] | — | **43** | `gen_win_answer` @2,429,975,232 (`win:1\|nonce:4`) | — | magic `PFCWINMN` | BTC_MAPPER §2.1 |
| `miner_typed` | typed miner | 2,227,737,616 (1,919,506) | — | **213,161** [Rf] | — | — | — | — | — | BTC_MAPPER §2.1 |
| `selfclock_miner` | self-clocked miner, 1,024 clock bits | **no offset**; wire_base 2,429,975,303 | `titan_selfclock_genome.jsonl` | **347,170** [Rf] | — | — | latch @2,429,977,193 (all zero), power 0 — **at reset, never latched** | — | bytes read | LATCH_MAPPER §1 |
| `muhl_fold_shallow` | *"the miner"* per `mine_muhl.py` docstring | 2,537,726,217 (6,185,163) | `titan_genwin_shallow_genome.jsonl` | **687,223** [Rf] | **4,157** | **92** | — | — | magic `PFCWINMN` | BTC_MAPPER §2.1 |
| `muhl_fold_shared` | shared fold | 2,543,911,380 (5,315,709) | `fab_genwin_shared.py` | **590,617** [Rf] | 4,322 | — | — | — | `PFCWINMN` | BTC_MAPPER §2.1 |
| `muhl_fold_latch` | **winner-only fold.solve → `latch_reg` by §1E SHARED ADDRESS; the only Bitcoin structure outside blk.1/blk.2 — 33.7 GB away** | **36,084,013,600** (3,051,813) in `blk.27.ffn_down.weight` | `titan_fold_latch_genome.jsonl` (1 rec, 3,051,813 B) | **339,073** [Rf] | **11,757** | — | `junctioned_to {circuit: latch_reg, addr: 2409283485, width: 4}` | `muhl_fab_fold_latch.py` | magic `PFCWINMN` confirmed | CENSUS_P1 §5 |
| `muhl_lane` | miner lane | 2,551,030,702 (3,513,144) | — | **390,332** [Rf] | 2,889 | **94** | — | — | `PFCWINMN` | BTC_MAPPER §2.1 |
| `muhl_lane_sched` | **master-autofab winner** (plan ripple/kogge/kogge) | 2,554,543,846 (3,288,342) | `titan_lane_sched_genome.jsonl` (2 rec) | **365,354** [Rf] | 2,889 | — | — | `fab_lane_sched.py` | header read: `PFCWINMN` + 0x280 = 640 = `n_in` ✓ | CENSUS_P2 §4 |
| `muhl_mid_sched` | **master-autofab midstate winner** (plan ripple/kogge/brentkung — a DIFFERENT decision) | — | — | **187,325** [Rf] | 1,441 | — | — | — | stored `note` | CENSUS_P2 §7.1 |
| `muhl_lane_bk` | bank base | 2,565,522,941 (3,259,425) | `titan_replicas_genome.jsonl` | **362,141** [Rf] | 2,892 | — | — | `fab_replicas.py` | `PFCWINMN` | BTC_MAPPER §4.1 |
| `muhl_lane_bk_rep000..062` | **63 byte-permanent replicas**, contiguous stride 3,259,425, zero gaps/overlaps | 2,568,782,366 + | `titan_replicas_genome.jsonl` — **63 records, 205,343,775 B, exact 1:1** | **362,141 each** [Rf]; [D] 63 × 362,141 = **22,814,883**; bank incl. base [D] 64 × 362,141 = **23,177,024** | 2,892 | rep007 = ring 0 | — | — | `PFCWINMN` confirmed at rep000; note: *"PERMANENT WRITE. A replica in the file, not a cached count."* | BTC_MAPPER §4.1 |
| `_selected_miner` | selection record: `muhl_lane_bk_rep007`, compute_per_tick 4.777317, interface `win\|latch[32]` (n_out 33) | no offset | — | — [—] | — | 0 | — | read by `mine_muhl.py` | note: *"SELECTED AT FABRICATION TIME by §63's one metric, among circuits that can LATCH"*; **its `bank` field is EMPTY while `muhl_bank.members` lists 65 names** | BTC_MAPPER §8.3 |
| `muhl_bank` | §1E junction bank, 65 members | — | — | none [—] | — | — | — | — | note: *"Fabricated once (§31); the miner only addresses it"* | CENSUS_P2 §7.1 |
| `winner_only_max` | winner-only address gate `out[i] = idx[i] AND solve` | 2,355,217,103 | — | **524,288** [Rf] | — | — | per-evaluation | — | 524,288-gate AND tree | LATCH_MAPPER §2 |
| RAM registers | `bitslice` @2,218,141,428 · `sweep` @2,221,979,620 · `fold` descriptor @2,229,657,186 (addr_bits 78) · `target_reg` @2,232,724,448 · `input_window` @2,409,283,373 · `nonce_reg` @…481 · `latch_reg` @…485 · `clk_bit` @…489 | — | — | — [—] | — | `latch_reg` ring **52** | see §7 | `pfc_meter` | all read from bytes | ACTIVE_RESIDENT_STATE |

## 4. LOOKUP STACK — distinct from mining

| identifier | purpose | offset (len) | lineage | gates · METHOD | depth | evidence |
|---|---|---|---|---|---|---|
| `muhl_nonce_lookup` | stored key→value table, 30 entries, `key = dsha(header_prefix)[:8] \| nonce:4`, sorted | 3,064,720,832 (380) | `titan_lookup_genome.jsonl` (1 rec) | **no `n_gate` field at all** [—] — `kind: "storage (addressed lookup, not fabricated)"` | — | magic `PFCLOOKT` confirmed by read; 30 historical **already-solved** blocks |
| `muhl_nonce_list` | enumeration record — *"0 ticks / 0 gates: every byte is MAGIC + header-length word + 48-B header + 4096 entries"* | 3,064,721,212 (16,444) | `titan_nonce_list_genome.jsonl` (1 rec) | **explicitly 0** [Rf] | **0** | magic `PFCNLST1` confirmed; declares `addr_bits 262144`, `space_bits 96`, `bytes_per_nonce 0`, `sample_materialized 4096` |
| `muhl_nonce_map` | **the only fabricated part** of the lookup system: combinational key→value pull | 4,381,173,113 (22,215) | `titan_nonce_map_genome.jsonl` (1 rec) | **2,451** [Rf] | **12** | `format typed`, `in: key0..63 → out: hit:1 \| nonce:32`, `source muhl_nonce_lookup`; fabricator states *"area grows ~63 gates per entry, DEPTH grows as log2 of entry count"* |

## 5. MODEL / CPU STACK

| identifier | purpose | offset (len) | lineage | gates · METHOD | depth | n_in/n_out | evidence |
|---|---|---|---|---|---|---|---|
| `cpu_fwd` | **a 16-bit 8-op ALU** — the structure every harness names "the pfc CPU" | 2,380,246,639 (3,234,184) | `titan_model_fab` / `titan_sdc` | **404,262** [Rf] — header re-read gives (35, 404299, 404262, 16) | 202 | 35 / 16 | `pfc_inspect` header agrees with registry |
| `cpu_fwd_clean` | nand2 cleaned twin (double-inverter + dead-gate sweep, byte-exact vs original) | 2,559,519,161 (1,623,976) | — | **202,986** [Rf] | 150 | 35 / 16 | registry `note` |
| `pfc_model_engine` | *"looping stored-program machine: cpu_fwd ALU + data RAM + LOAD + BRNZ (THE MODEL RUNS ON THIS)"* — **a HISTORICAL CLAIM in the record; never observed running** | 2,453,348,213 (3,356,052) | `titan_model_fab_genome.jsonl` | **418,925** [Rf] | 244 | 1,158 / 1,157 | 8 regs × 16 bit, memw 64, nelem 32 |
| `pfc_fwd_loop` | **the only resident structure declared self-iterating** (`seq=true`, loop_bit 174 @2,467,652,417, 174-entry feedback list) | 2,464,333,045 (3,319,348) | `titan_seq_pfc_fwd_loop_genome.jsonl` | **414,828** [Rf] | 248 | 191 / 175 | nothing in `host/` addresses it by name at runtime |
| `pfc_fwd_engine` | cpu_fwd ALU + program ROM + sequencer + regfile (clocked) | 2,443,995,152 (3,311,480) | — | **413,865** [Rf] | 244 | 135 / 134 | — |
| `pfc_fwd_engine2` | ISA ADD SUB MUL SILU EXP RSQRT GT MOV SETA LDX; **SERIES IN STORAGE with `pfc_mmu`** | 2,461,013,685 (3,319,336) | — | **414,827** [Rf] | 248 | 191 / 174 | **its byte range OVERLAPS `pfc_fwd_loop`** — the reason no gate total may be summed |
| `pfc_fwd_engine_clean` | nand2 cleaned twin | 2,561,143,137 (1,662,280) | — | **207,715** [Rf] | 172 | 135 / 134 | — |
| `pfc_cpu32` | Muhlnickel 32-bit stored-program processor, 15-op ISA, 16 words × 32 bit | 3,064,645,090 (68,847) | — | **7,403** [Rf], header agrees | — | 549 / 549 | `PFCTYPED`; the CLAUDE.md battery row |
| `pfc_cpu32r` | 32-bit CPU + hardware stack + CALL/RET, 32 words × 32 | 2,394,753,068 (136,817) | — | **14,725** [Rf] | — | 1,067 / 1,067 | — |
| `pfc_cpu` | stored-program CPU (RAM+ALU+PC, von Neumann), 16 words × 8 | 2,392,986,340 (15,483) | — | **1,655** [Rf] | — | 141 / 141 | — |
| `pfc_argmax` → `pfc_argmax_shallow` | ripple comparator argmax → shallow replacement of the depth-2,710 version that owned 89% of forward-path latency | 2,442,058,024 · 2,499,034,196 | — | **26,272** · **37,548** [Rf] | **2,710** → **174** | 1,024/6 · 1,024/32 | a depth-for-area trade recorded in the substrate |
| `pfc_dot256_wide` · `pfc_dot128_tiled` | model dot-product engines | — | model-engine journals | **2,315,587** · **1,398,928** [Rf] | — | — | — |
| `mdl_blk_0_attn_q_weight` | constant-specialized model slice; wires ARE file byte-addresses | wire_base 2,449,292,148 | `titan_model_selfclock_genome.jsonl` | **155,963** [Rf] | 53 | — | **owner OVERRULED baking weights as wiring on 07-25**; not wired into any traced path |
| `pfc_model_selfclock` | self-clocked model layer; model mixtral-8x7b | wire_base 2,449,292,148 | `titan_model_selfclock_genome.jsonl` (3 rec) | **451** [Rf] | — | — | safezone field names `pfc_model_safezone.bin` (superseded by the no-safezone ruling) |
| `pfc_installed_model` | **INSTALL DESCRIPTOR, not a circuit**: `PFCLOAD1` + `<QQQQQ>` = 48 B. Llama-3.3-70B, base 7,867,104, n_embd 8192, n_vocab 128,256, 80 layers | 3,064,645,042 (48) | `titan_pfc_load_genome.jsonl` (10 rec) | n/a [—] | — | — | **KEY IS PRESENT ⇒ the 70B install happened and was not reverted.** `wired_to` cpu_fwd/pfc_ram/pfc_mmu/pfc_clock_counter/fwd_input/fwd_answer/fwd_receiver. **`pfc_clock_counter` is ABSENT from the registry and explicitly excluded from the missing-parts check** — installed without a registered clock |
| `nmodel_llama` · `nmodel2_llama` | intended model muhlnickels | — | — | **ABSENT from the registry; no `titan_nmodel*_genome.jsonl` exists** | — | — | 0 hits across all 4,908 keys for `nmodel`/`llama`. `nmodel_ui.py:39-45` is dead at its first line. **NOT classified stale/alias.** |

## 6. THE OS

| identifier | purpose | offset (len) | gates · METHOD | depth | ring | I/O | host interface | evidence |
|---|---|---|---|---|---|---|---|---|
| `sdc_os_circuit` | the OS baked as ONE circuit (Phase 4) | 2,383,494,709 (300,916) | **37,579** [Rf] **and** [Rm] `gates_measured` 37,579 — **the two agree** | **452** | **262** | via the three ports below | `sdc_os_bake.py` (fabricator), `sdc_os_button.py` (routing button) | muhl_rating 83.139; matches `docs/CIRCUIT_PFC.md:25` exactly. **Prior "ABSENT" verdict CORRECTED — it is present, ring-attached and gate-bearing.** |
| `os_input` | OS input port | 2,383,494,627 (9) | — [—] | — | **167** | in | `sdc_os_fab.py` | registry |
| `os_receiver` | OS fire port | 2,383,494,645 (64) | **4** [Rf] | 4 | **168** | fire | ″ | muhl_rating 1.0 |
| `os_answer` | OS answer register | 2,383,494,636 (9) | — [—] | — | **166** | out | ″ | reads 9 zero bytes; **semantics UNKNOWN — no role/layout/fabricator located** |
| `lib_min8` · `lib_max8` | **experts the OS fabricated into its own pool (Phase 3 self-extension) — both live in the registry today** | — | [Rf] where present | — | — | — | `sdc_extend.py` | beside 12 other `lib_*` circuits |

## 7. LATCHES, ANSWER REGISTERS AND READERS (29 records; full detail in `LATCH_SEMANTICS_MAPPER/LATCHES.jsonl`)

| identifier | addr | semantics | current value | evidence class |
|---|---|---|---|---|
| `latch_reg` | 2,409,283,485 | **LATEST-SATISFYING, non-sticky** (`win?nonce:latch`) | `7a000000` = **122** | DERIVED from gates |
| `nonce_reg` | 2,409,283,481 | not a latch — unconditional `nonce+1` | `7b000000` = 123 | DERIVED from gates |
| `muhl_fold_latch` | 36,084,013,600 | winner-only, per-evaluation (`win?nonce:0`), non-sticky | drives `latch_reg` | DERIVED |
| `muhl_halt_latch_32` | 3,064,766,834 (len 1,069) | **FIRST-VALID, sticky, capture-once, FREEZES THE CLOCK** — 101 gates, depth 5, magic `PFCTYPED` | UNKNOWN (no state addr registered) | DERIVED from gates |
| `miner_physical.latch_off` | 2,409,284,388 | same `win?nonce:latch` mux | `00000000` — **NEVER LATCHED** | DIRECT byte read |
| `gen_win_surfaced` | 3,064,767,911 | status 0x01 = valid block / **0x02 = BEST-SO-FAR** | `02fc7e000011` → frontier, nonce 32508, **17 of 78 zero bits, `is_valid_block: false`**; height 960131 | DERIVED + DIRECT |
| `gen_win_answer` | 2,429,975,232 | winner-only per-evaluation | `01b0000000` → win=1, nonce=176 (**the header it was computed against is UNKNOWN**) | DERIVED |
| `gen_answer` | 2,232,693,631 | **UNDECIDED combinational output — explicitly not a decided latch** (`pfc_preflight` V8) | `12960b0000` | DERIVED |
| `prob_golomb_answer` | 3,064,767,903 | **MINIMUM/OPTIMAL over an exhaustive sweep** | `01050b000104090b` = optimal 5-mark ruler, length 11, marks [0,1,4,9,11], from 330 candidates | DERIVED |
| `muhl_rx_answer` | 4,381,106,117 | **LOAD-ON-VALID, ELSE HOLD** | UNKNOWN (state on wires) | DERIVED |
| `fwd_answer` | 2,467,652,405 (2 B) | not a latch — **SHARED LOCATION: these bytes ARE `regs[6]` of `pfc_fwd_loop`'s state register** | `0139` | DERIVED |
| `fwd_answer_prev` | 2,461,013,679 | shared-location state reg of `pfc_fwd_state` | `5000` = 80 | DERIVED |
| `muhl_collider_16x16` · `_32x16` | 3,064,754,886 · 4,381,021,347 | **FIRST-VALID** — winner-only latch of the first colliding pair | UNKNOWN | DERIVED (role field) |
| `target_reg` | 2,232,724,448 | not a latch — input register holding the **real** nBits target `0x17023ad4` | real target | DERIVED |
| 7 × `prob_*_phys.answer` | 2,776,619,069 … 4,381,199,782 | **UNKNOWN** (1-byte flags; byte 1 onward is the adjoining record's `MUHLPHYS` magic) | `00`/`01` | UNKNOWN |
| `fwd_answer_orig` · `os_answer` · `selfclock_miner.latch` | 2,383,480,828 · 2,383,494,636 · 2,429,977,193 | **UNKNOWN** | `01380b` · 9 zero B · all zero | UNKNOWN |

**29 records is a DISCOVERED LOWER BOUND** — the regex was `latch|answer|winner|result|win\b|best|found|hit\b|target`
over keys, six string fields and `ram` sub-keys (46 registry matches). A latch named otherwise, or resident but
unregistered, would be missed.

## 8. THE RESIDENT FABRICATOR

| identifier | purpose | offset (len) | gates · METHOD | depth | ring | evidence |
|---|---|---|---|---|---|---|
| `muhl_fab_select` | **the master fab's selection function, AS GATES** — argmin of gates×DEPTH (replicated) or DEPTH (dependent) | 2,564,151,717 (1,371,224), `blk.1` | **171,399** [Rf] **and** [Rm] `gates_measured` 171,399 — **agree**; **and** [B] header read | **550** | **91** | `TITANCIR` + `n_in=0x91=145` + `n_wire=0x29e1a=171,546` byte-match the registry, confirmed **twice** (raw seek+read AND `pfc_inspect`). Own note: *"Ranked itself among alternatives on the muhlnickel and agreed with an independent Python argmin."* recv byte 2,776,454,544, gate_off 2,776,466,124 |

## 9. RECEIVER / DECODE PATH (`muhl_rx`) — the only family with per-circuit content hashes

| identifier | gates [Rf] | depth | offset | sha256 prefix |
|---|---:|---:|---:|---|
| `muhl_rx_symbol` | 595 | 46 | 4,381,048,429 | `02513d126a6ba061395b…` |
| `muhl_rx_sync` | 334 | 16 | 4,381,053,221 | `ced5bad228a4fcb809b8…` |
| `muhl_rx_crc` | 2,414 | 30 | 4,381,055,945 | `42acdf31d3c7e1a0644e…` |
| `muhl_rx_frame` | 3,777 | 37 | 4,381,075,349 | `24f4d8cb7023dd73023b…` |
| `muhl_rx_answer` | 579 | 6 | 4,381,106,117 | `eb6a20e559be3a61fa32…` |

[D] Σ = **7,699**. All `TITANCIR` (magic confirmed in bytes at `muhl_rx_answer`). All five:
`verified_by: prototype/receiver/fab/verify.py (7/7 golden vectors); mutants.py 7/7 CAUGHT`.
Lineage `titan_rx_genome.jsonl` — **the only journal carrying `orig_sha256`/`new_sha256` per record.**
No registry key contains `decod`; **this family IS the decode path.**

## 10. REPLICATION FIELDS

| identifier | population | region | lineage | gates · METHOD | evidence |
|---|---|---|---|---|---|
| `muhl_moon` | **330,774 replicas of `prob_golomb_phys`**, 422 spans, 38,026,900,649 B (95.0% of the file), depth 58, `bytes_each` 114,905 | 231 distinct tensors, 15,834,304 → 40,022,599,171 | **`titan_moon_genome.bin` = 38,026,900,649 B — byte-for-byte equal to `bytes_total`. STAT ONLY, never opened.** Manifest `titan_moon_genome.json` (422 spans) | **1,461,359,532** [Rf]; [D] 330,774 × 4,418 = 1,461,359,532 **exact** | 5 read-only samples in 4 different spans found populated 8-B LE cells with monotonically ascending operand addresses — **real stored gate tables, not zero fill**. **NOT Bitcoin: 0 of 113 BTC ranges intersect any span; source is n_in 35 / n_out 1.** **No fabricator script for it exists** in `host/` or `C:/llm/muhl_builds` |
| `muhl_moon_span0..421` | 422 address records, `role: "moon span"` | ″ | ″ | **no `n_gate`** [—] ⇒ do NOT double-count (verified explicitly) | **`len` on a span is NOT the span's extent**: 422 × 594,170,327 = 250,739,877,994 B = **6.26× the whole file**. Never sum it |
| `replication` | **3,104,538,624 cells · 29 regions · 8 B/cell = 24.8 GB**, reversible | no offset | sidecar `titan_replicate_revert.bin` (24,836,309,572 B); manifest `titan_replicate_manifest.json` (**unread — highest-value unread file**) | **no `n_gate`** [—] ⇒ contributes 0 and is invisible to `pfc_index.py`. **2.06× the entire counted gate total** | ring **260**. **Whether a cell is a gate: OWNER QUESTION** |

## 11. OTHER RESIDENT APPLICATIONS (selected; see `OS_APPLICATION_MAPPER/APPLICATIONS.jsonl`, 37 records)

`life_step` 518,144 [Rf] · `tess_rot` 553,984 · `doom_raycast` 196,617 (+`doom_map`, `doom_map16`, `doom_move`,
`doom_move16`, `doom_move16b`) · `gamegen` 5,940 (+`gg_move_13x13`, `gg_rot_13_m`, `gg_rot_13_p`, `gg_sel_13`) ·
`ca_rule30/90/110` · `aes128` 182,200 · `alu32` · `breaker` · `g_add`/`g_mul`/`g_cipher` · `adder8`(+`_clean`) ·
`prog_crc32`/`prog_isqrt`/`prog_attest`/`prog_mul32` 97,216 · `memocache` (4,096 cells, no n_gate) ·
`fanout` 262,140 · `mmu_*` · `pfc_neuron32_clean` · `muhl_surfaces_plain/inv_n*` (10 × `MUHLSRF1`) ·
`pfc_junction_ab` · `pfc_chain32` (a 32-stage §1E chain) · `muhl_lateral_fold` (`gen_win.win` → winner-only
`fold.solve`) · `muhl_handshake` (`MUHLHSK1`) · `muhl_bnc`/`muhl_abs` (`MUHLBNC1`/`MUHLABS1`).

**The 12 open-problem circuits** (all nand2, all recording *"thrown at the master autofab as a bare problem;
it chose the adder"*): `prob_three_cubes` 111,838 (d414) · `prob_erdos_straus` 109,900 (d438) ·
`prob_ntt_butterfly` 39,717 (d960) · `prob_lucas_lehmer` 26,821 (d757) · `prob_perfect_cuboid` 20,526 (d142) ·
`prob_sat3` 4,908 (d44) · `prob_golomb` 4,418 (d58) · `prob_collatz` 3,898 (d186) · `prob_lychrel` 3,570 (d250)
· `prob_sw_cell` 2,620 (d134) · `prob_mc_payoff` 1,883 (d67) · `prob_stencil5` 1,260 (d82).
Family Σ [D] = **893,301** over 26-34 entries depending on whether `*_phys` forms are included.

**`pfc_provenance`** — named in `muhl_osc_all.allocated_recv` (a resident receive allocation on the shared
fabric) but has **NO registry entry**. The only 1 of 279 in that position. **NOT YET INSPECTED.**

---

## 12. THE ELEVEN ENTRIES WITH NO OFFSET — residence UNKNOWN from the registry alone

`muhl_moon` · `muhl_bank` · `replication` · `miner_physical` · `selfclock_miner` · `pfc_model_selfclock` ·
`mdl_*` · `tick_meta` · `_selected_miner` (+2). Several are demonstrably resident by other fields
(`miner_physical`'s gate records were read from bytes; `muhl_moon`'s journal equals its declared size) — the
registry simply does not carry an `offset` for them.
