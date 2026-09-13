#!/usr/bin/env python3
"""Run a reviewed command plan against one exact clean Git commit and emit evidence.

This is an execution-receipt substrate for cloud workers when hosted CI is
unavailable. It is intentionally not a sandbox and never claims to prevent
network/provider side effects. Plans must therefore contain test/validation
commands only and remain subject to human/source review.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath, PureWindowsPath
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from typing import Any
from urllib.parse import urlparse

PLAN_SCHEMA = "commons-exact-head-exec-plan/v1"
RECEIPT_SCHEMA = "commons-exact-head-exec-receipt/v1"
MAX_COMMANDS = 64
MAX_TIMEOUT_SECONDS = 3600.0


class ReceiptError(RuntimeError):
    pass


def _sha256_bytes(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _git(root: Path, *args: str, text: bool = True) -> str | bytes:
    done = subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
        text=text,
    )
    return done.stdout


def _valid_sha(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 40
        and all(ch in "0123456789abcdefABCDEF" for ch in value)
    )


def _strict_json(path: Path) -> tuple[dict[str, Any], str]:
    raw = path.read_bytes()

    def pairs(rows):
        out = {}
        for key, value in rows:
            if key in out:
                raise ReceiptError(f"duplicate JSON key: {key}")
            out[key] = value
        return out
    try:
        obj = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=pairs,
            parse_constant=lambda value: (_ for _ in ()).throw(
                ReceiptError(f"non-standard JSON constant: {value}")
            ),
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ReceiptError(f"invalid plan JSON: {exc}") from exc
    if not isinstance(obj, dict):
        raise ReceiptError("plan root must be an object")
    return obj, _sha256_bytes(raw)


def _validate_rel_cwd(value: Any) -> str:
    if value is None:
        return "."
    if not isinstance(value, str) or not value or "\x00" in value:
        raise ReceiptError("command cwd must be a non-empty string")
    if value == ".":
        return value
    posix = PurePosixPath(value)
    windows = PureWindowsPath(value)
    lexical = value.replace("\\", "/").split("/")
    if (
        posix.is_absolute()
        or windows.is_absolute()
        or windows.drive
        or any(part in ("", ".", "..") for part in lexical)
    ):
        raise ReceiptError(f"unsafe command cwd: {value}")
    return value


def _validate_plan(plan: dict[str, Any], expected_head: str) -> list[dict[str, Any]]:
    if plan.get("schema") != PLAN_SCHEMA:
        raise ReceiptError(f"plan schema must be {PLAN_SCHEMA}")
    if plan.get("head_sha") != expected_head:
        raise ReceiptError("plan head_sha does not equal external expected head")
    repo = plan.get("repo")
    if not isinstance(repo, str) or repo.count("/") != 1 or any(not part for part in repo.split("/")):
        raise ReceiptError("plan repo must be OWNER/NAME")
    commands = plan.get("commands")
    if not isinstance(commands, list) or not commands or len(commands) > MAX_COMMANDS:
        raise ReceiptError(f"commands must contain 1..{MAX_COMMANDS} entries")
    seen: set[str] = set()
    normalized: list[dict[str, Any]] = []
    for index, row in enumerate(commands):
        if not isinstance(row, dict):
            raise ReceiptError(f"command {index} must be an object")
        ident = row.get("id")
        if not isinstance(ident, str) or not ident.strip() or len(ident) > 80:
            raise ReceiptError(f"command {index} has invalid id")
        if ident in seen:
            raise ReceiptError(f"duplicate command id: {ident}")
        seen.add(ident)
        argv = row.get("argv")
        if (
            not isinstance(argv, list)
            or not argv
            or len(argv) > 128
            or any(not isinstance(arg, str) or "\x00" in arg for arg in argv)
        ):
            raise ReceiptError(f"command {ident} argv must be a non-empty string list")
        timeout = row.get("timeout_seconds", 600)
        if type(timeout) not in (int, float) or not math.isfinite(timeout) or timeout <= 0 or timeout > MAX_TIMEOUT_SECONDS:
            raise ReceiptError(f"command {ident} timeout_seconds must be in (0,{MAX_TIMEOUT_SECONDS}]")
        normalized.append({
            "id": ident,
            "argv": argv,
            "cwd": _validate_rel_cwd(row.get("cwd", ".")),
            "timeout_seconds": float(timeout),
        })
    unknown = set(plan) - {"schema", "repo", "head_sha", "commands", "notes"}
    if unknown:
        raise ReceiptError("unknown plan keys: " + ", ".join(sorted(unknown)))
    return normalized


def _repo_from_origin(root: Path) -> str:
    """Return canonical OWNER/NAME without ever returning remote credentials."""
    try:
        raw = str(_git(root, "config", "--get", "remote.origin.url")).strip()
    except subprocess.CalledProcessError as exc:
        raise ReceiptError("checkout has no remote.origin.url") from exc
    if raw.startswith("git@github.com:"):
        path = raw[len("git@github.com:"):]
    else:
        parsed = urlparse(raw)
        if parsed.scheme not in ("https", "ssh") or parsed.hostname != "github.com":
            raise ReceiptError("origin must name github.com over HTTPS or SSH")
        path = parsed.path.lstrip("/")
    if path.endswith(".git"):
        path = path[:-4]
    if path.count("/") != 1 or any(not part for part in path.split("/")):
        raise ReceiptError("origin does not name one GitHub OWNER/NAME repository")
    return path


def _checkout_state(root: Path) -> dict[str, Any]:
    head = str(_git(root, "rev-parse", "--verify", "HEAD^{commit}")).strip().lower()
    tree = str(_git(root, "rev-parse", "HEAD^{tree}")).strip().lower()
    porcelain = bytes(_git(root, "status", "--porcelain=v1", "--untracked-files=all", "-z", text=False))
    ignored = bytes(_git(root, "ls-files", "--others", "--ignored", "--exclude-standard", "-z", text=False))
    staged = bytes(_git(root, "ls-files", "--stage", "-z", text=False))
    special: list[dict[str, str]] = []
    symlinks: list[str] = []
    for entry in staged.split(b"\0"):
        if not entry:
            continue
        meta, path = entry.split(b"\t", 1)
        mode, _object_sha, stage = meta.split()
        decoded = path.decode("utf-8", "surrogateescape")
        if stage != b"0":
            special.append({"path": decoded, "kind": "unmerged-index"})
        elif mode == b"120000":
            symlinks.append(decoded)
        elif mode == b"160000":
            special.append({"path": decoded, "kind": "gitlink"})
    unsafe_symlinks: list[str] = []
    for rel in symlinks:
        link = root / rel
        try:
            resolved = link.resolve(strict=True)
            resolved.relative_to(root)
        except (OSError, ValueError):
            unsafe_symlinks.append(rel)
    return {
        "head_sha": head,
        "tree_sha": tree,
        "worktree_dirty": bool(porcelain),
        "ignored_entry_count": sum(1 for item in ignored.split(b"\0") if item),
        "tracked_symlink_count": len(symlinks),
        "unsafe_tracked_symlinks": unsafe_symlinks,
        "special_entries": special,
    }


def _assert_safe_checkout(root: Path, expected_head: str, expected_repo: str) -> dict[str, Any]:
    state = _checkout_state(root)
    repo = _repo_from_origin(root)
    if repo.casefold() != expected_repo.casefold():
        raise ReceiptError(f"checkout origin repo {repo} != plan repo {expected_repo}")
    state["repo"] = repo
    if state["head_sha"] != expected_head.lower():
        raise ReceiptError(f"checkout head {state['head_sha']} != expected {expected_head.lower()}")
    if state["worktree_dirty"]:
        raise ReceiptError("checkout is dirty or has untracked files")
    if state["ignored_entry_count"]:
        raise ReceiptError("checkout contains ignored files; runtime inputs are ambiguous")
    if state["unsafe_tracked_symlinks"]:
        raise ReceiptError("checkout contains tracked symlink(s) escaping or missing inside the checkout")
    if state["special_entries"]:
        kinds = sorted({row["kind"] for row in state["special_entries"]})
        raise ReceiptError("checkout contains unsupported special entries: " + ",".join(kinds))
    return state


def _safe_env(home: Path) -> dict[str, str]:
    env: dict[str, str] = {}
    for key in ("PATH", "LANG", "LC_ALL", "LC_CTYPE", "TZ", "SYSTEMROOT", "WINDIR", "PATHEXT"):
        value = os.environ.get(key)
        if value:
            env[key] = value
    env.update({
        "HOME": str(home),
        "USERPROFILE": str(home),
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_TERMINAL_PROMPT": "0",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONHASHSEED": "0",
        "CI": "true",
    })
    return env


def _prepare_commands(root: Path, commands: list[dict[str, Any]], env: dict[str, str]) -> list[dict[str, Any]]:
    prepared: list[dict[str, Any]] = []
    for command in commands:
        cwd = (root / command["cwd"]).resolve()
        try:
            cwd.relative_to(root)
        except ValueError as exc:
            raise ReceiptError(f"command cwd escapes checkout: {command['cwd']}") from exc
        if not cwd.is_dir() or cwd.is_symlink():
            raise ReceiptError(f"command cwd is not an ordinary directory: {command['cwd']}")
        executable = command["argv"][0]
        if os.path.isabs(executable):
            resolved = Path(executable).resolve()
            if not resolved.is_file():
                raise ReceiptError(f"command executable is not an ordinary file: {executable}")
        else:
            found = shutil.which(executable, path=env.get("PATH"))
            if not found:
                raise ReceiptError(f"command executable not found on sanitized PATH: {executable}")
            resolved = Path(found).resolve()
            if not resolved.is_file():
                raise ReceiptError(f"resolved command executable is not an ordinary file: {resolved}")
        prepared.append({
            **command,
            "_cwd_path": cwd,
            "_exec_path": resolved,
            "_exec_sha256": _sha256_file(resolved),
        })
    return prepared


def _run_one(command: dict[str, Any], log_dir: Path, env: dict[str, str]) -> dict[str, Any]:
    cwd = command["_cwd_path"]
    stdout_path = log_dir / (command["id"] + ".stdout")
    stderr_path = log_dir / (command["id"] + ".stderr")
    started = time.monotonic()
    timed_out = False
    launch_error = None
    code = 127
    argv = [str(command["_exec_path"]), *command["argv"][1:]]
    with stdout_path.open("wb") as out, stderr_path.open("wb") as err:
        try:
            proc = subprocess.Popen(
                argv, cwd=cwd, env=env,
                stdin=subprocess.DEVNULL, stdout=out, stderr=err,
                start_new_session=(os.name == "posix"),
            )
            try:
                code = proc.wait(timeout=command["timeout_seconds"])
            except subprocess.TimeoutExpired:
                timed_out = True
                if os.name == "posix":
                    try:
                        os.killpg(proc.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                else:
                    proc.kill()
                proc.wait()
                code = 124
        except OSError as exc:
            launch_error = f"{type(exc).__name__}: {exc}"
            code = 127
    elapsed = time.monotonic() - started
    return {
        "id": command["id"],
        "argv": command["argv"],
        "cwd": command["cwd"],
        "resolved_executable": str(command["_exec_path"]),
        "executable_sha256": command["_exec_sha256"],
        "timeout_seconds": command["timeout_seconds"],
        "exit_code": code,
        "timed_out": timed_out,
        "launch_error": launch_error,
        "elapsed_seconds": round(elapsed, 6),
        "stdout": {"sha256": _sha256_file(stdout_path), "bytes": stdout_path.stat().st_size},
        "stderr": {"sha256": _sha256_file(stderr_path), "bytes": stderr_path.stat().st_size},
    }


def execute_plan(root: Path, plan_path: Path, expected_head: str) -> tuple[dict[str, Any], int]:
    if not _valid_sha(expected_head):
        raise ReceiptError("expected head must be 40 hex characters")
    root = root.resolve()
    if not (root / ".git").exists():
        # rev-parse below is authority, but this yields a clearer error for plain dirs.
        raise ReceiptError("root is not a Git worktree")
    plan, plan_sha = _strict_json(plan_path)
    commands = _validate_plan(plan, expected_head.lower())
    before = _assert_safe_checkout(root, expected_head, plan["repo"])
    receipt: dict[str, Any] = {
        "schema": RECEIPT_SCHEMA,
        "repo": plan["repo"],
        "expected_head_sha": expected_head.lower(),
        "checkout": before,
        "plan_sha256": plan_sha,
        "safety": {
            "hosted_ci_replacement_claimed": False,
            "network_isolation_enforced": False,
            "external_side_effects_prevented": False,
            "environment_allowlisted": True,
            "checkout_mutation_detected": False,
            "transient_checkout_mutation_prevented": False,
            "command_executables_hash_bound": True,
        },
        "commands": [],
        "conclusion": "FAILED",
    }
    with tempfile.TemporaryDirectory(prefix="exact-head-exec-logs-") as td, tempfile.TemporaryDirectory(prefix="exact-head-exec-home-") as hd:
        log_dir, home = Path(td), Path(hd)
        env = _safe_env(home)
        prepared = _prepare_commands(root, commands, env)
        all_ok = True
        for command in prepared:
            result = _run_one(command, log_dir, env)
            receipt["commands"].append(result)
            try:
                after = _assert_safe_checkout(root, expected_head, plan["repo"])
            except ReceiptError as exc:
                receipt["safety"]["checkout_mutation_detected"] = True
                receipt["mutation_error"] = str(exc)
                all_ok = False
                break
            if after["tree_sha"] != before["tree_sha"] or result["exit_code"] != 0:
                all_ok = False
                if result["exit_code"] != 0:
                    break
        receipt["conclusion"] = "PASSED" if all_ok and len(receipt["commands"]) == len(commands) else "FAILED"
    return receipt, 0 if receipt["conclusion"] == "PASSED" else 1


def _write_exclusive(path: Path, body: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    try:
        view = memoryview(body)
        while view:
            n = os.write(fd, view)
            if n <= 0:
                raise OSError("short write")
            view = view[n:]
        os.fsync(fd)
    finally:
        os.close(fd)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--expected-head", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    root = args.root.resolve()
    out = args.out.resolve()
    try:
        out.relative_to(root)
    except ValueError:
        pass
    else:
        parser.error("--out must be outside the tested checkout")
    try:
        receipt, code = execute_plan(root, args.plan, args.expected_head)
    except (ReceiptError, OSError, subprocess.CalledProcessError) as exc:
        receipt = {
            "schema": RECEIPT_SCHEMA,
            "expected_head_sha": args.expected_head.lower() if isinstance(args.expected_head, str) else None,
            "conclusion": "PRECHECK_FAILED",
            "error": str(exc),
            "safety": {
                "hosted_ci_replacement_claimed": False,
                "network_isolation_enforced": False,
                "external_side_effects_prevented": False,
            },
        }
        code = 2
    body = (json.dumps(receipt, sort_keys=True, indent=2, ensure_ascii=True) + "\n").encode("utf-8")
    try:
        _write_exclusive(out, body)
    except FileExistsError:
        print("refusing to overwrite existing receipt", file=sys.stderr)
        return 2
    print(receipt["conclusion"])
    return code

if __name__ == "__main__":
    raise SystemExit(main())
