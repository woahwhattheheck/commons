"""medication_allergy peer — isolated deterministic worker (no external models)."""

from charttrace.peers.workers._base import run_keyword_peer

ROLE_ID = "medication_allergy"


def run_peer(packet):
    return run_keyword_peer(
        role_id=ROLE_ID,
        domain="medication_allergy",
        keywords=(
            "allergy",
            "allergic",
            "medication",
            "dose",
            "mg",
            "contraindicated",
            "warfarin",
            "heparin",
            "antibiotic",
            "reaction",
        ),
        default_phase="medication",
        packet=packet,
        weak_keywords=("overnight", "same day", "chronic", "baseline", "expected course"),
    )
