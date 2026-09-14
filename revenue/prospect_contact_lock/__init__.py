"""Canonical fail-closed prospect contact coordination."""
from .lock import (
    AUTHORITY_BRANCH,
    AUTHORITY_DIGEST,
    AUTHORITY_GENERATION,
    AUTHORITY_ROOT,
    CANONICAL_API_ORIGIN,
    CANONICAL_REPOSITORY,
    ConflictError,
    LockError,
    Receipt,
    RemoteError,
    Target,
    ValidationError,
    digest_message_bytes,
    digest_message_file,
    normalize_target,
    verify_receipt,
)
from .hardened import ProspectContactLock
__all__ = [
    "AUTHORITY_BRANCH", "AUTHORITY_DIGEST", "AUTHORITY_GENERATION",
    "AUTHORITY_ROOT", "CANONICAL_API_ORIGIN", "CANONICAL_REPOSITORY",
    "ConflictError", "LockError", "ProspectContactLock", "Receipt",
    "RemoteError", "Target", "ValidationError", "digest_message_bytes",
    "digest_message_file", "normalize_target", "verify_receipt",
]
