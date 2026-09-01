"""Deterministic local swarm runner — zero external model calls."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

from charttrace.grounding.loader import resolve_requested_packs
from charttrace.peers.content_hashes import bound_content_hashes
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
from charttrace.prompts.loader import load_prompt, load_prompt_library


def _require_complete_discovery_roles(role_ids: Optional[Sequence[str]]) -> List[str]:
    configured = list(DISCOVERY_ROLE_IDS)
    if role_ids is None:
        roles = configured
    else:
        roles = list(role_ids)
    if not roles:
        raise ValueError("discovery swarm fail-closed: empty role set is not success")
    if any(not r or r == "placeholder" for r in roles):
        raise ValueError("discovery swarm fail-closed: placeholder roles rejected")
    if len(roles) != len(set(roles)):
        raise ValueError("discovery swarm fail-closed: role ids must be unique")
    if set(roles) != set(configured) or len(roles) != 11:
        raise ValueError(
            "discovery swarm fail-closed: exactly the configured 11 discovery roles must run independently"
        )
    return configured


def _isolated_packet(packet: PeerPacket, *, sealed=None) -> PeerPacket:
    resolved = resolve_requested_packs(
        list(packet.grounding_pack_ids),
        packet.care_date_start,
        packet.care_date_end,
    )
    return PeerPacket(
        case_id=packet.case_id,
        jurisdiction=packet.jurisdiction,
        care_date_start=packet.care_date_start,
        care_date_end=packet.care_date_end,
        excerpts=list(packet.excerpts),
        known_facts=list(packet.known_facts),
        source_universe=list(packet.source_universe),
        grounding_pack_ids=resolved,
        sealed_peer_results=sealed,
    )


def _load_bound_artifacts(role_ids: Sequence[str]) -> Dict[str, Any]:
    library = load_prompt_library()
    for required in ("global_scope", "peer_mandate", *role_ids):
        if required not in library:
            raise FileNotFoundError(f"missing prompt template: {required}")
        load_prompt(required)
    return bound_content_hashes()


def run_discovery_swarm(
    packet: PeerPacket,
    *,
    role_ids: Optional[Sequence[str]] = None,
    use_child_process: bool = False,
) -> Dict[str, Any]:
    roles = _require_complete_discovery_roles(role_ids)
    if SYNTHESIS_ROLE_ID in roles:
        raise ValueError("use run_full_swarm for synthesis")
    hashes = _load_bound_artifacts(roles)
    isolated = _isolated_packet(packet)

    results: List[Dict[str, Any]] = []
    for role_id in roles:
        if use_child_process:
            results.append(run_peer_child_process(role_id, isolated))
        else:
            results.append(run_peer_in_process(role_id, isolated))

    seen = [row.get("role_id") for row in results]
    if seen != list(roles) or len(set(seen)) != 11:
        raise ValueError("discovery swarm fail-closed: incomplete or non-unique role execution")
    if any(row.get("external_model_calls") != 0 for row in results):
        raise ValueError("discovery swarm fail-closed: external model calls must be zero")

    payload = {
        "schema_version": SCHEMA_VERSION,
        "peer_swarm_version": PEER_SWARM_VERSION,
        "policy_version": POLICY_VERSION,
        "prompt_version": PROMPT_VERSION,
        "model_version": MODEL_VERSION,
        "grounding_version": GROUNDING_VERSION,
        "external_model_calls": 0,
        "discovery_results": results,
        "loaded_prompt_ids": sorted(("global_scope", "peer_mandate", *roles)),
        "loaded_authority_ids": list(isolated.grounding_pack_ids),
        "source_universe_searched": sorted(
            {ex.source_category for ex in isolated.excerpts} or {"supplied_record_excerpts"}
        ),
    }
    payload.update(hashes)
    return attach_global_scope(payload)


def run_full_swarm(
    packet: PeerPacket,
    *,
    use_child_process: bool = False,
) -> Dict[str, Any]:
    discovery = run_discovery_swarm(packet, use_child_process=use_child_process)
    sealed = discovery["discovery_results"]
    if len(sealed) != 11:
        raise ValueError("full swarm fail-closed: discovery cardinality is not 11")
    synth_packet = _isolated_packet(packet, sealed=sealed)
    if use_child_process:
        synthesis = run_peer_child_process(SYNTHESIS_ROLE_ID, synth_packet)
    else:
        synthesis = run_peer_in_process(SYNTHESIS_ROLE_ID, synth_packet)
    if synthesis.get("role_id") != SYNTHESIS_ROLE_ID:
        raise ValueError("full swarm fail-closed: synthesis identity is not trusted")
    out = dict(discovery)
    out["synthesis"] = synthesis
    out["global_scope_statement"] = GLOBAL_SCOPE_STATEMENT
    out["external_model_calls"] = 0
    return out
