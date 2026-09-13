# Cross-Site Clinical Fill Tech-Transfer Evidence Gate

A dependency-free, read-only compiler for a bounded synthetic/non-production clinical-manufacturing handoff pilot. It freezes source-site and receiving-site generations, reconciles packet identity and declared evidence, and emits deterministic `TRANSFER_READY` / `HOLD` evidence with replayable SHA-256 receipts.

It is not a GMP, quality, scientific, regulatory, deviation, process-parameter, or batch-release engine. It never writes to manufacturing systems.

## Custody and packet model

Each snapshot binds immutable snapshot identity, source/receiving role, schema revision, transfer generation, canonical UTC capture time, literal complete-export declaration, normalized rows SHA-256, and the exact normalized packets needed for offline replay.

The canonical packet key is `project_id + molecule_id + batch_id + site_id`. Each packet additionally binds the receiving site, process/method versions, container configuration, equipment and calibration evidence, operator qualification, QC inspection, microbiology evidence, storage condition, transfer evidence, release evidence, and evidence update time.

Principal deterministic HOLD families:

- `METHOD_OR_VERSION_MISMATCH`
- `LOT_OR_RELEASE_GAP`
- `CONTAINER_OR_BATCH_CONFIG_MISMATCH`
- `EQUIPMENT_OR_CALIBRATION_GAP`
- `OPERATOR_QUALIFICATION_GAP`
- `MICROBIOLOGY_OR_INSPECTION_GAP`

Additional fail-closed states cover duplicate keys, missing receiving packets, receiving-only packets, stale evidence, and generic transfer conflicts. Duplicate and missing evidence take precedence over semantic readiness. `TRANSFER_READY_FOR_OWNER_REVIEW` is possible only when every source packet is one-to-one and ready, no receiving-only keys exist, and snapshot/generation/schema custody is valid.

## Frozen 144-packet Chicago/Rankweil acceptance

`synthetic_acceptance.py` creates exactly 144 synthetic/deidentified transfer packets:

| Classification | Count |
| --- | ---: |
| TRANSFER_READY | 120 |
| METHOD_OR_VERSION_MISMATCH | 4 |
| LOT_OR_RELEASE_GAP | 4 |
| CONTAINER_OR_BATCH_CONFIG_MISMATCH | 4 |
| EQUIPMENT_OR_CALIBRATION_GAP | 4 |
| OPERATOR_QUALIFICATION_GAP | 4 |
| MICROBIOLOGY_OR_INSPECTION_GAP | 4 |

Every seeded HOLD carries exact field paths plus source/receiving value commitments. The suite also proves three-run receipt determinism, order invariance, replay verification, strict generation/schema/role/digest custody, stale/future-time handling, duplicate JSON-key and non-finite JSON rejection, type strictness, target-only handling, report resealing resistance, and create-exclusive/symlink-safe outputs.

```bash
python -m unittest -v test_engine.py
python -O -m unittest -v test_engine.py
python synthetic_acceptance.py
python -m compileall -q .
```

## CLI

Production compilation samples current UTC internally:

```bash
python engine.py compile --input request.json --report report.json --markdown report.md
python engine.py verify --report report.json --markdown report.md
```

The request contains exactly `source`, `receiving`, and `policy`. Output paths must not already exist; final-component symlinks are refused.

## Privacy and authority ceiling

Public fixtures contain no Vetter, patient, product, customer, or production data. No live Vetter access or credentials are used. `TRANSFER_READY_FOR_OWNER_REVIEW` is evidence/handoff support only and does not authorize process-parameter recommendations, deviation disposition, GMP/quality/scientific/regulatory decisions, batch release, deployment, buyer contact, payment, cash, or revenue recognition. Human site operations and QA retain authority.
