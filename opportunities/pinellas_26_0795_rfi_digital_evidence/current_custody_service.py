from __future__ import annotations

import hashlib
import json
import re
from collections import namedtuple
from datetime import datetime, timezone
from typing import Any, Protocol

from custody_reference import AuthorityRecord, AuthoritySnapshot, CustodyError, Evidence


class HostTrustProvider(Protocol):
    """Host-owned time/witness/authority boundary for current custody state."""

    def current_time_utc(self) -> str: ...

    def retained_custody_witness(
        self, case_id: str, object_id: str
    ) -> dict[str, Any]: ...

    def compare_and_retain_custody_witness(
        self,
        case_id: str,
        object_id: str,
        expected_witness: dict[str, Any] | None,
        successor_witness: dict[str, Any],
    ) -> bool: ...

    def current_authority_snapshot(
        self, case_id: str, object_id: str
    ) -> AuthoritySnapshot: ...

    def archived_authority_snapshot(
        self, case_id: str, object_id: str, root: str
    ) -> AuthoritySnapshot: ...


def _build_current_factory(
    evidence_type,
    snapshot_type,
    record_type,
    error_type,
    sha256_func,
    encoder_encode,
    fromisoformat,
    utc_zone,
    object_new,
    object_setattr,
    object_getattribute,
):
    hex64 = re.compile(r"[0-9a-f]{64}\Z")

    def canon(value: Any) -> bytes:
        return encoder_encode(value).encode("utf-8")

    def sha(data: bytes) -> str:
        return sha256_func(data).hexdigest()

    def digest(value: Any, label: str) -> str:
        if type(value) is not str or hex64.fullmatch(value) is None:
            raise error_type(f"{label} must be lowercase 64-hex sha256")
        return value

    def nonempty(value: Any, label: str) -> str:
        if type(value) is not str or not value.strip():
            raise error_type(f"{label} must be a non-empty string")
        return value

    def utc(text: str) -> str:
        if type(text) is not str or not text.endswith("Z"):
            raise error_type("timestamp must use UTC Z form")
        try:
            dt = fromisoformat(text[:-1] + "+00:00")
        except ValueError as exc:
            raise error_type("invalid timestamp") from exc
        if dt.microsecond:
            raise error_type("timestamp must use whole seconds")
        normalized = dt.astimezone(utc_zone).strftime("%Y-%m-%dT%H:%M:%SZ")
        if normalized != text:
            raise error_type("timestamp must be canonical UTC Z form")
        return normalized

    def clone(value: Any) -> Any:
        value_type = type(value)
        if value_type in (str, int, bool, bytes, type(None)):
            return value
        if value_type is list:
            return [clone(item) for item in value]
        if value_type is tuple:
            return tuple(clone(item) for item in value)
        if value_type is dict:
            return {clone(key): clone(item) for key, item in value.items()}
        raise error_type("current custody value contains unsupported mutable type")

    def record_body(row) -> dict[str, Any]:
        if type(row) is not record_type:
            raise error_type("authority snapshot records must be AuthorityRecord")
        evidence_id = nonempty(row.evidence_id, "authority evidence_id")
        case_id = nonempty(row.case_id, "authority case_id")
        object_id = nonempty(row.object_id, "authority object_id")
        issuer = nonempty(row.issuer, "authority issuer")
        if type(row.generation) is not int or row.generation < 1:
            raise error_type("authority generation must be a positive integer")
        decisions = {
            "LEGAL_HOLD": {"ENABLED", "RELEASED"},
            "RETENTION_ELIGIBILITY": {"ELIGIBLE", "INELIGIBLE"},
            "NOTICE_COMPLETE": {"COMPLETE", "INCOMPLETE"},
            "APPROVAL": {"APPROVED", "DENIED"},
            "DESTRUCTION_AUTHORITY": {"AUTHORIZED", "DENIED"},
        }
        if type(row.kind) is not str or row.kind not in decisions:
            raise error_type("authority kind invalid")
        if type(row.decision) is not str or row.decision not in decisions[row.kind]:
            raise error_type("authority decision invalid for kind")
        if type(row.revoked) is not bool:
            raise error_type("authority revoked must be boolean")
        at = utc(row.at)
        return {
            "evidence_id": evidence_id,
            "kind": row.kind,
            "generation": row.generation,
            "case_id": case_id,
            "object_id": object_id,
            "decision": row.decision,
            "issuer": issuer,
            "at": at,
            "revoked": row.revoked,
        }

    def record_root(row) -> str:
        return sha(canon(record_body(row)))

    def snapshot_rows(snapshot) -> tuple:
        if type(snapshot) is not snapshot_type:
            raise error_type("host authority snapshot unavailable")
        raw = object_getattribute(snapshot, "__dict__").get("_records")
        if type(raw) is not tuple or not raw:
            raise error_type("authority snapshot rows unavailable")
        rows = tuple(raw)
        seen = set()
        for row in rows:
            body = record_body(row)
            key = (body["evidence_id"], body["generation"])
            if key in seen:
                raise error_type("duplicate authority evidence generation")
            seen.add(key)
        return tuple(
            sorted(rows, key=lambda row: (row.evidence_id, row.generation, record_root(row)))
        )

    def snapshot_root(snapshot) -> str:
        rows = snapshot_rows(snapshot)
        body = {
            "schema": "pinellas.authority-snapshot.v1",
            "records": [
                {"record": record_body(row), "record_root": record_root(row)}
                for row in rows
            ],
        }
        return sha(canon(body))

    def current_row(snapshot, evidence_id: str):
        nonempty(evidence_id, "authority evidence_id")
        rows = [
            row for row in snapshot_rows(snapshot)
            if row.evidence_id == evidence_id
        ]
        if not rows:
            raise error_type("authority evidence id absent from snapshot")
        return max(rows, key=lambda row: row.generation)

    def verify_binding(
        snapshot,
        binding: Any,
        *,
        case_id: str,
        object_id: str,
        kind: str,
        decision: str,
        transition_at: str,
    ):
        transition_at = utc(transition_at)
        if type(binding) is not dict or set(binding) != {
            "evidence_id", "generation", "record_root"
        }:
            raise error_type("authority binding grammar invalid")
        evidence_id = nonempty(binding["evidence_id"], "authority binding evidence_id")
        if type(binding["generation"]) is not int or binding["generation"] < 1:
            raise error_type("authority binding generation invalid")
        digest(binding["record_root"], "authority binding record root")
        row = current_row(snapshot, evidence_id)
        if row.generation != binding["generation"] or record_root(row) != binding["record_root"]:
            raise error_type("authority binding is stale or root-mismatched")
        body = record_body(row)
        if body["revoked"]:
            raise error_type("authority binding is revoked")
        if body["case_id"] != case_id or body["object_id"] != object_id:
            raise error_type("authority binding subject mismatch")
        if body["kind"] != kind or body["decision"] != decision:
            raise error_type("authority binding decision mismatch")
        if body["at"] > transition_at:
            raise error_type("future authority binding cannot authorize transition")
        return row

    def make_binding(
        snapshot,
        *,
        evidence_id: str,
        case_id: str,
        object_id: str,
        kind: str,
        decision: str,
        transition_at: str,
    ) -> dict[str, Any]:
        row = current_row(snapshot, evidence_id)
        binding = {
            "evidence_id": row.evidence_id,
            "generation": row.generation,
            "record_root": record_root(row),
        }
        verify_binding(
            snapshot,
            binding,
            case_id=case_id,
            object_id=object_id,
            kind=kind,
            decision=decision,
            transition_at=transition_at,
        )
        return binding

    def evidence_fields(evidence):
        if type(evidence) is not evidence_type:
            raise error_type("Evidence instance required")
        attrs = object_getattribute(evidence, "__dict__")
        required = {
            "case_id", "object_id", "original_sha256",
            "accepted", "legal_hold", "destroyed", "events",
        }
        if not required.issubset(attrs):
            raise error_type("Evidence state incomplete")
        case_id = nonempty(attrs["case_id"], "case_id")
        object_id = nonempty(attrs["object_id"], "object_id")
        original = digest(attrs["original_sha256"], "current original digest")
        accepted = attrs["accepted"]
        hold = attrs["legal_hold"]
        destroyed = attrs["destroyed"]
        events = attrs["events"]
        if any(type(value) is not bool for value in (accepted, hold, destroyed)):
            raise error_type("state flags must be boolean")
        if type(events) is not list:
            raise error_type("events must be a list")
        return case_id, object_id, original, accepted, hold, destroyed, events

    def clone_evidence(evidence):
        case_id, object_id, original, accepted, hold, destroyed, events = evidence_fields(evidence)
        candidate = object_new(evidence_type)
        object_setattr(candidate, "case_id", case_id)
        object_setattr(candidate, "object_id", object_id)
        object_setattr(candidate, "original_sha256", original)
        object_setattr(candidate, "accepted", accepted)
        object_setattr(candidate, "legal_hold", hold)
        object_setattr(candidate, "destroyed", destroyed)
        object_setattr(candidate, "events", clone(events))
        return candidate

    def state_body(evidence) -> dict[str, Any]:
        _, _, original, accepted, hold, destroyed, _ = evidence_fields(evidence)
        return {
            "original_sha256": original,
            "accepted": accepted,
            "legal_hold": hold,
            "destroyed": destroyed,
        }

    def witness(evidence) -> dict[str, Any]:
        case_id, object_id, _, _, _, _, events = evidence_fields(evidence)
        state_sha256 = sha(canon(state_body(evidence)))
        if events:
            head = events[-1].get("event_hash") if type(events[-1]) is dict else None
            digest(head, "head event hash")
        else:
            head = "GENESIS"
        body = {
            "schema": "pinellas.custody-witness.v1",
            "case_id": case_id,
            "object_id": object_id,
            "event_count": len(events),
            "head_event_hash": head,
            "state_sha256": state_sha256,
        }
        return {**body, "witness_sha256": sha(canon(body))}

    def validate_witness(value: Any) -> dict[str, Any]:
        expected = {
            "schema", "case_id", "object_id", "event_count",
            "head_event_hash", "state_sha256", "witness_sha256",
        }
        if type(value) is not dict or set(value) != expected:
            raise error_type("external custody witness grammar invalid")
        if value["schema"] != "pinellas.custody-witness.v1":
            raise error_type("external custody witness schema invalid")
        nonempty(value["case_id"], "witness case_id")
        nonempty(value["object_id"], "witness object_id")
        if type(value["event_count"]) is not int or value["event_count"] < 1:
            raise error_type("witness event count invalid")
        digest(value["head_event_hash"], "witness head event hash")
        digest(value["state_sha256"], "witness state digest")
        digest(value["witness_sha256"], "witness digest")
        body = {key: value[key] for key in expected if key != "witness_sha256"}
        if sha(canon(body)) != value["witness_sha256"]:
            raise error_type("external custody witness digest mismatch")
        return value

    Service = namedtuple(
        "BoundCurrentCustodyService",
        (
            "verify_current",
            "submit_current",
            "view_current",
            "classify_current",
            "accept_current",
            "replace_original_current",
            "set_hold_current",
            "destroy_current",
        ),
    )

    def public_factory(provider: HostTrustProvider):
        current_time = getattr(provider, "current_time_utc", None)
        retained_witness = getattr(provider, "retained_custody_witness", None)
        compare_and_retain = getattr(provider, "compare_and_retain_custody_witness", None)
        current_snapshot = getattr(provider, "current_authority_snapshot", None)
        archived_snapshot = getattr(provider, "archived_authority_snapshot", None)
        if any(not callable(method) for method in (
            current_time, retained_witness, compare_and_retain,
            current_snapshot, archived_snapshot,
        )):
            raise error_type("host trust provider contract incomplete")

        def identity(evidence):
            case_id, object_id, *_ = evidence_fields(evidence)
            return case_id, object_id

        def trusted_now() -> str:
            return utc(current_time())

        def resolve_archived(case_id: str, object_id: str, root: str, cache: dict):
            digest(root, "authority snapshot root")
            if root not in cache:
                snapshot = archived_snapshot(case_id, object_id, root)
                if type(snapshot) is not snapshot_type or snapshot_root(snapshot) != root:
                    raise error_type(
                        "host archived authority snapshot unavailable or root-mismatched"
                    )
                cache[root] = snapshot
            return cache[root]

        def verify_against(evidence, expected_witness, now: str):
            now = utc(now)
            expected_witness = validate_witness(clone(expected_witness))
            (
                case_id,
                object_id,
                current_original,
                current_accepted,
                current_hold,
                current_destroyed,
                events,
            ) = evidence_fields(evidence)
            if (
                expected_witness["case_id"] != case_id
                or expected_witness["object_id"] != object_id
            ):
                raise error_type("external custody witness identity mismatch")

            prev = "GENESIS"
            prior_at = None
            derived_original = None
            derived_accepted = False
            derived_hold = False
            derived_destroyed = False
            known = {
                "SUBMITTED", "VIEWED", "CLASSIFIED", "ACCEPTED_LOCKED",
                "ORIGINAL_REPLACED_PRE_ACCEPTANCE", "LEGAL_HOLD_CHANGED", "DESTROYED",
            }
            snapshots = {}

            for i, event in enumerate(events, 1):
                if type(event) is not dict:
                    raise error_type("event must be object")
                event_keys = {
                    "seq", "case_id", "object_id", "kind", "actor",
                    "at", "prev_hash", "data", "event_hash",
                }
                if set(event) != event_keys:
                    raise error_type("event keys invalid")
                if type(event["seq"]) is not int or event["seq"] != i:
                    raise error_type("event sequence invalid")
                if event["case_id"] != case_id or event["object_id"] != object_id:
                    raise error_type("event identity mismatch")
                if type(event["kind"]) is not str or event["kind"] not in known:
                    raise error_type("event kind invalid")
                nonempty(event["actor"], "event actor")
                at = utc(event["at"])
                if at > now:
                    raise error_type("future custody event cannot be current")
                if prior_at is not None and at < prior_at:
                    raise error_type("event timestamp moved backwards")
                prior_at = at
                if event["prev_hash"] != prev:
                    raise error_type("event chain predecessor mismatch")
                if prev != "GENESIS":
                    digest(event["prev_hash"], "event predecessor hash")
                if type(event["data"]) is not dict:
                    raise error_type("event data must be object")
                digest(event["event_hash"], "event hash")
                body = {key: event[key] for key in event_keys if key != "event_hash"}
                if sha(canon(body)) != event["event_hash"]:
                    raise error_type("event hash mismatch")

                kind = event["kind"]
                data = event["data"]
                if i == 1 and kind != "SUBMITTED":
                    raise error_type("first event must be SUBMITTED")
                if kind == "SUBMITTED":
                    if i != 1 or set(data) != {"sha256", "size"}:
                        raise error_type("SUBMITTED event invalid")
                    derived_original = digest(data["sha256"], "submitted digest")
                    if type(data["size"]) is not int or data["size"] < 0:
                        raise error_type("submitted size invalid")
                elif kind == "ORIGINAL_REPLACED_PRE_ACCEPTANCE":
                    if derived_accepted or derived_destroyed:
                        raise error_type("replacement after acceptance/destruction")
                    if (
                        set(data) != {"old_sha256", "new_sha256", "size"}
                        or data["old_sha256"] != derived_original
                    ):
                        raise error_type("replacement lineage invalid")
                    digest(data["old_sha256"], "replacement old digest")
                    derived_original = digest(data["new_sha256"], "replacement new digest")
                    if type(data["size"]) is not int or data["size"] < 0:
                        raise error_type("replacement size invalid")
                elif kind == "ACCEPTED_LOCKED":
                    if derived_accepted or derived_destroyed:
                        raise error_type("duplicate/late acceptance")
                    if set(data) != {"sha256"} or data["sha256"] != derived_original:
                        raise error_type("acceptance digest mismatch")
                    digest(data["sha256"], "acceptance digest")
                    derived_accepted = True
                elif kind == "LEGAL_HOLD_CHANGED":
                    if derived_destroyed:
                        raise error_type("hold event after destruction")
                    if (
                        set(data) != {"enabled", "authority_snapshot_root", "authority"}
                        or type(data["enabled"]) is not bool
                        or data["enabled"] == derived_hold
                    ):
                        raise error_type("hold event invalid")
                    root = digest(data["authority_snapshot_root"], "authority snapshot root")
                    snapshot = resolve_archived(case_id, object_id, root, snapshots)
                    decision = "ENABLED" if data["enabled"] else "RELEASED"
                    verify_binding(
                        snapshot,
                        data["authority"],
                        case_id=case_id,
                        object_id=object_id,
                        kind="LEGAL_HOLD",
                        decision=decision,
                        transition_at=at,
                    )
                    derived_hold = data["enabled"]
                elif kind == "DESTROYED":
                    if not derived_accepted or derived_hold or derived_destroyed:
                        raise error_type("destruction state invalid")
                    if set(data) != {
                        "original_sha256", "authority_snapshot_root", "retention",
                        "notice", "approvals", "destruction_authority",
                    }:
                        raise error_type("destruction receipt invalid")
                    if data["original_sha256"] != derived_original:
                        raise error_type("destruction digest mismatch")
                    digest(data["original_sha256"], "destruction original digest")
                    root = digest(data["authority_snapshot_root"], "authority snapshot root")
                    snapshot = resolve_archived(case_id, object_id, root, snapshots)
                    verify_binding(
                        snapshot,
                        data["retention"],
                        case_id=case_id,
                        object_id=object_id,
                        kind="RETENTION_ELIGIBILITY",
                        decision="ELIGIBLE",
                        transition_at=at,
                    )
                    verify_binding(
                        snapshot,
                        data["notice"],
                        case_id=case_id,
                        object_id=object_id,
                        kind="NOTICE_COMPLETE",
                        decision="COMPLETE",
                        transition_at=at,
                    )
                    approvals = data["approvals"]
                    if type(approvals) is not list or len(approvals) < 2:
                        raise error_type("destruction approvals invalid")

                    def approval_key(binding):
                        if type(binding) is not dict:
                            return ("", 0, "")
                        return (
                            binding.get("evidence_id", ""),
                            binding.get("generation", 0),
                            binding.get("record_root", ""),
                        )

                    if approvals != sorted(approvals, key=approval_key):
                        raise error_type("destruction approvals must be canonical")
                    approval_rows = [
                        verify_binding(
                            snapshot,
                            binding,
                            case_id=case_id,
                            object_id=object_id,
                            kind="APPROVAL",
                            decision="APPROVED",
                            transition_at=at,
                        )
                        for binding in approvals
                    ]
                    if len({row.evidence_id for row in approval_rows}) != len(approval_rows):
                        raise error_type("destruction approval identities must be distinct")
                    if len({row.issuer for row in approval_rows}) < 2:
                        raise error_type("destruction approvals require distinct issuers")
                    verify_binding(
                        snapshot,
                        data["destruction_authority"],
                        case_id=case_id,
                        object_id=object_id,
                        kind="DESTRUCTION_AUTHORITY",
                        decision="AUTHORIZED",
                        transition_at=at,
                    )
                    derived_destroyed = True
                elif kind == "VIEWED":
                    if (
                        derived_destroyed
                        or set(data) != {"purpose"}
                        or type(data["purpose"]) is not str
                        or not data["purpose"].strip()
                    ):
                        raise error_type("view event invalid")
                elif kind == "CLASSIFIED":
                    if (
                        derived_destroyed
                        or set(data) != {"status", "confidential"}
                        or type(data["status"]) is not str
                        or not data["status"].strip()
                        or type(data["confidential"]) is not bool
                    ):
                        raise error_type("classification event invalid")
                prev = event["event_hash"]

            if derived_original is None:
                raise error_type("missing submission event")
            if current_original != derived_original:
                raise error_type("current original digest diverges from custody chain")
            if current_accepted != derived_accepted:
                raise error_type("accepted state diverges from custody chain")
            if current_hold != derived_hold:
                raise error_type("legal-hold state diverges from custody chain")
            if current_destroyed != derived_destroyed:
                raise error_type("destroyed state diverges from custody chain")
            current_witness = witness(evidence)
            if current_witness != expected_witness:
                raise error_type(
                    "custody history/state diverges from independently retained witness"
                )
            return {
                "ok": True,
                "case_id": case_id,
                "object_id": object_id,
                "original_sha256": current_original,
                "event_count": len(events),
                "head_event_hash": prev,
                "accepted": current_accepted,
                "legal_hold": current_hold,
                "destroyed": current_destroyed,
                "witness_sha256": current_witness["witness_sha256"],
            }

        def append_event(evidence, kind: str, *, actor: str, at: str, data=None):
            case_id, object_id, _, _, _, destroyed, events = evidence_fields(evidence)
            if destroyed:
                raise error_type("destroyed evidence cannot receive lifecycle events")
            nonempty(actor, "actor")
            at = utc(at)
            if events and at < utc(events[-1]["at"]):
                raise error_type("event timestamp cannot move backwards")
            prev_hash = events[-1]["event_hash"] if events else "GENESIS"
            body = {
                "seq": len(events) + 1,
                "case_id": case_id,
                "object_id": object_id,
                "kind": kind,
                "actor": actor,
                "at": at,
                "prev_hash": prev_hash,
                "data": {} if data is None else clone(data),
            }
            event = {**body, "event_hash": sha(canon(body))}
            events.append(event)
            return event

        def replace_state(target, candidate):
            _, _, original, accepted, hold, destroyed, events = evidence_fields(candidate)
            object_setattr(target, "original_sha256", original)
            object_setattr(target, "accepted", accepted)
            object_setattr(target, "legal_hold", hold)
            object_setattr(target, "destroyed", destroyed)
            object_setattr(target, "events", clone(events))

        def verify_current(evidence):
            case_id, object_id = identity(evidence)
            now = trusted_now()
            expected = clone(retained_witness(case_id, object_id))
            return verify_against(evidence, expected, now)

        def advance(candidate, expected, now):
            successor = witness(candidate)
            verify_against(candidate, successor, now)
            case_id, object_id = identity(candidate)
            result = compare_and_retain(
                case_id,
                object_id,
                clone(expected),
                clone(successor),
            )
            if result is not True:
                raise error_type("host custody witness predecessor changed")
            return successor

        def mutate(evidence, operation):
            case_id, object_id = identity(evidence)
            now = trusted_now()
            expected = clone(retained_witness(case_id, object_id))
            candidate = clone_evidence(evidence)
            verify_against(candidate, expected, now)
            result = operation(candidate, now)
            advance(candidate, expected, now)
            replace_state(evidence, candidate)
            return clone(result)

        def submit_current(*, case_id: str, object_id: str, original: bytes, actor: str):
            case_id = nonempty(case_id, "case_id")
            object_id = nonempty(object_id, "object_id")
            actor = nonempty(actor, "actor")
            if type(original) is not bytes:
                raise error_type("original must be bytes")
            now = trusted_now()
            candidate = object_new(evidence_type)
            object_setattr(candidate, "case_id", case_id)
            object_setattr(candidate, "object_id", object_id)
            object_setattr(candidate, "original_sha256", sha(original))
            object_setattr(candidate, "accepted", False)
            object_setattr(candidate, "legal_hold", False)
            object_setattr(candidate, "destroyed", False)
            object_setattr(candidate, "events", [])
            append_event(
                candidate,
                "SUBMITTED",
                actor=actor,
                at=now,
                data={"sha256": candidate.original_sha256, "size": len(original)},
            )
            advance(candidate, None, now)
            return candidate

        def view_current(evidence, *, actor: str, purpose: str):
            nonempty(purpose, "view purpose")
            mutate(
                evidence,
                lambda item, now: append_event(
                    item,
                    "VIEWED",
                    actor=actor,
                    at=now,
                    data={"purpose": purpose},
                ),
            )

        def classify_current(
            evidence, *, actor: str, status: str, confidential: bool
        ):
            nonempty(status, "status")
            if type(confidential) is not bool:
                raise error_type("confidential must be boolean")
            mutate(
                evidence,
                lambda item, now: append_event(
                    item,
                    "CLASSIFIED",
                    actor=actor,
                    at=now,
                    data={"status": status, "confidential": confidential},
                ),
            )

        def accept_current(evidence, *, actor: str):
            def operation(item, now):
                _, _, original, accepted, _, destroyed, _ = evidence_fields(item)
                if accepted or destroyed:
                    raise error_type("already accepted or destroyed")
                append_event(
                    item,
                    "ACCEPTED_LOCKED",
                    actor=actor,
                    at=now,
                    data={"sha256": original},
                )
                object_setattr(item, "accepted", True)

            mutate(evidence, operation)

        def replace_original_current(evidence, *, new_bytes: bytes, actor: str):
            if type(new_bytes) is not bytes:
                raise error_type("new_bytes must be bytes")

            def operation(item, now):
                _, _, original, accepted, _, destroyed, _ = evidence_fields(item)
                if accepted:
                    raise error_type("accepted evidence original is immutable")
                if destroyed:
                    raise error_type("destroyed evidence cannot be replaced")
                new_sha = sha(new_bytes)
                append_event(
                    item,
                    "ORIGINAL_REPLACED_PRE_ACCEPTANCE",
                    actor=actor,
                    at=now,
                    data={
                        "old_sha256": original,
                        "new_sha256": new_sha,
                        "size": len(new_bytes),
                    },
                )
                object_setattr(item, "original_sha256", new_sha)

            mutate(evidence, operation)

        def current_snapshot_for(evidence):
            case_id, object_id = identity(evidence)
            snapshot = current_snapshot(case_id, object_id)
            if type(snapshot) is not snapshot_type:
                raise error_type("host current authority snapshot unavailable")
            snapshot_root(snapshot)
            return snapshot

        def set_hold_current(
            evidence, *, actor: str, authority_evidence_id: str
        ):
            def operation(item, now):
                case_id, object_id, _, _, hold, _, _ = evidence_fields(item)
                snapshot = current_snapshot_for(item)
                row = current_row(snapshot, authority_evidence_id)
                body = record_body(row)
                if body["kind"] != "LEGAL_HOLD" or body["decision"] not in {
                    "ENABLED", "RELEASED"
                }:
                    raise error_type("legal-hold authority decision required")
                enabled = body["decision"] == "ENABLED"
                if enabled == hold:
                    raise error_type("legal-hold transition does not change state")
                binding = make_binding(
                    snapshot,
                    evidence_id=authority_evidence_id,
                    case_id=case_id,
                    object_id=object_id,
                    kind="LEGAL_HOLD",
                    decision=body["decision"],
                    transition_at=now,
                )
                append_event(
                    item,
                    "LEGAL_HOLD_CHANGED",
                    actor=actor,
                    at=now,
                    data={
                        "enabled": enabled,
                        "authority_snapshot_root": snapshot_root(snapshot),
                        "authority": binding,
                    },
                )
                object_setattr(item, "legal_hold", enabled)

            mutate(evidence, operation)

        def destroy_current(
            evidence,
            *,
            actor: str,
            retention_evidence_id: str,
            notice_evidence_id: str,
            approval_evidence_ids: list[str],
            destruction_authority_evidence_id: str,
        ):
            def operation(item, now):
                (
                    case_id,
                    object_id,
                    original,
                    accepted,
                    hold,
                    destroyed,
                    _,
                ) = evidence_fields(item)
                if not accepted:
                    raise error_type(
                        "only accepted evidence can enter destruction workflow"
                    )
                if hold:
                    raise error_type("legal hold blocks destruction")
                if destroyed:
                    raise error_type("evidence already destroyed")
                if (
                    type(approval_evidence_ids) is not list
                    or any(
                        type(value) is not str or not value.strip()
                        for value in approval_evidence_ids
                    )
                    or len(set(approval_evidence_ids)) < 2
                ):
                    raise error_type("two distinct approval evidence IDs required")
                snapshot = current_snapshot_for(item)
                retention = make_binding(
                    snapshot,
                    evidence_id=retention_evidence_id,
                    case_id=case_id,
                    object_id=object_id,
                    kind="RETENTION_ELIGIBILITY",
                    decision="ELIGIBLE",
                    transition_at=now,
                )
                notice = make_binding(
                    snapshot,
                    evidence_id=notice_evidence_id,
                    case_id=case_id,
                    object_id=object_id,
                    kind="NOTICE_COMPLETE",
                    decision="COMPLETE",
                    transition_at=now,
                )
                approvals = [
                    make_binding(
                        snapshot,
                        evidence_id=evidence_id,
                        case_id=case_id,
                        object_id=object_id,
                        kind="APPROVAL",
                        decision="APPROVED",
                        transition_at=now,
                    )
                    for evidence_id in sorted(set(approval_evidence_ids))
                ]
                approval_rows = [
                    current_row(snapshot, binding["evidence_id"])
                    for binding in approvals
                ]
                if len({row.issuer for row in approval_rows}) < 2:
                    raise error_type("two distinct approval issuers required")
                destruction_authority = make_binding(
                    snapshot,
                    evidence_id=destruction_authority_evidence_id,
                    case_id=case_id,
                    object_id=object_id,
                    kind="DESTRUCTION_AUTHORITY",
                    decision="AUTHORIZED",
                    transition_at=now,
                )
                receipt = append_event(
                    item,
                    "DESTROYED",
                    actor=actor,
                    at=now,
                    data={
                        "original_sha256": original,
                        "authority_snapshot_root": snapshot_root(snapshot),
                        "retention": retention,
                        "notice": notice,
                        "approvals": approvals,
                        "destruction_authority": destruction_authority,
                    },
                )
                object_setattr(item, "destroyed", True)
                return receipt

            return mutate(evidence, operation)

        return Service(
            verify_current,
            submit_current,
            view_current,
            classify_current,
            accept_current,
            replace_original_current,
            set_hold_current,
            destroy_current,
        )

    return public_factory


CurrentCustodyService = _build_current_factory(
    Evidence,
    AuthoritySnapshot,
    AuthorityRecord,
    CustodyError,
    hashlib.sha256,
    json.JSONEncoder(
        sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode,
    datetime.fromisoformat,
    timezone.utc,
    object.__new__,
    object.__setattr__,
    object.__getattribute__,
)
del _build_current_factory
