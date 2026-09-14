# Connector capability preflight

`connector_preflight` turns tool-discovery evidence and action-attempt evidence into a deterministic answer to one narrow coordination question:

> What does this retained carrier report about the GitHub and Slack write rails?

It does **not** call GitHub, Slack, or any other provider. It does not grant permission to mutate anything. It only compiles and verifies evidence supplied by the caller.

## Why

A worker can see an initially narrow tool projection and incorrectly report that publication is blocked. In this environment the complete connector catalog is exposed by a first-pass discovery such as:

```text
api_tool.list_resources({"paths":["GitHub","Slack"]})
```

The preflight makes the evidence requirements mechanical:

1. one complete, unfiltered first-pass discovery must cover both `GitHub` and `Slack`;
2. the latest such discovery controls; an older catalog or action result cannot override newer evidence;
3. each action is reduced from its latest nonconflicting attempt generation only;
4. CURRENT mode requires the controlling discovery and latest write attempts to remain inside the smaller of the caller policy and the code-owned one-hour ceiling;
5. `policy.required_actions` is diagnostic display input only; it cannot hide other discovered WRITE actions or mint a blocker;
6. read-endpoint throttling never proves a write rail absent;
7. temporary, ambiguous, authorization, or unknown write failures do not become connector-absence evidence;
8. caller-authored discovery/attempt rows and public SHA-256 references are not provider authentication.

## Authentication boundary

Schema `commons.connector-preflight/v1` carries normalized caller-authored JSON. Its `evidence_sha256` fields are integrity pointers only. The compiler does not receive the provider response bytes, a connector signature, or an independently retained host attestation root.

For that reason, v1 may report discovered actions and latest attempt outcomes, but it **never** elevates caller rows to `work_blocked_claim_supported=true`. A read-only catalog or all-`UNAVAILABLE` result set under a `NO_WRITE_RAIL` claim becomes `HOLD` with `CALLER_EVIDENCE_CANNOT_SUPPORT_NO_WRITE_RAIL`.

`BLOCKER_SUPPORTED` is reserved for a future schema that binds exact provider evidence to an independently acquired host/connector attestation. It is not emitted by v1.

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
- `BLOCKER_SUPPORTED` — reserved for authenticated evidence
- `HOLD`

A GitHub read `403`, Slack read `429`, safety rejection, authorization error, unknown outcome, unattempted exposed action, self-described read-only catalog, or arbitrary digest is **not** represented as proof that the write rail does not exist.

## Input

The input schema is `commons.connector-preflight/v1`.

- `claim`: `CAPABILITY_REPORT` or `NO_WRITE_RAIL`
- `captured_at`: canonical whole-second UTC
- `policy.max_age_seconds`: a caller ceiling that may tighten, never widen, the code-owned CURRENT ceiling
- `policy.required_actions`: diagnostic probe names for GitHub and Slack
- `discoveries`: normalized discovery request/result snapshots
- `attempts`: normalized action attempts bound to an exact discovery request

See `examples/discovery-only.json` and `examples/write-confirmed.json`.

## Python API and CLI

The public explicit-time API is historical-integrity-only:

```python
compile_at(raw, evaluated_at)
```

It has no `mode` argument and cannot mint CURRENT authority. The public current paths sample process UTC internally:

```python
compile_current(raw)
verify_current(raw, bundle)
```

They accept no `clock`, `now`, or `as_of` override. Deterministic CURRENT helpers are underscore-private for tests and exact historical reconstruction.

Run from the repository root:

```bash
python -m coordination.connector_preflight.cli compile input.json bundle.json
python -m coordination.connector_preflight.cli verify input.json bundle.json
python -m coordination.connector_preflight.cli verify-current input.json bundle.json
```

`verify` proves exact retained historical integrity. Current verification fails when the wrapper, controlling discovery, or authority-bearing write attempts become stale, or when the current decision projection differs from the retained one.

Input reads require one bounded regular-file generation. The descriptor generation is compared before and after the read, and the visible pathname must still identify the same generation. Final symlinks, FIFOs, in-place generation changes, pathname replacement, and growth beyond the ceiling are rejected. Output creation is create-exclusive, mode `0600`, and refuses overwrite/final-symlink publication. The retained writer is closed before the final readback/namespace observation; success therefore proves that the final observation saw the exact retained regular-file generation and exact bytes. It does not claim the pathname is immutable after that point-in-time observation.

## Tests

```bash
python -m unittest -q \
  coordination.connector_preflight.test_preflight \
  coordination.connector_preflight.test_latest \
  coordination.connector_preflight.test_publication
python -O -m unittest -q \
  coordination.connector_preflight.test_preflight \
  coordination.connector_preflight.test_latest \
  coordination.connector_preflight.test_publication
python -m py_compile \
  coordination/connector_preflight/core.py \
  coordination/connector_preflight/latest.py \
  coordination/connector_preflight/cli.py \
  coordination/connector_preflight/publication.py \
  coordination/connector_preflight/test_preflight.py \
  coordination/connector_preflight/test_latest.py \
  coordination/connector_preflight/test_publication.py
```

The 63-test hostile suite covers malformed and filtered discovery, incomplete catalogs, caller-selected probe hiding, unauthenticated blocker attempts, read throttling, missing or unknown action attempts, latest-result ordering, same-time conflicts, confirmed write rails, chronology, process-owned current time, code-owned age ceilings, stale/future evidence, duplicate identities, type aliases, order invariance, receipt tamper, currentness drift, strict JSON, FIFO rejection, retained-generation changes, pathname replacement, safe file publication, exceptional-path foreign-successor preservation, and post-close namespace replacement.

## Authority ceiling

Every packet hard-codes all external authority flags false, including `provider_evidence_authenticated=false`. A receipt does not authorize connector calls, repository mutation, messaging, customer contact, payment activity, submission, or a revenue claim.

Runtime support is explicitly Python 3.10+; hosted CI exercises Python 3.10 and 3.12.
