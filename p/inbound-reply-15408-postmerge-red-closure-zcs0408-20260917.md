# Inbound reply triage post-merge RED closure — 2026-09-17

Operation: `INBOUND-REPLY-15408-POSTMERGE-RED-CLOSURE-ZCS0408-20260917`

This fix-forward consumes the independent exact-head review lineage after #15408 merged without closing authority/collision predecessors. Original Z-Sol product/source/recovery credit and Z-CheckoutSentinel-0408 first-review/fix-forward credit are preserved; later Swarm Z work is bounded to stale RED recovery, additional predecessor closure, proof, topology, and finalization.

## Closed predecessors

1. **Invisible/compatibility/default-ignorable binding split.** `org_key` and `route_key` previously admitted caller-authored Unicode spellings that could be stripped, rendered invisibly, or remain visually indistinguishable while duplicate custody used only retained text plus `casefold()`. The repaired boundary validates the original spelling before canonicalization, requires exact NFKC, rejects Unicode category-C, line/paragraph separators, every non-ASCII `Zs` separator, and the non-category-C `Default_Ignorable_Code_Point` ranges needed to cover variation selectors, grapheme joiner, Hangul fillers, and related controls. Only outer ASCII SPACE (`U+0020`) may be trimmed.

2. **Same-second list-order send authority.** `MUSE_SELECTED@T` followed by `SENT@T` previously passed for an initial send. Repeat sends also failed to require the intervening human reply strictly before the current send. The repaired transition contract requires `MUSE_SELECTED < current SENT`; after a prior send it additionally requires `previous SENT < HUMAN_REPLY < current SENT`.

3. **Same-second reply/draft readiness authority.** `HUMAN_REPLY@T` followed by `RESPONSE_DRAFT_READY@T` previously could reach `RESPONSE_READY_OWNER_REVIEW` using caller list order. The validator now requires `HUMAN_REPLY.at < RESPONSE_DRAFT_READY.at`, and the classifier independently requires strict `draft.at > human.at`.

Retained hostile coverage includes U+200B/U+202E/U+2060, edge U+2028/U+2029/NBSP/U+3000/U+1680, U+FE0F variation selector, U+034F combining grapheme joiner, U+115F Hangul filler, compatibility/fullwidth and decomposed-normalization spellings, initial/repeat same-second Muse/SENT, repeat same-second human/SENT, both same-second human/draft list orders, valid strict orderings, and explicit `python -O` replay.

## Evidence / authority ceiling

Event and lease `evidence_refs` remain retained caller evidence identifiers. Receipt verification exactly recompiles source/packet bytes but does not provider-authenticate those refs. `NEW_HUMAN_INBOUND`, lease activity, and `RESPONSE_READY_OWNER_REVIEW` therefore remain retained-evidence states unless a separate reviewed provider/source binding is supplied elsewhere.

No Gmail/Muse/outbound/provider/customer/contract/invoice/payment/receivable/revenue mutation is performed or authorized. Existing hard-false authority bits remain unchanged.
