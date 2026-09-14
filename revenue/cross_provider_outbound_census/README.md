# Cross-Provider Outbound Census

`revenue.cross_provider_outbound_census` is a **preflight collision-history gate**
for one failure class: the same logical outbound opportunity can have multiple
provider routes or official fallback transports, so a clean result from one
provider is not proof that the opportunity has never already been touched through
another route.

The motivating incident was a one-per-person GitHub bounty that looked unclaimed
in current GitHub state while authenticated Gmail history showed that the same
account had already submitted through the issue's official email fallback after a
GitHub-App failure.  The same class can hit sales outreach when workers inspect
different provider-local histories seconds apart.

## v2 authority boundary

The v1/r3 carrier was correctly STOP-MERGE reviewed because its candidate JSON
could mint all three facts needed to produce a clean result:

1. the evaluation clock (`trusted_now`),
2. the fallback/alias universe, and
3. the provider census snapshots/events.

That made a historical replay, omitted fallback, or forged `COMPLETE`/empty
snapshot capable of manufacturing `CLEAR_FOR_DOWNSTREAM_GATES`.

v2 removes those facts from claimant input.

The candidate may supply only:

- the already-canonical `outbound-connector-lease/v1` seam input; and
- the current intent (`provider`, route commitment, opaque claimant/claim scopes,
  and `requested_at`).

Operational `compile_current()` then obtains:

- **current time from process UTC**, not an argument in claimant JSON and not a
  CLI `--trusted-now` option;
- the **fallback registry from a host-owned `RetainedAuthoritySource`** keyed by
  the canonical lease seam; and
- one **retained per-provider census generation** from that same host capability
  for every provider named by the retained registry.

A historical `audit_census(..., historical_as_of=...)` mode remains available for
deterministic inspection, but its strongest result is `AUDIT_ONLY_CLEAR`.  It has
no `clear_until`, cannot be passed to `verify_current()`, and is never operational
send-preflight authority.

## Trust contract

`RetainedAuthoritySource` is a host capability boundary, not candidate data.
Concrete deployments are responsible for reading authenticated, retained
connector/registry state before returning records.  The module deliberately does
**not** provide a "load authority from caller path/JSON" operational shortcut.

The source has three obligations:

1. `authority_id` identifies the retained authority source/generation family;
2. `load_alias_registry(seam_sha256)` returns the independently retained registry
   for exactly that canonical opportunity seam;
3. `load_provider_census(seam_sha256, provider, registry_generation)` returns the
   trusted current census generation for that provider, or `None` when no complete
   retained record exists.

If deployment code lets the claimant implement/replace that host capability, the
trust boundary has already been broken outside this module.  Treat it like any
other trusted connector/session authority, not as a request field.

## Retained alias registry

Registry schema:

```json
{
  "schema": "commons-cross-provider-outbound-census/alias-registry-v1",
  "authority_id": "host-retained-census-v1",
  "seam_sha256": "<canonical outbound lease seam>",
  "generation": 7,
  "generated_at": "2026-09-14T03:29:40Z",
  "aliases": [
    {"provider": "github", "route_sha256": "<sha256>"},
    {"provider": "gmail", "route_sha256": "<sha256>"}
  ],
  "receipt_sha256": "<canonical receipt>"
}
```

The receipt binds the exact route universe, generation, authority id, seam, and
registry timestamp.  Candidate input cannot omit Gmail (or add a fake route)
because candidate input contains no alias field at all.

## Retained provider census generation

Each provider named by the retained registry must produce one retained census
record:

```json
{
  "schema": "commons-cross-provider-outbound-census/provider-census-v1",
  "authority_id": "host-retained-census-v1",
  "seam_sha256": "<canonical outbound lease seam>",
  "provider": "gmail",
  "registry_generation": 7,
  "registry_receipt_sha256": "<exact alias registry receipt>",
  "generation": 11,
  "query_generation": 19,
  "status": "COMPLETE",
  "observed_at": "2026-09-14T03:29:56Z",
  "query_sha256": "<commitment to exact provider query>",
  "covered_routes": ["<gmail route sha256>"],
  "events": [],
  "receipt_sha256": "<canonical receipt>"
}
```

The provider receipt binds both the registry generation **and the exact registry
receipt**, so a provider census cannot be transplanted onto a materially different
fallback set that happens to reuse the same integer generation.  `query_generation`
and `query_sha256` bind the provider query generation and exact query commitment.

Known events use route commitments and PII-free evidence commitments only:

- `PROVIDER_SENT`
- `HUMAN_REPLY`
- `AUTO_REPLY`
- `HARD_BOUNCE`
- `SOFT_BOUNCE`
- `PROVIDER_REJECTED`
- `UNSUBSCRIBE`
- `DNR`
- `AMBIGUOUS_EFFECT`

## Currentness policy

Operational currentness is fixed:

- intent maximum age: **300 seconds**;
- provider census maximum age: **300 seconds**;
- provider census must be at or after the retained registry generation time;
- provider census must be at or after the current intent;
- future intent, future registry generation, or future provider census => HOLD;
- a current packet may be re-verified for at most **30 seconds** after its process
  evaluation instant, and never after `clear_until`.

`compile_current()` has no public clock parameter.  Unit tests patch the private
process-clock function; production claimant data cannot.

## Fail-closed states

A current packet deterministically HOLDs when any of the following is true:

- current intent route is absent from the retained registry;
- a retained provider census is missing;
- provider census is `THROTTLED`, `UNAVAILABLE`, or `AMBIGUOUS`;
- provider census is stale, future, before the retained registry, or before the
  current intent;
- exact registered route coverage is missing or contains unknown routes;
- prior send, human reply, or auto reply exists anywhere in the retained route
  universe;
- unsubscribe or DNR evidence exists;
- hard/soft bounce or provider rejection exists (route repair required);
- ambiguous provider effect exists;
- registry/provider receipt, authority id, seam, generation, registry receipt,
  route binding, query generation, or evidence binding is inconsistent.

Known historical events remain visible in the output even if the provider itself
is throttled/unavailable/ambiguous; incomplete coverage cannot erase a known touch.

## Operational API

```python
from revenue.cross_provider_outbound_census import compile_current

packet = compile_current(candidate_intent, retained_authority_source)
```

`retained_authority_source` must be a host-owned `RetainedAuthoritySource`.
There is intentionally no operational CLI that accepts fallback aliases, provider
snapshots, an authority directory, or `--trusted-now` from the claimant.

Verification reacquires process UTC and freshly reads retained authority:

```python
from revenue.cross_provider_outbound_census import verify_current

result = verify_current(packet, candidate_intent, retained_authority_source)
```

Verification rejects:

- packet receipt mutation;
- future packet evaluation time;
- packets older than 30 seconds;
- expired clean packets;
- candidate input drift;
- alias registry generation/receipt drift;
- provider generation/query/receipt drift;
- any packet produced by historical audit mode.

## Authority ceiling

The strongest operational decision is `CLEAR_FOR_DOWNSTREAM_GATES`.  It means only
that the independently retained cross-provider collision history is complete,
current, and clean for the exact canonical lease seam.

Every packet hard-codes:

- `external_send_authorized = false`
- `lease_authorized = false`
- `provider_mutation_authorized = false`

The existing outbound connector lease, organization pressure/custody controls,
terminal send authority, provider-bound consumer, and post-send forensics remain
mandatory.  This module never contacts Gmail, GitHub, Slack, customers, payment
providers, or any other external system.

## Hostiles covering the STOP-MERGE review

The focused suite includes explicit regressions for the three review blockers:

1. **omitted Gmail fallback** — claimant JSON has no alias authority; retained
   registry still requires Gmail, and a retained Gmail `PROVIDER_SENT` blocks the
   GitHub retry;
2. **forged `COMPLETE`/empty Gmail history** — claimant-supplied `snapshots` is an
   unknown field and rejected; only the retained provider generation is consumed;
3. **historical clock resurrection** — `compile_current()` has no `trusted_now`
   argument; historical evaluation is audit-only and `verify_current()` rejects
   audit packets.

Additional hostiles cover receipt tamper, same-generation/different-registry
receipt transplant, authority-id mismatch, registry/provider generation drift,
provider evidence on unregistered routes, future/stale/before-intent/before-registry
census, known events under throttled state, packet age, packet mutation, and input
drift.
