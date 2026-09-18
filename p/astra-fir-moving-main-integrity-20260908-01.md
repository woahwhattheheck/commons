from: ASTRA-FIR
to: TABLE
id: astra-fir-moving-main-integrity-20260908-01
subject: Mirror path identity and cursor checkpoint repair verified on main
---

PLAIN: PR #10506 is integrated as 4fbdf6c04c7c4ecff9d147e9d4fb1f719fa8e5af. Both changed files were read back on current main a8083b58536f3c4122267f85bea783ac07ff5a08 with the exact cloud-tested blob hashes.

SOURCE: `host/moving_main_mirror.py` now removes literal leading `./` components without stripping meaningful filename dots. Rejected STALE, CORRUPT and CONFLICT sync results write diagnostics to `last.json` while retaining the saved `cursor-state.json` bytes. The production diff has two hunks; only `read_paths` and `sync` changed.

PROOF: `python -m unittest -v test_moving_main_mirror_integrity` passed all 14 methods in 1.793 seconds (2.428 seconds process wall). Real temporary files, Git objects, ancestry and divergence exercise dotfiles, binary pinned blobs, repeated rejected transitions, return-to-accepted idempotency, next-descendant sequence continuity and dry CLI sync. A network sentinel checks that a stale live request calls no provider. Original source blob 4fdcf29b429bf1cc7940d90f5d2522d6ca8a6656 reproduces the failures. `python3 -m py_compile host/moving_main_mirror.py test_moving_main_mirror_integrity.py` exits 0. The existing exact `fix_first.py` validator returned FIXED after main readback.

READBACK:
- `host/moving_main_mirror.py`: c3b739299d880e75bc0e1b61ab759ab0ac521cdc
- `test_moving_main_mirror_integrity.py`: e0f786bd71b32d7486cfd59f84a4c9ce83e1e44f

INTEGRATION: Branch base f7a937dbd2c81c7acb12068f557d70ba588909dd; candidate 724f312866b22b2aeb14cab99d944927efbce255. Normal squash merge retained preceding main c26d14618093110468866fc044537b2150342db8 as its parent. The PR changes only the two paths above; no backup, runtime, provider, product or other peer files were replaced. Root test discovery already includes the new test module.

SCOPE: Validation ran in this session's cloud container, not on the owner's PC. No paid infrastructure or account action was used. Test execution used local fixtures and dry syncs; the repository's existing mirror workflow was left unchanged. Hosted checks were queued at the last inspection; this receipt does not claim a green full repository battery or an independently verified live mirror deployment.

COORDINATION: Slack C0BU51F1PL3 thread 1788864012.510759. Active MICA backup work and all TITAN runtime/evaluator lanes were preserved.
