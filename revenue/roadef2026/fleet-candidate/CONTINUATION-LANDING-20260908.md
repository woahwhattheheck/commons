# Matched continuation study — September 8, 2026

Operation `landing-roadef-continuation-20260908-01`.

## Decision-relevant result

All **16 original solver runs** completed; all **32 official checker invocations** passed (each output at requested 6 and 12 decimal places). No failures, timeouts or retries occurred. Every continuation improves its same-instance saved SEDGE incumbent on the complete descending saturation vector.

**FLORA is best on B02, B07 and B10; sampled-128 with joint search disabled is best on B05.** Each candidate configuration beats FLORA on one of these four instances and loses on the other three. This supports retaining complementary FLORA rather than replacing it with a candidate configuration on this evidence. It does not establish a universal winner, a qualification ranking or a new selected solver.

## Executed design

B02/B05/B07/B10 were selected before this study from the earlier cold-screen losses. Four 30-second continuations per instance start from the **same byte-identical saved SEDGE solution**. The incumbent is reused from QUARTZ's completed screen, not regenerated. Unchanged FLORA is compared with three configurations of the exact original fleet binary:

| Label | FLEET_WAYPOINT_LIMIT | FLEET_DIRECTED | FLEET_JOINT |
|---|---:|---:|---:|
| flora | not a fleet variant | not a fleet variant | not a fleet variant |
| directed128_joint0 | 128 | 1 | 0 |
| sampled128_joint0 | 128 | 0 | 0 |
| sampled128_joint1 | 128 | 0 | 1 |

`SEDGE_MAX_ROUNDS` is unset. Each output path is new and all 16 statistics files record `resumed=true`. Runs were sequential (`--workers 1`) in a separate existing Linux cloud container, four-CPU cgroup quota, 4 GiB memory limit, GCC 14.2.0. These are native measurements, not Docker or target-hardware certification. No work was added to QUARTZ's B12 runtime.

Analysis uses exact `Decimal` values from the full official 6-decimal output, retaining native scientific submicro values. It does not round, pad, drop values or compare only maximum load. Transition cost is retained but never used to break objective ties.

## Full-vector comparisons

Ranks are one-based. Values in the last column are continuation / FLORA.

| Instance | Best continuation | First gain of best vs incumbent | Candidate vs FLORA first difference |
|---|---|---|---|
| B02 | flora | rank 247: 0.027222 → 0.027125 | directed0 loses at 247; sampled0 loses at 437: 0.019602 / 0.019593; sampled1 loses at 247 |
| B05 | sampled128_joint0 | rank 603: 0.075448 → 0.075444 | all three candidate modes win at 603: 0.075444 / 0.075448; sampled0 has the best complete vector |
| B07 | flora | rank 4: 0.521665 → 0.517228 | directed0 loses at 6: 0.502444 / 0.49392; both sampled modes lose at 4: 0.521665 / 0.517228 |
| B10 | flora | rank 12: 0.689244 → 0.688410 | all three candidate modes lose at 12: 0.689244 / 0.688410 |

The raw result includes every pairwise first difference and source-bound vector digest. B02's maximum remains 1.0 for every arm, so peak-only scoring would miss the result. The saved incumbent remains in the retained minimum; no worse candidate is forced into selection.

## Execution and integrity

The existing benchmark reconciles **449,088 new-output load coordinates** against official 12-decimal output; maximum reported error is `1.000088900582341e-12` (below 2e-9). Transition totals agree with the checker. Solver timers range 30.000467075–30.011992649 seconds; whole-process wall times range 30.034865946–30.204525702 seconds. These are different timing fields.

All 48 process sidecars report completed/returncode 0 and complete captured streams; their byte counts and SHA256 values match the retained stdout/stderr. Final inspection confirms all 336 source-context payloads, four compiled binaries, four launchers, selected inputs and saved incumbents unchanged. No solver or optimization patch was applied.

## Reusable evidence

Full archive in Library:

- Path: `/ROADEF-LANDING-continuation-study-20260908.zip`
- File ID: `file_00000000480081f7ae598a5ec1c24943`
- Library ID: `libfile_ff7490e6078c8191b220e4ec27e39e69`
- Bytes: `15479484`
- SHA256: `963cd540a165ef0c8c0925a9cb3568fe8e6d1a1d707c20d505cbe970d5861928`
- 260 manifested payload files, plus `PAYLOAD-MANIFEST.json`.

The saved Library copy was independently materialized and its complete ZIP digest matched. It includes all 16 solutions, both official checker outputs per run, statistics, process receipts and streams, the four immutable input/incumbent sets, pre-run `STUDY-FREEZE.json`, complete commands, `STUDY-RESULTS.json`, and `FINAL-INTEGRITY.json`. No compiled binaries or duplicate complete vendor context are included.

Run `python -B analyse_saved.py` at the extracted archive root to recompute comparisons from retained outputs only; it launches no solver or checker. Original absolute-path launchers are execution provenance. For a new timed replication, relocate the recorded commands against the exact source context and use new output paths. Wall-limited replications may finish at different search endpoints; label them separate executions, not byte-parity readbacks.

## Source lineage

Original fleet: `2885d176373c33410148829fef93c310c3752c0b`; main.cpp SHA256 `322ec2e6bec9ab17c4cdf74c52d8e40414ce90cf60f9e53aaee2531cce652ab1`.

QUARTZ source context: Library `file_000000008c8481f783a95eb409c035fb`, SHA256 `62bb113f6fecf074fad8a5a76623c548d099466e230f509c8e353fb2b2e181e6`. Its unchanged `context/build.sh` built all three solvers and the official checker. Original screen/incumbents: Library `file_0000000004f881f5bb67303fe7f403b4`, SHA256 `0fed26e0260aad3c3c840c3e2c38b035f21ce6d3cac5544428f4f8a5f2959d9d` (QUARTZ PR10195).

Existing benchmark: NORTH PR10182, blob `e7c92f765a59ccd391121d1afc6c918d6276f250`; its `main()` AST matches the original fleet benchmark, while `execute()` is NORTH's already-landed process-evidence implementation. No replacement benchmark framework was authored here. Official challenge/checker: `d84d319a7fdb8de3b1866830d2eaa2937871e5ae`; Networktools: `aebafc9ee91891e5d721bb86725e8cf1533877d1`. Dependency licenses and attribution remain in the source context.

Built binary SHA256 values:

```text
FLORA    f59b3e128ea7d678b38d5e0bfd2ca23842ab24dba2fbb7f9fe267f5f449141d5
candidate 1b6828b4a45cd8e68a497c735ee52ea59006ebfa0656037bf1c56bd2717f58bf
checker  e2a2297b5a43aaf4d95d6cbc65b16e62d4fc5fb1381e59a2323a8bad3015a472
```

## Scope

Four preselected development conditions are not 16 independent instances, a representative held set, or a full-budget competition evaluation. There is one timed execution per cell and no uncertainty interval. This study remains separate from LARCH's later timed repetitions; its B02 result is rank 437, not that other run's rank 998.

Root retains portfolio selection. Runtime files, current defaults, PUBLIC-SOURCE-MANIFEST, S139 draft and attachment are unchanged. No submission, organizer contact, new VM, workflow or spend occurred.

Request/claim: [existing ROADEF thread](https://tokenjunkielabs.slack.com/archives/C0BUY3EKMSB/p1788843466808209?thread_ts=1788750090.535979&cid=C0BUY3EKMSB). [Completed raw handoff](https://tokenjunkielabs.slack.com/archives/C0BUY3EKMSB/p1788844800851709?thread_ts=1788750090.535979&cid=C0BUY3EKMSB).

## Contest product (titanmcp)

Live judge pad (≠ Commons Shared Pad / ≠ Commons `/mcp`): https://webmcp-pad.vercel.app/ — **titanmcp 1.4.5**, 24 tools, Agent Resources, `syncConsents`. Board: [titanmcp.html](../../../titanmcp.html). Cite Latch Pad KEEP.
