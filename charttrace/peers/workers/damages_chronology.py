"""damages_chronology peer — isolated deterministic worker (no external models)."""

from charttrace.peers.workers._base import run_keyword_peer

ROLE_ID = "damages_chronology"


def run_peer(packet):
    return run_keyword_peer(
        role_id=ROLE_ID,
        domain="damages_chronology",
        keywords=(
            "readmission",
            "complication",
            "ICU",
            "intubat",
            "death",
            "disability",
            "loss of",
            "additional procedure",
            "prolonged",
        ),
        default_phase="sequelae",
        packet=packet,
        weak_keywords=("overnight", "same day", "chronic", "baseline", "expected course"),
    )
