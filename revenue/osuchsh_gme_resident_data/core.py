"""Deterministic, data-free GME resident administration prototype.

This module intentionally avoids clinical decision support. It demonstrates the hard
systems boundaries that matter for migrating spreadsheet/ancillary-system resident
administration data: strict parsing, conflict detection, least privilege, stale-write
rejection, tamper-evident mutation history, and aggregate-only analytics export.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
from collections import Counter
from dataclasses import dataclass
from typing import Any, Iterable, Mapping


class DataError(ValueError):
    """Input is malformed or outside the administrative data contract."""


class ConflictError(DataError):
    """Migration or mutation would silently discard conflicting authority."""


class PermissionDenied(DataError):
    """Role is not authorized for the requested data operation."""


class StaleWriteError(DataError):
    """Optimistic concurrency precondition does not match current state."""


class AuditError(DataError):
    """Audit chain verification failed."""


_ID_RE = re.compile(r"^[A-Z0-9][A-Z0-9_-]{2,31}$")
_EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

ALLOWED_FIELDS = frozenset(
    {
        "resident_id",
        "first_name",
        "last_name",
        "email",
        "program",
        "pgy_level",
        "start_date",
        "expected_end_date",
        "training_status",
        "license_status",
        "coordinator_notes",
    }
)
DIRECT_IDENTIFIERS = frozenset({"resident_id", "first_name", "last_name", "email"})

ROLE_VIEW_FIELDS = {
    "admin": ALLOWED_FIELDS,
    "coordinator": ALLOWED_FIELDS,
    "program_director": ALLOWED_FIELDS - {"coordinator_notes"},
    "resident_self": frozenset(
        {
            "resident_id",
            "first_name",
            "last_name",
            "email",
            "program",
            "pgy_level",
            "start_date",
            "expected_end_date",
            "training_status",
            "license_status",
        }
    ),
    "auditor": frozenset(
        {
            "program",
            "pgy_level",
            "start_date",
            "expected_end_date",
            "training_status",
            "license_status",
        }
    ),
}

ROLE_WRITE_FIELDS = {
    "admin": ALLOWED_FIELDS - {"resident_id"},
    "coordinator": frozenset(
        {
            "first_name",
            "last_name",
            "email",
            "program",
            "pgy_level",
            "start_date",
            "expected_end_date",
            "training_status",
            "license_status",
            "coordinator_notes",
        }
    ),
    "program_director": frozenset({"program", "pgy_level", "training_status"}),
    "resident_self": frozenset(),
    "auditor": frozenset(),
}

_REQUIRED_FIELDS = frozenset(
    {
        "resident_id",
        "first_name",
        "last_name",
        "email",
        "program",
        "pgy_level",
        "start_date",
        "expected_end_date",
        "training_status",
        "license_status",
    }
)


def _reject_constant(value: str) -> None:
    raise DataError(f"non-finite JSON number rejected: {value}")


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise DataError("duplicate JSON key rejected")
        out[key] = value
    return out


def _validate_unicode(value: Any, path: str = "$") -> None:
    if isinstance(value, str):
        for char in value:
            code = ord(char)
            if 0xD800 <= code <= 0xDFFF:
                raise DataError(f"non-scalar Unicode rejected at {path}")
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _validate_unicode(item, f"{path}[{index}]")
        return
    if isinstance(value, dict):
        for key, item in value.items():
            _validate_unicode(key, f"{path}.<key>")
            _validate_unicode(item, f"{path}.{key}")


def strict_json_loads(text: str) -> Any:
    if not isinstance(text, str):
        raise DataError("JSON input must be text")
    try:
        value = json.loads(
            text,
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_constant,
        )
    except DataError:
        raise
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        raise DataError("invalid JSON") from exc
    _validate_unicode(value)
    return value


def canonical_bytes(value: Any) -> bytes:
    _validate_unicode(value)
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError, UnicodeError) as exc:
        raise DataError("value is not canonical-JSON encodable") from exc


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _require_text(name: str, value: Any, *, max_len: int) -> str:
    if not isinstance(value, str):
        raise DataError(f"{name} must be text")
    _validate_unicode(value, f"$.{name}")
    value = value.strip()
    if not value or len(value) > max_len:
        raise DataError(f"{name} length invalid")
    return value


def validate_record(record: Mapping[str, Any], *, require_all: bool = True) -> dict[str, Any]:
    if not isinstance(record, Mapping):
        raise DataError("resident record must be an object")
    unknown = set(record) - ALLOWED_FIELDS
    if unknown:
        raise DataError(f"unknown resident fields: {sorted(unknown)}")
    if require_all:
        missing = _REQUIRED_FIELDS - set(record)
        if missing:
            raise DataError(f"missing required resident fields: {sorted(missing)}")

    out = dict(record)
    if "resident_id" in out:
        rid = _require_text("resident_id", out["resident_id"], max_len=32).upper()
        if not _ID_RE.fullmatch(rid):
            raise DataError("resident_id format invalid")
        out["resident_id"] = rid
    for field in ("first_name", "last_name", "program"):
        if field in out:
            out[field] = _require_text(field, out[field], max_len=120)
    if "email" in out:
        email = _require_text("email", out["email"], max_len=254).lower()
        if not _EMAIL_RE.fullmatch(email):
            raise DataError("email format invalid")
        out["email"] = email
    if "pgy_level" in out:
        level = out["pgy_level"]
        if type(level) is not int or not 1 <= level <= 12:
            raise DataError("pgy_level must be integer 1..12")
    for field in ("start_date", "expected_end_date"):
        if field in out:
            value = _require_text(field, out[field], max_len=10)
            if not _DATE_RE.fullmatch(value):
                raise DataError(f"{field} must be YYYY-MM-DD")
            out[field] = value
    if "training_status" in out:
        status = _require_text("training_status", out["training_status"], max_len=32).upper()
        if status not in {"ACTIVE", "LEAVE", "COMPLETED", "WITHDRAWN"}:
            raise DataError("training_status invalid")
        out["training_status"] = status
    if "license_status" in out:
        status = _require_text("license_status", out["license_status"], max_len=32).upper()
        if status not in {"CURRENT", "PENDING", "EXPIRED", "NOT_REQUIRED"}:
            raise DataError("license_status invalid")
        out["license_status"] = status
    if "coordinator_notes" in out:
        note = out["coordinator_notes"]
        if note is None:
            out["coordinator_notes"] = ""
        else:
            out["coordinator_notes"] = _require_text("coordinator_notes", note, max_len=2000)

    if "start_date" in out and "expected_end_date" in out:
        if out["expected_end_date"] < out["start_date"]:
            raise DataError("expected_end_date precedes start_date")
    return out


@dataclass(frozen=True)
class MigrationPlan:
    records: tuple[dict[str, Any], ...]
    conflicts: tuple[dict[str, Any], ...]
    source_rows: int
    plan_digest: str

    @property
    def status(self) -> str:
        return "READY" if not self.conflicts else "CONFLICTS_PRESENT"


def compile_migration(rows: Iterable[Mapping[str, Any]]) -> MigrationPlan:
    """Compile source-tagged rows into a deterministic, conflict-explicit plan.

    Each input row must have `source`, `row`, and `record`. Missing values may be
    supplied by another source. Divergent non-empty values for the same resident/field
    become explicit conflicts; no source wins by ordering.
    """

    normalized: list[dict[str, Any]] = []
    for item in rows:
        if not isinstance(item, Mapping) or set(item) != {"source", "row", "record"}:
            raise DataError("migration row keys must be exactly source,row,record")
        source = _require_text("source", item["source"], max_len=200)
        row_no = item["row"]
        if type(row_no) is not int or row_no < 1:
            raise DataError("migration row must be a positive integer")
        record = validate_record(item["record"], require_all=False)
        if "resident_id" not in record:
            raise DataError("migration record requires resident_id")
        normalized.append({"source": source, "row": row_no, "record": record})

    normalized.sort(key=lambda x: (x["record"]["resident_id"], x["source"], x["row"]))
    by_resident: dict[str, list[dict[str, Any]]] = {}
    for row in normalized:
        by_resident.setdefault(row["record"]["resident_id"], []).append(row)

    output_records: list[dict[str, Any]] = []
    conflicts: list[dict[str, Any]] = []
    for resident_id in sorted(by_resident):
        rows_for_resident = by_resident[resident_id]
        merged: dict[str, Any] = {"resident_id": resident_id}
        conflicted_fields: set[str] = set()
        for field in sorted(ALLOWED_FIELDS - {"resident_id"}):
            values: dict[str, list[dict[str, Any]]] = {}
            for row in rows_for_resident:
                if field not in row["record"]:
                    continue
                value = row["record"][field]
                key = canonical_bytes(value).decode("utf-8")
                values.setdefault(key, []).append(
                    {"source": row["source"], "row": row["row"], "value": value}
                )
            if not values:
                continue
            if len(values) > 1:
                conflicted_fields.add(field)
                evidence = []
                for key in sorted(values):
                    evidence.extend(sorted(values[key], key=lambda x: (x["source"], x["row"])))
                conflicts.append(
                    {
                        "resident_id": resident_id,
                        "field": field,
                        "evidence": evidence,
                    }
                )
            else:
                merged[field] = next(iter(values.values()))[0]["value"]
        if not conflicted_fields:
            output_records.append(validate_record(merged, require_all=True))

    plan_body = {
        "records": output_records,
        "conflicts": conflicts,
        "source_rows": len(normalized),
    }
    return MigrationPlan(
        records=tuple(copy.deepcopy(output_records)),
        conflicts=tuple(copy.deepcopy(conflicts)),
        source_rows=len(normalized),
        plan_digest=digest(plan_body),
    )


class ResidentStore:
    """Small deterministic administration store with CAS and hash-chained audit."""

    def __init__(self) -> None:
        self._records: dict[str, dict[str, Any]] = {}
        self._versions: dict[str, int] = {}
        self._audit: list[dict[str, Any]] = []

    def _append_audit(
        self,
        *,
        action: str,
        actor_role: str,
        resident_id: str,
        before_version: int,
        after_version: int,
        changes: Mapping[str, Any],
    ) -> dict[str, Any]:
        prev_hash = self._audit[-1]["event_hash"] if self._audit else "0" * 64
        payload = {
            "seq": len(self._audit) + 1,
            "action": action,
            "actor_role": actor_role,
            "resident_id": resident_id,
            "before_version": before_version,
            "after_version": after_version,
            "changes_digest": digest(dict(changes)),
            "prev_hash": prev_hash,
        }
        event = {**payload, "event_hash": digest(payload)}
        self._audit.append(event)
        return copy.deepcopy(event)

    def apply_migration(self, plan: MigrationPlan, *, actor_role: str = "admin") -> dict[str, Any]:
        if actor_role != "admin":
            raise PermissionDenied("only admin may apply a compiled migration")
        if plan.conflicts:
            raise ConflictError("migration plan contains unresolved conflicts")
        if self._records:
            raise ConflictError("initial migration requires an empty store")
        for record in plan.records:
            rid = record["resident_id"]
            if rid in self._records:
                raise ConflictError("duplicate resident in migration")
            self._records[rid] = copy.deepcopy(record)
            self._versions[rid] = 1
            self._append_audit(
                action="MIGRATE_CREATE",
                actor_role=actor_role,
                resident_id=rid,
                before_version=0,
                after_version=1,
                changes=record,
            )
        return self.receipt()

    def view(self, resident_id: str, *, role: str, self_resident_id: str | None = None) -> dict[str, Any]:
        rid = _require_text("resident_id", resident_id, max_len=32).upper()
        if role not in ROLE_VIEW_FIELDS:
            raise PermissionDenied("unknown role")
        if role == "resident_self" and self_resident_id != rid:
            raise PermissionDenied("resident_self may view only own record")
        if rid not in self._records:
            raise DataError("resident not found")
        fields = ROLE_VIEW_FIELDS[role]
        return {
            "resident": {k: copy.deepcopy(v) for k, v in self._records[rid].items() if k in fields},
            "version": self._versions[rid],
        }

    def update(
        self,
        resident_id: str,
        *,
        expected_version: int,
        patch: Mapping[str, Any],
        actor_role: str,
    ) -> dict[str, Any]:
        rid = _require_text("resident_id", resident_id, max_len=32).upper()
        if rid not in self._records:
            raise DataError("resident not found")
        if type(expected_version) is not int or expected_version < 1:
            raise DataError("expected_version must be a positive integer")
        if self._versions[rid] != expected_version:
            raise StaleWriteError("stale resident version")
        if actor_role not in ROLE_WRITE_FIELDS:
            raise PermissionDenied("unknown role")
        if not isinstance(patch, Mapping) or not patch:
            raise DataError("patch must be a non-empty object")
        if "resident_id" in patch:
            raise DataError("resident_id is immutable")
        unauthorized = set(patch) - ROLE_WRITE_FIELDS[actor_role]
        if unauthorized:
            raise PermissionDenied(f"role cannot write fields: {sorted(unauthorized)}")
        clean_patch = validate_record(patch, require_all=False)
        candidate = {**self._records[rid], **clean_patch}
        candidate = validate_record(candidate, require_all=True)
        if candidate == self._records[rid]:
            raise DataError("no-op update rejected")
        before = self._versions[rid]
        after = before + 1
        self._records[rid] = candidate
        self._versions[rid] = after
        event = self._append_audit(
            action="UPDATE",
            actor_role=actor_role,
            resident_id=rid,
            before_version=before,
            after_version=after,
            changes=clean_patch,
        )
        return {"resident_id": rid, "version": after, "event_hash": event["event_hash"]}

    def analytics_export(self, *, role: str) -> dict[str, Any]:
        if role not in {"admin", "auditor", "program_director"}:
            raise PermissionDenied("role cannot export analytics")
        by_program = Counter(record["program"] for record in self._records.values())
        by_pgy = Counter(str(record["pgy_level"]) for record in self._records.values())
        by_status = Counter(record["training_status"] for record in self._records.values())
        result = {
            "record_count": len(self._records),
            "by_program": dict(sorted(by_program.items())),
            "by_pgy_level": dict(sorted(by_pgy.items())),
            "by_training_status": dict(sorted(by_status.items())),
        }
        if any(key in result for key in DIRECT_IDENTIFIERS):
            raise DataError("direct identifier escaped analytics boundary")
        return result

    def audit_events(self, *, role: str) -> tuple[dict[str, Any], ...]:
        if role not in {"admin", "auditor"}:
            raise PermissionDenied("role cannot read audit events")
        return tuple(copy.deepcopy(self._audit))

    def verify_audit(self, events: Iterable[Mapping[str, Any]] | None = None) -> bool:
        candidate = list(copy.deepcopy(self._audit if events is None else list(events)))
        prev_hash = "0" * 64
        for expected_seq, event in enumerate(candidate, start=1):
            required = {
                "seq",
                "action",
                "actor_role",
                "resident_id",
                "before_version",
                "after_version",
                "changes_digest",
                "prev_hash",
                "event_hash",
            }
            if set(event) != required:
                raise AuditError("audit event shape invalid")
            if event["seq"] != expected_seq or event["prev_hash"] != prev_hash:
                raise AuditError("audit sequence/link invalid")
            if not isinstance(event["changes_digest"], str) or not _SHA256_RE.fullmatch(event["changes_digest"]):
                raise AuditError("audit changes digest invalid")
            payload = {k: event[k] for k in required - {"event_hash"}}
            expected_hash = digest(payload)
            if event["event_hash"] != expected_hash:
                raise AuditError("audit event hash invalid")
            prev_hash = expected_hash
        return True

    def receipt(self) -> dict[str, Any]:
        self.verify_audit()
        record_snapshot = [
            {"resident_id": rid, "version": self._versions[rid], "record": self._records[rid]}
            for rid in sorted(self._records)
        ]
        return {
            "schema": "osuchsh-gme-resident-data-receipt-v1",
            "record_count": len(record_snapshot),
            "records_digest": digest(record_snapshot),
            "audit_event_count": len(self._audit),
            "audit_head": self._audit[-1]["event_hash"] if self._audit else "0" * 64,
            "audit_valid": True,
            "clinical_decision_support": False,
            "live_osu_data_used": False,
        }
