# FABRICATION LINEAGE MAP

AGGREGATOR · 2026-08-01 · assembled from `FABRICATION_LINEAGE_MAPPER`, `census/p1`, `census/p2`,
`BITCOIN_MINER_DEEP_MAPPER`, `COUNT_AUDITOR`, `a1_foundry_genome`.
**No journal was opened by this agent. The 38 GB `titan_moon_genome.bin` remains STAT-ONLY across all agents.**

---

## 1. WHAT A FABRICATION RECORD IS

**Journal schema (read directly by p1):** `{"off": <absolute file address>, "orig": "<hex of the bytes that
were there before>"}` — an **fsynced pre-write UNDO log**. Bytes written by a fabricator = `len(orig)/2` per
record. `revert()` replays in reverse, pops the registry, and re-checks GGUF magic.

Six journals additionally carry `len`+`name` (a named lineage). **Exactly one — `titan_rx_genome.jsonl` —
carries `orig_sha256` + `new_sha256` per record**, i.e. a later, hash-verified journal generation.

**The Foundry writes no genome records itself** — it shells out to `muhl_moon.py`. Join proven:
`muhl_moon.bytes_total == stat(titan_moon_genome.bin) == 38,026,900,649`.

---

## 2. THE JOURNAL POPULATION — three counts, kept separate

| statement | value | class |
|---|---:|---|
| `C:/llm/models/*_genome.jsonl` (glob, non-recursive) | **78** | EXACT for that namespace |
| recursive `*genome*.jsonl` under `C:/llm` | 80 | EXACT for that sweep |
| + `titan_moon_genome.bin` + `titan_moon_genome.json` = **the published "82"** | 82 | EXACT *given an extension filter* {jsonl, bin, json} — it silently drops `titan_phys_chain_genome.jsonl.1` |
| + `.jsonl.1` backup | 83 | — |
| + `WeightGenome.kt` (Kotlin source, not an artifact) | 84 | `find -iname "*genome*"` |
| journals **present on disk** (78 .jsonl + 1 .bin) | **79** | FABRICATION_LINEAGE_MAPPER |
| journals **declared by host code** across three checkouts | **92** | ″ |
| **declared but ABSENT** | **25** | ″ |
| **present with no producer located** | **12** (7 resolve to a percent-format name in `muhl_phys_problem.py`, 1 to `_seq_genome()` in `titan_circuit.py`, 1 to `prototype/receiver/fab/store.py`; **3 unresolved**) | ″ |

**Fabrication RECORDS (lines), not files:** p1 and OS_APPLICATION_MAPPER both report **3,348** across the 78
top-level journals; FABRICATION_LINEAGE_MAPPER reports **3,770** total edit records including the 422 moon
manifest spans. **Both recorded; the difference is the moon spans plus scope. Not reconciled, not averaged.**
File count and record count differ by ~43×. **The published figure counts FILES.**

---

## 3. PRODUCER GENERATIONS — 228 scripts, 7 name-generations, 3 checkouts

| generation | producer scripts | trees | note |
|---|---:|---|---|
| `muhl_*` | 69 | worktree `muhl-osc` (+2 elsewhere) | newest generation |
| `pfc_*` | 68 | main repo + worktree `grounding-doc` | |
| `fab_*` | 61 | **all three trees, identical names** | a shared generation both others inherit |
| `sdc_*` | 21 | all three | oldest; **six of them share ONE journal** |
| `titan_circuit.py` core | 3 | all three | `_seq_genome(name)` → dynamic `titan_seq_<name>_genome.jsonl` |
| `nring2_*` | 2 | `grounding-doc` | the ring-field foundry |
| `nmodel*` / `nslice` | 3 | `grounding-doc` | **declared, journals ABSENT** |

**The `pfc_*` and `muhl_*` generations write the SAME journal filenames** — `pfc_aes.py` and `muhl_aes.py`
both write `titan_aes_genome.jsonl`; likewise cpu32, executor, miner, mmu, program, membus, batch, eval,
membership, app. **Direct evidence of one fabricator population carried across a generation boundary.**

**Many-to-one journals:** `titan_sdc_genome.jsonl` has **SIX** producers (`sdc_clock_wide`, `sdc_fab_big`,
`sdc_fanout`, `sdc_header_from_index`, `sdc_storage_computer`, `sdc_winner_max`) — a shared foundry journal.
The only other many-to-one is `titan_memocache_genome.jsonl` (2 producers).

---

## 4. REGISTRY-SIDE ATTRIBUTION — four DIFFERENT mechanisms that cannot be added

1. **Journal filename axis** — 78/79 lineages.
2. **`genome` field on residents** — only **1,032 of 4,908** name their producing journal:
   1,024 → `titan_nring2_genome.jsonl` · 5 → `titan_rx` · 1 each → `titan_race`, `titan_osccollatz`,
   `titan_oscwide`. ⇒ **3,876 entries have UNKNOWN lineage from the registry.**
3. **`foundry_genome` field** — **1,024** residents carry `{adder: ripple, clean: on, order: frontload}`
   stamped **inside the resident structure's own record**, not in a host log.
4. **`note`-field attribution to the master fab / master autofab** — **18** residents.

> **These are four attribution MECHANISMS, not four counts of the same thing. They must never be summed.**
> (CENSUS_P2 §7, §12.)

**Two distinct foundry decision genomes are on record with DIFFERENT values:**

| where | genome |
|---|---|
| stamped on 1,024 residents | `{adder: ripple, clean: **on**, order: frontload}` |
| foundry run record `C:/llm/sdc_out/muhl_foundry2.jsonl` | `{shape: tree, adder: ripple, clean: **off**, order: frontload, slack: spend}` |

Different `clean` setting, different field set. **Whatever the host files' 2-line diff shows, the recorded
OUTCOMES are not identical.** (CENSUS_P2 §0.)

---

## 5. PARENT–CHILD CHAINS TRACED (four, all with equations)

### Chain A — three generations, byte-confirmed
```
prob_golomb            typed, @2,775,067,638, record says it "keeps local wire indices and is UNTOUCHED"
  └─> prob_golomb_phys physical, @4,381,195,328, magic MUHLPHYS, 4,418 gates, depth 58, n_in 35 / n_out 1
        └─> muhl_moon  330,774 replicas × 4,418 = 1,461,359,532 gates · 422 spans · 38.03 GB journal
```
Evidence: `muhl_moon.source == "prob_golomb_phys"`; `prob_golomb_phys.source == "prob_golomb"`; n_gate 4,418
and depth 58 match on both; the multiplication is exact; the 422 manifest spans sum to 38,026,900,649 B =
the `.bin` size to the byte. **This is the typed→physical conversion recorded in the substrate itself.**
Producer: `muhl_moon.py` (worktree `muhl-osc`) — but **no fabricator script for `muhl_moon` exists in `host/`
or `C:/llm/muhl_builds`** per BITCOIN_MINER_DEEP_MAPPER §6. *(Both statements recorded; see
CONTRADICTIONS_AND_CORRECTIONS.md D3.)*

### Chain B — 63 children, exact 1:1 with the journal
`muhl_lane_bk` → `muhl_lane_bk_rep000..rep062`, each `replica_of: "muhl_lane_bk"`, 362,141 gates / depth 2,892
/ 3,259,425 B, typed, contiguous from 2,568,782,366 with **zero gaps and zero overlaps** (verified by sorted
offset traversal). Producer `fab_replicas.py`; journal `titan_replicas_genome.jsonl` = **63 records,
205,343,775 substrate bytes**. Entry note verbatim: *"PERMANENT WRITE. A replica in the file, not a cached
count."*

### Chain C — 1,024 siblings from ONE foundry configuration
`nring2_000 … nring2_1023`, each 66 gates / 32 cells / depth 2 / 1,666 B, **plus 3,072 `kind: reservation`
byte allocations** (`.rail` / `.recv` / `.gates`) — **3 per ring, matching the journal's 3,072 records
exactly.** Journal bytes 1,773,568 = 1,024 × (65 + 1,666 + 1) = 1,024 × 1,732. **Exact.**

### Chain D — multi-substrate, the only journal that leaves `titan.gguf`
`titan_sdc_federation_genome.jsonl` — 12 records, 57 B each, recording byte edits at **12 DIFFERENT substrate
files**: Llama-70B, SmolLM2, gemma-4-26B, gemma-4-31B, gemma-3-27b, Mistral-Small-24B, Mixtral-8x7B, phi-4,
`titan.gguf`, `titan_test.gguf`, sd-turbo, sd15.

---

## 6. LINEAGE ↔ SUBSTRATE AGREEMENTS (independent cross-checks that PASSED)

| check | equation | result |
|---|---|---|
| nring2 | 1,773,568 B = 1,024 × (65 rail + 1,666 gates + 1 recv) | **exact** |
| oscall | 36,804 B = 1,413 wires + 35,391 gate table, in 2 records / 2 regions | **exact** |
| oscwireall | 8,832 B at 2,776,444,482 = the junction table's exact offset and length | **exact** |
| miner_physical | 339,136 gates × 25 stride = 8,478,400 = `gate_bytes` | **exact** |
| junction table | 276 × 32 = 8,832 = registry `len` | **exact** |
| lane bank | 63 replicas × 3,259,425 B = 205,343,775 = journal bytes | **exact** |
| moon | 330,774 × 4,418 = 1,461,359,532; 422 spans = 38,026,900,649 = `stat(.bin)` | **exact** |
| moon (bytes) | 330,774 × 114,905 = 38,007,586,470 vs declared `bytes_total` 38,026,900,649 | **MISMATCH: 19,314,179 B (0.05%) — UNEXPLAINED** |

---

## 7. TOP LINEAGES BY SUBSTRATE BYTES REWRITTEN

| journal | file bytes | edit records | substrate bytes rewritten | off_min | off_max |
|---|---:|---:|---:|---:|---:|
| `titan_moon_genome.bin` | 38,026,900,649 | 422 | 38,026,900,649 | 15,834,304 | 40,022,599,171 |
| `titan_replicas_genome.jsonl` | 410,689,629 | 63 | 205,343,775 | 2,568,782,366 | 2,774,126,141 |
| `titan_sdc_genome.jsonl` | 260,918,880 | 10 | 130,459,275 | 2,232,693,700 | 2,362,989,111 |
| `titan_selfclock_genome.jsonl` | 35,700,902 | 6 | 17,850,352 | 2,418,101,956 | 2,439,004,638 |
| `titan_miner_physical_genome.jsonl` | 17,637,033 | 3 | 8,818,467 | 2,409,283,490 | 2,418,101,956 |
| `titan_model_fab_genome.jsonl` | 14,779,093 | 9 | 7,389,398 | 2,449,292,148 | 2,461,013,571 |
| `titan_lane_sched_genome.jsonl` | 13,095,600 | 2 | 6,547,767 | 2,554,543,846 | 2,568,782,366 |
| `titan_genwin_shallow_genome.jsonl` | 12,370,359 | 1 | 6,185,163 | 2,537,726,217 | 2,543,911,380 |
| `titan_nring2_genome.jsonl` | 3,767,368 | **3,072** | 1,773,568 | 3,064,769,714 | 4,383,107,242 |
| `titan_fold_latch_genome.jsonl` | 6,103,660 | 1 | 3,051,813 | **36,084,013,600** | 36,087,065,413 |
| `titan_pfc_miner_genome.jsonl` | 6,105,407 | 5 | — | — | — |
| `titan_problems_genome.jsonl` | 5,366,069 | 13 | — | — | — |
| `titan_rx_genome.jsonl` | 126,453 | 5 | 62,636 | 4,381,048,429 | 4,381,111,065 |

**Record count tracks REPLICA COUNT, not size** — `titan_nring2` holds 3,072 of 3,770 records but only
1.77 MB; `titan_sdc` holds 10 records in 261 MB.

Total substrate bytes rewritten across all journals (**with overlap, not deduped**): **38,471,836,756**.

---

## 8. COVERAGE — two independent traversals, two answers, both recorded

| traversal | covered | never covered | gaps |
|---|---|---|---|
| **fabrication journals + moon manifest** (FABRICATION_LINEAGE_MAPPER §2.1) | 38,471,614,002 B (**96.111%**) | **1,556,702,798 B (3.889%)** | 256 |
| **registry `[offset, offset+len)` union** (COUNT_AUDITOR §9) | 38,555,389,803 B (**96.32%**) | **1,472,926,997 B (3.68%)** | 268 |

Both exclude `titan_replicate_revert.bin`. **Uncovered is UNEXPLORED, not empty.**
Largest gap in both: **887,784,721 → 1,746,224,832 = 858,440,111 B (0.86 GB)**.

---

## 9. FABRICATION BELTS — where each generation laid down its work

| region | entries | recorded gates | character |
|---|---:|---:|---|
| 0–2 GiB | 20 | 0 | header / metadata / early tensor directory |
| **2–3 GiB** | **413** | **46,620,853** | historic `sdc_*` → `pfc_*` belt: miners, folds, CPUs, executor, AES, model engines, the OS, the resident fabricator |
| 3–4 GiB | 8 | 0 | receiver / **shared-address plane** (recv at 3,064,7xx,xxx) |
| **4–5 GiB** | **4,086** | **96,594** | `nring2` ring field + `prob_*_phys` physical-form belt |
| 5–33 GiB | ~330 | 0 | `muhl_moon` spans only — gates real, recorded once on the parent |
| 33–34 GiB | 11 | 339,073 | `physical-address` form + fold/latch belt |
| 34–37 GiB | 29 | 0 | moon span tail |

**Three distinct address territories:** 2 GiB (legacy typed circuits), 4 GiB (physical-form + ring field),
3.06 GiB (a shared receive-address plane — ring 000's `recv` points into it while ring 1023's points at its
own bytes: **a mixed junction topology**).

---

## 10. HOW MANY DISTINCT FABRICATING LINEAGES? — every answer, by axis

| axis | answer | class |
|---|---:|---|
| producer generation (name prefix) | **7** across **228** producer scripts in 3 checkouts | **DISCOVERED LOWER BOUND** — trees outside `host/*.py` were not swept |
| journals on disk / declared by code | **79 / 92** | EXACT for those sweeps |
| distinct `genome` values on artifacts | **5** | EXACT for the registry |
| distinct `foundry_genome` configurations observed | **2** (one stamped on 1,024 residents, one in a run record) | EXACT for what was read |
| residents attributed to master fab/autofab by their own note | **18**, carrying **≥2 distinct adder plans** | EXACT for the note field |
| **count of resident Foundry MACHINES** | **UNKNOWN** — CENSUS_P2 explicitly refused to invent one | **UNKNOWN/UNBOUNDED** |

**What IS proven resident:** `muhl_fab_select` — a 171,399-gate, depth-550 nand2 circuit at 2,564,151,717,
`TITANCIR` header byte-matching the registry, wired to oscillation ring 91, whose own stored note says it
*"Ranked itself among alternatives on the muhlnickel and agreed with an independent Python argmin."*
**The selection function is gates in the file, not host code.**

**What is NOT YET INSPECTED (a gap in looking, NOT a finding of absence):** the foundry SEARCH/PROPOSE half ·
`pfc_foundry` (*"proposes alternate MASTER FABS … runs continuously"*) · `muhl_motif_foundry`
(*"designs its own primitives … mined not handed"*) · `foundry_swarm / drive / quad / scale / asic`.

**`muhl_selfimprove` — a POSITIVE measurement, not an absence of looking:** no registry key; all 18 quoted
identifiers in its source cross-referenced against the registry → **0 match**; `grep` for
`gguf|registry|titan_circuits|json.dump` returns exactly one line, its own docstring *"titan.gguf is never
opened for compute."* **It writes no substrate byte and registers nothing** ⇒ classified
**INTERFACE / fabrication-time host tool**. Its netlist rewrites (double-inverter removal, balanced XOR
reduction tree, Kogge-Stone adder) are re-verified byte-exact against **two** independent references —
**nothing about it is reported as corruption or damage; a naive mutation detector flagging it would be the
thing that is wrong.**

---

## 11. UNKNOWN / UNBOUNDED IN THE LINEAGE AXIS

3,595 registry entries with no `n_gate` · 3,876 with no `genome` field · 11 with no offset · 25 declared-but-
absent journals · 3 journals whose producer was not located · the 38 GB moon payload (never opened) ·
9 `*.wbgenome` directories · `titan_replicate_revert.bin` (24,836,309,572 B) · `titan_replicate_manifest.json`
(unread) · 11 further substrate files touched by the federation journal ·
`C:/llm/models/_nightwork_backup`, `_removed`, `_to_delete_spent_genomes` (never enumerated).
