# Normative profile: `nih-temporal-kg-ontology/v1`

The words **MUST**, **MUST NOT**, **SHOULD**, and **MAY** are normative within this repository profile. This document defines a deliberately closed interchange contract, not all legal RDF 1.1 N-Triples.

## 1. Source model

The source is canonical JSONL produced by `TemporalEvidenceGraph.to_jsonl()` in the parent module. Records are immutable facts or append-only correction events. Canonical fact and event IDs are SHA-256 values computed by the parent engine from their semantic content.

The exporter MUST parse source text through `TemporalEvidenceGraph.from_jsonl()` and MUST export the graph's regenerated canonical JSONL, not caller ordering or whitespace.

## 2. Serialization

The RDF representation MUST:

1. use UTF-8 text and LF line endings;
2. end in exactly one LF;
3. contain one triple per nonempty line;
4. contain no comments, blank nodes, prefixes, relative IRIs, language tags, bare literals, or graph names;
5. use explicit datatypes for every literal;
6. sort complete rendered lines lexicographically;
7. contain no duplicate triple lines;
8. use canonical escapes: `\\`, `\"`, `\t`, `\n`, `\r`, `\b`, `\f`, uppercase `\uXXXX`, or uppercase `\UXXXXXXXX`;
9. render non-ASCII characters as fixed-width escapes;
10. render timestamps as UTC microseconds ending in `Z`;
11. render confidence as a canonical `xsd:decimal` within `[0,1]` and counts as canonical `xsd:nonNegativeInteger`.

A graph that is semantically similar but serializes differently is outside this exact profile.

## 3. Resource identity

Profile resources are deterministic:

| Resource | IRI form |
| --- | --- |
| Profile header | `urn:ntkg:profile:v1` |
| Fact assertion | `urn:ntkg:fact:{fact_id}` |
| Correction event | `urn:ntkg:event:{event_id}` |
| Validity interval | `urn:ntkg:interval:{fact_id}` |
| Beginning instant | `urn:ntkg:instant:{fact_id}:valid-from` |
| Ending instant | `urn:ntkg:instant:{fact_id}:valid-to` |
| Entity lexeme | `urn:ntkg:entity:{sha256(UTF-8 lexeme)}` |
| Non-Biolink predicate | `urn:ntkg:predicate:{sha256(UTF-8 lexeme)}` |
| Source entity | `urn:ntkg:source:{digest_json({source_id,source_sha256})}` |

A predicate matching `biolink:([A-Za-z][A-Za-z0-9_]*)` maps instead to `https://w3id.org/biolink/vocab/{local}`. This is a deterministic lexical mapping, not proof that the term exists in a particular Biolink release.

## 4. Profile header

`urn:ntkg:profile:v1` MUST have exactly:

- type `ntkg:InteroperabilityProfile`;
- `ntkg:profileVersion = "nih-temporal-kg-ontology/v1"`;
- `ntkg:sourceSchema = "temporal-evidence-jsonl/v1"`;
- `ntkg:jsonlSha256` equal to SHA-256 of regenerated canonical JSONL;
- exact `recordCount`, `factCount`, and `eventCount`;
- the exact three `ntkg:usesOntology` IRIs declared by the implementation.

## 5. Temporal assertions

Every fact assertion MUST have exactly the profile's expected type set and one value for each functional property:

- canonical fact ID;
- original subject, predicate, and object lexemes;
- deterministic subject, predicate, and object nodes;
- one OWL-Time validity interval;
- one confidence value;
- one `prov:generatedAtTime` knowledge/observation time;
- one `prov:wasDerivedFrom` source entity.

The validity interval MUST be a `time:ProperInterval` with one beginning instant. A finite source interval MUST have one ending instant. An open-ended source interval MUST have none. The importer reconstructs the parent engine's half-open interval semantics; RDF consumers MUST NOT reinterpret the end as inclusive.

## 6. Correction records

A retraction record MUST:

- have the exact retraction-event type set;
- carry action lexeme `retract`;
- target one profile fact;
- carry no replacement assertion.

A supersession record MUST:

- have the exact supersession-event type set;
- carry action lexeme `supersede`;
- target one profile fact;
- identify exactly one different replacement fact.

Both MUST carry canonical event ID, knowledge/observation time, and source provenance. Parent-engine constraints still apply: the target must exist; an event cannot predate its target's observation; a supersession replacement must exist and must have been observed no later than the supersession.

## 7. Sources

Every source entity MUST have exactly:

- type `prov:Entity`;
- one nonempty source ID literal;
- one lowercase 64-hex source SHA-256 literal.

Its IRI MUST match the canonical digest of those two values. Sharing the same source node across records is permitted only when both values are identical.

Preserving a digest establishes content identity within the record. It does not authenticate the source publisher or establish biomedical truth.

## 8. Fixed axioms

The graph MUST contain the implementation's complete fixed axiom set, including:

- the local namespace resource typed as `owl:Ontology`;
- profile/assertion/retraction/supersession classes;
- their declared PROV-O subclass relationships;
- object and datatype property declarations;
- functional-property declarations for single-valued profile properties;
- validity, target/replacement, and confidence domain/range statements.

Removing or adding profile semantics that prevent exact canonical regeneration causes rejection.

## 9. Import and conformance

The importer MUST reject:

- malformed or noncanonical serialization;
- missing fixed axioms;
- unknown profile version or source schema;
- wrong profile counts or JSONL digest;
- wrong or ambiguous type/cardinality sets;
- resource aliases or content-address mismatch;
- invalid temporal data or event topology;
- any graph that cannot regenerate the exact original profile bytes.

Successful import MUST reconstruct canonical JSONL whose SHA-256 equals the profile header and whose semantic fact/event IDs equal the originals.

## 10. Conformance receipt

`nih-temporal-kg-ontology-conformance/v1` binds:

- profile and source-schema versions;
- canonical JSONL SHA-256;
- N-Triples SHA-256;
- round-trip JSONL SHA-256;
- exact adapter implementation SHA-256;
- exact parent temporal-engine SHA-256;
- fact, event, and triple counts;
- referenced-vocabulary list;
- a literal successful semantic-round-trip flag;
- canonical receipt SHA-256.

Verification rebuilds the receipt from all three supplied artifacts and requires exact object equality. Rehashing a modified receipt without producing matching implementation/data bytes does not validate it.
