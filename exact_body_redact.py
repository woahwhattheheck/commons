#!/usr/bin/env python3
"""Redact private local paths and attachment URLs in exact-body republish.

PICK: when exact-body fidelity and the no-private-paths rule collide,
redact-with-marker preserves both. The rest of the body stays exact.
The secret span is replaced, not dropped and not leaked.

This is not an admission gate. Posts still land. Redaction only transforms
matching bytes as they are written to public/git surfaces.

Law: ground/EXACT_BODY_REDACT.md
Leftover: exact-body-republish-private-paths-attachments
"""

from __future__ import annotations

import re

# HEAD did not pin a different exact string for this leftover. Existing
# `[local]` markers are copied-LDA / muhl-pub prefixes, not this PICK.
LOCAL_PATH_REDACTED = "[local path redacted]"

# Home-dir and Windows user profiles. Repo-relative and /usr /var stay.
_WINDOWS_USER = re.compile(
    r"(?<![A-Za-z0-9])[A-Za-z]:[/\\]Users[/\\][^\s`\"'<>]+",
    re.IGNORECASE,
)
_UNIX_HOME = re.compile(
    r"(?<![A-Za-z0-9._-])/(?:home|Users)/[A-Za-z0-9._-]+(?:/[^\s`\"'<>]*)?"
)

# Raw attachment URLs. No named attachment marker exists on HEAD; use the
# same PICK marker and never emit the URL. Do not recover expired ntfy files.
_ATTACHMENT_URL = re.compile(
    r"https?://(?:files\.slack\.com|slack-files\.com|"
    r"(?:www\.)?ntfy\.sh/file|ntfy\.envs\.net/file)/[^\s`\"'<>]+",
    re.IGNORECASE,
)

_SPANS = (_ATTACHMENT_URL, _WINDOWS_USER, _UNIX_HOME)


def redact_private_spans(text: str) -> str:
    """Replace private-path and attachment-URL spans. Leave every other byte."""
    if not text:
        return text
    out = text
    for pattern in _SPANS:
        out = pattern.sub(LOCAL_PATH_REDACTED, out)
    return out


def same_after_redact(left: str, right: str) -> bool:
    """True when two bodies differ only by private spans that redact equally."""
    return redact_private_spans(left or "").rstrip("\n") == redact_private_spans(
        right or ""
    ).rstrip("\n")
