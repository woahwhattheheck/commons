# LADBS 222114 / 2025AIP007 — qualification carrier

**Carrier:** `LADBS-AIP-PPC-222114-ZFCYM7R5-20260913`  
**Buyer:** City of Los Angeles Department of Building and Safety (LADBS)  
**Opportunity:** 222114 / RFP 2025AIP007 — Artificial Intelligence (AI)-Powered Pre-Plan Check (AIP-PPC) Assistant  
**Current disposition:** `HOLD_CONTROLLING_PACKAGE_BYTES`  
**Response deadline indexed by current RAMP mirrors:** 2026-09-17

This directory is a buyer-specific qualification and response-working packet. It composes with the buyer-neutral `tools/proposal_gate/proposal_gate.py`; it does not fork that gate and it is not a claim that Commons already operates a municipal pre-plan-check product.

## What is verified versus discovered

The official RAMP opportunity URL resolves, but its dynamic Salesforce surface did not expose controlling document bytes to this execution path. Current RAMP-indexed mirrors agree on opportunity identity, amended stage, deadline and a 33-document package. Secondary document indexes additionally expose useful scope/risk signals. Those signals are discovery evidence only until the exact RFP/addendum/Q&A/functional matrix bytes are recovered.

The most important discovered blocker is mandatory-proposer-conference language reported by a current document index. The packet **does not** assume that language is controlling and **does not** assume attendance. `GATE-003` therefore stays blocked on both controlling clause text and actual attendance evidence.

## Files

- `sources.json` — source hierarchy, known package inventory, and explicit secondary-only risk signals.
- `requirements.json` — buyer requirement register consumed by the generic proposal gate.
- `evidence.json` — truthful evidence inventory. Missing means missing; pending means not yet curated/proven.
- `FIT-GAP.md` — prime/teaming/no-bid blockers and cures.
- `CAPABILITY-TRUTH.md` — real reusable assets versus proposed/unproven buyer capability.
- `ARCHITECTURE.md` — proposed technical acceptance architecture only.
- `RESPONSE-SKELETON.md` — evidence-constrained response outline; not a submission draft.
- `CURRENT-READINESS.json` — compact deterministic receipt recomputed from the generic proposal gate.

## Rebuild

```bash
python tools/proposal_gate/proposal_gate.py pursuits/ladbs_aip_ppc_222114/requirements.json pursuits/ladbs_aip_ppc_222114/evidence.json --json-out pursuits/ladbs_aip_ppc_222114/offer-readiness.json --markdown-out pursuits/ladbs_aip_ppc_222114/offer-readiness.md --check
```

`--check` is expected to exit `2` while the packet is truthful and blocked. A zero exit is not a target to game; it is earned only when mandatory evidence is actually available and owner gates are deliberately resolved outside this carrier.

## External-action ceiling

No LADBS/RAMP contact, portal registration, proposer-conference claim, proposal submission, signature, notarization, cost commitment, insurance representation, BIP/subcontractor representation, reference invention, legal/compliance certification, deployment/cloud spend, buyer acceptance, receivable, cash or revenue claim. Any future outbound or submission needs a separate exact ownership/provider-history/authorized-human gate.
