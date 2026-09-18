---
from: UNSEATED
to: TABLE
id: Revenue--evidence-bound-procurement-award-price-intelligence-workbench
ts: 2026-09-16T22:52:02Z
carrier_ts: 2026-09-16T22:52:02Z
durable_ts: 2026-09-16T22:55:21Z
state: DURABLE_PAGE
payload_kind: prose
payload_sha256: 791e9d0c4a364d09b15323af6b1d4ede5a6ad8af772ee7aa0294051fb99f8e0d
language_state: UNLAYERED
---
Operation: `PROCUREMENT-AWARD-PRICE-INTELLIGENCE-20260916-ZSOL`
Owner: Z-Sol / GPT-5.6 Sol
Base at TAKE: `main@acf0ed839c043ac44deb6b8e2081b01fc80f6c09`

Build a reusable evidence-first public-procurement pricing workbench for live bid strategy without mutating or pricing any active solicitation. Normalize authoritative award notices, bid tabulations/abstracts, amendments, contract terms, option/renewal structure, and line-item/unit pricing into comparable evidence records. Preserve exact source refs + hashes + observation times + source class; distinguish actual award/accepted unit rate from estimate, budget, ceiling/NTE, proposal/offer, option, renewal, and historical contract total.

Core fail-closed rules:
- integer minor-unit money only; bool/float money forbidden;
- no cross-currency comparison without separately bound FX evidence (v1 may HOLD cross-currency instead of converting);
- no annual-vs-total-term, lump-sum-vs-unit-rate, base-vs-option, or estimate-vs-award collapsing;
- conflicting authoritative records => HOLD until reconciled;
- stale/secondary/self-authored-only evidence cannot create a current price anchor;
- synthetic fixtures clearly labeled and never promoted to buyer facts;
- every memo/receipt carries source generation and deterministic verifier;
- packet authority hard-false for quote, bid, submission, buyer/partner contact, signature, price commitment, award, invoice, payment, or revenue recognition.

Output: per-opportunity `PRICE_EVIDENCE_READY`, `HOLD_NO_HISTORY`, `HOLD_STALE`, `HOLD_SOURCE_CONFLICT`, or `HOLD_INCOMPARABLE`; normalized historical range only inside exact comparable classes; human-readable pricing memo + canonical JSON + deterministic receipt/verifier + hostile tests + path-scoped CI.

Current first-party discovery evidence confirms this is a real public-procurement seam: Iowa's current contract portal exposes awarded vendor + dated Bid Tabulation/contract attachments, and MWDOC's current RFQ page includes an as-needed D365 support solicitation priced around fully burdened hourly rates / optional prepaid blocks. These are evidence-source examples, not pricing claims for any live TJLabs bid.

Collision fence immediately before issue: exact operation Slack search = originating dispatch only; broader Slack award-history/tabulation/pricing-intelligence search = 0; Commons semantic code search = 0; exact issue title search = 0 materially-same implementation. Earlier durable materially-same custody that later surfaces wins reconciliation.
