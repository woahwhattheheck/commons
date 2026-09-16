#!/usr/bin/env python3
"""Deterministic, evidence-bound enterprise security questionnaire compiler."""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import stat
from pathlib import Path, PurePosixPath
import re
import sys
from typing import Any

SCHEMA = "security-questionnaire-evidence-v1"
REPORT_SCHEMA = "security-questionnaire-report-v1"
MAX_EVIDENCE = 300
MAX_QUESTIONS = 150
MAX_ARTIFACT_BYTES = 2_000_000
