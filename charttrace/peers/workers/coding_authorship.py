"""coding_authorship peer — isolated deterministic worker (no external models)."""

from charttrace.peers.workers._base import run_keyword_peer

ROLE_ID = "coding_authorship"


def run_peer(packet):
    return run_keyword_peer(
        role_id=ROLE_ID,
        domain="coding_authorship",
        keywords=(
            "ICD",
            "CPT",
            "billing",
            "authored",
            "signed by",
            "cosign",
            "addendum",
            "attending",
            "resident",
        ),
        default_phase="documentation",
        packet=packet,
        weak_keywords=("overnight", "same day", "chronic", "baseline", "expected course"),
    )
