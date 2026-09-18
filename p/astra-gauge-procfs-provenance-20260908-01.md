# Record evaluator procfs sampling outcomes

Operation: `astra-gauge-procfs-provenance-20260908-01`. Coordination claim: Slack `C0BU51F1PL3`, message `1788864328.947759`.

Adds `procfs_sample_status` to future actor reports: unattempted, non-Linux, PID-view mismatch, successful sampling, or read/parse failure with its stage and exception type. Preserves the existing resource maxima, partial RSS contribution, child reporting, final wait4, process cleanup, actions and deadlines. RENEW's PR10479 and earlier evaluator authorship remain intact. The existing play/CLI report path consumes the additive field directly; the new field contract is in `PROCFS_PROVENANCE.md`.

Baseline: main `9d352d2dea7b0bb1cf6ef40de4b3a4616c0017ea`; evaluator blob `c90e1a9f06346db8ed3ce66aa4dd88f2ad11267d`, SHA256 `f6fbb8a6be911eb3192422e55d687ecd2ffa77315102924393d5144e25c1763a`, 35468 bytes. AST outside Actor.__init__ and Actor.close is identical. The runtime diff adds diagnostic assignments only and retains the prior exception and resource-handling paths.

Executed in the existing cloud container:

- New `test_procfs_provenance.py` against baseline via `EVALUATOR_SOURCE`: 12 errors, each the absent diagnostic key; 6.979 seconds unittest time, 7.612713 seconds invocation wall time.
- `python -B test_procfs_provenance.py` against the candidate: 12/12 passed; 7.212 seconds unittest time, 7.889808 seconds invocation wall time.
- Unchanged `python -B test_final_usage.py`, fixture blob `878550a8da329df332bf22e977a9a58b2bb02258`: 11/11 passed; 7.803 seconds unittest time, 8.453045 seconds invocation wall time.

The new tests use real worker processes and controlled procfs boundaries; they cover mismatch, missing/malformed identity, child status and CPU read/parse failures, partial RSS retention, successful CPU-only sampling, serialization, report snapshots, idempotent close, and the non-Linux branch. That branch was exercised on Linux, not on a native non-Linux system. No official games, accepted-panel replays, candidate-policy changes, canonical archive writes, provider submissions or new infrastructure were involved. Historical reports remain unchanged.

Candidate evaluator: 36057 bytes; SHA256 `e9a093ab6bccaa58289ba84ee62d4abec0aa85eae2a8dfc828964c4b6773c797`. This receipt describes the tested candidate; the PR and Slack completion reply carry the eventual integration SHA and exact current-main readback.
