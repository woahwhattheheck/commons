# Vetter Tech-Transfer Recovery Boundary

This successor closes the three original #13976 stop-merge families **and** the independent Z-Helix exact-head RED on #14471.

## 1. Snapshot chronology

Every source and receiving row must satisfy:

`last_updated_utc <= snapshot.captured_at_utc <= evaluation time`

The chronology repair is installed into each private retained-core namespace before either current or historical compilation can occur.

## 2. Descriptor-bound production ingress

Production `_read_bounded()`:

- requires `O_NOFOLLOW` and rejects final-component symlinks;
- opens once and retains that descriptor;
- accepts only a regular file;
- enforces `MAX_JSON_BYTES` during consumption, before unbounded allocation;
- re-`fstat()`s the same descriptor and rejects in-place generation/size drift;
- remains bound to the opened inode if the pathname is replaced after open.

Hostiles cover final symlinks, same-size pathname replacement after open, and in-read byte-cap enforcement.

## 3. Current verification actually means current

The supported current surface is `engine.py`:

- `compile_transfer(source, receiving, policy)` has no `as_of` argument;
- `verify_report_current(report)` has only `report`;
- both sample process UTC through lexical capabilities constructed once at import;
- the construction factory and retained raw core namespace are deleted from the current module after binding;
- verification compares the full decision projection after resampling current UTC, excluding only evaluation time and receipt bytes.

A READY result that ages past the declared evidence freshness therefore fails current verification even if historical integrity remains valid.

## 4. Explicit time is historical/test-only

The independent review of `cdeded7f705394b4263e0fa002a4256e3a13ff82` correctly found that an importable clock-injectable verifier factory and a package-exported `compile_transfer(..., as_of=...)` could still mint current-looking artifacts.

That surface is removed.

- Explicit-time replay exists only in `historical.py`.
- Historical reports use schema `vetter-clinical-fill-tech-transfer-historical/v1` and authority mode `HISTORICAL_INTEGRITY_ONLY`.
- Historical verification uses a distinct historical-verification schema and exposes only `historical_decision_state`, never the current verification schema.
- Package `__init__.py` exports only current compilation/current verification.
- The retained predecessor source is remapped byte-for-byte from importable `_engine_v1.py` to inert `_engine_v1.txt`.
- `engine.py` and `historical.py` evaluate the trusted retained text into private namespaces, bind only their intended capabilities, then delete the raw namespace/factories from their importable surfaces.

The recovery tests inspect signatures and module attributes, reject a caller `as_of` on the current compiler, prove a historical envelope cannot pass the current verifier, and prove no importable `_engine_v1` Python module remains.

## Frozen predecessor behavior

The 144-packet synthetic corpus still executes the retained classifier through a test-local historical adapter: 120 READY plus four packets in each of six named HOLD families, deterministic receipts, order invariance, strict custody/type checks, replay/tamper checks, and output exclusivity. Deterministic fixture time is therefore preserved without being confused with current authority.

## Exact execution gate

The dedicated workflow is intended to run from this product directory:

```bash
python -m compileall -q .
python -m unittest -v test_engine.py test_recovery.py
python -O -m unittest -v test_engine.py test_recovery.py
python synthetic_acceptance.py
```

GitHub had scheduled **zero** runs for the predecessor recovery heads despite push/PR events. Zero runs are UNKNOWN/no-run, never represented as green. Any later hosted result must bind the exact semantic head it executed.

## Authority ceiling

Read-only synthetic/non-production handoff evidence only. No Vetter/provider outreach, live manufacturing write, process recommendation, deviation disposition, GMP/quality/scientific/regulatory decision, batch release, deployment, contract, payment, cash, or recognized revenue mutation is performed by this carrier.
