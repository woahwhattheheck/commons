from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

CAPABILITY_STATES = {
    "SUPPORTED", "CONFIGURABLE", "THIRD_PARTY", "PLANNED", "NOT_SUPPORTED", "UNKNOWN"
}
AFFIRMATIVE_CAPABILITY_STATES = {"SUPPORTED", "CONFIGURABLE", "THIRD_PARTY", "PLANNED"}
QUESTION_STATES = {"ANSWERED", "OWNER_INPUT_REQUIRED", "NOT_APPLICABLE"}
SOURCE_AUTHORITIES = {"CONTROLLING", "SECONDARY"}
SOURCE_CLASSES = {"SOLICITATION_HEADER", "BUYER_ATTACHMENT", "AMENDMENT", "SECONDARY_REFERENCE"}
PRIVACY_FACT_IDS = {
    "facial_recognition", "human_review", "bias_performance_validation", "explainability",
    "retention", "data_ownership", "deployment_boundary", "encryption_access_control",
    "auditability", "accessibility", "incident_response",
}
TCO_CATEGORIES = {
    "ONE_TIME", "RECURRING", "IMPLEMENTATION", "SUPPORT_TRAINING", "INFRASTRUCTURE", "OPTIONAL_THIRD_PARTY"
}
READINESS = {"RESEARCH_READY", "RESPONSE_DRAFT_READY", "HOLD"}
HEX64 = re.compile(r"^[0-9a-f]{64}$")
ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{1,127}$")


class CompileError(ValueError):
    pass


def _exact(obj: Any, keys: set[str], where: str) -> dict[str, Any]:
    if type(obj) is not dict:
        raise CompileError(f"{where}:object_required")
    if set(obj) != keys:
        missing = sorted(keys - set(obj))
        extra = sorted(set(obj) - keys)
        raise CompileError(f"{where}:keys:missing={missing}:extra={extra}")
    return obj


def _list(value: Any, where: str) -> list[Any]:
    if type(value) is not list:
        raise CompileError(f"{where}:array_required")
    return value


def _str(value: Any, where: str, *, allow_empty: bool = False) -> str:
    if type(value) is not str or (not allow_empty and not value.strip()):
        raise CompileError(f"{where}:string_required")
    return value


def _bool(value: Any, where: str) -> bool:
    if type(value) is not bool:
        raise CompileError(f"{where}:bool_required")
    return value


def _int(value: Any, where: str, *, minimum: int | None = None) -> int:
    if type(value) is not int:
        raise CompileError(f"{where}:integer_required")
    if minimum is not None and value < minimum:
        raise CompileError(f"{where}:min={minimum}")
    return value


def _id(value: Any, where: str) -> str:
    value = _str(value, where)
    if not ID_RE.fullmatch(value):
        raise CompileError(f"{where}:invalid_id")
    return value


def _sha(value: Any, where: str, *, nullable: bool = False) -> str | None:
    if value is None and nullable:
        return None
    value = _str(value, where)
    if not HEX64.fullmatch(value):
        raise CompileError(f"{where}:invalid_sha256")
    return value


def _time(value: Any, where: str) -> datetime:
    value = _str(value, where)
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise CompileError(f"{where}:invalid_time") from exc
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise CompileError(f"{where}:timezone_required")
    return dt.astimezone(timezone.utc)


def _canon(obj: Any) -> bytes:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _digest(obj: Any) -> str:
    return hashlib.sha256(_canon(obj)).hexdigest()


def _unique_ids(rows: list[dict[str, Any]], where: str) -> None:
    seen: set[str] = set()
    for row in rows:
        rid = row["id"]
        if rid in seen:
            raise CompileError(f"{where}:duplicate_id:{rid}")
        seen.add(rid)


def _refs(value: Any, evidence: dict[str, dict[str, Any]], where: str, *, subject: str | None = None) -> list[str]:
    refs = _list(value, where)
    out: list[str] = []
    seen: set[str] = set()
    for i, raw in enumerate(refs):
        ref = _id(raw, f"{where}[{i}]")
        if ref in seen:
            raise CompileError(f"{where}:duplicate_ref:{ref}")
        seen.add(ref)
        if ref not in evidence:
            raise CompileError(f"{where}:unknown_evidence:{ref}")
        if subject is not None and evidence[ref]["subject"] != subject:
            raise CompileError(f"{where}:evidence_transplant:{ref}")
        out.append(ref)
    return out


def _normalize(doc: Any) -> tuple[dict[str, Any], dict[str, dict[str, Any]], datetime]:
    doc = _exact(doc, {
        "schema", "evaluation_time", "opportunity", "company", "sources", "evidence", "capabilities",
        "privacy", "architecture", "compatibility", "tco", "questions", "required_attachments"
    }, "root")
    if doc["schema"] != "commons.mass-dds-ipms-rfi-input/v1":
        raise CompileError("root:schema")
    evaluation_time = _time(doc["evaluation_time"], "evaluation_time")

    opp = _exact(doc["opportunity"], {
        "buyer", "solicitation_id", "alternate_id", "notice_url", "deadline", "market_research_only"
    }, "opportunity")
    for k in ("buyer", "solicitation_id", "alternate_id", "notice_url"):
        _str(opp[k], f"opportunity.{k}")
    _time(opp["deadline"], "opportunity.deadline")
    if _bool(opp["market_research_only"], "opportunity.market_research_only") is not True:
        raise CompileError("opportunity:must_be_market_research_only")

    company = _exact(doc["company"], {"legal_name", "contact_name", "contact_email", "product_name"}, "company")
    for k, v in company.items():
        if v is not None:
            _str(v, f"company.{k}")

    sources = _list(doc["sources"], "sources")
    normalized_sources: list[dict[str, Any]] = []
    for i, raw in enumerate(sources):
        row = _exact(raw, {"id", "source_class", "authority", "url", "published_at", "observed_at", "sha256", "current", "supersedes"}, f"sources[{i}]")
        sid = _id(row["id"], f"sources[{i}].id")
        if row["source_class"] not in SOURCE_CLASSES:
            raise CompileError(f"sources[{i}].source_class")
        if row["authority"] not in SOURCE_AUTHORITIES:
            raise CompileError(f"sources[{i}].authority")
        _str(row["url"], f"sources[{i}].url")
        published = _time(row["published_at"], f"sources[{i}].published_at")
        observed = _time(row["observed_at"], f"sources[{i}].observed_at")
        if published > observed:
            raise CompileError(f"sources[{i}]:published_after_observed")
        if observed > evaluation_time:
            raise CompileError(f"sources[{i}]:future_observation")
        sha = _sha(row["sha256"], f"sources[{i}].sha256", nullable=True)
        current = _bool(row["current"], f"sources[{i}].current")
        supersedes = row["supersedes"]
        if supersedes is not None:
            supersedes = _id(supersedes, f"sources[{i}].supersedes")
        if row["source_class"] == "AMENDMENT" and current and row["authority"] != "CONTROLLING":
            raise CompileError(f"sources[{i}]:current_amendment_must_control")
        normalized_sources.append({**row, "id": sid, "sha256": sha, "current": current, "supersedes": supersedes})
    _unique_ids(normalized_sources, "sources")
    source_by_id = {row["id"]: row for row in normalized_sources}
    for row in normalized_sources:
        if row["supersedes"] is not None:
            if row["supersedes"] not in source_by_id:
                raise CompileError(f"sources:{row['id']}:unknown_supersedes")
            if row["supersedes"] == row["id"]:
                raise CompileError(f"sources:{row['id']}:self_supersedes")
    if any(s["source_class"] == "SECONDARY_REFERENCE" and s["authority"] == "CONTROLLING" for s in normalized_sources):
        raise CompileError("sources:secondary_cannot_control")

    evidence_rows = _list(doc["evidence"], "evidence")
    normalized_evidence: list[dict[str, Any]] = []
    for i, raw in enumerate(evidence_rows):
        row = _exact(raw, {"id", "subject", "source_id", "claim", "observed_at"}, f"evidence[{i}]")
        eid = _id(row["id"], f"evidence[{i}].id")
        subject = _id(row["subject"], f"evidence[{i}].subject")
        source_id = _id(row["source_id"], f"evidence[{i}].source_id")
        if source_id not in source_by_id:
            raise CompileError(f"evidence[{i}]:unknown_source")
        if not source_by_id[source_id]["current"]:
            raise CompileError(f"evidence[{i}]:stale_source:{source_id}")
        _str(row["claim"], f"evidence[{i}].claim")
        observed = _time(row["observed_at"], f"evidence[{i}].observed_at")
        if observed > evaluation_time:
            raise CompileError(f"evidence[{i}]:future_observation")
        if observed < _time(source_by_id[source_id]["published_at"], f"sources:{source_id}.published_at"):
            raise CompileError(f"evidence[{i}]:predates_source")
        normalized_evidence.append({**row, "id": eid, "subject": subject, "source_id": source_id})
    _unique_ids(normalized_evidence, "evidence")
    evidence = {row["id"]: row for row in normalized_evidence}

    capabilities = _list(doc["capabilities"], "capabilities")
    normalized_caps: list[dict[str, Any]] = []
    for i, raw in enumerate(capabilities):
        row = _exact(raw, {"id", "label", "semantic", "state", "evidence_refs", "caveat"}, f"capabilities[{i}]")
        cid = _id(row["id"], f"capabilities[{i}].id")
        _str(row["label"], f"capabilities[{i}].label")
        semantic = _str(row["semantic"], f"capabilities[{i}].semantic")
        if row["state"] not in CAPABILITY_STATES:
            raise CompileError(f"capabilities[{i}].state")
        refs = _refs(row["evidence_refs"], evidence, f"capabilities[{i}].evidence_refs", subject=cid)
        if row["state"] in AFFIRMATIVE_CAPABILITY_STATES and not refs:
            raise CompileError(f"capabilities[{i}]:affirmative_without_evidence")
        caveat = row["caveat"]
        if caveat is not None:
            _str(caveat, f"capabilities[{i}].caveat")
        normalized_caps.append({**row, "id": cid, "semantic": semantic, "evidence_refs": refs})
    _unique_ids(normalized_caps, "capabilities")

    privacy_rows = _list(doc["privacy"], "privacy")
    normalized_privacy: list[dict[str, Any]] = []
    for i, raw in enumerate(privacy_rows):
        row = _exact(raw, {"id", "value", "evidence_refs", "caveat"}, f"privacy[{i}]")
        pid = _id(row["id"], f"privacy[{i}].id")
        value = _str(row["value"], f"privacy[{i}].value")
        refs = _refs(row["evidence_refs"], evidence, f"privacy[{i}].evidence_refs", subject=pid)
        if value != "UNKNOWN" and not refs:
            raise CompileError(f"privacy[{i}]:known_without_evidence")
        caveat = row["caveat"]
        if caveat is not None:
            _str(caveat, f"privacy[{i}].caveat")
        normalized_privacy.append({**row, "id": pid, "value": value, "evidence_refs": refs})
    _unique_ids(normalized_privacy, "privacy")
    privacy_by_id = {row["id"]: row for row in normalized_privacy}
    if set(privacy_by_id) != PRIVACY_FACT_IDS:
        raise CompileError(f"privacy:required_ids:{sorted(PRIVACY_FACT_IDS - set(privacy_by_id))}:extra={sorted(set(privacy_by_id)-PRIVACY_FACT_IDS)}")

    fr_caps = [c for c in normalized_caps if c["semantic"] == "FACIAL_RECOGNITION" and c["state"] in AFFIRMATIVE_CAPABILITY_STATES]
    fr_value = privacy_by_id["facial_recognition"]["value"]
    if fr_caps and fr_value in {"NOT_USED", "NOT_SUPPORTED"}:
        raise CompileError("privacy:facial_recognition_contradiction")

    architecture = _list(doc["architecture"], "architecture")
    normalized_arch: list[dict[str, Any]] = []
    for i, raw in enumerate(architecture):
        row = _exact(raw, {"id", "claim", "state", "evidence_refs", "caveat"}, f"architecture[{i}]")
        aid = _id(row["id"], f"architecture[{i}].id")
        _str(row["claim"], f"architecture[{i}].claim")
        if row["state"] not in {"EVIDENCED", "OWNER_INPUT_REQUIRED", "UNKNOWN"}:
            raise CompileError(f"architecture[{i}].state")
        refs = _refs(row["evidence_refs"], evidence, f"architecture[{i}].evidence_refs", subject=aid)
        if row["state"] == "EVIDENCED" and not refs:
            raise CompileError(f"architecture[{i}]:evidenced_without_evidence")
        caveat = row["caveat"]
        if caveat is not None:
            _str(caveat, f"architecture[{i}].caveat")
        normalized_arch.append({**row, "id": aid, "evidence_refs": refs})
    _unique_ids(normalized_arch, "architecture")

    compatibility = _list(doc["compatibility"], "compatibility")
    normalized_compat: list[dict[str, Any]] = []
    for i, raw in enumerate(compatibility):
        row = _exact(raw, {"id", "surface", "state", "evidence_refs", "caveat"}, f"compatibility[{i}]")
        xid = _id(row["id"], f"compatibility[{i}].id")
        _str(row["surface"], f"compatibility[{i}].surface")
        if row["state"] not in {"SUPPORTED", "CONFIGURABLE", "THIRD_PARTY", "NOT_SUPPORTED", "UNKNOWN"}:
            raise CompileError(f"compatibility[{i}].state")
        refs = _refs(row["evidence_refs"], evidence, f"compatibility[{i}].evidence_refs", subject=xid)
        if row["state"] in {"SUPPORTED", "CONFIGURABLE", "THIRD_PARTY"} and not refs:
            raise CompileError(f"compatibility[{i}]:affirmative_without_evidence")
        caveat = row["caveat"]
        if caveat is not None:
            _str(caveat, f"compatibility[{i}].caveat")
        normalized_compat.append({**row, "id": xid, "evidence_refs": refs})
    _unique_ids(normalized_compat, "compatibility")

    tco = _exact(doc["tco"], {"currency", "components", "declared_five_year_low", "declared_five_year_high"}, "tco")
    if tco["currency"] != "USD":
        raise CompileError("tco:currency")
    components = _list(tco["components"], "tco.components")
    normalized_components: list[dict[str, Any]] = []
    total_low = 0
    total_high = 0
    for i, raw in enumerate(components):
        row = _exact(raw, {"id", "category", "period", "years", "low_cents", "high_cents", "source"}, f"tco.components[{i}]")
        cid = _id(row["id"], f"tco.components[{i}].id")
        if row["category"] not in TCO_CATEGORIES:
            raise CompileError(f"tco.components[{i}].category")
        if row["period"] not in {"ONE_TIME", "ANNUAL"}:
            raise CompileError(f"tco.components[{i}].period")
        years = _int(row["years"], f"tco.components[{i}].years", minimum=1)
        if row["period"] == "ONE_TIME" and years != 1:
            raise CompileError(f"tco.components[{i}]:one_time_years")
        if row["period"] == "ANNUAL" and years > 5:
            raise CompileError(f"tco.components[{i}]:annual_years_gt_5")
        low = _int(row["low_cents"], f"tco.components[{i}].low_cents", minimum=0)
        high = _int(row["high_cents"], f"tco.components[{i}].high_cents", minimum=0)
        if low > high:
            raise CompileError(f"tco.components[{i}]:low_gt_high")
        if row["source"] not in {"OWNER_INPUT", "VENDOR_INPUT"}:
            raise CompileError(f"tco.components[{i}].source")
        mult = years if row["period"] == "ANNUAL" else 1
        total_low += low * mult
        total_high += high * mult
        normalized_components.append({**row, "id": cid, "years": years, "low_cents": low, "high_cents": high})
    _unique_ids(normalized_components, "tco.components")
    declared_low = _int(tco["declared_five_year_low"], "tco.declared_five_year_low", minimum=0)
    declared_high = _int(tco["declared_five_year_high"], "tco.declared_five_year_high", minimum=0)
    if declared_low != total_low or declared_high != total_high:
        raise CompileError(f"tco:declared_total_mismatch:computed={total_low}-{total_high}")

    questions = _list(doc["questions"], "questions")
    normalized_questions: list[dict[str, Any]] = []
    for i, raw in enumerate(questions):
        row = _exact(raw, {"id", "prompt", "answer", "state", "evidence_refs", "caveats", "attachments", "required"}, f"questions[{i}]")
        qid = _id(row["id"], f"questions[{i}].id")
        _str(row["prompt"], f"questions[{i}].prompt")
        answer = row["answer"]
        if answer is not None:
            _str(answer, f"questions[{i}].answer")
        if row["state"] not in QUESTION_STATES:
            raise CompileError(f"questions[{i}].state")
        if row["state"] == "ANSWERED" and answer is None:
            raise CompileError(f"questions[{i}]:answered_without_answer")
        refs = _refs(row["evidence_refs"], evidence, f"questions[{i}].evidence_refs")
        caveats = [_str(v, f"questions[{i}].caveats[{j}]") for j, v in enumerate(_list(row["caveats"], f"questions[{i}].caveats"))]
        attachments = [_str(v, f"questions[{i}].attachments[{j}]") for j, v in enumerate(_list(row["attachments"], f"questions[{i}].attachments"))]
        required = _bool(row["required"], f"questions[{i}].required")
        normalized_questions.append({**row, "id": qid, "answer": answer, "evidence_refs": refs, "caveats": caveats, "attachments": attachments, "required": required})
    _unique_ids(normalized_questions, "questions")

    required_attachments = _list(doc["required_attachments"], "required_attachments")
    normalized_required: list[dict[str, Any]] = []
    for i, raw in enumerate(required_attachments):
        row = _exact(raw, {"id", "source_id", "required", "available"}, f"required_attachments[{i}]")
        rid = _id(row["id"], f"required_attachments[{i}].id")
        sid = _id(row["source_id"], f"required_attachments[{i}].source_id")
        if sid not in source_by_id:
            raise CompileError(f"required_attachments[{i}]:unknown_source")
        required = _bool(row["required"], f"required_attachments[{i}].required")
        available = _bool(row["available"], f"required_attachments[{i}].available")
        if available and source_by_id[sid]["sha256"] is None:
            raise CompileError(f"required_attachments[{i}]:available_without_hash")
        normalized_required.append({**row, "id": rid, "source_id": sid, "required": required, "available": available})
    _unique_ids(normalized_required, "required_attachments")

    normalized = {
        **doc,
        "sources": normalized_sources,
        "evidence": normalized_evidence,
        "capabilities": normalized_caps,
        "privacy": normalized_privacy,
        "architecture": normalized_arch,
        "compatibility": normalized_compat,
        "tco": {**tco, "components": normalized_components, "declared_five_year_low": declared_low, "declared_five_year_high": declared_high},
        "questions": normalized_questions,
        "required_attachments": normalized_required,
    }
    return normalized, evidence, evaluation_time


def _readiness(doc: dict[str, Any], evaluation_time: datetime) -> tuple[str, list[str]]:
    holds: list[str] = []
    current_controlling = [s for s in doc["sources"] if s["current"] and s["authority"] == "CONTROLLING"]
    if not current_controlling:
        holds.append("NO_CURRENT_CONTROLLING_SOURCE")
    if not any(s["source_class"] == "SOLICITATION_HEADER" for s in current_controlling):
        holds.append("NO_CURRENT_SOLICITATION_HEADER")
    for s in current_controlling:
        observed = _time(s["observed_at"], f"source:{s['id']}.observed_at")
        age = (evaluation_time - observed).total_seconds()
        if age > 7 * 24 * 3600:
            holds.append(f"STALE_CONTROLLING_SOURCE:{s['id']}")
    for row in doc["required_attachments"]:
        if row["required"] and not row["available"]:
            holds.append(f"MISSING_REQUIRED_ATTACHMENT:{row['id']}")
    for field in ("legal_name", "contact_name", "contact_email", "product_name"):
        if doc["company"][field] is None:
            holds.append(f"MISSING_COMPANY_FIELD:{field}")
    for cap in doc["capabilities"]:
        if cap["state"] == "UNKNOWN":
            holds.append(f"UNKNOWN_CAPABILITY:{cap['id']}")
    for row in doc["privacy"]:
        if row["value"] == "UNKNOWN":
            holds.append(f"UNKNOWN_PRIVACY_FACT:{row['id']}")
    required_missing = [q["id"] for q in doc["questions"] if q["required"] and q["state"] == "OWNER_INPUT_REQUIRED"]
    holds.extend(f"MISSING_REQUIRED_RESPONSE:{qid}" for qid in required_missing)
    if not doc["tco"]["components"]:
        holds.append("MISSING_TCO_INPUTS")

    if holds:
        return "HOLD", sorted(set(holds))
    draft_gaps = [q["id"] for q in doc["questions"] if q["state"] != "ANSWERED" and q["required"]]
    if draft_gaps:
        return "RESEARCH_READY", [f"REQUIRED_QUESTION_NOT_ANSWERED:{q}" for q in sorted(draft_gaps)]
    return "RESPONSE_DRAFT_READY", []


def _money(cents: int) -> str:
    return f"${cents / 100:,.2f}"


def _markdown(doc: dict[str, Any], readiness: str, blockers: list[str]) -> str:
    lines = [
        "# Massachusetts DDS IPMS RFI — evidence-bound response pack",
        "",
        f"- Solicitation: `{doc['opportunity']['solicitation_id']}` / `{doc['opportunity']['alternate_id']}`",
        f"- Buyer: {doc['opportunity']['buyer']}",
        f"- Evaluation time: `{doc['evaluation_time']}`",
        f"- Readiness: **{readiness}**",
        "- Authority: internal market-response drafting only; this packet does not submit, sign, price-bind, contact the buyer, claim award, or claim revenue.",
        "",
        "## Readiness blockers",
    ]
    lines += ([f"- `{b}`" for b in blockers] if blockers else ["- None for internal response-draft readiness."])
    lines += ["", "## Source ledger"]
    for s in sorted(doc["sources"], key=lambda x: x["id"]):
        lines.append(f"- `{s['id']}` — {s['authority']} / {s['source_class']} / current={str(s['current']).lower()} / sha256={s['sha256'] or 'UNAVAILABLE'} / {s['url']}")
    lines += ["", "## Capability register"]
    for c in sorted(doc["capabilities"], key=lambda x: x["id"]):
        lines.append(f"- `{c['id']}` — **{c['state']}** — {c['label']} — evidence={','.join(c['evidence_refs']) or 'NONE'}" + (f" — caveat: {c['caveat']}" if c['caveat'] else ""))
    lines += ["", "## Responsible AI / privacy"]
    for p in sorted(doc["privacy"], key=lambda x: x["id"]):
        lines.append(f"- `{p['id']}` — **{p['value']}** — evidence={','.join(p['evidence_refs']) or 'NONE'}" + (f" — caveat: {p['caveat']}" if p['caveat'] else ""))
    lines += ["", "## Architecture"]
    for a in sorted(doc["architecture"], key=lambda x: x["id"]):
        lines.append(f"- `{a['id']}` — **{a['state']}** — {a['claim']} — evidence={','.join(a['evidence_refs']) or 'NONE'}" + (f" — caveat: {a['caveat']}" if a['caveat'] else ""))
    lines += ["", "## Compatibility"]
    for x in sorted(doc["compatibility"], key=lambda x: x["id"]):
        lines.append(f"- `{x['id']}` — **{x['state']}** — {x['surface']} — evidence={','.join(x['evidence_refs']) or 'NONE'}" + (f" — caveat: {x['caveat']}" if x['caveat'] else ""))
    lines += ["", "## Five-year TCO input worksheet"]
    for c in sorted(doc["tco"]["components"], key=lambda x: x["id"]):
        mult = c["years"] if c["period"] == "ANNUAL" else 1
        lines.append(f"- `{c['id']}` — {c['category']} — {c['period']} x {mult} — {_money(c['low_cents'] * mult)} to {_money(c['high_cents'] * mult)} — source={c['source']}")
    lines.append(f"- **Five-year total:** {_money(doc['tco']['declared_five_year_low'])} to {_money(doc['tco']['declared_five_year_high'])} (owner/vendor inputs; not a bid or binding price)")
    lines += ["", "## Response template"]
    for q in sorted(doc["questions"], key=lambda x: x["id"]):
        lines += [f"### `{q['id']}` — {q['prompt']}", f"State: **{q['state']}**", "", q["answer"] or "OWNER INPUT REQUIRED", "", f"Evidence: {', '.join(q['evidence_refs']) or 'NONE'}"]
        if q["caveats"]:
            lines.append("Caveats: " + "; ".join(q["caveats"]))
        if q["attachments"]:
            lines.append("Attachments: " + ", ".join(q["attachments"]))
        lines.append("")
    lines += ["## Future procurement handoff", ""]
    needs = []
    needs += [f"Capability evidence: {c['id']}" for c in doc["capabilities"] if c["state"] in {"UNKNOWN", "PLANNED"}]
    needs += [f"Privacy/RAI evidence: {p['id']}" for p in doc["privacy"] if p["value"] == "UNKNOWN"]
    needs += [f"Architecture evidence: {a['id']}" for a in doc["architecture"] if a["state"] != "EVIDENCED"]
    needs += [f"Compatibility evidence: {x['id']}" for x in doc["compatibility"] if x["state"] == "UNKNOWN"]
    needs += [f"Buyer/source bytes: {a['id']}" for a in doc["required_attachments"] if a["required"] and not a["available"]]
    lines += ([f"- {n}" for n in sorted(needs)] if needs else ["- No unresolved evidence gaps in this input packet."])
    lines.append("")
    return "\n".join(lines)


def compile_packet(input_doc: Any) -> tuple[dict[str, Any], dict[str, Any]]:
    doc, _, evaluation_time = _normalize(input_doc)
    readiness, blockers = _readiness(doc, evaluation_time)
    if readiness not in READINESS:
        raise AssertionError("unreachable readiness")
    response = {
        "schema": "commons.mass-dds-ipms-rfi-response/v1",
        "operation": "MASS-DDS-IPMS-RFI-RECOVERY-ZSBT8Q6-20260915",
        "solicitation_id": doc["opportunity"]["solicitation_id"],
        "alternate_id": doc["opportunity"]["alternate_id"],
        "evaluation_time": doc["evaluation_time"],
        "readiness": readiness,
        "blockers": blockers,
        "authority": {
            "buyer_contact": False,
            "provider_submission": False,
            "binding_pricing": False,
            "signature": False,
            "spend": False,
            "award_claim": False,
            "payment_claim": False,
            "revenue_claim": False,
        },
        "five_year_tco": {
            "currency": "USD",
            "low_cents": doc["tco"]["declared_five_year_low"],
            "high_cents": doc["tco"]["declared_five_year_high"],
            "input_only": True,
        },
        "source_ids": sorted(s["id"] for s in doc["sources"]),
        "capability_states": {c["id"]: c["state"] for c in sorted(doc["capabilities"], key=lambda x: x["id"])},
        "privacy_values": {p["id"]: p["value"] for p in sorted(doc["privacy"], key=lambda x: x["id"])},
        "markdown": _markdown(doc, readiness, blockers),
    }
    receipt_core = {
        "schema": "commons.mass-dds-ipms-rfi-receipt/v1",
        "input_sha256": _digest(doc),
        "response_sha256": _digest(response),
        "operation": response["operation"],
        "solicitation_id": response["solicitation_id"],
        "readiness": readiness,
    }
    receipt = {**receipt_core, "receipt_sha256": _digest(receipt_core)}
    return response, receipt


def verify_bundle(input_doc: Any, response: Any, receipt: Any) -> None:
    compiled_response, compiled_receipt = compile_packet(input_doc)
    if type(response) is not dict or response != compiled_response:
        raise CompileError("verify:response_mismatch")
    if type(receipt) is not dict or receipt != compiled_receipt:
        raise CompileError("verify:receipt_mismatch")
    core = {k: receipt[k] for k in receipt if k != "receipt_sha256"}
    if receipt.get("receipt_sha256") != _digest(core):
        raise CompileError("verify:receipt_digest")


def _load_json(path: Path) -> Any:
    raw = path.read_bytes()
    if len(raw) > 4_000_000:
        raise CompileError("input:file_too_large")
    try:
        text = raw.decode("utf-8", "strict")
    except UnicodeDecodeError as exc:
        raise CompileError("input:utf8") from exc
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for key, value in items:
            if key in out:
                raise CompileError(f"input:duplicate_json_key:{key}")
            out[key] = value
        return out
    try:
        return json.loads(text, object_pairs_hook=pairs, parse_constant=lambda tok: (_ for _ in ()).throw(CompileError(f"input:non_finite:{tok}")))
    except json.JSONDecodeError as exc:
        raise CompileError("input:invalid_json") from exc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compile or verify the Massachusetts DDS IPMS RFI evidence-bound response pack")
    sub = parser.add_subparsers(dest="command", required=True)
    c = sub.add_parser("compile")
    c.add_argument("input", type=Path)
    c.add_argument("--json-out", type=Path, required=True)
    c.add_argument("--md-out", type=Path, required=True)
    c.add_argument("--receipt-out", type=Path, required=True)
    v = sub.add_parser("verify")
    v.add_argument("input", type=Path)
    v.add_argument("response", type=Path)
    v.add_argument("receipt", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "compile":
            doc = _load_json(args.input)
            response, receipt = compile_packet(doc)
            args.json_out.write_text(json.dumps(response, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            args.md_out.write_text(response["markdown"], encoding="utf-8")
            args.receipt_out.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        else:
            verify_bundle(_load_json(args.input), _load_json(args.response), _load_json(args.receipt))
    except CompileError as exc:
        print(f"HOLD: {exc}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
