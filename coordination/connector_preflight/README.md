# Connector capability preflight

`connector_preflight` turns tool-discovery evidence and action-attempt evidence into a deterministic answer to one narrow coordination question:

> Does the retained evidence support saying that the GitHub and Slack write rails are unavailable?

It does **not** call GitHub, Slack, or any other provider. It does not grant permission to mutate anything. It only compiles and verifies evidence supplied by the caller.

## Why

A worker can see an initially narrow tool projection and incorrectly report that publication is blocked. In this environment the complete connector catalog is exposed by a first-pass discovery such as:

```text
api_tool.list_resources({"paths":["GitHub","Slack"]})
```

The preflight makes the evidence requirements mechanical:

1. one complete, unfiltered first-pass discovery must cover both `GitHub` and `Slack`;
2. the latest such discovery controls; an older catalog or action success cannot override newer evidence;
3. CURRENT mode requires the controlling discovery and latest write attempts to remain inside `max_age_seconds`; a fresh wrapper cannot revive old provider evidence;
4. the discovery catalog is checked for policy-required write actions;
5. a `NO_WRITE_RAIL` claim requires a relevant write attempt when those actions are exposed;
6. read-endpoint throttling never proves a write rail absent;
7. temporary or ambiguous write failures do not become connector-absence evidence;
8. only complete read-only discovery or unavailable results for every exposed required probe can support the blocker claim.

## States

Per connector:

- `NOT_DISCOVERED`
- `DISCOVERED_READ_ONLY`
- `WRITE_ACTIONS_EXPOSED`
- `WRITE_ATTEMPT_REQUIRED`
- `WRITE_ATTEMPT_FAILED`
- `WRITE_RAIL_CONFIRMED`

Overall:

- `NOT_DISCOVERED`
- `DISCOVERED_READ_ONLY`
- `WRITE_ACTIONS_EXPOSED`
- `WRITE_ATTEMPT_REQUIRED`
- `WRITE_RAIL_CONFIRMED`
- `BLOCKER_SUPPORTED`
- `HOLD`

`work_blocked_claim_supported=true` is intentionally rare. A GitHub read `403`, Slack read `429`, a safety rejection, an authorization error, an unknown outcome, or an unattempted exposed action is **not** represented as proof that the write rail does not exist.

## Input

The input schema is `commons.connector-preflight/v1`.

- `claim`: `CAPABILITY_REPORT` or `NO_WRITE_RAIL`
- `captured_at`: canonical whole-second UTC
- `policy.required_actions`: exact probe actions for GitHub and Slack
- `discoveries`: normalized discovery request/result snapshots
- `attempts`: normalized action attempts bound to an exact discovery request

Every discovery and attempt carries a SHA-256 evidence pointer. The compiler checks syntax and internal binding, but a public digest is integrity metadata, not provider authentication.

See `examples/discovery-only.json` and `examples/write-confirmed.json`.

## CLI

Run from the repository root:

```bash
python -m coordination.connector_preflight.cli compile input.json bundle.json
python -m coordination.connector_preflight.cli verify input.json bundle.json
python -m coordination.connector_preflight.cli verify-current input.json bundle.json
```

`compile` and `verify-current` use process UTC. Their public Python APIs accept no `clock`, `now`, or `as_of` override. `verify` proves exact retained historical integrity. Current verification fails when the wrapper, controlling discovery, or authority-bearing write attempts become stale, or when the current decision projection differs from the retained one.

Input reads require a bounded regular file and reject a final symlink. Output creation is create-exclusive, mode `0600`, and refuses overwrite/final-symlink publication.

## Tests

```bash
python -m unittest -q coordination.connector_preflight.test_preflight coordination.connector_preflight.test_latest
python -O -m unittest -q coordination.connector_preflight.test_preflight coordination.connector_preflight.test_latest
python -m py_compile \
  coordination/connector_preflight/core.py \
  coordination/connector_preflight/cli.py \
  coordination/connector_preflight/test_preflight.py \
  coordination/connector_preflight/test_latest.py
```

The hostile suite covers malformed discovery, filtered first-pass discovery, incomplete catalogs, read throttling, missing or unknown action attempts, temporary write failure, confirmed write rails, unavailable rails, chronology, stale/future evidence, duplicate identities, type aliases, order invariance, receipt tamper, currentness drift, strict JSON, and safe file publication.

## Authority ceiling

Every packet hard-codes all external authority flags false. A receipt does not authorize connector calls, repository mutation, messaging, customer contact, payment activity, submission, or a revenue claim.

Runtime support is explicitly Python 3.10+; hosted CI exercises Python 3.10 and 3.12.
