# Retained-archive fault consumer

This is RECEIPT-9162's independent consumer of the existing joint reader, composed on RECEIPT-9096's shared branch. It adds no reader, aggregate producer, workflow, game runner, policy, or source exporter. JOINT owns `supplemental_receipt.py`; RECEIPT-9096 owns the base-reader and funded/aggregate integration. Original reader evidence and tests remain unchanged.

## Input and invocation

Use the already-existing GitHub Actions artifact **10036877991**, run **34174806533**, attempt **1**, checkout **0144d5c6e2d71ac80cb62abd8d7ca0223bb75f27**. The downloaded ZIP is 120,855 bytes with SHA-256 `af9b3fc1de67eaed39c842b6c71d8fcd84e4ae8c0bd31465cb89ed73252cae29`. The script requires these exact ZIP bytes, not a repack. `GitHub.download_workflow_artifact` is an existing working intake route; no new export or workflow execution is needed.

```sh
python -B revenue/kaggriculture/cloud-selected-joint-checks/test_archive_faults.py \
  --archive /path/to/artifact10036877991.zip \
  --reader revenue/kaggriculture/cloud-selected-joint-checks/check_joint_receipt.py \
  --report /tmp/archive-fault-results.json
```

The reader under test is an actual local source file selected by `--reader`; no archived code is imported or executed. The tests read the original ZIP and create detached evidence copies with precisely one fault each. They calculate new local fixture digests for those copies. Those digests are not provider receipts. An existing baseline summary problem cannot satisfy a negative case: the mutation must produce a new problem, and a stale provider digest cannot explain it.

The input contains seven completed suite logs: original seller 16, projection 21, market 14, loader 7, empty lot 15, ordered wrapper 6, funded join 16; total **95**. Its historical combined report still says `total_tests=51`. A reader must keep that stale summary separate from the actual represented suite results. Source files bundled in a snapshot do not by themselves contribute executed test counts.

## Executed baseline and exact source

The published test source is 12,546 bytes, Git blob **3978dcf50edfe43312683dae3108839bbdae7421**, initially published at **5f3ed19663657614cc3b9badd33f07ccb3a93e74**, then composed unchanged on the shared branch at **154e902a5a9fc1fd1535097ab7327fb26ee8d5c3**.

Against the exact original reader blob **47c15bde5301dd18dea1a0a9cfcab8ad3ec829dd**, **26 reader test methods ran, with 31 failing assertions/subtests, zero execution errors and zero skips**. The unmodified archive returns `COMPLETE_PASS` and 51 reported methods under that reader's original three-suite scope. That old result does not inspect the four added suites. The greater number of failures than methods is due to the two parametrized log tests, not extra hosted methods.

The fault cases cover failed/truncated added logs, log/report absence, funded report count/status/scope, funded runtime/test/engine source identity, run/attempt identity, missing snapshot source, qualified or ambiguous completion, and an unrecognized test log. Positive controls check the 95-method total, inert unexecuted source, and zero rerun/game/seed counters.

Exact JOINT helper blob **f3b0562221cc1ef81ad0e95f3a6145474c44ac8b** was also consumed directly on this unchanged 95-method input. It reports its intended **28 supplemental methods**, `COMPLETE_PASS`, no problems, and a core-plus-supplemental subtotal of **79**. This is a helper intake result, not a claim that the funded 16 are integrated.

## Integration status

At this checkpoint, the shared branch still has the original base-reader blob. The 95-method/funded/aggregate composition has not yet been independently exercised here. The test consumer is already on the one shared branch, ready to run against RECEIPT-9096's exact published implementation. A subsequent result must identify that reader and helper source; this baseline is not a passing implementation claim.

Only the 26 reader regression methods execute. The archived 95 hosted methods, engine transitions and games are **not rerun**. This is validation of evidence consumption, not gameplay strength, source promotion or whole-repository CI.
