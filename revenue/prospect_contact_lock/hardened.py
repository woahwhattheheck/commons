"""Canonical deployment wrapper for prospect contact coordination.

The lower-level state machine lives in :mod:`revenue.prospect_contact_lock.lock`.
This wrapper adds two deployment invariants that must hold before any record read:
(1) the code-pinned authority marker exists on the canonical coordination ref,
and (2) compensation prose cannot self-promote via substring matches such as
``unpaid`` -> ``paid``.
"""
from __future__ import annotations

import base64
from decimal import Decimal, InvalidOperation
import hashlib
import json
import re
import unicodedata
import urllib.parse
from typing import Any, Mapping

from . import lock as core

AUTHORITY_MARKER_PATH = f"{core.AUTHORITY_ROOT}/AUTHORITY.json"
AUTHORITY_MARKER_SCHEMA = "prospect-contact-lock-authority/v1"
EXPECTED_AUTHORITY_MARKER: dict[str, str] = {
    "schema": AUTHORITY_MARKER_SCHEMA,
    "generation": core.AUTHORITY_GENERATION,
    "api_origin": core.CANONICAL_API_ORIGIN,
    "repository": core.CANONICAL_REPOSITORY,
    "branch": core.AUTHORITY_BRANCH,
    "root": core.AUTHORITY_ROOT,
    "authority_digest": core.AUTHORITY_DIGEST,
}

_SIGNAL_PHRASES = (
    "paid",
    "payment",
    "bounty",
    "prize",
    "invoice",
    "fee",
    "commission",
    "award",
    "purchase order",
    "retainer",
)
_NEGATIVE_COMP_RE = re.compile(
    r"(?:\b(?:unpaid|gratis|volunteer|free)\b|"
    r"\bpro\s+bono\b|"
    r"\b(?:no|not|without|zero)\s+(?:pay|paid|payment|fee|compensation|bounty|prize|invoice|commission|retainer)\b|"
    r"\b(?:no|not|without)\s+(?:[$€£]\s*[0-9]|[0-9][0-9,.]*\s*(?:usd|eur|gbp|rtc)\b))",
    re.IGNORECASE,
)
_AMOUNT_RE = re.compile(
    r"(?:[$€£]\s*(?P<lead>[0-9][0-9,]*(?:\.[0-9]{1,2})?)|"
    r"(?P<trail>[0-9][0-9,]*(?:\.[0-9]{1,2})?)\s*(?:usd|eur|gbp|rtc)\b)",
    re.IGNORECASE,
)
_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _authority_marker_url() -> str:
    path = urllib.parse.quote(AUTHORITY_MARKER_PATH, safe="/")
    url = (
        f"{core.CANONICAL_API_ORIGIN}/repos/{core.CANONICAL_REPOSITORY}/contents/"
        f"{path}?ref={urllib.parse.quote(core.AUTHORITY_BRANCH, safe='')}"
    )
    core._assert_canonical_url(url)
    return url


def _strict_compensation_category(text: str) -> str:
    if not isinstance(text, str):
        raise core.ValidationError("compensation_path must be text")
    norm = unicodedata.normalize("NFKC", text.strip()).casefold()
    if not norm or len(norm) > 500 or core.CONTROL_RE.search(norm):
        raise core.ValidationError("compensation_path invalid")
    if _NEGATIVE_COMP_RE.search(norm):
        raise core.ValidationError("compensation_path contains explicit free/negative compensation language")

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
            return core._compensation_category(text)

    raise core.ValidationError(
        "compensation_path must contain a positive amount or an exact non-negated paid/award signal"
    )


class ProspectContactLock(core.ProspectContactLock):
    """Canonical safe surface over the core CAS state machine."""

    def _verify_authority_marker(self) -> None:
        response = self._transport.request(
            "GET", _authority_marker_url(), self._headers, None
        )
        core._server_time(response.headers)
        if response.status != 200:
            raise core.RemoteError(
                "canonical prospect-contact authority marker unavailable; fail closed"
            )
        envelope = core._parse_json_strict(response.body)
        if not isinstance(envelope, Mapping):
            raise core.ValidationError("authority marker envelope invalid")
        blob_sha = envelope.get("sha")
        if not isinstance(blob_sha, str) or not re.fullmatch(r"[0-9a-f]{40}", blob_sha):
            raise core.ValidationError("authority marker blob SHA invalid")
        if envelope.get("encoding") != "base64" or not isinstance(envelope.get("content"), str):
            raise core.ValidationError("authority marker encoding invalid")
        try:
            raw = base64.b64decode(envelope["content"], validate=False)
        except Exception as exc:
            raise core.ValidationError("authority marker base64 invalid") from exc
        marker = core._parse_json_strict(raw)
        if marker != EXPECTED_AUTHORITY_MARKER:
            raise core.ValidationError("canonical authority marker mismatch")

    def _get(self, target: core.Target):
        self._verify_authority_marker()
        return super()._get(target)

    def arm(
        self,
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
        return super().arm(
            kind,
            raw_target,
            agent_id=agent_id,
            operation_id=operation_id,
            message_sha256=message_sha256,
            channel=channel,
            compensation_path=compensation_path,
        )

    def finalize_contacted(
        self,
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
        return super().finalize_contacted(
            kind,
            raw_target,
            agent_id=agent_id,
            operation_id=operation_id,
            message_sha256=message_sha256,
            channel=channel,
            compensation_path=compensation_path,
            provider_receipt=provider_receipt,
        )
