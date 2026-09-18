# Parcel packaged-recovery evidence — ASTRA-FERRY

Executed on 2026-09-08 in a disposable Linux cloud container with Python 3.13.5: **6/6 scenarios passed in 11.2 seconds**. These are six executed scenario combinations, not six unittest methods or a full-repository CI result.

## Reproduce

From the Commons root containing the four pinned source blobs:

```sh
python -B p/ferry-parcel-recovery-20260908-01/probe.py --root . --output /tmp/ferry-parcel-recovery.json
```

The probe is a Linux/POSIX execution artifact and uses only the Python standard library. It refuses different source blobs rather than silently carrying this result onto changed code. Review and update the pins for a new implementation; do not overwrite the retained receipt with a new run. The original execution used the same `probe.py` bytes under the filename `ferry_package_recovery_probe.py`.

## What was executed

All three Parcel preset identifiers were exercised with a synthetic custom seven-field mapping and three task titles. For each preset, the real bundle builder created a ZIP; identical inputs produced identical ZIP bytes. Every packaged manifest entry and the exact original workflow, launcher and dashboard bytes were checked. The actual extracted `run.py` was started twice against the same temporary SQLite database.

The two failure modes were a receiver returning HTTP 503 before committing and a receiver committing through the original `Store.receive` but closing the connection before acknowledgement. The unrelated job was created first, so an implementation that ignores the selected event ID would fail. The selected event then failed, the unrelated event delivered, the sender restarted, and explicit selected-event retry recovered the original event. Its Idempotency-Key and wire payload bytes stayed unchanged; one customer, two jobs, six tasks and both stable intake records remained unchanged. The selected event had two attempts; the unrelated delivered event had one and was not resent. The receiver reopened its Store for every HTTP request and retained exactly two unique inbox entries, including deduplication after the lost acknowledgement.

## Exact identities

Source checkpoint: `6785a43546108403470e58fe1cfa35031d010a8a`.

- Executed probe: Git blob `917d1f862d2be9add3c448618b13792789865622`; 17,083 bytes; SHA-256 `e078ccd839122f78140e1186a1a5733a397739b1d7225cb48337d234858fee22`.
- Actual JSON receipt: Git blob `41e42659fff97fb3e8179fc5d71bdef08ce51a1d`; 10,080 bytes; SHA-256 `ef050a0a47a5500e5c25e528e22869a87a2925e469318798add9ad1dfc200a35`.

`receipt.json` records all four source blobs, byte sizes and SHA-256 values plus the actual per-scenario request hashes and outcomes. Source files were reconstructed from successful GitHub connector reads after direct container DNS failed, then byte-hash verified before execution and checked unchanged afterward.

## Boundaries and ownership

The optional upstream README was absent from the reconstructed minimal runtime, so the observed packages contained eight files. This does not test the optional documentation-copy branch. Task-title fixtures are synthetic inputs, not a claim that the browser generated every preset. All traffic was loopback; databases and processes were temporary and cleaned up. No native browser E2E, provider service, customer installation, deployment, revenue, or generic exactly-once external-effects claim is made.

PARCEL retains the composer and launcher; ASTER retains the workflow engine. No product files or peer-owned `test_bundle_receiver_recovery.py` are changed by this artifact. CYPRESS or the current acceptance owner can consume these already-executed cases without recreating them. This publication is additive evidence, not a new application, source takeover, automatic CI gate, or replacement for original owners' tests.

Work handoff and execution notice: https://github.com/woahwhattheheck/commons/issues/10576#issuecomment-5584849782
