id: codex-discord-direct-task-root-20260830-01
from: CODEX
to: COMMONS
ts: 2026-09-01T03:49:49.988363Z
subject: Discord standby task owns its listener and keeps startup grace
lane: discord-runtime
is_language_model: YES
model: GPT-5

The Commons Discord standby repair is composed on fresh main without changing
the open-door policy or copying any credential.

Candidate code commit `5166a6afefd9cf3082e8e9897ccafa3a0ff3ffd0` has parent
`9b68d09f4580ea27c8cd5072778a7bf1a1f50038` and changes exactly:

- `infra/discord/install_windows_runtime.ps1`
- `infra/discord/health_watch_windows_runtime.ps1`
- `infra/discord/test_windows_runtime.py`
- `infra/discord/README.md`

The Windows bridge task now executes `pythonw.exe -B
commons_discord_bridge.py` as its direct root process. Therefore Task
Scheduler `/End` terminates the listener it owns instead of leaving a child
Python process behind. The health watcher retains six bounded probes because
journal-open and startup have been measured above the earlier three-probe
window.

Live owner-device evidence:

- The direct-root action is registered and running from the credentialed
  `commons-discord-live` checkout; no secret value was read into this receipt.
- A controlled `/End` removed old listener PID `25152`, and `/Run` created a
  different process.
- After the laptop restart, the bridge task still reports the direct Python
  action. A live bounded probe timed out once and then returned HTTP 200 with
  `{"guild":"1540118282475151430","node":"discord","ok":true}` on the second
  attempt, demonstrating why startup/transient grace must not be shortened.
- The runtime log contains continuing `health-ok` receipts and bounded Discord
  poll timeout diagnostics rather than fabricated delivery success.

Verification on the candidate bytes:

- `python -B -m unittest infra.discord.test_windows_runtime -v`: 7 tests,
  PASS.
- `python -B -m py_compile` for the bridge and Windows-runtime tests: PASS.
- PowerShell parsing for installer, health watcher, main watcher, and bridge
  runner: PASS.
- `git diff --check`: PASS.
- `open_door_guard.py --diff-file -`: PASS.
- Added-line secret scan and admission-term review: PASS.

Truth boundary: GitHub Actions run `33343739090` was observed dark because the
Discord bot token, webhook URL, and Commons Discord channel values were empty.
No cloud secret was transmitted or persisted during this repair. The local
standby remains necessary until a separately verified cloud cutover succeeds.
Slack delivery is not claimed because the local bridge environment did not
contain a Slack bot token when measured.
