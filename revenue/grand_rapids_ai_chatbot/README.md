# Grand Rapids 920-45-269 — AI chatbot proposal carrier

Operation: `GRANDRAPIDS-920-45-269-AI-CHATBOT-ZSOLSTICE-20260913`  
GitHub issue: `#13870`  
Owner: Z-Solstice / GPT-5.6 Sol

This directory is a fail-closed production carrier for the City of Grand Rapids RFP 920-45-269 opportunity. It deliberately separates what public/official sources support from what only the controlling MITN packet or owner evidence can establish.

## What is here

- `requirements.json` — claim/source ledger with `CONFIRMED_OFFICIAL`, `CORROBORATED`, `PACKET_REQUIRED`, and `OWNER_REQUIRED` states.
- `submission_state.json` — current readiness gates. It starts on HOLD and does not pretend the packet, certifications, references, pricing form, registrations, or owner release exist.
- `preflight.py` — deterministic fail-closed readiness receipt.
- `acceptance.py` — executable UAT invariant checker for grounding, routing, source freshness/conflict, high-risk holds, duplicate/retry semantics, timeout reconciliation, and replay.
- `proposal_scaffold.md` — technical/administrative proposal carrier with packet insertion points.
- `questions.md` — packet-first clarification ledger and do-not-duplicate access inquiry record.
- `test_preflight.py`, `test_acceptance.py` — hostile regressions.

## Current commercial truth

The controlling RFP/addenda are not held by this lane. Official City Purchasing says MITN is its online procurement/current-opportunity system and current opportunities require vendor login; it also says vendors must register in Vendor Self Service to be paid and publishes EBO policies/forms. Those facts do **not** prove the opportunity-specific forms, evaluation rules, eligibility, certifications, or pricing schedule.

A single access-only email was sent to the named buyer on 2026-09-13 after a provider-level Gmail dedupe returned zero prior Grand Rapids/solicitation/buyer traffic. That email asked only for the authoritative packet/access path and permitted question channel. No reply is claimed.

## Verify

```bash
python -m unittest discover -s revenue/grand_rapids_ai_chatbot -p 'test_*.py' -v
python revenue/grand_rapids_ai_chatbot/preflight.py revenue/grand_rapids_ai_chatbot/submission_state.json
```

Expected current preflight status: `HOLD`. A `READY` result is possible only when all named gates have non-placeholder evidence and owner release is explicit. The tools never contact the buyer, sign, submit, spend, award, invoice, or move money.
