"""source_provenance peer — isolated deterministic worker (no external models)."""

from charttrace.peers.workers._base import run_keyword_peer

ROLE_ID = "source_provenance"


def run_peer(packet):
    return run_keyword_peer(
        role_id=ROLE_ID,
        domain="provenance_integrity",
        keywords=(
            "addendum",
            "amended",
            "unsigned",
            "copy forward",
            "copy-forward",
            "late entry",
            "authentication",
            "missing page",
            "ocr",
        ),
        default_phase="documentation",
        packet=packet,
        weak_keywords=("overnight", "same day", "chronic", "baseline", "expected course"),
    )
