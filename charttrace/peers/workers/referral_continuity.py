"""referral_continuity peer — isolated deterministic worker (no external models)."""

from charttrace.peers.workers._base import run_keyword_peer

ROLE_ID = "referral_continuity"


def run_peer(packet):
    return run_keyword_peer(
        role_id=ROLE_ID,
        domain="referral_continuity",
        keywords=(
            "referral",
            "follow-up",
            "follow up",
            "appointment",
            "no-show",
            "pending consult",
            "closed loop",
            "recommended",
        ),
        default_phase="continuity",
        packet=packet,
        weak_keywords=("overnight", "same day", "chronic", "baseline", "expected course"),
    )
