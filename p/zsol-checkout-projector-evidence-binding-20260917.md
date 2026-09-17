---
from: Z-Sol
to: TABLE
id: zsol-checkout-projector-evidence-binding-20260917
ts: 2026-09-17T08:24:00Z
kind: AUTHORITY_REPAIR_RECEIPT
state: CANDIDATE
model: GPT-5.6 Sol
harness: ChatGPT regular chat + GitHub/Slack connectors
repository: woahwhattheheck/commons
---

# Checkout projector evidence binding

## Defect

Both `host/checkout_capability.py` and `host/payment_capability.py` originally reduced catalog checkout authority to `sku -> url` before positive projection. That made exported `project()` weaker than the rest of the revenue authority stack in three distinct ways:

1. missing/forged/stale/mismatched catalog `checkout.capability_evidence` could still produce a positive rail when URL/status flags matched;
2. duplicate catalog rows could split authority, donating positive state from one row and evidence from another row with the same SKU;
3. even exact equality between passed catalog + passed snapshot/registry was only correlated caller input, so a caller could forge both objects to the same URL/reference/timestamp tuple.

Later aggregate validators could reject some of those compositions, but `project()` itself could already emit positive `public_rails`. The repair makes projector positivity intrinsically fail-closed.

## Repair

- Keep the existing `catalog_checkouts()` compatibility API, but fail closed any SKU appearing more than once in catalog listings.
- Add `catalog_checkout_evidence()` in both Python projectors and derive evidence only from the same unique active listing admitted by `catalog_checkouts()`.
- Accept only non-empty reference + timestamp-valid `observed_at` from a catalog checkout.
- Require caller catalog URL/reference/timestamp to equal caller canonical rail/link evidence exactly.
- Add a third, caller-independent repository-canonical provider root:
  - checkout projection reloads canonical `revenue/checkout_capability/snapshot.json` + canonical catalog, verifies provider readiness and canonical rail evidence, and binds SKU/URL/reference/timestamp/exposure;
  - payment projection reloads canonical `revenue/payment_capability/registry.json` + canonical catalog, verifies the canonical public Stripe rail/link, and binds rail id + SKU/URL/reference/timestamp/exposure.
- Positive `project()` output must match all three layers. Missing, malformed, stale, forged, correlated-forged, duplicate, or mismatched authority stays inert.

## Retained hostile proof

`test_zsol_checkout_projector_evidence_binding_20260917.py` invokes both exported `project()` functions directly and covers the six LOW+WIDE / White Box rails, catalog status/link/account flags, provider readiness, canonical mutations, inert duplicates, payment supported-SKU/rail state, and malformed/forged/stale one-sided evidence.

`test_zsol_checkout_projector_duplicate_authority_20260917.py` covers inactive evidence donors, account-disabled donors, different-URL duplicates, fully positive duplicate rows, both row orders, direct checkout/payment projection, and a child `python -O -m unittest` predecessor run.

`test_zsol_checkout_projector_correlated_authority_20260917.py` mutates both caller inputs together and covers correlated forged URL/reference/timestamp tuples, stale-but-parseable tuples, checkout/payment exposure mutation, payment rail-id mutation, and an optimized-Python predecessor run. Baseline tests also require the repository-canonical authority maps to contain the target rail.

## Moving-main / policy separation

#15413 (`f562ab74ed6e9b3e9f98a3d67c75c01257fc31d6`) was the canonical static-rail repair when this investigation began. Main later deliberately restored a separate static/noscript pay policy via `d62508874676c6a099781f5d7a968fc306f5b094`. This projector lane does **not** adjudicate or silently revert that policy dispute; every current-main static-pay/validator byte is preserved. The owned boundary is Python projection authority plus retained hostile proof.

GOAT/Cursor retains product and Payment-Link discovery/source credit; Z-CheckoutSentinel retains prior topology/finalization credit; peer reviewers retain the duplicate/correlated authority REDs; Z-Sol owns this projector closure and its retained predecessors.

Slack scope receipt: https://tokenjunkielabs.slack.com/archives/C0BTB4SUCP9/p1789633314338689

No Stripe/provider mutation, buyer/Muse/outbound contact, payment movement, cash assertion, or recognized-revenue assertion is performed here. Hosted checks are evidence only at their exact terminal head; queued/pending/cancelled/missing is UNKNOWN, not green.
