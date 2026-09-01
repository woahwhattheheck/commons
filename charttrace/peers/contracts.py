"""Lead and input contracts for ChartTrace peer workers (Lane B)."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
import re
from typing import Any, Dict, List, Mapping, Optional, Tuple

from charttrace.peers.versions import MODEL_VERSION, POLICY_VERSION, PROMPT_VERSION


_ID_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._:-]{0,127}$")

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


def _require_id(value: str, field_name: str) -> None:
    if not isinstance(value, str) or not _ID_RE.fullmatch(value):
        raise ValueError(f"{field_name} must be a stable non-sensitive identifier")


def _require_nonempty(value: str, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} is required")


@dataclass(frozen=True)
class PeerLead:
    """Investigative lead with hard provenance fields (v1.1)."""

    lead_id: str
    title: str
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
    jurisdiction_date_scope: str
    evidence_grade: EvidenceGrade
    relevance_grade: RelevanceGrade
    clinical_plausibility: str
    temporal_linkage: str
    peer_version: str
    model_version: str = MODEL_VERSION
    prompt_version: str = PROMPT_VERSION
    policy_version: str = POLICY_VERSION
    review_history: Tuple[str, ...] = ()
    layer: EvidenceLayer = EvidenceLayer.INVESTIGATIVE_LEAD
    weak_label: Optional[str] = None

    def __post_init__(self) -> None:
        _require_id(self.lead_id, "lead_id")
        for name in (
            "title",
            "domain",
            "care_phase",
            "cited_observation",
            "hypothesis",
            "review_question",
            "jurisdiction_date_scope",
            "clinical_plausibility",
            "temporal_linkage",
            "peer_version",
            "model_version",
            "prompt_version",
            "policy_version",
        ):
            _require_nonempty(getattr(self, name), name)
        if not self.supporting_facts:
            raise ValueError("supporting_facts must cite at least one record fact")
        if not self.source_universe_searched:
            raise ValueError("source_universe_searched must bound the search")
        if self.layer is not EvidenceLayer.INVESTIGATIVE_LEAD:
            raise ValueError("PeerLead must remain INVESTIGATIVE_LEAD")
        if not isinstance(self.evidence_grade, EvidenceGrade):
            raise ValueError("evidence_grade invalid")
        if not isinstance(self.relevance_grade, RelevanceGrade):
            raise ValueError("relevance_grade invalid")

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["evidence_grade"] = self.evidence_grade.value
        data["relevance_grade"] = self.relevance_grade.value
        data["layer"] = self.layer.value
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
        "peer_version",
        "model_version",
        "prompt_version",
        "policy_version",
        "review_history",
    }
)


def assert_lead_complete(lead: Mapping[str, Any]) -> None:
    missing = sorted(REQUIRED_LEAD_FIELDS - set(lead.keys()))
    if missing:
        raise ValueError(f"lead missing fields: {missing}")


def strip_forbidden_inputs(payload: Mapping[str, Any]) -> Dict[str, Any]:
    def _walk(obj: Any) -> Any:
        if isinstance(obj, Mapping):
            return {
                k: _walk(v)
                for k, v in obj.items()
                if str(k).lower() not in FORBIDDEN_PEER_INPUT_KEYS
            }
        if isinstance(obj, list):
            return [_walk(v) for v in obj]
        if isinstance(obj, tuple):
            return tuple(_walk(v) for v in obj)
        return obj

    return _walk(dict(payload))


def detect_forbidden_inputs(payload: Mapping[str, Any]) -> List[str]:
    found: List[str] = []

    def _walk(obj: Any, path: str = "") -> None:
        if isinstance(obj, Mapping):
            for k, v in obj.items():
                key = str(k)
                here = f"{path}.{key}" if path else key
                if key.lower() in FORBIDDEN_PEER_INPUT_KEYS:
                    found.append(here)
                _walk(v, here)
        elif isinstance(obj, (list, tuple)):
            for i, v in enumerate(obj):
                _walk(v, f"{path}[{i}]")

    _walk(payload)
    return found
