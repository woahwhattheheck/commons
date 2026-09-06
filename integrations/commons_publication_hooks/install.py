"""Install publication hooks into existing client config, without a daemon."""
from __future__ import annotations
import argparse
import json
import shutil
import sys
from pathlib import Path


def install(config_dir: Path, *, claude: bool = False) -> dict:
    source = Path(__file__).resolve().parent
    repo = source.parents[1]
    destination = config_dir / "commons-publication-hooks"
    destination.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source / "hook.py", destination / "hook.py")
    shutil.copy2(repo / "commons_publication_policy.py", destination / "commons_publication_policy.py")
    path = config_dir / ("settings.json" if claude else "hooks.json")
    config = json.loads(path.read_text(encoding="utf-8-sig")) if path.exists() else {}
    if claude and config.get("disableAllHooks"):
        # Preserve intentionally disabled existing hooks without waking them.
        backup = config_dir / "commons-publication-hooks" / "previous-disabled-hooks.json"
        if not backup.exists():
            backup.write_text(json.dumps({"disableAllHooks": True, "hooks": config.get("hooks", {})}, indent=2), encoding="utf-8")
        config["hooks"] = {}
        config["disableAllHooks"] = False
    hooks = config.setdefault("hooks", {})
    command = f'"{sys.executable}" "{destination / "hook.py"}"'
    for event in ("SessionStart", "UserPromptSubmit", "PreToolUse"):
        groups = hooks.setdefault(event, [])
        if not any("commons-publication-hooks" in str(handler.get("command", ""))
                   for group in groups for handler in group.get("hooks", [])):
            group = {"hooks": [{"type": "command", "command": command, "timeout": 5}]}
            if event == "PreToolUse":
                group["matcher"] = ".*"
            groups.append(group)
    temporary = path.with_suffix(path.suffix + ".commons-publication.tmp")
    temporary.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)
    return {"config": str(path), "hook": str(destination / "hook.py"), "daemon": False}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config-dir", type=Path, required=True)
    parser.add_argument("--claude", action="store_true")
    args = parser.parse_args()
    print(json.dumps(install(args.config_dir, claude=args.claude)))
