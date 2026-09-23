# Private cloud-to-PC bridge

Cloud sessions can send a TITAN Hands request to the logged-in Windows PC without opening a port or starting another coding harness. The PC makes outbound GitHub requests every 30 seconds, runs at most one queued request at a time, and returns the result on a private branch of `woahwhattheheck/commons-ship-enforcer`.

The existing public `fire_action` and `commons-device-executor` routes stay available. Use this private route when a request reads local files or returns other machine-specific data; its request and result stay off the public Commons repository.

## Inspect before starting

From the existing checkout, inspect queue metadata without executing a job:

```powershell
python -B -m host.cloud_pc_bridge --status
```

This mode uses GitHub GET requests only; it neither imports TITAN Hands nor
claims a request or writes a result. It works from a cloud host with the existing
GitHub CLI access too. `queued`, `started_without_result`, and `result_files` are
observed file counts, not proof of a running Windows worker. The separate directory
reads are not atomic; `worker_running` explicitly remains `UNKNOWN`. The `-B`
option avoids creating Python bytecode caches.

On the PC, read the existing task metadata separately:

```powershell
Get-ScheduledTask -TaskName "Commons Cloud PC Bridge" -ErrorAction SilentlyContinue |
    Select-Object TaskName, State, Actions, Principal
```

## Start it on the PC

The installer **registers and immediately starts** the logon task. It can consume
existing inbox jobs. Inspect their intended effects first; neither the installer
nor `--once` is a read-only diagnostic. Before upgrading, coordinate a pause in
new enqueues and let old bridge instances finish. The old version does not honor
the new worker mutex. Use this queue on one Windows host; a host-local mutex does
not coordinate separate computers.

Use the existing Commons checkout; do not make another clone. From its root, run:

```powershell
powershell -ExecutionPolicy Bypass -File host/install_cloud_pc_bridge.ps1
```

The scheduled task runs only in the signed-in Windows desktop session, at limited privilege. It uses the existing `gh` command-line sign-in and the existing Python installation. It opens no listener and starts no model. TITAN Hands is imported only when a request arrives.

For a visible one-time execution:

```powershell
python -B -m host.cloud_pc_bridge --once
```

## Send a job from a cloud session

Use the connected GitHub tools to create one JSON file on branch `pc-bridge`:

- path: `pc_bridge/inbox/<job_id>.json`
- `job_id`: stable, unique, 8–80 characters from letters, digits, `.`, `_`, or `-`
- body:

```json
{
  "schema": "commons-cloud-pc-job/v1",
  "job_id": "cursor-report-scan-20260923-01",
  "request": {
    "op": "observe",
    "target": "windows"
  }
}
```

`request` is passed to the existing `TitanHandsOne.handle()` surface. It can use the same TITAN Hands operations and targets available to a local harness. Do not put credentials in the request. The bridge refuses common credential formats and redacts them from results.

Read the result from `pc_bridge/results/<job_id>.json` on `pc-bridge`. A request is claimed by a durable `pc_bridge/started/<job_id>.json` marker before it runs. Keep the job ID, request and start marker stable. The bridge never replays a started job. A new ID is a new execution, not a result-delivery retry.

Jobs are processed one at a time. Request JSON is limited to 256 KiB; a returned result is limited to 512 KiB. Oversized results return a size and SHA-256 receipt so the cloud caller can ask for a narrower extract.

## Result delivery and crash recovery

The continuous worker keeps the current bounded, redacted result in memory until
GitHub readback matches its bytes. A delivery failure leaves that result pending;
the next poll retries delivery before taking another job and never calls TITAN
Hands again for that retry. A conflicting remote result is not overwritten and
raises `RESULT_CONFLICT` rather than falsely reporting `DONE`.

A fileless Windows named mutex serializes patched workers on the same host,
including manual `--once` runs, for the whole process loop. A second execution
returns `BRIDGE_BUSY`. No mutex file, profile directory, database, or disk result
cache is created. Durable request/start/result records stay in the private cloud
repository. The installer also uses Python's `-B` option.

This is **not exactly-once execution**. A process crash before GitHub accepts its
result loses any in-flight memory. A start without a result becomes `UNCERTAIN`
after 30 minutes, even when its inbox file was removed. Invalid or far-future
start metadata also becomes `UNCERTAIN`. A broker exception is `UNCERTAIN`, since
it may follow a side effect; an explicit `ok: false` response remains `FAILED`.
Neither state proves nothing happened. Inspect the affected system before
issuing a new job ID. `--once` exits 1 for a failed/uncertain/incomplete job and 2
for a bridge error. Exit 0 means the one-shot poll returned `IDLE`, or a stored
`DONE` result with `ok: true`; it does not mean every queued job completed.
Exiting also loses any undelivered in-flight result. Continue to read the private
result file for the job's durable outcome.

To stop without rebooting, first pause new enqueues and allow active work and
pending delivery to finish. Then disable and stop the task, retaining the cloud
records:

```powershell
Disable-ScheduledTask -TaskName "Commons Cloud PC Bridge"
Stop-ScheduledTask -TaskName "Commons Cloud PC Bridge"
```

To remove only the task after reconciliation:

```powershell
Unregister-ScheduledTask -TaskName "Commons Cloud PC Bridge" -Confirm:$false
```

## Data and resource behavior

- Job requests, start markers, and results stay on the private `pc-bridge` branch. No local clone, worktree, log, or result cache is created.
- The bridge uses GitHub's existing private-repository access on both ends. It does not create, print, or copy a token.
- Idle operation is one small Python process and a periodic GitHub poll. No Cursor, Devin, Codex, or other model harness is launched.
- The bridge calls TITAN Hands in the current user session; normal TITAN Hands capabilities remain available.
