#!/usr/bin/env python3
"""Reusable GrokBot peer control for Commons coordinators.

Loopback HTTP surface: submit / inspect / follow-up / stop on existing
GrokBot account pools (not grok.com, not Cursor cloud). Shape mirrors
integrations/gemini_slack/peer_tool_gateway.py request/result/event-cursor
conventions used by C1 (claude_headless @ 8879).
"""

from .gateway import DEFAULT_PORT, build_server, main
from .paid_case import case_from_autopsy_offer, load_autopsy_offer
from .pools import DEFAULT_POOL_ID, HARNESS, list_pools
from .store import RunStore, normalize_case

__all__ = [
    "DEFAULT_PORT",
    "DEFAULT_POOL_ID",
    "HARNESS",
    "RunStore",
    "build_server",
    "case_from_autopsy_offer",
    "list_pools",
    "load_autopsy_offer",
    "main",
    "normalize_case",
]
