# Indiana ERP modernization — bounded evidence/traceability workstream

**Opportunity:** Indiana IDOA RFI 27-87809 / event `000610000087809`  
**Due:** 2026-10-02 15:00 ET  
**State:** market research / modernization-strategy RFI, not an award

## Purpose

This packet defines a specialist workstream that an established public-sector ERP consulting prime can use while assessing a current environment and building a modernization roadmap. It is intentionally narrower than ERP strategy: turn customer-approved current-state inputs into a reproducible evidence set, keep assumptions separate from observations, and make each option/risk/cost statement traceable to its basis.

The current commercial path is a teaming inquiry to Daniels Associates. This repository packet does **not** establish an Indiana engagement, public-sector ERP past performance for Token Junkie Labs, authority to respond directly to IDOA, price, staffing, or a recommendation for any ERP product.

## Inputs

The prime/customer supplies authoritative source material: application and interface inventories, business-process documentation, contract/licensing facts, organizational constraints, approved interview notes, cost inputs, and any policy or architecture standards. Public sources may be included when they are named and dated. The workstream does not invent missing current-state facts.

## Deliverables

1. Normalized source register with stable source IDs, provenance, date, classification, and owner.
2. Current-state inventory rows whose factual fields cite one or more source IDs.
3. Dependency/interface edges tied to source evidence rather than inferred silently.
4. Assumption register that labels assumptions, confidence, validation owner, and status.
5. Option matrix with explicit criteria and evidence/assumption references.
6. Risk register with trigger, impact, mitigation, owner, and evidence basis.
7. Cost-range records that name estimation basis, currency, range, exclusions, and assumptions.
8. Recommendation/roadmap statements whose supporting evidence and assumptions are machine-traceable.
9. Change report showing which conclusions need regeneration when an upstream fact changes.

## Operating boundary

- Customer/prime retains ERP strategy, interviews, public-sector subject-matter judgment, procurement advice, scoring policy, final recommendations, pricing, staffing, and State interface.
- No response is submitted to IDOA from this packet.
- No State relationship, incumbent knowledge, public-sector ERP past performance, or product-vendor neutrality is asserted without separate evidence.
- Unknown facts stay unknown. They may become explicit assumptions, never observations.
- Cost ranges are planning evidence, not quotes; every range requires a documented basis and exclusions.
- A recommendation is invalid if it cannot identify both its evidence basis and any material assumptions.
- Product/vendor selection is outside this bounded workstream.
- Sensitive customer material belongs only in an environment and handling process approved by the customer/prime; the repository packet contains schema and synthetic examples only.

## Canonical contract

`evidence_contract.json` is the structured guardrail. `validate_evidence_contract.py` fails closed when the contract is weakened—for example if direct submission is enabled, decision authority moves away from the customer/prime, unknowns are allowed to masquerade as observations, cost basis becomes optional, or recommendation traceability is removed.

Run:

```bash
python revenue/indiana_erp_strategy/validate_evidence_contract.py
python -m unittest revenue.indiana_erp_strategy.test_validate_evidence_contract
```

Passing these tests validates only this packaging contract. It does not validate Indiana's current ERP environment, any modernization recommendation, any cost estimate, or any bidder qualification.
