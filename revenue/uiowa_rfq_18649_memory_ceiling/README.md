# OPS-MEMORY-CEILING — peak memory per delivered lane

How much memory each lane's tooling needs, measured by running that lane's own
test suite in a fresh subprocess and reading `resource.getrusage(RUSAGE_SELF).ru_maxrss`
from inside it.

Built by seat **OP5-OBSIDIAN** (Claude Opus 5). Complements `OPS-RUN-SWEEP`,
which records whether suites run and how long they take; this records what they
cost in memory. It does not re-measure time and does not build a runner.

Every figure in `results/` was measured on this machine in one run.

## Run

Python 3 standard library only. No network.

```bash
cd revenue/uiowa_rfq_18649_memory_ceiling
python3 -m unittest discover -v
python3 measure_memory.py --revenue ..
python3 mem_probe.py <lane-dir>       # one lane
python3 mem_probe.py --baseline       # bare interpreter
```

## Files

| File | What it is |
|---|---|
| `mem_probe.py` | Runs one lane's suite in its own process and reports peak RSS as JSON on stdout. |
| `measure_memory.py` | Driver across all lanes, summary, report renderer. |
| `test_memory_ceiling.py` | 19 `unittest` tests. |
| `results/MEMORY_REPORT.md` | Generated report. |
| `results/memory_results.json` / `.csv` | Full record. |

## Why a fresh process per lane

`ru_maxrss` is a high-water mark that never falls. Measuring several lanes in
one process would report a running maximum and silently attribute the heaviest
lane's peak to every lane measured after it. A fresh interpreter per lane is
what makes the number belong to that lane. There is a test
(`test_each_lane_is_measured_independently`) that runs a deliberately hungry
lane and then a small one, and fails if the peak leaks forward.

## Measured result

- Lanes found: **71**
- Lanes with a usable figure: **62**
- Lanes without one (UNKNOWN, not zero): **9**
- Bare-interpreter baseline: **13.1 MiB** — every per-lane figure includes this
- Highest peak: **31.4 MiB** (`uiowa_rfq_18649_exit_signals`)

Statuses: 60 `OK`, 2 `TESTS_FAILED`, 9 `NO_TESTS`.

**The kit's tooling is not memory-hungry.** The heaviest lane's suite peaks at
roughly 31 MiB, against a 13 MiB interpreter baseline — so the most any single
lane's tests add is around 18 MiB. Nothing here suggests an operator needs an
unusual machine to run the kit's own test suites.

The two `TESTS_FAILED` lanes were re-run by hand from their own directories to
confirm the failures are real and not an artifact of this harness's working
directory. They are:

- `uiowa_rfq_18649_capability_appendix` — 3 assertion failures in the lane's own
  tests.
- `uiowa_rfq_18649_document_extraction` — 2 errors raised while importing the
  third-party `pypdf` / `cryptography` stack in this container
  (`pyo3_runtime.PanicException`). That is an environment failure, not the
  lane's logic.

Both are recorded as observations for the owning seats. This lane does not edit
them.

## UNKNOWN is never zero

Every path that fails to produce a real measurement reports `UNKNOWN`, and each
has a test driving it:

| Situation | Status | Memory figure |
|---|---|---|
| Lane has no `test_*.py` | `NO_TESTS` | `UNKNOWN` |
| Test module will not import | `COLLECTION_ERROR` | `UNKNOWN` (observed value retained separately) |
| Suite exceeds the timeout | `TIMEOUT` | `UNKNOWN` |
| Probe produced no parseable output | `NO_OUTPUT` / `UNPARSEABLE` | `UNKNOWN` |
| Tests ran and some failed | `TESTS_FAILED` | kept — the code did run |

`COLLECTION_ERROR` exists because of a bug this lane's own tests caught. A test
module with a syntax error does not raise out of `unittest.discover()` — the
loader substitutes a `_FailedTest` placeholder that presents as an ordinary test
error. The lane then reported `TESTS_FAILED` with a small, tidy memory figure
that described an interpreter failing to import a file rather than the lane's
cost: cheap-looking precisely because nothing ran. Load failures are now
detected and their figures withheld.

## What is measured and what is not

- **Measured:** peak RSS and suite duration for each lane's own test suite, on
  this machine in this run, plus the interpreter baseline.
- **The baseline is reported, not subtracted.** The figures stay comparable to
  what an operator would actually see.
- **UNKNOWN — memory under the University's real data volumes.** Test suites run
  on small synthetic fixtures. These numbers are not a prediction of production
  memory and are not extrapolated into one. A lane whose peak tracks input size
  (which UIOWA-095 measured for at least one shape) will not look heavy here.
- **Not a score.** Lanes are sorted by memory so an operator can see the ceiling.
  A higher figure is not a defect, and no lane, seat, or person is ranked.

Read-only with respect to other seats' lanes: it executes their test suites,
which is what those suites are for, and writes nothing into them.
