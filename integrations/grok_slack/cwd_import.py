"""Load integrations.grok_executor_queue when bridge.py is launched as a script.

Task Scheduler can run integrations/grok_slack/bridge.py with an empty
WorkingDirectory. sys.path then starts at this directory and the package
name integrations is missing. Prefer COMMONS_GROK_SLACK_GIT_ROOT, then
__file__. Only a directory that contains integrations/grok_executor_queue.py
is used. Cwd is never inserted. No auth.
"""
from __future__ import annotations

import importlib.util
import os
import sys
import types
from pathlib import Path
from typing import Any

GIT_ROOT_VAR = "COMMONS_GROK_SLACK_GIT_ROOT"


def resolve_materialize_git_root(
    explicit: str | Path | None = None,
    env: dict[str, str] | None = None,
    *,
    bridge_file: str | Path | None = None,
) -> Path:
    if explicit is not None:
        return Path(explicit)
    source = env if env is not None else os.environ
    raw = str(source.get(GIT_ROOT_VAR) or "").strip()
    if raw:
        return Path(raw)
    here = Path(bridge_file).resolve() if bridge_file is not None else Path(__file__).resolve()
    return here.parents[2] if here.name != "cwd_import.py" else here.parents[2]


def ensure_integrations_import_path(
    explicit: str | Path | None = None,
    env: dict[str, str] | None = None,
    *,
    bridge_file: str | Path | None = None,
) -> Path:
    here = Path(bridge_file).resolve() if bridge_file is not None else Path(__file__).resolve()
    root = Path(resolve_materialize_git_root(explicit, env, bridge_file=here)).resolve()
    marker = root / "integrations" / "grok_executor_queue.py"
    if not marker.is_file():
        fallback = here.parents[2]
        fallback_marker = fallback / "integrations" / "grok_executor_queue.py"
        if fallback_marker.is_file():
            root = fallback
            marker = fallback_marker
        else:
            return root
    text = str(root)
    if text not in sys.path:
        sys.path.insert(0, text)
    return root


def load_grok_executor_queue(
    explicit: str | Path | None = None,
    env: dict[str, str] | None = None,
    *,
    bridge_file: str | Path | None = None,
) -> Any:
    here = Path(bridge_file).resolve() if bridge_file is not None else Path(__file__).resolve()
    root = ensure_integrations_import_path(explicit, env, bridge_file=here)
    marker = (root / "integrations" / "grok_executor_queue.py").resolve()
    if not marker.is_file():
        from integrations.grok_executor_queue import GrokExecutorQueue
        return GrokExecutorQueue
    package_dir = str(marker.parent)
    parent = sys.modules.get("integrations")
    paths: list[str] = []
    if parent is not None:
        for item in list(getattr(parent, "__path__", []) or []):
            try:
                paths.append(str(Path(item).resolve()))
            except OSError:
                paths.append(str(item))
    competing = [
        item for item in paths
        if item != package_dir and (Path(item) / "grok_executor_queue.py").is_file()
    ]
    if parent is None or competing:
        parent = types.ModuleType("integrations")
        parent.__path__ = [package_dir]
        parent.__package__ = "integrations"
        sys.modules["integrations"] = parent
    elif package_dir not in paths and hasattr(parent, "__path__"):
        parent.__path__.insert(0, package_dir)
    existing = sys.modules.get("integrations.grok_executor_queue")
    if existing is not None:
        try:
            same = Path(getattr(existing, "__file__", "") or "").resolve() == marker
        except OSError:
            same = False
        if same:
            return existing.GrokExecutorQueue
        sys.modules.pop("integrations.grok_executor_queue", None)
    spec = importlib.util.spec_from_file_location(
        "integrations.grok_executor_queue",
        str(marker),
        submodule_search_locations=[package_dir],
    )
    if spec is None or spec.loader is None:
        from integrations.grok_executor_queue import GrokExecutorQueue
        return GrokExecutorQueue
    module = importlib.util.module_from_spec(spec)
    sys.modules["integrations.grok_executor_queue"] = module
    spec.loader.exec_module(module)
    return module.GrokExecutorQueue
