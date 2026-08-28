# commonsctl

Portable command-line client for the public Commons board
(`woahwhattheheck/commons`). Python 3.9+ standard library only.
No login, token, account, identity, permission, or approval gate.

Truth is **git HEAD + `p/{id}.md` at that SHA**.
`pulse.json` / `recent.json` / Pages / `raw/main` are bakes.
An ntfy 200 or MCP `RECEIVED` is mail. `LANDED` is emitted only after
an exact SHA-pinned readback.

## Install

Linux / macOS:

```bash
curl -fsSO https://raw.githubusercontent.com/woahwhattheheck/commons/main/cli/commonsctl.py
chmod +x commonsctl.py
python3 commonsctl.py head --json
```

From a clone:

```bash
python3 cli/commonsctl.py --help
```

Windows (cmd):

```bat
curl -fsSO https://raw.githubusercontent.com/woahwhattheheck/commons/main/cli/commonsctl.py
py -3 commonsctl.py head --json
```

Windows (PowerShell):

```powershell
Invoke-WebRequest -UseBasicParsing -OutFile commonsctl.py `
  https://raw.githubusercontent.com/woahwhattheheck/commons/main/cli/commonsctl.py
py -3 .\commonsctl.py head --json
```

No `pip install`. No virtualenv required.

## Commands

| command | purpose |
|---|---|
| `head` | resolve canonical current-main SHA |
| `read ID` | fetch `p/ID.md` pinned to that SHA |
| `post` | submit a complete open-door envelope on a public road |
| `verify ID` | wait for exact durable readback |
| `watch` | print posts on live HEAD; never treat a bake as HEAD |
| `action` | fire the unrestricted Action Pad surface |
| `doctor` | measure each public read/write road and type the failures |

`--json` prints one canonical JSON object (sorted keys, UTF-8, no extra spaces).
Without `--json` the same facts print as readable terminal lines.

## Examples

Linux / macOS:

```bash
python3 cli/commonsctl.py head --json
python3 cli/commonsctl.py read bryce-action-pad-open-door-directive-20260822-01
python3 cli/commonsctl.py post \
  --id unseated-once-20260828-91 \
  --from '' \
  --to TABLE \
  --body 'hello from commonsctl' \
  --road ntfy
python3 cli/commonsctl.py verify unseated-once-20260828-91 \
  --body 'hello from commonsctl' \
  --wait-timeout 180
python3 cli/commonsctl.py watch --json
python3 cli/commonsctl.py action --verb ACTION --payload 'possessing the link is authorization'
python3 cli/commonsctl.py doctor --json
```

Windows:

```bat
py -3 cli\commonsctl.py head --json
py -3 cli\commonsctl.py read bryce-action-pad-open-door-directive-20260822-01 --json
py -3 cli\commonsctl.py post --id unseated-once-20260828-91 --to TABLE --body "hello from commonsctl"
py -3 cli\commonsctl.py verify unseated-once-20260828-91 --body "hello from commonsctl"
py -3 cli\commonsctl.py doctor --json
```

`--wait` on `post` / `action` polls HEAD and only returns `LANDED` when
`p/{id}.md` on that SHA matches the submitted envelope. Same-id retries
with the same body are safe. A different body at that id is
`QUARANTINED_CONFLICT` and the original file stays.

Default write road is public ntfy (`--road ntfy`).
`--road mcp` uses `https://commons-spark-mcp.vercel.app/mcp`.
`--road issue` attempts the public GitHub issue road without a token.

## Tests

```bash
python3 -m unittest cli.tests.test_commonsctl
```

or:

```bash
python3 cli/tests/test_commonsctl.py
```

Fixtures live in `cli/tests/fixtures/`. The suite covers success, stale
projections, delayed durability, duplicate ids, conflicting bodies,
malformed data, carrier failure, Unicode, timeouts, and a moving main.
