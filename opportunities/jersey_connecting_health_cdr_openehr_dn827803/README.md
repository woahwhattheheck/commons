# Jersey Connecting Health — CDR + openEHR qualification carrier

Internal commercial qualification carrier for **States of Jersey / Government of Jersey** procurement **DN827803**, *Connecting Health - Clinical Data Repository (CDR) and openEHR*.

## Current truthful state

**`HOLD_TENDER_PACK_REQUIRED`**.

The public listing establishes a live CDR/openEHR opportunity, but the controlling tender pack is still not retained here. Authority v2 therefore cannot reach `READY_FOR_OWNER_TENDER_REVIEW`.

## Authority v2

`qualify.py` no longer lets the caller authenticate its own qualification packet.

Current-work evaluation now:

- loads the retained `trusted_root.json` from beside the engine; neither the CLI nor the public Python evaluation APIs accept a caller-supplied trust root;
- uses process UTC for current authority (`trusted_as_of` is explicit only in the library/test API);
- binds the exact `sources.json` bytes to the retained source commitment;
- binds the buyer deadline to both the retained root and, before any future READY, the retained buyer-pack extraction;
- requires the exact tender-pack bytes and retained pack digest;
- requires a retained extraction digest covering the complete tender/addenda inventory and mandatory requirement universe;
- commits stable buyer requirement IDs, source coordinates/digests, route/cure/mandatory semantics, raw-text digest, description digest, counts, and set digests;
- requires a separately retained evidence bundle whose records are subject-, requirement-, category-, source-, and claim-bound;
- rejects implicit cross-requirement evidence reuse;
- applies a 24-hour current-source freshness fence and trusted-time rollback/future-time checks;
- keeps historical replay explicitly non-current and unable to emit current READY authority.

Today's root intentionally has no tender-pack, extraction, or evidence commitment, so the public fixture remains a deterministic HOLD under an explicit trusted time.

## Contents

- `sources.json` — public-source ledger and explicit tender-pack state.
- `trusted_root.json` — independently retained current source/deadline and future pack/extraction/evidence commitments.
- `requirements.md` — public-scope architecture/evidence matrix; **not** buyer-pack completeness authority.
- `route_matrix.md` — prime vs bounded specialist teaming routes.
- `tender_pack_recovery.md` — authorized exact-byte recovery and v2 retention procedure.
- `partner_response.md` — prime-evidence profile plus fill-only response structure.
- `qualify.py` — public fail-closed boundary; loads the retained trust root internally.
- `_qualify_engine.py` — private implementation core used by the boundary and hostile tests.
- `fixtures/public_hold.json` — current truthful v2 qualification manifest.
- `fixtures/public_hold.expected.json` — frozen receipt at the test's explicit trusted UTC.
- `tests/test_qualify.py` — 26 adversarial authority tests, including a public-API trust-root injection fence.

## Run

Current-work verification uses process UTC:

```bash
python3 qualify.py fixtures/public_hold.json
```

Expected current state while the tender pack remains absent: `HOLD_TENDER_PACK_REQUIRED`, exit `3`.

After an authorized acquisition/review, future evaluation requires all three exact-byte inputs whose digests are already retained in `trusted_root.json`:

```bash
python3 qualify.py fixtures/OWNER_MANIFEST.json \
  --tender-pack ACTUAL_CONTROLLING_ARCHIVE \
  --extraction RETAINED_EXTRACTION.json \
  --evidence RETAINED_EVIDENCE.json
```

Historical replay is explicit and can never emit current READY authority:

```bash
python3 qualify.py fixtures/public_hold.json \
  --historical-as-of 2026-09-13T14:40:00Z
```

## Exit codes

- `0`: `READY_FOR_OWNER_TENDER_REVIEW` — internal owner review only, **not** submission authority.
- `3`: valid input but HOLD, including historical replay.
- `2`: invalid or unsafe input.

## Authority ceiling

No ProContract registration/login, buyer contact, clarification question, tender submission, supplier representation, clinical certification claim, pricing/staffing commitment, contract acceptance, spend, payment, or revenue claim is authorized by this package.
