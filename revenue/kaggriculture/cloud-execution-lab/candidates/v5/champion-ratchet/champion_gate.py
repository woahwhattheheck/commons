#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Authenticate and score a full V5 champion panel against exact submitted V3.1."""
from __future__ import annotations
import argparse, hashlib, json, math, os, re, sys, uuid
from pathlib import Path
from typing import Any, Iterable

SCHEMA = "titan-v5-champion-ratchet-receipt/v2"
V31_ARCHIVE_SHA256 = "5db3921f85efbc7596e5a1e7e198fc5f4644ceea43d8e8323c74ded7b4ba4361"
V31_SOURCE_COMMIT = "a90d888f03987ef0b35cfd20ec3519c6144db08a"
V31_SUBMISSION_ID = 56172377
CORPUS_MANIFEST_SHA256 = "510ca5c5438fb65d29755f2009f07bb85bbf3e8963054b88c4abe3ec3737924e"
CORPUS_REL = "cloud-execution-lab/candidates/v5/gauntlet-top30-union/manifest.json"
EXPECTED_TARGETS = 41
EXPECTED_REPLAYS_PER_TARGET = 3
EXPECTED_CALLBACKS = 719
