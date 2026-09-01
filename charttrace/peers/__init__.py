"""ChartTrace Lane B — high-recall peer swarm (v1.1).

Twelve independent peer roles run as isolated functions or child-process
contracts. Discovery peers never see each other's leads. Peers never see
packet price, destination firm, affiliate identity, or compensation.
No external model calls — deterministic local workers + prompt templates.
"""

from charttrace.peers.runner import run_discovery_swarm, run_full_swarm
from charttrace.peers.scope import GLOBAL_SCOPE_STATEMENT
from charttrace.peers.versions import (
    GROUNDING_VERSION,
    MODEL_VERSION,
    PEER_SWARM_VERSION,
    POLICY_VERSION,
    PROMPT_VERSION,
    SCHEMA_VERSION,
)

__all__ = [
    "GLOBAL_SCOPE_STATEMENT",
    "GROUNDING_VERSION",
    "MODEL_VERSION",
    "PEER_SWARM_VERSION",
    "POLICY_VERSION",
    "PROMPT_VERSION",
    "SCHEMA_VERSION",
    "run_discovery_swarm",
    "run_full_swarm",
]
