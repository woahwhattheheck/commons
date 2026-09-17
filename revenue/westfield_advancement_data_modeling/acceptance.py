#!/usr/bin/env python3
"""Deterministic acceptance compiler for advancement-modeling workshares.

Metadata only: this does not train a donor model or consume donor PII.
"""
from __future__ import annotations
import hashlib
import json
from typing import Any, Iterable

SCHEMA = "advancement-model-acceptance/v1"
RECEIPT_SCHEMA = "advancement-model-acceptance-receipt/v1"
ALLOWED_COMMERCIAL_STATES = {"PROPOSED_NOT_ACCEPTED", "ACCEPTED_UNFUNDED", "FUNDED_NOT_DELIVERED"}
REQUIRED_CHECKS = {
    "source_provenance", "entity_deduplication", "household_leakage",
    "temporal_leakage", "target_window", "calibration", "ranking_lift",
    "reproducible_handoff",
}

class ContractError(ValueError):
    pass

def _strict_object(pairs: Iterable[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise ContractError(f"duplicate key: {key}")
        out[key] = value
    return out

def load_strict_json(text: str) -> dict[str, Any]:
    def bad_constant(value: str) -> None:
        raise ContractError(f"non-finite number: {value}")
    obj = json.loads(text, object_pairs_hook=_strict_object, parse_constant=bad_constant)
    if not isinstance(obj, dict):
        raise ContractError("top-level JSON must be an object")
    return obj

def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)

def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()

def _expect_keys(obj: dict[str, Any], *, required: set[str], optional: set[str] | None = None, where: str) -> None:
    optional = optional or set()
    missing = required - obj.keys()
    extra = obj.keys() - required - optional
    if missing:
        raise ContractError(f"{where}: missing keys {sorted(missing)}")
    if extra:
        raise ContractError(f"{where}: unexpected keys {sorted(extra)}")

def _expect_bool(value: Any, where: str) -> bool:
    if type(value) is not bool:
        raise ContractError(f"{where}: must be boolean")
    return value

def _expect_str(value: Any, where: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ContractError(f"{where}: must be non-empty string")
    return value.strip()

def _expect_str_list(value: Any, where: str) -> list[str]:
    if not isinstance(value, list) or not value:
        raise ContractError(f"{where}: must be non-empty array")
    out: list[str] = []
    for i, item in enumerate(value):
        item = _expect_str(item, f"{where}[{i}]")
        if item in out:
            raise ContractError(f"{where}: duplicate value {item!r}")
        out.append(item)
    return out

def _validate_authority(authority: dict[str, Any]) -> None:
    required = {
        "prime_vendor_confirmed", "buyer_approved", "references_verified",
        "production_data_access", "award_received", "payment_received",
        "revenue_recognized",
    }
    _expect_keys(authority, required=required, where="authority")
    for key in sorted(authority):
        if _expect_bool(authority[key], f"authority.{key}"):
            raise ContractError(f"authority.{key}: must remain false in this pre-award carrier")

def _validate_sources(sources: Any) -> list[dict[str, str]]:
    if not isinstance(sources, list) or not sources:
        raise ContractError("sources: must be non-empty array")
    out: list[dict[str, str]] = []
    seen: set[str] = set()
    for i, row in enumerate(sources):
        if not isinstance(row, dict):
            raise ContractError(f"sources[{i}]: must be object")
        _expect_keys(row, required={"kind", "url"}, optional={"note"}, where=f"sources[{i}]")
        kind = _expect_str(row["kind"], f"sources[{i}].kind")
        url = _expect_str(row["url"], f"sources[{i}].url")
        if not url.startswith("https://"):
            raise ContractError(f"sources[{i}].url: https required")
        if url in seen:
            raise ContractError(f"sources[{i}].url: duplicate")
        seen.add(url)
        record = {"kind": kind, "url": url}
        if "note" in row:
            record["note"] = _expect_str(row["note"], f"sources[{i}].note")
        out.append(record)
    return out

def _validate_metrics(metrics: dict[str, Any]) -> None:
    _expect_keys(metrics, required={"calibration", "ranking", "evaluation_split"}, where="model_acceptance.metrics")
    if metrics["calibration"] not in {"brier_and_reliability", "log_loss_and_reliability"}:
        raise ContractError("model_acceptance.metrics.calibration: unsupported")
    if metrics["ranking"] not in {"lift_at_k", "precision_recall_at_k"}:
        raise ContractError("model_acceptance.metrics.ranking: unsupported")
    if metrics["evaluation_split"] != "temporal_holdout":
        raise ContractError("model_acceptance.metrics.evaluation_split: temporal_holdout required")

def compile_acceptance(manifest: dict[str, Any]) -> dict[str, Any]:
    _expect_keys(manifest, required={"schema", "opportunity", "commercial", "sources", "authority", "workshare", "model_acceptance"}, where="manifest")
    if manifest["schema"] != SCHEMA:
        raise ContractError(f"schema: expected {SCHEMA!r}")

    opp = manifest["opportunity"]
    if not isinstance(opp, dict):
        raise ContractError("opportunity: must be object")
    _expect_keys(opp, required={"buyer", "solicitation", "deadline", "submission_route"}, where="opportunity")
    opportunity = {k: _expect_str(opp[k], f"opportunity.{k}") for k in opp}

    commercial = manifest["commercial"]
    if not isinstance(commercial, dict):
        raise ContractError("commercial: must be object")
    _expect_keys(commercial, required={"role", "state", "pricing_basis"}, where="commercial")
    if commercial["role"] != "paid_subcontract_workshare":
        raise ContractError("commercial.role: paid_subcontract_workshare required")
    if commercial["state"] not in ALLOWED_COMMERCIAL_STATES:
        raise ContractError("commercial.state: unsupported")
    pricing_basis = _expect_str(commercial["pricing_basis"], "commercial.pricing_basis")
    if "$" in pricing_basis or "£" in pricing_basis:
        raise ContractError("commercial.pricing_basis: binding price is not admitted")

    sources = _validate_sources(manifest["sources"])
    authority = manifest["authority"]
    if not isinstance(authority, dict):
        raise ContractError("authority: must be object")
    _validate_authority(authority)

    workshare = manifest["workshare"]
    if not isinstance(workshare, dict):
        raise ContractError("workshare: must be object")
    _expect_keys(workshare, required={"deliverables", "exclusions"}, where="workshare")
    deliverables = _expect_str_list(workshare["deliverables"], "workshare.deliverables")
    exclusions = _expect_str_list(workshare["exclusions"], "workshare.exclusions")

    acceptance = manifest["model_acceptance"]
    if not isinstance(acceptance, dict):
        raise ContractError("model_acceptance: must be object")
    _expect_keys(acceptance, required={"entity_key_policy", "time_anchor_policy", "required_checks", "metrics", "handoff_artifacts"}, where="model_acceptance")
    entity_policy = _expect_str(acceptance["entity_key_policy"], "model_acceptance.entity_key_policy")
    time_policy = _expect_str(acceptance["time_anchor_policy"], "model_acceptance.time_anchor_policy")
    checks = set(_expect_str_list(acceptance["required_checks"], "model_acceptance.required_checks"))
    missing_checks = REQUIRED_CHECKS - checks
    if missing_checks:
        raise ContractError(f"model_acceptance.required_checks: missing {sorted(missing_checks)}")
    metrics = acceptance["metrics"]
    if not isinstance(metrics, dict):
        raise ContractError("model_acceptance.metrics: must be object")
    _validate_metrics(metrics)
    handoff = _expect_str_list(acceptance["handoff_artifacts"], "model_acceptance.handoff_artifacts")

    return {
        "schema": SCHEMA,
        "opportunity": opportunity,
        "commercial": {"role": "paid_subcontract_workshare", "state": commercial["state"], "pricing_basis": pricing_basis},
        "sources": sources,
        "authority": {key: False for key in sorted(authority)},
        "acceptance_plan": {
            "entity_key_policy": entity_policy,
            "time_anchor_policy": time_policy,
            "required_checks": sorted(checks),
            "metrics": metrics,
            "deliverables": deliverables,
            "handoff_artifacts": handoff,
            "exclusions": exclusions,
        },
    }

def make_receipt(manifest: dict[str, Any]) -> dict[str, Any]:
    plan = compile_acceptance(manifest)
    return {
        "schema": RECEIPT_SCHEMA,
        "manifest_sha256": sha256_json(manifest),
        "plan_sha256": sha256_json(plan),
        "authority": {
            "award_received": False, "buyer_approved": False, "payment_received": False,
            "prime_vendor_confirmed": False, "production_data_access": False,
            "references_verified": False, "revenue_recognized": False,
        },
    }

def verify_receipt(manifest: dict[str, Any], receipt: dict[str, Any]) -> bool:
    return canonical_json(receipt) == canonical_json(make_receipt(manifest))

def main() -> int:
    import argparse, pathlib
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest")
    parser.add_argument("--receipt")
    args = parser.parse_args()
    manifest = load_strict_json(pathlib.Path(args.manifest).read_text(encoding="utf-8"))
    plan = compile_acceptance(manifest)
    receipt = make_receipt(manifest)
    print(canonical_json({"plan": plan, "receipt": receipt}))
    if args.receipt:
        pathlib.Path(args.receipt).write_text(canonical_json(receipt) + "\n", encoding="utf-8")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
