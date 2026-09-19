"""Data contract for milestone delivery + billing evidence packets (UIOWA-135).

Why this file is defensive rather than a plain set of dataclasses: a milestone
billing packet is the one artifact in an engagement most likely to quietly
assert something that never happened -- that a deliverable was ACCEPTED, that an
invoice was ISSUED, that a cited file exists. The work order's completion bar is
explicit: the samples must be "usable drafts rather than claims of an issued
invoice, acceptance, or payment." So the unsafe states are unrepresentable here,
not merely discouraged in a README.

Three rules are enforced by construction:
  1. Money is integer cents. Float dollars are refused outright, because
     8000.00 + 8000.00 + 7999.99 prints like $24,000.00 and is not.
  2. Delivery and acceptance are separate state machines. Nothing can move an
     artifact to ACCEPTED_RECORDED except a dated AcceptanceRecord naming a
     party; a delivery alone leaves acceptance PENDING.
  3. UNKNOWN is a sentinel with no arithmetic and no truthiness. A missing
     input cannot silently become 0, False, or "fine".
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

SYNTHETIC_BANNER = "SYNTHETIC / FICTION - not a University of Iowa record"

# The packet is a draft. These strings are the ones that would turn a draft into
# a false assertion, so the renderer refuses to emit them (see packets.py).
FORBIDDEN_CLAIM_STATES = frozenset(
    {"PAID", "INVOICE_ISSUED", "APPROVED_FOR_PAYMENT", "ACCEPTED", "PAYMENT_RECEIVED"}
)

DRAFT_STAMP = "DRAFT - NOT AN ISSUED INVOICE, NOT A RECORD OF ACCEPTANCE OR PAYMENT"


class PacketError(Exception):
    """Base class so the CLI can report a diagnostic instead of a traceback."""


class MoneyTypeError(PacketError):
    pass


class ForbiddenClaimError(PacketError):
    pass


class UnknownUsedAsValueError(PacketError):
    pass


class SchemaError(PacketError):
    pass


class _Unknown:
    """Absent input. Deliberately hostile to being used as a number or a flag.

    OP5-CINDER's 084 build found a real bug this way: if UNKNOWN had been 0 or
    None-coerced, an unestimated value would have been scored silently. Same
    reasoning applies to an unrecorded milestone amount or a missing disposition
    -- the failure has to be loud at the point of use.
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __repr__(self) -> str:
        return "UNKNOWN"

    def __str__(self) -> str:
        return "UNKNOWN"

    def _refuse(self, *_a: Any, **_k: Any):
        raise UnknownUsedAsValueError(
            "UNKNOWN has no value: it cannot be summed, compared, or tested for "
            "truth. Compare with 'is UNKNOWN' and report the gap instead."
        )

    __add__ = __radd__ = __sub__ = __rsub__ = _refuse
    __mul__ = __rmul__ = __truediv__ = __rtruediv__ = _refuse
    __lt__ = __le__ = __gt__ = __ge__ = _refuse
    __int__ = __float__ = __bool__ = _refuse


UNKNOWN = _Unknown()


def opt(value: Any) -> Any:
    """Normalize a possibly-absent JSON field to UNKNOWN."""
    if value is None or value == "":
        return UNKNOWN
    return value


_MONEY_RE = re.compile(r"^\$?\s*(-?)(\d{1,3}(?:,\d{3})*|\d+)(?:\.(\d{2}))?$")


@dataclass(frozen=True)
class Money:
    """US dollars held as integer cents. There is no float path in or out."""

    cents: int

    def __post_init__(self) -> None:
        # bool is an int subclass; True would otherwise become one cent.
        if isinstance(self.cents, bool) or not isinstance(self.cents, int):
            raise MoneyTypeError(
                f"Money takes integer cents, got {type(self.cents).__name__}. "
                "Float dollars are refused: they make a wrong total look right."
            )

    @classmethod
    def parse(cls, raw: Any) -> "Money":
        if isinstance(raw, Money):
            return raw
        if isinstance(raw, float):
            raise MoneyTypeError(
                f"refusing float dollars {raw!r}: write the amount as a string "
                '(e.g. "4,800.00") or as integer cents.'
            )
        if isinstance(raw, bool):
            raise MoneyTypeError("refusing bool as an amount")
        if isinstance(raw, int):
            return cls(raw)
        if isinstance(raw, str):
            text = raw.strip()
            m = _MONEY_RE.match(text)
            if not m:
                raise MoneyTypeError(f"unparseable amount {raw!r}")
            # A bare digit run is ambiguous and the ambiguity is a factor of 100:
            # int 24000 means cents here, so string "24000" could reasonably mean
            # either $240.00 or $24,000.00. Refusing it is the whole point of
            # holding money as integer cents -- a unit mistake must be loud, not
            # resolved by a convention the caller may not share.
            if not any(ch in text for ch in ".,$"):
                raise MoneyTypeError(
                    f"ambiguous amount {raw!r}: a bare digit string could be dollars "
                    'or cents. Write dollars explicitly ("24,000.00" or "$24000.00") '
                    "or pass an int for cents (2400000)."
                )
            sign, whole, frac = m.group(1), m.group(2).replace(",", ""), m.group(3) or "00"
            cents = int(whole) * 100 + int(frac)
            return cls(-cents if sign == "-" else cents)
        raise MoneyTypeError(f"unsupported amount type {type(raw).__name__}")

    def __add__(self, other: "Money") -> "Money":
        if not isinstance(other, Money):
            raise MoneyTypeError("Money may only be added to Money")
        return Money(self.cents + other.cents)

    def dollars(self) -> str:
        sign = "-" if self.cents < 0 else ""
        c = abs(self.cents)
        return f"{sign}${c // 100:,}.{c % 100:02d}"


# ---------------------------------------------------------------- state values

SUBMISSION_STATES = ("NOT_SUBMITTED", "DELIVERED")
# ACCEPTED_RECORDED is reachable only from an AcceptanceRecord, never from a
# delivery. That separation is the order's "draft delivery and final acceptance
# are represented distinctly" requirement, made structural.
ACCEPTANCE_STATES = ("NOT_REQUESTED", "PENDING", "REVISION_REQUESTED", "ACCEPTED_RECORDED")
BILLING_STATES = ("DRAFT_NOT_ISSUED",)

DISPOSITIONS = (
    "RETAIN_WITH_DELIVERABLE",
    "RETURN_TO_CLIENT",
    "DESTROY_AT_CLOSEOUT",
    "CLIENT_SYSTEM_OF_RECORD",
)

MILESTONE_KINDS = ("KICKOFF", "DRAFT_DELIVERY", "FINAL_ACCEPTANCE")


@dataclass
class IndexItem:
    """One row of a milestone's delivered-file index.

    Every row carries where it came from, who holds it, where it lives, and what
    happens to it at closeout. `disposition` may be UNKNOWN -- and when it is,
    the completeness report FAILS with MISSING_DISPOSITION rather than picking a
    default. An unmade decision is reported as unmade.
    """

    item_id: str
    path: str
    title: str
    declared_version: Any
    source: Any
    custodian: Any
    storage_location: Any
    disposition: Any
    criteria_ids: list = field(default_factory=list)
    notes: str = ""

    @classmethod
    def from_json(cls, d: dict) -> "IndexItem":
        _require(d, ("item_id", "path", "title"), "index item")
        disp = opt(d.get("disposition"))
        if disp is not UNKNOWN and disp not in DISPOSITIONS:
            raise SchemaError(
                f"{d['item_id']}: disposition {disp!r} not in {DISPOSITIONS}"
            )
        return cls(
            item_id=d["item_id"],
            path=d["path"],
            title=d["title"],
            declared_version=opt(d.get("declared_version")),
            source=opt(d.get("source")),
            custodian=opt(d.get("custodian")),
            storage_location=opt(d.get("storage_location")),
            disposition=disp,
            criteria_ids=list(d.get("criteria_ids", [])),
            notes=d.get("notes", ""),
        )


@dataclass
class Criterion:
    criterion_id: str
    text: str
    evidence_item_ids: list = field(default_factory=list)

    @classmethod
    def from_json(cls, d: dict) -> "Criterion":
        _require(d, ("criterion_id", "text"), "criterion")
        return cls(d["criterion_id"], d["text"], list(d.get("evidence_item_ids", [])))


@dataclass
class Dependency:
    """Something still outstanding. `needed_by` drives the overdue calculation."""

    dependency_id: str
    description: str
    owner: Any
    needed_by: Any          # ISO date string or UNKNOWN
    state: str              # OPEN | CLOSED

    @classmethod
    def from_json(cls, d: dict) -> "Dependency":
        _require(d, ("dependency_id", "description", "state"), "dependency")
        if d["state"] not in ("OPEN", "CLOSED"):
            raise SchemaError(f"{d['dependency_id']}: state must be OPEN or CLOSED")
        return cls(
            d["dependency_id"], d["description"], opt(d.get("owner")),
            opt(d.get("needed_by")), d["state"],
        )


@dataclass
class AcceptanceRecord:
    """The ONLY thing that can put a milestone in ACCEPTED_RECORDED.

    A delivery cannot do it. A criterion with evidence attached cannot do it.
    Acceptance is a client act, so it needs a dated client record with a name on
    it and a reference that a reader can go look up.
    """

    recorded_on: str
    recorded_by: str
    reference: str

    @classmethod
    def from_json(cls, d: Any) -> Any:
        if d is None:
            return UNKNOWN
        _require(d, ("recorded_on", "recorded_by", "reference"), "acceptance record")
        if not _ISO_DATE.match(str(d["recorded_on"])):
            raise SchemaError(f"acceptance record date {d['recorded_on']!r} not YYYY-MM-DD")
        return cls(d["recorded_on"], d["recorded_by"], d["reference"])


_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


@dataclass
class Milestone:
    milestone_id: str
    name: str
    kind: str
    sequence: int
    amount: Money
    due_date: Any
    submission_state: str
    delivered_on: Any
    acceptance: Any                      # AcceptanceRecord | UNKNOWN
    invoice_description: str
    transmittal_note: str
    criteria: list = field(default_factory=list)
    index_items: list = field(default_factory=list)
    dependencies: list = field(default_factory=list)

    @property
    def acceptance_state(self) -> str:
        """Derived, never stored. A delivery never implies acceptance."""
        if isinstance(self.acceptance, AcceptanceRecord):
            return "ACCEPTED_RECORDED"
        if self.submission_state == "DELIVERED":
            return "PENDING"
        return "NOT_REQUESTED"

    @property
    def billing_state(self) -> str:
        # There is exactly one billing state this tool can produce. Issuing an
        # invoice and recording a payment are outside its authority.
        return "DRAFT_NOT_ISSUED"

    @classmethod
    def from_json(cls, d: dict) -> "Milestone":
        _require(
            d,
            ("milestone_id", "name", "kind", "sequence", "amount", "submission_state"),
            "milestone",
        )
        if d["kind"] not in MILESTONE_KINDS:
            raise SchemaError(f"{d['milestone_id']}: kind must be one of {MILESTONE_KINDS}")
        if d["submission_state"] not in SUBMISSION_STATES:
            raise SchemaError(
                f"{d['milestone_id']}: submission_state must be one of {SUBMISSION_STATES}"
            )
        # A fixture that tries to hand us a finished, billed, accepted milestone
        # is rejected here rather than rendered into a document.
        for key in ("billing_state", "acceptance_state", "status"):
            val = d.get(key)
            if isinstance(val, str) and val.replace(" ", "_").upper() in FORBIDDEN_CLAIM_STATES:
                raise ForbiddenClaimError(
                    f"{d['milestone_id']}: refusing {key}={val!r}. This tool produces "
                    "drafts; it cannot assert an issued invoice, an acceptance, or a "
                    "payment. Supply a dated acceptance_record instead."
                )
        return cls(
            milestone_id=d["milestone_id"],
            name=d["name"],
            kind=d["kind"],
            sequence=int(d["sequence"]),
            amount=Money.parse(d["amount"]),
            due_date=opt(d.get("due_date")),
            submission_state=d["submission_state"],
            delivered_on=opt(d.get("delivered_on")),
            acceptance=AcceptanceRecord.from_json(d.get("acceptance_record")),
            invoice_description=d.get("invoice_description", ""),
            transmittal_note=d.get("transmittal_note", ""),
            criteria=[Criterion.from_json(c) for c in d.get("criteria", [])],
            index_items=[IndexItem.from_json(i) for i in d.get("index_items", [])],
            dependencies=[Dependency.from_json(x) for x in d.get("dependencies", [])],
        )


@dataclass
class Engagement:
    engagement_id: str
    title: str
    contract_total: Money
    milestones: list
    synthetic: bool = True

    @classmethod
    def from_json(cls, d: dict) -> "Engagement":
        _require(d, ("engagement_id", "title", "contract_total", "milestones"), "engagement")
        ms = [Milestone.from_json(m) for m in d["milestones"]]
        ms.sort(key=lambda m: m.sequence)
        return cls(
            engagement_id=d["engagement_id"],
            title=d["title"],
            contract_total=Money.parse(d["contract_total"]),
            milestones=ms,
            synthetic=bool(d.get("synthetic", True)),
        )

    def milestone_total(self) -> Money:
        total = Money(0)
        for m in self.milestones:
            total = total + m.amount
        return total


def _require(d: Any, keys: tuple, what: str) -> None:
    if not isinstance(d, dict):
        raise SchemaError(f"{what}: expected an object, got {type(d).__name__}")
    missing = [k for k in keys if k not in d]
    if missing:
        raise SchemaError(f"{what}: missing required field(s) {', '.join(missing)}")
