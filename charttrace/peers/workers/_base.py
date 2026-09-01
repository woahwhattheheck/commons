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
from charttrace.peers.sanitize import QUARANTINE_MARKER, UNTRUSTED_PREFIX, quote_from_worker_span
from charttrace.peers.versions import MODEL_VERSION, POLICY_VERSION, PROMPT_VERSION

NEGATION_CUES = (
    "resolved",
    "documented discussion",
    "patient notified",
    "denied",
    "no evidence",
    "not indicated",
    "unrelated",
    "baseline",
    "expected course",
)


def _stable_id(*parts: str) -> str:
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:12]


def searched_universe(packet: Mapping[str, Any]) -> Tuple[str, ...]:
    cats = []
    for ex in packet.get("excerpts", []):
        cat = str(ex.get("source_category") or "clinical_note")
        if cat and cat not in cats:
            cats.append(cat)
    return tuple(cats) if cats else ("supplied_record_excerpts",)


def citation_from_excerpt(
    excerpt: Mapping[str, Any],
    start: int,
    end: int,
) -> Dict[str, Any]:
    raw_start, raw_end, quote = quote_from_worker_span(excerpt, start, end)
    return {
        "document_id": str(excerpt.get("document_id")),
        "page": int(excerpt.get("page")),
        "source_sha256": str(excerpt.get("source_sha256")),
        "span_start": raw_start,
        "span_end": raw_end,
        "quote": quote,
    }


def fact_from_citation(citation: Mapping[str, Any]) -> str:
    clean = " ".join(str(citation.get("quote", "")).split())
    if len(clean) > 240:
        clean = clean[:237] + "..."
    return (
        f"{citation['document_id']}:p{citation['page']}:"
        f"{str(citation['source_sha256'])[:12]} :: {clean}"
    )


def find_keyword_hits(
    excerpts: Sequence[Mapping[str, Any]],
    keywords: Sequence[str],
) -> List[Tuple[Mapping[str, Any], str, int, int]]:
    hits: List[Tuple[Mapping[str, Any], str, int, int]] = []
    for ex in excerpts:
        text = str(ex.get("text", ""))
        lower = text.lower()
        for kw in keywords:
            needle = kw.lower()
            start_at = 0
            while True:
                pos = lower.find(needle, start_at)
                if pos < 0:
                    break
                end = pos + len(needle)
                if pos < len(UNTRUSTED_PREFIX) or QUARANTINE_MARKER in text[pos:end]:
                    start_at = end
                    continue
                hits.append((ex, kw, pos, end))
                start_at = end
    return hits


def same_excerpt_counterevidence(
    excerpt: Mapping[str, Any],
    supporting: Mapping[str, Any],
) -> List[Dict[str, Any]]:
    text = str(excerpt.get("text", "")).lower()
    bound: List[Dict[str, Any]] = []
    for cue in NEGATION_CUES:
        pos = text.find(cue)
        if pos < 0:
            continue
        end = pos + len(cue)
        if pos < len(UNTRUSTED_PREFIX) or QUARANTINE_MARKER.lower() in text[pos:end]:
            continue
        citation = citation_from_excerpt(excerpt, pos, end)
        if citation["document_id"] != supporting["document_id"]:
            continue
        if citation["page"] != supporting["page"]:
            continue
        if citation["source_sha256"] != supporting["source_sha256"]:
            continue
        bound.append(
            {
                "kind": "citation",
                "citation": citation,
                "note": f"same-source negation/alternative cue: {cue}",
            }
        )
        break
    return bound


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
    counterevidence: Sequence[Any],
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
    temporal_date: str,
    citations: Sequence[Mapping[str, Any]] = (),
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
        temporal_date=temporal_date,
        peer_version=f"{role_id}@1.2",
        citations=tuple(dict(c) for c in citations),
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
    return {
        "role_id": role_id,
        "leads": leads,
        "injection_commands_followed": 0,
        "external_model_calls": 0,
        "notes": list(notes or []),
        "source_universe_searched": list(searched_universe(packet)),
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


def jurisdiction_scope(packet: Mapping[str, Any]) -> str:
    return (
        f"{packet.get('jurisdiction', 'US-federal-context')} | "
        f"{packet.get('care_date_start', '?')}–{packet.get('care_date_end', '?')}"
    )


def run_keyword_peer(
    *,
    role_id: str,
    domain: str,
    keywords: Sequence[str],
    default_phase: str,
    packet: Mapping[str, Any],
    weak_keywords: Optional[Sequence[str]] = None,
) -> Dict[str, Any]:
    excerpts = list(packet.get("excerpts", []))
    universe = searched_universe(packet)
    scope = jurisdiction_scope(packet)
    temporal_date = str(packet.get("care_date_start") or "")
    authorities = list(packet.get("grounding_pack_ids") or [])
    weak_set = {w.lower() for w in (weak_keywords or ())}
    leads: List[Dict[str, Any]] = []
    notes: List[str] = []
    hits = find_keyword_hits(excerpts, keywords)
    cited = 0

    for ex, kw, start, end in hits:
        try:
            citation = citation_from_excerpt(ex, start, end)
        except ValueError:
            continue
        cited += 1
        fact = fact_from_citation(citation)
        weak = None
        grade = EvidenceGrade.SUPPORTED
        relevance = RelevanceGrade.PLAUSIBLE
        if kw.lower() in weak_set:
            weak = "weak_or_longshot"
            grade = EvidenceGrade.CLUE
            relevance = RelevanceGrade.TENUOUS
        counter = same_excerpt_counterevidence(ex, citation)
        leads.append(
            build_lead(
                role_id=role_id,
                title=f"{domain.replace('_', ' ').title()} signal: {kw}",
                domain=domain,
                care_phase=str(ex.get("care_phase") or default_phase),
                cited_observation=fact,
                hypothesis=(
                    f"If confirmed across independent sources, the presence of '{kw}' "
                    f"in {citation['document_id']}:p{citation['page']} may indicate a "
                    f"{domain} issue warranting review."
                ),
                review_question=(
                    f"What additional {domain} documentation would confirm or refute "
                    f"the '{kw}' signal for counsel/clinician review?"
                ),
                supporting_facts=[fact],
                citations=[citation],
                counterevidence=counter,
                conflicts=[],
                missing_records=[
                    "Complete source pages spanning the cited date range",
                    "Independent corroborating note from a second author/source category",
                ],
                alternative_explanations=[
                    "Documentation phrasing may reflect template/copy-forward rather than a new event.",
                    "Clinically expected course without deviation remains possible.",
                ],
                source_universe_searched=universe,
                external_authorities=authorities,
                jurisdiction_date_scope=scope,
                evidence_grade=grade,
                relevance_grade=relevance,
                clinical_plausibility=(
                    "Plausible as a documentation/process signal; clinical significance "
                    "requires qualified clinician judgment."
                ),
                temporal_linkage=(
                    f"Linked to care window {packet.get('care_date_start')}–"
                    f"{packet.get('care_date_end')} via cited excerpt date context."
                ),
                temporal_date=temporal_date,
                weak_label=weak,
                review_history=[f"emitted_by:{role_id}"],
            )
        )

    if not cited:
        notes.append(
            bounded_absence(
                topic=f"{domain} keyword signals",
                corpus="supplied excerpts",
                start=str(packet.get("care_date_start") or ""),
                end=str(packet.get("care_date_end") or ""),
            )
        )
        leads.append(
            build_lead(
                role_id=role_id,
                title=f"Bounded absence: {domain}",
                domain=domain,
                care_phase=default_phase,
                cited_observation="No matching keyword documentation in the searched source universe.",
                hypothesis=(
                    f"Absence of {domain} cues in the supplied corpus may reflect a "
                    f"gap, a true negative, or incomplete source production."
                ),
                review_question=(
                    f"Which additional source categories should be requested to test "
                    f"the {domain} absence?"
                ),
                supporting_facts=[],
                citations=[],
                counterevidence=[],
                conflicts=[],
                missing_records=[
                    f"No {domain} keyword documentation in searched source categories: {', '.join(universe)}"
                ],
                alternative_explanations=[
                    "Signal may exist in unproduced records.",
                    "Signal may be documented under alternate terminology.",
                ],
                source_universe_searched=universe,
                external_authorities=authorities,
                jurisdiction_date_scope=scope,
                evidence_grade=EvidenceGrade.CLUE,
                relevance_grade=RelevanceGrade.TENUOUS,
                clinical_plausibility="Unknown without broader record production.",
                temporal_linkage=(
                    f"Bounded to {packet.get('care_date_start')}–{packet.get('care_date_end')}."
                ),
                temporal_date=temporal_date,
                weak_label="weak_absence_signal",
                review_history=[f"emitted_by:{role_id}"],
            )
        )

    return base_result(role_id, packet, leads, notes=notes)
