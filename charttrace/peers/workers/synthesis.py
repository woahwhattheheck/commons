"""Synthesis peer — receives sealed independent peer outputs only.

Does not re-run discovery; preserves dissent; deduplicates by observation+hypothesis.
Never invents facts or authorities. Never sees price/firm/affiliate inputs.
"""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Set, Tuple

from charttrace.peers.contracts import EvidenceGrade, RelevanceGrade, assert_lead_complete
from charttrace.peers.isolation import DISCOVERY_ROLE_IDS, compute_envelope_hash
from charttrace.peers.versions import (
    MODEL_VERSION,
    PEER_SWARM_VERSION,
    POLICY_VERSION,
    PROMPT_VERSION,
    SCHEMA_VERSION,
)
from charttrace.peers.workers._base import (
    base_result,
    build_lead,
    jurisdiction_scope,
    searched_universe,
)

ROLE_ID = "synthesis"
REQUIRED_DISCOVERY_ROLES = frozenset(DISCOVERY_ROLE_IDS)


def _assert_authenticated_envelopes(sealed: List[Mapping[str, Any]], case_id: str) -> None:
    if len(sealed) != 11:
        raise ValueError("synthesis requires exactly 11 sealed discovery results")
    roles = [str(row.get("role_id") or "") for row in sealed]
    if len(set(roles)) != 11 or set(roles) != REQUIRED_DISCOVERY_ROLES:
        raise ValueError("synthesis requires exactly one envelope per discovery role")
    for row in sealed:
        role = str(row.get("role_id") or "")
        if row.get("envelope_bound_case_id") != case_id:
            raise ValueError("synthesis envelope case binding mismatch")
        if row.get("schema_version") != SCHEMA_VERSION:
            raise ValueError("synthesis envelope schema binding mismatch")
        if row.get("peer_swarm_version") != PEER_SWARM_VERSION:
            raise ValueError("synthesis envelope version binding mismatch")
        if row.get("policy_version") != POLICY_VERSION:
            raise ValueError("synthesis envelope version binding mismatch")
        if row.get("prompt_version") != PROMPT_VERSION:
            raise ValueError("synthesis envelope version binding mismatch")
        if row.get("model_version") != MODEL_VERSION:
            raise ValueError("synthesis envelope version binding mismatch")
        expected = compute_envelope_hash(role, row, case_id)
        if row.get("envelope_hash") != expected:
            raise ValueError("synthesis envelope hash mismatch")


def _lead_key(lead: Mapping[str, Any]) -> Tuple[str, str]:
    return (str(lead.get("cited_observation", "")), str(lead.get("hypothesis", "")))


def run_peer(packet: Mapping[str, Any]) -> Dict[str, Any]:
    sealed = list(packet.get("sealed_peer_results") or [])
    _assert_authenticated_envelopes(sealed, str(packet.get("case_id") or ""))

    universe = searched_universe(packet)
    scope = jurisdiction_scope(packet)
    temporal_date = str(packet.get("care_date_start") or "")
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

    all_leads.insert(
        0,
        build_lead(
            role_id=ROLE_ID,
            title="Cross-peer synthesis inventory",
            domain="synthesis",
            care_phase="review",
            cited_observation="Independent discovery peers produced a sealed lead inventory for professional review.",
            hypothesis=(
                "Independent peer passes may surface overlapping and dissenting leads; "
                "counsel/clinician review should examine retained weak leads rather than "
                "discarding them for aggressiveness alone."
            ),
            review_question=(
                "Which retained leads require additional source production before "
                "professional significance review?"
            ),
            supporting_facts=[],
            citations=[],
            counterevidence=[],
            conflicts=list(dissent[:20]),
            missing_records=["Any source categories never searched by discovery peers"],
            alternative_explanations=[
                "Apparent conflicts may reflect incomplete production rather than true inconsistency."
            ],
            source_universe_searched=universe,
            external_authorities=list(packet.get("grounding_pack_ids") or []),
            jurisdiction_date_scope=scope,
            evidence_grade=EvidenceGrade.CLUE,
            relevance_grade=RelevanceGrade.MATERIAL_IF_CONFIRMED,
            clinical_plausibility="Not a clinical determination — inventory only.",
            temporal_linkage=scope,
            temporal_date=temporal_date,
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
