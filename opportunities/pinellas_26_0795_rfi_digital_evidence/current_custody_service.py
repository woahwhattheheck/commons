from __future__ import annotations

import builtins
import hashlib
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
    fromisoformat,
    utc_zone,
    object_new,
    object_getattribute,
    builtins_module,
):
    # Capture every ordinary runtime primitive CURRENT depends on while the
    # private builder still exists. Later module-global rebinding cannot redirect
    # the public factory or already-created operation closures.
    type_ = builtins_module.type
    NoneType_ = type_(None)
    str_ = builtins_module.str
    int_ = builtins_module.int
    bool_ = builtins_module.bool
    bytes_ = builtins_module.bytes
    list_ = builtins_module.list
    tuple_ = builtins_module.tuple
    dict_ = builtins_module.dict
    set_ = builtins_module.set
    len_ = builtins_module.len
    sorted_ = builtins_module.sorted
    max_ = builtins_module.max
    any_ = builtins_module.any
    callable_ = builtins_module.callable
    getattr_ = builtins_module.getattr
    enumerate_ = builtins_module.enumerate
    ord_ = builtins_module.ord
    format_ = builtins_module.format
    ValueError_ = builtins_module.ValueError
    dict_setitem_ = dict_.__setitem__

    record_keys = {
        "evidence_id",
        "kind",
        "generation",
        "case_id",
        "object_id",
        "decision",
        "issuer",
        "at",
        "revoked",
    }
    evidence_keys = {
        "case_id",
        "object_id",
        "original_sha256",
        "accepted",
        "legal_hold",
        "destroyed",
        "events",
    }
    event_keys = {
        "seq",
        "case_id",
        "object_id",
        "kind",
        "actor",
        "at",
        "prev_hash",
        "data",
        "event_hash",
    }
    witness_keys = {
        "schema",
        "case_id",
        "object_id",
        "event_count",
        "head_event_hash",
        "state_sha256",
        "witness_sha256",
    }
    decisions = {
        "LEGAL_HOLD": {"ENABLED", "RELEASED"},
        "RETENTION_ELIGIBILITY": {"ELIGIBLE", "INELIGIBLE"},
        "NOTICE_COMPLETE": {"COMPLETE", "INCOMPLETE"},
        "APPROVAL": {"APPROVED", "DENIED"},
        "DESTRUCTION_AUTHORITY": {"AUTHORIZED", "DENIED"},
    }
    known_events = {
        "SUBMITTED",
        "VIEWED",
        "CLASSIFIED",
        "ACCEPTED_LOCKED",
        "ORIGINAL_REPLACED_PRE_ACCEPTANCE",
        "LEGAL_HOLD_CHANGED",
        "DESTROYED",
    }
    control_escapes = {
        "\b": "\\b",
        "\t": "\\t",
        "\n": "\\n",
        "\f": "\\f",
        "\r": "\\r",
        '"': '\\"',
        "\\": "\\\\",
    }

    def nonempty(value, label):
        if type_(value) is not str_ or not value.strip():
            raise error_type(f"{label} must be a non-empty string")
        return value

    def digest(value, label):
        if (
            type_(value) is not str_
            or len_(value) != 64
            or any_(ch not in "0123456789abcdef" for ch in value)
        ):
            raise error_type(f"{label} must be lowercase 64-hex sha256")
        return value

    def utc(text):
        if type_(text) is not str_ or not text.endswith("Z"):
            raise error_type("timestamp must use UTC Z form")
        try:
            dt = fromisoformat(text[:-1] + "+00:00")
        except ValueError_ as exc:
            raise error_type("invalid timestamp") from exc
        if dt.microsecond:
            raise error_type("timestamp must use whole seconds")
        normalized = dt.astimezone(utc_zone).strftime("%Y-%m-%dT%H:%M:%SZ")
        if normalized != text:
            raise error_type("timestamp must be canonical UTC Z form")
        return normalized

    def quote(text):
        if type_(text) is not str_:
            raise error_type("canonical JSON string required")
        parts = ['"']
        for ch in text:
            if ch in control_escapes:
                parts.append(control_escapes[ch])
                continue
            code = ord_(ch)
            if 0xD800 <= code <= 0xDFFF:
                raise error_type("canonical JSON rejects surrogate code points")
            if code < 0x20:
                parts.append("\\u" + format_(code, "04x"))
            else:
                parts.append(ch)
        parts.append('"')
        return "".join(parts)

    def canon_text(value):
        value_type = type_(value)
        if value_type is str_:
            return quote(value)
        if value_type is bool_:
            return "true" if value else "false"
        if value is None:
            return "null"
        if value_type is int_:
            if value < -(2**63) or value > 2**63 - 1:
                raise error_type("canonical integer outside supported range")
            return str_(value)
        if value_type is list_:
            return "[" + ",".join(canon_text(item) for item in value) + "]"
        if value_type is dict_:
            keys = list_(value)
            if any_(type_(key) is not str_ for key in keys):
                raise error_type("canonical JSON object keys must be strings")
            keys = sorted_(keys)
            return "{" + ",".join(
                quote(key) + ":" + canon_text(value[key]) for key in keys
            ) + "}"
        raise error_type("unsupported canonical JSON value")

    def canon(value):
        return canon_text(value).encode("utf-8")

    def sha(data):
        if type_(data) is not bytes_:
            raise error_type("sha256 input must be bytes")
        return sha256_func(data).hexdigest()

    def clone(value):
        value_type = type_(value)
        if value_type in (str_, int_, bool_, bytes_, NoneType_):
            return value
        if value_type is list_:
            return [clone(item) for item in value]
        if value_type is tuple_:
            return tuple_(clone(item) for item in value)
        if value_type is dict_:
            return {clone(key): clone(item) for key, item in value.items()}
        raise error_type("current custody value contains unsupported mutable type")

    def raw_dict(value, expected_type, label):
        if type_(value) is not expected_type:
            raise error_type(f"{label} type invalid")
        attrs = object_getattribute(value, "__dict__")
        if type_(attrs) is not dict_:
            raise error_type(f"{label} storage invalid")
        return attrs

    def put_raw(attrs, key, value):
        # attrs is already exact built-in dict storage. Captured dict.__setitem__
        # replaces existing raw slots without dispatching Evidence data descriptors.
        dict_setitem_(attrs, key, value)

    def record_body(row):
        attrs = raw_dict(row, record_type, "authority record")
        if set_(attrs) != record_keys:
            raise error_type("authority record storage invalid")
        evidence_id = nonempty(attrs["evidence_id"], "authority evidence_id")
        case_id = nonempty(attrs["case_id"], "authority case_id")
        object_id = nonempty(attrs["object_id"], "authority object_id")
        issuer = nonempty(attrs["issuer"], "authority issuer")
        generation = attrs["generation"]
        if type_(generation) is not int_ or generation < 1 or generation > 2**63 - 1:
            raise error_type("authority generation invalid")
        kind = attrs["kind"]
        decision = attrs["decision"]
        if type_(kind) is not str_ or kind not in decisions:
            raise error_type("authority kind invalid")
        if type_(decision) is not str_ or decision not in decisions[kind]:
            raise error_type("authority decision invalid for kind")
        revoked = attrs["revoked"]
        if type_(revoked) is not bool_:
            raise error_type("authority revoked must be boolean")
        at = utc(attrs["at"])
        return {
            "evidence_id": evidence_id,
            "kind": kind,
            "generation": generation,
            "case_id": case_id,
            "object_id": object_id,
            "decision": decision,
            "issuer": issuer,
            "at": at,
            "revoked": revoked,
        }

    def record_root(row):
        return sha(canon(record_body(row)))

    def snapshot_rows(snapshot):
        attrs = raw_dict(snapshot, snapshot_type, "authority snapshot")
        rows = attrs.get("_records")
        if type_(rows) is not tuple_ or not rows:
            raise error_type("authority snapshot rows unavailable")
        seen = set_()
        material = []
        for row in rows:
            body = record_body(row)
            key = (body["evidence_id"], body["generation"])
            if key in seen:
                raise error_type("duplicate authority evidence generation")
            seen.add(key)
            material.append((body, row, record_root(row)))
        material = sorted_(
            material,
            key=lambda item: (
                item[0]["evidence_id"],
                item[0]["generation"],
                item[2],
            ),
        )
        return tuple_(item[1] for item in material)

    def snapshot_root(snapshot):
        rows = snapshot_rows(snapshot)
        body = {
            "schema": "pinellas.authority-snapshot.v1",
            "records": [
                {"record": record_body(row), "record_root": record_root(row)}
                for row in rows
            ],
        }
        return sha(canon(body))

    def current_row(snapshot, evidence_id):
        evidence_id = nonempty(evidence_id, "authority evidence_id")
        candidates = []
        for row in snapshot_rows(snapshot):
            body = record_body(row)
            if body["evidence_id"] == evidence_id:
                candidates.append((body["generation"], row))
        if not candidates:
            raise error_type("authority evidence id absent from snapshot")
        return max_(candidates, key=lambda item: item[0])[1]

    def verify_binding(
        snapshot,
        binding,
        *,
        case_id,
        object_id,
        kind,
        decision,
        transition_at,
    ):
        transition_at = utc(transition_at)
        if type_(binding) is not dict_ or set_(binding) != {
            "evidence_id",
            "generation",
            "record_root",
        }:
            raise error_type("authority binding grammar invalid")
        evidence_id = nonempty(binding["evidence_id"], "authority binding evidence_id")
        generation = binding["generation"]
        if type_(generation) is not int_ or generation < 1 or generation > 2**63 - 1:
            raise error_type("authority binding generation invalid")
        digest(binding["record_root"], "authority binding record root")
        row = current_row(snapshot, evidence_id)
        body = record_body(row)
        if body["generation"] != generation or record_root(row) != binding["record_root"]:
            raise error_type("authority binding is stale or root-mismatched")
        if body["revoked"]:
            raise error_type("authority binding is revoked")
        if body["case_id"] != case_id or body["object_id"] != object_id:
            raise error_type("authority binding subject mismatch")
        if body["kind"] != kind or body["decision"] != decision:
            raise error_type("authority binding decision mismatch")
        if body["at"] > transition_at:
            raise error_type("future authority binding cannot authorize transition")
        return body

    def make_binding(
        snapshot,
        *,
        evidence_id,
        case_id,
        object_id,
        kind,
        decision,
        transition_at,
    ):
        row = current_row(snapshot, evidence_id)
        body = record_body(row)
        binding = {
            "evidence_id": body["evidence_id"],
            "generation": body["generation"],
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
        attrs = raw_dict(evidence, evidence_type, "evidence")
        if set_(attrs) != evidence_keys:
            raise error_type("Evidence state storage invalid")
        case_id = nonempty(attrs["case_id"], "case_id")
        object_id = nonempty(attrs["object_id"], "object_id")
        original = digest(attrs["original_sha256"], "current original digest")
        accepted = attrs["accepted"]
        legal_hold = attrs["legal_hold"]
        destroyed = attrs["destroyed"]
        events = attrs["events"]
        if any_(type_(value) is not bool_ for value in (accepted, legal_hold, destroyed)):
            raise error_type("state flags must be boolean")
        if type_(events) is not list_:
            raise error_type("events must be a list")
        return case_id, object_id, original, accepted, legal_hold, destroyed, events

    def new_evidence():
        candidate = object_new(evidence_type)
        attrs = object_getattribute(candidate, "__dict__")
        if type_(attrs) is not dict_ or attrs:
            raise error_type("new Evidence raw storage unavailable")
        return candidate, attrs

    def clone_evidence(evidence):
        case_id, object_id, original, accepted, legal_hold, destroyed, events = evidence_fields(evidence)
        candidate, attrs = new_evidence()
        put_raw(attrs, "case_id", case_id)
        put_raw(attrs, "object_id", object_id)
        put_raw(attrs, "original_sha256", original)
        put_raw(attrs, "accepted", accepted)
        put_raw(attrs, "legal_hold", legal_hold)
        put_raw(attrs, "destroyed", destroyed)
        put_raw(attrs, "events", clone(events))
        if set_(attrs) != evidence_keys:
            raise error_type("cloned Evidence raw storage invalid")
        return candidate

    def state_body(evidence):
        _, _, original, accepted, legal_hold, destroyed, _ = evidence_fields(evidence)
        return {
            "original_sha256": original,
            "accepted": accepted,
            "legal_hold": legal_hold,
            "destroyed": destroyed,
        }

    def witness(evidence):
        case_id, object_id, _, _, _, _, events = evidence_fields(evidence)
        state_sha256 = sha(canon(state_body(evidence)))
        head = "GENESIS"
        if events:
            if type_(events[-1]) is not dict_:
                raise error_type("event must be object")
            head = digest(events[-1].get("event_hash"), "head event hash")
        body = {
            "schema": "pinellas.custody-witness.v1",
            "case_id": case_id,
            "object_id": object_id,
            "event_count": len_(events),
            "head_event_hash": head,
            "state_sha256": state_sha256,
        }
        return {**body, "witness_sha256": sha(canon(body))}

    def validate_witness(value):
        if type_(value) is not dict_ or set_(value) != witness_keys:
            raise error_type("external custody witness grammar invalid")
        if value["schema"] != "pinellas.custody-witness.v1":
            raise error_type("external custody witness schema invalid")
        nonempty(value["case_id"], "witness case_id")
        nonempty(value["object_id"], "witness object_id")
        count = value["event_count"]
        if type_(count) is not int_ or count < 1 or count > 2**63 - 1:
            raise error_type("witness event count invalid")
        digest(value["head_event_hash"], "witness head event hash")
        digest(value["state_sha256"], "witness state digest")
        digest(value["witness_sha256"], "witness digest")
        body = {key: value[key] for key in witness_keys if key != "witness_sha256"}
        if sha(canon(body)) != value["witness_sha256"]:
            raise error_type("external custody witness digest mismatch")
        return value

    def publication_values(candidate):
        case_id, object_id, original, accepted, legal_hold, destroyed, events = evidence_fields(candidate)
        return {
            "case_id": case_id,
            "object_id": object_id,
            "original_sha256": original,
            "accepted": accepted,
            "legal_hold": legal_hold,
            "destroyed": destroyed,
            "events": clone(events),
        }

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
        current_time = getattr_(provider, "current_time_utc", None)
        retained_witness = getattr_(provider, "retained_custody_witness", None)
        compare_and_retain = getattr_(provider, "compare_and_retain_custody_witness", None)
        current_snapshot = getattr_(provider, "current_authority_snapshot", None)
        archived_snapshot = getattr_(provider, "archived_authority_snapshot", None)
        if any_(
            not callable_(method)
            for method in (
                current_time,
                retained_witness,
                compare_and_retain,
                current_snapshot,
                archived_snapshot,
            )
        ):
            raise error_type("host trust provider contract incomplete")

        def trusted_now():
            return utc(current_time())

        def identity(evidence):
            case_id, object_id, *_ = evidence_fields(evidence)
            return case_id, object_id

        def resolve_archived(case_id, object_id, root, cache):
            root = digest(root, "authority snapshot root")
            if root not in cache:
                snapshot = archived_snapshot(case_id, object_id, root)
                if type_(snapshot) is not snapshot_type or snapshot_root(snapshot) != root:
                    raise error_type(
                        "host archived authority snapshot unavailable or root-mismatched"
                    )
                cache[root] = snapshot
            return cache[root]

        def verify_against(evidence, expected_witness, now):
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
            snapshots = {}

            for i, event in enumerate_(events, 1):
                if type_(event) is not dict_ or set_(event) != event_keys:
                    raise error_type("event grammar invalid")
                if type_(event["seq"]) is not int_ or event["seq"] != i:
                    raise error_type("event sequence invalid")
                if event["case_id"] != case_id or event["object_id"] != object_id:
                    raise error_type("event identity mismatch")
                kind = event["kind"]
                if type_(kind) is not str_ or kind not in known_events:
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
                if type_(event["data"]) is not dict_:
                    raise error_type("event data must be object")
                digest(event["event_hash"], "event hash")
                body = {key: event[key] for key in event_keys if key != "event_hash"}
                if sha(canon(body)) != event["event_hash"]:
                    raise error_type("event hash mismatch")

                data = event["data"]
                if i == 1 and kind != "SUBMITTED":
                    raise error_type("first event must be SUBMITTED")
                if kind == "SUBMITTED":
                    if i != 1 or set_(data) != {"sha256", "size"}:
                        raise error_type("SUBMITTED event invalid")
                    derived_original = digest(data["sha256"], "submitted digest")
                    if type_(data["size"]) is not int_ or data["size"] < 0:
                        raise error_type("submitted size invalid")
                elif kind == "ORIGINAL_REPLACED_PRE_ACCEPTANCE":
                    if derived_accepted or derived_destroyed:
                        raise error_type("replacement after acceptance/destruction")
                    if (
                        set_(data) != {"old_sha256", "new_sha256", "size"}
                        or data["old_sha256"] != derived_original
                    ):
                        raise error_type("replacement lineage invalid")
                    digest(data["old_sha256"], "replacement old digest")
                    derived_original = digest(data["new_sha256"], "replacement new digest")
                    if type_(data["size"]) is not int_ or data["size"] < 0:
                        raise error_type("replacement size invalid")
                elif kind == "ACCEPTED_LOCKED":
                    if derived_accepted or derived_destroyed:
                        raise error_type("duplicate/late acceptance")
                    if set_(data) != {"sha256"} or data["sha256"] != derived_original:
                        raise error_type("acceptance digest mismatch")
                    digest(data["sha256"], "acceptance digest")
                    derived_accepted = True
                elif kind == "LEGAL_HOLD_CHANGED":
                    if derived_destroyed:
                        raise error_type("hold event after destruction")
                    if (
                        set_(data)
                        != {"enabled", "authority_snapshot_root", "authority"}
                        or type_(data["enabled"]) is not bool_
                        or data["enabled"] == derived_hold
                    ):
                        raise error_type("hold event invalid")
                    root = digest(data["authority_snapshot_root"], "authority snapshot root")
                    snapshot = resolve_archived(case_id, object_id, root, snapshots)
                    verify_binding(
                        snapshot,
                        data["authority"],
                        case_id=case_id,
                        object_id=object_id,
                        kind="LEGAL_HOLD",
                        decision="ENABLED" if data["enabled"] else "RELEASED",
                        transition_at=at,
                    )
                    derived_hold = data["enabled"]
                elif kind == "DESTROYED":
                    if not derived_accepted or derived_hold or derived_destroyed:
                        raise error_type("destruction state invalid")
                    if set_(data) != {
                        "original_sha256",
                        "authority_snapshot_root",
                        "retention",
                        "notice",
                        "approvals",
                        "destruction_authority",
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
                    if type_(approvals) is not list_ or len_(approvals) < 2:
                        raise error_type("destruction approvals invalid")
                    approval_bodies = [
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
                    canonical_approvals = sorted_(
                        approvals,
                        key=lambda binding: (
                            binding.get("evidence_id", "") if type_(binding) is dict_ else "",
                            binding.get("generation", 0) if type_(binding) is dict_ else 0,
                            binding.get("record_root", "") if type_(binding) is dict_ else "",
                        ),
                    )
                    if approvals != canonical_approvals:
                        raise error_type("destruction approvals must be canonical")
                    if len_(set_(body["evidence_id"] for body in approval_bodies)) != len_(approval_bodies):
                        raise error_type("destruction approval identities must be distinct")
                    if len_(set_(body["issuer"] for body in approval_bodies)) < 2:
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
                        or set_(data) != {"purpose"}
                        or type_(data["purpose"]) is not str_
                        or not data["purpose"].strip()
                    ):
                        raise error_type("view event invalid")
                elif kind == "CLASSIFIED":
                    if (
                        derived_destroyed
                        or set_(data) != {"status", "confidential"}
                        or type_(data["status"]) is not str_
                        or not data["status"].strip()
                        or type_(data["confidential"]) is not bool_
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
                "event_count": len_(events),
                "head_event_hash": prev,
                "accepted": current_accepted,
                "legal_hold": current_hold,
                "destroyed": current_destroyed,
                "witness_sha256": current_witness["witness_sha256"],
            }

        def append_event(evidence, kind, *, actor, at, data=None):
            case_id, object_id, _, _, _, destroyed, events = evidence_fields(evidence)
            if destroyed:
                raise error_type("destroyed evidence cannot receive lifecycle events")
            nonempty(actor, "actor")
            at = utc(at)
            if events and at < utc(events[-1]["at"]):
                raise error_type("event timestamp cannot move backwards")
            prev_hash = events[-1]["event_hash"] if events else "GENESIS"
            body = {
                "seq": len_(events) + 1,
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

        def preflight_publication(target, candidate):
            target_attrs = raw_dict(target, evidence_type, "evidence")
            if set_(target_attrs) != evidence_keys:
                raise error_type("target Evidence raw storage invalid")
            values = publication_values(candidate)
            if set_(values) != evidence_keys:
                raise error_type("successor publication shape invalid")
            if object_getattribute(target, "__dict__") is not target_attrs:
                raise error_type("target Evidence raw storage changed")
            return target_attrs, values

        def publish_raw(target_attrs, values):
            # All seven keys already exist in target_attrs, and both operands are
            # exact built-in dicts. This path cannot dispatch Evidence descriptors.
            for key in evidence_keys:
                put_raw(target_attrs, key, values[key])

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
            target_attrs, values = preflight_publication(evidence, candidate)
            advance(candidate, expected, now)
            publish_raw(target_attrs, values)
            return clone(result)

        def submit_current(*, case_id, object_id, original, actor):
            case_id = nonempty(case_id, "case_id")
            object_id = nonempty(object_id, "object_id")
            actor = nonempty(actor, "actor")
            if type_(original) is not bytes_:
                raise error_type("original must be bytes")
            now = trusted_now()
            candidate, attrs = new_evidence()
            put_raw(attrs, "case_id", case_id)
            put_raw(attrs, "object_id", object_id)
            put_raw(attrs, "original_sha256", sha(original))
            put_raw(attrs, "accepted", False)
            put_raw(attrs, "legal_hold", False)
            put_raw(attrs, "destroyed", False)
            put_raw(attrs, "events", [])
            if set_(attrs) != evidence_keys:
                raise error_type("submitted Evidence raw storage invalid")
            append_event(
                candidate,
                "SUBMITTED",
                actor=actor,
                at=now,
                data={"sha256": sha(original), "size": len_(original)},
            )
            advance(candidate, None, now)
            return candidate

        def view_current(evidence, *, actor, purpose):
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

        def classify_current(evidence, *, actor, status, confidential):
            nonempty(status, "status")
            if type_(confidential) is not bool_:
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

        def accept_current(evidence, *, actor):
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
                put_raw(raw_dict(item, evidence_type, "evidence"), "accepted", True)

            mutate(evidence, operation)

        def replace_original_current(evidence, *, new_bytes, actor):
            if type_(new_bytes) is not bytes_:
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
                        "size": len_(new_bytes),
                    },
                )
                put_raw(raw_dict(item, evidence_type, "evidence"), "original_sha256", new_sha)

            mutate(evidence, operation)

        def current_snapshot_for(evidence):
            case_id, object_id = identity(evidence)
            snapshot = current_snapshot(case_id, object_id)
            if type_(snapshot) is not snapshot_type:
                raise error_type("host current authority snapshot unavailable")
            snapshot_root(snapshot)
            return snapshot

        def set_hold_current(evidence, *, actor, authority_evidence_id):
            def operation(item, now):
                case_id, object_id, _, _, hold, _, _ = evidence_fields(item)
                snapshot = current_snapshot_for(item)
                row = current_row(snapshot, authority_evidence_id)
                body = record_body(row)
                if body["kind"] != "LEGAL_HOLD" or body["decision"] not in {
                    "ENABLED",
                    "RELEASED",
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
                put_raw(raw_dict(item, evidence_type, "evidence"), "legal_hold", enabled)

            mutate(evidence, operation)

        def destroy_current(
            evidence,
            *,
            actor,
            retention_evidence_id,
            notice_evidence_id,
            approval_evidence_ids,
            destruction_authority_evidence_id,
        ):
            def operation(item, now):
                case_id, object_id, original, accepted, hold, destroyed, _ = evidence_fields(item)
                if not accepted:
                    raise error_type("only accepted evidence can enter destruction workflow")
                if hold:
                    raise error_type("legal hold blocks destruction")
                if destroyed:
                    raise error_type("evidence already destroyed")
                if (
                    type_(approval_evidence_ids) is not list_
                    or any_(
                        type_(value) is not str_ or not value.strip()
                        for value in approval_evidence_ids
                    )
                    or len_(set_(approval_evidence_ids)) < 2
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
                    for evidence_id in sorted_(set_(approval_evidence_ids))
                ]
                approval_issuers = {
                    record_body(current_row(snapshot, binding["evidence_id"]))["issuer"]
                    for binding in approvals
                }
                if len_(approval_issuers) < 2:
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
                put_raw(raw_dict(item, evidence_type, "evidence"), "destroyed", True)
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
    datetime.fromisoformat,
    timezone.utc,
    object.__new__,
    object.__getattribute__,
    builtins,
)
del _build_current_factory
