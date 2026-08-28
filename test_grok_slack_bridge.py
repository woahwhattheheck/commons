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
from pathlib import Path
from typing import Any
