#!/usr/bin/env python3
"""Deterministic fakes for the Grok Slack connector."""

from __future__ import annotations

import hashlib
import importlib.util
import io
import json
import os
import sqlite3
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path
from typing import Any


MODULE_PATH = Path(__file__).parent / "integrations" / "grok_slack" / "bridge.py"
SPEC = importlib.util.spec_from_file_location("grok_slack_bridge", MODULE_PATH)
bridge = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = bridge
SPEC.loader.exec_module(bridge)

from integrations.grokcom_revenue.orchestrator import orchestrate


SECRET_MARKER = "slack-secret-token-BOT-test-marker"
RESULT_MARKER = "grok-result-private-bytes-☃"
MAIN_SHA = "a" * 40
CAPACITY = {
    "state": "AVAILABLE",
    "evidence": "authenticated grok.com usage indicator shows capacity",
    "observed_at": "2026-08-30T05:15:00Z",
}


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
