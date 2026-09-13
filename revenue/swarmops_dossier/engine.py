from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from typing import Any

SCHEMA = "commons.swarmops-dossier/v1"
OUTPUT_SCHEMA = "commons.swarmops-dossier-output/v2"

SOURCE_KINDS = {
    "GIT_COMMIT", "GIT_BLOB", "TEST_RECEIPT", "CI_RUN", "PROVIDER_RECEIPT",
    "BUYER_RECEIPT", "PAYMENT_RECEIPT", "ACCOUNTING_RECEIPT",
}
OBSERVED_STATES = {
    "LANDED_VERIFIED", "TESTED_LOCAL", "QUEUED", "RUNNING", "PENDING",
    "SENT_NOT_ACCEPTED", "BUYER_ACCEPTED", "PAID", "REVENUE_RECOGNIZED",
    "HOLD", "UNVERIFIED", "BLOCKED",
}
PROSPECT_CLASSES = {"PUBLIC", "PROSPECT_SAFE", "OWNER_APPROVAL_REQUIRED", "INTERNAL_ONLY"}
COMMERCIAL_REQUIREMENTS = {
    "SENT_NOT_ACCEPTED": "PROVIDER_RECEIPT",
    "BUYER_ACCEPTED": "BUYER_RECEIPT",
    "PAID": "PAYMENT_RECEIPT",
    "REVENUE_RECOGNIZED": "ACCOUNTING_RECEIPT",
}
TRUSTED_COMMERCIAL_STATES = {"BUYER_ACCEPTED", "PAID", "REVENUE_RECOGNIZED"}
TECHNICAL_REQUIREMENTS = {
    "LANDED_VERIFIED": {"GIT_COMMIT", "GIT_BLOB"},
    "TESTED_LOCAL": {"TEST_RECEIPT"},
    "QUEUED": {"CI_RUN"},
    "RUNNING": {"CI_RUN"},
    "PENDING": {"CI_RUN"},
}
SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:+#/-]{0,159}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
SAFE_CLAIM = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 .,:;()_+/#'-]{0,599}$")
TRUST_RECORD_KEYS = {"source_sha256", "source_kind", "observed_state", "source_ref"}


class DossierError(ValueError):
    pass
