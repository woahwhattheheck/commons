# WF1: current-runtime replay and purchase-capacity counterexample

## Disposition

**Evidence and tooling only. Keep the existing feature default OFF.** This packet
contains no policy repair, runtime installer, production archive, or Kaggle
submission. Its additive patch targets the existing WF1 folder on `main`, not a
new V4 integration branch. The exact shared donor and current adapter are reused.
The originating recovery session had read-only GitHub and Slack actions, so this
evidence remained unpublished. This recovery reconciles its source pins against
GitHub before publication; it does not convert historical replay receipts into
claims about the current production archive.

## Recovery compatibility fence (2026-09-15)

Recovered against `main` at `80e65a38c41dbd0dc1d99ad92bb503356654863b`.
The two live WF1 seam files still match this packet's immutable source lock exactly:
`wf1_current_adapter.py` is `5b8f4c0144ce43ae449373a6a188ce03409a16ee` and
`r04_wheat_fert.py` is `b35a30431f64c1d6b40d1d599190338a9d50b555`.

The `reference_main_commit` and `reference_current_source_blob` in `SOURCE-LOCK.json`
are **historical provenance**. The old
`runtime/integrated-selected/CURRENT-SOURCE.json` path is no longer present at the
recovery head, although the pinned manifest object remains retrievable by its Git
object id. Do not treat that manifest as today's source-of-truth map.

Current `main` already carries `WF1-CURRENT-NATIVE-FIELD-RECEIPT.json`, which records
a newer current-native eight-cell gate over the same locked donor/adapter seam.
This recovered packet is complementary: it preserves the separate 18-tape
fixed-opponent replay and the causal fertilizer purchase-capacity counterexample.
It neither supersedes the current-native receipt nor authorizes default activation.

Recovery validation on 2026-09-15: Python compilation passed, and the 44 standalone
evidence/contract tests in `test_wf1_replay.py` passed in normal and optimized
mode. The nine official-market witnesses require the detached locked runtime fixture,
which is intentionally not part of this 12-file patch, so those nine tests were not
re-run during recovery. The 53-test statement below is retained as the original
evidence receipt, not re-certified by this recovery.

## What actually ran

Pinned main reference: `7ab60c39d600416a64a35303648cdafc77c9573d` (PR 12703).
Current-source manifest blob: `8dafbc57595a09eaa8b67e7fc061e60cbcdacc74`.
WF1 adapter: `5b8f4c0144ce43ae449373a6a188ce03409a16ee`, including the peer's
market-budget and selected-actor collision guards. Donor unchanged:
`b35a30431f64c1d6b40d1d599190338a9d50b555`. Official engine:
`3c202c7ee921da239356789e266b694635103fc4`.

Eighteen recorded V3.1 games from Slack file `F0C1D4ZKBGR` were declared before
running. All 18 recorded two-seat trajectories reproduced both terminal rewards
exactly. Each cell then ran OFF and ON in separate fresh Python processes against
the same recorded opponent action stream and seed: **54 full episodes, 719
callbacks each**. The self-play tape is retained but reported separately.

For the 17 external-opponent pairs:

| Measure | Result |
|---|---:|
| Better / unchanged / worse margin | 12 / 4 / 1 |
| Mean own cash change | +86.5882 |
| Mean opponent cash change | -5.1765 |
| Mean margin change | +91.7647 |
| Wins / losses, OFF and ON | 13 / 4 in both |
| Activated games / changed callbacks | 13 / 39 |

All 36 runtime trials had zero observed parent deadline fallbacks, absent parent
instances, action mutations, over-budget parent market queues, and callbacks
exceeding one second. Maximum measured in-process callback was 0.082090 seconds.
Two instrumented regression reruns reproduced both complete action-stream hashes
and final scores of their uninstrumented references. All cash movements reconcile.
The latest adapter's 36 runtime trajectories/scores also matched the preceding
`58bee36a` panel exactly; that is measured equivalence on these cells, not a global
proof that the collision guard is inert.

The included **53 tests pass normally and under `python -O`**, with no skips:
44 evaluator/evidence contract tests and 9 official-market causal witnesses.
The nine witnesses characterize an **unfixed** failure; passing them does not
mean WF1 has been repaired.

## Counterexample: episode 107952194, candidate seat 1

OFF bank `[91169, 84204]`; ON bank `[91177, 84160]`. Candidate cash falls 44,
opponent cash rises 8, so margin falls **52**.

At callback 696, both arms return exactly nine HIRE rows followed by
`["BUY_PRODUCT", "FERTILIZER", 10]` in the tenth executable market slot. OFF has
93 units in the shed and receives **7 fertilizer**. ON has 96 units—its only shed
item difference is **three additional wheat**—and receives **4 fertilizer**.
This is a purchase-capacity failure, not shed discard and not cash shortage.

Causal controls execute the unchanged official `_process_market`:

- Removing three wheat from ON restores seven fills; adding three wheat to OFF
  reproduces four fills.
- Adding 100,000 cash to ON does not restore fills; increasing capacity to 103 does.
- Reducing the raw market cap to nine makes the fertilizer purchase inert in both
  arms, confirming that the factual purchase occupied an executable tenth slot.

The full-game ledger then records four extra wheat sold, but three fewer carrots
harvested and sold after the lost fertilizer replenishment. Candidate cash delta:
`+160 wheat -215 carrot +11 lower fertilizer purchases -10 fertilizer sales
+10 milk = -44`. Opponent cash delta is `+8`. Complete observed market states,
per-item ledgers, changed actions, and trace hashes are included.

**Integration consequence:** avoiding discarded output is not enough. Extra crop
stock can displace later input purchases. The existing WF1 credit-sales mechanism
sold its credited four wheat, yet parent-policy feedback left three extra wheat
at the replenishment callback. A native follow-through needs a capacity-aware
replenishment check or another tested resolution, rather than a blanket promotion
based on positive average margin. No particular policy repair is asserted here.

## Reproduction

The standalone evidence ZIP includes a `reproducer/` directory with the exact
runtime executable/config closure, engine and loader, donor and adapter, and all
18 input tapes. No pip installation or downloads are needed in the tested Python
3.13.5 environment. Python 3.13.5 is the measured version; other versions are not
certified by this receipt.

```sh
cd reproducer
python reproduce_wf1_panel.py --check-inputs
python -m unittest -v test_wf1_replay test_wf1_market_crowdout
python -O -m unittest -v test_wf1_replay test_wf1_market_crowdout
python reproduce_wf1_panel.py --output fresh-results
```

The driver refuses existing output directories and altered source/tape bytes.
Every arm gets a fresh process. `fresh-results/PAIRS.json` is emitted only after
all declared cells complete. Timings vary; scores and action-stream hashes are
the comparison targets. Keep complete logs of any fallbacks on a different host.

To reproduce the traced regression after that run:

```sh
python trace_wf1_replay.py --tape tapes/107952194.json \
  --runtime runtime-fixture --lock replay-capacity-evidence/SOURCE-LOCK.json \
  --arm off --candidate-seat 1 --control fresh-results/107952194-recorded.json \
  --reference fresh-results/107952194-off.json --output fresh-trace-off.json
python trace_wf1_replay.py --tape tapes/107952194.json \
  --runtime runtime-fixture --lock replay-capacity-evidence/SOURCE-LOCK.json \
  --arm on --candidate-seat 1 --control fresh-results/107952194-recorded.json \
  --reference fresh-results/107952194-on.json --output fresh-trace-on.json
```

In an existing repository checkout, the patch adds these tools beside the shared
WF1 donor/adapter. Supply `--runtime` and `--tapes` to the driver, and set
`TITAN_REPLAY_RUNTIME` for the market tests. The source lock intentionally refuses
a different adapter; new bytes require an explicit new lock and fresh controls.
Do not overwrite newer shared source with the fixture copies in the ZIP.

## Scope, provenance, and limits

This is the available 18-tape panel, **not** the separately requested 88 historical
cells. Fixed replay opponents do not adapt to the candidate. The candidate uses
current source-pinned `main.agent`, followed by the WF1 adapter **externally**;
this is not native finalizer/history/deadline composition. It does not measure
hosted Kaggle RPC performance, prove current whole-archive readiness, or authorize
default activation. No confidence interval is offered for a population win rate.

Runtime recovery used existing GitHub Actions artifact `10123395668`; its older
`main.py` and `early_capital.py` were replaced locally with byte-verified current
source. Sixty-one executable/config records are pinned in SOURCE-LOCK. Stale
artifact tests/docs were not treated as current package validation. The original
WF1 donor came from Slack `F0C19EXC5T8`; the observer is adapted from its
`wf_money.py`, with delegated engine operations and action/score equivalence gates.
All included upstream license and notice files are preserved with fixtures.

`SUMMARY.json`, `PAIRS.json`, `REGRESSION-LEDGER.json`, source lock, and panel are
under `replay-capacity-evidence/`. Raw current receipts, traces, and test logs are
under `evidence/` in the ZIP. `MANIFEST.sha256` binds every distributed file.
