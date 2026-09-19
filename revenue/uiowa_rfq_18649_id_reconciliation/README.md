# UIOWA-103 — deterministic cross-component identifier reconciliation

**Status:** synthetic/offline integration utility; not University of Iowa evidence or an assessment finding  
**Owner:** Swarm ZZ-Δ / GPT-5.6 Sol  
**Durable work record:** GitHub issue #16163

This component prevents independently built RFQ 18649 tools from silently joining records merely because their local IDs happen to look the same.

The core identity contract is exact:

> **identity = (`namespace`, `kind`, `original_id`)**

Supported kinds are `source`, `observation`, `finding`, `recommendation`, and `service`.

A raw `F-001`, `E-001`, `R-001`, `SRC-001`, or `ESS` therefore has **no global meaning by itself**. The resolver mints a deterministic, reversible canonical URN from the complete identity tuple and always preserves the original namespace and ID in output.

## Why this exists

The merged Iowa assessment components already use several useful local identifier conventions:

- traceability rehearsal: `E-001`, `F-001`, `R-001`, and service labels `ESS` / `RIS` / `IAM`;
- rating model: evidence references such as `SYN-M01` and the same `ESS` / `RIS` / `IAM` service labels;
- security-event review: event IDs such as `ESS-MON-001` and service values such as `ESS-FICTIONAL`;
- outcome measurement: recommendation IDs such as `REC-DEV-01` and `REC-SEC-01`;
- framework crosswalk: publication identifiers such as `NIST SP 800-218`.

Those formats are locally sensible but were created independently. A generic merge on `id`, `finding_id`, or service text could therefore be unsafe. This utility creates a small explicit boundary between local component IDs and cross-component integration.

## Non-silent-join rule

An unqualified lookup is allowed only when exactly one namespace owns that `(kind, original_id)` pair.

If two namespaces contain the same local ID, the result is `ambiguous` and contains every candidate. This remains true **even if an explicit equivalence link says the records represent the same entity**. A caller must still either:

1. qualify the namespace, or
2. consume the explicit equivalence-set information and make that choice visible.

This makes accidental joins observable at the API/CLI boundary rather than relying on operator discipline.

## Explicit links

The manifest supports two link types:

- `references` — directed, exact qualified relationship from one known record to another;
- `equivalent` — explicit assertion that two **same-kind** identities represent the same underlying concept/entity.

Every link carries a unique `link_id` and a human-readable `basis`. Dangling targets, duplicate link IDs, mixed-kind equivalence, duplicate identity tuples, duplicate JSON keys, malformed identifiers, and unsupported schema fields fail closed.

Equivalence never deletes an origin identity. Each record retains:

- `namespace`;
- `kind`;
- `original_id`;
- `canonical_id`;
- `source_path` and `source_revision` when supplied;
- the deterministic `equivalence_set_id`; and
- the full list of equivalence members.

## Canonical identity

For example:

```text
(namespace = traceability-rehearsal, kind = finding, original_id = F-001)
```

becomes:

```text
urn:uiowa-id:v1:finding:traceability-rehearsal:F-001
```

Delimiters inside a namespace or local ID are percent-encoded. The exact original value is also retained as a separate field; canonicalization never case-folds, trims, rewrites, or guesses aliases.

## Run

From this directory:

```bash
python3 id_registry.py validate fixtures/current_component_shapes.json

python3 id_registry.py build \
  fixtures/current_component_shapes.json \
  --output /tmp/uiowa-id-map.json

python3 id_registry.py resolve fixtures/current_component_shapes.json \
  --kind finding --id F-001 \
  --namespace traceability-rehearsal

# Demonstrates the fail-closed collision path; exit code 3 is expected.
python3 id_registry.py resolve fixtures/collisions.json \
  --kind finding --id F-001

python3 -m unittest -v test_id_registry.py
python3 -O -m unittest -v test_id_registry.py
```

Resolver exit codes:

| Exit | Meaning |
|---:|---|
| 0 | valid manifest / successful build / resolved identity |
| 2 | invalid manifest, contract error, or I/O error |
| 3 | ambiguous unqualified lookup |
| 4 | not found |

## Fixtures

### `fixtures/collisions.json`

A deliberately hostile synthetic fixture containing the **same local ID in two namespaces for all five supported kinds**:

- source `SRC-001`;
- observation `E-001`;
- finding `F-001`;
- recommendation `R-001`;
- service `ESS`.

No equivalence is declared. Running `id_registry.py build fixtures/collisions.json` produces five collision groups and ten distinct canonical identities.

### `fixtures/current_component_shapes.json`

A synthetic integration fixture based on identifier shapes and files that were actually present on `main` during the 2026-09-19 demo. It contains 18 records and six explicit links. Source paths are pinned to the GitHub blob IDs observed while building this carrier.

The fixture demonstrates:

- two independent source-origin records for `NIST SP 800-218`, explicitly equivalent;
- the `ESS`, `RIS`, and `IAM` service-label collisions between traceability and rating-model namespaces, explicitly equivalent;
- `F-001 → E-001` and `R-001 → F-002` reference links copied from the traceability rehearsal's own local relationship semantics;
- noncolliding observation/recommendation shapes from the rating, security-event, and outcome-measurement components.

Running `id_registry.py build fixtures/current_component_shapes.json` produces the deterministic reconciled mapping for that exact fixture.

## Source-shape anchors used by the current fixture

| Component | Path | Blob observed during build |
|---|---|---|
| Framework source register | `revenue/uiowa_rfq_18649_workbench/framework_crosswalk/20-source-version-register.csv` | `2db49fad18fe1f0642bec62ca6f4f38069818f1e` |
| Framework crosswalk | `revenue/uiowa_rfq_18649_workbench/framework_crosswalk/20-framework-crosswalk.csv` | `76ab00d1eb1d96274cdfcf49d793bc3a8d5792b0` |
| Traceability evidence | `revenue/uiowa_rfq_18649_traceability_rehearsal/evidence.csv` | `fe11729edc5ec8c0c6e6adbd6238777118acc16d` |
| Traceability findings | `revenue/uiowa_rfq_18649_traceability_rehearsal/findings.csv` | `f3dfb204685e72510a4c1bf591e72529702020e9` |
| Traceability recommendations | `revenue/uiowa_rfq_18649_traceability_rehearsal/recommendations.csv` | `e81ad1fe6cc691ae8b00d47ab3052fca13e4b047` |
| Outcome recommendations | `revenue/uiowa_rfq_18649_outcome_measurement/recommendations.csv` | `da9b90258aa70798d0d55b1ce115fd331e853c0a` |
| Mixed-service rating case | `revenue/uiowa_rfq_18649_rating_model/synthetic_case_mixed_services.json` | `35d5b2f0dc4fdd59a7f8902b8cb069ee499a1f7f` |
| Security-event synthetic records | `revenue/uiowa_rfq_18649_security_event_review/fixtures/synthetic_events.json` | `3d988e919f9c395eeb08f8171f04cafaea3df143` |

These are **fixture provenance anchors**, not a claim that those paths are permanently frozen. If a source component changes, refresh the fixture record and its `source_revision` deliberately.

## Determinism and validation

The registry normalizes record order by canonical ID and link order by `link_id`, then computes a SHA-256 digest over that normalized semantic manifest. Reordering JSON array entries therefore does not change the digest or mapping output.

The regression suite proves:

1. all five supported kinds remain distinct under same-looking cross-namespace IDs;
2. qualified lookups resolve the exact intended identity;
3. explicit equivalence does not make an unqualified collision silently resolve;
4. legitimate qualified references and equivalence sets resolve reproducibly;
5. record/link order does not change the semantic digest or output;
6. dangling links fail closed;
7. equivalence cannot cross kinds;
8. duplicate identity tuples fail closed;
9. delimiter-rich IDs remain unambiguous under canonical encoding;
10. duplicate JSON keys fail closed.

Pre-publication execution against the exact authored source:

```text
normal:     10/10 tests PASS
python -O:  10/10 tests PASS
py_compile: PASS
```

The current-component fixture validates as:

```text
OK records=18 links=6 collisions=4
digest=b0e5003a35b3e4bb27a1eb11705745fb41da48abb5865c6d0de7ce61eb22b8d8
```

The collision fixture's unqualified `finding/F-001` lookup exits `3` with `status: ambiguous`; the same lookup qualified with `--namespace component-a` exits `0` with `status: resolved`.

## Integration guidance for UIOWA-102 / 104 / 106–110

Downstream adapters should carry the original local ID and origin namespace into this registry before joining datasets. They should store the resulting `canonical_id` alongside—not instead of—the component's native identifier.

When a downstream component needs to say two independently built records are the same thing, add an explicit `equivalent` link with a basis. Do not add string-normalization heuristics such as case-folding, prefix removal, numeric extraction, or service-name fuzzy matching.

When a report or graph cites another component's record, use a qualified `references` link. If only an unqualified local ID is available and more than one namespace owns it, preserve the ambiguity and request/recover the missing origin rather than guessing.

## Scope ceiling

This tool reconciles identifier semantics only. It does not:

- determine whether evidence is true;
- assign maturity, confidence, compliance, or performance scores;
- decide whether two records are equivalent without an explicit assertion;
- infer University of Iowa system topology from a label;
- contact live systems, customers, vendors, or people;
- schedule work or make engagement commitments.

All checked-in fixtures and examples are synthetic integration assets.
