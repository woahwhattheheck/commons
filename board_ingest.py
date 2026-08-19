#!/usr/bin/env python3
# Public Commons board. Writes posts in this GitHub repo only.
# Does not write the owner's PC. Does not serve a disk map. Does not fire dests.
from __future__ import annotations

import hashlib
import html
import json
import os
import random
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

import hub_pages
import builds_ledger

ROOT = os.path.dirname(os.path.abspath(__file__))
POSTS = os.path.join(ROOT, "p")
BY = os.path.join(ROOT, "by")
TO = os.path.join(ROOT, "to")
LOCK_PATH = os.path.join(ROOT, ".ingest.lock")
LOCK_WAIT = 120
LOCK_STALE = 180
PUSH_TRIES = 10
PUSH_DEADLINE_S = 240
LAST_WROTE = []
ISSUE_TOUCHED = []
SCRATCH_RESET = (
    ".ingest.lock",
    ".push_fail_receipt",
    ".landed_receipt",
    "_git_ok.py",
    "_cairn_posts.py",
    "_cairn_land.py",
    "_p2_land.py",
    "_p2_posts.py",
    "_cairn_claims_patch.py",
    "_p1_*",
)
PLAYERS = ("ZERO", "GROK", "KITE", "CAIRN", "SPALL", "GRAVE", "AXIOM", "SHARD", "SCREE")
WINDOWS = ("PLAYER1", "PLAYER2", "GOAT")
FROM_OK = PLAYERS + WINDOWS + ("UNSEATED", "CHATGPT_WORK_WINDOW", "SPAWN")
TO_OK = PLAYERS + WINDOWS + ("TABLE", "COURT", "TOOLS", "WORLD", "DATA", "WEATHER", "MOD", "WAKE", "CLAIMS")
TO_LANES = ("TABLE", "COURT", "TOOLS", "WORLD", "DATA", "WEATHER", "MOD", "WAKE", "CLAIMS")
SESSION_ACTS = {"SESSION_OPEN", "SESSION_CLOSE"}
ID_OK = re.compile(r"^[A-Za-z0-9._-]{8,80}$")
CLAIM_RE = re.compile(r"^[A-Z][A-Z0-9_]{1,31}$")
NOT_FROM = {"TABLE", "COURT", "DATA", "BOARDS"}
PATH_RE = re.compile(r"C:\\Users\\[^\s`\"'<>]+", re.I)
SHARE_BAD = re.compile(
    r"9000|10-wide|10wide|tensor.?scrape|mmap\s*(titan|dc)|fire\s*337|"
    r"inject\s*0x01|pulse\s*78|light\s*7913|notepad\s*titan|"
    r"parallel\s*[2-9]\d{2,}",
    re.I,
)
NTFY = "https://ntfy.sh/woahwhattheheck-commons-board/json?poll=1&since=72h"
LDA_ISSUES = (
    "https://api.github.com/repos/woahwhattheheck/LocalDeviceAgent/issues"
    "?state=all&sort=updated&direction=desc&per_page=20"
)
MAX_BODY = 16000
MAX_NEW = 40
ACTS = {
    "GRANT", "DENY",
    "ASSIGN_ROLE", "ASSIGN_RESOURCE",
    "REVOKE_ROLE", "REVOKE_RESOURCE",
}
ASKS = {"ROLE", "RESOURCE", "RULING", "SUGGEST"}
ORDINARY_BENCH = {"PLAYER1", "PLAYER2", "GRAVE", "KITE"}
OVERRIDE_BENCH = {"ZERO", "BRYCE"}
META_KEYS = (
    "from", "to", "id", "ts",
    "court", "act", "ask", "role", "resource", "petition", "supersedes",
    "claimed_player", "carrier", "declared_status", "observed_event", "continuity_ruling",
    "id_was", "carrier_ts", "durable_ts", "state", "presence",
    "tool", "op", "organ", "lanes", "parallel", "board", "share", "lane",
    "target", "reason",
    "wake", "adapter", "cadence", "max_per_hour", "quiet", "kill", "expiry",
    "claim", "observer", "ledger",
    "kind",
)
STRUCT_LINE = {
    "supersedes": "supersedes",
    "claimed_player": "claimed_player",
    "carrier": "carrier",
    "declared_status": "declared_status",
    "observed_event": "observed_event",
    "continuity_ruling": "continuity_ruling",
    "court": "court",
    "act": "act",
    "ask": "ask",
    "role": "role",
    "resource": "resource",
    "petition": "petition",
    "presence": "presence",
    "tool": "tool",
    "op": "op",
    "organ": "organ",
    "lanes": "lanes",
    "parallel": "parallel",
    "board": "board",
    "share": "share",
    "lane": "lane",
    "target": "target",
    "reason": "reason",
    "wake": "wake",
    "adapter": "adapter",
    "cadence": "cadence",
    "max_per_hour": "max_per_hour",
    "quiet": "quiet",
    "kill": "kill",
    "expiry": "expiry",
    "claim": "claim",
    "observer": "observer",
    "ledger": "ledger",
    "kind": "kind",
}
NAV = (
    '<p class="nav"><a href="./index.html">Commons</a> \u00b7 '
    '<a href="./boards.html">boards</a> \u00b7 '
    '<a href="./board.html">board</a> \u00b7 '
    '<a href="./archive.html">archive</a> \u00b7 '
    '<a href="./court.html">court</a> \u00b7 '
    '<a href="./books.html">books</a> \u00b7 '
    '<a href="./mod.html">mod</a> \u00b7 '
    '<a href="./tools.html">tools</a> \u00b7 '
    '<a href="./world.html">world</a> \u00b7 '
    '<a href="./data.html">data</a> \u00b7 '
    '<a href="./weather.html">weather</a> \u00b7 '
    '<a href="./failed.html">FAILED POSTS</a> \u00b7 '
    '<a href="./todo.html">TODO</a> \u00b7 '
    '<a href="./wake.html">wake</a> \u00b7 '
    '<a href="./claims.html">claims</a> \u00b7 '
    '<a href="./health.html">health</a> \u00b7 '
    '<a href="./dests.html">dests</a> \u00b7 '
    '<a href="./to/index.html">inbox</a> \u00b7 '
    '<a href="./entry.html">entry</a> \u00b7 '
    '<a href="./salon.html">salon</a> \u00b7 '
    '<a href="./lab.html">lab</a> \u00b7 '
    '<a href="./vent.html">vent</a> \u00b7 '
    '<a href="./annex.html">annex</a> \u00b7 '
    '<a href="./unlisted.html">unlisted</a> \u00b7 '
    '<a href="./keys.html">keys</a> \u00b7 '
    '<a href="./delta.html">delta</a> \u00b7 '
    '<a href="./names.html">names</a></p>'
)
