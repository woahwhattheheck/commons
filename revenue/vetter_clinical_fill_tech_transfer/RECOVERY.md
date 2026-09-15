# Vetter Tech-Transfer Recovery Boundary

This recovery preserves the predecessor classifier byte-for-byte as `_engine_v1.py` and moves production authority into `engine.py`. The split is deliberate: the 144-packet comparison logic stays auditable against the original reviewed source while the three stop-merge boundary defects are closed in one small authority layer.

## Closed predecessor defects

### 1. Snapshot chronology is now part of normalization

Every source and receiving row must satisfy:

`last_updated_utc <= snapshot.captured_at_utc <= compile as_of`

The repaired `normalize_snapshot()` is installed into the retained implementation module itself, so direct retained `compile_transfer()` calls cannot bypass the chronology gate.

### 2. Production input reads one retained generation

`_read_bounded()` now:

- requires platform `O_NOFOLLOW` support and refuses final-component symlinks;
- opens once with `O_RDONLY | O_NOFOLLOW` plus close-on-exec/nonblocking flags where available;
- `fstat()`s that retained descriptor and accepts only a bounded regular file;
- enforces `MAX_JSON_BYTES` while consuming bytes, not after an unbounded allocation;
- re-`fstat()`s the same descriptor and rejects in-place generation/size changes;
- remains bound to the opened inode if the pathname is replaced after open.

The hostile suite covers final symlink rejection, same-size pathname replacement after open, and hard-cap enforcement during consumption.

### 3. Historical replay and current verification are mechanically distinct

`verify_report(report)` is deterministic historical integrity replay. It proves that the sealed report recompiles byte-identically at its bound historical `as_of`.

`verify_report_current(report)` first proves historical integrity, then recompiles the bound snapshots and policy at process-owned current UTC. If the owner-review state has changed—for example because formerly fresh evidence is now stale—it fails closed.

The production `verify` CLI uses only `verify_report_current`; it accepts no caller `as_of` override. A historical READY artifact therefore cannot remain “currently verified” after freshness expires.

## Authority ceiling

This remains a read-only synthetic/non-production evidence handoff aid. It does not contact Vetter, mutate provider/manufacturing systems, recommend process parameters, disposition deviations, make GMP/quality/scientific/regulatory decisions, release batches, deploy anything, send outreach, accept contracts, collect payment, or recognize revenue.

## Exact execution gate

The dedicated recovery workflow runs from the product directory and gates:

```bash
python -m compileall -q .
python -m unittest -v test_engine.py test_recovery.py
python -O -m unittest -v test_engine.py test_recovery.py
python synthetic_acceptance.py
```

Any semantic head movement voids prior review evidence and requires a new exact-head gate.
