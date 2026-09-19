#!/usr/bin/env python3
"""UIOWA-108 -- the contractor-transition scenario packet: schema and guards.

Two guards live here, and both exist because of the same sentence in the work
order: the example must distinguish completed access changes, unresolved
ownership and missing evidence *"without inserting real account data."*

  * The REALISM GUARD refuses any identifier that could be mistaken for a real
    account.  A contractor-transition packet is precisely where real-looking
    account data leaks into a deliverable -- a plausible NetID, a real-looking
    university address, a service-account name that might actually exist.  The
    guard is a hard refusal, not a naming convention, and test_transition.py
    feeds it real-looking data and asserts it goes red.  A guard that has
    never failed is worth nothing.

  * REFERENTIAL INTEGRITY refuses a packet whose records point at each other
    incorrectly.  A dangling owner reference is not a row to skip; it is the
    reason a handoff report says "complete" about something nobody owns.

Everything in this lane is FICTIONAL.  Identifiers follow SYN-<KIND>-<NNN>,
addresses sit under the reserved `.invalid` top-level domain (RFC 2606, which
can never resolve to a real host), and account names are prefixed `syn-`.
Join keys (service ESS/RIS/IAM, `synthetic: true`,
`authority: FICTIONAL_REHEARSAL_ONLY`) match the collection landed for
UIOWA-091 so this packet is readable by the same tools.
"""

import re

AUTHORITY = "FICTIONAL_REHEARSAL_ONLY"
SERVICES = ("ESS", "RIS", "IAM")

# An identifier that could not be mistaken for a real one.
SYNTHETIC_ID = re.compile(r"^SYN-[A-Z]+-\d{3}$")

# RFC 2606 reserves .invalid precisely so it can never resolve.  Any other
# top-level domain in a deliverable is an address somebody might actually try.
SAFE_EMAIL = re.compile(r"^[a-z0-9][a-z0-9._-]*@[a-z0-9.-]+\.invalid$")

# Account names must announce themselves as fictional.  A bare `jsmith` or
# `svc-payments` is exactly the shape of a real account.
SAFE_ACCOUNT = re.compile(r"^syn-[a-z0-9-]+$")

# Nine consecutive digits is the shape of a university ID number.  Refusing it
# outright is cheap; explaining one in a delivered packet is not.
ID_NUMBER_SHAPE = re.compile(r"\d{9}")

EMAIL_SHAPE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")

EMPLOYMENT_TYPES = ("staff", "contractor")

# What a transition item can be.
SUBJECT_KINDS = ("application", "service_identity", "runbook")

ACCESS_ACTIONS = ("REASSIGN_OWNER", "REVOKE_ACCESS", "ROTATE_CREDENTIAL", "UPDATE_RUNBOOK")
ACCESS_STATUSES = ("COMPLETED", "REQUESTED", "IN_PROGRESS")

SAFETY_CODES = (
    "REAL_LOOKING_EMAIL",
    "REAL_LOOKING_ACCOUNT_NAME",
    "POSSIBLE_REAL_ID_NUMBER",
    "IDENTIFIER_NOT_MARKED_SYNTHETIC",
    "RECORD_NOT_MARKED_SYNTHETIC",
)

INTEGRITY_CODES = (
    "DANGLING_REFERENCE",
    "DUPLICATE_RECORD_ID",
    "UNKNOWN_VOCABULARY_VALUE",
    "MISSING_REQUIRED_FIELD",
)


class PacketIssue(object):
    __slots__ = ("record_id", "code", "field", "detail")

    def __init__(self, record_id, code, field, detail):
        assert code in SAFETY_CODES + INTEGRITY_CODES, code
        self.record_id = record_id
        self.code = code
        self.field = field
        self.detail = detail

    @property
    def is_safety(self):
        return self.code in SAFETY_CODES

    def as_dict(self):
        return {
            "record_id": self.record_id,
            "code": self.code,
            "field": self.field,
            "detail": self.detail,
            "class": "SAFETY" if self.is_safety else "INTEGRITY",
        }

    def __repr__(self):  # pragma: no cover - debugging aid
        return "PacketIssue(%s,%s,%s)" % (self.record_id, self.code, self.field)


def check_realism(record_id, record):
    """Refuse anything in this record that could be mistaken for real account
    data.  Returns a list of PacketIssue."""
    issues = []

    if record.get("synthetic") is not True:
        issues.append(
            PacketIssue(record_id, "RECORD_NOT_MARKED_SYNTHETIC", "synthetic",
                        "every record in a delivered packet must declare itself fictional")
        )

    rid = record.get("id")
    if isinstance(rid, str) and not SYNTHETIC_ID.match(rid):
        issues.append(
            PacketIssue(record_id, "IDENTIFIER_NOT_MARKED_SYNTHETIC", "id",
                        "expected SYN-<KIND>-<NNN>, got %r" % rid)
        )

    for field, value in sorted(record.items()):
        if not isinstance(value, str):
            continue
        if ID_NUMBER_SHAPE.search(value):
            issues.append(
                PacketIssue(record_id, "POSSIBLE_REAL_ID_NUMBER", field,
                            "a nine-digit run is the shape of a real university ID")
            )
        for found in EMAIL_SHAPE.findall(value):
            if not SAFE_EMAIL.match(found):
                issues.append(
                    PacketIssue(record_id, "REAL_LOOKING_EMAIL", field,
                                "%r is deliverable-unsafe; fictional addresses must sit under .invalid" % found)
                )
        if field == "account_name" and not SAFE_ACCOUNT.match(value):
            issues.append(
                PacketIssue(record_id, "REAL_LOOKING_ACCOUNT_NAME", field,
                            "%r has the shape of a real account; fictional accounts are prefixed syn-" % value)
            )
    return issues


def _require(record_id, record, fields, issues):
    for field in fields:
        value = record.get(field)
        if value is None or (isinstance(value, str) and not value.strip()):
            issues.append(
                PacketIssue(record_id, "MISSING_REQUIRED_FIELD", field, "required field is empty")
            )


def validate_packet(packet):
    """Validate one scenario packet. Returns (issues, index).

    `index` maps every record id to (kind, record) so the classifier can
    resolve references without re-walking the packet.
    """
    issues = []
    index = {}

    sections = (
        ("people", ("id", "role", "employment_type", "service")),
        ("applications", ("id", "name", "owner_ref", "service")),
        ("service_identities", ("id", "account_name", "owner_ref", "service")),
        ("runbooks", ("id", "title", "owner_ref", "service")),
        ("access_changes", ("id", "subject_ref", "target_ref", "action", "status")),
    )

    for kind, required in sections:
        for record in packet.get(kind, []) or []:
            if not isinstance(record, dict):
                issues.append(PacketIssue("<unreadable>", "MISSING_REQUIRED_FIELD", kind,
                                          "record is not an object"))
                continue
            rid = record.get("id") or "<missing id>"
            if rid in index:
                issues.append(PacketIssue(rid, "DUPLICATE_RECORD_ID", "id",
                                          "id already used by a %s record" % index[rid][0]))
            else:
                index[rid] = (kind, record)
            _require(rid, record, required, issues)
            issues.extend(check_realism(rid, record))

            service = record.get("service")
            if service is not None and service not in SERVICES:
                issues.append(PacketIssue(rid, "UNKNOWN_VOCABULARY_VALUE", "service",
                                          "expected one of %s, got %r" % (list(SERVICES), service)))
            if kind == "people":
                et = record.get("employment_type")
                if et is not None and et not in EMPLOYMENT_TYPES:
                    issues.append(PacketIssue(rid, "UNKNOWN_VOCABULARY_VALUE", "employment_type",
                                              "expected one of %s, got %r" % (list(EMPLOYMENT_TYPES), et)))
            if kind == "access_changes":
                action = record.get("action")
                if action is not None and action not in ACCESS_ACTIONS:
                    issues.append(PacketIssue(rid, "UNKNOWN_VOCABULARY_VALUE", "action",
                                              "expected one of %s, got %r" % (list(ACCESS_ACTIONS), action)))
                status = record.get("status")
                if status is not None and status not in ACCESS_STATUSES:
                    issues.append(PacketIssue(rid, "UNKNOWN_VOCABULARY_VALUE", "status",
                                              "expected one of %s, got %r" % (list(ACCESS_STATUSES), status)))

    # Referential integrity, once every id is known.
    ref_fields = ("owner_ref", "successor_ref", "subject_ref", "target_ref", "covers_app_ref", "used_by_app_ref")
    for rid, (kind, record) in sorted(index.items()):
        for field in ref_fields:
            ref = record.get(field)
            if ref and ref not in index:
                issues.append(PacketIssue(rid, "DANGLING_REFERENCE", field,
                                          "%r does not name a record in this packet" % ref))

    departing = packet.get("transition", {}).get("departing_ref")
    if departing and departing not in index:
        issues.append(PacketIssue("transition", "DANGLING_REFERENCE", "departing_ref",
                                  "%r does not name a person in this packet" % departing))
    elif not departing:
        issues.append(PacketIssue("transition", "MISSING_REQUIRED_FIELD", "departing_ref",
                                  "the packet does not say who is leaving"))

    return issues, index


def is_deliverable(issues):
    """A packet with any SAFETY issue is not deliverable at any confidence.

    Integrity problems are reported and the report still renders, because a
    broken reference is itself a finding. Real-looking account data is
    different in kind: it must not leave the building, so the report refuses
    to render rather than degrading gracefully.
    """
    return not any(i.is_safety for i in issues)
