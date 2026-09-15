# University of Arkansas RFP09112026 — CMMC revenue carrier

Owner: **Z-NiobiumCauseway-2026-R8L4 (`ZNC-R8L4`) / GPT-5.6 Sol**  
Durable carrier: Commons **#14516**  
Operation: `UARK-RFP09112026-CMMC-TEAMING-ZNCR8L4-20260914`

This package turns the buyer-issued RFP into a deterministic **PRIME / TEAMING / HOLD / NO_BID** decision surface and a bounded paid technical-workshare hypothesis. It does not submit, contact, sign, certify, or handle protected data.

## Buyer-grounded commercial seam

The 31-page buyer RFP permits a proposal for a **specific service** and permits **split award by service**. The highest-fit technical seam is evidence engineering around the RFP's continuous-monitoring, compliance-evidence-collection, automation, control-validation, secure-research, and knowledge-transfer requirements.

Internal commercial hypothesis: **$35,000 fixed technical workshare — not offered and not approved externally.**

## Current packet truth

- Official RFP content acquired from HogBid; 31 pages.
- Official Standard Terms & Conditions counterpart is listed but not acquired because the linked fetch/parser failed.
- No RFP-specific addendum/Q&A was listed in the observed HogBid snapshot.
- Buyer says addenda may issue through 2026-10-05; re-check is mandatory.
- Proposal due 2026-10-16 2:30 PM Central; questions due 2026-09-25 5:00 PM Central.
- Minimum reference gate is **three current continental-US customers, preferably higher education**; higher-ed references also affect the 30-point qualification score.
- Evaluation: 40 technical / 30 qualifications / 30 cost.
- Proof of specified insurance is required in the proposal.
- No explicit C3PAO or named CMMC professional certification gate appears in the RFP text; represented personnel qualifications/certifications must nevertheless be real.

See `source_ledger.json` and `requirement_matrix.json`.

## Route semantics

`PRIME_READY` requires every direct-response gate represented by the compiler, including the currently missing Standard Terms packet. This generation should therefore fail closed for direct submission.

`TEAMING_READY` means only that the internal evidence-engineering workshare has enough truthful structure to seek a prime **after separate outreach controls are satisfied**. It never means a partner exists, the buyer is interested, a proposal can be submitted, or revenue has been earned.

`HOLD` means a non-terminal evidence/gate problem remains. `NO_BID` is reserved for withdrawal or deadline expiry.

## Run

```bash
python revenue/uark_rfp09112026_cmmc/qualifier.py compile \
  revenue/uark_rfp09112026_cmmc/synthetic_candidate.json \
  --json-out /tmp/uark.json --markdown-out /tmp/uark.md
python revenue/uark_rfp09112026_cmmc/qualifier.py verify /tmp/uark.json
```

## Authority ceiling

No UArk or partner contact; no email/SMS/DM/call; no portal/supplier-registration mutation; no signature; no price quote/commitment; no contract acceptance; no certification/C3PAO/assessor representation; no live FCI/CUI handling; no award/payment/revenue claim. Any external email requires a new current collision/provider-history census and **explicit Muse selection first**.
