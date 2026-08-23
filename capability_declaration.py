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
SLACK_KINDS = {"SLACK_MESSAGE", "SLACK_THREAD_REPLY"}


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
    """Normalize optional provenance without deciding whether a record lands."""
    out = dict(meta or {})
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
