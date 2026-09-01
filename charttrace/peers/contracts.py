"""Lead and input contracts for ChartTrace peer workers (Lane B)."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Dict, List, Mapping, Optional, Tuple

from charttrace.peers.versions import MODEL_VERSION, POLICY_VERSION, PROMPT_VERSION


FORBIDDEN_PEER_INPUT_KEYS = frozenset(
    {
        "price",
        "packet_price",
        "destination_firm",
        "destination",
        "firm",
        "firm_id",
        "firm_name",
        "affiliate",
        "affiliate_id",
        "affiliate_identity",
        "compensation",
        "review_fee",
        "contingency",
        "case_value",
        "recovery",
        "damages_value",
        "success_probability",
        "routing_score",
        "stripe",
        "payment",
        "payout",
    }
)


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


@dataclass(frozen=True)
class PeerCitation:
    document_id: str
    page: int
    source_sha256: str
    span_start: int
    span_end: int
    quote: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "document_id": self.document_id,
            "page": self.page,
            "source_sha256": self.source_sha256,
            "span_start": self.span_start,
            "span_end": self.span_end,
            "quote": self.quote,
        }


@dataclass(frozen=True)
class PeerLead:
    """Investigative lead with hard provenance fields (v1.2)."""

    lead_id: str
    title: str
    domain: str
    care_phase: str
    cited_observation: str
    hypothesis: str
    review_question: str
    supporting_facts: Tuple[str, ...]
    counterevidence: Tuple[Any, ...]
    conflicts: Tuple[str, ...]
    missing_records: Tuple[str, ...]
    alternative_explanations: Tuple[str, ...]
    source_universe_searched: Tuple[str, ...]
    external_authorities: Tuple[str, ...]
    jurisdiction_date_scope: str
    evidence_grade: EvidenceGrade
    relevance_grade: RelevanceGrade
    clinical_plausibility: str
    temporal_linkage: str
    temporal_date: str
    peer_version: str
    citations: Tuple[Dict[str, Any], ...] = ()
    model_version: str = MODEL_VERSION
    prompt_version: str = PROMPT_VERSION
    policy_version: str = POLICY_VERSION
    review_history: Tuple[str, ...] = ()
    layer: EvidenceLayer = EvidenceLayer.INVESTIGATIVE_LEAD
    weak_label: Optional[str] = None

    def __post_init__(self) -> None:
        from charttrace.peers.validate import assert_lead_complete

        assert_lead_complete(self.to_dict())

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["evidence_grade"] = self.evidence_grade.value
        data["relevance_grade"] = self.relevance_grade.value
        data["layer"] = self.layer.value
        data["citations"] = [dict(c) for c in self.citations]
        return data


REQUIRED_LEAD_FIELDS = frozenset(
    {
        "lead_id",
        "title",
        "domain",
        "care_phase",
        "cited_observation",
        "hypothesis",
        "review_question",
        "supporting_facts",
        "counterevidence",
        "conflicts",
        "missing_records",
        "alternative_explanations",
        "source_universe_searched",
        "external_authorities",
        "jurisdiction_date_scope",
        "evidence_grade",
        "relevance_grade",
        "clinical_plausibility",
        "temporal_linkage",
        "temporal_date",
        "peer_version",
        "model_version",
        "prompt_version",
        "policy_version",
        "review_history",
        "citations",
    }
)

ALLOWED_LEAD_KEYS = REQUIRED_LEAD_FIELDS | frozenset({"weak_label", "layer"})


def assert_lead_complete(lead: Mapping[str, Any]) -> None:
    from charttrace.peers.validate import assert_lead_complete as _assert

    _assert(lead)


def strip_forbidden_inputs(payload: Mapping[str, Any]) -> Dict[str, Any]:
    from charttrace.peers.validate import key_is_commercial

    def _walk(obj: Any) -> Any:
        if isinstance(obj, Mapping):
            return {k: _walk(v) for k, v in obj.items() if not key_is_commercial(str(k))}
        if isinstance(obj, list):
            return [_walk(v) for v in obj]
        if isinstance(obj, tuple):
            return tuple(_walk(v) for v in obj)
        return obj

    return _walk(dict(payload))


def detect_forbidden_inputs(payload: Mapping[str, Any]) -> List[str]:
    from charttrace.peers.validate import detect_commercial_aliases

    return detect_commercial_aliases(payload)
