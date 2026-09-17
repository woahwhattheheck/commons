from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

SCHEMA = "TJL_MERGED_WORK_PAYMENT_CLAIM_V1"
REPORT_SCHEMA = "TJL_MERGED_WORK_PAYMENT_CLAIM_REPORT_V1"
RECEIPT_SCHEMA = "TJL_MERGED_WORK_PAYMENT_CLAIM_RECEIPT_V1"
COMPILER_ID = "merged-work-payment-claim/v1"
MAX_BYTES = 1_048_576
MAX_SAFE_INT = 9_007_199_254_740_991

_STATES = frozenset(
    {
        "READY_FOR_MUSE_PAYMENT_REQUEST",
        "HOLD_ALREADY_PAID",
        "HOLD_COOLDOWN",
        "HOLD_INELIGIBLE",
        "HOLD_STALE",
        "HOLD_NO_COMPENSATION",
        "HOLD_NO_ACCEPTANCE",
        "HOLD_EVIDENCE",
    }
)
_ACCEPTANCE_CLASSES = frozenset(
    {"TARGET_MERGE_EVENT", "SPONSOR_ACCEPTANCE", "BUYER_ACCEPTANCE", "PLATFORM_ACCEPTANCE"}
)
_ELIGIBILITY = frozenset({"ELIGIBLE", "INELIGIBLE", "UNKNOWN"})
_PAYMENT = frozenset({"PAID", "UNPAID", "UNKNOWN"})
_FOLLOWUP_KINDS = frozenset(
    {"PAYMENT_REQUEST_SENT", "PAYMENT_STATUS_RECEIVED", "SPONSOR_REPLIED", "PAYMENT_REJECTED"}
)


class ClaimError(ValueError):
    pass


def _canonical(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8", "strict")
    except (TypeError, ValueError, UnicodeError, RecursionError) as exc:
        raise ClaimError(f"not canonical JSON: {exc}") from exc


def _sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha_value(value: Any) -> str:
    return _sha_bytes(_canonical(value))


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if type(key) is not str:
            raise ClaimError("JSON object key must be a string")
        if key in out:
            raise ClaimError(f"duplicate JSON key: {key}")
        out[key] = value
    return out


def _parse_int(token: str) -> int:
    if len(token.lstrip("-")) > 16:
        raise ClaimError("integer token too large")
    value = int(token, 10)
    if abs(value) > MAX_SAFE_INT:
        raise ClaimError("integer outside safe range")
    return value


def _reject_float(token: str) -> Any:
    raise ClaimError(f"floats forbidden: {token}")


def _reject_constant(token: str) -> Any:
    raise ClaimError(f"non-finite constant forbidden: {token}")


def strict_loads(text: str) -> Any:
    if type(text) is not str:
        raise ClaimError("strict_loads requires text")
    try:
        value = json.loads(
            text,
            object_pairs_hook=_pairs,
            parse_int=_parse_int,
            parse_float=_reject_float,
            parse_constant=_reject_constant,
        )
    except (json.JSONDecodeError, UnicodeError) as exc:
        raise ClaimError(f"invalid JSON: {exc}") from exc
    _reject_surrogates(value, "$")
    return value


def _reject_surrogates(value: Any, where: str) -> None:
    if type(value) is str:
        if any(0xD800 <= ord(ch) <= 0xDFFF for ch in value):
            raise ClaimError(f"{where}: lone surrogate forbidden")
    elif type(value) is list:
        for i, item in enumerate(value):
            _reject_surrogates(item, f"{where}[{i}]")
    elif type(value) is dict:
        for key, item in value.items():
            _reject_surrogates(key, f"{where}.<key>")
            _reject_surrogates(item, f"{where}.{key}")


def _exact(value: Any, keys: set[str] | frozenset[str], where: str) -> dict[str, Any]:
    if type(value) is not dict or any(type(k) is not str for k in value):
        raise ClaimError(f"{where}: exact object required")
    have, want = set(value), set(keys)
    if have != want:
        raise ClaimError(
            f"{where}: exact keys required; missing={sorted(want-have)} extra={sorted(have-want)}"
        )
    return value


def _text(value: Any, where: str, maximum: int = 512) -> str:
    if type(value) is not str or not value or len(value) > maximum:
        raise ClaimError(f"{where}: bounded nonempty string required")
    for ch in value:
        code = ord(ch)
        if code < 32 or code == 127 or 0xD800 <= code <= 0xDFFF:
            raise ClaimError(f"{where}: control/surrogate forbidden")
    return value


def _enum(value: Any, allowed: frozenset[str], where: str) -> str:
    text = _text(value, where, 64)
    if text not in allowed:
        raise ClaimError(f"{where}: unsupported value")
    return text


def _int(value: Any, where: str, minimum: int = 0, maximum: int = MAX_SAFE_INT) -> int:
    if type(value) is not int or not (minimum <= value <= maximum):
        raise ClaimError(f"{where}: bounded integer required")
    return value


def _sha(value: Any, where: str) -> str:
    text = _text(value, where, 64)
    if len(text) != 64 or any(ch not in "0123456789abcdef" for ch in text):
        raise ClaimError(f"{where}: lowercase sha256 required")
    return text


def _git_sha(value: Any, where: str) -> str:
    text = _text(value, where, 40)
    if len(text) != 40 or any(ch not in "0123456789abcdef" for ch in text):
        raise ClaimError(f"{where}: 40-char lowercase git sha required")
    return text


def _repo(value: Any, where: str) -> str:
    text = _text(value, where, 160)
    if text.count("/") != 1:
        raise ClaimError(f"{where}: owner/name repository required")
    owner, name = text.split("/", 1)
    allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_.")
    if not owner or not name or any(ch not in allowed for ch in owner + name):
        raise ClaimError(f"{where}: unsafe repository")
    return text


def _time(value: Any, where: str) -> tuple[str, datetime]:
    if type(value) is not str or len(value) != 20 or not value.endswith("Z"):
        raise ClaimError(f"{where}: whole-second UTC RFC3339 Z required")
    try:
        dt = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError as exc:
        raise ClaimError(f"{where}: invalid timestamp") from exc
    return value, dt


def _nullable_time(value: Any, where: str) -> tuple[str | None, datetime | None]:
    if value is None:
        return None, None
    return _time(value, where)


def _validate_work(raw: Any, evaluation_at: datetime) -> dict[str, Any]:
    row = _exact(
        raw,
        {
            "repository",
            "pr_number",
            "merged_commit_sha",
            "deliverable_sha256",
            "merged_at",
            "source_ref",
            "source_sha256",
        },
        "work",
    )
    merged_at, merged_dt = _time(row["merged_at"], "work.merged_at")
    if merged_dt > evaluation_at:
        raise ClaimError("work.merged_at: future evidence")
    return {
        "repository": _repo(row["repository"], "work.repository"),
        "pr_number": _int(row["pr_number"], "work.pr_number", 1, 2_147_483_647),
        "merged_commit_sha": _git_sha(row["merged_commit_sha"], "work.merged_commit_sha"),
        "deliverable_sha256": _sha(row["deliverable_sha256"], "work.deliverable_sha256"),
        "merged_at": merged_at,
        "source_ref": _text(row["source_ref"], "work.source_ref"),
        "source_sha256": _sha(row["source_sha256"], "work.source_sha256"),
    }


def _validate_compensation(raw: Any, evaluation_at: datetime) -> dict[str, Any] | None:
    if raw is None:
        return None
    row = _exact(
        raw,
        {
            "offer_id",
            "source_ref",
            "source_sha256",
            "advertised_at",
            "expires_at",
            "currency",
            "amount_minor",
        },
        "compensation",
    )
    advertised_at, advertised_dt = _time(row["advertised_at"], "compensation.advertised_at")
    expires_at, expires_dt = _nullable_time(row["expires_at"], "compensation.expires_at")
    if advertised_dt > evaluation_at:
        raise ClaimError("compensation.advertised_at: future evidence")
    if expires_dt is not None and expires_dt < advertised_dt:
        raise ClaimError("compensation.expires_at: predates advertisement")
    currency = _text(row["currency"], "compensation.currency", 3)
    if len(currency) != 3 or currency.upper() != currency or not currency.isalpha() or not currency.isascii():
        raise ClaimError("compensation.currency: uppercase ISO-like code required")
    return {
        "offer_id": _text(row["offer_id"], "compensation.offer_id", 120),
        "source_ref": _text(row["source_ref"], "compensation.source_ref"),
        "source_sha256": _sha(row["source_sha256"], "compensation.source_sha256"),
        "advertised_at": advertised_at,
        "expires_at": expires_at,
        "currency": currency,
        "amount_minor": _int(row["amount_minor"], "compensation.amount_minor", 1),
    }


def _validate_acceptance(raw: Any, work: dict[str, Any], evaluation_at: datetime) -> dict[str, Any] | None:
    if raw is None:
        return None
    row = _exact(
        raw,
        {
            "acceptance_id",
            "source_class",
            "source_ref",
            "source_sha256",
            "accepted_at",
            "repository",
            "pr_number",
            "merged_commit_sha",
        },
        "acceptance",
    )
    accepted_at, accepted_dt = _time(row["accepted_at"], "acceptance.accepted_at")
    if accepted_dt > evaluation_at:
        raise ClaimError("acceptance.accepted_at: future evidence")
    if accepted_dt < _time(work["merged_at"], "work.merged_at")[1] and row["source_class"] == "TARGET_MERGE_EVENT":
        raise ClaimError("acceptance.accepted_at: merge acceptance predates merged work")
    normalized = {
        "acceptance_id": _text(row["acceptance_id"], "acceptance.acceptance_id", 120),
        "source_class": _enum(row["source_class"], _ACCEPTANCE_CLASSES, "acceptance.source_class"),
        "source_ref": _text(row["source_ref"], "acceptance.source_ref"),
        "source_sha256": _sha(row["source_sha256"], "acceptance.source_sha256"),
        "accepted_at": accepted_at,
        "repository": _repo(row["repository"], "acceptance.repository"),
        "pr_number": _int(row["pr_number"], "acceptance.pr_number", 1, 2_147_483_647),
        "merged_commit_sha": _git_sha(row["merged_commit_sha"], "acceptance.merged_commit_sha"),
    }
    for field in ("repository", "pr_number", "merged_commit_sha"):
        if normalized[field] != work[field]:
            raise ClaimError(f"acceptance.{field}: cross-work transplant")
    return normalized


def _validate_eligibility(raw: Any, evaluation_at: datetime) -> dict[str, Any]:
    row = _exact(raw, {"status", "source_ref", "source_sha256", "observed_at"}, "eligibility")
    observed_at, observed_dt = _time(row["observed_at"], "eligibility.observed_at")
    if observed_dt > evaluation_at:
        raise ClaimError("eligibility.observed_at: future evidence")
    return {
        "status": _enum(row["status"], _ELIGIBILITY, "eligibility.status"),
        "source_ref": _text(row["source_ref"], "eligibility.source_ref"),
        "source_sha256": _sha(row["source_sha256"], "eligibility.source_sha256"),
        "observed_at": observed_at,
    }


def _validate_payment(raw: Any, evaluation_at: datetime) -> dict[str, Any]:
    row = _exact(
        raw,
        {"status", "source_ref", "source_sha256", "observed_at", "paid_amount_minor", "payment_ref"},
        "payment_status",
    )
    observed_at, observed_dt = _time(row["observed_at"], "payment_status.observed_at")
    if observed_dt > evaluation_at:
        raise ClaimError("payment_status.observed_at: future evidence")
    status = _enum(row["status"], _PAYMENT, "payment_status.status")
    paid_amount = row["paid_amount_minor"]
    payment_ref = row["payment_ref"]
    if status == "PAID":
        paid_amount = _int(paid_amount, "payment_status.paid_amount_minor", 1)
        payment_ref = _text(payment_ref, "payment_status.payment_ref")
    else:
        if paid_amount is not None or payment_ref is not None:
            raise ClaimError("payment_status: non-PAID rows must not carry paid amount/ref")
    return {
        "status": status,
        "source_ref": _text(row["source_ref"], "payment_status.source_ref"),
        "source_sha256": _sha(row["source_sha256"], "payment_status.source_sha256"),
        "observed_at": observed_at,
        "paid_amount_minor": paid_amount,
        "payment_ref": payment_ref,
    }


def _validate_followups(raw: Any, evaluation_at: datetime) -> list[dict[str, Any]]:
    if type(raw) is not list or len(raw) > 200:
        raise ClaimError("followups: bounded array required")
    rows: list[dict[str, Any]] = []
    ids: set[str] = set()
    economics: set[tuple[str, str, str, str]] = set()
    for i, item in enumerate(raw):
        row = _exact(item, {"id", "kind", "source_ref", "source_sha256", "observed_at"}, f"followups[{i}]")
        event_id = _text(row["id"], f"followups[{i}].id", 120)
        if event_id in ids:
            raise ClaimError("followups: duplicate id")
        ids.add(event_id)
        observed_at, observed_dt = _time(row["observed_at"], f"followups[{i}].observed_at")
        if observed_dt > evaluation_at:
            raise ClaimError("followups: future evidence")
        kind = _enum(row["kind"], _FOLLOWUP_KINDS, f"followups[{i}].kind")
        ref = _text(row["source_ref"], f"followups[{i}].source_ref")
        digest = _sha(row["source_sha256"], f"followups[{i}].source_sha256")
        econ = (kind, observed_at, ref, digest)
        if econ in economics:
            raise ClaimError("followups: duplicate economic event under reminted id")
        economics.add(econ)
        rows.append(
            {"id": event_id, "kind": kind, "source_ref": ref, "source_sha256": digest, "observed_at": observed_at}
        )
    rows.sort(key=lambda row: (row["observed_at"], row["id"]))
    return rows


def _validate_policy(raw: Any) -> dict[str, Any]:
    row = _exact(raw, {"max_status_age_hours", "cooldown_hours"}, "policy")
    return {
        "max_status_age_hours": _int(row["max_status_age_hours"], "policy.max_status_age_hours", 1, 720),
        "cooldown_hours": _int(row["cooldown_hours"], "policy.cooldown_hours", 0, 720),
    }


def _normalize(document: Any, evaluation_at_text: str) -> tuple[dict[str, Any], datetime]:
    evaluation_at_text, evaluation_at = _time(evaluation_at_text, "evaluation_at")
    doc = _exact(
        document,
        {"schema", "claim_id", "work", "compensation", "acceptance", "eligibility", "followups", "payment_status", "policy"},
        "document",
    )
    if doc["schema"] != SCHEMA:
        raise ClaimError("document.schema: unsupported")
    work = _validate_work(doc["work"], evaluation_at)
    normalized = {
        "schema": SCHEMA,
        "claim_id": _text(doc["claim_id"], "claim_id", 160),
        "work": work,
        "compensation": _validate_compensation(doc["compensation"], evaluation_at),
        "acceptance": _validate_acceptance(doc["acceptance"], work, evaluation_at),
        "eligibility": _validate_eligibility(doc["eligibility"], evaluation_at),
        "followups": _validate_followups(doc["followups"], evaluation_at),
        "payment_status": _validate_payment(doc["payment_status"], evaluation_at),
        "policy": _validate_policy(doc["policy"]),
    }
    return normalized, evaluation_at


def _age_hours(evaluation_at: datetime, value: str) -> float:
    dt = _time(value, "age timestamp")[1]
    return (evaluation_at - dt).total_seconds() / 3600


def _choose_state(doc: dict[str, Any], evaluation_at: datetime) -> tuple[str, list[str]]:
    comp = doc["compensation"]
    acceptance = doc["acceptance"]
    eligibility = doc["eligibility"]
    payment = doc["payment_status"]
    policy = doc["policy"]

    if comp is None:
        return "HOLD_NO_COMPENSATION", ["advertised_compensation_missing"]
    if acceptance is None:
        return "HOLD_NO_ACCEPTANCE", ["acceptance_evidence_missing"]
    if eligibility["status"] == "INELIGIBLE":
        return "HOLD_INELIGIBLE", ["retained_eligibility_is_ineligible"]
    if payment["status"] == "PAID":
        return "HOLD_ALREADY_PAID", ["retained_payment_status_is_paid"]

    if comp["expires_at"] is not None:
        expiry = _time(comp["expires_at"], "compensation.expires_at")[1]
        if evaluation_at > expiry:
            return "HOLD_STALE", ["advertised_compensation_expired"]

    max_age = policy["max_status_age_hours"]
    stale: list[str] = []
    if _age_hours(evaluation_at, eligibility["observed_at"]) > max_age:
        stale.append("eligibility_status_stale")
    if _age_hours(evaluation_at, payment["observed_at"]) > max_age:
        stale.append("payment_status_stale")
    if stale:
        return "HOLD_STALE", stale

    blockers: list[str] = []
    if eligibility["status"] != "ELIGIBLE":
        blockers.append("eligibility_not_proven")
    if payment["status"] != "UNPAID":
        blockers.append("unpaid_status_not_proven")
    if any(row["kind"] == "PAYMENT_REJECTED" for row in doc["followups"]):
        blockers.append("prior_payment_rejection_requires_review")
    if blockers:
        return "HOLD_EVIDENCE", blockers

    sent = [row for row in doc["followups"] if row["kind"] == "PAYMENT_REQUEST_SENT"]
    if sent and policy["cooldown_hours"]:
        latest = max(_time(row["observed_at"], "followup.observed_at")[1] for row in sent)
        if evaluation_at - latest < timedelta(hours=policy["cooldown_hours"]):
            return "HOLD_COOLDOWN", ["prior_payment_request_inside_cooldown"]

    return "READY_FOR_MUSE_PAYMENT_REQUEST", []


def _authority() -> dict[str, bool]:
    # Source literal, not caller controlled. READY is diagnostic readiness only.
    return {
        "send_authorized": False,
        "muse_authorized": False,
        "provider_action_authorized": False,
        "payment_authorized": False,
        "payment_proven": False,
        "invoice_created": False,
        "receivable_asserted": False,
        "revenue_recognized": False,
        "contract_or_accounting_conclusion": False,
    }


def _request_payload(doc: dict[str, Any]) -> dict[str, Any]:
    comp = doc["compensation"]
    acceptance = doc["acceptance"]
    assert comp is not None and acceptance is not None
    return {
        "claim_id": doc["claim_id"],
        "repository": doc["work"]["repository"],
        "pr_number": doc["work"]["pr_number"],
        "merged_commit_sha": doc["work"]["merged_commit_sha"],
        "advertised_currency": comp["currency"],
        "advertised_amount_minor": comp["amount_minor"],
        "offer_id": comp["offer_id"],
        "compensation_source_ref": comp["source_ref"],
        "acceptance_source_ref": acceptance["source_ref"],
        "payment_status_source_ref": doc["payment_status"]["source_ref"],
        "recipient": None,
        "route": None,
        "send_state": "NOT_SENT_REQUIRES_FRESH_MUSE_ELECTION",
    }


def _markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Merged-work payment claim packet",
        "",
        f"State: `{report['state']}`",
        f"Claim: `{report['claim_id']}`",
        f"Evaluation: `{report['evaluation_at']}`",
        "",
        "This artifact is an evidence-bound draft only. It has no recipient, route, Muse election, provider-send, payment, receivable, or revenue authority.",
        "",
    ]
    if report["state"] == "READY_FOR_MUSE_PAYMENT_REQUEST":
        req = report["payment_request"]
        assert req is not None
        lines.extend(
            [
                "## Direct payment-request draft",
                "",
                (
                    f"Please process the advertised {req['advertised_currency']} "
                    f"{req['advertised_amount_minor']} minor-unit payment for "
                    f"{req['repository']} PR #{req['pr_number']} at merged commit "
                    f"`{req['merged_commit_sha']}`."
                ),
                "",
                f"Advertised compensation evidence: `{req['compensation_source_ref']}`.",
                f"Acceptance evidence: `{req['acceptance_source_ref']}`.",
                f"Latest retained payment-status evidence: `{req['payment_status_source_ref']}` (UNPAID).",
                "",
                "If payment has already been issued, please provide the provider/payment reference so the retained status can be reconciled instead of sending another request.",
                "",
                "Before any external send: obtain a fresh Muse single-writer election, perform last-inch contact/payment recensus, bind a provider route, and preserve provider send evidence.",
            ]
        )
    else:
        lines.extend(["## Hold reasons", ""])
        for blocker in report["blockers"]:
            lines.append(f"- `{blocker}`")
    lines.extend(["", "## Authority ceiling", ""])
    for key, value in sorted(report["authority"].items()):
        lines.append(f"- `{key}={str(value).lower()}`")
    return "\n".join(lines) + "\n"


def compile_artifacts(document: Any, evaluation_at: str) -> tuple[dict[str, Any], str, dict[str, Any]]:
    doc, evaluation_dt = _normalize(document, evaluation_at)
    state, blockers = _choose_state(doc, evaluation_dt)
    if state not in _STATES:
        raise ClaimError("internal: unknown state")
    payment_request = _request_payload(doc) if state == "READY_FOR_MUSE_PAYMENT_REQUEST" else None
    report = {
        "schema": REPORT_SCHEMA,
        "compiler_id": COMPILER_ID,
        "claim_id": doc["claim_id"],
        "evaluation_at": evaluation_at,
        "state": state,
        "blockers": blockers,
        "input_sha256": _sha_value(doc),
        "work_identity_sha256": _sha_value(doc["work"]),
        "compensation_identity_sha256": _sha_value(doc["compensation"]) if doc["compensation"] is not None else None,
        "acceptance_identity_sha256": _sha_value(doc["acceptance"]) if doc["acceptance"] is not None else None,
        "payment_request": payment_request,
        "authority": _authority(),
    }
    markdown = _markdown(report)
    receipt_seed = {
        "schema": RECEIPT_SCHEMA,
        "compiler_id": COMPILER_ID,
        "claim_id": doc["claim_id"],
        "evaluation_at": evaluation_at,
        "input_sha256": report["input_sha256"],
        "report_sha256": _sha_bytes(_canonical(report)),
        "markdown_sha256": _sha_bytes(markdown.encode("utf-8", "strict")),
    }
    receipt = dict(receipt_seed)
    receipt["receipt_sha256"] = _sha_value(receipt_seed)
    return report, markdown, receipt


def verify_artifacts(
    document: Any,
    evaluation_at: str,
    report: Any,
    markdown: str,
    receipt: Any,
) -> bool:
    try:
        expected_report, expected_markdown, expected_receipt = compile_artifacts(document, evaluation_at)
        if _canonical(report) != _canonical(expected_report):
            return False
        if type(markdown) is not str or markdown.encode("utf-8", "strict") != expected_markdown.encode("utf-8", "strict"):
            return False
        if _canonical(receipt) != _canonical(expected_receipt):
            return False
        return True
    except (ClaimError, UnicodeError, TypeError, ValueError):
        return False


def _read_regular(path: Path) -> bytes:
    try:
        st_before = path.lstat()
    except OSError as exc:
        raise ClaimError(f"read {path}: {exc}") from exc
    if not stat.S_ISREG(st_before.st_mode):
        raise ClaimError(f"read {path}: regular file required")
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(path, flags)
    except OSError as exc:
        raise ClaimError(f"read {path}: {exc}") from exc
    try:
        st_fd = os.fstat(fd)
        if not stat.S_ISREG(st_fd.st_mode) or (st_fd.st_dev, st_fd.st_ino) != (st_before.st_dev, st_before.st_ino):
            raise ClaimError(f"read {path}: file identity changed")
        data = os.read(fd, MAX_BYTES + 1)
        if len(data) > MAX_BYTES:
            raise ClaimError(f"read {path}: file too large")
        if os.read(fd, 1):
            raise ClaimError(f"read {path}: file too large")
        return data
    finally:
        os.close(fd)


def load_json_file(path: Path) -> Any:
    data = _read_regular(path)
    try:
        text = data.decode("utf-8", "strict")
    except UnicodeDecodeError as exc:
        raise ClaimError(f"read {path}: UTF-8 required") from exc
    return strict_loads(text)


def _write_exclusive(path: Path, data: bytes) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(path, flags, 0o600)
    except OSError as exc:
        raise ClaimError(f"write {path}: {exc}") from exc
    try:
        view = memoryview(data)
        while view:
            n = os.write(fd, view)
            if n <= 0:
                raise ClaimError(f"write {path}: short write")
            view = view[n:]
        os.fsync(fd)
    finally:
        os.close(fd)


def publish(directory: Path, report: dict[str, Any], markdown: str, receipt: dict[str, Any]) -> tuple[Path, Path, Path]:
    try:
        st = directory.stat()
    except OSError as exc:
        raise ClaimError(f"output directory: {exc}") from exc
    if not stat.S_ISDIR(st.st_mode) or directory.is_symlink():
        raise ClaimError("output directory must be a real directory")
    paths = (
        directory / "payment-claim.report.json",
        directory / "payment-claim.md",
        directory / "payment-claim.receipt.json",
    )
    written: list[Path] = []
    payloads = (
        _canonical(report) + b"\n",
        markdown.encode("utf-8", "strict"),
        _canonical(receipt) + b"\n",
    )
    try:
        for path, data in zip(paths, payloads):
            _write_exclusive(path, data)
            written.append(path)
    except Exception:
        for path in reversed(written):
            try:
                path.unlink()
            except OSError:
                pass
        raise
    return paths


def _cmd_compile(args: argparse.Namespace) -> int:
    doc = load_json_file(Path(args.input))
    report, markdown, receipt = compile_artifacts(doc, args.evaluation_at)
    publish(Path(args.output_dir), report, markdown, receipt)
    print(receipt["receipt_sha256"])
    return 0


def _cmd_verify(args: argparse.Namespace) -> int:
    doc = load_json_file(Path(args.input))
    report = load_json_file(Path(args.report))
    receipt = load_json_file(Path(args.receipt))
    try:
        markdown = _read_regular(Path(args.markdown)).decode("utf-8", "strict")
    except UnicodeDecodeError as exc:
        raise ClaimError("markdown: UTF-8 required") from exc
    ok = verify_artifacts(doc, args.evaluation_at, report, markdown, receipt)
    print("VERIFIED" if ok else "INVALID")
    return 0 if ok else 2


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Compile/verify merged-work payment-claim packets")
    sub = parser.add_subparsers(dest="command", required=True)
    c = sub.add_parser("compile")
    c.add_argument("input")
    c.add_argument("output_dir")
    c.add_argument("--evaluation-at", required=True)
    c.set_defaults(func=_cmd_compile)
    v = sub.add_parser("verify")
    v.add_argument("input")
    v.add_argument("report")
    v.add_argument("markdown")
    v.add_argument("receipt")
    v.add_argument("--evaluation-at", required=True)
    v.set_defaults(func=_cmd_verify)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        return int(args.func(args))
    except ClaimError as exc:
        print(f"ERROR: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
