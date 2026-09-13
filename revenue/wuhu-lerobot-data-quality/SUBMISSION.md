# Wuhu embodied-intelligence data-quality milestone receipt

## Target fit

The competition brief asks for an automated full-dataset report over roughly 100 LeRobot v2.1 dual-arm humanoid trajectories. Required outputs are faulted trajectory, anomaly type, anomaly location, data quality, and a 0–100 training-value assessment across temporal, multimodal synchronization, content/structure, and value dimensions.

`wuhu_quality.py` implements that inspection/reporting core against local dataset bytes. It scans every declared episode and every detected camera, locates frame spans and modalities, emits per-episode and overall scorecards, and records explicit capability receipts so missing decoders cannot masquerade as clean data.

## Current evidence

- Source is Python 3 with no network calls and no hosted-model dependency.
- Raw dataset paths are read-only; report/probe destinations below the dataset root are rejected.
- Parquet decoding uses optional `pyarrow`; video metadata and deterministic visual sampling use `ffprobe`/`ffmpeg`.
- `capture` freezes normalized, fingerprint-bound evidence; `inspect --probe-jsonl` reproduces the same report bytes.
- `python3 -B -m unittest discover -s tests -v` executes 15 passing tests.
- Fault injection covers frame loss/order, FPS jitter, timestamp reversal, state/action jitter, camera offsets/drift/coverage, corrupt video, black/flat imagery, vector non-finite/wrong-dimension/out-of-range values, and malformed metadata/path templates.
- Tests verify exact episode/frame/modality localization, span compression, incomplete-capability downgrades, HTML escaping, immutable dataset snapshots, output containment, symlink rejection, stable digests, and CLI exit behavior.

## External acceptance run still required

A submission-quality receipt must be produced in an environment with:

1. the organizer-provided dataset and its license/terms;
2. `pyarrow`, `ffprobe`, and `ffmpeg` available;
3. a report destination outside the raw archive;
4. `capture --require-complete` followed by `inspect --strict-capabilities`;
5. archived command output, probe fingerprint, report digest, full-file dataset hashes if required, and the generated report bundle;
6. manual review of visual heuristic findings and score thresholds against organizer reference data;
7. the organizer’s actual registration and submission workflow.

## Claim boundary

This repository milestone does **not** claim organizer registration, acceptance of terms, access to the private archive, organizer-data execution, leaderboard submission, finalist status, ranking, award, contract, or payment. Those states must be reported only from their own external receipts.
