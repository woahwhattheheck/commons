# Cross-Site Clinical Fill Tech-Transfer Evidence Gate

A dependency-free, read-only compiler for a bounded synthetic/non-production clinical-manufacturing handoff pilot. It freezes source-site and receiving-site generations, reconciles packet identity and declared evidence, and emits evidence for owner review with replayable SHA-256 receipts.

It is not a GMP, quality, scientific, regulatory, deviation, process-parameter, or batch-release engine. It never writes to manufacturing systems.

## Authority split

The production/current surface is intentionally different from deterministic historical replay.

### Current production authority

`engine.py` exports `compile_transfer(source, receiving, policy)` with **no caller `as_of` parameter**. It samples process UTC inside a closure whose constructor and retained explicit-time core are removed from the module namespace after import. It emits only:

- schema `vetter-clinical-fill-tech-transfer-current/v2`;
- authority mode `CURRENT_OWNER_REVIEW`;
- process-owned `evaluated_at_utc`;
- the bound decision payload;
- a current-envelope receipt.

`verify_report_current(report)` also accepts no time override. It first proves the envelope and retained decision integrity, then recompiles at newly sampled process UTC and requires the full decision projection—not merely the top-level READY/HOLD label—to remain identical.

### Historical/test replay

Explicit time exists only in `historical.py`. It emits schema `vetter-clinical-fill-tech-transfer-historical/v1` with authority mode `HISTORICAL_INTEGRITY_ONLY`. Historical verification returns a distinct historical-verification schema and never emits the current report or current-verification schema.

The retained predecessor source is stored as inert `_engine_v1.txt`, not an importable Python module. Current and historical facades evaluate those exact source bytes into private namespaces and retain only their own wrapped capabilities.

## Custody and packet model

Each snapshot binds immutable snapshot identity, source/receiving role, schema revision, transfer generation, canonical UTC capture time, literal complete-export declaration, normalized rows SHA-256, and the exact normalized packets needed for offline replay.

Every packet now additionally satisfies the chronology invariant:

`last_updated_utc <= snapshot.captured_at_utc <= evaluation time`

The canonical packet key is `project_id + molecule_id + batch_id + site_id`. Principal deterministic HOLD families are method/version mismatch, lot/release gap, container/batch configuration mismatch, equipment/calibration gap, operator-qualification gap, microbiology/inspection gap, stale evidence, duplicate packet, missing receiving packet, and generic transfer conflict.

## Frozen 144-packet Chicago/Rankweil acceptance

`synthetic_acceptance.py` is deliberately historical/test-only. Its deterministic envelope contains 144 synthetic/deidentified transfer packets: 120 `TRANSFER_READY` and four packets in each of six named HOLD families. The predecessor corpus still proves exact distribution, field commitments, deterministic receipts, order invariance, strict generation/schema/role/digest custody, stale/future-time handling, duplicate JSON-key and non-finite JSON rejection, target-only handling, receipt tamper resistance, and create-exclusive outputs.

The recovery corpus additionally proves current/historical schema separation, absence of a supported caller-clock current API, row-before-capture chronology, process-time current expiry, final-symlink rejection, retained-descriptor pathname-swap resistance, and in-read byte-cap enforcement.

```bash
python -m compileall -q .
python -m unittest -v test_engine.py test_recovery.py
python -O -m unittest -v test_engine.py test_recovery.py
python synthetic_acceptance.py
```

## Production CLI

Production compilation and verification sample process UTC internally:

```bash
python engine.py compile --input request.json --report report.json --markdown report.md
python engine.py verify --report report.json --markdown report.md
```

The request contains exactly `source`, `receiving`, and `policy`. Input is read from one retained `O_NOFOLLOW` regular-file descriptor with a hard cap enforced during consumption. Output paths must not already exist.

## Privacy and authority ceiling

Public fixtures contain no Vetter, patient, product, customer, or production data. No live Vetter access or credentials are used. A current `TRANSFER_READY_FOR_OWNER_REVIEW` decision is evidence/handoff support only and does not authorize process-parameter recommendations, deviation disposition, GMP/quality/scientific/regulatory decisions, batch release, deployment, buyer contact, payment, cash, or revenue recognition. Human site operations and QA retain authority.
