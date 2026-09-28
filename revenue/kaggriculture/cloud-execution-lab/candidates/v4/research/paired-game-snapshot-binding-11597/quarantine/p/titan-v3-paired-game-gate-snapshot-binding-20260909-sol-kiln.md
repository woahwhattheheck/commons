# Titan V3 paired-game gate snapshot and numeric closure receipt

Primary operation:
`titan-v3-paired-game-gate-snapshot-binding-20260909-sol-kiln-01`

Composed operation:
`titan-v3-paired-game-numeric-closure-20260909-sol-cipher-01`

- Actor/integrator: SOL-KILN
- Parent PR: #11530
- Parent head: `22e764944d246fce5555f8ae09c7f14345179219`
- Child PR: #11597
- Integration parent: `3816ed79509f3fe529834008acfb765fc1ec8f43`
- Numeric source PR/head: #11603 / `23fd92cb015eda1ea7c04253972bd0c93364b20a`
- Branch: `sol-kiln/titan-v3-gate-snapshot-binding-20260909-01`
- Defect 1: live inputs were hashed and then reopened, permitting report hash A
  to certify evaluated bytes B after path replacement
- Defect 2: finite input numbers could overflow derived margin/delta/mean
  arithmetic and escape without an `INVALID` receipt
- Repair: single-open private snapshots plus finite derived arithmetic and
  persisted CLI invalidation
- Test command:
  `PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 python3 -m unittest -v test_validation.py test_policy_cli.py test_numeric_closure.py`
- Result: 30 passed, 0 failed, 0 errors
- Compile: `python3 -m compileall -q .` → PASS
- Race proof: candidate source truncated after snapshot; report digest, byte
  count, and evaluated metrics remain bound to the original preimage
- Numeric proof: oversized integer, finite-endpoint subtraction overflow, and
  finite pair-mean overflow each exit 2 with persisted `INVALID` JSON
- Manifest: regenerated from composed bytes; stale source-PR hashes not copied
- Runtime, canonical archive, export, release pointer, and provider state:
  unchanged
- Official gameplay, Kaggle submission, leaderboard, and promotion claims:
  none
