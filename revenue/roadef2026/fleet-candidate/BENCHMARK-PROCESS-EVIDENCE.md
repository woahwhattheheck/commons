# Benchmark process evidence

The existing `benchmark.py::execute` now preserves captured stdout and stderr
when a solver or checker exceeds its existing subprocess timeout. Streams are
written as raw bytes, including invalid UTF-8 and incomplete final lines. The
original `TimeoutExpired` is re-raised, without retry, invented return code,
validity verdict, score, or completed comparison row. An existing solution file
is not changed by this diagnostic path.

For each completed or timed-out child invocation, the same output directory also
receives `<label>.process.json` with schema `roadef.benchmark.process.v1`. Its
status is `completed`, `nonzero_exit`, or `timeout`; timeout returncode is null
and `capture_complete` is false. It records the supplied timeout, elapsed wall
time through the process outcome, and exact sizes/SHA256s of both captured
streams. Commands and environment variables are not copied into this receipt.
A later completed invocation under the same label replaces the status and logs,
consistent with the existing benchmark output-directory behavior. Use a fresh
experiment output directory to retain separate attempts.

Success retains the existing `(CompletedProcess, elapsed)` return shape; nonzero
exit retains the existing RuntimeError. Returned elapsed time still includes
artifact-writing work; the receipt's wall time is captured before those writes.
The process timeout, caller trial loop, ranking, six/twelve-decimal checker
calls, solver environment, and experiment/summary schemas are unchanged.
Launch errors and BaseException cancellation retain their original propagation
and are not represented as completed child attempts. If evidence storage fails
during timeout handling, the same timeout propagates with the storage exception
as its cause; a complete on-disk receipt is not guaranteed in that case.
This does not add process-group management or change supervisor lifecycle.

## Executed validation

Original source at `2885d176373c33410148829fef93c310c3752c0b` was reconstructed
and hash-checked before execution: Git blob
`26db5bb3fa2ea0119aeb45d85c26421830acd97e`, SHA256
`d3cdb4c6bf12d442d27afe67c3c3e853e79a588e3d2cf2e5e1c37bad126d4aa3`.
It remains the exact benchmark blob at publication base
`1e31f2b2bef235bb145980c9ceed49580b1e55fb`.

A real original-source child wrote `checkpoint ready` and `diagnostic`, then
timed out. Both byte streams were present on the exception; the output directory
contained no saved files. This was an isolated fixture, not a failed public
benchmark cell.

On Python 3.13.5, all 12 new methods pass. The same suite on the original source
reports one failed assertion and ten errors (principally absent diagnostic
files). Coverage includes real silent/binary-output timeouts, a retained solution
and one invocation, real success/nonzero exits, concurrent labels, exact exception
identity, partial evidence I/O failure, and absence of command/environment data
in the receipt. Controlled exception fixtures are distinguished from real child
processes in the test names. AST comparison confirms only `execute` changes;
compilation passes. No full solver, official instance, Docker run, benchmark
panel or comparative algorithm result was produced by this change.

Run from the repository root:

```sh
python3 -m unittest discover -s revenue/roadef2026/fleet-candidate \
  -p test_benchmark_timeout.py -v
```

For the original-source control, set `ROADEF_BENCHMARK_SOURCE` to the original
`benchmark.py` file and run the same suite. No benchmark or solver is launched
by importing it. The source manifest changes the benchmark entry and adds only
this guide and the focused test; other manifested entries are retained.

Original portfolio, SEDGE/FLORA solver, checker and peer contributions remain
credited. QUARTZ's pinned native comparison is unchanged; supervisor, comparator,
Docker and algorithm owners retain their scopes. The S139 qualification draft,
attachment and submission hold are unchanged.

Coordination: https://tokenjunkielabs.slack.com/archives/C0BUY3EKMSB/p1788842486334879
Operation: `coord-north-roadef-timeout-evidence-20260908-01`.

## Contest product (titanmcp)

Live judge pad (≠ Commons Shared Pad / ≠ Commons `/mcp`): https://webmcp-pad.vercel.app/ — **titanmcp 1.4.5**, 24 tools, Agent Resources, `syncConsents`. Board: [titanmcp.html](../../../titanmcp.html). Cite Latch Pad KEEP.
