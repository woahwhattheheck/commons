"""clinical_chronology peer — isolated deterministic worker (no external models)."""

from __future__ import annotations

from typing import Any, Dict, List, Mapping

from charttrace.peers.contracts import EvidenceGrade, RelevanceGrade
from charttrace.peers.workers._base import (
    base_result,
    bounded_absence,
    build_lead,
    cite_excerpt,
    default_universe,
    fact_from_excerpt,
    find_keyword_hits,
    jurisdiction_scope,
)

ROLE_ID = "clinical_chronology"
DOMAIN = "chronology"
KEYWORDS = ['timeline', 'admitted', 'discharged', 'transfer', 'overnight', 'hours later', 'same day', 'prior to', 'after']
DEFAULT_PHASE = "acute_care"
WEAK_KEYWORDS = {"overnight", "same day", "chronic", "baseline", "expected course"}


def run_peer(packet: Mapping[str, Any]) -> Dict[str, Any]:
    excerpts = list(packet.get("excerpts", []))
    universe = default_universe(packet, [DOMAIN, DEFAULT_PHASE])
    scope = jurisdiction_scope(packet)
    leads: List[Dict[str, Any]] = []
    hits = find_keyword_hits(excerpts, KEYWORDS)
    notes: List[str] = []

    for ex, kw, snippet in hits:
        fact = fact_from_excerpt(ex, snippet)
        weak = None
        grade = EvidenceGrade.SUPPORTED
        relevance = RelevanceGrade.PLAUSIBLE
        if kw.lower() in WEAK_KEYWORDS:
            weak = "weak_or_longshot"
            grade = EvidenceGrade.CLUE
            relevance = RelevanceGrade.TENUOUS
        counter: List[str] = []
        text_l = str(ex.get("text", "")).lower()
        if "resolved" in text_l or "documented discussion" in text_l or "patient notified" in text_l:
            counter.append(fact_from_excerpt(ex, "contrary cue present in same excerpt"))
        leads.append(
            build_lead(
                role_id=ROLE_ID,
                title=f"{DOMAIN.replace('_', ' ').title()} signal: {kw}",
                domain=DOMAIN,
                care_phase=str(ex.get("care_phase") or DEFAULT_PHASE),
                cited_observation=fact,
                hypothesis=(
                    f"If confirmed across independent sources, the presence of '{kw}' "
                    f"in {cite_excerpt(ex)} may indicate a {DOMAIN} issue warranting review."
                ),
                review_question=(
                    f"What additional {DOMAIN} documentation would confirm or refute "
                    f"the '{kw}' signal for counsel/clinician review?"
                ),
                supporting_facts=[fact],
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
                external_authorities=list(packet.get("grounding_pack_ids") or []),
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
                weak_label=weak,
                review_history=[f"emitted_by:{ROLE_ID}"],
            )
        )

    if not hits:
        absence = bounded_absence(
            topic=f"{DOMAIN} keyword signals",
            corpus="supplied excerpts",
            start=str(packet.get("care_date_start") or ""),
            end=str(packet.get("care_date_end") or ""),
        )
        notes.append(absence)
        leads.append(
            build_lead(
                role_id=ROLE_ID,
                title=f"Bounded absence: {DOMAIN}",
                domain=DOMAIN,
                care_phase=DEFAULT_PHASE,
                cited_observation=absence,
                hypothesis=(
                    f"Absence of {DOMAIN} cues in the supplied corpus may reflect a "
                    f"gap, a true negative, or incomplete source production."
                ),
                review_question=(
                    f"Which additional source categories should be requested to test "
                    f"the {DOMAIN} absence?"
                ),
                supporting_facts=[absence],
                counterevidence=["Absence is not proof of non-occurrence."],
                conflicts=[],
                missing_records=["Unproduced source categories outside supplied excerpts"],
                alternative_explanations=[
                    "Signal may exist in unproduced records.",
                    "Signal may be documented under alternate terminology.",
                ],
                source_universe_searched=universe,
                external_authorities=list(packet.get("grounding_pack_ids") or []),
                jurisdiction_date_scope=scope,
                evidence_grade=EvidenceGrade.CLUE,
                relevance_grade=RelevanceGrade.TENUOUS,
                clinical_plausibility="Unknown without broader record production.",
                temporal_linkage=(
                    f"Bounded to {packet.get('care_date_start')}–{packet.get('care_date_end')}."
                ),
                weak_label="weak_absence_signal",
                review_history=[f"emitted_by:{ROLE_ID}"],
            )
        )

    return base_result(ROLE_ID, packet, leads, notes=notes)
