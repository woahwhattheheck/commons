# Westfield State RFP 2027-002 — paid technical analytics workshare

**State:** `PROPOSED_NOT_ACCEPTED / $0 booked / no buyer submission`

This carrier turns Commons issue #14030 into a concrete subcontract workshare that a qualified advancement prime can evaluate quickly. It does **not** claim that KHow Consulting is pursuing the RFP, that Token Junkie Labs is the prime, or that Westfield has approved any supplier.

## Pinned public context, not live-provider authority

The carrier pins these two public source identities:

- Westfield State University's open-bids page: `https://www.westfield.ma.edu/offices/open-general-bids`
- KHow Consulting's public profile: `https://khowconsulting.com/`

The compiler labels this boundary `PINNED_PUBLIC_IDENTITIES_NOT_LIVE_PROVIDER_AUTHENTICATED`. It does not fetch those pages, prove they are still live, prove KHow is bidding, or convert public descriptions into solicitation-specific qualification. Any external use still needs a fresh provider/source check and the separate Muse single-writer gate.

The pinned opportunity identity is exactly:

- buyer: `Westfield State University`
- solicitation: `RFP #2027-002 Advancement Data Modeling`
- deadline: `2026-09-25`
- route: `Bonfire/Euna`

Those fields are code-owned in this pre-award carrier; a caller cannot transplant another buyer, solicitation, deadline, route, or source and rehash it into a valid receipt.

## Commercial truth boundary

This package is pre-award only. `commercial.state` is pinned to `PROPOSED_NOT_ACCEPTED`. Stronger states such as accepted, funded, delivered, paid, or revenue-recognized are not representable here.

Pricing is also closed rather than prose-screened: the only accepted value is the sentinel `UNPRICED_SCOPE_NEGOTIATION_REQUIRED`. Actual commercial terms belong in a separately evidenced contract/payment layer, not this readiness carrier.

All buyer/prime/reference/data/award/payment/revenue authority flags remain false.

## Paid workshare

TJLabs proposes a bounded **technical analytics / model-validation subcontract**, contingent on a qualified prime deciding to pursue the RFP and agreeing scope/payment before implementation.

Deliverables:

1. **Source-to-feature provenance ledger** — each candidate predictor bound to its source field, transformation, as-of date and allowed use.
2. **Entity + household leakage controls** — constituent dedupe and household grouping before train/validation partitioning so the same donor unit cannot leak across folds.
3. **Temporal validation contract** — features must be knowable at the historical scoring cutoff; gift/bequest outcomes must occur strictly after that cutoff.
4. **Calibration + ranked-lift acceptance** — Brier/reliability plus lift-at-k, not accuracy theater on an imbalanced outcome.
5. **Reproducible handoff** — split manifest, metric definitions, model/config digest, exception ledger and a content-addressed acceptance receipt.

Excluded unless separately contracted: buyer portal submission, campaign-strategy leadership, production-data custody, prime responsibility, reference ownership, buyer commitments, or independent certification.

## Closed acceptance semantics

The manifest uses closed policy IDs instead of free-form promises:

- `CONSTITUENT_HOUSEHOLD_GROUP_BEFORE_SPLIT_V1`
- `FEATURES_KNOWABLE_AT_CUTOFF_OUTCOMES_STRICTLY_AFTER_V1`

The required-check set is exact and temporal holdout is mandatory. Source roles, URLs, and their boundary notes are code-owned. The canonical deliverables, exclusions, handoff artifacts, and metric selections are also code-owned and order-bound. Caller prose cannot substitute a stronger award/payment/submission/data-access claim and then rehash it into a valid acceptance receipt. Receipt verification recompiles this full normalized plan.

## Executable contract

```bash
python revenue/westfield_advancement_data_modeling/acceptance.py \
  revenue/westfield_advancement_data_modeling/westfield_manifest.json

python -m unittest discover -s revenue/westfield_advancement_data_modeling/tests -v
python -O -m unittest discover -s revenue/westfield_advancement_data_modeling/tests -v
python -m unittest -v test_westfield_advancement_data_modeling.py
python -O -m unittest -v test_westfield_advancement_data_modeling.py
```

The root bridge exists so the existing path-filtered `tests.yml` battery retains this product in both ordinary and optimized Python without adding a workflow slot.

No donor PII or production data belongs in this public carrier.
