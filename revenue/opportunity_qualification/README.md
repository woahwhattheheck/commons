# Opportunity Qualification Engine

Reusable offline qualification for public RFPs, paid-work solicitations, and teaming opportunities.

The engine produces one conservative result: `PRIME_READY`, `TEAMING_READY`, `HOLD`, or `NO_BID`.

## Trust model

Qualification has **three distinct inputs**:

1. the opportunity packet (buyer/capability sources, evidence, requirements, deadlines);
2. an independently retained controlling-package completeness manifest; and
3. the independently retained canonical SHA-256 of that manifest.

The packet is intentionally not allowed to prove that its own requirement list is complete. The completeness manifest is `tjlabs.opportunity-qualification-completeness/v1` and binds:

- opportunity ID;
- controlling buyer source ID + SHA-256;
- extraction time + retained extraction-evidence SHA-256;
- exact `complete` boolean;
- expected gate count and canonical gate-set SHA-256; and
- every expected gate's ID, category, mandatory/scoreable status, route, cure policy, buyer source ID + SHA-256, and description SHA-256.

The separate verifier trust root (`trusted_completeness_sha256` / CLI `--completeness-sha256`) must equal the canonical SHA-256 of the normalized manifest. It is the external commitment that prevents a caller from deleting a requirement and regenerating both the packet and manifest at consumption time.

**Do not derive that expected manifest digest from the qualification packet or from a newly supplied manifest during verification.** Retain it independently when the controlling-package extraction is reviewed/finalized. The repository fixture demonstrates this as two separate artifacts: `completeness_fixture.json` and `completeness_fixture.sha256`.

Without both the manifest and its independently supplied expected digest, package completeness is unverified. Any would-be `PRIME_READY`, `TEAMING_READY`, or requirement-derived `NO_BID` becomes `HOLD`. A separately buyer-official expired proposal deadline may still produce `NO_BID`, because that fact does not depend on requirement-set completeness.

Omitting a mandatory gate, omitting a scoreable category, dropping an addendum-derived gate, changing route/cure/category, changing a buyer-source binding/digest, or changing requirement text breaks the committed gate set and fails closed.

## Requirement and evidence semantics

Mandatory gates cannot green from procurement mirrors; they must bind `OFFICIAL` buyer sources. Capability readiness evidence must bind `OFFICIAL` capability sources.

Each requirement has a stable gate ID, category, mandatory flag, route (`PRIME`, `TEAM`, `BOTH`), cure policy (`NONE`, `PARTNER`), buyer-source binding, and prime/team evidence state + evidence IDs. `MISSING` cannot carry evidence. `PASS`/`FAIL` require evidence. Duplicate IDs, same-ID changed payloads, source/subject/category drift, future or expired evidence, duplicate JSON keys, floats/non-finite numbers, malformed digests/URLs, and credential-shaped text fail closed.

`PRIME_READY` requires all applicable mandatory prime gates plus verified package completeness. `TEAMING_READY` additionally requires buyer-official teaming authority and all applicable partner/cure gates. Scoreable gaps are reported without being promoted into mandatory facts.

## Negative authority

A non-curable mandatory failure may produce a gate-derived `NO_BID` only when the committed package completeness boundary verifies. An expired proposal deadline can independently produce `NO_BID` only when the controlling package and the deadline source are buyer-official. Secondary mirrors cannot close the team route or force deadline expiry authority.

An official addendum may move a deadline or carry a requirement only when it is represented as an official buyer source and committed through the relevant field/gate. The engine does not scrape or infer addenda.

## Determinism and receipts

Packet lists are canonicalized by stable IDs and bound into `input_digest`. Receipts record disposition/reasons, prime/team route status, requirement-only readiness diagnostics, package source truth, expected/observed completeness commitments, scoreable gaps, counts, fixed-false external-action authority, and `receipt_digest`.

`verify_receipt()` verifies receipt integrity and refuses authority mutations. `verify_receipt_against_inputs()` is stronger: it recompiles against the packet, trusted time, completeness manifest, and independently retained manifest SHA-256, then compares canonical bytes.

## CLI

```bash
python engine.py packet.json \
  --completeness completeness.json \
  --completeness-sha256 <independently-retained-manifest-sha256> \
  --as-of 2026-09-13T10:00:00Z \
  --markdown qualification.md
```

Both JSON inputs are parsed strictly. The trusted `--as-of` must equal packet `as_of`; completeness extraction time cannot be in the future relative to it.

## Commercial boundary

This module evaluates supplied evidence only. It does not contact buyers/partners, log into portals, register entities, submit questions/proposals, commit pricing, sign, spend, mutate payment providers, deploy, assert an award, or recognize revenue.

`PRIME_READY` / `TEAMING_READY` are evidence-package states for a human commercial decision, never external-action authority.

## Validation

From this directory:

```bash
python -m py_compile engine.py engine_core.py test_engine.py test_authority_overlay.py
python -m unittest -v
python -O -m unittest -v
```

The hostile suite covers original route/evidence semantics plus retained-manifest/root matching, missing trust inputs, caller-regenerated manifest attacks, mandatory/scoreable/category omission, addendum-gate omission, route drift, controlling-source drift, incomplete extraction, manifest tampering/future time/type aliases, requirement-derived NO_BID gating, official deadline expiry, and full re-verification against trust inputs.
