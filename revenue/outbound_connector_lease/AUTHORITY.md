# Canonical production outbound seam authority

## Decision

For any externally visible outbound mutation from the swarm, the **only**
production mutual-exclusion seam is the closed-schema connector-native lease in
`revenue/outbound_connector_lease/`.

The authoritative identity is:

```text
outbound-connector-lease/v1/<sha256(canonical seam JSON)>
```

and the decisive atomic event is an exact successful GitHub create of that branch
from current `main`. A pre-existing ref, any provider/transport error, or an
ambiguous branch-create result is `HOLD`.

This file narrows mutex authority only. It does not weaken or replace buyer,
content, legal, route, cooldown, payment, owner, provider-history, or other
outbound gates.

## Why one seam

Commons also contains `revenue/outbound_mutex/`, merged by #14266. Its reference
CAS machinery is useful for local/offline modeling, but its key is derived from a
caller-authored free-form `opportunity` string plus channel and destination.
Two workers can therefore describe one commercial situation differently and
obtain different keys.

Example of the forbidden split:

```text
SigNoz / $2,500 survival proof
signoz agent reliability pilot
```

for the same destination. Those labels are semantically aliases but hash to
different legacy lease paths.

The connector lease predates that helper and intentionally closes this class of
alias: `buyer_scope` is the organization primary domain and opportunity identity
is one of three exact schemas. Price, contact, route, subject and draft are not
identity fields.

Therefore a `revenue/outbound_mutex` document — active, released, sent, or
otherwise — **never satisfies the production outbound mutex prerequisite**.
Do not create a new legacy lease as a substitute after a connector branch already
exists or after connector branch creation fails/returns ambiguously.

## Required sequence

1. Re-read authoritative provider history and coordination evidence.
2. Resolve the organization's canonical primary domain (`buyer_scope`).
3. Compile exactly one connector seam:
   - external: issuer/source domain + stable authoritative opportunity ID;
   - cold: exact `{"kind":"cold"}` at organization scope;
   - reply: provider + exact durable human inbound event ID.
4. Optionally run `authority.py` over the compiled document. It validates identity
   shape only and always returns `external_send_authorized=false`.
5. Atomically create the exact compiled GitHub branch. Only exact create success
   establishes the mutex prerequisite.
6. Re-read provider history immediately before mutation. Any relevant change
   means stop and re-evaluate.
7. Apply all independent owner/content/legal/route/cooldown/payment gates.
8. Perform at most one provider mutation.
9. Persist the canonical provider SENT/outcome receipt immediately. If provider
   outcome is ambiguous, do not retry; reconcile provider state.

## Legacy migration rule

Existing historical `coordination/outbound/leases/*.json` records remain evidence
and must not be erased or rewritten to fabricate continuity. They may be useful
for incident analysis, but they are not production send clearance.

A worker facing both systems must choose the connector seam and treat legacy state
conservatively as additional evidence. A legacy `sent` observation can make a
send less permissible; it can never make a send more permissible.

## Mechanical admission

`revenue/outbound_connector_lease/authority.py` accepts only exact compiled output
from `key.py`, recomputes the branch/digest, rejects extra identity fields, and
explicitly rejects the #14266 legacy lease shape.

A successful admission means only:

```text
CANONICAL_MUTEX_PREREQUISITE
```

with:

```text
atomic_branch_create_required=true
provider_reread_required=true
legacy_mutex_accepted=false
external_send_authorized=false
```

The atomic GitHub branch creation and live provider readback still have to happen
outside this offline validator.
