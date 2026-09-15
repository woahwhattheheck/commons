# Cross-Site Clinical Fill Tech-Transfer Evidence Gate

A dependency-free, read-only compiler for a bounded synthetic/non-production clinical-manufacturing handoff pilot. It freezes source-site and receiving-site generations, reconciles packet identity and declared evidence, and produces owner-review evidence with replayable SHA-256 receipts.

It is not a GMP, quality, scientific, regulatory, deviation, process-parameter, or batch-release engine. It never writes to manufacturing systems.

## Authority split

The production/current surface deliberately separates **candidate compilation** from **current authority**.

### Current candidate

`engine.py` exports `compile_transfer(source, receiving, policy)` with **no caller `as_of` parameter**. It samples process UTC and emits schema `vetter-clinical-fill-tech-transfer-current-candidate/v3` with authority mode `CURRENT_EVIDENCE_CANDIDATE`.

A candidate is not a current owner-review authorization. It is a sealed input/decision generation that must cross a fresh verification gate before any current-authority representation is emitted.

### Current owner-review authority

`verify_report_current(candidate)` accepts no clock override. It re-evaluates the candidate snapshots and policy at newly sampled process UTC and requires the entire semantic decision projection—not merely READY/HOLD—to remain identical. Only this verifier emits schema `vetter-clinical-fill-tech-transfer-current-verification/v3` with authority mode `CURRENT_OWNER_REVIEW`.

`render_markdown(candidate)` is also a current-authority operation: it performs the same fresh process-time semantic gate before rendering. A stale/backdated READY candidate therefore cannot be rendered as current owner-review evidence.

This design intentionally does **not** pretend Python same-process reflection is a secrecy boundary. An importer may inspect closure cells and recover the retained deterministic classifier. That recovered explicit-time classifier can produce raw/historical decisions or candidate-shaped data, but it cannot make a stale decision pass fresh current verification/rendering.

### Historical/test replay

Explicit time exists only as a supported API in `historical.py`. It emits schema `vetter-clinical-fill-tech-transfer-historical/v1` with authority mode `HISTORICAL_INTEGRITY_ONLY`. Historical verification returns a distinct historical-verification schema and never emits the current-verification schema or `CURRENT_OWNER_REVIEW` authority.

The retained predecessor source is stored as inert `_engine_v1.txt`, not an importable Python module. The current and historical facades evaluate those exact source bytes into private namespaces and wrap them with their distinct authority contracts.

## Custody and packet model

Each snapshot binds immutable snapshot identity, source/receiving role, schema revision, transfer generation, canonical UTC capture time, literal complete-export declaration, normalized rows SHA-256, and the exact normalized packets needed for offline replay.

Every packet additionally satisfies:

`last_updated_utc <= snapshot.captured_at_utc <= evaluation time`

The canonical packet key is `project_id + molecule_id + batch_id + site_id`. Principal deterministic HOLD families are method/version mismatch, lot/release gap, container/batch configuration mismatch, equipment/calibration gap, operator-qualification gap, microbiology/inspection gap, stale evidence, duplicate packet, missing receiving packet, and generic transfer conflict.

## Frozen 144-packet Chicago/Rankweil acceptance

`synthetic_acceptance.py` is deliberately historical/test-only. Its deterministic envelope contains 144 synthetic/deidentified transfer packets: 120 `TRANSFER_READY` and four packets in each of six named HOLD families. The predecessor corpus proves exact distribution, field commitments, deterministic receipts, order invariance, strict generation/schema/role/digest custody, stale/future-time handling, duplicate JSON-key and non-finite JSON rejection, target-only handling, receipt tamper resistance, and create-exclusive outputs.

The recovery corpus additionally proves current/historical schema separation, absence of caller-clock current API parameters, candidate-vs-authority separation, closure-introspection attack handling, fresh render/verify expiry, row-before-capture chronology, final-symlink rejection, retained-descriptor pathname-swap resistance, and in-read byte-cap enforcement.

```bash
python -m compileall -q .
python -m unittest -v test_engine.py test_recovery.py
python -O -m unittest -v test_engine.py test_recovery.py
python synthetic_acceptance.py
```

## Production CLI

Production candidate compilation and current verification sample process UTC internally:

```bash
python engine.py compile --input request.json --report candidate.json --markdown current.md
python engine.py verify --report candidate.json
```

The request contains exactly `source`, `receiving`, and `policy`. Input is read from one retained `O_NOFOLLOW` regular-file descriptor with a hard cap enforced during consumption. Output paths must not already exist. The compile command will not write Markdown unless the newly compiled candidate passes the fresh current-render gate.

## Privacy and authority ceiling

Public fixtures contain no Vetter, patient, product, customer, or production data. No live Vetter access or credentials are used. Even `CURRENT_OWNER_REVIEW` is evidence/handoff support only and does not authorize process-parameter recommendations, deviation disposition, GMP/quality/scientific/regulatory decisions, batch release, deployment, buyer contact, payment, cash, or revenue recognition. Human site operations and QA retain authority.
