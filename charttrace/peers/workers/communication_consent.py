"""communication_consent peer — isolated deterministic worker (no external models)."""

from charttrace.peers.workers._base import run_keyword_peer

ROLE_ID = "communication_consent"


def run_peer(packet):
    return run_keyword_peer(
        role_id=ROLE_ID,
        domain="communication_consent",
        keywords=(
            "consent",
            "informed",
            "discussed",
            "refused",
            "interpreter",
            "capacity",
            "told patient",
            "notification",
            "callback",
        ),
        default_phase="communication",
        packet=packet,
        weak_keywords=("overnight", "same day", "chronic", "baseline", "expected course"),
    )
