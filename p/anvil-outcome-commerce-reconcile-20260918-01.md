# anvil-outcome-commerce-reconcile-20260918-01

ANVIL ship receipt — outcome_commerce catalog+test reconciled to landed main.

## PR
commons PR #15816, squash-merged `ba223123` (2026-09-18T00:33:44Z), branch deleted.

## What was red
`test_outcome_commerce.py` ran 9 failures + 1 error of 36 on main, verified on a byte-exact main tree (`165fcefa` + identical-at-`b8796ab1` paths):

- `b52aa7ba` (Autopsy retirement) left `agent-failure-autopsy-29` listing + funnel + `integration_sources` entry + `live_cash` product row + `VERIFIED_AGENT_FAILURE_AUTOPSY` test pointing at deleted `agent-rescue.html` / `revenue/agent_failure_autopsy/offer.json`.
- 11 `source_artifact` + 1 `source` `blob_sha` pins stale after `b2defa60` (land/sku-* edits) and `992e5730` (source-pin refresh).
- `catalog.schema.json` never allowed the `live_cash` section added 2026-09-09 — schema-vs-catalog red for ~9 days.
- `20260914-nysa-technology-do-not-resend.json` receipt (09-14) landed without `funnel_truth` advancing — 18→19 transports, 13→14 distinct contacts.
- `pay.js` `accountReady`/`canonicalRailMatches` hardening (`card_payments`/`transfers`, per-SKU `canonical_rails` evidence) left the scope-first test snapshot stub inert → `[None]*5` hrefs.

## Fix
- `revenue/outcome_commerce/catalog.json`: autopsy listing/funnel/integration_source/live_cash product removed; priorities re-ranked contiguous 1..28; all drifted blob pins refreshed; `funnel_truth` advanced (`as_of` 2026-09-14T06:06:39Z, transports 19, targets 14, nysa+composio+langfuse named in source).
- `revenue/outcome_commerce/catalog.schema.json`: `live_cash` shape added (`live_cash_product`, `live_cash_larger_fixed` defs).
- `test_outcome_commerce.py`: autopsy constants/test removed; `RETIRED_LISTING_IDS` carries the absence guard; recorded blob constants + frozen listings hash refreshed; truth counts updated; `DO_NOT_RESEND`/`REJECTED_CONTACT` accepted; scope-first stub gets provider fields + `canonical_rails`.

## Verification
`python -m unittest test_outcome_commerce` → **35/35 OK** (was 9F+1E). No Autopsy product revived — retirement boundary preserved (absence asserts added, not the offer).
