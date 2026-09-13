# Scope-to-delivery trusted-time gate

`host/scope_to_delivery.py` remains the canonical content composer for agreements,
work packets, execution evidence, delivery receipts, invoice state, and money
state. Its historical projection is deterministic, but the v1 schemas do not by
themselves establish that the agreement or observations are temporally current.

`host/scope_to_delivery_time_gate.py` is the temporal/provenance prerequisite
before treating a composed `LOCKED_SOW`, `ISSUED` work packet, or execution
observation as current work authority.

## One-artifact composition contract

Current-work authority now requires **one exact input pair to satisfy both gates**.
The authority-producing library boundary is `evaluate_bytes()`:

1. It receives the exact agreement bytes and optional exact observation bytes.
2. It bounds the bytes, strict-parses them with duplicate-key rejection, and
   derives each raw SHA-256 from the same bytes it parsed.
3. It passes those same parsed objects through the canonical
   `scope_to_delivery.py` composer using the repository's canonical catalog and
   bindings. A partial or schema-drifted temporal lookalike cannot obtain
   `canonical_scope_validated=true`.
4. It derives `canonical_project_sha256` from that same-input canonical project.
5. A caller must supply the canonical project it plans to consume. That project
   must hash exactly to the internally derived project. Otherwise evaluation
   fails closed. Omitting the project yields `HOLD_CANONICAL_PROJECT_UNBOUND`.

This prevents a canonical agreement **A** from being paired with a same-ID temporal
agreement **B**, including when both A and B are individually complete and valid.
The same rule binds observation sets. `verify_project_binding(project, receipt)` is
the executable downstream check for a project/temporal-receipt pair.

`evaluate()` remains available only as a parsed-object chronology helper. Parsed
objects cannot prove exact raw-byte custody or canonical-project identity, so that
path emits `provenance_mode=CANONICAL_OBJECT_ONLY` and can never set
`current_work_authorized=true`.

## Required current-work conditions

For `current_work_authorized=true`, all of the following must hold:

- `raw_byte_provenance_verified=true` and
  `provenance_mode=EXACT_RAW_BYTES_VERIFIED`;
- `canonical_scope_validated=true` for the same exact parsed agreement and
  observation objects;
- `canonical_project_bound=true`, meaning the supplied canonical project digest
  equals the project derived from those same objects;
- the canonical agreement is `commons-scope-agreement/v1` / `SCOPE_AGREEMENT`
  and satisfies the canonical catalog/terms/buyer/acceptance-row contract;
- any observations satisfy the full canonical observation schema and bind the
  same agreement;
- `written_acceptance.status` is `PRESENT` with a real `accepted_at`;
- acceptance is no later than the contracted window end and no later than the
  trusted verifier clock;
- the trusted verifier clock is inside the contracted work window;
- every execution observation is at or after acceptance, inside the work window,
  and no later than the trusted verifier clock.

Duplicate observation identities, duplicate JSON keys, malformed timestamps,
symlinked/non-regular input files, oversized inputs, future evidence, partial
same-ID temporal lookalikes, and canonical-project mismatches all fail closed.

Raw and canonical hashes deliberately mean different things. Insignificant JSON
formatting may preserve the canonical SHA-256 while changing the raw SHA-256. The
canonical project commitment binds semantics/output; the raw hashes bind the exact
input byte custody.

An expired window produces `HOLD_WINDOW_EXPIRED`. Historical observations that
were chronologically valid remain auditable, but an old `PRESENT` acceptance
cannot start new work after the window closes.

## CLI

First compose the canonical project from the exact agreement/observations to be
used:

```text
python3 host/scope_to_delivery.py project \
  --agreement revenue/scope_to_delivery/fixtures/accepted_agreement.json \
  --observations revenue/scope_to_delivery/fixtures/accepted_observations.json \
  > /tmp/scope-project.json
```

Then evaluate those same exact input files and bind that project:

```text
python3 host/scope_to_delivery_time_gate.py \
  --agreement revenue/scope_to_delivery/fixtures/accepted_agreement.json \
  --observations revenue/scope_to_delivery/fixtures/accepted_observations.json \
  --project /tmp/scope-project.json
```

The CLI captures exact regular-file bytes with `O_NOFOLLOW` and process UTC. It
exposes no caller-controlled `--as-of` or raw-digest override. `--project` may be
omitted only for diagnostic/HOLD evaluation; without a bound project, a current
window cannot return exit `0`.

Exit codes:

- `0`: exact-byte temporal prerequisite is ready and the canonical project is
  exactly bound at the verifier's current UTC instant;
- `3`: truthful temporal/provenance/binding HOLD;
- `2`: malformed, ambiguous, future, out-of-window, unsafe, or mismatched evidence.

## Authority ceiling

This gate proves chronology, exact input-byte custody, and same-input canonical
project binding. It does **not** grant buyer/provider contact, send, contract or
signature execution, fulfillment, deployment, invoice/payment mutation, cash,
spend, or revenue authority. Delivery/payment/provider/cash gates remain
independently mandatory.

Every receipt therefore carries false external-action/payment/delivery/revenue
authority flags. The public August 28 synthetic fixture remains intentionally
historical and must return `HOLD_WINDOW_EXPIRED` at current September 2026 time.
