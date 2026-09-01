"""clinical_chronology peer — isolated deterministic worker (no external models)."""

from charttrace.peers.workers._base import run_keyword_peer

ROLE_ID = "clinical_chronology"


def run_peer(packet):
    return run_keyword_peer(
        role_id=ROLE_ID,
        domain="chronology",
        keywords=(
            "timeline",
            "admitted",
            "discharged",
            "transfer",
            "overnight",
            "hours later",
            "same day",
            "prior to",
            "after",
        ),
        default_phase="acute_care",
        packet=packet,
        weak_keywords=("overnight", "same day", "chronic", "baseline", "expected course"),
    )
