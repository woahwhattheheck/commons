#!/usr/bin/env python3
"""EvidenceAAR: deterministic, evidence-bound offline Digital Scribe prototype.

This module deliberately has no network/provider code. It consumes a bounded
strict-JSON event packet, corrects per-source clock offsets, segments a
timeline, builds evidence-linked AAR claims, records contradictions/coverage,
and emits deterministic JSON/Markdown/HTML plus a content-addressed receipt.

Authority ceiling: synthetic/offline evaluation only. Nothing here registers,
submits, contacts a sponsor, processes restricted exercise data, or claims an
award/payment.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

ENGINE_VERSION = "evidenceaar/1.0"
INPUT_SCHEMA = "evidenceaar-input/v1"
BUNDLE_SCHEMA = "evidenceaar-bundle/v1"
RECEIPT_SCHEMA = "evidenceaar-receipt/v1"

MAX_INPUT_BYTES = 2_000_000
MAX_SOURCES = 128
MAX_EVENTS = 10_000
MAX_TEXT_BYTES = 16_384
MAX_ID_LEN = 128
MAX_SUBJECT_LEN = 256
MAX_ASSERTION_LEN = 1024
MAX_TAGS = 32
MAX_GAP_MS = 86_400_000
MAX_OFFSET_MS = 86_400_000
MAX_NESTING = 64

MODALITIES = {"TEXT", "AUDIO", "VIDEO", "SENSOR", "CHAT", "IMAGE", "OTHER"}
CLAIM_KINDS = {"OBSERVATION", "DECISION", "ACTION", "OUTCOME"}
_SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$")
_MD_META = re.compile(r"([\\`*_{}\[\]()<>#+\-.!|])")


class ContractError(ValueError):
    """Input/bundle violates the deterministic contract."""


def _fail(message: str) -> None:
    raise ContractError(message)


def _exact_int(value: Any, field: str, lo: int, hi: int) -> int:
    if type(value) is not int:
        _fail(f"{field}: expected integer")
    if value < lo or value > hi:
        _fail(f"{field}: out of range")
    return value
