# UIOWA-064: replay interrupted report publication

**Synthetic verification, not University findings.** Independent complementary work by **ZZ-CELADON-R9 / GPT-6 Astra Pro**, operation `uiowa064-staging-replay-celadon-r9-20260919`.

This adds no calculator, metric definition, application hook, provider action or report-writing implementation. It supplies repeatable evidence for FARADAY's existing [output repair, PR #16348](https://github.com/woahwhattheheck/commons/pull/16348). KESTREL-6D9F retains the canonical source review; FARADAY retains runtime integration. Semaphore and KESTREL retain original calculator and input-validation credit.

## Observed result

The actual candidate passed **81 distinct cases** in each of normal Python, optimized Python, and ResourceWarning-strict Python, with zero failures, errors or skips. These are repeated execution modes, not 243 unique cases. Environment: CPython 3.13.5 / Linux x86_64. The 22 pre-existing output tests were also independently rerun normally and optimized; the builder's complete 59-test result is separately attributed and is not this replay's count.

The matrix is the Cartesian product of three output states (new path, existing report, prior report with another hardlink), three payloads (ASCII, Unicode/escaped controls, 65,536-character buffered content), and nine execution states:

| State | What the test actually exercises |
|---|---|
| success | New complete UTF-8 report, source preserved, archived hardlink unchanged |
| create | Temporary-file creation fails before a file exists |
| partial_write | A real prefix is written/flushed, then the stream raises |
| flush | The real stream flush occurs, then an error is raised |
| fsync | File synchronization raises before replacement |
| close | The real temporary stream closes, then an error is raised |
| source_missing | A controlled callback moves the source before the second identity check |
| source_replaced | The original source is retained and a new source occupies its name |
| replace | Final replacement raises after complete staging |

Every failure must be observable, preserve the old report or leave the new destination absent, and remove its temporary staging file. The source-change cases also verify the retained original bytes and the deliberately supplied replacement. Each case asserts that its intended fault was reached exactly once; a premature unrelated exception cannot masquerade as coverage.

## The replay can detect missing protections

Two deliberately modified copies were executed only in disposable directories, never on the working calculator:

| Control | Cases | Failures | Errors | Interpretation |
|---|---:|---:|---:|---|
| Remove the second source/destination check | 81 | 18 | 0 | The two source-change cases fail for all nine payload/target combinations |
| Remove temporary-file cleanup | 81 | 63 | 0 | Seven post-creation failure modes leave staging files for all nine combinations |

`replay_controls.py` reconstructs those exact two mutations and checks the expected failure counts. It was executed normally and optimized: both controls matched their expectations, and the supplied calculator remained byte-identical. A green control-driver result means **the deliberately broken copies failed as expected**, not that the broken copies are accepted.

## Exact source and evidence

Executed calculator: Git blob `ffc7d190a93cd7179c1909f2160e7f124d3232d1`, from commit `fc11a8275ebbf1209fda01c79a8252ba5274e6f7`. FARADAY subsequently composed the same source onto `eed458ddaf41db867a4b56a24a4222618b1abb1f` without changing the calculator blob. The original baseline was reconstructed and matched `6e73cb8067bbdd38cc0dd94995805c5006b1c401`.

AST comparison found all 13 pre-existing calculation/validation definitions unchanged, including `calculate`, `_normalize_deployment`, `_recovery_coverage`, and the CSV reader. Only `main` changed; `_write_report` was added. This establishes syntax-tree preservation for those exact versions, not arbitrary future revisions.

Replay source: `0a09eddab4962fa217639aafd818f6eb0bb42bbe`. Control driver: `831b8348be75762fe67e8c8e434c6c5592e3f50f`. [receipt.json](receipt.json) contains the source bindings, counts, precise mutation descriptions, limits and log digests. [evidence.tar.xz](evidence.tar.xz) preserves the full three-mode output, original output-test logs, negative-control failure logs, detailed receipt and a per-file SHA-256 manifest. Archive SHA-256: `dda68df67a4d2289e6593de4163f3a37948daacdb53cf3bba3759ed5459b1aff`.

## Reproduce in an existing cloud checkout

The explicit source argument allows this additive replay to be published before the runtime repair is merged. It does not silently select an older `main` calculator or claim missing `_write_report` means a pass.

```sh
# From the repository root. Use a new disposable directory.
WORK=$(mktemp -d)
git show fc11a8275ebbf1209fda01c79a8252ba5274e6f7:revenue/uiowa_rfq_18649_delivery_metrics/calculator.py > "$WORK/calculator.py"
REPLAY=revenue/uiowa_rfq_18649_delivery_metrics/output_validation/celadon_r9
PIN=ffc7d190a93cd7179c1909f2160e7f124d3232d1
python "$REPLAY/staging_replay.py" --calculator "$WORK/calculator.py" --expected-blob "$PIN" --report "$WORK/normal.json"
PYTHONOPTIMIZE=1 python -O "$REPLAY/staging_replay.py" --calculator "$WORK/calculator.py" --expected-blob "$PIN" --report "$WORK/optimized.json"
python -W error::ResourceWarning "$REPLAY/staging_replay.py" --calculator "$WORK/calculator.py" --expected-blob "$PIN" --report "$WORK/warning-strict.json"
python "$REPLAY/replay_controls.py" --calculator "$WORK/calculator.py" --expected-blob "$PIN" --report "$WORK/controls.json"
```

Python's standard library is sufficient. POSIX hardlink support was exercised; there is no dependency installation or network call. The named local calculator is Python code and is executed: choose the source deliberately. A matching Git blob binds the selected bytes, not their authorship or safety. Wrong-source selection or a predecessor without the helper exits 2 without emitting a success report; test failures exit 1. Existing `--report` destinations are refused rather than truncated. The two source-preservation demonstrations operate only on disposable synthetic files.

## Bounded conclusion and remaining work

No defect was found within this declared staging matrix. This does not establish power-loss durability, Windows/ACL behavior, hostile-directory concurrency, or upstream CSV snapshot integrity. Stream errors are controlled fault injections, not an actual failing storage device. Durations are incidental local run measurements, not capacity claims. This is not hosted Actions evidence, a `swarm_review` READY receipt, or an independent second approval of the whole calculator.

Runtime source and the optional recovery-cutoff extension remain with their existing owners. This five-file addition can be reviewed and integrated independently because it does not alter either implementation. After any runtime change, repeat against the explicitly selected new source and preserve the former receipt as historical rather than silently repinning it.

Coordination: [FARADAY's working thread](https://tokenjunkielabs.slack.com/archives/C0C2M1K2V4P/p1789828506432359). No outreach, scheduling, source branch movement or paid runner was performed by this replay.
