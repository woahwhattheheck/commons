# Commercial opportunity alias identity

This package is a **coordination/canonicalization primitive only**. It answers one narrow question: when the same measured solicitation is referenced by more than one official ID or HTTPS authority URL, which repository-carried canonical opportunity key do those aliases describe?

It does **not** contact a prospect, select a sender, replace Muse arbitration, approve outreach, authorize an external action, mutate a provider, or infer that two names mean the same solicitation. Those decisions and workflows remain outside this package.

## Why this exists

The commercial-opportunity custody and first-contact layers need a stable pursuit identity. A buyer website, procurement portal, and human shorthand can name one solicitation differently. If each spelling is treated as a new opportunity, independent workers can accidentally obtain distinct coordination seams for the same real pursuit.

`opportunity_identity_alias` removes only that spelling ambiguity **after the equivalence has been explicitly measured and recorded in `registry.json`**.

## Honest bootstrap

The checked-in registry is generation 1 and intentionally contains zero opportunities. No buyer or solicitation aliases are invented by this carrier. A future ordinary repository change can add a row only when there is durable evidence that the aliases identify the same pursuit.

Unknown aliases return `UNRESOLVED_ALIAS`; they never auto-create a canonical key. A set of known aliases that points at more than one registered pursuit returns `AMBIGUOUS_ALIAS_SET`.

## Schemas

A registry row binds:

```json
{
  "canonical_opportunity_key": "opp_example_04254",
  "buyer_key": "buyer_example",
  "aliases": [
    {"kind": "official_id", "value": "rfp-04254"},
    {"kind": "authority_url", "value": "https://procurement.example/bids/04254"}
  ]
}
```

Supported alias kinds are `official_id` and `authority_url`. Official IDs are Unicode-normalized, case-folded, whitespace-collapsed machine strings. Authority URLs must be HTTPS, contain no userinfo or fragment, and normalize host casing/IDNA/default port without changing path/query semantics.

Results bind the exact registry SHA-256, generation, buyer key, normalized alias-set SHA-256, status, and canonical opportunity key when resolved. They contain no external-action fields.

## Evolution

V1 registry evolution is append-only. `compile_transition(previous_raw, next_value)` requires the next generation number, the SHA-256 of the exact previous canonical bytes, preservation of every existing canonical opportunity/buyer binding, and preservation of every existing alias. It may add aliases or add opportunities.

Reassigning or removing a known alias is deliberately not expressible as a silent V1 update. A future correction mechanism must make that semantic change explicit rather than rewriting history.

## APIs

- `compile_initial_registry(value) -> bytes`
- `compile_transition(previous_raw, next_value) -> bytes`
- `parse_registry(raw) -> dict`
- `resolve_against(observation, registry_raw) -> dict` for deterministic replay/tests
- `resolve_current(observation) -> dict` for repository-carried current equivalence data
- `verify_result(...)` / `verify_current(...)` for exact recomputation

`resolve_current()` has no registry/path selector. The pure replay helpers accept bytes as data so historic receipts and transition tests can be recomputed; they do not confer external authority.

## Verification

From this directory:

```bash
python -B -m unittest -v test_alias.py
python -O -B -m unittest -v test_alias.py
python -m py_compile alias.py __init__.py test_alias.py
```

The hostile suite covers conflicting aliases, cross-buyer transplants, strict observation fields, unknown/ambiguous sets, append-only transitions, digest binding, tamper detection, canonical JSON, and current-registry bootstrap behavior.

Operation: `COMMONS-OPPORTUNITY-IDENTITY-ALIAS-ZNLV7R5-20260914` / issue #14523.
