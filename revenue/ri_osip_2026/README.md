# Rhode Island OSIP - Qualified-Prime Operations Workshare

Operation: `RI-OSIP-QUALIFIED-PRIME-TEAMING-DOSSIER-ZSOL17-20260917`

**Current state:** `HOLD_PRIME_UNSELECTED`  
**Commercial hypothesis:** `$24,000 fixed / PROPOSED_NOT_ACCEPTED` for a bounded specialist workshare.  
**TokenJunkieLabs role:** `SUBCONTRACTOR_WORKSHARE_CANDIDATE`, never prime by this package.

## Why this lane exists

The Rhode Island Office of the General Treasurer issued an RFP on 2026-09-15 for investment management, recordkeeping, operational and administrative services for the Ocean State Investment Pool (OSIP). Questions are due 2026-09-25 at 4:00 PM ET and proposals are due 2026-10-20 at 4:00 PM ET.

The respondent minimums make a direct TokenJunkieLabs prime response non-credible absent entirely different retained evidence: at least five years as an investment-management organization in the relevant strategy, Rhode Island investment-management authorization, at least five years relevant experience for directly involved investment professionals, at least $5 billion in institutional AUM in the subject/similar strategy, and an institutional public client.

The useful lane is qualified-prime teaming. The RFP explicitly asks respondents to identify subcontractors used for fund administration, and Administration and Operations carries 25 of 100 evaluation points.

Official RFP: https://treasury.ri.gov/media/2171/download?language=en

## Candidate specialist workshare

Subject to a separately qualified prime and a negotiated paid subcontract:

- source-bound data intake and participant-account authority mapping;
- participant ledger, deposits/withdrawals and balance/earnings reconciliation evidence;
- earnings-allocation control evidence;
- fund-accounting reconciliation support without an accounting opinion;
- Treasury/statutory reporting evidence packs and custom extract acceptance;
- audit/custody coordination evidence and exception ledgers;
- transaction-processing QA and deterministic exception evidence, without executing transactions;
- technology/internal-control/business-continuity evidence;
- implementation/UAT acceptance support with replayable receipts.

The internal fixed-fee hypothesis is **$24,000**. It is not a buyer fee, an accepted quote, booked revenue, or a promise that the prime will use this workshare.

## Prime evidence gate

`osip_teaming.py` has seven exact minimum-qualification gates:

1. business tenure (>= 5 years);
2. Rhode Island investment-management authority;
3. same-day credit through 3:00 PM ET;
4. directly involved investment-professional experience (>= 5 years);
5. institutional AUM in the subject/similar strategy (>= $5B);
6. at least one institutional public client in the strategy;
7. equal-opportunity-employer status.

`PASS` requires retained evidence from gate-appropriate source classes. Even seven PASS rows cannot self-promote from the JSON payload: `READY_FOR_PRIME_TEAMING_REVIEW` additionally requires an out-of-band SHA-256 of the normalized evidence manifest. The unselected fixture therefore remains held.

The highest possible state is `READY_FOR_PRIME_TEAMING_REVIEW`. There is no bid/submission/award state.

## Procurement/contact boundary

The RFP names `Cash_RFPs@treasury.ri.gov` as the sole RFP contact and prohibits contact with other Treasurer/State personnel about the procurement. This package authorizes **no** buyer contact, RFP-question send, partner outreach send, proposal submission, portal action, lobbying, signature, investment management, portfolio/participant transaction execution, custody/fund movement, accounting/compliance opinion, contract acceptance, award, payment/refund, or revenue recognition.

Reaching the teaming-review state still does not authorize an outbound message. Outbound remains a separately coordinated action.

## Commands

```bash
cd revenue/ri_osip_2026
python -m unittest -v test_osip_teaming.py
python -O -m unittest -v test_osip_teaming.py
python osip_teaming.py compile --prime-evidence candidate_prime.example.json --output report.json
python osip_teaming.py verify --prime-evidence candidate_prime.example.json --report report.json
```

Expected fixture state: `HOLD_PRIME_UNSELECTED`.

## Integrity boundary

The compiler captures its ordinary trust-bearing JSON/hash/regex dependencies into an import generation and tests visible module-global rebinding. It explicitly claims only `COOPERATIVE_IN_PROCESS_NOT_HOSTILE_RUNTIME`; hostile mutation of Python function code/closures is outside the boundary.
