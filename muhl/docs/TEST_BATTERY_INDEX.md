# TEST BATTERY INDEX — the complete recovered, authenticated battery
**Recovery run: 2026-07-29 (afternoon), BRYCESLAPTOP, Ryzen 5 7520U / 8 GB, Python 3.12.10.**
Report-only directory. Nothing in the project was modified: no test, fixture, threshold, expected output,
spec, preflight, measurement, workload, build, or session evidence was touched. Evidence labels used
throughout: `OBSERVED` / `TESTED` / `HISTORICAL` / `NOT_YET_LOCATED` / `UNRESOLVED` / `INFERENCE`.

> **⛔ STANDING WARNING (propagate to every future session): DO NOT RUN `git gc` OR `git prune` on
> `LocalDeviceAgent`.** Two dropped stashes (`4f8ee36`, `f0b150c`) and pre-amend checkpoints survive only
> as unreferenced git objects; gc/prune destroys them permanently. (HISTORICAL, git fsck.)

---

## 1. WHERE THE BATTERY LIVES (absolute paths)

| What | Path | Status |
|---|---|---|
| **Master catalog (run of record 2026-07-29)** | `C:\Users\lucys\OneDrive\Desktop\LocalDeviceAgent\KEEPCURRENTALLTESTS.md` | UNTRACKED in git — highest loss risk. Byte-identical copies preserved at `C:\llm\RECOVERY_CANONICAL\tests\` and `...\evidence\at_risk_untracked\root\`. sha256 `4AF90BE729EC1B79B7DD9AB853C6C211D1DC7CD91A1C5AA955A467158293120C` |
| **Canonical battery runner (17-row, current line)** | `C:\Users\lucys\OneDrive\Desktop\LocalDeviceAgent\host\run_battery.py` | sha256 `9224102FC7D98E6E24B9946F5F5C14D4B021C3D9010C2309C06FB4A90AF4C5FA` · git blob `eb66fb7` at HEAD `be560f4` |
| **Superset battery runner (21-row, stranded branch)** | `...\LocalDeviceAgent\.claude\worktrees\muhl-osc\host\run_battery.py` (branch `muhl-rename-osc`) | sha256 `9BC54F1C0B8D3A39A0AB4391781B304803D61D932794A64320AF197CE68B2F26` · git blob `5799210` at `78ef0f7` |
| Battery #1 (12 suites, 34 checks) | `...\LocalDeviceAgent\host\muhl_test.py` | sha256 `0FA510AC…C285F14A` |
| Battery #2 (15 tests incl. tests-the-tests) | `...\LocalDeviceAgent\host\muhl_test2.py` | sha256 `E37C96C0…74802998D` |
| Spec enforcer (57 live rules, current line) | `...\LocalDeviceAgent\host\pfc_preflight.py` | sha256 `E71F7B59…8AB5D95A0A6` |
| Spec enforcer (60 live rules, strictest, branch) | `...\worktrees\muhl-osc\host\muhl_preflight.py` | sha256 `B9EA4DA5…1AA146DC` — enforces `docs/OWNER_RULES.md` via V62 |
| **OWNER_RULES.md (R1–R20)** | `...\worktrees\muhl-osc\docs\OWNER_RULES.md` — exists in EXACTLY ONE checkout | copy at `C:\llm\RECOVERY_CANONICAL\components\docs\OWNER_RULES.md`, sha256_16 `da9bc8d290c11a45` |
| All 47 named claim/instrument scripts | `...\LocalDeviceAgent\host\` (per-file hashes: `raw_outputs\..` + §5 of `TEST_PROVENANCE.md`) | ALL LOCATED — none missing |
| Engine fleet (73 self-verifying engines) | `C:\llm\muhl_builds\` (superset) mirrored at `C:\Users\lucys\OneDrive\Desktop\Titan\engines\` (60 files, 59 byte-identical, 1 stale: `muhl_life.py`) | OBSERVED |
| The build under test | `C:\llm\models\titan.gguf` — 40,028,316,800 bytes (NOTE: `models\` subdir; `host/pfc_paths.py` resolves it; older docs say `C:/llm/titan.gguf` — stale) | sha256 `71DC56056A3AB34B3D215BA8A216F3C81C16CCDD38AA52FB38732BD2B4A7C643` (pre AND post run — see §4) |
| Circuit registry | `C:\llm\models\titan_circuits.json` (802 entries) | sha256 `FF9B4A47…3EE96E30` at 15:22 |
| White Box (hard dependency, SINGLE COPY) | `C:\llm\sdc_sandbox\sdc_cc.py` — in NO git repo | sha256 `3A64FD4A65FE47A142029F592ECE45657EA2DC87F5576D3131DFBC1EC44AB6D3` — **single point of failure, back it up** |
| Prior recovery corpus (session evidence — protected) | `C:\llm\RECOVERY_CANONICAL\` (LEDGER.jsonl, git_forensics, integrity_audit, operator_statements, ablation results) | do not modify |
| This recovery's raw run evidence | `C:\Users\lucys\OneDrive\Desktop\RECOVERY_REPORTS_TEST_BATTERY\raw_outputs\` | 16 runs, exit codes + full stdout |

## 2. THE BATTERY, BY THE NUMBERS (what "at least 44 tests" resolves to)

The count ≥44 is real and multiply satisfied (OBSERVED, KEEPCURRENTALLTESTS.md + prior-session master runner):
- **Category A — claim-demonstration tests: 36 rows** (each verdicts against an independent reference).
- **Category B — instruments: 12** (measurements, not verdicts).
- **Category C — experimental/UI/preconditioned tools: 15–16** (never scored as claims).
- The prior sweep's master runner (`jobs\b525e703\tmp\run_all_tests.py`) enumerates **66 commands** (A=40/B=11/C=15).
- Within single files: `muhl_test.py` = **34** checks; `muhl_test2.py` = **15**; preflight = **57 live rules** (60 on branch).
- The four "44"s in the corpus are distinct things — see `TEST_INTEGRITY_AUDIT.md` §5. **"44" is never a test count.**

## 3. THE AUTHENTICATED COMMANDS (run these; env in `HISTORICAL_TEST_COMMANDS.md`)

From `C:\Users\lucys\OneDrive\Desktop\LocalDeviceAgent`, with `PYTHONUTF8=1` (and/or `PYTHONIOENCODING=utf-8`):
```
python host/run_battery.py            # 17 rows — canonical §3 battery
python host/muhl_test.py              # 34 PASS expected
python host/muhl_test2.py             # 15 PASS expected (t11 = tests-the-tests)
python host/mafab_laws.py --verify    # ALL LAWS REPRODUCED
python host/pfc_space.py --selftest   # 4/4 mutants killed
python host/pfc_docaudit.py --selftest# 4/4 mutants killed
python host/pfc_inspect.py pfc_cpu32  # 7,403-gate CPU header
```
Full 64+-command catalog with per-command safety flags: `HISTORICAL_TEST_COMMANDS.md`.
**Never run without owner say-so:** anything network-touching (`sdc_checker.py`, `pfc_ceiling_test.py` — has a
hidden live stratum socket, `pfc_fire.py`, `pfc_btc_live.py`, live fire of any kind), standalone `revert`
commands (destructive by design), `pfc_move_circuit --move`, `fab_*.py` (fabrication, writes titan.gguf).

## 4. THIS SESSION'S RE-RUN — the battery reproduces (TESTED, 2026-07-29 ~15:20–15:50)

| Run | Where | Result | Exit | Raw output |
|---|---|---|---|---|
| `run_battery.py` (17-row) | main checkout | **17/17 passed** | 0 | `raw_outputs\main_run_battery_17row.txt` |
| `muhl_test.py` | main | **34 PASS · 0 FAIL** (187 s) | 0 | `raw_outputs\main_muhl_test.txt` |
| `muhl_test2.py` | main | **15 PASS · 0 FAIL** (80 s) | 0 | `raw_outputs\main_muhl_test2.txt` |
| `pfc_inspect.py pfc_cpu32` | main | PFCTYPED (549,7954,**7403**,549) | 0 | `raw_outputs\main_pfc_inspect_cpu32.txt` |
| `mafab_laws.py --verify` | main | **ALL LAWS REPRODUCED** | 0 | `raw_outputs\main_mafab_laws_verify.txt` |
| `pfc_space.py --selftest` | main | 4/4 mutants killed | 0 | `raw_outputs\main_pfc_space_selftest.txt` |
| `pfc_docaudit.py --selftest` | main | 4/4 mutants killed | 0 | `raw_outputs\main_pfc_docaudit_selftest.txt` |
| `pfc_serial_audit.py` | main | ran (instrument, no verdict) | 0 | `raw_outputs\main_pfc_serial_audit.txt` |
| `run_battery.py` (21-row) | muhl-osc worktree | **17/21 — 17 classic rows pass; 4 tick rows REFUSED by V63 rule-integrity gate** (see audit §4) | 1 | `raw_outputs\wt_run_battery_21row.txt` |
| `muhl_test.py` | muhl-osc worktree | **34 PASS · 0 FAIL** (193 s) | 0 | `raw_outputs\wt_muhl_test.txt` |
| `muhl_test2.py` | muhl-osc worktree | **15 PASS · 0 FAIL** (76 s) | 0 | `raw_outputs\wt_muhl_test2.txt` |
| `muhl_turing.py` | `C:\llm\muhl_builds` | exact (BB verdicts) | 0 | `raw_outputs\mb_muhl_turing.txt` |
| `muhl_ecc.py` | `C:\llm\muhl_builds` | ALL PASS (exhaustive) | 0 | `raw_outputs\mb_muhl_ecc.txt` |
| `muhl_reason.py` | `C:\llm\muhl_builds` | pass | 0 | `raw_outputs\mb_muhl_reason.txt` |
| `muhl_turing.py` / `muhl_ecc.py` | `Desktop\Titan\engines` | identical results (hash-identical files) | 0 | `raw_outputs\ti_*.txt` |

**Build integrity proven:** titan.gguf SHA-256 **before** the battery == SHA-256 **after** the battery ==
`71DC56056A3AB34B3D215BA8A216F3C81C16CCDD38AA52FB38732BD2B4A7C643` (40,028,316,800 B). The battery's
bake→verify→revert rows are net byte-exact on the real 40 GB build. (`raw_outputs\titan_gguf_sha256_{PRE,POST}.txt`)
Same-day corroboration: the sibling session's independent run at 15:08 also read **17/17**
(`C:\llm\RECOVERY_CANONICAL\tests\battery_run_of_record.txt`), and three prior 17/17 logs exist in
`C:\Users\lucys\.claude\jobs\{a9cbb2b3,fcde8276,b525e703}\tmp\` (HISTORICAL).

## 5. OPERATOR-APPROVAL EVIDENCE (verbatim, sourced)

- `KEEPCURRENTALLTESTS.md:8-10` — "**Run of record:** 2026-07-29, on the owner's box … Every command below was
  executed exactly as written — no test was edited, patched, or re-argued." (Assistant-authored on the owner's
  box under his direction; no doc claims Bryce personally typed the commands.)
- `docs/PFC_PROOF_REPORT.md:4` — "Re-run again 2026-07-26 via `python host/run_battery.py`: 17/17 rows passed."
- Owner (session 894de29b, 2026-07-29): "**I AM ORDERING YOU TO RUN EVERY SINGLE TEST ON MY PC**" — the sweep
  that produced the 16/17 fresh-registry reading.
- Owner-directed grounding: `CLAUDE.md:91` (07-20), `docs/PFC_GROUNDING.md` 6-test table.
- `OWNER_RULES.md` R20: a measured number is an achieved ceiling — corrections only improve it.

## 6. NOT_YET_LOCATED — referenced by evidence, not found in any searched location

Every named battery entry point **was located**. The residue (referenced in transcripts/docs, absent from the
7 canonical dirs + both worktrees + clone + sandbox + engines + job scratch):

| Name | Evidence it existed | Notes |
|---|---|---|
| `pfc_mine_clk.py` | handoff memory §10 ("the clocked machine pfc_mine_clk, clk_bit = input wire 928") | function exists inside `pfc_mine_check.py` flow; standalone script NOT_YET_LOCATED |
| `muhl_battery.py`, `muhl_cavity.py`, `muhl_win_surface.py` (07-28 osc variants) | job logs `jobs\a9cbb2b3\tmp\{bounce,cavity,surfaces,gain_hunt}.log` | outputs survive; 07-28 scripts NOT_YET_LOCATED (a NEWER `muhl_win_surface.py` 07-29 IS located in grounding-doc + RECOVERY_CANONICAL) |
| `sdc_os_sdc.py` | `CLAUDE.md` runtime spec | **owner-directed deletion 2026-07-19** ("Never build its like again") — documented removal, not a loss |
| `pfc_life.py`, `test_gates.py`, `wf_yourfile.py`, etc. | prose mentions only | INFERENCE: prose shorthand (`pfc_game.py life`, placeholder names), not real files |

Cross-agent correction recorded: `muhl_accelerator/collider/halt_latch/systolic_fold/miner_systolic/`
`selfrouted_loop/golomb_search/resident_probe` and friends **ARE located** — `...\worktrees\grounding-doc\host\`
and `C:\llm\RECOVERY_CANONICAL\components\host\` (a transcript-mining pass that skipped those two locations
had wrongly listed them missing).

## 7. FOR THE NEXT SESSION (fastest correct path)

1. Read this file, then `TEST_INTEGRITY_AUDIT.md` (the verdicts), then `HISTORICAL_TEST_COMMANDS.md` (env).
2. Ground with one command: `cd C:\Users\lucys\OneDrive\Desktop\LocalDeviceAgent && set PYTHONUTF8=1 && python host/run_battery.py` → expect 17/17 (16/17 only on a freshly-reverted registry — row-2 lazy-bake ordering, see audit §2).
3. The 21-row superset needs an owner decision (V63 grant or rule restore) before its 4 tick rows will fire — do not force it.
4. Never `git gc`/`git prune`; never commit as Claude; KEEPCURRENTALLTESTS.md is untracked — committing it (owner's call) would close the biggest loss risk.
