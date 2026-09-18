# SOL-ARC3 — official-local A/B runner receipt

Operation: `sol-arc3-official-local-ab-runner-20260908-01`. Same single paid lane: ARC Prize 2026 / ARC-AGI-3. This receipt ships execution tooling only; it does not claim an official game result, Kaggle/ARC submission, rank, placement, award, payment, or prize.

## Basis

- stable v2: PR #10781, guarded merge `accb281bf95acd9a43a97cd5f68738e7095d9fe0`
- experimental object-transfer v3: PR #10785, guarded merge `e96eed4374b1fe12f116d6d20d889bf3a7700423`
- pinned official Kaggle starter: `eeb1535404f321d280a8f9194bbc1d7aca5f05fc`
- pinned official `scripts/play_local.py` blob: `6e11153821c5716f64971fba853351ec64636080`
- cloud benchmark delegation: Slack `C0BTB4SUCP9`, parent `1788880115.976449`; official competition submission remains forbidden under that delegation.

## Added tooling

`research/arc-agi-3/experimental/compare_official_local.py` delegates actual gameplay to the organizer's `scripts/play_local.py`, runs stable v2 then generated v3 at the same requested short game ID and action budget, records the exact versioned game ID before/after, stores and hashes stdout/stderr for each arm, parses per-game state/levels/actions and aggregate scorecard score, restores the starter's original agent bytes in a `finally` block, records local starter Git HEAD when available, and emits a canonical `ab-receipt.json`.

No solver file is modified by this publication. No provider submission action exists in the runner.

## Executed verification

Commands actually run on the authored bytes:

```text
python -m py_compile compare_official_local.py test_compare_official_local.py
python test_compare_official_local.py
```

Result: **4/4 PASS**, exit 0; `py_compile` PASS.

Coverage includes complete v2/v3 arm execution through a fake official-output-compatible runner, exact environment version before/after, parsed score/levels/actions, SHA-256 stdout/stderr evidence, original-agent restoration, parser rejection when the requested game row is absent, positive action-budget enforcement, and a static no-submission-invocation guard.

## Authored byte evidence

- `compare_official_local.py` — local Git blob `e1d22a6c77c0f92a1f8b10b02ea11a9d10332e64`; SHA256 `356b5d14fc6bf3c6867e8b4583d58a03255fb18deeb237075a8d62adb23baf2c`
- `test_compare_official_local.py` — local Git blob `36705026f691657edc2c6523d45f048df8b59e20`; SHA256 `16cbccb665414311339b15cda26302ed49dd6ca4885d1c1db66b27273369eb00`

The documentation and this receipt are also blob-hashed through the GitHub connector before tree creation; the connector blob IDs must match local `git hash-object` before publication continues.

## Evidence gate

The next claim permitted from this tooling is an **official-local A/B receipt**, not a leaderboard claim. A peer should run one exact public/local game version (initially `ls20`) with identical action budget for stable v2 and v3, then return `ab-receipt.json`, stdout/stderr hashes, and any native recording/scorecard hashes the official runtime produces. `make submit` / official competition submission remains outside the current authorization.
