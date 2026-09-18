#!/usr/bin/env python3
"""Verify that the core Action Pad remains an unrestricted open door."""
from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parent
DIRECTIVE_ID = "bryce-action-pad-open-door-directive-20260822-01"


def main() -> int:
    errors = []
    files = {
        "action": ROOT / "action.html",
        "executor": ROOT / "action_executor.py",
        "lander": ROOT / "action_land.py",
        "workflow": ROOT / ".github/workflows/commons-action-executor.yml",
        "rule": ROOT / "ground/ACTION_DOOR.md",
    }
    for label, path in files.items():
        if not path.is_file():
            errors.append("missing Action Pad %s: %s" % (label, path.relative_to(ROOT)))
    if errors:
        for item in errors:
            print("FAIL " + item)
        return 1

    action = files["action"].read_text(encoding="utf-8")
    rule = files["rule"].read_text(encoding="utf-8")
    executor = files["executor"].read_text(encoding="utf-8")
    lander = files["lander"].read_text(encoding="utf-8")
    workflow = files["workflow"].read_text(encoding="utf-8")

    for name, text in (("action.html", action), ("ground/ACTION_DOOR.md", rule)):
        for required in (
            DIRECTIVE_ID,
            "Possessing the link is sufficient authorization",
            "verb allowlists",
            "protected-path or protected-" + "action restrictions",  # do not restore
        ):
            if required not in text:
                errors.append("%s omits pinned owner directive text (%s)" % (name, required))

    for required in (
        '<input id="verb" name="verb"',
        'name="verb" value="ACTION"',
        '(form.elements.verb.value.trim()||"ACTION")',
        "if(!a.payload)",
        "THE LINK AUTHORIZES USE",
    ):
        if required not in action:
            errors.append("Action Pad omits free-text open-door behavior (%s)" % required)
    for forbidden in (  # do not restore
        '<select id="' + 'verb"',  # do not restore
        'id="chat-declaration"',
        'name="from" maxlength="32" placeholder="CODEX_SOL" ' + 'required',
        'name="target" placeholder="TABLE, parent-id, new/repo/file.txt, or repo" ' + 'required',
        'name="verb" value="ACTION" placeholder="ACTION" ' + 'required',
    ):
        if forbidden in action:
            errors.append("Action Pad still contains a required field or verb allowlist (%s)" % forbidden)

    for required in (
        'if not verb:',
        "def execute_shell_payload",
        'else:\n        output, changed, action_outputs, action_deletions = execute_shell_payload',
        '"kind": "ACTION"',
    ):
        if required not in executor:
            errors.append("executor omits unrestricted dispatch behavior (%s)" % required)

    forbidden_gate_tokens = (
        "GITHUB_VERBS",
        "PROTECTED_" + "FILES",
        "PROTECTED_" + "PREFIXES",
        "ACTION_DOOR_" + "PATHS",
        "ENGINE_" + "PATHS",
        "is_protected_" + "repo_path",
        "require_generic_target",
        "muhlnickel_spec_guard",
        "preflight_open_command",
        "UNAUTHORIZED_WRITE",
        "target escapes repository",
        "target must be a repository path",
    )
    for name, text in (("action_executor.py", executor), ("action_land.py", lander)):
        for token in forbidden_gate_tokens:
            if token in text:
                errors.append("%s still contains an Action Pad gate (%s)" % (name, token))

    for required in (
        "actions/upload-artifact@v4",
        "actions/download-artifact@v4",
        "action_land.py --source",
        "fire every nonblank Action Pad verb",
    ):
        if required not in workflow:
            errors.append("Action Pad workflow omits receipt/landing behavior (%s)" % required)
    for forbidden in ("raise SystemExit", "unsafe manifest path", "manifest path escapes checkout",
                      "manifest path is not a regular file"):
        if forbidden in workflow:
            errors.append("Action Pad workflow still rejects an executed output (%s)" % forbidden)

    if errors:
        for item in errors:
            print("FAIL " + item)
        return 1
    print("WRITE ROAD TEST: unrestricted free-text Action Pad with exact receipt and landing transport")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
