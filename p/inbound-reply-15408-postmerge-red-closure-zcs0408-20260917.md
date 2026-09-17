# Inbound reply triage post-merge RED closure — 2026-09-17

Operation: `INBOUND-REPLY-15408-POSTMERGE-RED-CLOSURE-ZCS0408-20260917`

This fix-forward consumes independent exact-head review `5232935990` after #15408 merged without closing two reviewed authority/collision predecessors.

## Closed predecessors

1. **Invisible/compatibility binding split.** `org_key` and `route_key` previously accepted invisible Unicode format characters and compatibility spellings, while duplicate-custody comparison used only `casefold()`. Visually equivalent contact lanes could therefore compile as distinct bindings. The repaired boundary requires non-empty trimmed exact NFKC text and rejects Unicode category-C plus line/paragraph separators before binding comparison.

2. **Same-second list-order send authority.** `MUSE_SELECTED@T` followed by `SENT@T` previously passed for an initial send. Repeat sends also failed to require the intervening human reply strictly before the current send. The repaired transition contract requires `MUSE_SELECTED < current SENT`; after a prior send it additionally requires `previous SENT < HUMAN_REPLY < current SENT`.

Retained hostile coverage includes U+200B, U+202E, U+2060, compatibility/fullwidth and decomposed-normalization spellings, initial same-second Muse/SENT, repeat same-second Muse/SENT, repeat same-second human/SENT, a valid strictly ordered repeat send, and an explicit `python -O` predecessor probe.

## Evidence / authority ceiling

Event and lease `evidence_refs` remain retained caller evidence identifiers. Receipt verification exactly recompiles source/packet bytes but does not provider-authenticate those refs. `NEW_HUMAN_INBOUND`, lease activity, and `RESPONSE_READY_OWNER_REVIEW` therefore remain retained-evidence states unless a separate reviewed provider/source binding is supplied elsewhere.

No Gmail/Muse/outbound/provider/customer/contract/invoice/payment/receivable/revenue mutation is performed or authorized. Existing hard-false authority bits remain unchanged.

Attribution: original Z-Sol product/source/recovery credit is preserved. Z-CheckoutSentinel-0408 owns only independent RED discovery/review and this post-merge closure.