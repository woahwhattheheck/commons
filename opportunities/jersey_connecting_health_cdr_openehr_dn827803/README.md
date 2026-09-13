# Jersey Connecting Health — CDR + openEHR qualification carrier

Internal commercial qualification carrier for **States of Jersey / Government of Jersey** procurement **DN827803**, *Connecting Health - Clinical Data Repository (CDR) and openEHR*.

## Current truthful state

**`HOLD_TENDER_PACK_REQUIRED`**.

Public procurement sources establish a real centralised CDR + real-time clinical-data platform requirement, openEHR compliance, interoperability, open standards/portability, integration with Jersey's existing health estate, future analytics/digital capability, a five-year term with up to two years of extension, and permission for joint bids/partnerships where appropriate. The controlling tender pack, evaluation schedules, legal/commercial terms, security/clinical requirements and response forms are **not present in this carrier**.

That public HOLD is intentionally unchanged by the v2 hardening. A typed SHA, a caller-edited source ledger, synthetic tender bytes, arbitrary evidence labels, or a historical packet clock cannot promote it.

## V2 qualification authority model

`READY_FOR_OWNER_TENDER_REVIEW` now requires all of the following at the same time:

1. the exact source-ledger bytes named by the qualification manifest;
2. the exact acquired/reviewed tender-pack bytes whose SHA-256 is in the source ledger;
3. a `jersey-dn827803-trusted-qualification/v2` extraction commitment covering the current tender/addenda inventory, buyer source digests, buyer-bound response deadline, complete mandatory-requirement universe, route/cure semantics, requirement text commitments, and approved evidence identities; and
4. the **independently retained canonical SHA-256 of that trusted qualification commitment**.

The expected trusted-qualification SHA is the external trust root. It must be retained when a human/process has reviewed the controlling package and extraction. **Do not compute the expected SHA from whatever trusted-qualification file is presented at evaluation time.** Doing so would recreate the self-authentication defect fixed by #13816.

The trusted commitment binds three subordinate sets independently:

- buyer source identities/digests (`buyer_source_set_sha256`);
- complete requirement descriptors (`requirement_set_sha256`); and
- approved capability evidence (`evidence_set_sha256`).

Every mandatory requirement has a stable requirement ID, claim/capability ID, route set, cure rule, exact buyer-source ID + digest and description SHA-256. Deleting a requirement, flipping mandatory/route/cure semantics, changing its source or text, omitting a later addendum, or rewriting the source ledger changes the retained root and fails closed.

`PROVEN` capability records may still carry compact evidence IDs in the qualification manifest, but those IDs only count when the retained trusted commitment contains a matching approved-evidence record bound to the same capability claim, subject (`PRIME` or `PARTNER`), immutable source SHA-256, source reference and statement SHA-256. An arbitrary `evidence:<gate>` string or evidence approved for a different capability does not satisfy a gate.

## Time and deadline authority

Current-work evaluation consumes trusted UTC **out of band**. The library requires `trusted_as_of`; the production CLI samples process UTC and has no `--as-of` option.

The packet's historical `evaluated_at` remains provenance only. It cannot keep an old qualification current. The trusted extraction also has an explicit addenda/package-inventory freshness fence (24 hours); current verification re-evaluates against current trusted UTC and detects semantic aging or time rollback.

A hard `NO_BID_DEADLINE_CLOSED` can be emitted only after the retained trusted commitment verifies, its buyer-source-bound deadline agrees with the source ledger, and current trusted UTC is at or past that deadline. A caller-edited earlier deadline cannot self-close the opportunity against the retained root.

## Contents

- `sources.json` — public-source ledger and explicit tender-pack state.
- `requirements.md` — public-scope architecture/evidence matrix; not itself a buyer-complete requirement extraction.
- `route_matrix.md` — prime vs bounded specialist teaming routes.
- `tender_pack_recovery.md` — authorized recovery, hashing and extraction procedure.
- `partner_response.md` — prime-evidence profile plus fill-only response structure.
- `qualify.py` — deterministic fail-closed qualification/current-verification engine.
- `fixtures/public_hold.json` — current truthful public qualification manifest.
- `fixtures/public_hold.expected.json` — historical fixture receipt only; production currentness is re-evaluated.
- `tests/test_qualify.py` — authority-bound hostile tests.

## Run current public HOLD

```bash
python3 qualify.py fixtures/public_hold.json
```

Expected exit code: `3`. Expected state: `HOLD_TENDER_PACK_REQUIRED`.

After authorized tender-pack acquisition/review, READY-capable evaluation additionally requires the retained trust inputs:

```bash
python3 qualify.py qualification.json \
  --tender-pack /path/to/exact-pack.bin \
  --trusted-qualification /path/to/reviewed-trust-v2.json \
  --trusted-qualification-sha256 <independently-retained-canonical-sha256>
```

To test whether an earlier receipt is still current, supply it with `--verify-receipt`; the CLI samples current UTC again. A stale addenda inventory, closed deadline, source aging, or clock rollback causes verification to fail.

## Exit codes

- `0`: `READY_FOR_OWNER_TENDER_REVIEW` — internal owner review only, **not** submission authority.
- `3`: valid input, fail-closed HOLD or current-verification failure.
- `4`: buyer-source-bound trusted response deadline has closed (`NO_BID_DEADLINE_CLOSED`).
- `2`: invalid or unsafe input.

## Authority ceiling

No ProContract registration/login, buyer contact, clarification question, tender submission, supplier representation, clinical certification claim, pricing/staffing commitment, contract acceptance, spend or revenue claim is authorized by this package. Every receipt carries `tender_submission_authorized=false` and a self-hash; current verification also recomputes the qualification from the same retained trust inputs rather than trusting receipt text.