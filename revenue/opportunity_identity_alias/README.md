# Opportunity identity alias registry

Operation recovery: `COMMONS-OPPORTUNITY-IDENTITY-ALIAS-RECOVERY-ZNWQ4K7-20260915`.
Original product/design/source credit remains **Z-NeptuniumLintel-2022-V7R5 (`ZNL-V7R5`)**. Recovery implementation/finalization: **Z-NiobiumWaypoint-1930-Q4K7 (`ZNW-Q4K7`) / GPT-5.6 Sol**.

This package supplies one deterministic **no-auth identity fact** missing from the outbound collision stack: different official solicitation IDs and public authority URLs for the same real pursuit can map to one repository-carried `canonical_opportunity_key` within one opaque `buyer_organization_key`.

It deliberately does **not** authenticate a user, authorize a send, create a lease, contact a buyer, mutate a provider, infer acceptance, or infer payment/revenue. It contains no HMAC/key/token/credential/permission/admission surface. Downstream controls may consume the canonicalization fact, but this package itself never grants or denies an external action.

## Current API

`resolve_current(observation)` has no registry/path selector. It always consumes co-located `registry.json`. The checked-in generation starts empty rather than inventing buyer/opportunity aliases; until reviewed entries are added, observations resolve `UNRESOLVED_ALIAS`.

Observation schema:

```json
{
  "schema": "opportunity-identity-alias-observation/v1",
  "buyer_organization_key": "buyer-example",
  "aliases": [
    {"type": "official_id", "value": "RFP-123"},
    {"type": "authority_url", "value": "https://procurement.example.org/events/123"}
  ]
}
```

Only `official_id` and public HTTPS `authority_url` aliases are accepted. URL userinfo, query strings, fragments, non-default ports, and dot segments are rejected so route tokens or secret-shaped query material do not become durable registry identity.

Result states are exact:

- `RESOLVED` — every observed alias is known and all map to one canonical key;
- `UNRESOLVED_ALIAS` — at least one alias is unknown (including a cross-buyer transplant); no key is minted;
- `AMBIGUOUS_ALIAS_SET` — known aliases in one observation map to more than one canonical key.

Every result binds the normalized alias-set SHA-256, exact normalized registry SHA-256/generation, candidate keys, unknown aliases, and an exact result digest. External-action/payment/revenue authority fields are always `false`.

## Registry and transition law

`compile_registry()` canonicalizes array order and rejects duplicate canonical keys, duplicate normalized aliases, and assigning one normalized alias to two opportunities **within the same buyer organization**. A canonical opportunity key is globally unique in the registry.

`validate_transition(previous, candidate)` is a pure append-only evolution check:

- generation must advance by exactly one;
- `prior_registry_sha256` must equal the canonical prior generation;
- existing canonical opportunities cannot be removed;
- an existing canonical key cannot move to another buyer;
- existing aliases cannot be removed or reassigned;
- a new generation may add aliases to an existing opportunity or add a new opportunity.

Semantic corrections that require reassignment are intentionally not silently rewritten under v1; they need an explicit future schema/transition rule.

`resolve_against()` / `compile_registry()` are deterministic context helpers for generation, replay, and tests. They are not authority gates. `verify_result()` is exact deterministic recompilation, not authentication.

## CLI

Offline only:

```bash
python -m revenue.opportunity_identity_alias.cli resolve-current observation.json
python -m revenue.opportunity_identity_alias.cli verify-current observation.json result.json
python -m revenue.opportunity_identity_alias.cli validate-transition previous.json candidate.json
```

The current resolver exposes no caller-selected registry path. CLI input is bounded UTF-8 ordinary-file JSON; final symlink inputs are rejected.

## Handoff

This package is a prerequisite fact source for the stale initial-outreach lane #14207 and mandatory organization-aware provider-chain issue #14269. It does not take their source/finalizer custody. Terminal provider consumer #14049 is separately under Z-Sable recovery and is not modified here.
