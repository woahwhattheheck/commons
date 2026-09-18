# Big Onion sensitive-key shape repair

Operation: `big-onion-sensitive-key-shape-repair-20260909-01`
Source package: `big-onion-hold-rescue-01`
Source PR: #11260
Independent review blocker: `5158123659`

## Finding

The landed sensitive-field validator only case-folded top-level keys and compared literal spellings. Canonical top-level `email` failed closed, but common equivalent shapes such as `customerName`, `payment-token`, `card number`, and nested `{"metadata":{"email":...}}` remained eligible. That contradicted the package's explicit sensitive/customer/payment-shaped field fail-closed boundary.

## Repair

Forbidden key names are now normalized to an alphanumeric case-folded shape and the validator recursively scans JSON mappings and sequences. This closes camelCase, punctuation/space, and nested sensitive-key variants while preserving benign nested synthetic metadata.

Exact landed preimages:
- source `99de466b0c75bd2d17f76658523a8a2107cb4d2e`
- test `91f7c8edb156779eb63db5ba92d586c532e43e57`

Exact repaired blobs:
- source `7b0a8bf1b70d49b26402a2242c7d39ee570d7fe4`
- test `f37b120e6aa52134babe8f503515171d2c77e807`

## Acceptance

- byte-faithful preimage reconstruction matched both Git blobs before editing
- `py_compile` exit 0
- focused unittest 11/11 PASS (including canonical, camelCase, punctuation, spaced, nested-mapping, and nested-list sensitive-key denials plus a benign nested-metadata positive)
- CLI exit 0; eligible IDs remain exactly `E1,E2`
- E2 remains eligible at exactly 48 hours
- replay remains identical
- `sends=0`, `actions=0`, `provider_writes=0`, `state_mutations=0`, `events_added=0`
- fixture and manifest are unchanged

The local Python harness printed an unrelated spreadsheet-runtime warmup warning during interpreter startup; compile, unittest, and CLI processes all returned 0 and the Big Onion suite itself was clean.

## Boundary

Synthetic/read-only only. No real customer/payment data, outreach, reminder, collection, provider/customer/system write, transport, spend, owner-PC action, or force-push.