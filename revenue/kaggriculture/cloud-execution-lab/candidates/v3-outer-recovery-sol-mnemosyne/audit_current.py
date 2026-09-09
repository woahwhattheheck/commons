# SPDX-License-Identifier: Apache-2.0
"""Fail-closed source audit for the outer-deadline continuity seam."""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import stat
from typing import Any

MAX_SOURCE_BYTES = 2_000_000
FILES = {
    "main": Path("main.py"),
    "runtime": Path("titan_runtime.py"),
    "arlene": Path("reference/next-panel/vendor/arlene.py"),
}
SAFE_FIELDS = {
    "_completed_route",
    "_completed_seller_state",
    "_seller_fallback_observations",
}
EXPECTED_DECISION_TURNS = [226, 360, 433]


class AuditError(ValueError):
    pass


def _read_regular(root: Path, relative: Path) -> bytes:
    root = root.resolve(strict=True)
    path = root / relative
    # Reject a symlink in every relative path component before opening the file.
    cursor = root
    for part in relative.parts:
        cursor = cursor / part
        try:
            mode = cursor.lstat().st_mode
        except FileNotFoundError as error:
            raise AuditError(f"missing source: {relative.as_posix()}") from error
        if stat.S_ISLNK(mode):
            raise AuditError(f"symlink source component: {relative.as_posix()}")
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0)
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(path, flags)
    except OSError as error:
        raise AuditError(f"cannot open source: {relative.as_posix()}: {error}") from error
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode):
            raise AuditError(f"non-regular source: {relative.as_posix()}")
        if info.st_size > MAX_SOURCE_BYTES:
            raise AuditError(f"oversized source: {relative.as_posix()}")
        chunks = []
        remaining = MAX_SOURCE_BYTES + 1
        while remaining:
            block = os.read(fd, min(65536, remaining))
            if not block:
                break
            chunks.append(block)
            remaining -= len(block)
        data = b"".join(chunks)
        if len(data) != info.st_size:
            raise AuditError(f"source changed during read: {relative.as_posix()}")
        return data
    finally:
        os.close(fd)


def _parse(name: str, raw: bytes) -> ast.Module:
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as error:
        raise AuditError(f"{name} is not UTF-8") from error
    try:
        return ast.parse(text, filename=name)
    except SyntaxError as error:
        raise AuditError(f"{name} does not parse: {error}") from error


def _dotted(node: ast.AST | None) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        left = _dotted(node.value)
        return f"{left}.{node.attr}" if left else node.attr
    return ""


def _function(tree: ast.AST, name: str, *, owner: str | None = None) -> ast.FunctionDef:
    scope: list[ast.stmt]
    if owner is None:
        scope = getattr(tree, "body", [])
    else:
        classes = [n for n in getattr(tree, "body", []) if isinstance(n, ast.ClassDef) and n.name == owner]
        if len(classes) != 1:
            raise AuditError(f"expected one class {owner}, found {len(classes)}")
        scope = classes[0].body
    matches = [n for n in scope if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == name]
    if len(matches) != 1 or not isinstance(matches[0], ast.FunctionDef):
        raise AuditError(f"expected one function {owner + '.' if owner else ''}{name}, found {len(matches)}")
    return matches[0]


def _is_self_attr(node: ast.AST, name: str) -> bool:
    return isinstance(node, ast.Attribute) and node.attr == name and isinstance(node.value, ast.Name) and node.value.id == "self"


def _audit_main(tree: ast.Module) -> dict[str, Any]:
    agent = _function(tree, "agent")
    handlers = []
    for node in ast.walk(agent):
        if isinstance(node, ast.Try):
            handlers.extend(
                handler for handler in node.handlers
                if _dotted(handler.type) == "deadline.DeadlineExceeded"
            )
    if len(handlers) != 1:
        raise AuditError(f"expected one canonical DeadlineExceeded handler, found {len(handlers)}")
    handler = handlers[0]
    handler_remember_lines = []
    discard_lines = []
    for node in ast.walk(handler):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr == "_remember_seller_fallback" and _dotted(node.func.value) == "instance":
                handler_remember_lines.append(node.lineno)
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            value = node.value
            if isinstance(value, ast.Constant) and value.value is None:
                if any(isinstance(target, ast.Name) and target.id == "_INSTANCE" for target in targets):
                    discard_lines.append(node.lineno)
    if handler_remember_lines:
        raise AuditError(
            "outer deadline handler now records fallback observations; "
            "re-audit candidate ownership before use"
        )
    if len(discard_lines) != 1:
        raise AuditError(f"expected one outer instance discard, found {len(discard_lines)}")

    all_remember_lines = []
    for node in ast.walk(agent):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr == "_remember_seller_fallback" and _dotted(node.func.value) == "instance":
                all_remember_lines.append(node.lineno)
    if len(all_remember_lines) != 1:
        raise AuditError(
            f"expected one live-prelude fallback recorder outside the outer handler, "
            f"found {len(all_remember_lines)}"
        )
    if all_remember_lines[0] >= discard_lines[0]:
        raise AuditError("live-prelude recorder no longer precedes the outer discard seam")
    _function(tree, "_new_instance")
    return {
        "deadline_handler_count": 1,
        "outer_fallback_record_count": 0,
        "live_prelude_fallback_record_line": all_remember_lines[0],
        "instance_discard_line": discard_lines[0],
    }


def _audit_runtime(tree: ast.Module) -> dict[str, Any]:
    init = _function(tree, "__init__", owner="TitanAgent")
    initialized = set()
    for node in ast.walk(init):
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                if isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name) and target.value.id == "self":
                    initialized.add(target.attr)
    missing = sorted(SAFE_FIELDS - initialized)
    if missing:
        raise AuditError(f"TitanAgent no longer initializes safe fields: {missing}")

    initialize = _function(tree, "_initialize", owner="TitanAgent")
    route_restore = False
    seller_restore_call = False
    for node in ast.walk(initialize):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if (
                    isinstance(target, ast.Attribute)
                    and target.attr == "cur"
                    and _dotted(target.value) == "self.controller"
                    and _is_self_attr(node.value, "_completed_route")
                ):
                    route_restore = True
        if isinstance(node, ast.Call) and _dotted(node.func) == "self._restore_seller_state":
            seller_restore_call = True
    if not route_restore:
        raise AuditError("TitanAgent._initialize no longer restores _completed_route")
    if not seller_restore_call:
        raise AuditError("TitanAgent._initialize no longer calls _restore_seller_state")
    _function(tree, "_restore_seller_state", owner="TitanAgent")
    _function(tree, "_remember_seller_fallback", owner="TitanAgent")
    return {
        "safe_fields": sorted(SAFE_FIELDS),
        "route_restore": True,
        "seller_restore": True,
    }


def _assignment_value(tree: ast.Module, name: str) -> ast.AST:
    matches = []
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == name for t in node.targets):
            matches.append(node.value)
    if len(matches) != 1:
        raise AuditError(f"expected one {name} assignment, found {len(matches)}")
    return matches[0]


def _audit_arlene(tree: ast.Module) -> dict[str, Any]:
    decisions = _assignment_value(tree, "DECISIONS")
    if not isinstance(decisions, (ast.Tuple, ast.List)):
        raise AuditError("DECISIONS is not a static sequence")
    turns = []
    for row in decisions.elts:
        if not isinstance(row, (ast.Tuple, ast.List)) or len(row.elts) < 4:
            raise AuditError("DECISIONS has malformed rows")
        try:
            turns.append(int(ast.literal_eval(row.elts[0])))
        except (TypeError, ValueError, SyntaxError) as error:
            raise AuditError("DECISIONS turn is not a literal integer") from error
    if turns != EXPECTED_DECISION_TURNS:
        raise AuditError(f"unexpected route decision turns: {turns}")

    act = _function(tree, "act", owner="Agent")
    exact_turn = False
    commits_target = False
    for node in ast.walk(act):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Eq):
            left, right = node.left, node.comparators[0]
            if { _dotted(left), _dotted(right) } == {"turn", "step"}:
                exact_turn = True
        if isinstance(node, ast.Assign) and _dotted(node.value) == "target":
            if any(_dotted(target) == "self.cur" for target in node.targets):
                commits_target = True
    if not exact_turn or not commits_target:
        raise AuditError("Agent.act no longer has exact-turn route commitment")
    _function(tree, "_switch_ok", owner="Agent")
    return {
        "decision_turns": turns,
        "exact_turn_only": True,
        "commits_target": True,
    }


def audit(root: Path) -> dict[str, Any]:
    raw = {name: _read_regular(root, relative) for name, relative in FILES.items()}
    trees = {name: _parse(name, value) for name, value in raw.items()}
    report = {
        "schema": "titan.outer-recovery.source-audit.v1",
        "status": "PASS",
        "files": {
            name: {
                "path": FILES[name].as_posix(),
                "bytes": len(value),
                "sha256": hashlib.sha256(value).hexdigest(),
            }
            for name, value in sorted(raw.items())
        },
        "main": _audit_main(trees["main"]),
        "runtime": _audit_runtime(trees["runtime"]),
        "arlene": _audit_arlene(trees["arlene"]),
    }
    # Prove the report itself is canonical JSON serializable before returning it.
    json.dumps(report, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        report = audit(args.root)
    except (AuditError, OSError) as error:
        report = {
            "schema": "titan.outer-recovery.source-audit.v1",
            "status": "FAIL",
            "error": str(error),
        }
        rendered = json.dumps(report, sort_keys=True, separators=(",", ":")) + "\n"
        if args.output:
            args.output.write_text(rendered, encoding="utf-8")
        print(rendered, end="")
        return 1
    rendered = json.dumps(report, sort_keys=True, separators=(",", ":")) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
