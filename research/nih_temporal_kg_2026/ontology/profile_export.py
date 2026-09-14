from __future__ import annotations

try:  # package import
    from .profile_ntriples import *
except ImportError:  # direct script / cwd import
    from profile_ntriples import *

def _static_axioms() -> set[Triple]:
    triples: set[Triple] = {_type(NTKG_ONTOLOGY, OWL_ONTOLOGY)}
    classes = (C_PROFILE, C_ASSERTION, C_RETRACT, C_SUPERSEDE)
    for class_iri in classes:
        triples.add(_type(class_iri, OWL_CLASS))
    for class_iri in (C_ASSERTION, C_RETRACT, C_SUPERSEDE):
        triples.add(_t(class_iri, RDFS_SUBCLASS, iri(PROV_ENTITY)))
    object_properties = (
        P_USES_ONTOLOGY, P_SUBJECT_NODE, P_PREDICATE_NODE, P_OBJECT_NODE,
        P_VALIDITY, P_TARGET, P_REPLACEMENT,
    )
    datatype_properties = (
        P_PROFILE_VERSION, P_SOURCE_SCHEMA, P_JSONL_SHA, P_RECORD_COUNT,
        P_FACT_COUNT, P_EVENT_COUNT, P_FACT_ID, P_EVENT_ID, P_SUBJECT_LEXEME,
        P_PREDICATE_LEXEME, P_OBJECT_LEXEME, P_CONFIDENCE, P_ACTION,
        P_SOURCE_ID, P_SOURCE_SHA,
    )
    functional = tuple(p for p in object_properties if p != P_USES_ONTOLOGY) + datatype_properties
    for prop in object_properties:
        triples.add(_type(prop, OWL_OBJECT_PROPERTY))
    for prop in datatype_properties:
        triples.add(_type(prop, OWL_DATATYPE_PROPERTY))
    for prop in functional:
        triples.add(_type(prop, OWL_FUNCTIONAL_PROPERTY))
    triples.update({
        _t(P_VALIDITY, RDFS_DOMAIN, iri(C_ASSERTION)),
        _t(P_VALIDITY, RDFS_RANGE, iri(TIME_PROPER_INTERVAL)),
        _t(P_TARGET, RDFS_RANGE, iri(C_ASSERTION)),
        _t(P_REPLACEMENT, RDFS_RANGE, iri(C_ASSERTION)),
        _t(P_CONFIDENCE, RDFS_DOMAIN, iri(C_ASSERTION)),
        _t(P_CONFIDENCE, RDFS_RANGE, iri(XSD_DECIMAL)),
    })
    return triples


STATIC_AXIOMS = frozenset(_static_axioms())


def _fact_iri(fact_id: str) -> str:
    if not _HEX64.fullmatch(fact_id):
        raise OntologyProfileError("fact ID must be 64 lowercase hex")
    return "urn:ntkg:fact:" + fact_id


def _event_iri(event_id: str) -> str:
    if not _HEX64.fullmatch(event_id):
        raise OntologyProfileError("event ID must be 64 lowercase hex")
    return "urn:ntkg:event:" + event_id


def _interval_iri(fact_id: str) -> str:
    return "urn:ntkg:interval:" + fact_id


def _instant_iri(fact_id: str, role: str) -> str:
    if role not in {"valid-from", "valid-to"}:
        raise OntologyProfileError("unknown instant role")
    return f"urn:ntkg:instant:{fact_id}:{role}"


def _entity_iri(value: str) -> str:
    return "urn:ntkg:entity:" + _sha(value.encode("utf-8"))


def _predicate_iri(value: str) -> str:
    match = _BIOLINK_CURIE.fullmatch(value)
    if match:
        return BIOLINK + match.group(1)
    return "urn:ntkg:predicate:" + _sha(value.encode("utf-8"))


def _source_key(source_id: str, source_sha256: str) -> str:
    return digest_json({"source_id": source_id, "source_sha256": source_sha256})


def _source_iri(source_id: str, source_sha256: str) -> str:
    return "urn:ntkg:source:" + _source_key(source_id, source_sha256)


def _source_triples(source_id: str, source_sha256: str) -> set[Triple]:
    node = _source_iri(source_id, source_sha256)
    return {
        _type(node, PROV_ENTITY),
        _t(node, P_SOURCE_ID, literal(source_id)),
        _t(node, P_SOURCE_SHA, literal(source_sha256)),
    }


def _build_ntriples(graph: TemporalEvidenceGraph) -> str:
    canonical_jsonl = graph.to_jsonl()
    triples: set[Triple] = set(STATIC_AXIOMS)
    triples.update({
        _type(PROFILE_NODE, C_PROFILE),
        _t(PROFILE_NODE, P_PROFILE_VERSION, literal(PROFILE_VERSION)),
        _t(PROFILE_NODE, P_SOURCE_SCHEMA, literal(SOURCE_SCHEMA)),
        _t(PROFILE_NODE, P_JSONL_SHA, literal(_sha(canonical_jsonl.encode("utf-8")))),
        _t(PROFILE_NODE, P_RECORD_COUNT, literal(str(len(graph.facts) + len(graph.events)), XSD_NNI)),
        _t(PROFILE_NODE, P_FACT_COUNT, literal(str(len(graph.facts)), XSD_NNI)),
        _t(PROFILE_NODE, P_EVENT_COUNT, literal(str(len(graph.events)), XSD_NNI)),
    })
    for vocabulary in REFERENCED_VOCABULARIES:
        triples.add(_t(PROFILE_NODE, P_USES_ONTOLOGY, iri(vocabulary)))

    for fact in graph.facts:
        node = _fact_iri(fact.fact_id)
        interval = _interval_iri(fact.fact_id)
        begin = _instant_iri(fact.fact_id, "valid-from")
        source = _source_iri(fact.source_id, fact.source_sha256)
        triples.update(_source_triples(fact.source_id, fact.source_sha256))
        triples.update({
            _type(node, C_ASSERTION),
            _type(node, PROV_ENTITY),
            _t(node, P_FACT_ID, literal(fact.fact_id)),
            _t(node, P_SUBJECT_LEXEME, literal(fact.subject)),
            _t(node, P_PREDICATE_LEXEME, literal(fact.predicate)),
            _t(node, P_OBJECT_LEXEME, literal(fact.object)),
            _t(node, P_SUBJECT_NODE, iri(_entity_iri(fact.subject))),
            _t(node, P_PREDICATE_NODE, iri(_predicate_iri(fact.predicate))),
            _t(node, P_OBJECT_NODE, iri(_entity_iri(fact.object))),
            _t(node, P_VALIDITY, iri(interval)),
            _t(node, P_CONFIDENCE, literal(_decimal_lexeme(fact.confidence), XSD_DECIMAL)),
            _t(node, PROV_GENERATED_AT, literal(_ts(fact.observed_at), XSD_DATETIME_STAMP)),
            _t(node, PROV_WAS_DERIVED_FROM, iri(source)),
            _type(interval, TIME_PROPER_INTERVAL),
            _t(interval, TIME_HAS_BEGINNING, iri(begin)),
            _type(begin, TIME_INSTANT),
            _t(begin, TIME_IN_XSD, literal(_ts(fact.valid_from), XSD_DATETIME_STAMP)),
        })
        if fact.valid_to is not None:
            end = _instant_iri(fact.fact_id, "valid-to")
            triples.update({
                _t(interval, TIME_HAS_END, iri(end)),
                _type(end, TIME_INSTANT),
                _t(end, TIME_IN_XSD, literal(_ts(fact.valid_to), XSD_DATETIME_STAMP)),
            })

    for event in graph.events:
        node = _event_iri(event.event_id)
        source = _source_iri(event.source_id, event.source_sha256)
        class_iri = C_RETRACT if event.action == "retract" else C_SUPERSEDE
        triples.update(_source_triples(event.source_id, event.source_sha256))
        triples.update({
            _type(node, class_iri),
            _type(node, PROV_ENTITY),
            _t(node, P_EVENT_ID, literal(event.event_id)),
            _t(node, P_ACTION, literal(event.action)),
            _t(node, P_TARGET, iri(_fact_iri(event.target_fact_id))),
            _t(node, PROV_GENERATED_AT, literal(_ts(event.observed_at), XSD_DATETIME_STAMP)),
            _t(node, PROV_WAS_DERIVED_FROM, iri(source)),
        })
        if event.replacement_fact_id is not None:
            triples.add(_t(node, P_REPLACEMENT, iri(_fact_iri(event.replacement_fact_id))))
    return render_ntriples(triples)


def export_ntriples(jsonl_text: str) -> str:
    try:
        graph = TemporalEvidenceGraph.from_jsonl(jsonl_text)
    except TemporalEvidenceError as exc:
        raise OntologyProfileError(f"invalid temporal JSONL: {exc}") from exc
    return _build_ntriples(graph)

__all__ = tuple(name for name in globals() if not name.startswith("__"))
