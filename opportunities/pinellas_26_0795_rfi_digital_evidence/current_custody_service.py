from __future__ import annotations

import copy
from collections import namedtuple
from datetime import datetime, timezone
from typing import Any, Protocol

from custody_reference import AuthoritySnapshot, CustodyError, Evidence


class HostTrustProvider(Protocol):
    """Host-owned time/witness/authority boundary for current custody state.

    ``compare_and_retain_custody_witness`` MUST atomically compare the retained
    predecessor with ``expected_witness`` and replace it with the successor only
    on an exact match. ``None`` is create-if-absent for first submission.
    """

    def current_time_utc(self) -> str: ...
    def retained_custody_witness(self, case_id: str, object_id: str) -> dict[str, Any]: ...
    def compare_and_retain_custody_witness(
        self, case_id: str, object_id: str,
        expected_witness: dict[str, Any] | None,
        successor_witness: dict[str, Any],
    ) -> bool: ...
    def current_authority_snapshot(self, case_id: str, object_id: str) -> AuthoritySnapshot: ...
    def archived_authority_snapshot(
        self, case_id: str, object_id: str, root: str
    ) -> AuthoritySnapshot: ...


def _host_utc(text: str, _datetime=datetime, _timezone=timezone) -> str:
    if type(text) is not str or not text.endswith("Z"):
        raise CustodyError("host current time must use UTC Z form")
    try:
        dt = _datetime.fromisoformat(text[:-1] + "+00:00")
    except ValueError as exc:
        raise CustodyError("host current time invalid") from exc
    if dt.microsecond:
        raise CustodyError("host current time must use whole seconds")
    return dt.astimezone(_timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def CurrentCustodyService(
    provider: HostTrustProvider,
    _Evidence=Evidence,
    _AuthoritySnapshot=AuthoritySnapshot,
    _CustodyError=CustodyError,
    _deepcopy=copy.deepcopy,
    _normalize_host_time=_host_utc,
):
    """Return immutable current-positive operation closures bound to ``provider``.

    Provider methods, low-level types, deepcopy, and time normalization are
    captured once. They are not writable service attributes, so later ordinary
    provider/module rebinding does not redirect an existing service. Arbitrary
    closure introspection or interpreter compromise is outside this reference
    boundary. Low-level ``Evidence`` remains historical/integrity-only.
    """
    current_time = getattr(provider, "current_time_utc", None)
    retained_witness = getattr(provider, "retained_custody_witness", None)
    compare_and_retain = getattr(provider, "compare_and_retain_custody_witness", None)
    current_snapshot = getattr(provider, "current_authority_snapshot", None)
    archived_snapshot = getattr(provider, "archived_authority_snapshot", None)
    if any(not callable(method) for method in (
        current_time, retained_witness, compare_and_retain,
        current_snapshot, archived_snapshot,
    )):
        raise _CustodyError("host trust provider contract incomplete")

    def identity(evidence):
        if type(evidence) is not _Evidence:
            raise _CustodyError("Evidence instance required")
        return evidence.case_id, evidence.object_id

    def trusted_now():
        return _normalize_host_time(current_time())

    def roots(evidence):
        found = set()
        for event in evidence.events:
            if type(event) is not dict:
                continue
            data = event.get("data")
            if type(data) is dict and type(data.get("authority_snapshot_root")) is str:
                found.add(data["authority_snapshot_root"])
        return found

    def snapshot_for(evidence):
        case_id, object_id = identity(evidence)
        snapshot = current_snapshot(case_id, object_id)
        if type(snapshot) is not _AuthoritySnapshot:
            raise _CustodyError("host current authority snapshot unavailable")
        return snapshot

    def verify_against(evidence, expected_witness, now):
        case_id, object_id = identity(evidence)
        if type(expected_witness) is not dict:
            raise _CustodyError("host retained custody witness unavailable")
        for event in evidence.events:
            if type(event) is not dict or type(event.get("at")) is not str:
                raise _CustodyError("custody event grammar invalid")
            if event["at"] > now:
                raise _CustodyError("future custody event cannot be current")
        snapshots = {}
        for root in roots(evidence):
            snapshot = archived_snapshot(case_id, object_id, root)
            if type(snapshot) is not _AuthoritySnapshot or snapshot.root != root:
                raise _CustodyError(
                    "host archived authority snapshot unavailable or root-mismatched"
                )
            snapshots[root] = snapshot
        return evidence.verify(
            expected_witness=_deepcopy(expected_witness),
            authority_snapshots=snapshots,
            trusted_snapshot_roots=set(snapshots),
        )

    def advance(candidate, expected_witness):
        case_id, object_id = identity(candidate)
        advanced = compare_and_retain(
            case_id, object_id,
            _deepcopy(expected_witness),
            _deepcopy(candidate.witness()),
        )
        if advanced is not True:
            raise _CustodyError("host custody witness predecessor changed")

    def replace_state(target, candidate):
        target.original_sha256 = candidate.original_sha256
        target.accepted = candidate.accepted
        target.legal_hold = candidate.legal_hold
        target.destroyed = candidate.destroyed
        target.events = _deepcopy(candidate.events)

    def verify_current(evidence):
        case_id, object_id = identity(evidence)
        now = trusted_now()
        expected = _deepcopy(retained_witness(case_id, object_id))
        return verify_against(evidence, expected, now)

    def mutate(evidence, operation):
        case_id, object_id = identity(evidence)
        now = trusted_now()
        expected = _deepcopy(retained_witness(case_id, object_id))
        candidate = _deepcopy(evidence)
        verify_against(candidate, expected, now)
        result = operation(candidate, now)
        advance(candidate, expected)
        replace_state(evidence, candidate)
        return _deepcopy(result)

    def submit_current(*, case_id: str, object_id: str, original: bytes, actor: str):
        now = trusted_now()
        candidate = _Evidence.submit(
            case_id=case_id, object_id=object_id, original=original, actor=actor, at=now
        )
        advance(candidate, None)
        return candidate

    def view_current(evidence, *, actor: str, purpose: str):
        mutate(evidence, lambda item, now: item.view(actor=actor, at=now, purpose=purpose))

    def classify_current(evidence, *, actor: str, status: str, confidential: bool):
        mutate(evidence, lambda item, now: item.classify(
            actor=actor, at=now, status=status, confidential=confidential
        ))

    def accept_current(evidence, *, actor: str):
        mutate(evidence, lambda item, now: item.accept(actor=actor, at=now))

    def replace_original_current(evidence, *, new_bytes: bytes, actor: str):
        mutate(evidence, lambda item, now: item.replace_original(
            new_bytes=new_bytes, actor=actor, at=now
        ))

    def set_hold_current(evidence, *, actor: str, authority_evidence_id: str):
        def operation(item, now):
            snapshot = snapshot_for(item)
            item.set_hold(
                actor=actor, at=now, snapshot=snapshot,
                trusted_snapshot_root=snapshot.root,
                authority_evidence_id=authority_evidence_id,
            )
        mutate(evidence, operation)

    def destroy_current(
        evidence, *, actor: str, retention_evidence_id: str,
        notice_evidence_id: str, approval_evidence_ids: list[str],
        destruction_authority_evidence_id: str,
    ):
        def operation(item, now):
            snapshot = snapshot_for(item)
            return item.destroy(
                actor=actor, at=now, snapshot=snapshot,
                trusted_snapshot_root=snapshot.root,
                retention_evidence_id=retention_evidence_id,
                notice_evidence_id=notice_evidence_id,
                approval_evidence_ids=approval_evidence_ids,
                destruction_authority_evidence_id=destruction_authority_evidence_id,
            )
        return mutate(evidence, operation)

    Service = namedtuple("BoundCurrentCustodyService", (
        "verify_current", "submit_current", "view_current", "classify_current",
        "accept_current", "replace_original_current", "set_hold_current", "destroy_current",
    ))
    return Service(
        verify_current, submit_current, view_current, classify_current,
        accept_current, replace_original_current, set_hold_current, destroy_current,
    )
