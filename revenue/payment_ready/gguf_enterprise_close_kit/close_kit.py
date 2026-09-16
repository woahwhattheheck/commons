from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

AUTHORITY_SCHEMA = "tjlabs.gguf-12k-authority/v1"
INTAKE_SCHEMA = "tjlabs.gguf-12k-intake/v1"
EVIDENCE_SCHEMA = "tjlabs.gguf-12k-delivery-evidence/v1"
ACCEPTANCE_SCHEMA = "tjlabs.gguf-12k-acceptance/v1"
CLOSE_PACKET_SCHEMA = "tjlabs.gguf-12k-close-packet/v1"

OFFER_ID = "gguf-diagnostic-10d-12k"
PUBLIC_PRODUCT_NAME = "White Box diagnostic"
FIXED_AMOUNT_USD = 12000
TERM_CALENDAR_DAYS = 10
M1_AMOUNT_USD = 6000
M2_AMOUNT_USD = 6000
M1_DUE = "before customer file exchange; after NDA and SOW signing"
ACCEPTANCE_RULE = "rollback evidence, not metric lift"
ACCEPTANCE_IDS = ("AT1", "AT2", "AT3", "AT4", "AT5", "AT6")
PUBLIC_SURFACE = "diagnostic.html"
CANONICAL_PACK = "revenue/payment_ready/pack.json"
CANONICAL_RECOVERY = "revenue/payment_ready/recovery.json"
SAFE_EVIDENCE_NONE = "NONE"

AUTHORITY_FALSE = {
    "buyer_contact_authorized": False,
    "private_file_transfer_authorized": False,
    "nda_signed": False,
    "sow_signed": False,
    "m1_payment_received": False,
    "customer_acceptance_recorded": False,
    "invoice_authorized": False,
    "payment_mutation_authorized": False,
    "revenue_recognized": False,
}

SHA_RE = re.compile(r"^[0-9a-f]{64}$")
ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,95}$")
SENSITIVE_KEY_PARTS = {
    "password",
    "passwd",
    "secret_value",
    "credential_value",
    "private_key",
    "api_key",
    "auth_token",
    "access_token",
    "routing_number",
    "account_number",
    "card_number",
    "cvv",
    "tax_id",
    "model_bytes",
    "gguf_bytes",
    "raw_model",
    "signed_document_bytes",
}


class ContractError(ValueError):
    pass


def _pairs_no_dupes(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise ContractError(f"duplicate JSON key: {key}")
        out[key] = value
    return out


def strict_loads(text: str) -> Any:
    return json.loads(
        text,
        object_pairs_hook=_pairs_no_dupes,
        parse_constant=lambda token: (_ for _ in ()).throw(
            ContractError(f"non-finite number: {token}")
        ),
    )


def strict_load(path: str | Path) -> Any:
    return strict_loads(Path(path).read_text(encoding="utf-8"))


def canonical_json(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _dict(value: Any, where: str) -> dict[str, Any]:
    if type(value) is not dict:
        raise ContractError(f"{where}: object required")
    return value


def _list(value: Any, where: str, *, min_items: int = 0, max_items: int = 1000) -> list[Any]:
    if type(value) is not list or not (min_items <= len(value) <= max_items):
        raise ContractError(f"{where}: list length in [{min_items}, {max_items}] required")
    return value


def _exact_keys(value: Any, keys: set[str], where: str) -> dict[str, Any]:
    obj = _dict(value, where)
    if set(obj) != keys:
        raise ContractError(
            f"{where}: key mismatch missing={sorted(keys - set(obj))} extra={sorted(set(obj) - keys)}"
        )
    return obj


def _text(value: Any, where: str, *, max_len: int = 2000) -> str:
    if type(value) is not str or not value or len(value) > max_len:
        raise ContractError(f"{where}: bounded non-empty string required")
    if any(ord(ch) < 32 and ch not in "\t\n" for ch in value):
        raise ContractError(f"{where}: control characters forbidden")
    return value


def _ident(value: Any, where: str) -> str:
    text = _text(value, where, max_len=96)
    if not ID_RE.fullmatch(text):
        raise ContractError(f"{where}: safe identifier required")
    return text


def _bool(value: Any, where: str) -> bool:
    if type(value) is not bool:
        raise ContractError(f"{where}: bool required")
    return value


def _int(value: Any, where: str, lo: int = 0, hi: int = 2**63 - 1) -> int:
    if type(value) is not int or not (lo <= value <= hi):
        raise ContractError(f"{where}: integer in [{lo}, {hi}] required")
    return value


def _sha(value: Any, where: str, *, allow_none: bool = False) -> str:
    if allow_none and value == SAFE_EVIDENCE_NONE:
        return value
    text = _text(value, where, max_len=64)
    if not SHA_RE.fullmatch(text):
        raise ContractError(f"{where}: lowercase SHA-256 required")
    return text


def _https(value: Any, where: str) -> str:
    text = _text(value, where, max_len=500)
    parsed = urlparse(text)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ContractError(f"{where}: public HTTPS URL required")
    if parsed.query or parsed.fragment:
        raise ContractError(f"{where}: query/fragment forbidden")
    return text


def _assert_no_sensitive_keys(value: Any, where: str = "document") -> None:
    if type(value) is dict:
        for key, child in value.items():
            lowered = str(key).lower()
            if any(part in lowered for part in SENSITIVE_KEY_PARTS):
                raise ContractError(f"{where}.{key}: sensitive/raw field name forbidden")
            _assert_no_sensitive_keys(child, f"{where}.{key}")
    elif type(value) is list:
        for index, child in enumerate(value):
            _assert_no_sensitive_keys(child, f"{where}[{index}]")


def _add_receipt(packet: dict[str, Any]) -> dict[str, Any]:
    out = dict(packet)
    out["receipt_sha256"] = sha256_hex(canonical_json(packet))
    return out


def _validate_authority_packet(authority: Any) -> dict[str, Any]:
    auth = _dict(authority, "authority")
    if auth.get("schema") != AUTHORITY_SCHEMA:
        raise ContractError("authority: unsupported schema")
    expected = {
        "offer_id": OFFER_ID,
        "public_product_name": PUBLIC_PRODUCT_NAME,
        "fixed_amount_usd": FIXED_AMOUNT_USD,
        "term_calendar_days": TERM_CALENDAR_DAYS,
        "m1_amount_usd": M1_AMOUNT_USD,
        "m1_due": M1_DUE,
        "m2_amount_usd": M2_AMOUNT_USD,
        "acceptance_rule": ACCEPTANCE_RULE,
        "acceptance_ids": list(ACCEPTANCE_IDS),
        "public_surface": PUBLIC_SURFACE,
        "public_surface_kind": "PURCHASE_INTENT_ONLY",
        "payment_collection_on_public_surface": False,
    }
    for key, value in expected.items():
        if auth.get(key) != value:
            raise ContractError(f"authority.{key}: canonical authority drift")
    for field in AUTHORITY_FALSE:
        if auth.get(field) is not False:
            raise ContractError(f"authority.{field}: must remain false")
    for digest_field in ("pack_sha256", "recovery_sha256"):
        _sha(auth.get(digest_field), f"authority.{digest_field}")
    _text(auth.get("canonical_demand"), "authority.canonical_demand", max_len=64)
    _text(auth.get("canonical_cash_state"), "authority.canonical_cash_state", max_len=64)
    _int(auth.get("canonical_collected_cash_usd"), "authority.canonical_collected_cash_usd", 0)
    receipt = _sha(auth.get("receipt_sha256"), "authority.receipt_sha256")
    unsigned = dict(auth)
    unsigned.pop("receipt_sha256", None)
    if receipt != sha256_hex(canonical_json(unsigned)):
        raise ContractError("authority.receipt_sha256: receipt mismatch")
    return auth


def _authority_packet(pack: Any, recovery: Any) -> dict[str, Any]:
    p = _dict(pack, "pack")
    r = _dict(recovery, "recovery")
    offer = _dict(p.get("offer"), "pack.offer")
    rec_offer = _dict(r.get("offer"), "recovery.offer")

    if offer.get("offer_id") != OFFER_ID or rec_offer.get("offer_id") != OFFER_ID:
        raise ContractError("canonical offer id drift")
    if offer.get("public_product_name") != PUBLIC_PRODUCT_NAME:
        raise ContractError("canonical public product name drift")
    if offer.get("fixed_amount") != FIXED_AMOUNT_USD or rec_offer.get("fixed_amount") != FIXED_AMOUNT_USD:
        raise ContractError("canonical fixed amount drift")
    if offer.get("term_calendar_days") != TERM_CALENDAR_DAYS or rec_offer.get("term_calendar_days") != TERM_CALENDAR_DAYS:
        raise ContractError("canonical term drift")
    if offer.get("acceptance_rule") != ACCEPTANCE_RULE or rec_offer.get("acceptance_rule") != ACCEPTANCE_RULE:
        raise ContractError("canonical acceptance rule drift")
    if offer.get("payment_collection") != "NOT_PROVIDED_ON_THIS_PAGE":
        raise ContractError("canonical payment-collection boundary drift")

    milestones = _list(offer.get("milestones"), "pack.offer.milestones", min_items=2, max_items=2)
    m1 = _dict(milestones[0], "pack.offer.milestones[0]")
    m2 = _dict(milestones[1], "pack.offer.milestones[1]")
    if (m1.get("id"), m1.get("amount"), m1.get("due")) != ("M1_BEFORE_FILE", M1_AMOUNT_USD, M1_DUE):
        raise ContractError("canonical M1 drift")
    if (m2.get("id"), m2.get("amount")) != ("M2_AT1_AT6", M2_AMOUNT_USD):
        raise ContractError("canonical M2 drift")

    pack_tests = tuple(
        _dict(row, "pack.acceptance_tests[]").get("id")
        for row in _list(p.get("acceptance_tests"), "pack.acceptance_tests", min_items=6, max_items=6)
    )
    recovery_tests = tuple(
        _list(rec_offer.get("acceptance_tests"), "recovery.offer.acceptance_tests", min_items=6, max_items=6)
    )
    if pack_tests != ACCEPTANCE_IDS or recovery_tests != ACCEPTANCE_IDS:
        raise ContractError("canonical AT1-AT6 set/order drift")

    public = _dict(r.get("public_surface"), "recovery.public_surface")
    if public.get("path") != PUBLIC_SURFACE:
        raise ContractError("canonical public surface drift")
    for field in ("no_login", "no_auth", "no_gate"):
        if public.get(field) is not True:
            raise ContractError(f"canonical public surface {field} drift")

    processor = _dict(r.get("processor_handoff"), "recovery.processor_handoff")
    if processor.get("values_never_enter_commons") is not True:
        raise ContractError("processor private-values boundary drift")
    if processor.get("recommended_provider") != "Stripe":
        raise ContractError("processor recommendation drift")

    truth = _dict(r.get("truth"), "recovery.truth")
    collected_cash = _int(truth.get("collected_cash_usd"), "recovery.truth.collected_cash_usd", 0)
    packet = {
        "schema": AUTHORITY_SCHEMA,
        "offer_id": OFFER_ID,
        "public_product_name": PUBLIC_PRODUCT_NAME,
        "fixed_amount_usd": FIXED_AMOUNT_USD,
        "term_calendar_days": TERM_CALENDAR_DAYS,
        "m1_amount_usd": M1_AMOUNT_USD,
        "m1_due": M1_DUE,
        "m2_amount_usd": M2_AMOUNT_USD,
        "acceptance_rule": ACCEPTANCE_RULE,
        "acceptance_ids": list(ACCEPTANCE_IDS),
        "public_surface": PUBLIC_SURFACE,
        "public_surface_kind": "PURCHASE_INTENT_ONLY",
        "payment_collection_on_public_surface": False,
        "canonical_demand": _text(rec_offer.get("demand"), "recovery.offer.demand", max_len=64),
        "canonical_cash_state": _text(rec_offer.get("cash_state"), "recovery.offer.cash_state", max_len=64),
        "canonical_collected_cash_usd": collected_cash,
        "pack_sha256": sha256_hex(canonical_json(p)),
        "recovery_sha256": sha256_hex(canonical_json(r)),
        **AUTHORITY_FALSE,
    }
    return _add_receipt(packet)


def load_authority(repo_root: str | Path) -> dict[str, Any]:
    root = Path(repo_root)
    return _authority_packet(strict_load(root / CANONICAL_PACK), strict_load(root / CANONICAL_RECOVERY))


def validate_authority_docs(pack: Any, recovery: Any) -> dict[str, Any]:
    return _authority_packet(pack, recovery)


def validate_intake(document: Any) -> dict[str, Any]:
    _assert_no_sensitive_keys(document)
    row = _exact_keys(
        document,
        {"schema", "engagement_id", "customer_reference", "gguf", "harness", "scope", "security", "external_evidence"},
        "intake",
    )
    if row["schema"] != INTAKE_SCHEMA:
        raise ContractError("intake.schema: unsupported")
    engagement_id = _ident(row["engagement_id"], "intake.engagement_id")
    customer_reference = _ident(row["customer_reference"], "intake.customer_reference")

    gguf = _exact_keys(row["gguf"], {"sha256", "size_bytes", "control_attested"}, "intake.gguf")
    gguf_sha = _sha(gguf["sha256"], "intake.gguf.sha256")
    gguf_size = _int(gguf["size_bytes"], "intake.gguf.size_bytes", 1)
    control = _bool(gguf["control_attested"], "intake.gguf.control_attested")

    harness = _exact_keys(
        row["harness"],
        {"name", "version", "reproducible_command_sha256", "eval_suite_sha256", "ready"},
        "intake.harness",
    )
    harness_name = _text(harness["name"], "intake.harness.name", max_len=120)
    harness_version = _text(harness["version"], "intake.harness.version", max_len=80)
    command_sha = _sha(harness["reproducible_command_sha256"], "intake.harness.reproducible_command_sha256")
    eval_sha = _sha(harness["eval_suite_sha256"], "intake.harness.eval_suite_sha256")
    harness_ready = _bool(harness["ready"], "intake.harness.ready")

    scope = _exact_keys(row["scope"], {"objective", "bounded_intervention", "metric_lift_guaranteed"}, "intake.scope")
    objective = _text(scope["objective"], "intake.scope.objective", max_len=1000)
    bounded_intervention = _bool(scope["bounded_intervention"], "intake.scope.bounded_intervention")
    if _bool(scope["metric_lift_guaranteed"], "intake.scope.metric_lift_guaranteed"):
        raise ContractError("intake.scope.metric_lift_guaranteed: canonical offer never guarantees metric lift")

    security = _exact_keys(
        row["security"],
        {"data_classification", "transfer_channel", "retention_days", "raw_model_public_allowed", "credentials_required", "public_contact_url"},
        "intake.security",
    )
    if security["data_classification"] != "CONFIDENTIAL_CUSTOMER_CONTROLLED":
        raise ContractError("intake.security.data_classification: unsupported")
    if security["transfer_channel"] != "OWNER_PRIVATE_EXTERNAL":
        raise ContractError("intake.security.transfer_channel: must remain owner-private external")
    retention_days = _int(security["retention_days"], "intake.security.retention_days", 0, 30)
    if _bool(security["raw_model_public_allowed"], "intake.security.raw_model_public_allowed"):
        raise ContractError("intake.security.raw_model_public_allowed: must remain false")
    if _bool(security["credentials_required"], "intake.security.credentials_required"):
        raise ContractError("intake.security.credentials_required: this carrier accepts no credentials")
    public_contact_url = _https(security["public_contact_url"], "intake.security.public_contact_url")

    external = _exact_keys(
        row["external_evidence"],
        {"nda_receipt_sha256", "sow_receipt_sha256", "m1_payment_receipt_sha256"},
        "intake.external_evidence",
    )
    nda = _sha(external["nda_receipt_sha256"], "intake.external_evidence.nda_receipt_sha256", allow_none=True)
    sow = _sha(external["sow_receipt_sha256"], "intake.external_evidence.sow_receipt_sha256", allow_none=True)
    m1 = _sha(external["m1_payment_receipt_sha256"], "intake.external_evidence.m1_payment_receipt_sha256", allow_none=True)

    holds: list[str] = []
    if not control:
        holds.append("HOLD_GGUF_CONTROL")
    if not harness_ready:
        holds.append("HOLD_HARNESS_NOT_READY")
    if not bounded_intervention:
        holds.append("HOLD_UNBOUNDED_SCOPE")
    if nda == SAFE_EVIDENCE_NONE:
        holds.append("HOLD_NDA_EXTERNAL_EVIDENCE")
    if sow == SAFE_EVIDENCE_NONE:
        holds.append("HOLD_SOW_EXTERNAL_EVIDENCE")
    if m1 == SAFE_EVIDENCE_NONE:
        holds.append("HOLD_M1_EXTERNAL_EVIDENCE")

    packet = {
        "schema": INTAKE_SCHEMA,
        "engagement_id": engagement_id,
        "customer_reference": customer_reference,
        "gguf_sha256": gguf_sha,
        "gguf_size_bytes": gguf_size,
        "harness_name": harness_name,
        "harness_version": harness_version,
        "harness_command_sha256": command_sha,
        "eval_suite_sha256": eval_sha,
        "objective": objective,
        "retention_days": retention_days,
        "public_contact_url": public_contact_url,
        "external_prerequisite_receipts_present": {
            "nda": nda != SAFE_EVIDENCE_NONE,
            "sow": sow != SAFE_EVIDENCE_NONE,
            "m1_payment": m1 != SAFE_EVIDENCE_NONE,
        },
        "qualification_state": "READY_FOR_OWNER_PRIVATE_REVIEW" if not holds else "HOLD",
        "holds": holds,
        **AUTHORITY_FALSE,
    }
    return _add_receipt(packet)


def evaluate_acceptance(intake: Any, evidence: Any) -> dict[str, Any]:
    intake_result = validate_intake(intake)
    _assert_no_sensitive_keys(evidence)
    row = _exact_keys(
        evidence,
        {"schema", "engagement_id", "artifacts", "harness_runs", "finding", "delivery_receipt", "payment_reference_sha256"},
        "evidence",
    )
    if row["schema"] != EVIDENCE_SCHEMA:
        raise ContractError("evidence.schema: unsupported")
    engagement_id = _ident(row["engagement_id"], "evidence.engagement_id")
    if engagement_id != intake_result["engagement_id"]:
        raise ContractError("evidence.engagement_id: intake mismatch")

    artifacts = _exact_keys(row["artifacts"], {"original", "ablated", "restored"}, "evidence.artifacts")
    parsed: dict[str, tuple[str, int]] = {}
    for name in ("original", "ablated", "restored"):
        artifact = _exact_keys(artifacts[name], {"sha256", "size_bytes"}, f"evidence.artifacts.{name}")
        parsed[name] = (
            _sha(artifact["sha256"], f"evidence.artifacts.{name}.sha256"),
            _int(artifact["size_bytes"], f"evidence.artifacts.{name}.size_bytes", 1),
        )

    runs = _exact_keys(
        row["harness_runs"],
        {"baseline_receipt_sha256", "ablation_receipt_sha256", "restore_receipt_sha256"},
        "evidence.harness_runs",
    )
    run_hashes = [
        _sha(runs["baseline_receipt_sha256"], "evidence.harness_runs.baseline_receipt_sha256"),
        _sha(runs["ablation_receipt_sha256"], "evidence.harness_runs.ablation_receipt_sha256"),
        _sha(runs["restore_receipt_sha256"], "evidence.harness_runs.restore_receipt_sha256"),
    ]

    finding = _exact_keys(row["finding"], {"report_sha256", "statement", "limitations"}, "evidence.finding")
    report_sha = _sha(finding["report_sha256"], "evidence.finding.report_sha256")
    statement = _text(finding["statement"], "evidence.finding.statement", max_len=1200)
    limitations = [
        _text(value, f"evidence.finding.limitations[{index}]", max_len=500)
        for index, value in enumerate(_list(finding["limitations"], "evidence.finding.limitations", min_items=1, max_items=20))
    ]

    delivery = _exact_keys(row["delivery_receipt"], {"receipt_sha256", "artifact_hashes"}, "evidence.delivery_receipt")
    delivery_sha = _sha(delivery["receipt_sha256"], "evidence.delivery_receipt.receipt_sha256")
    manifest_hashes = [
        _sha(value, f"evidence.delivery_receipt.artifact_hashes[{index}]")
        for index, value in enumerate(
            _list(delivery["artifact_hashes"], "evidence.delivery_receipt.artifact_hashes", min_items=7, max_items=32)
        )
    ]
    if len(manifest_hashes) != len(set(manifest_hashes)):
        raise ContractError("evidence.delivery_receipt.artifact_hashes: duplicate hashes forbidden")

    payment_reference = _sha(row["payment_reference_sha256"], "evidence.payment_reference_sha256", allow_none=True)
    original_sha, original_size = parsed["original"]
    ablated_sha, _ = parsed["ablated"]
    restored_sha, restored_size = parsed["restored"]
    required_hashes = {original_sha, ablated_sha, restored_sha, *run_hashes, report_sha}

    tests = {
        "AT1": original_sha == intake_result["gguf_sha256"] and original_size == intake_result["gguf_size_bytes"],
        "AT2": ablated_sha != original_sha,
        "AT3": restored_sha == original_sha and restored_size == original_size,
        "AT4": len(set(run_hashes)) == 3,
        "AT5": bool(statement.strip()) and bool(limitations),
        "AT6": required_hashes.issubset(set(manifest_hashes)),
    }
    failed = [test_id for test_id in ACCEPTANCE_IDS if not tests[test_id]]
    if intake_result["qualification_state"] != "READY_FOR_OWNER_PRIVATE_REVIEW":
        verdict = "HOLD_INTAKE_PREREQUISITES"
    elif failed:
        verdict = "HOLD_ACCEPTANCE_EVIDENCE"
    else:
        verdict = "AT1_AT6_EVIDENCE_READY_FOR_CUSTOMER_REVIEW"

    return _add_receipt(
        {
            "schema": ACCEPTANCE_SCHEMA,
            "engagement_id": engagement_id,
            "acceptance_rule": ACCEPTANCE_RULE,
            "tests": tests,
            "failed_tests": failed,
            "verdict": verdict,
            "payment_reference_present": payment_reference != SAFE_EVIDENCE_NONE,
            "payment_reference_proves_acceptance": False,
            "delivery_receipt_sha256": delivery_sha,
            "finding_report_sha256": report_sha,
            **AUTHORITY_FALSE,
        }
    )


def compile_close_packet(authority: Any, intake: Any, evidence: Any | None = None) -> dict[str, Any]:
    auth = _validate_authority_packet(authority)
    intake_result = validate_intake(intake)
    acceptance = evaluate_acceptance(intake, evidence) if evidence is not None else None
    if acceptance is None:
        state = "READY_FOR_OWNER_PRIVATE_REVIEW" if intake_result["qualification_state"] == "READY_FOR_OWNER_PRIVATE_REVIEW" else "HOLD"
    elif acceptance["verdict"] == "AT1_AT6_EVIDENCE_READY_FOR_CUSTOMER_REVIEW":
        state = "READY_FOR_CUSTOMER_ACCEPTANCE_REVIEW"
    else:
        state = "HOLD"
    return _add_receipt(
        {
            "schema": CLOSE_PACKET_SCHEMA,
            "offer_id": OFFER_ID,
            "authority_receipt_sha256": auth["receipt_sha256"],
            "intake_receipt_sha256": intake_result["receipt_sha256"],
            "acceptance_receipt_sha256": acceptance["receipt_sha256"] if acceptance else SAFE_EVIDENCE_NONE,
            "state": state,
            "customer_acceptance_required": True,
            "customer_acceptance_is_external_event": True,
            "public_purchase_intent_is_not_payment": True,
            "payment_reference_is_not_acceptance": True,
            "metric_lift_is_not_acceptance": True,
            "rollback_evidence_is_required": True,
            "expansion_path": "same-GGUF $30k / 30d pilot only after real AT1-AT6 acceptance; license only after paid delivery",
            **AUTHORITY_FALSE,
        }
    )


def verify_close_packet(packet: Any, authority: Any, intake: Any, evidence: Any | None = None) -> bool:
    if type(packet) is not dict:
        return False
    try:
        expected = compile_close_packet(authority, intake, evidence)
    except (ContractError, KeyError, TypeError, ValueError):
        return False
    return canonical_json(packet) == canonical_json(expected)
