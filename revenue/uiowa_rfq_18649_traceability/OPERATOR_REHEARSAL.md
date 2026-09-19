# What a clean auditor result actually establishes

A worked synthetic demonstration of OP5-LANTERN's retained UIOWA-093B auditor,
with ZZ-Astra Relay's execution-evidence repair. This guide records an executed
example; it is not a University assessment, release authorization or hosted-CI
result. The executable candidate is [PR #16362](https://github.com/woahwhattheheck/commons/pull/16362),
revision `80303d7178b17695f90b3ba1bc938ecbcbe91a51`. Publishing this Markdown guide
to main does not merge or activate that separate executable candidate.

## Ten cases, one actual auditor

The rehearsal builds ten fixed synthetic lanes in a fresh temporary directory,
invokes the existing auditor as a child process, and checks the returned rows.
The following outcomes were actually observed in normal, `-O` and `-OO` runs.
Run/skip counts are unittest measurements, not assertion counts.

| Synthetic lane | Observed verdict | Run / skipped | What the operator should notice |
| --- | --- | --- | --- |
| clean | CLEAN | 1 / 0 | A discovered test ran successfully; no snapshot mutation was observed. |
| empty | NO_TESTS_EXECUTED | 0 / 0 | An importable test module is not evidence that a test body ran. |
| failed | TESTS_NOT_GREEN | 1 / 0 | The measured assertion failed. Do not relabel it as missing execution. |
| foreign | WRITES_OUTSIDE_LANE | 1 / 0 | A passing test wrote into a sibling lane inside the scratch tree. |
| mutating | NON_HERMETIC | 1 / 0 | A passing test rewrote its fixture from BEFORE to AFTER. |
| no_modules | NO_TESTS | No receipt | No test module was discovered. This is a coverage gap, not a pass. |
| partial | PARTIAL_TEST_COVERAGE | 2 / 1 | One case ran and another was skipped. Preserve both observations. |
| self_sealing | SELF_SEALING | 1 / 0 | The test rewrote the expected digest-shaped value in its manifest. |
| skipped | NO_TESTS_EXECUTED | 1 / 1 | Unittest counted a skipped case; its test body did not run. |
| unknown | TEST_EXECUTION_UNKNOWN | Missing receipt | The imported module exited zero before the runner could record a result. |

The digest example deliberately replaces 64 zeroes with 64 ones. It exercises
the existing changed-digest heuristic; it does not prove that every changed hash
was an integrity check or that a digest authenticates its source.

## Two different meanings of success

The actual rehearsal output includes:

```text
rehearsal_passed=True; auditor_all_clean=False
```

The rehearsal exits zero because all ten *expected* outcomes were observed.
The underlying auditor exits **1** with `--require-clean`, because some lanes
are deliberately defective. Confusing those two exit codes would turn a useful
negative demonstration into a false all-clear.

For ordinary auditor use, the historical default remains available: only a
SELF_SEALING finding makes that default command return 1. Therefore default exit
zero is not a promise of full clean coverage. With `--require-clean`, exit 0
requires a nonempty set of entirely CLEAN results; exit 1 reports an observed
defect; exit 2 reports incomplete, missing or unknown execution without such a
higher-severity defect. Always retain the individual lane and `suite.runs` rows.

## Reproduce the worked example

Use an existing isolated cloud checkout of the pinned executable revision above.
These commands are not instructions to switch a shared worktree or run on the
owner's computer. The files may not yet exist in a main-only checkout.

```sh
python revenue/uiowa_rfq_18649_traceability/rehearse_execution.py
python -OO revenue/uiowa_rfq_18649_traceability/rehearse_execution.py --format json
```

No customer data, API credentials, network call, scheduling or new paid runner is
needed by the rehearsal. It creates only fixed synthetic inputs in its temporary
workspace. In all three executed modes, source and synthetic input bytes were
unchanged after the auditor completed.

The combined test command, from the component directory, is:

```sh
python -m unittest -v test_audit_self_sealing test_audit_execution_evidence test_rehearse_execution
```

Repeat with `python -O` or `python -OO` to test optimization propagation. Actual
Python 3.13.5 container results: **53 tests OK per mode** (27.684s normal, 27.176s
`-O`, 26.757s `-OO`). This is 45 core auditor methods plus eight rehearsal methods,
not 159 distinct methods or a full-repository test. The earlier separate
45-method receipt remains preserved, rather than being relabeled as this run.

[Exact source/log receipt](https://github.com/woahwhattheheck/commons/blob/80303d7178b17695f90b3ba1bc938ecbcbe91a51/revenue/uiowa_rfq_18649_traceability/REHEARSAL_RECEIPT_20260919.json)
and [complete compressed logs and CLI outputs](https://github.com/woahwhattheheck/commons/blob/80303d7178b17695f90b3ba1bc938ecbcbe91a51/revenue/uiowa_rfq_18649_traceability/REHEARSAL_EVIDENCE_20260919.log.gz)
are retained on that revision. Decompress the latter with `gzip -dc`; each
section names its original log or JSON output. The receipt records recovery of
an interrupted combined shell command; no incomplete output is counted as a pass.

## What this does not establish

Copied tests are not a security sandbox. Cooperative test code still has the
filesystem, subprocess and network access allowed by its execution environment.
The sidecar is not an attestation against dishonest test code. CLEAN is limited
to discovered groups and files that the existing snapshot function reads;
snapshot read errors, symlinks and undiscovered tests are not turned into
universal integrity guarantees. Use separate isolation for untrusted suites.

The original sibling-lane copy and fixture-suite exclusion are retained. The
broader donor trace checker, its bundles and the separate canonical traceability
rehearsal are not replaced by this auditor slice.

Original implementation and ten tests: **OP5-LANTERN / Claude Opus 5**.
Initiating manual fixture finding: **OP5-CONTROL**. Execution repair, added
regressions, this operator rehearsal and guide: **ZZ-Astra Relay / GPT-6 Astra Pro**.
The later donor NO_TESTS warning is preserved from blob
`926cd50af9b1c92efb9296b69704198c85d48378`; original test blob
`b9687332defb1d40ee7fead84123b367acfb835b` is unchanged.
