# Canonical package consistency in existing TITAN CI

The `canonical` job in the existing `titan-selected-projection` workflow consumes the repository's single current package. It checks out the immutable event commit, runs the existing `build_integrated.py --check`, and keeps the event merge and pull-request head identities separate. It never rebuilds the checked-out archive or changes the runtime/configuration.

The existing `test_release_consistency.py` is reused unchanged. Its build, history-preservation and corruption probes run in temporary copies, not against the current package. The new 13-method `test_canonical_binding.py` covers workflow execution and runs the actual finalization block against explicit synthetic filesystem records: failed/skipped/cancelled steps, changed/added/deleted source, bad receipt size/hash/manifest, missing snapshot and truncated output cannot produce a successful result. A stale successful check file cannot override a failed process.

```sh
python3 -B revenue/kaggriculture/cloud-composition-cases/cover/test_canonical_binding.py -v
python3 -B revenue/kaggriculture/cloud-execution-lab/build_integrated.py --check
```

Thirteen local methods pass on workflow blob `0bd60f44fbb87be7e628db29418d5a9597827ae4`. The existing BIRCH `focused` job from workflow `11983ff0e2fea1de4e130ec41104de7ee9efff52` is unchanged. All embedded Python and Bash blocks parse. These are local workflow/receipt tests, not an assertion that the current canonical package passed hosted execution; that result belongs to the PR's actual run.

## Diagnostic artifact

`titan-canonical-check-<run>-<attempt>` contains `SOURCE-SNAPSHOT.json`, `current-check.json`, `current-check.stderr`, the two test logs and `CANONICAL-RESULTS.json`. The snapshot records file hashes, actual checkout, PR head/base, Python and zlib versions. Finalization rehashes the checked sources and records any changed, missing or added file. Bytecode generation is disabled for this job and its inherited subprocesses.

The artifact contains diagnostics only: no copied runtime archive and no second release. A passing result means the existing checker accepted the committed package, the two named test invocations succeeded, and the checked source stayed unchanged. It is not game strength, a one-second runtime guarantee, a submission receipt, or a whole-repository pass. Failures retain their logs and an unsuccessful receipt for the canonical builder; the job does not repair or silently rebuild stale packages.

BIRCH's component suites and ATLAS's combined-report contract remain separate. BROOK owns publication I/O in the existing builder; the canonical builder owns release advancement and root owns submission. No new workflow identity, exporter, branch protection, required-review setting, policy variant, game or seed is introduced.
