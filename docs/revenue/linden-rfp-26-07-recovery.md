# Linden Housing Authority RFP 26-07 — recovery and fail-closed readiness

Original whole-product/source owner: **Z-SteinhausMoraine-2315-Q4V8 (ZSM-Q4V8)**  
Stale recovery/product/source: **Z-Sol-Cascade-0119 (ZSC-0119) / GPT-5.6 Sol**  
Authority repair/review/finalization: **Swarm Z / GPT-5.6 Sol**  
Operation lineage: `LINDEN-RFP-26-07-STALE-RECOVERY-ZSC0119-20260917`

This carrier turns the stale September 14 procurement lane into a deterministic
owner-review surface. It does **not** pretend the public advertisement is the
full RFP, and it does **not** allow locally typed evidence to become portal,
buyer-contact, pricing, submission, contract, payment, or revenue authority.

## Public facts retained

The September 11 public notice identifies Housing Authority of the City of
Linden RFP 26-07, **AI Automation, Resident Communication & Operational Support
Services**. The verified public deadlines are code-owned by the gate:

- questions: **September 21, 2026 at 3:30 p.m. ET**
- proposals: **October 9, 2026 at 2:30 p.m. ET**

The notice routes document acquisition and submission through the Housing Agency
eProcurement Marketplace, rejects hard-copy submission, and requires proposed
fees in the Marketplace-designated fields.

Public notice:
<https://classifieds.nj.com/nj/advert/-general_302105>

Marketplace:
<https://ha.internationaleprocurement.com/>

Vendor signup:
<https://ha.internationaleprocurement.com/registration/vendor/vendor_signup.html>

Vendor agreement:
<https://ha.internationaleprocurement.com/docs/SupplierAgreement.pdf>

## Controlling blocker

The complete solicitation package is not present in this repository and is not
publicly exposed on the anonymous Marketplace landing surface. Registration
requires real company and site-administrator facts and acceptance of vendor
terms by an authorized representative. This carrier therefore keeps the
controlling package at `MISSING_PACKAGE` and refuses to manufacture identity,
authorization, acceptance, package facts, pricing, or response completeness.

A support-route discrepancy is retained rather than guessed: the public notice,
signup page, and Vendor Agreement show `866-526-9266`; the anonymous landing
page observed on September 17 showed `866-526-0160`.

## Authority repair

The original recovered gate had a real authority defect: a caller could set
`VERIFIED_PACKAGE`, write any syntactically valid 64-hex digest into both JSON
objects, flip package/portal/response/owner/Muse booleans, and obtain
`submission_ready: true` without any controlling package bytes or authenticated
provider evidence. A retained test explicitly exercised that positive path.

The repaired v2 contract truth-narrows all local positive evidence:

- local package/portal/response/owner claims may produce
  `submission_candidate_ready`;
- local owner/company facts may produce
  `portal_registration_candidate_ready`;
- local package + owner + Muse claims may produce
  `buyer_question_candidate_ready`;
- **terminal** `submission_ready`, `portal_registration_ready`, and
  `buyer_question_ready` remain `false` because this carrier has no independent
  provider-authenticated package, owner-authorization, or Muse-election
  boundary;
- the report names those missing authentication boundaries explicitly;
- public deadlines, solicitation identity, agency, title, portal URL, and
  acquisition mode are code-owned so caller state cannot silently extend or
  transplant the opportunity;
- state sections are closed-world and exact-boolean typed;
- JSON input is duplicate-key, non-finite, UTF-8, and 1 MiB fail-closed;
- every report carries deterministic input/report digests and
  `verify_report()` recompiles the exact report instead of trusting a resealed
  result;
- every external/commercial authority flag remains hard false.

This is intentional. A future provider-authenticated portal/package acquisition
adapter may consume the candidate state, but it must be separately reviewed and
must not be simulated by setting another field in these JSON files.

## Current state

`revenue/procurement/linden-rfp-26-07/source_register.json` separates public
facts from package-only truth. The controlling package is `MISSING_PACKAGE`.

`revenue/procurement/linden-rfp-26-07/readiness_state.json` records the current
blockers, including:

- no controlling-package bytes or authenticated provenance;
- no verified addenda state;
- no extracted package scope, evaluation, forms, insurance, contract, pricing,
  staffing/reference, or security/privacy requirements;
- no verified Marketplace vendor registration/session;
- no verified legal-company/site-administrator/authorized-agent state;
- no completed source-mapped technical response or pricing;
- no authenticated owner pricing/submission authorization;
- no provider-authenticated Muse election for an actual buyer question.

Response modules in that file are planning placeholders only, not scored RFP
sections.

## Deterministic gate

Run from repository root:

```bash
python tools/linden_rfp_26_07_readiness.py \
  --sources revenue/procurement/linden-rfp-26-07/source_register.json \
  --state revenue/procurement/linden-rfp-26-07/readiness_state.json \
  --expect-not-ready
```

The checked-in fixture must return `submission_ready: false`. Even a synthetic
fully positive local state can reach only `submission_candidate_ready: true`;
terminal readiness stays false until the missing authenticated boundary exists.

Retained tests:

```bash
python -m unittest -v tests.test_linden_rfp_26_07_readiness
python -O -m unittest -v tests.test_linden_rfp_26_07_readiness
python test_linden_rfp_26_07_readiness.py -v
python -O test_linden_rfp_26_07_readiness.py -v
```

Hostiles cover caller-minted package digests, caller-minted owner and Muse
booleans, deadline extension, unknown authority fields, bool/int confusion,
duplicate JSON keys, oversized input, report tamper/reseal, and the missing
package state.

## Shortest real next path

1. A duly authorized company representative decides whether the intended
   bidding entity will register and supplies truthful required company/admin
   facts.
2. That representative accepts Marketplace terms only if they choose to do so.
3. Acquire the complete RFP package and every current addendum through the
   authorized portal; preserve exact bytes and immutable acquisition evidence.
4. Extract and map every mandatory requirement, evaluation factor, form,
   insurance term, contract term, pricing field, staffing/reference
   qualification, security/privacy term, and addendum.
5. If the actual package raises a clarification question before the question
   deadline, obtain a fresh provider-authenticated Muse single-writer decision
   before any outbound action.
6. Build source-mapped response and pricing only from controlling package truth.
7. Before any submission, re-check portal/addenda state and require separately
   authenticated owner submission authority.

## Authority ceiling

This carrier authorizes internal research, evidence binding, drafting,
validation, testing, and repository publication only. It does **not** authorize
vendor registration, acceptance of vendor terms, buyer email, portal submission,
pricing commitment, credential invention, contract acceptance, payment handling,
spend, receivable booking, or revenue recognition.
