# Z-Solstice receipt — Grand Rapids 920-45-269

Operation: `GRANDRAPIDS-920-45-269-AI-CHATBOT-ZSOLSTICE-20260913`  
Seat: Z-Solstice / GPT-5.6 Sol  
Issue: #13870  
Branch: `zsolstice/grandrapids-920-45-269-20260913`

## Landed candidate

A fail-closed proposal-production carrier for City of Grand Rapids RFP 920-45-269, **AI Powered Chatbot Platform**:

- source/requirement ledger separating official confirmation, public corroboration, packet-required facts, and owner-required evidence;
- explicit administrative/eligibility/VSS/EBO/certification/reference/form/security/integration/pricing gates;
- deterministic readiness preflight that cannot emit `READY` while a named gate is missing or placeholder-backed;
- executable UAT invariants for approved-source grounding, stale/conflicting/missing sources, high-risk intents, routing, duplicate cross-channel requests, timeout-after-commit reconciliation, and replay;
- technical proposal scaffold plus packet-first question ledger;
- hostile regression tests.

## Verification

Candidate verification before PR:

- `python -m unittest discover -s revenue/grand_rapids_ai_chatbot -p 'test_*.py' -v` -> **50/50 PASS**
- `python -m py_compile revenue/grand_rapids_ai_chatbot/preflight.py revenue/grand_rapids_ai_chatbot/acceptance.py revenue/grand_rapids_ai_chatbot/test_preflight.py revenue/grand_rapids_ai_chatbot/test_acceptance.py` -> **PASS**
- current preflight -> **HOLD**, **15 blockers**, **0 errors**
- deterministic proposal-state SHA-256 -> `45ebabd1596e0665378b1668cf23d88fd5f671dfd1b5b2b0a383aed695b60a64`

The HOLD is intentional: this lane does not possess the controlling MITN packet/addenda, packet hash, resolved packet-only requirements, complete pricing form, or owner release to submit.

## Procurement access event

Provider-level Gmail dedupe across the solicitation ID/title, named buyer route, Purchasing route, and Grand Rapids returned **0 prior messages**. One access-only email was then sent to named buyer Jeffrey Poll on 2026-09-13 asking for the authoritative packet/access path and whether bidder questions must use MITN.

Gmail provider receipt/message ID: `1a09afab50ae4fc0`.

**DNR:** do not send another outreach on this lane absent buyer reply/bounce or another material procurement event. No pitch, price, attachment, certification, eligibility, EBO, registration, submission, award, payment, or revenue claim was sent or made.

## Authority ceiling / continuation

This carrier is evidence and proposal-production infrastructure only. It does not sign, submit, mutate a procurement portal, award, invoice, or move money. Once the controlling packet/addenda are acquired, reconcile every packet-only HOLD gate, update the evaluation matrix and pricing/form carrier from source, rerun the tests/preflight, and obtain explicit owner release before any submission action.
