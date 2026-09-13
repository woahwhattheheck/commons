# Life Couriers custody evidence core

Provider-free synthetic acceptance core for one proposed cross-system custody / temperature evidence boundary.

## What it proves

- exact shipment, leg, custody-party, source-system and source-record lineage;
- deterministic multi-leg route continuity;
- required temperature-evidence counts and configured range checks;
- exact event-ID idempotence (retries collapse without a second logical effect);
- fail-closed conflicting event IDs and ambiguous source lineage;
- explicit open exception and timeout-after-commit `UNKNOWN_EFFECT` states;
- reconciliation evidence for unknown effects before a shipment can become `READY_FOR_HANDOFF`;
- order-invariant canonical manifests and offline SHA-256 integrity receipts.

`READY_FOR_HANDOFF` means only that the supplied synthetic evidence satisfies this core's declared completeness/integrity rules. It is **not** a clinical, product-release, regulatory, customs, quality, delivery, or carrier authorization.

## Run

```bash
python -m unittest -v test_rail.py
python -O -m unittest -v test_rail.py
python acceptance.py --require-pass
python -O acceptance.py --require-pass
```

The deterministic acceptance fixture contains 120 synthetic shipments: 100 complete and 20 deliberate holds spanning missing temperature evidence, temperature excursion, unresolved exception, unresolved external-effect uncertainty, and ambiguous source lineage. Input events are shuffled before ingest to exercise out-of-order delivery, and every shipment includes an exact retry.

## Integration boundary

This package has no network client and no credentials. An integration may translate buyer-owned event records into the strict event schema, but external side effects remain outside this core. Receipt hashes provide tamper-evident integrity only; no digital signature is claimed or fabricated.
