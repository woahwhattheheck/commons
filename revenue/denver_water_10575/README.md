# Denver Water solicitation 10575 — evidence-bound qualification

Operation: `DENVER-WATER-10575-AI-AGENT-ASSIST-ZNAVEC-H3V7-20260913`  
Issue: `woahwhattheheck/commons#13798`

## Current commercial disposition

**HOLD — controlling buyer packet not acquired.** Denver Water's official current-opportunities page lists solicitation **10575 — Customer Experience AI Chatbot**, released 2026-08-31 and due 2026-09-30. The official page routes procurement downloads to Denver Water's BidNet surface. That package was not retrievable from this harness during this build, so secondary summaries are discovery evidence only and cannot prove a mandatory buyer gate.

This is not a no-bid. The opportunity is a strong domain fit for an agent-assist / agent-quality specialist seam, but PRIME or TEAMING readiness requires exact buyer documents plus truthful supplier evidence.

## What this carrier does

`qualification.py` is an offline, deterministic evaluator. It accepts an exact opportunity/source/gate envelope and emits one conservative disposition:

- `PRIME_READY`
- `TEAMING_READY`
- `HOLD`
- `NO_BID`

A mandatory requirement can authorize a route only when it is bound to an **acquired, SHA-256-bound official packet or addendum**. `SECONDARY` sources may discover candidate requirements, but never green them. Unknown, missing, future, stale-source-equivalent, malformed or conflicting evidence fails closed. A PRIME failure marked `PARTNER_CURABLE` can still leave a TEAMING route alive when the official team gates are independently proven.

The current fixture (`current_qualification.json`) intentionally compiles to `HOLD` because the controlling packet has not been acquired.

## Source authority

1. **Official notice:** Denver Water current opportunities page, which identifies solicitation 10575 and the Sep. 30 deadline.
2. **Buyer-linked procurement route:** Denver Water's BidNet page. The controlling package must be recovered from the buyer route before mandatory-gate claims.
3. **Secondary discovery:** current procurement indexing describing an internal Customer Care AI Agent Assistant, reported Genesys / SharePoint / CC&B integration, human-reviewed later-phase write-back, governance/security/accessibility/records requirements, references and insurance. These details remain provisional until buyer-controlled documents are recovered.

## High-value specialist seam if PRIME is not evidenced

The most credible bounded contribution is **agent reliability + enterprise-integration acceptance QA**, not pretending to own the customer's Genesys/CC&B platform or supplier qualifications. See `TEAMING_PACKET.md`.

## Run

```bash
python revenue/denver_water_10575/qualification.py compile \
  --input revenue/denver_water_10575/current_qualification.json \
  --output /tmp/denver-10575-receipt.json

python revenue/denver_water_10575/qualification.py verify \
  --input revenue/denver_water_10575/current_qualification.json \
  --receipt /tmp/denver-10575-receipt.json

python -m unittest discover -s revenue/denver_water_10575 -p 'test_qualification.py' -v
python -O -m unittest discover -s revenue/denver_water_10575 -p 'test_qualification.py' -v
```

## Authority ceiling

This package performs no buyer contact, BidNet login/registration/terms action, question, proposal submission, pricing commitment, signature, contract action, provider mutation, deployment, spend, award or revenue recognition. It does not invent supplier references, insurance, certifications, platform status or implementation history.
