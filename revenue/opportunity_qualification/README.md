# Opportunity Qualification Engine

Reusable offline qualification for public RFPs, paid-work solicitations, and teaming opportunities.

The engine converts a source-bound opportunity packet into one conservative result:

- `PRIME_READY`
- `TEAMING_READY`
- `HOLD`
- `NO_BID`

It is designed for the recurring commercial question: **does the evidence actually support a direct-prime route, a teaming route, neither route yet, or a hard no-bid?**

## Evidence model

A packet binds five things:

1. an opportunity identity and current trusted evaluation time;
2. buyer sources, separated into `OFFICIAL` and `SECONDARY`;
3. capability sources for the prime and any proposed team member;
4. mandatory and scoreable requirement records tied to exact buyer sources; and
5. exact evidence records tied to immutable source digests.

Mandatory requirements cannot become green from a procurement mirror. They must bind an `OFFICIAL` buyer source. Likewise, readiness evidence must bind an `OFFICIAL` capability source rather than an unverified summary.

Every requirement carries:

- a stable `gate_id`;
- category;
- mandatory vs scoreable status;
- route (`PRIME`, `TEAM`, or `BOTH`);
- cure policy (`NONE` or `PARTNER`);
- exact buyer-source binding;
- prime evidence state + evidence IDs; and
- team evidence state + evidence IDs.

`MISSING` may not carry evidence. `PASS` and `FAIL` must carry source-bound evidence. Duplicate IDs, same-ID changed payloads, source drift, subject/category drift, future evidence, expired capability evidence, and malformed input fail closed.

## Route semantics

For `PRIME_READY`, every mandatory `PRIME`/`BOTH` requirement must be satisfied by prime evidence.

For `TEAMING_READY`, the buyer must explicitly allow teaming in an official source. A missing or failed prime requirement may be cured by partner evidence only when the requirement says `cure: PARTNER`. A `BOTH` requirement must be satisfied on both sides.

A non-curable failed mandatory requirement can make a route impossible. Missing evidence normally produces `HOLD`, not an invented failure. An expired proposal deadline produces `NO_BID` unless the packet has been updated to an officially evidenced live extension.

Scoreable gaps are reported but never promoted into mandatory facts.

## Deadlines

Proposal and question deadlines are each tied to exact buyer source IDs.

The proposal deadline affects disposition. The question deadline is tracked as urgency metadata only.

An official addendum can move the proposal deadline by supplying the new timestamp and binding the deadline field to the addendum's official source record. The engine does not scrape or infer an extension.

## Determinism and receipts

Input lists are canonicalized by stable IDs, then committed into `input_digest`.

The receipt includes:

- exact disposition and reasons;
- prime/team route status;
- package-source truth;
- scoreable gaps;
- counts;
- a fixed external-action authority ceiling; and
- a final `receipt_digest`.

`verify_receipt()` recomputes the digest and also refuses any receipt whose authority flags are no longer all `false`.

`render_markdown()` renders only a verified receipt.

## Strict JSON

Use `loads_strict()` when reading packet JSON. It rejects duplicate keys, floats, NaN/Infinity, unknown fields, malformed canonical UTC values, malformed SHA-256 values, unsafe URL forms, and several common credential shapes.

Example invocation:

```bash
python engine.py packet.json \
  --as-of 2026-09-13T10:00:00Z \
  --markdown qualification.md
```

The trusted `--as-of` value must exactly match the packet `as_of`.

## Commercial boundary

This module evaluates supplied evidence only. It does not contact a buyer or partner, log into a procurement portal, register an entity, submit questions or proposals, commit pricing, sign anything, move money, deploy a service, or assert an award or recognized revenue.

`PRIME_READY` and `TEAMING_READY` are evidence-package states for a human commercial decision, not external-action execution.

## Validation

From this directory:

```bash
python -m py_compile engine.py test_engine.py
python -m unittest -v test_engine.py
python -O -m unittest -v test_engine.py
```

The hostile suite covers direct-prime and team routes, non-curable failures, missing evidence, secondary-source limitations, official deadline extensions, future/expired evidence, replay/conflict behavior, strict types and JSON, credential-shaped text, receipt tampering, and input-order invariance.
