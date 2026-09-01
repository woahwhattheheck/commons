"""Synthesis peer — receives sealed independent peer outputs only.

Does not re-run discovery; preserves dissent; deduplicates by observation+hypothesis.
Never invents facts or authorities. Never sees price/firm/affiliate inputs.
"""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Set, Tuple

from charttrace.peers.contracts import EvidenceGrade, RelevanceGrade, assert_lead_complete
from charttrace.peers.workers._base import (
    base_result,
    build_lead,
    default_universe,
    jurisdiction_scope,
)

ROLE_ID = "synthesis"


def _lead_key(lead: Mapping[str, Any]) -> Tuple[str, str]:
    return (str(lead.get("cited_observation", "")), str(lead.get("hypothesis", "")))


def run_peer(packet: Mapping[str, Any]) -> Dict[str, Any]:
    sealed = list(packet.get("sealed_peer_results") or [])
    if not sealed:
        raise ValueError("synthesis requires sealed_peer_results from discovery peers")

    universe = default_universe(packet, ["synthesis"])
    scope = jurisdiction_scope(packet)
    all_leads: List[Dict[str, Any]] = []
    dissent: List[str] = []
    seen: Set[Tuple[str, str]] = set()
    weak_kept = 0

    for peer_result in sealed:
        role = peer_result.get("role_id", "unknown")
        for lead in peer_result.get("leads", []):
            assert_lead_complete(lead)
            key = _lead_key(lead)
            if key in seen:
                dissent.append(f"duplicate_collapsed_from:{role}:{lead.get('lead_id')}")
                continue
            seen.add(key)
            if lead.get("weak_label"):
                weak_kept += 1
            enriched = dict(lead)
            hist = list(enriched.get("review_history") or [])
            hist.append(f"synthesized_from:{role}")
            enriched["review_history"] = hist
            all_leads.append(enriched)

    meta_obs = (
        f"Synthesis ingested {len(sealed)} sealed peer results and retained "
        f"{len(all_leads)} leads ({weak_kept} weak-labeled)."
    )
    all_leads.insert(
        0,
        build_lead(
            role_id=ROLE_ID,
            title="Cross-peer synthesis inventory",
            domain="synthesis",
            care_phase="review",
            cited_observation=meta_obs,
            hypothesis=(
                "Independent peer passes may surface overlapping and dissenting leads; "
                "counsel/clinician review should examine retained weak leads rather than "
                "discarding them for aggressiveness alone."
            ),
            review_question=(
                "Which retained leads require additional source production before "
                "professional significance review?"
            ),
            supporting_facts=[meta_obs],
            counterevidence=[
                "Synthesis does not independently verify clinical or legal significance."
            ],
            conflicts=list(dissent[:20]),
            missing_records=["Any source categories never searched by discovery peers"],
            alternative_explanations=[
                "Apparent conflicts may reflect incomplete production rather than true inconsistency."
            ],
            source_universe_searched=universe,
            external_authorities=list(packet.get("grounding_pack_ids") or []),
            jurisdiction_date_scope=scope,
            evidence_grade=EvidenceGrade.SUPPORTED,
            relevance_grade=RelevanceGrade.MATERIAL_IF_CONFIRMED,
            clinical_plausibility="Not a clinical determination — inventory only.",
            temporal_linkage=scope,
            weak_label=None,
            review_history=[f"emitted_by:{ROLE_ID}"],
        ),
    )

    result = base_result(
        ROLE_ID,
        packet,
        all_leads,
        notes=[
            f"sealed_peers={len(sealed)}",
            f"retained_leads={len(all_leads)}",
            f"weak_kept={weak_kept}",
            f"dissent_notes={len(dissent)}",
        ],
    )
    result["dissent"] = dissent
    result["weak_leads_retained"] = weak_kept
    return result
