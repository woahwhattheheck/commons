"""Atomic, privacy-minimized outreach claim coordination."""

from .core import (
    ClaimConflict, ClaimFenceError, ClaimNotFound, ClaimReceipt, HttpResponse,
    OwnershipError, ProtocolError, RemoteError, TargetIdentity, UrllibTransport,
    ValidationError, SCHEMA, _HEX_64, _canonical_json_bytes, _format_timestamp,
    _record_digest, _seal_record, digest_message_bytes, digest_message_file,
    normalize_target,
)
from .store import GitHubContentsClaimStore
from .cli import main

__all__ = [
    "ClaimConflict", "ClaimFenceError", "ClaimNotFound", "ClaimReceipt",
    "GitHubContentsClaimStore", "HttpResponse", "OwnershipError", "ProtocolError",
    "RemoteError", "TargetIdentity", "UrllibTransport", "ValidationError",
    "digest_message_bytes", "digest_message_file", "main", "normalize_target",
]
