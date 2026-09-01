"""diagnoses_results peer — isolated deterministic worker (no external models)."""

from charttrace.peers.workers._base import run_keyword_peer

ROLE_ID = "diagnoses_results"


def run_peer(packet):
    return run_keyword_peer(
        role_id=ROLE_ID,
        domain="diagnoses_results",
        keywords=(
            "pathology",
            "lab",
            "critical value",
            "abnormal",
            "pending",
            "ordered",
            "result",
            "diagnosis",
            "problem list",
            "biopsy",
        ),
        default_phase="diagnostics",
        packet=packet,
        weak_keywords=("overnight", "same day", "chronic", "baseline", "expected course"),
    )
