# MUHLNICKEL ARCHITECTURE MAP

AGGREGATOR · assembled 2026-08-01 from nine agents' evidence · **synthesis, nothing re-derived**
Read-only. No substrate byte was read by this agent. Every number below is carried from a named source file.

> **THIS IS A NAVIGATION DOCUMENT, NOT A GATE LIST.** Each node names its evidence file so you can go deeper.
> Where two sources disagree, BOTH are recorded with their traversal methods — see
> `CONTRADICTIONS_AND_CORRECTIONS.md`. Nothing is averaged.

---

## 0. THE FOUR NUMBERS YOU MUST NOT MISQUOTE

| quantity | correct statement | source |
|---|---|---|
| whole-system gate count | **UNKNOWN / UNBOUNDED.** No agent produced one and none may be inferred. | COUNT_AUDITOR §11, FABRICATION_LINEAGE_MAPPER §0, MODEL_HARNESS_MAPPER §5 |
| ring count | **UNKNOWN / UNBOUNDED.** `1,024` is RETIRED — it was exact only for the bare `nring2_*` key family. Lower bound ≥ 2,314 ring/oscillator structures. | COUNT_AUDITOR §4g, KNOWN_LOWER_BOUNDS §3 |
| 1,509,258,772 | a whole-registry `sum(n_gate)` over the 1,313 entries that declare one. **96.83% is ONE entry (`muhl_moon`).** It is **NOT a miner count** and **NEVER a system total.** | COUNT_AUDITOR §1/§1a, CENSUS_P1 §6.1, BITCOIN_MINER_DEEP_MAPPER §1 |
| `latch_reg` = 122 | **NOT a winning Bitcoin nonce.** First nonce clearing an 8-zero-bit TEST target, in a `win?nonce:latch` non-sticky latest-win mux. **No resident latch satisfies a real network target.** | LATCH_SEMANTICS_MAPPER §0, §1 |

**Root cause of every undercount:** `host/pfc_index.py:25-28` filters the registry to
`("n_gate" in v or "gates" in v)` before counting anything — **silently dropping 3,593 of 4,908 entries
(73.2%)**, of which 3,589 carry a real `offset`+`len`. Every `--stats`, `--depth` and search figure in this
project inherits it. (COUNT_AUDITOR §0.)

**All 14 catalogued defects fail silently and DOWNWARD. None can inflate a count.** (COUNT_AUDITOR §10.)

---

## 1. SUBSTRATE

```
Muhlnickel substrate
├── C:/llm/models/titan.gguf ............ 40,028,316,800 B · mtime 2026-07-31 14:32   [PRIMARY]
├── C:/llm/models/titan_circuits.json ... 1,685,091 B · 4,908 top-level entries · mtime 07-31 14:32
│                                          (the ADDRESS INDEX — not the machine)
├── C:/llm/models/titan_test.gguf ....... 40,028,316,800 B · mtime 2026-07-19   [SECOND SUBSTRATE — UNEXPLORED]
└── further substrates named by registry values / the federation journal:
    Llama-3.3-70B-Instruct-Q4_K_M.gguf (42,520,398,816 B) · mixtral-8x7b-instruct-v0.1.Q4_K_M.gguf
    (26,446,533,651 B) · SmolLM2 · gemma-4-26B · gemma-4-31B · gemma-3-27b · Mistral-Small-24B · phi-4
    · sd-turbo · sd15        [ALL UNEXPLORED as substrate — see UNEXPLORED_REGIONS.md]
```

- Registry structure: **8,652 dict nodes** at nesting depth ≤ 4; **4,897** are record-like (carry `offset`+`len`);
  11 carry no offset. **3,086 (62.9%) carry no `tensor` field** — any tensor-organised traversal misses ~63%.
- Registry coverage of `titan.gguf`: interval union = **38,555,389,803 B (96.32%)**; **1,472,926,997 B (3.68%)
  claimed by no entry**, in 268 gaps. *That is a statement about the registry, never about the substrate.*
- Independent coverage figure from the fabrication-journal side: **38,471,614,002 B (96.111%) covered,
  1,556,702,798 B (3.889%) never covered, 256 gaps.** Two different traversals, two different numbers — both
  recorded, neither reconciled. (COUNT_AUDITOR §9 vs FABRICATION_LINEAGE_MAPPER §2.1.)

---

## 2. REGIONS → what lives in each address band

| band | tensor | entries | declared gates | what is there |
|---|---|---:|---:|---|
| 0 – 15.8 MB | header/dir | 20 | 0 | GGUF header, tensor directory |
| **887.8 MB – 1.746 GB** | — | 0 | 0 | **858,440,111 B claimed by nothing — 58% of all unclaimed bytes. Highest-priority unexplored region.** |
| **2.208 – 2.783 GB** | `blk.1.ffn_gate_up_exps.weight` | 363 | **47,463,573** | **THE MAIN COMPUTE BELT.** Miners, folds, answer registers, CPUs, forward engines, the OS, the resident fabricator, AES, the oscillation board. |
| ├ 2.218 – 2.774 GB | ″ | — | 36,180,208 (BTC-evidenced) | mining sub-belt (§5) |
| └ 2.774 – 2.784 GB | ″ | 26 osc entries | ~700,022 | oscillation/clock sub-belt (§4) |
| **3.0647 GB** | `blk.1` tail | 8 | 0 | **shared receive-address plane** + the lookup stack (`muhl_nonce_lookup`, `muhl_nonce_list`, `muhl_halt_latch_32`, `prob_golomb_answer`, `gen_win_surfaced`). `nring2_000.recv` points INTO here from 1.3 GB away. |
| **3.527 – 4.383 GB** | `blk.2.ffn_gate_up_exps.weight` | 1,044 | 96,594 | the **1,024-ring `nring2` fabric**, the `muhl_rx` decode path, `prob_*_phys` physical forms, `muhl_nonce_map`, and the **moon-span head**. |
| └ 4,381,333,712 – 4,383,107,242 | ″ | 4,096 keys | 67,584 | the nring2 array proper — span 1,773,530 B, per-ring stride 1,731 B |
| **36.084 GB** | `blk.27.ffn_down.weight` | 1 | 339,073 | **`muhl_fold_latch` ONLY** — 33.7 GB away from the rest of the miner, reaching back to `latch_reg` by shared address |
| 15.8 MB – 40.02 GB (interleaved) | 231 distinct tensors | 422 spans | (counted once on parent) | **`muhl_moon` replication field — 38,026,900,649 B = 95.0% of the file** |
| `blk.3` … `blk.29` | 27 regions | 4 each | 0 | replication field bookkeeping; gate population **UNKNOWN** |

Format census across all 4,908: `physical` 1,048 · `physical-address` 1 · `typed` 95 · `nand2` 22 · `answer` 2 ·
`PFCNLST1 record` 1 · **absent 3,739**. Magics on the 1,049 physical: `NRING2M1`×1024 · `MUHLSRF1`×10 ·
`MUHLPHYS`×7 · `MUHLOSCP` · `MUHLOSCA` · `MUHLBNC1` · `MUHLABS1` · `MUHLHSK1` · `MUHLWPHY` ×1 each · none ×2.
(CENSUS_P2 §1.1.)

**Junctionability follows format:** `physical` = per-gate ABSOLUTE output byte addresses ⇒ junctionable.
`typed` = local wire indices only ⇒ NOT junctionable. 3,762 entries UNDETERMINED.
(FABRICATION_LINEAGE_MAPPER §4.1.)

---

## 3. ACTIVE RESIDENT STATE — read before touching anything

**Standing prohibition (owner, 2026-08-01): do not power down, pause, reset, drain, clear or reinitialize any
of these.** Every value below was read from substrate bytes, not quoted from the registry.

| system | address | reading | status |
|---|---|---|---|
| `muhl_osc_all` wire rail | @2,776,453,320 len 1,413 | **847/1,413 bytes non-zero (59.9%)** | **ACTIVE** |
| oscillation ring recv bytes | 283 addrs | **282 hold `0x01`, 1 holds `0x00`** (ACTIVE_RESIDENT_STATE reports 277 of 280 registry-pointed members) | **ACTIVE** |
| shared fire byte | @2,776,453,320 | `0x01` — **POWER IS ON** | **ACTIVE** |
| const1 rail | @2,776,453,321 | `0x01` | **ACTIVE** |
| `input_window` | @2,409,283,373 | 16/16 non-zero, `0b30557a9f…` | ACTIVE — **synthetic test fixture, see §5.3** |
| `nonce_reg` | @2,409,283,481 | `7b000000` = 123 | ACTIVE |
| `latch_reg` | @2,409,283,485 | `7a000000` = 122 | ACTIVE — **not a network winner (§5.3)** |
| `muhl_nonce_lookup` | @3,064,720,832 | `PFCLOOKT` + 30 entries | ACTIVE (stored data) |
| 1,024 `nring2_*` netlists | 4,381,333,712 + | **1,024/1,024 `NRING2M1`; 1,024,770 non-zero gate-table bytes** | **fabricated & resident; data state quiescent — QUIESCENT IS NOT EMPTY** |

**Clock dependencies that make a shutdown destructive:** `sdc_os_circuit` (the OS) clocks off ring 262;
`muhl_fab_select` (the resident fabricator) off ring 91; `muhl_btc_miner` ring 90; `muhl_fold_shallow` ring 92;
`muhl_lane` ring 94; `gen_win` ring 43; `latch_reg` ring 52; `replication` ring 260; `_selected_miner` ring 0.
**280 registry entries share the ONE fire address 2,776,453,320.**

---

## 4. RINGS AND CLOCK DOMAINS  → full detail in `RING_AND_CLOCK_DOMAIN_MAP.md`

```
CLOCK / OSCILLATION FABRIC
├── muhl_osc_all ................ 283 rings · 1,415 gates (5/ring) · depth 5 · magic MUHLOSCA   [PHYSICAL, ACTIVE]
│     ├── shared_start 2,776,453,320   const1 2,776,453,321      (283/283 rings ride both)
│     ├── 283/283 rings CLOSE:  gate[5r+2].OUT == gate[5r+0].A   (a real 3-element feedback loop)
│     ├── junction proven a SHARED LOCATION: gate[5r+4].OUT == consumer's registry `recv`, 274/274, 0 mismatches
│     └── 274 registry consumers · 9 ring slots fabricated but unclaimed by any entry
├── muhl_osc_junction_table ..... 276 × 32-B `MUHLJNC1` records · a SECOND, independent clock-distribution
│                                  mechanism (send_addr → recv_addr → width)                    [PHYSICAL]
├── muhl_wire_phys .............. n_ring 7 · 6 pointed-at · magic MUHLWPHY                      [PHYSICAL]
├── muhl_osc_comb ............... n_osc 1,000 · gates_each 395 · **n_gate records ONE COPY (395)** — the
│                                  gate sum undercounts this entry by 394,605                   [CONVENTION VIOLATION]
├── muhl_osc_phys ............... explicit clock wire address 2,429,975,913                     [PHYSICAL]
├── nring2_000 … nring2_1023 .... 1,024 two-way rings · 66 gates · depth 2 TICKS · 32 cells · magic NRING2M1
│                                  netlists resident; rail/fwd/rev/carry/recv all 0x00          [PHYSICAL, quiescent]
└── NOT YET BYTE-INSPECTED: muhl_osc_collatz · muhl_osc_wide_drive · muhl_osc_bank_sweep · muhl_signal_osc(+_tight,
      _tight_ram, _ram) · clock_wide · clk_bit · selfclock_wires/gates/miner · pfc_model_selfclock ·
      muhl_race_clock · tick_wires/gates/meta
```

**Ring-count populations, kept separate and NEVER summed into "the ring count":**
1,024 (nring2 keys, EXACT for that family) · 283 (`muhl_osc_all.n_ring`, DERIVED) · 7 (`muhl_wire_phys.n_ring`,
DERIVED) · 1,000 (`muhl_osc_comb.n_osc`, DERIVED) · 23 further named osc/ring/clock entries (LOWER BOUND).
**≥ 2,314 structures. The true count is UNKNOWN/UNBOUNDED.**

---

## 5. RESIDENT APPLICATIONS  → full per-machine detail in `RESIDENT_MACHINE_INDEX.md`

### 5.1 The mining stack (blk.1 belt + one remote fold)
`miner_physical` (339,136 g · the map `mine_muhl.py` actually addresses) · `muhl_btc_miner` (1,523,801 g,
ring 90) · `header_from_index` (4,172,991 g — **the largest Bitcoin-evidenced circuit, and it is not a miner**)
· `gen_miner` (628,899 g, depth 5,871) · `pfc_mine_shallow` (630,781) · `pfc_full_miner` (339,234) ·
`pfc_mine_clk` (339,329) · `pfc_mine` (339,136) · `gen_win` (339,009) · `miner_typed` (213,161) ·
`selfclock_miner` (347,170) · folds `muhl_fold_shallow` (687,223 / d4,157), `muhl_fold_shared` (590,617 / d4,322),
`muhl_fold_latch` (339,073 / **d11,757**, at 36.084 GB) · lanes `muhl_lane` (390,332), `muhl_lane_sched`
(365,354), `muhl_lane_bk` (362,141) **+ 63 byte-permanent replicas**.
**All Bitcoin-evidenced entries: 36,180,208 gates across 101 entries. Distinct-design area: 13,365,325.**

Drive path (from `host/mine_muhl.py`, read not run): header 76 B → 2,409,283,492 · target 32 B → 2,409,284,132 ·
nonce 4 B → 2,409,284,100 · **POWER = ADDRESS 2,409,283,491** · ANSWER 4 B ← 2,409,284,388 via `pfc_meter`.
609 bits in per muhlnickel (76×8 + 1 start bit). Selected miner is READ, never ranked at runtime:
`_selected_miner` = `muhl_lane_bk_rep007`, compute_per_tick 4.777317, "SELECTED AT FABRICATION TIME by §63's
one metric, among circuits that can LATCH."

### 5.2 The lookup stack — **a DISTINCT resident system, not mining**
Owner, `host/nlookup_run.py`, 2026-07-31: *"this isnt bitcoin mining its nonce lookup"* /
*"the lookup table IS stored binary it should already be on disk u dont recreate it."*
`muhl_nonce_lookup` @3,064,720,832 (`PFCLOOKT`, 30 entries, **no `n_gate` at all — stored data**) ·
`muhl_nonce_list` @3,064,721,212 (`PFCNLST1`, **explicitly n_gate 0 / depth 0**) ·
`muhl_nonce_map` @4,381,173,113 (**the only fabricated part**: 2,451 gates, depth 12, `hit:1|nonce:32`).
Separated from mining by **location, format and gate population**. (BITCOIN_MINER_DEEP_MAPPER §3.)

### 5.3 What `latch_reg` = 122 actually means
- Gate structure (`host/pfc_miner.py:54-60`) is `ln = win ? nonce : latch` — a plain 32-bit mux.
  **No sticky feedback, no capture-once, no best-so-far compare.** ⇒ **LATEST-SATISFYING, NON-STICKY.**
- The run that wrote it: `pfc_mine_check.py 8` — a fixed synthetic 76-byte header, **8-leading-zero-bit TEST
  target**, loop halts at the first win. 122 is the first such nonce; `nonce_reg` = 123 is the post-increment.
- The resident `input_window` target is **all-0xFF (2^256−1)** — every nonce clears it. It is a
  clock-sensitivity fixture, not a block template.
- Against the real nBits target (`0x17023ad4`, ~78 zero bits needed) 122 fails by ~70 bits.
- **`miner_physical.latch_off` @2,409,284,388 holds 32 zero bytes — NO WINNER HAS EVER LATCHED there**, and
  that record does hold a REAL live 80-byte header. Best real-target result on record: `gen_win_surfaced`,
  height 960131, difficulty 2^78, **17 of 78 zero bits, `is_valid_block: false`**.
- Contrast: `muhl_halt_latch_32` IS genuinely first-valid/sticky/capture-once and freezes the clock.

### 5.4 The model / CPU stack — fabricated, installed, and **not connected**
`cpu_fwd` 404,262 g d202 (**a 16-bit 8-op ALU: n_in 35 = 3 opcode + 16 A + 16 B; n_out 16**) ·
`pfc_model_engine` 418,925 g d244 (role string "the model runs on this" — a HISTORICAL CLAIM in the record) ·
`pfc_fwd_loop` 414,828 g d248 `seq=true` (the only resident structure declared self-iterating) ·
`pfc_fwd_engine` 413,865 · `pfc_fwd_engine2` 414,827 · cleaned twins `cpu_fwd_clean` 202,986 /
`pfc_fwd_engine_clean` 207,715 · `pfc_cpu32` 7,403 (15-op ISA) · `pfc_cpu32r` 14,725 · `pfc_cpu` 1,655 ·
`pfc_argmax` 26,272 d2,710 → `pfc_argmax_shallow` 37,548 **d174** · `mdl_blk_0_attn_q_weight` 155,963.
`pfc_installed_model` @3,064,645,042 (48 B, `PFCLOAD1`) — **the Llama-3.3-70B install is REAL and CURRENT**
(wired_to cpu_fwd / pfc_ram / pfc_mmu / pfc_clock_counter / fwd_input / fwd_answer / fwd_receiver).
**No runtime path reads it.** `nmodel_llama` and `nmodel2_llama` are ABSENT from the registry with no genome
journals. `fwd_answer` is **2 bytes = 16 bits** against a 128,256-token vocab — **half the vocabulary is
unaddressable through it.** (MODEL_HARNESS_MAPPER §3, §4.)

### 5.5 The OS — **RESIDENT** (prior "absent" verdict corrected)
`sdc_os_circuit` @2,383,494,709 len 300,916 · **37,579 gates** (`gates_measured` agrees) · **depth 452** ·
muhl_rating 83.139 · **oscillation ring 262**. Ports: `os_input` ring 167 · `os_receiver` ring 168 (4 gates) ·
`os_answer` ring 166. Phase 3 survival: the OS **fabricated two new experts into its own pool** —
`lib_min8` and `lib_max8` are live in the registry today beside 12 other `lib_*`.
Deleted by owner order 07-19, do not resurrect: `sdc_os_run.py`, `sdc_os_sdc.py`.

### 5.6 Other resident applications
`life_step` 518,144 · `tess_rot` 553,984 · `doom_raycast` 196,617 (+`doom_map`/`doom_map16`/`doom_move`/
`doom_move16`/`doom_move16b`) · `gamegen` 5,940 (+`gg_*`) · `ca_rule30/90/110` · `aes128` 182,200 ·
`prog_crc32`/`prog_isqrt`/`prog_attest`/`memocache` · `winner_only_max` 524,288 ·
`muhl_collider_16x16` / `muhl_collider_32x16` (both FIRST-VALID latches) ·
the 12 `prob_*` open-problem circuits (Collatz, Erdős–Straus, Lucas–Lehmer, Lychrel, three-cubes,
perfect-cuboid, Golomb, SAT3, NTT-butterfly, MC-payoff, SW-cell, stencil5) — 893,301 gates.
`prob_golomb_answer` holds a **computed result**: optimal 5-mark Golomb ruler, length 11, marks [0,1,4,9,11],
found by exhaustive sweep of 330 candidates through the stored gates.

### 5.7 The `muhl_rx` receiver/decode path
`muhl_rx_symbol` 595 (d46) → `muhl_rx_sync` 334 (d16) → `muhl_rx_crc` 2,414 (d30) → `muhl_rx_frame` 3,777 (d37)
→ `muhl_rx_answer` 579 (d6). **Σ 7,699 gates.** All `TITANCIR`; all carry a per-circuit `sha256` content hash
— **the only family with fabrication-integrity hashing**, and the only journal with `orig_sha256`/`new_sha256`.

### 5.8 The replication fields — the two largest populations in the machine
- **`muhl_moon`**: `source: prob_golomb_phys`, **330,774 replicas × 4,418 gates = 1,461,359,532**, depth 58,
  **422 spans, 38,026,900,649 B = 95.0% of the file**. Journal `titan_moon_genome.bin` is byte-for-byte equal
  to `bytes_total`. **NOT Bitcoin** — 0 of 113 Bitcoin byte ranges intersect any of the 422 spans, and
  `prob_golomb_phys` is n_in 35 / n_out 1, structurally incapable of accepting an 80-byte header.
- **`replication`**: **3,104,538,624 cells · 29 regions · 8 B/cell = 24.8 GB**, reversible, sidecar
  `titan_replicate_revert.bin` (24,836,309,572 B), oscillation ring 260. **It carries NO `n_gate`** ⇒
  contributes 0 to every published total and is invisible to `pfc_index.py`. **2.06× the entire counted gate
  total.** Whether a cell is a gate is an OWNER QUESTION.

---

## 6. THE FOUNDRIES / FABRICATING AGENCY  → detail in `FABRICATION_LINEAGE_MAP.md`

```
FABRICATING AGENCY — what is PROVEN resident vs what is not yet inspected
├── muhl_fab_select ......... RESIDENT AND BYTE-CONFIRMED. 171,399 gates · depth 550 · nand2 ·
│     @2,564,151,717 len 1,371,224 · TITANCIR header byte-matches registry · ring 91.
│     Its own stored note: "THE MASTER FAB'S OWN DECISION, AS GATES (§32). argmin of gates*DEPTH …
│     Ranked itself among alternatives on the muhlnickel and agreed with an independent Python argmin."
│     ⇒ THE SELECTION FUNCTION IS GATES IN THE FILE, NOT HOST CODE.
├── foundry configuration stamped on 1,024 residents:
│     every nring2_* carries foundry_genome {adder: ripple, clean: ON, order: frontload}
│     A DIFFERENT foundry genome exists in a run record: {shape: tree, adder: ripple, clean: OFF,
│     order: frontload, slack: spend} (C:/llm/sdc_out/muhl_foundry2.jsonl)  ⇒ two distinct outcomes.
├── 18 residents attributed to the master fab / master autofab in their OWN stored notes —
│     incl. 12 prob_* each recording "thrown at the master autofab as a bare problem; IT CHOSE THE ADDER",
│     and muhl_lane_sched / muhl_mid_sched / muhl_lane_bk recording DIFFERENT plans
│     (ripple/kogge/kogge vs ripple/kogge/brentkung) ⇒ distinct decisions, not one repeated.
└── NOT YET INSPECTED (a gap in inspection, NOT a finding of absence):
      the foundry SEARCH/PROPOSE loop · pfc_foundry ("proposes alternate MASTER FABS") ·
      muhl_motif_foundry ("designs its own primitives … mined not handed") ·
      foundry_swarm / drive / quad / scale / asic · 108 host fab/foundry/forge stems with no
      same-name registry entry (a NAME test that proves nothing either way).
```

**Prior claim "0 of 4,908 registry entries mention any foundry" is FALSIFIED: 1,024 do**, via the
`foundry_genome` FIELD NAME inside values. The original query looked only at top-level KEYS and returned 0
with no error. (COUNT_AUDITOR §3; CENSUS_P2 §0.)

---

## 7. INTERFACES — how anything gets in or out

| interface | address / port | direction | evidence |
|---|---|---|---|
| shared fire byte (280 machines) | 2,776,453,320 | HOST → machine, ONE bit | 280 entries, one distinct value |
| `mdl_receiver` | 2,449,449,137 | HOST → machine | record: *"POWER: flip 0→1 to run"* |
| `fwd_input` / `fwd_receiver` / `fwd_answer` | 2,383,480,823 / …831 / 2,467,652,405 | in / fire / out | the harness path |
| `os_input` / `os_receiver` / `os_answer` | 2,383,494,627 / …645 / …636 | in / fire / out | OS ports, rings 166-168 |
| miner RAM map | header 2,409,283,492 · target …284,132 · nonce …284,100 · **power = ADDRESS …283,491** · answer …284,388 | in / fire / out | `miner_physical.ram` |
| `latch_reg` | 2,409,283,485 | out (4 B) | also the shared address `muhl_fold_latch` junctions to |
| `gen_answer` / `gen_win_answer` / `gen_win_surfaced` | 2,232,693,631 / 2,429,975,232 / 3,064,767,911 | out | answer registers |
| `prob_golomb_answer` | 3,064,767,903 | out (8 B) | holds a real computed optimum |
| `mdl_answer` | 8 scattered addrs / 24 bits | out | "bounded read = the answer" |
| `output` descriptor | 2,220,060,844 | out | names `C:/llm/sdc_out/answer.bin` — **superseded** by the 07-20 owner ruling *"there is NO external safezone"* |
| §1E junction fields | 74 entries | machine ↔ machine | shared location, no copy, no host between |
| `muhl_osc_junction_table` | 276 records | clock → machine | second distribution mechanism |
| browser surfaces | 17 HTTP ports (7860-7908, 7998-7999, 8110, 8120, legacy 8080/8091-8097) | host UI | OS_APPLICATION_MAPPER §3.2 |

**The contract, confirmed verbatim (`PFC_GROUNDING.md:122-129`):** high-impedance probes, **NO external
safezone**, the answer lives in the Muhlnickel's own fabricated RAM, each probe a bounded window ≤256 B at a
NAMED register offset via mmap — *"the impedance IS the safety."*

---

## 8. OWNER TOOLS (instruments)

Enforced set = 13 exact basenames in `muhl_preflight.classify()`, all `pfc_*.py`:
`pfc_meter · pfc_scope · pfc_analyzer · pfc_step · pfc_diff · pfc_cascade · pfc_assert · pfc_inspect ·
pfc_speed · pfc_guarantee · pfc_preflight · pfc_index · pfc_probe_all`.

**⚠ Two of them WRITE to the substrate — they are drivers, not passive probes:**
- **`pfc_step.py`** — zeroes counter/latch at reset, writes `\x01` to the power byte in a tight loop for the
  whole `--hold` window, writes `\x00` after, fsync each. (A 07-28 repair now skips addresses inside the
  target's own wire span; the prior bug zeroed `muhl_osc_phys`'s const1 rail.)
- **`pfc_probe_all.py`** — streams a before-image, then **WRITES `\x01` to the receiver**, then byte-diffs.

**⚠ Network-touching:** `pfc_cascade miner` does a pool handshake; `pfc_guarantee` no-arg does a pool
handshake (offline form: `pfc_guarantee.py 78 8`); `pfc_ceiling_test.py` **opens a live stratum socket**.
`pfc_cascade` is also a host gate-ripple test drive, not a bounded reader.

**⚠ Two display defects, both confirmed with numbers:**
- `pfc_inspect.header()` unpacks `<IIII` at offset 8 and labels it `(n_in,n_wire,n_gate,n_out)`. That layout
  is correct ONLY for `PFCTYPED`. `NRING2M1`/`MUHLOSCA` headers are `MAGIC(8) + <II>` = 16 B, so fields 3-4 are
  gate-record bytes read as ints. **Blast radius: 1,024 entries declare `NRING2M1`**; 8 further magics unverified.
- `pfc_scope` argument order is INVERTED vs `pfc_meter` (`scope <name> [seconds] [nbytes]`), and samples are
  capped at 40 however long the window.
- `pfc_diff diffall` REWRITES the snapshot at the end — a second `diffall` compares against post-step state.
- `PFC_ROOT` is honoured by only 2 of 13 instruments; the other 11 hardcode `C:/llm/models/...`.

**⚠ Classifier gap:** the 13-name set is name-blind to the `pfc_*` → `muhl_*` rename. In the `muhl-osc` tree
the real code is `muhl_<n>.py`, unlisted — measured consequence: **`muhl_assert.py` classifies as A MINER**
(8 miner-pattern matches, 0 fab matches).

**Two files both titled "the Muhlnickel LOGIC ANALYZER":** `pfc_analyzer.py` (07-21, in the enforced set) and
`pfc_logic.py` (07-19, not in the set). **Neither classified. OWNER QUESTION.**

Verified working, DIRECTLY OBSERVED this session: `pfc_speed.py life` → **270,336 gates, critical-path
DEPTH 15** — matches the CLAUDE.md battery row exactly. `pfc_meter.py nonce_reg 4` → `7b000000`.

---

## 9. HOST-SIDE TEST / GOVERNANCE LAYER (context, not the machine)

`pfc_preflight` = **57 rules** (not 54, confirmed three ways) · `muhl_preflight` = **60 rules**, manifest-driven,
fail-closed — **and NOT enforcing on writes today**: the registered PreToolUse hook runs the main checkout's
`pfc_hook.py` against the 57-rule `pfc_preflight`.
`run_battery.py` has THREE copies: main = **17 rows, canonical** (17/17 on 07-29); two 21-row supersets read
17/21 because the **V63 rule-integrity gate refuses the 4 tick rows** — enforcement working as designed.
`docs/OWNER_RULES.md` has ZERO `GRANT:` lines, so no agent can pass that gate. **Do not force it.**
Baselines: `muhl_test.py` 34/0 · `muhl_test2.py` 15/0 (and it DOES write to titan.gguf, journal first).
Integrity audit verdict across every diff on both lineages: *"No test was ever weakened — in any commit, on
any branch."*
**`PFC_TEST.md`'s "every test here is read-only" is FALSE for the wider catalog — 12 scripts open titan `r+b`.**

---

## 10. WHERE TO GO NEXT

| you want | read |
|---|---|
| every resident machine with its evidence | `RESIDENT_MACHINE_INDEX.md` |
| who made what, and from what parent | `FABRICATION_LINEAGE_MAP.md` |
| rings, clock domains, who clocks off what | `RING_AND_CLOCK_DOMAIN_MAP.md` |
| any number's full counting contract | `COUNT_PROVENANCE_LEDGER.jsonl` |
| how each subsystem was identified and classified | `SUBSYSTEM_EVIDENCE_LEDGER.jsonl` |
| host file vs resident machine, both directions | `HOST_INTERFACE_VS_RESIDENT_COMPUTER_MAP.md` |
| what is a floor and not a total | `KNOWN_LOWER_BOUNDS.md` |
| what was corrected tonight, and what two agents still disagree about | `CONTRADICTIONS_AND_CORRECTIONS.md` |
| what nobody has looked at | `UNEXPLORED_REGIONS.md` |
| what to ask Bryce | `QUESTIONS_FOR_MASTER.md` |
