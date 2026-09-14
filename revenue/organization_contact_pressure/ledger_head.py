"""Current ledger acceptance anchored by a root-owned monotonic floor.

The historical journal implementation is preserved byte-for-byte in
``ledger_head_legacy.py``.  This wrapper first applies every journal check and
then requires the mutable ledger to match a separately retained floor that the
ledger writer cannot delete or roll back in production.
"""

from __future__ import annotations

import hmac
import os
from datetime import datetime, timedelta
from pathlib import Path

from . import ledger_head_legacy as _legacy
from .core import AuthorityUnavailable, InputError, VerificationError, _expect_object, _hmac_hex, _parse_time, strict_json_loads
from .monotonic import _ledger_floor_root, _read_floor
from .storage import _authority_root

LEDGER_HEAD_SCHEMA = _legacy.LEDGER_HEAD_SCHEMA
_ledger_head_epoch_sha256 = _legacy._ledger_head_epoch_sha256
_ledger_head_filename = _legacy._ledger_head_filename
_normalize_ledger_head_document = _legacy._normalize_ledger_head_document


def _load_current_floor(
    floor_root: Path,
    *,
    floor_owner_uid: int,
    enforce_floor_custody: bool,
    active,
    authority,
    now: datetime,
):
    floor_path = floor_root / f"{authority.organization_scope_sha256}.json"
    if not enforce_floor_custody and not floor_path.exists():
        return None
    try:
        raw = _read_floor(
            floor_root,
            authority.organization_scope_sha256,
            expected_uid=floor_owner_uid,
            enforce_production_custody=enforce_floor_custody,
        )
    except AuthorityUnavailable as exc:
        raise VerificationError("monotonic ledger floor is unavailable") from exc
    try:
        document = _expect_object(strict_json_loads(raw), "ledger floor")
        body, signature = _normalize_ledger_head_document(document)
    except InputError as exc:
        raise VerificationError("monotonic ledger floor is malformed") from exc
    if body["organization_scope_sha256"] != authority.organization_scope_sha256:
        raise VerificationError("monotonic ledger floor scope mismatch")
    if body["key_id"] != active.key_id or body["verifier_id"] != active.verifier_id:
        raise VerificationError("monotonic ledger floor verifier epoch is not active")
    if body["policy_generation"] != authority.policy_generation:
        raise VerificationError("monotonic ledger floor policy epoch is not active")
    if not hmac.compare_digest(signature, _hmac_hex(active.key, body)):
        raise VerificationError("monotonic ledger floor HMAC is invalid")
    ledger_updated = _parse_time(body["ledger_updated_at"], "ledger_floor.ledger_updated_at")
    committed = _parse_time(body["committed_at"], "ledger_floor.committed_at")
    skew = timedelta(seconds=authority.max_future_skew_seconds)
    if ledger_updated > committed:
        raise VerificationError("monotonic ledger floor predates ledger update")
    if committed > now + skew:
        raise VerificationError("monotonic ledger floor is future-committed")
    return body["ledger_generation"], body["ledger_sha256"], ledger_updated


def _verify_current_ledger_head(
    root: Path,
    active,
    authority,
    ledger,
    now: datetime,
    *,
    floor_root: Path | None = None,
    floor_owner_uid: int | None = None,
    enforce_floor_custody: bool | None = None,
) -> None:
    if floor_root is None:
        production = Path(root) == _authority_root()
        floor_root = _ledger_floor_root() if production else Path(root) / "ledger-floors"
        floor_owner_uid = 0 if production else os.geteuid()
        enforce_floor_custody = production
    if floor_owner_uid is None or enforce_floor_custody is None:
        raise TypeError("floor custody arguments must be complete")
    _legacy._verify_current_ledger_head(root, active, authority, ledger, now)
    floor = _load_current_floor(
        floor_root,
        floor_owner_uid=floor_owner_uid,
        enforce_floor_custody=enforce_floor_custody,
        active=active,
        authority=authority,
        now=now,
    )
    if floor is None:
        return
    generation, digest, updated = floor
    if ledger.generation < generation:
        raise VerificationError("ledger rollback detected below monotonic floor")
    if ledger.generation > generation:
        raise VerificationError("ledger is newer than monotonic floor")
    if ledger.digest != digest:
        raise VerificationError("ledger digest differs from monotonic floor")
    if ledger.updated_at != updated:
        raise VerificationError("ledger update time differs from monotonic floor")
