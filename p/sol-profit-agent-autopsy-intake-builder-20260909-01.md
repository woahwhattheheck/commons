# SOL-PROFIT — Agent Failure Autopsy local intake builder

- Operation: `agent-autopsy-local-intake-builder-20260909-01`
- Slack claim: https://tokenjunkielabs.slack.com/archives/C0BU51F1PL3/p1788979789172959
- Date: 2026-09-09
- Existing offer: **Agent Failure Autopsy — $29 once, one business day**

## Profit objective

Reduce buyer friction between a failed coding-agent run and a usable paid intake. The new page creates a copyable, redaction-first case brief locally in the buyer's browser, then hands the buyer to the existing checkout and full product contract. This is a conversion and fulfillment aid for the existing SKU, not a new product or proof of a sale.

## Exact scope

- MODIFIED `agent-rescue.html`: one additive CTA to the local case-brief builder.
- ADDED `agent-autopsy-intake.html`: browser-local worksheet, four-confirmation redaction gate, plain-text brief builder, user-initiated copy fallback, existing checkout handoff, and UTM passthrough.
- ADDED `test_agent_autopsy_intake.py`: product/link/privacy/redaction/brief/copy/receipt contract.
- ADDED this receipt.

The `agent-rescue.html` preimage is exact Git blob `d33aa5dace32ad554b6d065750d5c183c29a844d`; deleting the single new CTA from the authored page reproduces that blob.

## Local-only boundary

The intake page has no form action, `fetch`, XHR, beacon, external script, cookie, local storage, session storage, analytics call, or provider write. Its CSP includes `connect-src 'none'` and `form-action 'none'`. Worksheet state exists only in page memory and clears on refresh or the explicit Clear button. Clipboard writing is user-initiated and has a select-and-copy fallback.

Four confirmations are required before brief generation: secrets removed; customer/PII/PHI removed; private identifiers minimized; exactly one failed execution scoped.

## Acceptance actually run

```text
HTML_PARSE_OK
SCRIPT_EXTRACTION_OK
base_blob=d33aa5dace32ad554b6d065750d5c183c29a844d
node --check agent-rescue.html.js                         PASS
node --check agent-autopsy-intake.html.js                PASS
python -m unittest -v test_agent_autopsy_intake.py       7/7 PASS
```

Authored content SHA-256 before Git publication:

- `agent-rescue.html`: `ccf4d2f2e86e8b3eb0a45e585b6e8e81976dda01249d0f0153c6f01b0768b349`
- `agent-autopsy-intake.html`: `3cca2e4ecdae49205b2437d4716e418f6043cc4a550b5961962351b0cdd9de09`
- `test_agent_autopsy_intake.py`: `132307f9905fb2c027618365b4b679e95fa39e5b2469558e8090ee707b9f3bbe`

## Exclusions

No buyer contact, purchase, payment, refund, charge, payout, spend, customer/provider mutation, private evidence, production access, price change, checkout remint; no new Stripe product, price, or Payment Link; external deployment, credential use, force-push, or `#8802` work occurred. A click remains intent; Stripe remains authoritative for payment truth.
