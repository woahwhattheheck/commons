# SPDX-License-Identifier: Apache-2.0
"""Challenger registration for the TITAN v3 adversarial league.

A challenger is registered by writing one JSON file per challenger under
``league/challengers/<name>.json``.  The weekly runner only plays
registrations that validate and are marked ``active``.  Registration
records the entrypoint SHA-256 at registration time; the runner re-hashes
at staging time and refuses to play a challenger whose entrypoint moved.

Schema::

    {
      "name": "v3-final-crop-binding",
      "entry": "candidates/v3-final-crop-binding/candidate_main.py",
      "callable": "agent",
      "support_modules": [
        "cloud-runtime-pulse/observed_clone.py",
        "cloud-quickstep/seller_snapshot.py"
      ],
      "sha256": "<entry file sha256 at registration>",
      "registered": "2026-09-10",
      "active": true,
      "notes": "..."
    }

Paths are relative to ``revenue/kaggriculture/``.  ``support_modules``
are plain sibling sources the candidate's import chain needs at
act-time (the evaluator's worker processes run with a stripped
environment and a bare cwd, so anything outside the candidate dir and
the lab root must be staged explicitly).  Support files are copied
verbatim into the run staging dir; their SHA-256 is recorded in the run
report for provenance.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import date
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
LAB = HERE.parent
REPO_ROOT = LAB.parent  # revenue/kaggriculture/

NAME_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{1,63}$")


class RegistrationError(ValueError):
    """Raised when a challenger registration is invalid."""


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_registration(data: dict[str, Any]) -> dict[str, Any]:
    """Validate a registration dict; return a normalized copy.

    Checks: name pattern, entry exists under the repo, callable name is a
    plain identifier, support modules exist, sha256 matches the entry file.
    Raises RegistrationError on any problem.
    """
    if not isinstance(data, dict):
        raise RegistrationError("registration must be a JSON object")
    name = data.get("name")
    if not isinstance(name, str) or not NAME_RE.match(name):
        raise RegistrationError(f"name must match {NAME_RE.pattern}, got {name!r}")
    entry = data.get("entry")
    if not isinstance(entry, str) or not entry or ".." in Path(entry).parts or Path(entry).is_absolute():
        raise RegistrationError(f"entry must be a repo-relative path, got {entry!r}")
    entry_path = (REPO_ROOT / entry).resolve()
    try:
        entry_path.relative_to(REPO_ROOT.resolve())
    except ValueError:
        raise RegistrationError(f"entry escapes the repo root: {entry!r}")
    if not entry_path.is_file():
        raise RegistrationError(f"entry file not found: {entry}")
    callable_name = data.get("callable", "agent")
    if not isinstance(callable_name, str) or not callable_name.isidentifier():
        raise RegistrationError(f"callable must be an identifier, got {callable_name!r}")
    support = data.get("support_modules", [])
    if not isinstance(support, list) or any(not isinstance(s, str) for s in support):
        raise RegistrationError("support_modules must be a list of strings")
    for module in support:
        module_path = (REPO_ROOT / module).resolve()
        try:
            module_path.relative_to(REPO_ROOT.resolve())
        except ValueError:
            raise RegistrationError(f"support module escapes the repo root: {module!r}")
        if not module_path.is_file():
            raise RegistrationError(f"support module not found: {module}")
    recorded = data.get("sha256")
    actual = sha256_file(entry_path)
    if recorded is not None and recorded != actual:
        raise RegistrationError(
            f"entry sha256 mismatch for {name}: registered {recorded}, now {actual}")
    normalized = dict(data)
    normalized["sha256"] = actual
    return normalized


def register_challenger(registry_dir: str | Path, name: str, entry: str,
                        callable_name: str = "agent",
                        support_modules: list[str] | None = None,
                        notes: str = "", force: bool = False) -> Path:
    """Create (or refresh) a challenger registration file.  Returns its path."""
    registry_dir = Path(registry_dir)
    data = validate_registration({
        "name": name,
        "entry": entry,
        "callable": callable_name,
        "support_modules": support_modules or [],
        "registered": date.today().isoformat(),
        "active": True,
        "notes": notes,
    })
    registry_dir.mkdir(parents=True, exist_ok=True)
    path = registry_dir / f"{name}.json"
    if path.exists() and not force:
        raise RegistrationError(f"{path} exists; pass force=True to re-register")
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
    return path


def load_registry(registry_dir: str | Path) -> list[dict[str, Any]]:
    """Load and validate every registration; return the active ones sorted by name."""
    registry_dir = Path(registry_dir)
    active: list[dict[str, Any]] = []
    if not registry_dir.is_dir():
        return active
    for path in sorted(registry_dir.glob("*.json")):
        data = json.loads(path.read_text())
        normalized = validate_registration(data)  # re-hashes; drift fails closed
        if normalized.get("active", True):
            active.append(normalized)
    active.sort(key=lambda item: item["name"])
    return active


def check_entrypoint_callable(entry: str, callable_name: str = "agent",
                              support_modules: list[str] | None = None) -> None:
    """Import the entry file in-process and verify the named callable exists.

    Mirrors what the league runner's generated bootstrap does (support
    modules first on sys.path, then the entry file by path).  Raises
    RegistrationError when the import fails or the callable is missing.
    Candidate modules are executable code: run this in an isolated
    container, same as the evaluator itself.
    """
    import importlib.util
    import tempfile
    entry_path = (REPO_ROOT / entry).resolve()
    with tempfile.TemporaryDirectory(prefix="league-register-") as staging:
        support_dir = Path(staging) / "support"
        support_dir.mkdir()
        for module in support_modules or []:
            source = (REPO_ROOT / module).resolve()
            (support_dir / source.name).write_bytes(source.read_bytes())
        sys.path.insert(0, str(support_dir))
        sys.path.insert(0, str(entry_path.parent))
        try:
            module_name = "_league_registration_probe"
            spec = importlib.util.spec_from_file_location(module_name, entry_path)
            if spec is None or spec.loader is None:
                raise RegistrationError(f"cannot import {entry}")
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
        except RegistrationError:
            raise
        except BaseException as exc:
            raise RegistrationError(
                f"entry import failed for {entry}: {type(exc).__name__}: {exc}") from exc
        finally:
            sys.path.remove(str(entry_path.parent))
            sys.path.remove(str(support_dir))
            sys.modules.pop(module_name, None)
        target = getattr(module, callable_name, None)
        if not callable(target):
            raise RegistrationError(f"{entry} has no callable {callable_name!r}")


def main(argv: list[str] | None = None) -> int:
    import argparse
    parser = argparse.ArgumentParser(description="Register a league challenger")
    parser.add_argument("--name", required=True)
    parser.add_argument("--entry", required=True,
                        help="repo-relative path under revenue/kaggriculture/")
    parser.add_argument("--callable", default="agent")
    parser.add_argument("--support", action="append", default=[],
                        help="repo-relative support module; repeatable")
    parser.add_argument("--notes", default="")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--check", action="store_true",
                        help="also import the entrypoint and verify the callable")
    parser.add_argument("--registry", default=str(HERE / "challengers"))
    args = parser.parse_args(argv)
    try:
        path = register_challenger(args.registry, args.name, args.entry,
                                   args.callable, args.support, args.notes, args.force)
        if args.check:
            check_entrypoint_callable(args.entry, args.callable, args.support)
        print(f"registered {args.name} -> {path}")
        return 0
    except RegistrationError as exc:
        print(f"registration failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
