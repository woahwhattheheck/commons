# Canonical outbound opportunity/reply seam authority

## Decision

`revenue/outbound_connector_lease/` is the canonical **opportunity/reply seam** for
external outbound work. It is not, by itself, the sole production mutex for an
organization.

The connector seam identity is:

```text
outbound-connector-lease/v1/<sha256(canonical seam JSON)>
```

and the decisive atomic event for that seam is an exact successful GitHub create
of that branch from current `main`. A pre-existing ref, any provider/transport
error, or an ambiguous branch-create result is `HOLD` for that opportunity seam.

This layer intentionally does not claim to serialize every simultaneous
opportunity at one organization and does not prove that a caller-supplied domain
is the organization's one authoritative identity.

## What this fixes

Commons also contains `revenue/outbound_mutex/`, merged by #14266. Its reference
CAS machinery hashes caller-authored free-form `opportunity + channel +
destination`. Two workers can therefore describe one commercial situation
differently and obtain different legacy lease paths.

Example of the forbidden split:

```text
SigNoz / $2,500 survival proof
signoz agent reliability pilot
```

for the same route/destination. The closed connector schema removes price,
recipient, route, subject and draft from one opportunity/reply identity, so those
labels cannot mint parallel canonical opportunity seams.

A `revenue/outbound_mutex` document — active, released, sent or otherwise — never
satisfies the canonical opportunity/reply seam prerequisite. Historical legacy
records remain conservative evidence; they are not send clearance.

## Explicit limits

The connector key compiler performs syntactic normalization, not semantic
organization resolution. These are deliberately different connector seams:

- one buyer scope with `cold` versus an `external` opportunity;
- one buyer scope with external opportunity A versus external opportunity B;
- `example.com` versus `www.example.com` as caller-supplied buyer scopes;
- two syntactically valid authority domains chosen for the same real source.

Therefore exact branch-create success for a connector seam does **not** prove
organization-wide mutual exclusion. `authority.py` makes that ceiling mechanical
with:

```text
organization_scope_authority_required=true
organization_wide_mutex_required=true
production_mutex_complete=false
external_send_authorized=false
```

This PR does not invent a replacement organization-wide lock or bless an
unmerged/SOURCE-RED carrier as authority.

## Required composition and lock order

When production policy requires both organization-wide pile-on prevention and an
opportunity/reply seam, acquire them in one order only:

1. **Authoritative organization scope first.** Resolve the buyer to retained,
   current organization identity evidence. A guessed domain, convenient
   subdomain, alternate brand domain or stale alias mapping is not authority.
2. **Organization-wide atomic mutex second.** Use the current landed and
   independently validated organization-level pressure/lease authority. If none
   is available for a path that requires one, `HOLD`; do not substitute the
   connector seam or any SOURCE-RED/unmerged carrier.
3. **Canonical opportunity/reply seam third.** Compile the closed connector
   schema and atomically create exactly its GitHub branch.
4. **Provider readback next.** Re-read authoritative provider history immediately
   before mutation. Any relevant change means stop and re-evaluate.
5. Apply every independent owner/content/legal/route/cooldown/payment gate, then
   perform at most one provider mutation.
6. Persist the canonical provider outcome immediately. Ambiguous provider outcome
   means reconcile; never retry blindly.

Never acquire these layers in the reverse order to race another worker. If a
later prerequisite fails after an organization-wide lease was acquired, follow
that authority's own release/expiry contract; do not improvise a new unlock or
mint a variant identity.

## Mechanical admission

`revenue/outbound_connector_lease/authority.py` accepts only exact compiled output
from `key.py`, recomputes branch/digest, rejects extra identity fields, and
explicitly rejects the #14266 legacy lease shape.

A successful admission means only:

```text
CANONICAL_OPPORTUNITY_SEAM_PREREQUISITE
```

It confirms one closed-schema connector seam. It explicitly does not certify
organization identity, organization-wide exclusivity, production readiness or
external-send authority.
