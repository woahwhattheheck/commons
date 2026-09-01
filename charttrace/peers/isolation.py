"""Isolated function and child-process contracts for peer workers.

Discovery peers never receive each other's leads.
"""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Optional

from charttrace.peers.contracts import detect_forbidden_inputs
from charttrace.peers.packet import PeerPacket
from charttrace.peers.versions import PEER_SWARM_VERSION, SCHEMA_VERSION


@dataclass(frozen=True)
class PeerContract:
    role_id: str
    role_name: str
    module_path: str
    entrypoint: str = "run_peer"
    allows_cross_peer_input: bool = False


DISCOVERY_ROLE_IDS = (
    "source_provenance",
    "clinical_chronology",
    "diagnoses_results",
    "communication_consent",
    "referral_continuity",
    "medication_allergy",
    "procedure_discharge",
    "coding_authorship",
    "damages_chronology",
    "authority_librarian",
    "alternative_defense",
)

SYNTHESIS_ROLE_ID = "synthesis"
ALL_ROLE_IDS = DISCOVERY_ROLE_IDS + (SYNTHESIS_ROLE_ID,)


def peer_contracts() -> List[PeerContract]:
    contracts: List[PeerContract] = []
    for role_id in DISCOVERY_ROLE_IDS:
        contracts.append(
            PeerContract(
                role_id=role_id,
                role_name=role_id.replace("_", " "),
                module_path=f"charttrace.peers.workers.{role_id}",
                allows_cross_peer_input=False,
            )
        )
    contracts.append(
        PeerContract(
            role_id=SYNTHESIS_ROLE_ID,
            role_name="synthesis",
            module_path="charttrace.peers.workers.synthesis",
            allows_cross_peer_input=True,
        )
    )
    return contracts


def assert_discovery_isolation(packet: Mapping[str, Any], role_id: str) -> None:
    if role_id == SYNTHESIS_ROLE_ID:
        return
    if packet.get("sealed_peer_results"):
        raise ValueError(
            f"discovery peer {role_id} must not receive sealed_peer_results"
        )
    for key in ("peer_leads", "other_peer_leads", "anchor_leads"):
        if key in packet:
            raise ValueError(f"discovery peer {role_id} must not receive {key}")


def run_peer_in_process(role_id: str, packet: PeerPacket) -> Dict[str, Any]:
    from charttrace.peers import registry

    contract = registry.get_contract(role_id)
    data = packet.to_sanitized_dict()
    assert_discovery_isolation(data, role_id)
    if detect_forbidden_inputs(data):
        raise ValueError("forbidden inputs in peer packet")
    worker = registry.load_worker(role_id)
    result = worker(data)
    if not isinstance(result, dict):
        raise TypeError("peer must return a dict result")
    result.setdefault("role_id", role_id)
    result.setdefault("schema_version", SCHEMA_VERSION)
    result.setdefault("peer_swarm_version", PEER_SWARM_VERSION)
    result.setdefault("allows_cross_peer_input", contract.allows_cross_peer_input)
    result.setdefault("external_model_calls", 0)
    return result


CHILD_PROCESS_DRIVER = (
    "import json,sys;"
    "from charttrace.peers.isolation import run_peer_in_process;"
    "from charttrace.peers.packet import packet_from_mapping;"
    "payload=json.load(sys.stdin);"
    "result=run_peer_in_process(payload['role_id'], packet_from_mapping(payload['packet']));"
    "json.dump(result, sys.stdout, sort_keys=True)"
)


def run_peer_child_process(
    role_id: str,
    packet: PeerPacket,
    *,
    python_executable: Optional[str] = None,
    timeout_s: float = 30.0,
) -> Dict[str, Any]:
    exe = python_executable or sys.executable
    payload = {"role_id": role_id, "packet": packet.to_sanitized_dict()}
    assert_discovery_isolation(payload["packet"], role_id)
    proc = subprocess.run(
        [exe, "-c", CHILD_PROCESS_DRIVER],
        input=json.dumps(payload).encode("utf-8"),
        capture_output=True,
        timeout=timeout_s,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"peer child process failed ({role_id}): "
            f"{proc.stderr.decode('utf-8', errors='replace')}"
        )
    return json.loads(proc.stdout.decode("utf-8"))
