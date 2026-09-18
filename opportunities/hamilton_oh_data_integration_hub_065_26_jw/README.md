# Hamilton County, Ohio RFP 065-26/JW — Data Integration Hub

Recovered source-authority-bounded pursuit carrier for Commons issue #13928.

## Current disposition

`HOLD` — not a bid and not a no-bid. The opportunity is publicly visible and appears open, but the controlling Hamilton County solicitation packet/addenda have not been retained in this carrier. Discovery mirrors are useful for prioritizing packet recovery and specialist/partner questions; they are never allowed to mint buyer requirements or submission authority.

As checked on 2026-09-17, public mirrors report an October 14, 2026 response deadline and describe a justice-data integration hub with API/event-driven integration, mapping/orchestration, validation, logging/monitoring, and NIEM/CJIS/FedRAMP-High themes. Those claims remain `DISCOVERY_ONLY` until recovered from controlling County material.

## Decision model

The compiler emits exactly one of:

- `PRIME`: official packet retained, official submission mechanics bound, and every prime gate evidence-backed.
- `TEAMING`: official material permits teaming/subcontracting, specialist delivery evidence is complete, and a real prime partner is evidence-backed.
- `HOLD`: potentially valuable, but authority or qualification gates incomplete.
- `NO_BID`: the retained official response deadline has passed.

Mirror sources (`MIRROR`) and the bare official portal entry (`OFFICIAL_PORTAL_ENTRY`) are structurally forbidden from controlling buyer fields such as deadlines, submission mechanics, teaming rules, evaluation criteria, or mandatory requirements.

## Immediate work order

1. Recover the exact official RFP and all current addenda from the County procurement portal. Retain byte hashes and identify the current generation.
2. Bind official response/question deadlines, submission mechanics, teaming rules, evaluation criteria, security/compliance requirements, insurance, references, pricing forms, and addendum precedence.
3. Re-evaluate prime economics. Do not claim TJLabs has justice-sector references, CJIS/FedRAMP authorization, insurance, or certifications unless retained owner/vendor evidence proves them.
4. If prime gates remain unproven and official rules permit subcontracting, identify a qualified prime and offer a paid specialist workshare around integration implementation, deterministic validation/evidence, cutover, observability, and test automation. External contact must use the fleet single-writer/Muse collision gate first.
5. Stop on an official deadline pass, official prohibition on teaming, or evidence that qualification/cost makes the pursuit uneconomic.

## Usage

```bash
python -m opportunities.hamilton_oh_data_integration_hub_065_26_jw.gate \
  --ledger opportunities/hamilton_oh_data_integration_hub_065_26_jw/source_ledger.json \
  --requirements opportunities/hamilton_oh_data_integration_hub_065_26_jw/requirements.json \
  --now 2026-09-17T07:05:00Z
```

Output is canonical JSON with a self-verifying SHA-256 receipt. It grants no County contact, portal registration, question/proposal submission, signature, pricing commitment, partner representation, award, payment, or revenue authority.
