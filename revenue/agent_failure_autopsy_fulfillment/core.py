from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

INPUT_SCHEMA = "agent-autopsy-fulfillment-batch/v1"
PACKET_SCHEMA = "agent-autopsy-fulfillment-packet/v1"
REPORT_SCHEMA = "agent-autopsy-fulfillment-report/v1"
PAYMENT_STATES = {"UNVERIFIED", "VERIFIED_PAID", "REFUNDED"}
CASE_STATES = {
    "HOLD_PAYMENT_UNVERIFIED",
    "HOLD_INTAKE_INCOMPLETE",
    "READY_FOR_ANALYSIS",
    "REFUND_REQUIRED",
    "DELIVERED",
}
STATE_PRIORITY = {
    "REFUND_REQUIRED": 0,
    "READY_FOR_ANALYSIS": 1,
    "HOLD_INTAKE_INCOMPLETE": 2,
    "HOLD_PAYMENT_UNVERIFIED": 3,
    "DELIVERED": 4,
}
HEX64 = re.compile(r"^[0-9a-f]{64}$")
OPAQUE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]{0,79}$")
EMAIL = re.compile(r"(?i)(?:^|\s)[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}(?:\s|$)")
URL = re.compile(r"(?i)\b(?:https?://|www\.)")
PHONE = re.compile(r"(?<!\d)(?:\+?1[ .:/-]?)?\(?\d{3}\)?[ .:/-]\d{3}[ .:/-]\d{4}(?!\d)")
SECRET = re.compile(r"(?i)\b(?:api[_ -]?key|access[_ -]?token|auth[_ -]?token|password|passwd|client[_ -]?secret|private[_ -]?key|bearer)\b")
SECRET_PREFIX = re.compile(r"(?i)(?:sk_(?:live|test)_|ghp_|github_pat_|xox[baprs]-|AKIA[0-9A-Z]{12,})")
MAX_CASES = 100
MAX_TEXT = 4000
MAX_EVIDENCE = 10
MAX_EVIDENCE_BYTES = 25_000_000


class FulfillmentError(ValueError):
    pass


def _reject_constant(value: str) -> None:
    raise FulfillmentError(f"non-finite JSON constant refused: {value}")


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise FulfillmentError(f"duplicate JSON key refused: {key}")
        out[key] = value
    return out


def strict_json_loads(text: str) -> Any:
    try:
        return json.loads(text, object_pairs_hook=_pairs, parse_constant=_reject_constant)
    except FulfillmentError:
        raise
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise FulfillmentError(f"invalid JSON: {exc}") from None


def strict_json_file(path: Path) -> Any:
    try:
        return strict_json_loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError) as exc:
        raise FulfillmentError(f"cannot read UTF-8 JSON: {exc}") from None


def canonical_bytes(value: Any) -> bytes:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")
    except (TypeError, ValueError, UnicodeError) as exc:
        raise FulfillmentError(f"cannot canonicalize value: {exc}") from None


def sha256_value(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _exact(obj: Any, keys: set[str], where: str) -> dict[str, Any]:
    if not isinstance(obj, dict):
        raise FulfillmentError(f"{where} must be an object")
    got = set(obj)
    if got != keys:
        missing = sorted(keys - got)
        extra = sorted(got - keys)
        raise FulfillmentError(f"{where} keys mismatch; missing={missing} extra={extra}")
    return obj


def _text(value: Any, where: str, *, required: bool = True, maximum: int = MAX_TEXT) -> str:
    if not isinstance(value, str):
        raise FulfillmentError(f"{where} must be a string")
    if "\ud800" <= value <= "\udfff":
        raise FulfillmentError(f"{where} contains an invalid Unicode scalar")
    cleaned = value.replace("\r\n", "\n").replace("\r", "\n").strip()
    if required and not cleaned:
        raise FulfillmentError(f"{where} must be non-empty")
    if len(cleaned) > maximum:
        raise FulfillmentError(f"{where} exceeds {maximum} characters")
    if any(ord(ch) < 0x20 and ch not in "\n\t" for ch in cleaned):
        raise FulfillmentError(f"{where} contains control characters")
    if cleaned and (EMAIL.search(cleaned) or URL.search(cleaned) or PHONE.search(cleaned) or SECRET.search(cleaned) or SECRET_PREFIX.search(cleaned)):
        raise FulfillmentError(f"{where} violates the sanitized-evidence boundary")
    return cleaned


def _opaque(value: Any, where: str) -> str:
    text = _text(value, where, maximum=80)
    if not OPAQUE.fullmatch(text):
        raise FulfillmentError(f"{where} must be an opaque ASCII reference")
    lower = text.lower()
    if any(token in lower for token in ("token", "secret", "password", "apikey", "api_key", "email", "phone", "account", "routing")):
        raise FulfillmentError(f"{where} looks like sensitive metadata")
    return text


def _digest_or_none(value: Any, where: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not HEX64.fullmatch(value):
        raise FulfillmentError(f"{where} must be null or a lowercase SHA-256 digest")
    return value


def _nonnegative_int(value: Any, where: str, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise FulfillmentError(f"{where} must be an integer")
    if value < 0 or value > maximum:
        raise FulfillmentError(f"{where} out of range")
    return value


def _evidence_items(value: Any, case_ref: str) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise FulfillmentError(f"cases[{case_ref}].intake.evidence_items must be an array")
    if len(value) > MAX_EVIDENCE:
        raise FulfillmentError(f"cases[{case_ref}] has more than {MAX_EVIDENCE} evidence items")
    seen: set[str] = set()
    total = 0
    out: list[dict[str, Any]] = []
    for index, raw in enumerate(value):
        item = _exact(raw, {"kind", "sha256", "bytes"}, f"cases[{case_ref}].intake.evidence_items[{index}]")
        kind = _text(item["kind"], f"evidence[{index}].kind", maximum=40)
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,39}", kind):
            raise FulfillmentError(f"evidence[{index}].kind must be an ASCII label")
        digest = _digest_or_none(item["sha256"], f"evidence[{index}].sha256")
        assert digest is not None
        if digest in seen:
            raise FulfillmentError(f"duplicate evidence digest in case {case_ref}")
        seen.add(digest)
        size = _nonnegative_int(item["bytes"], f"evidence[{index}].bytes", MAX_EVIDENCE_BYTES)
        total += size
        if total > MAX_EVIDENCE_BYTES:
            raise FulfillmentError(f"case {case_ref} exceeds cumulative evidence byte cap")
        out.append({"kind": kind, "sha256": digest, "bytes": size})
    return out


def _normalize_case(raw: Any) -> dict[str, Any]:
    case = _exact(raw, {"case_ref", "payment", "intake", "operator"}, "case")
    case_ref = _opaque(case["case_ref"], "case.case_ref")
    payment = _exact(case["payment"], {"state", "receipt_sha256"}, f"cases[{case_ref}].payment")
    state = payment["state"]
    if not isinstance(state, str) or state not in PAYMENT_STATES:
        raise FulfillmentError(f"cases[{case_ref}].payment.state invalid")
    receipt = _digest_or_none(payment["receipt_sha256"], f"cases[{case_ref}].payment.receipt_sha256")
    if state == "UNVERIFIED" and receipt is not None:
        raise FulfillmentError(f"cases[{case_ref}] UNVERIFIED payment cannot carry a receipt digest")
    if state in {"VERIFIED_PAID", "REFUNDED"} and receipt is None:
        raise FulfillmentError(f"cases[{case_ref}] {state} payment requires a receipt digest")

    intake = _exact(
        case["intake"],
        {"intended_outcome", "observed_failure", "stack", "first_error", "evidence_items", "redaction_confirmed"},
        f"cases[{case_ref}].intake",
    )
    if not isinstance(intake["redaction_confirmed"], bool):
        raise FulfillmentError(f"cases[{case_ref}].intake.redaction_confirmed must be boolean")
    normalized_intake = {
        "intended_outcome": _text(intake["intended_outcome"], f"cases[{case_ref}].intake.intended_outcome", required=False),
        "observed_failure": _text(intake["observed_failure"], f"cases[{case_ref}].intake.observed_failure", required=False),
        "stack": _text(intake["stack"], f"cases[{case_ref}].intake.stack", required=False, maximum=300),
        "first_error": _text(intake["first_error"], f"cases[{case_ref}].intake.first_error", required=False),
        "evidence_items": _evidence_items(intake["evidence_items"], case_ref),
        "redaction_confirmed": intake["redaction_confirmed"],
    }
    operator = _exact(
        case["operator"],
        {"delivery_receipt_sha256", "refund_receipt_sha256", "refund_reason"},
        f"cases[{case_ref}].operator",
    )
    normalized_operator = {
        "delivery_receipt_sha256": _digest_or_none(operator["delivery_receipt_sha256"], f"cases[{case_ref}].operator.delivery_receipt_sha256"),
        "refund_receipt_sha256": _digest_or_none(operator["refund_receipt_sha256"], f"cases[{case_ref}].operator.refund_receipt_sha256"),
        "refund_reason": _text(operator["refund_reason"], f"cases[{case_ref}].operator.refund_reason", required=False, maximum=300),
    }
    if normalized_operator["refund_receipt_sha256"] and not normalized_operator["refund_reason"]:
        raise FulfillmentError(f"cases[{case_ref}] refund receipt requires a reason")
    if normalized_operator["delivery_receipt_sha256"] and normalized_operator["refund_reason"]:
        raise FulfillmentError(f"cases[{case_ref}] cannot be both delivered and refund-required")
    return {
        "case_ref": case_ref,
        "payment": {"state": state, "receipt_sha256": receipt},
        "intake": normalized_intake,
        "operator": normalized_operator,
    }


def _case_state(case: dict[str, Any]) -> tuple[str, list[str], bool]:
    payment = case["payment"]
    intake = case["intake"]
    operator = case["operator"]
    if payment["state"] == "UNVERIFIED":
        return "HOLD_PAYMENT_UNVERIFIED", ["operator must verify the existing checkout receipt before analysis starts"], False
    if payment["state"] == "REFUNDED" or operator["refund_reason"]:
        satisfied = payment["state"] == "REFUNDED" or operator["refund_receipt_sha256"] is not None
        return "REFUND_REQUIRED", [operator["refund_reason"] or "provider receipt records refunded payment"], satisfied
    required_fields = ["intended_outcome", "observed_failure", "stack", "first_error"]
    missing = [name for name in required_fields if not intake[name]]
    if not intake["redaction_confirmed"]:
        missing.append("redaction_confirmed")
    if not intake["evidence_items"]:
        missing.append("evidence_items")
    if missing:
        return "HOLD_INTAKE_INCOMPLETE", ["missing/false: " + ", ".join(missing)], False
    if operator["delivery_receipt_sha256"]:
        return "DELIVERED", ["operator supplied a digest of the completed delivery artifact"], False
    return "READY_FOR_ANALYSIS", ["payment asserted verified and sanitized intake is complete"], False


def compile_batch(source: Any) -> dict[str, Any]:
    root = _exact(source, {"schema", "cases"}, "input")
    if root["schema"] != INPUT_SCHEMA:
        raise FulfillmentError(f"input.schema must be {INPUT_SCHEMA}")
    if not isinstance(root["cases"], list) or not root["cases"] or len(root["cases"]) > MAX_CASES:
        raise FulfillmentError(f"input.cases must contain 1..{MAX_CASES} cases")
    normalized: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in root["cases"]:
        case = _normalize_case(raw)
        if case["case_ref"] in seen:
            raise FulfillmentError(f"duplicate case_ref: {case['case_ref']}")
        seen.add(case["case_ref"])
        normalized.append(case)
    normalized.sort(key=lambda row: row["case_ref"])

    compiled_cases: list[dict[str, Any]] = []
    counts = {state: 0 for state in sorted(CASE_STATES)}
    for case in normalized:
        state, reasons, refund_satisfied = _case_state(case)
        counts[state] += 1
        compiled_cases.append({
            "case_ref": case["case_ref"],
            "case_digest": sha256_value(case),
            "state": state,
            "reasons": reasons,
            "refund_satisfied": refund_satisfied,
            "payment_state": case["payment"]["state"],
            "payment_receipt_sha256": case["payment"]["receipt_sha256"],
            "evidence_count": len(case["intake"]["evidence_items"]),
            "evidence_bytes": sum(item["bytes"] for item in case["intake"]["evidence_items"]),
            "source_case": case,
        })
    queueable_cases = [
        row for row in compiled_cases
        if not (row["state"] == "REFUND_REQUIRED" and row["refund_satisfied"])
    ]
    queue = [
        {"case_ref": row["case_ref"], "state": row["state"], "case_digest": row["case_digest"]}
        for row in sorted(queueable_cases, key=lambda row: (STATE_PRIORITY[row["state"]], row["case_ref"]))
    ]
    semantic = {
        "schema": PACKET_SCHEMA,
        "source_schema": INPUT_SCHEMA,
        "source_sha256": sha256_value({"schema": INPUT_SCHEMA, "cases": normalized}),
        "price_usd": 29,
        "checkout_authority": "EXISTING_CANONICAL_STRIPE_LINK_ONLY",
        "payment_truth": "OPERATOR_ASSERTED_PROVIDER_RECEIPT_NOT_PROVIDER_AUTHENTICATED_BY_THIS_LAYER",
        "cases": compiled_cases,
        "queue": queue,
        "counts": counts,
        "authority": {
            "stripe_write": False,
            "email_send": False,
            "buyer_contact": False,
            "payment_capture": False,
            "refund_execute": False,
            "cash_received_claim": False,
            "revenue_recognition": False,
            "upsell_acceptance": False,
        },
    }
    packet = dict(semantic)
    packet["receipt_sha256"] = sha256_value(semantic)
    return packet


def render_report(packet: dict[str, Any]) -> str:
    if not verify_packet(packet):
        raise FulfillmentError("cannot render an unverified packet")
    lines = [
        "# Agent Failure Autopsy fulfillment queue",
        "",
        f"Schema: `{REPORT_SCHEMA}`  ",
        f"Packet receipt: `{packet['receipt_sha256']}`  ",
        f"Price: **$29 USD per existing canonical checkout**  ",
        "Payment truth: this layer records operator-asserted provider-receipt state; it does not authenticate Stripe or move funds.",
        "",
        "## Queue",
        "",
    ]
    for row in packet["queue"]:
        lines.append(f"- `{row['case_ref']}` — **{row['state']}** — `{row['case_digest']}`")
    lines += ["", "## Case details", ""]
    by_ref = {row["case_ref"]: row for row in packet["cases"]}
    for row in packet["queue"]:
        case = by_ref[row["case_ref"]]
        lines += [
            f"### {case['case_ref']}",
            f"- state: `{case['state']}`",
            f"- payment: `{case['payment_state']}`",
            f"- evidence: {case['evidence_count']} item(s) / {case['evidence_bytes']} byte(s)",
            f"- refund satisfied: `{str(case['refund_satisfied']).lower()}`",
            "- reason(s): " + "; ".join(case["reasons"]),
            "",
        ]
    terminal_refunds = [
        row for row in packet["cases"]
        if row["state"] == "REFUND_REQUIRED" and row["refund_satisfied"]
    ]
    if terminal_refunds:
        lines += ["## Completed refunds", ""]
        for case in terminal_refunds:
            lines += [
                f"### {case['case_ref']}",
                "- terminal: `refund satisfied`",
                f"- payment: `{case['payment_state']}`",
                "- reason(s): " + "; ".join(case["reasons"]),
                "",
            ]
    lines += [
        "## Authority ceiling",
        "",
        "This artifact cannot send email, contact a buyer, capture/refund payment, claim cash received, recognize revenue, or accept an upsell. Those authorities are all false in the verified packet.",
        "",
    ]
    return "\n".join(lines)


def verify_packet(packet: Any) -> bool:
    try:
        root = _exact(
            packet,
            {"schema", "source_schema", "source_sha256", "price_usd", "checkout_authority", "payment_truth", "cases", "queue", "counts", "authority", "receipt_sha256"},
            "packet",
        )
        receipt = root["receipt_sha256"]
        if not isinstance(receipt, str) or not HEX64.fullmatch(receipt):
            return False
        semantic = {key: value for key, value in root.items() if key != "receipt_sha256"}
        if sha256_value(semantic) != receipt:
            return False
        if root["schema"] != PACKET_SCHEMA or root["source_schema"] != INPUT_SCHEMA or root["price_usd"] != 29:
            return False
        if root["checkout_authority"] != "EXISTING_CANONICAL_STRIPE_LINK_ONLY":
            return False
        if root["payment_truth"] != "OPERATOR_ASSERTED_PROVIDER_RECEIPT_NOT_PROVIDER_AUTHENTICATED_BY_THIS_LAYER":
            return False
        expected_authority = {
            "stripe_write": False,
            "email_send": False,
            "buyer_contact": False,
            "payment_capture": False,
            "refund_execute": False,
            "cash_received_claim": False,
            "revenue_recognition": False,
            "upsell_acceptance": False,
        }
        if root["authority"] != expected_authority:
            return False
        source_cases = [row["source_case"] for row in root["cases"]]
        rebuilt = compile_batch({"schema": INPUT_SCHEMA, "cases": source_cases})
        return canonical_bytes(rebuilt) == canonical_bytes(root)
    except (FulfillmentError, KeyError, TypeError, ValueError):
        return False


def _write_exclusive(output_dir: Path, packet: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=False)
    (output_dir / "packet.json").write_bytes(canonical_bytes(packet) + b"\n")
    (output_dir / "report.md").write_text(render_report(packet), encoding="utf-8")


def cli(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="agent-autopsy-fulfillment")
    sub = parser.add_subparsers(dest="cmd", required=True)
    compile_p = sub.add_parser("compile")
    compile_p.add_argument("input")
    compile_p.add_argument("output_dir")
    verify_p = sub.add_parser("verify")
    verify_p.add_argument("packet")
    args = parser.parse_args(argv)
    try:
        if args.cmd == "compile":
            packet = compile_batch(strict_json_file(Path(args.input)))
            _write_exclusive(Path(args.output_dir), packet)
            print(packet["receipt_sha256"])
            return 0
        packet = strict_json_file(Path(args.packet))
        if not verify_packet(packet):
            raise FulfillmentError("packet verification failed")
        print("VERIFIED")
        return 0
    except FulfillmentError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except FileExistsError:
        print("ERROR: output directory already exists", file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"ERROR: filesystem error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(cli())
