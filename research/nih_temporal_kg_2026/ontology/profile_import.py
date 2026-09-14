from __future__ import annotations

try:  # package import
    from .profile_export import *
except ImportError:  # direct script / cwd import
    from profile_export import *

class _Index:
    def __init__(self, triples: Sequence[Triple]) -> None:
        self.triples = tuple(triples)
        self.by_subject: dict[str, list[Triple]] = {}
        for triple in triples:
            self.by_subject.setdefault(triple.subject, []).append(triple)

    def objects(self, subject: str, predicate: str) -> list[Term]:
        return [t.object for t in self.by_subject.get(subject, []) if t.predicate == predicate]

    def one(self, subject: str, predicate: str, *, kind: str | None = None, datatype: str | None = None) -> Term:
        values = self.objects(subject, predicate)
        if len(values) != 1:
            raise OntologyProfileError(f"{subject} requires exactly one {predicate}")
        term = values[0]
        if kind is not None and term.kind != kind:
            raise OntologyProfileError(f"{predicate} has wrong term kind")
        if datatype is not None and term.datatype != datatype:
            raise OntologyProfileError(f"{predicate} has wrong datatype")
        return term

    def types(self, subject: str) -> set[str]:
        values = self.objects(subject, RDF_TYPE)
        if any(term.kind != "iri" for term in values):
            raise OntologyProfileError("rdf:type objects must be IRIs")
        return {term.value for term in values}


def _literal_value(index: _Index, subject: str, predicate: str, datatype: str = XSD_STRING) -> str:
    return index.one(subject, predicate, kind="literal", datatype=datatype).value


def _iri_value(index: _Index, subject: str, predicate: str) -> str:
    return index.one(subject, predicate, kind="iri").value


def _source_from_index(index: _Index, source_node: str, cache: dict[str, tuple[str, str]]) -> tuple[str, str]:
    if source_node in cache:
        return cache[source_node]
    if index.types(source_node) != {PROV_ENTITY}:
        raise OntologyProfileError("source node must be exactly a prov:Entity")
    source_id = _literal_value(index, source_node, P_SOURCE_ID)
    source_sha = _literal_value(index, source_node, P_SOURCE_SHA)
    if not _HEX64.fullmatch(source_sha):
        raise OntologyProfileError("sourceSha256 must be 64 lowercase hex")
    if _source_iri(source_id, source_sha) != source_node:
        raise OntologyProfileError("source IRI does not bind source ID and digest")
    cache[source_node] = (source_id, source_sha)
    return cache[source_node]


def _fact_from_index(index: _Index, node: str, sources: dict[str, tuple[str, str]]) -> Fact:
    if index.types(node) != {C_ASSERTION, PROV_ENTITY}:
        raise OntologyProfileError("fact resource has incorrect rdf:type set")
    fact_id = _literal_value(index, node, P_FACT_ID)
    if _fact_iri(fact_id) != node:
        raise OntologyProfileError("fact IRI does not match factId")
    subject = _literal_value(index, node, P_SUBJECT_LEXEME)
    predicate = _literal_value(index, node, P_PREDICATE_LEXEME)
    object_value = _literal_value(index, node, P_OBJECT_LEXEME)
    if _iri_value(index, node, P_SUBJECT_NODE) != _entity_iri(subject):
        raise OntologyProfileError("subjectNode is not bound to subjectLexeme")
    if _iri_value(index, node, P_PREDICATE_NODE) != _predicate_iri(predicate):
        raise OntologyProfileError("predicateNode is not bound to predicateLexeme")
    if _iri_value(index, node, P_OBJECT_NODE) != _entity_iri(object_value):
        raise OntologyProfileError("objectNode is not bound to objectLexeme")
    confidence = _parse_decimal(_literal_value(index, node, P_CONFIDENCE, XSD_DECIMAL))
    observed_at = _parse_ts_literal(_literal_value(index, node, PROV_GENERATED_AT, XSD_DATETIME_STAMP))
    source_id, source_sha = _source_from_index(index, _iri_value(index, node, PROV_WAS_DERIVED_FROM), sources)
    interval = _iri_value(index, node, P_VALIDITY)
    if interval != _interval_iri(fact_id) or index.types(interval) != {TIME_PROPER_INTERVAL}:
        raise OntologyProfileError("validity interval identity/type mismatch")
    begin = _iri_value(index, interval, TIME_HAS_BEGINNING)
    if begin != _instant_iri(fact_id, "valid-from") or index.types(begin) != {TIME_INSTANT}:
        raise OntologyProfileError("beginning instant identity/type mismatch")
    valid_from = _parse_ts_literal(_literal_value(index, begin, TIME_IN_XSD, XSD_DATETIME_STAMP))
    ends = index.objects(interval, TIME_HAS_END)
    if len(ends) > 1:
        raise OntologyProfileError("validity interval has multiple ends")
    valid_to: datetime | None = None
    if ends:
        end = ends[0]
        if end.kind != "iri" or end.value != _instant_iri(fact_id, "valid-to"):
            raise OntologyProfileError("ending instant identity mismatch")
        if index.types(end.value) != {TIME_INSTANT}:
            raise OntologyProfileError("ending instant type mismatch")
        valid_to = _parse_ts_literal(_literal_value(index, end.value, TIME_IN_XSD, XSD_DATETIME_STAMP))
    try:
        fact = Fact.create(
            subject=subject,
            predicate=predicate,
            object=object_value,
            valid_from=valid_from,
            valid_to=valid_to,
            observed_at=observed_at,
            source_id=source_id,
            source_sha256=source_sha,
            confidence=confidence,
        )
    except TemporalEvidenceError as exc:
        raise OntologyProfileError(f"fact violates temporal contract: {exc}") from exc
    if fact.fact_id != fact_id:
        raise OntologyProfileError("RDF fact content does not match canonical factId")
    return fact


def _event_from_index(index: _Index, node: str, sources: dict[str, tuple[str, str]]) -> EvidenceEvent:
    types = index.types(node)
    event_classes = types & {C_RETRACT, C_SUPERSEDE}
    if len(event_classes) != 1 or types != {PROV_ENTITY, next(iter(event_classes))}:
        raise OntologyProfileError("event resource has incorrect rdf:type set")
    event_class = next(iter(event_classes))
    action = _literal_value(index, node, P_ACTION)
    expected_action = "retract" if event_class == C_RETRACT else "supersede"
    if action != expected_action:
        raise OntologyProfileError("event action/type mismatch")
    event_id = _literal_value(index, node, P_EVENT_ID)
    if _event_iri(event_id) != node:
        raise OntologyProfileError("event IRI does not match eventId")
    target_node = _iri_value(index, node, P_TARGET)
    if not target_node.startswith("urn:ntkg:fact:"):
        raise OntologyProfileError("event target must be a profile fact IRI")
    target_id = target_node.removeprefix("urn:ntkg:fact:")
    replacements = index.objects(node, P_REPLACEMENT)
    replacement_id: str | None = None
    if expected_action == "retract":
        if replacements:
            raise OntologyProfileError("retraction must not have replacementAssertion")
    else:
        if len(replacements) != 1 or replacements[0].kind != "iri":
            raise OntologyProfileError("supersession requires one replacementAssertion")
        replacement_node = replacements[0].value
        if not replacement_node.startswith("urn:ntkg:fact:"):
            raise OntologyProfileError("replacement must be a profile fact IRI")
        replacement_id = replacement_node.removeprefix("urn:ntkg:fact:")
    observed_at = _parse_ts_literal(_literal_value(index, node, PROV_GENERATED_AT, XSD_DATETIME_STAMP))
    source_id, source_sha = _source_from_index(index, _iri_value(index, node, PROV_WAS_DERIVED_FROM), sources)
    try:
        event = EvidenceEvent.create(
            action=action,
            target_fact_id=target_id,
            replacement_fact_id=replacement_id,
            observed_at=observed_at,
            source_id=source_id,
            source_sha256=source_sha,
        )
    except TemporalEvidenceError as exc:
        raise OntologyProfileError(f"event violates temporal contract: {exc}") from exc
    if event.event_id != event_id:
        raise OntologyProfileError("RDF event content does not match canonical eventId")
    return event


def import_ntriples(text: str) -> TemporalEvidenceGraph:
    triples = parse_ntriples(text)
    triple_set = set(triples)
    missing_axioms = set(STATIC_AXIOMS) - triple_set
    if missing_axioms:
        raise OntologyProfileError("required ontology axioms are missing")
    index = _Index(triples)
    if index.types(PROFILE_NODE) != {C_PROFILE}:
        raise OntologyProfileError("profile header rdf:type mismatch")
    if _literal_value(index, PROFILE_NODE, P_PROFILE_VERSION) != PROFILE_VERSION:
        raise OntologyProfileError("unsupported profileVersion")
    if _literal_value(index, PROFILE_NODE, P_SOURCE_SCHEMA) != SOURCE_SCHEMA:
        raise OntologyProfileError("unsupported sourceSchema")
    expected_jsonl_sha = _literal_value(index, PROFILE_NODE, P_JSONL_SHA)
    if not _HEX64.fullmatch(expected_jsonl_sha):
        raise OntologyProfileError("jsonlSha256 must be 64 lowercase hex")
    fact_count = _parse_nni(_literal_value(index, PROFILE_NODE, P_FACT_COUNT, XSD_NNI))
    event_count = _parse_nni(_literal_value(index, PROFILE_NODE, P_EVENT_COUNT, XSD_NNI))
    record_count = _parse_nni(_literal_value(index, PROFILE_NODE, P_RECORD_COUNT, XSD_NNI))
    vocab_terms = index.objects(PROFILE_NODE, P_USES_ONTOLOGY)
    if any(term.kind != "iri" for term in vocab_terms) or {term.value for term in vocab_terms} != set(REFERENCED_VOCABULARIES):
        raise OntologyProfileError("usesOntology set is not exact")

    fact_nodes = sorted(subject for subject in index.by_subject if C_ASSERTION in index.types(subject))
    event_nodes = sorted(subject for subject in index.by_subject if index.types(subject) & {C_RETRACT, C_SUPERSEDE})
    if len(fact_nodes) != fact_count or len(event_nodes) != event_count or record_count != fact_count + event_count:
        raise OntologyProfileError("profile record counts do not match resources")

    graph = TemporalEvidenceGraph()
    sources: dict[str, tuple[str, str]] = {}
    for node in fact_nodes:
        graph.add_fact(_fact_from_index(index, node, sources))
    events = [_event_from_index(index, node, sources) for node in event_nodes]
    for event in sorted(events, key=lambda item: (item.observed_at, item.event_id)):
        try:
            graph.add_event(event)
        except TemporalEvidenceError as exc:
            raise OntologyProfileError(f"event graph consistency failure: {exc}") from exc

    canonical_jsonl = graph.to_jsonl()
    if _sha(canonical_jsonl.encode("utf-8")) != expected_jsonl_sha:
        raise OntologyProfileError("reconstructed JSONL digest does not match profile header")
    canonical_nt = _build_ntriples(graph)
    if canonical_nt != text:
        raise OntologyProfileError("graph is outside the exact emitted profile")
    return graph

__all__ = tuple(name for name in globals() if not name.startswith("__"))
