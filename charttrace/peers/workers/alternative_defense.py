"""alternative_defense peer — isolated deterministic worker (no external models)."""

from charttrace.peers.workers._base import run_keyword_peer

ROLE_ID = "alternative_defense"


def run_peer(packet):
    return run_keyword_peer(
        role_id=ROLE_ID,
        domain="alternative_defense",
        keywords=(
            "differential",
            "idiopathic",
            "noncompliance",
            "patient declined",
            "unrelated",
            "baseline",
            "chronic",
            "expected course",
        ),
        default_phase="differential",
        packet=packet,
        weak_keywords=("overnight", "same day", "chronic", "baseline", "expected course"),
    )
