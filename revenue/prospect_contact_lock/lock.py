"""Canonical production surface for the prospect contact lock.

The landed CAS implementation remains source-preserved in :mod:`._core`, but
its ``ProspectContactLock`` class object is hardened *in place* here during
package initialization.  Python imports the package before returning any
``revenue.prospect_contact_lock._core`` submodule import, so direct ``_core``
callers, package callers, CLI callers, and the compatibility ``hardened``
module all receive the same production class identity and invariants.

Ordinary construction accepts only the GitHub token.  Deterministic transport
substitution exists only through the deliberately private ``_for_tests``
capability used by the hostile suite.
"""
from __future__ import annotations

import base64
from decimal import Decimal, InvalidOperation
import re
import unicodedata
import urllib.parse
from typing import Any, Mapping

from . import _core as core

SCHEMA = core.SCHEMA
RECEIPT_SCHEMA = core.RECEIPT_SCHEMA
AUTHORITY_GENERATION = core.AUTHORITY_GENERATION
CANONICAL_API_ORIGIN = core.CANONICAL_API_ORIGIN
CANONICAL_REPOSITORY = core.CANONICAL_REPOSITORY
AUTHORITY_BRANCH = core.AUTHORITY_BRANCH
AUTHORITY_ROOT = core.AUTHORITY_ROOT
AUTHORITY_DOCUMENT = core.AUTHORITY_DOCUMENT
AUTHORITY_DIGEST = core.AUTHORITY_DIGEST
MAX_MESSAGE_BYTES = core.MAX_MESSAGE_BYTES
ZERO_SHA256 = core.ZERO_SHA256
HEX64_RE = core.HEX64_RE
TOKEN_RE = core.TOKEN_RE
PHONE_RE = core.PHONE_RE
CONTROL_RE = core.CONTROL_RE
PAID_SIGNALS = core.PAID_SIGNALS

LockError = core.LockError
ValidationError = core.ValidationError
ConflictError = core.ConflictError
RemoteError = core.RemoteError
Response = core.Response
Target = core.Target
Receipt = core.Receipt

verify_receipt = core.verify_receipt
normalize_target = core.normalize_target
digest_message_bytes = core.digest_message_bytes
digest_message_file = core.digest_message_file
_assert_canonical_url = core._assert_canonical_url
_parse_json_strict = core._parse_json_strict

AUTHORITY_MARKER_PATH = f"{AUTHORITY_ROOT}/AUTHORITY.json"
AUTHORITY_MARKER_SCHEMA = "prospect-contact-lock-authority/v1"
EXPECTED_AUTHORITY_MARKER: dict[str, str] = {
    "schema": AUTHORITY_MARKER_SCHEMA,
    "generation": AUTHORITY_GENERATION,
    "api_origin": CANONICAL_API_ORIGIN,
    "repository": CANONICAL_REPOSITORY,
    "branch": AUTHORITY_BRANCH,
    "root": AUTHORITY_ROOT,
    "authority_digest": AUTHORITY_DIGEST,
}

_SIGNAL_PHRASES = (
    "paid", "payment", "bounty", "prize", "invoice", "fee",
    "commission", "award", "purchase order", "retainer", "contract",
    "subcontract", "bid", "pilot", "discovery",
)
_NEGATIVE_COMP_RE = re.compile(
    r"(?:\b(?:unpaid|gratis|volunteer|free)\b|"
    r"\bpro\s+bono\b|"
    r"\b(?:no|not|without|zero)\s+(?:pay|paid|payment|fee|compensation|bounty|prize|invoice|commission|retainer|award|contract|subcontract|bid|pilot|discovery)\b|"
    r"\b(?:no|not|without)\s+(?:[$€£]\s*[0-9]|[0-9][0-9,.]*\s*(?:usd|eur|gbp|rtc)\b))",
    re.IGNORECASE,
)
_ZERO_AMOUNT_RE = re.compile(
    r"(?:[$€£]\s*0(?:[.,]0+)?\b|\b0(?:[.,]0+)?\s*(?:usd|eur|gbp|rtc)\b)",
    re.IGNORECASE,
)
_AMOUNT_RE = re.compile(
    r"(?:[$€£]\s*(?P<lead>[0-9][0-9,]*(?:\.[0-9]{1,2})?)|"
    r"(?P<trail>[0-9][0-9,]*(?:\.[0-9]{1,2})?)\s*(?:usd|eur|gbp|rtc)\b)",
    re.IGNORECASE,
)
_TOKEN_RE = re.compile(r"[a-z0-9]+")
_NEGATOR_TOKENS = frozenset(
    {"no", "not", "without", "zero", "unpaid", "free", "gratis", "volunteer"}
)


def _authority_marker_url() -> str:
    path = urllib.parse.quote(AUTHORITY_MARKER_PATH, safe="/")
    url = (
        f"{CANONICAL_API_ORIGIN}/repos/{CANONICAL_REPOSITORY}/contents/"
        f"{path}?ref={urllib.parse.quote(AUTHORITY_BRANCH, safe='')}"
    )
    _assert_canonical_url(url)
    return url


def _strict_compensation_category(text: str) -> str:
    """Accept only an explicit positive paid/award path; otherwise fail closed."""
    if not isinstance(text, str):
        raise ValidationError("compensation_path must be text")
    norm = unicodedata.normalize("NFKC", text.strip()).casefold()
    if not norm or len(norm) > 500 or CONTROL_RE.search(norm):
        raise ValidationError("compensation_path invalid")
    if _NEGATIVE_COMP_RE.search(norm) or _ZERO_AMOUNT_RE.search(norm):
        raise ValidationError(
            "compensation_path contains explicit free/negative/zero compensation language"
        )

    for match in _AMOUNT_RE.finditer(norm):
        raw = (match.group("lead") or match.group("trail") or "").replace(",", "")
        try:
            if Decimal(raw) > 0:
                return core._compensation_category(text)
        except InvalidOperation:
            continue

    tokens = _TOKEN_RE.findall(norm)
    for phrase in _SIGNAL_PHRASES:
        words = phrase.split()
        width = len(words)
        for i in range(0, len(tokens) - width + 1):
            if tokens[i : i + width] != words:
                continue
            if any(tok in _NEGATOR_TOKENS for tok in tokens[max(0, i - 3) : i]):
                continue
            return core._compensation_category(text)

    raise ValidationError(
        "compensation_path must contain a positive amount or an exact non-negated paid/award signal"
    )


def _install_core_hardening() -> type:
    """Harden the actual core class object before package import completes.

    Raw predecessor methods are captured only in function closures, never left
    as module attributes.  The resulting class is the object already stored at
    ``_core.ProspectContactLock``; direct `_core` imports therefore cannot select
    a weaker constructor or weaker mutation path.
    """
    cls = core.ProspectContactLock
    raw_init = cls.__init__
    raw_get = cls._get
    raw_arm = cls.arm
    raw_finalize = cls.finalize_contacted

    def safe_init(self: Any, token: str) -> None:
        raw_init(self, token)

    def test_constructor(inner_cls: type, token: str, transport: Any) -> Any:
        if transport is None or not callable(getattr(transport, "request", None)):
            raise TypeError("test transport must provide request()")
        obj = inner_cls.__new__(inner_cls)
        raw_init(obj, token, transport)
        return obj

    def verify_authority_marker(self: Any) -> None:
        response = self._transport.request(
            "GET", _authority_marker_url(), self._headers, None
        )
        core._server_time(response.headers)
        if response.status != 200:
            raise RemoteError(
                "canonical prospect-contact authority marker unavailable; fail closed"
            )
        envelope = core._parse_json_strict(response.body)
        if not isinstance(envelope, Mapping):
            raise ValidationError("authority marker envelope invalid")
        blob_sha = envelope.get("sha")
        if not isinstance(blob_sha, str) or not re.fullmatch(r"[0-9a-f]{40}", blob_sha):
            raise ValidationError("authority marker blob SHA invalid")
        if envelope.get("encoding") != "base64" or not isinstance(envelope.get("content"), str):
            raise ValidationError("authority marker encoding invalid")
        try:
            raw = base64.b64decode(envelope["content"], validate=False)
        except Exception as exc:
            raise ValidationError("authority marker base64 invalid") from exc
        marker = core._parse_json_strict(raw)
        if marker != EXPECTED_AUTHORITY_MARKER:
            raise ValidationError("canonical authority marker mismatch")

    def safe_get(self: Any, target: Target):
        verify_authority_marker(self)
        return raw_get(self, target)

    def safe_arm(
        self: Any,
        kind: str,
        raw_target: str,
        *,
        agent_id: str,
        operation_id: str,
        message_sha256: str,
        channel: str,
        compensation_path: str,
    ) -> dict[str, Any]:
        _strict_compensation_category(compensation_path)
        return raw_arm(
            self,
            kind,
            raw_target,
            agent_id=agent_id,
            operation_id=operation_id,
            message_sha256=message_sha256,
            channel=channel,
            compensation_path=compensation_path,
        )

    def safe_finalize(
        self: Any,
        kind: str,
        raw_target: str,
        *,
        agent_id: str,
        operation_id: str,
        message_sha256: str,
        channel: str,
        compensation_path: str,
        provider_receipt: str,
    ) -> dict[str, Any]:
        _strict_compensation_category(compensation_path)
        return raw_finalize(
            self,
            kind,
            raw_target,
            agent_id=agent_id,
            operation_id=operation_id,
            message_sha256=message_sha256,
            channel=channel,
            compensation_path=compensation_path,
            provider_receipt=provider_receipt,
        )

    cls.__init__ = safe_init
    cls._for_tests = classmethod(test_constructor)
    cls._verify_authority_marker = verify_authority_marker
    cls._get = safe_get
    cls.arm = safe_arm
    cls.finalize_contacted = safe_finalize
    return cls


ProspectContactLock = _install_core_hardening()
del _install_core_hardening

# Mechanical invariant: these are the same class object, not wrapper/core peers.
if core.ProspectContactLock is not ProspectContactLock:  # pragma: no cover
    raise RuntimeError("prospect contact lock hardening identity split")
