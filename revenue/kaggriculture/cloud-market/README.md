# Frozen-source Kaggriculture strategy study

This is an additive continuation of Euler's device-side agent work, not a rewrite
or replacement of the accepted package. It consumes the exact `main.py`, frozen
incumbent, source loader and `ECONOMICS.md` from Commons commit
`c57fc2962d7a0da5109162f0b6a267967c3a616e`. Each byte set is checked against its
Git blob ID and recorded with SHA-256. The prior long-horizon, marginal-lifetime
and same-tile-bonus experiments are retained in the original package; they are
not silently promoted or repeated here.

The eight declared candidates test compact labor/capacity, unused care-yield
headroom and a different travel-distance penalty. Each is emitted as complete
standalone Python, with no live policy imports. Development seeds are
733, 2801, 8191, both seats, against frozen Euler28 and original compact22.
Selection maximizes the smaller of the two mean money margins, then the overall
mean and candidate name. Only that exact-byte selection advances to validation:
1237, 4421, 10007, 32771, 65539, 131071, 262147, 524287, both seats, additionally
against the original incumbent36 and official starter. Validation outcomes do
not tune the candidate or change the declared selection rule.

## Reproduce in ephemeral cloud storage

```sh
cd revenue/kaggriculture/cloud-market
python -B study.py prepare --root /tmp/kag-study
python -B test_study.py
python -B study.py development --root /tmp/kag-study
python -B study.py validation --root /tmp/kag-study
```

Preparation is the only networked phase. The focused Actions workflow prepares
public source and then runs all actual-interpreter tests and games with Docker
networking disabled, read-only repository source, 1.6 CPU and 6.5 GiB memory.
The existing accepted agent, original evaluator and submission notebook remain
unchanged. All generated files and snapshots live in ephemeral cloud storage.

Every game result, including failures, is fsynced to an append-only journal.
Interrupted runs resume with the same full source/runtime/settings contract;
only a torn final journal record is removed. Complete corrupted records or
changed contracts are errors, not excuses to blend incompatible results.
Both seats share a seed cluster for descriptive bootstrap intervals. Failed games
are never counted as wins. The selected policy is replayed against every
validation opponent. Code hashes, all losing candidates, per-game records,
selection, source snapshots, runtime image and resource receipts are retained.

The existing KAG-EVAL driver's strict one-second RPC limit does not emulate
Kaggle's overage-time bank; see `../cloud-eval/README.md` for its limitations.
These are official-interpreter experiments, not hosted Kaggle acceptance,
leaderboard placement or prize receipts. Root keeps the existing account and
notebook submission; this workflow never registers, accepts terms or submits.

Owner-authored additions: MIT OR CC-BY-4.0, preserving the same dual grant in
`../20260907-offline-agent/LICENSE`. Attribution: Bryce Xavier Muhlnickel /
TokenJunkieLabs; Euler's base implementation, ASTRA-WORK continuation.
Upstream Kaggle source remains Apache-2.0 and is not relicensed.
