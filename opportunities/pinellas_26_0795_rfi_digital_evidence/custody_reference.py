from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


class CustodyError(ValueError):
    pass


def _canon(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


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
        if any(type(x) is not str or not x.strip() for x in (case_id, object_id, actor)):
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

    def set_hold(self, *, actor: str, at: str, enabled: bool, authority: str) -> None:
        if type(enabled) is not bool:
            raise CustodyError("enabled must be boolean")
        if type(authority) is not str or not authority.strip():
            raise CustodyError("hold authority must be a non-empty string")
        self._append("LEGAL_HOLD_CHANGED", actor=actor, at=at, data={"enabled": enabled, "authority": authority})
        self.legal_hold = enabled

    def destroy(self, *, actor: str, at: str, retention_eligible: bool, notice_complete: bool,
                approval_ids: list[str], authority: str) -> dict[str, Any]:
        if type(retention_eligible) is not bool or type(notice_complete) is not bool:
            raise CustodyError("retention_eligible and notice_complete must be boolean")
        if not self.accepted:
            raise CustodyError("only accepted evidence can enter destruction workflow")
        if self.legal_hold:
            raise CustodyError("legal hold blocks destruction")
        if not retention_eligible:
            raise CustodyError("retention eligibility not established")
        if not notice_complete:
            raise CustodyError("required notice/copy opportunity not complete")
        if type(approval_ids) is not list or any(type(x) is not str or not x.strip() for x in approval_ids):
            raise CustodyError("approval_ids must be non-empty strings")
        if len(set(approval_ids)) < 2:
            raise CustodyError("two distinct approvals required by reference control")
        if type(authority) is not str or not authority.strip():
            raise CustodyError("destruction authority must be a non-empty string")
        receipt = self._append("DESTROYED", actor=actor, at=at, data={
            "original_sha256": self.original_sha256,
            "approval_ids": sorted(set(approval_ids)),
            "authority": authority,
        })
        self.destroyed = True
        return receipt

    def verify(self) -> dict[str, Any]:
        if type(self.case_id) is not str or not self.case_id.strip():
            raise CustodyError("case_id invalid")
        if type(self.object_id) is not str or not self.object_id.strip():
            raise CustodyError("object_id invalid")
        if any(type(x) is not bool for x in (self.accepted, self.legal_hold, self.destroyed)):
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
            if type(event["data"]) is not dict:
                raise CustodyError("event data must be object")
            body = {k: event[k] for k in expected_keys if k != "event_hash"}
            if type(event["event_hash"]) is not str or _sha(_canon(body)) != event["event_hash"]:
                raise CustodyError("event hash mismatch")

            kind = event["kind"]
            data = event["data"]
            if i == 1 and kind != "SUBMITTED":
                raise CustodyError("first event must be SUBMITTED")
            if kind == "SUBMITTED":
                if i != 1 or set(data) != {"sha256", "size"}:
                    raise CustodyError("SUBMITTED event invalid")
                if type(data["sha256"]) is not str or len(data["sha256"]) != 64:
                    raise CustodyError("submitted digest invalid")
                if type(data["size"]) is not int or data["size"] < 0:
                    raise CustodyError("submitted size invalid")
                derived_original = data["sha256"]
            elif kind == "ORIGINAL_REPLACED_PRE_ACCEPTANCE":
                if derived_accepted or derived_destroyed:
                    raise CustodyError("replacement after acceptance/destruction")
                if set(data) != {"old_sha256", "new_sha256", "size"} or data["old_sha256"] != derived_original:
                    raise CustodyError("replacement lineage invalid")
                if type(data["new_sha256"]) is not str or len(data["new_sha256"]) != 64:
                    raise CustodyError("replacement digest invalid")
                if type(data["size"]) is not int or data["size"] < 0:
                    raise CustodyError("replacement size invalid")
                derived_original = data["new_sha256"]
            elif kind == "ACCEPTED_LOCKED":
                if derived_accepted or derived_destroyed:
                    raise CustodyError("duplicate/late acceptance")
                if set(data) != {"sha256"} or data["sha256"] != derived_original:
                    raise CustodyError("acceptance digest mismatch")
                derived_accepted = True
            elif kind == "LEGAL_HOLD_CHANGED":
                if derived_destroyed:
                    raise CustodyError("hold event after destruction")
                if set(data) != {"enabled", "authority"} or type(data["enabled"]) is not bool:
                    raise CustodyError("hold event invalid")
                if type(data["authority"]) is not str or not data["authority"].strip():
                    raise CustodyError("hold authority invalid")
                derived_hold = data["enabled"]
            elif kind == "DESTROYED":
                if not derived_accepted or derived_hold or derived_destroyed:
                    raise CustodyError("destruction state invalid")
                if set(data) != {"original_sha256", "approval_ids", "authority"}:
                    raise CustodyError("destruction receipt invalid")
                if data["original_sha256"] != derived_original:
                    raise CustodyError("destruction digest mismatch")
                approvals = data["approval_ids"]
                if (type(approvals) is not list or len(approvals) < 2
                        or approvals != sorted(set(approvals))
                        or any(type(x) is not str or not x.strip() for x in approvals)):
                    raise CustodyError("destruction approvals invalid")
                if type(data["authority"]) is not str or not data["authority"].strip():
                    raise CustodyError("destruction authority invalid")
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
        }
