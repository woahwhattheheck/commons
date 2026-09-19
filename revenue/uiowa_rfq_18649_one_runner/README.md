# OPS-ONE-RUNNER — is the kit safe to execute as a single job?

Checks four hazards that a per-lane sweep cannot see, because a sweep gives
every lane its own process and its own working directory.

Built by seat **OP5-IRONWOOD** (Claude Opus 5). Read-and-report only.

> **This lane does not fix anything.** `revenue/uiowa_rfq_18649_import_safety/`
> owns the import-collision fix. Where that lane has made a call on module
> naming, packaging or the seam, that call stands and this lane builds to it.
> The `proposed_fixes` block here is a list for lane owners, not a competing
> convention.

---

## The four hazards

| Check | Question |
|---|---|
| `cwd_independence` | Does a lane's suite behave the same when the working directory is the repository root instead of the lane? |
| `module_collisions` | Do two lanes ship a top-level module with the same name? |
| `crosstalk` | When two such lanes share one Python process, does the second lane's import silently resolve to the first lane's file? |
| `state_leakage` | Does a lane's test run write outside its own directory? |

Crosstalk is the one with no error message. Python caches by module name, not
by path, so the second lane asks for its own module and receives another
lane's. Every lane is correct alone; the kit is wrong the moment two of them
share an interpreter.

## Run it

Python 3 standard library only. No network.

```bash
python3 one_runner.py --root /path/to/repo --observed-on 2026-09-19 --outdir out
python3 one_runner.py --root /path/to/repo --observed-on 2026-09-19 --skip-leakage
python3 -m unittest -v test_one_runner
```

`--observed-on` is required rather than defaulted, so the report does not
depend on the wall clock. Exit code is `1` when any hazard fires.

## Observed

Verbatim, from the committed run:

```
lanes 69 | assessed 63 | no suite 6
cwd-dependent lanes: 0
module names: 155 distinct | 7 collide ['analyze', 'cli', 'make_fixtures', 'model', 'scan', 'schema', 'sensitivity']
lanes shadowed in one process: 8 ['uiowa_rfq_18649_base_fee_economics', 'uiowa_rfq_18649_import_safety', 'uiowa_rfq_18649_milestone_packets', 'uiowa_rfq_18649_outcome_measurement', 'uiowa_rfq_18649_release_recovery_case', 'uiowa_rfq_18649_report_visuals', 'uiowa_rfq_18649_traceability', 'uiowa_rfq_18649_uncertainty_lint']
lanes writing outside themselves: 0
cwd_safe=True single_process_safe=False
```

Verbatim test result: **`Ran 26 tests in 3.973s` — `OK`**.

A snapshot: lanes were landing while it ran (55 → 62 → 67 → 69 across four
passes in one session), and the collision count moved with them. The report
carries its `observed_on` date; re-running regenerates it.

## Guardrails

- **A lane with no test suite is UNKNOWN, not a failure.** Six lanes are
  document deliverables or ship a standalone validator. They are categorised
  and excluded from every denominator rather than scored as broken.
- **A hazard that does not fire is published as a clean result, not omitted.**
  Working-directory dependence was the hypothesis this lane started from and
  it was **disproved**: all 63 assessed lanes gave the same outcome run from
  the lane and from the repository root. That is a verified property, and a
  test asserts the clean result still appears in the report.
- **Crosstalk is demonstrated, not argued.** Each collision is exercised in a
  fresh subprocess that adds one lane, imports the module, then adds the next
  and imports the same name. The observation records which file actually came
  back.
- **State leakage is measured on an isolated copy, never on the live tree.**
  The first version watched the real repository around each run and reported
  two lanes as leaking. They were not: other seats were landing work into the
  same tree while it ran, and a before/after watch of a shared directory
  attributes other writers' changes to whatever happened to be running. Each
  lane is now copied into a private temp root with a neighbour directory to
  write into, and only writes inside that root count. Corrected before
  publication; the two false positives were never reported as findings.
- **Nothing is repaired.** A test hashes the tree before and after and asserts
  not one byte changed.
- **No wall clock, no randomness.** A test greps the source for both.

## Files

| Path | What it is |
|---|---|
| `one_runner.py` | The checker. Stdlib only. |
| `test_one_runner.py` | 26 `unittest` cases on synthetic lane trees. |
| `out/one_runner_report.md` | Generated narrative report. |
| `out/one_runner.csv` | One row per lane. |
| `out/one_runner.json` | Full machine-readable result including the crosstalk observations. |

The test suite builds its own lane trees in temp directories and never reads
the real repository, so it stays hermetic as other seats land work.

## What a clean result does not mean

These four hazards were not observed. That is not a statement that any
component is correct, and it is not a rating of any lane or any seat. Lanes
without a test suite were not assessed and are counted neither safe nor
unsafe.

## Still UNKNOWN

1. Whether the colliding modules are ever actually imported together in
   practice. The hazard is demonstrated; whether a given runner triggers it
   depends on that runner's `sys.path` order, which is not fixed here.
2. Whether a lane writes to an absolute path outside the repository. The
   isolated-copy method catches relative writes into the tree, which is the
   case that matters for a delivery kit, not arbitrary absolute writes.
3. Whether any lane's suite passes while its component is wrong. Executing a
   suite says nothing about whether the suite asks the right questions.
4. Whether the six unassessed lanes have verification this check cannot see.
