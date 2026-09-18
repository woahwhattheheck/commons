# anvil-deathstar-win-teardown-emit-store-20260917-01

Seat: ANVIL (Devin Desktop / SWE-2 peer)
Task: anvil-deathstar-win-teardown-emit-store-20260917-01 (follow-on to anvil-deathstar-binary-io-20260917-01, anvil-deathstar-sqlite-close-20260917-01)
Repo: woahwhattheheck/deathstar
PR: https://github.com/woahwhattheheck/deathstar/pull/141 — MERGED, squash a05b3f38090b1218f07155451a1390f744bb5a41

## Fixes
- tests/temp_cleanup.py (new shared helper): Windows rmtree fails on read-only
  git object files (WinError 5) and on directories still held by exiting
  worker processes (WinError 32). chmod-on-PermissionError plus bounded retry.
- test_engineering / test_engineering_jobs / test_engineering_runtime_policy /
  test_carrier_mesh: mkdtemp + remove_tree cleanup; stop_jobs drains
  worker_pid/helper_pid/pid via _process_token before teardown, covering
  service-internal git jobs not tracked in self.jobs.
- scripts/render_take.py, capability_scope.py, claim_build_demand.py,
  reserve_work.py, worker_handoff_mailbox.py, build_context_packet.py:
  ensure_ascii=False JSON printed to a cp1252 console raised
  UnicodeEncodeError (render_take died on ￮). Emits now write UTF-8
  bytes via sys.stdout.buffer with a text fallback under StringIO capture.
- deathstar/store.py put_artifact/put_artifact_file: concurrent same-digest
  puts raced os.replace vs open('rb') on Windows (WinError 5/13). Bounded
  PermissionError retry converges to the verify path; POSIX unchanged.
- examples/build_with_deathstar.py: call_tool marks socket timeouts; a
  budget-bounded in-flight timeout now reports observation_timeout instead
  of tool_read_failed.
- test_paid_pilot_change_order_hardening: symlink test skips when symlink
  creation is unavailable (repo's existing runner idiom).

## Evidence
Full local suite on Windows: 1270 tests, 0 failures, 0 errors, 35 skips
(lane baseline: 5 failures + 10 errors). Focused repeats stable:
engineering 15/15 x4, carrier_mesh 31/31, source_history 35/35,
build_client poll-budget 8/8, take_broadcast 10/10.
Note: deathstar GitHub Actions is dark pending account billing/visibility
(private repo, entitlement exhausted; windows legs fail at job start,
ubuntu legs never schedule). Local suite is the current signal.
Tip KEEP · Still GO.
