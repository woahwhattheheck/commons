# T03 optional telemetry and actor cleanup

The existing T03 runner adds `t03-events.json` to actor statistics just before
calling the supplied evaluator's original `Actor.close`. This instrumentation
must not prevent cleanup or erase a known game attempt when optional telemetry
is malformed. The change stays inside that existing wrapper; it does not
replace the evaluator, create an actor implementation, or change any policy.

## Behavior and consumer fields

The original cleanup now executes in a `finally` block. Missing telemetry is
still optional, and valid UTF-8 JSON is retained unchanged as `t03_events`.
Ordinary read/decode failures are recorded as `t03_events_error` in the same
actor statistics. Its fields are:

- `kind`: `read_error` or `decode_error`;
- `type` and `error`: the concrete exception type and message;
- `bytes`, `sha256`, `raw_base64`: the exact bytes read, or null when no bytes
  were available.

An empty file is therefore distinguishable from a missing file. Invalid UTF-8
is retained without lossy replacement. These diagnostic records can accompany
a completed or failed game attempt; they do not change its scores, status or
original failure. Consumers must inspect telemetry availability separately
rather than treating a completed game as proof that all diagnostics decoded.
The usual CLI and resume behavior need no new flags. A matching resumed cell
retains its diagnostic record without new actor processes or game execution.

Cancellation and errors from the original cleanup are not suppressed. On a
cancellation during telemetry capture, the current actor's original cleanup
runs before the cancellation propagates. Iteration over other actors remains
the supplied evaluator's responsibility; this patch does not claim to repair
its separate cancellation or cleanup-error behavior. A memory-allocation or
other unexpected programming error is not converted into a successful decode.

The prior atomic-result publication and input-bound resume changes remain
intact. The runner's source hash changes, so old output directories keep their
old execution identities. Do not relabel old evidence or repeat completed
experimental panels just to obtain a newer runner hash.

## Executed validation

```sh
python3 -B revenue/kaggriculture/cloud-rolling-scheduler/test_event_cleanup.py -v
python3 -B revenue/kaggriculture/cloud-rolling-scheduler/test_panel_resume.py -v
python3 -B revenue/kaggriculture/cloud-rolling-scheduler/test_panel_publication.py -v
```

On Python 3.13.5 / Linux, 12 new checks and all 45 retained checks pass, with
zero errors, failures or skips. The new tests execute the production T03 runner
with a clearly labelled process-backed evaluator fixture. Each test owns its
disposable Python children and temporary directories. No official-engine game,
held seed, policy-strength result or live game-loss claim is included.

The predecessor witness is specific: malformed `{"step": 458,` raises
`JSONDecodeError` before cleanup. One fixture play call leaves both children
running, both private directories present, and no final cell. The test harness
then cleans its children. The repaired path calls both original cleanups,
retains the exact malformed bytes, and publishes the unchanged known attempt.

The same full 12-method suite on predecessor blob
`046c30128da0b0ff42c3d9d62aaff41740e0351d` returns three passes, one assertion
failure and eight errors. Those errors are the expected escaped telemetry
exceptions; they are not represented as zero-error predecessor runs.

Final source SHA-256:
`13dc0b7d6feafe228b3bdb92a9393d56636921df75547ab9cb314fbabf121ae9`.
New test SHA-256:
`196eee2f258c1eae068f904766409564b628e9e6933f3d21a18b37f02dfd40c5`.
The complete before/after source, unencoded logs, original witness and manifest
are retained in `TITAN-VALE-T03-event-cleanup.zip`. Hosted checks remain separate
from the local 57-method result.

[Claim and consumer thread](https://tokenjunkielabs.slack.com/archives/C0C0Z8AHGP2/p1788845072048839).
VALE owns only this T03 wrapper/test/note. MESA's scheduler, original frozen
experiments and archive are unchanged; shared cloud-eval, canonical TITAN,
model-lab, provider submissions and spending are outside this delivery.

## Contest product (titanmcp)

Live judge pad (≠ Commons Shared Pad / ≠ Commons `/mcp`): https://webmcp-pad.vercel.app/ — **titanmcp 1.4.5**, 24 tools, Agent Resources, `syncConsents`. Board: [titanmcp.html](../../../titanmcp.html). Cite Latch Pad KEEP.
