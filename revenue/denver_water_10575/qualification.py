#!/usr/bin/env python3
"""Deterministic, evidence-bound qualification for Denver Water solicitation 10575.

This module is deliberately offline. It does not fetch buyer documents, contact a
buyer, sign into BidNet, submit a proposal, or assert qualifications that were not
supplied as evidence. Secondary discovery sources can describe candidate gates but
cannot satisfy a buyer-mandatory gate.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA = "denver-water-10575-qualification/v1"
RECEIPT_SCHEMA = "denver-water-10575-qualification-receipt/v1"
SOURCE_CLASSES = {"OFFICIAL_NOTICE", "OFFICIAL_PACKET", "OFFICIAL_ADDENDUM", "SECONDARY"}
SOURCE_STATES = {"OBSERVED", "ACQUIRED", "SUPERSEDED"}
ROUTES = {"PRIME", "TEAMING", "BOTH"}
EVIDENCE_STATES = {"PROVEN", "MISSING", "UNKNOWN", "FAILED"}
CURE_POLICIES = {"NONE", "PARTNER_CURABLE", "OWNER_CURABLE"}
DISPOSITIONS = {"PRIME_READY", "TEAMING_READY", "HOLD", "NO_BID"}
HEX64 = re.compile(r"^[0-9a-f]{64}$")
ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
URL_RE = re.compile(r"^https://[^\s]+$")
MAX_BYTES = 1_000_000

class QualificationError(ValueError):
    pass


def _plain_int(v: Any) -> bool:
    return type(v) is int


def _require_exact_keys(obj: dict[str, Any], expected: set[str], where: str) -> None:
    actual = set(obj)
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        raise QualificationError(f"{where}: key mismatch missing={missing} extra={extra}")


def _req_str(v: Any, where: str, *, max_len: int = 512) -> str:
    if type(v) is not str or not v or len(v) > max_len:
        raise QualificationError(f"{where}: expected non-empty string <= {max_len}")
    if "\x00" in v:
        raise QualificationError(f"{where}: NUL not allowed")
    return v


def _req_id(v: Any, where: str) -> str:
    s = _req_str(v, where, max_len=128)
    if not ID_RE.fullmatch(s):
        raise QualificationError(f"{where}: invalid identifier")
    return s


def _req_sha(v: Any, where: str) -> str:
    s = _req_str(v, where, max_len=64)
    if not HEX64.fullmatch(s):
        raise QualificationError(f"{where}: expected lowercase sha256")
    return s


def _req_url(v: Any, where: str) -> str:
    s = _req_str(v, where, max_len=1024)
    if not URL_RE.fullmatch(s):
        raise QualificationError(f"{where}: expected https URL")
    return s


def _parse_time(v: Any, where: str) -> datetime:
    s = _req_str(v, where, max_len=32)
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", s):
        raise QualificationError(f"{where}: expected canonical UTC seconds")
    dt = datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    if dt.strftime("%Y-%m-%dT%H:%M:%SZ") != s:
        raise QualificationError(f"{where}: noncanonical UTC")
    return dt


def _canonical_bytes(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _sha_obj(obj: Any) -> str:
    return hashlib.sha256(_canonical_bytes(obj)).hexdigest()


def _object_pairs_no_dupes(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in pairs:
        if k in out:
            raise QualificationError(f"duplicate JSON key: {k}")
        out[k] = v
    return out


def load_json_bytes(raw: bytes) -> Any:
    if type(raw) is not bytes or len(raw) > MAX_BYTES:
        raise QualificationError("input bytes missing or too large")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise QualificationError("input must be UTF-8") from exc
    try:
        return json.loads(
            text,
            object_pairs_hook=_object_pairs_no_dupes,
            parse_constant=lambda x: (_ for _ in ()).throw(QualificationError(f"nonfinite JSON number: {x}")),
        )
    except QualificationError:
        raise
    except Exception as exc:
        raise QualificationError(f"invalid JSON: {exc}") from exc


def _validate_source(src: Any, as_of: datetime, where: str) -> dict[str, Any]:
    if type(src) is not dict:
        raise QualificationError(f"{where}: source must be object")
    _require_exact_keys(src, {"id", "class", "state", "url", "captured_at", "sha256", "label"}, where)
    sid = _req_id(src["id"], f"{where}.id")
    cls = _req_str(src["class"], f"{where}.class", max_len=32)
    state = _req_str(src["state"], f"{where}.state", max_len=32)
    if cls not in SOURCE_CLASSES or state not in SOURCE_STATES:
        raise QualificationError(f"{where}: invalid source class/state")
    url = _req_url(src["url"], f"{where}.url")
    captured = _parse_time(src["captured_at"], f"{where}.captured_at")
    if captured > as_of:
        raise QualificationError(f"{where}: future source capture")
    digest = src["sha256"]
    if digest is not None:
        digest = _req_sha(digest, f"{where}.sha256")
    if state == "ACQUIRED" and cls in {"OFFICIAL_PACKET", "OFFICIAL_ADDENDUM"} and digest is None:
        raise QualificationError(f"{where}: acquired controlling source requires digest")
    label = _req_str(src["label"], f"{where}.label", max_len=160)
    return {"id": sid, "class": cls, "state": state, "url": url, "captured_at": src["captured_at"], "sha256": digest, "label": label}


def _validate_evidence(ev: Any, as_of: datetime, where: str) -> dict[str, Any]:
    if type(ev) is not dict:
        raise QualificationError(f"{where}: evidence must be object")
    _require_exact_keys(ev, {"id", "state", "observed_at", "sha256", "ref"}, where)
    eid = _req_id(ev["id"], f"{where}.id")
    state = _req_str(ev["state"], f"{where}.state", max_len=16)
    if state not in EVIDENCE_STATES:
        raise QualificationError(f"{where}: invalid evidence state")
    observed = _parse_time(ev["observed_at"], f"{where}.observed_at")
    if observed > as_of:
        raise QualificationError(f"{where}: future evidence")
    digest = ev["sha256"]
    ref = ev["ref"]
    if state == "PROVEN":
        digest = _req_sha(digest, f"{where}.sha256")
        ref = _req_str(ref, f"{where}.ref", max_len=240)
    else:
        if digest is not None or ref is not None:
            raise QualificationError(f"{where}: non-PROVEN evidence cannot carry proof fields")
    return {"id": eid, "state": state, "observed_at": ev["observed_at"], "sha256": digest, "ref": ref}


def _validate_gate(gate: Any, source_ids: set[str], as_of: datetime, where: str) -> dict[str, Any]:
    if type(gate) is not dict:
        raise QualificationError(f"{where}: gate must be object")
    _require_exact_keys(
        gate,
        {"id", "title", "route", "mandatory", "cure", "requirement_source_id", "evidence"},
        where,
    )
    gid = _req_id(gate["id"], f"{where}.id")
    title = _req_str(gate["title"], f"{where}.title", max_len=180)
    route = _req_str(gate["route"], f"{where}.route", max_len=16)
    cure = _req_str(gate["cure"], f"{where}.cure", max_len=32)
    if route not in ROUTES or cure not in CURE_POLICIES:
        raise QualificationError(f"{where}: invalid route/cure")
    if type(gate["mandatory"]) is not bool:
        raise QualificationError(f"{where}.mandatory: expected bool")
    src_id = _req_id(gate["requirement_source_id"], f"{where}.requirement_source_id")
    if src_id not in source_ids:
        raise QualificationError(f"{where}: unknown requirement source")
    ev = _validate_evidence(gate["evidence"], as_of, f"{where}.evidence")
    return {
        "id": gid,
        "title": title,
        "route": route,
        "mandatory": gate["mandatory"],
        "cure": cure,
        "requirement_source_id": src_id,
        "evidence": ev,
    }


def _gate_applies(g: dict[str, Any], route: str) -> bool:
    return g["route"] in {route, "BOTH"}


def _source_can_authorize_requirement(src: dict[str, Any]) -> bool:
    return src["class"] in {"OFFICIAL_PACKET", "OFFICIAL_ADDENDUM"} and src["state"] == "ACQUIRED" and src["sha256"] is not None


def evaluate(payload: Any) -> dict[str, Any]:
    if type(payload) is not dict:
        raise QualificationError("root must be object")
    _require_exact_keys(payload, {"schema", "opportunity", "sources", "gates"}, "root")
    if payload["schema"] != SCHEMA:
        raise QualificationError("unsupported schema")

    opp = payload["opportunity"]
    if type(opp) is not dict:
        raise QualificationError("opportunity must be object")
    _require_exact_keys(opp, {"id", "solicitation_id", "title", "as_of", "proposal_deadline"}, "opportunity")
    oid = _req_id(opp["id"], "opportunity.id")
    sid = _req_id(opp["solicitation_id"], "opportunity.solicitation_id")
    title = _req_str(opp["title"], "opportunity.title", max_len=240)
    as_of = _parse_time(opp["as_of"], "opportunity.as_of")
    deadline = _parse_time(opp["proposal_deadline"], "opportunity.proposal_deadline")

    sources_raw = payload["sources"]
    gates_raw = payload["gates"]
    if type(sources_raw) is not list or type(gates_raw) is not list or not sources_raw or not gates_raw:
        raise QualificationError("sources and gates must be non-empty arrays")
    if len(sources_raw) > 128 or len(gates_raw) > 256:
        raise QualificationError("too many sources/gates")

    sources = [_validate_source(s, as_of, f"sources[{i}]") for i, s in enumerate(sources_raw)]
    source_map: dict[str, dict[str, Any]] = {}
    for src in sources:
        if src["id"] in source_map:
            raise QualificationError(f"duplicate source id: {src['id']}")
        source_map[src["id"]] = src

    gates = [_validate_gate(g, set(source_map), as_of, f"gates[{i}]") for i, g in enumerate(gates_raw)]
    gate_ids: set[str] = set()
    evidence_ids: dict[str, str] = {}
    for gate in gates:
        if gate["id"] in gate_ids:
            raise QualificationError(f"duplicate gate id: {gate['id']}")
        gate_ids.add(gate["id"])
        eid = gate["evidence"]["id"]
        digest = _sha_obj(gate["evidence"])
        if eid in evidence_ids and evidence_ids[eid] != digest:
            raise QualificationError(f"conflicting evidence id: {eid}")
        evidence_ids[eid] = digest

    official_packet_ids = sorted(
        s["id"] for s in sources if s["class"] == "OFFICIAL_PACKET" and s["state"] == "ACQUIRED" and s["sha256"]
    )
    official_addenda_ids = sorted(
        s["id"] for s in sources if s["class"] == "OFFICIAL_ADDENDUM" and s["state"] == "ACQUIRED" and s["sha256"]
    )
    controlling_packet_acquired = bool(official_packet_ids)

    reasons: list[str] = []
    route_detail: dict[str, Any] = {}

    if as_of >= deadline:
        disposition = "NO_BID"
        reasons.append("PROPOSAL_DEADLINE_EXPIRED")
    elif not controlling_packet_acquired:
        disposition = "HOLD"
        reasons.append("CONTROLLING_PACKET_NOT_ACQUIRED")
    else:
        route_results: dict[str, dict[str, Any]] = {}
        for route in ("PRIME", "TEAMING"):
            holds: list[str] = []
            failures: list[str] = []
            curable_failures: list[str] = []
            passed: list[str] = []
            for gate in sorted((g for g in gates if g["mandatory"] and _gate_applies(g, route)), key=lambda x: x["id"]):
                req_src = source_map[gate["requirement_source_id"]]
                if not _source_can_authorize_requirement(req_src):
                    holds.append(f"{gate['id']}:REQUIREMENT_NOT_OFFICIAL")
                    continue
                state = gate["evidence"]["state"]
                if state == "PROVEN":
                    passed.append(gate["id"])
                elif state == "FAILED":
                    if route == "PRIME" and gate["cure"] == "PARTNER_CURABLE":
                        curable_failures.append(gate["id"])
                    else:
                        failures.append(gate["id"])
                else:
                    holds.append(f"{gate['id']}:{state}")
            status = "PASS" if not holds and not failures and not curable_failures else "HOLD"
            if failures:
                status = "FAIL"
            elif route == "PRIME" and curable_failures:
                status = "PARTNER_GAP"
            route_results[route] = {
                "status": status,
                "passed_gate_ids": passed,
                "hold_reasons": holds,
                "failed_gate_ids": failures,
                "partner_curable_failed_gate_ids": curable_failures,
            }
        route_detail = route_results
        prime = route_results["PRIME"]
        team = route_results["TEAMING"]
        if prime["status"] == "PASS":
            disposition = "PRIME_READY"
            reasons.append("ALL_OFFICIAL_PRIME_GATES_PROVEN")
        elif team["status"] == "PASS" and prime["status"] in {"PARTNER_GAP", "FAIL", "HOLD"}:
            disposition = "TEAMING_READY"
            reasons.append("OFFICIAL_TEAMING_GATES_PROVEN")
            if prime["status"] == "PARTNER_GAP":
                reasons.append("PRIME_HAS_PARTNER_CURABLE_GAPS")
        elif prime["status"] == "FAIL" and team["status"] == "FAIL":
            disposition = "NO_BID"
            reasons.append("BOTH_ROUTES_HAVE_NONCURABLE_MANDATORY_FAILURES")
        else:
            disposition = "HOLD"
            reasons.append("MANDATORY_EVIDENCE_INCOMPLETE")

    normalized_payload = {
        "schema": SCHEMA,
        "opportunity": {"id": oid, "solicitation_id": sid, "title": title, "as_of": opp["as_of"], "proposal_deadline": opp["proposal_deadline"]},
        "sources": sorted(sources, key=lambda x: x["id"]),
        "gates": sorted(gates, key=lambda x: x["id"]),
    }
    receipt_core = {
        "schema": RECEIPT_SCHEMA,
        "opportunity_id": oid,
        "solicitation_id": sid,
        "as_of": opp["as_of"],
        "proposal_deadline": opp["proposal_deadline"],
        "input_sha256": _sha_obj(normalized_payload),
        "controlling_packet_acquired": controlling_packet_acquired,
        "official_packet_source_ids": official_packet_ids,
        "official_addendum_source_ids": official_addenda_ids,
        "disposition": disposition,
        "reasons": sorted(set(reasons)),
        "route_detail": route_detail,
        "authority": {
            "buyer_contact": False,
            "portal_action": False,
            "proposal_submission": False,
            "pricing_commitment": False,
            "certification_or_reference_claim": False,
            "contract_acceptance": False,
            "spend": False,
            "award_or_revenue_claim": False,
        },
    }
    receipt = dict(receipt_core)
    receipt["receipt_sha256"] = _sha_obj(receipt_core)
    return receipt


def verify(payload: Any, receipt: Any) -> dict[str, Any]:
    if type(receipt) is not dict:
        raise QualificationError("receipt must be object")
    expected = evaluate(payload)
    if receipt != expected:
        raise QualificationError("receipt mismatch/tamper")
    return expected


def _bounded_read(path: Path) -> bytes:
    st = path.stat(follow_symlinks=False)
    if not stat.S_ISREG(st.st_mode):
        raise QualificationError(f"not a regular file: {path}")
    if st.st_size > MAX_BYTES:
        raise QualificationError(f"file too large: {path}")
    return path.read_bytes()


def _exclusive_write(path: Path, data: bytes) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(path, flags, 0o600)
    try:
        os.write(fd, data)
    finally:
        os.close(fd)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("compile")
    c.add_argument("--input", required=True)
    c.add_argument("--output", required=True)
    v = sub.add_parser("verify")
    v.add_argument("--input", required=True)
    v.add_argument("--receipt", required=True)
    args = p.parse_args(argv)

    payload = load_json_bytes(_bounded_read(Path(args.input)))
    if args.cmd == "compile":
        receipt = evaluate(payload)
        _exclusive_write(Path(args.output), json.dumps(receipt, indent=2, sort_keys=True).encode("utf-8") + b"\n")
        return 0
    receipt = load_json_bytes(_bounded_read(Path(args.receipt)))
    verify(payload, receipt)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
