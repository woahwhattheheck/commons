from __future__ import annotations

import copy
import hashlib
import json
import tempfile
import threading
import unittest
import urllib.parse
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import revenue.initial_outreach_slot.slot as initial_slot_impl
from revenue.organization_outbound_chain import chain
from revenue.organization_outbound_chain.provider_boundary import (
    GmailBoundary,
    ProviderBoundaryError,
    invoke_provider_boundary,
    provider_name,
    registered_boundary_types,
)
from revenue.organization_outbound_chain.registry import (
    ADAPTERS,
    find_bypasses,
    registered_host_mutation_identities,
    registered_provider_names,
    validate_registry,
)
from revenue.organization_outbound_lease import FileLeaseStore, acquire_lease


ORG = "1" * 64
CAP = bytes.fromhex("ab" * 32)
CAP_B = bytes.fromhex("cd" * 32)
PRESSURE = "2" * 64
AUTH = "3" * 64
LEDGER = "4" * 64
LOWER_ANCHOR = "5" * 40
ACTIVE_GENERATION = "6" * 40
CANONICAL_KEY = "opportunity-key"
