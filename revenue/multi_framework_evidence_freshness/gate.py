from __future__ import annotations

import hashlib
import json
import os
import re
import stat
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA = "commons.multi-framework-evidence-freshness/v1"
PACKET_SCHEMA = "commons.multi-framework-evidence-freshness-packet/v1"
STATES = ("REUSABLE", "STALE", "SCOPE_MISMATCH", "MISSING_OWNER", "INCOMPLETE")
FRAMEWORKS = ("SOC2", "ISO27001", "HITRUST", "PCI-DSS")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_REF_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/+-]{0,159}$")
_CONTROL_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/+-]{0,79}$")
_MAX_ROWS = 10_000
_MAX_CONTROLS = 2_000


class GateError(ValueError):
    pass


def _pairs_hook(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise GateError(f"duplicate_json_key:{key}")
        out[key] = value
    return out
