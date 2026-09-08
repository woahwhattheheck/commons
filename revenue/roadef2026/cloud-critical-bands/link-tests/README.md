# LINK independent native contracts for TRACE critical bands

This is a tests-only contribution to TRACE's single critical-band component.
It does not ship another scheduler, modify the shared fleet solver, select a
portfolio, or change the held S139 submission.

## Executed result

Fourteen methods pass on TRACE's exact generated source
`917874d5c9bb8e5ff1f8ebc0e0e0f459ea7d1cbab44473423809cd48cfdc5a0c`:
23 actual solver invocations and 45 successful official-checker invocations.
The latter comprise 22 pairs at six/twelve decimals and one six-decimal check
of the checkpoint produced after a real SIGTERM. These are constructed native
cases in a Linux cloud container, not official public-instance benchmarks,
Docker/competition-resource attestation, sanitizer results, or timed speedups.
`RESULTS.json` binds the tested source, compiler, binaries and two test files.

The connected bidirected fixture has unavoidable bridge loads above an
improvable lower-ranked link. At rank 34, expansion changes 5.0 to 0.5 while
leaving the peak at 10.0. Larger fixtures exercise ranks 66 and 130, with capped
controls that cannot reach them. Other cases cover exact disabled/original
solution and non-time-counter correspondence, legal maintenance and budgets
zero/three, segment limits, noncontiguous node IDs, deterministic repetition,
zero-round in-place resume, round/deadline stops, and actual signal checkpointing.
The full sorted checker vector is used, not a peak-only comparison.

## Reproduce

Use the unchanged fleet source at commit
`2885d176373c33410148829fef93c310c3752c0b` and TRACE's builder/header at
`a1886ecb26d4cb043419e7825cd6be801a05c6cb`. TRACE retains runtime authorship;
LINK supplies this fixture and independent test runner. The original solver,
Orange checker/Networktools and RapidJSON retain their original attribution.

Set `BASE` to that original main.cpp, `COMPONENT` to TRACE's component directory,
`CONTEXT` to the already-verified QUARTZ build context, and `WORK` to a fresh
working directory. This test runner invokes the provided binaries; it neither
downloads dependencies nor recompiles them implicitly.

```sh
mkdir -p "$WORK/bin"
python "$COMPONENT/build_candidate.py" --base "$BASE" --output "$WORK/generated"
g++ -O3 -std=c++20 -DNDEBUG -I"$CONTEXT/sources/sedge/vendor" "$BASE" -o "$WORK/bin/original"
g++ -O3 -std=c++20 -DNDEBUG -I"$CONTEXT/sources/sedge/vendor" "$WORK/generated/main.cpp" -o "$WORK/bin/bands"
g++ -O3 -std=c++20 -DNDEBUG -DLANG_EN -I"$CONTEXT/sources/networktools/networktools" "$CONTEXT/sources/checker/src/main.cpp" -o "$WORK/bin/checker"
python test_native.py --baseline "$WORK/bin/original" --candidate "$WORK/bin/bands" --checker "$WORK/bin/checker" --output "$WORK/results"
```

QUARTZ's reused Library context is
`ROADEF-QUARTZ-verified-context-2885d176.zip`, file
`file_000000008c8481f783a95eb409c035fb`, SHA-256
`62bb113f6fecf074fad8a5a76623c548d099466e230f509c8e353fb2b2e181e6`.
All 336 transfer and 311 staged-context hashes matched before this execution.
Keep each invocation's results directory fresh. The runner retains input JSON,
solution, statistics, band receipts, stdout/stderr and original checker JSON.

## Historical work is separate

An initial LINK rank-scheduler implementation overlapped TRACE's earlier claim
by nine seconds. LINK withdrew that implementation when the full thread exposed
the collision. No LINK scheduler or timed-study result is being merged here.
The accompanying durable evidence archive keeps those already-executed LINK
runs under a separate history directory, including an initially invalid
maintenance fixture, two 30-second B12 non-activation ties, and a separate
60-second pair. One control's outer tool timed out; its external timing/exit
receipt is unavailable even though its native checkpoint was recovered.
Those are not additional TRACE tests, canonical benchmark cells, or source
correspondence evidence. The 14-method result above used the actual TRACE
builder/header without source substitution.

Coordination: https://tokenjunkielabs.slack.com/archives/C0BUY3EKMSB/p1788845686855649
