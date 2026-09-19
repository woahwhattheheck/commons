"""Read-only evidence-packet conformance checks, separate from payment authority.

An explicit adapter maps a producer's actual packet into Snapshot. This module
never builds a packet, grants acceptance, sends a message, or changes source data.
"""
from __future__ import annotations
from dataclasses import asdict, dataclass
from datetime import datetime
import hashlib
from pathlib import Path, PurePosixPath
from typing import Iterable

TERMS = {
    "kickoff": (40, 960_000, "written_authorization"),
    "draft": (40, 960_000, "draft_delivery"),
    "final": (20, 480_000, "final_acceptance"),
}
SOURCE_BLOBS = {
    "revenue/uiowa_rfq_18649_workshare/COMMERCIAL.md": "b6e9ca58984c15d96b497f3bb51000992fdb9b5f",
    "revenue/uiowa_rfq_18649_workshare/ACCEPTANCE_EXHIBIT.md": "48465060fff1402af966871352e894686fffe05e",
}


@dataclass(frozen=True)
class Finding:
    code: str
    locator: str
    detail: str


@dataclass(frozen=True)
class Artifact:
    id: str
    path: str
    version: str
    generation: str
    sha256: str
    locator: str


@dataclass(frozen=True)
class Event:
    id: str
    kind: str
    generation: str
    artifact_ids: tuple[str, ...]
    evidence_id: str
    at: str
    locator: str


@dataclass(frozen=True)
class Snapshot:
    id: str
    generation: str
    currency: str
    percent: int
    amount_cents: int
    trigger: str
    artifacts: tuple[Artifact, ...]
    evidence: tuple[Artifact, ...]
    events: tuple[Event, ...]
    open_dependencies: tuple[str, ...]
    locator: str
    option_included_in_base: bool = False


def _nonblank(value) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _path(root: Path, value: str) -> Path:
    if not _nonblank(value):
        raise ValueError("empty artifact path")
    parts = value.split("/")
    if PurePosixPath(value).is_absolute() or "\\" in value or ":" in value or any(x in ("", ".", "..") for x in parts):
        raise ValueError("artifact path is not a bounded relative POSIX path")
    current = root
    for part in parts:
        current /= part
        if current.is_symlink():
            raise ValueError("symlink artifact is not a supported evidence copy")
    if not current.resolve().is_relative_to(root):
        raise ValueError("artifact path leaves the supplied packet root")
    return current


def _at(value: str) -> datetime:
    if not _nonblank(value):
        raise ValueError("missing event time")
    d = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if d.tzinfo is None or d.utcoffset() is None:
        raise ValueError("event time requires an explicit UTC offset")
    return d


def inspect(snapshot: Snapshot, root: Path) -> dict:
    """Inspect one adapted, synthetic packet without authenticating its claims.

    Trigger-record status and byte integrity are deliberately separate. Missing
    deliverables cannot add a condition to kickoff or draft payment; the result
    never declares an amount due. All findings retain producer source locators.
    """
    findings: list[Finding] = []
    def add(code, locator, detail):
        findings.append(Finding(code, str(locator), detail))
    expected = TERMS.get(snapshot.id)
    if expected is None:
        add("UNKNOWN_MILESTONE", snapshot.locator, str(snapshot.id))
    elif (snapshot.currency != "USD" or type(snapshot.percent) is not int or
          type(snapshot.amount_cents) is not int or
          (snapshot.percent, snapshot.amount_cents, snapshot.trigger) != expected):
        add("PROPOSED_TERM_MISMATCH", snapshot.locator,
            f"Expected USD {expected[1]} cents, {expected[0]}%, trigger={expected[2]}; no automatic repricing")
    if snapshot.option_included_in_base is not False:
        add("OPTION_LEAKS_INTO_BASE", snapshot.locator, "USD 4,000 readout requires separate authorization")
    if not _nonblank(snapshot.generation):
        add("GENERATION_MISSING", snapshot.locator, "Packet needs a declared generation")
    packet_root = root.resolve()
    if not packet_root.is_dir():
        add("PACKET_ROOT_MISSING", snapshot.locator, str(root))
    all_artifacts = (*snapshot.artifacts, *snapshot.evidence)
    by_id: dict[str, Artifact] = {}
    good_ids: set[str] = set()
    duplicate_ids: set[str] = set()
    for a in all_artifacts:
        if not _nonblank(a.id):
            add("ARTIFACT_ID_MISSING", a.locator, "Artifact IDs cannot be blank")
        if a.id in by_id:
            duplicate_ids.add(a.id)
            add("DUPLICATE_ARTIFACT_ID", a.locator, f"Also appears at {by_id[a.id].locator}")
        else:
            by_id[a.id] = a
        if not _nonblank(a.version):
            add("ARTIFACT_VERSION_MISSING", a.locator, a.id)
        if not isinstance(a.sha256, str) or len(a.sha256) != 64 or any(c not in "0123456789abcdef" for c in a.sha256):
            add("INVALID_DIGEST", a.locator, "Expected lowercase SHA256")
            continue
        try:
            path = _path(packet_root, a.path)
            actual = hashlib.sha256(path.read_bytes()).hexdigest()
        except FileNotFoundError:
            add("ARTIFACT_MISSING", a.locator, a.path)
        except (ValueError, OSError) as exc:
            add("ARTIFACT_UNREADABLE", a.locator, str(exc))
        else:
            if actual != a.sha256:
                add("ARTIFACT_DIGEST_MISMATCH", a.locator, f"Declared {a.sha256}; actual {actual}")
            else:
                good_ids.add(a.id)
    good_ids -= duplicate_ids
    if not snapshot.artifacts:
        add("EMPTY_DELIVERY_INDEX", snapshot.locator, "No delivered artifacts supplied")
    for a in snapshot.artifacts:
        if not _nonblank(a.generation):
            add("ARTIFACT_GENERATION_MISSING", a.locator, a.id)
        elif a.generation != snapshot.generation:
            add("MIXED_DELIVERY_GENERATION", a.locator, f"{a.generation!r} differs from packet {snapshot.generation!r}")
    expected_ids = {a.id for a in snapshot.artifacts}
    observed = []
    seen_events = set()
    allowed = {expected[2]} if expected else set()
    if snapshot.id == "final":
        allowed.add("final_delivery")
    for e in snapshot.events:
        errors = []
        if e.id in seen_events or not _nonblank(e.id):
            errors.append("event ID is duplicate or empty")
        seen_events.add(e.id)
        if e.kind not in allowed:
            errors.append("event kind does not belong to this milestone")
        if not _nonblank(e.generation) or not _nonblank(snapshot.generation):
            errors.append("event or packet generation is not supplied")
        elif e.generation != snapshot.generation:
            errors.append("event generation differs from the packet")
        if e.evidence_id not in good_ids:
            errors.append("event documentary evidence is unavailable or ambiguous")
        if len(e.artifact_ids) != len(set(e.artifact_ids)):
            errors.append("event contains duplicate artifact IDs")
        if e.kind != "written_authorization" and set(e.artifact_ids) != expected_ids:
            errors.append("event artifact set differs from the delivered index")
        try:
            at = _at(e.at)
        except (TypeError, ValueError) as exc:
            errors.append(str(exc))
            at = None
        for err in errors:
            add("EVENT_RECORD_CONFLICT", e.locator, err)
        observed.append({"id": e.id, "kind": e.kind, "locator": e.locator,
                         "state": "conflicting_record" if errors else "recorded_unverified", "at": at})
    # A duplicate identifier makes every occurrence ambiguous, not only the last.
    for record in observed:
        if sum(x["id"] == record["id"] for x in observed) > 1:
            record["state"] = "conflicting_record"
    deliveries = [r for r in observed if r["kind"] == "final_delivery" and r["state"] == "recorded_unverified"]
    for r in observed:
        if r["kind"] == "final_acceptance" and r["state"] == "recorded_unverified":
            if not any(d["at"] <= r["at"] for d in deliveries):
                r["state"] = "conflicting_record"
                add("ACCEPTANCE_WITHOUT_PRIOR_DELIVERY_RECORD", r["locator"], "No matching, preceding final-delivery record")
    trigger_records = [r for r in observed if expected and r["kind"] == expected[2]]
    trigger_state = "not_recorded"
    if trigger_records:
        trigger_state = "recorded_unverified" if all(r["state"] == "recorded_unverified" for r in trigger_records) else "conflicting_records"
    byte_codes = {"ARTIFACT_ID_MISSING", "DUPLICATE_ARTIFACT_ID", "INVALID_DIGEST", "ARTIFACT_MISSING", "ARTIFACT_UNREADABLE", "ARTIFACT_DIGEST_MISMATCH", "EMPTY_DELIVERY_INDEX", "MIXED_DELIVERY_GENERATION", "ARTIFACT_VERSION_MISSING", "ARTIFACT_GENERATION_MISSING", "GENERATION_MISSING"}
    return {
        "milestone": snapshot.id, "source_locator": snapshot.locator,
        "byte_and_version_integrity": "unresolved" if any(f.code in byte_codes for f in findings) else "matches_supplied_manifest",
        "commercial_record_state": trigger_state,
        "open_dependencies": list(snapshot.open_dependencies),
        "payment_due": "NOT_DETERMINED", "accepted": "NOT_DETERMINED",
        "records_authenticated": False, "invoice_issued": False,
        "event_records": [{**r, "at": r["at"].isoformat() if r["at"] else None} for r in observed],
        "findings": [asdict(f) for f in sorted(findings, key=lambda f: (f.locator, f.code, f.detail))],
        "boundary": "Read-only documentary check of a synthetic draft. Not an acceptance decision, invoice, payment request or extra commercial condition.",
    }


def reconcile(snapshots: Iterable[Snapshot]) -> dict:
    """Reconcile base arithmetic without determining whether any amount is due."""
    rows = tuple(snapshots)
    identifiers = [s.id for s in rows]
    complete = len(identifiers) == 3 and set(identifiers) == set(TERMS)
    integer_amounts = all(type(s.amount_cents) is int for s in rows)
    total = sum(s.amount_cents for s in rows) if integer_amounts else None
    correct_rows = all(s.id in TERMS and s.currency == "USD" and type(s.percent) is int and
                       (s.percent, s.amount_cents, s.trigger) == TERMS[s.id] and
                       s.option_included_in_base is False for s in rows)
    return {"complete_base_set": complete, "total_cents": total,
            "matches_proposed_base": complete and integer_amounts and correct_rows and total == 2_400_000,
            "optional_readout_cents": 400_000, "option_included": False,
            "payment_due": "NOT_DETERMINED"}
