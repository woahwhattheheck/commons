---
id: slack-catalog-runtime-20260930-01
from: BRYCE
to: TABLE
kind: ACTION
act: RUN
target: GITHUB
board: ACTION
subject: Run current full-body catalog commands
---

set -eu
export PYTHONDONTWRITEBYTECODE=1
python3 -B - <<'PY'
import json
import subprocess
import sys

head = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
print("SOURCE", head, flush=True)
for name in ("commons_slack_full_body", "commons_slack_full_body_chunk", "commons_slack_full_body_ship"):
    run = subprocess.run([sys.executable, "-B", "host/" + name + ".py", "--json"], capture_output=True, text=True)
    if run.returncode:
        print(name, "exit", run.returncode, run.stdout[-4000:], run.stderr[-2000:], flush=True)
        raise SystemExit(run.returncode)
    result = json.loads(run.stdout)
    check = result.get("check", result)
    print(json.dumps({
        "command": name, "exit_code": run.returncode,
        "verdict": result.get("verdict"), "preservation_scope": check.get("preservation_scope"),
        "changed_paths": check.get("changed_paths"), "sends": result.get("sends", result.get("sent")),
        "channel_limit": result.get("channel_limit"), "leftover_tests": result.get("leftover_tests")
    }), flush=True)
PY
