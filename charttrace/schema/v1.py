"""Frozen ChartTrace v1.1 evidence objects.

The schema deliberately separates record facts, external authority,
investigative hypotheses, and professional review.  No object in this module
represents a legal or clinical conclusion.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, fields, is_dataclass
from enum import Enum
from typing import Any, Dict, Mapping, Optional, Sequence, Tuple, Union


SCHEMA_VERSION = "charttrace.schema.v1.1"
GLOBAL_SCOPE_STATEMENT = (
    "ChartTrace is an investigative research aid. It separates "
    "record-supported observations, external authority, hypotheses, "
    "counterevidence, and professional review questions. Licensed counsel "
    "determines legal significance; qualified clinicians determine clinical "
    "significance."
)


class _StringEnum(str, Enum):
    def __str__(self) -> str:
        return self.value


class EvidenceObjectType(_StringEnum):
    OBSERVATION = "OBSERVATION"
    RECORD_FACT = "RECORD_FACT"
    HYPOTHESIS = "HYPOTHESIS"
    EXTERNAL_AUTHORITY = "EXTERNAL_AUTHORITY"
    COUNTEREVIDENCE = "COUNTEREVIDENCE"
    MISSING_PROOF = "MISSING_PROOF"
    INVESTIGATIVE_LEAD = "INVESTIGATIVE_LEAD"
    COUNSEL_OR_CLINICIAN_REVIEW = "COUNSEL_OR_CLINICIAN_REVIEW"


OBSERVATION = EvidenceObjectType.OBSERVATION
RECORD_FACT = EvidenceObjectType.RECORD_FACT
HYPOTHESIS = EvidenceObjectType.HYPOTHESIS
EXTERNAL_AUTHORITY = EvidenceObjectType.EXTERNAL_AUTHORITY
COUNTEREVIDENCE = EvidenceObjectType.COUNTEREVIDENCE
MISSING_PROOF = EvidenceObjectType.MISSING_PROOF
INVESTIGATIVE_LEAD = EvidenceObjectType.INVESTIGATIVE_LEAD
COUNSEL_OR_CLINICIAN_REVIEW = EvidenceObjectType.COUNSEL_OR_CLINICIAN_REVIEW


class EvidenceGrade(_StringEnum):
    CLUE = "CLUE"
    SUPPORTED = "SUPPORTED"
    CORROBORATED = "CORROBORATED"
    EXPLICIT = "EXPLICIT"


class RelevanceGrade(_StringEnum):
    TENUOUS = "TENUOUS"
    PLAUSIBLE = "PLAUSIBLE"
    MATERIAL_IF_CONFIRMED = "MATERIAL_IF_CONFIRMED"
    PRIORITY_REVIEW = "PRIORITY_REVIEW"


class AuthorityReviewStatus(_StringEnum):
    CONTEXT_ONLY = "context_only"
    CLINICIAN_CONFIRMED = "clinician_confirmed"
    COUNSEL_CONFIRMED = "counsel_confirmed"
    INAPPLICABLE = "inapplicable"


class ReviewDisposition(_StringEnum):
    PASS = "PASS"
    REPAIR = "REPAIR"
    DOWNGRADE = "DOWNGRADE"
    WEAK_APPENDIX = "WEAK_APPENDIX"
    MERGE_DUPLICATE = "MERGE_DUPLICATE"
    REJECT_UNSUPPORTED = "REJECT_UNSUPPORTED"
    HOLD = "HOLD"


class DateCertainty(_StringEnum):
    EXACT = "EXACT"
    APPROXIMATE = "APPROXIMATE"
    RANGE = "RANGE"
    UNDATED = "UNDATED"


class ForbiddenSemanticClaim(_StringEnum):
    MALPRACTICE = "MALPRACTICE"
    NEGLIGENCE = "NEGLIGENCE"
    CAUSE_OF_DEATH = "CAUSE_OF_DEATH"
    STANDARD_OF_CARE_BREACH = "STANDARD_OF_CARE_BREACH"
    NOT_DISCLOSED = "NOT_DISCLOSED"
    PATIENT_WAS_NOT_TOLD = "PATIENT_WAS_NOT_TOLD"


FORBIDDEN_SEMANTIC_CLAIMS: Tuple[ForbiddenSemanticClaim, ...] = tuple(
    ForbiddenSemanticClaim
)

_FORBIDDEN_PATTERNS = {
    ForbiddenSemanticClaim.MALPRACTICE: re.compile(r"\bmalpractice\b", re.I),
    ForbiddenSemanticClaim.NEGLIGENCE: re.compile(r"\bnegligen(?:ce|t)\b", re.I),
    ForbiddenSemanticClaim.CAUSE_OF_DEATH: re.compile(
        r"\bcause[\s_-]+of[\s_-]+death\b", re.I
    ),
    ForbiddenSemanticClaim.STANDARD_OF_CARE_BREACH: re.compile(
        r"\bstandard[\s_-]+of[\s_-]+care[\s_-]+breach\b", re.I
    ),
    ForbiddenSemanticClaim.NOT_DISCLOSED: re.compile(
        r"\b(?:was\s+)?not[\s_-]+disclosed\b", re.I
    ),
    ForbiddenSemanticClaim.PATIENT_WAS_NOT_TOLD: re.compile(
        r"\bpatient[\s_-]+was[\s_-]+not[\s_-]+told\b", re.I
    ),
}

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")


class SchemaValidationError(ValueError):
    """Raised when an evidence object violates the frozen v1 contract."""


class DuplicateIdError(SchemaValidationError):
    """Raised when two evidence objects share one stable identifier."""


class OrphanCitationError(SchemaValidationError):
    """Raised when a citation or object reference cannot be resolved."""


def find_forbidden_semantic_claims(text: str) -> Tuple[ForbiddenSemanticClaim, ...]:
    """Return forbidden conclusion-like claims present in ``text``."""

    return tuple(
        claim for claim, pattern in _FORBIDDEN_PATTERNS.items() if pattern.search(text)
    )


def assert_permitted_semantics(text: str, *, field_name: str = "text") -> None:
    found = find_forbidden_semantic_claims(text)
    if found:
        names = ", ".join(claim.value for claim in found)
        raise SchemaValidationError(
            f"{field_name} contains forbidden semantic claim(s): {names}"
        )


def _validate_identifier(value: str, field_name: str) -> None:
    if not _IDENTIFIER_RE.fullmatch(value):
        raise SchemaValidationError(f"{field_name} is not a stable identifier")


def _as_tuple(value: Sequence[Any]) -> Tuple[Any, ...]:
    return value if isinstance(value, tuple) else tuple(value)


@dataclass(frozen=True, slots=True)
class TextSpan:
    start: int
    end: int
    quote: str = ""

    def __post_init__(self) -> None:
        if self.start < 0 or self.end <= self.start:
            raise SchemaValidationError("text span must have 0 <= start < end")


@dataclass(frozen=True, slots=True)
class BoundingBox:
    x0: float
    y0: float
    x1: float
    y1: float

    def __post_init__(self) -> None:
        if self.x0 < 0 or self.y0 < 0 or self.x1 <= self.x0 or self.y1 <= self.y0:
            raise SchemaValidationError("bounding box coordinates are invalid")


SpanOrBoundingBox = Union[TextSpan, BoundingBox]


@dataclass(frozen=True, slots=True)
class Citation:
    document: str
    page: int
    span_or_bbox: SpanOrBoundingBox
    source_hash: str

    def __post_init__(self) -> None:
        _validate_identifier(self.document, "document")
        if self.page < 1:
            raise SchemaValidationError("citation page is one-based")
        if not isinstance(self.span_or_bbox, (TextSpan, BoundingBox)):
            raise SchemaValidationError(
                "span_or_bbox must be a TextSpan or BoundingBox"
            )
        if not _SHA256_RE.fullmatch(self.source_hash):
            raise SchemaValidationError("source_hash must be lowercase SHA-256")


@dataclass(frozen=True, slots=True)
class Observation:
    observation_id: str
    statement: str
    citation: Citation
    domain: str
    care_phase: str
    object_type: EvidenceObjectType = EvidenceObjectType.OBSERVATION

    def __post_init__(self) -> None:
        _validate_identifier(self.observation_id, "observation_id")
        assert_permitted_semantics(self.statement, field_name="statement")
        if self.object_type is not EvidenceObjectType.OBSERVATION:
            raise SchemaValidationError("Observation object_type cannot be changed")


@dataclass(frozen=True, slots=True)
class RecordFact:
    fact_id: str
    statement: str
    citation: Citation
    domain: str
    care_phase: str
    event_date: Optional[str] = None
    date_certainty: DateCertainty = DateCertainty.UNDATED
    object_type: EvidenceObjectType = EvidenceObjectType.RECORD_FACT

    def __post_init__(self) -> None:
        _validate_identifier(self.fact_id, "fact_id")
        assert_permitted_semantics(self.statement, field_name="statement")
        if self.object_type is not EvidenceObjectType.RECORD_FACT:
            raise SchemaValidationError("RecordFact object_type cannot be changed")


Fact = RecordFact


@dataclass(frozen=True, slots=True)
class Hypothesis:
    hypothesis_id: str
    statement: str
    cited_observations: Tuple[str, ...]
    citation: Citation
    object_type: EvidenceObjectType = EvidenceObjectType.HYPOTHESIS

    def __post_init__(self) -> None:
        _validate_identifier(self.hypothesis_id, "hypothesis_id")
        object.__setattr__(self, "cited_observations", _as_tuple(self.cited_observations))
        if not self.cited_observations:
            raise SchemaValidationError("hypothesis must cite at least one observation")
        for observation_id in self.cited_observations:
            _validate_identifier(observation_id, "cited_observations item")
        assert_permitted_semantics(self.statement, field_name="statement")
        if self.object_type is not EvidenceObjectType.HYPOTHESIS:
            raise SchemaValidationError("Hypothesis object_type cannot be changed")


@dataclass(frozen=True, slots=True)
class ExternalAuthority:
    authority_id: str
    authority_type: str
    issuer: str
    jurisdiction: str
    effective_from: str
    effective_to: Optional[str]
    care_date_match: bool
    primary_url: str
    pinpoint: str
    retrieval_date: str
    supported_proposition: str
    supersession: Optional[str]
    review_status: AuthorityReviewStatus
    citation: Optional[Citation] = None
    object_type: EvidenceObjectType = EvidenceObjectType.EXTERNAL_AUTHORITY

    def __post_init__(self) -> None:
        _validate_identifier(self.authority_id, "authority_id")
        assert_permitted_semantics(
            self.supported_proposition, field_name="supported_proposition"
        )
        if self.object_type is not EvidenceObjectType.EXTERNAL_AUTHORITY:
            raise SchemaValidationError(
                "ExternalAuthority object_type cannot be changed"
            )


Authority = ExternalAuthority


@dataclass(frozen=True, slots=True)
class Counterevidence:
    counterevidence_id: str
    statement: str
    counters: str
    citation: Citation
    object_type: EvidenceObjectType = EvidenceObjectType.COUNTEREVIDENCE

    def __post_init__(self) -> None:
        _validate_identifier(self.counterevidence_id, "counterevidence_id")
        _validate_identifier(self.counters, "counters")
        assert_permitted_semantics(self.statement, field_name="statement")
        if self.object_type is not EvidenceObjectType.COUNTEREVIDENCE:
            raise SchemaValidationError(
                "Counterevidence object_type cannot be changed"
            )


@dataclass(frozen=True, slots=True)
class MissingProof:
    missing_proof_id: str
    statement: str
    needed_for: str
    citation: Optional[Citation] = None
    object_type: EvidenceObjectType = EvidenceObjectType.MISSING_PROOF

    def __post_init__(self) -> None:
        _validate_identifier(self.missing_proof_id, "missing_proof_id")
        _validate_identifier(self.needed_for, "needed_for")
        assert_permitted_semantics(self.statement, field_name="statement")
        if self.object_type is not EvidenceObjectType.MISSING_PROOF:
            raise SchemaValidationError("MissingProof object_type cannot be changed")


@dataclass(frozen=True, slots=True)
class ReviewHistoryEntry:
    reviewer_role: str
    disposition: ReviewDisposition
    reviewed_at: str
    reason: str
    reviewer_id: Optional[str] = None

    def __post_init__(self) -> None:
        assert_permitted_semantics(self.reason, field_name="review reason")


@dataclass(frozen=True, slots=True)
class InvestigativeLead:
    lead_id: str
    neutral_title: str
    domain: str
    care_phase: str
    cited_observation: str
    hypothesis: str
    review_question: str
    supporting_facts: Tuple[str, ...]
    counterevidence: Tuple[str, ...]
    conflicts: Tuple[str, ...]
    missing_records: Tuple[str, ...]
    alternative_explanations: Tuple[str, ...]
    source_universe_searched: Tuple[str, ...]
    external_authorities: Tuple[str, ...]
    jurisdiction_scope: str
    date_scope: str
    evidence_grade: EvidenceGrade
    relevance_grade: RelevanceGrade
    clinical_plausibility: str
    temporal_linkage: str
    peer_version: str
    model_version: str
    prompt_version: str
    policy_version: str
    review_history: Tuple[ReviewHistoryEntry, ...]
    object_type: EvidenceObjectType = EvidenceObjectType.INVESTIGATIVE_LEAD

    def __post_init__(self) -> None:
        _validate_identifier(self.lead_id, "lead_id")
        tuple_fields = (
            "supporting_facts",
            "counterevidence",
            "conflicts",
            "missing_records",
            "alternative_explanations",
            "source_universe_searched",
            "external_authorities",
            "review_history",
        )
        for field_name in tuple_fields:
            object.__setattr__(self, field_name, _as_tuple(getattr(self, field_name)))

        for field_name in (
            "neutral_title",
            "cited_observation",
            "hypothesis",
            "review_question",
            "clinical_plausibility",
            "temporal_linkage",
        ):
            assert_permitted_semantics(
                getattr(self, field_name), field_name=field_name
            )
        for field_name in (
            "counterevidence",
            "conflicts",
            "missing_records",
            "alternative_explanations",
        ):
            for value in getattr(self, field_name):
                assert_permitted_semantics(value, field_name=field_name)

        if not self.supporting_facts:
            raise SchemaValidationError("lead must cite at least one supporting fact")
        for fact_id in self.supporting_facts:
            _validate_identifier(fact_id, "supporting_facts item")
        for authority_id in self.external_authorities:
            _validate_identifier(authority_id, "external_authorities item")
        if self.object_type is not EvidenceObjectType.INVESTIGATIVE_LEAD:
            raise SchemaValidationError(
                "InvestigativeLead object_type cannot be changed"
            )


@dataclass(frozen=True, slots=True)
class CounselOrClinicianReview:
    review_id: str
    lead_id: str
    reviewer_role: str
    reviewer_id: str
    judgment: str
    disposition: ReviewDisposition
    reviewed_at: str
    object_type: EvidenceObjectType = (
        EvidenceObjectType.COUNSEL_OR_CLINICIAN_REVIEW
    )

    def __post_init__(self) -> None:
        _validate_identifier(self.review_id, "review_id")
        _validate_identifier(self.lead_id, "lead_id")
        _validate_identifier(self.reviewer_id, "reviewer_id")
        assert_permitted_semantics(self.judgment, field_name="judgment")
        if self.object_type is not EvidenceObjectType.COUNSEL_OR_CLINICIAN_REVIEW:
            raise SchemaValidationError(
                "CounselOrClinicianReview object_type cannot be changed"
            )


EvidenceObject = Union[
    Observation,
    RecordFact,
    Hypothesis,
    ExternalAuthority,
    Counterevidence,
    MissingProof,
    InvestigativeLead,
    CounselOrClinicianReview,
]


_ID_FIELDS = (
    "observation_id",
    "fact_id",
    "hypothesis_id",
    "authority_id",
    "counterevidence_id",
    "missing_proof_id",
    "lead_id",
    "review_id",
)


def object_id(value: Any) -> str:
    for field_name in _ID_FIELDS:
        if hasattr(value, field_name):
            return str(getattr(value, field_name))
    raise SchemaValidationError("object has no stable identifier")


def citations_of(value: Any) -> Tuple[Citation, ...]:
    found = []
    citation = getattr(value, "citation", None)
    if isinstance(citation, Citation):
        found.append(citation)
    return tuple(found)


def assert_unique_ids(objects: Sequence[Any]) -> Dict[str, Any]:
    """Reject duplicate stable IDs across a typed object graph."""

    seen: Dict[str, Any] = {}
    for value in objects:
        identifier = object_id(value)
        if identifier in seen:
            raise DuplicateIdError(f"duplicate object id: {identifier}")
        seen[identifier] = value
    return seen


def assert_citations_resolve(
    objects: Sequence[Any],
    *,
    known_source_hashes: Sequence[str],
    known_documents: Sequence[str],
) -> None:
    """Reject orphan citations and dangling object references."""

    hashes = set(known_source_hashes)
    documents = set(known_documents)
    ids = assert_unique_ids(objects)
    for value in objects:
        for citation in citations_of(value):
            if citation.source_hash not in hashes or citation.document not in documents:
                raise OrphanCitationError(
                    f"orphan citation {citation.document} page {citation.page}"
                )
        for field_name in ("cited_observations", "supporting_facts"):
            for reference in getattr(value, field_name, ()):
                if reference not in ids:
                    raise OrphanCitationError(f"orphan object reference: {reference}")
        for field_name in ("counters", "needed_for"):
            reference = getattr(value, field_name, None)
            if reference and reference not in ids:
                raise OrphanCitationError(f"orphan object reference: {reference}")


def to_primitive(value: Any) -> Any:
    """Convert frozen schema objects into deterministic JSON primitives."""

    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return {
            field.name: to_primitive(getattr(value, field.name))
            for field in fields(value)
        }
    if isinstance(value, Mapping):
        return {
            str(key): to_primitive(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, (tuple, list)):
        return [to_primitive(item) for item in value]
    return value
