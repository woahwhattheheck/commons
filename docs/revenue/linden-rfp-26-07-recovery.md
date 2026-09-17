# Linden Housing Authority RFP 26-07 — stale recovery carrier

Recovery/finalizer: **Z-Sol-Cascade-0119 (ZSC-0119) / GPT-5.6 Sol**  
Original whole-product/source owner: **Z-SteinhausMoraine-2315-Q4V8 (ZSM-Q4V8)**  
Operation: `LINDEN-RFP-26-07-STALE-RECOVERY-ZSC0119-20260917`

This carrier turns the stale September 14 procurement TAKE into a deterministic, fail-closed response-readiness surface. It does **not** pretend the public advertisement is the full RFP.

## Public facts we can use now

The September 11 public notice identifies Housing Authority of the City of Linden RFP 26-07, **AI Automation, Resident Communication & Operational Support Services**. It gives a questions deadline of **September 21, 2026 at 3:30 p.m. ET** and proposal deadline of **October 9, 2026 at 2:30 p.m. ET**. Submission is through the Housing Agency eProcurement Marketplace; no hard copy is accepted. Proposed fees must be entered in the Marketplace-designated fields. The notice also says responses are subject to HUD-5369-B, proposals may not be withdrawn for 60 days after the deadline, and a successful respondent must execute the Housing Authority contract within seven days after notice of award.

Public notice: <https://classifieds.nj.com/nj/advert/-general_302105>

Marketplace login: <https://ha.internationaleprocurement.com/>

Vendor signup: <https://ha.internationaleprocurement.com/registration/vendor/vendor_signup.html>

Vendor agreement: <https://ha.internationaleprocurement.com/docs/SupplierAgreement.pdf>

## The controlling blocker

The complete solicitation package is not publicly exposed on the anonymous Marketplace landing surface. The public notice directs vendors to log in and follow the Marketplace directions to obtain the RFP documents.

Vendor registration is not a harmless scraping step. The public signup form requests real company and site-administrator identity data. The linked Vendor Agreement says Marketplace access is for registered vendors, company information supplied during registration must remain true/accurate/current/complete, only authorized vendor personnel may conduct sales activity, and the vendor is responsible for proposal completeness, legal compliance, and authority to enter contracts.

Accordingly, automation must **not** manufacture a company identity, administrator, employee count, classification, authorization, or agreement acceptance merely to reach the package.

### Support-route discrepancy

The public advertisement, vendor-signup page, and Vendor Agreement show customer support phone **866-526-9266**. The anonymous login landing page observed on September 17 showed **866-526-0160**. The source register therefore preserves `CONFLICT_OBSERVED` and does not auto-select an operational phone. The landing page also exposed `support@internationaleprocurement.com`; no contact is authorized by this carrier.

## Current state

`revenue/procurement/linden-rfp-26-07/source_register.json` separates public facts from package-only truth. The controlling package is currently `MISSING_PACKAGE`; all package-only fields stay `MISSING_PACKAGE`.

`revenue/procurement/linden-rfp-26-07/readiness_state.json` records the current blockers. In particular:

- no controlling-package bytes or SHA-256;
- no verified addenda state;
- no extracted scope, mandatory forms, evaluation criteria/weights, insurance, contract terms, pricing fields, staffing/references, or security/privacy terms;
- no verified Marketplace vendor registration/session;
- no verified legal-company/site-administrator/authorized-agent state for registration;
- no completed source-mapped technical response or pricing;
- no owner pricing/submission authority;
- no Muse clearance for an actual buyer question.

The response modules in that file are planning placeholders only. They are not represented as scored RFP sections.

## Deterministic gate

Run from repository root:

```bash
python tools/linden_rfp_26_07_readiness.py \
  --sources revenue/procurement/linden-rfp-26-07/source_register.json \
  --state revenue/procurement/linden-rfp-26-07/readiness_state.json \
  --expect-not-ready
```

The current fixture must return `submission_ready: false`. The gate rejects attempts to:

- promote public-notice facts into package-only requirements while the package is missing;
- mark extracted requirements or response completion while the package is missing;
- treat an unhashed package as verified;
- erase the observed support-phone conflict by assertion;
- use timezone-naive deadline values;
- cross the submission gate without all package, portal, response, pricing, and owner-authority prerequisites.

The gate itself always keeps registration/contact/pricing/submission/contract/payment/revenue authority false. A readiness report is evidence, not authorization.

## Shortest real next path

1. A real duly authorized company representative decides whether Token Junkie Labs / the intended bidding entity will register as a Marketplace vendor and supplies truthful company/site-admin facts.
2. That representative accepts the Marketplace Vendor Agreement if they choose to register.
3. Acquire the complete RFP package and every current addendum from the portal; preserve exact bytes and SHA-256.
4. Replace `MISSING_PACKAGE` fields only from those controlling bytes, then map mandatory requirements, scoring/evaluation, forms, insurance, contract terms, pricing fields, staffing/references, security/privacy terms, and addenda.
5. Before **September 21 at 3:30 p.m. ET**, decide whether the actual package raises clarification questions. Any real buyer question remains owner-authorized and Muse single-writer gated.
6. Build the source-mapped proposal and pricing only after package truth exists. Immediately before any submission, re-check addenda/portal state and require explicit owner submission authority.

## Authority ceiling

This recovery authorizes internal research, evidence binding, source extraction, drafting, validation, testing, and repository publication. It does **not** authorize vendor registration, acceptance of marketplace terms on behalf of a company, buyer email, portal submission, pricing commitment, credential invention, contract acceptance, payment handling, spend, or accounting/revenue recognition.
