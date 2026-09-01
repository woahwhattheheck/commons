"""authority_librarian peer — isolated deterministic worker (no external models)."""

from charttrace.peers.workers._base import run_keyword_peer

ROLE_ID = "authority_librarian"


def run_peer(packet):
    return run_keyword_peer(
        role_id=ROLE_ID,
        domain="authority_research",
        keywords=(
            "standard",
            "guideline",
            "policy",
            "protocol",
            "required",
            "must document",
            "critical result",
        ),
        default_phase="authority",
        packet=packet,
        weak_keywords=("overnight", "same day", "chronic", "baseline", "expected course"),
    )
