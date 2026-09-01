"""Local evidence sealing and synthetic peer-analysis helpers."""

import hashlib
from pathlib import Path
from typing import Iterable, List, Tuple, Union

from .cases import SourceSeal


SourceInput = Union[Path, Tuple[str, bytes]]


def seal_sources(sources: Iterable[SourceInput]) -> List[SourceSeal]:
    """Hash source bytes locally without retaining paths or source contents."""
    seals: List[SourceSeal] = []
    for source in sources:
        if isinstance(source, tuple):
            display_name, content = source
            if not isinstance(content, bytes):
                raise TypeError("In-memory source content must be bytes.")
        else:
            path = Path(source)
            display_name = path.name
            content = path.read_bytes()
        if not display_name.strip():
            raise ValueError("Each source requires a display name.")
        seals.append(
            SourceSeal(
                display_name=display_name.strip(),
                sha256=hashlib.sha256(content).hexdigest(),
                size_bytes=len(content),
            )
        )
    if not seals:
        raise ValueError("Secure ingest requires at least one source.")
    return seals


def synthetic_peer_output(seals: Iterable[SourceSeal]) -> dict:
    """Create an explicitly synthetic analysis envelope for human review.

    This function does not call a model or network service.  The controller is
    responsible for applying the legal gate before it can be invoked.
    """
    source_ids = [seal.sha256 for seal in seals]
    return {
        "kind": "UNSIGNED_SYNTHETIC",
        "signing_state": "unsigned",
        "source_hashes": source_ids,
        "hypotheses": [],
        "disclosure": (
            "Synthetic peer envelope only; no factual conclusion. "
            "Human source and citation review required."
        ),
    }
