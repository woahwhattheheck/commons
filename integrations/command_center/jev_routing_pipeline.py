"""Compose installed-connector metadata, the Jev ledger, and action-loop plans.

The module is transport-free. Callers supply the raw-private-text-free connector metadata
accepted by ``jev_connector_projection`` plus a typed result from the existing Jev client.
Only a fresh, complete selected source may produce an action plan. Provider execution and
readback remain connector/controller responsibilities.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
import re
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any

from integrations.command_center import jev_action_loop as action_loop
from integrations.command_center import jev_connector_projection as connector_projection
from integrations.command_center import jev_event_ledger as event_ledger

BUNDLE_SCHEMA = "commons.jev_routing_pipeline.bundle/v1"
MAX_BYTES = 8 * 1024 * 1024
MAX_ROUTES = 256
TOKEN_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/#@+-]{0,255}\\Z")
