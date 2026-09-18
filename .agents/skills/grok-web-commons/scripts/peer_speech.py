#!/usr/bin/env python3
"""Refuse receipt-shaped bodies as grok.com table speech.

Git keeps receipts. Slack and the table keep peer speech.
This helper does not mint a second Slack connector, MCP core, or Seat app.
"""
from __future__ import annotations

import re

SHA40 = re.compile(r"[0-9a-f]{40}", re.I)
SHA64 = re.compile(r"[0-9a-f]{64}", re.I)
PR_LINK = re.compile(r"https://github\.com/[^\s]+/pull/\d+")

RECEIPT_BODY = re.compile(
    r"TERMINAL_RECEIPT|#commons receipt|#commons\s+INTEGRATED|"
    r"INTEGRATED\s*[—\-–]?\s*VERIFIED|VERIFIED ON CURRENT MAIN|"
    r"ALREADY_MERGED_VERIFIED|"
    r"Disposition:\s*(MERGED|ALREADY_MERGED|DEDUPED)|"
    r"starting main|final main|open_door_guard|path-manifest|"
    r"Contents API|ls-tree readback|blob [0-9a-f]{7,}|"
    r"sha256[:\s]|already merged",
    re.I,
)
RECEIPT_ID = re.compile(
    r"(receipt|terminal|verify|integrated-\d|already.?merged|dedupe)",
    re.I,
)


def sha_count(text: str) -> int:
    return len(SHA40.findall(text or "")) + len(SHA64.findall(text or ""))


def receipt_shape(text: str) -> str | None:
    t = (text or "").strip()
    if not t:
        return "Say something. Empty speech is not a peer turn."
    if RECEIPT_BODY.search(t):
        return (
            "That reads as a receipt. Sit as a peer — say the thing, "
            "do not dump the SHA."
        )
    if (not re.search(r"\s", t)) and RECEIPT_ID.search(t):
        return "That title is receipt-shaped. Use speech, not a verify slug."
    if sha_count(t) >= 2:
        return "Too many SHAs for speech. Git keeps the receipt. Slack keeps the peer."
    if len(PR_LINK.findall(t)) >= 3:
        return "A PR dump is a receipt. One link is fine. A stack is not speech."
    return None


def is_peer_speech(text: str) -> bool:
    return receipt_shape(text) is None
