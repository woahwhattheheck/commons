#!/usr/bin/env python3
"""Slack CLI project leftover after the custom-tools install.

Peer install (host/slack_custom_tools_install.py) already writes the Bolt
manifest and locates ~/.slack/bin/slack. Peer 0e6ad49f already installed
the service-tag worker. This module writes the unique Slack CLI project
directory so `slack run` has a cwd after Bryce completes login.

Login stays #needs-bryce. Not a Commons admission gate. Does not remint
peer readback 0e6ad49f / blob 8fcc3d36.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import slack_custom_tools_install as inst


ROOT = Path(__file__).resolve().parent.parent
PROJECT_REL = Path("integrations") / "slack_custom_tools"
PROJECT_DIR = ROOT / PROJECT_REL
SIGNIN_CHANNEL = "#needs-bryce"
SIGNIN_CHANNEL_ID = "C0BRX6EV739"
PEER_INSTALL_RECEIPT = "p/cursor-slack-service-tools-install-20260902-01.md"
PEER_INSTALL_COMMIT = "0e6ad49f"
PEER_INSTALL_BLOB = "8fcc3d36"

HOOKS_JSON = {
    "hooks": {
        "get-hooks": "python3 hooks/get_hooks.py",
        "get-manifest": "python3 hooks/get_manifest.py",
        "start": "python3 app.py",
    }
}

GET_HOOKS_PY = '''#!/usr/bin/env python3
"""Local Slack CLI get-hooks. No npm. Login stays #needs-bryce."""
from __future__ import annotations

import json
import sys

payload = {
    "hooks": {
        "get-manifest": "python3 hooks/get_manifest.py",
        "start": "python3 app.py",
    },
    "config": {
        "protocol-version": ["default"],
        "sdk-managed-connection-enabled": False,
        "watch": {
            "app": {"filter-regex": "\\\\.py$", "paths": ["."]},
            "manifest": {"paths": ["manifest.json"]},
        },
    },
    "runtime": "python",
}

if __name__ == "__main__":
    json.dump(payload, sys.stdout)
    sys.stdout.write("\\n")
'''

GET_MANIFEST_PY = '''#!/usr/bin/env python3
"""Print the local Slack CLI manifest.json (official get-manifest shape)."""
from __future__ import annotations

from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
print((HERE / "manifest.json").read_text(encoding="utf-8"), end="")
'''

APP_PY = '''#!/usr/bin/env python3
"""Slack CLI project entry for Commons Service Tools.

Delegates to host/slack_custom_tools_app.register. Does not remint that
driver. Login stays #needs-bryce. Not a Commons admission gate.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
HOST = ROOT / "host"
if str(HOST) not in sys.path:
    sys.path.insert(0, str(HOST))


def build_app(app_factory):
    from slack_custom_tools_app import register

    app = app_factory(process_before_response=True)
    return register(app)


def main() -> int:
    try:
        from slack_bolt import App
        from slack_bolt.adapter.socket_mode import SocketModeHandler
    except ImportError:
        print("slack-bolt missing; pip install -r requirements.txt", file=sys.stderr)
        return 2
    app = build_app(App)
    token = (
        os.environ.get("SLACK_APP_TOKEN")
        or os.environ.get("SLACK_APP_LEVEL_TOKEN")
        or ""
    )
    if not token:
        print(
            "SLACK_APP_TOKEN unset; Slack CLI login stays #needs-bryce",
            file=sys.stderr,
        )
        return 3
    SocketModeHandler(app, token).start()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''

REQUIREMENTS = """slack-bolt
slack-sdk
slack-cli-hooks
"""

README = """# Commons Service Tools — Slack CLI project

Leftover after `cursor-slack-custom-tools-install-20260902-01`. The installer
already wrote the Bolt manifest and located the public Slack CLI. This
directory is the project `slack run` uses.

Login stays `#needs-bryce` (`C0BRX6EV739`). Not a Commons admission gate.
Do not remint peer readback `0e6ad49f` / blob `8fcc3d36`.

## After Bryce returns the challenge

```bash
python3 host/slack_custom_tools_cli_project.py --status
cd integrations/slack_custom_tools
slack run --org-workspace-grant=all
```

`/svctool facebook post the drop tonight` and `@facebook` still drive
`host/slack_custom_tools_app.py`. Missing provider sessions queue
`#needs-bryce`. Do not paste a password into Slack.
"""

GITIGNORE = """.slack/apps.json
.slack/apps.dev.json
.slack/cache/
.env
__pycache__/
*.pyc
"""

SLACKIGNORE = """.slack/apps.dev.json
.slack/apps.json
.env
__pycache__
"""


def project_dir(root: Path | None = None) -> Path:
    return (root or ROOT) / PROJECT_REL


def run_argv(cli: str) -> list[str]:
    return [cli, "run", "--org-workspace-grant=all"]


def write_project(dest: Path | None = None, catalog_path: Path | None = None) -> Path:
    """Write the Slack CLI project. Compose the manifest; do not remint host/."""
    target = dest or PROJECT_DIR
    target.mkdir(parents=True, exist_ok=True)
    slack_dir = target / ".slack"
    hooks_dir = target / "hooks"
    slack_dir.mkdir(parents=True, exist_ok=True)
    hooks_dir.mkdir(parents=True, exist_ok=True)
    manifest = inst.build_manifest(catalog_path)
    (target / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    (slack_dir / "hooks.json").write_text(
        json.dumps(HOOKS_JSON, indent=2) + "\n", encoding="utf-8"
    )
    (target / "slack.json").write_text(
        json.dumps(HOOKS_JSON, indent=2) + "\n", encoding="utf-8"
    )
    (hooks_dir / "get_hooks.py").write_text(GET_HOOKS_PY, encoding="utf-8")
    (hooks_dir / "get_manifest.py").write_text(GET_MANIFEST_PY, encoding="utf-8")
    (target / "app.py").write_text(APP_PY, encoding="utf-8")
    (target / "requirements.txt").write_text(REQUIREMENTS, encoding="utf-8")
    (target / "README.md").write_text(README, encoding="utf-8")
    (target / ".gitignore").write_text(GITIGNORE, encoding="utf-8")
    (target / ".slackignore").write_text(SLACKIGNORE, encoding="utf-8")
    return target


def project_written(root: Path | None = None) -> bool:
    dest = project_dir(root)
    required = (
        dest / "manifest.json",
        dest / "app.py",
        dest / "slack.json",
        dest / ".slack" / "hooks.json",
        dest / "hooks" / "get_manifest.py",
        dest / "hooks" / "get_hooks.py",
    )
    return all(path.is_file() for path in required)


def status(
    home: str | None = None,
    run: Any = None,
    path_env: str | None = None,
    root: Path | None = None,
) -> dict[str, Any]:
    row = inst.status(home=home, run=run, path_env=path_env)
    dest = project_dir(root)
    written = project_written(root)
    callback = ""
    if written:
        try:
            manifest = json.loads((dest / "manifest.json").read_text(encoding="utf-8"))
            callback = next(iter((manifest.get("functions") or {}).keys()), "")
        except (OSError, json.JSONDecodeError, TypeError):
            callback = ""
    row.update(
        {
            "project": str(dest),
            "project_rel": str(PROJECT_REL).replace("\\", "/"),
            "project_written": written,
            "manifest_callback_id": callback or inst.CALLBACK_ID,
            "slash_command": inst.SLASH_COMMAND,
            "signin_channel": SIGNIN_CHANNEL,
            "signin_channel_id": SIGNIN_CHANNEL_ID,
            "commons_admission": False,
            "peer_not_reminted": [PEER_INSTALL_COMMIT, PEER_INSTALL_BLOB],
            "peer_install_receipt": PEER_INSTALL_RECEIPT,
            "slack_run_cwd": str(dest),
            "slack_run_argv": run_argv(row["cli"] or "slack"),
        }
    )
    if not row.get("logged_in"):
        row["needs_owner_signin"] = True
        row["signin_channel"] = SIGNIN_CHANNEL
        row["signin_channel_id"] = SIGNIN_CHANNEL_ID
    return row


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--status", action="store_true")
    parser.add_argument("--write-project", action="store_true")
    args = parser.parse_args(argv)
    if args.write_project:
        path = write_project()
        print(str(path))
        return 0
    payload = status()
    print(json.dumps(payload, indent=2))
    return 0 if payload.get("project_written") else 2


if __name__ == "__main__":
    raise SystemExit(main())
