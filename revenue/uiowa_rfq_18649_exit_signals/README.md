# Kit exit signals — a runner contract, a scanner, and a non-invasive wrapper

Ledger item **OPS-EXIT-SIGNALS**. Built by seat **OP5-QUARRY** (Claude Opus 5).

Additive and isolated. **Read-only against every other seat's lane** — nothing here
imports, executes or edits another lane. The scanner parses source; it does not run it.

## The measured condition

Read-only shallow clone of `claude/multi-agent-slack-demo-4ikzfs` at
`03fa2f987df4326ca4db115e24336c220c5b9260`, scanned 2026-09-19, scope
`revenue/uiowa_rfq_18649_*`:

```
lanes=47  entrypoints=115
GATE=37   REPORT_ONLY=69   INDETERMINATE=9
NO_SIGNAL_PATH     65
CRASH_AS_SIGNAL    23
UNRESOLVED_EXIT     9
FALSE_CLEAN         4
```

69 of 115 entrypoints cannot return a non-zero exit code under any input. 4 of those
print failure vocabulary to stdout and exit 0 anyway. A runner records the same result
for those as for a clean run.

Full output: `evidence/kit_scan_20260919.{md,csv,json}`. It is a point-in-time
snapshot of a branch that moves; re-run to get current figures.

### Two corrections, recorded because the first number was published

1. A crude pre-scan grep for `sys.exit(<nonzero literal>)` reported **20 gates / 85
   always-zero over 105 entrypoints**, and that figure was posted to the board before
   `scan.py` existed. It was wrong: it did not resolve `sys.exit(main())` into
   `main()`'s return values, so it counted real gates as report-only.
2. An early version of `scan.py` over-reported `NO_CONTRACT_LINE` by looking for the
   literal string `KIT-STATUS`, which missed tools that emit the line through
   `contract.emit()` — including `audit_kit.py` itself. Caught by the dogfood test on
   its first run.

Both corrections are in `evidence/kit_scan_20260919.json` under `provenance`.

---

## Run it

Python 3 standard library only. No installs, no network.

```bash
cd revenue/uiowa_rfq_18649_exit_signals

python3 audit_kit.py fixtures                 # audit the sample tools
python3 -m unittest -v test_exit_signals      # 35 tests

# reproduce the measurement above against any checkout:
python3 audit_kit.py <path-to>/revenue --lane-prefix uiowa_rfq_18649_ --out evidence

# wrap an existing tool without editing it:
python3 wrap.py -- python3 some_lane/build_kit.py
python3 wrap.py --rule exit_code -- python3 some_lane/build_kit.py
python3 wrap.py --rule stdout_markers --marker FAIL -- python3 some_lane/build_kit.py
```

---

## The contract

| Code | Name | Meaning |
|---|---|---|
| 0 | `CLEAN` | ran to completion; nothing requiring operator attention |
| 1 | `FINDINGS` | ran to completion; found something an operator must look at |
| 2 | `INPUT_ERROR` | could not run: bad arguments, missing or malformed input |
| 3 | `INDETERMINATE` | ran, but could not determine whether there are findings |

Precedence: `INPUT_ERROR` > `FINDINGS` > `INDETERMINATE` > `CLEAN`.

Code 3 exists because this engagement's standing rule is that missing evidence stays
UNKNOWN. `0` means "I checked and it is clean". A tool that could not reach its inputs
has not checked. Collapsing those two into one code is the same error as scoring an
un-inventoried system as zero.

Optionally a tool prints one flat line a runner can grep without parsing prose:

```
KIT-STATUS: code=1 status=FINDINGS tool=audit_kit findings=69 indeterminate=9 note=...
```

---

## The scanner (`scan.py`)

| Class | Meaning |
|---|---|
| `GATE` | a non-zero exit is reachable from the entrypoint |
| `REPORT_ONLY` | no non-zero exit path exists |
| `INDETERMINATE` | an exit value could not be resolved statically |

| Finding | Severity | What it means |
|---|---|---|
| `FALSE_CLEAN` | HIGH | prints failure vocabulary and exits 0 |
| `DEAD_GATE` | HIGH | a non-zero exit sits in unreachable code |
| `NO_SIGNAL_PATH` | MEDIUM | cannot return non-zero under any input |
| `UNRESOLVED_EXIT` | MEDIUM | exit value unresolvable, and no status line |
| `CRASH_AS_SIGNAL` | LOW | non-zero available only via an uncaught exception |
| `RUNTIME_DECLARED_STATUS` | INFO | unresolvable statically, but emits a status line |
| `NO_CONTRACT_LINE` | INFO | a runner must infer meaning from the exit code alone |

Two things deliberately not counted as a signal:

- **A `sys.exit(1)` in unreachable code.** `fixtures/t_dead_gate.py` has one after an
  unconditional `return`. A grep-based check calls that tool gated; it is dead text.
- **An uncaught exception.** `fixtures/t_crash_only.py` exits `1`, the same code as
  the real gate `fixtures/t_gate.py`. From outside, the exit code alone cannot tell
  them apart — only the traceback does. A crash says the tool broke, not that the
  subject has findings.

### Stated limitation

Reachability is **shallow**. It detects statements made dead by an unconditional
terminator earlier in the same block, and resolves `sys.exit(f())` one level into a
same-module function. It is not interprocedural or path-sensitive. Anything it cannot
resolve becomes `INDETERMINATE` — not an assumption in either direction. `FALSE_CLEAN`
rests on a word list (`fail`, `error`, `missing`, `broken`, …) found in printed string
literals; it will miss failure phrased in other words and can flag a tool that prints
those words harmlessly. It is a tripwire on ordinary output, not a proof.

---

## The wrapper (`wrap.py`)

Remediation that respects lane ownership: run an existing tool as a subprocess, read
what it produced, translate it into the contract. **No lane is edited.**

| Rule | Behavior |
|---|---|
| `status_only` (default) | honor a `KIT-STATUS` line; otherwise **`INDETERMINATE`** |
| `exit_code` | operator declares the tool's own exit code is meaningful |
| `stdout_markers` | declared words on stdout mean `FINDINGS` |

The default is `INDETERMINATE`, not `CLEAN`. A tool that emitted no status line and
has no declared rule has told the runner nothing about its subject. A crash is always
translated to `INPUT_ERROR`, never `FINDINGS`.

`audit_kit.py` obeys the same contract it audits: `1` on findings, `2` on a missing
root, `3` when entrypoints could not be resolved. Asserted in the tests.

---

## What is real vs. draft

**Real and runnable now**

- The contract, its precedence order, status-line emission and parsing, including
  refusal of off-contract codes and malformed status lines.
- The scanner, with all seven findings exercised by runnable fixtures, plus an
  assertion that it does not execute or import what it reads.
- The wrapper, all three rules, and the crash-vs-gate distinction.
- The recorded measurement against a real branch, with its provenance and both
  corrections.

**Draft / judgement**

- The four-code vocabulary is a proposal. If the engagement already has a runner
  convention, that one should win.
- The failure-vocabulary word list is a first cut.
- The severity assignments (which findings are HIGH) are a judgement.

## UNKNOWN

1. Whether the delivery kit will be run by a script, a CI lane, or a person reading
   output — which decides whether any of this is needed.
2. Whether seats want to adopt `contract.emit()` in their own lanes or be wrapped from
   outside. Nothing here assumes either; both paths work.
3. Whether the 23 `CRASH_AS_SIGNAL` entrypoints raise on malformed input deliberately
   or incidentally. Not determined; not scored.
4. Whether the 4 `FALSE_CLEAN` entrypoints intend their printed failure to be
   actionable. Flagged, not judged.

## File map

```
contract.py           four exit codes, precedence, KIT-STATUS line emit/parse
scan.py               read-only AST classifier with shallow reachability
wrap.py               subprocess wrapper + three fallback rules; library and CLI
report.py             Markdown / CSV rendering
audit_kit.py          CLI; obeys its own contract
fixtures/t_*.py       one runnable tool per behavior, incl. hostile cases
evidence/             dated snapshot of the real branch, with provenance
test_exit_signals.py  35 unittest cases
```
