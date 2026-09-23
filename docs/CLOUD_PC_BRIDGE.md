# Private cloud-to-PC bridge

Cloud sessions can send a TITAN Hands request to the logged-in Windows PC without opening a port or starting another coding harness. The PC makes outbound GitHub requests every 30 seconds, runs at most one queued request at a time, and returns the result on a private branch of `woahwhattheheck/commons-ship-enforcer`.

The existing public `fire_action` and `commons-device-executor` routes stay available. Use this private route when a request reads local files or returns other machine-specific data; its request and result stay off the public Commons repository.

## Start it on the PC

Use the existing Commons checkout; do not make another clone. From its root, run:

```powershell
powershell -ExecutionPolicy Bypass -File host/install_cloud_pc_bridge.ps1
```

The scheduled task runs only in the signed-in Windows desktop session, at limited privilege. It uses the existing `gh` command-line sign-in and the existing Python installation. It opens no listener and starts no model. TITAN Hands is imported only when a request arrives. To remove the task:

```powershell
Unregister-ScheduledTask -TaskName "Commons Cloud PC Bridge" -Confirm:$false
```

For a visible one-time run while diagnosing setup:

```powershell
python -m host.cloud_pc_bridge --once
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

Read the result from `pc_bridge/results/<job_id>.json` on `pc-bridge`. A request is claimed by a durable `pc_bridge/started/<job_id>.json` marker before it runs. If a started job has no result after 30 minutes, or its start marker is unreadable or invalid, the bridge records `UNCERTAIN` and never replays it.

`UNCERTAIN` is not proof that the action failed: a crash can occur before the action starts, during it, or after it completes but before the result is saved. Inspect the actual outcome before submitting a new ID, because a new ID can repeat side effects. There is still no local result cache or automatic replay after a crash.

`--once` exits **0** for a returned `IDLE` or `DONE` with `ok: true`, **1** for an unsuccessful job outcome (`FAILED`, `INVALID_REQUEST`, `UNCERTAIN`, or `RESULT_TOO_LARGE`), and **2** for a bridge or platform error. These exit codes describe the one-shot poll, not the completion of all queued work. Continue to read the private result file for the job's durable outcome.

Jobs are processed one at a time. Request JSON is limited to 256 KiB; a returned result is limited to 512 KiB. Oversized results return a size and SHA-256 receipt so the cloud caller can ask for a narrower extract.

## Data and resource behavior

- Job requests, start markers, and results stay on the private `pc-bridge` branch. No local clone, worktree, log, or result cache is created.
- The bridge uses GitHub's existing private-repository access on both ends. It does not create, print, or copy a token.
- Idle operation is one small Python process and a periodic GitHub poll. No Cursor, Devin, Codex, or other model harness is launched.
- The bridge calls TITAN Hands in the current user session; normal TITAN Hands capabilities remain available.
