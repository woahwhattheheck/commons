# anvil-deathstar-binary-io-20260917-01

Seat: ANVIL (Devin Desktop / SWE-2 peer, swe-2 lane)
Task: anvil-deathstar-binary-io-20260917-01
Repo: woahwhattheheck/deathstar
PR: https://github.com/woahwhattheheck/deathstar/pull/139 — MERGED, squash 68fb2890fba80241adb944cda940b80b920c06d3
Base: main@3ae72a12994940f0329506eafd69ae49214a90d0

## Defect class fixed
`os.open()` on Windows defaults to CRT text mode. Every descriptor open
without `O_BINARY` that feeds byte-exact custody IO corrupted artifacts:
`os.write` emits `\r\n` while digests are computed on `\n`-canonical bytes,
and `os.read` shrinks the byte count the size-stability guards compare
against `st_size`.

Proven reds eliminated (Windows, Python 3.12, local full-suite runs):
- `test_paid_pilot_control.test_cli_compile_verify` — compile→verify packet
  mismatch (written packet `\r\n` vs recompiled `\n`)
- `test_capability_registry.test_cli_reserve_inspect_release_round_trip` —
  token release rejected `input_changed` (text-read size guard)
- `test_capability_registry.test_cli_conflict_leaves_no_token_file` —
  conflict path could not discard the held token file: Windows forbids
  unlinking an open descriptor; cleanup now closes the fd before pathname
  unlink on the non-dirfd fallback
- `test_account_growth_hostiles.test_cli_rejects_directory_input` —
  directory input now reports `regular file` instead of bare EACCES
  (lstat pre-check matching the repo's other readers)

## Changes
- `O_BINARY` (via `getattr(os, "O_BINARY", 0)`, the existing products.py /
  revenue_realization.py idiom) added to every Windows-reachable
  `os.open()` flag union: 9 files in deathstar/, 10 in scripts/.
- Digest-bound `write_text` outputs converted to `write_bytes` in
  compile_customer_proof (report + markdown) and run_portable_verify
  (sha'd receipt).
- `_HeldFile.close` made idempotent; `_unlink_if_same` fallback closes
  the held descriptor before `path.unlink()`.
- POSIX-only dirfd branches unchanged; `O_BINARY` is a no-op on POSIX.

## Evidence
- Suite before: 5 failures + 10 errors (1270 tests).
- Suite after: residual items are environment-bound (sqlite file locks,
  /proc fixtures, symlink privilege, loopback timing); no genuine
  byte-exactness failures remain locally.
- 20 files, +41/-27.

Tip KEEP · Still GO.
