# Titan V3 paired-game gate snapshot-binding hardening receipt

Operation:
`titan-v3-paired-game-gate-snapshot-binding-20260909-sol-kiln-01`

- Actor: SOL-KILN
- Parent PR: #11530
- Parent head: `22e764944d246fce5555f8ae09c7f14345179219`
- Branch: `sol-kiln/titan-v3-gate-snapshot-binding-20260909-01`
- Owned repair paths: paired-gate acquisition, schema validation, tests,
  threat model, verification receipt, and source manifest
- Defect: the parent gate hashed each live input and then reopened it for
  parsing, allowing report hash A to certify evaluated bytes B after a path
  replacement
- Repair: open each source once, stream it to a private snapshot while hashing,
  parse only those snapshots, record exact input byte counts, and recheck
  snapshot digests after evaluation
- Adjacent fail-closed repairs: boolean `schema_version` values are rejected;
  integer-to-float overflow is converted to `GateError`
- Test command:
  `PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 python3 -m unittest -v test_validation.py test_policy_cli.py`
- Result: 27 passed, 0 failed, 0 errors
- Compile: `python3 -m compileall -q .` → PASS
- Race proof: candidate source truncated after snapshot; report digest, byte
  count, and evaluated metrics remain bound to the original preimage
- Runtime, canonical archive, export, release pointer, and provider state:
  unchanged
- Official gameplay, Kaggle submission, leaderboard, and promotion claims:
  none
