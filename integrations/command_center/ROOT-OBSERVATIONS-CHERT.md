# Preserve work when Slack thread coverage is incomplete

This is the reproduction and consumer-integration guide for the complementary
repair in [PR #16385](https://github.com/woahwhattheheck/commons/pull/16385), targeting
SUNDIAL's existing [PR #16326](https://github.com/woahwhattheheck/commons/pull/16326).
It is not a second thread reader, a replacement board, or a deployed connector fix.

**Why this matters:** the command center uses a complete source snapshot to remove
records that are no longer present. A reply omitted from an incomplete observation
must not disappear from the work view together with its previously recorded owner
direction. Resolving a root identity is necessary, but does not by itself prove
that all of that root's known replies were observed.

## The worked case

All messages, work instructions, timestamps and identities in these tests are
fictional. The tests make no live Slack requests and do not change provider data.

1. The actual collector ingests a parent with two replies into the actual SQLite
   `WorkstreamStore`. A fictional owner direction is attached to the first reply.
2. A later channel observation contains a broadcast whose nested root still says
   two replies exist. The replies response instead returns a one-reply parent and
   only the second reply. The earlier first reply was not observed in this read.
3. Before the repair, nested-root evidence is discarded. The smaller response can
   be declared complete and the first work item disappears from the work view.
4. After the repair, the larger previously observed count remains binding. The
   batch is incomplete, valid fresh rows are ingested, and the earlier item and its
   owner direction remain visible. This is retention of an earlier observation,
   not a new claim that the missing message still exists at Slack.

The same real-store test suite exercises a zero-count parent naming a missing
latest reply, nested evidence returned inside reply pages, and a broadcast subtype
changing between history pages. Five of its eight methods fail against the old
reader. The other three test nullable metadata, legitimate complete-snapshot
removal, and persisted rate-limit cooldowns. All eight pass with the repair.

## What changed and what did not

The existing reader now combines top-level and nested root observations, keeping
the greatest observed reply count and every known latest-reply identity. It checks
these observations in channel history, direct-context selection, and fetched reply
pages. A zero-count parent with a known latest reply remains a thread candidate;
changed broadcast subtype across pages invalidates coverage. Malformed nested
counts and timestamps follow the existing top-level validation convention. Absent
optional fields remain supported.

Existing request/page/thread caps, metadata shapes, selected-data persistence,
redaction rules and owner-work storage are unchanged. `thread_ts` and `reply_count`
can still be null; no unknown root becomes its own child ID and no unknown count
becomes zero. Complete coverage still cannot grant ownership or provider-write
authority. The current repository merge/execution policy is not changed here.

## Actual execution

Execution environment: CPython 3.13.5 on Linux in an ephemeral cloud sandbox.
Native GitHub reads supplied the complete source files for the selected dependency
closure; all eleven files were Git-blob verified before and after execution. The
original collector, request budget, schema, SQLite store, replay and both original
test suites were unmodified. Only provider responses are fixtures. No production
class was replaced with a local imitation.

The selected suite contains **114 methods: 27 new reader tests, 8 new real-store
tests, 47 original SUNDIAL tests, and 32 existing collector/thread tests**.

| Source | Invocation mode | Result |
| --- | --- | --- |
| Repaired reader | Normal Python | 114 tests, 0 failures, 0 skips; exit 0 |
| Repaired reader | `python -O` | 114 tests, 0 failures, 0 skips; exit 0 |
| Repaired reader | `python -OO` | 114 tests, 0 failures, 0 skips; exit 0 |
| Original reader | Normal Python | 114 tests, 48 assertion/subtest failures; exit 1 |
| Original reader | `python -O` | 114 tests, 48 assertion/subtest failures; exit 1 |

The 48 failures are 43 assertions/subtests in the new reader suite plus five new
store-retention methods, **not 48 distinct bugs**. The original 79 test methods
remain unchanged. The original offline replay also ran normally and under `-O`;
its outputs were byte-identical, SHA-256
`08ec7901e93eece00a36d89e2bc4462780891e5c02886e6f7d1bc8e6b2caab28`.

These are real executions of the complete selected test dependency closure, not a
full repository checkout, hosted Actions run, UI-rendering test, or live connector
deployment. Repository-wide integration and current-main execution authority
remain separate. The earlier limited component-only evidence is superseded for
these four suites, not promoted into a broader claim.

## Reproduce from a checkout containing this donor

Run at the repository root; no account credentials are needed. These tests use
fresh temporary SQLite databases and do not use the operator's private state.

```sh
python -m unittest -v test_slack_root_observations_chert test_slack_root_retention_chert test_slack_thread_root_context integrations.command_center.test_slack_threads
python -O -m unittest -v test_slack_root_observations_chert test_slack_root_retention_chert test_slack_thread_root_context integrations.command_center.test_slack_threads
python -OO -m unittest -v test_slack_root_observations_chert test_slack_root_retention_chert test_slack_thread_root_context integrations.command_center.test_slack_threads
python -m integrations.command_center.slack_thread_root_replay
```

To run only the demonstrated work-preservation case:

```sh
python -m unittest -v test_slack_root_retention_chert.StoreRetentionTests.test_nested_prior_count_preserves_owner_work
```

For a before/after comparison, use a **separate disposable copy** of this selected
source closure, replacing only its `slack_threads.py` with the original from commit
`5406ef6ca6c75eccf18434a0b809069911326e3f`. Do not overwrite an active checkout or
another seat's staged files. The expected original-reader Git blob is
`99e50df43efe902763788559270f0cd23253630e`; the fixed blob is
`31af4ec26e67a522fb9cbf84bd4fea712166c065`.

## Inspect the retained execution record

`ROOT-OBSERVATIONS-CHERT-EXECUTION.json.xz` contains all seven final command records,
including the deliberately failing baseline runs, exact stdout/stderr, return
codes, timestamps, interpreter identity and eleven input-file digests. It is
6,876 bytes compressed and 190,000 bytes uncompressed. Its SHA-256 is
`4f29e0aa8090c800f228b10affbbec5b08b220aea52823c12d4737e5ca151f40`.
It records source head `a57b60cbae9ae937d860a90bbf3d7ff5c293ae85`; subsequent guide
and receipt publication does not alter those executed source blobs.

This read-only command verifies the archive and the checked-out input bytes. A
mismatch means this historical run does not describe that file, not that the new
file is defective. Run the tests again against the intended new composition.

```sh
python - <<'PY'
from pathlib import Path
import hashlib, json, lzma
p = Path('integrations/command_center/ROOT-OBSERVATIONS-CHERT-EXECUTION.json.xz')
packed = p.read_bytes()
if hashlib.sha256(packed).hexdigest() != '4f29e0aa8090c800f228b10affbbec5b08b220aea52823c12d4737e5ca151f40':
    raise SystemExit('Execution archive digest mismatch')
record = json.loads(lzma.decompress(packed))
mismatches = []
for row in record['inputs']:
    path = Path(row['path'])
    if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != row['sha256']:
        mismatches.append(row['path'])
for run in record['runs']:
    print(run['label'], 'exit', run['returncode'], 'tests', run['test_count'], 'failures', run['failure_count'])
if mismatches:
    raise SystemExit('Historical source mismatch: ' + ', '.join(mismatches))
print('Archive and eleven historical input identities match; not a new execution.')
PY
```

## Integration handoff and attribution

The donor targets `swarm-zz/slack-thread-root-context-sundial64`. Compose the accepted
repair into that existing implementation rather than retaining competing readers.
Preserve current-main changes and execute the existing repository review/merge
front door against the exact resulting source and provider state. Queued jobs are
not passing jobs, and a clean GitHub merge calculation is not execution evidence.
This guide grants no exception to those requirements.

SUNDIAL-64 retains original implementation and main-integration ownership;
BITTERN-58E2 retains the live symptom discovery. CHERT-6B21 contributed the
independent findings, complementary source repair, 35 additional tests and actual
consumer-integration execution. All are distinct contributions under a shared
GitHub account; no second human approval or independent account is implied.

Operation: `slack-root-observation-review-chert6b21-20260919`.
