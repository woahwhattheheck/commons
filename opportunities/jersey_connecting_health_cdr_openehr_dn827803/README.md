# Jersey Connecting Health — CDR + openEHR qualification carrier

Internal commercial qualification carrier for **States of Jersey / Government of Jersey** procurement **DN827803**, *Connecting Health - Clinical Data Repository (CDR) and openEHR*.

## Current truthful state

**`HOLD_TENDER_PACK_REQUIRED`**.

Public procurement sources establish a real centralised CDR + real-time clinical-data platform requirement, openEHR compliance, interoperability, open standards/portability, integration with Jersey's existing health estate, future analytics/digital capability, a five-year term with up to two years of extension, and permission for joint bids/partnerships where appropriate. The controlling tender pack, evaluation schedules, legal/commercial terms, security/clinical requirements and response forms are **not present in this carrier**.

A typed SHA is not enough. `qualify.py` requires the actual tender-pack bytes and verifies their SHA-256 before any READY state is possible.

## Contents

- `sources.json` — public-source ledger and explicit tender-pack state.
- `requirements.md` — public-scope architecture/evidence matrix.
- `route_matrix.md` — prime vs bounded specialist teaming routes.
- `tender_pack_recovery.md` — authorized recovery, hashing and extraction procedure.
- `partner_response.md` — prime-evidence profile plus fill-only response structure.
- `qualify.py` — deterministic fail-closed qualification engine.
- `fixtures/public_hold.json` — current truthful qualification manifest.
- `fixtures/public_hold.expected.json` — frozen expected receipt.
- `tests/test_qualify.py` — hostile gate tests.

## Run

```bash
python3 qualify.py fixtures/public_hold.json
```

Expected exit code: `3`. Expected state: `HOLD_TENDER_PACK_REQUIRED`.

## Exit codes

- `0`: `READY_FOR_OWNER_TENDER_REVIEW` — internal owner review only, **not** submission authority.
- `3`: valid input, fail-closed HOLD.
- `2`: invalid or unsafe input.

## Authority ceiling

No ProContract registration/login, buyer contact, clarification question, tender submission, supplier representation, clinical certification claim, pricing/staffing commitment, contract acceptance, spend or revenue claim is authorized by this package.
