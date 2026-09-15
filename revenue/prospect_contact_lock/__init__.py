"""Canonical fail-closed prospect contact coordination."""
from typing import Any, Mapping

from . import hardened as _hardened
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

_InjectedProspectContactLock = _hardened.ProspectContactLock


class ProspectContactLock(_InjectedProspectContactLock):
    """Only supported production mutation surface.

    Production owns the canonical GitHub transport.  Arbitrary caller transport
    injection is intentionally absent from this constructor so a caller cannot
    synthesize authority-branch/ref/commit/content truth.
    """

    def __init__(self, token: str) -> None:
        super().__init__(token, None)


class _TestProspectContactLock(_InjectedProspectContactLock):
    """Private deterministic transport seam for repository hostiles only.

    Every status/receipt emitted by this seam is marked ``test_only_transport``.
    Mutation receipts retain their original seal, so adding that marker makes
    them deliberately fail production ``verify_receipt`` validation.  Test
    transport output therefore cannot masquerade as a production authority
    artifact even if this underscore class is imported deliberately.
    """

    def __init__(self, token: str, transport: _core.Transport) -> None:
        if not bool(getattr(transport, "supports_authority_transactions", False)):
            raise ValidationError("test transport lacks transactional authority protocol")
        super().__init__(token, transport)

    @staticmethod
    def _receipt(
        action: str,
        outcome: str,
        target: Target,
        record: Mapping[str, Any],
        blob_sha: str | None,
        commit_sha: str | None,
    ) -> dict[str, Any]:
        doc = _InjectedProspectContactLock._receipt(
            action, outcome, target, record, blob_sha, commit_sha
        )
        marked = dict(doc)
        marked["test_only_transport"] = True
        return marked

    def status(self, kind: str, raw_target: str) -> dict[str, Any]:
        doc = dict(super().status(kind, raw_target))
        doc["test_only_transport"] = True
        return doc


# One production class is installed onto every supported import path.  The
# injected-transport implementation remains reachable only under an explicit
# underscore test name and cannot emit production-verifiable receipts.
_hardened.ProspectContactLock = ProspectContactLock
_hardened._TestProspectContactLock = _TestProspectContactLock
_core.ProspectContactLock = ProspectContactLock

__all__ = [
    "AUTHORITY_BRANCH", "AUTHORITY_DIGEST", "AUTHORITY_GENERATION",
    "AUTHORITY_ROOT", "CANONICAL_API_ORIGIN", "CANONICAL_REPOSITORY",
    "ConflictError", "LockError", "ProspectContactLock", "Receipt",
    "RemoteError", "Target", "ValidationError", "digest_message_bytes",
    "digest_message_file", "normalize_target", "verify_receipt",
]
