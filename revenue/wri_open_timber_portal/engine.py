from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
import re
from typing import Any, Mapping
from urllib.parse import urlparse

INPUT_SCHEMA = "wri-open-timber-proposal/v1"
REPORT_SCHEMA = "wri-open-timber-proposal-report/v1"
VERIFY_SCHEMA = "wri-open-timber-proposal-verification/v1"

_TOKEN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$")
_UTC = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
_ALLOWED_AUTHORITIES = {"OFFICIAL_BUYER_PAGE", "BUYER_OWNED_PUBLIC_REPO", "SECONDARY_PROCUREMENT_MIRROR"}
_ALLOWED_ACCESS = {"RETRIEVED", "UNRETRIEVED_403"}
_ALLOWED_EVIDENCE = {"VERIFIED", "UNVERIFIED", "UNKNOWN"}
_ALLOWED_COMMERCIAL = {"OWNER_DECISION_REQUIRED", "PROPOSED_NOT_SUBMITTED"}
_REQUIRED_WORKSTREAMS = {
    "reference_and_runtime_updates",
    "performance_and_security",
    "surface_fixes",
    "maintenance_and_bugs",
    "forward_improvement_list",
}
_BLOCKING_UNKNOWN_CATEGORIES = {
    "submission_route",
    "deadline_time_and_timezone",
    "mandatory_qualifications",
    "required_forms_and_representations",
    "evaluation_method",
    "pricing_instructions",
    "role_title",
}


class ContractError(ValueError):
    pass


def canonical_json(value: Any) -> bytes:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ContractError(f"non-canonical value: {exc}") from exc


def digest(value: Any) -> str:
    return sha256(canonical_json(value)).hexdigest()


def load_json_strict(raw: bytes) -> Any:
    if len(raw) > 2_000_000:
        raise ContractError("input too large")
    try:
        text_value = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ContractError("input must be UTF-8") from exc

    def hook(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for key, value in pairs:
            if key in out:
                raise ContractError(f"duplicate JSON key: {key}")
            out[key] = value
        return out

    def bad_constant(value: str) -> Any:
        raise ContractError(f"non-finite JSON number: {value}")

    try:
        return json.loads(text_value, object_pairs_hook=hook, parse_constant=bad_constant)
    except json.JSONDecodeError as exc:
        raise ContractError(f"invalid JSON: {exc.msg}") from exc


def exact_keys(obj: Mapping[str, Any], expected: set[str], where: str) -> None:
    actual = set(obj)
    if actual != expected:
        raise ContractError(f"{where} schema mismatch missing={sorted(expected-actual)} extra={sorted(actual-expected)}")


def token(value: Any, where: str) -> str:
    if not isinstance(value, str) or not _TOKEN.fullmatch(value):
        raise ContractError(f"{where} must be a canonical token")
    return value


def text(value: Any, where: str, max_len: int = 3000) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip() or len(value) > max_len or any(ord(ch) < 32 and ch not in "\t" for ch in value):
        raise ContractError(f"{where} must be non-empty trimmed text")
    return value


def strict_bool(value: Any, where: str) -> bool:
    if type(value) is not bool:
        raise ContractError(f"{where} must be boolean")
    return value


def strict_int(value: Any, where: str, minimum: int = 0, maximum: int = 10**12) -> int:
    if type(value) is not int or not minimum <= value <= maximum:
        raise ContractError(f"{where} must be an exact integer in {minimum}..{maximum}")
    return value


def utc(value: Any, where: str) -> datetime:
    if not isinstance(value, str) or not _UTC.fullmatch(value):
        raise ContractError(f"{where} must be canonical UTC seconds")
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError as exc:
        raise ContractError(f"{where} is not a real timestamp") from exc


def trusted_time(value: datetime, where: str) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ContractError(f"{where} must be timezone-aware")
    return value.astimezone(timezone.utc).replace(microsecond=0)


def utc_text(value: datetime) -> str:
    return trusted_time(value, "timestamp").strftime("%Y-%m-%dT%H:%M:%SZ")


def https_url(value: Any, where: str) -> str:
    value = text(value, where, max_len=2048)
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password or parsed.fragment:
        raise ContractError(f"{where} must be an https URL without credentials or fragment")
    return value


def unique_tokens(value: Any, where: str, *, allow_empty: bool = False) -> tuple[str, ...]:
    if not isinstance(value, list) or (not value and not allow_empty):
        raise ContractError(f"{where} must be a {'possibly empty ' if allow_empty else 'non-empty '}list")
    out = tuple(token(item, f"{where}[]") for item in value)
    if len(out) != len(set(out)):
        raise ContractError(f"{where} contains duplicates")
    return out


def unique_texts(value: Any, where: str, *, allow_empty: bool = False, max_items: int = 64) -> tuple[str, ...]:
    if not isinstance(value, list) or (not value and not allow_empty) or len(value) > max_items:
        raise ContractError(f"{where} must be a bounded list")
    out = tuple(text(item, f"{where}[]") for item in value)
    if len(out) != len(set(out)):
        raise ContractError(f"{where} contains duplicates")
    return out


def normalize(packet: Any) -> dict[str, Any]:
    if not isinstance(packet, dict):
        raise ContractError("packet must be an object")
    exact_keys(packet, {"schema", "opportunity", "sources", "controlling_unknowns", "technical_baseline", "workstreams", "company_evidence", "commercial"}, "packet")
    if packet["schema"] != INPUT_SCHEMA:
        raise ContractError("unsupported packet schema")

    opp = packet["opportunity"]
    if not isinstance(opp, dict):
        raise ContractError("opportunity must be an object")
    exact_keys(opp, {"buyer_id", "opportunity_id", "buyer_name", "project_name", "target_role", "issued_date_hint", "proposal_due_date_hint", "vendor_decision_date_hint", "anticipated_start_date_hint", "deliverables_due_date_hint"}, "opportunity")
    normalized_opp = {
        "buyer_id": token(opp["buyer_id"], "opportunity.buyer_id"),
        "opportunity_id": token(opp["opportunity_id"], "opportunity.opportunity_id"),
        "buyer_name": text(opp["buyer_name"], "opportunity.buyer_name", 200),
        "project_name": text(opp["project_name"], "opportunity.project_name", 300),
        "target_role": text(opp["target_role"], "opportunity.target_role", 200),
        "issued_date_hint": text(opp["issued_date_hint"], "opportunity.issued_date_hint", 32),
        "proposal_due_date_hint": text(opp["proposal_due_date_hint"], "opportunity.proposal_due_date_hint", 32),
        "vendor_decision_date_hint": text(opp["vendor_decision_date_hint"], "opportunity.vendor_decision_date_hint", 32),
        "anticipated_start_date_hint": text(opp["anticipated_start_date_hint"], "opportunity.anticipated_start_date_hint", 32),
        "deliverables_due_date_hint": text(opp["deliverables_due_date_hint"], "opportunity.deliverables_due_date_hint", 32),
    }

    sources = packet["sources"]
    if not isinstance(sources, list) or not 2 <= len(sources) <= 20:
        raise ContractError("sources must contain 2..20 rows")
    normalized_sources: list[dict[str, Any]] = []
    source_ids: set[str] = set()
    source_urls: set[str] = set()
    for raw in sources:
        if not isinstance(raw, dict):
            raise ContractError("source must be an object")
        exact_keys(raw, {"source_id", "authority", "url", "access_state", "observed_at", "fresh_until", "claims", "limitations"}, "source")
        sid = token(raw["source_id"], "source.source_id")
        if sid in source_ids:
            raise ContractError("duplicate source_id")
        source_ids.add(sid)
        url = https_url(raw["url"], "source.url")
        if url in source_urls:
            raise ContractError("duplicate source URL")
        source_urls.add(url)
        authority = token(raw["authority"], "source.authority")
        if authority not in _ALLOWED_AUTHORITIES:
            raise ContractError("unsupported source authority")
        access_state = token(raw["access_state"], "source.access_state")
        if access_state not in _ALLOWED_ACCESS:
            raise ContractError("unsupported source access state")
        claims = unique_tokens(raw["claims"], "source.claims", allow_empty=True)
        limitations = unique_texts(raw["limitations"], "source.limitations", allow_empty=False, max_items=16)
        observed = utc(raw["observed_at"], "source.observed_at")
        fresh_until = utc(raw["fresh_until"], "source.fresh_until")
        if fresh_until < observed:
            raise ContractError("source fresh_until precedes observed_at")
        if access_state == "UNRETRIEVED_403" and claims:
            raise ContractError("unretrieved source cannot carry factual claims")
        normalized_sources.append({"source_id": sid, "authority": authority, "url": url, "access_state": access_state, "observed_at": utc_text(observed), "fresh_until": utc_text(fresh_until), "claims": sorted(claims), "limitations": list(limitations)})

    unknowns = packet["controlling_unknowns"]
    if not isinstance(unknowns, list) or not unknowns:
        raise ContractError("controlling_unknowns must be non-empty")
    normalized_unknowns: list[dict[str, Any]] = []
    categories: set[str] = set()
    for raw in unknowns:
        if not isinstance(raw, dict):
            raise ContractError("controlling_unknown must be an object")
        exact_keys(raw, {"category", "blocking", "description", "resolution_evidence"}, "controlling_unknown")
        category = token(raw["category"], "controlling_unknown.category")
        if category in categories:
            raise ContractError("duplicate controlling_unknown category")
        categories.add(category)
        blocking = strict_bool(raw["blocking"], "controlling_unknown.blocking")
        resolution = raw["resolution_evidence"]
        if resolution is not None:
            resolution = text(resolution, "controlling_unknown.resolution_evidence", 2000)
        normalized_unknowns.append({"category": category, "blocking": blocking, "description": text(raw["description"], "controlling_unknown.description", 2000), "resolution_evidence": resolution})
    missing_categories = _BLOCKING_UNKNOWN_CATEGORIES - categories
    if missing_categories:
        raise ContractError(f"required controlling unknown categories omitted: {sorted(missing_categories)}")
    for row in normalized_unknowns:
        if row["category"] in _BLOCKING_UNKNOWN_CATEGORIES and not row["blocking"]:
            raise ContractError(f"{row['category']} must remain blocking until independently resolved")
        if row["resolution_evidence"] is not None:
            raise ContractError("v1 carrier does not accept self-asserted resolution evidence; refresh from a controlling source in a new input generation")

    baseline = packet["technical_baseline"]
    if not isinstance(baseline, dict):
        raise ContractError("technical_baseline must be an object")
    exact_keys(baseline, {"repo_url", "application", "runtime", "database", "spatial_extension", "queue", "hosting", "provisioning", "deployment", "test_command", "parallel_test_command", "repo_source_id"}, "technical_baseline")
    repo_source_id = token(baseline["repo_source_id"], "technical_baseline.repo_source_id")
    source_by_id = {row["source_id"]: row for row in normalized_sources}
    if repo_source_id not in source_by_id:
        raise ContractError("technical baseline source does not exist")
    repo_source = source_by_id[repo_source_id]
    if repo_source["authority"] != "BUYER_OWNED_PUBLIC_REPO" or repo_source["access_state"] != "RETRIEVED":
        raise ContractError("technical baseline must be bound to a retrieved buyer-owned public repo")
    repo_url = https_url(baseline["repo_url"], "technical_baseline.repo_url")
    if repo_url != repo_source["url"]:
        raise ContractError("technical baseline repo URL must equal buyer-owned repo source URL")
    normalized_baseline = {
        "repo_url": repo_url,
        "application": text(baseline["application"], "technical_baseline.application", 200),
        "runtime": text(baseline["runtime"], "technical_baseline.runtime", 100),
        "database": text(baseline["database"], "technical_baseline.database", 100),
        "spatial_extension": text(baseline["spatial_extension"], "technical_baseline.spatial_extension", 100),
        "queue": text(baseline["queue"], "technical_baseline.queue", 100),
        "hosting": text(baseline["hosting"], "technical_baseline.hosting", 300),
        "provisioning": text(baseline["provisioning"], "technical_baseline.provisioning", 300),
        "deployment": text(baseline["deployment"], "technical_baseline.deployment", 300),
        "test_command": text(baseline["test_command"], "technical_baseline.test_command", 300),
        "parallel_test_command": text(baseline["parallel_test_command"], "technical_baseline.parallel_test_command", 300),
        "repo_source_id": repo_source_id,
    }
    if "Ruby on Rails" not in normalized_baseline["application"]:
        raise ContractError("target carrier must stay bound to the Ruby on Rails backend surface")

    workstreams = packet["workstreams"]
    if not isinstance(workstreams, list) or len(workstreams) < len(_REQUIRED_WORKSTREAMS):
        raise ContractError("workstreams are incomplete")
    normalized_workstreams: list[dict[str, Any]] = []
    ws_ids: set[str] = set()
    buckets: set[str] = set()
    for raw in workstreams:
        if not isinstance(raw, dict):
            raise ContractError("workstream must be an object")
        exact_keys(raw, {"workstream_id", "bucket", "objective", "activities", "acceptance_evidence", "assumptions"}, "workstream")
        wid = token(raw["workstream_id"], "workstream.workstream_id")
        bucket = token(raw["bucket"], "workstream.bucket")
        if wid in ws_ids:
            raise ContractError("duplicate workstream_id")
        if bucket in buckets:
            raise ContractError("duplicate workstream bucket")
        ws_ids.add(wid)
        buckets.add(bucket)
        normalized_workstreams.append({"workstream_id": wid, "bucket": bucket, "objective": text(raw["objective"], "workstream.objective", 1500), "activities": list(unique_texts(raw["activities"], "workstream.activities", max_items=16)), "acceptance_evidence": list(unique_texts(raw["acceptance_evidence"], "workstream.acceptance_evidence", max_items=16)), "assumptions": list(unique_texts(raw["assumptions"], "workstream.assumptions", allow_empty=True, max_items=16))})
    missing_ws = _REQUIRED_WORKSTREAMS - buckets
    if missing_ws:
        raise ContractError(f"missing published work buckets: {sorted(missing_ws)}")

    evidence = packet["company_evidence"]
    if not isinstance(evidence, dict) or not evidence:
        raise ContractError("company_evidence must be a non-empty object")
    normalized_evidence: dict[str, str] = {}
    for key, value in evidence.items():
        k = token(key, "company_evidence key")
        v = token(value, f"company_evidence.{k}")
        if v not in _ALLOWED_EVIDENCE:
            raise ContractError(f"unsupported evidence state for {k}")
        normalized_evidence[k] = v
    for required in ("ruby_rails_delivery", "legal_vendor_eligibility", "relevant_past_performance", "named_staffing"):
        if required not in normalized_evidence:
            raise ContractError(f"missing company evidence gate: {required}")

    commercial = packet["commercial"]
    if not isinstance(commercial, dict):
        raise ContractError("commercial must be an object")
    exact_keys(commercial, {"currency", "amount_minor", "pricing_status", "pricing_basis", "offer_status", "assumptions"}, "commercial")
    currency = token(commercial["currency"], "commercial.currency")
    if not re.fullmatch(r"[A-Z]{3}", currency):
        raise ContractError("commercial.currency must be three uppercase letters")
    amount = commercial["amount_minor"]
    if amount is not None:
        amount = strict_int(amount, "commercial.amount_minor", minimum=1)
    pricing_status = token(commercial["pricing_status"], "commercial.pricing_status")
    if pricing_status not in _ALLOWED_COMMERCIAL:
        raise ContractError("unsupported commercial.pricing_status")
    if pricing_status == "OWNER_DECISION_REQUIRED" and amount is not None:
        raise ContractError("owner-decision pricing cannot include an amount")
    if pricing_status == "PROPOSED_NOT_SUBMITTED" and amount is None:
        raise ContractError("proposed pricing requires amount_minor")
    if commercial["offer_status"] != "NOT_SUBMITTED":
        raise ContractError("v1 offer_status must remain NOT_SUBMITTED")
    normalized_commercial = {"currency": currency, "amount_minor": amount, "pricing_status": pricing_status, "pricing_basis": text(commercial["pricing_basis"], "commercial.pricing_basis", 2000), "offer_status": "NOT_SUBMITTED", "assumptions": list(unique_texts(commercial["assumptions"], "commercial.assumptions", allow_empty=True, max_items=32))}

    return {"schema": INPUT_SCHEMA, "opportunity": normalized_opp, "sources": sorted(normalized_sources, key=lambda row: row["source_id"]), "controlling_unknowns": sorted(normalized_unknowns, key=lambda row: row["category"]), "technical_baseline": normalized_baseline, "workstreams": sorted(normalized_workstreams, key=lambda row: row["bucket"]), "company_evidence": dict(sorted(normalized_evidence.items())), "commercial": normalized_commercial}


def compile_proposal(packet: Any, *, as_of: datetime) -> dict[str, Any]:
    normalized = normalize(packet)
    now = trusted_time(as_of, "as_of")
    now_text = utc_text(now)
    current_source_ids = [row["source_id"] for row in normalized["sources"] if utc(row["observed_at"], "source.observed_at") <= now <= utc(row["fresh_until"], "source.fresh_until")]
    stale_source_ids = [row["source_id"] for row in normalized["sources"] if now > utc(row["fresh_until"], "source.fresh_until")]
    if normalized["technical_baseline"]["repo_source_id"] not in current_source_ids:
        raise ContractError("buyer-owned repository evidence is not current at evaluation time")
    unresolved = [row for row in normalized["controlling_unknowns"] if row["resolution_evidence"] is None]
    blocking_unknowns = [row["category"] for row in unresolved if row["blocking"]]
    evidence_gaps = sorted(key for key, value in normalized["company_evidence"].items() if value != "VERIFIED")
    technical_ready = set(row["bucket"] for row in normalized["workstreams"]) >= _REQUIRED_WORKSTREAMS
    pricing_ready = normalized["commercial"]["pricing_status"] == "PROPOSED_NOT_SUBMITTED" and normalized["commercial"]["amount_minor"] is not None
    submission_ready = technical_ready and not blocking_unknowns and not evidence_gaps and pricing_ready and not stale_source_ids
    if submission_ready:
        raise ContractError("v1 cannot become submission-ready without a new controlling-source generation")
    authority = {"contact_authorized": False, "submission_authorized": False, "signature_authorized": False, "personnel_commitment_authorized": False, "contract_acceptance_claimed": False, "deployment_authorized": False, "award_claimed": False, "payment_claimed": False, "revenue_recognition_authorized": False}
    core = {
        "schema": REPORT_SCHEMA,
        "buyer_id": normalized["opportunity"]["buyer_id"],
        "opportunity_id": normalized["opportunity"]["opportunity_id"],
        "project_name": normalized["opportunity"]["project_name"],
        "target_role": normalized["opportunity"]["target_role"],
        "technical_readiness": "TECHNICALLY_READY" if technical_ready else "TECHNICAL_HOLD",
        "submission_readiness": "SUBMISSION_READY" if submission_ready else "HOLD_CONTROLLING_SOURCE",
        "blocking_unknowns": blocking_unknowns,
        "company_evidence_gaps": evidence_gaps,
        "current_source_ids": current_source_ids,
        "stale_source_ids": stale_source_ids,
        "technical_baseline": normalized["technical_baseline"],
        "workstreams": normalized["workstreams"],
        "commercial": normalized["commercial"],
        "authority": authority,
        "source_manifest_sha256": digest(normalized["sources"]),
        "input_sha256": digest(normalized),
    }
    state_sha = digest(core)
    historical = {**core, "evaluated_at": now_text, "state_sha256": state_sha}
    return {**historical, "receipt_sha256": digest(historical)}


def verify_report(packet: Any, report: Any, *, current_as_of: datetime) -> dict[str, Any]:
    if not isinstance(report, dict):
        raise ContractError("report must be an object")
    expected = {"schema", "buyer_id", "opportunity_id", "project_name", "target_role", "technical_readiness", "submission_readiness", "blocking_unknowns", "company_evidence_gaps", "current_source_ids", "stale_source_ids", "technical_baseline", "workstreams", "commercial", "authority", "source_manifest_sha256", "input_sha256", "evaluated_at", "state_sha256", "receipt_sha256"}
    exact_keys(report, expected, "report")
    if report["schema"] != REPORT_SCHEMA:
        raise ContractError("unsupported report schema")
    receipt = report["receipt_sha256"]
    if not isinstance(receipt, str) or not re.fullmatch(r"[0-9a-f]{64}", receipt):
        raise ContractError("invalid report receipt")
    payload = {key: value for key, value in report.items() if key != "receipt_sha256"}
    historical_receipt_valid = digest(payload) == receipt
    evaluated = utc(report["evaluated_at"], "report.evaluated_at")
    historical = compile_proposal(packet, as_of=evaluated)
    historical_exact = historical == report
    current = compile_proposal(packet, as_of=current_as_of)
    current_same_state = current["state_sha256"] == report["state_sha256"]
    verdict = "CURRENT_TECHNICAL_CARRIER_VERIFIED" if historical_receipt_valid and historical_exact and current_same_state else "STALE_OR_DRIFTED"
    verification = {"schema": VERIFY_SCHEMA, "verdict": verdict, "historical_receipt_valid": historical_receipt_valid, "historical_exact": historical_exact, "current_same_state": current_same_state, "current_submission_readiness": current["submission_readiness"], "report_receipt_sha256": receipt, "current_state_sha256": current["state_sha256"]}
    return {**verification, "receipt_sha256": digest(verification)}


def render_markdown(report: Mapping[str, Any]) -> str:
    if report.get("schema") != REPORT_SCHEMA:
        raise ContractError("not a WRI OTP proposal report")
    baseline = report["technical_baseline"]
    commercial = report["commercial"]
    lines = [
        "# World Resources Institute — Open Timber Portal technical proposal carrier",
        "",
        f"**Target surface:** {report['target_role']}  ",
        f"**Technical readiness:** `{report['technical_readiness']}`  ",
        f"**Submission readiness:** `{report['submission_readiness']}`  ",
        f"**Receipt:** `{report['receipt_sha256']}`",
        "",
        "## Source-bound technical baseline",
        "",
        f"- Buyer-owned repository: {baseline['repo_url']}",
        f"- Application: {baseline['application']}",
        f"- Runtime: {baseline['runtime']}",
        f"- Data: {baseline['database']} + {baseline['spatial_extension']}",
        f"- Background processing: {baseline['queue']}",
        f"- Hosting: {baseline['hosting']}",
        f"- Provisioning: {baseline['provisioning']}",
        f"- Deployment: {baseline['deployment']}",
        f"- Test path: `{baseline['test_command']}` / `{baseline['parallel_test_command']}`",
        "",
        "## Six-month delivery plan",
        "",
    ]
    for ws in report["workstreams"]:
        lines += [f"### {ws['workstream_id']} — {ws['bucket']}", ws["objective"], "", "**Activities**", *[f"- {item}" for item in ws["activities"]], "", "**Acceptance evidence**", *[f"- {item}" for item in ws["acceptance_evidence"]]]
        if ws["assumptions"]:
            lines += ["", "**Assumptions**", *[f"- {item}" for item in ws["assumptions"]]]
        lines.append("")
    lines += [
        "## Commercial posture",
        "",
        f"- Status: `{commercial['pricing_status']}` / `{commercial['offer_status']}`",
        f"- Currency: {commercial['currency']}",
        f"- Amount (minor units): {commercial['amount_minor'] if commercial['amount_minor'] is not None else 'UNSET'}",
        f"- Basis: {commercial['pricing_basis']}",
        "",
        "## Blocking procurement facts",
        "",
    ]
    lines.extend(f"- `{item}`" for item in report["blocking_unknowns"])
    lines += ["", "## Company evidence still required", ""]
    lines.extend(f"- `{item}`" for item in report["company_evidence_gaps"])
    lines += ["", "## Authority ceiling", "", "This carrier does not authorize contact or submission, commit personnel, sign or accept a contract, deploy into WRI infrastructure, claim an award or payment, or recognize revenue.", ""]
    return "\n".join(lines)
