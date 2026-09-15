# Jersey Connecting Health — CDR + openEHR qualification carrier

Internal commercial qualification carrier for **States of Jersey / Government of Jersey** procurement **DN827803**, *Connecting Health - Clinical Data Repository (CDR) and openEHR*.

## Current truthful state

**`HOLD_TENDER_PACK_REQUIRED`**.

Public procurement sources establish a real centralised CDR + real-time clinical-data platform requirement, openEHR compliance, interoperability, open standards/portability, integration with Jersey's existing health estate, future analytics/digital capability, a five-year term with up to two years of extension, and permission for joint bids/partnerships where appropriate. The controlling tender pack, evaluation schedules, legal/commercial terms, security/clinical requirements and response forms are **not retained in the current reviewed source generation**.

Current readiness authority is the repo-pinned Pursuit Evidence Bridge binding **`jersey-dn827803-main-v1`** in `revenue/pursuit_evidence_bridge/`. That binding pins the exact current source ledger and submission-manifest roots, owns process-current UTC/deadline evaluation, and remains HOLD while the tender pack is absent and bidder-vault roots are unpinned.

## Legacy qualifier retirement

`qualify.py` remains as a compatibility/diagnostic surface, but its historical READY authority is retired.

The original v1 engine accepted caller-owned `evaluated_at`, `route`, `partner_prime_confirmed`, capability declarations and future tender-pack bytes. Independent reviews of successor PR #14010 showed those caller-controlled facts could change HOLD→READY without an independently retained current generation. The shared bridge now owns current evidence authority instead.

The compatibility gate therefore:

- accepts the historical source/manifest API only to verify it against `jersey-dn827803-main-v1`;
- rejects route, partner, caller-time or source-generation mutations because they change the pinned manifest/source roots;
- rejects `tender_pack_bytes` as legacy caller authority; a real source upgrade must rotate reviewed repo-pinned evidence instead;
- obtains current UTC/deadline state from the hardened shared bridge;
- preserves the present `HOLD_TENDER_PACK_REQUIRED` state for the checked-in public fixture;
- can **never** emit `READY_FOR_OWNER_TENDER_REVIEW` or return exit 0, even if a future bridge generation becomes evidence-ready;
- keeps every action-authority bit and external/tender-submission authorization false; and
- writes optional diagnostic receipts create-exclusively rather than replacing an existing path.

A future positive pursuit generation must first retain the controlling buyer packet/addenda and independently retained bidder-evidence roots, rotate the shared bridge binding in review, and then make any route/partner/commercial decision through a separate reviewed layer. Evidence readiness is not route approval and is never submission authority.

## Contents

- `sources.json` — public-source ledger and explicit tender-pack state.
- `requirements.md` — public-scope architecture/evidence matrix.
- `route_matrix.md` — advisory prime vs bounded specialist teaming routes.
- `tender_pack_recovery.md` — authorized recovery, hashing and extraction procedure.
- `partner_response.md` — prime-evidence profile plus fill-only response structure.
- `qualify.py` — HOLD-only legacy compatibility wrapper over the repo-pinned bridge.
- `fixtures/public_hold.json` — current pinned public HOLD manifest.
- `fixtures/public_hold.expected.json` — stable expectations for the current HOLD-only wrapper.
- `tests/test_qualify.py` — hostile regressions for the retired false-READY seams.

## Run

From the repository root:

```bash
python opportunities/jersey_connecting_health_cdr_openehr_dn827803/qualify.py \
  opportunities/jersey_connecting_health_cdr_openehr_dn827803/fixtures/public_hold.json
```

Expected exit code: `3`. Expected state: `HOLD_TENDER_PACK_REQUIRED`.

Canonical shared gate:

```bash
python -m revenue.pursuit_evidence_bridge.bridge jersey-dn827803-main-v1 < envelope.json
```

The bridge can report `OPPORTUNITY_EVIDENCE_READY` only for a future reviewed binding with no static/source/evidence HOLDs. That status still does not authorize contact, submission, signature, price, staffing, contract acceptance, spend, award, payment, or revenue recognition.

## Exit codes for `qualify.py`

- `3`: valid legacy diagnostic input, fail-closed HOLD.
- `2`: malformed, unbound, root-mismatched, self-authenticating, or unsafe input.
- `0`: intentionally unreachable on the retired legacy authority surface.

## Authority ceiling

No ProContract registration/login, buyer contact, clarification question, tender submission, supplier representation, clinical certification claim, pricing/staffing commitment, contract acceptance, spend, payment, award or revenue claim is authorized by this package.
