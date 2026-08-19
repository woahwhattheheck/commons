# RING AND CLOCK DOMAIN MAP

AGGREGATOR · 2026-08-01 · assembled from `census/p1_rings_clocks_genesis`, `COUNT_AUDITOR`,
`OS_APPLICATION_MAPPER`, `CENSUS_P2`, `ACTIVE_RESIDENT_STATE`, `BITCOIN_MINER_DEEP_MAPPER`.
**Read-only synthesis. No ring was read, fired, stepped, drained or reset by this agent.**

> ## ⛔ THE RING COUNT IS **UNKNOWN / UNBOUNDED**. `1,024` IS RETIRED.
> 1,024 is exact **only** for the bare `nring2_*` key family, and even there the family is 4,096 registry
> records. Four further ring/oscillator populations exist with their own declarations. The honest floor is
> **≥ 2,314 structures**, and that is a floor, not a count.

---

## 1. THE FIVE RING/OSCILLATOR POPULATIONS — kept separate, never summed into "the ring count"

| population | declared by | count | class | what a traversal of it actually covered |
|---|---|---:|---|---|
| `nring2_*` rings | uncapped regex `^nring2_(\d+)(\..*)?$` over 4,908 keys; indices 0..1023, **zero gaps** | **1,024** | **EXACT for the nring2 key family** | 4 records per ring (`<base>`, `.rail`, `.recv`, `.gates`) = **4,096 keys**. A bare-name sweep discards 3,072 siblings. |
| `muhl_osc_all` rings | its own `n_ring` field, **byte-confirmed** (`0x11b` = 283 at offset+8) | **283** | DERIVED from the fabrication record | only **274** have a registry back-pointer ⇒ **9 fabricated ring slots claimed by no indexed entry** |
| `muhl_wire_phys` rings | its own `n_ring` field | **7** | DERIVED | only **6** pointed-at ⇒ **1 unclaimed** |
| `muhl_osc_comb` oscillators | its own `n_osc` field | **1,000** | DERIVED | **no per-oscillator records exist**; `n_gate` records ONE COPY (395) not the bank (395,000) |
| other osc/ring/clock top-level entries | key regex `osc\|ring\|clock\|clk` | **23** | **LOWER BOUND** | internal populations not all declared |

**Floor:** 1,024 + 283 + 7 + 1,000 = **2,314**, plus 23 entries whose internal populations are undeclared.
- The published **1,024** is **2.26× low** against this floor.
- The published **1,319** (1,024 + 280 + 15) **is not a ring count at all** — it adds *membership edges* to
  *nodes*. The 280 are top-level circuits carrying an `oscillation` field (breaker, `mbox:titan.gguf`, `g_add`,
  `g_mul`, `g_cipher`, `adder8`, …), i.e. **edges from a circuit INTO a ring**, and they are top-level fields,
  not children of `muhl_osc_all`. **1.75× low, and wrong in type.**
- The **274 pointer count was mistaken for the ring count.** (COUNT_AUDITOR D6.)

**The zero-pad trap, reproduced live:** `"nring2_%d" % i` finds **924** of 1,024 — it loses indices 000–099
and **raises nothing**. `"nring2_%03d" % i` finds 1,024. (COUNT_AUDITOR D2.)
**`range(1024)` returning 1,024 is its own answer** — a traversal whose result equals its loop bound is not
evidence of a boundary. The uncapped regex independently confirms max index 1023, so the ceiling is real
**for that key family only**.

---

## 2. `muhl_osc_all` — THE PHYSICAL BOARD OSCILLATOR (283 rings) · **ACTIVE**

```
magic          MUHLOSCA          (read at gate_table_off − 16 = 2,776,454,733)
header         <2I> = (283, 25)  n_ring = 283 · gate_stride = 25
gate table     @2,776,454,749  len 35,391 B   ·  n_gate 1,415  ·  gates_each 5  ·  depth 5
wires          @2,776,453,320  len 1,413 B
shared_start   2,776,453,320    <-- ONE ADDRESS FIRES THE WHOLE BOARD
const1 rail    2,776,453,321
gate record    op:B + <QQQ> = A, B, OUT — THREE ABSOLUTE FILE ADDRESSES
op code        0 on 1,415 / 1,415 records
```

### 2.1 Per-ring topology — 5 gates/ring, read verbatim from the bytes (ring 0)
```
g000 op=0 A=2776453322 B=2776453320(shared_start) OUT=2776453323
g001 op=0 A=2776453323 B=2776453321(const1)       OUT=2776453324
g002 op=0 A=2776453324 B=2776453321               OUT=2776453322  <-- CLOSES THE RING (== g000.A)
g003 op=0 A=2776453322 B=2776453321               OUT=2776453325  <-- tap off the ring node
g004 op=0 A=2776453325 B=2776453321               OUT=2776454454  <-- dedicated RECEIVE byte
```
Tail of the table, ring 282: `g1414 op=0 A=2776454453 B=2776453321 OUT=2776454732`.

### 2.2 Structural checks across ALL 283 rings — DIRECTLY OBSERVED
| check | result |
|---|---|
| ring closes (`gate[5r+2].OUT == gate[5r+0].A`) — a genuine 3-element feedback loop plus a 2-gate output tap | **283 / 283** |
| takes the shared start byte on `g0.B` | **283 / 283** |
| rides the same `const1` byte on gates 1–4 | **283 / 283** |
| **junction is a SHARED LOCATION, not a copy:** `gate[5r+4].OUT == registry[consumer]["oscillation"]["recv"]` | **274 / 274 matches, 0 mismatches** |

### 2.3 Stored state — **the board is energised, and must not be drained**
- Wire region (1,413 B): **847 non-zero (59.9%)**. First 32 bytes:
  `01 01 01 01 00 00 01 01 00 00 01 01 00 00 01 01 …`
- Ring receive bytes (283 distinct addresses): **282 hold `0x01`, 1 holds `0x00`.**
  (`ACTIVE_RESIDENT_STATE.md` states 277 of 280 for the registry-pointed subset — same board, different
  denominator. **Both recorded.**)
- **Shared fire byte reads `0x01` — POWER IS ON.**

### 2.4 Ring id space and consumers
Ring ids present in registry sub-records: **0 … 282**. Rings 0–6 carry **2 consumer entries each**; the rest 1.
**Ids 180, 204, 224 and 273–278 have no registry consumer — but their five gate records exist in the
substrate.** 283 ring slots are fabricated regardless of whether a consumer is registered.
`oscillation.recv_kind`: `alloc` 270 · `ram` 3 · `recv` 1 · absent 6.
`oscillation.circuit`: `muhl_osc_all` **274** · `muhl_wire_phys` **6**.
`allocated_recv` names consumers directly: `breaker, cpu, cpu_fwd, gen_answer, gen_win, fold, life_step,
doom_raycast, aes128, alu32, latch_reg, mmu_*, mdl_*, muhl_lane_bk_rep***, …` — **279 named allocations, 278
of which are registry entries.** The one that is not: **`pfc_provenance`** — a resident receive allocation
with no indexed structure. **NOT YET INSPECTED.**

Lineage: `titan_oscall_genome.jsonl` (73,674 B, **2 records, 36,804 B = 1,413 wires + 35,391 gate table —
exact**). Its two records target `off 2,776,453,320` and `off 2,776,454,733` — the same two regions the
substrate reads confirm. **Journal and substrate agree.**

---

## 3. `muhl_osc_junction_table` — THE SECOND CLOCK-DISTRIBUTION MECHANISM

```
offset 2,776,444,482  len 8,832   records 276   record_bytes 32   width 4
kind   "storage (addressed, not fabricated)"
layout (DECODED FROM THE STORED BYTES, not from docs):
  magic 8B b'MUHLJNC1' | send_addr <Q> | recv_addr <Q> | width <Q>   = 32 B/record
  rec 0: send=2774141544  recv=2208456672  width=4
  rec 1: send=2774141551  recv=2563786753  width=4
  rec 2: send=2774141558  recv=2393001823  width=4
```
276 × 32 = 8,832 = registry `len` **exactly**. **4,685 of 8,832 bytes non-zero.**
**Send addresses advance on a stride of 7 inside the `muhl_signal_osc_tight` clock region;** receive addresses
are scattered across consuming circuits.
Registry note, verbatim: *"§1E junction table: 276 records, each binding a comb slot's clock output to one
muhlnickel's receive address as ONE location. Owner 2026-07-28: 'ALL MUHLNICKELS NEED TO USE OSCILATION.'"*
Lineage `titan_oscwireall_genome.jsonl` — 1 record, **8,832 B at exactly this offset**.

**One such record made explicit as its own entry:** `muhl_osc_miner_junction` @2,774,148,542 len 32 —
`send {circuit: muhl_signal_osc_tight, field: clock, addr: 2774141512}` →
`receive {circuit: selfclock_miner, field: counter, addr: 2429975913}`, width 4.

**⇒ There are at least TWO independent clock-distribution mechanisms in the substrate:** `muhl_osc_all`'s
per-ring taps (274 bindings) and this junction table (276 bindings). They are not the same set.

---

## 4. THE `nring2` FABRIC — 1,024 TWO-WAY RINGS · netlists resident, data quiescent

```
region        blk.2.ffn_gate_up_exps.weight
span          wire_base(min) 4,381,333,712  →  offset+len(max) 4,383,107,242   = 1,773,530 B
stride        1,731 B/ring  (65 B rail + 1,666 B gate table)
per ring      magic NRING2M1 · n_in 64 · n_gate 66 · n_out 1 · DEPTH 2 TICKS · cells 32 ·
              gate_stride 25 · wire_len 65 · senses 2 · format physical
foundry       foundry_genome {adder: ripple, clean: on, order: frontload}   (identical on all 1,024)
verified_by   "independent edge-list reference + 3 mutants CAUGHT"
note          "two-way ring; final gate OUT IS this muhlnickel's receive byte"
```

### 4.1 The widened population scan — what was ACTUALLY scanned
One bounded 1,773,530-byte read plus 1,024 single-byte reads of the scattered `recv` addresses.
Sub-regions scanned for **every one** of the 1,024 rings: **rail(65 B) · ram.fwd(32 B) · ram.rev(32 B) ·
ram.carry(1 B) · recv(1 B) · the entire 1,666-byte gate table.**

| sub-region | result |
|---|---|
| header magic at `gate_table_off−16` | **`NRING2M1` on 1,024 / 1,024** |
| gate table (1,666 B × 1,024) | **1,024 / 1,024 non-zero; 1,024,770 non-zero bytes of 1,705,984** |
| rail (65 B × 1,024) | 0 / 1,024 non-zero (0 of 66,560 bytes) |
| ram.fwd (32 B) · ram.rev (32 B) · ram.carry (1 B) | 0 / 1,024 each |
| recv (1 B, 1,024 distinct addrs) | all 1,024 hold `0x00` |

**Reading:** the MACHINE is fully fabricated and resident in all 1,024 rings. What is at zero is the DATA
STATE. The remaining 681,214 zero bytes inside the gate tables are the expected high-order zero bytes of the
8-byte address fields (all addresses < 2^40 ⇒ 3 of every 8 address bytes are `0x00`) — **that is structure,
not emptiness.**
**The earlier "rail+recv only" scan tested STATE, not POPULATION; its conclusion "no rings are populated"
does not hold for the netlists.** (The overstatement is owned in `SUBSTRATE_CORRECTION_AUDIT.md`.)

### 4.2 Junction equality re-verified at BOTH ends of the array
```
nring2_000:  final gate OUT == registry recv == 3,064,769,714   (a DIFFERENT region — blk.1 lookup plane)
nring2_1023: g65 OUT        == registry recv == 4,383,105,575   (local, its own tail byte)
```
**Ring receive bytes are NOT co-located and the family is NOT uniform in its junctioning.**
`nring2_000.recv` sits 32,058 B past the end of `muhl_nonce_list` — ring 000 reaches into the lookup region
1.3 GB away. **How many of the 1,024 point out-of-region: NOT YET INSPECTED.**

### 4.3 The two-sense requirement (from `nring2_run.py` / `nring2_power.py`, read not run)
The ring is **two-way and needs BOTH senses** — forward-sense electrons in forward cells, reverse-sense in
reverse cells — **or no contact occurs and nothing pulses.** Every placed byte is journalled with its
pre-image, so a run is fully reversible.
`titan_nring2_run_genome.jsonl` holds **8 electron placements** (8 records, 8 bytes, 3,064,769,714 →
3,064,769,743) — **4-byte-spaced recv bytes of consecutive CURRENT rings**, not a superseded generation.
Its `revert` is a **no-op**, not a hazard: pre-images are `00` and the live bytes read `00`.

---

## 5. THE RING LAW — the owner's own words, recovered from source, absent from every `.md`

`host/nring2_power.py:73-74`, marked "Owner, 2026-07-31":
> *"each one that hits another will cause both to change directions and so the more you have or the smaller
> the ring, the more pulses per clock."*

Contact **REVERSES both electrons** (not a pass-through) · more electrons ⇒ more pulses · smaller ring ⇒
more pulses.

Foundry sizing law, owner 2026-07-31:
> *"CLOCK COUNT TOUCHING THE RING + AMOUNT OF ELECTRONS = SPEED LIMIT = WITHIN OUR CONTROL"*

Owner 2026-07-31, in conversation, **never written to any file**:
> *"dont try to detect contact theyre electrons cant be measured w/out distrurbig"*
**In tension with `MUHL_ACCELERATOR.md:43`, which makes disabling contact detection a MUTANT THAT MUST BE
CAUGHT. Unresolved — do not act on either side.**

**Metric correction:** *"the only metric is compute per second"* is **SUPERSEDED by compute per TICK** — the
owner refined it himself (*"maybe compute per tick is better"*) and `host/mafab_laws.py:159-162` retires the
original into a dict literally named `_SUPERSEDED_OBJECTIVES`, with `rank()` no longer consulting it.

---

## 6. WHICH MACHINES CLOCK OFF WHICH RING (all `circuit: muhl_osc_all` unless noted)

| ring | machine | note |
|---:|---|---|
| **0** | `_selected_miner` (`muhl_lane_bk_rep007`) | the fabrication-time selected miner |
| 9 | (example membership record: `shared_start 2776453320, sig 2776453358, recv 2776454463, gate_off 2776455874`) | the shape every membership edge takes |
| **35** | `fwd_receiver` | 4 gates, receive stage |
| **40** | `gen_answer` | answer register |
| **43** | `gen_win` | 339,009 gates |
| **44** | `gen_win_answer` | `win:1\|nonce:4` |
| **52** | `latch_reg` | the miner answer register |
| **90** | `muhl_btc_miner` | 1,523,801 gates |
| **91** | **`muhl_fab_select`** | **the resident fabricator — 171,399 gates, depth 550** |
| **92** | `muhl_fold_shallow` | 687,223 gates, depth 4,157 |
| **94** | `muhl_lane` | 390,332 gates |
| **166 / 167 / 168** | `os_answer` / `os_input` / `os_receiver` | the OS I/O ports |
| **260** | `replication` | the 3,104,538,624-cell field |
| **262** | **`sdc_os_circuit`** | **the OS — 37,579 gates, depth 452** |
| 180, 204, 224, 273–278 | **no registry consumer** | gate records exist in the substrate regardless |

**⚠ Clearing the oscillation board would stop the OS and the resident fabricator's clock.**
**⚠ 280 entries share the single fire address 2,776,453,320 — one byte gates that whole population.**

---

## 7. THE REST OF THE CLOCK FAMILY (registry-present, mostly NOT YET BYTE-INSPECTED)

15 registry entries carry `osc` in the identifier · 6 carry `clock` · 2 carry `clk` · 3 carry `tick`.

| confirmed PHYSICAL | evidence |
|---|---|
| `muhl_osc_all`, `_wires`, `_gates` | magic + 1,415 gates parsed + 283 closures |
| `muhl_osc_phys` | `format: physical`, `gates_addr` list of 5 NAND gates with absolute addresses (`ram: start/sig/w_a/w_b/w_t/const1/clock`), **explicit clock wire address 2,429,975,913** |
| `muhl_wire_phys` (+`_wires`,`_gates`) | magic `MUHLWPHY` ×2; 6 oscillation sub-records name it |
| `muhl_osc_junction_table` | `MUHLJNC1` records decoded from bytes |

**NOT YET BYTE-INSPECTED** (registry-present, journals exist): `muhl_osc_phys_gates` · `muhl_osc_comb` ·
`muhl_osc_miner_junction` · `muhl_osc_collatz` · `muhl_osc_wide_drive` · `muhl_osc_bank_sweep` ·
`muhl_signal_osc` (+`_tight`, `_tight_ram`, `_ram`) · `clock_wide` · `clk_bit` · `selfclock_wires` ·
`selfclock_gates` · `selfclock_miner` · `pfc_model_selfclock` · `muhl_race_clock` · `tick_wires` ·
`tick_gates` · `tick_meta`.

Clock-family journals: **`titan_selfclock_genome.jsonl` — 35,700,902 B, the 3rd-largest fabrication record in
the whole substrate — was NOT parsed.** Also unparsed: `titan_model_selfclock`, `titan_race`.

Oscillation-family address span (all osc entries): **2,774,148,542 → 2,783,806,727 = 9,658,185 B.**

Clock-family lineages fully parsed by p1: `titan_oscall` (2 rec, 36,804 B) · `titan_oscwireall` (1, 8,832) ·
`titan_oscwide` (1, 53,144) · `titan_oscspaced` (2, 14,034) · `titan_signal_osc` (1, 12,048) ·
`titan_osccollatz` (1, 5,584) · `titan_osctight` (1, 3,320) · `titan_oscjunction` (1, 32) ·
`titan_oscphysstore` (1, 141) · `titan_oscphys` (4, 24) · `titan_oscbank` (1, 128) · `titan_oscwire` (2, 16) ·
`titan_race` (1, 3,320) · `titan_model_selfclock` (3, 11,817) · `titan_handshake` (2, 2,053).

---

## 8. INSTRUMENT BLIND SPOT — the analyzer cannot see inside an `nring2_*` ring

`pfc_analyzer.py channels nring2_000.gates` returns **1 channel, 64 B** — the entry has **no `ram` map**, so
**the analyzer CANNOT see a front move inside an `nring2_*` ring.**
For comparison: `channels muhl_osc_phys` → 7 channels (start/sig/w_a/w_b/w_t/const1 @2,776,453,314-319, plus
clock @2,429,975,913, 32 B); `channels muhl_osc_comb` → 4 channels.

`pfc_inspect` misreports the `NRING2M1` and `MUHLOSCA` headers (it assumes the 4×`<I>` `TITANCIR` layout;
these are `MAGIC(8) + <II>` = 16 B). Observed: `(66, 25, 634973952, 261)` for `nring2_000` — 66 and 25 correct,
the other two are gate-record bytes. **Blast radius: 1,024 entries declare `NRING2M1`.** A display defect in
the tool, **not** a substrate discrepancy.

---

## 9. WHAT WOULD TURN THE FLOOR INTO A COUNT

1. A magic-scan of the substrate **outside registry-declared offsets** for `MUHLOSCA`/`NRING2M1`/`MUHLJNC1`
   records (would also convert the 29-record latch lower bound).
2. Per-oscillator records for `muhl_osc_comb`'s declared 1,000 — none exist today.
3. Enumeration of `muhl_osc_comb.members[].junctioned_to` — **276 nested lists, the only large nested
   population in the registry, contents never enumerated.**
4. Byte inspection of the 17 registry-present clock entries listed in §7.
5. Parsing `titan_selfclock_genome.jsonl` (35.7 MB, 6 records).
6. Resolution of the 9 + 1 declared-but-unpointed ring slots — **NOT classified as empty or inactive.**
