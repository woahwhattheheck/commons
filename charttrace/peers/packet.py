"""Peer input packet: sealed synthetic derivatives only."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional

from charttrace.peers.contracts import detect_forbidden_inputs, strip_forbidden_inputs
from charttrace.peers.sanitize import InjectionFinding, collect_injection_findings, quarantine_excerpts
from charttrace.peers.validate import (
    ALLOWED_PACKET_KEYS,
    assert_care_phase,
    assert_excerpt_contract,
    assert_packet_allowlist,
    assert_raw_packet_types,
    assert_source_category,
    assert_synthetic_id,
    parse_iso_date,
)


@dataclass(frozen=True)
class RecordExcerpt:
    document_id: str
    page: int
    source_sha256: str
    text: str
    care_phase: str = "unspecified"
    source_category: str = "clinical_note"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "document_id": self.document_id,
            "page": self.page,
            "source_sha256": self.source_sha256,
            "text": self.text,
            "care_phase": self.care_phase,
            "source_category": self.source_category,
        }


@dataclass
class PeerPacket:
    """Inputs visible to a single isolated peer worker."""

    case_id: str
    jurisdiction: str
    care_date_start: str
    care_date_end: str
    excerpts: List[RecordExcerpt]
    known_facts: List[str] = field(default_factory=list)
    source_universe: List[str] = field(default_factory=list)
    grounding_pack_ids: List[str] = field(default_factory=list)
    sealed_peer_results: Optional[List[Dict[str, Any]]] = field(
        default=None, repr=False, compare=False
    )

    def to_allowlisted_dict(self) -> Dict[str, Any]:
        raw = {
            "case_id": self.case_id,
            "jurisdiction": self.jurisdiction,
            "care_date_start": self.care_date_start,
            "care_date_end": self.care_date_end,
            "excerpts": [e.to_dict() for e in self.excerpts],
            "known_facts": list(self.known_facts),
            "source_universe": list(self.source_universe),
            "grounding_pack_ids": list(self.grounding_pack_ids),
        }
        cleaned = strip_forbidden_inputs(raw)
        extra = sorted(set(cleaned.keys()) - ALLOWED_PACKET_KEYS)
        if extra:
            raise ValueError(f"unknown packet metadata rejected: {extra}")
        assert_packet_allowlist(cleaned)
        assert_synthetic_id(cleaned["case_id"], "case_id", packet_id=True)
        parse_iso_date(cleaned["care_date_start"], "care_date_start")
        parse_iso_date(cleaned["care_date_end"], "care_date_end")
        for ex in cleaned.get("excerpts", []):
            assert_excerpt_contract(ex)
        forbidden = detect_forbidden_inputs(cleaned)
        if forbidden:
            raise ValueError(f"forbidden peer inputs remain: {forbidden}")
        return cleaned

    def to_sanitized_dict(self) -> Dict[str, Any]:
        cleaned = self.to_allowlisted_dict()
        quarantined, _findings = quarantine_excerpts(list(cleaned.get("excerpts") or []))
        cleaned["excerpts"] = quarantined
        cleaned.pop("known_facts", None)
        return cleaned

    def injection_findings(self) -> List[InjectionFinding]:
        return collect_injection_findings([e.to_dict() for e in self.excerpts])


def attach_runner_sealed(
    packet: PeerPacket, sealed: Optional[List[Dict[str, Any]]]
) -> PeerPacket:
    packet.sealed_peer_results = list(sealed or [])
    return packet


def packet_from_mapping(data: Mapping[str, Any]) -> PeerPacket:
    incoming = dict(data)
    extra = sorted(set(incoming.keys()) - ALLOWED_PACKET_KEYS)
    if extra:
        raise ValueError(f"unknown packet metadata rejected: {extra}")
    assert_raw_packet_types(incoming)
    cleaned = strip_forbidden_inputs(incoming)
    assert_packet_allowlist(cleaned)
    excerpts = []
    for ex in cleaned.get("excerpts", []):
        assert_excerpt_contract(ex)
        care_phase = ex.get("care_phase", "unspecified")
        source_category = ex.get("source_category", "clinical_note")
        assert_care_phase(care_phase)
        assert_source_category(source_category)
        excerpts.append(
            RecordExcerpt(
                document_id=ex["document_id"],
                page=ex["page"],
                source_sha256=ex["source_sha256"],
                text=ex["text"],
                care_phase=care_phase,
                source_category=source_category,
            )
        )
    assert_synthetic_id(cleaned["case_id"], "case_id", packet_id=True)
    parse_iso_date(cleaned["care_date_start"], "care_date_start")
    parse_iso_date(cleaned["care_date_end"], "care_date_end")
    return PeerPacket(
        case_id=cleaned["case_id"],
        jurisdiction=cleaned.get("jurisdiction", "US-federal-context"),
        care_date_start=cleaned["care_date_start"],
        care_date_end=cleaned["care_date_end"],
        excerpts=excerpts,
        known_facts=list(cleaned.get("known_facts") or []),
        source_universe=list(cleaned.get("source_universe") or []),
        grounding_pack_ids=list(cleaned.get("grounding_pack_ids") or []),
        sealed_peer_results=None,
    )
