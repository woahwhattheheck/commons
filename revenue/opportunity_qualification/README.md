# Opportunity Qualification Engine

Reusable offline qualification for public RFPs, paid-work solicitations, and teaming opportunities.

The engine converts a source-bound opportunity packet plus an independently retained controlling-package completeness manifest into one conservative result:

- `PRIME_READY`
- `TEAMING_READY`
- `HOLD`
- `NO_BID`

It is designed for the recurring commercial question: **does the evidence actually support a direct-prime route, a teaming route, neither route yet, or a hard no-bid?**

## Two trust inputs

The qualification packet binds:

1. opportunity identity and trusted evaluation time;
2. buyer sources separated into `OFFICIAL` and `SECONDARY`;
3. capability sources for the prime and any proposed team member;
4. mandatory and scoreable requirement records tied to exact buyer sources; and
5. exact capability evidence tied to immutable source digests.

The packet is intentionally **not allowed to prove that its own requirement list is complete**. `PRIME_READY`, `TEAMING_READY`, and requirement-derived `NO_BID` additionally require a separate `tjlabs.opportunity-qualification-completeness/v1` manifest supplied through the `trusted_completeness` argument or CLI `--completeness` file.

That manifest is an out-of-band extraction commitment. It binds:

- opportunity ID;
- controlling buyer source ID + SHA-256;
- extraction time + retained extraction-evidence SHA-256;
- an exact `complete` boolean;
- expected gate count;
- canonical gate-set SHA-256; and
- every expected gate's ID, category, mandatory/scoreable status, route, cure policy, buyer source ID + SHA-256, and description SHA-256.

The engine compares that independent commitment against the packet's observed gate descriptors. Omitting a mandatory gate, omitting a scoreable category, dropping an addendum-derived gate, changing route/cure/category, changing a buyer-source binding, or changing requirement text breaks the commitment and forces `HOLD`.

A missing completeness manifest also forces `HOLD` for any result that would otherwise assert package readiness or a requirement-derived no-bid. A separately buyer-official expired proposal deadline may still produce `NO_BID` because that negative fact does not depend on requirement-set completeness.

**Do not generate the trusted completeness manifest from the same packet at consumption time.** It is the independently retained output of the controlling-package extraction/review boundary.

## Requirement and evidence semantics

Mandatory requirements cannot become green from a procurement mirror; they must bind an `OFFICIAL` buyer source. Readiness evidence must bind an `OFFICIAL` capability source rather than an unverified summary.

Every requirement carries a stable `gate_id`, category, mandatory status, route (`PRIME`, `TEAM`, or `BOTH`), cure policy (`NONE` or `PARTNER`), exact buyer-source binding, and prime/team evidence state + evidence IDs.

`MISSING` may not carry evidence. `PASS` and `FAIL` must carry source-bound evidence. Duplicate IDs, same-ID changed payloads, source drift, subject/category drift, future evidence, expired capability evidence, malformed input, duplicate JSON keys, floats, and non-finite numbers fail closed.

For `PRIME_READY`, every mandatory `PRIME`/`BOTH` gate must be satisfied by prime evidence **and** package completeness must verify.

For `TEAMING_READY`, the buyer must officially allow teaming, the applicable mandatory gates must be satisfied under their cure rules, **and** package completeness must verify. A `BOTH` gate must be satisfied on both sides.

A non-curable failed mandatory gate can make a route impossible only when the independently committed gate set is complete. Missing evidence normally produces `HOLD`, not an invented failure. Scoreable gaps are reported but never promoted into mandatory facts.

## Deadlines

Proposal and question deadlines are each tied to exact buyer source IDs. The proposal deadline affects disposition; the question deadline is urgency metadata only.

An official addendum can move a proposal deadline by supplying the new timestamp and binding that field to the addendum's official source record. The engine does not scrape or infer extensions.

## Determinism and receipts

Packet lists are canonicalized by stable IDs and committed into `input_digest`. The receipt records exact disposition/reasons, route status, package-source truth, completeness verification + expected/observed gate commitments, scoreable gaps, counts, a fixed false external-action authority ceiling, and `receipt_digest`.

`verify_receipt()` checks receipt integrity and refuses any receipt whose authority flags are no longer all `false`. `verify_receipt_against_inputs()` is stronger: it recompiles using the packet, trusted clock, and the same independent completeness manifest and compares canonical bytes.

`render_markdown()` renders only an integrity-verified receipt.

## CLI

Use strict JSON for both inputs. The CLI requires the independent completeness file:

```bash
python engine.py packet.json \
  --completeness completeness.json \
  --as-of 2026-09-13T10:00:00Z \
  --markdown qualification.md
```

The trusted `--as-of` value must exactly match packet `as_of`. The completeness extraction time may not be in the future relative to that trusted clock.

## Commercial boundary

This module evaluates supplied evidence only. It does not contact a buyer or partner, log into a procurement portal, register an entity, submit questions or proposals, commit pricing, sign anything, move money, deploy a service, or assert an award or recognized revenue.

`PRIME_READY` and `TEAMING_READY` are evidence-package states for a human commercial decision, not external-action execution.

## Validation

From this directory:

```bash
python -m py_compile engine.py engine_core.py test_engine.py test_authority_overlay.py
python -m unittest -v
python -O -m unittest -v
```

The hostile suite covers direct-prime/team routes, non-curable failures, official-vs-secondary authority, extensions, future/expired evidence, replay/conflict behavior, strict types/JSON, credential-shaped text, receipt tampering, input-order invariance, missing completeness, mandatory and scoreable gate omission, addendum-gate omission, route drift, controlling-source drift, incomplete extraction, manifest tampering, and trust-input re-verification.
