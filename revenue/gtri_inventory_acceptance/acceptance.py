"""Deterministic evidence for bounded federal-asset migration acceptance workshares.

This module checks continuity against a caller-frozen normalized contract. It does not
certify FAR/DFARS/NIST/508 or any other legal, security, accounting, audit, or buyer
compliance requirement.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "gtri-inventory-acceptance/v1"


class AcceptanceError(ValueError):
    """Raised when evidence cannot safely support an acceptance decision."""
