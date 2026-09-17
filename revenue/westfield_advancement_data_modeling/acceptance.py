#!/usr/bin/env python3
"""Deterministic, truth-bounded acceptance compiler for the Westfield workshare.

Metadata only: this does not train a donor model, consume donor PII, authenticate
live procurement sources, or create buyer/prime/payment/revenue authority.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Iterable

SCHEMA = "advancement-model-acceptance/v2"
RECEIPT_SCHEMA = "advancement-model-acceptance-receipt/v2"

COMMERCIAL_STATE = "PROPOSED_NOT_ACCEPTED"
COMMERCIAL_ROLE = "paid_subcontract_workshare"
PRICING_POSTURE = "UNPRICED_SCOPE_NEGOTIATION_REQUIRED"

EXPECTED_OPPORTUNITY = {
    "buyer": "Westfield State University",
    "solicitation": "RFP #2027-002 Advancement Data Modeling",
    "deadline": "2026-09-25",
    "submission_route": "Bonfire/Euna",
}

EXPECTED_SOURCE_URLS = {
    "buyer_official": "https://www.westfield.ma.edu/offices/open-general-bids",
    "partner_public": "https://khowconsulting.com/",
}
EXPECTED_SOURCE_NOTES = {
    "buyer_official": (
        "Pinned public source identity only; compiler does not authenticate live "
        "availability."
    ),
    "partner_public": (
        "Pinned public profile identity only; not evidence of pursuit, partnership, "
        "or solicitation-specific qualification."
    ),
}
SOURCE_PROVENANCE_MODE = "PINNED_PUBLIC_IDENTITIES_NOT_LIVE_PROVIDER_AUTHENTICATED"

ENTITY_KEY_POLICY = "CONSTITUENT_HOUSEHOLD_GROUP_BEFORE_SPLIT_V1"
TIME_ANCHOR_POLICY = "FEATURES_KNOWABLE_AT_CUTOFF_OUTCOMES_STRICTLY_AFTER_V1"

EXPECTED_DELIVERABLES = (
    "source-to-feature provenance ledger",
    "entity and household duplicate-control report",
    "time-anchored training and holdout contract",
    "calibration and ranked-lift acceptance report",
    "reproducible model-card and handoff receipt",
)
EXPECTED_EXCLUSIONS = (
    "buyer portal submission",
    "prime responsibility",
    "reference ownership",
    "production-data custody",
    "campaign strategy representation",
)
EXPECTED_HANDOFF_ARTIFACTS = (
    "data dictionary/provenance map",
    "split manifest",
    "metric definitions",
    "model/config digest",
    "acceptance exception log",
)
EXPECTED_METRICS = {
    "calibration": "brier_and_reliability",
    "ranking": "lift_at_k",
    "evaluation_split": "temporal_holdout",
}

REQUIRED_CHECKS = {
    "source_provenance",
    "entity_deduplication",
    "household_leakage",
    "temporal_leakage",
    "target_window",
    "calibration",
    "ranking_lift",
    "reproducible_handoff",
}
AUTHORITY_KEYS = {
    "prime_vendor_confirmed",
    "buyer_approved",
    "references_verified",
    "production_data_access",
    "award_received",
    "payment_received",
    "revenue_recognized",
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

    try:
        obj = json.loads(
            text,
            object_pairs_hook=_strict_object,
            parse_constant=bad_constant,
        )
    except ContractError:
        raise
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise ContractError("invalid JSON") from exc
    if not isinstance(obj, dict):
        raise ContractError("top-level JSON must be an object")
    return obj


def canonical_json(value: Any) -> str:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise ContractError("value is not canonical-JSON encodable") from exc


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _expect_keys(
    obj: dict[str, Any],
    *,
    required: set[str],
    optional: set[str] | None = None,
    where: str,
) -> None:
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
    if value != value.strip():
        raise ContractError(f"{where}: surrounding whitespace is not admitted")
    return value


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


def _expect_exact_str_list(
    value: Any,
    expected: tuple[str, ...],
    where: str,
) -> list[str]:
    if not isinstance(value, list) or len(value) != len(expected):
        raise ContractError(
            f"{where}: must equal the code-owned Westfield values in canonical order"
        )
    out = _expect_str_list(value, where)
    if tuple(out) != expected:
        raise ContractError(
            f"{where}: must equal the code-owned Westfield values in canonical order"
        )
    return list(expected)


def _validate_authority(authority: dict[str, Any]) -> None:
    _expect_keys(authority, required=AUTHORITY_KEYS, where="authority")
    for key in sorted(authority):
        if _expect_bool(authority[key], f"authority.{key}"):
            raise ContractError(
                f"authority.{key}: must remain false in this pre-award carrier"
            )


def _validate_opportunity(value: Any) -> dict[str, str]:
    if not isinstance(value, dict):
        raise ContractError("opportunity: must be object")
    _expect_keys(value, required=set(EXPECTED_OPPORTUNITY), where="opportunity")
    normalized = {
        key: _expect_str(value[key], f"opportunity.{key}")
        for key in EXPECTED_OPPORTUNITY
    }
    for key, expected in EXPECTED_OPPORTUNITY.items():
        if normalized[key] != expected:
            raise ContractError(
                f"opportunity.{key}: must equal the code-owned Westfield value"
            )
    return dict(EXPECTED_OPPORTUNITY)


def _validate_sources(value: Any) -> list[dict[str, str]]:
    if not isinstance(value, list) or len(value) != len(EXPECTED_SOURCE_URLS):
        raise ContractError(
            f"sources: exactly {len(EXPECTED_SOURCE_URLS)} admitted source rows required"
        )

    by_kind: dict[str, dict[str, str]] = {}
    for i, row in enumerate(value):
        if not isinstance(row, dict):
            raise ContractError(f"sources[{i}]: must be object")
        _expect_keys(
            row,
            required={"kind", "url", "note"},
            where=f"sources[{i}]",
        )
        kind = _expect_str(row["kind"], f"sources[{i}].kind")
        url = _expect_str(row["url"], f"sources[{i}].url")
        note = _expect_str(row["note"], f"sources[{i}].note")
        if kind in by_kind:
            raise ContractError(f"sources[{i}].kind: duplicate {kind!r}")
        if kind not in EXPECTED_SOURCE_URLS:
            raise ContractError(f"sources[{i}].kind: unadmitted source role")
        if url != EXPECTED_SOURCE_URLS[kind]:
            raise ContractError(
                f"sources[{i}].url: does not match code-owned {kind!r} source"
            )
        if note != EXPECTED_SOURCE_NOTES[kind]:
            raise ContractError(
                f"sources[{i}].note: must equal the code-owned {kind!r} boundary note"
            )
        by_kind[kind] = {"kind": kind, "url": url, "note": note}

    if set(by_kind) != set(EXPECTED_SOURCE_URLS):
        raise ContractError("sources: all code-owned source roles are required")
    return [by_kind[kind] for kind in sorted(by_kind)]


def _validate_metrics(metrics: dict[str, Any]) -> dict[str, str]:
    _expect_keys(
        metrics,
        required=set(EXPECTED_METRICS),
        where="model_acceptance.metrics",
    )
    normalized = {
        key: _expect_str(metrics[key], f"model_acceptance.metrics.{key}")
        for key in EXPECTED_METRICS
    }
    for key, expected in EXPECTED_METRICS.items():
        if normalized[key] != expected:
            raise ContractError(
                f"model_acceptance.metrics.{key}: "
                "must equal the code-owned Westfield value"
            )
    return dict(EXPECTED_METRICS)


def compile_acceptance(manifest: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(manifest, dict):
        raise ContractError("manifest: must be object")
    _expect_keys(
        manifest,
        required={
            "schema",
            "opportunity",
            "commercial",
            "sources",
            "authority",
            "workshare",
            "model_acceptance",
        },
        where="manifest",
    )
    if manifest["schema"] != SCHEMA:
        raise ContractError(f"schema: expected {SCHEMA!r}")

    opportunity = _validate_opportunity(manifest["opportunity"])

    commercial = manifest["commercial"]
    if not isinstance(commercial, dict):
        raise ContractError("commercial: must be object")
    _expect_keys(
        commercial,
        required={"role", "state", "pricing_posture"},
        where="commercial",
    )
    if commercial["role"] != COMMERCIAL_ROLE:
        raise ContractError(f"commercial.role: {COMMERCIAL_ROLE} required")
    if commercial["state"] != COMMERCIAL_STATE:
        raise ContractError(
            "commercial.state: this pre-award carrier is pinned to "
            "PROPOSED_NOT_ACCEPTED"
        )
    if commercial["pricing_posture"] != PRICING_POSTURE:
        raise ContractError(
            "commercial.pricing_posture: unpriced scope-negotiation sentinel required"
        )

    sources = _validate_sources(manifest["sources"])

    authority = manifest["authority"]
    if not isinstance(authority, dict):
        raise ContractError("authority: must be object")
    _validate_authority(authority)

    workshare = manifest["workshare"]
    if not isinstance(workshare, dict):
        raise ContractError("workshare: must be object")
    _expect_keys(
        workshare,
        required={"deliverables", "exclusions"},
        where="workshare",
    )
    deliverables = _expect_exact_str_list(
        workshare["deliverables"],
        EXPECTED_DELIVERABLES,
        "workshare.deliverables",
    )
    exclusions = _expect_exact_str_list(
        workshare["exclusions"],
        EXPECTED_EXCLUSIONS,
        "workshare.exclusions",
    )

    model_acceptance = manifest["model_acceptance"]
    if not isinstance(model_acceptance, dict):
        raise ContractError("model_acceptance: must be object")
    _expect_keys(
        model_acceptance,
        required={
            "entity_key_policy",
            "time_anchor_policy",
            "required_checks",
            "metrics",
            "handoff_artifacts",
        },
        where="model_acceptance",
    )
    if model_acceptance["entity_key_policy"] != ENTITY_KEY_POLICY:
        raise ContractError(
            f"model_acceptance.entity_key_policy: expected {ENTITY_KEY_POLICY}"
        )
    if model_acceptance["time_anchor_policy"] != TIME_ANCHOR_POLICY:
        raise ContractError(
            f"model_acceptance.time_anchor_policy: expected {TIME_ANCHOR_POLICY}"
        )

    checks = set(
        _expect_str_list(
            model_acceptance["required_checks"],
            "model_acceptance.required_checks",
        )
    )
    if checks != REQUIRED_CHECKS:
        raise ContractError(
            "model_acceptance.required_checks: must equal the closed required set"
        )

    metrics = model_acceptance["metrics"]
    if not isinstance(metrics, dict):
        raise ContractError("model_acceptance.metrics: must be object")
    normalized_metrics = _validate_metrics(metrics)
    handoff = _expect_exact_str_list(
        model_acceptance["handoff_artifacts"],
        EXPECTED_HANDOFF_ARTIFACTS,
        "model_acceptance.handoff_artifacts",
    )

    return {
        "schema": SCHEMA,
        "opportunity": opportunity,
        "commercial": {
            "role": COMMERCIAL_ROLE,
            "state": COMMERCIAL_STATE,
            "pricing_posture": PRICING_POSTURE,
        },
        "sources": sources,
        "source_provenance": {
            "mode": SOURCE_PROVENANCE_MODE,
            "live_provider_authenticated": False,
        },
        "authority": {key: False for key in sorted(AUTHORITY_KEYS)},
        "acceptance_plan": {
            "entity_key_policy": ENTITY_KEY_POLICY,
            "time_anchor_policy": TIME_ANCHOR_POLICY,
            "required_checks": sorted(REQUIRED_CHECKS),
            "metrics": normalized_metrics,
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
        "truth": {
            "commercial_state": COMMERCIAL_STATE,
            "source_provenance_mode": SOURCE_PROVENANCE_MODE,
            "live_provider_authenticated": False,
            "submission_authorized": False,
            "award_received": False,
            "payment_received": False,
            "revenue_recognized": False,
        },
    }


def verify_receipt(manifest: dict[str, Any], receipt: dict[str, Any]) -> bool:
    try:
        return canonical_json(receipt) == canonical_json(make_receipt(manifest))
    except (ContractError, TypeError, ValueError):
        return False


def main() -> int:
    import argparse
    import pathlib

    parser = argparse.ArgumentParser()
    parser.add_argument("manifest")
    parser.add_argument("--receipt")
    args = parser.parse_args()

    manifest = load_strict_json(
        pathlib.Path(args.manifest).read_text(encoding="utf-8")
    )
    plan = compile_acceptance(manifest)
    receipt = make_receipt(manifest)
    print(canonical_json({"plan": plan, "receipt": receipt}))
    if args.receipt:
        pathlib.Path(args.receipt).write_text(
            canonical_json(receipt) + "\n",
            encoding="utf-8",
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
