# KEEP CURRENT — working / broken / needs work

Fact-checked 2026-08-05 by running things in spec, not by trusting handoff docs. Every row
below says HOW it was checked. A model-authored document is evidence a model wrote it, not
that the thing exists — several claims in the existing handoffs did not survive contact.

---

## ✅ WORKING — run in spec this session

| what | evidence |
|---|---|
| `MUHLNICKEL_LOOM\loom.mno` 140,454 B | `python run_muhlnickel.py 200 55` → `loom(200, 55) = 0x94  (ring published: 1)` |
| `MUHLNICKEL_LOOM_fixed\loom.mno` | same command → `0x94`, identical to LOOM |
| `MUHLNICKEL_DISTRO\muhlnickel.mno` 136,450 B | `python run_muhlnickel.py 200 55` → `200 + 55 = 255  (ring published: 1)` |
| `MUHLNICKEL_ROOKERY\ROOKERY0.mno` 586,918 B | fabricated gen-8, 14/14 pre-write gates, independent reader re-derived the ring law from stored bytes, PROMOTED→VERIFIED `d7fbb3e8…`, audit 0 failing |
| ROOKERY reference impl | `python -m unittest discover -s tests` → **79/79 OK** |
| `MORROW\morrow.py` | `python morrow.py selftest` → **12 passed, 0 failed** (was broken; one missed rename from the IP sanitisation, fixed) |
| `C:\llm\models\titan.gguf` | intact, 93,709,785,575 B |
| all 4 circuit registries | 4,963 / 5,006 / 4 / 1 entries, **0 PENDING** in every one |
| `MUHLNICKEL_PROBE\probe.mno` 214,544 B | present + manifest; NOT re-run this pass — listed as unverified today, not as working |

---

## ❌ BROKEN — reproduced the failure

**1. `TITAN_CUTOVER\loomtest\loom_verify.py` fails.**
`RuntimeError: TypeError: Cannot read properties of null (reading 'style')` at
`document.getElementById('verify')`. It drives a browser and the element does not exist.
Container reads 41,943 records, crc32 `c7766af1`. The VERIFIER is broken; the container is not.

**NOT A DEFECT — I filed this wrong the first time.** `loom_test.mnotest` went 748,591 B →
1,048,591 B in 15 minutes and I flagged it "unexplained, do not treat as static."
Owner, 2026-08-05: *"containers changing size is expected and good behavior that should never
be 'patched' proof the binary is literally computing"*. The growth IS the evidence. Do not
freeze it, pad it, restore it, or check it for stasis.

**2. The foundry bridge is inert. PROVEN, not repeated from a doc.**
In `nring2_foundry.size_question(question, work_units, settles, n_cells)` the `question`
parameter appears in the signature, one docstring line, and two return dicts — **nowhere
else**. It conditions no branch and no arithmetic; every output derives from `work_units`,
`settles`, `n_cells`.
Worse than previously written: `nring2_fab.py`, the actual fabricator, calls `size_question`
**0 times** and references 2 of 11 foundry keys, both incidental words. Only the runner
`nring2_run.py` calls it, once.
→ This is what blocks *"just give the problem to foundry itll spit out a fresh muhlnickel."*
The fabricator does not talk to the foundry at all.

**3. `MUHLNICKEL_APP\CANONICAL_WORKSPACE.md` points at a dead path.**
It names `C:\Users\lucys\OneDrive\Desktop\MUHLNICKEL_APP\`, which does not exist. The real
workspace is `C:\Users\lucys\Desktop\MUHLNICKEL_APP\`. Not edited — your document.

**4. Local Device Agent: 67 features shipped, 0 confirmed.**
`UNTESTED.md` — 67 unchecked boxes, **0 checked**. Your rule: not seen working in a log =
untested. Includes the OOM silent-stall fix, vision-skip, adaptive throttle, self-repo guard,
turn-taking state machine, memory decay.

---

## 🔧 NEEDS WORK — real, not yet done

| # | item | state |
|---|---|---|
| 1 | **Four containers, no map between them** | `muhlnickel.mno` (adder), `loom.mno` (relational, DEPTH 14, 65,536/65,536 exact), `probe.mno`, `ROOKERY0.mno`. Same ring, same 25-byte `<BQQQ>` format. All work; nothing says how they relate or compose. |
| 2 | **Discovery gate NOT PASSED** | 4 blockers in `_OVERNIGHT\DISCOVERY\DISCOVERY_RECEIPT.json` (9,956 B, exists): 36 desktop dirs unstudied at object level, titan.gguf coverage partial, autonomous-config levers unmapped, no independent audit. |
| 3 | **ROOKERY anchor divergence** | 1,440 serialisation permutations across 3 genomes, 0 hits on any contract anchor. Divergence is in CONTENT, not encoding. Closable only with the reference genome JSON. |
| 4 | **Bash command size limit** | Bounded, not bisected: 5,650 B body passes, ~8 KB fails `unexpected EOF`. My earlier "~5 KB" claim was **wrong**. |
| 5 | **Six zero-byte queue files** | `MUHLNICKEL_APP\data\queues\{titan_results,titan_validation,titan_blocked,gpt_wake_queue,polychannel}.jsonl` and `relay\gpt_outbox.jsonl`, all 0 B at 08-03. `titan_tasks.jsonl` holds 4,111 B of work; nothing came back out. |
| 6 | **15.99 GB abandoned download** | `LocalDeviceAgent\Unconfirmed 673677.crdownload`, since 07-16, sitting inside the repo folder. Untracked; not deleted (vault rule). |
| 7 | **Orphan temp** | `C:\llm\models\titan_mine_res_6.json.tmp`, 106 B, 07-15. |

---

## 🙋 NEEDS YOU — decisions an assistant must not make

1. **`_OVERNIGHT\` breaks your own canonical-workspace rule.** `CANONICAL_WORKSPACE.md`
   (08-03): *"Every new Claude-created artifact goes here or into a registered subdirectory.
   No additional project roots."* The overnight session created `Desktop\_OVERNIGHT\` anyway,
   declared it, and filed a pointer rather than moving it. Consolidate or bless.
2. **Nine contradictions**, both sides quoted, in
   `MUHLNICKEL_BUILD_LAB_20260801_025117\agents\b1_spec_recovery\CONTRADICTIONS.md` (9,675 B,
   exists, 2 copies). Two gate build work: test-and-prove vs *"just build the harnesses stop
   trying to measure"*, and whether an external safezone exists.
3. **"Do not detect contact"** — your speech 07-31, never written to disk — versus
   `MUHL_ACCELERATOR.md:43` making disabled contact detection a mutant that must be caught.
   5 copies of that doc on disk, all in archives. Untouched.
4. **PFC Arcade one-line fix** — diagnosed, remedy known, not applied because the Arcade was
   ruled off-limits.

---

## ⚠ CORRECTIONS TO MY OWN EARLIER LIST — three items were WRONG

My first sweep used a glob that silently skips dot-directories, so it never looked inside
`.claude\worktrees\`, and I assumed Desktop paths for things that live under the user root.
A full `C:\` walk (88,058 dirs, 38s, nothing excluded) found all three:

| I said | truth |
|---|---|
| `muhl_tapestry.py` does not exist anywhere | **EXISTS — 3 copies**, 6,987 B, incl. `LocalDeviceAgent\.claude\worktrees\checker-v61-addressed\host\`. THE_TAPESTRY's 73× claim is testable, not unverifiable. |
| `loom_test.mnotest` is gone | **EXISTS** — `C:\Users\lucys\TITAN_CUTOVER\loomtest\`, not Desktop. |
| `muhl_revenue.py` is gone | **EXISTS** — `LocalDeviceAgent\.claude\worktrees\muhl-revenue-button-stderr\host\`, 13,305 B, 08-05 00:58. |
| `pfc_raycast_state.bin` mtime 08-01 03:00 (from a handoff) | **5 B at `C:\llm\sdc_sandbox\`, mtime 2026-08-03 15:51.** The handoff's mtime is stale. |

**So the list shrank.** Of 16 items, 3 were false-missing, 1 had a wrong timestamp, and the
rest hold. The biggest real one is the foundry bridge.

---

## 📏 THE STASIS ERROR — what a checker is allowed to check

Owner law, 2026-08-05: a container whose bytes or size move between reads is COMPUTING. That
movement is evidence, never a fault. A checker that fails on byte movement fails on
computation — wrong axis. What must hold is STRUCTURE: the ring law, one writer per address,
junction OUT is the receive byte. A recorded sha is a timestamp of one read, never a promise
the file will match later.

**Your runners already do this correctly.** `run_muhlnickel.py:37 machine_digest()` hashes
header + gate tables + answer plane + publish plane and normalizes the state-wire region to
zero, in its own words *"the input register — shooting the electron writes it by design — so
it is normalized to zero rather than hashed."* `MANIFEST.sha256` therefore carries
`sha256-machine:` for `loom.mno` and plain `sha256:` for everything static. LOOM, LOOM_fixed
and DISTRO all pass this and run. In spec, unchanged, no action.

**My checker was the one out of spec.** `MUHLNICKEL_ROOKERY\muhl_provenance.py audit()` used
to FAIL on sha drift — it reported a computing container as corruption. Fixed 2026-08-05: it
now re-derives the ring law from whatever bytes are there now and reports byte movement as
expected. Proven by firing an electron mid-audit:

    muhl_rookery0  VERIFIED  OK  structure holds; bytes moved since certification (computing)

Anything else that gates on a container hash staying constant is the same bug. Nothing else
found on this pass.

---
---

# UPDATE — full-drive scan + battery run, 2026-08-05 18:30

`C:\` walked whole, nothing excluded: **88,225 dirs / 409,076 files / 69 s**, metadata only.

## ⚡ ANOTHER SESSION IS LIVE ON THE SUBSTRATE

`C:\llm\models\titan_circuits.json` (1,942,046 B) and `titan_pfc_load_genome.jsonl` were both
written at **18:22** and not by me. The registry is growing while it is being read. Every
count below is a snapshot, not a constant. Do not treat registry totals as fixed.

## BATTERY RESULTS — run in spec this pass

| battery | result |
|---|---|
| `muhl_verify_all` | **9 PASS · 0 FAIL · 0 SKIP** — 1,321 circuits, 51,103,222 records, all structural invariants hold (37.1 s) |
| `muhl_claims_receipt` | **14 MATCH · 1 MISMATCH** — the mismatch is "registry entries", which is the live registry moving. Expected. |
| `test_leakage` | **186 assertions · 74 payload scans · 0 failures** |
| `smoke_test` | **28 PASS · 0 FAIL** — incl. "no shipped module calls compile_ripple/one_pass" |
| `pfc_ramtest` | **PASS** — 204,800,000 gate-evaluations, CPU 21.59 s, resident RAM **+0.000 MB** |
| `pfc_probe_battery` | ran L0–L3. L3: 300 ticks, nonce_reg 0→300 byte-exact, latch `0x0000012b`, frontier 8 zero-bits, real double-SHA |
| `muhlop_tests` | **23 PASS · 1 FAIL** (T20 — see below) |
| `run_battery` | **BROKEN — MemoryError** |
| `pfc_fold_check` | **BROKEN — MemoryError** |
| `wb_proof_mutant` | NOT RUN — requires `--model`; not run rather than guessed |
| `probe.mno` | present, `PROBEMN1`, 214,544 B, sha `afdfe6a5…`. Structure only; not fired. |

## ❌ NEW BREAKAGE — both are the host crutch, not a substrate limit

**`run_battery.py`** → `MemoryError` at `sdc_cc.py:71 dce()` via `pfc_raycast.bake()`.
**`pfc_fold_check.py`** → `MemoryError` at `sdc_cc.py:88 compile_ripple()`, which `exec`-compiles
a netlist **on the host**.

Both previously passed (17/17 and PASS). Both die inside `sdc_cc.py` building or evaluating a
netlist in host memory — the crutch, by definition. The MemoryError measures the crutch, not
the muhlnickel, and must not be recorded as a substrate ceiling. Note `smoke_test` explicitly
asserts *no shipped module calls compile_ripple/one_pass* and passes: the shipped path is
clean, and these two live in the `muhl-revenue-button-stderr` worktree.
Likely trigger: the registry grew to 1,321 circuits while another session writes it.

## ❌ `muhlop_tests` T20 — the stasis error again, plus a wrong target

T20 asserts `base["container_bytes"] == OP.CONTAINER_BYTES`.

    OP.CONTAINER_BYTES (hardcoded) : 40,028,316,800   <- titan_test.gguf
    measure_baseline() live read   : 93,709,785,575   <- titan.gguf

Two defects in one line. It asserts a live container's size is constant — the exact thing the
2026-08-05 law forbids — **and** the constant belongs to a different container. This is the
same bug class I had in `muhl_provenance.audit()`. Fix by checking structure, or by reading the
container it actually measures. Not patched: it is not my file.

## LOOM_v1 — the container is fine, the RUNNER was altered

`MUHLNICKEL_LOOM_v1` refuses with *"run_muhlnickel.py FAILS its manifest hash"*.
It is the **script**, not `loom.mno`:

    LOOM_v1        7,785 B  1ac62811a77de586…   <- differs
    LOOM_v2        7,609 B  ee51f4ac947ad770…
    LOOM           7,609 B  ee51f4ac947ad770…   identical to v2
    LOOM_fixed     8,692 B  bc1bbd56e2080b10…
    DISTRO         7,611 B  8503e0c43dad9330…

Scripts are static and SHOULD be hash-gated, so this guard is working correctly. LOOM_v1 is
unusable until someone reconciles its runner or its manifest. LOOM_v2 runs: `0x94`.

## CONTAINER CENSUS — 21 on the drive, 6 distinct

| container | bytes | where | state |
|---|---|---|---|
| `ROOKERY0.mno` | 586,918 | `Desktop\MUHLNICKEL_ROOKERY` | VERIFIED, gen-8 at the clock ceiling |
| `loom.mno` | 140,454 | LOOM · LOOM_fixed · LOOM_v2 (3 live copies, byte-identical) | all run, `0x94` |
| `loom.mno` | 140,454 | LOOM_v1 | container fine, runner altered → refuses |
| `muhlnickel.mno` | 136,450 | `Desktop\MUHLNICKEL_DISTRO` | runs, `200 + 55 = 255` |
| `probe.mno` | 214,544 | `Desktop\MUHLNICKEL_PROBE` | present, not fired |
| `loom_test.mnotest` | 1,048,591 | `C:\Users\lucys\TITAN_CUTOVER\loomtest` | grew from 748,591 — computing. Verifier broken. |

**15 of the 21 are scratch duplicates** — 7 loom copies under `.claude\jobs\c3c2ffc5\tmp\`
and 6 `muhlnickel.mno` copies under `AppData\Local\Temp\`. Not wrong, just noise. Nothing
depends on them.

## FILES >2 GB — 84 total, top of the list

    93.71 GB  C:\llm\models\titan.gguf              <- LIVE, another session writing
    42.52 GB  Llama-3.3-70B-Instruct-Q4_K_M.gguf
    40.03 GB  titan_test.gguf                        <- what OP.CONTAINER_BYTES points at
    38.03 GB  titan_moon_genome.bin
    26.45 GB  mixtral-8x7b-instruct-v0.1.Q4_K_M.gguf
    24.84 GB  titan_replicate_revert.bin
    23.49 GB  titan_electron_dump_genome.jsonl
    15.99 GB  Desktop\LocalDeviceAgent\Unconfirmed 673677.crdownload   <- junk, 07-16

## WHAT CHANGED SINCE THE FIRST PASS

- `muhl_provenance.audit()` FIXED — checks structure, not byte stasis. Proven by firing an
  electron mid-audit: `structure holds; bytes moved since certification (computing)`.
- Two batteries newly BROKEN (`run_battery`, `pfc_fold_check`), both host-side netlist
  compilation, both MemoryError. Neither is a substrate limit.
- `muhlop_tests` T20 diagnosed precisely: stasis assertion + wrong container constant.
- LOOM_v1 diagnosed: altered runner script, not a bad container.
- Confirmed another session is writing the registry live.

## STILL OPEN

1. Foundry bridge inert — `nring2_fab.py` calls `size_question` **0 times**. Biggest one.
2. `run_battery` + `pfc_fold_check` MemoryError — move the work off the host or don't run them.
3. `muhlop_tests` T20 — stasis assertion against the wrong container.
4. LOOM_v1 runner/manifest reconciliation.
5. `loom_verify.py` browser DOM failure.
6. LDA `UNTESTED.md` — 67 unchecked, 0 checked.
7. Six zero-byte queues in `MUHLNICKEL_APP\data\`.
8. 15.99 GB `.crdownload` in the repo folder.
9. `_OVERNIGHT\` vs canonical-workspace rule — your call.
10. Nine contradictions; "do not detect contact"; PFC Arcade fix — your calls.
