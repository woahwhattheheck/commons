# Retained Hamilton evidence

Positive owner or partner evidence is closed-world. A JSON leaf in this directory is admissible only when `gate.py`'s source-owned `SOURCE_OWNED_RETAINED_EVIDENCE` map pins that exact leaf name to its exact SHA-256. The production map is intentionally empty in this carrier: no owner qualification, capability, capacity, pricing, insurance/security satisfaction, past-performance record, or prime-partner due diligence is currently claimed.

The gate additionally requires a one-link regular file, one no-follow file-descriptor generation, exact raw-byte digest, opportunity/source/requirement/class binding, and substantive typed facts/refs. Creating a new runtime file here and self-authoring matching ledger/manifest rows is not sufficient; adding future positive evidence requires a reviewed source mutation that adds the artifact and pins its digest in code.

Unit tests temporarily substitute a private source-owned index only to exercise the future reviewed-evidence path and restore the production empty mapping after each test. That test seam is not exposed through the CLI or runtime JSON inputs.
