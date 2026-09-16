# Muse-backed outbound single-writer guard

The canonical fleet entry point is `tools/outbound_single_writer_guard_strict.py`. It wraps `tools/outbound_single_writer_guard.py`, which owns strict parsing, deterministic normalization, the core Muse-evidence evaluator, report sealing, bounded file ingress, and create-exclusive output.

The guard exists for one expensive operational failure mode: two or more agents decide within seconds of each other to contact the same hot lead through the same route. The owner-side rule is to ask Muse for a single-writer election before external outreach. This tool does **not** replace Muse and does **not** send anything. It compiles retained, provider-normalized evidence into a deterministic preflight report.

## What READY means

For one exact outbound intent, evidence binds:

- commercial `opportunityKey`;
- swarm `operationId`;
- unique `intentKey` for this exact planned send;
- provider `routeKey` plus channel and recipient;
- SHA-256 digests of subject and body;
- Muse request messages and requester seats;
- Muse decisions, lease IDs, and the exact requests they adjudicate;
- prior provider send receipts;
- do-not-recontact (`dnr`) evidence for opportunity + route;
- independent source-observation digests retained by the caller.

`READY_SINGLE_WRITER` means the supplied snapshot has one latest Muse `SELECTED` decision bound to a real prior request from the selected seat, no matching prior send receipt, no DNR, no evidence-ordering contradiction, and no strict scope/route rebound.

It means **only that**. READY is coordination evidence, not provider authentication and not permission to send.

## Authority ceiling

Every compiled report hard-codes these values to `false`:

- `externalSendAuthorized`
- `providerMutationAuthorized`
- `paymentAuthorized`
- `contractAuthorized`
- `submissionAuthorized`
- `revenueRecognized`

The core's public `AUTHORITY_FALSE` convenience object is deliberately not authority-bearing. The hostile suite mutates and fully rebinds that object and proves reports remain false. The tool never contacts Slack, Gmail, GitHub, Muse, a buyer, a payment processor, or a competition/submission provider.

## Fail-closed results

- `READY_SINGLE_WRITER` — exact Muse selection plus no stronger stop.
- `HOLD_NO_REQUEST` — no matching Muse request.
- `HOLD_REQUEST_CONFLICT` — exact-intent request evidence is internally ambiguous.
- `HOLD_NO_MUSE_DECISION` — no matching decision, or a later HOLD/YIELD/REVOKED supersedes an older selection.
- `HOLD_MUSE_CONFLICT` — latest Muse evidence is ambiguous or selects a seat inconsistent with the cited request.
- `HOLD_ROUTE_MISMATCH` — the same intent key appears on a different provider route.
- `HOLD_ALREADY_SENT` — a provider send receipt already exists for the exact intent.
- `HOLD_AFTER_DNR` — a DNR / hard-negative exists for opportunity + route.
- `HOLD_EVIDENCE_ORDERING` — retained evidence occurs after `asOfUtc`, or a decision does not follow its cited request.
- `HOLD_SOURCE_CONFLICT` — the same intent key is rebound to a different operation or opportunity.

The strict wrapper performs the route/scope-rebinding fence before delegating valid exact-scope evidence to the core evaluator. Any ambiguity remains a HOLD.

## Root snapshot

The root object has exactly:

```json
{
  "schemaVersion": 1,
  "asOfUtc": "2026-09-16T14:00:00Z",
  "intent": {},
  "requests": [],
  "decisions": [],
  "sendReceipts": [],
  "dnr": [],
  "sourceObservations": []
}
```

All timestamps are whole-second UTC. Slack message timestamps use canonical `1234567890.123456` form. SHA-256 values are lowercase 64-hex strings. IDs and route keys are bounded printable provider identifiers.

### Intent

```json
{
  "intentKey": "ACME-ONE-SEND",
  "operationId": "ACME-OUTREACH-20260916",
  "opportunityKey": "ACME-RFP-42",
  "createdUtc": "2026-09-16T13:50:00Z",
  "route": {
    "channel": "EMAIL",
    "recipient": "buyer@example.com",
    "routeKey": "EMAIL:buyer@example.com"
  },
  "subjectSha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "bodySha256": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
}
```

Allowed route channels are `EMAIL`, `SLACK_DM`, `GITHUB_COMMENT`, `FORM`, and `OTHER`.

### Muse request

Each request carries the exact intent/operation/opportunity/route, requester seat, whole-second request time, Slack message timestamp, and SHA-256 of the retained request message. Multiple contenders are allowed; Muse exists to adjudicate them.

### Muse decision

Each decision carries exact scope, the request Slack timestamp it adjudicates, decision (`SELECTED`, `HOLD`, `YIELD`, or `REVOKED`), selected seat only for `SELECTED`, lease ID, decision time, Muse message timestamp, and message digest. A later non-selection decision supersedes an older selection. Multiple decisions at the same latest decision time are ambiguous and HOLD.

### Send receipt and DNR

Any matching send receipt forces `HOLD_ALREADY_SENT`. A genuinely new follow-up needs a new `intentKey` and another Muse arbitration. DNR evidence is stronger than a selection and forces `HOLD_AFTER_DNR` while surfacing the retained provider reference.

## Determinism and verification

The parser rejects duplicate JSON keys, floats, NaN/Infinity, unsafe integers, unknown or missing fields, malformed hashes/timestamps, duplicate provider identifiers, and oversized collections. Collections normalize into stable order.

`compile_report()` records `sourceDigestSha256` over canonical normalized input and seals the payload with `receiptSha256`. Verification recompiles the exact source and compares canonical semantics, so payload tampering fails even if an attacker recomputes the outer receipt.

## CLI

Compile with the strict fleet entry point:

```bash
python tools/outbound_single_writer_guard_strict.py preflight snapshot.json report.json
```

Verify later against the exact retained snapshot:

```bash
python tools/outbound_single_writer_guard_strict.py verify snapshot.json report.json
```

Successful verification prints `VERIFIED`.

Input is bounded UTF-8 from a regular file descriptor with final-component symlink refusal where the host supports `O_NOFOLLOW`. Output is create-exclusive mode `0600`; an existing output path is never overwritten.

## Recommended fleet procedure

1. Define one exact intent before asking Muse: opportunity, operation, route, subject/body digests, and intent key.
2. Recensus Slack/Gmail/provider history for prior sends and DNR evidence.
3. Post Muse request(s), retaining exact message timestamps and body digests.
4. Retain Muse's canonical decision and the request timestamp it adjudicates.
5. Build the provider-normalized snapshot and run the strict preflight.
6. If the result is not READY, resolve the evidence conflict; do not improvise around the HOLD.
7. If READY, independently confirm no newer provider evidence exists immediately before the actual send.
8. After sending, retain the provider message ID so later preflights for that exact intent stop as already sent.

This turns a timing assumption into explicit single-writer evidence and makes duplicate hot-lead outreach fail closed even when search indexes lag by seconds.
