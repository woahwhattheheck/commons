from __future__ import annotations

import hashlib
import json
import os
import stat
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

MAX_EVIDENCE_BYTES = 8 * 1024 * 1024
MAX_SOURCE_BYTES = 32 * 1024 * 1024
REQUIRED_SOURCE_KINDS = {
    "innovation_call",
    "general_solicitation",
    "concept_paper_template",
}
DIRECT_REQUIRED_EVIDENCE_TYPES = {
    "facility_clearance_top_secret",
    "personnel_us_citizenship",
    "personnel_interim_secret_or_higher",
}
PRIVILEGED_REQUIRED_EVIDENCE_TYPES = {
    "privileged_user_t5_or_allowed_interim",
}
REQUIRED_ARCHITECTURE_DOMAINS = {
    "unified_access_shell",
    "identity_provider_adapter",
    "attribute_policy_decision",
    "api_event_integration",
    "legacy_continuity_canary",
    "observability_rollback",
}


class PacketError(ValueError):
    pass


@dataclass(frozen=True)
class BoundFile:
    path: str
    sha256: str
    size: int


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_ts(value: str, field: str) -> datetime:
    if not isinstance(value, str) or not value:
        raise PacketError(f"{field} must be a non-empty ISO-8601 string")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise PacketError(f"{field} is not valid ISO-8601") from exc
    if parsed.tzinfo is None:
        raise PacketError(f"{field} must include timezone")
    return parsed.astimezone(timezone.utc)


def _canonical(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _sha(obj: Any) -> str:
    return hashlib.sha256(_canonical(obj)).hexdigest()


def _read_bound_file(path_text: str, expected_sha256: str, max_bytes: int) -> BoundFile:
    if not isinstance(path_text, str) or not path_text:
        raise PacketError("evidence/source path must be non-empty")
    if not isinstance(expected_sha256, str) or len(expected_sha256) != 64:
        raise PacketError(f"invalid sha256 for {path_text!r}")
    path = Path(path_text)
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(path, flags)
    try:
        st1 = os.fstat(fd)
        if not stat.S_ISREG(st1.st_mode):
            raise PacketError(f"bound path is not a regular file: {path}")
        if st1.st_size > max_bytes:
            raise PacketError(f"bound file too large: {path}")
        h = hashlib.sha256()
        remaining = max_bytes + 1
        total = 0
        while remaining > 0:
            chunk = os.read(fd, min(1024 * 1024, remaining))
            if not chunk:
                break
            total += len(chunk)
            remaining -= len(chunk)
            h.update(chunk)
        if total > max_bytes:
            raise PacketError(f"bound file too large while reading: {path}")
        st2 = os.fstat(fd)
        identity1 = (st1.st_dev, st1.st_ino, st1.st_size, st1.st_mtime_ns)
        identity2 = (st2.st_dev, st2.st_ino, st2.st_size, st2.st_mtime_ns)
        if identity1 != identity2:
            raise PacketError(f"bound file changed while reading: {path}")
        actual = h.hexdigest()
        if actual.lower() != expected_sha256.lower():
            raise PacketError(f"sha256 mismatch for {path}")
        return BoundFile(path=str(path), sha256=actual, size=total)
    finally:
        os.close(fd)


def _validate_source_vault(packet: dict[str, Any], now: datetime) -> tuple[list[dict[str, Any]], list[str]]:
    rows = packet.get("sources")
    if not isinstance(rows, list) or not rows:
        return [], ["SOURCE_VAULT_EMPTY"]
    max_age_hours = packet.get("source_max_age_hours", 72)
    if not isinstance(max_age_hours, int) or not (1 <= max_age_hours <= 720):
        raise PacketError("source_max_age_hours must be integer 1..720")
    seen: set[str] = set()
    bound: list[dict[str, Any]] = []
    holds: list[str] = []
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise PacketError(f"sources[{index}] must be object")
        kind = row.get("kind")
        if not isinstance(kind, str) or not kind:
            raise PacketError(f"sources[{index}].kind missing")
        if kind in seen:
            holds.append(f"SOURCE_KIND_DUPLICATE:{kind}")
            continue
        seen.add(kind)
        captured = _parse_ts(row.get("captured_at"), f"sources[{index}].captured_at")
        if captured > now:
            holds.append(f"SOURCE_CAPTURE_FUTURE:{kind}")
        age = (now - captured).total_seconds() / 3600
        if age > max_age_hours:
            holds.append(f"SOURCE_STALE:{kind}")
        url = row.get("url")
        if not isinstance(url, str) or not url.startswith("https://"):
            holds.append(f"SOURCE_URL_INVALID:{kind}")
        bf = _read_bound_file(row.get("path"), row.get("sha256"), MAX_SOURCE_BYTES)
        bound.append({
            "kind": kind,
            "url": url,
            "captured_at": _iso(captured),
            "sha256": bf.sha256,
            "size": bf.size,
        })
    for kind in sorted(REQUIRED_SOURCE_KINDS - seen):
        holds.append(f"SOURCE_REQUIRED_MISSING:{kind}")
    declared_current_addendum = packet.get("current_addendum_generation")
    if declared_current_addendum is not None:
        if not isinstance(declared_current_addendum, str) or not declared_current_addendum:
            raise PacketError("current_addendum_generation must be non-empty string or null")
        addenda = [r for r in bound if r["kind"].startswith("addendum:")]
        wanted = f"addendum:{declared_current_addendum}"
        if not any(r["kind"] == wanted for r in addenda):
            holds.append(f"CURRENT_ADDENDUM_NOT_BOUND:{declared_current_addendum}")
    return bound, sorted(set(holds))


def _validate_evidence(packet: dict[str, Any], now: datetime) -> tuple[list[dict[str, Any]], set[str], list[str]]:
    rows = packet.get("eligibility_evidence", [])
    if not isinstance(rows, list):
        raise PacketError("eligibility_evidence must be a list")
    bound: list[dict[str, Any]] = []
    valid_types: set[str] = set()
    holds: list[str] = []
    seen_ids: set[str] = set()
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise PacketError(f"eligibility_evidence[{index}] must be object")
        eid = row.get("id")
        etype = row.get("type")
        subject = row.get("subject")
        if not all(isinstance(x, str) and x for x in (eid, etype, subject)):
            raise PacketError(f"eligibility_evidence[{index}] id/type/subject required")
        if eid in seen_ids:
            holds.append(f"EVIDENCE_ID_DUPLICATE:{eid}")
            continue
        seen_ids.add(eid)
        observed = _parse_ts(row.get("observed_at"), f"eligibility_evidence[{index}].observed_at")
        if observed > now:
            holds.append(f"EVIDENCE_FUTURE:{eid}")
        expires_value = row.get("expires_at")
        expires = _parse_ts(expires_value, f"eligibility_evidence[{index}].expires_at") if expires_value else None
        if expires and expires <= now:
            holds.append(f"EVIDENCE_EXPIRED:{eid}")
            continue
        status_value = row.get("status")
        if status_value != "evidenced":
            holds.append(f"EVIDENCE_STATUS_NOT_EVIDENCED:{eid}")
            continue
        bf = _read_bound_file(row.get("path"), row.get("sha256"), MAX_EVIDENCE_BYTES)
        valid_types.add(etype)
        bound.append({
            "id": eid,
            "type": etype,
            "subject": subject,
            "observed_at": _iso(observed),
            "expires_at": _iso(expires) if expires else None,
            "sha256": bf.sha256,
            "size": bf.size,
            "issuer_or_source": row.get("issuer_or_source", "UNSPECIFIED"),
        })
    return bound, valid_types, sorted(set(holds))


def _architecture_holds(packet: dict[str, Any]) -> list[str]:
    rows = packet.get("architecture_domains", [])
    if not isinstance(rows, list):
        raise PacketError("architecture_domains must be a list")
    present = {x for x in rows if isinstance(x, str) and x}
    return [f"ARCHITECTURE_DOMAIN_MISSING:{x}" for x in sorted(REQUIRED_ARCHITECTURE_DOMAINS - present)]


def _acceptance_matrix() -> list[dict[str, Any]]:
    return [
        {"phase": 1, "name": "foundation", "evidence": ["legacy_inventory", "identity_provider_contracts", "baseline_workflow_traces", "threat_model"]},
        {"phase": 2, "name": "integration", "evidence": ["api_event_contract_tests", "attribute_policy_tests", "legacy_continuity_canary", "rollback_drill"]},
        {"phase": 3, "name": "validation", "evidence": ["GAT", "UAT", "regression", "integration", "performance", "accessibility", "security", "issue_disposition"]},
        {"phase": 4, "name": "authorization_transition", "evidence": ["ATO_evidence_index", "production_readiness_ROM", "sustainment_handoff", "onboarding_runbook"]},
    ]


def _rank_teaming_targets(packet: dict[str, Any]) -> list[dict[str, Any]]:
    targets = packet.get("teaming_targets", [])
    if not isinstance(targets, list):
        raise PacketError("teaming_targets must be a list")
    out: list[dict[str, Any]] = []
    for index, t in enumerate(targets):
        if not isinstance(t, dict):
            raise PacketError(f"teaming_targets[{index}] must be object")
        name = t.get("name")
        if not isinstance(name, str) or not name:
            raise PacketError(f"teaming_targets[{index}].name required")
        signals = t.get("signals", [])
        if not isinstance(signals, list):
            raise PacketError(f"teaming_targets[{index}].signals must be list")
        normalized = {s for s in signals if isinstance(s, str)}
        score = 0
        score += 5 if "current_dcsa_nb_is_work" in normalized else 0
        score += 4 if "govcloud_devsecops" in normalized else 0
        score += 4 if "identity_application_modernization" in normalized else 0
        score += 3 if "small_business" in normalized else 0
        score += 2 if "public_partner_route" in normalized else 0
        score -= 5 if "incumbent_overlap_risk" in normalized else 0
        # Deliberately no score for claimed facility clearance. It must be owner-verified separately.
        out.append({
            "name": name,
            "score": score,
            "signals": sorted(normalized),
            "facility_clearance": "OWNER_VERIFY",
            "contact_authority": False,
        })
    return sorted(out, key=lambda x: (-x["score"], x["name"].lower()))


def evaluate(packet: dict[str, Any]) -> dict[str, Any]:
    """Evaluate using process-owned current UTC time. Caller cannot backdate the production clock."""
    if not isinstance(packet, dict):
        raise PacketError("packet must be object")
    now = _utc_now()
    deadline = _parse_ts(packet.get("concept_paper_deadline"), "concept_paper_deadline")
    if now >= deadline:
        return _receipt(packet, now, "HOLD", ["DEADLINE_PASSED"], [], [], [])

    bound_sources, source_holds = _validate_source_vault(packet, now)
    bound_evidence, evidence_types, evidence_holds = _validate_evidence(packet, now)
    arch_holds = _architecture_holds(packet)

    all_holds = sorted(set(source_holds + evidence_holds + arch_holds))
    if source_holds or arch_holds:
        state = "HOLD"
    else:
        missing_direct = sorted(DIRECT_REQUIRED_EVIDENCE_TYPES - evidence_types)
        privileged_needed = bool(packet.get("privileged_users_in_scope", True))
        if privileged_needed:
            missing_direct += sorted(PRIVILEGED_REQUIRED_EVIDENCE_TYPES - evidence_types)
        if evidence_holds:
            state = "HOLD"
        elif missing_direct:
            state = "TEAMING_REQUIRED"
            all_holds += [f"DIRECT_EVIDENCE_MISSING:{x}" for x in missing_direct]
        else:
            state = "DIRECT_READY"

    return _receipt(packet, now, state, sorted(set(all_holds)), bound_sources, bound_evidence, _rank_teaming_targets(packet))


def _receipt(packet: dict[str, Any], now: datetime, state: str, holds: list[str], sources: list[dict[str, Any]], evidence: list[dict[str, Any]], targets: list[dict[str, Any]]) -> dict[str, Any]:
    body = {
        "schema": "dcsa-innovation-call-01-readiness/v1",
        "state": state,
        "evaluated_at": _iso(now),
        "opportunity": packet.get("opportunity", "DCSAInnovationCall01"),
        "concept_paper_deadline": packet.get("concept_paper_deadline"),
        "holds": holds,
        "bound_sources": sources,
        "bound_eligibility_evidence": evidence,
        "acceptance_matrix": _acceptance_matrix(),
        "teaming_targets": targets,
        "authority_ceiling": {
            "clearance_truth_certified": False,
            "government_submission_authorized": False,
            "buyer_contact_authorized": False,
            "contract_awarded": False,
            "payment_or_revenue": False,
            "meaning": "mechanical evidence-readiness only; owner/legal/security authority remains external",
        },
    }
    body["receipt_sha256"] = _sha(body)
    return body


def compile_concept_markdown(packet: dict[str, Any], receipt: dict[str, Any]) -> str:
    """Render a bounded concept-paper draft scaffold without inventing qualifications."""
    lines = [
        "# DCSA Innovation Call #01 — Solution Concept Paper Scaffold",
        "",
        f"Readiness state: **{receipt['state']}**",
        f"Evidence receipt: `{receipt['receipt_sha256']}`",
        "",
        "> This scaffold does not assert facility clearance, personnel clearance, award, buyer approval, or submission authority. Unsupported qualifications remain explicit holds.",
        "",
        "## 1. Mission Outcome",
        "Provide a unified, user-centered access layer over fragmented mission applications while preserving legacy continuity during phased modernization.",
        "",
        "## 2. Technical Approach",
        "- Unified access shell with bounded application adapters rather than a big-bang rewrite.",
        "- Identity-provider adapters and explicit attribute-policy decision contracts.",
        "- API/event integration with idempotency, replay, dead-letter, rollback, and provenance controls.",
        "- Legacy-continuity canaries before each migration or onboarding change.",
        "- IaC/DevSecOps evidence designed for GovCloud deployment boundaries; environment authority remains with the cleared prime/Government.",
        "",
        "## 3. Verification and Acceptance",
    ]
    for row in receipt["acceptance_matrix"]:
        lines.append(f"- Phase {row['phase']} — {row['name']}: " + ", ".join(row["evidence"]))
    lines += [
        "",
        "## 4. Transition and Sustainment",
        "Use application onboarding contracts, issue-disposition evidence, ATO evidence indexing, rollback drills, sustainment handoff, and a production-readiness ROM.",
        "",
        "## 5. Teaming / Eligibility",
    ]
    if receipt["state"] == "DIRECT_READY":
        lines.append("Mechanical evidence packet contains the required direct-readiness evidence classes. Independent security/legal verification is still required before submission.")
    elif receipt["state"] == "TEAMING_REQUIRED":
        lines.append("Direct-readiness evidence is incomplete. Pursue a cleared-prime teaming path; TJLabs workshare remains bounded to integration architecture and acceptance evidence unless separately authorized.")
    else:
        lines.append("Submission remains on HOLD until source/architecture/evidence holds are resolved.")
    if receipt["holds"]:
        lines += ["", "### Unresolved holds"] + [f"- `{h}`" for h in receipt["holds"]]
    if receipt["teaming_targets"]:
        lines += ["", "### Researched teaming candidates (no contact authority)"]
        for target in receipt["teaming_targets"]:
            lines.append(f"- {target['name']} — fit score {target['score']}; FCL: OWNER_VERIFY")
    lines += [
        "",
        "## 6. Source Boundaries",
    ]
    for src in receipt["bound_sources"]:
        lines.append(f"- {src['kind']}: `{src['sha256']}` — {src['url']}")
    lines.append("")
    return "\n".join(lines)
