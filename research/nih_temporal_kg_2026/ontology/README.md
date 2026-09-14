# NIH temporal-KG ontology interoperability profile

This directory adds a strict interoperability layer to the existing bitemporal evidence engine in the parent directory. It exports canonical temporal JSONL to a deterministic RDF 1.1 N-Triples profile that references OWL-Time, PROV-O, and Biolink vocabulary IRIs, then imports **only that exact profile** back to the original canonical JSONL semantics.

It is engineering evidence for the ontology/interoperability portion of NIH ODSS's “It’s About Time: Temporal Reasoning in Biomedical Knowledge Graphs Challenge.” It is not a general RDF parser, OWL reasoner, SPARQL endpoint, biomedical ontology endorsement, clinical system, challenge submission, or evidence of prize eligibility or performance on NIH data.

## What the adapter preserves

The adapter keeps the temporal engine's two clocks distinct:

- **valid time** is represented as an OWL-Time `time:ProperInterval` with a required `time:hasBeginning` instant and an optional `time:hasEnd` instant. The parent engine's interval remains half-open: `[valid_from, valid_to)`.
- **knowledge time** is the immutable fact or correction record's `prov:generatedAtTime`. A later retraction or supersession never rewrites an earlier historical knowledge view.

Each assertion also binds:

- the canonical `fact_id` and exact subject/predicate/object lexemes;
- deterministic subject, predicate, and object resource IRIs;
- confidence as canonical `xsd:decimal`;
- a source entity carrying exact `source_id` and source SHA-256;
- the source record through `prov:wasDerivedFrom`.

Retraction and supersession records are append-only immutable evidence entities. They bind their canonical event ID, action, observation time, source, target assertion, and—only for supersession—the replacement assertion.

A syntactically valid predicate lexeme such as `biolink:precedes` maps to `https://w3id.org/biolink/vocab/precedes`. Other predicate lexemes receive a content-addressed local predicate IRI. The original predicate lexeme is always retained, so the mapping cannot erase source semantics.

## Exact-profile policy

The importer is intentionally narrower than a general RDF stack. It rejects rather than guesses when the graph is outside `nih-temporal-kg-ontology/v1`.

Required properties include:

- absolute IRIs; no blank nodes or relative IRIs;
- one sorted LF-terminated N-Triples serialization with explicit datatypes;
- no duplicate triples or blank lines;
- uppercase fixed-width Unicode escapes and canonical literal escaping;
- canonical UTC microsecond `xsd:dateTimeStamp` values;
- canonical nonnegative integers and confidence decimals;
- the complete fixed class/property/domain/range/functional-property axiom set;
- exact resource identities derived from canonical fact, event, source, entity, interval, and instant content;
- exact cardinality and type sets;
- exact profile header counts, source JSONL digest, and referenced-vocabulary set;
- byte-for-byte regeneration of the canonical emitted graph after import.

This strictness prevents silent semantic loss. An arbitrary RDF graph may be valid RDF and still be rejected because it is not this versioned interchange profile.

## CLI

From `research/nih_temporal_kg_2026/ontology`:

```bash
python ontology_adapter.py export example.jsonl exported.nt --receipt receipt.json
python ontology_adapter.py import exported.nt roundtrip.jsonl
cmp example.jsonl roundtrip.jsonl
python ontology_adapter.py verify example.jsonl exported.nt receipt.json
```

`verify` prints `VALID` and exits `0` only when the JSONL, N-Triples, exact implementation source-set bytes, parent temporal-engine bytes, semantic round trip, and receipt digest all agree. Invalid input exits `2`.

The CLI reads regular non-symlink UTF-8 files through one descriptor, caps each input at 8 MiB, checks path/descriptor identity, and rejects in-read mutation. Output uses a same-directory temporary file, `fsync`, and atomic replacement.

## Tests

```bash
python -m unittest -v test_ontology_adapter.py
python -O -m unittest -v test_ontology_adapter.py
python -m py_compile ontology_adapter.py test_ontology_adapter.py
```

The optimized run is required because no validation or integrity boundary may depend on Python `assert` statements.

The hostile suite covers deterministic record ordering; finite/open intervals; literal escaping; missing axioms; blank nodes; relative IRIs; malformed or noncanonical N-Triples; unknown terms; conflicting functional properties; entity/source/fact/event transplant and replay; wrong correction type/action; interval-end insertion/removal; header-count tampering; receipt tampering; symlink ingress; and the complete CLI export/import/verify path.

## Files

- `ontology_adapter.py` — stable CLI and public import facade.
- `profile_vocab.py` / `profile_ntriples.py` — vocabulary constants and strict canonical N-Triples codec.
- `profile_export.py` / `profile_import.py` — deterministic profile construction and exact-profile reconstruction.
- `profile_receipt.py` — source-set integrity receipt and hardened file ingress/egress.
- `test_ontology_adapter.py` — focused hostile and round-trip suite.
- `PROFILE.md` — normative graph shape, identities, canonicalization, and rejection rules.
- `CHALLENGE_MAP.md` — NIH criterion mapping and explicit missing proof.
- `example.jsonl` — synthetic non-PHI temporal evidence.
- The canonical N-Triples graph is generated deterministically from `example.jsonl` in CI rather than checked in as a second source of truth.

## Deliberate non-claims

This profile does not establish:

- correctness on the NIH shared benchmark or any biomedical corpus;
- Biolink-model semantic validation beyond the declared CURIE-to-IRI mapping;
- entailment completeness, SHACL conformance, SPARQL support, or general OWL reasoning;
- source authenticity merely because a source SHA-256 is preserved;
- biological or clinical truth, diagnosis, treatment, or safety;
- challenge registration, eligibility, submission, acceptance, award, payment, or revenue.

Those remain separate proof gates. See `CHALLENGE_MAP.md`.
