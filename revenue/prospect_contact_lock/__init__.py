"""Canonical fail-closed prospect contact coordination."""
from . import lock as _core
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

# There is one supported mutation-capable class. Direct module import of
# revenue.prospect_contact_lock.lock.ProspectContactLock resolves to the same
# hardened surface instead of bypassing deployment invariants.
_core.ProspectContactLock = ProspectContactLock

__all__ = [
    "AUTHORITY_BRANCH", "AUTHORITY_DIGEST", "AUTHORITY_GENERATION",
    "AUTHORITY_ROOT", "CANONICAL_API_ORIGIN", "CANONICAL_REPOSITORY",
    "ConflictError", "LockError", "ProspectContactLock", "Receipt",
    "RemoteError", "Target", "ValidationError", "digest_message_bytes",
    "digest_message_file", "normalize_target", "verify_receipt",
]
