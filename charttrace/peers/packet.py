"""Peer input packet: sealed synthetic derivatives only."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional

from charttrace.peers.contracts import detect_forbidden_inputs, strip_forbidden_inputs
from charttrace.peers.sanitize import InjectionFinding, collect_injection_findings, quarantine_excerpts
from charttrace.peers.validate import (
    ALLOWED_PACKET_KEYS,
    assert_excerpt_contract,
    assert_packet_allowlist,
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
    sealed_peer_results: Optional[List[Dict[str, Any]]] = None

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
            "sealed_peer_results": self.sealed_peer_results,
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
        return cleaned

    def injection_findings(self) -> List[InjectionFinding]:
        return collect_injection_findings([e.to_dict() for e in self.excerpts])


def packet_from_mapping(data: Mapping[str, Any]) -> PeerPacket:
    incoming = dict(data)
    extra = sorted(set(incoming.keys()) - ALLOWED_PACKET_KEYS)
    if extra:
        raise ValueError(f"unknown packet metadata rejected: {extra}")
    cleaned = strip_forbidden_inputs(incoming)
    assert_packet_allowlist(cleaned)
    excerpts = []
    for ex in cleaned.get("excerpts", []):
        assert_excerpt_contract(ex)
        excerpts.append(
            RecordExcerpt(
                document_id=str(ex["document_id"]),
                page=int(ex["page"]),
                source_sha256=str(ex["source_sha256"]),
                text=str(ex["text"]),
                care_phase=str(ex.get("care_phase", "unspecified")),
                source_category=str(ex.get("source_category", "clinical_note")),
            )
        )
    assert_synthetic_id(cleaned["case_id"], "case_id", packet_id=True)
    parse_iso_date(str(cleaned.get("care_date_start", "")), "care_date_start")
    parse_iso_date(str(cleaned.get("care_date_end", "")), "care_date_end")
    return PeerPacket(
        case_id=str(cleaned["case_id"]),
        jurisdiction=str(cleaned.get("jurisdiction", "US-federal-context")),
        care_date_start=str(cleaned.get("care_date_start", "")),
        care_date_end=str(cleaned.get("care_date_end", "")),
        excerpts=excerpts,
        known_facts=[str(x) for x in cleaned.get("known_facts", [])],
        source_universe=[str(x) for x in cleaned.get("source_universe", [])],
        grounding_pack_ids=[str(x) for x in cleaned.get("grounding_pack_ids", [])],
        sealed_peer_results=cleaned.get("sealed_peer_results"),
    )
