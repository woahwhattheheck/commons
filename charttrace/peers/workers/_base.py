"""Shared helpers for isolated deterministic peer workers."""

from __future__ import annotations

import hashlib
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from charttrace.peers.contracts import (
    EvidenceGrade,
    PeerLead,
    RelevanceGrade,
    assert_lead_complete,
)
from charttrace.peers.sanitize import collect_injection_findings, neutralize_as_document_text
from charttrace.peers.versions import (
    MODEL_VERSION,
    PEER_SWARM_VERSION,
    POLICY_VERSION,
    PROMPT_VERSION,
)


def _stable_id(*parts: str) -> str:
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:12]


def cite_excerpt(excerpt: Mapping[str, Any]) -> str:
    return (
        f"{excerpt.get('document_id', 'unknown')}:"
        f"p{excerpt.get('page', '?')}:"
        f"{str(excerpt.get('source_sha256', ''))[:12]}"
    )


def fact_from_excerpt(excerpt: Mapping[str, Any], snippet: str) -> str:
    clean = " ".join(snippet.split())
    if len(clean) > 240:
        clean = clean[:237] + "..."
    return f"{cite_excerpt(excerpt)} :: {clean}"


def find_keyword_hits(
    excerpts: Sequence[Mapping[str, Any]],
    keywords: Sequence[str],
) -> List[Tuple[Mapping[str, Any], str, str]]:
    hits: List[Tuple[Mapping[str, Any], str, str]] = []
    for ex in excerpts:
        text = str(ex.get("text", ""))
        neutralize_as_document_text(text)
        lower = text.lower()
        for kw in keywords:
            if kw.lower() in lower:
                idx = lower.find(kw.lower())
                start = max(0, idx - 40)
                end = min(len(text), idx + len(kw) + 80)
                hits.append((ex, kw, text[start:end].strip()))
    return hits


def build_lead(
    *,
    role_id: str,
    title: str,
    domain: str,
    care_phase: str,
    cited_observation: str,
    hypothesis: str,
    review_question: str,
    supporting_facts: Sequence[str],
    counterevidence: Sequence[str],
    conflicts: Sequence[str],
    missing_records: Sequence[str],
    alternative_explanations: Sequence[str],
    source_universe_searched: Sequence[str],
    external_authorities: Sequence[str],
    jurisdiction_date_scope: str,
    evidence_grade: EvidenceGrade,
    relevance_grade: RelevanceGrade,
    clinical_plausibility: str,
    temporal_linkage: str,
    weak_label: Optional[str] = None,
    review_history: Sequence[str] = (),
) -> Dict[str, Any]:
    lead_id = f"{role_id}-{_stable_id(title, cited_observation, hypothesis)}"
    lead = PeerLead(
        lead_id=lead_id,
        title=title,
        domain=domain,
        care_phase=care_phase,
        cited_observation=cited_observation,
        hypothesis=hypothesis,
        review_question=review_question,
        supporting_facts=tuple(supporting_facts),
        counterevidence=tuple(counterevidence),
        conflicts=tuple(conflicts),
        missing_records=tuple(missing_records),
        alternative_explanations=tuple(alternative_explanations),
        source_universe_searched=tuple(source_universe_searched),
        external_authorities=tuple(external_authorities),
        jurisdiction_date_scope=jurisdiction_date_scope,
        evidence_grade=evidence_grade,
        relevance_grade=relevance_grade,
        clinical_plausibility=clinical_plausibility,
        temporal_linkage=temporal_linkage,
        peer_version=f"{role_id}@1.1",
        model_version=MODEL_VERSION,
        prompt_version=PROMPT_VERSION,
        policy_version=POLICY_VERSION,
        review_history=tuple(review_history),
        weak_label=weak_label,
    )
    data = lead.to_dict()
    assert_lead_complete(data)
    return data


def base_result(
    role_id: str,
    packet: Mapping[str, Any],
    leads: List[Dict[str, Any]],
    *,
    notes: Optional[List[str]] = None,
) -> Dict[str, Any]:
    injections = [
        f.to_dict()
        for f in collect_injection_findings(list(packet.get("excerpts", [])))
    ]
    return {
        "role_id": role_id,
        "peer_swarm_version": PEER_SWARM_VERSION,
        "leads": leads,
        "injection_findings": injections,
        "injection_commands_followed": 0,
        "external_model_calls": 0,
        "notes": list(notes or []),
        "source_universe_searched": list(packet.get("source_universe", [])),
        "jurisdiction": packet.get("jurisdiction"),
        "care_date_scope": {
            "start": packet.get("care_date_start"),
            "end": packet.get("care_date_end"),
        },
    }


def bounded_absence(topic: str, corpus: str, start: str, end: str) -> str:
    return (
        f"No documentation of {topic} was located in the supplied {corpus} "
        f"for {start or 'START'}–{end or 'END'}."
    )


def default_universe(packet: Mapping[str, Any], extra: Sequence[str]) -> Tuple[str, ...]:
    base = list(packet.get("source_universe") or [])
    if not base:
        cats = [
            str(ex.get("source_category", "clinical_note"))
            for ex in packet.get("excerpts", [])
        ]
        base = sorted(set(cats)) or ["supplied_record_excerpts"]
    return tuple(dict.fromkeys(list(base) + list(extra)))


def jurisdiction_scope(packet: Mapping[str, Any]) -> str:
    return (
        f"{packet.get('jurisdiction', 'US-federal-context')} | "
        f"{packet.get('care_date_start', '?')}–{packet.get('care_date_end', '?')}"
    )
