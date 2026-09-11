# H13 × L3 exact interaction screen

Claim: `TITAN-V31-H13-L3-HORIZON10-INTERACTION-GATE-20260911-01`

This experiment answers one narrow question: **does the R04 sale-window horizon-10 improvement survive after L3's no-late-sale-advance policy is active?**

It is intentionally not a promotion gate for L3 itself. L3 has opponent-conditioned evidence and remains disposition-sensitive; this experiment only isolates H13 *inside the exact reviewed L3 policy*.

## Fixed inputs

- L3 source commit: `d181d6ecf848f88885bc1cc348c456714b7360cd` (PR #12377 reviewed source head).
- Canonical archive: SHA-256 `5f6a4153e502713b9467776eafe7464af650584149173ce7507a31a1b2af60f1`.
- Immutable canonical carrier commit: `c580f7805cc7468094c0e880f4923133d45d70d0` (PR #12392).
- Official interpreter pin enforced by `reference/evaluator/evaluate.py`: `28b6d8af3ce73926b3d0fda1410c1ddd8384ab8c`.
- Frozen panel: seeds `2611151001..2611151008`, candidate seats 0 and 1 (16 interaction games), matching `OFFICIAL-GATE-PANEL.json`.

The workflow fetches the two PR refs only so the pinned commits are locally available, then the harness addresses the commits by full SHA. Advancing either PR cannot silently alter the executed source.

## Isolation

The harness materializes the L3 source tree from Git, materializes the canonical tar from its digest-addressed history object, and invokes L3's own `make_submission.py` twice:

- opponent: `r04_sale_horizon = 8`, L3 enabled at cutoff 648;
- candidate: `r04_sale_horizon = 10`, L3 enabled at cutoff 648.

It then extracts both packages and compares their complete `TITAN-CONFIG.json` objects after removing only `r04_sale_horizon`. Any second config difference hard-fails before evaluation. The required V3.1 R04 knobs (`row_order`, `evening_flush`, `sale_fertilizer`, `cattle_early`) and L3 flag/cutoff are type-and-value checked.

Before the 16-game interaction panel, horizon-8-on-L3 plays itself on seed 2611151001 from both candidate seats; both margins must be exact zero. The interaction panel then runs horizon-10-on-L3 against horizon-8-on-L3 on all frozen seed/seat cells, with the evaluator's first-cell trace+score replay check enabled.

## Outputs

The dedicated workflow uploads:

- `interaction-receipt.json`: hashes, exact inputs, isolation proof, all 16 cell margins, aggregate statistics, and a non-promotion disposition;
- `h10-vs-h8-l3-raw.json`: raw pinned evaluator receipt;
- `control-h8-vs-h8.json`: raw identity-control receipt;
- `run.log`: builder/evaluator console record.

The receipt labels the result as an **offline official-interpreter isolation screen**. It is not a hosted Kaggle score and cannot, by itself, justify enabling L3 or changing the canonical/default submission.

No runtime, overlay, config default, package artifact, evaluator, opponent, canonical archive, or Kaggle state is modified by this PR.
