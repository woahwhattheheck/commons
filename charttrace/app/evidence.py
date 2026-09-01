"""Local evidence sealing and synthetic peer-analysis helpers."""

import hashlib
import os
from pathlib import Path
from typing import Iterable, List, Tuple, Union

from .cases import SourceSeal
from .paths import validate_local_file


SourceInput = Union[Path, str, Tuple[str, bytes]]


def _hash_local_file(path: Path) -> Tuple[str, int]:
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags)
    digest = hashlib.sha256()
    size = 0
    with os.fdopen(descriptor, "rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
            size += len(chunk)
    return digest.hexdigest(), size


def seal_sources(sources: Iterable[SourceInput]) -> List[SourceSeal]:
    """Hash source bytes locally without retaining paths or source contents."""
    seals: List[SourceSeal] = []
    for source in sources:
        if isinstance(source, tuple):
            display_name, content = source
            if not isinstance(content, bytes):
                raise TypeError("In-memory source content must be bytes.")
            source_hash = hashlib.sha256(content).hexdigest()
            source_size = len(content)
        else:
            path = validate_local_file(source)
            display_name = path.name
            source_hash, source_size = _hash_local_file(path)
        if not display_name.strip():
            raise ValueError("Each source requires a display name.")
        seals.append(
            SourceSeal(
                display_name=display_name.strip(),
                sha256=source_hash,
                size_bytes=source_size,
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
