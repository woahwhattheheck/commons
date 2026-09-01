"""Grounding pack schema — authority context, not liability conclusions."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Dict, Optional


class GroundingStatus(str, Enum):
    CONTEXT_ONLY = "context_only"
    CLINICIAN_CONFIRMED = "clinician_confirmed"
    COUNSEL_CONFIRMED = "counsel_confirmed"
    INAPPLICABLE = "inapplicable"


@dataclass(frozen=True)
class GroundingPack:
    pack_id: str
    authority_type: str
    issuer: str
    jurisdiction: str
    effective_from: str
    effective_to: Optional[str]
    care_date_match_rule: str
    primary_url: str
    pinpoint: str
    retrieval_date: str
    supported_proposition: str
    supersession: str
    status: GroundingStatus
    engineering_anchor_only: bool = False
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["status"] = self.status.value
        return data


REQUIRED_PACK_FIELDS = frozenset(
    {
        "pack_id",
        "authority_type",
        "issuer",
        "jurisdiction",
        "effective_from",
        "effective_to",
        "care_date_match_rule",
        "primary_url",
        "pinpoint",
        "retrieval_date",
        "supported_proposition",
        "supersession",
        "status",
    }
)


def assert_pack_complete(pack: Dict[str, Any]) -> None:
    missing = sorted(REQUIRED_PACK_FIELDS - set(pack.keys()))
    if missing:
        raise ValueError(f"grounding pack missing fields: {missing}")
    if pack["status"] not in {s.value for s in GroundingStatus}:
        raise ValueError(f"invalid grounding status: {pack['status']}")
