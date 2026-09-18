"""Evidence classifier for Alameda County RFP 902737."""
from __future__ import annotations
from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
import json
import re

OPPORTUNITY_ID = "ALAMEDA-902737"
EXPECTED_DEADLINE = "2026-10-13T14:00:00-07:00"
_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")

OFFICIAL_ROOTS = {}
PRIME_ROOTS = {}
LOCAL_ROOTS = {}
WORKSHARE_ROOTS = {}

class GateError(ValueError):
    pass

def _canon(value):
    try:
        raw = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise GateError("non-canonical input") from exc
    if len(raw.encode()) > 256_000:
        raise GateError("input too large")
    return raw.encode()

def _digest(value):
    return sha256(_canon(value)).hexdigest()

def _id(value, name):
    if type(value) is not str or not _ID.fullmatch(value):
        raise GateError(f"{name}: invalid")
    return value

def _sha(value, name):
    if type(value) is not str or not _HEX64.fullmatch(value):
        raise GateError(f"{name}: invalid")
    return value

def _roots(value):
    if type(value) is not dict:
        raise GateError("roots must be dict")
    out = {}
    for digest, descriptor in value.items():
        out[_sha(digest, "root sha")] = tuple(descriptor)
    return out

def _rows(packet):
    rows = packet.get("evidence")
    if type(rows) is not list or len(rows) > 128:
        raise GateError("evidence must be bounded list")
    out = []
    seen = set()
    for row0 in rows:
        if type(row0) is not dict:
            raise GateError("evidence row must be object")
        row = {
            "source_id": _id(row0.get("source_id"), "source_id"),
            "sha256": _sha(row0.get("sha256"), "sha256"),
            "kind": _id(row0.get("kind"), "kind"),
            "subject": _id(row0.get("subject"), "subject"),
            "gate": _id(row0.get("gate"), "gate"),
        }
        key = (row["source_id"], row["sha256"])
        if key in seen:
            raise GateError("duplicate evidence identity")
        seen.add(key)
        out.append(row)
    return tuple(out)

def _has(rows, roots, kind, subject, gate):
    expected = (kind, subject, gate)
    matches = [r for r in rows if (r["kind"], r["subject"], r["gate"]) == expected]
    return bool(matches) and all(roots.get(r["sha256"]) == expected for r in matches)

def build_classifier(official_roots, prime_roots, local_roots, workshare_roots):
    official = _roots(dict(official_roots))
    prime = _roots(dict(prime_roots))
    local = _roots(dict(local_roots))
    workshare = _roots(dict(workshare_roots))

    def classify(packet0, *, now=None):
        if type(packet0) is not dict:
            raise GateError("packet must be object")
        packet = deepcopy(packet0)
        if packet.get("opportunity_id") != OPPORTUNITY_ID:
            raise GateError("wrong opportunity")
        rows = _rows(packet)
        buyer = packet.get("buyer")
        if type(buyer) is not dict or buyer.get("deadline") != EXPECTED_DEADLINE:
            raise GateError("buyer identity mismatch")
        if not _has(rows, official, "OFFICIAL_PACKET", "alameda-county", "buyer_packet"):
            state = "HOLD_MISSING_OFFICIAL_PACKET"
        elif not _has(rows, official, "OFFICIAL_ADDENDA_INDEX", "alameda-county", "addenda_generation"):
            state = "HOLD_ADDENDA_UNBOUND"
        elif buyer.get("teaming") == "PROHIBITED":
            state = "NO_PARTNER_ROUTE"
        elif buyer.get("teaming") != "PERMITTED":
            state = "HOLD_TEAMING_UNKNOWN"
        elif buyer.get("local_participation") not in ("REQUIRED", "NOT_REQUIRED"):
            state = "HOLD_LOCAL_PARTICIPATION_UNKNOWN"
        else:
            current = now if now is not None else datetime.now(timezone.utc)
            if not isinstance(current, datetime) or current.tzinfo is None:
                raise GateError("now must be offset-aware")
            if current >= datetime.fromisoformat(EXPECTED_DEADLINE):
                state = "NO_BID_DEADLINE_CLOSED"
            else:
                p = packet.get("prime")
                if type(p) is not dict:
                    raise GateError("prime must be object")
                org = _id(p.get("org_id"), "prime.org_id")
                required = ("platform", "three_similar_jurisdictions", "insurance", "security_accessibility", "support_24x7")
                if not all(_has(rows, prime, "PRIME_EVIDENCE", org, g) for g in required):
                    state = "HOLD_PRIME_EVIDENCE"
                elif buyer["local_participation"] == "REQUIRED" and not _has(rows, local, "LOCAL_PARTICIPATION_EVIDENCE", org, "local_participation"):
                    state = "HOLD_LOCAL_PARTICIPATION_EVIDENCE"
                elif not _has(rows, workshare, "INTERNAL_WORKSHARE_EVIDENCE", org, "paid_tjlabs_seam"):
                    state = "HOLD_PAID_WORKSHARE_UNBOUND"
                else:
                    state = "QUALIFIED_FOR_INTERNAL_NEXT_EDGE"
        semantic = {"opportunity_id": OPPORTUNITY_ID, "state": state, "deadline": EXPECTED_DEADLINE, "evidence_generation_sha256": _digest(list(rows))}
        return {"schema": "alameda-902737-qualification/v1", "semantic": semantic, "receipt_sha256": _digest(semantic)}
    return classify

classify = build_classifier(OFFICIAL_ROOTS, PRIME_ROOTS, LOCAL_ROOTS, WORKSHARE_ROOTS)

def production_state():
    return classify({
        "opportunity_id": OPPORTUNITY_ID,
        "buyer": {"deadline": EXPECTED_DEADLINE, "teaming": "UNKNOWN", "local_participation": "UNKNOWN"},
        "prime": {"org_id": "unselected-prime"},
        "evidence": [],
    })
