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
            raise _error(f"duplicate JSON key: {k}")
        out[k] = v
    return out


def _reject_constant(v):
    raise _error(f"non-finite JSON number: {v}")


def _ensure_utf8_tree(value: Any, label: str = "json") -> Any:
    """Reject lone surrogates before any later canonical UTF-8 encoding."""
    def visit(v: Any, where: str) -> None:
        if type(v) is str:
            try:
                v.encode("utf-8", "strict")
            except UnicodeEncodeError as exc:
                raise _error(f"{where} contains invalid Unicode") from exc
            return
        if type(v) is list:
            for i, item in enumerate(v):
                visit(item, f"{where}[{i}]")
            return
        if type(v) is dict:
            for key, item in v.items():
                if type(key) is not str:
                    raise _error(f"{where} keys must be exact strings")
                visit(key, f"{where}.<key>")
                visit(item, f"{where}.{key}")
    visit(value, label)
    return value


def loads_strict(
    text: str,
    _json_loads=json.loads,
    _pairs_hook=_pairs_no_dupes,
    _constant_hook=_reject_constant,
    _utf8_tree=_ensure_utf8_tree,
    _json_error=json.JSONDecodeError,
    _error=GateError,
) -> Any:
    try:
        value = _json_loads(
            text,
            object_pairs_hook=_pairs_hook,
            parse_constant=_constant_hook,
        )
        return _utf8_tree(value)
    except _error:
        raise
    except (_json_error, TypeError, ValueError, RecursionError) as exc:
        raise _error(str(exc)) from exc


def _freeze(value: Any, label: str = "value", _error=GateError) -> Any:
    def visit(v: Any, where: str) -> Any:
        if v is None or type(v) in (bool, int):
            return v
        if type(v) is str:
            try:
                v.encode("utf-8", "strict")
            except UnicodeEncodeError as exc:
                raise _error(f"{where} contains invalid Unicode") from exc
            return v
        if type(v) is float:
            if v != v or v in (float("inf"), float("-inf")):
                raise _error(f"{where} contains non-finite float")
            return v
        if type(v) is list:
            return [visit(item, f"{where}[{i}]") for i, item in enumerate(v)]
        if type(v) is dict:
            out = {}
            for key, item in v.items():
                if type(key) is not str:
                    raise _error(f"{where} keys must be exact strings")
                try:
                    key.encode("utf-8", "strict")
                except UnicodeEncodeError as exc:
                    raise _error(f"{where} key contains invalid Unicode") from exc
                out[key] = visit(item, f"{where}.{key}")
            return out
        raise _error(f"{where} must be an exact built-in JSON value")

    return visit(value, label)


def _str(v: Any, label: str) -> str:
    if type(v) is not str or not v.strip() or v != v.strip():
        raise _error(f"{label} must be a trimmed non-empty string")
    return v


def _bool(v: Any, label: str) -> bool:
    if type(v) is not bool:
        raise _error(f"{label} must be a JSON boolean")
    return v


def _sha(v: Any, label: str) -> str:
    s = _str(v, label)
    if len(s) != 64 or s.lower() != s or any(c not in "0123456789abcdef" for c in s):
        raise _error(f"{label} must be lowercase sha256")
    return s


def _time(v: Any, label: str, _datetime=datetime, _timezone=timezone) -> datetime:
    s = _str(v, label)
    try:
        dt = _datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError as exc:
        raise _error(f"{label} must be ISO-8601") from exc
    if dt.tzinfo is None:
        raise _error(f"{label} must include timezone")
    return dt.astimezone(_timezone.utc)


def _safe_relpath(v: Any, label: str) -> str:
    s = _str(v, label)
    p = PurePosixPath(s)
    if p.is_absolute() or not p.parts or any(x in ("", ".", "..") for x in p.parts):
        raise _error(f"{label} must be a safe relative path")
    return s


def _expect_keys(obj: dict, required: set[str], label: str) -> None:
    if set(obj) != required:
        missing = sorted(required - set(obj))
        extra = sorted(set(obj) - required)
        raise _error(f"{label} keys mismatch missing={missing} extra={extra}")


def _read_retained(
    root: Path,
    relpath: str,
    _safe_relpath_fn=_safe_relpath,
    _pure_path=PurePosixPath,
    _os_open=os.open,
    _os_fspath=os.fspath,
    _os_close=os.close,
    _os_fstat=os.fstat,
    _os_read=os.read,
    _o_rdonly=os.O_RDONLY,
    _o_directory=getattr(os, "O_DIRECTORY", 0),
    _o_nofollow=getattr(os, "O_NOFOLLOW", None),
    _is_regular=stat.S_ISREG,
    _max_bytes=MAX_RETAINED_BYTES,
    _error=GateError,
) -> bytes:
    """Read one source through an import-bound no-follow descriptor generation."""
    if _o_nofollow is None:
        raise _error("platform lacks O_NOFOLLOW; refusing retained evidence reads")
    rel = _pure_path(_safe_relpath_fn(relpath, "retained relpath"))
    root_fd = _os_open(
        _os_fspath(root),
        _o_rdonly | _o_directory | _o_nofollow,
    )
    fd = root_fd
    try:
        for part in rel.parts[:-1]:
            child = _os_open(
                part,
                _o_rdonly | _o_directory | _o_nofollow,
                dir_fd=fd,
            )
            if fd != root_fd:
                _os_close(fd)
            fd = child
        leaf = _os_open(rel.parts[-1], _o_rdonly | _o_nofollow, dir_fd=fd)
        try:
            before = _os_fstat(leaf)
            if not _is_regular(before.st_mode) or before.st_nlink != 1:
                raise _error(
                    f"retained source must be ordinary single-link file: {relpath}"
                )
            if before.st_size > _max_bytes:
                raise _error(f"retained source too large: {relpath}")
            chunks, remaining = [], _max_bytes + 1
            while remaining:
                chunk = _os_read(leaf, min(1024 * 1024, remaining))
                if not chunk:
                    break
                chunks.append(chunk)
                remaining -= len(chunk)
            data = b"".join(chunks)
            after = _os_fstat(leaf)
            identity = lambda st: (
                st.st_dev,
                st.st_ino,
                st.st_size,
                st.st_mtime_ns,
                st.st_ctime_ns,
            )
            if identity(before) != identity(after) or len(data) != before.st_size:
                raise _error(f"retained source changed during read: {relpath}")
            return data
        finally:
            _os_close(leaf)
    finally:
        if fd != root_fd:
            _os_close(fd)
        _os_close(root_fd)


def _parse_authority(
    raw: bytes,
    root: Path,
    expected_sha256: str,
    _sha256=hashlib.sha256,
    _loads_strict_fn=loads_strict,
    _freeze_fn=_freeze,
    _expect_keys_fn=_expect_keys,
    _str_fn=_str,
    _safe_relpath_fn=_safe_relpath,
    _sha_fn=_sha,
    _read_retained_fn=_read_retained,
    _source_binding=SourceBinding,
    _evidence_binding=EvidenceBinding,
    _evidence_authority=EvidenceAuthority,
    _mapping_proxy=MappingProxyType,
    _positive_authorities=frozenset(POSITIVE_SOURCE_AUTHORITIES),
    _opportunity_id=OPPORTUNITY_ID,
    _event_id=EVENT_ID,
    _error=GateError,
) -> EvidenceAuthority:
    got = _sha256(raw).hexdigest()
    if got != expected_sha256:
        raise _error("authority manifest does not match source-literal pinned root")
    try:
        doc = _loads_strict_fn(raw.decode("utf-8"))
    except UnicodeDecodeError as exc:
        raise _error("authority manifest must be UTF-8") from exc
    doc = _freeze_fn(doc, "authority manifest")
    if type(doc) is not dict:
        raise _error("authority manifest must be object")
    _expect_keys_fn(doc, {"schema", "opportunity_id", "event_id", "generation_id", "sources", "evidence"}, "authority manifest")
    if doc["schema"] != "indiana-iot-observability-authority/v1":
        raise _error("authority manifest schema mismatch")
    if doc["opportunity_id"] != _opportunity_id or doc["event_id"] != _event_id:
        raise _error("authority manifest identity mismatch")
    generation = _str_fn(doc["generation_id"], "authority generation_id")
    if type(doc["sources"]) is not list or type(doc["evidence"]) is not list:
        raise _error("authority sources/evidence must be arrays")

    sources = {}
    for i, row in enumerate(doc["sources"]):
        if type(row) is not dict:
            raise _error(f"authority sources[{i}] must be object")
        _expect_keys_fn(row, {"id", "authority", "relpath", "sha256", "subject", "scope", "generation_id"}, f"authority sources[{i}]")
        sid = _str_fn(row["id"], f"authority sources[{i}].id")
        if sid in sources:
            raise _error(f"duplicate authority source id: {sid}")
        authority = _str_fn(row["authority"], f"{sid}.authority")
        if authority not in _positive_authorities:
            raise _error(f"{sid} cannot be a positive retained authority")
        if row["subject"] != _opportunity_id or row["generation_id"] != generation:
            raise _error(f"{sid} subject/generation mismatch")
        relpath = _safe_relpath_fn(row["relpath"], f"{sid}.relpath")
        digest = _sha_fn(row["sha256"], f"{sid}.sha256")
        data = _read_retained_fn(root, relpath)
        if _sha256(data).hexdigest() != digest:
            raise _error(f"retained source digest mismatch: {sid}")
        sources[sid] = _source_binding(
            sid, authority, relpath, digest, OPPORTUNITY_ID,
            _str(row["scope"], f"{sid}.scope"), generation,
        )

    evidence = {}
    for i, row in enumerate(doc["evidence"]):
        if type(row) is not dict:
            raise _error(f"authority evidence[{i}] must be object")
        _expect_keys_fn(row, {"id", "source_id", "requirement_id", "subject", "scope", "generation_id"}, f"authority evidence[{i}]")
        eid = _str_fn(row["id"], f"authority evidence[{i}].id")
        if eid in evidence:
            raise _error(f"duplicate evidence id: {eid}")
        source_id = _str_fn(row["source_id"], f"{eid}.source_id")
        if source_id not in sources:
            raise _error(f"{eid} source is not authenticated")
        if row["subject"] != _opportunity_id or row["generation_id"] != generation:
            raise _error(f"{eid} subject/generation mismatch")
        if row["scope"] != sources[source_id].scope:
            raise _error(f"{eid} scope does not match source scope")
        evidence[eid] = _evidence_binding(
            eid, source_id, _str(row["requirement_id"], f"{eid}.requirement_id"),
            _opportunity_id, row["scope"], generation,
        )
    return _evidence_authority(got, generation, _mapping_proxy(sources), _mapping_proxy(evidence))


def _load_authority(
    root: Path = PACKAGE_ROOT,
    expected_sha256: str = AUTHORITY_MANIFEST_SHA256,
    _parser=_parse_authority,
    _reader=_read_retained,
    _manifest=AUTHORITY_MANIFEST,
) -> EvidenceAuthority:
    return _parser(_reader(root, _manifest), root, expected_sha256)


def _sources(ledger: Mapping[str, Any], authority: EvidenceAuthority):
    ledger = _freeze(ledger, "source ledger")
    if type(ledger) is not dict or ledger.get("opportunity_id") != _opportunity_id or ledger.get("event_id") != EVENT_ID:
        raise _error("source ledger identity mismatch")
    rows = ledger.get("sources")
    if type(rows) is not list:
        raise _error("sources must be array")
    out = {}
    authenticated_seen = set()
    for i, row in enumerate(rows):
        if type(row) is not dict:
            raise _error(f"sources[{i}] must be object")
        sid = _str_fn(row.get("id"), f"sources[{i}].id")
        if sid in out:
            raise _error(f"duplicate source id: {sid}")
        source_authority = _str_fn(row.get("authority"), f"{sid}.authority")
        if source_authority not in AUTHORITIES:
            raise _error(f"unsupported authority: {source_authority}")
        retained = _bool(row.get("retained"), f"{sid}.retained")
        _str(row.get("url"), f"{sid}.url")
        claims, controls = row.get("claims", {}), row.get("controls", [])
        if type(claims) is not dict or type(controls) is not list or any(type(x) is not str for x in controls):
            raise _error(f"{sid} claims/controls malformed")
        if len(controls) != len(set(controls)):
            raise _error(f"{sid}.controls duplicates")
        binding = authority.sources.get(sid)
        if retained and binding is None:
            raise _error(f"{sid} retained=true is not authenticated by the pinned authority root")
        if binding is not None:
            if not retained or binding.authority != source_authority:
                raise _error(f"{sid} authenticated source does not match source-ledger assertion")
            authenticated_seen.add(sid)
        elif controls:
            raise _error(f"{sid} cannot control fields without authenticated retained bytes")
        if source_authority != "OFFICIAL_CONTROLLING_PACKAGE" and CONTROLLING_FIELDS.intersection(controls):
            raise _error(f"{sid} cannot control package-only fields")
        out[sid] = row
    if authenticated_seen != set(authority.sources):
        raise _error("source ledger does not expose the complete authenticated retained-source inventory")
    return out


def _requirements(doc: Mapping[str, Any], authority: EvidenceAuthority):
    doc = _freeze(doc, "requirements")
    if type(doc) is not dict or doc.get("opportunity_id") != _opportunity_id:
        raise _error("requirements identity mismatch")
    rows = doc.get("requirements")
    if type(rows) is not list:
        raise _error("requirements must be array")
    out = {}
    used = set()
    for i, row in enumerate(rows):
        if type(row) is not dict:
            raise _error(f"requirements[{i}] must be object")
        rid = _str_fn(row.get("id"), f"requirements[{i}].id")
        if rid in out:
            raise _error(f"duplicate requirement id: {rid}")
        state = _str_fn(row.get("state"), f"{rid}.state")
        if state not in ALLOWED_REQUIREMENT_STATES:
            raise _error(f"{rid}.state unsupported")
        ev = row.get("evidence")
        if type(ev) is not list or any(type(x) is not str or not x for x in ev) or len(ev) != len(set(ev)):
            raise _error(f"{rid}.evidence must be unique string array")
        if state == "PROVEN" and not ev:
            raise _error(f"{rid} PROVEN requires retained evidence")
        if state != "PROVEN" and ev:
            raise _error(f"{rid} non-PROVEN cannot carry positive evidence")
        for eid in ev:
            binding = authority.evidence.get(eid)
            if binding is None:
                raise _error(f"{rid} evidence {eid} is not authenticated")
            if binding.requirement_id != rid:
                raise _error(f"{eid} is bound to another requirement")
            if eid in used:
                raise _error(f"{eid} cannot be reused across requirements")
            used.add(eid)
        out[rid] = row
    return out


def _canonical_json_bytes(
    value: Any,
    _json_dumps=json.dumps,
    _error=GateError,
) -> bytes:
    try:
        return _json_dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8", "strict")
    except (TypeError, ValueError, UnicodeError) as exc:
        raise _error(f"cannot canonicalize JSON value: {exc}") from exc


def _receipt(
    report: Mapping[str, Any],
    _canonical_bytes=_canonical_json_bytes,
    _sha256=hashlib.sha256,
) -> str:
    base = dict(report)
    base.pop("receipt_sha256", None)
    return _sha256(_canonical_bytes(base)).hexdigest()


def _compile(
    ledger: Mapping[str, Any], requirements: Mapping[str, Any], partners: Mapping[str, Any],
    scope: Mapping[str, Any], *, authority: EvidenceAuthority, evaluation_dt: datetime, current: bool,
):
    sources = _sources(ledger, authority)
    reqs = _requirements(requirements, authority)
    partners = _freeze(partners, "partners")
    scope = _freeze(scope, "scope")
    if type(partners) is not dict or partners.get("opportunity_id") != _opportunity_id or type(partners.get("targets")) is not list:
        raise _error("partner targets identity/shape mismatch")
    targets = partners["targets"]
    for i, target in enumerate(targets):
        if type(target) is not dict:
            raise _error(f"targets[{i}] malformed")
        _str(target.get("name"), f"targets[{i}].name")
        if target.get("status") != "RESEARCH_TARGET_NO_CONTACT" or target.get("contact_authority") is not False:
            raise _error("partner target may not claim contact or selection")
    if type(scope) is not dict or scope.get("opportunity_id") != _opportunity_id or scope.get("status") != "TEMPLATE_NOT_OFFER":
        raise _error("paid specialist scope must remain a non-offer template")
    if scope.get("price_usd") is not None:
        raise _error("template price must remain unset before partner discovery")

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


def _make_public(
    loader,
    compiler,
    clock,
    freezer,
    receipt_fn,
    canonical_bytes_fn,
    time_fn=_time,
    utc=timezone.utc,
    max_age_seconds=CURRENT_MAX_AGE_SECONDS,
    future_skew_seconds=CURRENT_FUTURE_SKEW_SECONDS,
    error_type=GateError,
):
    def compile_pursuit(ledger, requirements, partners, scope, *, now: str):
        return compiler(
            ledger, requirements, partners, scope,
            authority=loader(), evaluation_dt=time_fn(now, "now"), current=False,
        )

    def compile_current(ledger, requirements, partners, scope):
        return compiler(
            ledger, requirements, partners, scope,
            authority=loader(), evaluation_dt=clock(utc), current=True,
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
            dt = time_fn(frozen.get("evaluation_time"), "packet.evaluation_time")
            if mode == "CURRENT_PROCESS_TIME":
                fresh_now = clock(utc)
                age = (fresh_now - dt).total_seconds()
                if age > max_age_seconds or age < -future_skew_seconds:
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
            return canonical_bytes_fn(frozen) == canonical_bytes_fn(expected)
        except (error_type, OSError, UnicodeError, ValueError, TypeError):
            return False

    return compile_pursuit, compile_current, verify_pursuit


compile_pursuit, compile_current, verify_pursuit = _make_public(
    _load_authority,
    _compile,
    datetime.now,
    _freeze,
    _receipt,
    _canonical_json_bytes,
)
del _make_public


def _read(path: Path):
    try:
        return loads_strict(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError) as exc:
        raise _error(f"cannot read {path}: {exc}") from exc


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
