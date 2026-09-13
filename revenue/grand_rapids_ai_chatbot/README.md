# Grand Rapids 920-45-269 — AI chatbot proposal carrier

Original operation: `GRANDRAPIDS-920-45-269-AI-CHATBOT-ZSOLSTICE-20260913`  
Post-merge authority repair: `GRANDRAPIDS-PREFLIGHT-INDEPENDENT-AUTHORITY-ZLFW3H7-20260913`  
GitHub issues: `#13870`, `#13884`

This directory is a fail-closed production carrier for the City of Grand Rapids RFP 920-45-269 opportunity. It deliberately separates public/official-source context, proposal-state claims, and **independently authenticated retained authority**.

## What is here

- `requirements.json` — claim/source ledger with `CONFIRMED_OFFICIAL`, `CORROBORATED`, `PACKET_REQUIRED`, and `OWNER_REQUIRED` states.
- `submission_state.json` — untrusted current readiness claims. It remains HOLD and does not pretend the packet, certifications, references, pricing form, registrations, or owner release exist.
- `trusted_authority.py` — host-authenticated, anti-rollback authority envelope for the exact solicitation, controlling packet/addenda generation, canonical gate universe, typed evidence records, and owner release.
- `preflight.py` — deterministic fail-closed readiness receipt. A PASS claim cannot contribute to READY unless its evidence IDs resolve against the **host-pinned current** authority generation.
- `TRUSTED_AUTHORITY.md` — trust boundary, envelope schema, host-root rotation, and operator procedure.
- `acceptance.py` — executable UAT invariant checker for grounding, routing, source freshness/conflict, high-risk holds, duplicate/retry semantics, timeout reconciliation, and replay.
- `proposal_scaffold.md` — technical/administrative proposal carrier with packet insertion points.
- `questions.md` — packet-first clarification ledger and do-not-duplicate access inquiry record.
- `test_preflight.py`, `test_acceptance.py` — hostile regressions.

## Current commercial truth

The controlling RFP/addenda are not held by this lane. Official City Purchasing says MITN is its online procurement/current-opportunity system and current opportunities require vendor login; it also says vendors must register in Vendor Self Service to be paid and publishes EBO policies/forms. Those facts do **not** prove the opportunity-specific forms, evaluation rules, eligibility, certifications, or pricing schedule.

A single access-only email was sent to the named buyer on 2026-09-13 after a provider-level Gmail dedupe returned zero prior Grand Rapids/solicitation/buyer traffic. That email asked only for the authoritative packet/access path and permitted question channel. No reply is claimed.

The landed v1 preflight previously treated non-placeholder strings inside `submission_state.json` as sufficient PASS evidence. That meant the same caller could author packet custody, certifications, pricing, references, and even owner release. v2 removes that authority: proposal state is untrusted, and READY additionally requires a separately retained authority document whose exact current generation + canonical SHA-256 are pinned by the validation host outside proposal bytes.

## Verify current state

```bash
python -m unittest discover -s revenue/grand_rapids_ai_chatbot -p 'test_*.py' -v
python -O -m unittest discover -s revenue/grand_rapids_ai_chatbot -p 'test_*.py' -v
python revenue/grand_rapids_ai_chatbot/preflight.py revenue/grand_rapids_ai_chatbot/submission_state.json
```

Expected current preflight status: `HOLD`.

A future authenticated evaluation may add `--authority /trusted/path/authority.json`. The CLI deliberately has **no generation or root-digest flags**. Those current-root values are host-provisioned only:

- `GRAND_RAPIDS_PREFLIGHT_AUTHORITY_GENERATION`
- `GRAND_RAPIDS_PREFLIGHT_AUTHORITY_SHA256`

Do not let proposal-state authors control those host values. See `TRUSTED_AUTHORITY.md`.

`READY` means only that every canonical gate resolved to typed evidence in the host-authenticated current authority generation. It never contacts the buyer, signs, submits, spends, awards, invoices, recognizes revenue, or moves money.
