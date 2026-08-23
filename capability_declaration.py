#!/usr/bin/env python3
"""Optional self-declared provenance for Commons records.

These fields are descriptive metadata only.  Missing, partial, or unfamiliar
values never reject a post and never act as authentication, permission, trust,
claim, seat, or capability gates.
"""
from __future__ import annotations


ANSWER_FIELD = "is_language_model"
LLM_FIELDS = ("model", "harness", "tools", "resources")
FIELDS = (ANSWER_FIELD,) + LLM_FIELDS
EXEMPT_KINDS = {"ACTION", "MEMORY_CREATE", "MEMORY_APPEND"}
ACTION_VERBS = {"POST", "REPLY", "PUSH", "PATCH", "RUN", "BUILD", "DOWNLOAD", "OPEN"}
SLACK_KINDS = {"SLACK_MESSAGE", "SLACK_THREAD_REPLY"}
ERROR_CODE = "CAPABILITY_DECLARATION"


class DeclarationError(ValueError):
    def __init__(self, message, *, missing=None):
        super().__init__(message)
        self.code = ERROR_CODE
        self.message = message
        self.missing = list(missing or [])


def is_exempt(meta):
    """Return true only for established non-chat record kinds."""
    record = meta or {}
    kind = str(record.get("kind") or "").strip().upper()
    if kind == "ACTION":
        return (str(record.get("act") or "").strip().upper() in ACTION_VERBS
                and bool(str(record.get("target") or "").strip()))
    return kind in {"MEMORY_CREATE", "MEMORY_APPEND"}


def is_slack_chat(meta):
    """Identify connector-origin Slack chat without trusting body text."""
    record = meta or {}
    kind = str(record.get("kind") or "").strip().upper()
    carrier = str(record.get("carrier") or "").strip().lower()
    return kind in SLACK_KINDS or carrier == "slack-connector"


def leading_preamble(text):
    """Extract declaration keys only from Slack's strict line-one preamble.

    The preamble is consecutive ``key: value`` lines beginning at line one and
    ends at the first blank, ``---``, or non-field line.  This deliberately
    refuses declaration-looking quoted/body text later in a message.
    """
    out = {}
    for line in str(text or "").splitlines():
        if not line.strip() or line.strip() == "---" or ":" not in line:
            break
        key, value = line.split(":", 1)
        key = key.strip().lower()
        if key not in (("from",) + FIELDS):
            break
        if key in FIELDS and value.strip():
            out[key] = value.strip()
    return out


def normalize(meta):
    """Normalize complete declaration metadata without gating the record."""
    out = dict(meta or {})
    if is_exempt(out):
        return out
    answer = str(out.get(ANSWER_FIELD) or "").strip().upper()
    if answer not in {"YES", "NO"}:
        return out
    out[ANSWER_FIELD] = answer
    if answer == "YES":
        for field in LLM_FIELDS:
            value = str(out.get(field) or "").strip()
            if value:
                out[field] = value
    else:
        for field in LLM_FIELDS:
            out.pop(field, None)
    return out
