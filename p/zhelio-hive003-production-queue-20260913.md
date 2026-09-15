# HIVE003 production queue — Z-Heliocline

Operation: `HIVE003-PRODUCTION-QUEUE-ZHELIOCLINE-Q4N8-20260913`

## Purpose

Turn the released Short Video Studio from a one-project renderer into a repeatable local production workflow for a multi-video campaign without changing the canonical renderer.

## Source boundary

New:
- `revenue/hive/short-video-studio/production_queue.py`
- `revenue/hive/short-video-studio/test_production_queue.py`
- `revenue/hive/short-video-studio/production.example.json`
- `.github/workflows/hive003-production-queue.yml`

Bounded documentation update:
- `revenue/hive/short-video-studio/README.md`

Canonical `studio.py`, `app.py`, prior tests, and demo projects remain byte-identical.

## Contract

- exact SHA-256 binding to project bytes before a render is considered reusable;
- deterministic per-job spec identity;
- verified MP4 + SRT digests required before a job is skipped on resume;
- project or output mutation forces rerender;
- project mutation during render fails closed;
- partial failures persist successful jobs and permit bounded retry;
- duplicate job IDs, duplicate targets, traversal, symlink targets, and source/output aliases are rejected;
- customer delivery manifest is deterministic and explicitly carries no provider/publication/payment/revenue authority.

## Local acceptance before publication

Isolated queue tests using a renderer-interface test double:

- `python -m unittest -v test_production_queue.py` → 14/14 PASS
- `python -O -m unittest -v test_production_queue.py` → 14/14 PASS
- `python -m py_compile production_queue.py test_production_queue.py` → PASS

The branch workflow runs the same suite against the repository's actual `studio.py` import plus validation of `production.example.json`. Hosted workflow status is reported separately and is never inferred from the isolated run.

## External boundary

No customer or creator data, platform publishing, provider/account mutation, payment, spend, credentials, or owner-device action. A `DELIVERY_READY` local manifest means only that all listed local outputs exactly match the bound source revisions and recorded hashes.
