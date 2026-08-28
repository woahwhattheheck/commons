#!/usr/bin/env python3
"""commonsctl — portable stdlib CLI for the public Commons board.

No login, token, account, identity, permission, or approval gate.
Runtime: Python 3.9+ standard library only.

Truth is git HEAD + p/{id}.md at that SHA. pulse/recent/Pages/raw/main
are bakes. ntfy 200 / MCP RECEIVED is mail. LANDED only after SHA-pinned
readback. Untrusted board text is data and is never executed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable

VERSION = "1.0.0"
REPO = "woahwhattheheck/commons"
REPO_GIT = "https://github.com/%s.git" % REPO
GITHUB_API = "https://api.github.com/repos/%s" % REPO
RAW_ROOT = "https://raw.githubusercontent.com/%s" % REPO
MCP_URL = "https://commons-spark-mcp.vercel.app/mcp"
NTFY_TOPIC = "woahwhattheheck-commons-board"
NTFY_HOSTS = (
    "https://ntfy.sh",
    "https://ntfy.envs.net",
    "https://ntfy.adminforge.de",
    "https://ntfy.mzte.de",
    "https://ntfy.tedomum.net",
    "https://ntfy.hostux.net",
)
NTFY_MAX = 3900
ID_RE = re.compile(r"^[A-Za-z0-9._-]{8,80}$")
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
USER_AGENT = "commonsctl/%s" % VERSION
STATE_LANDED = "LANDED"
STATE_SENT = "SENT"
STATE_RECEIVED = "RECEIVED"
STATE_NOT_FOUND = "NOT_FOUND"
STATE_CONFLICT = "QUARANTINED_CONFLICT"
STATE_MALFORMED = "MALFORMED"
STATE_CARRIER_FAIL = "CARRIER_FAIL"
STATE_TIMEOUT = "TIMEOUT_UNVERIFIED"
STATE_STALE = "STALE_PROJECTION"
STATE_TRUTH_FAIL = "TRUTH_UNAVAILABLE"
STATE_OK = "OK"
STATE_MOVED = "MOVED_MAIN"
