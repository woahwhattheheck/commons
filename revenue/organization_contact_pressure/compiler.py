"""Compile a current organization-pressure decision receipt."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from .core import HOLD_AUTHORITY, AuthorityView, LedgerView, VerificationError
from .decision import _evaluate
from .receipt_body import _receipt_body, _seal_receipt
from .records import _load_authority, _load_ledger, _normalize_request
from .storage import _authority_root, _load_active_key

def _compile_at(request_data: bytes, *, root: Path, now: datetime) -> dict[str, Any]:
    if now.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    now = now.astimezone(timezone.utc).replace(microsecond=0)
    request = _normalize_request(request_data)
    active = _load_active_key(root)
    authority: Optional[AuthorityView] = None
    ledger: Optional[LedgerView] = None
    try:
        authority = _load_authority(root, active, request["organization_scope_sha256"], now)
        ledger = _load_ledger(root, active, authority, now)
        decision, reasons = _evaluate(request, authority, ledger, now)
    except VerificationError as exc:
        # Do not emit a partially validated authority chain.  A canonical
        # HOLD_AUTHORITY receipt either binds a complete authority+ledger pair
        # or binds neither, while the retained verifier key still authenticates
        # the failure decision.
        authority = None
        ledger = None
        decision = HOLD_AUTHORITY
        reasons = (f"AUTHORITY_INVALID:{type(exc).__name__}",)
    body = _receipt_body(request, active, authority, ledger, decision, reasons, now)
    return _seal_receipt(body, active.key)


def compile_current(request_data: bytes) -> dict[str, Any]:
    """Compile with process-owned UTC and the fixed retained authority root."""
    now = datetime.now(timezone.utc).replace(microsecond=0)
    return _compile_at(request_data, root=_authority_root(), now=now)
