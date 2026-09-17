#!/usr/bin/env python3
"""Deterministic close/delivery evidence compiler for the $12k GGUF diagnostic.

This module never executes a customer's model, sends contact, touches payment
providers, or claims legal acceptance / cash / recognized revenue. It compiles
secret-free intake and digest-only benchmark evidence into a deterministic
owner-review packet bound to the existing canonical offer.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import re
import sys
from pathlib import Path
from typing import Any

OFFER_ID = "gguf-diagnostic-10d-12k"
FIXED_AMOUNT_USD = 12_000
TERM_CALENDAR_DAYS = 10
M1_AMOUNT_USD = 6_000
M2_AMOUNT_USD = 6_000
ACCEPTANCE_RULE = "rollback evidence, not metric lift"
TERMS_SHA256 = "1c0756062563415e551587a5f1ab22147366d406135de6c45ccbd3a562985730"
ACCEPTANCE_IDS = ("AT1", "AT2", "AT3", "AT4", "AT5", "AT6")
CASE_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{2,63}$")
SHA_RE = re.compile(r"^[0-9a-f]{64}$")
URL_RE = re.compile(r"https?://", re.IGNORECASE)

# Reuse the canonical GGUF revenue rail's fail-closed DLP implementation rather
# than inventing a weaker sibling regex. The helper is bound once from the exact
# repository source and the module handle is discarded; every free-text value
# retained in a public packet is checked before packet construction.
_DLP_PATH = Path(__file__).resolve().parents[2] / "host" / "revenue_recovery.py"
_DLP_SPEC = importlib.util.spec_from_file_location("gguf_close_kit_canonical_dlp", _DLP_PATH)
if _DLP_SPEC is None or _DLP_SPEC.loader is None:  # pragma: no cover - repo contract
    raise ImportError(f"cannot load canonical revenue DLP from {_DLP_PATH}")
_dlp_module = importlib.util.module_from_spec(_DLP_SPEC)
_DLP_SPEC.loader.exec_module(_dlp_module)
_CANONICAL_DLP = _dlp_module.contains_sensitive_value
del _dlp_module, _DLP_SPEC


class InputError(ValueError):
    pass


def _pairs_no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise InputError(f"duplicate JSON key: {key}")
        out[key] = value
    return out


def parse_json_strict(text: str) -> Any:
    try:
        return json.loads(
            text,
            object_pairs_hook=_pairs_no_duplicates,
            parse_constant=lambda value: (_ for _ in ()).throw(InputError(f"non-finite JSON constant: {value}")),
        )
    except InputError:
        raise
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        raise InputError(f"invalid JSON: {exc}") from exc


def read_json(path: Path) -> Any:
    if path.is_symlink() or not path.is_file():
        raise InputError(f"input must be a regular non-symlink file: {path}")
    return parse_json_strict(path.read_text(encoding="utf-8"))


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def sha256_obj(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _exact_keys(value: dict[str, Any], expected: set[str], where: str) -> None:
    actual = set(value)
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        raise InputError(f"{where} schema mismatch; missing={missing} extra={extra}")


def _bool(value: Any, where: str) -> bool:
    if type(value) is not bool:
        raise InputError(f"{where} must be boolean")
    return value


def _text(value: Any, where: str, *, max_len: int = 500) -> str:
    if not isinstance(value, str):
        raise InputError(f"{where} must be a string")
    stripped = value.strip()
    if not stripped or len(stripped) > max_len or any(ord(ch) < 32 and ch not in "\t\n" for ch in stripped):
        raise InputError(f"{where} must be nonempty safe text <= {max_len} chars")
    # Public close-kit text is descriptive metadata, never a transport for
    # contacts, URLs, credentials, payment data, model bytes, or other secrets.
    # Disallow URLs outright and apply the canonical revenue-pipeline DLP to
    # every admitted free-text value even when caller privacy booleans are false.
    if URL_RE.search(stripped) or _CANONICAL_DLP(stripped):
        raise InputError(f"{where} contains forbidden sensitive/private content")
    return stripped


def _digest(value: Any, where: str, *, optional: bool = False) -> str | None:
    if value is None and optional:
        return None
    if not isinstance(value, str) or SHA_RE.fullmatch(value) is None:
        raise InputError(f"{where} must be a lowercase sha256 hex digest")
    return value


def _metric(value: Any, where: str) -> float:
    if type(value) not in (int, float):
        raise InputError(f"{where} must be numeric")
    numeric = float(value)
    if not math.isfinite(numeric):
        raise InputError(f"{where} must be finite")
    return numeric


def canonical_offer() -> dict[str, Any]:
    return {
        "offer_id": OFFER_ID,
        "terms_sha256": TERMS_SHA256,
        "currency": "USD",
        "fixed_amount": FIXED_AMOUNT_USD,
        "term_calendar_days": TERM_CALENDAR_DAYS,
        "milestones": [
            {"id": "M1_BEFORE_FILE", "amount": M1_AMOUNT_USD, "due": "after NDA + SOW; before customer file exchange"},
            {"id": "M2_AT1_AT6", "amount": M2_AMOUNT_USD, "due": "on AT1-AT6 acceptance evidence"},
        ],
        "acceptance_rule": ACCEPTANCE_RULE,
        "acceptance_tests": list(ACCEPTANCE_IDS),
        "expansion": "same-GGUF $30k / 30d White Box pilot only after paid AT1-AT6 delivery",
    }


def validate_intake(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise InputError("intake must be an object")
    _exact_keys(value, {"schema_version", "kind", "mode", "offer_id", "case_id", "customer_readiness", "privacy", "scope", "evidence_refs"}, "intake")
    if value["schema_version"] != 1 or value["kind"] != "GGUF_ENTERPRISE_INTAKE":
        raise InputError("unsupported intake schema/kind")
    if value["mode"] not in {"SYNTHETIC_DEMO", "CUSTOMER_PRIVATE"}:
        raise InputError("intake.mode must be SYNTHETIC_DEMO or CUSTOMER_PRIVATE")
    if value["offer_id"] != OFFER_ID:
        raise InputError("intake offer_id drift")
    if not isinstance(value["case_id"], str) or CASE_RE.fullmatch(value["case_id"]) is None:
        raise InputError("case_id must match [a-z0-9][a-z0-9._-]{2,63}")

    readiness = value["customer_readiness"]
    if not isinstance(readiness, dict):
        raise InputError("customer_readiness must be object")
    readiness_keys = {"legal_control_confirmed", "harness_ready", "nda_signed", "sow_signed", "m1_received_owner_reported"}
    _exact_keys(readiness, readiness_keys, "customer_readiness")
    for key in readiness_keys:
        _bool(readiness[key], f"customer_readiness.{key}")

    privacy = value["privacy"]
    if not isinstance(privacy, dict):
        raise InputError("privacy must be object")
    privacy_keys = {"public_model_bytes_present", "public_secret_values_present", "public_private_contact_present"}
    _exact_keys(privacy, privacy_keys, "privacy")
    for key in privacy_keys:
        if _bool(privacy[key], f"privacy.{key}"):
            raise InputError(f"privacy violation: {key} must be false")

    scope = value["scope"]
    if not isinstance(scope, dict):
        raise InputError("scope must be object")
    _exact_keys(scope, {"model_label", "objective", "harness_label", "start_window", "data_classification"}, "scope")
    _text(scope["model_label"], "scope.model_label", max_len=120)
    _text(scope["objective"], "scope.objective", max_len=500)
    _text(scope["harness_label"], "scope.harness_label", max_len=120)
    _text(scope["start_window"], "scope.start_window", max_len=120)
    if scope["data_classification"] not in {"PUBLIC_SYNTHETIC", "PRIVATE_CUSTOMER_CONTROLLED"}:
        raise InputError("unsupported scope.data_classification")
    if value["mode"] == "SYNTHETIC_DEMO" and scope["data_classification"] != "PUBLIC_SYNTHETIC":
        raise InputError("synthetic demo must use PUBLIC_SYNTHETIC")
    if value["mode"] == "CUSTOMER_PRIVATE" and scope["data_classification"] != "PRIVATE_CUSTOMER_CONTROLLED":
        raise InputError("customer mode must use PRIVATE_CUSTOMER_CONTROLLED")

    refs = value["evidence_refs"]
    if not isinstance(refs, dict):
        raise InputError("evidence_refs must be object")
    _exact_keys(refs, {"nda_sha256", "sow_sha256", "m1_sha256"}, "evidence_refs")
    normalized_refs = {key: _digest(refs[key], f"evidence_refs.{key}", optional=True) for key in refs}
    binding = {
        "nda_signed": "nda_sha256",
        "sow_signed": "sow_sha256",
        "m1_received_owner_reported": "m1_sha256",
    }
    if value["mode"] == "CUSTOMER_PRIVATE":
        for flag, ref in binding.items():
            if readiness[flag] and normalized_refs[ref] is None:
                raise InputError(f"{flag}=true requires {ref}")
            if not readiness[flag] and normalized_refs[ref] is not None:
                raise InputError(f"{ref} present while {flag}=false")
    else:
        if any(normalized_refs.values()):
            raise InputError("synthetic demo must not carry NDA/SOW/payment evidence refs")
        if any(readiness.values()):
            raise InputError("synthetic demo must not assert customer readiness/payment facts")

    return value


def validate_evidence(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise InputError("evidence must be an object")
    _exact_keys(value, {"schema_version", "kind", "case_id", "artifacts", "harness_runs", "finding_sha256", "delivery_receipt_sha256", "claims"}, "evidence")
    if value["schema_version"] != 1 or value["kind"] != "GGUF_ACCEPTANCE_EVIDENCE":
        raise InputError("unsupported evidence schema/kind")
    if not isinstance(value["case_id"], str) or CASE_RE.fullmatch(value["case_id"]) is None:
        raise InputError("evidence.case_id invalid")

    artifacts = value["artifacts"]
    if not isinstance(artifacts, dict):
        raise InputError("artifacts must be object")
    _exact_keys(artifacts, {"original_sha256", "ablated_sha256", "restored_sha256"}, "artifacts")
    for key in artifacts:
        _digest(artifacts[key], f"artifacts.{key}")

    runs = value["harness_runs"]
    if not isinstance(runs, dict):
        raise InputError("harness_runs must be object")
    _exact_keys(runs, {"baseline", "ablation", "restore"}, "harness_runs")
    for phase in ("baseline", "ablation", "restore"):
        run = runs[phase]
        if not isinstance(run, dict):
            raise InputError(f"harness_runs.{phase} must be object")
        _exact_keys(run, {"log_sha256", "metrics"}, f"harness_runs.{phase}")
        _digest(run["log_sha256"], f"harness_runs.{phase}.log_sha256")
        metrics = run["metrics"]
        if not isinstance(metrics, dict) or not metrics:
            raise InputError(f"harness_runs.{phase}.metrics must be nonempty object")
        if len(metrics) > 32:
            raise InputError("too many metrics")
        for name, metric in metrics.items():
            if not isinstance(name, str) or re.fullmatch(r"[a-z][a-z0-9_.-]{0,63}", name) is None:
                raise InputError(f"invalid metric name: {name!r}")
            _metric(metric, f"harness_runs.{phase}.metrics.{name}")
    if set(runs["baseline"]["metrics"]) != set(runs["ablation"]["metrics"]) or set(runs["baseline"]["metrics"]) != set(runs["restore"]["metrics"]):
        raise InputError("metric key sets must match across baseline/ablation/restore")

    _digest(value["finding_sha256"], "finding_sha256")
    _digest(value["delivery_receipt_sha256"], "delivery_receipt_sha256")
    claims = value["claims"]
    if not isinstance(claims, dict):
        raise InputError("claims must be object")
    _exact_keys(claims, {"public_binary_bytes_present", "metric_lift_required", "buyer_acceptance_claimed", "payment_claimed"}, "claims")
    if _bool(claims["public_binary_bytes_present"], "claims.public_binary_bytes_present"):
        raise InputError("public binary bytes are forbidden")
    if _bool(claims["metric_lift_required"], "claims.metric_lift_required"):
        raise InputError("metric lift cannot be an acceptance requirement")
    if _bool(claims["buyer_acceptance_claimed"], "claims.buyer_acceptance_claimed"):
        raise InputError("this compiler cannot assert buyer/legal acceptance")
    if _bool(claims["payment_claimed"], "claims.payment_claimed"):
        raise InputError("this compiler cannot assert payment")
    return value


def _readiness(intake: dict[str, Any]) -> tuple[str, list[str]]:
    if intake["mode"] == "SYNTHETIC_DEMO":
        return "SYNTHETIC_DEMO_ONLY", []
    r = intake["customer_readiness"]
    holds: list[str] = []
    if not r["legal_control_confirmed"]:
        holds.append("LEGAL_GGUF_CONTROL_NOT_CONFIRMED")
    if not r["harness_ready"]:
        holds.append("CUSTOMER_HARNESS_NOT_READY")
    if not r["nda_signed"]:
        holds.append("NDA_NOT_SIGNED")
    if not r["sow_signed"]:
        holds.append("SOW_NOT_SIGNED")
    if not r["m1_received_owner_reported"]:
        holds.append("M1_NOT_OWNER_REPORTED_RECEIVED")
    return ("READY_FOR_OWNER_PRIVATE_FILE_EXCHANGE_REVIEW" if not holds else "HOLD"), holds


def _acceptance(evidence: dict[str, Any]) -> tuple[dict[str, bool], dict[str, Any]]:
    a = evidence["artifacts"]
    runs = evidence["harness_runs"]
    tests = {
        "AT1": SHA_RE.fullmatch(a["original_sha256"]) is not None,
        "AT2": a["ablated_sha256"] != a["original_sha256"],
        "AT3": a["restored_sha256"] == a["original_sha256"],
        "AT4": all(SHA_RE.fullmatch(runs[p]["log_sha256"]) is not None for p in ("baseline", "ablation", "restore")),
        "AT5": SHA_RE.fullmatch(evidence["finding_sha256"]) is not None,
        "AT6": SHA_RE.fullmatch(evidence["delivery_receipt_sha256"]) is not None,
    }
    metrics: dict[str, dict[str, float]] = {}
    for name in sorted(runs["baseline"]["metrics"]):
        baseline = float(runs["baseline"]["metrics"][name])
        ablation = float(runs["ablation"]["metrics"][name])
        restore = float(runs["restore"]["metrics"][name])
        metrics[name] = {
            "baseline": baseline,
            "ablation": ablation,
            "restore": restore,
            "ablation_delta": ablation - baseline,
            "restore_delta": restore - baseline,
        }
    return tests, {"metrics": metrics, "metric_lift_is_acceptance": False}


def compile_packet(intake_raw: Any, evidence_raw: Any) -> dict[str, Any]:
    intake = validate_intake(intake_raw)
    evidence = validate_evidence(evidence_raw)
    if evidence["case_id"] != intake["case_id"]:
        raise InputError("intake/evidence case_id mismatch")
    readiness_state, readiness_holds = _readiness(intake)
    tests, benchmark = _acceptance(evidence)
    evidence_complete = all(tests.values())
    synthetic = intake["mode"] == "SYNTHETIC_DEMO"
    if synthetic:
        terminal_state = "SYNTHETIC_DEMO_COMPLETE" if evidence_complete else "SYNTHETIC_DEMO_HOLD"
    elif readiness_state != "READY_FOR_OWNER_PRIVATE_FILE_EXCHANGE_REVIEW":
        terminal_state = "HOLD_PRE_FILE_EXCHANGE"
    elif not evidence_complete:
        terminal_state = "HOLD_AT1_AT6_INCOMPLETE"
    else:
        terminal_state = "READY_FOR_OWNER_M2_ACCEPTANCE_REVIEW"

    packet: dict[str, Any] = {
        "schema_version": 1,
        "kind": "GGUF_ENTERPRISE_CLOSE_PACKET",
        "offer": canonical_offer(),
        "case_id": intake["case_id"],
        "mode": intake["mode"],
        "intake": intake,
        "evidence": evidence,
        "readiness": {
            "state": readiness_state,
            "holds": readiness_holds,
            "private_file_exchange_is_publicly_authorized": False,
        },
        "acceptance": {
            "tests": tests,
            "all_at1_at6_evidence_complete": evidence_complete,
            "rule": ACCEPTANCE_RULE,
            "legal_acceptance_claimed": False,
        },
        "benchmark": benchmark,
        "terminal_state": terminal_state,
        "milestones": {
            "M1": "SYNTHETIC_NOT_APPLICABLE" if synthetic else ("OWNER_REPORTED_EVIDENCE_PRESENT" if intake["customer_readiness"]["m1_received_owner_reported"] else "HOLD"),
            "M2": "SYNTHETIC_NOT_APPLICABLE" if synthetic else ("READY_FOR_OWNER_ACCEPTANCE_REVIEW" if terminal_state == "READY_FOR_OWNER_M2_ACCEPTANCE_REVIEW" else "HOLD"),
        },
        "expansion": {
            "white_box_30d_discussion_ready": bool(not synthetic and terminal_state == "READY_FOR_OWNER_M2_ACCEPTANCE_REVIEW"),
            "expansion_accepted": False,
        },
        "authority": {
            "buyer_contact_authorized": False,
            "legal_acceptance_authorized": False,
            "customer_file_transfer_authorized_by_this_packet": False,
            "payment_capture_authorized": False,
            "refund_authorized": False,
            "revenue_recognition_authorized": False,
            "public_model_bytes_allowed": False,
        },
        "truth": {
            "build_is_buyer_interest": False,
            "build_is_payment": False,
            "build_is_revenue": False,
            "synthetic_demo": synthetic,
        },
    }
    packet["packet_receipt_sha256"] = sha256_obj(packet)
    return packet


def verify_packet(packet_raw: Any) -> None:
    if not isinstance(packet_raw, dict):
        raise InputError("packet must be object")
    required = {"schema_version", "kind", "offer", "case_id", "mode", "intake", "evidence", "readiness", "acceptance", "benchmark", "terminal_state", "milestones", "expansion", "authority", "truth", "packet_receipt_sha256"}
    _exact_keys(packet_raw, required, "packet")
    receipt = _digest(packet_raw["packet_receipt_sha256"], "packet_receipt_sha256")
    unsigned = dict(packet_raw)
    unsigned.pop("packet_receipt_sha256")
    if sha256_obj(unsigned) != receipt:
        raise InputError("packet receipt mismatch")
    rebuilt = compile_packet(packet_raw["intake"], packet_raw["evidence"])
    if rebuilt != packet_raw:
        raise InputError("packet semantic verification mismatch")


def render_markdown(packet: dict[str, Any]) -> str:
    verify_packet(packet)
    tests = packet["acceptance"]["tests"]
    test_lines = "\n".join(f"- {key}: {'PASS' if tests[key] else 'HOLD'}" for key in ACCEPTANCE_IDS)
    holds = packet["readiness"]["holds"]
    hold_lines = "\n".join(f"- {item}" for item in holds) if holds else "- none"
    metrics: list[str] = []
    for name, row in packet["benchmark"]["metrics"].items():
        metrics.append(f"- {name}: baseline={row['baseline']:g}, ablation={row['ablation']:g}, restore={row['restore']:g}")
    metric_lines = "\n".join(metrics)
    synthetic_note = "**SYNTHETIC / UNPAID / NOT A CUSTOMER CASE**\n\n" if packet["truth"]["synthetic_demo"] else ""
    return (
        "# GGUF diagnostic evidence packet\n\n"
        + synthetic_note
        + f"Offer: `{OFFER_ID}` · **$12,000 fixed / 10 calendar days**  \n"
        + f"Case: `{packet['case_id']}`  \n"
        + f"State: `{packet['terminal_state']}`  \n"
        + f"Acceptance rule: **{ACCEPTANCE_RULE}**\n\n"
        + "## Pre-file-exchange holds\n" + hold_lines + "\n\n"
        + "## AT1–AT6 evidence\n" + test_lines + "\n\n"
        + "## Reproducible benchmark summary\n" + metric_lines + "\n\n"
        + "Metric lift is observational only and is **not** an acceptance condition. AT3 is byte-exact rollback.\n\n"
        + "## Authority boundary\n"
        + "This packet does not authorize buyer contact, legal acceptance, customer-file transfer, payment capture, refund execution, or revenue recognition. Public model bytes are forbidden.\n\n"
        + f"Receipt: `{packet['packet_receipt_sha256']}`\n"
    )


def _write_exclusive(path: Path, text: str) -> None:
    if path.exists() or path.is_symlink():
        raise InputError(f"exclusive create refused: {path}")
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)
    c = sub.add_parser("compile")
    c.add_argument("intake", type=Path)
    c.add_argument("evidence", type=Path)
    c.add_argument("--json-out", type=Path)
    c.add_argument("--markdown-out", type=Path)
    v = sub.add_parser("verify")
    v.add_argument("packet", type=Path)
    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command == "compile":
            packet = compile_packet(read_json(args.intake), read_json(args.evidence))
            json_text = canonical_json(packet) + "\n"
            md_text = render_markdown(packet)
            if args.json_out:
                _write_exclusive(args.json_out, json_text)
            else:
                sys.stdout.write(json_text)
            if args.markdown_out:
                _write_exclusive(args.markdown_out, md_text)
            return 0
        if args.command == "verify":
            verify_packet(read_json(args.packet))
            print("VERIFIED")
            return 0
        raise InputError("unknown command")
    except InputError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
