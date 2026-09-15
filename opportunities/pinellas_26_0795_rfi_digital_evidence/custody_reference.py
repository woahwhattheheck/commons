from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Iterable, Mapping


class CustodyError(ValueError):
    pass


_HEX64 = re.compile(r"[0-9a-f]{64}\Z")
_AUTHORITY_DECISIONS = {
    "LEGAL_HOLD": {"ENABLED", "RELEASED"},
    "RETENTION_ELIGIBILITY": {"ELIGIBLE", "INELIGIBLE"},
    "NOTICE_COMPLETE": {"COMPLETE", "INCOMPLETE"},
    "APPROVAL": {"APPROVED", "DENIED"},
    "DESTRUCTION_AUTHORITY": {"AUTHORIZED", "DENIED"},
}


def _canon(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _digest(value: Any, label: str) -> str:
    if type(value) is not str or _HEX64.fullmatch(value) is None:
        raise CustodyError(f"{label} must be lowercase 64-hex sha256")
    return value


def _nonempty(value: Any, label: str) -> str:
    if type(value) is not str or not value.strip():
        raise CustodyError(f"{label} must be a non-empty string")
    return value


def _utc(text: str) -> str:
    if type(text) is not str or not text.endswith("Z"):
        raise CustodyError("timestamp must use UTC Z form")
    try:
        dt = datetime.fromisoformat(text[:-1] + "+00:00")
    except ValueError as exc:
        raise CustodyError("invalid timestamp") from exc
    if dt.microsecond:
        raise CustodyError("timestamp must use whole seconds")
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass(frozen=True)
class AuthorityRecord:
    evidence_id: str
    kind: str
    generation: int
    case_id: str
    object_id: str
    decision: str
    issuer: str
    at: str
    revoked: bool = False

    def __post_init__(self) -> None:
        _nonempty(self.evidence_id, "authority evidence_id")
        _nonempty(self.case_id, "authority case_id")
        _nonempty(self.object_id, "authority object_id")
        _nonempty(self.issuer, "authority issuer")
        if type(self.generation) is not int or self.generation < 1:
            raise CustodyError("authority generation must be a positive integer")
        if type(self.kind) is not str or self.kind not in _AUTHORITY_DECISIONS:
            raise CustodyError("authority kind invalid")
        if type(self.decision) is not str or self.decision not in _AUTHORITY_DECISIONS[self.kind]:
            raise CustodyError("authority decision invalid for kind")
        if type(self.revoked) is not bool:
            raise CustodyError("authority revoked must be boolean")
        object.__setattr__(self, "at", _utc(self.at))

    def body(self) -> dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "kind": self.kind,
            "generation": self.generation,
            "case_id": self.case_id,
            "object_id": self.object_id,
            "decision": self.decision,
            "issuer": self.issuer,
            "at": self.at,
            "revoked": self.revoked,
        }

    @property
    def root(self) -> str:
        return _sha(_canon(self.body()))


class AuthoritySnapshot:
    """Immutable authority generation supplied by an external trust system.

    ``root`` is an integrity identifier, not a trust grant. Callers must obtain
    the separately retained trusted root from outside the Evidence object.
    """

    schema = "pinellas.authority-snapshot.v1"

    def __init__(self, records: Iterable[AuthorityRecord]):
        rows = tuple(records)
        if not rows:
            raise CustodyError("authority snapshot must contain records")
        if any(type(row) is not AuthorityRecord for row in rows):
            raise CustodyError("authority snapshot records must be AuthorityRecord")
        seen: set[tuple[str, int]] = set()
        for row in rows:
            key = (row.evidence_id, row.generation)
            if key in seen:
                raise CustodyError("duplicate authority evidence generation")
            seen.add(key)
        self._records = tuple(sorted(rows, key=lambda row: (row.evidence_id, row.generation, row.root)))
        self._by_id: dict[str, tuple[AuthorityRecord, ...]] = {}
        for row in self._records:
            self._by_id[row.evidence_id] = self._by_id.get(row.evidence_id, tuple()) + (row,)

    @property
    def records(self) -> tuple[AuthorityRecord, ...]:
        return self._records

    def body(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "records": [{"record": row.body(), "record_root": row.root} for row in self._records],
        }

    @property
    def root(self) -> str:
        return _sha(_canon(self.body()))

    def assert_trusted(self, trusted_root: str) -> str:
        _digest(trusted_root, "trusted authority snapshot root")
        if trusted_root != self.root:
            raise CustodyError("authority snapshot does not match independently retained trusted root")
        return trusted_root

    def current(self, evidence_id: str) -> AuthorityRecord:
        _nonempty(evidence_id, "authority evidence_id")
        rows = self._by_id.get(evidence_id)
        if not rows:
            raise CustodyError("authority evidence id absent from snapshot")
        return max(rows, key=lambda row: row.generation)

    def bind_current(
        self, *, evidence_id: str, case_id: str, object_id: str,
        kind: str, decision: str, transition_at: str,
    ) -> dict[str, Any]:
        transition_at = _utc(transition_at)
        row = self.current(evidence_id)
        if row.revoked:
            raise CustodyError("authority evidence is revoked")
        if row.case_id != case_id or row.object_id != object_id:
            raise CustodyError("authority evidence subject mismatch")
        if row.kind != kind or row.decision != decision:
            raise CustodyError("authority evidence decision mismatch")
        if row.at > transition_at:
            raise CustodyError("future authority evidence cannot authorize transition")
        return {"evidence_id": row.evidence_id, "generation": row.generation, "record_root": row.root}

    def verify_binding(
        self, binding: Any, *, case_id: str, object_id: str,
        kind: str, decision: str, transition_at: str,
    ) -> AuthorityRecord:
        if type(binding) is not dict or set(binding) != {"evidence_id", "generation", "record_root"}:
            raise CustodyError("authority binding grammar invalid")
        evidence_id = _nonempty(binding["evidence_id"], "authority binding evidence_id")
        if type(binding["generation"]) is not int or binding["generation"] < 1:
            raise CustodyError("authority binding generation invalid")
        _digest(binding["record_root"], "authority binding record root")
        row = self.current(evidence_id)
        if row.generation != binding["generation"] or row.root != binding["record_root"]:
            raise CustodyError("authority binding is stale or root-mismatched")
        if row.revoked:
            raise CustodyError("authority binding is revoked")
        if row.case_id != case_id or row.object_id != object_id:
            raise CustodyError("authority binding subject mismatch")
        if row.kind != kind or row.decision != decision:
            raise CustodyError("authority binding decision mismatch")
        if row.at > _utc(transition_at):
            raise CustodyError("future authority binding cannot authorize transition")
        return row


@dataclass
class Evidence:
    case_id: str
    object_id: str
    original_sha256: str
    accepted: bool = False
    legal_hold: bool = False
    destroyed: bool = False
    events: list[dict[str, Any]] = field(default_factory=list)

    @classmethod
    def submit(cls, *, case_id: str, object_id: str, original: bytes, actor: str, at: str) -> "Evidence":
        if any(type(value) is not str or not value.strip() for value in (case_id, object_id, actor)):
            raise CustodyError("case_id, object_id and actor must be non-empty strings")
        ev = cls(case_id=case_id, object_id=object_id, original_sha256=_sha(original))
        ev._append("SUBMITTED", actor=actor, at=at, data={"sha256": ev.original_sha256, "size": len(original)})
        return ev

    def _append(self, kind: str, *, actor: str, at: str, data: dict[str, Any] | None = None) -> dict[str, Any]:
        if self.destroyed and kind not in {"VERIFY", "EXPORT_AUDIT"}:
            raise CustodyError("destroyed evidence cannot receive lifecycle events")
        if type(actor) is not str or not actor.strip():
            raise CustodyError("actor must be a non-empty string")
        at = _utc(at)
        if self.events and at < self.events[-1]["at"]:
            raise CustodyError("event timestamp cannot move backwards")
        prev_hash = self.events[-1]["event_hash"] if self.events else "GENESIS"
        body = {
            "seq": len(self.events) + 1,
            "case_id": self.case_id,
            "object_id": self.object_id,
            "kind": kind,
            "actor": actor,
            "at": at,
            "prev_hash": prev_hash,
            "data": data or {},
        }
        event_hash = _sha(_canon(body))
        event = {**body, "event_hash": event_hash}
        self.events.append(event)
        return event

    def view(self, *, actor: str, at: str, purpose: str) -> None:
        if type(purpose) is not str or not purpose.strip():
            raise CustodyError("view purpose must be a non-empty string")
        self._append("VIEWED", actor=actor, at=at, data={"purpose": purpose})

    def classify(self, *, actor: str, at: str, status: str, confidential: bool) -> None:
        if type(confidential) is not bool:
            raise CustodyError("confidential must be boolean")
        if type(status) is not str or not status.strip():
            raise CustodyError("status must be a non-empty string")
        self._append("CLASSIFIED", actor=actor, at=at, data={"status": status, "confidential": confidential})

    def accept(self, *, actor: str, at: str) -> None:
        if self.accepted:
            raise CustodyError("already accepted")
        self._append("ACCEPTED_LOCKED", actor=actor, at=at, data={"sha256": self.original_sha256})
        self.accepted = True

    def replace_original(self, *, new_bytes: bytes, actor: str, at: str) -> None:
        if self.accepted:
            raise CustodyError("accepted evidence original is immutable")
        if self.destroyed:
            raise CustodyError("destroyed evidence cannot be replaced")
        new_sha = _sha(new_bytes)
        old_sha = self.original_sha256
        self._append("ORIGINAL_REPLACED_PRE_ACCEPTANCE", actor=actor, at=at, data={
            "old_sha256": old_sha, "new_sha256": new_sha, "size": len(new_bytes)
        })
        self.original_sha256 = new_sha

    def set_hold(
        self, *, actor: str, at: str, snapshot: AuthoritySnapshot,
        trusted_snapshot_root: str, authority_evidence_id: str,
    ) -> None:
        if type(snapshot) is not AuthoritySnapshot:
            raise CustodyError("authority snapshot required")
        root = snapshot.assert_trusted(trusted_snapshot_root)
        row = snapshot.current(authority_evidence_id)
        if row.kind != "LEGAL_HOLD" or row.decision not in {"ENABLED", "RELEASED"}:
            raise CustodyError("legal-hold authority decision required")
        enabled = row.decision == "ENABLED"
        if enabled == self.legal_hold:
            raise CustodyError("legal-hold transition does not change state")
        binding = snapshot.bind_current(
            evidence_id=authority_evidence_id, case_id=self.case_id, object_id=self.object_id,
            kind="LEGAL_HOLD", decision=row.decision, transition_at=at,
        )
        self._append("LEGAL_HOLD_CHANGED", actor=actor, at=at, data={
            "enabled": enabled,
            "authority_snapshot_root": root,
            "authority": binding,
        })
        self.legal_hold = enabled

    def destroy(
        self, *, actor: str, at: str, snapshot: AuthoritySnapshot, trusted_snapshot_root: str,
        retention_evidence_id: str, notice_evidence_id: str,
        approval_evidence_ids: list[str], destruction_authority_evidence_id: str,
    ) -> dict[str, Any]:
        if type(snapshot) is not AuthoritySnapshot:
            raise CustodyError("authority snapshot required")
        root = snapshot.assert_trusted(trusted_snapshot_root)
        if not self.accepted:
            raise CustodyError("only accepted evidence can enter destruction workflow")
        if self.legal_hold:
            raise CustodyError("legal hold blocks destruction")
        if type(approval_evidence_ids) is not list or any(
            type(value) is not str or not value.strip() for value in approval_evidence_ids
        ):
            raise CustodyError("approval evidence IDs must be non-empty strings")
        if len(set(approval_evidence_ids)) < 2:
            raise CustodyError("two distinct approvals required by reference control")
        retention = snapshot.bind_current(
            evidence_id=retention_evidence_id, case_id=self.case_id, object_id=self.object_id,
            kind="RETENTION_ELIGIBILITY", decision="ELIGIBLE", transition_at=at,
        )
        notice = snapshot.bind_current(
            evidence_id=notice_evidence_id, case_id=self.case_id, object_id=self.object_id,
            kind="NOTICE_COMPLETE", decision="COMPLETE", transition_at=at,
        )
        approvals = [
            snapshot.bind_current(
                evidence_id=evidence_id, case_id=self.case_id, object_id=self.object_id,
                kind="APPROVAL", decision="APPROVED", transition_at=at,
            )
            for evidence_id in sorted(set(approval_evidence_ids))
        ]
        approval_issuers = {snapshot.current(binding["evidence_id"]).issuer for binding in approvals}
        if len(approval_issuers) < 2:
            raise CustodyError("two distinct approval issuers required by reference control")
        destruction_authority = snapshot.bind_current(
            evidence_id=destruction_authority_evidence_id, case_id=self.case_id, object_id=self.object_id,
            kind="DESTRUCTION_AUTHORITY", decision="AUTHORIZED", transition_at=at,
        )
        receipt = self._append("DESTROYED", actor=actor, at=at, data={
            "original_sha256": self.original_sha256,
            "authority_snapshot_root": root,
            "retention": retention,
            "notice": notice,
            "approvals": approvals,
            "destruction_authority": destruction_authority,
        })
        self.destroyed = True
        return receipt

    def _state_body(self) -> dict[str, Any]:
        _digest(self.original_sha256, "current original digest")
        if any(type(value) is not bool for value in (self.accepted, self.legal_hold, self.destroyed)):
            raise CustodyError("state flags must be boolean")
        return {
            "original_sha256": self.original_sha256,
            "accepted": self.accepted,
            "legal_hold": self.legal_hold,
            "destroyed": self.destroyed,
        }

    def witness(self) -> dict[str, Any]:
        state_sha256 = _sha(_canon(self._state_body()))
        if self.events:
            head = self.events[-1].get("event_hash")
            _digest(head, "head event hash")
        else:
            head = "GENESIS"
        body = {
            "schema": "pinellas.custody-witness.v1",
            "case_id": self.case_id,
            "object_id": self.object_id,
            "event_count": len(self.events),
            "head_event_hash": head,
            "state_sha256": state_sha256,
        }
        return {**body, "witness_sha256": _sha(_canon(body))}

    @staticmethod
    def _validate_witness(value: Any) -> dict[str, Any]:
        expected = {
            "schema", "case_id", "object_id", "event_count",
            "head_event_hash", "state_sha256", "witness_sha256",
        }
        if type(value) is not dict or set(value) != expected:
            raise CustodyError("external custody witness grammar invalid")
        if value["schema"] != "pinellas.custody-witness.v1":
            raise CustodyError("external custody witness schema invalid")
        _nonempty(value["case_id"], "witness case_id")
        _nonempty(value["object_id"], "witness object_id")
        if type(value["event_count"]) is not int or value["event_count"] < 1:
            raise CustodyError("witness event count invalid")
        _digest(value["head_event_hash"], "witness head event hash")
        _digest(value["state_sha256"], "witness state digest")
        _digest(value["witness_sha256"], "witness digest")
        body = {key: value[key] for key in expected if key != "witness_sha256"}
        if _sha(_canon(body)) != value["witness_sha256"]:
            raise CustodyError("external custody witness digest mismatch")
        return value

    @staticmethod
    def _trusted_snapshot(
        root: Any, authority_snapshots: Mapping[str, AuthoritySnapshot], trusted_snapshot_roots: set[str],
    ) -> AuthoritySnapshot:
        root = _digest(root, "authority snapshot root")
        if root not in trusted_snapshot_roots:
            raise CustodyError("authority snapshot root is not independently trusted")
        snapshot = authority_snapshots.get(root)
        if type(snapshot) is not AuthoritySnapshot or snapshot.root != root:
            raise CustodyError("authority snapshot bytes unavailable or root-mismatched")
        return snapshot

    def verify(
        self, *, expected_witness: dict[str, Any],
        authority_snapshots: Mapping[str, AuthoritySnapshot] | None = None,
        trusted_snapshot_roots: set[str] | None = None,
    ) -> dict[str, Any]:
        expected_witness = self._validate_witness(expected_witness)
        authority_snapshots = {} if authority_snapshots is None else authority_snapshots
        trusted_snapshot_roots = set() if trusted_snapshot_roots is None else trusted_snapshot_roots
        if not isinstance(authority_snapshots, Mapping) or type(trusted_snapshot_roots) is not set:
            raise CustodyError("authority trust inputs invalid")
        for root in trusted_snapshot_roots:
            _digest(root, "trusted authority snapshot root")

        _nonempty(self.case_id, "case_id")
        _nonempty(self.object_id, "object_id")
        _digest(self.original_sha256, "current original digest")
        if any(type(value) is not bool for value in (self.accepted, self.legal_hold, self.destroyed)):
            raise CustodyError("state flags must be boolean")

        prev = "GENESIS"
        prior_at: str | None = None
        derived_original: str | None = None
        derived_accepted = False
        derived_hold = False
        derived_destroyed = False
        known = {
            "SUBMITTED", "VIEWED", "CLASSIFIED", "ACCEPTED_LOCKED",
            "ORIGINAL_REPLACED_PRE_ACCEPTANCE", "LEGAL_HOLD_CHANGED", "DESTROYED",
        }

        for i, event in enumerate(self.events, 1):
            if type(event) is not dict:
                raise CustodyError("event must be object")
            expected_keys = {"seq", "case_id", "object_id", "kind", "actor", "at", "prev_hash", "data", "event_hash"}
            if set(event) != expected_keys:
                raise CustodyError("event keys invalid")
            if type(event["seq"]) is not int or event["seq"] != i:
                raise CustodyError("event sequence invalid")
            if event["case_id"] != self.case_id or event["object_id"] != self.object_id:
                raise CustodyError("event identity mismatch")
            if type(event["kind"]) is not str or event["kind"] not in known:
                raise CustodyError("event kind invalid")
            if type(event["actor"]) is not str or not event["actor"].strip():
                raise CustodyError("event actor invalid")
            at = _utc(event["at"])
            if prior_at is not None and at < prior_at:
                raise CustodyError("event timestamp moved backwards")
            prior_at = at
            if event["prev_hash"] != prev:
                raise CustodyError("event chain predecessor mismatch")
            if prev != "GENESIS":
                _digest(event["prev_hash"], "event predecessor hash")
            if type(event["data"]) is not dict:
                raise CustodyError("event data must be object")
            _digest(event["event_hash"], "event hash")
            body = {key: event[key] for key in expected_keys if key != "event_hash"}
            if _sha(_canon(body)) != event["event_hash"]:
                raise CustodyError("event hash mismatch")

            kind = event["kind"]
            data = event["data"]
            if i == 1 and kind != "SUBMITTED":
                raise CustodyError("first event must be SUBMITTED")
            if kind == "SUBMITTED":
                if i != 1 or set(data) != {"sha256", "size"}:
                    raise CustodyError("SUBMITTED event invalid")
                _digest(data["sha256"], "submitted digest")
                if type(data["size"]) is not int or data["size"] < 0:
                    raise CustodyError("submitted size invalid")
                derived_original = data["sha256"]
            elif kind == "ORIGINAL_REPLACED_PRE_ACCEPTANCE":
                if derived_accepted or derived_destroyed:
                    raise CustodyError("replacement after acceptance/destruction")
                if set(data) != {"old_sha256", "new_sha256", "size"} or data["old_sha256"] != derived_original:
                    raise CustodyError("replacement lineage invalid")
                _digest(data["old_sha256"], "replacement old digest")
                _digest(data["new_sha256"], "replacement new digest")
                if type(data["size"]) is not int or data["size"] < 0:
                    raise CustodyError("replacement size invalid")
                derived_original = data["new_sha256"]
            elif kind == "ACCEPTED_LOCKED":
                if derived_accepted or derived_destroyed:
                    raise CustodyError("duplicate/late acceptance")
                if set(data) != {"sha256"} or data["sha256"] != derived_original:
                    raise CustodyError("acceptance digest mismatch")
                _digest(data["sha256"], "acceptance digest")
                derived_accepted = True
            elif kind == "LEGAL_HOLD_CHANGED":
                if derived_destroyed:
                    raise CustodyError("hold event after destruction")
                if set(data) != {"enabled", "authority_snapshot_root", "authority"} or type(data["enabled"]) is not bool:
                    raise CustodyError("hold event invalid")
                if data["enabled"] == derived_hold:
                    raise CustodyError("hold event does not change state")
                snapshot = self._trusted_snapshot(
                    data["authority_snapshot_root"], authority_snapshots, trusted_snapshot_roots
                )
                decision = "ENABLED" if data["enabled"] else "RELEASED"
                snapshot.verify_binding(
                    data["authority"], case_id=self.case_id, object_id=self.object_id,
                    kind="LEGAL_HOLD", decision=decision, transition_at=at,
                )
                derived_hold = data["enabled"]
            elif kind == "DESTROYED":
                if not derived_accepted or derived_hold or derived_destroyed:
                    raise CustodyError("destruction state invalid")
                if set(data) != {
                    "original_sha256", "authority_snapshot_root", "retention",
                    "notice", "approvals", "destruction_authority",
                }:
                    raise CustodyError("destruction receipt invalid")
                if data["original_sha256"] != derived_original:
                    raise CustodyError("destruction digest mismatch")
                _digest(data["original_sha256"], "destruction original digest")
                snapshot = self._trusted_snapshot(
                    data["authority_snapshot_root"], authority_snapshots, trusted_snapshot_roots
                )
                snapshot.verify_binding(
                    data["retention"], case_id=self.case_id, object_id=self.object_id,
                    kind="RETENTION_ELIGIBILITY", decision="ELIGIBLE", transition_at=at,
                )
                snapshot.verify_binding(
                    data["notice"], case_id=self.case_id, object_id=self.object_id,
                    kind="NOTICE_COMPLETE", decision="COMPLETE", transition_at=at,
                )
                approvals = data["approvals"]
                if type(approvals) is not list or len(approvals) < 2:
                    raise CustodyError("destruction approvals invalid")
                def approval_key(binding: Any) -> tuple[Any, Any, Any]:
                    if type(binding) is not dict:
                        return ("", 0, "")
                    return (binding.get("evidence_id", ""), binding.get("generation", 0), binding.get("record_root", ""))
                if approvals != sorted(approvals, key=approval_key):
                    raise CustodyError("destruction approvals must be canonical")
                approval_rows = [
                    snapshot.verify_binding(
                        binding, case_id=self.case_id, object_id=self.object_id,
                        kind="APPROVAL", decision="APPROVED", transition_at=at,
                    )
                    for binding in approvals
                ]
                if len({row.evidence_id for row in approval_rows}) != len(approval_rows):
                    raise CustodyError("destruction approval identities must be distinct")
                if len({row.issuer for row in approval_rows}) < 2:
                    raise CustodyError("destruction approvals require distinct issuers")
                snapshot.verify_binding(
                    data["destruction_authority"], case_id=self.case_id, object_id=self.object_id,
                    kind="DESTRUCTION_AUTHORITY", decision="AUTHORIZED", transition_at=at,
                )
                derived_destroyed = True
            elif kind == "VIEWED":
                if derived_destroyed or set(data) != {"purpose"} or type(data["purpose"]) is not str or not data["purpose"].strip():
                    raise CustodyError("view event invalid")
            elif kind == "CLASSIFIED":
                if (derived_destroyed or set(data) != {"status", "confidential"}
                        or type(data["status"]) is not str or not data["status"].strip()
                        or type(data["confidential"]) is not bool):
                    raise CustodyError("classification event invalid")

            prev = event["event_hash"]

        if derived_original is None:
            raise CustodyError("missing submission event")
        if self.original_sha256 != derived_original:
            raise CustodyError("current original digest diverges from custody chain")
        if self.accepted != derived_accepted:
            raise CustodyError("accepted state diverges from custody chain")
        if self.legal_hold != derived_hold:
            raise CustodyError("legal-hold state diverges from custody chain")
        if self.destroyed != derived_destroyed:
            raise CustodyError("destroyed state diverges from custody chain")

        current_witness = self.witness()
        if current_witness != expected_witness:
            raise CustodyError("custody history/state diverges from independently retained witness")

        return {
            "ok": True,
            "case_id": self.case_id,
            "object_id": self.object_id,
            "original_sha256": self.original_sha256,
            "event_count": len(self.events),
            "head_event_hash": prev,
            "accepted": self.accepted,
            "legal_hold": self.legal_hold,
            "destroyed": self.destroyed,
            "witness_sha256": current_witness["witness_sha256"],
        }
