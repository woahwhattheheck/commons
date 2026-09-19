"""Offline reconciliation of declared fictional mortgage-case observations.

Reconstructed from Z-Quorum-7F2C's retained schema/design, not executed from the
damaged original. This module makes no lending or source-authenticity decision.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import unicodedata
from datetime import datetime
from itertools import groupby
from typing import Any

SCHEMA = "mortgage-case-reconcile/v1"
RECEIPT_SCHEMA = "mortgage-case-receipt/v1"
MAX_INPUT_BYTES = 2_000_000
MAX_NODES = 100_000
MAX_DEPTH = 64
ALLOWED_KINDS = {"bool", "code", "date", "money", "text"}
ALLOWED_DOC_STATUS = {"received", "validated", "rejected"}
ALLOWED_EVENT_TYPES = {"status", "request", "response", "document"}
ALLOWED_CHANNELS = {"broker_portal", "lender_portal", "system", "email_receipt"}
OPAQUE_ID = re.compile(r"[A-Z0-9][A-Z0-9._:-]{0,63}\Z")
FIELD_ID = re.compile(r"[a-z][a-z0-9_.-]{1,95}\Z")
DOC_TYPE = re.compile(r"[A-Z][A-Z0-9_]{1,63}\Z")
CODE = re.compile(r"[A-Z0-9][A-Z0-9_.:-]{0,63}\Z")
SHA256 = re.compile(r"[0-9a-f]{64}\Z")
FORBIDDEN_KEY_TOKENS = {
    "address", "bank_account", "birth", "dob", "email", "first_name",
    "full_name", "iban", "last_name", "national_insurance", "nino",
    "passport", "phone", "postcode", "routing_number", "sort_code", "ssn",
}


class ContractError(ValueError):
    """The supplied case does not meet the explicit input contract."""


def canonical_bytes(obj: Any) -> bytes:
    """Canonical JSON, without a trailing newline; no nonfinite numbers."""
    try:
        return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=False, allow_nan=False).encode("utf-8")
    except (TypeError, ValueError, UnicodeError, RecursionError, OverflowError) as exc:
        raise ContractError("value cannot be represented as canonical UTF-8 JSON") from exc


def _no_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ContractError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def strict_json_loads(text: str) -> Any:
    if type(text) is not str:
        raise ContractError("JSON input must be text")
    try:
        text.encode("utf-8")
        result = json.loads(text, object_pairs_hook=_no_duplicate_keys,
                            parse_constant=lambda value: (_ for _ in ()).throw(
                                ContractError(f"nonfinite JSON number: {value}")))
        # Also rejects escaped lone surrogates and overflowed finite literals.
        _tree(result, bounded=False)
        return result
    except ContractError:
        raise
    except (ValueError, UnicodeError, TypeError, RecursionError, OverflowError) as exc:
        raise ContractError("invalid UTF-8 JSON input") from exc


def _tree(value: Any, *, bounded: bool = True) -> None:
    """Check JSON types, cycles, Unicode and finite numbers before schema work."""
    nodes = 0
    active: set[int] = set()

    def visit(obj: Any, depth: int) -> None:
        nonlocal nodes
        nodes += 1
        if depth > MAX_DEPTH or (bounded and nodes > MAX_NODES):
            raise ContractError("input exceeds supported JSON depth or node count")
        kind = type(obj)
        if kind is str:
            try:
                obj.encode("utf-8")
            except UnicodeError as exc:
                raise ContractError("strings must contain Unicode scalar values") from exc
        elif kind is float:
            if not math.isfinite(obj):
                raise ContractError("nonfinite numbers are not supported")
        elif kind in (dict, list):
            identity = id(obj)
            if identity in active:
                raise ContractError("cyclic objects are not JSON input")
            active.add(identity)
            if kind is dict:
                for key, child in obj.items():
                    if type(key) is not str:
                        raise ContractError("object keys must be strings")
                    visit(key, depth + 1)
                    visit(child, depth + 1)
            else:
                for child in obj:
                    visit(child, depth + 1)
            active.remove(identity)
        elif kind not in (int, bool, type(None)):
            raise ContractError("input contains a non-JSON value")

    visit(value, 0)
    if bounded and len(canonical_bytes(value)) > MAX_INPUT_BYTES:
        raise ContractError("normalized case input exceeds 2,000,000 UTF-8 bytes")


def _obj(value: Any, keys: set[str], where: str) -> dict[str, Any]:
    if type(value) is not dict:
        raise ContractError(f"{where} must be an object")
    if set(value) != keys:
        missing = sorted(keys - set(value))
        extra = sorted(set(value) - keys)
        raise ContractError(f"{where} keys differ; missing={missing}, unsupported={extra}")
    return value


def _list(value: Any, where: str, minimum: int = 0) -> list[Any]:
    if type(value) is not list or len(value) < minimum:
        raise ContractError(f"{where} must be an array with at least {minimum} item(s)")
    return value


def _match(value: Any, pattern: re.Pattern[str], where: str) -> str:
    if type(value) is not str or not pattern.fullmatch(value):
        raise ContractError(f"{where} has invalid identifier syntax")
    return value


def _timestamp(value: Any, where: str) -> str:
    if type(value) is not str or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z", value):
        raise ContractError(f"{where} must be whole-second UTC YYYY-MM-DDTHH:MM:SSZ")
    try:
        datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError as exc:
        raise ContractError(f"{where} is not a real UTC timestamp") from exc
    return value


def _date(value: Any, where: str) -> str:
    if type(value) is not str or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
        raise ContractError(f"{where} must be YYYY-MM-DD")
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError as exc:
        raise ContractError(f"{where} is not a real date") from exc
    return value


def _sensitive_name(value: str) -> bool:
    return any(re.search(r"(?:^|[_.:-])" + re.escape(token) + r"(?:$|[_.:-])", value.casefold())
               for token in FORBIDDEN_KEY_TOKENS)


def _field(value: Any, where: str) -> str:
    result = _match(value, FIELD_ID, where)
    if _sensitive_name(result):
        raise ContractError(f"{where}: PII-shaped field names are outside this fictional demo")
    return result


def _unique(values: list[Any], where: str) -> None:
    if len(set(values)) != len(values):
        raise ContractError(f"duplicate identifier in {where}")


def _value(value: Any, kind: str, where: str) -> Any:
    if kind == "bool":
        if type(value) is not bool:
            raise ContractError(f"{where} must be a Boolean")
        return value
    if kind == "code":
        return _match(value, CODE, where)
    if kind == "date":
        return _date(value, where)
    if kind == "money":
        money = _obj(value, {"currency", "minor_units"}, where)
        currency = money["currency"]
        if type(currency) is not str or not re.fullmatch(r"[A-Z]{3}", currency):
            raise ContractError(f"{where}.currency must be three uppercase ASCII letters")
        units = money["minor_units"]
        if type(units) is not int or not 0 <= units <= 10**15:
            raise ContractError(f"{where}.minor_units must be an integer from 0 through 10^15")
        return {"currency": currency, "minor_units": units}
    if type(value) is not str:
        raise ContractError(f"{where} must be text")
    result = " ".join(unicodedata.normalize("NFC", value).split())
    if not 1 <= len(result) <= 160 or any(unicodedata.category(c).startswith("C") for c in result):
        raise ContractError(f"{where} must normalize to 1..160 characters without controls")
    return result


def normalize_case(raw: Any) -> dict[str, Any]:
    """Validate and return a fresh normalized case without changing the caller."""
    _tree(raw)
    root = _obj(raw, {"schema", "case_id", "subject_ref", "as_of", "field_specs", "sources",
                      "document_requirements", "milestone_order", "events"}, "case")
    if root["schema"] != SCHEMA:
        raise ContractError("unsupported case schema")
    case_id = _match(root["case_id"], OPAQUE_ID, "case_id")
    subject_ref = _match(root["subject_ref"], OPAQUE_ID, "subject_ref")
    as_of = _timestamp(root["as_of"], "as_of")
    specs = []
    for index, raw_spec in enumerate(_list(root["field_specs"], "field_specs")):
        where = f"field_specs[{index}]"
        spec = _obj(raw_spec, {"field_id", "kind", "required_sources"}, where)
        field_id = _field(spec["field_id"], where + ".field_id")
        if type(spec["kind"]) is not str or spec["kind"] not in ALLOWED_KINDS:
            raise ContractError(f"{where}.kind is unsupported")
        required = [_match(s, OPAQUE_ID, where + ".required_sources")
                    for s in _list(spec["required_sources"], where + ".required_sources", 1)]
        _unique(required, where + ".required_sources")
        specs.append({"field_id": field_id, "kind": spec["kind"], "required_sources": sorted(required)})
    _unique([s["field_id"] for s in specs], "field_specs")
    kinds = {s["field_id"]: s["kind"] for s in specs}
    sources = []
    for index, raw_source in enumerate(_list(root["sources"], "sources")):
        where = f"sources[{index}]"
        source = _obj(raw_source, {"source_id", "observed_at", "fields", "documents"}, where)
        source_id = _match(source["source_id"], OPAQUE_ID, where + ".source_id")
        observed = _timestamp(source["observed_at"], where + ".observed_at")
        if observed > as_of:
            raise ContractError(f"{where}.observed_at is after as_of")
        fields = []
        for item in _list(source["fields"], where + ".fields"):
            item = _obj(item, {"field_id", "value"}, where + ".fields[]")
            fid = _field(item["field_id"], where + ".fields[].field_id")
            if fid not in kinds:
                raise ContractError(f"undeclared field {fid} in {source_id}")
            fields.append({"field_id": fid, "value": _value(item["value"], kinds[fid], source_id + "." + fid)})
        _unique([f["field_id"] for f in fields], where + ".fields")
        documents = []
        for item in _list(source["documents"], where + ".documents"):
            item = _obj(item, {"document_id", "document_type", "sha256", "status"}, where + ".documents[]")
            did = _match(item["document_id"], OPAQUE_ID, where + ".document_id")
            dtype = _match(item["document_type"], DOC_TYPE, where + ".document_type")
            sha = _match(item["sha256"], SHA256, where + ".sha256")
            if type(item["status"]) is not str or item["status"] not in ALLOWED_DOC_STATUS:
                raise ContractError(f"{where}: unsupported document status")
            documents.append({"document_id": did, "document_type": dtype, "sha256": sha, "status": item["status"]})
        _unique([d["document_id"] for d in documents], where + ".documents")
        sources.append({"source_id": source_id, "observed_at": observed,
                        "fields": sorted(fields, key=lambda f: f["field_id"]),
                        "documents": sorted(documents, key=lambda d: d["document_id"])})
    _unique([s["source_id"] for s in sources], "sources")
    source_ids = {s["source_id"] for s in sources}
    for spec in specs:
        unknown = set(spec["required_sources"]) - source_ids
        if unknown:
            raise ContractError(f"required_sources reference undeclared sources: {sorted(unknown)}")
    requirements = []
    for item in _list(root["document_requirements"], "document_requirements"):
        item = _obj(item, {"document_type", "min_validated"}, "document_requirements[]")
        dtype = _match(item["document_type"], DOC_TYPE, "document_requirements.document_type")
        minimum = item["min_validated"]
        if type(minimum) is not int or not 1 <= minimum <= 20:
            raise ContractError("min_validated must be an integer from 1 through 20")
        requirements.append({"document_type": dtype, "min_validated": minimum})
    _unique([r["document_type"] for r in requirements], "document_requirements")
    milestones = [_match(m, OPAQUE_ID, "milestone_order") for m in _list(root["milestone_order"], "milestone_order", 2)]
    _unique(milestones, "milestone_order")
    events = []
    for item in _list(root["events"], "events", 1):
        item = _obj(item, {"event_id", "at", "event_type", "milestone", "channel", "message_ref"}, "events[]")
        event_id = _match(item["event_id"], OPAQUE_ID, "event_id")
        at = _timestamp(item["at"], "event.at")
        if at > as_of:
            raise ContractError("event.at is after as_of")
        if type(item["event_type"]) is not str or item["event_type"] not in ALLOWED_EVENT_TYPES:
            raise ContractError("unsupported event_type")
        if type(item["channel"]) is not str or item["channel"] not in ALLOWED_CHANNELS:
            raise ContractError("unsupported event channel")
        milestone = _match(item["milestone"], OPAQUE_ID, "event.milestone")
        if milestone not in milestones:
            raise ContractError("event refers to an undeclared milestone")
        events.append({"event_id": event_id, "at": at, "event_type": item["event_type"],
                       "milestone": milestone, "channel": item["channel"],
                       "message_ref": _match(item["message_ref"], OPAQUE_ID, "event.message_ref")})
    _unique([e["event_id"] for e in events], "events")
    return {"schema": SCHEMA, "case_id": case_id, "subject_ref": subject_ref, "as_of": as_of,
            "field_specs": sorted(specs, key=lambda s: s["field_id"]),
            "sources": sorted(sources, key=lambda s: s["source_id"]),
            "document_requirements": sorted(requirements, key=lambda r: r["document_type"]),
            "milestone_order": milestones, "events": sorted(events, key=lambda e: (e["at"], e["event_id"]))}


def compile_case(raw: Any) -> dict[str, Any]:
    case = normalize_case(raw)
    issues: list[dict[str, Any]] = []

    def issue(code: str, subject: str, sources: list[str], details: Any) -> None:
        issues.append({"code": code, "severity": "BLOCK", "subject": subject,
                       "source_ids": sorted(set(sources)), "details": details})

    fields = []
    for spec in case["field_specs"]:
        fid = spec["field_id"]
        observations = [{"source_id": source["source_id"], "observed_at": source["observed_at"],
                         "value": entry["value"], "required": source["source_id"] in spec["required_sources"]}
                        for source in case["sources"] for entry in source["fields"] if entry["field_id"] == fid]
        present = {o["source_id"] for o in observations}
        missing = sorted(set(spec["required_sources"]) - present)
        values = {canonical_bytes(o["value"]): o["value"] for o in observations}
        distinct = [values[key] for key in sorted(values)]
        if missing:
            issue("SOURCE_FIELD_MISSING", "field:" + fid, missing, {"missing_sources": missing})
        if len(distinct) > 1:
            issue("FIELD_CONFLICT", "field:" + fid, sorted(present), {"distinct_values": distinct})
        fields.append({**spec, "observations": observations, "missing_sources": missing, "distinct_values": distinct,
                       "status": "CONFLICT" if len(distinct) > 1 else "MISSING" if missing else "ALIGNED"})

    all_documents = [{**doc, "source_id": source["source_id"], "observed_at": source["observed_at"]}
                     for source in case["sources"] for doc in source["documents"]]
    all_documents.sort(key=lambda d: (d["source_id"], d["document_id"]))
    by_hash: dict[str, list[dict[str, Any]]] = {}
    by_id: dict[str, list[dict[str, Any]]] = {}
    for doc in all_documents:
        by_hash.setdefault(doc["sha256"], []).append(doc)
        by_id.setdefault(doc["document_id"], []).append(doc)
    contested: set[str] = set()
    for sha, docs in sorted(by_hash.items()):
        statuses = sorted({d["status"] for d in docs})
        if len(statuses) > 1:
            contested.add(sha)
            issue("DOCUMENT_STATUS_CONFLICT", "document_hash:" + sha, [d["source_id"] for d in docs],
                  {"sha256": sha, "statuses": statuses, "observations": docs})
    for doc_id, docs in sorted(by_id.items()):
        identities = {(d["sha256"], d["document_type"]) for d in docs}
        if len(identities) > 1:
            hashes = sorted({d["sha256"] for d in docs})
            contested.update(hashes)
            issue("DOCUMENT_ID_CONFLICT", "document_id:" + doc_id, [d["source_id"] for d in docs],
                  {"document_id": doc_id, "hashes": hashes, "observations": docs})
    requirements = {r["document_type"]: r["min_validated"] for r in case["document_requirements"]}
    documents = []
    for dtype in sorted(set(requirements) | {d["document_type"] for d in all_documents}):
        observations = [d for d in all_documents if d["document_type"] == dtype]
        validated = sorted({d["sha256"] for d in observations if d["status"] == "validated" and d["sha256"] not in contested})
        minimum = requirements.get(dtype, 0)
        status = "NOT_REQUIRED" if not minimum else "SATISFIED" if len(validated) >= minimum else "UNMET"
        if status == "UNMET":
            issue("DOCUMENT_REQUIREMENT_UNMET", "document:" + dtype, [d["source_id"] for d in observations],
                  {"min_validated": minimum, "validated_unique_count": len(validated)})
        documents.append({"document_type": dtype, "required": dtype in requirements, "min_validated": minimum,
                          "validated_unique_hashes": validated,
                          "contested_hashes": sorted({d["sha256"] for d in observations} & contested),
                          "observations": observations, "status": status})

    ranks = {milestone: n for n, milestone in enumerate(case["milestone_order"])}
    groups = []
    previous = None
    for at, iterator in groupby((e for e in case["events"] if e["event_type"] == "status"), key=lambda e: e["at"]):
        events = list(iterator)
        milestones = sorted({e["milestone"] for e in events}, key=ranks.__getitem__)
        group = {"at": at, "milestones": milestones, "event_ids": [e["event_id"] for e in events],
                 "status": "KNOWN" if len(milestones) == 1 else "AMBIGUOUS"}
        if len(milestones) > 1:
            issue("MILESTONE_AMBIGUOUS", "status_group:" + at, [], group)
        if previous is not None and max(ranks[m] for m in milestones) < min(ranks[m] for m in previous["milestones"]):
            issue("MILESTONE_REGRESSION", "status_group:" + at, [], {"previous": previous, "current": group})
        groups.append(group)
        previous = group
    if not groups:
        current = None
        current_status = "UNKNOWN"
        issue("MILESTONE_STATUS_MISSING", "case:" + case["case_id"], [], {"status_event_count": 0})
    else:
        current_status = groups[-1]["status"]
        current = groups[-1]["milestones"][0] if current_status == "KNOWN" else None
    issues.sort(key=lambda i: (i["code"], i["subject"], canonical_bytes(i["details"])))
    instructions = {
        "SOURCE_FIELD_MISSING": "Obtain the missing declared source field observations.",
        "FIELD_CONFLICT": "Reconcile the conflicting supplied field observations; retain their provenance.",
        "DOCUMENT_STATUS_CONFLICT": "Clarify contradictory status declarations for the same document hash.",
        "DOCUMENT_ID_CONFLICT": "Clarify the changed content hash or type attached to the same document identifier.",
        "DOCUMENT_REQUIREMENT_UNMET": "Supply the required distinct, uncontested declared-validated document observations.",
        "MILESTONE_AMBIGUOUS": "Clarify contradictory simultaneous status observations without selecting by event identifier.",
        "MILESTONE_REGRESSION": "Review the backward transition between supplied status groups.",
        "MILESTONE_STATUS_MISSING": "Supply an explicit status event; informational events do not establish case state.",
    }
    actions = []
    for index, item in enumerate(issues, 1):
        item["issue_id"] = f"ISSUE-{index:04d}"
        actions.append({"action_id": f"ACTION-{index:04d}", "issue_id": item["issue_id"],
                        "action": instructions[item["code"]], "subject": item["subject"],
                        "source_ids": list(item["source_ids"])})
    receipt = {"schema": RECEIPT_SCHEMA, "case_id": case["case_id"], "subject_ref": case["subject_ref"],
               "as_of": case["as_of"], "case": case,
               "source_digest": hashlib.sha256(canonical_bytes(case)).hexdigest(),
               "current_milestone": current, "current_milestone_status": current_status,
               "reconciliation_status": "REVIEW_REQUIRED" if issues else "NO_DECLARED_BLOCKERS",
               "fields": fields, "documents": documents, "timeline": case["events"], "status_groups": groups,
               "issues": issues, "next_actions": actions,
               "authority": {key: False for key in ("underwriting_decision", "affordability_decision",
                   "fraud_determination", "eligibility_decision", "customer_contact", "lender_submission",
                   "commercial_acceptance", "payment_or_revenue")}}
    receipt["semantic_digest"] = hashlib.sha256(canonical_bytes(receipt)).hexdigest()
    # Remove shared object aliases between the normalized case and projections.
    return json.loads(canonical_bytes(receipt))
