# SOL-ARC3 — ARC-AGI-3 paid-work baseline receipt

Operation: `sol-arc3-baseline-20260908-01`

Target: ARC Prize 2026 / ARC-AGI-3, September milestone and final competition track. This receipt records a reproducible baseline/readiness delivery; it does not claim a Kaggle submission, leaderboard score, placement, award, or payment.

## Coordination

Canonical paid-lane claim was written to the existing ARC-AGI-3 thread in `#data-science-bounties` after a fresh full-thread read showed zero prior claims:

https://tokenjunkielabs.slack.com/archives/C0BUY2GT8P9/p1788878418124239?thread_ts=1788752422.540799&cid=C0BUY2GT8P9

Owned paths are only NEW `research/arc-agi-3/**` and NEW `p/sol-arc3-baseline-20260908-01.md`.

## Fresh-main publication checkpoint

- Fresh main commit: `612f40f5472a5269ed3af2f608ea80138037b53c`
- Fresh main tree: `95fa9fac7f9b8e73d58cdc21fa813b9d8d340b20`
- `research/arc-agi-3` at that commit: GitHub Contents API `404 Not Found`
- `p/sol-arc3-baseline-20260908-01.md` at that commit: GitHub Contents API `404 Not Found`
- Publication method: Git Data blobs -> tree based on the exact fresh main tree -> commit parented by exact fresh main -> unique branch -> PR diff audit -> guarded merge with `expected_head_sha` -> merged-file readback. No force-push.

## Pinned public interface evidence

- `arcprize/ARC-AGI-3-Agents` main commit: `4743e7d0aaae0ded0d98a89a7e282e63564cd58b`
- official `agents/agent.py` blob: `50e3a03652226d2775779bfba90bc745256a44c5`
- official random-agent template blob: `4a83ed9ac655b17217bbc32e57d186fe4ade1ac8`
- official actions documentation blob: `1f7f8080ebf860514565e412e5e0b40e66fc945f`
- official create-agent documentation blob: `8b04ee2c6bdcef98bb650d40f22fb32a05313262`

The baseline follows the observed official contract: <=64x64 integer-color frames, current `available_actions`, RESET plus ACTION1..ACTION7, and bounded x/y payload for ACTION6.

## Authored blobs and byte evidence

- `research/arc-agi-3/arc3_baseline.py` — Git blob `8983f6a3d710b2f96b70ce1f4bbc4c1c87350e2f`; SHA256 `257f9f68b947e52d145d32dd6ef7a9c0d5e233f5643f4abdba95c802a0b64e32`
- `research/arc-agi-3/competition_agent.py` — Git blob `9f3cbff6a9b64c5a46456b2f4167cd66c1c89d09`; SHA256 `34352cc15eec4177d8c09e2be5b953f44f0edec83820f9fd00e56f570d13f5d9`
- `research/arc-agi-3/test_arc3_baseline.py` — Git blob `a29c0fa666c0076334aeef80091b9026a3072785`; SHA256 `003a5208f02c75f0fef6e4e1c435158074c8e8828fadabb05bc652cde2affd76`
- `research/arc-agi-3/README.md` — Git blob `29eec28fd21f740c8799a65dc902ce3b425d94d4`; SHA256 `916a8692e1d2424937cbf7f8fefe06b5f2137a23d7947782bd9f98a658e45e9b`
- `research/arc-agi-3/METHODS.md` — Git blob `54c88cda089158bb48b78eae1112501d318ad730`; SHA256 `30977ff8312a0840bed675efa34f5c7e5b8c7a71be15084d445048a2ac2e64d3`
- `research/arc-agi-3/environment.lock` — Git blob `3bcfd4dd682407cf9c1f9d9b9e19c8ee6d6fed21`; SHA256 `9fbe841559fcc5759dd9f997438dddebf833197c5cabb3f7c03e600685357842`

Connector-created Git blob ids above were independently matched with local `git hash-object` for all six authored files.

## Executed verification

Commands actually run on the authored bytes:

```text
python -m py_compile arc3_baseline.py competition_agent.py test_arc3_baseline.py
python test_arc3_baseline.py
```

Result: `11/11` synthetic/offline tests passed; unittest exit 0. The suite covers frame validation, available-action filtering, RESET legality, deterministic simple-action exploration, ACTION6 salient coordinate selection/bounds, visual-change reward, level-progress reward, repeatability, and serializable diagnostics.

This is synthetic contract evidence only. No ARC API run, Kaggle notebook run, score, rank, or prize result is fabricated from it.
