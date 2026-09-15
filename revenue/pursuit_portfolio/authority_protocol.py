"""Wire constants for the isolated pursuit-portfolio authority worker."""
from __future__ import annotations

PRODUCTION_HOST_SEAL_SCHEMA = "pursuit-portfolio-allocation/host-seal/v3"
AUTHORITY_RUNTIME = "isolated-worker/v1"
WORKER_REQUEST_SCHEMA = "pursuit-portfolio-allocation/authority-worker-request/v1"
WORKER_RESPONSE_SCHEMA = "pursuit-portfolio-allocation/authority-worker-response/v1"
MAX_WORKER_REQUEST_BYTES = 8_000_000
MAX_WORKER_RESPONSE_BYTES = 12_000_000
