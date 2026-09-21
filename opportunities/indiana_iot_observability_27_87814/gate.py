"""Fail-closed pursuit compiler for Indiana IOT RFP 27-87814.

Positive readiness is source-bound: caller packets cannot mint retained evidence or
qualification. Current decisions use process-owned UTC; historical replay is diagnostic.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from types import MappingProxyType
from typing import Any, Mapping

OPPORTUNITY_ID = "27-87814"
EVENT_ID = "000670000087814"
AUTHORITIES = {
    "OFFICIAL_PUBLIC_NOTICE", "OFFICIAL_CONTROLLING_PACKAGE", "DISCOVERY_MIRROR",
    "VENDOR_PUBLIC", "OWNER_RETAINED_EVIDENCE", "INTERNAL",
}
CONTROLLING_FIELDS = {
    "submission_mechanics", "question_deadline", "prebid", "teaming_rules",
    "mandatory_requirements", "evaluation_criteria", "security_compliance",
    "pricing_forms", "insurance", "contract_terms",
}
ALLOWED_REQUIREMENT_STATES = {"UNKNOWN", "PROVEN", "GAP", "NOT_APPLICABLE", "PROPOSED"}
POSITIVE_SOURCE_AUTHORITIES = {"OFFICIAL_CONTROLLING_PACKAGE", "OWNER_RETAINED_EVIDENCE"}
AUTHORITY_MANIFEST = "authority_manifest.json"
AUTHORITY_MANIFEST_SHA256 = "4fd50658996cf65e3303d679293dd68857d1d84cf9305ee22ce02c08878c0814"
PACKAGE_ROOT = Path(__file__).resolve().parent
MAX_RETAINED_BYTES = 16 * 1024 * 1024
CURRENT_MAX_AGE_SECONDS = 300
CURRENT_FUTURE_SKEW_SECONDS = 5


class GateError(ValueError):
    pass


@dataclass(frozen=True)
class SourceBinding:
    id: str
    authority: str
    relpath: str
    sha256: str
    subject: str
    scope: str
    generation_id: str


@dataclass(frozen=True)
class EvidenceBinding:
    id: str
    source_id: str
    requirement_id: str
    subject: str
    scope: str
    generation_id: str


@dataclass(frozen=True)
class EvidenceAuthority:
    manifest_sha256: str
    generation_id: str
    sources: Mapping[str, SourceBinding]
    evidence: Mapping[str, EvidenceBinding]


def _pairs_no_dupes(pairs):
    out = {}
    for k, v in pairs:
        if k in out:
            raise GateError(f"duplicate JSON key: {k}")
        out[k] = v
    return out


def _reject_constant(v):
    raise GateError(f"non-finite JSON number: {v}")


def loads_strict(text: str) -> Any:
    try:
        return json.loads(text, object_pairs_hook=_pairs_no_dupes, parse_constant=_reject_constant)
    except GateError:
        raise
    except (json.JSONDecodeError, TypeError) as exc:
        raise GateError(str(exc)) from exc


def _freeze(value: Any, label: str = "value") -> Any:
    if value is None or type(value) in (str, bool, int):
        return value
    if type(value) is float:
        if value != value or value in (float("inf"), float("-inf")):
            raise GateError(f"{label} contains non-finite float")
        return value
    if type(value) is list:
        return [_freeze(v, f"{label}[{i}]") for i, v in enumerate(value)]
    if type(value) is dict:
        out = {}
        for k, v in value.items():
            if type(k) is not str:
                raise GateError(f"{label} keys must be exact strings")
            out[k] = _freeze(v, f"{label}.{k}")
        return out
    raise GateError(f"{label} must be an exact built-in JSON value")


def _str(v: Any, label: str) -> str:
    if type(v) is not str or not v.strip() or v != v.strip():
        raise GateError(f"{label} must be a trimmed non-empty string")
    return v


def _bool(v: Any, label: str) -> bool:
    if type(v) is not bool:
        raise GateError(f"{label} must be a JSON boolean")
    return v


def _sha(v: Any, label: str) -> str:
    s = _str(v, label)
    if len(s) != 64 or s.lower() != s or any(c not in "0123456789abcdef" for c in s):
        raise GateError(f"{label} must be lowercase sha256")
    return s


def _time(v: Any, label: str, _datetime=datetime, _timezone=timezone) -> datetime:
    s = _str(v, label)
    try:
        dt = _datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError as exc:
        raise GateError(f"{label} must be ISO-8601") from exc
    if dt.tzinfo is None:
        raise GateError(f"{label} must include timezone")
    return dt.astimezone(_timezone.utc)


def _safe_relpath(v: Any, label: str) -> str:
    s = _str(v, label)
    p = PurePosixPath(s)
    if p.is_absolute() or not p.parts or any(x in ("", ".", "..") for x in p.parts):
        raise GateError(f"{label} must be a safe relative path")
    return s


def _expect_keys(obj: dict, required: set[str], label: str) -> None:
    if set(obj) != required:
        missing = sorted(required - set(obj))
        extra = sorted(set(obj) - required)
        raise GateError(f"{label} keys mismatch missing={missing} extra={extra}")


def _read_retained(root: Path, relpath: str) -> bytes:
    """Read one ordinary single-link file under a fixed package root without symlink leaves."""
    rel = PurePosixPath(_safe_relpath(relpath, "retained relpath"))
    root_fd = os.open(
        os.fspath(root),
        os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0),
    )
    fd = root_fd
    try:
        for part in rel.parts[:-1]:
            child = os.open(
                part,
                os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0),
                dir_fd=fd,
            )
            if fd != root_fd:
                os.close(fd)
            fd = child
        leaf = os.open(rel.parts[-1], os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0), dir_fd=fd)
        try:
            before = os.fstat(leaf)
            if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
                raise GateError(f"retained source must be ordinary single-link file: {relpath}")
            if before.st_size > MAX_RETAINED_BYTES:
                raise GateError(f"retained source too large: {relpath}")
            chunks, remaining = [], MAX_RETAINED_BYTES + 1
            while remaining:
                b = os.read(leaf, min(1024 * 1024, remaining))
                if not b:
                    break
                chunks.append(b)
                remaining -= len(b)
            data = b"".join(chunks)
            after = os.fstat(leaf)
            identity = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
            if identity(before) != identity(after) or len(data) != before.st_size:
                raise GateError(f"retained source changed during read: {relpath}")
            return data
        finally:
            os.close(leaf)
    finally:
        if fd != root_fd:
            os.close(fd)
        os.close(root_fd)


def _parse_authority(raw: bytes, root: Path, expected_sha256: str) -> EvidenceAuthority:
    got = hashlib.sha256(raw).hexdigest()
    if got != expected_sha256:
        raise GateError("authority manifest does not match source-literal pinned root")
    try:
        doc = loads_strict(raw.decode("utf-8"))
    except UnicodeDecodeError as exc:
        raise GateError("authority manifest must be UTF-8") from exc
    doc = _freeze(doc, "authority manifest")
    if type(doc) is not dict:
        raise GateError("authority manifest must be object")
    _expect_keys(doc, {"schema", "opportunity_id", "event_id", "generation_id", "sources", "evidence"}, "authority manifest")
    if doc["schema"] != "indiana-iot-observability-authority/v1":
        raise GateError("authority manifest schema mismatch")
    if doc["opportunity_id"] != OPPORTUNITY_ID or doc["event_id"] != EVENT_ID:
        raise GateError("authority manifest identity mismatch")
    generation = _str(doc["generation_id"], "authority generation_id")
    if type(doc["sources"]) is not list or type(doc["evidence"]) is not list:
        raise GateError("authority sources/evidence must be arrays")

    sources = {}
    for i, row in enumerate(doc["sources"]):
        if type(row) is not dict:
            raise GateError(f"authority sources[{i}] must be object")
        _expect_keys(row, {"id", "authority", "relpath", "sha256", "subject", "scope", "generation_id"}, f"authority sources[{i}]")
        sid = _str(row["id"], f"authority sources[{i}].id")
        if sid in sources:
            raise GateError(f"duplicate authority source id: {sid}")
        authority = _str(row["authority"], f"{sid}.authority")
        if authority not in POSITIVE_SOURCE_AUTHORITIES:
            raise GateError(f"{sid} cannot be a positive retained authority")
        if row["subject"] != OPPORTUNITY_ID or row["generation_id"] != generation:
            raise GateError(f"{sid} subject/generation mismatch")
        relpath = _safe_relpath(row["relpath"], f"{sid}.relpath")
        digest = _sha(row["sha256"], f"{sid}.sha256")
        data = _read_retained(root, relpath)
        if hashlib.sha256(data).hexdigest() != digest:
            raise GateError(f"retained source digest mismatch: {sid}")
        sources[sid] = SourceBinding(
            sid, authority, relpath, digest, OPPORTUNITY_ID,
            _str(row["scope"], f"{sid}.scope"), generation,
        )

    evidence = {}
    for i, row in enumerate(doc["evidence"]):
        if type(row) is not dict:
            raise GateError(f"authority evidence[{i}] must be object")
        _expect_keys(row, {"id", "source_id", "requirement_id", "subject", "scope", "generation_id"}, f"authority evidence[{i}]")
        eid = _str(row["id"], f"authority evidence[{i}].id")
        if eid in evidence:
            raise GateError(f"duplicate evidence id: {eid}")
        source_id = _str(row["source_id"], f"{eid}.source_id")
        if source_id not in sources:
            raise GateError(f"{eid} source is not authenticated")
        if row["subject"] != OPPORTUNITY_ID or row["generation_id"] != generation:
            raise GateError(f"{eid} subject/generation mismatch")
        if row["scope"] != sources[source_id].scope:
            raise GateError(f"{eid} scope does not match source scope")
        evidence[eid] = EvidenceBinding(
            eid, source_id, _str(row["requirement_id"], f"{eid}.requirement_id"),
            OPPORTUNITY_ID, row["scope"], generation,
        )
    return EvidenceAuthority(got, generation, MappingProxyType(sources), MappingProxyType(evidence))


def _load_authority(root: Path = PACKAGE_ROOT, expected_sha256: str = AUTHORITY_MANIFEST_SHA256) -> EvidenceAuthority:
    return _parse_authority(_read_retained(root, AUTHORITY_MANIFEST), root, expected_sha256)


def _sources(ledger: Mapping[str, Any], authority: EvidenceAuthority):
    ledger = _freeze(ledger, "source ledger")
    if type(ledger) is not dict or ledger.get("opportunity_id") != OPPORTUNITY_ID or ledger.get("event_id") != EVENT_ID:
        raise GateError("source ledger identity mismatch")
    rows = ledger.get("sources")
    if type(rows) is not list:
        raise GateError("sources must be array")
    out = {}
    authenticated_seen = set()
    for i, row in enumerate(rows):
        if type(row) is not dict:
            raise GateError(f"sources[{i}] must be object")
        sid = _str(row.get("id"), f"sources[{i}].id")
        if sid in out:
            raise GateError(f"duplicate source id: {sid}")
        source_authority = _str(row.get("authority"), f"{sid}.authority")
        if source_authority not in AUTHORITIES:
            raise GateError(f"unsupported authority: {source_authority}")
        retained = _bool(row.get("retained"), f"{sid}.retained")
        _str(row.get("url"), f"{sid}.url")
        claims, controls = row.get("claims", {}), row.get("controls", [])
        if type(claims) is not dict or type(controls) is not list or any(type(x) is not str for x in controls):
            raise GateError(f"{sid} claims/controls malformed")
        if len(controls) != len(set(controls)):
            raise GateError(f"{sid}.controls duplicates")
        binding = authority.sources.get(sid)
        if retained and binding is None:
            raise GateError(f"{sid} retained=true is not authenticated by the pinned authority root")
        if binding is not None:
            if not retained or binding.authority != source_authority:
                raise GateError(f"{sid} authenticated source does not match source-ledger assertion")
            authenticated_seen.add(sid)
        elif controls:
            raise GateError(f"{sid} cannot control fields without authenticated retained bytes")
        if source_authority != "OFFICIAL_CONTROLLING_PACKAGE" and CONTROLLING_FIELDS.intersection(controls):
            raise GateError(f"{sid} cannot control package-only fields")
        out[sid] = row
    if authenticated_seen != set(authority.sources):
        raise GateError("source ledger does not expose the complete authenticated retained-source inventory")
    return out


def _requirements(doc: Mapping[str, Any], authority: EvidenceAuthority):
    doc = _freeze(doc, "requirements")
    if type(doc) is not dict or doc.get("opportunity_id") != OPPORTUNITY_ID:
        raise GateError("requirements identity mismatch")
    rows = doc.get("requirements")
    if type(rows) is not list:
        raise GateError("requirements must be array")
    out = {}
    used = set()
    for i, row in enumerate(rows):
        if type(row) is not dict:
            raise GateError(f"requirements[{i}] must be object")
        rid = _str(row.get("id"), f"requirements[{i}].id")
        if rid in out:
            raise GateError(f"duplicate requirement id: {rid}")
        state = _str(row.get("state"), f"{rid}.state")
        if state not in ALLOWED_REQUIREMENT_STATES:
            raise GateError(f"{rid}.state unsupported")
        ev = row.get("evidence")
        if type(ev) is not list or any(type(x) is not str or not x for x in ev) or len(ev) != len(set(ev)):
            raise GateError(f"{rid}.evidence must be unique string array")
        if state == "PROVEN" and not ev:
            raise GateError(f"{rid} PROVEN requires retained evidence")
        if state != "PROVEN" and ev:
            raise GateError(f"{rid} non-PROVEN cannot carry positive evidence")
        for eid in ev:
            binding = authority.evidence.get(eid)
            if binding is None:
                raise GateError(f"{rid} evidence {eid} is not authenticated")
            if binding.requirement_id != rid:
                raise GateError(f"{eid} is bound to another requirement")
            if eid in used:
                raise GateError(f"{eid} cannot be reused across requirements")
            used.add(eid)
        out[rid] = row
    return out


def _receipt(report: Mapping[str, Any]) -> str:
    base = dict(report)
    base.pop("receipt_sha256", None)
    return hashlib.sha256(json.dumps(base, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def _compile(
    ledger: Mapping[str, Any], requirements: Mapping[str, Any], partners: Mapping[str, Any],
    scope: Mapping[str, Any], *, authority: EvidenceAuthority, evaluation_dt: datetime, current: bool,
):
    sources = _sources(ledger, authority)
    reqs = _requirements(requirements, authority)
    partners = _freeze(partners, "partners")
    scope = _freeze(scope, "scope")
    if type(partners) is not dict or partners.get("opportunity_id") != OPPORTUNITY_ID or type(partners.get("targets")) is not list:
        raise GateError("partner targets identity/shape mismatch")
    targets = partners["targets"]
    for i, target in enumerate(targets):
        if type(target) is not dict:
            raise GateError(f"targets[{i}] malformed")
        _str(target.get("name"), f"targets[{i}].name")
        if target.get("status") != "RESEARCH_TARGET_NO_CONTACT" or target.get("contact_authority") is not False:
            raise GateError("partner target may not claim contact or selection")
    if type(scope) is not dict or scope.get("opportunity_id") != OPPORTUNITY_ID or scope.get("status") != "TEMPLATE_NOT_OFFER":
        raise GateError("paid specialist scope must remain a non-offer template")
    if scope.get("price_usd") is not None:
        raise GateError("template price must remain unset before partner discovery")

    package = sources.get("idoa-bid-package")
    binding = authority.sources.get("idoa-bid-package")
    package_retained = bool(
        package and binding and package["authority"] == "OFFICIAL_CONTROLLING_PACKAGE"
        and binding.authority == "OFFICIAL_CONTROLLING_PACKAGE"
    )
    proven = {rid for rid, row in reqs.items() if row["state"] == "PROVEN"}
    required_prime = {
        "controlling_package", "submission_mechanics", "questions_and_prebid", "teaming_rules",
        "prime_platform_qualification", "security_compliance", "staffing_capacity", "pricing_forms",
    }
    prime_candidate = package_retained and required_prime.issubset(proven)
    teaming_candidate = package_retained and {"teaming_rules", "paid_specialist_workshare"}.issubset(proven)
    decision, reasons = "HOLD", []
    if not package_retained:
        reasons.append("CONTROLLING_PACKAGE_NOT_RETAINED")
    if not prime_candidate:
        reasons.append("PRIME_QUALIFICATION_NOT_PROVEN")
    if current:
        if prime_candidate:
            decision = "PRIME_REVIEW_READY"
        if teaming_candidate:
            decision = "TEAMING_REVIEW_READY"
    elif prime_candidate or teaming_candidate:
        reasons.append("HISTORICAL_EVALUATION_NOT_CURRENT")

    mirror = [
        {"source_id": sid, "claims": src.get("claims", {}), "authority": "DISCOVERY_ONLY"}
        for sid, src in sorted(sources.items()) if src["authority"] == "DISCOVERY_MIRROR"
    ]
    work_orders = []
    if not package_retained:
        work_orders += [
            {"id": "RETAIN_CONTROLLING_STATE_ZIP", "priority": 1},
            {"id": "BIND_QUESTION_PREBID_SUBMISSION_TIMELINE", "priority": 2},
            {"id": "BIND_TEAMING_SECURITY_PRICING_EVALUATION_TERMS", "priority": 3},
        ]
    work_orders += [
        {"id": "QUALIFY_PLATFORM_OR_PRIME_PARTNER", "priority": 4},
        {"id": "PACKAGE_PAID_SPECIALIST_WORKSHARE", "priority": 5},
    ]
    external_authority = {k: False for k in (
        "buyer_contact", "vendor_contact", "partner_contact", "prebid_registration",
        "question_submission", "proposal_submission", "pricing_commitment", "signature",
        "award", "payment", "revenue",
    )}
    report = {
        "schema": "indiana-iot-observability-pursuit/v2",
        "opportunity_id": OPPORTUNITY_ID,
        "event_id": EVENT_ID,
        "evaluation_time": evaluation_dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
        "evaluation_mode": "CURRENT_PROCESS_TIME" if current else "HISTORICAL_CALLER_TIME",
        "decision": decision,
        "reasons": sorted(set(reasons)),
        "package_retained": package_retained,
        "authority_manifest_sha256": authority.manifest_sha256,
        "authority_generation_id": authority.generation_id,
        "authenticated_source_ids": sorted(authority.sources),
        "authenticated_evidence_ids": sorted(authority.evidence),
        "mirror_intelligence": mirror,
        "partner_research_targets": [t["name"] for t in targets],
        "work_orders": work_orders,
        "external_authority": external_authority,
    }
    report["receipt_sha256"] = _receipt(report)
    return report


def _make_public(loader, compiler, clock, freezer, receipt_fn):
    def compile_pursuit(ledger, requirements, partners, scope, *, now: str):
        return compiler(
            ledger, requirements, partners, scope,
            authority=loader(), evaluation_dt=_time(now, "now"), current=False,
        )

    def compile_current(ledger, requirements, partners, scope):
        return compiler(
            ledger, requirements, partners, scope,
            authority=loader(), evaluation_dt=clock(timezone.utc), current=True,
        )

    def verify_pursuit(packet, ledger, requirements, partners, scope) -> bool:
        try:
            frozen = freezer(packet, "packet")
            if type(frozen) is not dict or type(frozen.get("receipt_sha256")) is not str:
                return False
            if receipt_fn(frozen) != frozen["receipt_sha256"]:
                return False
            authority = loader()
            if frozen.get("authority_manifest_sha256") != authority.manifest_sha256:
                return False
            if frozen.get("authority_generation_id") != authority.generation_id:
                return False
            mode = frozen.get("evaluation_mode")
            dt = _time(frozen.get("evaluation_time"), "packet.evaluation_time")
            if mode == "CURRENT_PROCESS_TIME":
                fresh_now = clock(timezone.utc)
                age = (fresh_now - dt).total_seconds()
                if age > CURRENT_MAX_AGE_SECONDS or age < -CURRENT_FUTURE_SKEW_SECONDS:
                    return False
                current = True
            elif mode == "HISTORICAL_CALLER_TIME":
                current = False
            else:
                return False
            expected = compiler(
                ledger, requirements, partners, scope,
                authority=authority, evaluation_dt=dt, current=current,
            )
            return frozen == expected
        except (GateError, OSError, UnicodeError, ValueError):
            return False

    return compile_pursuit, compile_current, verify_pursuit


compile_pursuit, compile_current, verify_pursuit = _make_public(
    _load_authority, _compile, datetime.now, _freeze, _receipt,
)
del _make_public


def _read(path: Path):
    try:
        return loads_strict(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError) as exc:
        raise GateError(f"cannot read {path}: {exc}") from exc


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--ledger", type=Path, required=True)
    ap.add_argument("--requirements", type=Path, required=True)
    ap.add_argument("--partners", type=Path, required=True)
    ap.add_argument("--scope", type=Path, required=True)
    ap.add_argument("--historical-now", help="diagnostic replay only; readiness remains HOLD")
    ns = ap.parse_args(argv)
    inputs = (_read(ns.ledger), _read(ns.requirements), _read(ns.partners), _read(ns.scope))
    packet = compile_pursuit(*inputs, now=ns.historical_now) if ns.historical_now else compile_current(*inputs)
    print(json.dumps(packet, sort_keys=True, separators=(",", ":"), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
