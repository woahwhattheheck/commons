# Independent authority model

The qualification manifest is **not** a trust root. It is caller input. Current readiness is derived from verifier time plus independently retained authority packets whose exact SHA-256 values must already be present in the evaluator's reviewed trust-root sets.

Production trust-root sets are intentionally empty while the buyer questionnaire is unavailable. Synthetic tests patch them only inside the test process; that does not create production authority.

## 1. Questionnaire extraction authority

`--questionnaire-authority FILE` must be strict JSON and its exact file SHA-256 must appear in `TRUSTED_QUESTIONNAIRE_AUTHORITY_SHA256`.

Required semantics:

- `kind = questionnaire_extraction`;
- exact `notice_id = 080252-2026` and `atamis_contract_reference = C467704`;
- exact SHA-256 of the consumed `sources.json` bytes;
- exact SHA-256 of the consumed questionnaire bytes;
- nonempty extraction ID and document version;
- extraction timestamp no later than verifier time;
- `complete_addenda_set=true` plus unique ID/SHA-256 records for retained controlling files;
- a `required_gates_by_route` universe containing every supported route and at least every code baseline gate for that route.

A trusted packet that omits a route, drops a baseline gate, binds another source ledger/opportunity, or does not attest the complete addenda/version set is rejected.

## 2. Capability evidence authority

`--evidence-authority FILE` must have its exact file SHA-256 retained in `TRUSTED_EVIDENCE_AUTHORITY_SHA256` and must bind:

- this notice;
- the exact source-ledger SHA-256;
- the exact retained questionnaire-authority SHA-256;
- a named evidence generation;
- issue and expiry timestamps around verifier time;
- unique evidence IDs, each with exactly one capability identity, evidence kind/type, artifact SHA-256 and permitted route list.

A `PROVEN` manifest capability is accepted only when every referenced evidence ID exists in this retained authority, names the same capability and allows the selected route. Generic strings, cross-capability transplant, cross-route replay, expired evidence and cross-source replay fail closed.

## 3. Partner-prime authority

For `TEAMING_*` routes, `--partner-authority FILE` is mandatory after all capability gates pass. Its exact SHA-256 must be retained in `TRUSTED_PARTNER_AUTHORITY_SHA256` and it must bind:

- this notice and Atamis reference;
- the exact selected teaming route;
- `qualified_prime=true`;
- a nonempty partner identity and proof SHA-256;
- the exact retained questionnaire-authority SHA-256;
- the exact evidence generation used by the capability authority;
- a validity interval containing verifier time.

The legacy manifest boolean `partner_prime_confirmed` is recorded as caller metadata only. It cannot authorize a route.

## Trust-root promotion

When actual buyer/partner/evidence material exists, do **not** type its digest into a manifest and call it trusted. Instead:

1. retain exact authority packet bytes and independently review the underlying source/evidence;
2. compute the packet SHA-256 over the exact consumed bytes;
3. add only that digest to the appropriate `TRUSTED_*_SHA256` frozenset in a reviewed source change;
4. run normal and `python -O` hostile tests plus the exact current packet;
5. record the source commit/head and packet digests in the resulting review receipt.

Any authority-packet byte change creates a different SHA-256 and requires a new retention change. This is intentional.

## Verifier-owned time and historical mode

Current readiness uses `datetime.now(timezone.utc)` in the CLI. Tests inject a timezone-aware verifier time explicitly. Manifest `evaluated_at` never controls source age, deadline or authority validity.

`--historical-integrity-only` exists only to verify historical source/manifest structure and digest binding. It returns `commercial_readiness=false`; it does not bypass current deadline, source freshness, evidence or partner requirements because it does not issue READY at all.
