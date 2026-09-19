# Cross-lane reproducibility audit

Runs each lane's own documented commands twice, in separate processes, and
byte-compares the results.

Python 3 standard library only. No network. Nothing runs against the tree
itself.

## Method

For every lane matching `--pattern`:

1. Extract `python3 …` commands from fenced code blocks in the lane's
   `README.md`. Invocations are not invented.
2. Copy the lane twice into temporary directories with different absolute path
   lengths.
3. Run the command in copy A with `PYTHONHASHSEED=0` and in copy B with
   `PYTHONHASHSEED=1`.
4. Byte-compare the whole resulting tree of each copy.

Two separate processes with different hash seeds are required: Python
randomises string hashing per process, so a program that iterates a `set` and
writes the result emits a different order in a different process, while
re-running inside one process is byte-identical every time. Different absolute
paths surface embedded working directories. Running twice surfaces embedded
clocks.

Absolute path arguments (`--out /tmp/report.json`) are rewritten into
`_audit_redirect/` inside each copy, so the two runs do not share one
destination. Every substitution is recorded in the result.

## Verdicts

| verdict | meaning |
|---|---|
| `REPRODUCIBLE` | every artifact byte-identical across seeds and paths |
| `VARIES` | at least one artifact differed, or the two runs disagreed on their exit code; differing files are named and a cause is classified |
| `FAILED` | the documented command exited non-zero, with stderr, and wrote nothing new |
| `TIMEOUT` | the documented command did not finish |
| `SKIPPED` | test suite, server, shell pipeline, or script not present in the lane |
| `UNKNOWN` | no runnable documented command was found. Not a pass. |

A lane's verdict is the worst verdict among its commands, ignoring `SKIPPED`.
A lane whose commands were all skipped is `UNKNOWN`, not `REPRODUCIBLE`.

A non-zero exit is not by itself a failure: a checker that exits 1 because it
found problems is behaving correctly, and its artifacts are still compared. The
two runs disagreeing about the exit code is reported as `VARIES`.

Each `FAILED` result carries a `probable_owner`:

- `harness` — an absolute path was redirected and the command expected the
  original shape, or the command reads above its own lane and this audit copies
  lanes in isolation.
- `environment` — a dependency is not installed in this container.
- `lane` — the command as documented did not run.

Difference causes are a **list** per file, not a single label — a file can be
both path-derived and clock-derived, and reporting only the first found loses
the other: `ordering_like` (same lines, different order — the hash-seed class),
`timestamp_like`, `duration_like`, `absolute_path_like`, `length_differs`,
`binary_or_unreadable`, `unclassified`, `nondeterministic_exit`.

Every differing file also carries `sample_differences`: the actual differing
line pairs, truncated. `unclassified` is never the end of the story — whatever
the classifier concludes, the reader gets the bytes.

Path detection compares the output against the copy root, the workroot above
it, and both basenames. Two defects in the first version of this classifier are
pinned by `ClassifierRegressionTests`: it compared only against the copy root
(`<workroot>/lane`) while real output embeds the workroot or its basename, and
its numeric pattern ended in `\b`, which can never match scientific notation
(`5.290003173286095e-07`). Both produced `unclassified` on real artifacts.

## Run it

```bash
cd revenue/agent_ops/repro_audit

python3 repro_audit.py --tree ../.. --pattern 'uiowa_rfq_18649_*' --out sample
python3 repro_audit.py --tree fixtures --pattern 'lane_*'
python3 -m unittest -v test_repro_audit
```

Flags: `--tree`, `--pattern`, `--timeout` (default 90s per command), `--limit`,
`--skip`, `--out`. Exit code is 1 when any lane is `VARIES`.

## Fixtures

`fixtures/lane_deterministic/` and `fixtures/lane_nondeterministic/` are
synthetic miniature lanes. The second writes a wall-clock stamp, its own
absolute path, and unsorted set iteration. `test_the_audit_can_go_red` asserts
the audit flags it and classifies the causes.

## Sample run

`sample/audit.json` and `sample/audit.md` are the output of a run over
`revenue/uiowa_rfq_18649_*` at the time of commit. Lane counts move as seats
land, so the numbers in that file are a timestamped sample, not a standing
result.

## Scope

This reads and copies lanes. It does not write into any lane, does not run any
lane's test suite, and contains no University data. Running each lane on a copy
rather than in place is required, not stylistic: a number of lanes contain
`shutil.rmtree` and `subprocess` calls.

## UNKNOWN

- Whether a `VARIES` result is a defect or intended. A benchmark that records
  durations legitimately varies between runs. The audit reports the differing
  files and the classified cause; it does not decide which lanes are supposed
  to be reproducible.
- The correct invocation for a lane whose README documents no runnable command.
  Those stay `UNKNOWN`.
- Whether a `FAILED` result attributed to `harness` would pass when run by hand
  with its original absolute paths and sibling lanes present. Not verified here.
