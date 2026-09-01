"""Typed, synthetic-safe evidence objects for ChartTrace.

The schema deliberately keeps record facts, external authority, investigative
leads, and professional review separate.  It contains no inference engine and
does not assign legal or clinical significance.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
import re
from typing import Any


SCHEMA_VERSION = "charttrace-evidence-v1"
_ID_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._:-]{0,127}$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class EvidenceLayer(str, Enum):
    RECORD_FACT = "RECORD_FACT"
    EXTERNAL_AUTHORITY = "EXTERNAL_AUTHORITY"
    INVESTIGATIVE_LEAD = "INVESTIGATIVE_LEAD"
    COUNSEL_OR_CLINICIAN_REVIEW = "COUNSEL_OR_CLINICIAN_REVIEW"


class EvidenceGrade(str, Enum):
    CLUE = "CLUE"
    SUPPORTED = "SUPPORTED"
    CORROBORATED = "CORROBORATED"
    EXPLICIT = "EXPLICIT"


class RelevanceGrade(str, Enum):
    TENUOUS = "TENUOUS"
    PLAUSIBLE = "PLAUSIBLE"
    MATERIAL_IF_CONFIRMED = "MATERIAL_IF_CONFIRMED"
    PRIORITY_REVIEW = "PRIORITY_REVIEW"


def _require_id(value: str, field: str) -> None:
    if not _ID_RE.fullmatch(value):
        raise ValueError(f"{field} must be a stable, non-sensitive identifier")


def _require_sha256(value: str, field: str = "source_sha256") -> None:
    if not _SHA256_RE.fullmatch(value):
        raise ValueError(f"{field} must be a lowercase SHA-256 hex digest")


@dataclass(frozen=True, slots=True)
class SourceCitation:
    """An exact page citation with either a text span or bounding box."""

    document_id: str
    page: int
    source_sha256: str
    span_start: int | None = None
    span_end: int | None = None
    bbox: tuple[float, float, float, float] | None = None

    def __post_init__(self) -> None:
        _require_id(self.document_id, "document_id")
        _require_sha256(self.source_sha256)
        if self.page < 1:
            raise ValueError("page must be one-based")
        has_span = self.span_start is not None or self.span_end is not None
        if has_span:
            if self.span_start is None or self.span_end is None:
                raise ValueError("span_start and span_end must be provided together")
            if self.span_start < 0 or self.span_end <= self.span_start:
                raise ValueError("citation span must be non-empty and ordered")
        if self.bbox is not None:
            x1, y1, x2, y2 = self.bbox
            if not (0 <= x1 < x2 <= 1 and 0 <= y1 < y2 <= 1):
                raise ValueError("bbox coordinates must be normalized and ordered")
        if not has_span and self.bbox is None:
            raise ValueError("citation requires a text span or bounding box")


@dataclass(frozen=True, slots=True)
class RecordFact:
    fact_id: str
    text: str
    citation: SourceCitation
    observed_at: str | None = None
    layer: EvidenceLayer = EvidenceLayer.RECORD_FACT

    def __post_init__(self) -> None:
        _require_id(self.fact_id, "fact_id")
        if self.layer is not EvidenceLayer.RECORD_FACT:
            raise ValueError("RecordFact must remain in the RECORD_FACT layer")
        if not self.text.strip():
            raise ValueError("fact text must not be empty")
        if "\n" in self.text:
            raise ValueError("facts must be atomic single-line observations")


@dataclass(frozen=True, slots=True)
class ExternalAuthority:
    authority_id: str
    authority_type: str
    issuer: str
    jurisdiction: str
    effective_from: str
    effective_to: str | None
    primary_url: str
    pinpoint: str
    retrieval_date: str
    supported_proposition: str
    supersession_state: str
    applicability: str
    layer: EvidenceLayer = EvidenceLayer.EXTERNAL_AUTHORITY

    def __post_init__(self) -> None:
        _require_id(self.authority_id, "authority_id")
        if self.layer is not EvidenceLayer.EXTERNAL_AUTHORITY:
            raise ValueError("ExternalAuthority must remain in its own layer")
        required = (
            self.authority_type,
            self.issuer,
            self.jurisdiction,
            self.effective_from,
            self.primary_url,
            self.pinpoint,
            self.retrieval_date,
            self.supported_proposition,
            self.supersession_state,
        )
        if any(not value.strip() for value in required):
            raise ValueError("authority provenance fields must not be empty")
        if self.applicability not in {
            "context_only",
            "clinician_confirmed",
            "counsel_confirmed",
            "inapplicable",
        }:
            raise ValueError("unsupported authority applicability")


@dataclass(frozen=True, slots=True)
class InvestigativeLead:
    lead_id: str
    title: str
    domain: str
    care_phase: str
    cited_observation: str
    hypothesis: str
    review_question: str
    supporting_fact_ids: tuple[str, ...]
    counterevidence_fact_ids: tuple[str, ...]
    conflict_ids: tuple[str, ...]
    missing_records: tuple[str, ...]
    alternative_explanations: tuple[str, ...]
    source_universe_searched: tuple[str, ...]
    external_authority_ids: tuple[str, ...]
    jurisdiction: str
    authority_date_scope: str
    evidence_grade: EvidenceGrade
    relevance_grade: RelevanceGrade
    clinical_plausibility: str
    temporal_linkage: str
    peer_version: str
    model_version: str
    prompt_version: str
    policy_version: str
    review_history: tuple[str, ...] = ()
    layer: EvidenceLayer = EvidenceLayer.INVESTIGATIVE_LEAD

    def __post_init__(self) -> None:
        _require_id(self.lead_id, "lead_id")
        if self.layer is not EvidenceLayer.INVESTIGATIVE_LEAD:
            raise ValueError("InvestigativeLead must remain in its own layer")
        required = (
            self.title,
            self.domain,
            self.care_phase,
            self.cited_observation,
            self.hypothesis,
            self.review_question,
            self.jurisdiction,
            self.authority_date_scope,
            self.clinical_plausibility,
            self.temporal_linkage,
        )
        if any(not value.strip() for value in required):
            raise ValueError("lead metadata, scope, observation, and review fields are required")
        if not self.supporting_fact_ids:
            raise ValueError("a lead requires at least one cited supporting fact")
        if not self.source_universe_searched:
            raise ValueError("a lead must bound its source universe")
        for field_name, values in (
            ("supporting_fact_ids", self.supporting_fact_ids),
            ("counterevidence_fact_ids", self.counterevidence_fact_ids),
            ("external_authority_ids", self.external_authority_ids),
        ):
            for value in values:
                _require_id(value, field_name)
        versions = (self.peer_version, self.model_version, self.prompt_version, self.policy_version)
        if any(not value.strip() for value in versions):
            raise ValueError("peer/model/prompt/policy provenance is required")


def to_primitive(value: Any) -> Any:
    """Convert a schema object to deterministic JSON-compatible primitives."""

    if isinstance(value, Enum):
        return value.value
    if hasattr(value, "__dataclass_fields__"):
        return to_primitive(asdict(value))
    if isinstance(value, dict):
        return {str(key): to_primitive(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [to_primitive(item) for item in value]
    return value
