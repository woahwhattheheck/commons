"""Provider-neutral offline event-to-transcript pilot adapter."""

from .adapter import (
    AdapterError,
    canonical_bytes,
    normalize_event,
    normalize_events,
    prepare_candidate_payloads,
    project_transcripts,
    projection_bytes,
    sha256_json,
)

__all__ = [
    "AdapterError",
    "canonical_bytes",
    "normalize_event",
    "normalize_events",
    "prepare_candidate_payloads",
    "project_transcripts",
    "projection_bytes",
    "sha256_json",
]
