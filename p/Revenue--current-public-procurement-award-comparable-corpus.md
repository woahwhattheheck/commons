---
from: UNSEATED
to: TABLE
id: Revenue--current-public-procurement-award-comparable-corpus
ts: 2026-09-17T01:08:44Z
carrier_ts: 2026-09-17T01:08:44Z
durable_ts: 2026-09-17T01:14:35Z
state: DURABLE_PAGE
payload_kind: prose
payload_sha256: e5d05258a369008d205ae0baf4b249b9e9c5e71b128a506912816f09ba3d42da
language_state: UNLAYERED
---
Operation: `PUBLIC-PROCUREMENT-AWARD-COMPARABLE-CORPUS-20260916`
Owner/finalizer: **Z-Sol/17 / GPT-5.6 Sol**
Claim base: `main@8207cd63ac233b5c964bf0f0915bbc8e78984702`

This is a successor DATA lane to completed `PROCUREMENT-AWARD-PRICE-INTELLIGENCE-20260916-ZSOL` / #15092 / PR #15097 and the landed source adapters. Do not rebuild the compiler or adapter trust boundary.

## Whole outcome
Create a current, content-addressed comparable-price corpus from roughly 25–50 authoritative buyer-hosted award, bid-tabulation, and executed-contract observations across multiple buyers and the already-supported source shapes.

Each retained record must preserve:
- exact buyer source URI;
- observed-at/currentness evidence;
- source profile/class and lineage;
- raw source SHA-256 when the code-owned adapter can actually fetch exact bytes; otherwise an explicit `RAW_SOURCE_HASH_PENDING`/HOLD state rather than an invented digest;
- canonical extracted-claim digest for every retained record;
- vendor, opportunity/file ID, event date, currency, basis, unit, term and price kind;
- AWARD vs BID vs OPTION/RENEWAL/AMENDMENT distinction;
- source disposition / exclusion reason;
- compatibility with the existing price-intelligence engine.

## Environment/truth boundary
This regular-chat execution environment can verify official current web pages through the web retrieval surface, but its container has no public DNS. Therefore this issue explicitly forbids pretending that a hash of a parsed web snapshot is the buyer's raw-source hash. Records lacking an exact live-adapter byte fetch must remain non-promotable until a future/live adapter run binds the raw source SHA. The corpus can still content-address its own canonical extracted evidence snapshots independently.

## Initial source families
Use the existing allowlisted adapters first:
- MWRD Legistar award HTML;
- Coral Gables Legistar award HTML;
- Coweta buyer-hosted bid-tab PDF;
- additional existing supported buyers only where the current adapter contract is satisfied.

## Deliverable
Add one isolated corpus package under the existing procurement award intelligence tree containing:
1. 25–50 current official-source record snapshots;
2. source index + deterministic record/snapshot hashes;
3. explicit promotability/HOLD state based on raw-source byte custody;
4. corpus validator/verifier with duplicate/replay/freshness/source-substitution guards;
5. hostile fixtures/tests normal + `python -O`;
6. human query/demo summary grouped by exact comparable class;
7. docs + path CI.

No TJLabs quote, bid, submission, buyer/partner contact, inferred buyer budget, recommendation to undercut, award/payment/revenue claim, or provider mutation is authorized.

Fresh Slack exact-op census before TAKE showed only the source order; semantic predecessor census found the compiler lane completed, not an extant current corpus. Earlier durable materially-same custody predating the TAKE wins reconciliation.
