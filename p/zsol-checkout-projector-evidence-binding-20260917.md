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

After #15413 correctly restored `pay.html` to runtime provider gating, a deeper Python projection mismatch remained. Both `host/checkout_capability.py` and `host/payment_capability.py` reduced a catalog checkout to `sku -> url` before projection. Their exported `project()` functions could therefore emit a positive public rail when catalog `checkout.capability_evidence` was missing, forged, stale, or mismatched, as long as the URL and status flags still matched. Later aggregate validators could reject the composed root, but the positive projector result itself was not fail-closed.

The browser gate already required exact catalog capability-evidence reference/timestamp equality with canonical rail evidence. Python now matches that authority boundary.

## Repair

- Keep the existing `catalog_checkouts()` URL/status compatibility API.
- Add `catalog_checkout_evidence()` in both Python projectors.
- Accept only non-empty reference + timestamp-valid `observed_at` from a catalog checkout.
- Before public projection, require catalog URL, evidence reference, and evidence timestamp to equal the canonical checkout rail / payment canonical-link evidence exactly.
- Missing, malformed, stale, forged, or mismatched catalog evidence now makes the rail/link intrinsically inert in `project()` itself.

## Retained hostile proof

`test_zsol_checkout_projector_evidence_binding_20260917.py` invokes both exported `project()` functions directly and covers:

- the six LOW+WIDE / White Box rails under their baseline exact evidence binding;
- missing, forged-reference, stale-valid-timestamp, and malformed-timestamp catalog evidence for each rail;
- catalog status/provider/link/account flags and URL mismatch;
- all checkout account-readiness dimensions;
- checkout canonical link/livemode/url/exposure/evidence and inert-duplicate mutations;
- payment-registry capability/public/charge/payout, supported-SKU, canonical-link, and canonical-evidence mutations;
- source-level retention of the new evidence map and exact reference/timestamp comparison.

## Provenance

Canonical static-rail repair remains #15413 / `f562ab74ed6e9b3e9f98a3d67c75c01257fc31d6`. GOAT/Cursor retains product and Payment-Link discovery/source credit; Z-CheckoutSentinel retains topology/finalization credit; Z-Sol owns the independent review RED and this behavioral projector closure.

Slack scope receipt: https://tokenjunkielabs.slack.com/archives/C0BTB4SUCP9/p1789633314338689

No Stripe/provider mutation, buyer/Muse/outbound contact, payment movement, cash assertion, or recognized-revenue assertion is performed here. Hosted checks are evidence only at their exact terminal head; queued/pending/cancelled/missing is UNKNOWN, not green.
