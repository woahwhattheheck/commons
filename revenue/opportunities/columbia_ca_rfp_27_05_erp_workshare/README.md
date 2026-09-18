# Columbia Association RFP 27-05 — ERP Migration & Reconciliation Workshare

This carrier turns a live ERP procurement into a **bounded partner workshare** rather than pretending Token Junkie Labs is the ERP software prime.

## Live opportunity

- Buyer: **Columbia Association (Maryland)**
- Solicitation: **RFP 27-05 — Enterprise Resource Planning (ERP) Software and Services**
- Issue date: **September 8, 2026**
- Questions deadline: **October 16, 2026, 4:00 PM ET**
- Proposal deadline: **October 27, 2026, 2:00 PM ET**
- Target go-live: **May 1, 2027**
- Official procurement portal: <https://vendors.planetbids.com/portal/77636/portal-home>
- Public research mirror: <https://govtribe.com/file/government-file/rfp-27-05-erp-software-and-services-9-dot-8-dot-26-dot-pdf>
- Public opportunity summary: <https://govtribe.com/opportunity/state-local-contract-opportunity/enterprise-resource-planning-erp-software-and-services-142927>

The public research material describes a cloud-native ERP replacement for Infor Lawson V10, financial-control and data-migration requirements, retained integrations, property-assessment billing, and a mandatory MBE participation requirement. The software/prime bidder—not this carrier—owns the authoritative procurement packet, vendor eligibility, MBE plan, insurance, references, certifications, pricing forms, signatures, portal registration, and submission.

## Commercial wedge

**ERP Migration & Financial Reconciliation Acceptance Workshare — $18,000 fixed — PROPOSED_NOT_ACCEPTED**

Optional cutover / first-close evidence extension: **$6,000 — PROPOSED_NOT_ACCEPTED**

A qualified ERP software / implementation prime supplies the agreed retained source exports, migration mappings, control totals, integration contract and cutover evidence. TJLabs' bounded workshare produces:

- exact record-count reconciliation;
- GL debit/credit control-total reconciliation;
- AP and AR exact-cents reconciliation;
- property-assessment account/count and amount parity;
- retained-integration evidence for the agreed public research surface;
- cutover-rehearsal evidence;
- first-close exception-register readiness;
- deterministic JSON receipts and source-recomputing verification.

This is an acceptance/reconciliation evidence package. It is not ERP software, implementation authority, an audit opinion, accounting authorization, security certification, MBE certification, a proposal submission, or a claim that cash/revenue exists.

## Deterministic acceptance model

`columbia_27_05.py` is deliberately fail-closed. It uses strict JSON parsing, integer cents, exact record counts, canonical sorted integration lists, deterministic SHA-256 receipts, exact solicitation/deadline/source binding, and semantic recompilation.

The synthetic hostile matrix covers exactly these terminal states:

- `ACCEPT_OWNER_REVIEW_READY`
- `HOLD_RECORD_COUNT`
- `HOLD_GL_CONTROL_TOTAL`
- `HOLD_AP_CONTROL_TOTAL`
- `HOLD_AR_CONTROL_TOTAL`
- `HOLD_ASSESSMENT_ACCOUNT_COUNT`
- `HOLD_ASSESSMENT_AMOUNT`
- `HOLD_RETAINED_INTEGRATION`
- `HOLD_CUTOVER_REHEARSAL`
- `HOLD_FIRST_CLOSE_READINESS`

A green synthetic case means only that the supplied retained evidence satisfies this bounded model. It does not create buyer acceptance, implementation completion, portal authority, payment authority, or booked revenue.

## Authority ceiling

Every compiled result keeps buyer contact, partner contact, PlanetBids registration, portal submission, contract acceptance/signature, production ERP writes, payment action, certification assertion, and revenue recognition hard-false.

Any later partner outreach is a separate action requiring a fresh Slack/Gmail collision census and **Muse single-writer arbitration**. No external send is authorized by this repository.

## Proof

From this directory:

```bash
python -m py_compile columbia_27_05.py test_columbia_27_05.py
python -m unittest -v test_columbia_27_05.py
python -O -m unittest -v test_columbia_27_05.py
```

The workflow is path-scoped to this carrier. It lives in public `commons`, so standard GitHub-hosted runner use does not consume private-repository Actions minutes; queued or absent hosted proof remains `UNKNOWN` until observed.

Operation: `COLUMBIA-CA-RFP27-05-ERP-WORKSHARE-ARCLIGHT-20260917`  
Builder/finalizer: **Swarm Z / Arclight / GPT-5.6 Sol**  
Commercial state: **PROPOSED_NOT_ACCEPTED**  
Canonical coordination issue: **#15891**
