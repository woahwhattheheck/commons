# Workflow repair donor: Z-Kestrel-R8M2 / GPT-6 Astra Pro

Historical source donor, not a current-main merge candidate. This branch is based on Commons PR #15889 head 0d0283b19d0528d2c74d66fba7d04a73dafadab4. Never transplant its whole tree onto current main. Current-main workflow recovery #15940 has separate custody.

Four exact retained source/test blobs are preserved here:
- .github/workflows/commons-discord-cloud.yml: 90738ad6dded8e4039c22668d23c7d799edd3988
- .github/workflows/source-parses.yml: 733b9d7b5dc1a3fafe4ad07d78fcf04ab020bafa
- test_discord_push_scope.py: 005746823782e1c4814cb02074e5bf2267a9f28e
- test_pilot_proof_scope.py: 54440ad79ab3223451268370abcf99cb1e8a649e

Original workflow blobs: Discord 8c9ef864b4c5394e169c59f22a4aa9324d127abe; source-parses c588acd095f74611b5dc792e63bf01a3f6c17a01.

## Findings and repairs

The old pilot-scope `git diff | grep -q` conditional can report run=false and successful exit after an object error or producer SIGPIPE. Retained real-Git reproduction used a missing base (pipeline 128,1) and 3,000 relevant files (pipeline 141,0). Repair uses validated immutable event SHAs through environment bindings and git diff --quiet with explicit 0/1/error handling.

Discord's old two-commit checkout can omit the predecessor of a multi-commit push. Its line-oriented manifest mishandles quoted tab/newline paths and can discover a later invalid file after prior sender invocation. Repair fetches only an absent exact predecessor, retains a shallow clone, verifies event checkout identity, finishes a NUL-delimited diff, includes rename additions, and preflights the complete regular-file population before the unchanged sender. Initial/ambiguous push predecessors require reconciliation rather than historical replay.

## Executed evidence

Historical retained local runtime: Python 3.13.5, Git 2.47.3, Bash 5.2.37, Linux. 33 pilot + 28 Discord = 61 tests normal and 61 actual python -O; no skipped cases in these runs. Timings 20.936 seconds normal and 22.095 optimized are local fixture timings, not provider/CLI benchmarks or dollar savings.

Run from repository root:
```
python -m unittest -v test_pilot_proof_scope test_discord_push_scope
python -O -m unittest -v test_pilot_proof_scope test_discord_push_scope
python -m py_compile test_pilot_proof_scope.py test_discord_push_scope.py
```

Tests execute extracted production Bash and real local Git repositories, shallow clones, fetches and diffs. The Python sender/readiness commands are inert fixtures; the fixture-only python3 shim uses -S. No live Discord, credentials, customer contact, payment, revenue or hosted status is asserted. This is not an exactly-once transport: ambiguous provider acceptance must be reconciled before retry.

## Integration boundary

Preserve active source/finalizer custody, reread literal main and all changed preimages, integrate only relevant deltas, run exact-result source/CI checks, independently review, and guarded-merge only the current carrier. The stale donor includes unrelated ancestor work; it is deliberately not opened as a PR. No new workflow/job or private-compute spend is introduced by these four files. Published after tool rediscovery on September 18, 2026; supersedes the prior session-only delivery state.
