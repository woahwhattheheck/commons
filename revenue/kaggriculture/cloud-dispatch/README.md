# ROWAN dispatch and deposit-sales candidate — Sanskrit Juggernaut handoff

Bryce's current instruction: **“Give all stuff to sanskrit juggernaut so it can
prompt claude for testing and running simulations.”** This package transfers
the complete ROWAN contribution to that existing orchestration route. LARK is
assembling the shared `../claude-handoff/` package in the canonical
[Kaggriculture Slack thread](https://tokenjunkielabs.slack.com/archives/C0BUY2GT8P9/p1788752325435209).

`candidate.py` is a complete, stdlib-only, stateless experimental agent with
the usual `agent(obs, configuration=None)` interface. It is **selected on
development games, awaiting reserved validation**. It has not replaced the
working Kaggle entry. The file can be renamed to `main.py` for testing in a
submission-shaped directory. Existing account/root owns replacement submission.

## What changed

The base is ASTRA-WORK's exact lean20 standalone at
`5d9fe82d288ee2933b38e8db8871602e688410af`, retaining Euler's farm economics and
the 20-animal/eight-hand/no-expansion policy. Its SHA-256 is
`d9487c031b50ede06a706acc8bcb40e0b5a681d9b5e92c1a1a96492b26c2dd62`.

ROWAN adds two separately reproducible behaviors:

1. Workers generate candidate jobs before any worker reserves a destination.
   A global greedy dispatcher then assigns the highest-scoring worker/job pair,
   removes that worker and claimed destination, and reserves shed stock/seeds
   only for actions executing at the current position. This changes assignment
   order; it is not an exact optimal matching algorithm.
2. After planning actions, include carried goods from on-depot `DROP` actions
   in the same turn's market sale requests. The official engine executes unit
   actions before orders. Orders remain subject to actual stock, the shared
   price curve and the existing ten-order budget.

The exact selected `dispatch_sales` bytes are in `candidate.py`:
`d87fafab8c9267d508533cd04e7ab8fa8e7c5f71414d9935ec4ddd977f0e7f74`.
`variants.py` regenerates that candidate, both single-change ablations and the
unmodified lean20 baseline. It checks the base source hash before transformation.

## Measured development result

All 36 planned games completed, 719 action rounds each, using the unmodified
official interpreter at `28b6d8af3ce73926b3d0fda1410c1ddd8384ab8c` and
ASTRA-WORK's process-isolated evaluator. Every row includes both scores, source
contract, trace hash, failure status, per-agent timing and resource measurements.
The runs used development seeds **1879, 3547, 7919**, each in both seats.
Two earlier pilot games used the same seed 1879 and are not additional holdouts.

| Candidate | Wins vs lean20 | Mean coin margin | Wins vs Euler28 | Mean coin margin |
|---|---:|---:|---:|---:|
| Global dispatcher | 5/6 | +2,451.000 | 6/6 | +3,665.167 |
| Deposit sales | 6/6 | +3,824.667 | 6/6 | +5,556.000 |
| Dispatcher + deposit sales | 6/6 | +5,759.667 | 6/6 | +4,592.667 |

The declared rule maximizes the smaller opponent mean margin; it selected
**dispatch_sales**. This is a small development comparison, not evidence of
hosted rank, prize income or universal superiority. The single-dispatch loss
(-3,551 coins, seed1879/seat0) remains in the raw record.

Files: `results/development.json` contains all raw games and their source/runtime
contract; `selection.json` contains the selection and report hash; `plan.json`
contains the predeclared development/validation split and promotion rule.
`results/development-study.py` is the exact driver used in that development run
(SHA-256 `86b520d868d1f3168329be5df49734f8b3d885c49f439462bd6dd323d742a5df`).
The active driver subsequently corrects an unnecessary preliminary incumbent
hash comparison; its Git-blob fallback already verified the actual frozen
incumbent in the measured run. No agent or evaluator bytes changed. The original
record says `cloud-harvest/`; the lane moved to `cloud-dispatch/` to resolve a
simultaneous peer path claim, preserving KESTREL's harvest scope.

## Paste this task to Claude

> Work from this complete ROWAN handoff and LARK's aggregate packet. Bryce
> explicitly requested Sanskrit Juggernaut to prompt Claude for tests and
> simulations. Existing Euler/ASTRA/ROWAN development results are accepted inputs.
> Inspect the exact selected agent, then test the unmodified selected bytes
> before suggesting promotion. Do not tune on the reserved validation results.
>
> Run `study.py validation` with the included `selection.json` and pinned engine.
> The 80 untouched games cover ten seeds, both seats, against frozen lean20,
> Euler28, compact22 and the official starter. Produce raw scores, margins,
> both-seat summaries, crashes/timeouts, trace fingerprints and measured CPU/RSS.
> Replay a game against each opponent and compare exact scores and trace hashes.
> Check the complete submission-shaped standalone in the official runner if
> available, and distinguish that from the explicit-interpreter driver.
>
> Add meaningful behavioral tests for: two workers competing for a nearby job;
> scarce shared seeds/feed; final forced-DROP ordering; action list preserving
> worker indices; deterministic repeated calls; input observations unchanged;
> shed capacity and order truncation; custom configuration values. Specifically
> examine whether the new sales block sells feed that should remain reserved,
> and whether estimated DROP inventory exceeds space actually available in the
> shed. Those edge cases are not settled by development wins.
>
> If a defect requires a fix, retain this exact candidate and results; give the
> revised candidate a distinct hash/name and use a newly declared validation set.
> Never mix scores across source versions. Report the declared promotion rule
> honestly, including losses. Keep root's existing successful Kaggle entry and
> notebook intact. Route any replacement candidate back to its existing owner.

Reserved seeds: **11003, 22003, 33013, 44017, 55021, 66029, 77041, 88037,
99041, 123457**. None had been run by ROWAN when this package was produced.
The source variants never inspect an environment seed or use test IDs.

## Run from a Commons checkout in an existing cloud runner

Prepare the pinned public engine once while networking is available:

```bash
python revenue/kaggriculture/cloud-eval/evaluate.py --prepare-engine /tmp/rowan-engine
mkdir -p /tmp/rowan-validation
cp revenue/kaggriculture/cloud-dispatch/selection.json /tmp/rowan-validation/selection.json
python revenue/kaggriculture/cloud-dispatch/study.py validation \
  --output /tmp/rowan-validation --engine-dir /tmp/rowan-engine --workers 2
```

After preparation, run evaluation in the existing network-disabled cloud
container. The evaluator's one-second action deadline is stricter than Kaggle's
overage bank. Record the actual runtime image and resource limits; these local
measurements alone do not establish the hosted 1.6-vCPU/6.5-GiB behavior.
The driver reuses `../cloud-eval/evaluate.py` and `../cloud-market/study.py`
(journal recovery and seed-paired analysis), checking/fingerprinting actual
source files. No model/API calls occur during games.

For independent reproduction of development, use `study.py development` with a
new output directory. It regenerates all three variants. Avoid mixing the
old development journal with the moved/corrected driver's new source contract.
Continuation writes a result after each game and refuses mixed-source resume.

## Complete offline archive

`rowan-dispatch-handoff.tar.gz` contains this package, the three existing peer
source directories needed by the evaluator, the exact official engine/spec/seed
helper with its Apache-2.0 license, the raw development journal and report,
candidate source snapshots, and `run-validation.sh`. It excludes credentials,
account sessions, private datasets and owner-device files. Its `SHA256SUMS`
checks the included files. Extract into existing cloud storage, then:

```bash
sha256sum -c SHA256SUMS
bash run-validation.sh /tmp/rowan-validation
```

`bundle-manifest.json` records the archive hash and all included file hashes.
The archive is a testing handoff, not a competition submission archive.

## Peer provenance and ownership

- Euler: `../20260907-offline-agent/` and ECONOMICS.md; original implementation
  and 28/10 improvement, preserved.
- ASTRA-WORK: `../cloud-market/`, `../cloud-eval/`; lean20, frozen-source
  comparisons and evaluator, preserved. Their reported 42 tests and 160 games
  belong to their package, not to this candidate.
- KESTREL: `../cloud-harvest/`; harvest/endgame experiments, separate.
- SORREL: `../cloud-herd/`; herd purchasing/economics, separate.
- LARK: `../claude-handoff/`; shared Sanskrit Juggernaut → Claude assembly.
- ROWAN: this `cloud-dispatch/` contribution. No replacement Kaggle submission.

Owner-authored code retains MIT OR CC-BY-4.0; see the complete licenses here.
Kaggle code retains its own Apache-2.0 license. Account/root's existing
[successful v2 entry](https://www.kaggle.com/code/tokenjunkielabs/tokenjunkielabs-farm-manager?scriptVersionId=347872961)
and the existing contest-sharing workflow remain with their owner.
