# OHSU ERP RFP 2027-0005 — qualification + paid workshare evidence carrier

This carrier converts the **public OHSU bid notice** for `RFP-2027-0005` into a deterministic, fail-closed owner-review packet. It does **not** claim that the public notice is the controlling RFP package and does not infer qualifications that have not been sourced.

## Public source facts bound here

The reviewed public OHSU bids notice identifies **Enterprise Resource Planning (ERP) Assessment and Advisory Services**, issued **2026-08-21**, with intent to bid dated **2026-09-16** and proposal due **2026-09-25**. Its public scope is a comprehensive current ERP landscape assessment, future-state requirements, and an ERP modernization roadmap aligned to institutional goals, operational scale, and regulatory obligations. The notice names Royce Bitter, Senior Sourcing Manager, as contact. Source: `https://www.ohsu.edu/procurement/bids`.

`profile.json` intentionally sets `controlling_rfp_pack_materialized=false`. Changing the public dates, title, contact, URL, or scope is a contract error instead of a way to widen readiness.

## Commercial hypothesis — not a sale

A bounded **$15,000 fixed paid workshare / 10 business days** is compiled into every packet as `PROPOSED_NOT_ACCEPTED`:

- current-state ERP system/interface/owner/dependency inventory;
- future-state requirement traceability (source, owner, gap, validation status);
- data + integration dependency map and migration/reconciliation risks;
- option/TCO scenario scoring with explicit assumptions/sensitivities;
- modernization-roadmap evidence register with risks, dependencies, validation actions.

This is designed to sit behind a qualified ERP advisory prime if Token Junkie Labs cannot truthfully prove prime eligibility from the controlling pack. It is not OHSU pricing and is not accepted work until an authorized counterparty actually agrees.

## State machine

The strongest state is **owner review only**. No state authorizes contact, intent filing, proposal submission, contracting, payment, or revenue recognition.

- `HOLD_CONTROLLING_PACK` — exact controlling pack is not materialized.
- `HOLD_REQUIREMENT_REGISTRY` — pack digest exists but mandatory requirements have not been extracted/reviewed.
- `HOLD_MANDATORY_REQUIREMENTS` — at least one mandatory requirement is `MISSING` or `UNKNOWN`.
- `TEAMING_CANDIDATE` — requirements are evidenced, but no confirmed prime teaming commitment exists.
- `READY_FOR_OWNER_TEAMING_REVIEW` — reviewed requirements + explicit prime commitment evidence exist; still no external action authority.
- `READY_FOR_OWNER_PRIME_REVIEW` — reviewed requirements support an owner prime-route review; this is **not** OHSU eligibility verification.
- deadline/intent HOLD states fail closed when the public page gives a date but no independently verified submission time.

The public `compile_current()` surface owns the current UTC date. There is no `--as-of` or caller-supplied production clock. The private `_compile_at()` exists for deterministic tests only.

## Evidence boundary

A SHA-256 in bidder facts is a **content commitment**, not authentication. This code cannot prove that a caller-supplied pack, requirement artifact, intent receipt, or prime commitment came from OHSU or a prime. The packet therefore carries `controlling_pack_authenticity_verified=false` and `requirement_evidence_authenticity_verified=false`, and every external authority bit is fixed false.

Once the full RFP pack is obtained, extract each mandatory obligation into the requirement registry instead of encoding guessed requirements in source. Mandatory `UNKNOWN`/`MISSING` values HOLD.

## CLI

The CLI has no pathname input/output side effects. It accepts one bounded strict-JSON envelope on stdin and emits canonical JSON on stdout:

```bash
python -m revenue.ohsu_erp_rfp_2027_0005.qualification compile < input.json
python -m revenue.ohsu_erp_rfp_2027_0005.qualification verify < verify.json
```

Duplicate JSON keys, non-finite numbers, non-canonical digests, bool/int aliasing, duplicate requirement IDs, and notice drift are controlled refusals.

## Tests

```bash
python -m unittest revenue.ohsu_erp_rfp_2027_0005.test_qualification
python -O -m unittest revenue.ohsu_erp_rfp_2027_0005.test_qualification
```

The hostile suite covers notice/date/scope drift, missing/unknown requirements, fabricated readiness routes, absent prime commitment, intent chronology, unknown deadline times, duplicate keys/IDs, digest shape, ordering, and CLI controlled refusal.
