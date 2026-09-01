"""procedure_discharge peer — isolated deterministic worker (no external models)."""

from charttrace.peers.workers._base import run_keyword_peer

ROLE_ID = "procedure_discharge"


def run_peer(packet):
    return run_keyword_peer(
        role_id=ROLE_ID,
        domain="procedure_discharge",
        keywords=(
            "procedure",
            "surgery",
            "anesthesia",
            "discharge",
            "deteriorat",
            "failure to rescue",
            "rapid response",
            "post-op",
            "postop",
        ),
        default_phase="perioperative",
        packet=packet,
        weak_keywords=("overnight", "same day", "chronic", "baseline", "expected course"),
    )
