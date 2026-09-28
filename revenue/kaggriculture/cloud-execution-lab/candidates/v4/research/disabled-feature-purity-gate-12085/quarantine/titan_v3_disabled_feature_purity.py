#!/usr/bin/env python3
"""Reject Python work that executes before a disabled-feature early return.

Inputs may be Python files, directories, ZIPs, or tar archives. Archives are
scanned in place and never extracted.

Exit codes: 0 clean, 1 violations, 2 input/parse errors.
"""
from __future__ import annotations

import argparse
import ast
import dataclasses
import io
import json
import pathlib
import re
import sys
import tarfile
import tokenize
import zipfile
from collections.abc import Iterable, Iterator, Sequence
from typing import Final

TOOL_VERSION: Final = "1.0.0"
DEFAULT_FLAG_NAMES: Final = ("enable", "enabled")
DEFAULT_ALLOW_MARKER: Final = "titan-purity: allow"
DEFAULT_MAX_MEMBER_BYTES: Final = 8 * 1024 * 1024


class AuditInputError(Exception):
    """An input could not be safely or deterministically audited."""


@dataclasses.dataclass(frozen=True, order=True)
class SourceUnit:
    label: str
    text: str = dataclasses.field(compare=False)


@dataclasses.dataclass(frozen=True, order=True)
class Finding:
    source: str
    line: int
    column: int
    function: str
    guard_line: int
    feature: str
    rule: str
    statement: str

    def as_dict(self) -> dict[str, object]:
        return dataclasses.asdict(self)


@dataclasses.dataclass(frozen=True, order=True)
class ScanError:
    source: str
    line: int
    column: int
    message: str

    def as_dict(self) -> dict[str, object]:
        return dataclasses.asdict(self)


@dataclasses.dataclass(frozen=True)
class ScanResult:
    findings: tuple[Finding, ...]
    errors: tuple[ScanError, ...]
    scanned_sources: int
    guarded_functions: int

    def as_dict(self) -> dict[str, object]:
        return {
            "tool": "titan-disabled-feature-purity",
            "version": TOOL_VERSION,
            "summary": {
                "scanned_sources": self.scanned_sources,
                "guarded_functions": self.guarded_functions,
                "violations": len(self.findings),
                "errors": len(self.errors),
            },
            "findings": [item.as_dict() for item in self.findings],
            "errors": [item.as_dict() for item in self.errors],
        }


def _is_python_name(name: str) -> bool:
    return name.lower().endswith(".py") and not name.endswith("/")


def _decode(data: bytes, label: str) -> str:
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise AuditInputError(f"{label}: not UTF-8 at byte {exc.start}") from exc


def _iter_directory(path: pathlib.Path) -> Iterator[SourceUnit]:
    files = sorted(
        (candidate for candidate in path.rglob("*.py") if candidate.is_file()),
        key=lambda item: item.as_posix(),
    )
    for child in files:
        try:
            yield SourceUnit(child.as_posix(), child.read_text(encoding="utf-8"))
        except (OSError, UnicodeError) as exc:
            raise AuditInputError(f"{child}: {exc}") from exc


def _iter_zip(path: pathlib.Path, limit: int) -> Iterator[SourceUnit]:
    try:
        with zipfile.ZipFile(path) as archive:
            for info in sorted(archive.infolist(), key=lambda item: item.filename):
                if info.is_dir() or not _is_python_name(info.filename):
                    continue
                if info.flag_bits & 0x1:
                    raise AuditInputError(f"{path}!{info.filename}: encrypted member")
                if info.file_size > limit:
                    raise AuditInputError(
                        f"{path}!{info.filename}: member is {info.file_size} bytes; "
                        f"limit is {limit}"
                    )
                label = f"{path.as_posix()}!{info.filename}"
                yield SourceUnit(label, _decode(archive.read(info), label))
    except AuditInputError:
        raise
    except (OSError, zipfile.BadZipFile, RuntimeError) as exc:
        raise AuditInputError(f"{path}: invalid ZIP archive: {exc}") from exc


def _iter_tar(path: pathlib.Path, limit: int) -> Iterator[SourceUnit]:
    try:
        with tarfile.open(path, mode="r:*") as archive:
            for member in sorted(archive.getmembers(), key=lambda item: item.name):
                if not member.isfile() or not _is_python_name(member.name):
                    continue
                if member.size > limit:
                    raise AuditInputError(
                        f"{path}!{member.name}: member is {member.size} bytes; "
                        f"limit is {limit}"
                    )
                handle = archive.extractfile(member)
                if handle is None:
                    raise AuditInputError(f"{path}!{member.name}: unreadable member")
                data = handle.read(limit + 1)
                if len(data) > limit:
                    raise AuditInputError(
                        f"{path}!{member.name}: decompressed member exceeds {limit} bytes"
                    )
                label = f"{path.as_posix()}!{member.name}"
                yield SourceUnit(label, _decode(data, label))
    except AuditInputError:
        raise
    except (OSError, tarfile.TarError) as exc:
        raise AuditInputError(f"{path}: invalid tar archive: {exc}") from exc


def iter_source_units(
    paths: Iterable[str | pathlib.Path],
    *,
    max_member_bytes: int = DEFAULT_MAX_MEMBER_BYTES,
) -> Iterator[SourceUnit]:
    """Yield Python sources in stable order without extracting archives."""
    if max_member_bytes <= 0:
        raise AuditInputError("max_member_bytes must be positive")

    for raw in sorted((pathlib.Path(item).expanduser() for item in paths), key=str):
        if not raw.exists():
            raise AuditInputError(f"{raw}: no such file or directory")
        if raw.is_dir():
            yield from _iter_directory(raw)
        elif not raw.is_file():
            raise AuditInputError(f"{raw}: unsupported input type")
        elif raw.suffix.lower() == ".py":
            try:
                yield SourceUnit(raw.as_posix(), raw.read_text(encoding="utf-8"))
            except (OSError, UnicodeError) as exc:
                raise AuditInputError(f"{raw}: {exc}") from exc
        elif zipfile.is_zipfile(raw):
            yield from _iter_zip(raw, max_member_bytes)
        elif tarfile.is_tarfile(raw):
            yield from _iter_tar(raw, max_member_bytes)
        else:
            raise AuditInputError(
                f"{raw}: expected a Python file, directory, ZIP, or tar archive"
            )


def _dotted_name(node: ast.AST) -> str | None:
    parts: list[str] = []
    current = node
    while isinstance(current, ast.Attribute):
        parts.append(current.attr)
        current = current.value
    if isinstance(current, ast.Name):
        parts.append(current.id)
        return ".".join(reversed(parts))
    return None


def _flag_expr(node: ast.AST, flag_names: frozenset[str]) -> str | None:
    dotted = _dotted_name(node)
    if dotted and dotted.rsplit(".", 1)[-1] in flag_names:
        return dotted
    return None


def _disabled_guard(statement: ast.stmt, flags: frozenset[str]) -> str | None:
    if not isinstance(statement, ast.If) or statement.orelse:
        return None
    body = [item for item in statement.body if not isinstance(item, ast.Pass)]
    if len(body) != 1 or not isinstance(body[0], ast.Return):
        return None

    test = statement.test
    if isinstance(test, ast.UnaryOp) and isinstance(test.op, ast.Not):
        return _flag_expr(test.operand, flags)

    if isinstance(test, ast.Compare) and len(test.ops) == len(test.comparators) == 1:
        op = test.ops[0]
        right = test.comparators[0]
        if not isinstance(op, (ast.Is, ast.Eq)):
            return None
        if isinstance(right, ast.Constant) and right.value is False:
            return _flag_expr(test.left, flags)
        if isinstance(test.left, ast.Constant) and test.left.value is False:
            return _flag_expr(right, flags)
    return None


def _allow_lines(source: str, marker: str) -> frozenset[int]:
    allowed: set[int] = set()
    try:
        for token in tokenize.generate_tokens(io.StringIO(source).readline):
            if token.type == tokenize.COMMENT and marker in token.string:
                allowed.add(token.start[0])
    except (IndentationError, tokenize.TokenError):
        pass
    return frozenset(allowed)


def _statement_allowed(statement: ast.stmt, allowed: frozenset[int]) -> bool:
    start = getattr(statement, "lineno", 0)
    end = getattr(statement, "end_lineno", start)
    return any(line in allowed for line in range(start, end + 1))


def _is_docstring(statement: ast.stmt) -> bool:
    return (
        isinstance(statement, ast.Expr)
        and isinstance(statement.value, ast.Constant)
        and isinstance(statement.value.value, str)
    )


def _contains_effect(node: ast.AST) -> bool:
    effect_types = (
        ast.Call,
        ast.Await,
        ast.Yield,
        ast.YieldFrom,
        ast.NamedExpr,
        ast.ListComp,
        ast.SetComp,
        ast.DictComp,
        ast.GeneratorExp,
    )
    return any(isinstance(child, effect_types) for child in ast.walk(node))


def _local_target(target: ast.AST) -> bool:
    if isinstance(target, ast.Name):
        return True
    if isinstance(target, (ast.Tuple, ast.List)):
        return all(_local_target(item) for item in target.elts)
    return False


def _classify(statement: ast.stmt) -> str | None:
    if _is_docstring(statement) or isinstance(statement, ast.Pass):
        return None
    if isinstance(statement, ast.Assign):
        if not all(_local_target(target) for target in statement.targets):
            return "pre_guard_mutation"
        return "pre_guard_effectful_assignment" if _contains_effect(statement.value) else None
    if isinstance(statement, ast.AnnAssign):
        if not _local_target(statement.target):
            return "pre_guard_mutation"
        if statement.value is not None and _contains_effect(statement.value):
            return "pre_guard_effectful_assignment"
        return None
    if isinstance(statement, ast.Expr):
        return "pre_guard_call" if _contains_effect(statement) else None
    if isinstance(statement, (ast.AugAssign, ast.Delete, ast.Global, ast.Nonlocal)):
        return "pre_guard_mutation"
    if isinstance(statement, (ast.Import, ast.ImportFrom)):
        return "pre_guard_import"
    if isinstance(statement, (ast.Return, ast.Raise, ast.Break, ast.Continue)):
        return "pre_guard_control_flow"
    if isinstance(
        statement,
        (
            ast.If,
            ast.For,
            ast.AsyncFor,
            ast.While,
            ast.With,
            ast.AsyncWith,
            ast.Try,
            ast.Assert,
        ),
    ):
        return "pre_guard_control_flow"
    match_type = getattr(ast, "Match", None)
    if match_type is not None and isinstance(statement, match_type):
        return "pre_guard_control_flow"
    if isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        return "pre_guard_definition"
    return "pre_guard_unknown"


def _excerpt(lines: Sequence[str], statement: ast.stmt) -> str:
    number = getattr(statement, "lineno", 1)
    if not lines or number < 1 or number > len(lines):
        return type(statement).__name__
    return re.sub(r"\s+", " ", lines[number - 1].strip())[:200]


class _Auditor(ast.NodeVisitor):
    def __init__(self, unit: SourceUnit, flags: frozenset[str], marker: str) -> None:
        self.unit = unit
        self.flags = flags
        self.allowed = _allow_lines(unit.text, marker)
        self.lines = unit.text.splitlines()
        self.scope: list[str] = []
        self.findings: list[Finding] = []
        self.guarded_functions = 0

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self.scope.append(node.name)
        self.generic_visit(node)
        self.scope.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._visit_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._visit_function(node)

    def _visit_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        self.scope.append(node.name)
        self._audit(node)
        self.generic_visit(node)
        self.scope.pop()

    def _audit(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        guard_index: int | None = None
        feature: str | None = None
        for index, statement in enumerate(node.body):
            candidate = _disabled_guard(statement, self.flags)
            if candidate is not None:
                guard_index, feature = index, candidate
                break
        if guard_index is None or feature is None:
            return
        self.guarded_functions += 1
        guard = node.body[guard_index]
        for statement in node.body[:guard_index]:
            if _statement_allowed(statement, self.allowed):
                continue
            rule = _classify(statement)
            if rule is None:
                continue
            self.findings.append(
                Finding(
                    source=self.unit.label,
                    line=getattr(statement, "lineno", 1),
                    column=getattr(statement, "col_offset", 0) + 1,
                    function=".".join(self.scope),
                    guard_line=getattr(guard, "lineno", 1),
                    feature=feature,
                    rule=rule,
                    statement=_excerpt(self.lines, statement),
                )
            )


def scan_source(
    unit: SourceUnit,
    *,
    flag_names: frozenset[str],
    allow_marker: str = DEFAULT_ALLOW_MARKER,
) -> tuple[list[Finding], list[ScanError], int]:
    try:
        tree = ast.parse(unit.text, filename=unit.label)
    except SyntaxError as exc:
        return (
            [],
            [
                ScanError(
                    source=unit.label,
                    line=exc.lineno or 0,
                    column=exc.offset or 0,
                    message=exc.msg,
                )
            ],
            0,
        )
    auditor = _Auditor(unit, flag_names, allow_marker)
    auditor.visit(tree)
    return auditor.findings, [], auditor.guarded_functions


def scan_units(
    units: Iterable[SourceUnit],
    *,
    flag_names: Iterable[str] = DEFAULT_FLAG_NAMES,
    allow_marker: str = DEFAULT_ALLOW_MARKER,
) -> ScanResult:
    flags = frozenset(name.strip() for name in flag_names if name.strip())
    if not flags:
        raise AuditInputError("at least one non-empty flag name is required")
    if not allow_marker:
        raise AuditInputError("allow marker must not be empty")

    findings: list[Finding] = []
    errors: list[ScanError] = []
    scanned = guarded = 0
    for unit in sorted(units):
        scanned += 1
        found, failed, count = scan_source(
            unit, flag_names=flags, allow_marker=allow_marker
        )
        findings.extend(found)
        errors.extend(failed)
        guarded += count
    return ScanResult(
        findings=tuple(sorted(findings)),
        errors=tuple(sorted(errors)),
        scanned_sources=scanned,
        guarded_functions=guarded,
    )


def _render_human(result: ScanResult) -> None:
    for item in result.findings:
        print(
            f"{item.source}:{item.line}:{item.column}: {item.rule}: "
            f"{item.function} touches work before disabled guard for "
            f"{item.feature} at line {item.guard_line}: {item.statement}"
        )
    for item in result.errors:
        print(
            f"{item.source}:{item.line}:{item.column}: parse_error: {item.message}"
        )
    print(
        "summary: "
        f"sources={result.scanned_sources} "
        f"guarded_functions={result.guarded_functions} "
        f"violations={len(result.findings)} errors={len(result.errors)}"
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Reject calls, mutations, imports, and control flow before "
            "disabled-feature early-return guards."
        )
    )
    parser.add_argument(
        "paths", nargs="+", help="Python files, directories, ZIPs, or tar archives"
    )
    parser.add_argument("--format", choices=("human", "json"), default="human")
    parser.add_argument(
        "--flag-name",
        action="append",
        dest="flag_names",
        help="repeatable feature-flag leaf name (defaults: enable, enabled)",
    )
    parser.add_argument(
        "--allow-marker",
        default=DEFAULT_ALLOW_MARKER,
        help=f"same-statement suppression marker (default: {DEFAULT_ALLOW_MARKER!r})",
    )
    parser.add_argument(
        "--max-member-bytes",
        type=int,
        default=DEFAULT_MAX_MEMBER_BYTES,
        help=f"maximum decompressed Python archive member (default: {DEFAULT_MAX_MEMBER_BYTES})",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        units = tuple(
            iter_source_units(args.paths, max_member_bytes=args.max_member_bytes)
        )
        if not units:
            raise AuditInputError("no Python sources found in supplied inputs")
        result = scan_units(
            units,
            flag_names=args.flag_names or DEFAULT_FLAG_NAMES,
            allow_marker=args.allow_marker,
        )
    except AuditInputError as exc:
        result = ScanResult(
            findings=(),
            errors=(ScanError("<input>", 0, 0, str(exc)),),
            scanned_sources=0,
            guarded_functions=0,
        )

    if args.format == "json":
        print(json.dumps(result.as_dict(), indent=2, sort_keys=True))
    else:
        _render_human(result)
    return 2 if result.errors else 1 if result.findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
