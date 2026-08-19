# MUHLNICKEL SPEC MAP

Built by running tests on this machine, Desktop newest to oldest. Live runs only,
nothing quoted from a document. SUBSTRATE and HOST figures kept in separate columns.

AUTHORSHIP: assistant-written. Owner quotes are marked. Everything else is measurement.
started 2026-08-05 15:14

---

## 1. SHIPPED CONTAINERS - declared spec, read from each header

| container | bytes | netlist | operand | out | ring | driven | domain |
|---|---|---|---|---|---|---|---|
| LOOM_fixed | 140,454 | 283 g | 16 bit | 8 | 66g / 32c / 2 senses | 32,768 ticks | 65,536 resident |
| LOOM_v2 | 140,454 | 283 g | 16 bit | 8 | 66g / 32c / 2 senses | 32 ticks | 65,536 resident |
| LOOM_v1 | - | - | - | - | - | - | REFUSED: reader fails its own manifest hash |
| DISTRO | 136,450 | 129 g | 16 bit | 8 | 66g / 32c / 2 senses | 32 ticks | 65,536 resident |

LOOM_fixed and LOOM_v2 are identical in size and netlist. The ONLY difference is drive:
32,768 ticks vs 32. A 1,024x drive change with everything else constant.

LOOM_v1 refuses to run: run_muhlnickel.py fails its manifest hash (expected 1e67ba1e...,
found 1ac62811...). The tamper-check works. Not repaired.

---

## 2. THE BINARY SCRAPE - what a run actually writes

Owner: "loom run button updates files in that folder the binary scrape test that"

Method: sha256 every file, byte-copy loom.mno, fire one shot, diff to exact offsets.

```
shot fired    : loom 200 55  -> 0x94   ring published 1
files changed : loom.mno ONLY, 6 of 7 untouched, 0 new files
bytes changed : 32 of 140,454   0.02 percent
all changes   : inside the 84-byte state wire at 288..372
sealed region : 0 bytes moved
seal 192..224 : unchanged
```

| range | region |
|---|---|
| 288-303 | forward cells |
| 320-335 | reverse cells (same offsets +32) |
| 354-371 | operand register (16 bits) + sel (2 B) |

Both senses written, symmetrically. loom_genome.jsonl byte-identical: a shot into state
wires is not a fabrication event and writes no journal entry.

RULE ZERO verified under an actual fire. The seal excludes the state wire by design and
only that region moved.

---

## 3. WHOLE-FILE RING - addressed vs enumerated

Owner: "what if the entire file was a ring and just distributed electrons deterministic"

Tested on a 214,544 B container, N = every byte:

| | enumerated | addressed |
|---|---|---|
| gate records stored | 429,090 | 0 |
| gate table bytes | 10,727,250 | 0 |
| size vs file it rings | 50.0x | 0.0x |
| DEPTH ticks | 2 | 2 |

Enumerating stores one identical rule 214,544 times. Closed form:
position of electron j at settle t = ((j*N)//K + t) mod N.
Precedent in the registry: muhl_nonce_list, n_gate 0, depth 0, bytes_per_nonce 0.

Coverage is NOT monotonic in K - it is divisibility with N:

| K | period | dings/settle | coverage |
|---|---|---|---|
| 1 | 214,544 | 1 | 100.0% |
| 256 | 838 | 256 | 100.0% |
| 1,024 | 209 | 1,024 | 99.8% |
| 65,536 | 3 | 65,536 | 91.6% |
| 214,544 | 1 | 214,544 | 100.0% |

K=65,536 reaches LESS than K=256 because (j*N)//K collides when K does not divide N.
Good K divides N. A fabrication-time choice.

---

## 4. TEST BATTERY - run live this session

| suite | result |
|---|---|
| run_battery | 17/17 |
| muhl_verify_all | 9 PASS 0 FAIL 0 SKIP |
| muhl_gate_reader --sweep | 51,103,634 records, 1,322 circuits |
| muhl_gate_reader --typed | 29,868,234 records, 0 out-of-range, 0 dup |
| muhl_claims_receipt | 14 MATCH, 1 MISMATCH |
| whitebox smoke_test | 28 PASS 0 FAIL |
| muhlop_tests | 23 PASS 1 FAIL |
| muhl_proof | PASS |
| test_leakage | 186 assertions, 0 fail |
| wb_proof | 8/8 stages, all rc=0 |
| wb_proof_ref | 119/119 matched |
| wb_proof_mutant | 3/3 detected, control clean |
| pfc_fold_check | PASSED, winner latched |
| pfc_ramtest | 204,800,000 gate-evals, +0.000 MB |

The MISMATCH is registry 5,004 expected vs 5,006 live - two circuits fabricated today.
The check caught a real change rather than absorbing it.

muhlop T20 fails on stale CONTAINER_BYTES = 40,028,316,800, which is titan_test.gguf,
not titan.gguf. Same stale number is in CLAUDE.md line 385.

---

## 5. SUBSTRATE vs HOST - kept apart

| SUBSTRATE (ticks, gates, records) | HOST (seconds, RAM, tooling) |
|---|---|
| DEPTH 2 ticks per ring | verify_all 47.8 s transcription |
| 66 records per ring, 1:1 outs | wb_proof 103.5 s |
| 80,971,868 gate records, 0 anomalies | +0.000 MB over 204.8M gate-evals |
| 65,536 answers resident per container | citation gate race, host-side, mine |
| 32 bytes moved by a fire, all state wire | OneDrive hook path dead since purge |

No host number appears in a substrate column. 1 silly = 1 tick/sec; a tick is an
electron hitting a clock. Ticks are fabricated, sillies are measured.
