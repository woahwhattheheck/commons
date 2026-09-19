#!/usr/bin/env python3
"""Independent source-to-report conservation audit for uiowa.identity-map.v1.

Does not import the producer, infer equivalence, assess source truth, or repair
records. Reads JSON only. Exit 0: checked invariants hold; 1: report mismatch;
2: malformed input or IO failure. An unresolved reference can be faithfully
reported and pass this audit: conservation is not resolution or approval.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
import math
from pathlib import Path
import sys
from typing import Any

SCHEMA = "uiowa.identity-map.v1"
AUDIT_SCHEMA = "uiowa.identity-audit.v1"
FIELDS = ("namespace", "kind", "id", "revision")
KINDS = {"source", "observation", "finding", "recommendation", "service"}
MAX_BYTES = 16 * 1024 * 1024
MAX_DEPTH = 128
MAX_ROWS = 20000


class AuditInputError(ValueError):
    """The auditor cannot establish a well-formed comparison input."""


def _json_value(value: Any, depth: int = 0, active: set[int] | None = None) -> None:
    if depth > MAX_DEPTH:
        raise AuditInputError(f"JSON nesting exceeds {MAX_DEPTH}")
    if value is None or type(value) in (bool, int):
        return
    if type(value) is float:
        if not math.isfinite(value):
            raise AuditInputError("Non-finite numbers are not JSON evidence")
        return
    if type(value) is str:
        try:
            value.encode("utf-8")
        except UnicodeError as exc:
            raise AuditInputError("Unpaired Unicode surrogate") from exc
        return
    if type(value) not in (dict, list):
        raise AuditInputError("Only JSON objects, arrays, and scalars are accepted")
    active = set() if active is None else active
    if id(value) in active:
        raise AuditInputError("Circular input")
    active.add(id(value))
    try:
        values = value if isinstance(value, list) else value.values()
        if isinstance(value, dict):
            for name in value:
                if type(name) is not str:
                    raise AuditInputError("JSON object keys must be strings")
                _json_value(name, depth + 1, active)
        for item in values:
            _json_value(item, depth + 1, active)
    finally:
        active.remove(id(value))


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def fingerprint(value: Any, domain: str = "") -> str:
    return hashlib.sha256(((domain + "\0") if domain else "").encode("utf-8") + canonical(value).encode("utf-8")).hexdigest()


def _pairs(items: list[tuple[str, Any]]) -> dict:
    result = {}
    for name, value in items:
        if name in result:
            raise AuditInputError(f"Duplicate JSON key: {name!r}")
        result[name] = value
    return result


def load(path: Path) -> Any:
    with path.open("rb") as source:
        raw = source.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise AuditInputError(f"File exceeds {MAX_BYTES} bytes")
    def constant(name: str) -> None:
        raise AuditInputError(f"Non-finite JSON constant: {name}")
    try:
        result = json.loads(raw.decode("utf-8"), object_pairs_hook=_pairs, parse_constant=constant)
        _json_value(result)
        return result
    except (UnicodeError, json.JSONDecodeError, RecursionError, ValueError) as exc:
        if isinstance(exc, AuditInputError):
            raise
        raise AuditInputError(f"Invalid UTF-8 JSON: {exc}") from exc


def _text(value: Any, name: str) -> str:
    if type(value) is not str or not value.strip() or any(ord(c) < 32 or ord(c) == 127 for c in value):
        raise AuditInputError(f"{name} must be a nonempty string without control characters")
    return value


def _rows(value: Any, name: str) -> list[dict]:
    if type(value) is not list or len(value) > MAX_ROWS or any(type(v) is not dict for v in value):
        raise AuditInputError(f"{name} must contain at most {MAX_ROWS} objects")
    return value


def _selector(value: Any, complete: bool = False) -> dict:
    if type(value) is not dict or set(value) - set(FIELDS) or not {"kind", "id"}.issubset(value):
        raise AuditInputError("Invalid selector fields")
    if complete and set(value) != set(FIELDS):
        raise AuditInputError("A complete selector needs namespace, kind, id, and revision")
    for name, item in value.items():
        _text(item, f"selector.{name}")
    if value["kind"] not in KINDS:
        raise AuditInputError("Invalid entity kind")
    return value


def _identity(record: dict) -> tuple[str, ...]:
    selected = _selector({name: record[name] for name in FIELDS if name in record}, True)
    return tuple(selected[name] for name in FIELDS)


def _oid(identity: tuple[str, ...]) -> str:
    return "occ-" + fingerprint(list(identity), SCHEMA + "/occurrence")


def _validate_source(document: Any) -> tuple[list[dict], list[dict], list[dict]]:
    if type(document) is not dict or document.get("schema") != SCHEMA:
        raise AuditInputError(f"Source schema must be {SCHEMA}")
    records = _rows(document.get("records"), "records")
    seen = {}
    for record in records:
        identity = _identity(record)
        if type(record.get("synthetic")) is not bool or type(record.get("payload")) is not dict:
            raise AuditInputError("Records need an explicit synthetic boolean and object payload")
        locators = record.get("source_locators")
        if type(locators) is not list or not locators:
            raise AuditInputError("Records need nonempty source_locators")
        for value in locators:
            _text(value, "source locator")
        text = canonical(record)
        if identity in seen and seen[identity] != text:
            raise AuditInputError("Conflicting duplicate source occurrence; no report can conserve a selected winner")
        seen[identity] = text
    links = _rows([] if document.get("links") is None else document["links"], "links")
    decisions = _rows([] if document.get("equivalences") is None else document["equivalences"], "equivalences")
    for rows, field in ((links, "link_id"), (decisions, "decision_id")):
        ids = [_text(row.get(field), field) for row in rows]
        if len(ids) != len(set(ids)):
            raise AuditInputError(f"Duplicate {field}")
    for link in links:
        _text(link.get("relation"), "link relation")
        _selector(link.get("from"))
        _selector(link.get("to"))
    for decision in decisions:
        _text(decision.get("reason"), "decision reason")
        _selector(decision.get("left"), True)
        _selector(decision.get("right"), True)
        if decision.get("relation") not in ("same_entity", "different_entity"):
            raise AuditInputError("Unknown equivalence relation")
        locators = decision.get("evidence_locators")
        if type(locators) is not list or not locators:
            raise AuditInputError("Decision evidence_locators must be nonempty")
        for value in locators:
            _text(value, "decision evidence locator")
    # Equivalence closure, contradictions and active-decision semantics belong to
    # the canonical mapper and the independent graph conformance lane, not here.
    return records, links, decisions


def audit(document: Any, report: Any) -> dict:
    """Compare complete source data with a producer report without importing it.

    Diagnostics name JSON paths and mismatch classes, not copied evidence payloads.
    Hashes bind this check to both supplied documents; they are not signatures.
    """
    _json_value(document)
    _json_value(report)
    records, links, decisions = _validate_source(document)
    if type(report) is not dict:
        raise AuditInputError("Report must be a JSON object")
    findings = []
    checks = 0

    def check(condition: bool, code: str, path: str) -> None:
        nonlocal checks
        checks += 1
        if not condition:
            findings.append({"code": code, "path": path})

    def same(actual: Any, expected: Any, code: str, path: str) -> None:
        # Canonical equality preserves bool/int, int/float, null/empty distinctions.
        check(canonical(actual) == canonical(expected), code, path)

    def out_rows(name: str) -> list[dict]:
        value = report.get(name)
        valid = type(value) is list and len(value) <= MAX_ROWS and all(type(row) is dict for row in value)
        check(valid, "report_shape", "/" + name)
        return value if valid else []

    same(report.get("schema"), SCHEMA, "schema", "/schema")
    check(report.get("assessment_authority") is False, "authority_changed", "/assessment_authority")
    expected = {_identity(record): record for record in records}
    counts = Counter(_identity(record) for record in records)
    expected_by_oid = {_oid(identity): record for identity, record in expected.items()}
    represented = Counter()
    wrapper_by_oid = {}
    for index, wrapper in enumerate(out_rows("records")):
        path = f"/records/{index}"
        original = wrapper.get("original")
        count = wrapper.get("duplicate_count")
        valid_count = type(count) is int and count > 0
        check(valid_count, "duplicate_count_type", path + "/duplicate_count")
        if type(original) is not dict:
            check(False, "record_original_shape", path + "/original")
            continue
        if valid_count:
            represented[canonical(original)] += count
        try:
            identity = _identity(original)
        except AuditInputError:
            check(False, "record_identity_shape", path + "/original")
            continue
        oid = _oid(identity)
        same(wrapper.get("occurrence_id"), oid, "occurrence_id", path + "/occurrence_id")
        same(wrapper.get("entity_id"), "ent-" + fingerprint(list(identity[:3]), SCHEMA + "/entity"), "entity_id", path + "/entity_id")
        check(oid not in wrapper_by_oid, "duplicate_output_occurrence", path)
        wrapper_by_oid[oid] = wrapper
        same(count, counts.get(identity, 0), "duplicate_count", path + "/duplicate_count")
    same(dict(represented), dict(Counter(canonical(record) for record in records)), "record_conservation", "/records")
    same(sorted(wrapper_by_oid), sorted(expected_by_oid), "occurrence_inventory", "/records")
    extensions = {name: value for name, value in document.items() if name not in {"schema", "records", "equivalences", "links"}}
    same(report.get("extensions"), extensions, "envelope_extensions", "/extensions")
    same(sorted(canonical(d) for d in out_rows("equivalences")), sorted(canonical(d) for d in decisions), "decision_conservation", "/equivalences")

    # Group coverage and referential integrity only; no independent alias closure.
    membership = defaultdict(list)
    group_ids = set()
    for index, group in enumerate(out_rows("equivalence_groups")):
        path = f"/equivalence_groups/{index}"
        gid, members = group.get("group_id"), group.get("members")
        valid = type(gid) is str and type(members) is list and bool(members) and all(type(m) is str for m in members)
        check(valid, "group_shape", path)
        if not valid:
            continue
        check(gid not in group_ids, "duplicate_group", path)
        group_ids.add(gid)
        same(gid, "eq-" + fingerprint(sorted(members), SCHEMA + "/equivalence-snapshot"), "group_digest", path)
        for member in members:
            membership[member].append(gid)
            check(member in expected_by_oid, "group_unknown_member", path + "/members")
    same(sorted(membership), sorted(expected_by_oid), "group_inventory", "/equivalence_groups")
    for oid in sorted(expected_by_oid):
        groups = membership.get(oid, [])
        check(len(groups) == 1, "group_membership_count", "/equivalence_groups")
        wrapper = wrapper_by_oid.get(oid, {})
        same(wrapper.get("equivalence_group"), groups[0] if len(groups) == 1 else None, "record_group", "/records/" + oid)

    def resolution(query: dict, actual: Any, path: str) -> str:
        candidates = sorted(oid for oid, original in expected_by_oid.items()
                            if all(original[name] == value for name, value in query.items()))
        state = "resolved" if len(candidates) == 1 else "ambiguous" if candidates else "missing"
        if type(actual) is not dict:
            check(False, "resolution_shape", path)
            return state
        same(actual.get("selector"), query, "selector_changed", path + "/selector")
        same(actual.get("candidate_ids"), candidates, "candidate_inventory", path + "/candidate_ids")
        same(actual.get("status"), state, "resolution_status", path + "/status")
        same(actual.get("resolved_id"), candidates[0] if len(candidates) == 1 else None, "resolved_target", path + "/resolved_id")
        groups = sorted({gid for oid in candidates for gid in membership.get(oid, [])})
        same(actual.get("equivalence_groups"), groups, "resolution_group_inventory", path + "/equivalence_groups")
        return state

    actual_links = out_rows("links")
    link_index = {}
    originals = []
    for index, wrapper in enumerate(actual_links):
        lid = wrapper.get("link_id")
        valid = type(lid) is str
        check(valid, "link_id_shape", f"/links/{index}/link_id")
        if not valid:
            continue
        check(lid not in link_index, "duplicate_output_link", f"/links/{index}")
        link_index[lid] = wrapper
        originals.append(canonical(wrapper.get("original")))
    same(sorted(originals), sorted(canonical(link) for link in links), "link_conservation", "/links")
    same(sorted(link_index), sorted(link["link_id"] for link in links), "link_inventory", "/links")
    unresolved = 0
    for link in links:
        lid = link["link_id"]
        actual = link_index.get(lid, {})
        left = resolution(link["from"], actual.get("from"), "/links/" + lid + "/from")
        right = resolution(link["to"], actual.get("to"), "/links/" + lid + "/to")
        state = "resolved" if left == right == "resolved" else "unresolved"
        unresolved += state == "unresolved"
        same(actual.get("status"), state, "link_status", "/links/" + lid + "/status")
    grouped = defaultdict(list)
    for identity in expected:
        grouped[identity[1:3]].append(identity)
    collisions = [{"kind": kind, "id": original, "candidate_ids": sorted(_oid(i) for i in identities),
                   "namespaces": sorted({i[0] for i in identities}), "revisions": sorted({i[3] for i in identities})}
                  for (kind, original), identities in sorted(grouped.items()) if len(identities) > 1]
    same(sorted(canonical(row) for row in out_rows("collisions")), sorted(canonical(row) for row in collisions), "collision_inventory", "/collisions")
    expected_summary = {"input_records": len(records), "occurrences": len(expected), "collisions": len(collisions),
                        "links": len(links), "unresolved_links": unresolved}
    actual_summary = report.get("summary")
    if type(actual_summary) is not dict:
        check(False, "summary_shape", "/summary")
    else:
        for field, value in expected_summary.items():
            same(actual_summary.get(field), value, "summary_count", "/summary/" + field)
    snapshot = fingerprint({k: v for k, v in report.items() if k != "snapshot_sha256"}, SCHEMA + "/report")
    same(report.get("snapshot_sha256"), snapshot, "snapshot_digest", "/snapshot_sha256")
    return {"schema": AUDIT_SCHEMA, "status": "FAIL" if findings else "PASS",
            "assessment_authority": False, "checks": checks,
            "input_normalized_sha256": fingerprint(document), "report_normalized_sha256": fingerprint(report),
            "expected_counts": expected_summary,
            "diagnostics": sorted(findings, key=lambda item: (item["path"], item["code"])),
            "scope": "Original-record multiplicity, links, decisions, extensions, selector results, group references, collisions, summaries, snapshot integrity.",
            "excluded": ["source authenticity", "assessment conclusions", "equivalence-decision validity and transitive closure", "incremental identity stability", "approval"]}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("report", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        result = audit(load(args.input), load(args.report))
        text = json.dumps(result, sort_keys=True, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
        if args.output:
            with args.output.open("x", encoding="utf-8", newline="\n") as target:
                target.write(text)
        else:
            sys.stdout.write(text)
        return 0 if result["status"] == "PASS" else 1
    except (AuditInputError, OSError, RecursionError, UnicodeError, ValueError) as exc:
        print(f"identity-audit: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
