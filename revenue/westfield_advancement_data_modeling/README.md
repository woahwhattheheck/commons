# Westfield State RFP 2027-002 — paid technical analytics workshare

**State:** `PROPOSED_NOT_ACCEPTED / $0 booked / no buyer submission`

This carrier turns Commons issue #14030 into a concrete subcontract workshare that a qualified advancement prime can evaluate quickly. It does **not** claim that KHow Consulting is pursuing the RFP, that Token Junkie Labs is the prime, or that Westfield has approved any supplier.

## Current authority

Westfield State University's official open-bids page lists **RFP #2027-002 — Advancement Data Modeling**, posted September 4, 2026, with response/opening on **September 25, 2026 via Bonfire/Euna**:

- https://www.westfield.ma.edu/offices/open-general-bids

KHow Consulting's current public site describes advancement strategy, analytics, campaign readiness and data-informed decision work:

- https://khowconsulting.com/

That public profile supports *fit exploration only*. It is not evidence that KHow is bidding, has accepted TJLabs, or owns any particular reference for this solicitation.

## Paid workshare

TJLabs proposes a bounded **technical analytics / model-validation subcontract**, contingent on a qualified prime deciding to pursue the RFP and agreeing scope/payment before implementation.

Deliverables:

1. **Source-to-feature provenance ledger** — each candidate predictor bound to its source field, transformation, as-of date and allowed use.
2. **Entity + household leakage controls** — constituent dedupe and household grouping before train/validation partitioning so the same donor unit cannot leak across folds.
3. **Temporal validation contract** — features must be knowable at the historical scoring cutoff; gift/bequest outcomes must occur strictly after that cutoff.
4. **Calibration + ranked-lift acceptance** — Brier/reliability plus lift-at-k (or precision/recall-at-k by agreement), not accuracy theater on a highly imbalanced donor outcome.
5. **Reproducible handoff** — split manifest, metric definitions, model/config digest, exception ledger and a content-addressed acceptance receipt.

Excluded unless separately contracted: buyer portal submission, campaign-strategy leadership, production-data custody, prime responsibility, reference ownership, buyer commitments, or independent certification.

## Why this is valuable

The highest-risk failure modes in advancement modeling are often not “the algorithm.” They are identity duplication, household leakage, future information entering historical features, unstable ranking metrics, and an opaque handoff that cannot be reproduced. This scope makes those failure modes mechanically reviewable while leaving advancement strategy and client interpretation with the prime.

## Executable acceptance contract

`acceptance.py` validates a metadata-only manifest and compiles a deterministic acceptance plan plus tamper-detecting receipt. It intentionally refuses pre-award authority promotion and binding price claims.

```bash
python revenue/westfield_advancement_data_modeling/acceptance.py \
  revenue/westfield_advancement_data_modeling/westfield_manifest.json

python -m unittest discover -s revenue/westfield_advancement_data_modeling/tests -v
python -O -m unittest discover -s revenue/westfield_advancement_data_modeling/tests -v
```

No donor PII or production data belongs in this public carrier.
