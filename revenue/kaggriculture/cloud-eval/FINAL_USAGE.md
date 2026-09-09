# Final worker resource accounting

Operation: `astra-coord-kag-final-usage-20260907-01` (ASTRA-COORD).

LARK recorded a cloud child-procfs read failure in the [existing evaluator handoff](https://tokenjunkielabs.slack.com/archives/C0BTB4SUCP9/p1788763088116119). The evaluator already tolerated a failed procfs read, but then retained only the last child-reported snapshot. An allocation or CPU work inside an RPC that timed out, or a process that exited before reporting, could be absent from the final resource report. The original resource regression also assumed that an existing `/proc` directory meant a readable child status file.

`Actor.close()` now reaps its worker through `os.wait4` where available and incorporates the final OS CPU/RSS sample. It does not call `Popen.poll()` first, because that would consume the child's exit status without retaining its usage. The existing 100-ms EOF grace, process-group kill, pipe closure, private-directory cleanup, and idempotent close remain in place. Normal exit codes and negative signal codes remain distinct. The existing resource regression uses the final sample when child procfs cannot be read; it still requires an observed memory increase rather than silently passing that case.

The old `resource_sample` field continues to describe child reports and any pre-cleanup procfs sample. The additive `final_resource_sample` is `wait4` only after a successful OS sample; otherwise it reports an unavailable reason. Unsupported or failed wait4 calls retain ordinary Popen cleanup and earlier resource samples. An already-reaped worker with a known Popen return code preserves that code. Callers must leave reaping to Actor to retain the final sample.

This is worker resource accounting, not a complete process-group memory sum, a sandbox, or hosted Kaggle resource certification. Linux was exercised here. The existing macOS RSS normalization is retained, but macOS was not executed. Candidate IPC, observations, engine loading, `play`, score summaries, and policies are unchanged. No game or seed bank was rerun, and no competition submission was made.

## Validation

From this directory:

```sh
python -m unittest -v test_final_usage
python -m unittest -v test_evaluator.ActorTests.test_timeout_resource_measurement
python -m py_compile evaluate.py test_evaluator.py test_final_usage.py
```

Eight new real-worker tests passed: timeout with unavailable procfs, abrupt exit after allocation, successful action and bounded cleanup, zero exit status, missing wait4, unsupported wait4 syscall, interrupted wait retry, and an already-reaped worker. Assertions also check exit codes, closed pipes, removed private directories, and repeated close. The modified existing resource test passed both normally and with `Path.read_text` forced to raise `PermissionError`. These are nine distinct focused tests, not a full-suite result.

[Raw before/after observations](final-usage-evidence.json) retain the exact baseline blob and candidate SHA-256. Both probes allocate 32 MiB in an actual child; procfs is deliberately unavailable during close. The baseline reported 97,704 KiB for both timeout and abrupt-exit probes, unchanged from startup. The changed evaluator reported 127,240 and 127,244 KiB respectively, plus final CPU usage; exit statuses remained -9 and 23. Memory and CPU figures are measurements of this cloud runtime, not fixed expected platform values. The tests assert within-worker growth instead.

The probe source is the `hungry` and `abrupt` fixtures in `test_final_usage.py`. The eight-test run and raw comparison preceded the separate existing-test adaptation; the evaluator bytes are identical in both stages. AST comparison also confirmed nine unchanged execution/scoring/IPC function spans. No wider test-suite or new tournament success is claimed.

Reference: [Python os.wait4 and wait-status conversion](https://docs.python.org/3/library/os.html#os.wait4).
