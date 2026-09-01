"""Deterministic local swarm runner — zero external model calls."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

from charttrace.peers.isolation import (
    DISCOVERY_ROLE_IDS,
    SYNTHESIS_ROLE_ID,
    run_peer_child_process,
    run_peer_in_process,
)
from charttrace.peers.packet import PeerPacket
from charttrace.peers.scope import GLOBAL_SCOPE_STATEMENT, attach_global_scope
from charttrace.peers.versions import (
    GROUNDING_VERSION,
    MODEL_VERSION,
    PEER_SWARM_VERSION,
    POLICY_VERSION,
    PROMPT_VERSION,
    SCHEMA_VERSION,
)


def run_discovery_swarm(
    packet: PeerPacket,
    *,
    role_ids: Optional[Sequence[str]] = None,
    use_child_process: bool = False,
) -> Dict[str, Any]:
    roles = list(role_ids) if role_ids is not None else list(DISCOVERY_ROLE_IDS)
    if SYNTHESIS_ROLE_ID in roles:
        raise ValueError("use run_full_swarm for synthesis")

    results: List[Dict[str, Any]] = []
    for role_id in roles:
        isolated = PeerPacket(
            case_id=packet.case_id,
            jurisdiction=packet.jurisdiction,
            care_date_start=packet.care_date_start,
            care_date_end=packet.care_date_end,
            excerpts=list(packet.excerpts),
            known_facts=list(packet.known_facts),
            source_universe=list(packet.source_universe),
            grounding_pack_ids=list(packet.grounding_pack_ids),
            sealed_peer_results=None,
        )
        if use_child_process:
            results.append(run_peer_child_process(role_id, isolated))
        else:
            results.append(run_peer_in_process(role_id, isolated))

    return attach_global_scope(
        {
            "schema_version": SCHEMA_VERSION,
            "peer_swarm_version": PEER_SWARM_VERSION,
            "policy_version": POLICY_VERSION,
            "prompt_version": PROMPT_VERSION,
            "model_version": MODEL_VERSION,
            "grounding_version": GROUNDING_VERSION,
            "external_model_calls": 0,
            "discovery_results": results,
        }
    )


def run_full_swarm(
    packet: PeerPacket,
    *,
    use_child_process: bool = False,
) -> Dict[str, Any]:
    discovery = run_discovery_swarm(packet, use_child_process=use_child_process)
    sealed = discovery["discovery_results"]
    synth_packet = PeerPacket(
        case_id=packet.case_id,
        jurisdiction=packet.jurisdiction,
        care_date_start=packet.care_date_start,
        care_date_end=packet.care_date_end,
        excerpts=list(packet.excerpts),
        known_facts=list(packet.known_facts),
        source_universe=list(packet.source_universe),
        grounding_pack_ids=list(packet.grounding_pack_ids),
        sealed_peer_results=sealed,
    )
    if use_child_process:
        synthesis = run_peer_child_process(SYNTHESIS_ROLE_ID, synth_packet)
    else:
        synthesis = run_peer_in_process(SYNTHESIS_ROLE_ID, synth_packet)

    out = dict(discovery)
    out["synthesis"] = synthesis
    out["global_scope_statement"] = GLOBAL_SCOPE_STATEMENT
    return out
