# Cooperative replay completion deadline

The existing `replay_routes` now checks its shared deadline when the delegated
simulation returns and again after constructing the completed result. A final
simulation call or action-digest computation can overrun even when its preceding
check passed. Such a return now stays `incomplete`, with `reason=budget:time` and
`cash_gain=null`; it does not expose completed result or score fields.

This is not hard preemption or a guarantee that the caller returns within its
wall-clock limit. One dependency call, recording work, and final report formatting
can still overrun. Callers still need an appropriate budget and fallback. The
change makes late completion explicit rather than admitting it as an on-time
valued alternative.

Earlier complete route/scenario cases remain intact. All requested case identities
remain present, partial market rows remain available, ordinary errors remain
incomplete, and external `BaseException` cancellation still propagates. The
successful report schema and economic execution are unchanged. No controller,
scenario, route-selection, policy, engine, or oracle implementation is replaced.

## Executed validation

On Python 3.13.5 in an isolated cloud container:

- Eleven new boundary methods pass. The same suite on the unchanged original
  source has five failed assertions/subtests and no errors. It covers on-time,
  exact-deadline, delayed-return and delayed-digest completion, an incomplete
  multi-case grid, partial evidence, decision exhaustion, original-input
  preservation, cash-binding errors and cancellation.
- Twelve conditional single-decision native executions form six original/candidate
  pairs, using two recorded own actions at steps 577 and 718 from the existing
  PRISM development trace. The two on-time pairs agree in every report field
  except wall time. Four late-return/last-engine-stage pairs preserve exactly the
  original market rows while changing only completion availability as intended.
- All three changed Python files compile. These are not full games, controller
  restorations, runtime speed measurements, or new independent game samples.

The native check supplies the already-recorded own action through a test-only
single-action controller. It calls the unchanged T04 oracle and official engine;
unknown rival flows remain the explicitly empty conditional scenario. Historical
rival actions and outcomes are not used as runtime inputs.

## Source and input identities

Original replay Git blob: `7955b2c6683420f4b580e30dca15ca8c752f5560`.
It was re-read unchanged at main `8801b86ce2572c81ae1c31cfc51119763a0316f8`.
Candidate replay Git blob: `e299275048d241602541e3329631f169e4de7634`.
New boundary-test blob: `a5f667af98173d621884b17a08ce95ee7ab8fe77`.
Native checker blob: `802feff9afebc770a74927eebe0d90bfa39a49b6`.

Existing T04 oracle blob: `49640c27862d3d132c828fbafc6a8b4957527736`.
Official engine commit: `28b6d8af3ce73926b3d0fda1410c1ddd8384ab8c`;
the existing evaluator verifies its three file blobs before loading.

The original PRISM Library archive is
`prism-late-milk-choice-evidence-20260907.zip`, SHA256
`2f8566ed9cd7cd04d342216c9eb5922f3d8bd361ffd952994439e10e9771907a`.
All 72 manifested members were verified before use. The exact selected trace is
`work/dev1/9982019-arlene-p0-frozen_sell_control.trace.jsonl.gz`, SHA256
`cb11721af66b438dd1f2d8615033f6b7da11ea70815ed20d2de9863d6bf4b03b`.
The archive already includes the unchanged engine and source packs; no new export
or game is needed. Full native reports and execution logs remain in the private
completion package, not a second public trajectory collection.

## Replay

Run the new test beside the existing implementation:

```sh
python -B -m unittest -v test_completion_deadline
python -m py_compile physical_replay.py test_completion_deadline.py check_completion_deadline.py
```

For the native before/after boundary check, save the original source from the
pinned main above outside the checkout. Extract the existing PRISM archive and
its nested source/engine packs according to its `ARCHIVE-README.md`. Then run:

```sh
python -B check_completion_deadline.py \
  --original /cloud/original/physical_replay.py \
  --candidate ./physical_replay.py \
  --oracle ../cloud-service-value/oracle.py \
  --source-root /cloud/source/revenue/kaggriculture \
  --engine-root /cloud/engine \
  --trace /cloud/prism/work/dev1/9982019-arlene-p0-frozen_sell_control.trace.jsonl.gz \
  --output /cloud/completion-check.json \
  --private-output /cloud/completion-full-results.json
```

## Consumer and scope

PRISM's bounded model choice and JOINT's copied full-SELL continuation can consume
this correction through their existing injected `replay_routes` callable at the
next deliberate source revision. Existing frozen experiments remain on their
original pins. No running panel or selected policy was changed.

RILL retains the physical replay and its original evidence; PRISM, JOINT, T04,
DATE and FIR retain their implementations and economic results. This contribution
changes only `physical_replay.py`, adds `test_completion_deadline.py` and
`check_completion_deadline.py`, and supplies this guide.

Coordination: ASTRA-KESTREL-OW, operation
`kestrel-physical-replay-deadline-20260907-01`, in the existing T06 thread:
https://tokenjunkielabs.slack.com/archives/C0C0Z8AHGP2/p1788832807795799
