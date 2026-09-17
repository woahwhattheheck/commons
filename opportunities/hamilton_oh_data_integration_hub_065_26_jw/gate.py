"""Fail-closed pursuit gate for Hamilton County RFP 065-26/JW.

Discovery sources may guide investigation but cannot establish buyer control.
Positive owner/partner qualification is accepted only from source-owned, digest-pinned
retained evidence. Runtime inputs cannot extend that trust root.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from types import MappingProxyType
from typing import Any, Mapping, Sequence

OPPORTUNITY_ID = "065-26/JW"
EVIDENCE_ARTIFACT_SCHEMA = "hamilton-065-26-jw-evidence/v3"
PACKET_SCHEMA = "hamilton-065-26-jw-pursuit/v3"
MAX_RETAINED_EVIDENCE_BYTES = 262_144

BUYER_CONTROL_FIELDS = {
    "response_deadline", "question_deadline", "submission_mechanics",
    "teaming_rules", "evaluation_criteria", "mandatory_requirements",
}
SOURCE_AUTHORITIES = {
    "OFFICIAL_PORTAL_ENTRY", "OFFICIAL_CONTROLLING_PACKET", "OFFICIAL_ADDENDUM",
    "MIRROR", "INTERNAL_EVIDENCE",
}
PRIME_GATES = (
    "submission_mechanics", "eligibility", "security_compliance",
    "past_performance", "insurance_legal", "pricing",
)
SPECIALIST_GATES = ("integration_engineering", "validation_evidence", "delivery_capacity")
ALL_GATES = PRIME_GATES + SPECIALIST_GATES + ("partner_prime",)

# These are satisfaction classes, not a taxonomy of every document that may
# describe a requirement. Requirement text cannot prove that the owner satisfies it.
EVIDENCE_CLASSES = {
    "submission_mechanics": {"OFFICIAL_REQUIREMENT"},
    "eligibility": {"OWNER_QUALIFICATION"},
    "security_compliance": {"OWNER_QUALIFICATION"},
    "past_performance": {"OWNER_QUALIFICATION"},
    "insurance_legal": {"OWNER_QUALIFICATION"},
    "pricing": {"OWNER_PRICING"},
    "integration_engineering": {"OWNER_CAPABILITY"},
    "validation_evidence": {"OWNER_CAPABILITY"},
    "delivery_capacity": {"OWNER_CAPACITY"},
    "partner_prime": {"PARTNER_DUE_DILIGENCE"},
}
OFFICIAL_EVIDENCE_CLASSES = {"OFFICIAL_REQUIREMENT"}
INTERNAL_EVIDENCE_KIND = {
    "OWNER_QUALIFICATION": "OWNER_QUALIFICATION_RECORD",
    "OWNER_PRICING": "OWNER_PRICING_RECORD",
    "OWNER_CAPABILITY": "OWNER_CAPABILITY_RECORD",
    "OWNER_CAPACITY": "OWNER_CAPACITY_RECORD",
    "PARTNER_DUE_DILIGENCE": "PARTNER_DUE_DILIGENCE_RECORD",
}

# Source-owned trust root. The reviewed carrier intentionally has no positive
# owner/partner evidence yet. Adding one requires a source change that pins the
# retained leaf name to its exact SHA-256 here.
SOURCE_OWNED_RETAINED_EVIDENCE: Mapping[str, str] = MappingProxyType({})


class GateError(ValueError):
    pass


def _pairs_no_dupes(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise GateError(f"duplicate JSON key: {key}")
        out[key] = value
    return out


def _reject_constant(value):
    raise GateError(f"non-finite JSON number: {value}")


def loads_strict(text: str) -> Any:
    try:
        return json.loads(text, object_pairs_hook=_pairs_no_dupes, parse_constant=_reject_constant)
    except GateError:
        raise
    except json.JSONDecodeError as exc:
        raise GateError(str(exc)) from exc


def canonical_bytes(value: Any) -> bytes:
    try:
        return json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode("utf-8")
    except (TypeError, ValueError, UnicodeError) as exc:
        raise GateError(f"value is not canonical JSON: {exc}") from exc


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _raw_digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _bool(value: Any, label: str) -> bool:
    if type(value) is not bool:
        raise GateError(f"{label} must be a JSON boolean")
    return value


def _str(value: Any, label: str) -> str:
    if type(value) is not str or not value.strip():
        raise GateError(f"{label} must be a non-empty string")
    if value != value.strip():
        raise GateError(f"{label} must not contain surrounding whitespace")
    return value


def _string_list(value: Any, label: str, *, limit: int = 64) -> list[str]:
    if type(value) is not list or not value or len(value) > limit:
        raise GateError(f"{label} must be a non-empty bounded string array")
    out: list[str] = []
    for idx, item in enumerate(value):
        item = _str(item, f"{label}[{idx}]")
        if len(item) > 1000:
            raise GateError(f"{label}[{idx}] exceeds 1000 characters")
        if item in out:
            raise GateError(f"{label} contains duplicate value")
        out.append(item)
    return out


def _time(value: Any, label: str) -> datetime:
    value = _str(value, label)
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise GateError(f"{label} must be ISO-8601") from exc
    if dt.tzinfo is None:
        raise GateError(f"{label} must include timezone")
    return dt.astimezone(timezone.utc)


def _sha(value: Any, label: str) -> str:
    value = _str(value, label)
    if len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
        raise GateError(f"{label} must be lowercase sha256 hex")
    return value


def _retained_evidence_leaf(value: Any, sid: str) -> str:
    raw = _str(value, f"{sid}.retained_artifact.path")
    if "\\" in raw:
        raise GateError(f"{sid}.retained_artifact.path must use POSIX separators")
    rel = PurePosixPath(raw)
    if rel.is_absolute() or ".." in rel.parts or rel.parts[:1] != ("retained_evidence",):
        raise GateError(f"{sid}.retained_artifact.path must stay under retained_evidence/")
    if len(rel.parts) != 2 or rel.suffix != ".json":
        raise GateError(
            f"{sid}.retained_artifact.path must name one JSON file directly under retained_evidence/"
        )
    return rel.name


def _source_owned_retained_digest(leaf: str, sid: str) -> str:
    pinned = SOURCE_OWNED_RETAINED_EVIDENCE.get(leaf)
    if pinned is None:
        raise GateError(f"{sid}.retained_artifact is not admitted by source-owned evidence index")
    return _sha(pinned, f"source-owned retained digest for {leaf}")


def _read_retained_evidence_bytes(leaf: str, sid: str) -> bytes:
    """Read one admitted evidence inode through one no-follow fd generation."""
    package_dir = Path(__file__).resolve().parent
    base = package_dir / "retained_evidence"
    dir_flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
    file_flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    try:
        dir_fd = os.open(base, dir_flags)
    except OSError as exc:
        raise GateError(f"{sid}.retained_artifact evidence directory cannot be opened safely") from exc
    try:
        directory = os.fstat(dir_fd)
        if not stat.S_ISDIR(directory.st_mode):
            raise GateError(f"{sid}.retained_artifact evidence root is not a directory")
        try:
            fd = os.open(leaf, file_flags, dir_fd=dir_fd)
        except OSError as exc:
            raise GateError(f"{sid}.retained_artifact is not retained in source tree") from exc
        try:
            before = os.fstat(fd)
            if not stat.S_ISREG(before.st_mode):
                raise GateError(f"{sid}.retained_artifact must resolve to a regular file")
            if before.st_nlink != 1:
                raise GateError(f"{sid}.retained_artifact must have exactly one filesystem link")
            if before.st_size <= 0 or before.st_size > MAX_RETAINED_EVIDENCE_BYTES:
                raise GateError(f"{sid}.retained_artifact has invalid retained byte length")
            chunks: list[bytes] = []
            size = 0
            while size <= MAX_RETAINED_EVIDENCE_BYTES:
                chunk = os.read(fd, min(65536, MAX_RETAINED_EVIDENCE_BYTES + 1 - size))
                if not chunk:
                    break
                chunks.append(chunk)
                size += len(chunk)
            raw = b"".join(chunks)
            after = os.fstat(fd)
            before_id = (
                before.st_dev, before.st_ino, before.st_mode, before.st_nlink,
                before.st_size, before.st_mtime_ns, before.st_ctime_ns,
            )
            after_id = (
                after.st_dev, after.st_ino, after.st_mode, after.st_nlink,
                after.st_size, after.st_mtime_ns, after.st_ctime_ns,
            )
            if before_id != after_id:
                raise GateError(f"{sid}.retained_artifact changed during authenticated read")
            if not raw or len(raw) > MAX_RETAINED_EVIDENCE_BYTES or len(raw) != before.st_size:
                raise GateError(f"{sid}.retained_artifact has invalid retained byte length")
            return raw
        finally:
            os.close(fd)
    finally:
        os.close(dir_fd)


def _internal_artifact_binding(source: Mapping[str, Any], sid: str) -> tuple[str, str]:
    locator = source.get("retained_artifact")
    if type(locator) is not dict or set(locator) != {"path", "sha256"}:
        raise GateError(f"{sid}.retained_artifact must contain exact path and sha256 fields")
    leaf = _retained_evidence_leaf(locator.get("path"), sid)
    pinned_sha = _source_owned_retained_digest(leaf, sid)
    locator_sha = _sha(locator.get("sha256"), f"{sid}.retained_artifact.sha256")
    source_sha = _sha(source.get("content_sha256"), f"{sid}.content_sha256")
    if locator_sha != source_sha or locator_sha != pinned_sha:
        raise GateError(f"{sid}.retained_artifact digest does not match source-owned evidence index")
    raw = _read_retained_evidence_bytes(leaf, sid)
    if _raw_digest(raw) != pinned_sha:
        raise GateError(f"{sid}.content_sha256 does not authenticate retained file bytes")
    try:
        artifact = loads_strict(raw.decode("utf-8"))
    except UnicodeDecodeError as exc:
        raise GateError(f"{sid}.retained_artifact is not utf-8") from exc
    required = {"schema", "source_id", "opportunity_id", "binding", "evidence"}
    if type(artifact) is not dict or set(artifact) != required:
        raise GateError(f"{sid}.retained_artifact has unexpected record fields")
    if artifact.get("schema") != EVIDENCE_ARTIFACT_SCHEMA:
        raise GateError(f"{sid}.retained_artifact schema mismatch")
    if artifact.get("source_id") != sid:
        raise GateError(f"{sid}.retained_artifact source_id mismatch")
    if artifact.get("opportunity_id") != OPPORTUNITY_ID:
        raise GateError(f"{sid}.retained_artifact opportunity_id mismatch")
    binding = artifact.get("binding")
    if type(binding) is not dict or set(binding) != {"requirement_id", "evidence_class"}:
        raise GateError(f"{sid}.retained_artifact.binding must contain exact binding fields")
    rid = _str(binding.get("requirement_id"), f"{sid}.retained_artifact.binding.requirement_id")
    evidence_class = _str(
        binding.get("evidence_class"), f"{sid}.retained_artifact.binding.evidence_class"
    )
    if rid not in EVIDENCE_CLASSES or evidence_class not in EVIDENCE_CLASSES[rid]:
        raise GateError(f"{sid}.retained_artifact binding is not admissible: {rid}/{evidence_class}")
    if evidence_class in OFFICIAL_EVIDENCE_CLASSES:
        raise GateError(f"{sid}.retained_artifact cannot use an official evidence class")
    expected_kind = INTERNAL_EVIDENCE_KIND.get(evidence_class)
    if expected_kind is None:
        raise GateError(f"{sid}.retained_artifact unsupported internal evidence class")
    evidence = artifact.get("evidence")
    if type(evidence) is not dict or set(evidence) != {"kind", "facts", "refs"}:
        raise GateError(f"{sid}.retained_artifact.evidence must contain exact kind/facts/refs")
    if evidence.get("kind") != expected_kind:
        raise GateError(f"{sid}.retained_artifact.evidence.kind must be {expected_kind}")
    _string_list(evidence.get("facts"), f"{sid}.retained_artifact.evidence.facts")
    _string_list(evidence.get("refs"), f"{sid}.retained_artifact.evidence.refs")
    return rid, evidence_class


def _source_index(ledger: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    if type(ledger) is not dict or ledger.get("opportunity_id") != OPPORTUNITY_ID:
        raise GateError("source ledger opportunity_id mismatch")
    sources = ledger.get("sources")
    if type(sources) is not list:
        raise GateError("sources must be an array")
    out: dict[str, Mapping[str, Any]] = {}
    for idx, source in enumerate(sources):
        if type(source) is not dict:
            raise GateError(f"sources[{idx}] must be an object")
        sid = _str(source.get("id"), f"sources[{idx}].id")
        if sid in out:
            raise GateError(f"duplicate source id: {sid}")
        authority = _str(source.get("authority"), f"{sid}.authority")
        if authority not in SOURCE_AUTHORITIES:
            raise GateError(f"unsupported source authority: {authority}")
        retrieved = _bool(source.get("retrieved"), f"{sid}.retrieved")
        _str(source.get("url"), f"{sid}.url")
        _time(source.get("observed_at"), f"{sid}.observed_at")
        claims = source.get("claims", {})
        controls = source.get("controls", [])
        if type(claims) is not dict:
            raise GateError(f"{sid}.claims must be object")
        if type(controls) is not list or any(type(item) is not str for item in controls):
            raise GateError(f"{sid}.controls must be string array")
        if len(controls) != len(set(controls)):
            raise GateError(f"{sid}.controls contains duplicates")
        if authority in {"MIRROR", "INTERNAL_EVIDENCE", "OFFICIAL_PORTAL_ENTRY"}:
            forbidden = BUYER_CONTROL_FIELDS.intersection(controls)
            if forbidden:
                raise GateError(f"{sid} cannot control buyer fields as {authority}: {sorted(forbidden)}")
        if retrieved:
            _sha(source.get("content_sha256"), f"{sid}.content_sha256")
        out[sid] = source
    return out


def _official_value(sources: Mapping[str, Mapping[str, Any]], field: str) -> tuple[Any, str | None]:
    values: list[tuple[Any, str]] = []
    for sid, source in sources.items():
        if (
            not source["retrieved"]
            or source["authority"] not in {"OFFICIAL_CONTROLLING_PACKET", "OFFICIAL_ADDENDUM"}
        ):
            continue
        if field in source.get("controls", []) and field in source.get("claims", {}):
            values.append((source["claims"][field], sid))
    if not values:
        return None, None
    first = values[0][0]
    if any(value != first for value, _ in values[1:]):
        raise GateError(f"conflicting official authority for {field}")
    return first, ",".join(sorted(sid for _, sid in values))


def _evidence_index(
    manifest: Mapping[str, Any], sources: Mapping[str, Mapping[str, Any]]
) -> dict[str, dict[str, str]]:
    if (
        type(manifest) is not dict
        or set(manifest) != {"opportunity_id", "evidence"}
        or manifest.get("opportunity_id") != OPPORTUNITY_ID
    ):
        raise GateError("evidence manifest must contain exact opportunity_id/evidence fields")
    rows = manifest.get("evidence")
    if type(rows) is not list:
        raise GateError("evidence manifest evidence must be an array")
    out: dict[str, dict[str, str]] = {}
    internal_binding_cache: dict[str, tuple[str, str]] = {}
    exact_row_keys = {
        "id", "opportunity_id", "requirement_id", "evidence_class", "content_sha256", "source_id"
    }
    for idx, row in enumerate(rows):
        if type(row) is not dict or set(row) != exact_row_keys:
            raise GateError(f"evidence[{idx}] must contain exact evidence fields")
        eid = _str(row.get("id"), f"evidence[{idx}].id")
        if eid in out:
            raise GateError(f"duplicate evidence id: {eid}")
        if row.get("opportunity_id") != OPPORTUNITY_ID:
            raise GateError(f"{eid}.opportunity_id mismatch")
        rid = _str(row.get("requirement_id"), f"{eid}.requirement_id")
        if rid not in EVIDENCE_CLASSES:
            raise GateError(f"{eid}.requirement_id unsupported")
        evidence_class = _str(row.get("evidence_class"), f"{eid}.evidence_class")
        if evidence_class not in EVIDENCE_CLASSES[rid]:
            raise GateError(f"{eid}.evidence_class not admissible for {rid}")
        content_sha = _sha(row.get("content_sha256"), f"{eid}.content_sha256")
        source_id = _str(row.get("source_id"), f"{eid}.source_id")
        source = sources.get(source_id)
        if source is None or not source["retrieved"]:
            raise GateError(f"{eid}.source_id must resolve to retained source")
        if source.get("content_sha256") != content_sha:
            raise GateError(f"{eid}.content_sha256 does not bind source")
        authority = source["authority"]
        if evidence_class in OFFICIAL_EVIDENCE_CLASSES:
            if authority not in {"OFFICIAL_CONTROLLING_PACKET", "OFFICIAL_ADDENDUM"}:
                raise GateError(f"{eid} official evidence must bind official controlling source")
        else:
            if authority != "INTERNAL_EVIDENCE":
                raise GateError(f"{eid} owner/partner evidence must bind INTERNAL_EVIDENCE source")
            if source_id not in internal_binding_cache:
                internal_binding_cache[source_id] = _internal_artifact_binding(source, source_id)
            if internal_binding_cache[source_id] != (rid, evidence_class):
                raise GateError(f"{eid} is not authenticated by source-owned retained evidence")
        out[eid] = {
            "id": eid,
            "opportunity_id": OPPORTUNITY_ID,
            "requirement_id": rid,
            "evidence_class": evidence_class,
            "content_sha256": content_sha,
            "source_id": source_id,
        }
    return out


def _requirements_index(
    requirements: Mapping[str, Any], evidence: Mapping[str, Mapping[str, str]]
) -> dict[str, Mapping[str, Any]]:
    if type(requirements) is not dict or requirements.get("opportunity_id") != OPPORTUNITY_ID:
        raise GateError("requirements opportunity_id mismatch")
    rows = requirements.get("requirements")
    if type(rows) is not list:
        raise GateError("requirements must be an array")
    out: dict[str, Mapping[str, Any]] = {}
    consumed: set[str] = set()
    allowed_row_keys = {"id", "state", "evidence", "note"}
    for idx, row in enumerate(rows):
        if (
            type(row) is not dict
            or not {"id", "state", "evidence"}.issubset(row)
            or not set(row).issubset(allowed_row_keys)
        ):
            raise GateError(f"requirement[{idx}] has unexpected fields")
        rid = _str(row.get("id"), f"requirement[{idx}].id")
        if rid not in ALL_GATES:
            raise GateError(f"unsupported requirement id: {rid}")
        if rid in out:
            raise GateError(f"duplicate requirement id: {rid}")
        state = _str(row.get("state"), f"{rid}.state")
        if state not in {"PROVEN", "GAP", "UNKNOWN", "NOT_APPLICABLE"}:
            raise GateError(f"unsupported requirement state: {state}")
        refs = row.get("evidence")
        if type(refs) is not list or any(type(item) is not str or not item for item in refs):
            raise GateError(f"{rid}.evidence must be string array")
        if len(refs) != len(set(refs)):
            raise GateError(f"{rid}.evidence contains duplicate refs")
        if state == "PROVEN":
            if not refs:
                raise GateError(f"{rid} PROVEN requires retained evidence")
            for ref in refs:
                item = evidence.get(ref)
                if item is None:
                    raise GateError(f"{rid} evidence ref not retained: {ref}")
                if item["requirement_id"] != rid:
                    raise GateError(f"{rid} evidence ref bound to different requirement: {ref}")
                consumed.add(ref)
        elif refs:
            raise GateError(f"{rid} non-PROVEN requirement must not retain positive evidence refs")
        out[rid] = row
    missing = sorted(set(ALL_GATES) - set(out))
    if missing:
        raise GateError(f"missing requirement rows: {missing}")
    unbound = sorted(set(evidence) - consumed)
    if unbound:
        raise GateError(f"retained evidence has no matching PROVEN requirement: {unbound}")
    return out


def _proven(gates: Mapping[str, Mapping[str, Any]], rid: str) -> bool:
    row = gates.get(rid)
    return bool(row and row.get("state") == "PROVEN")


def compile_pursuit(
    ledger: Mapping[str, Any],
    requirements: Mapping[str, Any],
    evidence_manifest: Mapping[str, Any],
    *,
    now: str,
) -> dict[str, Any]:
    now_dt = _time(now, "now")
    sources = _source_index(ledger)
    evidence = _evidence_index(evidence_manifest, sources)
    gates = _requirements_index(requirements, evidence)
    controlling = sorted(
        sid for sid, source in sources.items()
        if source["retrieved"] and source["authority"] == "OFFICIAL_CONTROLLING_PACKET"
    )
    official_packet = bool(controlling)
    deadline_raw, deadline_source = _official_value(sources, "response_deadline")
    submission_raw, submission_source = _official_value(sources, "submission_mechanics")
    teaming_raw, teaming_source = _official_value(sources, "teaming_rules")
    decision = "HOLD"
    reasons: list[str] = []
    deadline_open = False
    if not official_packet:
        reasons.append("CONTROLLING_PACKET_NOT_ACQUIRED")
    if deadline_raw is None:
        reasons.append("RESPONSE_DEADLINE_UNCONTROLLED")
    else:
        if type(deadline_raw) is not str:
            raise GateError("official response_deadline must be string")
        deadline_dt = _time(deadline_raw, "official response_deadline")
        if now_dt >= deadline_dt:
            decision = "NO_BID"
            reasons.append("OFFICIAL_RESPONSE_DEADLINE_PASSED")
        else:
            deadline_open = True
    missing_prime = [rid for rid in PRIME_GATES if not _proven(gates, rid)]
    missing_specialist = [rid for rid in SPECIALIST_GATES if not _proven(gates, rid)]
    if decision != "NO_BID":
        if not official_packet or not deadline_open:
            decision = "HOLD"
        elif submission_raw is None:
            decision = "HOLD"
            reasons.append("SUBMISSION_MECHANICS_UNCONTROLLED")
        elif not missing_prime:
            decision = "PRIME"
        else:
            if teaming_raw is None:
                reasons.append("TEAMING_RULES_UNCONTROLLED")
            elif type(teaming_raw) is not bool:
                raise GateError("official teaming_rules must be boolean")
            elif not teaming_raw:
                reasons.append("TEAMING_NOT_ALLOWED_BY_RETAINED_OFFICIAL_AUTHORITY")
            if teaming_raw is True and not missing_specialist and _proven(gates, "partner_prime"):
                decision = "TEAMING"
            else:
                decision = "HOLD"
    if missing_prime:
        reasons.append("PRIME_GATES_UNPROVEN")
    if missing_specialist:
        reasons.append("SPECIALIST_GATES_UNPROVEN")
    if not _proven(gates, "partner_prime"):
        reasons.append("PRIME_PARTNER_UNPROVEN")
    mirrors = [
        {"source_id": sid, "claims": source.get("claims", {}),
         "authority": "DISCOVERY_ONLY_NOT_BUYER_CONTROL"}
        for sid, source in sorted(sources.items()) if source["authority"] == "MIRROR"
    ]
    work_orders: list[dict[str, Any]] = []
    if "CONTROLLING_PACKET_NOT_ACQUIRED" in reasons:
        work_orders.append({
            "id": "RECOVER_CONTROLLING_RFP_PACKET", "priority": 1,
            "stop_condition": "exact official packet/addenda retained with sha256 and reviewed",
        })
    if "RESPONSE_DEADLINE_UNCONTROLLED" in reasons:
        work_orders.append({
            "id": "BIND_OFFICIAL_RESPONSE_DEADLINE", "priority": 2,
            "stop_condition": "official packet/addendum controls a parseable future response_deadline",
        })
    if "TEAMING_RULES_UNCONTROLLED" in reasons:
        work_orders.append({
            "id": "BIND_TEAMING_AND_SUBCONTRACT_RULES", "priority": 3,
            "stop_condition": "official packet/addendum controls teaming_rules",
        })
    if missing_prime:
        work_orders.append({
            "id": "CLOSE_PRIME_QUALIFICATION_GAPS", "priority": 4, "gates": missing_prime,
            "stop_condition": "each gate proven from admissible retained satisfaction evidence or prime posture abandoned",
        })
    if decision == "HOLD" and not missing_specialist:
        work_orders.append({
            "id": "PREPARE_PAID_SPECIALIST_TEAMING_SCOPE", "priority": 5,
            "stop_condition": "official teaming permission plus evidence-backed prime partner",
        })
    evidence_bindings = {
        rid: sorted(gates[rid]["evidence"])
        for rid in ALL_GATES if gates[rid]["state"] == "PROVEN"
    }
    packet: dict[str, Any] = {
        "schema": PACKET_SCHEMA,
        "opportunity_id": OPPORTUNITY_ID,
        "evaluation_time": now_dt.isoformat().replace("+00:00", "Z"),
        "decision": decision,
        "reasons": sorted(set(reasons)),
        "inputs": {
            "source_ledger_sha256": digest(ledger),
            "requirements_sha256": digest(requirements),
            "evidence_manifest_sha256": digest(evidence_manifest),
        },
        "authority": {
            "official_packet_sources": controlling,
            "response_deadline_source": deadline_source,
            "teaming_rules_source": teaming_source,
            "submission_mechanics_source": submission_source,
            "mirror_can_control_buyer_terms": False,
        },
        "evidence_bindings": evidence_bindings,
        "gaps": {"prime": missing_prime, "specialist": missing_specialist},
        "mirror_intelligence": mirrors,
        "work_orders": sorted(work_orders, key=lambda item: (item["priority"], item["id"])),
        "external_authority": {
            "county_contact": False, "portal_registration": False,
            "question_submission": False, "proposal_submission": False,
            "signature": False, "pricing_commitment": False,
            "partner_representation": False, "award": False,
            "payment": False, "revenue": False,
        },
    }
    packet["receipt_sha256"] = digest(packet)
    return packet


def verify_receipt(
    packet: Mapping[str, Any],
    ledger: Mapping[str, Any],
    requirements: Mapping[str, Any],
    evidence_manifest: Mapping[str, Any],
    *,
    now: str,
) -> bool:
    if type(packet) is not dict:
        return False
    try:
        expected = compile_pursuit(ledger, requirements, evidence_manifest, now=now)
        return canonical_bytes(packet) == canonical_bytes(expected)
    except (GateError, TypeError, ValueError, OSError):
        return False


def _read(path: Path) -> Any:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise GateError(f"cannot read {path}: {exc}") from exc
    return loads_strict(text)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--requirements", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--now", required=True)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    try:
        packet = compile_pursuit(
            _read(args.ledger), _read(args.requirements), _read(args.evidence), now=args.now
        )
        encoded = canonical_bytes(packet) + b"\n"
        if args.out:
            args.out.write_bytes(encoded)
        else:
            os.write(1, encoded)
        return 0
    except (GateError, OSError) as exc:
        print(f"ERROR: {exc}", file=os.sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
