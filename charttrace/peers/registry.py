"""Registry of twelve ChartTrace peer workers."""

from __future__ import annotations

import importlib
from typing import Any, Callable, Dict

from charttrace.peers.isolation import ALL_ROLE_IDS, PeerContract, peer_contracts


_CONTRACTS = {c.role_id: c for c in peer_contracts()}


def get_contract(role_id: str) -> PeerContract:
    if role_id not in _CONTRACTS:
        raise KeyError(f"unknown peer role: {role_id}")
    return _CONTRACTS[role_id]


def load_worker(role_id: str) -> Callable[[Dict[str, Any]], Dict[str, Any]]:
    contract = get_contract(role_id)
    mod = importlib.import_module(contract.module_path)
    return getattr(mod, contract.entrypoint)


def list_role_ids() -> tuple:
    return ALL_ROLE_IDS
