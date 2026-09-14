from __future__ import annotations

import hashlib
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

# The profile is deliberately a sibling of the already-landed temporal engine.
_PARENT = Path(__file__).resolve().parents[1]
if str(_PARENT) not in sys.path:
    sys.path.insert(0, str(_PARENT))

from temporal_evidence import (  # type: ignore  # sibling module
    EvidenceEvent,
    Fact,
    TemporalEvidenceError,
    TemporalEvidenceGraph,
    canonical_json,
    digest_json,
    strict_json_loads,
)

UTC = timezone.utc
PROFILE_VERSION = "nih-temporal-kg-ontology/v1"
SOURCE_SCHEMA = "temporal-evidence-jsonl/v1"
MAX_TEXT_BYTES = 8 * 1024 * 1024
_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_ABSOLUTE_IRI = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:[^\x00-\x20<>\"{}|^`\\]*$")
_BIOLINK_CURIE = re.compile(r"^biolink:([A-Za-z][A-Za-z0-9_]*)$")
_CANONICAL_TS = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\.[0-9]{6}Z$")
_CANONICAL_INT = re.compile(r"^(?:0|[1-9][0-9]*)$")
_CANONICAL_DECIMAL = re.compile(r"^(?:0|[1-9][0-9]*)\.[0-9]+$")

RDF = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
RDFS = "http://www.w3.org/2000/01/rdf-schema#"
OWL = "http://www.w3.org/2002/07/owl#"
XSD = "http://www.w3.org/2001/XMLSchema#"
TIME = "http://www.w3.org/2006/time#"
PROV = "http://www.w3.org/ns/prov#"
BIOLINK = "https://w3id.org/biolink/vocab/"
NTKG = "https://woahwhattheheck.github.io/commons/ns/nih-temporal-kg/v1#"
NTKG_ONTOLOGY = NTKG[:-1]
PROFILE_NODE = "urn:ntkg:profile:v1"

RDF_TYPE = RDF + "type"
RDFS_SUBCLASS = RDFS + "subClassOf"
RDFS_DOMAIN = RDFS + "domain"
RDFS_RANGE = RDFS + "range"
OWL_CLASS = OWL + "Class"
OWL_OBJECT_PROPERTY = OWL + "ObjectProperty"
OWL_DATATYPE_PROPERTY = OWL + "DatatypeProperty"
OWL_FUNCTIONAL_PROPERTY = OWL + "FunctionalProperty"
OWL_ONTOLOGY = OWL + "Ontology"
XSD_STRING = XSD + "string"
XSD_DECIMAL = XSD + "decimal"
XSD_NNI = XSD + "nonNegativeInteger"
XSD_DATETIME_STAMP = XSD + "dateTimeStamp"
TIME_PROPER_INTERVAL = TIME + "ProperInterval"
TIME_INSTANT = TIME + "Instant"
TIME_HAS_BEGINNING = TIME + "hasBeginning"
TIME_HAS_END = TIME + "hasEnd"
TIME_IN_XSD = TIME + "inXSDDateTimeStamp"
PROV_ENTITY = PROV + "Entity"
PROV_GENERATED_AT = PROV + "generatedAtTime"
PROV_WAS_DERIVED_FROM = PROV + "wasDerivedFrom"

C_PROFILE = NTKG + "InteroperabilityProfile"
C_ASSERTION = NTKG + "TemporalAssertion"
C_RETRACT = NTKG + "RetractionEvent"
C_SUPERSEDE = NTKG + "SupersessionEvent"

P_PROFILE_VERSION = NTKG + "profileVersion"
P_SOURCE_SCHEMA = NTKG + "sourceSchema"
P_JSONL_SHA = NTKG + "jsonlSha256"
P_RECORD_COUNT = NTKG + "recordCount"
P_FACT_COUNT = NTKG + "factCount"
P_EVENT_COUNT = NTKG + "eventCount"
P_USES_ONTOLOGY = NTKG + "usesOntology"
P_FACT_ID = NTKG + "factId"
P_EVENT_ID = NTKG + "eventId"
P_SUBJECT_LEXEME = NTKG + "subjectLexeme"
P_PREDICATE_LEXEME = NTKG + "predicateLexeme"
P_OBJECT_LEXEME = NTKG + "objectLexeme"
P_SUBJECT_NODE = NTKG + "subjectNode"
P_PREDICATE_NODE = NTKG + "predicateNode"
P_OBJECT_NODE = NTKG + "objectNode"
P_VALIDITY = NTKG + "validityInterval"
P_CONFIDENCE = NTKG + "confidence"
P_ACTION = NTKG + "actionLexeme"
P_TARGET = NTKG + "targetAssertion"
P_REPLACEMENT = NTKG + "replacementAssertion"
P_SOURCE_ID = NTKG + "sourceId"
P_SOURCE_SHA = NTKG + "sourceSha256"

REFERENCED_VOCABULARIES = (
    "http://www.w3.org/2006/time",
    "http://www.w3.org/ns/prov-o",
    BIOLINK,
)


class OntologyProfileError(ValueError):
    """Raised when RDF data falls outside the exact interoperability profile."""


@dataclass(frozen=True, slots=True)
class Term:
    kind: str  # iri | literal
    value: str
    datatype: str | None = None


@dataclass(frozen=True, slots=True)
class Triple:
    subject: str
    predicate: str
    object: Term


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _ts(value: datetime) -> str:
    return value.astimezone(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _parse_ts_literal(value: str) -> datetime:
    if not _CANONICAL_TS.fullmatch(value):
        raise OntologyProfileError("dateTimeStamp must use canonical UTC microsecond form")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise OntologyProfileError("invalid dateTimeStamp") from exc
    if _ts(parsed) != value:
        raise OntologyProfileError("noncanonical dateTimeStamp")
    return parsed


def _decimal_lexeme(value: float | Decimal) -> str:
    if isinstance(value, float):
        dec = Decimal(str(value))
    elif isinstance(value, Decimal):
        dec = value
    else:
        raise OntologyProfileError("decimal value must be numeric")
    if not dec.is_finite() or dec < 0 or dec > 1:
        raise OntologyProfileError("confidence must be finite and within [0,1]")
    text = format(dec, "f")
    if "." not in text:
        text += ".0"
    else:
        text = text.rstrip("0").rstrip(".")
        if "." not in text:
            text += ".0"
    return text


def _parse_decimal(value: str) -> float:
    if not _CANONICAL_DECIMAL.fullmatch(value):
        raise OntologyProfileError("decimal must use canonical nonnegative lexical form")
    try:
        dec = Decimal(value)
    except InvalidOperation as exc:
        raise OntologyProfileError("invalid decimal") from exc
    if _decimal_lexeme(dec) != value:
        raise OntologyProfileError("noncanonical decimal")
    return float(dec)


def _parse_nni(value: str) -> int:
    if not _CANONICAL_INT.fullmatch(value):
        raise OntologyProfileError("nonNegativeInteger must be canonical")
    return int(value)


def _validate_iri(value: str) -> str:
    if not isinstance(value, str) or not _ABSOLUTE_IRI.fullmatch(value):
        raise OntologyProfileError(f"IRI is not absolute/canonical: {value!r}")
    return value

__all__ = tuple(name for name in globals() if not name.startswith("__"))
